"""CPU-only conversion of pinned contest-native receipts; never trains or uploads.

Local: --input-dir PRIVATE --inventory-sha256 SHA --packed-dir PRIVATE
       --packed-manifest-sha256 SHA --output-dir NEW_PRIVATE --dataset-version NAME
       --authorization-note TEXT
Remote: substitute --input-artifact entity/hasla-ai-private-training/
        hasla-contest-sources[-partial]-RUN:vN for --input-dir. Only inventory and
        registered native gzip files are downloaded, never PDFs. W&B-only env.
Inspect: --inspect with either input form downloads/reads only inventory.json and
        prints its actual SHA256 plus safe counts. It does not fetch native/PDFs.
        Remote inspect needs --output-dir PRIVATE_PLACEHOLDER or WANDB_DIR pointing
        to a private workspace; the placeholder output directory is not created.

packed-dir contains exactly named manifest.json, train.text.jsonl and
validation.text.jsonl (other local files are ignored). The pinned manifest must
have target_role='solver', format='text', files.{train,validation}.{bytes,sha256}.
Existing v2 extra fields are allowed; paths in that manifest are NEVER followed.
Every packed segment's source SHA is checked, not just first-segment provenance.

Outputs are delta-only train.text.jsonl, validation.text.jsonl, metadata-only
rejected-pages.jsonl and manifest.json. Native character slices preserve source
text; token lengths are NOT measured here and require the later tokenizer gate.
"""
from collections import Counter
from contextlib import contextmanager
import argparse
import gzip
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
import unicodedata

import private_fetch_contest_sources as fetch
from import_private_books import quality

PROJECT = fetch.PROJECT
MAX_INVENTORY = 16 * 1024**2
MAX_NATIVE_COMPRESSED = 64 * 1024**2
MAX_TOTAL_COMPRESSED = 512 * 1024**2
MAX_NATIVE_RAW = 256 * 1024**2
MAX_TOTAL_RAW = 2 * 1024**3
MAX_PAGE_BYTES = fetch.MAX_NATIVE_PAGE_BYTES
MAX_PACKED_BYTES = 256 * 1024**2
MAX_PACKED_LINE = 16 * 1024**2
MAX_OUTPUT_BYTES = 256 * 1024**2
SEED = 'hasla-contest-native-delta-v1'
STATUSES = frozenset(('verified_native_extracted', 'duplicate_existing_sha256',
    'duplicate_batch_sha256', 'archive_not_found', 'quarantined', 'failed'))
STATES = frozenset(('text_ready', 'scan_suspect', 'sparse_or_damaged'))
EXTRA_CREDENTIALS = ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_CLOUD_API_KEY',
    'GOOGLE_API_KEY', 'GCP_SA_KEY', 'CLOUDFLARE_API_TOKEN', 'TAVILY_API_KEY', 'BRAVE_SEARCH_KEY')


class DeltaError(RuntimeError):
    """Fixed safe codes only; never include source text, SDK errors or env values."""


def require(condition, code):
    if not condition:
        raise DeltaError(code)


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':'), allow_nan=False) + '\n').encode('utf8')


def sha_file(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked_sha(value):
    require(isinstance(value, str) and bool(fetch.SHA.fullmatch(value)), 'invalid_sha256')
    return value


def private_path(value):
    original = Path(value).expanduser().absolute()
    require(not any(p.is_symlink() for p in (original, *original.parents)), 'symlink_path_rejected')
    target = original.resolve()
    require(not any('onedrive' in p.casefold() for p in target.parts)
            and not any((p / '.git').exists() for p in (target, *target.parents)), 'private_path_required')
    return target


def checked_file(root, name, limit, expected_sha=None, expected_size=None):
    path = root / name
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)), 'input_file_rejected')
    require(path.resolve().is_relative_to(root.resolve()), 'input_path_rejected')
    size = path.stat().st_size
    require(0 < size <= limit and (expected_size is None or size == expected_size), 'input_size_mismatch')
    if expected_sha is not None:
        require(sha_file(path) == checked_sha(expected_sha), 'input_sha256_mismatch')
    return path


def parse_json(raw, code):
    try:
        return json.loads(raw.decode('utf-8'))
    except Exception:
        raise DeltaError(code) from None


def validate_inventory(value):
    require(isinstance(value, dict) and value.get('schema_version') == 1
            and type(value.get('schema_version')) is int
            and value.get('kind') == 'private_contest_source_receipts'
            and value.get('private') is True and type(value.get('complete')) is bool
            and value.get('complete_means') == 'all_plan_names_processed_not_all_valid'
            and value.get('ocr_performed') is False
            and value.get('training_or_deployment_performed') is False, 'inventory_schema_rejected')
    checked_sha(value.get('plan_sha256')); checked_sha(value.get('source_catalog_sha256'))
    sources = value.get('sources')
    require(isinstance(sources, list) and len(sources) <= fetch.MAX_RECORDS, 'inventory_counts_rejected')
    planned = value.get('planned_source_names')
    require(type(planned) is int and 1 <= planned <= fetch.MAX_RECORDS
            and value.get('processed_source_names') == len(sources)
            and type(value.get('processed_source_names')) is int
            and value.get('remaining_source_names') == planned-len(sources)
            and type(value.get('remaining_source_names')) is int and len(sources) <= planned,
            'inventory_counts_rejected')
    require(not value['complete'] or (len(sources) == planned and value.get('stop_code') is None),
            'inventory_counts_rejected')
    require(value.get('stop_code') is None or value['stop_code'] in fetch.SOURCE_FAILURES,
            'inventory_stop_code_rejected')
    known, filenames, compressed = set(), set(), 0
    for ordinal, row in enumerate(sources):
        require(isinstance(row, dict) and row.get('status') in STATUSES
                and row.get('alias') == f'source_{ordinal:06d}.pdf'
                and fetch.safe_filename(row.get('filename'))
                and row['filename'] not in filenames
                and row.get('scientific_accuracy_verified') is False
                and row.get('problem_segmentation') == 'pending', 'receipt_schema_rejected')
        filenames.add(row['filename'])
        try: fetch.archive_url(row.get('archive_url'), row['filename'])
        except fetch.FetchError: raise DeltaError('receipt_url_rejected') from None
        size = row.get('declared_bytes')
        require(type(size) is int and 0 < size <= fetch.MAX_PDF_BYTES, 'receipt_size_rejected')
        if row.get('declared_sha256') is not None: checked_sha(row['declared_sha256'])
        status = row['status']
        if status in ('failed', 'quarantined'):
            require(row.get('failure_code') in fetch.SOURCE_FAILURES, 'receipt_failure_rejected')
            continue
        if status == 'archive_not_found': continue
        source = checked_sha(row.get('sha256'))
        require(type(row.get('bytes')) is int and row['bytes'] == size
                and (row.get('declared_sha256') is None or row['declared_sha256'] == source),
                'receipt_source_mismatch')
        if status != 'verified_native_extracted': continue
        require(source not in known, 'duplicate_verified_source_rejected')
        known.add(source)
        alias = 'native/' + row['alias'][:-4] + '.jsonl.gz'
        require(row.get('native_alias') == alias, 'native_alias_rejected')
        checked_sha(row.get('native_sha256'))
        require(type(row.get('native_bytes')) is int and 0 < row['native_bytes'] <= MAX_NATIVE_COMPRESSED,
                'native_size_rejected')
        compressed += row['native_bytes']
        counts, pages = row.get('quality_counts'), row.get('pages')
        require(type(pages) is int and 1 <= pages <= 4096 and isinstance(counts, dict)
                and not set(counts)-STATES and all(type(n) is int and n >= 0 for n in counts.values())
                and sum(counts.values()) == pages
                and type(row.get('native_characters')) is int and 0 <= row['native_characters'] <= 2**31,
                'native_counts_rejected')
        require(row.get('integrity_basis') == ('declared_sha256_verified' if row.get('declared_sha256')
                else 'catalogued_archive_download_local_sha256'), 'source_integrity_basis_rejected')
    require(compressed <= MAX_TOTAL_COMPRESSED and value.get('native_compressed_bytes') == compressed,
            'inventory_native_total_rejected')
    require(type(value.get('downloaded_body_bytes')) is int
            and 0 <= value['downloaded_body_bytes'] <= fetch.MAX_TOTAL_PDF_BYTES+65536,
            'inventory_download_total_rejected')
    require(value.get('status_counts') == dict(Counter(r['status'] for r in sources)), 'inventory_counts_rejected')
    return value


def load_inventory(root, expected_sha=None):
    path = checked_file(root, 'inventory.json', MAX_INVENTORY, expected_sha)
    return validate_inventory(parse_json(path.read_bytes(), 'inventory_json_rejected')), sha_file(path)


def reference_parts(reference, env):
    match = re.fullmatch(r'([A-Za-z0-9][A-Za-z0-9_.-]{0,127})/' + PROJECT +
                        r'/(hasla-contest-sources-(partial-)?[0-9]{1,32}):v[0-9]+', reference or '')
    require(match is not None, 'immutable_private_reference_required')
    require(env.get('WANDB_ENTITY') == match[1] and env.get('WANDB_PROJECT', PROJECT) == PROJECT
            and env.get('WANDB_BASE_URL', fetch.WANDB_API).rstrip('/') == fetch.WANDB_API,
            'private_artifact_scope_mismatch')
    return match[1], fetch.PARTIAL_TYPE if match[3] else fetch.OUTPUT_TYPE


def download_sources(reference, expected_sha, env, root, *, inspect=False,
                     privacy=fetch.assert_private, sdk_loader=None):
    """PRIVATE and immutable checks precede SDK downloads. Never calls artifact.download()."""
    try:
        root = private_path(root)
        require(inspect or expected_sha is not None, 'inventory_pin_required')
        if expected_sha is not None: checked_sha(expected_sha)
        fetch.credentials(env)
        require(not any(env.get(k) for k in EXTRA_CREDENTIALS), 'wandb_only_credentials_required')
        entity, artifact_type = reference_parts(reference, env)
        deadline = time.monotonic()+1800
        privacy(entity, env, deadline)
        with fetch.quiet():
            sdk = (sdk_loader or (lambda: importlib.import_module('wandb')))()
            api = sdk.Api(api_key=env['WANDB_API_KEY'], overrides={'base_url': fetch.WANDB_API}, timeout=30)
            artifact = api.artifact(reference, type=artifact_type)
            require(artifact.qualified_name == reference and artifact.type == artifact_type
                    and artifact.state == 'COMMITTED' and not getattr(artifact, 'is_link', False),
                    'artifact_identity_rejected')
            meta = artifact.metadata
            require(isinstance(meta, dict) and meta.get('private') is True
                    and meta.get('complete') is (artifact_type == fetch.OUTPUT_TYPE), 'artifact_metadata_rejected')
            entries = artifact.manifest.entries
            require(isinstance(entries, dict) and 1 <= len(entries) <= 2*fetch.MAX_RECORDS+1
                    and 'inventory.json' in entries, 'artifact_entries_rejected')
            totals = Counter()
            for name, entry in entries.items():
                require(isinstance(name, str) and re.fullmatch(
                    r'(?:inventory\.json|pdf/source_[0-9]{6}\.pdf|native/source_[0-9]{6}\.jsonl\.gz)', name)
                    and getattr(entry, 'ref', None) is None
                    and str(getattr(entry, 'path', name)) == name, 'artifact_path_or_reference_rejected')
                kind = name.split('/')[0]
                cap = MAX_INVENTORY if kind == 'inventory.json' else fetch.MAX_PDF_BYTES if kind == 'pdf' else MAX_NATIVE_COMPRESSED
                require(type(entry.size) is int and 0 < entry.size <= cap, 'artifact_entry_size_rejected')
                totals[kind] += entry.size
            require(totals['pdf'] <= fetch.MAX_TOTAL_PDF_BYTES and totals['native'] <= MAX_TOTAL_COMPRESSED,
                    'artifact_total_size_rejected')

            def get(name, limit, digest=None, size=None):
                entry = entries[name]
                destination = root/name
                destination.parent.mkdir(parents=True, exist_ok=True)
                bound = artifact.get_entry(name)
                require(str(getattr(bound,'path','')) == name
                        and getattr(bound,'ref',None) is None
                        and type(getattr(bound,'size',None)) is int and bound.size == entry.size,
                        'bound_artifact_entry_rejected')
                result = Path(bound.download(root=str(root), skip_cache=True))
                require(result.absolute() == destination.absolute(), 'artifact_download_path_rejected')
                return checked_file(root, name, limit, digest, entry.size if size is None else size)

            get('inventory.json', MAX_INVENTORY, expected_sha)
            report, actual_sha = load_inventory(root, expected_sha)
            require(report['complete'] is meta['complete'] and report['plan_sha256'] == meta.get('plan_sha256')
                    and report['source_catalog_sha256'] == meta.get('source_catalog_sha256'),
                    'artifact_inventory_metadata_mismatch')
            expected = {'inventory.json'}
            for receipt in report['sources']:
                if receipt['status'] != 'verified_native_extracted': continue
                native, pdf = receipt['native_alias'], 'pdf/'+receipt['alias']
                expected.update((native, pdf))
                require(native in entries and pdf in entries and entries[native].size == receipt['native_bytes']
                        and entries[pdf].size == receipt['bytes'], 'artifact_inventory_files_mismatch')
            require(set(entries) == expected, 'artifact_inventory_files_mismatch')
            if not inspect:
                for receipt in report['sources']:
                    if receipt['status'] == 'verified_native_extracted':
                        get(receipt['native_alias'], MAX_NATIVE_COMPRESSED,
                            receipt['native_sha256'], receipt['native_bytes'])
        privacy(entity, env, deadline)
        return report, actual_sha
    except (DeltaError, fetch.FetchError) as exc:
        raise DeltaError(str(exc)) from None
    except Exception:
        raise DeltaError('private_artifact_download_failed') from None


def metadata_sources(meta):
    require(isinstance(meta, dict), 'packed_metadata_rejected')
    found = set()
    native = meta.get('haslalab_provenance')
    drive = meta.get('drive_provenance')
    if isinstance(native, dict) and native.get('local_source_sha256'):
        found.add(checked_sha(native['local_source_sha256']))
    if isinstance(drive, dict) and drive.get('local_original_pdf_sha256'):
        found.add(checked_sha(drive['local_original_pdf_sha256']))
    require(bool(found), 'packed_source_sha_missing')
    return found


def load_existing(packed_dir, manifest_sha):
    root = private_path(packed_dir)
    manifest = parse_json(checked_file(root, 'manifest.json', MAX_INVENTORY, manifest_sha).read_bytes(),
                          'packed_manifest_rejected')
    require(isinstance(manifest, dict) and manifest.get('target_role') == 'solver' and manifest.get('format') == 'text'
            and isinstance(manifest.get('files'), dict), 'packed_manifest_rejected')
    sources, content, pins = {}, set(), {}
    for split in ('train', 'validation'):
        spec = manifest['files'].get(split)
        require(isinstance(spec, dict) and type(spec.get('bytes')) is int
                and 0 < spec['bytes'] <= MAX_PACKED_BYTES, 'packed_manifest_rejected')
        path = checked_file(root, split+'.text.jsonl', MAX_PACKED_BYTES, checked_sha(spec.get('sha256')), spec['bytes'])
        count = 0
        with path.open('rb') as stream:
            while line := stream.readline(MAX_PACKED_LINE+1):
                require(len(line) <= MAX_PACKED_LINE, 'packed_line_size_limit')
                if not line.strip(): continue
                row = parse_json(line, 'packed_json_rejected')
                require(isinstance(row, dict) and isinstance(row.get('text'), str)
                        and row['text'].strip() and 'messages' not in row, 'packed_record_rejected')
                meta = row.get('metadata')
                require(isinstance(meta, dict) and meta.get('split') == split
                        and row.get('split', split) == split and meta.get('target_role') == 'solver',
                        'packed_split_or_role_rejected')
                metas = [meta]
                packing = meta.get('packing')
                if packing is not None:
                    require(isinstance(packing, dict) and isinstance(packing.get('segments'), list)
                            and 1 <= len(packing['segments']) <= 10000, 'packed_segments_rejected')
                    for segment in packing['segments']:
                        require(isinstance(segment, dict), 'packed_segments_rejected')
                        child = segment.get('metadata')
                        require(isinstance(child, dict) and child.get('split') == split, 'packed_segment_split_rejected')
                        metas.append(child)
                        if segment.get('original_text_sha256'):
                            content.add(checked_sha(segment['original_text_sha256']))
                for item in metas:
                    for source in metadata_sources(item):
                        require(source not in sources or sources[source] == split, 'existing_source_split_conflict')
                        sources[source] = split
                    if item.get('text_sha256'): content.add(checked_sha(item['text_sha256']))
                content.add(hashlib.sha256(row['text'].encode()).hexdigest())
                count += 1
        require(count > 0 and (spec.get('records') is None or spec['records'] == count), 'packed_count_mismatch')
        pins[split] = {'sha256': spec['sha256'], 'bytes': spec['bytes'], 'records': count}
    return sources, content, pins


def source_split(source, seed=SEED):
    checked_sha(source)
    return 'train' if int(hashlib.sha256((seed+':'+source).encode()).hexdigest()[:16], 16)/(1<<64) < .9 else 'validation'


def page_rejection(page):
    if page.get('native_status') != 'text_ready': return 'native_page_not_text_ready'
    if page.get('ocr_performed') or page.get('machine_ocr'): return 'ocr_page_rejected'
    meta = page.get('metadata', {})
    if not isinstance(meta, dict) or meta.get('ocr_performed') or meta.get('machine_ocr'):
        return 'ocr_page_rejected'
    if page.get('scan_suspect') or meta.get('scan_suspect'): return 'scan_page_rejected'
    if any('ocr' in str(v).casefold() for v in (page.get('extraction_method',''), meta.get('extraction_method',''))):
        return 'ocr_page_rejected'
    if page.get('extraction','native') != 'native' or meta.get('extraction','native') != 'native':
        return 'nonnative_page_rejected'
    gate = page['quality_gate']
    if gate.get('status') != 'ready_for_review' or gate.get('issues') != []:
        return 'native_quality_gate_rejected'
    text = page['native_text']
    if quality(text, min_chars=80)['status'] != 'ready_for_review': return 'native_quality_recheck_rejected'
    if sum(unicodedata.category(c) == 'Co' for c in text)/max(1,len(text)) > .02:
        return 'native_private_glyph_rejected'
    if sum(not c.isspace() for c in text) < 80: return 'native_sparse_page_rejected'
    return None


def native_pages(path, receipt, budget):
    """Bound decompression before JSON parsing; validate every page, including rejects."""
    counts, characters, pages, raw_bytes = Counter(), 0, 0, 0
    try:
        with gzip.open(path, 'rb') as stream:
            while line := stream.readline(MAX_PAGE_BYTES+1):
                raw_bytes += len(line);budget['raw_bytes'] += len(line)
                require(len(line) <= MAX_PAGE_BYTES and raw_bytes <= MAX_NATIVE_RAW
                        and budget['raw_bytes'] <= MAX_TOTAL_RAW, 'native_decompression_limit')
                page = parse_json(line, 'native_page_json_rejected')
                pages += 1
                require(isinstance(page, dict) and page.get('source_sha256') == receipt['sha256']
                        and type(page.get('source_bytes')) is int and page['source_bytes'] == receipt['bytes']
                        and type(page.get('pdf_page')) is int and page['pdf_page'] == pages
                        and isinstance(page.get('native_text'), str)
                        and type(page.get('native_char_count')) is int and page['native_char_count'] == len(page['native_text'])
                        and page.get('native_status') in STATES and isinstance(page.get('quality_gate'), dict)
                        and isinstance(page.get('text_geometry'), dict)
                        and type(page.get('native_image_object_count')) is int and page['native_image_object_count'] >= 0
                        and type(page.get('rotation')) is int and page['rotation'] in (0,90,180,270)
                        and page.get('independent_scientific_review') is False
                        and page.get('problem_segmentation') == 'pending', 'native_page_schema_rejected')
                require(pages <= receipt['pages'], 'native_page_count_mismatch')
                for key in ('width', 'height'):
                    require(type(page.get(key)) in (int,float) and math.isfinite(page[key]) and page[key] > 0,
                            'native_page_geometry_rejected')
                counts[page['native_status']] += 1;characters += len(page['native_text'])
                yield page
        require(pages == receipt['pages'] and dict(counts) == receipt['quality_counts']
                and characters == receipt['native_characters'], 'native_page_count_mismatch')
    except DeltaError: raise
    except Exception: raise DeltaError('native_gzip_rejected') from None


def chunks(text, limit):
    start = 0
    while start < len(text):
        end = min(len(text), start+limit)
        if len(text)-end < 80: end = len(text)
        yield start, end, text[start:end]
        start = end


def convert_local(input_dir, inventory_sha, packed_dir, packed_manifest_sha, output_dir,
                  dataset_version, authorization_note, *, artifact_reference=None, chunk_chars=3000):
    require(isinstance(dataset_version, str) and bool(fetch.NAME.fullmatch(dataset_version))
            and isinstance(authorization_note, str) and 1 <= len(authorization_note) <= 2000
            and type(chunk_chars) is int and 80 <= chunk_chars <= 12000, 'conversion_options_rejected')
    root, output = private_path(input_dir), private_path(output_dir)
    require(not output.exists() and not output.is_relative_to(root) and not root.is_relative_to(output),
            'output_collision_or_overlap')
    packed = private_path(packed_dir)
    require(not output.is_relative_to(packed) and not packed.is_relative_to(output), 'output_collision_or_overlap')
    report, actual_sha = load_inventory(root, checked_sha(inventory_sha))
    existing, seen_content, pins = load_existing(packed, checked_sha(packed_manifest_sha))
    output.parent.mkdir(parents=True, exist_ok=True)
    budget, totals, source_notes = {'raw_bytes':0}, Counter(), []
    with tempfile.TemporaryDirectory(prefix='.contest-delta-',dir=output.parent) as temporary:
        stage = Path(temporary)/'result';stage.mkdir()
        streams = {s:(stage/(s+'.text.jsonl')).open('wb') for s in ('train','validation')}
        rejects = (stage/'rejected-pages.jsonl').open('wb')
        written = Counter()
        try:
            verified = sorted((r for r in report['sources'] if r['status'] == 'verified_native_extracted'),key=lambda r:r['sha256'])
            totals['nonverified_source_receipts_skipped'] = len(report['sources'])-len(verified)
            for receipt in verified:
                source = receipt['sha256']
                if source in existing:
                    totals['existing_source_sha_skipped'] += 1
                    source_notes.append({'source_sha256':source,'status':'skipped_existing_source','existing_split':existing[source]})
                    continue
                native = checked_file(root,receipt['native_alias'],MAX_NATIVE_COMPRESSED,
                                      receipt['native_sha256'],receipt['native_bytes'])
                split, group = source_split(source), 'contest-pdf:'+source
                ready, rejected, emitted = 0, 0, 0
                for page in native_pages(native,receipt,budget):
                    reason = page_rejection(page)
                    if reason:
                        rejects.write(canonical({'source_sha256':source,'pdf_page':page['pdf_page'],
                            'native_status':page['native_status'],'reason':reason,'training_eligible':False}))
                        rejected += 1;totals['pages_rejected'] += 1
                        continue
                    ready += 1;totals['native_ready_pages'] += 1
                    for index,(start,end,text) in enumerate(chunks(page['native_text'],chunk_chars)):
                        if sum(not c.isspace() for c in text) < 80:
                            totals['sparse_chunks_rejected'] += 1;continue
                        text_sha = hashlib.sha256(text.encode()).hexdigest()
                        if text_sha in seen_content:
                            totals['exact_duplicate_chunks_skipped'] += 1;continue
                        seen_content.add(text_sha)
                        row={'id':f'contest-delta:{source}:p{page["pdf_page"]}:c{index}',
                            'source_id':'contest-native:'+source,'document_id':group,'text':text,'review_status':'approved',
                            'metadata':{'dataset_version':dataset_version,'target_role':'solver','role':'text',
                                'content_type':'competition_problem','source_document_role':'unspecified_competition_document',
                                'group_id':group,'split':split,'split_seed':SEED,'scan_suspect':False,
                                'source_ids':['contest-native:'+source],'page_number':page['pdf_page'],
                                'haslalab_provenance':{'source_id':'contest-native:'+source,'source_family':'competition_document',
                                    'local_source_sha256':source,'original_locator':'page:'+str(page['pdf_page']),'extraction':'native'},
                                'inventory_sha256':actual_sha,'input_artifact':artifact_reference,
                                'native_file_sha256':receipt['native_sha256'],'native_page_text_sha256':hashlib.sha256(page['native_text'].encode()).hexdigest(),
                                'text_sha256':text_sha,'char_start':start,'char_end':end,
                                'native_image_object_count':page['native_image_object_count'],'source_integrity_basis':receipt['integrity_basis'],
                                'review_scope':'native_text_extraction_and_source_receipt_only','human_reviewed':False,
                                'scientifically_verified':False,'solution_verified':False,'problem_segmentation':'pending',
                                'ocr_performed':False,'training_eligible':True,'training_authorization':authorization_note,
                                'copyright_ownership_asserted':False,'third_party_license_grant_inferred':False,
                                'token_length_measured':False}}
                        raw=canonical(row);written[split] += len(raw)
                        require(written[split] <= MAX_OUTPUT_BYTES,'output_size_limit')
                        streams[split].write(raw);emitted += 1;totals[split+'_records'] += 1
                source_notes.append({'source_sha256':source,'status':'native_gate_processed','split':split,
                    'native_ready_pages':ready,'pages_rejected':rejected,'records':emitted})
                totals['new_verified_sources_processed'] += 1
        finally:
            for stream in streams.values(): stream.close()
            rejects.close()
        files={s:{'path':s+'.text.jsonl','records':totals[s+'_records'],
                  'bytes':(stage/(s+'.text.jsonl')).stat().st_size,'sha256':sha_file(stage/(s+'.text.jsonl'))}
               for s in ('train','validation')}
        manifest={'schema_version':1,'kind':'private_contest_native_delta','private':True,
            'dataset_version':dataset_version,'target_role':'solver','format':'text',
            'inventory_sha256':actual_sha,'input_artifact':artifact_reference,'source_catalog_sha256':report['source_catalog_sha256'],
            'plan_sha256':report['plan_sha256'],'partial_source_inventory':not report['complete'],
            'remaining_source_names':report['remaining_source_names'],'source_receipt_status_counts':report['status_counts'],
            'packed_manifest_sha256':packed_manifest_sha,'existing_packed_files':pins,'files':files,'totals':dict(totals),
            'source_split_method':'SHA256(seed:source_sha256), train <0.9; validation otherwise; existing source SHA always skipped',
            'split_seed':SEED,'source_notes':source_notes,'native_raw_bytes_read':budget['raw_bytes'],
            'native_extraction_gate_passed':True,'training_or_upload_performed':False,'ocr_performed':False,
            'human_reviewed':False,'scientifically_verified':False,'requires_token_length_validation_before_training':True,
            'token_length_measured':False,'character_chunk_limit':chunk_chars,'chunk_overlap':0,
            'scope':'delta-only native text slices, never synthesized questions, answers, solutions or OCR',
            'training_ready':False,'training_ready_reason':'native/provenance ready; exact tokenizer/context check is a separate mandatory stage',
            'native_sources_nonempty':bool(totals['train_records'] and totals['validation_records'])}
        (stage/'manifest.json').write_bytes(canonical(manifest))
        stage.rename(output)
    return manifest


def inspect_summary(report, inventory_sha):
    return {'event':'private_contest_inventory_inspected','inventory_sha256':inventory_sha,
            'processed_source_names':report['processed_source_names'],'remaining_source_names':report['remaining_source_names'],
            'status_counts':report['status_counts'],'native_or_pdf_content_downloaded':False,'training_performed':False}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    inputs=parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--input-dir');inputs.add_argument('--input-artifact')
    parser.add_argument('--inventory-sha256');parser.add_argument('--inspect',action='store_true')
    parser.add_argument('--packed-dir');parser.add_argument('--packed-manifest-sha256')
    parser.add_argument('--output-dir');parser.add_argument('--dataset-version');parser.add_argument('--authorization-note')
    parser.add_argument('--chunk-chars',type=int,default=3000)
    args=parser.parse_args(argv)
    if args.inventory_sha256: checked_sha(args.inventory_sha256)
    if not args.inspect:
        require(all((args.inventory_sha256,args.packed_dir,args.packed_manifest_sha256,args.output_dir,
                     args.dataset_version,args.authorization_note)), 'conversion_arguments_required')
    if args.input_dir:
        root=private_path(args.input_dir)
        report, actual=load_inventory(root,args.inventory_sha256)
        result=inspect_summary(report,actual) if args.inspect else convert_local(root,actual,args.packed_dir,
            args.packed_manifest_sha256,args.output_dir,args.dataset_version,args.authorization_note,chunk_chars=args.chunk_chars)
    else:
        require(args.inspect or args.output_dir,'private_output_required')
        parent=private_path(args.output_dir).parent if args.output_dir else private_path(os.environ.get('WANDB_DIR',''))
        require(bool(args.output_dir or os.environ.get('WANDB_DIR')),'private_inspection_workspace_required')
        parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.contest-input-',dir=parent) as temporary:
            root=Path(temporary)
            report,actual=download_sources(args.input_artifact,args.inventory_sha256,os.environ,root,inspect=args.inspect)
            result=inspect_summary(report,actual) if args.inspect else convert_local(root,actual,args.packed_dir,
                args.packed_manifest_sha256,args.output_dir,args.dataset_version,args.authorization_note,
                artifact_reference=args.input_artifact,chunk_chars=args.chunk_chars)
    if args.inspect: print(json.dumps(result),flush=True)
    else: print(json.dumps({'event':'private_contest_delta_prepared','files':result['files'],
        'totals':result['totals'],'training_ready':result['training_ready'],'token_length_measured':False,
        'training_or_upload_performed':False}),flush=True)
    return result


if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(json.dumps({'event':'private_contest_delta_stopped',
            'reason':str(exc) if isinstance(exc,DeltaError) else 'local_configuration_or_conversion_failed',
            'raw_content_printed':False,'training_performed':False}),flush=True)
        raise SystemExit(1)

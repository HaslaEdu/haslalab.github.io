"""CPU-only, bounded acquisition from the catalogued Hasla PDF archive.

--prepare reads local metadata only. A transfer consumes one immutable, pinned
plan in an already PRIVATE W&B project; it never accepts arbitrary fetch URLs.
Raw files and partial receipts remain in an exclusive private output directory.
No training, GPU API, model token, production deployment or automatic retry.
"""
from collections import Counter
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import argparse
import base64
import gzip
import hashlib
import importlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unicodedata
from urllib.parse import unquote, urlsplit


PROJECT = 'hasla-ai-private-training'
WANDB_API = 'https://api.wandb.ai'
ARCHIVE_HOST = 'haslalab-pdf.haslalab.workers.dev'
PLAN_FILE = 'contest-fetch-plan.json'
PLAN_TYPE = 'contest-source-plan'
OUTPUT_TYPE = 'contest-source'
PARTIAL_TYPE = 'contest-source-partial'
MAX_PLAN_BYTES = 8 * 1024**2
MAX_PDF_BYTES = 64 * 1024**2
MAX_TOTAL_PDF_BYTES = 3 * 1024**3
MAX_TOTAL_NATIVE_BYTES = 512 * 1024**2
MAX_NATIVE_PAGE_BYTES = 4 * 1024**2
MAX_RECORDS = 6000
TRANSFER_SECONDS = 3600
UPLOAD_SECONDS = 600
WORKER_SECONDS = TRANSFER_SECONDS + UPLOAD_SECONDS
INLINE_MANIFEST = 'HASLA_CONTEST_FETCH_MANIFEST'
INLINE_PREFIX = 'HASLA_CONTEST_FETCH_PLAN_'
SHA = re.compile(r'[0-9a-f]{64}\Z')
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z')
FORBIDDEN_CREDENTIALS = ('RUNPOD_API_KEY', 'HF_TOKEN', 'HF_API_TOKEN', 'HF_API_KEY', 'HUGGINGFACE_TOKEN',
                         'HUGGING_FACE_HUB_TOKEN', 'HUGGINGFACE_HUB_TOKEN', 'HUGGINGFACEHUB_API_TOKEN')
ITEM_FAILURES = frozenset(('archive_size_mismatch', 'archive_item_size_limit', 'archive_sha256_mismatch',
    'archive_pdf_magic_mismatch', 'pdf_structure_rejected', 'native_parse_failed', 'native_page_size_limit'))
WORKER_FAILURES = frozenset(('transfer_deadline', 'worker_process_failed', 'worker_cleanup_unconfirmed'))
SOURCE_FAILURES = ITEM_FAILURES | WORKER_FAILURES | frozenset((
    'archive_access_stopped', 'archive_response_rejected', 'archive_content_encoding_rejected',
    'archive_total_size_limit', 'archive_body_rejected', 'native_output_rejected', 'native_total_size_limit',
    'private_output_collision', 'private_storage_or_transfer_failed', 'archive_or_native_processing_failed'))


class FetchError(RuntimeError):
    """Only fixed, nonsensitive codes are passed to this exception."""


@contextmanager
def quiet():
    """Discard SDK/PDF diagnostics, including native writes to stdout/stderr."""
    with open(os.devnull, 'w', encoding='utf8') as sink:
        saved = []
        try:
            for fd in (1, 2):
                saved.append((fd, os.dup(fd)))
                os.dup2(sink.fileno(), fd)
            with redirect_stdout(sink), redirect_stderr(sink):
                yield
        finally:
            for fd, original in reversed(saved):
                os.dup2(original, fd)
                os.close(original)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def remaining(deadline, clock):
    seconds = deadline - clock()
    if not math.isfinite(seconds) or seconds <= 0:
        raise FetchError('transfer_deadline')
    return seconds


def private_path(path):
    target = Path(path).resolve()
    if any('onedrive' in part.lower() for part in target.parts):
        raise FetchError('private_output_path_required')
    if any((parent / '.git').exists() for parent in (target, *target.parents)):
        raise FetchError('private_output_path_required')
    return target


def safe_filename(value):
    return (isinstance(value, str) and 5 <= len(value) <= 240 and value.lower().endswith('.pdf')
            and value not in ('.pdf', '..pdf') and not any(c in value for c in '/\\%?#:')
            and not any(ord(c) < 32 or ord(c) == 127 for c in value))


def archive_url(url, filename):
    if not isinstance(url, str) or not safe_filename(filename):
        raise FetchError('invalid_archive_url')
    try:
        parts = urlsplit(url)
        valid = (parts.scheme == 'https' and parts.netloc == ARCHIVE_HOST and parts.hostname == ARCHIVE_HOST
                 and parts.port is None and not parts.username and not parts.password
                 and not parts.query and not parts.fragment and unquote(parts.path) == '/pdf/' + filename)
    except ValueError:
        valid = False
    if not valid:
        raise FetchError('invalid_archive_url')
    return url


def checked_sha(value, code='invalid_sha256'):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise FetchError(code)
    return value


def validate_resume_provenance(value,count):
    required={'version','parent_plan_sha256','parent_source_names','prior_inventory_sha256',
              'prior_artifacts','source_ordinals','completed_source_names','request_spacing_milliseconds'}
    if (not isinstance(value,dict) or set(value)!=required or type(value['version']) is not int
            or value['version']!=1 or type(value['request_spacing_milliseconds']) is not int
            or value['request_spacing_milliseconds']!=5010 or type(count) is not int or not 1<=count<=256
            or type(value['parent_source_names']) is not int or not 1<=value['parent_source_names']<=MAX_RECORDS
            or type(value['completed_source_names']) is not int
            or not 0<=value['completed_source_names']<value['parent_source_names']
            or value['completed_source_names']+count>value['parent_source_names']):
        raise FetchError('invalid_resume_provenance')
    checked_sha(value['parent_plan_sha256'],'invalid_resume_provenance')
    pins,refs,ordinals=value['prior_inventory_sha256'],value['prior_artifacts'],value['source_ordinals']
    if (not isinstance(pins,list) or not 1<=len(pins)<=16 or any(not isinstance(p,str) for p in pins)
            or len(set(pins))!=len(pins) or not isinstance(refs,list) or len(refs)!=len(pins)
            or not isinstance(ordinals,list) or len(ordinals)!=count
            or any(type(i) is not int or not 0<=i<value['parent_source_names'] for i in ordinals)
            or ordinals!=sorted(set(ordinals))):
        raise FetchError('invalid_resume_provenance')
    for pin in pins:checked_sha(pin,'invalid_resume_provenance')
    for ref in refs:
        if not isinstance(ref,str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/'+PROJECT+r'/hasla-contest-sources-(?:partial-)?[0-9]{1,32}:v[0-9]+',ref):
            raise FetchError('invalid_resume_provenance')
    return value


def validate_plan(plan):
    keys={'schema_version', 'kind', 'private', 'source_catalog_sha256',
            'records', 'exclude_sha256', 'total_declared_bytes', 'excluded_cached_aliases', 'excluded_delta_names'}
    if not isinstance(plan, dict) or set(plan) not in (keys,keys|{'resume_provenance'}):
        raise FetchError('invalid_plan_schema')
    if (type(plan['schema_version']) is not int or plan['schema_version'] != 1
            or plan['kind'] != 'contest_source_fetch_plan' or plan['private'] is not True):
        raise FetchError('invalid_plan_schema')
    checked_sha(plan['source_catalog_sha256'])
    for key in ('excluded_cached_aliases', 'excluded_delta_names'):
        if type(plan[key]) is not int or not 0 <= plan[key] <= 15000:
            raise FetchError('invalid_plan_counts')
    excluded = plan['exclude_sha256']
    if not isinstance(excluded, list) or len(excluded) > 15000 or len(set(excluded)) != len(excluded):
        raise FetchError('invalid_excluded_hashes')
    for value in excluded:
        checked_sha(value)
    rows = plan['records']
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_RECORDS:
        raise FetchError('invalid_plan_counts')
    filenames, total = set(), 0
    for ordinal, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {'alias', 'filename', 'archive_url', 'declared_bytes', 'declared_sha256'}:
            raise FetchError('invalid_plan_record')
        if row['alias'] != f'source_{ordinal:06d}.pdf' or row['filename'] in filenames:
            raise FetchError('invalid_plan_record')
        archive_url(row['archive_url'], row['filename'])
        filenames.add(row['filename'])
        if type(row['declared_bytes']) is not int or not 1 <= row['declared_bytes'] <= MAX_PDF_BYTES:
            raise FetchError('invalid_pdf_size')
        if row['declared_sha256'] is not None:
            checked_sha(row['declared_sha256'])
        total += row['declared_bytes']
    if type(plan['total_declared_bytes']) is not int or total != plan['total_declared_bytes'] or total > MAX_TOTAL_PDF_BYTES:
        raise FetchError('invalid_total_size')
    if 'resume_provenance' in plan:
        validate_resume_provenance(plan['resume_provenance'],len(rows))
    return plan


def prepare_plan(catalog_path, cache_status_directory, delta_inventory_path, output_path):
    """Read metadata; do not open PDFs or contact any service."""
    catalog_path = Path(catalog_path)
    if not 0 < catalog_path.stat().st_size <= 32 * 1024**2:
        raise FetchError('catalog_size_limit')
    raw = catalog_path.read_bytes()
    catalog = [json.loads(line) for line in raw.decode('utf8').splitlines() if line.strip()]
    cached, delta, excluded_hashes = set(), set(), set()
    for path in Path(cache_status_directory).glob('*.json'):
        if path.stat().st_size > 1024**2:
            raise FetchError('cache_metadata_size_limit')
        value = json.loads(path.read_text(encoding='utf8'))
        if not safe_filename(value.get('filename')):
            raise FetchError('invalid_cache_metadata')
        cached.add(value['filename'])
        excluded_hashes.add(checked_sha(value.get('sha256')))
    delta_path = Path(delta_inventory_path)
    if not 0 < delta_path.stat().st_size <= MAX_PLAN_BYTES:
        raise FetchError('delta_metadata_size_limit')
    for line in delta_path.read_text(encoding='utf8').splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if (value.get('status') != 'declared_hash_verified_native_extracted'
                or value.get('declared_sha256_match') is not True or value.get('original_unchanged_verified') is not True
                or not safe_filename(value.get('filename'))):
            raise FetchError('unverified_delta_metadata')
        delta.add(value['filename'])
        excluded_hashes.add(checked_sha(value.get('sha256')))
    records = []
    for value in catalog:
        if value.get('filename') in cached | delta:
            continue
        declared = value.get('declared_sha256_candidates') or []
        if value.get('declared_sha_conflict') or not isinstance(declared, list) or len(declared) > 1:
            raise FetchError('conflicting_catalog_sha256')
        records.append({'alias': f'source_{len(records):06d}.pdf', 'filename': value.get('filename'),
                        'archive_url': value.get('archive_url'), 'declared_bytes': value.get('declared_bytes'),
                        'declared_sha256': declared[0] if declared else None})
    plan = validate_plan({'schema_version': 1, 'kind': 'contest_source_fetch_plan', 'private': True,
                         'source_catalog_sha256': hashlib.sha256(raw).hexdigest(), 'records': records,
                         'exclude_sha256': sorted(excluded_hashes),
                         'total_declared_bytes': sum(r['declared_bytes'] for r in records),
                         'excluded_cached_aliases': len(cached), 'excluded_delta_names': len(delta)})
    encoded = canonical(plan)
    if len(encoded) > MAX_PLAN_BYTES:
        raise FetchError('plan_size_limit')
    target = private_path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(encoded)
    return {'source_names': len(records), 'not_proven_unique': True,
            'declared_bytes': plan['total_declared_bytes'], 'plan_sha256': hashlib.sha256(encoded).hexdigest()}


def credentials(env):
    if any(env.get(key) for key in FORBIDDEN_CREDENTIALS) or not env.get('WANDB_API_KEY'):
        raise FetchError('wandb_only_credentials_required')


def inline_present(env):
    return INLINE_MANIFEST in env or any(key.startswith(INLINE_PREFIX) for key in env)


def decode_inline_plan(env):
    """Decode encrypted-secret payloads in memory; bound gzip before parsing."""
    try:
        encoded_manifest = env.get(INLINE_MANIFEST, '')
        if not isinstance(encoded_manifest, str) or not 0 < len(encoded_manifest) <= 16384:
            raise FetchError('invalid_inline_manifest')
        manifest = json.loads(encoded_manifest)
        if (not isinstance(manifest, dict) or set(manifest) != {'version', 'kind', 'raw_bytes',
                'raw_sha256', 'encoded_sha256', 'parts'} or type(manifest['version']) is not int
                or manifest['version'] != 1 or manifest['kind'] != 'contest_source_fetch_plan'
                or type(manifest['parts']) is not int or not 1 <= manifest['parts'] <= 16
                or type(manifest['raw_bytes']) is not int or not 1 <= manifest['raw_bytes'] <= 2 * 1024**2):
            raise FetchError('invalid_inline_manifest')
        for key in ('raw_sha256', 'encoded_sha256'):
            checked_sha(manifest[key])
        keys = {f'{INLINE_PREFIX}{i:02d}' for i in range(manifest['parts'])}
        if {key for key in env if key.startswith(INLINE_PREFIX)} != keys:
            raise FetchError('invalid_inline_parts')
        values = [env[f'{INLINE_PREFIX}{i:02d}'] for i in range(manifest['parts'])]
        if any(not isinstance(value, str) or not value.isascii() or not 0 < len(value) <= 40000 for value in values):
            raise FetchError('invalid_inline_parts')
        encoded = ''.join(values).encode('ascii')
        if hashlib.sha256(encoded).hexdigest() != manifest['encoded_sha256']:
            raise FetchError('inline_encoded_hash_mismatch')
        compressed = base64.b64decode(encoded, validate=True)
        if len(compressed) > 640000:
            raise FetchError('inline_compressed_size_limit')
        with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode='rb') as stream:
            raw = stream.read(manifest['raw_bytes'] + 1)
        if len(raw) != manifest['raw_bytes'] or hashlib.sha256(raw).hexdigest() != manifest['raw_sha256']:
            raise FetchError('inline_raw_hash_or_size_mismatch')
        return validate_plan(json.loads(raw.decode('utf8'))), manifest['raw_sha256']
    except FetchError:
        raise
    except Exception:
        raise FetchError('invalid_inline_payload') from None


def private_entity(env, deadline, clock=time.monotonic, post=None):
    entity = env.get('WANDB_ENTITY')
    if entity:
        if not isinstance(entity, str) or not NAME.fullmatch(entity):
            raise FetchError('invalid_private_entity')
        return entity
    if post is None:
        post = importlib.import_module('requests').post
    response = None
    try:
        with quiet():
            response = post(WANDB_API + '/graphql', auth=('api', env['WANDB_API_KEY']),
                            json={'query': '{viewer{entity}}'}, timeout=min(20, remaining(deadline, clock)))
            if not response.ok:
                raise FetchError('private_entity_unavailable')
            value = response.json()
        entity = ((value.get('data') or {}).get('viewer') or {}).get('entity')
        if value.get('errors') or not isinstance(entity, str) or not NAME.fullmatch(entity):
            raise FetchError('private_entity_unavailable')
        return entity
    except FetchError:
        raise
    except Exception:
        raise FetchError('private_entity_unavailable') from None
    finally:
        if response is not None:
            response.close()


def required_disk_bytes(plan):
    return 2 * (plan['total_declared_bytes'] + MAX_TOTAL_NATIVE_BYTES) + 256 * 1024**2


def reference_parts(reference):
    if not isinstance(reference, str):
        raise FetchError('invalid_private_artifact_reference')
    match = re.fullmatch(r'([A-Za-z0-9][A-Za-z0-9_.-]{0,127})/' + PROJECT + r'/([A-Za-z0-9][A-Za-z0-9_.-]{0,127}):v[0-9]+', reference)
    if not match:
        raise FetchError('invalid_private_artifact_reference')
    return match.group(1)


def assert_private(entity, env, deadline, clock=time.monotonic, post=None):
    if post is None:
        post = importlib.import_module('requests').post
    response = None
    try:
        with quiet():
            response = post(WANDB_API + '/graphql', auth=('api', env['WANDB_API_KEY']),
                json={'query': 'query($e:String!,$p:String!){project(name:$p,entityName:$e){name access}}',
                      'variables': {'e': entity, 'p': PROJECT}}, timeout=min(20, remaining(deadline, clock)))
            if not response.ok:
                raise FetchError('private_project_unavailable')
            value = response.json()
        project = (value.get('data') or {}).get('project') if isinstance(value, dict) else None
        if value.get('errors') or not isinstance(project, dict) or project.get('name') != PROJECT or project.get('access') != 'PRIVATE':
            raise FetchError('private_project_not_verified')
    except FetchError:
        raise
    except Exception:
        raise FetchError('private_project_unavailable') from None
    finally:
        if response is not None:
            response.close()


def load_private_plan(reference, expected_sha, env, temporary, deadline, clock=time.monotonic,
                      privacy=assert_private, sdk_loader=None):
    credentials(env)
    entity = reference_parts(reference)
    checked_sha(expected_sha)
    privacy(entity, env, deadline, clock)
    try:
        with quiet():
            sdk = (sdk_loader or (lambda: importlib.import_module('wandb')))()
            api = sdk.Api(api_key=env['WANDB_API_KEY'], overrides={'base_url': WANDB_API},
                          timeout=min(30, remaining(deadline, clock)))
            artifact = api.artifact(reference, type=PLAN_TYPE)
            if (artifact.qualified_name != reference or artifact.type != PLAN_TYPE or artifact.state != 'COMMITTED'
                    or getattr(artifact, 'is_link', False)):
                raise FetchError('input_artifact_identity_mismatch')
            entries = artifact.manifest.entries
            if set(entries) != {PLAN_FILE}:
                raise FetchError('input_artifact_file_mismatch')
            entry = entries[PLAN_FILE]
            if getattr(entry, 'ref', None) or type(entry.size) is not int or not 0 < entry.size <= MAX_PLAN_BYTES:
                raise FetchError('input_artifact_size_limit')
            result = Path(artifact.get_entry(PLAN_FILE).download(root=str(temporary)))
        root = Path(temporary).resolve()
        if result.is_symlink() or result.resolve().parent != root or result.name != PLAN_FILE:
            raise FetchError('input_artifact_path_mismatch')
        if result.stat().st_size != entry.size or digest(result) != expected_sha:
            raise FetchError('input_plan_hash_mismatch')
        plan = validate_plan(json.loads(result.read_text(encoding='utf8')))
        return entity, plan, sdk
    except FetchError:
        raise
    except Exception:
        raise FetchError('input_artifact_unavailable') from None


def validate_pdf(path):
    with quiet():
        import pymupdf
        with pymupdf.open(path) as document:
            if document.needs_pass or not 1 <= len(document) <= 4096:
                raise FetchError('pdf_structure_rejected')


class BoundedWriter:
    def __init__(self, stream, limit):
        self.stream, self.limit, self.written = stream, limit, 0

    def write(self, data):
        if self.written + len(data) > self.limit:
            raise FetchError('native_total_size_limit')
        count = self.stream.write(data)
        self.written += count
        return count

    def flush(self):
        self.stream.flush()


def extract_native(pdf_path, source_sha, source_bytes, native_stream, deadline, clock=time.monotonic):
    """Text and text geometry only; no OCR/image expansion or answer synthesis."""
    with quiet():
        import pymupdf
        from import_private_books import quality
        counts, pages, chars = Counter(), 0, 0
        with pymupdf.open(pdf_path) as document:
            if document.needs_pass or not 1 <= len(document) <= 4096:
                raise FetchError('pdf_structure_rejected')
            with gzip.GzipFile(fileobj=native_stream, mode='wb', mtime=0) as stream:
                for ordinal, page in enumerate(document, 1):
                    remaining(deadline, clock)
                    text = page.get_text('text', sort=False)
                    gate = quality(text, min_chars=80)
                    if sum(unicodedata.category(c) == 'Co' for c in text) / max(1, len(text)) > .02:
                        gate['issues'].append('private_use_glyph_ratio')
                        gate['status'] = 'pending_extraction'
                    images = len(page.get_images(full=True))
                    state = ('text_ready' if gate['status'] == 'ready_for_review' else
                             'scan_suspect' if len(text.strip()) < 80 and images else 'sparse_or_damaged')
                    geometry = page.get_text('dict', flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)
                    value = {'source_sha256': source_sha, 'source_bytes': source_bytes, 'pdf_page': ordinal,
                             'width': page.rect.width, 'height': page.rect.height, 'rotation': page.rotation,
                             'native_char_count': len(text), 'native_text': text, 'text_geometry': geometry,
                             'native_image_object_count': images, 'native_status': state, 'quality_gate': gate,
                             'independent_scientific_review': False, 'problem_segmentation': 'pending'}
                    encoded = canonical(value)
                    if len(encoded) > MAX_NATIVE_PAGE_BYTES:
                        raise FetchError('native_page_size_limit')
                    stream.write(encoded)
                    counts[state] += 1
                    pages += 1
                    chars += len(text)
        return {'pages': pages, 'native_characters': chars, 'quality_counts': dict(counts)}


def fetch_sources(plan, output, *, get, deadline, clock=time.monotonic, extractor=extract_native,
                  pdf_validator=validate_pdf, disk_free=None, sleep=time.sleep):
    validate_plan(plan)
    output = private_path(output)
    # SDK immutable/copy behavior may retain another full copy while uploading.
    required = required_disk_bytes(plan)
    free = (disk_free or (lambda p: shutil.disk_usage(p).free))(output.parent)
    if free < required:
        raise FetchError('insufficient_private_disk_space')
    output.mkdir(parents=False, exist_ok=False)
    (output / 'pdf').mkdir()
    (output / 'native').mkdir()
    receipts, files, known = [], [], {value: None for value in plan['exclude_sha256']}
    total_received, total_native, stop_code = 0, 0, None
    spacing=5.01 if 'resume_provenance' in plan else 0
    # The workflow's existing exclusive fetch concurrency serializes this host.
    # Waiting before the first request also preserves spacing across CI jobs.
    last_request=clock()

    def checkpoint(complete=False, code=None):
        report = {'schema_version': 1, 'kind': 'private_contest_source_receipts', 'private': True,
                  'source_catalog_sha256': plan['source_catalog_sha256'], 'plan_sha256': hashlib.sha256(canonical(plan)).hexdigest(),
                  'complete': complete, 'stop_code': code,
                  'complete_means': 'all_plan_names_processed_not_all_valid',
                  'planned_source_names': len(plan['records']), 'processed_source_names': len(receipts),
                  'remaining_source_names': len(plan['records']) - len(receipts),
                  'not_all_names_are_unique_pdfs': True, 'status_counts': dict(Counter(r['status'] for r in receipts)),
                  'downloaded_body_bytes': total_received, 'native_compressed_bytes': total_native,
                  'sources': receipts, 'ocr_performed': False, 'training_or_deployment_performed': False}
        if 'resume_provenance' in plan:report['resume_provenance']=plan['resume_provenance']
        temporary = output / 'inventory.pending.json'
        created = False
        try:
            with temporary.open('xb') as stream:
                created = True
                stream.write(canonical(report))
            os.replace(temporary, output / 'inventory.json')
        finally:
            if created:
                temporary.unlink(missing_ok=True)
        return report

    checkpoint()
    for row in plan['records']:
        response, owned, stage = None, [], 'archive_transfer'
        receipt = {key: row[key] for key in ('alias', 'filename', 'archive_url', 'declared_bytes', 'declared_sha256')}
        receipt.update(status='pending', scientific_accuracy_verified=False, problem_segmentation='pending')
        try:
            seconds = remaining(deadline, clock)
            if spacing:
                wait=max(0,spacing-(clock()-last_request))
                if wait>=remaining(deadline,clock):raise FetchError('transfer_deadline')
                if wait:sleep(wait)
                seconds=remaining(deadline,clock)
                last_request=clock()
            with quiet():
                response = get(row['archive_url'], headers={'Accept-Encoding': 'identity',
                    'User-Agent': 'HaslaContestArchivePreparation/1.0'}, allow_redirects=False,
                    stream=True, timeout=(min(5, seconds), min(15, seconds)))
            # Access/rate denial takes precedence over the common HTML error
            # representation, including replies without a challenge header.
            if response.status_code in (403, 429):
                receipt.update(archive_http_status=response.status_code,archive_response_redirected=False)
                raise FetchError('archive_access_stopped')
            if spacing and (str(response.headers.get('cf-mitigated','')).lower()=='challenge'
                    or 'text/html' in str(response.headers.get('Content-Type','')).lower()):
                if type(response.status_code) is int and 100<=response.status_code<=599:
                    receipt.update(archive_http_status=response.status_code,archive_response_redirected=False)
                raise FetchError('archive_access_stopped' if str(response.headers.get('cf-mitigated','')).lower()=='challenge'
                                 else 'archive_response_rejected')
            if response.status_code == 404:
                receipt['status'] = 'archive_not_found'
                receipts.append(receipt)
                checkpoint()
                continue
            if response.status_code != 200 or response.url != row['archive_url']:
                if type(response.status_code) is int and 100<=response.status_code<=599:
                    receipt.update(archive_http_status=response.status_code,
                        archive_response_redirected=response.status_code in (301,302,303,307,308) or response.url!=row['archive_url'])
                raise FetchError('archive_response_rejected')
            if str(response.headers.get('Content-Encoding', 'identity')).lower() not in ('', 'identity'):
                raise FetchError('archive_content_encoding_rejected')
            length = response.headers.get('Content-Length')
            if length is not None and (not str(length).isascii() or not str(length).isdigit() or int(length) != row['declared_bytes']):
                raise FetchError('archive_size_mismatch')
            part = output / 'pdf' / (row['alias'] + '.part')
            hasher, received, header = hashlib.sha256(), 0, b''
            with part.open('xb') as stream:
                owned.append(part)
                for chunk in response.iter_content(chunk_size=65536):
                    remaining(deadline, clock)
                    if not isinstance(chunk, bytes):
                        raise FetchError('archive_body_rejected')
                    if not chunk:
                        continue
                    received += len(chunk)
                    total_received += len(chunk)
                    if total_received > MAX_TOTAL_PDF_BYTES:
                        raise FetchError('archive_total_size_limit')
                    if received > row['declared_bytes'] or received > MAX_PDF_BYTES:
                        raise FetchError('archive_item_size_limit')
                    if len(header) < 5:
                        header = (header + chunk)[:5]
                    hasher.update(chunk)
                    stream.write(chunk)
            if received != row['declared_bytes']:
                raise FetchError('archive_size_mismatch')
            actual = hasher.hexdigest()
            if row['declared_sha256'] is not None and actual != row['declared_sha256']:
                raise FetchError('archive_sha256_mismatch')
            if header != b'%PDF-':
                if spacing:
                    receipt.update(archive_http_status=200,archive_response_redirected=False)
                    raise FetchError('archive_response_rejected')
                raise FetchError('archive_pdf_magic_mismatch')
            receipt.update(sha256=actual, bytes=received,
                           integrity_basis='declared_sha256_verified' if row['declared_sha256'] else 'catalogued_archive_download_local_sha256')
            stage = 'pdf_parse'
            with quiet():
                pdf_validator(part)
            if actual in known:
                receipt.update(status='duplicate_existing_sha256' if known[actual] is None else 'duplicate_batch_sha256',
                               canonical_alias=known[actual])
                part.unlink()
                owned.remove(part)
            else:
                native = output / 'native' / (row['alias'].removesuffix('.pdf') + '.jsonl.gz')
                stage = 'native_parse'
                with native.open('xb') as native_stream:
                    owned.append(native)
                    bounded = BoundedWriter(native_stream, MAX_TOTAL_NATIVE_BYTES - total_native)
                    with quiet():
                        details = extractor(part, actual, received, bounded, deadline, clock)
                if not native.is_file() or native.is_symlink():
                    raise FetchError('native_output_rejected')
                native_bytes = native.stat().st_size
                if total_native + native_bytes > MAX_TOTAL_NATIVE_BYTES:
                    raise FetchError('native_total_size_limit')
                stage = 'private_storage'
                final = output / 'pdf' / row['alias']
                if final.exists() or final.is_symlink():
                    raise FetchError('private_output_collision')
                os.link(part, final)
                owned.append(final)
                part.unlink()
                owned.remove(part)
                known[actual] = row['alias']
                receipt.update(status='verified_native_extracted', native_alias='native/' + native.name,
                               native_sha256=digest(native), native_bytes=native_bytes, **details)
                files.extend([(final, 'pdf/' + final.name), (native, 'native/' + native.name)])
                total_native += native_bytes
                owned.clear()
        except FetchError as error:
            code = str(error)
            receipt.update(status='quarantined' if code in ITEM_FAILURES else 'failed', failure_code=code)
            if code not in ITEM_FAILURES:
                stop_code = code
        except OSError:
            receipt.update(status='failed', failure_code='private_storage_or_transfer_failed')
            stop_code = 'private_storage_or_transfer_failed'
        except Exception:
            code = 'native_parse_failed' if stage in ('pdf_parse', 'native_parse') else 'archive_or_native_processing_failed'
            receipt.update(status='quarantined' if code in ITEM_FAILURES else 'failed', failure_code=code)
            if code not in ITEM_FAILURES:
                stop_code = code
        finally:
            if response is not None:
                with quiet():
                    try:
                        response.close()
                    except Exception:
                        pass
            for path in owned:
                path.unlink(missing_ok=True)
        receipts.append(receipt)
        checkpoint(code=stop_code)
        if stop_code:
            break
    report = checkpoint(complete=stop_code is None and len(receipts) == len(plan['records']), code=stop_code)
    target = output / 'inventory.json'
    files.append((target, target.name))
    return report, files


def load_checkpoint(output, plan, worker_error=None):
    """Trust only registered atomic receipts; rehash completed files after reap."""
    output = private_path(output)
    path = output / 'inventory.json'
    if (output.is_symlink() or path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= 16 * 1024**2):
        raise FetchError('verified_checkpoint_unavailable')
    try:
        report = json.loads(path.read_text(encoding='utf8'))
    except Exception:
        raise FetchError('verified_checkpoint_unavailable') from None
    if (not isinstance(report, dict) or report.get('private') is not True or report.get('schema_version') != 1
            or report.get('kind') != 'private_contest_source_receipts'
            or report.get('plan_sha256') != hashlib.sha256(canonical(plan)).hexdigest()
            or report.get('source_catalog_sha256') != plan['source_catalog_sha256']
            or type(report.get('complete')) is not bool
            or report.get('complete_means') != 'all_plan_names_processed_not_all_valid'
            or report.get('planned_source_names') != len(plan['records'])
            or report.get('resume_provenance') != plan.get('resume_provenance')
            or report.get('stop_code') is not None and report['stop_code'] not in SOURCE_FAILURES):
        raise FetchError('checkpoint_plan_mismatch')
    receipts = report.get('sources')
    if (not isinstance(receipts, list) or len(receipts) > len(plan['records'])
            or report.get('processed_source_names') != len(receipts)
            or report.get('remaining_source_names') != len(plan['records']) - len(receipts)
            or report['complete'] and (len(receipts) != len(plan['records']) or report.get('stop_code'))):
        raise FetchError('checkpoint_counts_mismatch')
    allowed = {'alias', 'filename', 'archive_url', 'declared_bytes', 'declared_sha256', 'status',
        'scientific_accuracy_verified', 'problem_segmentation', 'failure_code', 'sha256', 'bytes',
        'integrity_basis', 'canonical_alias', 'native_alias', 'native_sha256', 'native_bytes',
        'pages', 'native_characters', 'quality_counts','archive_http_status','archive_response_redirected'}
    files, safe_receipts, known = [], [], {sha: None for sha in plan['exclude_sha256']}
    for ordinal, receipt in enumerate(receipts):
        row = plan['records'][ordinal]
        if (not isinstance(receipt, dict) or set(receipt) - allowed
                or any(receipt.get(key) != row[key] for key in ('alias', 'filename', 'archive_url', 'declared_bytes', 'declared_sha256'))
                or receipt.get('scientific_accuracy_verified') is not False or receipt.get('problem_segmentation') != 'pending'):
            raise FetchError('checkpoint_source_mismatch')
        status = receipt.get('status')
        if status not in ('verified_native_extracted', 'duplicate_existing_sha256', 'duplicate_batch_sha256',
                          'archive_not_found', 'quarantined', 'failed'):
            raise FetchError('checkpoint_source_mismatch')
        if status in ('quarantined', 'failed'):
            if receipt.get('failure_code') not in SOURCE_FAILURES:
                raise FetchError('checkpoint_source_mismatch')
            safe={**row, 'status': status, 'failure_code': receipt['failure_code'],
                  'scientific_accuracy_verified': False, 'problem_segmentation': 'pending'}
            diagnostic={'archive_http_status','archive_response_redirected'} & set(receipt)
            if diagnostic:
                if (diagnostic!={'archive_http_status','archive_response_redirected'}
                        or receipt['failure_code'] not in ('archive_response_rejected','archive_access_stopped')
                        or type(receipt['archive_http_status']) is not int or not 100<=receipt['archive_http_status']<=599
                        or type(receipt['archive_response_redirected']) is not bool):
                    raise FetchError('checkpoint_source_mismatch')
                safe.update({k:receipt[k] for k in diagnostic})
            safe_receipts.append(safe)
            continue
        if status == 'archive_not_found':
            safe_receipts.append({**row, 'status': status, 'scientific_accuracy_verified': False,
                                  'problem_segmentation': 'pending'})
            continue
        actual = checked_sha(receipt.get('sha256'), 'checkpoint_source_mismatch')
        if receipt.get('bytes') != row['declared_bytes']:
            raise FetchError('checkpoint_source_mismatch')
        if row['declared_sha256'] is not None and actual != row['declared_sha256']:
            raise FetchError('checkpoint_source_mismatch')
        if status != 'verified_native_extracted':
            if actual not in known or receipt.get('canonical_alias') != known[actual]:
                raise FetchError('checkpoint_source_mismatch')
            safe_receipts.append({**row, 'status': status, 'sha256': actual, 'bytes': receipt['bytes'],
                'canonical_alias': known[actual], 'scientific_accuracy_verified': False, 'problem_segmentation': 'pending'})
            continue
        if actual in known:
            raise FetchError('checkpoint_source_mismatch')
        native_name = row['alias'].removesuffix('.pdf') + '.jsonl.gz'
        pdf, native = output / 'pdf' / row['alias'], output / 'native' / native_name
        if receipt.get('native_alias') != 'native/' + native_name:
            raise FetchError('checkpoint_source_mismatch')
        checked_sha(receipt.get('native_sha256'), 'checkpoint_source_mismatch')
        if any(p.is_symlink() for p in (output / 'pdf', output / 'native', pdf, native)):
            raise FetchError('checkpoint_file_rejected')
        if (not pdf.is_file() or not native.is_file() or pdf.stat().st_size != row['declared_bytes']
                or type(receipt.get('native_bytes')) is not int or native.stat().st_size != receipt['native_bytes']
                or digest(pdf) != actual or digest(native) != receipt['native_sha256']):
            raise FetchError('checkpoint_file_rejected')
        pages, counts = receipt.get('pages'), receipt.get('quality_counts')
        if (type(pages) is not int or not 1 <= pages <= 4096 or not isinstance(counts, dict)
                or set(counts) - {'text_ready', 'scan_suspect', 'sparse_or_damaged'}
                or any(type(n) is not int or n < 0 for n in counts.values()) or sum(counts.values()) != pages
                or type(receipt.get('native_characters')) is not int or not 0 <= receipt['native_characters'] <= 2**31):
            raise FetchError('checkpoint_source_mismatch')
        known[actual] = row['alias']
        safe_receipts.append({**row, 'status': status, 'sha256': actual, 'bytes': receipt['bytes'],
            'integrity_basis': 'declared_sha256_verified' if row['declared_sha256'] else 'catalogued_archive_download_local_sha256',
            'native_alias': 'native/' + native_name, 'native_sha256': receipt['native_sha256'],
            'native_bytes': receipt['native_bytes'], 'pages': pages, 'quality_counts': counts,
            'native_characters': receipt['native_characters'], 'scientific_accuracy_verified': False, 'problem_segmentation': 'pending'})
        files.extend([(pdf, 'pdf/' + row['alias']), (native, 'native/' + native_name)])
    if report.get('status_counts') != dict(Counter(row['status'] for row in receipts)):
        raise FetchError('checkpoint_counts_mismatch')
    received = report.get('downloaded_body_bytes')
    if type(received) is not int or not 0 <= received <= MAX_TOTAL_PDF_BYTES + 65536:
        raise FetchError('checkpoint_counts_mismatch')
    report = {'schema_version': 1, 'kind': 'private_contest_source_receipts', 'private': True,
        'source_catalog_sha256': plan['source_catalog_sha256'], 'plan_sha256': report['plan_sha256'],
        'complete': report['complete'], 'stop_code': report.get('stop_code'),
        'complete_means': 'all_plan_names_processed_not_all_valid', 'planned_source_names': len(plan['records']),
        'processed_source_names': len(receipts), 'remaining_source_names': len(plan['records']) - len(receipts),
        'not_all_names_are_unique_pdfs': True, 'status_counts': dict(Counter(row['status'] for row in receipts)),
        'downloaded_body_bytes': received,
        'native_compressed_bytes': sum(path.stat().st_size for path, name in files if name.startswith('native/')),
        'sources': safe_receipts, 'ocr_performed': False, 'training_or_deployment_performed': False}
    if 'resume_provenance' in plan:report['resume_provenance']=plan['resume_provenance']
    if worker_error:
        if worker_error not in WORKER_FAILURES:
            raise FetchError('invalid_worker_failure')
        report = {**report, 'complete': False, 'stop_code': worker_error}
    return report, files


def publish_private_sources(entity, run_id, report, files, sdk, env, deadline, clock=time.monotonic,
                            privacy=assert_private):
    if type(report.get('complete')) is not bool:
        raise FetchError('invalid_publication_report')
    complete = report['complete']
    if complete and report.get('stop_code'):
        raise FetchError('invalid_publication_report')
    if not isinstance(run_id, str) or not re.fullmatch(r'[0-9]{1,32}', run_id):
        raise FetchError('invalid_workflow_identity')
    credentials(env)
    privacy(entity, env, deadline, clock)
    artifact_name = 'hasla-contest-sources-' + ('' if complete else 'partial-') + run_id
    run, committed = None, False
    try:
        with quiet():
            if sdk is None:
                sdk = importlib.import_module('wandb')
            run = sdk.init(entity=entity, project=PROJECT, id='hasla-contest-fetch-' + run_id,
                name='hasla-contest-fetch-' + run_id, resume='never', job_type='private-contest-source-preparation',
                dir=str(private_path(files[-1][0]).parent),
                config={'private': True, 'source_count': report['planned_source_names'], 'plan_sha256': report['plan_sha256']},
                settings=sdk.Settings(console='off', silent=True, disable_code=True, save_code=False,
                    disable_git=True, disable_job_creation=True, x_disable_meta=True, x_disable_stats=True,
                    init_timeout=min(30, remaining(deadline, clock)), finish_timeout=30, base_url=WANDB_API))
            artifact = sdk.Artifact(artifact_name, type=OUTPUT_TYPE if complete else PARTIAL_TYPE, metadata={
                'private': True, 'complete': complete, 'complete_means': 'all_plan_names_processed_not_all_valid',
                'plan_sha256': report['plan_sha256'],
                'source_catalog_sha256': report['source_catalog_sha256'], 'source_count': report['planned_source_names'],
                'processed_source_names': report['processed_source_names'], 'remaining_source_names': report['remaining_source_names'],
                'stop_code': report['stop_code'],
                'status_counts': report['status_counts'], 'training_or_deployment_performed': False})
            for path, name in files:
                if not re.fullmatch(r'(?:pdf/source_[0-9]{6}\.pdf|native/source_[0-9]{6}\.jsonl\.gz|inventory\.json)', name):
                    raise FetchError('output_artifact_file_rejected')
                if path.is_symlink() or not path.is_file():
                    raise FetchError('output_artifact_file_rejected')
                remaining(deadline, clock)
                artifact.add_file(str(path), name=name, policy='immutable', skip_cache=True)
            privacy(entity, env, deadline, clock)
            run.log_artifact(artifact)
            artifact.wait(timeout=min(UPLOAD_SECONDS, remaining(deadline, clock)))
            exact = artifact.qualified_name
            if not isinstance(exact, str) or not re.fullmatch(re.escape(entity + '/' + PROJECT + '/' + artifact_name) + r':v[0-9]+', exact):
                raise FetchError('output_artifact_version_unavailable')
            committed = True
        return exact
    except FetchError:
        raise
    except Exception:
        raise FetchError('private_source_upload_failed') from None
    finally:
        if run is not None:
            with quiet():
                try:
                    run.finish(exit_code=0 if committed else 1)
                except Exception:
                    pass


def bounded_worker(command, env, *, seconds=TRANSFER_SECONDS, popen=None, kill_group=None):
    """Linux CI supervisor; fetch and publication get separate fixed limits."""
    if popen is None and os.name != 'posix':
        raise FetchError('bounded_worker_requires_linux')
    factory = popen or subprocess.Popen
    kill = kill_group or (lambda pid: os.killpg(pid, signal.SIGKILL))
    process = factory(command, env=env, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        return process.wait(timeout=seconds)
    except BaseException as error:
        try:
            kill(process.pid)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=10)
        except Exception:
            raise FetchError('worker_cleanup_unconfirmed') from None
        if isinstance(error, subprocess.TimeoutExpired):
            raise FetchError('transfer_deadline') from None
        raise


def local_worker_plan(path, expected_sha):
    path = private_path(path)
    checked_sha(expected_sha)
    if path.is_symlink() or path.name != PLAN_FILE or not 0 < path.stat().st_size <= MAX_PLAN_BYTES or digest(path) != expected_sha:
        raise FetchError('input_plan_hash_mismatch')
    return validate_plan(json.loads(path.read_text(encoding='utf8')))


def publish_checkpoint(plan, output, env, worker_error=None):
    """Run only in the separately time-bounded publisher process."""
    credentials(env)
    report, files = load_checkpoint(output, plan, worker_error)
    target = private_path(output) / 'publication-inventory.json'
    with target.open('xb') as stream:
        stream.write(canonical(report))
    files.append((target, 'inventory.json'))
    deadline = time.monotonic() + UPLOAD_SECONDS
    entity = private_entity(env, deadline)
    reference = publish_private_sources(entity, env.get('GITHUB_RUN_ID', ''), report, files,
                                        None, env, deadline)
    print(json.dumps({'event': 'private_contest_sources_staged', 'private': True, 'artifact': reference,
        'artifact_type': OUTPUT_TYPE if report['complete'] else PARTIAL_TYPE, 'complete': report['complete'],
        'source_names': report['processed_source_names'], 'remaining_source_names': report['remaining_source_names'],
        'status_counts': report['status_counts'], 'stop_code': report['stop_code']}), flush=True)
    return 0


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--catalog')
    parser.add_argument('--cache-status-directory')
    parser.add_argument('--delta-inventory')
    parser.add_argument('--input-artifact')
    parser.add_argument('--manifest-sha256')
    parser.add_argument('--out', required=True)
    parser.add_argument('--worker-child', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--local-worker-plan', help=argparse.SUPPRESS)
    parser.add_argument('--publish-worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--worker-error', choices=sorted(WORKER_FAILURES), help=argparse.SUPPRESS)
    args = parser.parse_args(arguments)
    try:
        if args.worker_child:
            mode = 'publish' if args.publish_worker else 'fetch'
            if (os.environ.get('HASLA_CONTEST_CPU_CHILD') != mode or not args.local_worker_plan
                    or args.input_artifact or args.prepare or args.preflight or inline_present(os.environ)):
                raise FetchError('invalid_worker_context')
            plan = local_worker_plan(args.local_worker_plan, args.manifest_sha256)
            if args.publish_worker:
                return publish_checkpoint(plan, args.out, os.environ, args.worker_error)
            if os.environ.get('WANDB_API_KEY') or any(os.environ.get(key) for key in FORBIDDEN_CREDENTIALS):
                raise FetchError('fetch_worker_must_not_have_credentials')
            import requests
            with requests.Session() as session:
                session.trust_env = False
                report, _ = fetch_sources(plan, args.out, get=session.get,
                                           deadline=time.monotonic() + TRANSFER_SECONDS)
            return 0 if report['complete'] else 1
        if args.local_worker_plan or args.publish_worker or args.worker_error:
            raise FetchError('invalid_worker_context')
        if args.prepare:
            if not all((args.catalog, args.cache_status_directory, args.delta_inventory)) or args.input_artifact or args.preflight:
                raise FetchError('invalid_prepare_arguments')
            result = prepare_plan(args.catalog, args.cache_status_directory, args.delta_inventory, args.out)
            print(json.dumps({'event': 'private_contest_fetch_plan', **result}), flush=True)
            return 0
        inline = inline_present(os.environ)
        if (bool(args.input_artifact) == inline or (args.input_artifact and not args.manifest_sha256)
                or (inline and args.manifest_sha256) or any((args.catalog, args.cache_status_directory, args.delta_inventory))):
            raise FetchError('invalid_transfer_arguments')
        credentials(os.environ)
        if not inline:
            reference_parts(args.input_artifact)
            checked_sha(args.manifest_sha256)
        else:
            plan, plan_sha = decode_inline_plan(os.environ)
        output = private_path(args.out)
        if output.exists():
            raise FetchError('private_output_collision')
        overall_deadline = time.monotonic() + WORKER_SECONDS
        deadline = min(overall_deadline, time.monotonic() + 120)
        if inline:
            entity = private_entity(os.environ, deadline)
            assert_private(entity, os.environ, deadline)
        else:
            with tempfile.TemporaryDirectory(prefix='hasla-private-contest-preflight-') as temporary:
                entity, plan, _ = load_private_plan(args.input_artifact, args.manifest_sha256, os.environ, temporary, deadline)
            plan_sha = args.manifest_sha256
        if args.preflight:
            if shutil.disk_usage(output.parent).free < required_disk_bytes(plan):
                raise FetchError('insufficient_private_disk_space')
            print(json.dumps({'event': 'private_contest_fetch_preflight', 'private_project': True,
                'source_names': len(plan['records']), 'not_proven_unique': True, 'declared_bytes': plan['total_declared_bytes'],
                'plan_sha256': plan_sha, 'free_space_sufficient': True}), flush=True)
            return 0
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='hasla-private-contest-control-') as directory:
            local_plan = Path(directory) / PLAN_FILE
            local_plan.write_bytes(canonical(plan))
            local_sha = digest(local_plan)
            common = [sys.executable, str(Path(__file__).resolve()), '--worker-child',
                      '--local-worker-plan', str(local_plan), '--manifest-sha256', local_sha, '--out', str(output)]
            base_env = {key: value for key, value in os.environ.items()
                        if key != INLINE_MANIFEST and not key.startswith(INLINE_PREFIX)}
            fetch_env = {key: value for key, value in base_env.items() if key != 'WANDB_API_KEY'}
            fetch_env['HASLA_CONTEST_CPU_CHILD'] = 'fetch'
            failure = None
            try:
                seconds = min(TRANSFER_SECONDS, max(1, overall_deadline - time.monotonic() - UPLOAD_SECONDS - 15))
                code = bounded_worker(common, fetch_env, seconds=seconds)
                if code not in (0, 1):
                    failure = 'worker_process_failed'
            except FetchError as error:
                if str(error) not in WORKER_FAILURES:
                    raise
                failure = str(error)
            report, _ = load_checkpoint(output, plan, failure)
            publisher_env = dict(base_env, HASLA_CONTEST_CPU_CHILD='publish', WANDB_ENTITY=entity)
            command = common + ['--publish-worker'] + (['--worker-error', failure] if failure else [])
            code = bounded_worker(command, publisher_env, seconds=min(UPLOAD_SECONDS, remaining(overall_deadline, time.monotonic)))
            if code:
                raise FetchError('private_source_upload_failed')
            return 0 if report['complete'] else 1
    except Exception as error:
        code = str(error) if isinstance(error, FetchError) else 'contest_preparation_failed'
        print(json.dumps({'event': 'private_contest_fetch_failed', 'code': code}), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

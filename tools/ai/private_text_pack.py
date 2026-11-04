"""Lossless CPU-only packing of an immutable private_contest_delta output.

prepare(input_dir, input_manifest_sha256, tokenizer_dir, tokenizer_sha256,
        tokenizer_config_sha256, output_dir, dataset_version, max_tokens=1024)

Only local tokenizer.json/tokenizer_config.json are loaded, after SHA256 checks.
tokenizers is imported lazily; no from_pretrained, model, Torch, GPU, download,
credential or API code exists here. Every original row is recovered exactly once
from contiguous character spans; complete original metadata/non-text fields stay
on each segment. EOS is the only inserted text. Same split/group/type only.
"""
from collections import Counter, defaultdict
import argparse
import copy
import hashlib
import importlib
import json
import math
from pathlib import Path
import tempfile

from private_contest_delta import (DeltaError, canonical, checked_file, checked_sha,
                                  metadata_sources, parse_json, private_path, sha_file)

CAPACITY = 1024
EOS = '<|im_end|>'
MAX_MANIFEST = 16 * 1024**2
MAX_TOKENIZER = 32 * 1024**2
MAX_TOKENIZER_CONFIG = 1024**2
MAX_INPUT = 256 * 1024**2
MAX_LINE = 16 * 1024**2
MAX_OUTPUT = 256 * 1024**2
MAX_ROWS = 250000
MAX_PIECES = 500000


class PackError(RuntimeError):
    """Only fixed, nonsensitive codes may be printed by the CLI."""


def require(condition, code):
    if not condition:
        raise PackError(code)


def text_sha(text):
    return hashlib.sha256(text.encode('utf8')).hexdigest()


def load_tokenizer(tokenizer_dir, tokenizer_sha256, tokenizer_config_sha256, *, loader=None):
    """Hash both public files before importing the local Rust tokenizer library."""
    original = Path(tokenizer_dir).expanduser().absolute()
    require(not any(p.is_symlink() for p in (original,*original.parents)), 'tokenizer_symlink_rejected')
    root = original.resolve()
    path = checked_file(root,'tokenizer.json',MAX_TOKENIZER,checked_sha(tokenizer_sha256))
    config_path = checked_file(root,'tokenizer_config.json',MAX_TOKENIZER_CONFIG,checked_sha(tokenizer_config_sha256))
    config = parse_json(config_path.read_bytes(),'tokenizer_config_json_rejected')
    require(isinstance(config,dict) and config.get('eos_token') == EOS
            and config.get('tokenizer_class') == 'Qwen2Tokenizer', 'official_qwq_config_required')
    try:
        module = (loader or (lambda:importlib.import_module('tokenizers')))()
        tokenizer = module.Tokenizer.from_file(str(path))
        tokenizer.no_truncation();tokenizer.no_padding()
        eos_ids = tokenizer.encode(EOS,add_special_tokens=False).ids
        require(len(eos_ids) == 1 and tokenizer.token_to_id(EOS) == eos_ids[0], 'one_token_eos_required')
    except PackError: raise
    except Exception: raise PackError('local_tokenizer_load_failed') from None
    return tokenizer, {'tokenizer_sha256':tokenizer_sha256,'tokenizer_bytes':path.stat().st_size,
        'tokenizer_config_sha256':tokenizer_config_sha256,'tokenizer_config_bytes':config_path.stat().st_size,
        'tokenizers_version':str(getattr(module,'__version__','unknown')),'eos_token':EOS,'eos_token_id':eos_ids[0],
        'add_special_tokens':False,'truncation_disabled':True,'padding_disabled':True,'local_files_only':True}


def measure(text, tokenizer, eos=EOS):
    try: encoded = tokenizer.encode(text+eos,add_special_tokens=False).ids
    except Exception: raise PackError('token_measurement_failed') from None
    require(isinstance(encoded,list) and encoded and encoded[-1] == tokenizer.token_to_id(eos),
            'terminal_eos_measurement_rejected')
    return len(encoded)


def split_row(row, tokenizer, eos=EOS, capacity=CAPACITY, input_index=0):
    """Bisect oversized character spans, preserving every character in order.

    Balanced subdivision avoids a greedy remainder that can isolate a short
    common footer. Every candidate is measured including EOS;
    no monotone BPE count assumption or token decode reconstruction is used.
    """
    require(type(capacity) is int and 2 <= capacity <= CAPACITY,'invalid_token_capacity')
    text = row['text'];original_sha = text_sha(text)
    pending = [(0,len(text))] if text else []
    while pending:
        start,end = pending.pop()
        count = measure(text[start:end],tokenizer,eos)
        if count > capacity:
            require(end-start > 1,'one_character_exceeds_capacity')
            middle = (start+end)//2
            pending.extend(((middle,end),(start,middle)))
            continue
        require(end > start and count <= capacity,'character_split_measurement_rejected')
        yield {'original':row,'original_id':row['id'],'original_text_sha256':original_sha,
            'input_row_index':input_index,'original_char_start':start,'original_char_end':end,
            'text':text[start:end],'segment_text_sha256':text_sha(text[start:end]),'tokens_including_eos':count}


def arrange(pieces, capacity=CAPACITY):
    """Deterministic best fit with bounded integer residual buckets."""
    groups = defaultdict(list)
    for index,piece in enumerate(pieces):
        meta = piece['original']['metadata'];size = piece['tokens_including_eos']
        require(type(size) is int and 1 <= size <= capacity,'piece_token_count_rejected')
        groups[(meta['split'],meta['group_id'],meta['content_type'])].append((index,piece))
    for key in sorted(groups):
        bins,buckets,residuals = [],defaultdict(list),0
        for item in sorted(groups[key],key=lambda p:(-p[1]['tokens_including_eos'],p[0])):
            need = item[1]['tokens_including_eos'];candidates = residuals >> need
            if candidates:
                remaining = need+(candidates & -candidates).bit_length()-1
                chosen = buckets[remaining].pop()
                if not buckets[remaining]:residuals &= ~(1 << remaining)
                bins[chosen].append(item)
            else:
                chosen,remaining = len(bins),capacity;bins.append([item])
            after = remaining-need;buckets[after].append(chosen);residuals |= 1 << after
        for parts in sorted(bins,key=lambda b:min(p[0] for p in b)):
            yield [piece for _,piece in sorted(parts,key=lambda p:p[0])]


def pack(parts, tokenizer, dataset_version, eos=EOS, capacity=CAPACITY):
    require(bool(parts),'empty_pack_rejected')
    first = parts[0]['original'];first_meta = first['metadata']
    key = tuple(first_meta[k] for k in ('split','group_id','content_type'))
    require(all(tuple(p['original']['metadata'][k] for k in ('split','group_id','content_type')) == key
                for p in parts),'packing_crossed_boundary')
    text = eos.join(p['text'] for p in parts);count = measure(text,tokenizer,eos)
    require(count <= capacity and count == sum(p['tokens_including_eos'] for p in parts),
            'packed_eos_boundary_or_capacity_rejected')
    segments,offset = [],0
    for piece in parts:
        original = piece['original'];end = offset+len(piece['text'])
        segments.append({k:piece[k] for k in ('original_id','original_text_sha256','input_row_index',
            'original_char_start','original_char_end','segment_text_sha256','tokens_including_eos')} |
            {'packed_char_start':offset,'packed_char_end':end,'metadata':copy.deepcopy(original['metadata']),
             'original_fields':copy.deepcopy({k:v for k,v in original.items() if k not in ('text','metadata')})})
        offset = end+len(eos)
    digest = text_sha(text);meta = copy.deepcopy(first_meta)
    meta.update(dataset_version=dataset_version,text_sha256=digest,tokens_including_eos=count,
        token_length_measured=True,char_start=0,char_end=len(text),
        source_ids=sorted({sid for p in parts for sid in p['original']['metadata']['source_ids']}),
        packing={'version':'lossless-original-character-spans-eos-v1','separator':eos,
                 'top_level_provenance':'first_segment','segments':segments})
    identity = hashlib.sha256(canonical({'text_sha256':digest,'key':key,
        'spans':[(s['original_id'],s['original_char_start'],s['original_char_end']) for s in segments]})).hexdigest()
    return {'id':'qwq-packed:'+identity,'text':text,'review_status':'approved','metadata':meta}


def verify_packed(row, originals, coverage, tokenizer, eos=EOS, capacity=CAPACITY):
    """Check text/metadata equality and record each immutable original span once."""
    meta = row['metadata'];segments = meta['packing']['segments'];recovered = [];offset = 0
    require(meta['text_sha256'] == text_sha(row['text']) and meta['tokens_including_eos'] == measure(row['text'],tokenizer,eos)
            and meta['tokens_including_eos'] <= capacity,'packed_remeasurement_failed')
    for segment in segments:
        original = originals.get(segment['original_id'])
        require(original is not None,'unknown_original_segment')
        start,end = segment['original_char_start'],segment['original_char_end']
        require(type(start) is int and type(end) is int and 0 <= start < end <= len(original['text']),
                'original_character_span_rejected')
        require(segment['packed_char_start'] == offset and segment['packed_char_end'] == offset+end-start,
                'packed_character_span_rejected')
        text = row['text'][segment['packed_char_start']:segment['packed_char_end']]
        require(text == original['text'][start:end] and segment['segment_text_sha256'] == text_sha(text)
                and segment['original_text_sha256'] == text_sha(original['text']), 'segment_source_text_mismatch')
        require(segment['metadata'] == original['metadata'] and segment['original_fields'] ==
            {k:v for k,v in original.items() if k not in ('text','metadata')},'original_metadata_mismatch')
        require(all(segment['metadata'][k] == meta[k] for k in ('split','group_id','content_type')),
                'packing_crossed_boundary')
        require(segment['tokens_including_eos'] == measure(text,tokenizer,eos),'segment_remeasurement_failed')
        marker = (start,end)
        require(marker not in coverage[segment['original_id']], 'original_span_repeated')
        coverage[segment['original_id']].add(marker)
        recovered.append(text);offset = segment['packed_char_end']+len(eos)
    require(eos.join(recovered) == row['text'],'nonseparator_text_inserted')


def verify_coverage(originals, coverage):
    require(set(coverage) == set(originals),'original_row_coverage_missing')
    for identifier,original in originals.items():
        end = 0
        for start,next_end in sorted(coverage[identifier]):
            require(start == end and next_end > start,'original_character_coverage_gap_or_overlap')
            end = next_end
        require(end == len(original['text']),'original_character_coverage_incomplete')


def load_input(input_dir, manifest_sha):
    root = private_path(input_dir)
    path = checked_file(root,'manifest.json',MAX_MANIFEST,checked_sha(manifest_sha))
    manifest = parse_json(path.read_bytes(),'input_manifest_json_rejected')
    require(isinstance(manifest,dict) and manifest.get('kind') == 'private_contest_native_delta'
        and manifest.get('schema_version') == 1 and manifest.get('private') is True
        and manifest.get('target_role') == 'solver' and manifest.get('format') == 'text'
        and manifest.get('native_extraction_gate_passed') is True and manifest.get('ocr_performed') is False
        and manifest.get('human_reviewed') is False and manifest.get('scientifically_verified') is False
        and manifest.get('training_or_upload_performed') is False and manifest.get('token_length_measured') is False
        and isinstance(manifest.get('files'),dict),'native_delta_manifest_required')
    splits,pins,source_splits,group_splits,contents,identifiers = {},{}, {},{}, {},set()
    for split in ('train','validation'):
        spec = manifest['files'].get(split)
        require(isinstance(spec,dict) and type(spec.get('bytes')) is int and 0 <= spec['bytes'] <= MAX_INPUT
                and type(spec.get('records')) is int and 1 <= spec['records'] <= MAX_ROWS,'input_inventory_rejected')
        path = checked_file(root,split+'.text.jsonl',MAX_INPUT,checked_sha(spec.get('sha256')),spec['bytes'])
        rows = []
        with path.open('rb') as stream:
            while line := stream.readline(MAX_LINE+1):
                require(len(line) <= MAX_LINE,'input_line_size_limit')
                if not line.strip():continue
                row = parse_json(line,'input_record_json_rejected')
                require(isinstance(row,dict) and isinstance(row.get('id'),str) and row['id']
                    and row['id'] not in identifiers and isinstance(row.get('text'),str) and row['text'].strip()
                    and 'messages' not in row and row.get('review_status') == 'approved','input_record_rejected')
                meta = row.get('metadata')
                require(isinstance(meta,dict) and meta.get('split') == split and row.get('split',split) == split
                    and meta.get('target_role') == 'solver' and meta.get('role') == 'text'
                    and isinstance(meta.get('group_id'),str) and meta['group_id']
                    and meta.get('scan_suspect') is False and meta.get('ocr_performed') is False
                    and meta.get('human_reviewed') is False and meta.get('scientifically_verified') is False
                    and meta.get('token_length_measured') is False and 'packing' not in meta
                    and isinstance(meta.get('haslalab_provenance'),dict) and meta['haslalab_provenance'].get('extraction') == 'native'
                    and isinstance(meta.get('source_ids'),list) and meta['source_ids']
                    and all(isinstance(s,str) and s for s in meta['source_ids']), 'native_row_gate_rejected')
                require(meta.get('text_sha256') == text_sha(row['text']),'input_text_sha256_mismatch')
                identifiers.add(row['id']);group = meta['group_id']
                require(group not in group_splits or group_splits[group] == split,'input_group_split_overlap')
                group_splits[group] = split
                for source in metadata_sources(meta):
                    require(source not in source_splits or source_splits[source] == split,'input_source_split_overlap')
                    source_splits[source] = split
                digest = text_sha(row['text'])
                require(digest not in contents,'duplicate_original_input_content')
                contents[digest] = split;rows.append(row)
                require(len(rows) <= MAX_ROWS,'input_record_count_limit')
        require(len(rows) == spec['records'],'input_record_count_mismatch')
        splits[split] = rows;pins[split] = {'bytes':spec['bytes'],'sha256':spec['sha256'],'records':len(rows)}
    try:
        from private_dual_run import validate_source_lineage
        for rows in splits.values():validate_source_lineage(rows,'solver')
    except Exception: raise PackError('existing_solver_source_gate_rejected') from None
    return splits,manifest,pins


def prepare(input_dir, input_manifest_sha256, tokenizer_dir, tokenizer_sha256,
            tokenizer_config_sha256, output_dir, dataset_version, max_tokens=CAPACITY):
    require(type(max_tokens) is int and 2 <= max_tokens <= CAPACITY,'invalid_token_capacity')
    require(isinstance(dataset_version,str) and 1 <= len(dataset_version) <= 128
            and all(c.isalnum() or c in '._-' for c in dataset_version),'invalid_dataset_version')
    root,output = private_path(input_dir),private_path(output_dir)
    tokenizer_root = Path(tokenizer_dir).expanduser().resolve()
    require(not output.exists() and not output.is_relative_to(root) and not root.is_relative_to(output)
            and not output.is_relative_to(tokenizer_root) and not tokenizer_root.is_relative_to(output),
            'output_collision_or_overlap')
    splits,source_manifest,input_pins = load_input(root,input_manifest_sha256)
    tokenizer,receipt = load_tokenizer(tokenizer_dir,tokenizer_sha256,tokenizer_config_sha256)
    pieces_by_split,originals_by_split,piece_hashes = {},{},{}
    piece_count = 0
    for split,rows in splits.items():
        pieces = []
        for index,row in enumerate(rows):
            source = frozenset(metadata_sources(row['metadata']))
            for piece in split_row(row,tokenizer,capacity=max_tokens,input_index=index):
                digest = piece['segment_text_sha256']
                if digest in piece_hashes:
                    prior_split,prior_source = piece_hashes[digest]
                    require(prior_split == split and prior_source == source,'duplicate_piece_crossed_split_or_source')
                else:piece_hashes[digest] = (split,source)
                pieces.append(piece);piece_count += 1
                require(piece_count <= MAX_PIECES,'piece_count_limit')
        pieces_by_split[split] = pieces;originals_by_split[split] = {r['id']:r for r in rows}
    output.parent.mkdir(parents=True,exist_ok=True)
    files,verification,categories,output_hashes,output_ids = {},{},defaultdict(Counter),{},set()
    with tempfile.TemporaryDirectory(prefix='.text-pack-',dir=output.parent) as temporary:
        stage = Path(temporary)/'result';stage.mkdir()
        for split,pieces in pieces_by_split.items():
            coverage = defaultdict(set);counts = Counter();groups,sources = set(),set();written = 0
            target = stage/(split+'.text.jsonl')
            with target.open('wb') as stream:
                for parts in arrange(pieces,capacity=max_tokens):
                    row = pack(parts,tokenizer,dataset_version,capacity=max_tokens)
                    verify_packed(row,originals_by_split[split],coverage,tokenizer,capacity=max_tokens)
                    meta = row['metadata'];digest = meta['text_sha256']
                    source = frozenset(s for p in parts for s in metadata_sources(p['original']['metadata']))
                    if digest in output_hashes:
                        require(output_hashes[digest] == (split,source),'duplicate_pack_crossed_split_or_source')
                        counts['same_source_repeated_packed_occurrences'] += 1
                    else:output_hashes[digest] = (split,source)
                    require(row['id'] not in output_ids,'duplicate_packed_identity')
                    output_ids.add(row['id']);raw = canonical(row);written += len(raw)
                    require(written <= MAX_OUTPUT,'output_size_limit')
                    stream.write(raw);counts['records'] += 1;counts['tokens_including_eos'] += meta['tokens_including_eos']
                    counts['characters'] += len(row['text']);counts['segments'] += len(parts)
                    counts['max_record_tokens'] = max(counts['max_record_tokens'],meta['tokens_including_eos'])
                    groups.add(meta['group_id']);sources.update(source)
                    categories[meta['content_type']][split+'_records'] += 1
                    categories[meta['content_type']][split+'_tokens'] += meta['tokens_including_eos']
            verify_coverage(originals_by_split[split],coverage)
            require(counts['segments'] == len(pieces),'segment_count_mismatch')
            files[split] = {'path':split+'.text.jsonl','bytes':written,'sha256':sha_file(target),
                'records':counts['records'],'tokens_including_eos':counts['tokens_including_eos'],
                'characters':counts['characters'],'source_groups':len(groups),'source_sha256_count':len(sources)}
            verification[split] = {'original_rows':len(splits[split]),'original_characters':sum(len(r['text']) for r in splits[split]),
                'segments_verified':counts['segments'],'exactly_once':True,'continuous_character_spans':True,
                'original_text_and_full_metadata_preserved':True,'max_record_tokens':counts['max_record_tokens'],
                'same_source_repeated_packed_occurrences':counts['same_source_repeated_packed_occurrences']}
        # Production loaders see these same immutable bytes, not a custom schema.
        try:
            from private_pod_train import rows_from_payload,validate_row_roles,verify_partitions
            from private_dual_run import validate_source_lineage
            from train_lora import load
            checked = []
            for split in ('train','validation'):
                values = rows_from_payload((stage/(split+'.text.jsonl')).read_bytes(),split,'text')
                validate_row_roles(values,'solver','text');validate_source_lineage(values,'solver');checked.append(values)
            verify_partitions(*checked)
            load(stage/'train.text.jsonl',data_format='text',validation_path=stage/'validation.text.jsonl',role='solver')
        except Exception:raise PackError('existing_solver_payload_gate_rejected') from None
        manifest = {'schema_version':1,'kind':'private_token_measured_text_pack','private':True,
            'dataset_version':dataset_version,'target_role':'solver','format':'text','files':files,
            'source_manifest':{'sha256':input_manifest_sha256,'kind':source_manifest['kind']},
            'source_inventory_complete':not source_manifest.get('partial_source_inventory',True),
            'source_inventory_sha256':source_manifest.get('inventory_sha256'),
            'source_artifact':source_manifest.get('input_artifact'),
            'input_files':input_pins,'token_measurement':receipt | {'max_tokens_including_eos':max_tokens,
                'measurement':'exact local tokenizer encode(text+EOS), add_special_tokens=False'},
            'packing':{'method':'deterministic best fit decreasing within split/group/content_type',
                'separator':EOS,'text_transformation':'continuous source-character splitting; EOS insertion only',
                'coverage':verification,'cross_split_source_overlap':0,'cross_split_group_overlap':0,
                'cross_split_content_overlap':0,'cross_source_exact_piece_or_pack_duplicates':0,
                'same_source_repeated_text_occurrences_preserved':True,'top_level_provenance':'first segment; every segment keeps original full metadata and non-text fields'},
            'content_types':dict(categories),'token_length_measured':True,'training_ready':True,
            'requires_token_length_validation_before_training':False,'existing_solver_gates_passed':True,
            'native_extraction_gate_passed':True,'human_reviewed':False,'scientifically_verified':False,
            'training_or_upload_performed':False,'ocr_performed':False,'model_downloaded':False,'gpu_used':False,
            'single_epoch_optimizer_steps_batch1_acc8':math.ceil(files['train']['records']/8),
            'builder_sha256':sha_file(__file__)}
        (stage/'manifest.json').write_bytes(canonical(manifest))
        # Detect input/tokenizer changes during processing before publishing output.
        require(sha_file(root/'manifest.json') == input_manifest_sha256,'input_manifest_changed_during_pack')
        for split,pin in input_pins.items():
            require(sha_file(root/(split+'.text.jsonl')) == pin['sha256'],'input_changed_during_pack')
        require(sha_file(tokenizer_root/'tokenizer.json') == tokenizer_sha256
                and sha_file(tokenizer_root/'tokenizer_config.json') == tokenizer_config_sha256,'tokenizer_changed_during_pack')
        stage.rename(output)
    return manifest


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('input-dir','input-manifest-sha256','tokenizer-dir','tokenizer-sha256',
                 'tokenizer-config-sha256','output-dir','dataset-version'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--max-tokens',type=int,default=CAPACITY)
    args=parser.parse_args(argv)
    manifest=prepare(**vars(args))
    print(json.dumps({'event':'private_text_packed','files':manifest['files'],'training_ready':True,
        'token_length_measured':True,'existing_solver_gates_passed':True,
        'manifest_sha256':sha_file(Path(args.output_dir)/'manifest.json'),
        'training_or_upload_performed':False}),flush=True)
    return manifest


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps({'event':'private_text_pack_stopped',
            'reason':str(exc) if isinstance(exc,(PackError,DeltaError)) else 'local_packing_failed',
            'raw_content_printed':False,'training_or_upload_performed':False}),flush=True)
        raise SystemExit(1)

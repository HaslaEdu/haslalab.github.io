"""Pinned private role-specific LoRA inputs and relative CPU update evidence.

No SDK imports, uploads, model imports, environment credentials, or training.
Continuing a saved LoRA via Unsloth restores adapter weights with a fresh
optimizer; this helper makes no exact optimizer/cursor-resume claim.
https://unsloth.ai/docs/basics/continued-pretraining
"""
import array
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
import tempfile


KIND = 'private_adapter_continuation'
PROJECT = 'hasla-ai-private-training'
FILES = ('adapter_config.json', 'adapter_model.safetensors')
MAX_ADAPTER_BYTES = 2 * 1024**3
MAX_CONFIG_BYTES = 1024**2
MAX_HEADER_BYTES = 8 * 1024**2
CHUNK = 1024**2
QWQ_BASES = frozenset(('Qwen/QwQ-32B', 'unsloth/QwQ-32B', 'unsloth/QwQ-32B-bnb-4bit',
                       'unsloth/QwQ-32B-unsloth-bnb-4bit'))
GEMMA_BASES = frozenset(('google/gemma-4-26B-A4B-it', 'unsloth/gemma-4-26B-A4B-it',
                        'unsloth/Gemma-4-26B-A4B-it'))
SHA = re.compile(r'[0-9a-f]{64}\Z')
ID = re.compile(r'[0-9]{1,32}\Z')
ENTITY = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z')
B_NAME = re.compile(r'(^|\.)(lora_B|lora_embedding_B)(?=\.|$)')
A_NAME = re.compile(r'(^|\.)(lora_A|lora_embedding_A)(?=\.|$)')
DTYPES = {'F32': (4, 'I', 0x7F800000, 0x7FFFFFFF),
          'F16': (2, 'H', 0x7C00, 0x7FFF), 'BF16': (2, 'H', 0x7F80, 0x7FFF)}


class ResumeError(RuntimeError):
    """Only fixed, nonsensitive codes leave this module."""


def require(condition, code):
    if not condition:
        raise ResumeError(code)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'json_duplicate_key')
        result[key] = value
    return result


def _no_constant(_):
    raise ResumeError('json_nonfinite_constant')


def _json(raw):
    try:
        return json.loads(raw, object_pairs_hook=_unique, parse_constant=_no_constant)
    except ResumeError:
        raise
    except Exception:
        raise ResumeError('invalid_json') from None


def _inventory_sha(inventory):
    return hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _sha_file(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _config(config):
    require(isinstance(config, dict), 'role_configuration_required')
    role = config.get('role')
    if role == 'solver':
        allowed, base, rank = QWQ_BASES, 'Qwen/QwQ-32B', 16
    elif role == 'chat':
        allowed, base, rank = GEMMA_BASES, 'google/gemma-4-26B-A4B-it', 8
        require(config.get('training_profile') == 'gemma-26b-qlora-v1'
                and config.get('precision') == '4bit' and config.get('training_method') == 'qlora'
                and config.get('load_in_4bit') is True and config.get('load_in_16bit') is False,
                'gemma_nf4_configuration_required')
    else:
        raise ResumeError('role_configuration_required')
    require(config.get('base_model') == base and type(config.get('default_rank')) is int
            and config['default_rank'] == rank, 'role_configuration_required')
    aliases = config.get('base_aliases')
    require(isinstance(aliases, list) and aliases
            and all(isinstance(value, str) and value in allowed for value in aliases)
            and len(set(aliases)) == len(aliases)
            and config['base_model'] in aliases, 'role_configuration_required')
    return set(aliases)


def validate_role_config(config):
    """Reject cross-role/base/rank/profile settings before any adapter I/O."""
    return _config(config)


def validate_spec(spec, roleconfig):
    """Return a detached, strict spec; prior verification IDs are informational."""
    aliases = _config(roleconfig)
    required = {'kind', 'version', 'role', 'base_model', 'rank', 'source_training_run_id', 'entity',
                'artifact', 'files', 'adapter_inventory_sha256'}
    require(isinstance(spec, dict) and required <= set(spec)
            and set(spec) <= required | {'prior_verification_run_id'}, 'invalid_continuation_spec')
    require(spec['kind'] == KIND and type(spec['version']) is int and spec['version'] == 1
            and spec['role'] == roleconfig['role'] and isinstance(spec['base_model'], str) and spec['base_model'] in aliases
            and type(spec['rank']) is int and spec['rank'] == roleconfig['default_rank'], 'invalid_continuation_spec')
    require(isinstance(spec['source_training_run_id'], str) and ID.fullmatch(spec['source_training_run_id'])
            and isinstance(spec['entity'], str) and ENTITY.fullmatch(spec['entity']), 'invalid_source_identity')
    prior = spec.get('prior_verification_run_id')
    require(prior is None or isinstance(prior, str) and ID.fullmatch(prior), 'invalid_prior_verification_id')
    expected = (spec['entity'] + '/' + PROJECT + '/hasla-private-books-'
                + spec['source_training_run_id'] + '-' + spec['role'] + '-lora:')
    reference = spec['artifact']
    require(isinstance(reference, str) and reference.startswith(expected)
            and re.fullmatch(r'v[0-9]+', reference[len(expected):]), 'invalid_source_artifact')
    inventory = spec['files']
    require(isinstance(inventory, list) and len(inventory) == 2, 'invalid_source_inventory')
    clean = []
    for name, row in zip(FILES, inventory):
        require(isinstance(row, dict) and set(row) == {'name', 'bytes', 'sha256'}
                and row['name'] == name and type(row['bytes']) is int and row['bytes'] > 0
                and isinstance(row['sha256'], str) and SHA.fullmatch(row['sha256']), 'invalid_source_inventory')
        require(row['bytes'] <= (MAX_CONFIG_BYTES if name == FILES[0] else MAX_ADAPTER_BYTES), 'source_size_limit')
        clean.append(dict(row))
    require(sum(row['bytes'] for row in clean) <= MAX_ADAPTER_BYTES, 'source_size_limit')
    require(isinstance(spec['adapter_inventory_sha256'], str) and SHA.fullmatch(spec['adapter_inventory_sha256'])
            and spec['adapter_inventory_sha256'] == _inventory_sha(clean), 'source_inventory_hash_mismatch')
    return {**spec, 'files': clean, 'prior_verification_run_id': prior}


@contextmanager
def _quiet():
    """Discard injected SDK diagnostics, including native stderr writes."""
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


def _private(privacy_callback, entity):
    try:
        with _quiet():
            value = privacy_callback(entity)
    except Exception:
        raise ResumeError('private_project_not_verified') from None
    valid = value is True or (isinstance(value, dict) and value.get('access') == 'PRIVATE'
        and value.get('entity') == entity and value.get('project', value.get('name')) == PROJECT)
    require(valid, 'private_project_not_verified')


def _private_root(path):
    raw = Path(path)
    require(raw.is_absolute() and not any('onedrive' in part.lower() for part in raw.parts), 'private_adapter_path_required')
    require(not any(part.is_symlink() for part in (raw, *raw.parents)), 'private_adapter_path_required')
    root = raw.resolve()
    require(not any((parent / '.git').exists() for parent in (root, *root.parents)), 'private_adapter_path_required')
    require(root.parent.is_dir(), 'private_adapter_parent_missing')
    return root


def _entry(entry, row):
    require(entry is not None and str(getattr(entry, 'path', '')) == row['name']
            and getattr(entry, 'ref', None) is None and type(getattr(entry, 'size', None)) is int
            and entry.size == row['bytes'], 'source_artifact_entry_invalid')


def _peft(path, aliases, rank):
    require(0 < path.stat().st_size <= MAX_CONFIG_BYTES, 'source_config_size_limit')
    value = _json(path.read_bytes())
    require(isinstance(value, dict) and value.get('peft_type') == 'LORA', 'source_adapter_type_invalid')
    require(value.get('base_model_name_or_path') in aliases, 'source_adapter_base_mismatch')
    require(type(value.get('r')) is int and value['r'] == rank, 'source_adapter_rank_mismatch')
    require(not value.get('rank_pattern'), 'source_rank_pattern_unsupported')
    if rank == 8:
        initializer = value.get('init_lora_weights', True)
        require(initializer is True or type(initializer) is str and initializer == 'gaussian',
                'source_gemma_initializer_unsupported')


def download_initial_adapter(spec, config, root, api, privacy_callback):
    """Validate and download exactly two files into a new private directory.

    privacy_callback(entity) must return True or an explicit PRIVATE
    {entity,project,access} record. The injected API may only read artifacts.
    Integrity verification here never proves that this artifact trained or that
    any future continuation changed its weights.
    """
    spec = validate_spec(spec, config)
    aliases = _config(config)
    root = _private_root(root)
    require(not root.exists(), 'initial_adapter_directory_exists')
    _private(privacy_callback, spec['entity'])
    owned, created = [], False
    try:
        with _quiet():
            artifact = api.artifact(spec['artifact'], type='lora')
            require(artifact.qualified_name == spec['artifact'] and artifact.type == 'lora'
                    and artifact.state == 'COMMITTED' and not getattr(artifact, 'is_link', False), 'source_artifact_identity_mismatch')
            metadata = artifact.metadata
            require(isinstance(metadata, dict) and metadata.get('private') is True
                    and metadata.get('role') == spec['role'] and metadata.get('base_model') == spec['base_model']
                    and type(metadata.get('rank')) is int and metadata['rank'] == spec['rank']
                    and metadata.get('adapter_sha256') == spec['adapter_inventory_sha256']
                    and metadata.get('adapter_inventory_sha256', spec['adapter_inventory_sha256']) == spec['adapter_inventory_sha256'],
                    'source_artifact_metadata_mismatch')
            if spec['role'] == 'chat':
                require(metadata.get('training_profile') == 'gemma-26b-qlora-v1'
                        and metadata.get('precision') == '4bit' and metadata.get('training_method') == 'qlora',
                        'source_artifact_profile_mismatch')
            entries = artifact.manifest.entries
            require(isinstance(entries, dict) and set(entries) == set(FILES), 'source_artifact_files_mismatch')
            for row in spec['files']:
                _entry(entries.get(row['name']), row)
        root.mkdir()
        created = True
        for row in spec['files']:
            _private(privacy_callback, spec['entity'])
            with tempfile.TemporaryDirectory(prefix='.download-', dir=root) as staging:
                with _quiet():
                    entry = artifact.get_entry(row['name'])
                    _entry(entry, row)
                    path = Path(entry.download(root=staging, skip_cache=True))
                expected = Path(staging) / row['name']
                require(path.absolute() == expected.absolute() and not path.is_symlink() and path.is_file()
                        and path.resolve() == expected.resolve() and path.stat().st_size == row['bytes'], 'downloaded_adapter_file_invalid')
                require(set(p.name for p in Path(staging).iterdir()) == {row['name']}, 'downloaded_adapter_extra_files')
                require(_sha_file(path) == row['sha256'], 'downloaded_adapter_hash_mismatch')
                target = root / row['name']
                os.link(path, target)
                owned.append(target)
        _peft(root / FILES[0], aliases, spec['rank'])
        _private(privacy_callback, spec['entity'])
        require(set(p.name for p in root.iterdir()) == set(FILES), 'downloaded_adapter_extra_files')
        return {'path': str(root), 'role': spec['role'], 'base_model': spec['base_model'], 'rank': spec['rank'],
                'artifact': spec['artifact'], 'source_training_run_id': spec['source_training_run_id'],
                'files': spec['files'], 'adapter_inventory_sha256': spec['adapter_inventory_sha256'],
                'integrity_verified': True, 'relative_weight_change_verified': False,
                'prior_verification_run_id': spec['prior_verification_run_id'],
                'prior_verification_independently_verified': False, 'optimizer_state_restored': False}
    except Exception as error:
        for path in owned:
            path.unlink(missing_ok=True)
        if created:
            try:
                root.rmdir()  # Preserve any unexpected/foreign collision file.
            except OSError:
                pass
        if isinstance(error, ResumeError):
            raise
        raise ResumeError('initial_adapter_download_failed') from None


def _layout(path, rank):
    require(type(rank) is int and rank in (8, 16), 'unsupported_continuation_rank')
    path = Path(path)
    require(not path.is_symlink() and path.is_file() and 8 < path.stat().st_size <= MAX_ADAPTER_BYTES, 'safetensors_size_limit')
    with path.open('rb') as stream:
        length = struct.unpack('<Q', stream.read(8))[0]
        require(2 <= length <= MAX_HEADER_BYTES and 8 + length <= path.stat().st_size, 'safetensors_header_size_invalid')
        raw = stream.read(length)
        try:
            text = raw.decode('utf8')
            header, end = json.JSONDecoder(object_pairs_hook=_unique, parse_constant=_no_constant).raw_decode(text)
        except ResumeError:
            raise
        except Exception:
            raise ResumeError('safetensors_header_invalid') from None
        require(raw.startswith(b'{') and all(c == ' ' for c in text[end:]) and isinstance(header, dict)
                and len(header) <= 100000, 'safetensors_header_invalid')
        data_size = path.stat().st_size - 8 - length
        tensors = {}
        for name, value in header.items():
            if name == '__metadata__':
                require(isinstance(value, dict) and all(isinstance(k, str) and isinstance(v, str)
                        for k, v in value.items()), 'safetensors_metadata_invalid')
                continue
            require(isinstance(name, str) and 0 < len(name) <= 4096 and isinstance(value, dict)
                    and set(value) == {'dtype', 'shape', 'data_offsets'}, 'tensor_header_invalid')
            dtype, shape, offsets = value['dtype'], value['shape'], value['data_offsets']
            require(isinstance(dtype, str) and dtype in DTYPES, 'tensor_dtype_unsupported')
            require(isinstance(shape, list) and len(shape) <= 32 and all(type(n) is int and 0 <= n <= MAX_ADAPTER_BYTES
                    for n in shape), 'tensor_shape_invalid')
            require(isinstance(offsets, list) and len(offsets) == 2 and all(type(n) is int for n in offsets)
                    and 0 <= offsets[0] <= offsets[1] <= data_size, 'tensor_offsets_invalid')
            elements = 1
            for dimension in shape:
                elements *= dimension
            require(elements * DTYPES[dtype][0] == offsets[1] - offsets[0], 'tensor_size_mismatch')
            tensors[name] = (dtype, shape, offsets, elements)
        cursor = 0
        for _, _, offsets, _ in sorted(tensors.values(), key=lambda value: (value[2][0], value[2][1])):
            require(offsets[0] == cursor, 'tensor_layout_invalid')
            cursor = offsets[1]
        require(cursor == data_size, 'tensor_layout_invalid')
    bs = {name: value for name, value in tensors.items() if B_NAME.search(name)}
    require(bs, 'lora_b_missing')
    paired = set()
    for name, (dtype, shape, _, elements) in bs.items():
        a = B_NAME.sub(lambda match: match[1] + match[2].replace('_B', '_A'), name, count=1)
        require(a in tensors and elements > 0 and tensors[a][3] > 0 and tensors[a][0] == dtype
                and not name.endswith('.bias'), 'lora_pair_invalid')
        a_shape = tensors[a][1]
        if len(shape) == len(a_shape) == 2:
            effective = shape[1]
            valid = (a_shape[0] == effective and (effective == rank or
                     '.experts.' in name and effective > rank and effective % rank == 0))
        elif len(shape) == len(a_shape) == 3:
            valid = shape[0] == a_shape[0] and shape[0] > 0 and shape[2] == a_shape[1] == rank
        else:
            valid = False
        require(valid, 'lora_pair_shape_unsupported')
        paired.add(a)
    require(paired == {name for name in tensors if A_NAME.search(name)}, 'lora_pair_invalid')
    return path, 8 + length, tensors, bs


def compare_lora_b(before, after, rank=16):
    """Require finite paired B tensors and measure change relative to baseline.

    Nonzero baseline weights are not update evidence. Signed zero is normalized
    before comparison/hashing. Only standard lora_B changes can verify an update;
    embedding-only changes are reported without asserting a verified update.
    """
    try:
        old_snapshot, new_snapshot = Path(before).stat(), Path(after).stat()
        old_path, old_start, old_tensors, old_bs = _layout(before, rank)
        new_path, new_start, new_tensors, new_bs = _layout(after, rank)
        require(set(old_tensors) == set(new_tensors), 'relative_tensor_names_mismatch')
        require(all(old_tensors[name][:2] == new_tensors[name][:2] for name in old_tensors), 'relative_tensor_layout_mismatch')
        require(set(old_bs) == set(new_bs), 'relative_lora_pairs_mismatch')
        old_hash, new_hash = hashlib.sha256(), hashlib.sha256()
        standard_tensors = standard_elements = embedding_tensors = embedding_elements = finite = 0
        with old_path.open('rb') as old, new_path.open('rb') as new:
            for name in sorted(old_bs):
                dtype, shape, old_offsets, _ = old_bs[name]
                new_offsets = new_bs[name][2]
                width, typecode, exponent, magnitude = DTYPES[dtype]
                descriptor = json.dumps({'name': name, 'dtype': dtype, 'shape': shape},
                                        sort_keys=True, separators=(',', ':')).encode()
                for hasher in (old_hash, new_hash):
                    hasher.update(struct.pack('<Q', len(descriptor)))
                    hasher.update(descriptor)
                old.seek(old_start + old_offsets[0])
                new.seek(new_start + new_offsets[0])
                left, changed = old_offsets[1] - old_offsets[0], 0
                while left:
                    count = min(max(width, CHUNK - CHUNK % width), left)
                    old_raw, new_raw = old.read(count), new.read(count)
                    require(len(old_raw) == len(new_raw) == count, 'relative_tensor_read_truncated')
                    old_bits, new_bits = array.array(typecode), array.array(typecode)
                    require(old_bits.itemsize == new_bits.itemsize == width, 'cpu_word_size_unsupported')
                    old_bits.frombytes(old_raw)
                    new_bits.frombytes(new_raw)
                    if sys.byteorder != 'little':
                        old_bits.byteswap()
                        new_bits.byteswap()
                    for ordinal, (old_value, new_value) in enumerate(zip(old_bits, new_bits)):
                        require(old_value & exponent != exponent and new_value & exponent != exponent, 'relative_lora_b_nonfinite')
                        if old_value & magnitude == 0:
                            old_bits[ordinal] = old_value = 0
                        if new_value & magnitude == 0:
                            new_bits[ordinal] = new_value = 0
                        changed += old_value != new_value
                        finite += 1
                    if sys.byteorder != 'little':
                        old_bits.byteswap()
                        new_bits.byteswap()
                    old_hash.update(old_bits.tobytes())
                    new_hash.update(new_bits.tobytes())
                    left -= count
                if B_NAME.search(name)[2] == 'lora_embedding_B':
                    embedding_tensors += bool(changed)
                    embedding_elements += changed
                else:
                    standard_tensors += bool(changed)
                    standard_elements += changed
        before_file_sha, after_file_sha = _sha_file(old_path), _sha_file(new_path)
        for path, snapshot in ((old_path, old_snapshot), (new_path, new_snapshot)):
            current = path.stat()
            require((current.st_ino, current.st_size, current.st_mtime_ns)
                    == (snapshot.st_ino, snapshot.st_size, snapshot.st_mtime_ns), 'relative_adapter_changed_during_inspection')
        return {'proof_method': 'relative_standard_lora_b_numeric_bits', 'all_b_finite': True,
                'b_tensor_count': len(old_bs), 'b_finite_elements_per_adapter': finite,
                'standard_b_changed_tensors': standard_tensors, 'standard_b_changed_elements': standard_elements,
                'embedding_b_changed_tensors': embedding_tensors, 'embedding_b_changed_elements': embedding_elements,
                'b_changed_tensors': standard_tensors + embedding_tensors,
                'b_changed_elements': standard_elements + embedding_elements,
                'before_b_payload_sha256': old_hash.hexdigest(), 'after_b_payload_sha256': new_hash.hexdigest(),
                'before_file_sha256': before_file_sha, 'after_file_sha256': after_file_sha,
                'signed_zero_normalized': True, 'relative_weight_change_verified': standard_tensors > 0,
                'weights_updated': standard_tensors > 0}
    except ResumeError:
        raise
    except Exception:
        raise ResumeError('relative_adapter_comparison_failed') from None

"""Stage two authenticated, encrypted private JSONL files into an existing PRIVATE project.

No GPU/model APIs, archive extraction, source uploads to Git, or project creation.
The transport descriptor is a repository secret; only fixed safe events leave CI.
"""
import base64
import contextlib
import gzip
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import re
import struct
import tempfile
import time
from urllib.parse import urlsplit

import requests


PROJECT = 'hasla-ai-private-training'
CIPHER_LIMIT = 128 * 1024**2
PLAIN_LIMIT = 512 * 1024**2
FILE_LIMIT = 256 * 1024**2
HEADER_LIMIT = 64 * 1024


class StageError(ValueError):
    pass


class Discard:
    def write(self, value):
        return len(value)
    def flush(self):
        pass


def require(condition, code):
    if not condition:
        raise StageError(code)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def strict_json(value):
    def pairs(items):
        result = {}
        for key, item in items:
            require(key not in result, 'duplicate_json_key')
            result[key] = item
        return result
    def constant(value):
        raise StageError('nonfinite_json')
    try:
        return json.loads(value, object_pairs_hook=pairs, parse_constant=constant)
    except StageError:
        raise
    except Exception:
        raise StageError('invalid_json') from None


def metadata_check(value):
    require(isinstance(value, dict) and value.get('role') in ('chat', 'solver'), 'invalid_role')
    fmt = 'chat' if value['role'] == 'chat' else 'text'
    require(value.get('format') == fmt, 'invalid_format')
    require(isinstance(value.get('dataset_version'), str)
            and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', value['dataset_version']), 'invalid_dataset_version')
    result = {key: value[key] for key in ('role', 'format', 'dataset_version')}
    for split in ('train', 'validation'):
        spec = value.get(split)
        require(isinstance(spec, dict), 'invalid_file_spec')
        require(type(spec.get('raw_bytes')) is int and 0 < spec['raw_bytes'] <= FILE_LIMIT, 'file_size_limit')
        require(type(spec.get('records')) is int and 0 < spec['records'] <= 10000000, 'invalid_record_count')
        require(isinstance(spec.get('raw_sha256'), str) and re.fullmatch(r'[a-f0-9]{64}', spec['raw_sha256']), 'invalid_file_hash')
        result[split] = {key: spec[key] for key in ('records', 'raw_bytes', 'raw_sha256')}
    return result


def descriptor_check(value):
    require(isinstance(value, dict) and type(value.get('version')) is int and value['version'] == 1, 'invalid_descriptor')
    metadata_check(value)
    parsed = urlsplit(value.get('url', ''))
    require(parsed.scheme == 'https' and re.fullmatch(r'[a-z0-9-]+\.trycloudflare\.com', parsed.hostname or '')
            and parsed.path == '/input' and not parsed.query and not parsed.fragment
            and parsed.username is None and parsed.password is None and parsed.port is None, 'invalid_transfer_url')
    require(isinstance(value.get('bearer'), str) and re.fullmatch(r'[A-Za-z0-9_-]{43}', value['bearer']), 'invalid_transfer_bearer')
    try:
        key = base64.b64decode(value.get('key_b64', ''), validate=True)
    except Exception:
        raise StageError('invalid_transfer_key') from None
    require(len(key) == 32, 'invalid_transfer_key')
    for name in ('cipher_sha256', 'header_sha256'):
        require(isinstance(value.get(name), str) and re.fullmatch(r'[a-f0-9]{64}', value[name]), 'invalid_transfer_hash')
    require(type(value.get('cipher_bytes')) is int and 40 < value['cipher_bytes'] <= CIPHER_LIMIT, 'cipher_size_limit')
    return key


def validate_corpora(metadata, files):
    from private_pod_train import rows_from_payload, verify_partitions
    from private_dual_run import validate_source_lineage
    rows = {}
    for split in ('train', 'validation'):
        raw = files[split]
        spec = metadata[split]
        require(len(raw) == spec['raw_bytes'] and sha(raw) == spec['raw_sha256'], 'raw_file_hash_mismatch')
        try:
            rows[split] = rows_from_payload(raw, split, metadata['format'])
            require(len(rows[split]) == spec['records'], 'record_count_mismatch')
            validate_source_lineage(rows[split], metadata['role'])
        except StageError:
            raise
        except Exception:
            raise StageError('source_or_row_validation_failed') from None
    try:
        verify_partitions(rows['train'], rows['validation'])
    except Exception:
        raise StageError('source_split_overlap') from None


def make_bundle(role, dataset_version, train, validation, *, key=None, nonce=None):
    """Local pure preparation; validates observed sources before encryption."""
    from nacl.secret import SecretBox
    import secrets
    require(role in ('chat', 'solver'), 'invalid_role')
    metadata = {'role': role, 'format': 'chat' if role == 'chat' else 'text', 'dataset_version': dataset_version}
    files = {'train': train, 'validation': validation}
    for split, raw in files.items():
        require(isinstance(raw, bytes) and 0 < len(raw) <= FILE_LIMIT, 'file_size_limit')
        metadata[split] = {'raw_bytes': len(raw), 'raw_sha256': sha(raw),
                           'records': sum(bool(line.strip()) for line in raw.splitlines())}
    metadata = metadata_check(metadata)
    validate_corpora(metadata, files)
    header = json.dumps(metadata, sort_keys=True, separators=(',', ':')).encode()
    framed = struct.pack('>Q', len(header)) + header + train + validation
    require(len(header) <= HEADER_LIMIT and len(framed) <= PLAIN_LIMIT, 'plain_size_limit')
    compressed = gzip.compress(framed, mtime=0)
    require(len(compressed) + 40 <= CIPHER_LIMIT, 'cipher_size_limit')
    key = secrets.token_bytes(32) if key is None else key
    cipher = bytes(SecretBox(key).encrypt(compressed, nonce=nonce))
    descriptor = {**metadata, 'version': 1, 'key_b64': base64.b64encode(key).decode(),
        'bearer': secrets.token_urlsafe(32), 'cipher_sha256': sha(cipher),
        'cipher_bytes': len(cipher), 'header_sha256': sha(header)}
    return cipher, descriptor


def decode_bundle(cipher, descriptor):
    from nacl.secret import SecretBox
    key = descriptor_check(descriptor)
    require(isinstance(cipher, bytes) and len(cipher) == descriptor['cipher_bytes'] and sha(cipher) == descriptor['cipher_sha256'], 'cipher_hash_mismatch')
    try:
        compressed = SecretBox(key).decrypt(cipher)
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
            plain = stream.read(PLAIN_LIMIT + 1)
    except Exception:
        raise StageError('decrypt_or_gzip_failed') from None
    require(8 < len(plain) <= PLAIN_LIMIT, 'plain_size_limit')
    size = struct.unpack('>Q', plain[:8])[0]
    require(0 < size <= HEADER_LIMIT and 8 + size <= len(plain), 'invalid_header_size')
    header = plain[8:8 + size]
    require(sha(header) == descriptor['header_sha256'], 'header_hash_mismatch')
    metadata = metadata_check(strict_json(header))
    require(metadata == metadata_check(descriptor), 'header_metadata_mismatch')
    require(len(plain) == 8 + size + sum(metadata[split]['raw_bytes'] for split in ('train', 'validation')), 'frame_length_mismatch')
    start = 8 + size
    middle = start + metadata['train']['raw_bytes']
    files = {'train': plain[start:middle], 'validation': plain[middle:]}
    validate_corpora(metadata, files)
    return metadata, files


def fetch_cipher(descriptor, *, get=None, clock=None):
    get = requests.get if get is None else get
    clock = time.monotonic if clock is None else clock
    descriptor_check(descriptor)
    response = None
    try:
        start = clock()
        response = get(descriptor['url'], headers={'Authorization': 'Bearer ' + descriptor['bearer']},
                       stream=True, allow_redirects=False, timeout=(5, 30))
        require(response.status_code == 200, 'cipher_fetch_failed')
        length = response.headers.get('Content-Length')
        require(length is not None and length.isdecimal() and int(length) == descriptor['cipher_bytes'], 'cipher_length_mismatch')
        parts, total = [], 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            require(clock() - start <= 600, 'cipher_fetch_deadline')
            total += len(chunk)
            require(total <= descriptor['cipher_bytes'] and total <= CIPHER_LIMIT, 'cipher_size_limit')
            parts.append(chunk)
        cipher = b''.join(parts)
        require(len(cipher) == descriptor['cipher_bytes'] and sha(cipher) == descriptor['cipher_sha256'], 'cipher_hash_mismatch')
        return cipher
    except StageError:
        raise
    except Exception:
        raise StageError('cipher_fetch_failed') from None
    finally:
        if response is not None:
            response.close()


def existing_private_project(query):
    viewer = query('{viewer{entity}}')
    entity = (viewer.get('viewer') or {}).get('entity')
    require(isinstance(entity, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', entity), 'private_project_unverified')
    assert_private(query, entity)
    return entity


def assert_private(query, entity):
    project = query('query($e:String!,$p:String!){project(name:$p,entityName:$e){name access}}',
                    {'e': entity, 'p': PROJECT}).get('project')
    require(isinstance(project, dict) and project.get('name') == PROJECT and project.get('access') == 'PRIVATE', 'private_project_unverified')


def stage(env=None, *, query=None, get=None, sdk=None):
    env = os.environ if env is None else env
    model_credentials = {'HF_TOKEN', 'HF_API_TOKEN', 'HUGGING_FACE_HUB_TOKEN', 'HUGGINGFACE_TOKEN',
                         'HUGGINGFACEHUB_API_TOKEN', 'HUGGINGFACE_API_KEY', 'HF_API_KEY'}
    require(not any(value and (name.upper() in model_credentials or name.upper().startswith('RUNPOD_'))
                    for name, value in env.items()), 'unexpected_gpu_credential')
    require(bool(env.get('WANDB_API_KEY')), 'missing_wandb_credential')
    require(env.get('WANDB_BASE_URL', 'https://api.wandb.ai').rstrip('/') == 'https://api.wandb.ai', 'invalid_wandb_endpoint')
    run_id = env.get('GITHUB_RUN_ID', '')
    require(isinstance(run_id, str) and re.fullmatch(r'[0-9]{1,32}', run_id), 'invalid_stage_run_id')
    raw = env.get('HASLA_STAGE_INPUT', '')
    require(isinstance(raw, str) and len(raw) <= 16384, 'invalid_descriptor')
    descriptor = strict_json(raw)
    descriptor_check(descriptor)
    import private_corpus_run as cloud
    cloud.E = env
    query = cloud.wandb_query if query is None else query
    run = None
    with quiet_output():
        entity = existing_private_project(query)
        cipher = fetch_cipher(descriptor, **({'get': get} if get else {}))
        metadata, files = decode_bundle(cipher, descriptor)
        assert_private(query, entity)
        # Import the SDK only after the project passed its privacy gate.
        if sdk is None:
            os.environ['WANDB_SILENT'] = 'true'
            os.environ['WANDB_CONSOLE'] = 'off'
            import wandb as sdk
        run_name = 'hasla-private-stage-' + run_id + '-' + metadata['role']
        try:
            temp_parent = Path(tempfile.gettempdir()).resolve()
            require(not any((parent / '.git').exists() for parent in (temp_parent, *temp_parent.parents))
                    and not any(part.lower().startswith('onedrive') for part in temp_parent.parts), 'private_temp_directory_required')
            with tempfile.TemporaryDirectory(prefix='hasla-private-stage-', dir=temp_parent) as directory:
                settings = sdk.Settings(console='off', disable_code=True, save_code=False, disable_git=True,
                    disable_job_creation=True, x_disable_meta=True, x_disable_stats=True)
                run = sdk.init(entity=entity, project=PROJECT, id=run_name, name=run_name, resume='never',
                    job_type='private-corpus-staging', config={'role': metadata['role'], 'format': metadata['format'], 'private': True}, settings=settings, dir=directory)
                artifact = sdk.Artifact(run_name + '-data', type='dataset', metadata={**metadata, 'private': True})
                for split in ('train', 'validation'):
                    path = Path(directory) / (split + '.' + metadata['format'] + '.jsonl')
                    path.write_bytes(files[split])
                    artifact.add_file(str(path), name=path.name)
                assert_private(query, entity)
                run.log_artifact(artifact)
                artifact.wait(timeout=600)
                reference = artifact.qualified_name
                require(isinstance(reference, str) and re.fullmatch(re.escape(entity + '/' + PROJECT + '/' + run_name + '-data:') + r'v[0-9]+', reference), 'immutable_artifact_unverified')
                event = {'event': 'private_corpus_staged', 'status': 'staged', **metadata,
                         'input_artifact': reference, 'private': True}
        finally:
            if run is not None:
                run.finish()
    return event


@contextlib.contextmanager
def quiet_output():
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        with contextlib.redirect_stdout(Discard()), contextlib.redirect_stderr(Discard()):
            yield
    finally:
        logging.disable(previous)


def main():
    try:
        event = stage()
        code = 0
    except StageError as error:
        event = {'event': 'private_corpus_staged', 'status': 'failed', 'code': str(error)}
        code = 1
    except Exception:
        event = {'event': 'private_corpus_staged', 'status': 'failed', 'code': 'private_staging_failed'}
        code = 1
    print(json.dumps(event, ensure_ascii=True, separators=(',', ':')), flush=True)
    return code


if __name__ == '__main__':
    raise SystemExit(main())

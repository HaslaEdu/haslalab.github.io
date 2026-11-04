"""Bounded, authenticated OCR-source transport into an existing PRIVATE project.

No OCR, PDF rendering, model downloads, GPU APIs, project creation or ZIP files.
Local preparation streams original PDFs into independently encrypted 16MiB
parts. Part zero is an encrypted path-free manifest. The short descriptor is a
single secret; neither it nor any private paths/text are console output.
"""
import base64
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import tempfile
import time
from urllib.parse import urlsplit

import private_stage_corpus as core

StageError, require, strict_json = core.StageError, core.require, core.strict_json
PROJECT = core.PROJECT
PART_BYTES = 16 * 1024**2
MANIFEST_LIMIT = 8 * 1024**2
DESCRIPTOR_LIMIT = 16 * 1024
FILE_LIMIT = 256 * 1024**2
TOTAL_LIMIT = 3 * 1024**3
SOURCE_LIMIT = 10000
TOTAL_PAGE_LIMIT = 1000000
PART_LIMIT = SOURCE_LIMIT + math.ceil(TOTAL_LIMIT / PART_BYTES)
DISK_HEADROOM = 256 * 1024**2
TRANSFER_SECONDS = 1800
TRIAGE = frozenset(('encoding_recovery_ocr_candidate', 'image_present_ocr_candidate',
                   'empty_native_requires_visual_triage', 'sparse_native_requires_visual_triage'))
PRIVATE_ROOTS = (Path('D:/haslalab-private-problem-bank'),
                 Path('C:/Users/andre/CodexWork/HaslaLab/.private-problem-bank-runtime'))
SAFE_CODES = frozenset('''descriptor_size_limit duplicate_json_key duplicate_source empty_private_directory_required
encoded_transport_forbidden immutable_artifact_unverified incomplete_parts insufficient_free_disk invalid_arguments
invalid_bearer invalid_bundle_id invalid_dataset_version invalid_descriptor invalid_drive_id invalid_integer invalid_json
invalid_key invalid_manifest invalid_page_count invalid_page_ranges invalid_part_policy invalid_pdf_magic invalid_schema_keys
invalid_sha256 invalid_source_alias invalid_source_family invalid_source_id invalid_source_inventory invalid_stage_run_id
invalid_transfer_url invalid_triage invalid_wandb_endpoint manifest_descriptor_mismatch manifest_size_limit
missing_wandb_credential never_overwrite_transfer no_source_parts nonce_reuse nonfinite_json overlapping_page_ranges
overlapping_triage part0_mismatch part_count_limit part_count_mismatch part_decryption_failed part_fetch_deadline
part_fetch_failed part_hash_mismatch part_length_mismatch part_offset_mismatch part_order_mismatch part_size_limit
part_size_mismatch part_source_mismatch pdf_hash_mismatch plain_part_hash_mismatch private_directory_required
private_project_unverified regular_file_required reparse_forbidden source_changed source_count_limit source_count_mismatch
source_hash_mismatch source_output_overlap source_outside_private_roots source_size_limit symlink_forbidden total_page_limit
total_size_limit total_size_mismatch transfer_deadline triage_coverage_mismatch unexpected_model_credential unexpected_part
cipher_index_mismatch cipher_index_size_limit cipher_size_mismatch cloudflared_checksum_mismatch descriptor_not_published
ocr_control_locked ocr_stage_consumer_active ocr_stage_consumer_queued published_bundle_changed transfer_is_not_fresh
transfer_not_prepared transfer_not_ready transfer_start_deadline transfer_start_failed tunnel_start_failed
workflow_activity_unverified'''.split())
SAFE_CODES = SAFE_CODES | frozenset(('ocr_registry_invalid','ocr_dispatch_pending','ocr_rotation_pending','ocr_completion_unverified'))
SAFE_CODES = SAFE_CODES | frozenset(('expected_bundle_mismatch','staging_deadline'))


def safe_failure_code(error, fallback):
    code = str(error)
    return code if code in SAFE_CODES else fallback


def digest(value):
    return hashlib.sha256(value).hexdigest()


def file_digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def exact_keys(value, expected):
    require(isinstance(value, dict) and set(value) == set(expected), 'invalid_schema_keys')


def hash_check(value):
    require(isinstance(value, str) and re.fullmatch(r'[a-f0-9]{64}', value), 'invalid_sha256')


def integer(value, lower, upper, code='invalid_integer'):
    require(type(value) is int and lower <= value <= upper, code)
    return value


def alias(index):
    integer(index, 0, SOURCE_LIMIT - 1)
    return 'source_' + str(index).zfill(4) + '.pdf'


def part_name(index):
    integer(index, 0, PART_LIMIT)
    return 'part_' + str(index).zfill(6) + '.bin'


def ranges_check(value, page_count):
    require(isinstance(value, list) and 0 < len(value) <= page_count, 'invalid_page_ranges')
    previous, pages = 0, set()
    for interval in value:
        require(isinstance(interval, list) and len(interval) == 2, 'invalid_page_ranges')
        start = integer(interval[0], 1, page_count, 'invalid_page_ranges')
        end = integer(interval[1], start, page_count, 'invalid_page_ranges')
        require(start > previous, 'overlapping_page_ranges')
        previous = end
        pages.update(range(start, end + 1))
    return pages


def source_check(value, index):
    fields = {'index', 'alias', 'source_id', 'source_family', 'pdf_bytes', 'pdf_sha256',
              'page_count', 'pending_page_ranges', 'triage_page_ranges', 'drive_file_id'}
    exact_keys(value, fields)
    require(value['index'] == index and type(value['index']) is int and value['alias'] == alias(index), 'invalid_source_alias')
    require(isinstance(value['source_id'], str) and re.fullmatch(r'[A-Za-z0-9_:\-]{1,180}', value['source_id']), 'invalid_source_id')
    require(value['source_family'] in ('textbook', 'competition_document'), 'invalid_source_family')
    integer(value['pdf_bytes'], 5, FILE_LIMIT, 'source_size_limit')
    hash_check(value['pdf_sha256'])
    integer(value['page_count'], 1, 100000, 'invalid_page_count')
    pending = ranges_check(value['pending_page_ranges'], value['page_count'])
    triage = value['triage_page_ranges']
    require(isinstance(triage, dict) and bool(triage) and set(triage) <= TRIAGE, 'invalid_triage')
    classified = set()
    for intervals in triage.values():
        pages = ranges_check(intervals, value['page_count'])
        require(not classified & pages, 'overlapping_triage')
        classified.update(pages)
    require(classified == pending, 'triage_coverage_mismatch')
    drive_id = value['drive_file_id']
    require(drive_id is None or isinstance(drive_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', drive_id), 'invalid_drive_id')
    return len(pending)


def descriptor_check(value):
    exact_keys(value, {'version', 'kind', 'bundle_id', 'dataset_version', 'url', 'bearer', 'key_b64',
                       'part0_cipher_sha256', 'part0_cipher_bytes', 'part_count', 'source_count', 'total_pdf_bytes'})
    require(type(value['version']) is int and value['version'] == 1 and value['kind'] == 'ocr-source', 'invalid_descriptor')
    require(isinstance(value['bundle_id'], str) and re.fullmatch(r'[a-f0-9]{32}', value['bundle_id']), 'invalid_bundle_id')
    require(isinstance(value['dataset_version'], str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', value['dataset_version']), 'invalid_dataset_version')
    try:
        parsed = urlsplit(value['url'])
        valid = (parsed.scheme == 'https' and re.fullmatch(r'[a-z0-9-]+\.trycloudflare\.com', parsed.hostname or '')
                 and parsed.path == '/ocr/' + value['bundle_id'] and not parsed.query and not parsed.fragment
                 and parsed.username is None and parsed.password is None and parsed.port is None)
        require(valid, 'invalid_transfer_url')
    except StageError:
        raise
    except Exception:
        raise StageError('invalid_transfer_url') from None
    require(isinstance(value['bearer'], str) and re.fullmatch(r'[A-Za-z0-9_-]{43}', value['bearer']), 'invalid_bearer')
    try:
        key = base64.b64decode(value['key_b64'], validate=True)
    except Exception:
        raise StageError('invalid_key') from None
    require(len(key) == 32, 'invalid_key')
    hash_check(value['part0_cipher_sha256'])
    integer(value['part0_cipher_bytes'], 41, MANIFEST_LIMIT + 40, 'manifest_size_limit')
    integer(value['part_count'], 2, PART_LIMIT + 1, 'part_count_limit')
    integer(value['source_count'], 1, SOURCE_LIMIT, 'source_count_limit')
    integer(value['total_pdf_bytes'], 5, TOTAL_LIMIT, 'total_size_limit')
    require(len(json.dumps(value, separators=(',', ':')).encode()) <= DESCRIPTOR_LIMIT, 'descriptor_size_limit')
    return key


def manifest_check(value, descriptor):
    exact_keys(value, {'version', 'kind', 'bundle_id', 'dataset_version', 'part_plain_bytes',
                       'total_pdf_bytes', 'source_inventory_sha256', 'page_jobs_sha256', 'sources', 'parts'})
    require(type(value['version']) is int and value['version'] == 1 and value['kind'] == 'ocr-source', 'invalid_manifest')
    for name in ('bundle_id', 'dataset_version', 'total_pdf_bytes'):
        require(value[name] == descriptor[name], 'manifest_descriptor_mismatch')
    require(type(value['part_plain_bytes']) is int and value['part_plain_bytes'] == PART_BYTES, 'invalid_part_policy')
    for name in ('source_inventory_sha256', 'page_jobs_sha256'):
        hash_check(value[name])
    sources, parts = value['sources'], value['parts']
    require(isinstance(sources, list) and len(sources) == descriptor['source_count'], 'source_count_mismatch')
    require(isinstance(parts, list) and len(parts) + 1 == descriptor['part_count'], 'part_count_mismatch')
    ids, hashes, pending, total = set(), set(), 0, 0
    integer(sum(integer(s.get('page_count'), 1, 100000, 'invalid_page_count') for s in sources),
            1, TOTAL_PAGE_LIMIT, 'total_page_limit')
    for index, source in enumerate(sources):
        pending += source_check(source, index)
        require(source['source_id'] not in ids and source['pdf_sha256'] not in hashes, 'duplicate_source')
        ids.add(source['source_id']); hashes.add(source['pdf_sha256'])
        total += source['pdf_bytes']
        require(total <= TOTAL_LIMIT, 'total_size_limit')
    require(total == descriptor['total_pdf_bytes'], 'total_size_mismatch')
    current, offset = 0, 0
    for index, part in enumerate(parts, 1):
        exact_keys(part, {'index', 'source_index', 'offset', 'plain_bytes', 'plain_sha256', 'cipher_bytes', 'cipher_sha256'})
        integer(part['index'], index, index, 'part_order_mismatch')
        if offset == sources[current]['pdf_bytes']:
            current += 1; offset = 0
        require(current < len(sources), 'unexpected_part')
        integer(part['source_index'], current, current, 'part_source_mismatch')
        integer(part['offset'], offset, offset, 'part_offset_mismatch')
        expected = min(PART_BYTES, sources[current]['pdf_bytes'] - offset)
        integer(part['plain_bytes'], expected, expected, 'part_size_mismatch')
        integer(part['cipher_bytes'], expected + 40, expected + 40, 'cipher_size_mismatch')
        hash_check(part['plain_sha256']); hash_check(part['cipher_sha256'])
        offset += expected
    require(current == len(sources) - 1 and offset == sources[-1]['pdf_bytes'], 'incomplete_parts')
    return {'source_count': len(sources), 'pending_pages': pending, 'total_pdf_bytes': total}


def private_directory(path):
    path = Path(path)
    for current in (path, *path.parents):
        require(not current.is_symlink(), 'symlink_forbidden')
        if current.exists():
            attributes = getattr(current.lstat(), 'st_file_attributes', 0)
            require(not attributes & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400), 'reparse_forbidden')
    resolved = path.resolve()
    require(not any(part.lower().startswith('onedrive') for part in resolved.parts)
            and not any((parent / '.git').exists() for parent in (resolved, *resolved.parents)), 'private_directory_required')
    return resolved


def regular_file(path):
    path = Path(path)
    private_directory(path.parent)
    require(not path.is_symlink(), 'symlink_forbidden')
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400), 'regular_file_required')
    return path.resolve(), info


def write_private(path, value, *, created=None):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        if created is not None:
            created.append(Path(path))
        stream.write(json.dumps(value, ensure_ascii=True, separators=(',', ':')) + '\n')
    with contextlib.suppress(OSError):
        Path(path).chmod(0o600)


def preparation_plan(inventory, output, *, allowed_roots=PRIVATE_ROOTS, disk_usage=shutil.disk_usage):
    inventory_path, _ = regular_file(inventory)
    require(inventory_path.stat().st_size <= MANIFEST_LIMIT, 'manifest_size_limit')
    document = strict_json(inventory_path.read_bytes())
    require(document.get('schema') == 'haslalab-pending-ocr-triage-v1' and document.get('metadata_only') is True
            and document.get('pdfs_opened') == 0 and isinstance(document.get('sources'), list), 'invalid_source_inventory')
    integer(len(document['sources']), 1, SOURCE_LIMIT, 'source_count_limit')
    hash_check(document.get('jobs', {}).get('sha256'))
    output = private_directory(output)
    require(not output.exists(), 'never_overwrite_transfer')
    roots = [Path(root).resolve() for root in allowed_roots]
    sources, local_paths, total, part_count, ids, hashes = [], [], 0, 0, set(), set()
    for index, original in enumerate(document['sources']):
        path, info = regular_file(original['local_pdf_path'])
        require(any(path.is_relative_to(root) for root in roots), 'source_outside_private_roots')
        require(not path.is_relative_to(output) and not output.is_relative_to(path), 'source_output_overlap')
        source = {'index': index, 'alias': alias(index), 'source_id': original['source_id'],
            'source_family': original['source_family'], 'pdf_bytes': info.st_size, 'pdf_sha256': original['local_pdf_sha256'],
            'page_count': original['source_page_count'], 'pending_page_ranges': original['pending_page_ranges'],
            'triage_page_ranges': original['triage_page_ranges'], 'drive_file_id': original.get('drive_file_id')}
        source_check(source, index)
        require(source['source_id'] not in ids and source['pdf_sha256'] not in hashes, 'duplicate_source')
        ids.add(source['source_id']); hashes.add(source['pdf_sha256'])
        sources.append(source); local_paths.append(path)
        total += info.st_size; part_count += math.ceil(info.st_size / PART_BYTES)
        require(total <= TOTAL_LIMIT, 'total_size_limit')
    require(sum(source['page_count'] for source in sources) <= TOTAL_PAGE_LIMIT, 'total_page_limit')
    projected = total + part_count * (40 + 4096) + MANIFEST_LIMIT + 40 + 65536
    ancestor = output.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
    require(disk_usage(ancestor).free >= projected + DISK_HEADROOM, 'insufficient_free_disk')
    return {'sources': sources, 'local_paths': local_paths, 'total_pdf_bytes': total,
            'projected_cipher_bytes_upper_bound': projected, 'data_part_count': part_count,
            'source_inventory_sha256': file_digest(inventory_path), 'page_jobs_sha256': document['jobs']['sha256']}


def prepare_bundle(inventory, output, *, allowed_roots=PRIVATE_ROOTS, disk_usage=shutil.disk_usage):
    """Explicit local action. One source part in memory; no original file copy."""
    from nacl.secret import SecretBox
    plan = preparation_plan(inventory, output, allowed_roots=allowed_roots, disk_usage=disk_usage)
    output = private_directory(output)
    output.mkdir(parents=True, exist_ok=False)
    with contextlib.suppress(OSError):
        output.chmod(0o700)
    created, parts, index, nonces = [], [], 1, set()
    key, bearer, bundle = secrets.token_bytes(32), secrets.token_urlsafe(32), secrets.token_hex(16)
    box = SecretBox(key)
    def encrypt(plain, number):
        nonce = secrets.token_bytes(24)
        require(nonce not in nonces, 'nonce_reuse')
        nonces.add(nonce)
        cipher = bytes(box.encrypt(plain, nonce))
        path = output / part_name(number)
        with path.open('xb') as stream:
            created.append(path)
            require(stream.write(cipher) == len(cipher), 'cipher_size_mismatch')
        require(path.stat().st_size == len(cipher) and file_digest(path) == digest(cipher), 'part_hash_mismatch')
        with contextlib.suppress(OSError):
            path.chmod(0o600)
        return {'cipher_bytes': len(cipher), 'cipher_sha256': digest(cipher)}
    try:
        for source, path in zip(plan['sources'], plan['local_paths']):
            path, before = regular_file(path)
            source_hash, offset = hashlib.sha256(), 0
            with path.open('rb') as stream:
                opened = os.fstat(stream.fileno())
                require((opened.st_size, opened.st_ino, opened.st_dev) == (before.st_size, before.st_ino, before.st_dev), 'source_changed')
                while offset < source['pdf_bytes']:
                    plain = stream.read(min(PART_BYTES, source['pdf_bytes'] - offset))
                    require(len(plain) == min(PART_BYTES, source['pdf_bytes'] - offset), 'source_changed')
                    if offset == 0:
                        require(plain.startswith(b'%PDF-'), 'invalid_pdf_magic')
                    source_hash.update(plain)
                    spec = {'index': index, 'source_index': source['index'], 'offset': offset,
                            'plain_bytes': len(plain), 'plain_sha256': digest(plain), **encrypt(plain, index)}
                    parts.append(spec); index += 1; offset += len(plain)
                require(stream.read(1) == b'', 'source_changed')
                after = os.fstat(stream.fileno())
            require((after.st_size, after.st_mtime_ns, after.st_ino, after.st_dev) ==
                    (before.st_size, before.st_mtime_ns, before.st_ino, before.st_dev), 'source_changed')
            require(source_hash.hexdigest() == source['pdf_sha256'], 'source_hash_mismatch')
        manifest = {'version': 1, 'kind': 'ocr-source', 'bundle_id': bundle, 'dataset_version': Path(inventory).parent.name,
            'part_plain_bytes': PART_BYTES, 'total_pdf_bytes': plan['total_pdf_bytes'],
            'source_inventory_sha256': plan['source_inventory_sha256'], 'page_jobs_sha256': plan['page_jobs_sha256'],
            'sources': plan['sources'], 'parts': parts}
        raw_manifest = json.dumps(manifest, ensure_ascii=True, separators=(',', ':')).encode()
        require(len(raw_manifest) <= MANIFEST_LIMIT, 'manifest_size_limit')
        part0 = encrypt(raw_manifest, 0)
        descriptor = {'version': 1, 'kind': 'ocr-source', 'bundle_id': bundle, 'dataset_version': manifest['dataset_version'],
            'url': 'https://unused.trycloudflare.com/ocr/' + bundle, 'bearer': bearer, 'key_b64': base64.b64encode(key).decode(),
            'part0_cipher_sha256': part0['cipher_sha256'], 'part0_cipher_bytes': part0['cipher_bytes'],
            'part_count': len(parts) + 1, 'source_count': len(plan['sources']), 'total_pdf_bytes': plan['total_pdf_bytes']}
        descriptor_check(descriptor); manifest_check(manifest, descriptor)
        index_document = {'bundle_id': bundle, 'parts': [{'index': 0, **part0}] + [
            {k: p[k] for k in ('index', 'cipher_bytes', 'cipher_sha256')} for p in parts]}
        for name, value in (('cipher-index.private.json', index_document), ('transfer.private.json', descriptor)):
            path = output / name
            write_private(path, value, created=created)
        ready = output / 'prepared.json'
        write_private(ready, {'prepared': True, 'source_count': len(plan['sources']), 'part_count': len(parts) + 1}, created=created)
        return {'event': 'ocr_source_transfer_prepared', 'source_count': len(plan['sources']),
                'part_count': len(parts) + 1, 'total_pdf_bytes': plan['total_pdf_bytes'], 'originals_modified': 0}
    except Exception:
        # No recursive deletion; only files created by this invocation are removed.
        for path in reversed(created):
            with contextlib.suppress(OSError):
                if path.parent == output and not path.is_symlink():
                    path.unlink()
        with contextlib.suppress(OSError):
            output.rmdir()
        raise


def fetch_part(descriptor, number, size, expected_hash, *, get=None, clock=time.monotonic, deadline=None):
    descriptor_check(descriptor)
    integer(number, 0, descriptor['part_count'] - 1)
    integer(size, 41, max(PART_BYTES, MANIFEST_LIMIT) + 40, 'part_size_limit')
    hash_check(expected_hash)
    get = core.requests.get if get is None else get
    response = None
    try:
        started = clock()
        response = get(descriptor['url'] + '/' + part_name(number), headers={'Authorization': 'Bearer ' + descriptor['bearer']},
                       stream=True, allow_redirects=False, timeout=(5, 30))
        require(response.status_code == 200, 'part_fetch_failed')
        require(response.headers.get('Content-Length') == str(size), 'part_length_mismatch')
        require(response.headers.get('Content-Encoding', 'identity') in ('identity', ''), 'encoded_transport_forbidden')
        value = bytearray()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            now = clock()
            require(now - started <= 600, 'part_fetch_deadline')
            require(deadline is None or now <= deadline, 'transfer_deadline')
            require(len(value) + len(chunk) <= size, 'part_size_limit')
            value.extend(chunk)
        require(len(value) == size and digest(value) == expected_hash, 'part_hash_mismatch')
        return bytes(value)
    except StageError:
        raise
    except Exception:
        raise StageError('part_fetch_failed') from None
    finally:
        if response is not None:
            response.close()


def reconstruct_sources(descriptor, directory, *, get=None, clock=time.monotonic, overall_deadline=None):
    from nacl.secret import SecretBox
    key = descriptor_check(descriptor)
    directory = private_directory(directory)
    require(directory.is_dir() and not any(directory.iterdir()), 'empty_private_directory_required')
    box, nonces = SecretBox(key), set()
    def decrypt(cipher):
        nonce = cipher[:24]
        require(nonce not in nonces, 'nonce_reuse')
        nonces.add(nonce)
        try:
            return box.decrypt(cipher)
        except Exception:
            raise StageError('part_decryption_failed') from None
    started = clock()
    deadline = started + TRANSFER_SECONDS
    if overall_deadline is not None:
        deadline = min(deadline, overall_deadline)
    cipher = fetch_part(descriptor, 0, descriptor['part0_cipher_bytes'], descriptor['part0_cipher_sha256'], get=get, clock=clock, deadline=deadline)
    manifest = strict_json(decrypt(cipher))
    totals = manifest_check(manifest, descriptor)
    require(shutil.disk_usage(directory).free >= descriptor['total_pdf_bytes'] + DISK_HEADROOM, 'insufficient_free_disk')
    handle, source_hash, offset, current, total = None, None, 0, -1, 0
    try:
        for part in manifest['parts']:
            require(clock() <= deadline, 'transfer_deadline')
            source = manifest['sources'][part['source_index']]
            if part['source_index'] != current:
                if handle is not None:
                    handle.close(); handle = None
                    previous = manifest['sources'][current]
                    completed_path, info = regular_file(directory / alias(current))
                    require(offset == previous['pdf_bytes'] and info.st_size == previous['pdf_bytes']
                            and source_hash.hexdigest() == previous['pdf_sha256']
                            and file_digest(completed_path) == previous['pdf_sha256'], 'pdf_hash_mismatch')
                current, offset, source_hash = part['source_index'], 0, hashlib.sha256()
                handle = (directory / alias(current)).open('xb')
            require(part['offset'] == offset, 'part_offset_mismatch')
            cipher = fetch_part(descriptor, part['index'], part['cipher_bytes'], part['cipher_sha256'], get=get, clock=clock, deadline=deadline)
            plain = decrypt(cipher)
            require(len(plain) == part['plain_bytes'] and digest(plain) == part['plain_sha256'], 'plain_part_hash_mismatch')
            if offset == 0:
                require(plain.startswith(b'%PDF-'), 'invalid_pdf_magic')
            require(offset + len(plain) <= source['pdf_bytes'] and total + len(plain) <= TOTAL_LIMIT, 'total_size_limit')
            require(handle.write(plain) == len(plain), 'plain_part_hash_mismatch')
            source_hash.update(plain)
            offset += len(plain); total += len(plain)
        require(handle is not None, 'no_source_parts')
        handle.close(); handle = None
        completed_path, info = regular_file(directory / alias(current))
        require(offset == source['pdf_bytes'] and info.st_size == source['pdf_bytes']
                and source_hash.hexdigest() == source['pdf_sha256']
                and file_digest(completed_path) == source['pdf_sha256'], 'pdf_hash_mismatch')
        require(total == descriptor['total_pdf_bytes'], 'total_size_mismatch')
        write_private(directory / 'manifest.json', manifest)
        return manifest, totals
    finally:
        if handle is not None:
            handle.close()


@contextlib.contextmanager
def quiet_output():
    # Suppress Python logging plus native/SDK writes to inherited fd 1/2.
    saved = []
    with core.quiet_output(), open(os.devnull, 'w') as sink:
        try:
            for number in (1, 2):
                saved.append((number, os.dup(number)))
                os.dup2(sink.fileno(), number)
            yield
        finally:
            for number, previous in reversed(saved):
                os.dup2(previous, number); os.close(previous)


def stage(env=None, *, query=None, get=None, sdk=None):
    stage_deadline = time.monotonic() + 2400
    env = os.environ if env is None else env
    forbidden = {'HF_TOKEN', 'HF_API_TOKEN', 'HUGGING_FACE_HUB_TOKEN', 'HUGGINGFACE_TOKEN',
                 'HUGGINGFACEHUB_API_TOKEN', 'HUGGINGFACE_API_KEY', 'HF_API_KEY', 'OPENAI_API_KEY'}
    require(not any(value and (name.upper() in forbidden or name.upper().startswith('RUNPOD_')) for name,value in env.items()), 'unexpected_model_credential')
    require(bool(env.get('WANDB_API_KEY')), 'missing_wandb_credential')
    require(env.get('WANDB_BASE_URL', 'https://api.wandb.ai').rstrip('/') == 'https://api.wandb.ai', 'invalid_wandb_endpoint')
    run_id = env.get('GITHUB_RUN_ID', '')
    require(isinstance(run_id, str) and re.fullmatch(r'[0-9]{1,32}', run_id), 'invalid_stage_run_id')
    raw = env.get('HASLA_OCR_STAGE_INPUT', '')
    require(isinstance(raw, str) and len(raw.encode()) <= DESCRIPTOR_LIMIT, 'descriptor_size_limit')
    descriptor = strict_json(raw); descriptor_check(descriptor)
    require(env.get('HASLA_OCR_STAGE_BUNDLE_ID') == descriptor['bundle_id'], 'expected_bundle_mismatch')
    import private_corpus_run as cloud
    cloud.E = env
    query = cloud.wandb_query if query is None else query
    run = None
    with quiet_output():
        entity = core.existing_private_project(query)
        parent = private_directory(Path(tempfile.gettempdir()))
        with tempfile.TemporaryDirectory(prefix='hasla-private-ocr-stage-', dir=parent) as temporary:
            data = Path(temporary) / 'data'; data.mkdir()
            manifest, totals = reconstruct_sources(descriptor, data, get=get, overall_deadline=stage_deadline)
            core.assert_private(query, entity)
            if sdk is None:
                os.environ['WANDB_SILENT'] = 'true'; os.environ['WANDB_CONSOLE'] = 'off'
                import wandb as sdk
            name = 'hasla-private-ocr-stage-' + run_id
            try:
                settings = sdk.Settings(console='off', disable_code=True, save_code=False, disable_git=True,
                    disable_job_creation=True, x_disable_meta=True, x_disable_stats=True, init_timeout=120)
                require(time.monotonic() < stage_deadline, 'staging_deadline')
                core.assert_private(query, entity)
                run = sdk.init(entity=entity, project=PROJECT, id=name, name=name, resume='never',
                    job_type='private-ocr-source-staging', config={'kind':'ocr-source', 'private':True}, settings=settings, dir=temporary)
                metadata = {'kind':'ocr-source', 'dataset_version':descriptor['dataset_version'], 'private':True, **totals}
                artifact = sdk.Artifact(name + '-sources', type='ocr-source', metadata=metadata)
                for source in manifest['sources']:
                    artifact.add_file(str(data / source['alias']), name=source['alias'])
                artifact.add_file(str(data / 'manifest.json'), name='manifest.json')
                core.assert_private(query, entity)
                remaining = stage_deadline - time.monotonic()
                require(remaining > 0, 'staging_deadline')
                run.log_artifact(artifact); artifact.wait(timeout=min(600, remaining))
                require(time.monotonic() <= stage_deadline, 'staging_deadline')
                reference = artifact.qualified_name
                require(isinstance(reference, str) and re.fullmatch(re.escape(entity + '/' + PROJECT + '/' + name + '-sources:') + r'v[0-9]+', reference), 'immutable_artifact_unverified')
                event = {'event':'private_ocr_sources_staged', 'status':'staged', 'input_artifact':reference, **metadata}
            finally:
                if run is not None:
                    run.finish()
    return event


def main():
    try:
        event, code = stage(), 0
    except StageError as error:
        event, code = {'event':'private_ocr_sources_staged', 'status':'failed',
                       'code':safe_failure_code(error, 'private_ocr_staging_failed')}, 1
    except Exception:
        event, code = {'event':'private_ocr_sources_staged', 'status':'failed', 'code':'private_ocr_staging_failed'}, 1
    print(json.dumps(event, ensure_ascii=True, separators=(',', ':')), flush=True)
    return code


if __name__ == '__main__':
    raise SystemExit(main())

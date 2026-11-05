"""Read public pinned-image package requirements only; no installs or GPU use."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

IMAGE = 'unsloth/unsloth@sha256:9e12ff9201f4753ae7290ba45b0ca681a010575d925a53dffd13b8a7829e295b'
PYTHON = '/opt/unsloth-venv/bin/python'
NAME = r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}'
VERSION = r'[A-Za-z0-9][A-Za-z0-9!+_.-]{0,100}'
REQUIREMENT = r'[A-Za-z0-9][A-Za-z0-9_.\[\],<>=!~ +;:\x27\x22-]{0,500}'
MISMATCH = re.compile(rf'^({NAME}) ({VERSION}) has requirement ({REQUIREMENT}), but you have ({NAME}) ({VERSION})\.$')
MISSING = re.compile(rf'^({NAME}) ({VERSION}) requires ({REQUIREMENT}), which is not installed\.$')
UNSUPPORTED = re.compile(rf'^({NAME}) ({VERSION}) is not supported on this platform$')


def parse_lines(raw):
    rows, unknown, hashes = [], 0, []
    for line in raw[:65536].decode('utf8', errors='replace').splitlines():
        line = line.strip()
        if not line or line == 'No broken requirements found.':
            continue
        found = MISMATCH.fullmatch(line)
        if found:
            a, b, c, d, e = found.groups()
            row = {'kind': 'version_mismatch', 'package': a, 'version': b, 'requirement': c,
                   'installed_package': d, 'installed_version': e}
        else:
            found = MISSING.fullmatch(line)
            if found:
                a, b, c = found.groups()
                row = {'kind': 'missing_requirement', 'package': a, 'version': b, 'requirement': c}
            else:
                found = UNSUPPORTED.fullmatch(line)
                row = {'kind': 'unsupported_platform', 'package': found[1], 'version': found[2]} if found else None
        if row is not None and len(rows) < 256:
            rows.append(row)
        else:
            unknown += 1
            if len(hashes) < 16:
                hashes.append(hashlib.sha256(line.encode()).hexdigest())
    return {'requirements': rows, 'unparsed_lines': unknown, 'unparsed_line_sha256': hashes,
            'captured_bytes': min(len(raw), 65536), 'output_truncated': len(raw) > 65536}


def validate(value):
    fixed = {'version': 1, 'kind': 'public_image_pipcheck_details', 'image': IMAGE,
             'package_installations': 0, 'model_calls': 0, 'gpu_provider_calls': 0, 'credentials_passed': False}
    if type(value) is not dict or set(value) != set(fixed) | {'pip_check_exit_code', 'wandb_metadata_version', 'details'} or any(type(value[k]) is not type(v) or value[k] != v for k, v in fixed.items()):
        raise ValueError('result_schema_invalid')
    if type(value['pip_check_exit_code']) is not int or not 0 <= value['pip_check_exit_code'] <= 255:
        raise ValueError('exit_code_invalid')
    if value['wandb_metadata_version'] is not None and (type(value['wandb_metadata_version']) is not str or not re.fullmatch(VERSION, value['wandb_metadata_version'])):
        raise ValueError('metadata_version_invalid')
    details = value['details']
    if type(details) is not dict or set(details) != {'requirements', 'unparsed_lines', 'unparsed_line_sha256', 'captured_bytes', 'output_truncated'}:
        raise ValueError('details_schema_invalid')
    if type(details['requirements']) is not list or len(details['requirements']) > 256:
        raise ValueError('requirements_invalid')
    for row in details['requirements']:
        if type(row) is not dict:
            raise ValueError('requirement_invalid')
        kind = row.get('kind')
        keys = {'kind', 'package', 'version'} | ({'requirement', 'installed_package', 'installed_version'} if kind == 'version_mismatch' else {'requirement'} if kind == 'missing_requirement' else set())
        if kind not in ('version_mismatch', 'missing_requirement', 'unsupported_platform') or set(row) != keys:
            raise ValueError('requirement_invalid')
        for key, val in row.items():
            pattern = REQUIREMENT if key == 'requirement' else VERSION if 'version' in key else NAME
            if type(val) is not str or not re.fullmatch(pattern, val):
                raise ValueError('requirement_invalid')
    if type(details['unparsed_lines']) is not int or not 0 <= details['unparsed_lines'] <= 65536 or type(details['captured_bytes']) is not int or not 0 <= details['captured_bytes'] <= 65536 or type(details['output_truncated']) is not bool:
        raise ValueError('bounds_invalid')
    if type(details['unparsed_line_sha256']) is not list or len(details['unparsed_line_sha256']) > 16 or any(type(v) is not str or not re.fullmatch('[0-9a-f]{64}', v) for v in details['unparsed_line_sha256']):
        raise ValueError('hashes_invalid')
    return value


def inside():
    if sys.executable != PYTHON:
        raise ValueError('fixed_python_required')
    root = Path('/probe-output')
    with (root/'pip-check.log').open('wb') as log:
        process = subprocess.run([PYTHON, '-m', 'pip', 'check'], stdout=log, stderr=subprocess.STDOUT, timeout=120, check=False)
    with (root/'pip-check.log').open('rb') as log:
        details = parse_lines(log.read(65537))
    try:
        wandb = importlib.metadata.version('wandb')
    except importlib.metadata.PackageNotFoundError:
        wandb = None
    value = {'version': 1, 'kind': 'public_image_pipcheck_details', 'image': IMAGE,
             'package_installations': 0, 'model_calls': 0, 'gpu_provider_calls': 0, 'credentials_passed': False,
             'pip_check_exit_code': process.returncode, 'wandb_metadata_version': wandb, 'details': details}
    (root/'result.json').write_text(json.dumps(validate(value), sort_keys=True), encoding='utf8')


def host(env, run=subprocess.run, disk=shutil.disk_usage):
    nonce = env.get('HASLA_DEPENDENCY_PROBE_LAUNCH_ID', '')
    if env.get('GITHUB_ACTIONS') != 'true' or env.get('RUNNER_OS') != 'Linux' or not re.fullmatch('[0-9a-f]{32}', nonce):
        raise ValueError('fixed_ephemeral_runner_required')
    event = {'event': 'private_qwq_dependency_details', 'launch_id': nonce, 'image': IMAGE,
             'model_calls': 0, 'gpu_provider_calls': 0, 'credentials_passed': False}
    if disk('/').free < 45*1024**3:
        return {**event, 'status': 'blocked', 'failure_code': 'disk_below_45gib'}
    name = 'hasla-qwq-pipcheck-details-' + nonce
    with tempfile.TemporaryDirectory(prefix='qwq-pipcheck-') as directory:
        root = Path(directory)
        with (root/'docker.log').open('wb') as log:
            attempted = False
            try:
                if run(['docker', 'pull', '--platform', 'linux/amd64', IMAGE], stdout=log, stderr=subprocess.STDOUT, timeout=900, check=False).returncode:
                    return {**event, 'status': 'failed', 'failure_code': 'image_pull_failed'}
                command = ['docker', 'run', '--rm', '--name', name, '--platform', 'linux/amd64', '--entrypoint', PYTHON,
                    '--mount', 'type=bind,src='+str(Path(__file__).resolve())+',dst=/probe.py,readonly',
                    '--mount', 'type=bind,src='+str(root)+',dst=/probe-output',
                    '--env', 'PIP_NO_INDEX=1', '--env', 'HF_HUB_OFFLINE=1', '--env', 'WANDB_MODE=disabled', IMAGE, '/probe.py', '--inside']
                attempted = True
                completed = run(command, stdout=log, stderr=subprocess.STDOUT, timeout=180, check=False)
                path = root/'result.json'
                if completed.returncode or not path.is_file() or path.is_symlink() or path.stat().st_size > 256*1024:
                    return {**event, 'status': 'failed', 'failure_code': 'container_probe_failed'}
                raw = path.read_bytes()
                return {**event, 'status': 'observed', 'result_sha256': hashlib.sha256(raw).hexdigest(), 'result': validate(json.loads(raw))}
            finally:
                if attempted:
                    try:
                        run(['docker', 'rm', '-f', name], stdout=log, stderr=subprocess.STDOUT, timeout=30, check=False)
                    except Exception:
                        pass


if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['--inside']:
            inside()
        elif not sys.argv[1:]:
            result = host(os.environ)
            print(json.dumps(result, sort_keys=True, allow_nan=False))
            raise SystemExit(0 if result['status'] == 'observed' else 1)
        else:
            raise ValueError('arguments_invalid')
    except Exception:
        print('{"event":"private_qwq_dependency_details","status":"failed","failure_code":"fixed_probe_failed"}')
        raise SystemExit(1)

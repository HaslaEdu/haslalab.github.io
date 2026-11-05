"""CPU-only diagnostic of a fixed image's metadata and pinned W&B installation.

No model, GPU provider, credentials, Unsloth import, or inference is used. Raw
process output stays in the ephemeral runner; only this fixed schema is emitted.
"""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib
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
CORE = ('torch', 'transformers', 'unsloth', 'unsloth_zoo', 'peft', 'bitsandbytes', 'trl')
AUX = ('vllm', 'triton', 'xformers', 'numpy', 'numba', 'protobuf', 'pydantic',
       'opentelemetry-api', 'opentelemetry-sdk')
ERRORS = {'ModuleNotFoundError', 'ImportError', 'RuntimeError', 'ValueError', 'AttributeError',
          'AssertionError', 'OSError', 'TypeError', 'TimeoutExpired', 'PackageNotFoundError'}
VERSION = re.compile(r'[A-Za-z0-9.+_-]{1,100}')
FIXED_ENV = {'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'WANDB_MODE': 'disabled',
             'WANDB_CONSOLE': 'off', 'UNSLOTH_SKIP_NOTEBOOK_SYNC': '1',
             'PIP_DISABLE_PIP_VERSION_CHECK': '1'}


def safe_version(value):
    return value if type(value) is str and VERSION.fullmatch(value) else None


def error_class(error):
    name = type(error).__name__
    return name if name in ERRORS else 'OtherError'


def metadata_versions(names=CORE, lookup=importlib.metadata.version):
    result = {}
    for name in names:
        try:
            result[name] = safe_version(lookup(name))
        except Exception:
            result[name] = None
    return result


def environment_snapshot(env=None, which=shutil.which):
    env = os.environ if env is None else env
    paths = env.get('PATH', '').split(os.pathsep)
    libs = env.get('LD_LIBRARY_PATH', '').split(os.pathsep)
    tools = {}
    prefixes = (('/opt/unsloth-venv/', 'venv'), ('/usr/local/cuda', 'cuda'),
                ('/opt/unsloth/', 'unsloth_shim'), ('/usr/local/bin/', 'usr_local'), ('/usr/bin/', 'system'))
    for name in ('python', 'pip', 'nvcc', 'ptxas'):
        value = which(name)
        tools[name] = None if value is None else next((label for prefix, label in prefixes if value.startswith(prefix)), 'other')
    return {'venv_bin_present': '/opt/unsloth-venv/bin' in paths,
            'cuda_bin_present': any(p.startswith('/usr/local/cuda') and p.endswith('/bin') for p in paths),
            'cuda_library_present': any(p.startswith('/usr/local/cuda') for p in libs), 'tool_roots': tools}


def login_environment(root, run):
    result = {'image_env': environment_snapshot()}
    for depth, label in ((1, 'login_shell'), (2, 'double_login_shell')):
        command = [PYTHON, '/probe.py', '--environment']
        import shlex
        for _ in range(depth):
            command = ['/bin/bash', '-lc', shlex.join(command)]
        path = root / (label + '.log')
        try:
            with path.open('wb') as log:
                completed = run(command, stdout=log, stderr=subprocess.STDOUT, timeout=20, check=False)
            result[label] = json.loads(path.read_bytes()) if completed.returncode == 0 and path.stat().st_size <= 4096 else None
        except Exception:
            result[label] = None
    return result


def pip_check(root, label, run):
    try:
        with (root / (label + '.log')).open('wb') as log:
            checked = run([PYTHON, '-m', 'pip', 'check'], stdout=log, stderr=subprocess.STDOUT, timeout=60, check=False)
        return checked.returncode if type(checked.returncode) is int and 0 <= checked.returncode <= 255 else 255
    except Exception:
        return 255


def import_probe(name, importer=importlib.import_module):
    # Explicitly exclude Unsloth and CUDA availability assertions on this CPU job.
    if name not in ('torch', 'wandb'):
        raise ValueError('import_not_permitted')
    try:
        module = importer(name)
        result = {'status': 'imported', 'version': safe_version(getattr(module, '__version__', None)),
                  'exception_type': None}
        if name == 'torch':
            result['compiled_cuda'] = safe_version(getattr(getattr(module, 'version', None), 'cuda', None))
        return result
    except Exception as error:
        result = {'status': 'failed', 'version': None, 'exception_type': error_class(error)}
        if name == 'torch':
            result['compiled_cuda'] = None
        return result


def inside(output, *, run=subprocess.run, versions=metadata_versions, importer=importlib.import_module):
    root = Path(output)
    if str(root) != '/probe-output' or sys.executable != PYTHON:
        raise ValueError('fixed_container_context_required')
    os.environ.update(FIXED_ENV)
    before = versions()
    aux_before = versions(AUX)
    environment = login_environment(root, run)
    check_before = pip_check(root, 'pip-check-before', run)
    with (root / 'pip.log').open('wb') as log:
        try:
            pip = run([PYTHON, '-m', 'pip', 'install', '-q', 'wandb==0.31.0'],
                      stdout=log, stderr=subprocess.STDOUT, timeout=600, check=False)
            exit_code = pip.returncode if type(pip.returncode) is int and 0 <= pip.returncode <= 255 else 255
            pip_error = None
        except Exception as error:
            exit_code, pip_error = 255, error_class(error)
    after = versions()
    aux_after = versions(AUX)
    check_after = pip_check(root, 'pip-check-after', run)
    changed = [name for name in CORE if before[name] != after[name]]
    # Import logs may contain library warnings; never send them to Actions stdout.
    with (root / 'imports.log').open('w', encoding='utf8') as log, redirect_stdout(log), redirect_stderr(log):
        imports = {name: import_probe(name, importer) for name in ('wandb', 'torch')}
    value = {'version': 1, 'kind': 'fixed_cpu_dependency_probe', 'image': IMAGE,
             'core_before': before, 'core_after': after, 'changed_core_packages': changed,
             'all_core_metadata_present': all(before.values()) and all(after.values()),
             'core_versions_unchanged': not changed, 'pip_exit_code': exit_code,
             'pip_exception_type': pip_error, 'imports': imports, 'unsloth_import_attempted': False,
             'gpu_assertion_attempted': False, 'model_calls': 0, 'credentials_passed': False,
             'aux_before': aux_before, 'aux_after': aux_after,
             'changed_aux_packages': [n for n in AUX if aux_before[n] != aux_after[n]],
             'pip_check_before_exit': check_before, 'pip_check_after_exit': check_after,
             'environment': environment}
    (root / 'result.json').write_text(json.dumps(value, sort_keys=True, allow_nan=False), encoding='utf8')


def validate(value):
    fixed = {'version': 1, 'kind': 'fixed_cpu_dependency_probe', 'image': IMAGE,
             'unsloth_import_attempted': False, 'gpu_assertion_attempted': False,
             'model_calls': 0, 'credentials_passed': False}
    keys = set(fixed) | {'core_before', 'core_after', 'changed_core_packages', 'all_core_metadata_present',
                         'core_versions_unchanged', 'pip_exit_code', 'pip_exception_type', 'imports',
                         'aux_before', 'aux_after', 'changed_aux_packages', 'pip_check_before_exit',
                         'pip_check_after_exit', 'environment'}
    if type(value) is not dict or set(value) != keys or any(type(value[k]) is not type(v) or value[k] != v for k, v in fixed.items()):
        raise ValueError('probe_result_invalid')
    for key in ('core_before', 'core_after', 'aux_before', 'aux_after'):
        row = value[key]
        if type(row) is not dict or set(row) != set(AUX if key.startswith('aux') else CORE) or any(v is not None and safe_version(v) != v for v in row.values()):
            raise ValueError('metadata_result_invalid')
    if value['changed_aux_packages'] != [n for n in AUX if value['aux_before'][n] != value['aux_after'][n]]:
        raise ValueError('metadata_diff_invalid')
    for key in ('pip_check_before_exit', 'pip_check_after_exit'):
        if type(value[key]) is not int or not 0 <= value[key] <= 255:
            raise ValueError('pip_check_result_invalid')
    environment = value['environment']
    if type(environment) is not dict or set(environment) != {'image_env', 'login_shell', 'double_login_shell'}:
        raise ValueError('environment_result_invalid')
    for label, row in environment.items():
        if row is None and label != 'image_env':
            continue
        if type(row) is not dict or set(row) != {'venv_bin_present', 'cuda_bin_present', 'cuda_library_present', 'tool_roots'} or any(type(row[k]) is not bool for k in ('venv_bin_present', 'cuda_bin_present', 'cuda_library_present')):
            raise ValueError('environment_result_invalid')
        if type(row['tool_roots']) is not dict or set(row['tool_roots']) != {'python', 'pip', 'nvcc', 'ptxas'} or any(v not in {None, 'venv', 'cuda', 'unsloth_shim', 'usr_local', 'system', 'other'} for v in row['tool_roots'].values()):
            raise ValueError('environment_result_invalid')
    changed = [name for name in CORE if value['core_before'][name] != value['core_after'][name]]
    if value['changed_core_packages'] != changed or type(value['core_versions_unchanged']) is not bool or value['core_versions_unchanged'] != (not changed):
        raise ValueError('metadata_diff_invalid')
    present = all(value['core_before'].values()) and all(value['core_after'].values())
    if type(value['all_core_metadata_present']) is not bool or value['all_core_metadata_present'] != present:
        raise ValueError('metadata_presence_invalid')
    if type(value['pip_exit_code']) is not int or not 0 <= value['pip_exit_code'] <= 255 or value['pip_exception_type'] not in ERRORS | {None, 'OtherError'}:
        raise ValueError('pip_result_invalid')
    imports = value['imports']
    if type(imports) is not dict or set(imports) != {'wandb', 'torch'}:
        raise ValueError('import_result_invalid')
    for name, row in imports.items():
        if type(row) is not dict or set(row) != ({'status', 'version', 'exception_type', 'compiled_cuda'} if name == 'torch' else {'status', 'version', 'exception_type'}):
            raise ValueError('import_result_invalid')
        if row['status'] not in ('imported', 'failed') or row['exception_type'] not in ERRORS | {None, 'OtherError'} or any(row[k] is not None and safe_version(row[k]) != row[k] for k in ('version', *(['compiled_cuda'] if name == 'torch' else []))):
            raise ValueError('import_result_invalid')
    return value


def host(env, *, run=subprocess.run, disk_usage=shutil.disk_usage):
    launch = env.get('HASLA_DEPENDENCY_PROBE_LAUNCH_ID', '')
    if env.get('GITHUB_ACTIONS') != 'true' or env.get('RUNNER_OS') != 'Linux' or not re.fullmatch('[0-9a-f]{32}', launch):
        raise ValueError('fixed_ephemeral_runner_required')
    free = disk_usage('/').free
    event = {'event': 'private_qwq_dependency_probe', 'launch_id': launch, 'image': IMAGE,
             'free_disk_bytes': free, 'model_calls': 0, 'gpu_provider_calls': 0, 'credentials_passed': False}
    if free < 45 * 1024**3:
        return {**event, 'status': 'blocked', 'failure_code': 'disk_below_45gib'}
    name = 'hasla-qwq-dependency-probe-' + launch
    with tempfile.TemporaryDirectory(prefix='qwq-dependency-') as directory:
        root = Path(directory)
        log = (root / 'docker.log').open('wb')
        attempted = False
        try:
            pulled = run(['docker', 'pull', '--platform', 'linux/amd64', IMAGE], stdout=log,
                         stderr=subprocess.STDOUT, timeout=600, check=False)
            if pulled.returncode != 0:
                return {**event, 'status': 'failed', 'failure_code': 'fixed_image_pull_failed'}
            command = ['docker', 'run', '--rm', '--name', name, '--platform', 'linux/amd64',
                       '--entrypoint', PYTHON, '--mount', 'type=bind,src=' + str(Path(__file__).resolve()) + ',dst=/probe.py,readonly',
                       '--mount', 'type=bind,src=' + str(root) + ',dst=/probe-output']
            for key, value in FIXED_ENV.items():
                command += ['--env', key + '=' + value]
            command += [IMAGE, '/probe.py', '--inside', '/probe-output']
            attempted = True
            completed = run(command, stdout=log, stderr=subprocess.STDOUT, timeout=780, check=False)
            path = root / 'result.json'
            if completed.returncode != 0 or not path.is_file() or path.is_symlink() or path.stat().st_size > 32768:
                return {**event, 'status': 'failed', 'failure_code': 'container_probe_not_completed'}
            raw = path.read_bytes()
            value = validate(json.loads(raw))
            return {**event, 'status': 'observed', 'result_sha256': hashlib.sha256(raw).hexdigest(), 'result': value,
                    'cpu_imports_do_not_validate_gpu_runtime': True}
        except Exception as error:
            return {**event, 'status': 'failed', 'failure_code': 'fixed_probe_execution_failed', 'exception_type': error_class(error)}
        finally:
            if attempted:
                try:
                    run(['docker', 'rm', '-f', name], stdout=log, stderr=subprocess.STDOUT, timeout=30, check=False)
                except Exception:
                    pass
            log.close()


def main():
    if sys.argv[1:] == ['--environment']:
        print(json.dumps(environment_snapshot(), sort_keys=True))
        return 0
    if sys.argv[1:] == ['--inside', '/probe-output']:
        inside('/probe-output')
        return 0
    if sys.argv[1:]:
        raise ValueError('arguments_invalid')
    result = host(os.environ)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result['status'] == 'observed' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('{"event":"private_qwq_dependency_probe","status":"failed","failure_code":"probe_setup_failed"}')
        raise SystemExit(1)

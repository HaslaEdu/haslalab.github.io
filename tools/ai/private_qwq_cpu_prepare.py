"""Prepare one fixed private QwQ comparison on a standard CPU runner.

No corpus, GPU provider, Hugging Face credential, model training, or promotion.
Public immutable files are streamed and checked; SDK diagnostics stay private.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import urljoin, urlsplit

import private_resume_adapter as resume
from private_verify_adapter import PrivateReader, credentials
from role_config import get_role_config

GIB = 1024**3
MEMORY_MIN = 15 * GIB
DISK_MIN = 24 * GIB
ENTITY = 'mimgyuson-haslaedu'
LLAMA_COMMIT = '3de52ac38818978d6da8f386eda43a856e53714a'
LLAMA_REPOSITORY = 'https://github.com/ggml-org/llama.cpp.git'
QWEN_REVISION = '976055f8c83f394f35dbd3ab09a285a984907bd0'
GGUF_REVISION = 'd5faedaaaae5cdacdc487b53d90dcc7210ca218c'
PUBLIC_FILES = (
    {'name': 'QwQ-32B-UD-IQ3_XXS.gguf', 'repo': 'unsloth/QwQ-32B-GGUF',
     'revision': GGUF_REVISION, 'bytes': 13052652128,
     'sha256': '40e30d9b5ea5cabb5a252e587750b9b3dc7aaf3a86dd27fcd9eddca9f406ddbc'},
    {'name': 'config.json', 'repo': 'Qwen/QwQ-32B', 'revision': QWEN_REVISION,
     'bytes': 662, 'sha256': '61feaaef406a79c195ba8629921e99ad27753434c1e7bf60f5809cd73a86de68'},
    {'name': 'tokenizer_config.json', 'repo': 'Qwen/QwQ-32B', 'revision': QWEN_REVISION,
     'bytes': 8291, 'sha256': 'ab43f460108ca40fbb09fa537696baf862b6a9b46a2c6688b9de711293e3ddc4'},
)
ADAPTER_SPEC = {
    'kind': 'private_adapter_continuation', 'version': 1, 'role': 'solver',
    'base_model': 'Qwen/QwQ-32B', 'rank': 16,
    'source_training_run_id': '41919750109', 'prior_verification_run_id': '41927293867',
    'entity': ENTITY,
    'artifact': ENTITY + '/' + resume.PROJECT + '/hasla-private-books-41919750109-solver-lora:v0',
    'files': [
        {'name': 'adapter_config.json', 'bytes': 1322,
         'sha256': 'f9392d8f82273d1142deee6742dbf6c38697697c00264a7257c1582676f50372'},
        {'name': 'adapter_model.safetensors', 'bytes': 536991984,
         'sha256': 'c3821d50ae7255e7fc296a421af7e7c9c2677ad530a1b9895c616ff9bf208bd9'},
    ],
    'adapter_inventory_sha256': '36d6116f3ac8e78d207dfc045c9f33e00a342c978041adc5b54cec23f0d0a9b8',
}


class PreparationError(RuntimeError):
    pass


def require(condition, code):
    if not condition:
        raise PreparationError(code)


def hardware_preflight(parent, *, meminfo=Path('/proc/meminfo'), disk_usage=shutil.disk_usage,
                       gpu_devices=None):
    """Check physical memory and free disk before dependency/model downloads."""
    try:
        text = meminfo.read_text(encoding='ascii')
        match = re.search(r'^MemTotal:\s+([0-9]+) kB\s*$', text, re.M)
        require(match is not None, 'memory_total_unknown')
        memory = int(match.group(1)) * 1024
        free = disk_usage(parent).free
        devices = list(Path('/dev').glob('nvidia[0-9]*')) if gpu_devices is None else gpu_devices
        require(not devices, 'gpu_device_present')
        require(memory >= MEMORY_MIN, 'physical_memory_below_15gib')
        require(free >= DISK_MIN, 'free_disk_below_24gib')
        return {'physical_memory_bytes': memory, 'free_disk_bytes': free, 'gpu_count': 0}
    except PreparationError:
        raise
    except Exception:
        raise PreparationError('hardware_preflight_failed') from None


def checked_credentials(env):
    key = credentials(env)
    require(env.get('WANDB_ENTITY') == ENTITY, 'private_entity_mismatch')
    require(not any(value and ('RUNPOD' in name.upper() or
                name.upper() in {'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_API_KEY',
                                 'CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_AI_TOKEN'})
                for name, value in env.items()), 'unexpected_provider_credential')
    return key


def child_environment(env=None):
    source = os.environ if env is None else env
    allowed = ('PATH', 'HOME', 'TMPDIR', 'TMP', 'TEMP', 'LANG', 'LC_ALL', 'SYSTEMROOT')
    result = {key: source[key] for key in allowed if key in source}
    result.update(CUDA_VISIBLE_DEVICES='', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                  HF_HUB_DISABLE_IMPLICIT_TOKEN='1', GIT_TERMINAL_PROMPT='0',
                  GIT_CONFIG_NOSYSTEM='1', WANDB_MODE='disabled')
    return result


def _public_host(url):
    parsed = urlsplit(url)
    host = parsed.hostname or ''
    return (parsed.scheme == 'https' and parsed.port in (None, 443)
            and not parsed.username and not parsed.password
            and (host == 'huggingface.co' or host.endswith('.huggingface.co')
                 or host == 'hf.co' or host.endswith('.hf.co')))


def download_public(spec, target, *, session=None, clock=time.monotonic):
    """No auth/proxy/session credentials; immutable HF URL and legitimate CDN only."""
    if session is None:
        import requests
        session = requests.Session()
        session.trust_env = False
    require(not target.exists() and not target.is_symlink(), 'public_file_already_exists')
    url = ('https://huggingface.co/' + spec['repo'] + '/resolve/' + spec['revision']
           + '/' + spec['name'])
    partial = target.with_name(target.name + '.partial')
    require(not partial.exists() and not partial.is_symlink(), 'public_partial_already_exists')
    started = clock()
    response = None
    partial_owned = False
    try:
        for _ in range(6):
            require(_public_host(url), 'public_redirect_invalid')
            response = session.get(url, stream=True, allow_redirects=False,
                                   timeout=(10, 45), headers={'Accept-Encoding': 'identity'})
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get('Location')
                require(isinstance(location, str) and location, 'public_redirect_invalid')
                url = urljoin(url, location)
                response.close()
                response = None
                continue
            break
        require(response is not None and response.status_code == 200, 'public_download_failed')
        length = response.headers.get('Content-Length')
        require(length is None or length.isdecimal() and int(length) == spec['bytes'],
                'public_length_mismatch')
        digest, size = hashlib.sha256(), 0
        with partial.open('xb') as stream:
            partial_owned = True
            for chunk in response.iter_content(chunk_size=1024**2):
                require(clock() - started <= 1800, 'public_download_timeout')
                if not chunk:
                    continue
                size += len(chunk)
                require(size <= spec['bytes'], 'public_size_limit')
                digest.update(chunk)
                stream.write(chunk)
        require(size == spec['bytes'] and digest.hexdigest() == spec['sha256'],
                'public_hash_mismatch')
        os.link(partial, target)
        return {'name': spec['name'], 'bytes': size, 'sha256': digest.hexdigest()}
    except PreparationError:
        raise
    except Exception:
        raise PreparationError('public_download_failed') from None
    finally:
        if response is not None:
            response.close()
        if partial_owned:
            partial.unlink(missing_ok=True)


def _run(command, *, runner=subprocess.run, timeout=1200):
    result = runner(command, env=child_environment(), stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=timeout, check=False)
    require(result.returncode == 0, 'cpu_build_failed')
    return result


def build_cpu(root, *, runner=subprocess.run):
    root.mkdir()
    for command in (
        ['git', 'init', str(root)],
        ['git', '-C', str(root), '-c', 'credential.helper=', 'fetch', '--depth=1',
         LLAMA_REPOSITORY, LLAMA_COMMIT],
        ['git', '-C', str(root), 'checkout', '--detach', 'FETCH_HEAD'],
    ):
        _run(command, runner=runner, timeout=300)
    observed = runner(['git', '-C', str(root), 'rev-parse', 'HEAD'], env=child_environment(),
                      stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20, check=False)
    require(observed.returncode == 0 and observed.stdout.decode('ascii').strip() == LLAMA_COMMIT,
            'llama_revision_mismatch')
    _run(['cmake', '-S', str(root), '-B', str(root / 'build'), '-DGGML_CUDA=OFF',
          '-DGGML_VULKAN=OFF', '-DGGML_BLAS=OFF', '-DLLAMA_OPENSSL=OFF',
          '-DLLAMA_BUILD_APP=OFF', '-DLLAMA_BUILD_UI=OFF', '-DLLAMA_USE_PREBUILT_UI=OFF',
          '-DLLAMA_CONNECT=OFF', '-DLLAMA_BUILD_TESTS=OFF', '-DLLAMA_BUILD_EXAMPLES=OFF',
          '-DLLAMA_BUILD_SERVER=ON'],
         runner=runner)
    _run(['cmake', '--build', str(root / 'build'), '--config', 'Release',
          '--target', 'llama-server', '-j', '4'], runner=runner)
    binary = root / 'build' / 'bin' / 'llama-server'
    require(binary.is_file() and not binary.is_symlink(), 'cpu_server_missing')
    require((root / 'convert_lora_to_gguf.py').is_file(), 'converter_missing')
    return binary


def private_clients(env):
    key = checked_credentials(env)
    reader = PrivateReader(key)
    def privacy(entity):
        require(entity == ENTITY, 'private_entity_mismatch')
        reader.assert_private(entity)
        return {'entity': entity, 'project': resume.PROJECT, 'access': 'PRIVATE'}
    privacy(ENTITY)
    with resume._quiet():
        import wandb
        api = wandb.Api(api_key=key, timeout=60)
    return api, privacy


def prepare(output_dir, env, *, downloader=download_public, builder=build_cpu,
            preflight=hardware_preflight, clients=private_clients,
            adapter_downloader=resume.download_initial_adapter):
    checked_credentials(env)
    spec = resume.validate_spec(deepcopy(ADAPTER_SPEC), get_role_config('solver'))
    root = resume._private_root(output_dir)
    require(not root.exists(), 'prepared_directory_exists')
    hardware = preflight(root.parent)
    api, privacy = clients(env)
    root.mkdir()
    base = root / 'base-config'
    base.mkdir()
    proofs = []
    for public in PUBLIC_FILES:
        target = root / public['name'] if public['name'].endswith('.gguf') else base / public['name']
        proofs.append(downloader(public, target))
    adapter = root / 'adapter'
    adapter_downloader(spec, get_role_config('solver'), adapter, api, privacy)
    binary = builder(root / 'llama.cpp')
    privacy(ENTITY)
    prepared = {'version': 1, 'kind': 'private_qwq_cpu_comparison_prepared', 'private': True,
                'base_model': 'Qwen/QwQ-32B', 'quant': 'iq3_xxs',
                'base_gguf_path': str(root / PUBLIC_FILES[0]['name']), 'adapter_dir': str(adapter),
                'base_config_dir': str(base), 'tokenizer_config_path': str(base / 'tokenizer_config.json'),
                'llama_cpp_dir': str(root / 'llama.cpp'), 'llama_server_path': str(binary),
                'converter_path': str(root / 'llama.cpp' / 'convert_lora_to_gguf.py'),
                'llama_commit': LLAMA_COMMIT, 'public_files': proofs,
                'adapter_spec': spec, 'hardware': hardware,
                'training_corpus_accessed': False, 'provider_created': False, 'gpu_count': 0}
    with (root / 'prepared.json').open('xb') as stream:
        stream.write((json.dumps(prepared, sort_keys=True) + '\n').encode())
    return prepared


def publish_report(directory, env, *, clients=private_clients, sdk=None):
    """Publish only the worker's schema-checked final JSON pair to PRIVATE W&B."""
    checked_credentials(env)
    run_id = env.get('GITHUB_RUN_ID', '')
    require(isinstance(run_id, str) and re.fullmatch(r'[0-9]{1,32}', run_id), 'comparison_run_id_invalid')
    launch_id, commit = env.get('HASLA_CPU_COMPARE_LAUNCH_ID', ''), env.get('GITHUB_SHA', '')
    require(isinstance(launch_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{8,80}', launch_id), 'comparison_launch_id_invalid')
    require(isinstance(commit, str) and re.fullmatch(r'[0-9a-f]{40}', commit), 'comparison_commit_invalid')
    from private_qwq_cpu_eval import validate_upload_bundle
    import private_qwq_comparison as comparison
    paths = validate_upload_bundle(directory)
    require([p.name for p in paths] == ['report.json', 'metadata.json'], 'comparison_files_invalid')
    # Freeze the checked bytes before any SDK operation; never include work-dir
    # contents, generated reasoning, the source adapter, or converted weights.
    with tempfile.TemporaryDirectory(prefix='hasla-cpu-final-') as temporary:
        frozen = Path(temporary)
        proofs = []
        for path in paths:
            require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 4 * 1024**2,
                    'comparison_file_invalid')
            data = path.read_bytes()
            (frozen / path.name).write_bytes(data)
            proofs.append({'name': path.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        validate_upload_bundle(frozen)
        report = comparison.load_json(frozen / 'report.json')
        execution = comparison.load_json(frozen / 'metadata.json')
        require(execution['gguf_quant'] == 'iq3_xxs', 'comparison_quantization_mismatch')
        _, privacy = clients(env)
        privacy(ENTITY)
        if sdk is None:
            with resume._quiet():
                import wandb as sdk
        name = 'hasla-qwq-cpu-comparison-' + run_id
        metadata = {'private': True, 'gpu_count': 0, 'provider_created': False,
                    'source_training_run_id': ADAPTER_SPEC['source_training_run_id'],
                    'adapter_inventory_sha256': ADAPTER_SPEC['adapter_inventory_sha256'],
                    'comparison_run_id': run_id, 'launch_id': launch_id, 'code_commit': commit,
                    'reasoning_included': False, 'files': proofs}
        run, committed = None, None
        finish_failed = False
        try:
            with resume._quiet():
                run = sdk.init(entity=ENTITY, project=resume.PROJECT, name=name,
                               job_type='cpu-comparison', config={'private': True, 'gpu_count': 0},
                               reinit=True, mode='online')
                artifact = sdk.Artifact(name, type='evaluation', metadata=metadata)
                for row in proofs:
                    artifact.add_file(str(frozen / row['name']), name=row['name'])
            privacy(ENTITY)
            with resume._quiet():
                logged = run.log_artifact(artifact)
                saved = logged.wait(timeout=180)
                reference = str(saved.qualified_name)
                expected = ENTITY + '/' + resume.PROJECT + '/' + name
                require(saved.state == 'COMMITTED' and re.fullmatch(re.escape(expected) + r':v[0-9]+', reference),
                        'comparison_commit_not_verified')
                committed = reference
            privacy(ENTITY)
        finally:
            if run is not None:
                try:
                    with resume._quiet():
                        run.finish()
                except Exception:
                    if committed is None:
                        raise PreparationError('comparison_finish_failed') from None
                    finish_failed = True
        scores = {}
        for mode, group in report.get('results', {}).items():
            scores[mode] = {key: group[key] for key in ('passed_cases', 'total_cases',
                'correct_numeric_quantities', 'total_numeric_quantities', 'abstention_passed',
                'failures', 'paired_passed_cases', 'paired_correct_numeric_quantities')}
            scores[mode]['correct_units'] = sum(value['unit_ok'] for row in group['cases'] for value in row['numeric'])
            scores[mode]['cases'] = [{key: row[key] for key in ('case_id', 'passed', 'numeric', 'failure')}
                                    for row in group['cases']]
        return {'event': 'private_qwq_cpu_comparison', 'status': 'uploaded',
                'execution_status': execution['status'],
                'artifact': committed, 'private': True, 'gpu_count': 0,
                'run_id': run_id, 'launch_id': launch_id, 'code_commit': commit,
                'case_set_sha256': report.get('case_set_sha256', comparison.build_plan()['case_set_sha256']),
                'model_sha256': PUBLIC_FILES[0]['sha256'],
                'adapter_sha256': ADAPTER_SPEC['files'][1]['sha256'],
                'quantization': 'unsloth_dynamic_iq3_xxs_external_lora_f32',
                'case_count': 8, 'paired_completed_cases': report['paired_completed_cases'],
                'coverage_complete': report.get('coverage_complete', False), 'scores': scores,
                'files': proofs, 'reasoning_included': False, 'final_answers_included': False,
                'official_benchmark': False, 'scientific_verification': 'pending',
                'sdk_finish_failed_after_commit': finish_failed}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--upload-report', type=Path)
    args = parser.parse_args(argv)
    try:
        require(not (args.upload_report is not None and (args.output_dir is not None or args.preflight_only)),
                'conflicting_prepare_modes')
        if args.upload_report is not None:
            print(json.dumps(publish_report(args.upload_report, os.environ)))
        elif args.preflight_only:
            require(args.output_dir is not None, 'output_directory_required')
            result = hardware_preflight(args.output_dir.parent)
            print(json.dumps({'status': 'preflight_passed', **result}))
        else:
            require(args.output_dir is not None, 'output_directory_required')
            prepare(args.output_dir, os.environ)
            print(json.dumps({'status': 'prepared', 'gpu_count': 0, 'provider_created': False}))
        return 0
    except Exception as error:
        code = str(error) if isinstance(error, PreparationError) else 'cpu_preparation_failed'
        print(json.dumps({'status': 'failed', 'failure_code': code}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

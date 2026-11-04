"""One private textbook LoRA pilot, with bounded cost and no production promotion.

Run only in the repository's trusted Actions job. Dataset shards are encrypted
repository secrets, never committed source or public workflow artifacts. Only
the requested data, HF token and private W&B credentials enter the GPU Pod.
"""
import base64
from decimal import Decimal, InvalidOperation
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import traceback

import requests

from training_budget import BudgetLedger, BudgetPolicy, PodQuote, reserve_run, settle_run, should_stop, validate_observed_pod
from private_pod_train import decode_payload, rows_from_payload, verify_partitions


REST = 'https://api.runpod.io/v2'
PROJECT = 'hasla-ai-private-training'
PREFIX = 'hasla-private-books-'
E = os.environ
GPU_IDS = ('NVIDIA A100 80GB PCIe', 'NVIDIA A100-SXM4-80GB',
           'NVIDIA H100 80GB HBM3', 'NVIDIA H100 PCIe', 'NVIDIA H100 NVL')


def normalized_pod(value):
    """Translate the documented v2 billing fields for the existing cost ledger."""
    if not isinstance(value, dict) or not isinstance(value.get('id'), str):
        raise ValueError('RunPod returned an invalid pod')
    row = dict(value)
    if 'cost' in row:
        row['costPerHr'] = row['cost']
    if 'disk' in row:
        row['containerDiskInGb'] = row['disk']
    if 'status' in row:
        row['desiredStatus'] = row['status']
    mounts = row.get('mounts') or {}
    row['volumeInGb'] = (mounts.get('persistent') or {}).get('size', 0)
    if mounts.get('network') or mounts.get('global'):
        row['networkVolume'] = True
    return row


def safe_event(kind, **fields):
    print(json.dumps({'event': kind, **fields}, ensure_ascii=True), flush=True)


def runpod(method, path, **kwargs):
    timeout = kwargs.pop('request_timeout', 20)
    response = requests.request(method, REST + path, headers={'Authorization': 'Bearer ' + E['RUNPOD_API_KEY']},
                                timeout=timeout, **kwargs)
    if response.status_code >= 400:
        # An upstream error can echo the request's secret dataset/environment.
        body = str(getattr(response, 'text', '')).lower()
        if any(word in body for word in ('insufficient credit', 'insufficient fund', 'balance', 'add funds', 'deposit')):
            category = 'account_funding'
        elif any(word in body for word in ('no available', 'not available', 'no longer available', 'capacity', 'out of stock')):
            category = 'gpu_capacity'
        elif response.status_code == 413 or ('env' in body and any(w in body for w in ('length', 'large', 'limit', 'size'))):
            category = 'request_size'
        elif response.status_code in (401, 403):
            category = 'authorization'
        elif response.status_code in (400, 422):
            category = 'request_validation'
        else:
            category = 'provider_error'
        safe_event('runpod_api_error', method=method, http_status=response.status_code, category=category)
        raise RuntimeError(f'RunPod {method} status {response.status_code}')
    data = response.json() if response.content else None
    if method == 'GET' and path == '/pods':
        if not isinstance(data, dict) or not isinstance(data.get('pods'), list):
            raise ValueError('RunPod v2 pod list is invalid')
        return [normalized_pod(row) for row in data['pods']]
    if path.startswith('/pods/') or method == 'POST' and path == '/pods':
        return normalized_pod(data) if data is not None else None
    return data


def wandb_query(query, variables=None, timeout=20):
    response = requests.post('https://api.wandb.ai/graphql', json={'query': query, 'variables': variables or {}},
                             auth=('api', E['WANDB_API_KEY']), timeout=timeout)
    if not response.ok:
        raise RuntimeError(f'W&B preflight status {response.status_code}')
    data = response.json()
    if data.get('errors'):
        safe_event('wandb_schema_error', error_count=len(data['errors']))
        raise RuntimeError('W&B preflight GraphQL error')
    return data['data']


def private_project():
    import wandb
    entity = wandb_query('{viewer{entity}}')['viewer']['entity']
    # No private text or model artifact is logged while creating the empty project.
    run = wandb.init(entity=entity, project=PROJECT, job_type='private-preflight',
                     config={'purpose': 'private textbook LoRA pilot', 'budget_krw': 30000},
                     settings=wandb.Settings(disable_code=True, disable_git=True, console='off', save_code=False,
                                             disable_job_creation=True, x_disable_meta=True, x_disable_stats=True))
    run.finish()
    data = wandb_query('query($e:String!,$p:String!){project(name:$p,entityName:$e){name access}}',
                       {'e': entity, 'p': PROJECT})
    if str((data.get('project') or {}).get('access', '')).upper() != 'PRIVATE':
        raise RuntimeError('W&B project is not verified PRIVATE; no GPU or private upload started')
    return entity


def capacity_preflight():
    query = 'query { myself { clientBalance underBalance } }'
    response = requests.post('https://api.runpod.io/graphql', json={'query': query},
                             headers={'Authorization': 'Bearer ' + E['RUNPOD_API_KEY']}, timeout=20)
    if not response.ok:
        raise RuntimeError('RunPod read-only funding/capacity check failed')
    data = response.json()
    if data.get('errors') or not isinstance(data.get('data'), dict):
        fields = []
        for error in data.get('errors', []):
            message = str(error.get('message', ''))
            fields.extend(re.findall(r'(?:field|argument|type) ["\']([A-Za-z_][A-Za-z_0-9]*)["\']', message))
        safe_event('runpod_readonly_schema_error', error_count=len(data.get('errors', [])), fields=fields)
        raise RuntimeError('RunPod read-only schema check failed')
    user = data['data'].get('myself') or {}
    balance = user.get('clientBalance')
    funded = isinstance(balance, (float, int)) and balance > 0 and user.get('underBalance') is not True
    catalog = runpod('GET', '/catalog/gpus?include=AVAILABILITY&product=POD&count=1&cloud=SECURE')
    quotes = [{'gpu': gpu.get('id'), 'hourly_usd': (gpu.get('price') or {}).get('secure'),
               'stock': gpu.get('availability')}
              for gpu in catalog.get('gpus', []) if gpu.get('id') in GPU_IDS]
    safe_event('runpod_readonly_preflight', funded=funded, quotes=quotes)
    if not funded:
        raise RuntimeError('RunPod account needs prepaid funds; no payment or GPU creation attempted')
    for gpu_id in (GPU_IDS[1], GPU_IDS[0], *GPU_IDS[2:]):
        for row in quotes:
            try:
                price = Decimal(str(row['hourly_usd']))
            except InvalidOperation:
                continue
            if (row['gpu'] == gpu_id and str(row['stock']).upper() in ('LOW', 'MEDIUM', 'HIGH')
                    and price.is_finite() and 0 < price <= 4):
                return gpu_id
    raise RuntimeError('No supported GPU is available within the reserved USD4 hourly ceiling')


def graphql_create_pod(name, env, command, gpu_id=GPU_IDS[1]):
    # Compatibility name for callers; provisioning now uses the current REST v2.
    # Make exactly one creation request, then reconcile by exact name on failure.
    if gpu_id not in GPU_IDS:
        raise ValueError('Only the configured A100/H100 training GPUs are allowed for this pilot')
    return runpod('POST', '/pods', json={
        'name': name, 'cloud': 'SECURE', 'gpu': {'id': gpu_id, 'count': 1},
        'disk': 200, 'image': 'runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404',
        'entrypoint': ['/bin/bash', '-lc'], 'cmd': [command], 'ports': [], 'env': env,
        'startSsh': False, 'startJupyter': False})


def publish_private_input(entity, run_id, manifest, data_env):
    """Upload two checked files to a verified private project before renting a GPU."""
    import wandb
    checked = wandb_query('query($e:String!,$p:String!){project(name:$p,entityName:$e){name access}}',
                         {'e': entity, 'p': PROJECT}).get('project') or {}
    if checked.get('name') != PROJECT or checked.get('access') != 'PRIVATE':
        raise RuntimeError('private input project could not be verified')
    data_format = manifest.get('format', 'text')
    if data_format not in ('text', 'chat'):
        raise ValueError('unsupported private data format')
    role = manifest.get('role', 'solver')
    run = wandb.init(entity=entity, project=PROJECT, id=run_id + '-input', name=run_id + '-input',
        job_type='private-dataset-transfer', config={'format': data_format, 'role': role, 'private': True, 'test_records_used': 0},
        settings=wandb.Settings(console='off', disable_code=True, save_code=False, disable_git=True,
                                disable_job_creation=True, x_disable_meta=True, x_disable_stats=True))
    try:
        with tempfile.TemporaryDirectory(prefix='hasla-private-input-') as directory:
            artifact = wandb.Artifact(run_id + '-data', type='dataset', metadata={
                'dataset_version': manifest['dataset_version'], 'format': data_format, 'role': role, 'private': True,
                'training_sha256': manifest['train']['raw_sha256'],
                'validation_sha256': manifest['validation']['raw_sha256'], 'test_records_used': 0})
            for label, prefix in (('train', 'HASLA_DATA'), ('validation', 'HASLA_VALIDATION')):
                raw = decode_payload(data_env, prefix)
                if len(raw) > 16 * 1024 * 1024:
                    raise ValueError('private input exceeds its size limit')
                data_format = manifest.get('format', 'text')
                if data_format not in ('text', 'chat'):
                    raise ValueError('unsupported private data format')
                path = Path(directory, label + '.' + data_format + '.jsonl')
                path.write_bytes(raw)
                artifact.add_file(str(path), name=path.name)
            run.log_artifact(artifact, aliases=['pilot-input'])
            artifact.wait(timeout=180)
            reference = artifact.qualified_name
            expected = f'{entity}/{PROJECT}/{run_id}-data:'
            if not isinstance(reference, str) or not reference.startswith(expected) or not re.fullmatch(r'v\d+', reference[len(expected):]):
                raise RuntimeError('private dataset immutable version is missing')
        safe_event('private_input_ready', artifact=reference, raw_files=2, public=False)
        return {'HASLA_INPUT_ARTIFACT': reference, 'HASLA_DATA_SHA256': manifest['train']['raw_sha256'],
                'HASLA_VALIDATION_SHA256': manifest['validation']['raw_sha256']}
    finally:
        run.finish()


def data_environment():
    manifest = json.loads(E['HASLA_CORPUS_MANIFEST'])
    if manifest.get('format') != 'text' or manifest.get('budget_krw') != 30000:
        raise ValueError('unexpected private training manifest')
    if not re.fullmatch(r'[0-9a-f]{40}', E.get('GITHUB_SHA', '')):
        raise ValueError('a pinned public code commit is required')
    for key in ('train_script_sha256', 'pod_script_sha256'):
        if not re.fullmatch(r'[0-9a-f]{64}', manifest.get(key, '')):
            raise ValueError('invalid pinned script checksum')
    out = {}
    for label, prefix in (('train', 'HASLA_DATA'), ('validation', 'HASLA_VALIDATION')):
        item = manifest[label]
        if not re.fullmatch(r'[0-9a-f]{64}', item.get('raw_sha256', '')):
            raise ValueError('invalid private data checksum')
        parts = item['parts']
        if type(parts) is not int or not 1 <= parts <= 16:
            raise ValueError('invalid private shard count')
        values = []
        for i in range(parts):
            key = f'{prefix}_{i:02d}'
            value = E.get(key, '')
            if not value or len(value) > 40000:
                raise ValueError('missing or oversized private shard')
            base64.b64decode(value, validate=True)
            out[key] = value
            values.append(value)
        if hashlib.sha256(''.join(values).encode()).hexdigest() != item['encoded_sha256']:
            raise ValueError('private shard checksum mismatch')
        out[prefix + '_PARTS'] = str(parts)
        out[prefix + '_SHA256'] = item['raw_sha256']
    if sum(len(v) for v in out.values()) > 900000:
        raise ValueError('private pilot exceeds the environment payload limit')
    training = rows_from_payload(decode_payload(out, 'HASLA_DATA'), 'train')
    validation = rows_from_payload(decode_payload(out, 'HASLA_VALIDATION'), 'validation')
    verify_partitions(training, validation)
    if len(training) != manifest['train']['records'] or len(validation) != manifest['validation']['records']:
        raise ValueError('private record count does not match its manifest')
    return manifest, out


def result_for(entity, run_id, timeout=20):
    # Query only a fixed safe summary field; never fetch console output or private data.
    data = wandb_query('query($e:String!,$p:String!,$r:String!){project(name:$p,entityName:$e){run(name:$r){state summaryMetrics}}}',
                       {'e': entity, 'p': PROJECT, 'r': run_id}, timeout=timeout)
    row = (data.get('project') or {}).get('run')
    if not row:
        return None
    summary = row.get('summaryMetrics') or '{}'
    if isinstance(summary, str):
        summary = json.loads(summary)
    return summary.get('private_training_result')


def delete_and_confirm(pod_id):
    # Retry deletion, not creation. Keep a failed deletion visible to the final cleanup step.
    for _ in range(3):
        try:
            response = requests.delete(REST + '/pods/' + pod_id,
                headers={'Authorization': 'Bearer ' + E['RUNPOD_API_KEY']}, timeout=20)
            if response.status_code not in (200, 204, 404):
                continue
            check = requests.get(REST + '/pods/' + pod_id,
                headers={'Authorization': 'Bearer ' + E['RUNPOD_API_KEY']}, timeout=20)
            if check.status_code == 404 or (check.ok and check.json().get('status') == 'TERMINATED'):
                return True
        except requests.RequestException:
            pass
    return False


def reconcile_created_pods(name):
    """A lost create response may precede listing visibility. Never recreate."""
    for attempt in range(4):
        matches = [p for p in runpod('GET', '/pods') if p.get('name') == name]
        if matches:
            return matches
        if attempt != 3:
            time.sleep(5)
    return []


def cleanup():
    name = E.get('HASLA_PRIVATE_POD_NAME', PREFIX + E.get('GITHUB_RUN_ID', 'invalid'))
    if not name.startswith(PREFIX):
        raise ValueError('cleanup target is outside this pilot')
    matches = [p for p in runpod('GET', '/pods') if p.get('name') == name]
    outcomes = [delete_and_confirm(p['id']) for p in matches]
    ok = all(outcomes)
    safe_event('cleanup', matched_pods=len(matches), deletion_confirmed=ok)
    return 0 if ok else 1


def main():
    if '--cleanup' in sys.argv:
        return cleanup()
    manifest, data_env = data_environment()
    # Credential/model access and project privacy are checked before creating paid resources.
    for key in ('RUNPOD_API_KEY', 'WANDB_API_KEY', 'HF_TOKEN'):
        if not E.get(key):
            raise ValueError('missing training credential: ' + key)
    existing = runpod('GET', '/pods')
    run_id = PREFIX + E['GITHUB_RUN_ID']
    if any(p.get('name') == run_id for p in existing):
        raise RuntimeError('this pilot already has a Pod; inspect it instead of creating a duplicate')
    if E.get('HASLA_CHECK_CAPACITY') == 'true':
        capacity_preflight()
    for filename in ('config.json', 'tokenizer_config.json'):
        check = requests.head('https://huggingface.co/Qwen/QwQ-32B/resolve/main/' + filename,
                              headers={'Authorization': 'Bearer ' + E['HF_TOKEN']}, allow_redirects=True, timeout=20)
        if not check.ok:
            raise RuntimeError(f'base model file access status {check.status_code}')
    entity = private_project()
    policy = BudgetPolicy(fx_krw_per_usd_upper=2000, budget_krw=30000, reserve_krw=5000, tax_multiplier='1.15')
    quote = PodQuote(gpu_usd_per_hour_upper=3, container_disk_gb=200, volume_disk_gb=0)
    ledger = reserve_run(BudgetLedger(policy, prior_spend_krw=manifest.get('prior_upper_krw', 0)),
                         run_id, 'solver', quote, time.monotonic(), 3600, 3600)
    plan = ledger.runs[-1].plan
    safe_event('preflight', training_records=manifest['train']['records'], validation_records=manifest['validation']['records'],
               budget_krw=30000, reserved_upper_krw=str(plan.reserved_krw), runtime_seconds=plan.run_seconds,
               production_promotion=False)
    if E.get('HASLA_PREFLIGHT_ONLY') == 'true':
        return 0
    if E.get('HASLA_INPUT_TRANSPORT') == 'artifact':
        data_env = publish_private_input(entity, run_id, manifest, data_env)
    env = {**data_env, 'REPO_SHA': E['GITHUB_SHA'],
           'HASLA_TRAIN_SCRIPT_SHA256': manifest['train_script_sha256'],
           'HF_TOKEN': E['HF_TOKEN'], 'WANDB_API_KEY': E['WANDB_API_KEY'], 'WANDB_ENTITY': entity,
           'WANDB_PROJECT': PROJECT, 'RUN': run_id, 'ARTIFACT': run_id + '-lora', 'ROLE': 'solver',
           'HASLA_MAX_STEPS': '32', 'WANDB_CONSOLE': 'off', 'WANDB_DISABLE_CODE': 'true'}
    script_url = f'https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io/{E["GITHUB_SHA"]}/tools/ai/private_pod_train.py'
    start = ('set -eu; export PIP_DISABLE_PIP_VERSION_CHECK=1; '
             'pip install -q --upgrade unsloth trl datasets wandb >/workspace/install.log 2>&1; '
             f'curl -fsSL {script_url} -o /workspace/private_pod_train.py; '
             f'echo "{manifest["pod_script_sha256"]}  /workspace/private_pod_train.py" | sha256sum -c - >/dev/null; '
             'python /workspace/private_pod_train.py')
    pod = None
    result = None
    confirmed = False
    creation_attempted = False
    try:
        creation_attempted = True
        bounded_command = 'timeout --signal=TERM --kill-after=30s 3300s bash -lc ' + __import__('shlex').quote(start)
        if E.get('HASLA_CREATE_API') == 'graphql':
            pod = graphql_create_pod(run_id, env, 'bash -lc ' + __import__('shlex').quote(bounded_command))
            pod = runpod('GET', '/pods/' + pod['id'])
        else:
            pod = runpod('POST', '/pods', json={'name': run_id, 'imageName': 'runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04',
                'cloudType': 'SECURE', 'gpuTypeIds': [GPU_IDS[0]], 'gpuCount': 1,
                'containerDiskInGb': 200, 'volumeInGb': 0, 'interruptible': False, 'env': env,
                'dockerStartCmd': ['bash', '-lc', bounded_command]})
        validate_observed_pod(plan, pod)
        safe_event('pod_started', pod_id=pod['id'], hourly_usd=pod['costPerHr'])
        Path('private-pilot-state.json').write_text(json.dumps({'pod_id': pod['id'], 'run': run_id}), encoding='utf-8')
        while not should_stop(plan, time.monotonic()):
            remaining = max(0.1, float(plan.deadline_monotonic) - time.monotonic())
            result = result_for(entity, run_id, timeout=min(10, remaining))
            if result:
                break
            if should_stop(plan, time.monotonic()):
                break
            remaining = max(0.1, float(plan.deadline_monotonic) - time.monotonic())
            info = runpod('GET', '/pods/' + pod['id'], request_timeout=min(10, remaining))
            validate_observed_pod(plan, info)
            if info.get('desiredStatus') in ('EXITED', 'TERMINATED'):
                raise RuntimeError('private GPU process ended without a completed adapter')
            time.sleep(min(20, max(0, float(plan.deadline_monotonic) - time.monotonic())))
        if not result or result.get('status') != 'uploaded':
            raise RuntimeError('private pilot did not complete before its deadline')
        safe_event('training_completed', artifact=result.get('artifact'), training_records=result.get('training_records'),
                   weights_updated=True, production_promotion=False)
        Path('private-pilot-result.json').write_text(json.dumps(result, ensure_ascii=True), encoding='utf-8')
        return 0
    finally:
        if creation_attempted:
            # A POST timeout does not prove creation failed. Recover only by exact run name.
            matches = [pod] if pod and pod.get('id') else [p for p in runpod('GET', '/pods') if p.get('name') == run_id]
            outcomes = [delete_and_confirm(p['id']) for p in matches]
            confirmed = all(outcomes)
            safe_event('pod_cleanup', matched_pods=len(matches), deletion_confirmed=confirmed)
            if confirmed:
                ledger = settle_run(ledger, run_id, time.monotonic(), deletion_confirmed=True)
                safe_event('cost_estimate_upper', krw=str(ledger.spent_krw), budget_krw=30000)
            else:
                raise RuntimeError('Pod deletion was not confirmed; final workflow cleanup must retry')


if __name__ == '__main__':
    def terminate(_signum, _frame):
        raise SystemExit(143)  # honor finally cleanup on an Actions cancellation
    signal.signal(signal.SIGTERM, terminate)
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Exception strings from third parties might contain a payload: print only the class.
        frames = [{'file': Path(f.filename).name, 'line': f.lineno, 'function': f.name}
                  for f in traceback.extract_tb(exc.__traceback__)[-6:]]
        safe_event('failed', error_class=type(exc).__name__, trace=frames, weights_updated=False)
        raise SystemExit(1)

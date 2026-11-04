"""One bounded A100 Pod; independent Gemma chat and QwQ textbook adapters."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import sys
import time
import traceback

import private_corpus_run as cloud
from private_pod_train import decode_payload, rows_from_payload, verify_partitions
from training_budget import BudgetLedger, BudgetPolicy, PodQuote, reserve_run, settle_run, should_stop, validate_observed_pod


def validate_source_lineage(rows, role):
    """This pilot must use collected exchanges and the user's Drive textbooks."""
    for row in rows:
        meta = row.get('metadata') or {}
        if role == 'chat':
            if (meta.get('derivation') != 'paraphrase_observed_exchange'
                    or meta.get('reconstructed') is not True
                    or meta.get('old_synthetic_seed') is not False
                    or not meta.get('observed_reply_link')
                    or not meta.get('reviewer')
                    or meta.get('review_status') != 'approved'
                    or not meta.get('collected_at')
                    or not re.fullmatch(r'https://(?:orbi\.kr/[0-9]+|gall\.dcinside\.com/(?:m?gallery/)?board/view/\?id=[A-Za-z0-9_]+&no=[0-9]+)', str(meta.get('source_url', '')))
                    or any(not re.fullmatch(r'[a-f0-9]{64}', str(meta.get(key, '')))
                           for key in ('question_sha256', 'answer_sha256'))):
                raise ValueError('Gemma requires reviewed, source-grounded collected exchanges')
        elif (not isinstance(meta.get('drive_provenance'), dict)
              or not meta['drive_provenance'].get('drive_file_id')
              or not re.fullmatch(r'[a-f0-9]{64}', str(meta['drive_provenance'].get('local_original_pdf_sha256', '')))
              or not meta.get('page_number')
              or meta.get('scan_suspect') is True):
            raise ValueError('QwQ requires native-text pages with Drive and PDF provenance')


def load_inputs(env):
    manifest = json.loads(env['HASLA_DUAL_MANIFEST'])
    if manifest.get('budget_krw') != 30000 or list(manifest.get('roles', {})) != ['chat', 'solver']:
        raise ValueError('invalid dual-role budget or ordering')
    for key in ('train_script_sha256', 'role_config_sha256', 'pod_script_sha256', 'dual_pod_sha256'):
        if not re.fullmatch(r'[a-f0-9]{64}', manifest.get(key, '')):
            raise ValueError('pinned code checksums are required')
    if not re.fullmatch(r'[0-9a-f]{40}', env.get('GITHUB_SHA', '')):
        raise ValueError('a pinned public commit is required')
    payloads = {}
    for role, spec in manifest['roles'].items():
        expected = 'chat' if role == 'chat' else 'text'
        if spec.get('format') != expected:
            raise ValueError('role and corpus formats do not match')
        data_env = {}
        for split, target in (('train', 'HASLA_DATA'), ('validation', 'HASLA_VALIDATION')):
            source = f'HASLA_{role.upper()}_' + ('DATA' if split == 'train' else 'VALIDATION')
            item = spec[split]
            count = item.get('parts')
            if type(count) is not int or not 1 <= count <= 16:
                raise ValueError('invalid private shard count')
            values = []
            for i in range(count):
                value = env.get(f'{source}_{i:02d}', '')
                if not value or len(value) > 40000:
                    raise ValueError('missing or oversized encrypted input shard')
                values.append(value)
                data_env[f'{target}_{i:02d}'] = value
            if hashlib.sha256(''.join(values).encode()).hexdigest() != item['encoded_sha256']:
                raise ValueError('private encoded input checksum mismatch')
            data_env[target + '_PARTS'] = str(count)
            data_env[target + '_SHA256'] = item['raw_sha256']
        training = rows_from_payload(decode_payload(data_env), 'train', expected)
        validation = rows_from_payload(decode_payload(data_env, 'HASLA_VALIDATION'), 'validation', expected)
        validate_source_lineage(training + validation, role)
        verify_partitions(training, validation)
        if len(training) != spec['train']['records'] or len(validation) != spec['validation']['records']:
            raise ValueError('private record count mismatch')
        payloads[role] = data_env
    return manifest, payloads


def main():
    env = os.environ
    cloud.E = env
    if '--cleanup' in sys.argv:
        return cloud.cleanup()
    manifest, payloads = load_inputs(env)
    for key in ('RUNPOD_API_KEY', 'WANDB_API_KEY', 'HF_TOKEN'):
        if not env.get(key):
            raise ValueError('missing required training credential')
    run_id = cloud.PREFIX + env['GITHUB_RUN_ID']
    if any(p.get('name') == run_id for p in cloud.runpod('GET', '/pods')):
        raise RuntimeError('a Pod already exists for this run')
    selected_gpu = cloud.capacity_preflight()
    bases = {'chat': 'google/gemma-4-26B-A4B-it', 'solver': 'Qwen/QwQ-32B'}
    for role, model in bases.items():
        response = cloud.requests.head(f'https://huggingface.co/{model}/resolve/main/config.json',
            headers={'Authorization': 'Bearer ' + env['HF_TOKEN']}, allow_redirects=True, timeout=20)
        if not response.ok:
            cloud.safe_event('model_access_failed', role=role, http_status=response.status_code)
            raise RuntimeError('base model access check failed')
    entity = cloud.private_project()
    policy = BudgetPolicy(fx_krw_per_usd_upper=2000, budget_krw=30000, reserve_krw=5000, tax_multiplier='1.15')
    quote = PodQuote(gpu_usd_per_hour_upper=3, container_disk_gb=200, volume_disk_gb=0)
    ledger = reserve_run(BudgetLedger(policy, prior_spend_krw=manifest.get('prior_upper_krw', 10)),
                         run_id, 'dual', quote, time.monotonic(), 7200, 7200)
    plan = ledger.runs[-1].plan
    cloud.safe_event('dual_preflight', roles={r: {'format': s['format'], 'training_records': s['train']['records'],
        'validation_records': s['validation']['records']} for r, s in manifest['roles'].items()},
        budget_krw=30000, reserved_upper_krw=str(plan.reserved_krw), runtime_seconds=plan.run_seconds)
    if env.get('HASLA_PREFLIGHT_ONLY') == 'true':
        return 0
    jobs = []
    for role, spec in manifest['roles'].items():
        input_ref = cloud.publish_private_input(entity, run_id + '-' + role, {**spec, 'role': role}, payloads[role])
        jobs.append({'role': role, 'format': spec['format'], 'run': run_id + '-' + role,
                     'input_artifact': input_ref['HASLA_INPUT_ARTIFACT'],
                     'training_sha256': spec['train']['raw_sha256'],
                     'validation_sha256': spec['validation']['raw_sha256']})
    pod_env = {'HASLA_ROLE_JOBS': json.dumps(jobs, separators=(',', ':')), 'REPO_SHA': env['GITHUB_SHA'],
        'HASLA_TRAIN_SCRIPT_SHA256': manifest['train_script_sha256'],
        'HASLA_ROLE_CONFIG_SHA256': manifest['role_config_sha256'],
        'HASLA_POD_SCRIPT_SHA256': manifest['pod_script_sha256'],
        'HF_TOKEN': env['HF_TOKEN'], 'WANDB_API_KEY': env['WANDB_API_KEY'],
        'WANDB_ENTITY': entity, 'WANDB_PROJECT': cloud.PROJECT,
        'WANDB_CONSOLE': 'off', 'WANDB_DISABLE_CODE': 'true'}
    url = f'https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io/{env["GITHUB_SHA"]}/tools/ai/private_dual_pod.py'
    start = ('set -eu; mkdir -p /workspace; export PIP_DISABLE_PIP_VERSION_CHECK=1; '
             'pip install -q --upgrade unsloth trl datasets wandb >/workspace/install.log 2>&1; '
             f'curl -fsSL {url} -o /workspace/private_dual_pod.py; '
             f'echo "{manifest["dual_pod_sha256"]}  /workspace/private_dual_pod.py" | sha256sum -c - >/dev/null; '
             'python /workspace/private_dual_pod.py')
    command = 'bash -lc ' + shlex.quote('timeout --signal=TERM --kill-after=30s 6600s bash -lc ' + shlex.quote(start))
    pod, attempted, results = None, False, {}
    try:
        attempted = True
        cloud.safe_event('gpu_request', api='rest_v2', gpu=selected_gpu, roles=['chat', 'solver'],
                         private_environment_bytes=sum(len(v) for v in pod_env.values()))
        pod = cloud.graphql_create_pod(run_id, pod_env, command, gpu_id=selected_gpu)
        pod = cloud.runpod('GET', '/pods/' + pod['id'])
        validate_observed_pod(plan, pod)
        cloud.safe_event('pod_started', pod_id=pod['id'], hourly_usd=pod['costPerHr'], roles=['chat', 'solver'])
        last_roles = []
        while not should_stop(plan, time.monotonic()):
            for job in jobs:
                remaining = float(plan.deadline_monotonic) - time.monotonic()
                if remaining <= 0:
                    break
                row = cloud.result_for(entity, job['run'], timeout=min(10, remaining))
                if row:
                    if row.get('status') != 'uploaded':
                        cloud.safe_event('role_failed', role=job['role'], stage=row.get('stage'), error_code=row.get('error_code'))
                        raise RuntimeError('one model did not complete successfully')
                    results[job['role']] = row
            if sorted(results) != last_roles:
                last_roles = sorted(results)
                cloud.safe_event('roles_completed', roles=last_roles)
            if len(results) == 2:
                cloud.safe_event('dual_training_completed', artifacts={r: x['artifact'] for r, x in results.items()},
                                 weights_updated=True, production_promotion=False)
                Path('private-dual-result.json').write_text(json.dumps(results, ensure_ascii=True), encoding='utf8')
                return 0
            remaining = float(plan.deadline_monotonic) - time.monotonic()
            if remaining <= 0:
                break
            info = cloud.runpod('GET', '/pods/' + pod['id'], request_timeout=min(10, remaining))
            validate_observed_pod(plan, info)
            if info.get('desiredStatus') in ('EXITED', 'ERROR', 'TERMINATED'):
                raise RuntimeError('GPU stopped before both private adapters were uploaded')
            time.sleep(min(20, max(0, float(plan.deadline_monotonic) - time.monotonic())))
        raise RuntimeError('dual-model deadline reached')
    finally:
        if attempted:
            matches = [pod] if pod and pod.get('id') else cloud.reconcile_created_pods(run_id)
            outcomes = [cloud.delete_and_confirm(p['id']) for p in matches]
            confirmed = all(outcomes)
            cloud.safe_event('pod_cleanup', matched_pods=len(matches), deletion_confirmed=confirmed)
            if confirmed:
                ledger = settle_run(ledger, run_id, time.monotonic(), deletion_confirmed=True)
                cloud.safe_event('cost_estimate_upper', krw=str(ledger.spent_krw), budget_krw=30000)
            else:
                raise RuntimeError('GPU deletion could not be confirmed')


if __name__ == '__main__':
    def terminate(_signum, _frame):
        raise SystemExit(143)
    signal.signal(signal.SIGTERM, terminate)
    try:
        raise SystemExit(main())
    except Exception as error:
        frames = [{'file': Path(f.filename).name, 'line': f.lineno, 'function': f.name}
                  for f in traceback.extract_tb(error.__traceback__)[-5:]]
        cloud.safe_event('failed', error_class=type(error).__name__, trace=frames, weights_updated=False)
        raise SystemExit(1)

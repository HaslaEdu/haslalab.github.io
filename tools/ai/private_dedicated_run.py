"""One separately bounded GPU Pod per model, sharing one authorized budget ledger."""
import json
from dataclasses import replace
import os
from pathlib import Path
import re
import shlex
import signal
import sys
import time

import private_corpus_run as cloud
import private_dual_run as inputs
from role_config import get_role_config
from training_budget import BudgetError, reserve_run, settle_run, should_stop, validate_observed_pod


def target_names(run_id):
    if not isinstance(run_id, str) or not re.fullmatch(r'[0-9]{1,32}', run_id):
        raise ValueError('a numeric workflow identity is required')
    base = cloud.PREFIX + run_id
    return {base + '-chat', base + '-solver'}


def cleanup(env):
    """Delete only the two exact dedicated names belonging to this workflow."""
    names = target_names(env.get('GITHUB_RUN_ID', ''))
    matches = []
    for attempt in range(4):
        matches = [pod for pod in cloud.runpod('GET', '/pods') if pod.get('name') in names]
        if matches or attempt == 3:
            break
        time.sleep(5)
    confirmed = all([cloud.delete_and_confirm(pod['id']) for pod in matches])
    pending = Path('private-dedicated-pending.json')
    if pending.exists():
        unknown_names = set(json.loads(pending.read_text(encoding='utf8')))
        confirmed = confirmed and unknown_names <= {pod['name'] for pod in matches}
    cloud.safe_event('cleanup', matched_pods=len(matches), deletion_confirmed=confirmed)
    return 0 if confirmed else 1


def pod_environment(env, manifest, entity, role, run_name, reference, seconds):
    spec = manifest['roles'][role]
    job = {'role': role, 'format': spec['format'], 'run': run_name, 'input_artifact': reference,
           'training_sha256': spec['train']['raw_sha256'],
           'validation_sha256': spec['validation']['raw_sha256'], 'runtime_seconds': seconds - 600}
    return {'HASLA_ROLE_JOBS': json.dumps([job], separators=(',', ':')), 'REPO_SHA': env['GITHUB_SHA'],
            'HASLA_TRAIN_SCRIPT_SHA256': manifest['train_script_sha256'],
            'HASLA_ROLE_CONFIG_SHA256': manifest['role_config_sha256'],
            'HASLA_POD_SCRIPT_SHA256': manifest['pod_script_sha256'],
            'HF_TOKEN': env['HF_TOKEN'], 'WANDB_API_KEY': env['WANDB_API_KEY'],
            'WANDB_ENTITY': entity, 'WANDB_PROJECT': cloud.PROJECT,
            'WANDB_CONSOLE': 'off', 'WANDB_DISABLE_CODE': 'true'}


def pod_command(env, manifest, seconds):
    url = f'https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io/{env["GITHUB_SHA"]}/tools/ai/private_dual_pod.py'
    start = ('set -eu; mkdir -p /workspace; export PIP_DISABLE_PIP_VERSION_CHECK=1; '
             'pip install -q --upgrade unsloth trl datasets wandb >/workspace/install.log 2>&1; '
             f'curl -fsSL {url} -o /workspace/private_dual_pod.py; '
             f'echo "{manifest["dual_pod_sha256"]}  /workspace/private_dual_pod.py" | sha256sum -c - >/dev/null; '
             'python /workspace/private_dual_pod.py')
    return 'bash -lc ' + shlex.quote(f'timeout --signal=TERM --kill-after=30s {seconds - 120}s bash -lc ' + shlex.quote(start))


def main():
    env = os.environ
    cloud.E = env
    if '--cleanup' in sys.argv:
        return cleanup(env)
    manifest, payloads = inputs.load_inputs(env)
    roles = manifest['selected_roles']
    target_names(env.get('GITHUB_RUN_ID', ''))
    for key in ('RUNPOD_API_KEY', 'WANDB_API_KEY', 'HF_TOKEN'):
        if not env.get(key):
            raise ValueError('missing training credential')
    inputs.verify_pinned_scripts(manifest, env['GITHUB_SHA'])
    if any(str(pod.get('name', '')).startswith(cloud.PREFIX) for pod in cloud.runpod('GET', '/pods')):
        raise RuntimeError('an earlier private Pod still needs confirmed cleanup')
    entity = cloud.private_project()
    inputs.verify_staged_inputs(manifest, payloads, env, entity)
    ledger = None
    plans, gpus, references = {}, {}, {}
    base = cloud.PREFIX + env['GITHUB_RUN_ID']
    for role in roles:
        initial, quote, seconds, preferences = inputs.resource_settings(manifest, role)
        ledger = replace(initial, policy=replace(initial.policy, max_active_pods=2)) if ledger is None else ledger
        gpu = cloud.capacity_preflight(preferred_gpu_ids=preferences, hourly_ceiling=quote.gpu_usd_per_hour_upper)
        if gpu not in preferences:
            raise ValueError('capacity response violates the frozen model GPU policy')
        gpus[role] = gpu
        response = cloud.requests.head(
            f'https://huggingface.co/{get_role_config(role)["base_model"]}/resolve/main/config.json',
            headers={'Authorization': 'Bearer ' + env['HF_TOKEN']}, allow_redirects=True, timeout=20)
        if not response.ok:
            cloud.safe_event('model_access_failed', role=role, http_status=response.status_code)
            raise RuntimeError('model access preflight failed')
        ledger = reserve_run(ledger, base + '-' + role, role, quote, time.monotonic(), seconds, seconds)
        plans[role] = ledger.runs[-1].plan
        if plans[role].run_seconds < 660:
            raise ValueError('the combined budget cannot cover a selected model')
    cloud.safe_event('dual_preflight', selected_roles=roles, dedicated_pods=True,
                     budget_krw=int(ledger.policy.budget_krw), prior_upper_krw=str(ledger.prior_spend_krw),
                     roles={r: {'format': manifest['roles'][r]['format'],
                                'training_records': manifest['roles'][r]['train']['records'],
                                'validation_records': manifest['roles'][r]['validation']['records'],
                                'runtime_seconds': plans[r].run_seconds, 'gpu': gpus[r],
                                'reserved_upper_krw': str(plans[r].reserved_krw)} for r in roles})
    if env.get('HASLA_PREFLIGHT_ONLY') == 'true':
        return 0
    for role in roles:
        spec = manifest['roles'][role]
        if spec.get('input_artifact'):
            references[role] = spec['input_artifact']
        else:
            references[role] = cloud.publish_private_input(entity, base + '-' + role,
                {**spec, 'role': role}, payloads[role])['HASLA_INPUT_ARTIFACT']
    attempted, pods, closed, results, failures, uncertain = set(), {}, set(), {}, {}, set()

    def close(role):
        nonlocal ledger
        if role in closed:
            return
        matches = [pods[role]] if role in pods else cloud.reconcile_created_pods(base + '-' + role)
        if not matches and role in uncertain:
            Path('private-dedicated-pending.json').write_text(json.dumps([base + '-' + r for r in uncertain]), encoding='utf8')
            raise RuntimeError('unknown creation outcome is not confirmed deletion')
        confirmed = all([cloud.delete_and_confirm(pod['id']) for pod in matches])
        cloud.safe_event('pod_cleanup', role=role, matched_pods=len(matches), deletion_confirmed=confirmed)
        if not confirmed:
            raise RuntimeError('dedicated GPU deletion is not confirmed')
        ledger = settle_run(ledger, base + '-' + role, time.monotonic(), deletion_confirmed=True)
        closed.add(role)
        uncertain.discard(role)
        Path('private-dedicated-pending.json').write_text(json.dumps([base + '-' + r for r in uncertain]), encoding='utf8')
        if ledger.over_budget:
            raise BudgetError('shared cost bound exceeded; close remaining GPUs')

    try:
        for role in roles:
            remaining = int(float(plans[role].deadline_monotonic) - time.monotonic())
            if remaining < 660 or should_stop(plans[role], time.monotonic()):
                failures[role] = {'status': 'failed', 'stage': 'gpu_creation', 'error_code': 'insufficient_model_runtime'}
                continue
            attempted.add(role)
            child_env = pod_environment(env, manifest, entity, role, base + '-' + role,
                                        references[role], remaining)
            cloud.safe_event('gpu_request', api='rest_v2', gpu=gpus[role], roles=[role], dedicated_pod=True)
            try:
                uncertain.add(role)
                pod = cloud.graphql_create_pod(base + '-' + role, child_env,
                    pod_command(env, manifest, remaining), gpu_id=gpus[role])
                pods[role] = pod
                uncertain.discard(role)
                pod = cloud.runpod('GET', '/pods/' + pod['id'])
                validate_observed_pod(plans[role], pod)
                if (pod.get('gpu') or {}).get('id') != gpus[role]:
                    raise ValueError('created GPU does not match its role policy')
                pods[role] = pod
                cloud.safe_event('pod_started', pod_id=pod['id'], role=role,
                                 hourly_usd=pod['costPerHr'], roles=[role], dedicated_pod=True)
            except Exception as error:
                if re.fullmatch(r'RunPod POST status (?:400|401|402|403|404|409|413|422|429)', str(error)):
                    uncertain.discard(role)
                failures[role] = {'status': 'failed', 'stage': 'gpu_creation', 'error_code': 'dedicated_gpu_creation_failed'}
                close(role)
        while len(results) + len(failures) < len(roles):
            for role in roles:
                if role in results or role in failures:
                    continue
                plan = plans[role]
                if should_stop(plan, time.monotonic()):
                    failures[role] = {'status': 'failed', 'stage': 'training', 'error_code': 'dedicated_model_deadline'}
                    close(role)
                    continue
                remaining = float(plan.deadline_monotonic) - time.monotonic()
                row = cloud.result_for(entity, base + '-' + role, timeout=min(10, remaining))
                if row:
                    if row.get('status') == 'uploaded':
                        results[role] = row
                        cloud.safe_event('roles_completed', roles=sorted(results))
                    else:
                        failures[role] = row
                        cloud.safe_event('role_failed', role=role, stage=row.get('stage'), error_code=row.get('error_code'))
                    close(role)
                    continue
                remaining = float(plan.deadline_monotonic) - time.monotonic()
                if remaining <= 0:
                    failures[role] = {'status': 'failed', 'stage': 'training', 'error_code': 'dedicated_model_deadline'}
                    close(role)
                    continue
                pod = cloud.runpod('GET', '/pods/' + pods[role]['id'], request_timeout=min(10, remaining))
                validate_observed_pod(plan, pod)
                if should_stop(plan, time.monotonic()) or pod.get('desiredStatus') in ('EXITED', 'ERROR', 'TERMINATED'):
                    failures[role] = {'status': 'failed', 'stage': 'training', 'error_code': 'dedicated_model_incomplete'}
                    cloud.safe_event('role_failed', role=role, stage='training', error_code='dedicated_model_incomplete')
                    close(role)
            if len(results) + len(failures) < len(roles):
                remaining = min(float(plans[role].deadline_monotonic) - time.monotonic()
                                for role in roles if role not in results and role not in failures)
                if remaining > 0:
                    time.sleep(min(20, remaining))
        Path('private-dual-result.json').write_text(json.dumps(results), encoding='utf8')
        if failures:
            Path('private-dual-failures.json').write_text(json.dumps(failures), encoding='utf8')
            cloud.safe_event('training_partial', completed_roles=sorted(results), failed_roles=sorted(failures),
                             artifacts={r: value['artifact'] for r, value in results.items()})
            return 1
        cloud.safe_event('dual_training_completed', artifacts={r: value['artifact'] for r, value in results.items()},
                         dedicated_pods=True, tensor_verification_pending=True, production_promotion=False)
        return 0
    finally:
        errors = []
        for role in attempted - closed:
            try:
                close(role)
            except Exception:
                errors.append(role)
        if errors:
            raise RuntimeError('one or more dedicated GPUs still need cleanup')
        cloud.safe_event('cost_estimate_upper', krw=str(ledger.spent_krw), budget_krw=int(ledger.policy.budget_krw))


if __name__ == '__main__':
    def terminate(_signum, _frame):
        raise SystemExit(143)
    signal.signal(signal.SIGTERM, terminate)
    try:
        raise SystemExit(main())
    except Exception as error:
        cloud.safe_event('failed', error_class=type(error).__name__, tensor_verification_pending=True)
        raise SystemExit(1)

"""One dedicated, bounded Pod per selected model; cumulative batch accounting."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import sys
import tempfile
import time
import traceback
from urllib.parse import parse_qs, urlsplit

import private_corpus_run as cloud
from private_pod_train import (MAX_ARTIFACT_RAW_BYTES, artifact_payloads, decode_payload,
                               rows_from_payload, verify_partitions)
from training_budget import BudgetLedger, BudgetPolicy, PodQuote, reserve_run, settle_run, should_stop, validate_observed_pod


def validate_source_lineage(rows, role):
    """Require observed chat exchanges or traceable HaslaLab educational sources."""
    for row in rows:
        meta = row.get('metadata') or {}
        if role == 'chat':
            author_filter = meta.get('author_filter') or {}
            source = urlsplit(str(meta.get('source_url', '')))
            if source.hostname == 'gall.dcinside.com' and parse_qs(source.query).get('id') == ['physicalscience']:
                raise ValueError('the user excluded the 물리학 gallery; 물리학과 is a different allowed gallery')
            if (meta.get('derivation') != 'paraphrase_observed_exchange'
                    or meta.get('reconstructed') is not True
                    or meta.get('old_synthetic_seed') is not False
                    or not meta.get('observed_reply_link')
                    or not meta.get('reviewer')
                    or meta.get('review_status') != 'approved'
                    or not meta.get('collected_at')
                    or not isinstance(author_filter, dict)
                    or author_filter.get('policy_version') != 'exclude-bugiu-v1'
                    or author_filter.get('post_author_checked') is not True
                    or author_filter.get('selected_reply_authors_checked') is not True
                    or author_filter.get('reply_branch_checked') is not True
                    or author_filter.get('excluded_author_present') is not False
                    or not re.fullmatch(r'https://(?:orbi\.kr/[0-9]+|gall\.dcinside\.com/(?:m?gallery/)?board/view/\?id=[A-Za-z0-9_]+&no=[0-9]+)', str(meta.get('source_url', '')))
                    or any(not re.fullmatch(r'[a-f0-9]{64}', str(meta.get(key, '')))
                           for key in ('question_sha256', 'answer_sha256'))):
                raise ValueError('Gemma requires source-grounded exchanges with the current author exclusion checks')
        else:
            drive = meta.get('drive_provenance')
            drive_ok = (isinstance(drive, dict) and bool(drive.get('drive_file_id'))
                        and re.fullmatch(r'[a-f0-9]{64}', str(drive.get('local_original_pdf_sha256', '')))
                        and bool(meta.get('page_number')) and meta.get('scan_suspect') is not True)
            source = meta.get('haslalab_provenance')
            native_ok = (isinstance(source, dict) and bool(source.get('source_id'))
                         and bool(source.get('source_family'))
                         and re.fullmatch(r'[a-f0-9]{64}', str(source.get('local_source_sha256', '')))
                         and source.get('extraction') in ('native', 'canonical_body')
                         and bool(source.get('original_locator') or meta.get('page_number'))
                         and meta.get('target_role') == 'solver' and bool(meta.get('group_id'))
                         and meta.get('scan_suspect') is False
                         and meta.get('content_type') in ('textbook', 'competition_problem', 'school_problem',
                                                          'solution', 'research_paper'))
            if not drive_ok and not native_ok:
                raise ValueError('QwQ requires native text or canonical source bodies with checked provenance')


def load_inputs(env):
    manifest = json.loads(env['HASLA_DUAL_MANIFEST'])
    if not isinstance(manifest, dict) or not isinstance(manifest.get('roles'), dict):
        raise ValueError('invalid model manifest')
    selected = manifest.get('selected_roles', ['chat', 'solver'])
    if (not isinstance(selected, list) or not 1 <= len(selected) <= 2
            or any(role not in ('chat', 'solver') for role in selected) or len(set(selected)) != len(selected)):
        raise ValueError('invalid selected model roles')
    if any(role not in manifest['roles'] for role in selected):
        raise ValueError('selected model input is missing')
    for role in selected:
        resource_settings(manifest, role)
    for key in ('train_script_sha256', 'role_config_sha256', 'pod_script_sha256', 'dual_pod_sha256'):
        if not re.fullmatch(r'[a-f0-9]{64}', manifest.get(key, '')):
            raise ValueError('pinned code checksums are required')
    if not re.fullmatch(r'[0-9a-f]{40}', env.get('GITHUB_SHA', '')):
        raise ValueError('a pinned public commit is required')
    payloads = {}
    for role in selected:
        spec = manifest['roles'][role]
        expected = 'chat' if role == 'chat' else 'text'
        if spec.get('format') != expected:
            raise ValueError('role and corpus formats do not match')
        if spec.get('input_artifact'):
            reference = spec['input_artifact']
            if (not isinstance(reference, str) or not re.fullmatch(
                    r'[A-Za-z0-9_.-]+/hasla-ai-private-training/[A-Za-z0-9_.-]+:v[0-9]+', reference)):
                raise ValueError('immutable private staged input is required')
            for split in ('train', 'validation'):
                item = spec.get(split, {})
                if (type(item.get('records')) is not int or not 1 <= item['records'] <= 1000000
                        or type(item.get('raw_bytes')) is not int or not 0 < item['raw_bytes'] <= MAX_ARTIFACT_RAW_BYTES
                        or not re.fullmatch(r'[a-f0-9]{64}', str(item.get('raw_sha256', '')))):
                    raise ValueError('invalid private staged input inventory')
            payloads[role] = {'HASLA_INPUT_ARTIFACT': reference}
            continue
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


def verify_staged_inputs(manifest, payloads, env, entity):
    """Validate full private artifact bytes on CPU before any paid Pod is created."""
    external = [role for role in manifest['selected_roles'] if manifest['roles'][role].get('input_artifact')]
    if not external:
        return
    from private_verify_adapter import quiet_sdk
    with tempfile.TemporaryDirectory(prefix='hasla-staged-input-') as directory:
        with quiet_sdk(Path(directory)):
            import wandb
            private = {'entity': entity, 'project': cloud.PROJECT, 'access': 'PRIVATE',
                       'base_url': 'https://api.wandb.ai'}
            for role in external:
                spec = manifest['roles'][role]
                settings = {'WANDB_API_KEY': env['WANDB_API_KEY'], 'WANDB_ENTITY': entity,
                            'WANDB_PROJECT': cloud.PROJECT, 'ROLE': role, 'HASLA_DATA_FORMAT': spec['format'],
                            'HASLA_INPUT_ARTIFACT': spec['input_artifact'],
                            'HASLA_DATA_SHA256': spec['train']['raw_sha256'],
                            'HASLA_VALIDATION_SHA256': spec['validation']['raw_sha256']}
                training_raw, validation_raw = artifact_payloads(settings, Path(directory) / role, wandb, private)
                rows = []
                for split, raw in (('train', training_raw), ('validation', validation_raw)):
                    if raw is None or len(raw) != spec[split]['raw_bytes']:
                        raise ValueError('private staged input byte count mismatch')
                    values = rows_from_payload(raw, split, spec['format'])
                    if len(values) != spec[split]['records']:
                        raise ValueError('private staged input row count mismatch')
                    validate_source_lineage(values, role)
                    rows.append(values)
                verify_partitions(*rows)


def resource_settings(manifest, role):
    """Validate one immutable role's budget, GPU preferences and total Pod time."""
    if role not in ('chat', 'solver') or not isinstance(manifest['roles'].get(role), dict):
        raise ValueError('invalid selected model resources')
    policy = BudgetPolicy(fx_krw_per_usd_upper=2000, budget_krw=manifest.get('budget_krw'),
        authorized_budget_krw=manifest.get('authorized_budget_krw', 30000), reserve_krw=5000, tax_multiplier='1.15')
    if 'prior_upper_krw' not in manifest:
        raise ValueError('cumulative prior budget is required')
    ledger = BudgetLedger(policy, prior_spend_krw=manifest['prior_upper_krw'])
    spec = manifest['roles'][role]
    maximum = 1800 if role == 'chat' else 14400
    seconds = spec.get('runtime_seconds', 1800 if role == 'chat' else 3600)
    if type(seconds) is not int or not 660 <= seconds <= maximum:
        raise ValueError('role runtime must include setup/upload and stay within its time ceiling')
    default_gpus = [*cloud.GPU_IDS[2:], cloud.GPU_IDS[1], cloud.GPU_IDS[0]] if role == 'chat' else list(cloud.GPU_IDS)
    gpu_ids = spec.get('gpu_ids', default_gpus)
    if (not isinstance(gpu_ids, list) or not gpu_ids
            or any(not isinstance(gpu, str) or gpu not in cloud.GPU_IDS for gpu in gpu_ids)
            or len(set(gpu_ids)) != len(gpu_ids)):
        raise ValueError('only configured training GPUs may be preferred')
    quote = PodQuote(gpu_usd_per_hour_upper=spec.get('gpu_usd_per_hour_upper', 4), container_disk_gb=200, volume_disk_gb=0)
    if quote.gpu_usd_per_hour_upper > 4:
        raise ValueError('role GPU hourly ceiling exceeds USD4')
    return ledger, quote, seconds, gpu_ids


def verify_pinned_scripts(manifest, commit):
    files = {'train_script_sha256': 'train_lora.py', 'role_config_sha256': 'role_config.py',
             'pod_script_sha256': 'private_pod_train.py', 'dual_pod_sha256': 'private_dual_pod.py'}
    for key, filename in files.items():
        url = f'https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io/{commit}/tools/ai/{filename}'
        response = cloud.requests.get(url, timeout=20)
        if (response.status_code != 200 or len(response.content) > 256 * 1024
                or hashlib.sha256(response.content).hexdigest() != manifest[key]):
            raise ValueError('pinned public code checksum mismatch: ' + filename)
    cloud.safe_event('public_code_verified', files=len(files), commit=commit)


def main():
    env = os.environ
    cloud.E = env
    if '--cleanup' in sys.argv:
        return cloud.cleanup()
    manifest, payloads = load_inputs(env)
    selected_roles = manifest.get('selected_roles', ['chat', 'solver'])
    if len(selected_roles) != 1 and env.get('HASLA_PREFLIGHT_ONLY') != 'true':
        raise ValueError('each paid Pod must select exactly one model role')
    role = selected_roles[0]
    ledger, quote, run_seconds, preferred_gpus = resource_settings(manifest, role)
    for key in ('RUNPOD_API_KEY', 'WANDB_API_KEY', 'HF_TOKEN'):
        if not env.get(key):
            raise ValueError('missing required training credential')
    verify_pinned_scripts(manifest, env['GITHUB_SHA'])
    run_id = cloud.PREFIX + env['GITHUB_RUN_ID']
    if any(str(p.get('name', '')).startswith(cloud.PREFIX) for p in cloud.runpod('GET', '/pods')):
        raise RuntimeError('an earlier private Pod remains; confirm cleanup before another role')
    selected_gpu = cloud.capacity_preflight(preferred_gpu_ids=preferred_gpus,
                                            hourly_ceiling=quote.gpu_usd_per_hour_upper)
    if selected_gpu not in preferred_gpus:
        raise ValueError('selected GPU differs from the frozen role policy')
    bases = {'chat': 'google/gemma-4-26B-A4B-it', 'solver': 'Qwen/QwQ-32B'}
    for role in selected_roles:
        model = bases[role]
        response = cloud.requests.head(f'https://huggingface.co/{model}/resolve/main/config.json',
            headers={'Authorization': 'Bearer ' + env['HF_TOKEN']}, allow_redirects=True, timeout=20)
        if not response.ok:
            cloud.safe_event('model_access_failed', role=role, http_status=response.status_code)
            raise RuntimeError('base model access check failed')
    entity = cloud.private_project()
    verify_staged_inputs(manifest, payloads, env, entity)
    ledger = reserve_run(ledger,
                         run_id, 'dual' if len(selected_roles) == 2 else selected_roles[0], quote,
                         time.monotonic(), run_seconds, run_seconds)
    plan = ledger.runs[-1].plan
    if plan.run_seconds < 660:
        raise ValueError('remaining budget cannot cover setup, training and upload')
    budget = int(ledger.policy.budget_krw)
    cloud.safe_event('dual_preflight', roles={r: {'format': s['format'], 'training_records': s['train']['records'],
        'validation_records': s['validation']['records']} for r, s in manifest['roles'].items() if r in selected_roles},
        selected_roles=selected_roles, dedicated_pod=True, budget_krw=budget,
        prior_upper_krw=str(ledger.prior_spend_krw), reserved_upper_krw=str(plan.reserved_krw), runtime_seconds=plan.run_seconds)
    if env.get('HASLA_PREFLIGHT_ONLY') == 'true':
        return 0
    jobs = []
    for role in selected_roles:
        spec = manifest['roles'][role]
        if spec.get('input_artifact'):
            input_ref = payloads[role]
            cloud.safe_event('private_input_ready', artifact=spec['input_artifact'], raw_files=2, public=False)
        else:
            input_ref = cloud.publish_private_input(entity, run_id + '-' + role, {**spec, 'role': role}, payloads[role])
        jobs.append({'role': role, 'format': spec['format'], 'run': run_id + '-' + role,
                     'input_artifact': input_ref['HASLA_INPUT_ARTIFACT'],
                     'training_sha256': spec['train']['raw_sha256'],
                     'validation_sha256': spec['validation']['raw_sha256'],
                     'runtime_seconds': plan.run_seconds - 600})
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
    command = 'bash -lc ' + shlex.quote(f'timeout --signal=TERM --kill-after=30s {plan.run_seconds - 120}s bash -lc ' + shlex.quote(start))
    pod, attempted, results, failures = None, False, {}, {}
    try:
        attempted = True
        cloud.safe_event('gpu_request', api='rest_v2', gpu=selected_gpu, roles=selected_roles,
                         private_environment_bytes=sum(len(v) for v in pod_env.values()))
        pod = cloud.graphql_create_pod(run_id, pod_env, command, gpu_id=selected_gpu)
        pod = cloud.runpod('GET', '/pods/' + pod['id'])
        validate_observed_pod(plan, pod)
        if (pod.get('gpu') or {}).get('id') != selected_gpu:
            raise ValueError('created GPU differs from the selected role GPU')
        cloud.safe_event('pod_started', pod_id=pod['id'], hourly_usd=pod['costPerHr'], roles=selected_roles)
        last_roles = []
        while not should_stop(plan, time.monotonic()):
            for job in jobs:
                if job['role'] in results or job['role'] in failures:
                    continue
                remaining = float(plan.deadline_monotonic) - time.monotonic()
                if remaining <= 0:
                    break
                row = cloud.result_for(entity, job['run'], timeout=min(10, remaining))
                if row:
                    if row.get('status') != 'uploaded':
                        cloud.safe_event('role_failed', role=job['role'], stage=row.get('stage'), error_code=row.get('error_code'))
                        failures[job['role']] = row
                    else:
                        results[job['role']] = row
            if sorted(results) != last_roles:
                last_roles = sorted(results)
                cloud.safe_event('roles_completed', roles=last_roles)
            if len(results) + len(failures) == len(jobs):
                if failures:
                    cloud.safe_event('training_partial', completed_roles=sorted(results), failed_roles=sorted(failures),
                                     artifacts={role: row['artifact'] for role, row in results.items()})
                    Path('private-dual-result.json').write_text(json.dumps(results, ensure_ascii=True), encoding='utf8')
                    Path('private-dual-failures.json').write_text(json.dumps(failures, ensure_ascii=True), encoding='utf8')
                    return 1
                cloud.safe_event('dual_training_completed', artifacts={r: x['artifact'] for r, x in results.items()},
                                 weights_updated=True, production_promotion=False)
                Path('private-dual-result.json').write_text(json.dumps(results, ensure_ascii=True), encoding='utf8')
                return 0
            remaining = float(plan.deadline_monotonic) - time.monotonic()
            if remaining <= 0:
                break
            info = cloud.runpod('GET', '/pods/' + pod['id'], request_timeout=min(10, remaining))
            validate_observed_pod(plan, info)
            if (info.get('gpu') or {}).get('id') != selected_gpu:
                raise ValueError('observed GPU differs from the selected role GPU')
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
                cloud.safe_event('cost_estimate_upper', krw=str(ledger.spent_krw), budget_krw=budget)
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

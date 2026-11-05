"""One explicitly budgeted A40 comparison; no training, corpus or promotion.

The child receives no provider credential. A creation is never retried; exact
ownership and protected preexisting IDs govern every cleanup attempt.
"""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import sys
import time

import private_corpus_run as cloud
import private_resume_adapter as resume
from private_dedicated_run import verify_reserved_funding
from role_config import get_role_config
from training_budget import (BudgetLedger, BudgetPolicy, PodQuote, reserve_run,
                             settle_run, validate_observed_pod)

REQUIRED_SCRIPTS = ('private_qwq_gpu_run.py', 'private_qwq_gpu_eval.py',
    'private_qwq_comparison.py', 'private_resume_adapter.py', 'private_verify_adapter.py',
    'role_config.py', 'private_corpus_run.py', 'private_pod_train.py', 'training_budget.py',
    'private_dedicated_run.py', 'private_dual_run.py')
CHILD_SCRIPTS = ('private_qwq_gpu_eval.py', 'private_qwq_comparison.py',
                 'private_resume_adapter.py', 'private_verify_adapter.py', 'role_config.py')
ENTITY = 'mimgyuson-haslaedu'
PREFIX = 'hasla-private-qwq-eval-'
STATE = Path('private-qwq-gpu-eval-state.json')
CASE_IDS = {'momentum_energy', 'isolated_capacitor', 'photoelectric', 'incline_friction',
            'external_resistor_heat', 'orbital_mass', 'stellar_radius', 'missing_official_rubric'}
SOURCE_ADAPTER = {'kind': 'private_adapter_continuation', 'version': 1, 'role': 'solver',
    'base_model': 'Qwen/QwQ-32B', 'rank': 16, 'source_training_run_id': '41931877157',
    'prior_verification_run_id': '41943069583', 'entity': ENTITY,
    'artifact': ENTITY + '/' + resume.PROJECT + '/hasla-private-books-41931877157-solver-lora:v0',
    'files': [{'name': 'adapter_config.json', 'bytes': 1322,
               'sha256': '1954f97392fb7b1873ad5f399febbb894a79a387b5dbf98785434d850a02801e'},
              {'name': 'adapter_model.safetensors', 'bytes': 536991984,
               'sha256': '5b4c2e755930a30298927cdf905fd158c4745473eea7c41f87630183729d0112'}],
    'adapter_inventory_sha256': 'c295c61015ebc1d1b1e32cfe7f535c1336ba536c4902645146f15a5f0df5de8f'}
ADAPTER_SPEC = SOURCE_ADAPTER
IMAGE = 'unsloth/unsloth@sha256:9e12ff9201f4753ae7290ba45b0ca681a010575d925a53dffd13b8a7829e295b'
PYTHON = '/opt/unsloth-venv/bin/python'
STARTUP_CAP_SECONDS = 1500
FIXED = {'version': 3, 'kind': 'private_qwq_gpu_evaluation_v3', 'authorized_total': 100000,
    'previous_eval_upper_krw': 1508, 'prior_upper_krw': 73049, 'reserve_krw': 5000, 'additional_limit_krw': 1492,
    'reserved_upper_krw': 1457, 'runtime_seconds': 3500, 'child_runtime_seconds': 2700,
    'cleanup_grace_seconds': 120, 'gpu_id': 'NVIDIA A40', 'gpu_count': 1,
    'gpu_usd_per_hour_upper': '0.60', 'container_disk_gb': 200, 'volume_gb': 0,
    'optimizer_steps': 0}


class EvaluationError(RuntimeError):
    pass


def require(value, code):
    if not value:
        raise EvaluationError(code)


def evaluation_plan():
    from private_qwq_gpu_eval import evaluation_plan as factory
    return factory()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def comparison_plan_sha256():
    return hashlib.sha256(canonical(evaluation_plan())).hexdigest()


def validate_manifest(manifest):
    keys = set(FIXED) | {'code_commit', 'launch_id', 'script_sha256', 'source_adapter',
                        'case_set_sha256', 'comparison_plan_sha256'}
    require(type(manifest) is dict and set(manifest) == keys, 'manifest_fields_invalid')
    for key, expected in FIXED.items():
        require(type(manifest[key]) is type(expected) and manifest[key] == expected, 'manifest_fixed_policy_mismatch')
    require(type(manifest['code_commit']) is str and re.fullmatch('[0-9a-f]{40}', manifest['code_commit']), 'manifest_commit_invalid')
    require(type(manifest['launch_id']) is str and re.fullmatch('[0-9a-f]{32}', manifest['launch_id']), 'manifest_launch_invalid')
    pins = manifest['script_sha256']
    require(type(pins) is dict and set(pins) == set(REQUIRED_SCRIPTS) and all(
        type(v) is str and re.fullmatch('[0-9a-f]{64}', v) for v in pins.values()), 'script_pins_invalid')
    checked = resume.validate_spec(manifest['source_adapter'], get_role_config('solver'))
    require(checked == SOURCE_ADAPTER, 'source_adapter_mismatch')
    plan = evaluation_plan()
    require(manifest['case_set_sha256'] == plan['comparison']['case_set_sha256'] and
            manifest['comparison_plan_sha256'] == hashlib.sha256(canonical(plan)).hexdigest(), 'comparison_plan_mismatch')
    ledger = budget_plan(manifest, 'manifest-validation', 0)
    require(int(ledger.reserved_krw) == 1457 and ledger.reserved_krw <= manifest['additional_limit_krw'],
            'additional_budget_exceeded')
    require(manifest['prior_upper_krw'] == 71541 + manifest['previous_eval_upper_krw']
            and manifest['additional_limit_krw'] == 3000 - manifest['previous_eval_upper_krw']
            and manifest['previous_eval_upper_krw'] + ledger.reserved_krw <= 3000, 'evaluation_cohort_budget_exceeded')
    return deepcopy(manifest)


def budget_plan(manifest, run_id, now):
    policy = BudgetPolicy(fx_krw_per_usd_upper=2000, budget_krw=manifest['authorized_total'],
        authorized_budget_krw=manifest['authorized_total'], reserve_krw=manifest['reserve_krw'], tax_multiplier='1.15')
    ledger = BudgetLedger(policy, prior_spend_krw=manifest['prior_upper_krw'])
    quote = PodQuote(gpu_usd_per_hour_upper=manifest['gpu_usd_per_hour_upper'],
                     container_disk_gb=200, volume_disk_gb=0, gpu_count=1)
    return reserve_run(ledger, run_id, 'solver', quote, now, 3500, 3500, cleanup_grace_seconds=120)


def inventory(pods):
    require(isinstance(pods, list), 'pod_inventory_unknown')
    identities = set()
    for pod in pods:
        require(isinstance(pod, dict) and type(pod.get('id')) is str and pod['id']
                and pod['id'] not in identities and type(pod.get('name')) is str, 'pod_inventory_unknown')
        identities.add(pod['id'])
        require(not pod['name'].startswith('hasla-private-'), 'existing_task_pod_present')
    return identities


class Services:
    def __init__(self, env):
        self.env = env
        cloud.E = env

    def pods(self):
        with resume._quiet():
            return cloud.runpod('GET', '/pods')

    def private(self):
        with resume._quiet():
            value = cloud.wandb_query('query($e:String!,$p:String!){project(name:$p,entityName:$e){name access}}',
                                      {'e': ENTITY, 'p': resume.PROJECT}).get('project')
        require(isinstance(value, dict) and value.get('name') == resume.PROJECT and value.get('access') == 'PRIVATE',
                'private_project_required')

    def source(self):
        self.private()
        with resume._quiet():
            import wandb
            api = wandb.Api(api_key=self.env['WANDB_API_KEY'], timeout=30)
            artifact = api.artifact(SOURCE_ADAPTER['artifact'], type='lora')
            require(artifact.qualified_name == SOURCE_ADAPTER['artifact'] and artifact.state == 'COMMITTED'
                    and artifact.type == 'lora' and not getattr(artifact, 'is_link', False), 'source_artifact_invalid')
            metadata = artifact.metadata
            require(isinstance(metadata, dict) and metadata.get('private') is True
                    and metadata.get('role') == 'solver' and metadata.get('base_model') == 'Qwen/QwQ-32B'
                    and type(metadata.get('rank')) is int and metadata['rank'] == 16
                    and metadata.get('adapter_sha256') == SOURCE_ADAPTER['adapter_inventory_sha256']
                    and metadata.get('adapter_inventory_sha256', SOURCE_ADAPTER['adapter_inventory_sha256'])
                        == SOURCE_ADAPTER['adapter_inventory_sha256'], 'source_metadata_invalid')
            entries = artifact.manifest.entries
            require(isinstance(entries, dict) and set(entries) == set(resume.FILES), 'source_files_invalid')
            for row in SOURCE_ADAPTER['files']:
                resume._entry(entries[row['name']], row)
        self.private()

    def quote(self):
        with resume._quiet():
            selected = cloud.capacity_preflight(['NVIDIA A40'], Decimal('0.60'))
            catalog = cloud.runpod('GET', '/catalog/gpus?include=AVAILABILITY&product=POD&count=1&cloud=SECURE&minCudaVersion=12.8')
        require(selected == 'NVIDIA A40', 'capacity_gpu_mismatch')
        rows = [r for r in catalog.get('gpus', []) if r.get('id') == 'NVIDIA A40']
        require(len(rows) == 1, 'capacity_quote_unknown')
        price = Decimal(str((rows[0].get('price') or {}).get('secure')))
        require(price.is_finite() and 0 < price <= Decimal('0.60')
                and str(rows[0].get('availability')).upper() in ('LOW', 'MEDIUM', 'HIGH'), 'capacity_unavailable')
        return price

    def funding(self, ledger):
        with resume._quiet():
            verify_reserved_funding(ledger)

    def create(self, name, env, command):
        with resume._quiet():
            # Preserve the official image entrypoint: it initializes the fixed venv.
            return cloud.runpod('POST', '/pods', json={
                'name': name, 'cloud': 'SECURE',
                'gpu': {'id': 'NVIDIA A40', 'count': 1, 'minCudaVersion': '12.8'},
                'disk': 200, 'image': IMAGE, 'cmd': ['/bin/bash', '-lc', command],
                'ports': [], 'env': env, 'startSsh': False, 'startJupyter': False})

    def bootstrap(self, identity, timeout):
        """Read only fixed JSON markers, discarding every other container byte."""
        from private_qwq_gpu_eval import hard_wall
        response = None
        found = None
        stop = time.monotonic() + min(6, timeout)
        try:
            with hard_wall(max(1, min(6, timeout))), resume._quiet():
                response = cloud.requests.get(cloud.REST + '/pods/' + identity + '/logs',
                    params={'source': 'container', 'tail': 60}, stream=True,
                    headers={'Authorization': 'Bearer ' + self.env['RUNPOD_API_KEY']},
                    allow_redirects=False, timeout=(3, 3))
                if response.status_code != 200:
                    return None
                total, buffer, events = 0, b'', 0
                for chunk in response.iter_content(chunk_size=1024):
                    total += len(chunk)
                    if total > 65536 or time.monotonic() >= stop:
                        break
                    buffer += chunk
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        if not line.startswith(b'data:'):
                            continue
                        events += 1
                        if events > 64:
                            return found
                        try:
                            event = json.loads(line[5:])
                            if (isinstance(event, dict) and event.get('source') in ('container', 'stdout', 'stderr')
                                    and type(event.get('line')) is str):
                                marker = bootstrap_marker(event['line'])
                                if marker is not None:
                                    found = marker
                        except (ValueError, TypeError):
                            pass
                return found
        except Exception:
            return found
        finally:
            if response is not None:
                response.close()

    def reconcile(self, name):
        with resume._quiet():
            return cloud.reconcile_created_pods(name)

    def delete(self, pod_id):
        with resume._quiet():
            return cloud.delete_and_confirm(pod_id)

    def pod(self, identity, timeout):
        with resume._quiet():
            return cloud.runpod('GET', '/pods/' + identity, request_timeout=timeout)

    def summary(self, run_id, timeout):
        with resume._quiet():
            value = cloud.wandb_query('query($e:String!,$p:String!,$r:String!){project(name:$p,entityName:$e){run(name:$r){summaryMetrics}}}',
                {'e': ENTITY, 'p': resume.PROJECT, 'r': 'hasla-qwq-gpu-comparison-' + run_id}, timeout=timeout)
        row = (value.get('project') or {}).get('run') or {}
        result = row.get('summaryMetrics') or {}
        if isinstance(result, str):
            result = resume._json(result)
        return result if isinstance(result, dict) else {}


def identity(pod, state, plan):
    require(isinstance(pod, dict) and type(pod.get('id')) is str
            and re.fullmatch('[A-Za-z0-9_-]{1,64}', pod['id']) and pod['id'] not in state['preexisting_ids']
            and pod.get('name') == state['pod_name'], 'created_pod_identity_invalid')
    validate_observed_pod(plan, pod)
    require((pod.get('gpu') or {}).get('id') == 'NVIDIA A40'
            and pod.get('containerDiskInGb') == 200 and pod.get('volumeInGb') == 0,
            'observed_resources_mismatch')


def write_state(state, path):
    path.write_text(json.dumps(state, sort_keys=True), encoding='utf8')


def cleanup(env, services=None, *, state_path=STATE, emit=cloud.safe_event):
    if not state_path.exists():
        emit('private_qwq_gpu_cleanup', attempted=False, deletion_confirmed=True, matched_pods=0)
        return True
    state = resume._json(state_path.read_bytes())
    run_id = env.get('GITHUB_RUN_ID', '')
    require(state.get('run_id') == run_id and state.get('pod_name') == PREFIX + run_id
            and isinstance(state.get('preexisting_ids'), list), 'cleanup_state_invalid')
    if state.get('closed') is True:
        emit('private_qwq_gpu_cleanup', attempted=True, deletion_confirmed=True, matched_pods=0)
        return True
    services = services or Services(env)
    pods = state.get('owned_pods', [])
    if not pods and state.get('attempted'):
        pods = services.reconcile(state['pod_name'])
    require(isinstance(pods, list) and all(isinstance(p, dict) and p.get('name') == state['pod_name']
            and type(p.get('id')) is str and p['id'] not in state['preexisting_ids'] for p in pods), 'cleanup_scope_invalid')
    # Absence after a lost create response cannot prove that no Pod was created.
    confirmed = bool(pods) and all([services.delete(p['id']) for p in pods])
    if confirmed:
        state.update(closed=True, owned_pods=pods)
        write_state(state, state_path)
    emit('private_qwq_gpu_cleanup', attempted=True, matched_pods=len(pods), deletion_confirmed=confirmed,
         reservation_retained=not confirmed)
    return confirmed


def child_environment(manifest, env, run_id, deadline_unix):
    job = {'version': 1, 'kind': 'private_qwq_gpu_evaluation_job', 'run_id': run_id,
           'code_commit': manifest['code_commit'], 'runtime_seconds': manifest['child_runtime_seconds'],
           'base_model': 'Qwen/QwQ-32B', 'rank': 16, 'source_adapter': manifest['source_adapter'],
           'optimizer_steps': 0, 'script_sha256': {n: manifest['script_sha256'][n] for n in CHILD_SCRIPTS}}
    job['deadline_unix'] = deadline_unix
    return {'WANDB_API_KEY': env['WANDB_API_KEY'], 'WANDB_ENTITY': ENTITY,
            'WANDB_PROJECT': resume.PROJECT, 'WANDB_CONSOLE': 'off',
            'WANDB_DISABLE_CODE': 'true', 'UNSLOTH_SKIP_NOTEBOOK_SYNC': '1',
            'HASLA_QWQ_GPU_EVAL_JOB': canonical(job).decode()}


def pod_command(manifest):
    base = 'https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io/' + manifest['code_commit'] + '/tools/ai/'
    core = "from importlib.metadata import version; import json; from pathlib import Path; names=('torch','transformers','unsloth','unsloth_zoo','peft','bitsandbytes','trl'); "
    before = core + "Path('/workspace/qwq-eval-core.json').write_text(json.dumps({n:version(n) for n in names},sort_keys=True))"
    after = core + "assert json.loads(Path('/workspace/qwq-eval-core.json').read_text()) == {n:version(n) for n in names}"
    failed = '{"event":"private_qwq_gpu_bootstrap","stage":"failed","exit_code":%d}\\n'
    failure_trap = 'code=$?; trap - ERR; printf ' + shlex.quote(failed) + ' "$code"; sleep 120; exit "$code"'
    def stage(value):
        return 'printf ' + shlex.quote('{"event":"private_qwq_gpu_bootstrap","stage":"' + value + '"}\\n')
    commands = ['set -Eeuo pipefail', 'trap ' + shlex.quote(failure_trap) + ' ERR', stage('starting'),
        'mkdir -p /workspace/qwq-eval', 'cd /workspace/qwq-eval',
        'export PIP_DISABLE_PIP_VERSION_CHECK=1',
        PYTHON + ' -c ' + shlex.quote(before) + ' >/workspace/qwq-eval-core.log 2>&1',
        stage('sdk'),
        PYTHON + ' -m pip install -q wandb==0.31.0 >/workspace/qwq-eval-install.log 2>&1',
        stage('dependencies'),
        PYTHON + ' -c ' + shlex.quote(after) + ' >>/workspace/qwq-eval-core.log 2>&1',
        PYTHON + ' -c "import unsloth, bitsandbytes, peft, torch, wandb; assert torch.cuda.is_available(); assert torch.cuda.device_count() == 1; assert wandb.__version__ == \'0.31.0\'" >/workspace/qwq-eval-dependencies.log 2>&1',
        stage('source')]
    for name in CHILD_SCRIPTS:
        commands += ['curl -fsSL --max-time 60 ' + shlex.quote(base + name) + ' -o ' + shlex.quote(name),
                     'echo ' + shlex.quote(manifest['script_sha256'][name] + '  ' + name) + ' | sha256sum -c - >/dev/null']
    commands += [stage('worker'), PYTHON + ' -B private_qwq_gpu_eval.py >/workspace/qwq-eval-worker.log 2>&1',
                 stage('completed')]
    return 'timeout --signal=TERM --kill-after=30s 3200s /bin/bash -lc ' + shlex.quote('; '.join(commands))


def bootstrap_marker(line):
    if type(line) is not str or len(line) > 256:
        return None
    try:
        value = json.loads(line)
    except (ValueError, TypeError):
        return None
    if type(value) is not dict or value.get('event') != 'private_qwq_gpu_bootstrap':
        return None
    stage = value.get('stage')
    if type(stage) is not str:
        return None
    if stage == 'failed':
        if set(value) == {'event', 'stage', 'exit_code'} and type(value['exit_code']) is int and 1 <= value['exit_code'] <= 255:
            return {'stage': stage, 'exit_code': value['exit_code']}
    elif stage in {'starting', 'sdk', 'dependencies', 'source', 'worker', 'completed'} and set(value) == {'event', 'stage'}:
        return {'stage': stage}
    return None


def safe_progress(summary):
    value = summary.get('private_qwq_gpu_progress')
    if isinstance(value, str):
        value = resume._json(value)
    if not isinstance(value, dict):
        return None
    phases = {'initializing', 'source', 'downloading_source', 'loading', 'ready', 'evaluating',
              'uploading', 'uploaded', 'completed', 'failed'}
    require(value.get('phase') in phases, 'progress_phase_invalid')
    require(value.get('evaluation_only') is True and value.get('weights_updated') is False,
            'progress_execution_mode_invalid')
    result = {'phase': value['phase']}
    for field, maximum in (('completed_attempts', 16), ('paired_completed_cases', 8)):
        require(type(value.get(field)) is int and 0 <= value[field] <= maximum, 'progress_count_invalid')
        result[field] = value[field]
    if value.get('mode') in ('base', 'adapted'):
        result['mode'] = value['mode']
    require(value.get('case_id') is None or value['case_id'] in CASE_IDS, 'progress_case_invalid')
    if value.get('case_id') is not None:
        result['case_id'] = value['case_id']
    return result


def verify_script_pins(manifest, root=None):
    root = root or Path(__file__).parent
    for name, digest in manifest['script_sha256'].items():
        path = root / name
        require(path.is_file() and not path.is_symlink()
                and hashlib.sha256(path.read_bytes()).hexdigest() == digest, 'public_script_hash_mismatch')


def run(env, services=None, *, clock=time.monotonic, wall_clock=time.time, sleep=time.sleep,
        state_path=STATE, emit=cloud.safe_event, result_validator=None):
    raw = env.get('HASLA_QWQ_GPU_EVAL_MANIFEST', '')
    require(type(raw) is str and len(raw.encode()) <= 32768, 'manifest_missing_or_oversized')
    manifest = validate_manifest(resume._json(raw))
    run_id = env.get('GITHUB_RUN_ID', '')
    require(type(run_id) is str and re.fullmatch('[0-9]{1,32}', run_id), 'run_id_invalid')
    require(env.get('GITHUB_SHA') == manifest['code_commit'] and env.get('HASLA_QWQ_GPU_EVAL_LAUNCH_ID') == manifest['launch_id'], 'workflow_binding_mismatch')
    require(env.get('HASLA_PREFLIGHT_ONLY') in ('true', 'false'), 'preflight_flag_invalid')
    require(env.get('RUNPOD_API_KEY') and env.get('WANDB_API_KEY') and env.get('WANDB_ENTITY') == ENTITY,
            'required_credentials_missing')
    verify_script_pins(manifest)
    services = services or Services(env)
    protected = inventory(services.pods())
    services.source()
    quoted = services.quote()
    require(isinstance(quoted, Decimal) and quoted.is_finite() and 0 < quoted <= Decimal('0.60'), 'capacity_quote_invalid')
    ledger = budget_plan(manifest, PREFIX + run_id, clock())
    services.funding(ledger)
    plan = ledger.runs[0].plan
    emit('private_qwq_gpu_preflight', status='preflight_ready', run_id=run_id, code_commit=manifest['code_commit'],
        launch_id=manifest['launch_id'], manifest_sha256=hashlib.sha256(raw.encode()).hexdigest(),
        source_training_run_id=SOURCE_ADAPTER['source_training_run_id'],
        prior_verification_run_id=SOURCE_ADAPTER['prior_verification_run_id'],
        source_adapter_inventory_sha256=SOURCE_ADAPTER['adapter_inventory_sha256'],
        source_adapter_model_sha256=SOURCE_ADAPTER['files'][1]['sha256'], source_adapter_files=SOURCE_ADAPTER['files'],
        case_set_sha256=manifest['case_set_sha256'], comparison_plan_sha256=manifest['comparison_plan_sha256'],
        quoted_hourly_usd=str(quoted), remaining_budget_krw=int(ledger.available_krw),
        private_project_verified=True, source_metadata_verified=True, live_funding_sufficient=True,
        capacity_verified=True, existing_private_pods=0, gpu_creation_performed=False,
        container_image=IMAGE, startup_cap_seconds=STARTUP_CAP_SECONDS,
        **{k: manifest[k] for k in FIXED if k not in ('version', 'kind', 'optimizer_steps')})
    if env['HASLA_PREFLIGHT_ONLY'] == 'true':
        return {'status': 'preflight_ready'}
    require(not state_path.exists(), 'paid_attempt_state_exists')
    protected.update(inventory(services.pods()))
    services.private()
    services.funding(ledger)
    # Start the billable clock immediately before the one allowed create.
    ledger = budget_plan(manifest, PREFIX + run_id, clock())
    plan = ledger.runs[0].plan
    state = {'run_id': run_id, 'pod_name': PREFIX + run_id, 'preexisting_ids': sorted(protected),
             'attempted': True, 'owned_pods': [], 'closed': False}
    write_state(state, state_path)
    result, failure, cleanup_ok = None, None, False
    def interrupted(_signum, _frame):
        raise EvaluationError('evaluation_interrupted')
    previous_handlers = {}
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            previous_handlers[sig] = signal.signal(sig, interrupted)
        emit('private_qwq_gpu_requested', run_id=run_id, pod_name=state['pod_name'], gpu_id='NVIDIA A40',
             gpu_count=1, reserved_upper_krw=1457, runtime_seconds=3500)
        startup_started = clock()
        try:
            pod = services.create(state['pod_name'], child_environment(manifest, env, run_id,
                int(wall_clock()) + manifest['runtime_seconds'] - 300), pod_command(manifest))
        except Exception:
            matches = services.reconcile(state['pod_name'])
            require(len(matches) == 1, 'creation_outcome_unknown')
            pod = matches[0]
        identity(pod, state, plan)
        state['owned_pods'] = [{'id': pod['id'], 'name': pod['name']}]
        write_state(state, state_path)
        emit('private_qwq_gpu_started', run_id=run_id, pod_id=pod['id'], pod_name=pod['name'],
             gpu_id='NVIDIA A40', gpu_count=1, observed_hourly_usd=str(pod['costPerHr']))
        previous, previous_bootstrap = None, None
        worker_observed = False
        while clock() < float(plan.deadline_monotonic) - 120:
            remaining = float(plan.deadline_monotonic) - 120 - clock()
            identity(services.pod(pod['id'], max(1, min(20, remaining))), state, plan)
            summary = services.summary(run_id, max(1, min(20, remaining)))
            progress = safe_progress(summary)
            if progress:
                worker_observed = True
            if progress and progress != previous:
                emit('private_qwq_gpu_progress', run_id=run_id, **progress)
                previous = progress
            value = summary.get('private_qwq_gpu_result_json')
            if isinstance(value, str):
                value = resume._json(value)
            if isinstance(value, dict) and value.get('status') in ('uploaded', 'failed'):
                result = value
                break
            if not worker_observed:
                marker = services.bootstrap(pod['id'], max(1, min(6, remaining)))
                if marker is not None and marker != previous_bootstrap:
                    emit('private_qwq_gpu_bootstrap', run_id=run_id, **marker)
                    previous_bootstrap = marker
                require(marker is None or marker.get('stage') != 'failed', 'evaluation_bootstrap_failed')
                require(clock() - startup_started < STARTUP_CAP_SECONDS, 'evaluation_startup_unobserved')
            sleep(max(0, min(20, float(plan.deadline_monotonic) - 120 - clock())))
        require(result is not None, 'evaluation_parent_deadline')
        require(result.get('status') == 'uploaded', 'evaluation_child_failed')
        # The worker owns strict final-only report projection and artifact proof.
        if result_validator is None:
            from private_qwq_gpu_eval import validate_result
            result_validator = validate_result
        result = result_validator(result, run_id)
        emit('private_qwq_gpu_evaluation', **{**result, 'run_id': run_id,
             'code_commit': manifest['code_commit'], 'launch_id': manifest['launch_id']})
        require(result.get('execution_status') in ('completed', 'partial'), 'evaluation_child_failed')
    except BaseException as error:
        failure = str(error) if isinstance(error, EvaluationError) else 'evaluation_parent_failed'
        emit('private_qwq_gpu_failed', run_id=run_id, failure_code=failure, reservation_retained=True)
    finally:
        try:
            cleanup_ok = cleanup(env, services, state_path=state_path, emit=emit)
        finally:
            for sig, previous_handler in previous_handlers.items():
                signal.signal(sig, previous_handler)
    if cleanup_ok:
        ledger = settle_run(ledger, PREFIX + run_id, clock(), deletion_confirmed=True)
        emit('private_qwq_gpu_cost', run_id=run_id, aggregate_upper_krw=int(ledger.spent_krw),
             run_upper_krw=int(ledger.spent_krw - ledger.prior_spend_krw), reserved_upper_krw=1457,
             authorized_total=100000, additional_limit_krw=1492, previous_eval_upper_krw=1508, deletion_confirmed=True)
    require(cleanup_ok, 'evaluation_cleanup_unconfirmed')
    require(failure is None, failure or 'evaluation_parent_failed')
    return result


def main():
    try:
        if sys.argv[1:] == ['--cleanup']:
            return 0 if cleanup(os.environ) else 1
        require(not sys.argv[1:], 'arguments_invalid')
        run(os.environ)
        return 0
    except Exception as error:
        cloud.safe_event('private_qwq_gpu_failed', failure_code=(str(error) if isinstance(error, EvaluationError)
                         else 'evaluation_parent_failed'))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

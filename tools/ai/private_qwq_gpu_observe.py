"""Fixed-target read-only status. No logs, model calls or mutations are emitted."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import time

import private_qwq_gpu_run as parent
import private_qwq_gpu_eval as worker
import private_resume_adapter as resume

TARGET = '41956885560'
TARGET_COMMIT = 'f0bdb62c28dd492a61afef15408b7e1698fee429'
POD_NAME = parent.PREFIX + TARGET
HELPER_PINS = {'private_qwq_gpu_run.py': 'ef0a1556848689a3caac04ac8d9006cc4c5fd4e6b4dee9b8ece14965b6c3d5d0', 'private_qwq_gpu_eval.py': '34c09c2a2db22f9b4c525030736e61039b6c2d72ddcc2d55d9bb888e635de0af', 'private_qwq_comparison.py': '280bfeef08d8bd9d26feddc784cf4724687373ae4c186302bc0d171b103298db', 'private_resume_adapter.py': 'e52f9e5c31d938c98b7f3215761e3a3ccee616c645b74bd4cfa899cb34b551af', 'private_verify_adapter.py': 'e349889bbbd25fc5aa80ff32f43c2a3911a3f21ca0fd6f8b530d9b82142063a9', 'role_config.py': 'fde4850efcb0002d3458772956fcf61398c705814e1d6534981404ae495eac03', 'private_corpus_run.py': '8fdbdfa9748f0d2c526cb4212b9b033878ec2847625adefc27091d66f0319888', 'private_pod_train.py': '52e40d98d532b2e4bf0ab686f65ad72ad5286f866b2146cc2cff10c65efaaef5', 'training_budget.py': '6727d8089e55289b89c6e750820ed3275b76fa5a991b324c089251c58d17c46f', 'private_dedicated_run.py': 'a62082d48d415197701397aea9d494793c18345919ab1649d1566a370a514963', 'private_dual_run.py': 'ec3c8e586ebc8f252ee1cdfbc0d4e619f60d1f6209bc07f2172d84cbfe70f49b'}
EXCEPTIONS = ('ModuleNotFoundError', 'ImportError', 'RuntimeError', 'MemoryError',
              'AssertionError', 'PermissionError', 'TimeoutError', 'CUDAOutOfMemoryError')


def system_signal(line):
    if not isinstance(line, str):
        return None
    text = line[:8192]
    lower = text.lower()
    code = None
    for words, candidate in ((('failed to pull', 'pull access denied', 'image pull failed'), 'image_pull_failed'),
        (('container exited',), 'container_exited'), (('runtime error', 'out of memory', 'failed to start'), 'runtime_error'),
        (('container started',), 'container_started'), (('starting container',), 'container_starting'),
        (('pull complete', 'download complete', 'image is up to date'), 'image_ready'),
        (('pulling image', 'pulling', 'downloading'), 'pulling_image')):
        if any(word in lower for word in words):
            code = candidate
            break
    result = {'code': code} if code else {}
    error = next((name for name in EXCEPTIONS if re.search(r'\b' + name + r'\b', text)), None)
    if error:
        result['exception_type'] = error
    exit_code = re.search(r'(?i)\bexit(?:ed)?(?:\s+with)?(?:\s+code|\s+status)?\s*[:=]?\s+([0-9]{1,3})\b', text)
    if exit_code and 0 <= int(exit_code[1]) <= 255:
        result['exit_code'] = int(exit_code[1])
    return result or None


def system_status(pod, env, *, get=None, clock=time.monotonic):
    """Only system-source SSE, at most six seconds/64 KiB/64 events, RAM only."""
    get = get or parent.cloud.requests.get
    response, old_handler = None, None
    stages, total, events = [], 0, 0
    deadline = clock() + 6
    result = {'state': 'unavailable', 'signals': []}
    try:
        if hasattr(signal, 'setitimer'):
            def expired(*_):
                raise TimeoutError()
            old_handler = signal.signal(signal.SIGALRM, expired)
            signal.setitimer(signal.ITIMER_REAL, 6)
        with resume._quiet():
            response = get(parent.cloud.REST + '/pods/' + pod['id'] + '/logs',
                params={'source': 'system', 'tail': 60}, stream=True, allow_redirects=False,
                timeout=(3, 3), headers={'Authorization': 'Bearer ' + env['RUNPOD_API_KEY']})
            if response.status_code != 200:
                return result
            for raw in response.iter_lines(chunk_size=1024):
                total += len(raw)
                if clock() >= deadline or total > 65536 or events >= 64:
                    break
                if not raw.startswith(b'data:'):
                    continue
                try:
                    value = json.loads(raw[5:])
                except (ValueError, UnicodeError):
                    continue
                events += 1
                if isinstance(value, dict) and value.get('source') == 'system':
                    stage = system_signal(value.get('line'))
                    if stage and stage not in stages:
                        stages.append(stage)
        result = {'state': 'observed' if stages else 'no_known_signal', 'signals': stages, 'events_read': events}
    except Exception:
        result = {'state': 'partial' if stages else 'unavailable', 'signals': stages, 'events_read': events}
    finally:
        if response is not None:
            response.close()
        if old_handler is not None:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
    return result


def numeric(value, maximum):
    return value if type(value) in (int, float) and math.isfinite(value) and 0 <= value <= maximum else None


def pod_projection(pod):
    parent.require(isinstance(pod, dict) and pod.get('name') == POD_NAME
        and type(pod.get('id')) is str and re.fullmatch('[A-Za-z0-9_-]{1,64}', pod['id']), 'unexpected_target_pod')
    plan = parent.budget_plan(parent.FIXED, 'readonly-observation', 0).runs[0].plan
    parent.validate_observed_pod(plan, pod)
    parent.require((pod.get('gpu') or {}).get('id') == 'NVIDIA A40', 'unexpected_target_gpu')
    status = pod.get('desiredStatus')
    safe = {'id': pod['id'], 'name': POD_NAME, 'gpu_id': 'NVIDIA A40', 'gpu_count': 1,
        'hourly_usd': str(pod['costPerHr']), 'status': status if status in
        {'RUNNING', 'STOPPED', 'EXITED', 'TERMINATED', 'CREATED', 'PENDING', 'STARTING'} else 'unknown'}
    runtime = pod.get('runtime')
    if isinstance(runtime, dict):
        uptime = numeric(runtime.get('uptimeInSeconds', runtime.get('uptime')), 1000000)
        if uptime is not None:
            safe['uptime_seconds'] = uptime
        gpus = runtime.get('gpus')
        if isinstance(gpus, list) and len(gpus) == 1 and isinstance(gpus[0], dict):
            for field, key, alternate in (('gpu_util_percent', 'util', 'gpuUtilPercent'),
                                           ('memory_util_percent', 'memoryUtil', 'memoryUtilPercent')):
                value = numeric(gpus[0].get(key, gpus[0].get(alternate)), 100)
                if value is not None:
                    safe[field] = value
    return safe


def observe(env, *, services=None, system=system_status):
    for name, digest in HELPER_PINS.items():
        parent.require(hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() == digest,
                       'frozen_helper_pin_mismatch')
    services = services or parent.Services(env)
    event = {'event': 'private_qwq_gpu_observation', 'target_run_id': TARGET,
        'target_code_commit': TARGET_COMMIT, 'provider_read_succeeded': False,
        'absence_proven': False, 'pod': None, 'private_project_verified': False,
        'progress': None, 'result': None, 'bootstrap': None, 'failure_codes': [],
        'gpu_creation_performed': False, 'pod_deletion_performed': False, 'model_calls': 0}
    try:
        rows = services.pods()
        parent.require(isinstance(rows, list) and all(isinstance(p, dict) for p in rows), 'inventory_unknown')
        matches = [p for p in rows if p.get('name') == POD_NAME]
        parent.require(len(matches) <= 1, 'duplicate_target_pods')
        event['provider_read_succeeded'] = True
        if matches:
            listed = matches[0]
            # The list payload can omit runtime. Only the same exact Pod's GET
            # response may supply health data; never widen the name/ID scope.
            pod_projection(listed)
            detail = services.pod(listed['id'], 20)
            parent.require(isinstance(detail, dict) and detail.get('id') == listed['id']
                           and detail.get('name') == POD_NAME, 'pod_detail_identity_changed')
            event['pod'] = pod_projection(detail)
            event['pod_source'] = 'exact_id_detail'
            event['system'] = system(detail, env)
            marker = services.bootstrap(detail['id'], 6)
            if marker is not None:
                event['bootstrap'] = parent.bootstrap_marker(json.dumps({'event': 'private_qwq_gpu_bootstrap', **marker}))
    except Exception:
        event['failure_codes'].append('provider_or_resource_observation_unavailable')
    try:
        services.private()
        event['private_project_verified'] = True
        summary = services.summary(TARGET, 20)
        event['progress'] = parent.safe_progress(summary)
        raw = summary.get('private_qwq_gpu_result_json')
        if isinstance(raw, str):
            raw = resume._json(raw)
        if raw is not None:
            event['result'] = worker.validate_result(raw, TARGET)
    except Exception:
        event['failure_codes'].append('private_summary_or_result_unavailable')
    event['initialization_observed'] = event['progress'] is not None or event['result'] is not None
    event['no_progress_does_not_prove_bootstrap_failure'] = True
    return event


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target-run-id', default=TARGET)
    args = parser.parse_args(argv)
    try:
        parent.require(args.target_run_id == TARGET, 'fixed_target_required')
        parent.require(os.environ.get('RUNPOD_API_KEY') and os.environ.get('WANDB_API_KEY')
                       and os.environ.get('WANDB_ENTITY') == parent.ENTITY, 'readonly_credentials_missing')
        result = observe(os.environ)
        print(json.dumps(result, ensure_ascii=True, allow_nan=False))
        return 0 if not result['failure_codes'] else 1
    except Exception:
        print(json.dumps({'event': 'private_qwq_gpu_observation_failed', 'target_run_id': TARGET,
            'failure_code': 'fixed_observer_setup_failed', 'gpu_creation_performed': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Run selected private GPU roles sequentially, preserving their explicit order."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request


def role_jobs(env):
    jobs = json.loads(env['HASLA_ROLE_JOBS'])
    if not isinstance(jobs, list) or not 1 <= len(jobs) <= 2 or any(not isinstance(j, dict) for j in jobs):
        raise ValueError('one or two private role jobs are required')
    expected_formats = {'chat': ('chat',), 'solver': ('text', 'chat')}
    seen_roles, seen_runs = set(), set()
    for job in jobs:
        role = job.get('role')
        if role not in expected_formats or role in seen_roles:
            raise ValueError('private roles must be unique chat or solver')
        seen_roles.add(role)
        if job.get('format') not in expected_formats[role]:
            raise ValueError('role and data format do not match')
        profile = job.get('training_profile')
        public_sft = role == 'solver' and job['format'] == 'chat' and profile is None and job.get('sft_epochs') == 3
        if job.get('assistant_only_loss') is not None and (job['assistant_only_loss'] != 'required'
                or not (role == 'chat' and job['format'] == 'chat' and profile == 'gemma-26b-qlora-v1' or public_sft)):
            raise ValueError('unsupported assistant-only loss job requirement')
        if 'sft_epochs' in job and (type(job['sft_epochs']) is not int or not public_sft or job.get('assistant_only_loss') != 'required'
                or any(not re.fullmatch('[a-f0-9]{64}', env.get(key, '')) for key in
                    ('HASLA_PUBLIC_RATIONALE_SCRIPT_SHA256', 'HASLA_OFFLINE_DPO_SCRIPT_SHA256'))
                or type(job.get('offline_dpo')) is not dict):
            raise ValueError('public-rationale SFT needs fixed epochs and pinned helpers')
        if profile is not None and (role, profile) not in (('chat', 'gemma-26b-qlora-v1'),
                                                         ('solver', 'qwq-32b-qlora-48gb-v1')):
            raise ValueError('unknown or incompatible training profile')
        if profile == 'qwq-32b-qlora-48gb-v1' and job['format'] != 'text':
            raise ValueError('QwQ low-memory profile requires native text1024')
        run_id = job.get('run')
        if not isinstance(run_id, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,120}', run_id) or run_id in seen_runs:
            raise ValueError('invalid private run identity')
        seen_runs.add(run_id)
        artifact = job.get('input_artifact')
        if not isinstance(artifact, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+:v[0-9]+', artifact):
            raise ValueError('immutable private input artifact is required')
        for key in ('training_sha256', 'validation_sha256'):
            if not isinstance(job.get(key), str) or not re.fullmatch(r'[a-f0-9]{64}', job[key]):
                raise ValueError('invalid private input checksum')
        runtime = job.get('runtime_seconds', 1200 if role == 'chat' else 2700)
        maximum = (3000 if profile == 'gemma-26b-qlora-v1' else 1800) if role == 'chat' else 14400
        if (type(runtime) is not int or not 60 <= runtime <= maximum):
            raise ValueError('invalid private role runtime')
        if job.get('initial_adapter') is not None and ((role == 'chat' and profile != 'gemma-26b-qlora-v1') or not isinstance(job['initial_adapter'], dict)
                or not re.fullmatch(r'[a-f0-9]{64}', env.get('HASLA_RESUME_SCRIPT_SHA256', ''))):
            raise ValueError('initial adapters require a supported role/profile and pinned helper')
    return jobs


def main():
    env = dict(os.environ)
    jobs = role_jobs(env)
    commit, expected = env['REPO_SHA'], env['HASLA_POD_SCRIPT_SHA256']
    if not re.fullmatch(r'[0-9a-f]{40}', commit) or not re.fullmatch(r'[a-f0-9]{64}', expected):
        raise ValueError('pinned child code is required')
    url = f'https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io/{commit}/tools/ai/private_pod_train.py'
    with urllib.request.urlopen(url, timeout=45) as response:
        code = response.read(256 * 1024 + 1)
    if len(code) > 256 * 1024 or hashlib.sha256(code).hexdigest() != expected:
        raise ValueError('private child code checksum mismatch')
    script = Path('/workspace/private_pod_train.py')
    script.write_bytes(code)
    workspaces = {job['role']: Path('/workspace') / job['role'] for job in jobs}
    # Filesystem/bootstrap failures abort before any GPU child is launched.
    for workspace in workspaces.values():
        workspace.mkdir(parents=True, exist_ok=True)
    any_failed = False
    for job in jobs:
        runtime = job.get('runtime_seconds', 1200 if job['role'] == 'chat' else 2700)
        child = {k: v for k, v in env.items() if k not in ('HASLA_ROLE_JOBS', 'HASLA_TRAINING_PROFILE', 'HASLA_ASSISTANT_ONLY_LOSS', 'HASLA_SFT_EPOCHS')}
        child.update({'ROLE': job['role'], 'HASLA_DATA_FORMAT': job['format'],
                      'HASLA_INPUT_ARTIFACT': job['input_artifact'],
                      'HASLA_DATA_SHA256': job['training_sha256'],
                      'HASLA_VALIDATION_SHA256': job['validation_sha256'],
                      'RUN': job['run'], 'ARTIFACT': job['run'] + '-lora',
                      'HASLA_WORKSPACE': workspaces[job['role']].as_posix(),
                      'HASLA_TRAIN_TIMEOUT_SECONDS': str(runtime)})
        if job.get('training_profile') is not None:
            child['HASLA_TRAINING_PROFILE'] = job['training_profile']
        if job.get('assistant_only_loss') is not None:
            child['HASLA_ASSISTANT_ONLY_LOSS'] = job['assistant_only_loss']
        if job.get('sft_epochs') is not None:
            child['HASLA_SFT_EPOCHS'] = str(job['sft_epochs'])
            child['HASLA_OFFLINE_DPO_META'] = json.dumps(job['offline_dpo'], separators=(',', ':'))
        if job.get('initial_adapter') is not None:
            child['HASLA_INITIAL_ADAPTER'] = json.dumps(job['initial_adapter'], separators=(',', ':'))
        try:
            result = subprocess.run([sys.executable, str(script)], env=child, cwd=workspaces[job['role']].as_posix(),
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     timeout=runtime + 300)
            failed = result.returncode != 0
        except (subprocess.TimeoutExpired, OSError):
            # subprocess.run kills and reaps its timed-out child before raising;
            # a launch OSError does not leave a successfully started child here.
            # Unknown exceptions remain global failures instead of risking overlap.
            failed = True
        if failed:
            print(json.dumps({'status': 'failed', 'role': job['role']}), flush=True)
            any_failed = True
        else:
            print(json.dumps({'status': 'uploaded', 'role': job['role']}), flush=True)
    return 1 if any_failed else 0


def entrypoint():
    try:
        return main()
    except Exception:
        print(json.dumps({'status': 'failed', 'role': 'bootstrap'}), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(entrypoint())

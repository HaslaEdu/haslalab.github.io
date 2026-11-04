"""Run Gemma and QwQ in separate processes on one private GPU, in that order."""
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
    if not isinstance(jobs, list) or [j.get('role') for j in jobs] != ['chat', 'solver']:
        raise ValueError('exactly chat then solver is required')
    expected_formats = {'chat': 'chat', 'solver': 'text'}
    for job in jobs:
        if job.get('format') != expected_formats[job['role']]:
            raise ValueError('role and data format do not match')
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,120}', job.get('run', '')):
            raise ValueError('invalid private run identity')
        for key in ('training_sha256', 'validation_sha256'):
            if not re.fullmatch(r'[a-f0-9]{64}', job.get(key, '')):
                raise ValueError('invalid private input checksum')
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
    for job in jobs:
        child = {k: v for k, v in env.items() if k != 'HASLA_ROLE_JOBS'}
        child.update({'ROLE': job['role'], 'HASLA_DATA_FORMAT': job['format'],
                      'HASLA_INPUT_ARTIFACT': job['input_artifact'],
                      'HASLA_DATA_SHA256': job['training_sha256'],
                      'HASLA_VALIDATION_SHA256': job['validation_sha256'],
                      'RUN': job['run'], 'ARTIFACT': job['run'] + '-lora',
                      'HASLA_WORKSPACE': '/workspace/' + job['role'],
                      'HASLA_TRAIN_TIMEOUT_SECONDS': '2700'})
        result = subprocess.run([sys.executable, str(script)], env=child, cwd='/workspace',
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3000)
        if result.returncode:
            print(json.dumps({'status': 'failed', 'role': job['role']}), flush=True)
            return 1
        print(json.dumps({'status': 'uploaded', 'role': job['role']}), flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({'status': 'failed', 'error_class': type(error).__name__}), flush=True)
        raise SystemExit(1)

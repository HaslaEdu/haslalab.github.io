"""Hasla AI's automatic training, run by .github/workflows/train-ai.yml (weekly, or by hand).

For each role (solver: QwQ 32B on Workers AI; chat: Gemma 4 26B-A4B on CoreWeave):
  1. gives the Worker a fresh key for this run (Worker secret AI_TRAIN_KEY) and asks how many approved conversations
     are new since the last training; too few → nothing more for that role
  2. starts a RunPod GPU pod that runs tools/ai/pod_train.py: downloads the data, trains a LoRA, uploads it to W&B
  3. waits for it, and always removes the pod at the end (also on failure), noting the GPU cost
  4. makes the adapter usable: solver → `wrangler ai finetune create` on Workers AI; chat → served by W&B Inference
     (the Worker secret AI_CHAT_KEY is the W&B key)
  5. tries it: the same problems answered with the current setting and with the new adapter, graded by the judge
  6. promotes it only when it scores better; every step is recorded and shown on ai-review.html (with a rollback)
  7. replaces the run's key with a random one, so it is good for this run only

Secrets: RUNPOD_API_KEY, WANDB_API_KEY, HF_TOKEN, CLOUDFLARE_API_TOKEN (the deploy token, which can set Worker secrets).
DRY_RUN=1 checks every key and the data without starting a GPU.
"""
import json
import os
import secrets
import subprocess
import sys
import time
from datetime import datetime, timezone

import requests

E = os.environ
WORKER = E.get('HASLA_WORKER', 'https://haslalab-community-edge.haslalab.workers.dev').rstrip('/')
RUNPOD = 'https://rest.runpod.io/v1'
COMMUNITY = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'community')
ROLES = ['solver', 'chat'] if E.get('ROLE', 'both') == 'both' else [E['ROLE']]
MIN = int(E.get('MIN_EXAMPLES') or 200)
TRIALS = int(E.get('TRIALS') or 8)
GPU = E.get('GPU') or 'NVIDIA A100 80GB PCIe'
IMAGE = E.get('IMAGE') or 'runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04'
FORCE = E.get('FORCE') == 'true'
DRY = E.get('DRY_RUN') == 'true'
MARGIN = 0.02            # the candidate must beat the current setting by this much (on a 0–1 scale)
TRAIN_TIMEOUT = 5 * 3600
SUMMARY = []


def say(*a):
    line = ' '.join(str(x) for x in a)
    print(line, flush=True)
    SUMMARY.append(line)


def wrangler(*args, stdin=None):
    return subprocess.run(['npx', 'wrangler', *args], cwd=COMMUNITY, input=stdin, text=True, capture_output=True)


def set_worker_secret(name, value):
    r = wrangler('secret', 'put', name, stdin=value)
    if r.returncode:
        raise SystemExit(f'could not set the Worker secret {name} (CLOUDFLARE_API_TOKEN needs "Edit Cloudflare Workers"):\n{r.stderr[-800:]}')


class Worker:
    def __init__(self, key):
        self.h = {'X-Hasla-Train-Key': key, 'Content-Type': 'application/json'}

    def get(self, path, **kw):
        r = requests.get(WORKER + '/api/admin/ai-train' + path, headers=self.h, timeout=120, **kw)
        r.raise_for_status()
        return r

    def post(self, path, body, timeout=120):
        r = requests.post(WORKER + '/api/admin/ai-train' + path, headers=self.h, json=body, timeout=timeout)
        r.raise_for_status()
        return r.json()

    def record(self, run, role, status, **fields):
        try:
            return self.post('/record', {'run': run, 'role': role, 'status': status, **fields})
        except Exception as e:
            print('record failed:', e, file=sys.stderr)


def runpod(method, path, **kw):
    r = requests.request(method, RUNPOD + path, headers={'Authorization': 'Bearer ' + E['RUNPOD_API_KEY']}, timeout=60, **kw)
    if r.status_code >= 400:
        raise RuntimeError(f'RunPod {method} {path}: {r.status_code} {r.text[:300]}')
    return r.json() if r.text else {}


def check_keys(w):
    """every outside account the run needs, before any money is spent"""
    ok = True
    try:
        runpod('GET', '/pods')
        say('✓ RunPod key works')
    except Exception as e:
        ok = False
        say('✗ RunPod:', e)
    r = requests.get('https://huggingface.co/api/whoami-v2', headers={'Authorization': 'Bearer ' + E.get('HF_TOKEN', '')}, timeout=30)
    say('✓ Hugging Face token works' if r.ok else f'✗ Hugging Face token: {r.status_code}')
    ok &= r.ok
    for repo in ('google/gemma-4-26B-A4B-it', 'Qwen/QwQ-32B'):
        r = requests.get(f'https://huggingface.co/api/models/{repo}', headers={'Authorization': 'Bearer ' + E.get('HF_TOKEN', '')}, timeout=30)
        say(f'✓ {repo} visible' if r.ok else f'✗ {repo}: {r.status_code} (accept its license on huggingface.co, or check the name)')
    r = requests.post('https://api.wandb.ai/graphql', json={'query': '{ viewer { entity } }'}, auth=('api', E.get('WANDB_API_KEY', '')), timeout=30)
    entity = (r.json().get('data') or {}).get('viewer', {}).get('entity') if r.ok else None
    say(f'✓ W&B key works (entity {entity})' if entity else f'✗ W&B key: {r.status_code}')
    ok &= bool(entity)
    r = wrangler('ai', 'finetune', 'list')
    say('✓ Cloudflare token can use Workers AI fine-tunes' if r.returncode == 0 else '✗ Cloudflare token cannot list Workers AI fine-tunes (add the Workers AI · Edit permission to the deploy token): ' + r.stderr[-300:])
    st = w.get('/status').json()
    for role in ('solver', 'chat'):
        c = st['counts'][role]
        say(f'· {role}: {c["approved"]} approved, {c["new_since_last"]} new since the last training (needs {MIN})')
    return ok, entity


def train_role(w, key, role, entity):
    st = w.get('/status').json()['counts'][role]
    if st['new_since_last'] < MIN and not FORCE:
        say(f'· {role}: {st["new_since_last"]} new approved examples, fewer than {MIN}; not training')
        return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M')
    run, artifact = f'hasla-{role}-{stamp}', f'hasla-{role}-lora'
    w.record(run, role, 'starting', examples=st['approved'], data_max_id=st['max_id'])
    pod, row, t0, cost_hr = None, None, time.time(), 0.0
    try:
        pod = runpod('POST', '/pods', json={
            'name': run, 'imageName': IMAGE, 'cloudType': 'SECURE', 'gpuTypeIds': [GPU], 'gpuCount': 1,
            'containerDiskInGb': 200, 'volumeInGb': 0, 'interruptible': False,
            'env': {'ROLE': role, 'RUN': run, 'ARTIFACT': artifact, 'TRAIN_KEY': key, 'HF_TOKEN': E['HF_TOKEN'],
                    'WANDB_API_KEY': E['WANDB_API_KEY'], 'WANDB_PROJECT': 'hasla-ai', 'REPO_SHA': E['GITHUB_SHA'], 'GPU_NAME': GPU,
                    'DATA_URL': f'{WORKER}/api/admin/ai-train/data?role={role}', 'REPORT_URL': f'{WORKER}/api/admin/ai-train/record'},
            'dockerStartCmd': ['bash', '-lc',
                'pip install -q --upgrade unsloth trl datasets wandb && '
                f'curl -fsSL https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io/{E["GITHUB_SHA"]}/tools/ai/pod_train.py -o /pod_train.py && '
                'python /pod_train.py'],
        })
        cost_hr = float(pod.get('costPerHr') or 0)
        say(f'· {role}: pod {pod.get("id")} on {GPU} (${cost_hr}/h)')
        while time.time() - t0 < TRAIN_TIMEOUT:
            time.sleep(60)
            row = next((r for r in w.get('/status').json()['runs'] if r['run'] == run), None)
            if row and row['status'] in ('uploaded', 'failed'):
                break
            info = runpod('GET', f'/pods/{pod["id"]}')
            if info.get('desiredStatus') in ('EXITED', 'TERMINATED') and (not row or row['status'] not in ('uploaded',)):
                time.sleep(30)   # its last report may still be on the way
                row = next((r for r in w.get('/status').json()['runs'] if r['run'] == run), None)
                break
        if not row or row['status'] != 'uploaded':
            raise RuntimeError(f'training did not finish: {row and row["status"]} {row and (row.get("note") or "")[:300]}')
    finally:
        if pod and pod.get('id'):
            try:
                runpod('DELETE', f'/pods/{pod["id"]}')
            except Exception as e:
                say(f'! could not remove pod {pod["id"]}: {e} — remove it on runpod.io so it stops billing')
        cost = round(cost_hr * (time.time() - t0) / 3600, 2)
        done = bool(row and row.get('status') == 'uploaded')
        w.record(run, role, 'trained' if done else 'failed', cost=cost)
        say(f'· {role}: GPU time {round((time.time() - t0) / 60)} min, about ${cost}')

    path = row['artifact']
    if role == 'solver':
        subprocess.run(['wandb', 'artifact', 'get', path, '--root', '/tmp/adapter'], check=True)
        name = run
        r = wrangler('ai', 'finetune', 'create', '@cf/qwen/qwq-32b', name, '/tmp/adapter')
        if r.returncode:
            w.record(run, role, 'failed', note='Workers AI did not take the adapter: ' + r.stderr[-1500:])
            raise RuntimeError('wrangler ai finetune create failed: ' + r.stderr[-600:])
        candidate = {'AI_SOLVER_LORA': name}
    else:
        set_worker_secret('AI_CHAT_KEY', E['WANDB_API_KEY'])
        candidate = {'AI_CHAT_URL': 'https://api.inference.wandb.ai/v1', 'AI_CHAT_REMOTE': f'wandb-artifact:///{path}',
                     'AI_CHAT_PROJECT': f'{entity}/hasla-ai'}
    w.record(run, role, 'testing', candidate=candidate)

    base, cand = [], []
    for i in range(TRIALS):
        try:
            t = w.post('/trial', {'role': role, 'candidate': candidate}, timeout=900)
        except Exception as e:
            say(f'  trial {i + 1}: failed ({e})')
            continue
        if t.get('base') is not None and t.get('cand') is not None:
            base.append(t['base']); cand.append(t['cand'])
            say(f'  trial {i + 1}: current {t["base"]:.2f}  new {t["cand"]:.2f}  ({t.get("ref")})')
    if len(base) < max(3, TRIALS // 2):
        w.record(run, role, 'rejected', trials=len(base), note='too few trials finished to judge')
        say(f'· {role}: only {len(base)} trials finished; not promoted')
        return
    b, c = sum(base) / len(base), sum(cand) / len(cand)
    w.record(run, role, 'tested', base_score=round(b, 3), cand_score=round(c, 3), trials=len(base))
    if c >= b + MARGIN:
        w.post('/promote', {'run': run})
        say(f'✓ {role}: new adapter {c:.2f} vs current {b:.2f} → promoted ({run})')
    else:
        w.record(run, role, 'rejected')
        say(f'· {role}: new adapter {c:.2f} vs current {b:.2f} → kept the current one')


def main():
    key = secrets.token_hex(24)
    set_worker_secret('AI_TRAIN_KEY', key)
    w = Worker(key)
    for _ in range(12):   # the new secret takes a few seconds to reach the edge
        try:
            w.get('/status')
            break
        except Exception:
            time.sleep(10)
    try:
        ok, entity = check_keys(w)
        if DRY:
            say('dry run: no GPU started')
            return 0 if ok else 1
        if not ok:
            say('a key is missing or wrong; fix it and run again')
            return 1
        failed = False
        for role in ROLES:
            try:
                train_role(w, key, role, entity)
            except Exception as e:
                failed = True
                say(f'✗ {role}: {e}')
        return 1 if failed else 0
    finally:
        set_worker_secret('AI_TRAIN_KEY', secrets.token_hex(24))   # this run's key stops working
        if E.get('GITHUB_STEP_SUMMARY'):
            open(E['GITHUB_STEP_SUMMARY'], 'a').write('## Hasla AI training\n\n' + '\n'.join(f'- {l}' for l in SUMMARY) + '\n')


if __name__ == '__main__':
    sys.exit(main())

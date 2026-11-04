"""Runs inside the RunPod GPU pod that tools/ai/autotrain.py starts (one training run, then the pod ends itself).

Environment (set by autotrain.py when it creates the pod): ROLE (solver|chat), RUN, DATA_URL, REPORT_URL, TRAIN_KEY
(the run's key for the Worker), HF_TOKEN, WANDB_API_KEY, WANDB_PROJECT, ARTIFACT, REPO_SHA.

1. downloads the approved conversations for the role from the Worker
2. trains a LoRA with tools/ai/train_lora.py (same commit)
3. uploads the adapter to W&B as an artifact of type "lora" (CoreWeave serves it for the chat model; for the solver
   the workflow fetches it from there and uploads it to Workers AI)
4. reports each step to the Worker (ai_train) and removes its own pod
"""
import json
import os
import subprocess
import sys
import traceback
import urllib.request

E = os.environ
BASES = {'chat': 'google/gemma-4-26B-A4B-it', 'solver': 'Qwen/QwQ-32B', 'fast': 'meta-llama/Llama-3.1-8B-Instruct'}


def call(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'X-Hasla-Train-Key': E['TRAIN_KEY'], 'Content-Type': 'application/json'},
                                 method='POST' if body is not None else 'GET')
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def report(status, **fields):
    try:
        call(E['REPORT_URL'], {'run': E['RUN'], 'role': E['ROLE'], 'status': status, **fields})
    except Exception as e:  # a report that does not arrive never stops the training
        print('report failed:', e, file=sys.stderr)


def end_pod():
    pod = E.get('RUNPOD_POD_ID')
    if pod:
        subprocess.run(['runpodctl', 'remove', 'pod', pod], check=False)


def main():
    role = E['ROLE']
    report('downloading')
    data = call(E['DATA_URL'])
    open('/data.jsonl', 'wb').write(data)
    n = sum(1 for line in data.decode('utf-8').splitlines() if line.strip())
    report('training', examples=n, note=f'{n} examples on {E.get("GPU_NAME", "GPU")}')
    script = '/train_lora.py'
    urllib.request.urlretrieve(f'https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io/{E["REPO_SHA"]}/tools/ai/train_lora.py', script)
    subprocess.run([sys.executable, script, '--base', role, '/data.jsonl', '/adapter'], check=True)

    # the adapter's config names its base, as the serving side expects
    cfg_path = '/adapter/adapter_config.json'
    cfg = json.load(open(cfg_path))
    cfg['base_model_name_or_path'] = BASES[role]
    json.dump(cfg, open(cfg_path, 'w'), indent=2)

    import wandb
    run = wandb.init(project=E.get('WANDB_PROJECT', 'hasla-ai'), job_type='lora', name=E['RUN'])
    try:
        art = wandb.Artifact(E['ARTIFACT'], type='lora', metadata={'wandb.base_model': BASES[role], 'examples': n}, storage_region='coreweave-us')
    except TypeError:  # an older wandb without storage_region
        art = wandb.Artifact(E['ARTIFACT'], type='lora', metadata={'wandb.base_model': BASES[role], 'examples': n})
    art.add_dir('/adapter')
    run.log_artifact(art, aliases=['latest'])
    art.wait()
    path = f'{run.entity}/{run.project}/{E["ARTIFACT"]}:latest'
    run.finish()
    report('uploaded', artifact=path)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        report('failed', note=traceback.format_exc()[-1500:])
        raise
    finally:
        end_pod()

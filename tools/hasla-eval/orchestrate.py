"""Runs the Hasla AI model-selection evaluation (run_eval.py) for each model asked for, by .github/workflows/hasla-eval.yml.

Models served by Workers AI are called through Cloudflare's API. The others are not served by any API (P1, SU-01) or not
by one we use (Qwen3.6), so each gets a RunPod GPU pod running vLLM for the length of its run, on the cheapest GPU that
holds it (a 48 GB card with FP8 weights and KV cache for the 30–35B mixture-of-experts models), and the pod is always
removed at the end, also on failure. GPU cost = the pod's hourly price × the time it was up, model download included.
"""
import json
import os
import subprocess
import sys
import time

import requests

from run_eval import cloudflare_account

E = os.environ
HERE = os.path.dirname(os.path.abspath(__file__))
RUNPOD = 'https://rest.runpod.io/v1'
IMAGE = E.get('VLLM_IMAGE') or 'vllm/vllm-openai:latest'
GPU_DEFAULT = ('NVIDIA L40S,NVIDIA RTX 6000 Ada Generation,NVIDIA L40,NVIDIA A40,NVIDIA RTX A6000,NVIDIA A100 80GB PCIe,'
               'NVIDIA A100-SXM4-80GB,NVIDIA H100 PCIe,NVIDIA H100 80GB HBM3')
GPUS = [g.strip() for g in (E.get('GPUS') or GPU_DEFAULT).split(',') if g.strip()]
SERVE = '--host 0.0.0.0 --port 8000 --max-model-len 65536 --quantization fp8 --gpu-memory-utilization 0.92 --max-num-seqs 16'
# FP8 KV cache only on Ada/Hopper (compute capability 8.9+); an Ampere card (A40, A6000, A100) keeps it in 16 bits
KV = 'cc=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1 | tr -d .); kv=""; [ "${cc:-0}" -ge 89 ] && kv="--kv-cache-dtype fp8"; '

MODELS = {
    'gemma4': {'kind': 'workers-ai', 'model': '@cf/google/gemma-4-26b-a4b-it', 'args': ['--template-kwargs', '{"enable_thinking": true}']},
    'qwen38': {'kind': 'workers-ai', 'model': '@cf/qwen/qwen3.8-27b', 'args': ['--effort', 'low']},
    'qwen36': {'kind': 'pod', 'hf': 'Qwen/Qwen3.6-35B-A3B', 'sampling': {'temperature': 0.6, 'top_p': 0.95, 'top_k': 20}},
    'p1': {'kind': 'pod', 'hf': 'PRIME-RL/P1-30B-A3B', 'sampling': {'temperature': 0.6, 'top_p': 0.9}},
    'su01': {'kind': 'pod', 'hf': 'Simplified-Reasoning/SU-01', 'sampling': {'temperature': 0.6, 'top_p': 0.95}, 'long_run': True},
}


def runpod(method, path, **kw):
    r = requests.request(method, RUNPOD + path, headers={'Authorization': 'Bearer ' + E['RUNPOD_API_KEY']}, timeout=60, **kw)
    if r.status_code >= 400:
        raise RuntimeError(f'RunPod {method} {path}: {r.status_code} {r.text[:300]}')
    return r.json() if r.text else {}


D1 = '96761b6d-c194-4ee5-9836-7845b51a5f07'


def fetch_grade_cases(bench):
    """event 2's audited answer sheets, read from D1 (the bench row of tune-grade-export) at run time: they are students'
    papers, so they never go into this public repository (grade_cases.json is git-ignored)"""
    path = os.path.join(HERE, 'grade_cases.json')
    if os.path.exists(path) or not bench:
        return
    for tok in (E.get('CLOUDFLARE_API_TOKEN'), E.get('CLOUDFLARE_AI_TOKEN')):
        if not tok:
            continue
        try:
            h = {'Authorization': f'Bearer {tok}'}
            acct = cloudflare_account()
            r = requests.post(f'https://api.cloudflare.com/client/v4/accounts/{acct}/d1/database/{D1}/query', headers=h, timeout=60,
                              json={'sql': 'SELECT output FROM lab_bench WHERE id = ?', 'params': [str(bench)]}).json()
            out = json.loads(r['result'][0]['results'][0]['output'])
            json.dump({'system': out['system'], 'cases': out['cases']}, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
            print(f'· event 2: {len(out["cases"])} answer sheets from bench {bench}', flush=True)
            return
        except Exception as e:
            print(f'! event 2 cases with this token: {str(e)[:200]}', flush=True)
    print('! event 2 skipped: the answer sheets could not be read from D1', flush=True)


def create_pod(spec, name):
    """a pod on the first cloud with a free card of the list (COMMUNITY first unless CLOUD says SECURE), retried for up
    to 15 minutes while RunPod has none free"""
    first = (E.get('CLOUD') or 'COMMUNITY').upper()
    clouds = [first] + [c for c in ('COMMUNITY', 'SECURE') if c != first]
    t0, last = time.time(), None
    while time.time() - t0 < 900:
        for cloud in clouds:
            try:
                pod = runpod('POST', '/pods', json={**spec, 'cloudType': cloud})
                print(f'· {name}: {cloud} cloud', flush=True)
                return pod
            except RuntimeError as e:
                last = e
                if 'no instances' not in str(e).lower() and 'not available' not in str(e).lower():
                    raise
        print(f'· {name}: no free GPU yet, trying again in 60 s', flush=True)
        time.sleep(60)
    raise RuntimeError(f'no free GPU in 15 minutes: {last}')


def run_eval(name, extra, out, events, budget):
    cmd = [sys.executable, os.path.join(HERE, 'run_eval.py'), '--name', name, '--events', events, '--budget', str(budget),
           '--out', out] + extra
    print('$', ' '.join(cmd), flush=True)
    return subprocess.run(cmd).returncode


def pod_model(name, cfg, events, budget, outdir):
    pod, t0, meta = None, time.time(), {'name': name, 'hf': cfg['hf']}
    try:
        pod = create_pod({
            'name': f'hasla-eval-{name}', 'imageName': IMAGE, 'gpuTypeIds': GPUS, 'gpuCount': 1, 'containerDiskInGb': 120, 'volumeInGb': 0, 'ports': ['8000/http'],
            'env': {'HF_TOKEN': E.get('HF_TOKEN', ''), 'HUGGING_FACE_HUB_TOKEN': E.get('HF_TOKEN', '')},
            'dockerEntrypoint': ['bash', '-lc'],
            'dockerStartCmd': [KV + f'vllm serve {cfg["hf"]} {SERVE} $kv'],
        }, name)
        meta.update({'pod': pod.get('id'), 'cost_per_hr': float(pod.get('costPerHr') or 0), 'gpu': (pod.get('machine') or {}).get('gpuTypeId')})
        print(f'· {name}: pod {pod.get("id")} ${meta["cost_per_hr"]}/h', flush=True)
        base = f'https://{pod["id"]}-8000.proxy.runpod.net/v1'
        while True:   # weights download + load: up to 40 minutes
            if time.time() - t0 > 2400:
                raise RuntimeError('vLLM did not come up in 40 minutes')
            try:
                if requests.get(base + '/models', timeout=20).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(20)
        meta['ready_s'] = round(time.time() - t0)
        print(f'· {name}: serving after {meta["ready_s"]} s', flush=True)
        common = ['--kind', 'openai', '--base-url', base, '--model', cfg['hf'], '--sampling', json.dumps(cfg['sampling'])]
        run_eval(name, common, os.path.join(outdir, f'{name}.json'), events, budget)
        if cfg.get('long_run') and '3' in events:
            # the same model with room to think as long as it was trained to (up to 60k tokens), on the solving event only
            run_eval(name + '-long', common + ['--answer-tokens', '4000'], os.path.join(outdir, f'{name}-long.json'), '3', 60000)
    except Exception as e:
        meta['error'] = str(e)[:500]
        print(f'! {name}: {e}', flush=True)
    finally:
        if pod and pod.get('id'):
            try:
                runpod('DELETE', f'/pods/{pod["id"]}')
            except Exception as e:
                print(f'! could not remove pod {pod["id"]}: {e} — remove it on runpod.io so it stops billing', flush=True)
        meta['up_s'] = round(time.time() - t0)
        meta['gpu_cost_usd'] = round(meta.get('cost_per_hr', 0) * meta['up_s'] / 3600, 3)
        json.dump(meta, open(os.path.join(outdir, f'{name}.pod.json'), 'w'), indent=1)
        print(f'· {name}: up {meta["up_s"]} s, about ${meta["gpu_cost_usd"]}', flush=True)


def main():
    names = [n.strip() for n in (E.get('MODELS') or 'gemma4,qwen38,qwen36,p1,su01').split(',') if n.strip()]
    events, budget = E.get('EVENTS') or '1,2,3', int(E.get('BUDGET') or 16000)
    outdir = os.path.join(HERE, 'results', E.get('RUN') or time.strftime('%Y%m%d-%H%M'))
    os.makedirs(outdir, exist_ok=True)
    if '2' in events:
        fetch_grade_cases(E.get('GRADE_BENCH') or '5613')
    for n in names:
        cfg = MODELS[n]
        if cfg['kind'] == 'workers-ai':
            run_eval(n, ['--kind', 'workers-ai', '--model', cfg['model']] + cfg['args'], os.path.join(outdir, f'{n}.json'), events, budget)
        else:
            pod_model(n, cfg, events, budget, outdir)
    print('results in', outdir)


if __name__ == '__main__':
    main()

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

E = os.environ
HERE = os.path.dirname(os.path.abspath(__file__))
RUNPOD = 'https://rest.runpod.io/v1'
IMAGE = E.get('VLLM_IMAGE') or 'vllm/vllm-openai:latest'
GPUS = [g.strip() for g in (E.get('GPUS') or 'NVIDIA L40S,NVIDIA RTX 6000 Ada Generation,NVIDIA A100 80GB PCIe').split(',') if g.strip()]
SERVE = '--host 0.0.0.0 --port 8000 --max-model-len 65536 --quantization fp8 --kv-cache-dtype fp8 --gpu-memory-utilization 0.92 --max-num-seqs 16'

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


def run_eval(name, extra, out, events, budget):
    cmd = [sys.executable, os.path.join(HERE, 'run_eval.py'), '--name', name, '--events', events, '--budget', str(budget),
           '--out', out] + extra
    print('$', ' '.join(cmd), flush=True)
    return subprocess.run(cmd).returncode


def pod_model(name, cfg, events, budget, outdir):
    pod, t0, meta = None, time.time(), {'name': name, 'hf': cfg['hf']}
    try:
        pod = runpod('POST', '/pods', json={
            'name': f'hasla-eval-{name}', 'imageName': IMAGE, 'gpuTypeIds': GPUS, 'gpuCount': 1,
            'cloudType': E.get('CLOUD') or 'COMMUNITY', 'containerDiskInGb': 120, 'volumeInGb': 0, 'ports': ['8000/http'],
            'env': {'HF_TOKEN': E.get('HF_TOKEN', ''), 'HUGGING_FACE_HUB_TOKEN': E.get('HF_TOKEN', '')},
            'dockerEntrypoint': ['bash', '-lc'],
            'dockerStartCmd': [f'vllm serve {cfg["hf"]} {SERVE}'],
        })
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
    for n in names:
        cfg = MODELS[n]
        if cfg['kind'] == 'workers-ai':
            run_eval(n, ['--kind', 'workers-ai', '--model', cfg['model']] + cfg['args'], os.path.join(outdir, f'{n}.json'), events, budget)
        else:
            pod_model(n, cfg, events, budget, outdir)
    print('results in', outdir)


if __name__ == '__main__':
    main()

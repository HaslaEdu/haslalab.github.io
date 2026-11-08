"""Which LoRA layouts CoreWeave's serverless inference (W&B Inference) serves on Qwen/Qwen3.6-35B-A3B, before any
training (HaslaEdu/hasla-ai, plan step 1). Builds three rank-16 adapters whose B matrices are zero (they change
nothing), with the layer shapes read from the model's safetensors headers (no weights downloaded):
  attn    full-attention q/k/v/o only
  dense   + linear attention (in_proj_qkv, in_proj_z, out_proj) + the shared expert (gate/up/down)
  experts + every routed expert's gate/up/down, as PEFT names them per expert (experts.<e>.gate_proj …)
uploads each as a W&B artifact of type lora (wandb.base_model, coreweave-us), then calls each through
https://api.inference.wandb.ai/v1 and prints whether it answers. WANDB_API_KEY in the environment."""
import json
import os
import struct
import sys
import tempfile

import requests
import torch
import wandb
from safetensors.torch import save_file

BASE = 'Qwen/Qwen3.6-35B-A3B'
HF = f'https://huggingface.co/{BASE}/resolve/main/'
R, ALPHA = 16, 32
PROJECT = os.environ.get('WANDB_PROJECT') or 'hasla-ai'
HDR = {'Authorization': f'Bearer {os.environ["HF_TOKEN"]}'} if os.environ.get('HF_TOKEN') else {}


def shapes():
    """weight name -> shape, from the safetensors headers (a ranged read of each shard's first bytes)"""
    index = requests.get(HF + 'model.safetensors.index.json', headers=HDR, timeout=60).json()['weight_map']
    out = {}
    for shard in sorted(set(index.values())):
        h = {**HDR, 'Range': 'bytes=0-7'}
        n = struct.unpack('<Q', requests.get(HF + shard, headers=h, timeout=60).content[:8])[0]
        meta = requests.get(HF + shard, headers={**HDR, 'Range': f'bytes=8-{8 + n - 1}'}, timeout=120).json()
        out.update({k: v['shape'] for k, v in meta.items() if k != '__metadata__'})
    return out


def lora(tensors, module, out_f, in_f):
    """PEFT names: base_model.model.<module>.lora_A/B.weight; B is zero, so the adapter changes nothing"""
    p = f'base_model.model.{module}'
    tensors[p + '.lora_A.weight'] = (torch.randn(R, in_f) * 0.01).to(torch.bfloat16)
    tensors[p + '.lora_B.weight'] = torch.zeros(out_f, R, dtype=torch.bfloat16)


def build(kind, sh, d):
    t, targets = {}, set()
    for name, shape in sh.items():
        if not name.startswith('model.language_model.layers.') or not name.endswith('.weight') or len(shape) != 2:
            continue
        mod, leaf = name[:-len('.weight')], name[:-len('.weight')].rsplit('.', 1)[1]
        if leaf in ('q_proj', 'k_proj', 'v_proj', 'o_proj') or (kind != 'attn' and leaf in (
                'in_proj_qkv', 'in_proj_z', 'out_proj') and '.linear_attn.' in name) or (kind != 'attn' and '.shared_expert.' in name and leaf in (
                'gate_proj', 'up_proj', 'down_proj')):
            lora(t, mod, shape[0], shape[1])
            targets.add(leaf)
    if kind == 'experts':   # routed experts are stored fused (E, 2I, H) and (E, H, I): written per expert, as PEFT on unfused modules
        for name, shape in sh.items():
            if name.startswith('model.language_model.layers.') and name.endswith('.mlp.experts.gate_up_proj'):
                layer = name[:-len('.gate_up_proj')]
                e, two_i, hid = shape
                for x in range(e):
                    lora(t, f'{layer}.{x}.gate_proj', two_i // 2, hid)
                    lora(t, f'{layer}.{x}.up_proj', two_i // 2, hid)
                    lora(t, f'{layer}.{x}.down_proj', hid, two_i // 2)
                targets.update(('gate_proj', 'up_proj', 'down_proj'))
    save_file(t, os.path.join(d, 'adapter_model.safetensors'))
    json.dump({'peft_type': 'LORA', 'task_type': 'CAUSAL_LM', 'base_model_name_or_path': BASE, 'r': R, 'lora_alpha': ALPHA,
               'lora_dropout': 0.0, 'bias': 'none', 'fan_in_fan_out': False, 'target_modules': sorted(targets),
               'modules_to_save': None, 'inference_mode': True}, open(os.path.join(d, 'adapter_config.json'), 'w'), indent=1)
    return len(t) // 2, os.path.getsize(os.path.join(d, 'adapter_model.safetensors'))


def ask(model, entity):
    r = requests.post('https://api.inference.wandb.ai/v1/chat/completions', timeout=300,
                      headers={'Authorization': f'Bearer {os.environ["WANDB_API_KEY"]}', 'OpenAI-Project': f'{entity}/{PROJECT}'},
                      json={'model': model, 'messages': [{'role': 'user', 'content': 'What is 1+1? Answer with the number only.'}],
                            'max_tokens': 2000})
    if r.status_code != 200:
        return False, f'{r.status_code} {r.text[:300]}'
    m = r.json()['choices'][0]['message']
    return True, repr((m.get('content') or '')[-80:])


def main():
    sh = shapes()
    print(f'{len(sh)} weights read from the headers', flush=True)
    run = wandb.init(project=PROJECT, job_type='lora-serving-check')
    entity = run.entity
    ok, msg = ask(BASE, entity)
    print(f'base {BASE}: {"OK" if ok else "FAIL"} {msg}', flush=True)
    results = {'base': ok}
    for kind in ('attn', 'dense', 'experts'):
        with tempfile.TemporaryDirectory() as d:
            n, size = build(kind, sh, d)
            art = wandb.Artifact(f'hasla-servecheck-{kind}', type='lora', metadata={'wandb.base_model': BASE},
                                 storage_region='coreweave-us')
            art.add_dir(d)
            run.log_artifact(art).wait()
        ok, msg = ask(f'wandb-artifact:///{entity}/{PROJECT}/hasla-servecheck-{kind}:latest', entity)
        results[kind] = ok
        print(f'{kind}: {n} LoRA pairs, {size / 1e6:.0f} MB -> {"OK" if ok else "FAIL"} {msg}', flush=True)
    run.finish()
    print('RESULT', json.dumps(results))
    sys.exit(0 if results['base'] else 1)


if __name__ == '__main__':
    main()

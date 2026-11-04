"""Train a LoRA adapter for HaslaLab AI from the approved conversations (ai-review.html → 학습 데이터 내보내기).

Run on a rented GPU (e.g. RunPod: A100 80GB for the 26–32B models, RTX 4090 for 8B), not on the site's servers:

    pip install "unsloth" "trl" "datasets"
    python train_lora.py --base chat haslalab-ai-train.jsonl out/chat-lora
    python train_lora.py --base solver haslalab-ai-train.jsonl out/solver-lora

Bases (each matches the model the Worker serves for that role, community/src/ai-assistant.js):
    chat    google/gemma-4-26B-A4B-it      → serve on CoreWeave (W&B Inference), set AI_CHAT_URL/_KEY/_REMOTE
    solver  Qwen/QwQ-32B                   → `npx wrangler ai finetune create @cf/qwen/qwq-32b haslalab-solver out/solver-lora`,
                                             then set AI_SOLVER_LORA=haslalab-solver
    fast    meta-llama/Llama-3.1-8B-Instruct (the intent classifier)

Rank 16 by default: CoreWeave takes rank ≤ 16, Workers AI ≤ 32 and files under 300 MB. The adapter is saved in PEFT
format (adapter_config.json + adapter_model.safetensors), which both accept. QLoRA (4-bit) training, but the adapter is
for the unquantized base, as Workers AI requires.

Not run in this repository's CI (it needs a GPU); check the loss and try the adapter on a few held-out questions
before switching the site to it.
"""
import argparse
import json
import random

BASES = {
    'chat': 'google/gemma-4-26B-A4B-it',
    'solver': 'Qwen/QwQ-32B',
    'fast': 'meta-llama/Llama-3.1-8B-Instruct',
}


def load(path, holdout):
    rows = [json.loads(line) for line in open(path, encoding='utf-8') if line.strip()]
    rows = [r for r in rows if isinstance(r.get('messages'), list) and r['messages'] and r['messages'][-1].get('role') == 'assistant']
    random.Random(0).shuffle(rows)
    n = max(1, int(len(rows) * holdout)) if len(rows) > 20 else 0
    return rows[n:], rows[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', choices=BASES, default='chat')
    ap.add_argument('data')
    ap.add_argument('out')
    ap.add_argument('--rank', type=int, default=16)
    ap.add_argument('--epochs', type=float, default=2)
    ap.add_argument('--lr', type=float, default=1e-4)
    ap.add_argument('--max-len', type=int, default=4096)
    ap.add_argument('--holdout', type=float, default=0.05)
    a = ap.parse_args()

    from unsloth import FastLanguageModel  # imported here so --help works without a GPU
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    train, held = load(a.data, a.holdout)
    print(f'{len(train)} training conversations, {len(held)} held out')
    model, tok = FastLanguageModel.from_pretrained(BASES[a.base], max_seq_length=a.max_len, load_in_4bit=True)
    model = FastLanguageModel.get_peft_model(model, r=a.rank, lora_alpha=a.rank * 2, lora_dropout=0,
                                             target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj'])
    fmt = lambda rows: Dataset.from_list([{'text': tok.apply_chat_template(r['messages'], tokenize=False)} for r in rows])
    trainer = SFTTrainer(model=model, tokenizer=tok, train_dataset=fmt(train), eval_dataset=fmt(held) if held else None,
                         args=SFTConfig(output_dir=a.out + '-run', num_train_epochs=a.epochs, learning_rate=a.lr,
                                        per_device_train_batch_size=1, gradient_accumulation_steps=8, warmup_ratio=0.05,
                                        lr_scheduler_type='cosine', logging_steps=5, save_strategy='no', bf16=True,
                                        dataset_text_field='text', max_seq_length=a.max_len,
                                        eval_strategy='epoch' if held else 'no'))
    trainer.train()
    model.save_pretrained(a.out)      # adapter_config.json + adapter_model.safetensors
    tok.save_pretrained(a.out)
    print('adapter saved to', a.out)


if __name__ == '__main__':
    main()

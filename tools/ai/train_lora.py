"""Train a LoRA adapter for Hasla AI from the approved conversations (ai-review.html → 학습 데이터 내보내기).

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
import hashlib
import json
from pathlib import Path

BASES = {
    'chat': 'google/gemma-4-26B-A4B-it',
    'solver': 'Qwen/QwQ-32B',
    'fast': 'meta-llama/Llama-3.1-8B-Instruct',
}


def read_rows(path, data_format='chat'):
    """Validate private input without printing any training text."""
    rows = []
    with open(path, encoding='utf-8-sig') as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except (ValueError, TypeError) as exc:
                raise ValueError(f'invalid JSON at line {number}') from exc
            if not isinstance(row, dict):
                raise ValueError(f'expected an object at line {number}')
            if data_format == 'text':
                valid = isinstance(row.get('text'), str) and bool(row['text'].strip())
            else:
                messages = row.get('messages')
                valid = (isinstance(messages, list) and bool(messages)
                         and all(isinstance(m, dict) and m.get('role') in ('system', 'user', 'assistant')
                                 and isinstance(m.get('content'), str) and m['content'].strip() for m in messages)
                         and messages[-1].get('role') == 'assistant'
                         and any(m['role'] == 'user' for m in messages))
            if not valid:
                raise ValueError(f'invalid {data_format} record at line {number}')
            rows.append(row)
    return rows


def fingerprint(row, data_format):
    value = row['text'] if data_format == 'text' else row['messages']
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def group_of(row, data_format):
    meta = row.get('metadata') or {}
    for key in ('group_id', 'duplicate_cluster_id', 'document_id', 'thread_id', 'conversation_id', 'source_id'):
        value = meta.get(key) or row.get(key)
        if value:
            return str(value)
    return fingerprint(row, data_format)


def split_of(row):
    return row.get('split') or (row.get('metadata') or {}).get('split')


def load(path, holdout=0.05, data_format='chat', validation_path=None):
    """Respect corpus splits; legacy input is held out by source/conversation, never by row."""
    if not 0 <= holdout < 1:
        raise ValueError('holdout must be in [0, 1)')
    rows = read_rows(path, data_format)
    assigned = any(split_of(r) is not None for r in rows)
    if assigned and any(split_of(r) not in ('train', 'validation', 'test') for r in rows):
        raise ValueError('all records must have a valid split when any record has one')
    if validation_path:
        if assigned and any(split_of(r) != 'train' for r in rows):
            raise ValueError('training input contains a non-train split')
        train, held = rows, read_rows(validation_path, data_format)
        if any(split_of(r) not in (None, 'validation') for r in held):
            raise ValueError('validation input contains a non-validation split')
    elif assigned:
        train = [r for r in rows if split_of(r) == 'train']
        held = [r for r in rows if split_of(r) == 'validation']
        # test records are deliberately excluded from both datasets.
    else:
        held_groups = {group_of(r, data_format) for r in rows
                       if int(hashlib.sha256(group_of(r, data_format).encode()).hexdigest()[:16], 16)
                       / (1 << 64) < holdout}
        train = [r for r in rows if group_of(r, data_format) not in held_groups]
        held = [r for r in rows if group_of(r, data_format) in held_groups]
    if not train:
        raise ValueError('no training records; review the input and group split')
    if {group_of(r, data_format) for r in train} & {group_of(r, data_format) for r in held}:
        raise ValueError('a source/conversation group overlaps training and validation')
    if {fingerprint(r, data_format) for r in train} & {fingerprint(r, data_format) for r in held}:
        raise ValueError('duplicate content overlaps training and validation')
    return train, held


def dataset_summary(train, held, data_format):
    def chars(row):
        return len(row['text']) if data_format == 'text' else sum(len(m['content']) for m in row['messages'])
    return {'format': data_format, 'training_records': len(train), 'validation_records': len(held),
            'training_groups': len({group_of(r, data_format) for r in train}),
            'validation_groups': len({group_of(r, data_format) for r in held}),
            'training_characters': sum(map(chars, train)),
            'validation_characters': sum(map(chars, held)),
            'weights_updated': False}


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
    ap.add_argument('--format', choices=('chat', 'text'), default='chat',
                    help='chat SFT or textbook language-model training; never invents Q&A')
    ap.add_argument('--validation-data', help='separately prepared validation JSONL; never use the test set')
    ap.add_argument('--prepare-only', action='store_true', help='validate/summarize without model downloads or GPU work')
    ap.add_argument('--max-steps', type=int, default=-1, help='bound a first GPU experiment; -1 uses epochs')
    a = ap.parse_args()

    train, held = load(a.data, a.holdout, a.format, a.validation_data)
    summary = dataset_summary(train, held, a.format)
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    if a.prepare_only:
        return
    repository = Path(__file__).resolve().parents[2]
    if Path(a.out).resolve().is_relative_to(repository):
        raise ValueError('save private adapters and training artifacts outside the source repository')

    from unsloth import FastLanguageModel, is_bfloat16_supported
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    model, tok = FastLanguageModel.from_pretrained(BASES[a.base], max_seq_length=a.max_len, load_in_4bit=True)
    model = FastLanguageModel.get_peft_model(model, r=a.rank, lora_alpha=a.rank * 2, lora_dropout=0,
                                             target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj'])
    def fmt(rows):
        return Dataset.from_list([{'text': (r['text'] + (tok.eos_token or '') if a.format == 'text'
                                           else tok.apply_chat_template(r['messages'], tokenize=False))} for r in rows])
    bf16 = is_bfloat16_supported()
    trainer = SFTTrainer(model=model, processing_class=tok, train_dataset=fmt(train), eval_dataset=fmt(held) if held else None,
                         args=SFTConfig(output_dir=a.out + '-run', num_train_epochs=a.epochs, learning_rate=a.lr,
                                        per_device_train_batch_size=1, gradient_accumulation_steps=8, warmup_ratio=0.05,
                                        lr_scheduler_type='cosine', logging_steps=5, save_strategy='no', bf16=bf16, fp16=not bf16,
                                        dataset_text_field='text', max_length=a.max_len, max_steps=a.max_steps,
                                        eval_strategy='epoch' if held else 'no'))
    trainer.train()
    model.save_pretrained(a.out)      # adapter_config.json + adapter_model.safetensors
    tok.save_pretrained(a.out)
    summary['weights_updated'] = True
    summary['base'] = BASES[a.base]
    Path(a.out, 'hasla_training_manifest.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('adapter saved to', a.out)


if __name__ == '__main__':
    main()

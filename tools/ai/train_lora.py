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

Chat uses Gemma MoE BF16 LoRA (FastModel, rank 8 initially). Solver uses QwQ 4-bit QLoRA
(FastLanguageModel, rank 16). Role-specific loading contracts live in role_config.py.
Chat accepts only structured conversations; solver also accepts private textbook text.

Not run in this repository's CI (it needs a GPU); check the loss and try the adapter on a few held-out questions
before switching the site to it.
"""
import argparse
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import re
import time

from role_config import BASES, get_role_config, validate_role_format


def valid_messages(messages):
    if not isinstance(messages, list) or not messages:
        return False
    expected = 'user'
    for index, message in enumerate(messages):
        if not isinstance(message, dict) or not isinstance(message.get('content'), str) or not message['content'].strip():
            return False
        if index == 0 and message.get('role') == 'system':
            continue
        if message.get('role') != expected:
            return False
        expected = 'assistant' if expected == 'user' else 'user'
    return messages[-1].get('role') == 'assistant' and any(m.get('role') == 'user' for m in messages)


def read_rows(path, data_format='chat', role=None):
    """Validate private input without printing any training text."""
    if data_format not in ('chat', 'text'):
        raise ValueError('unknown training data format')
    if role is not None:
        validate_role_format(role, data_format)
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
            if not isinstance(row.get('metadata', {}), dict):
                raise ValueError(f'invalid metadata at line {number}')
            if data_format == 'text':
                valid = (isinstance(row.get('text'), str) and bool(row['text'].strip())
                         and 'messages' not in row)
            else:
                messages = row.get('messages')
                valid = valid_messages(messages) and 'text' not in row
            if not valid:
                raise ValueError(f'invalid {data_format} record at line {number}')
            if role == 'solver' and data_format == 'chat':
                reviewed = row.get('review_status') or row.get('metadata', {}).get('review_status')
                if reviewed not in ('verified', 'approved'):
                    raise ValueError(f'solver chat requires a reviewed solution at line {number}')
            labels = [v for v in (row.get('split'), row.get('metadata', {}).get('split')) if v is not None]
            if len(set(labels)) > 1:
                raise ValueError(f'conflicting split metadata at line {number}')
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


def load(path, holdout=0.05, data_format='chat', validation_path=None, role=None):
    """Respect corpus splits; legacy input is held out by source/conversation, never by row."""
    if not 0 <= holdout < 1:
        raise ValueError('holdout must be in [0, 1)')
    rows = read_rows(path, data_format, role)
    assigned = any(split_of(r) is not None for r in rows)
    if assigned and any(split_of(r) not in ('train', 'validation', 'test') for r in rows):
        raise ValueError('all records must have a valid split when any record has one')
    if validation_path:
        if assigned and any(split_of(r) != 'train' for r in rows):
            raise ValueError('training input contains a non-train split')
        train, held = rows, read_rows(validation_path, data_format, role)
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
    test = [r for r in rows if split_of(r) == 'test'] if assigned else []
    if test:
        if {group_of(r, data_format) for r in train + held} & {group_of(r, data_format) for r in test}:
            raise ValueError('a source/conversation group overlaps the held-out test set')
        if {fingerprint(r, data_format) for r in train + held} & {fingerprint(r, data_format) for r in test}:
            raise ValueError('duplicate content overlaps the held-out test set')
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


def file_sha256(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def private_adapter_output(path, trainer_path=__file__):
    target = Path(path).resolve()
    script = Path(trainer_path).resolve()
    # A pinned standalone trainer on a Pod has no repository ancestors.
    # Inferring parents[2] there would identify '/' as the repository.
    if any((parent / '.git').exists() for parent in (target, *target.parents)):
        raise ValueError('save private adapters outside every source repository')
    if script.parent.name == 'ai' and script.parent.parent.name == 'tools':
        repository = script.parent.parent.parent
        if target.is_relative_to(repository):
            raise ValueError('save private adapters outside the source repository')
    return target


def selected_dataset_sha256(rows, data_format):
    return hashlib.sha256(('\n'.join(fingerprint(row, data_format) for row in rows) + '\n').encode()).hexdigest()


def loader_kwargs(config, max_length, bf16_dtype):
    options = {'model_name': config['base_model'], 'max_seq_length': max_length,
               'load_in_4bit': config['load_in_4bit'], 'load_in_16bit': config['load_in_16bit'],
               'full_finetuning': False}
    if config['precision'] == 'bf16':
        options['dtype'] = bf16_dtype
    return options


def choose_loader(unsloth_module, config):
    return getattr(unsloth_module, config['loader'])


def peft_kwargs(config, rank, max_length):
    options = {'r': rank, 'lora_alpha': rank, 'lora_dropout': 0, 'bias': 'none',
               'use_gradient_checkpointing': 'unsloth', 'random_state': 3407}
    if config['loader'] == 'FastModel':
        options.update(finetune_vision_layers=False, finetune_language_layers=True,
                       finetune_attention_modules=True, finetune_mlp_modules=True)
    else:
        options.update(target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj',
                                       'gate_proj', 'up_proj', 'down_proj'], max_seq_length=max_length)
    return options


def assistant_loss_support(processor, template_provider=None):
    """Use only library-provided generation masks, verified on nonsensitive text.

    TRL's documented get_training_chat_template recognizes supported families.
    We never insert custom Jinja spans or infer token boundaries ourselves.
    """
    template = getattr(processor, 'chat_template', None)
    if not isinstance(template, str) and hasattr(processor, 'tokenizer'):
        template = getattr(processor.tokenizer, 'chat_template', None)
    patched = None
    if template_provider is not None:
        try:
            patched = template_provider(processor)
        except (ValueError, TypeError, AttributeError):
            patched = None
    candidate = patched if isinstance(patched, str) else template
    if not isinstance(candidate, str) or not re.search(r'{%-?\s*generation\s*-?%}', candidate) or not re.search(
            r'{%-?\s*endgeneration\s*-?%}', candidate):
        return False, None, 'template_has_no_generation_markers'
    sample = [{'role': 'user', 'content': 'Synthetic mask check question.'},
              {'role': 'assistant', 'content': 'Synthetic mask check answer.'}]
    try:
        encoded = processor.apply_chat_template(sample, tokenize=True, return_dict=True,
                    add_generation_prompt=False, return_assistant_tokens_mask=True, chat_template=candidate)
        mask, tokens = encoded.get('assistant_masks'), encoded.get('input_ids')
        if not isinstance(mask, (list, tuple)) or not isinstance(tokens, (list, tuple)) or len(mask) != len(tokens):
            return False, None, 'generation_mask_not_available'
        if not mask or not all(value in (0, 1) for value in mask) or not 0 < sum(mask) < len(mask):
            return False, None, 'generation_mask_not_selective'
    except Exception:
        return False, None, 'generation_mask_check_failed'
    return True, candidate, 'library_generation_mask_verified'


def safe_loss_metrics(history, final_metrics=None):
    """Copy only finite scalar loss values, never arbitrary trainer log fields."""
    result = {'train_loss': None, 'eval_loss': None}
    for record in list(history or []) + ([final_metrics] if isinstance(final_metrics, dict) else []):
        if not isinstance(record, dict):
            continue
        for source, target in (('loss', 'train_loss'), ('train_loss', 'train_loss'), ('eval_loss', 'eval_loss')):
            value = record.get(source)
            if type(value) in (int, float) and math.isfinite(value):
                result[target] = float(value)
    return result


def warmup_policy(max_steps):
    """Keep a one/two-step pilot's first optimizer update at a positive LR.

    HF rounds proportional warmup up: 5% of one step becomes one warmup step,
    and its cosine scheduler initializes that sole optimizer update at LR=0.
    Bounded runs therefore use explicit integer steps, with no warmup for tiny
    pilots. Unbounded epoch mode retains the original 5% warmup policy.
    """
    if type(max_steps) is not int or max_steps == 0 or max_steps < -1:
        raise ValueError('invalid maximum step count for warmup')
    if max_steps == -1:
        return {'warmup_steps': None, 'warmup_ratio': 0.05, 'warmup_mode': 'epoch_ratio'}
    count = 0 if max_steps <= 2 else min(max_steps - 1, math.ceil(0.05 * max_steps))
    return {'warmup_steps': count, 'warmup_ratio': None, 'warmup_mode': 'bounded_integer'}


def warmup_training_options(max_steps, config_type):
    policy = warmup_policy(max_steps)
    if policy['warmup_steps'] is not None:
        return {'warmup_steps': policy['warmup_steps']}
    # Current HF uses fractional warmup_steps; older TrainingArguments/TRL
    # releases expose warmup_ratio explicitly. Preserve epoch-mode semantics
    # through the installed API rather than sending an unsupported keyword.
    if 'warmup_ratio' in inspect.signature(config_type).parameters:
        return {'warmup_ratio': policy['warmup_ratio']}
    return {'warmup_steps': policy['warmup_ratio']}


def progress_callback(callback_type, path, *, started, wall_seconds=None, clock=time.monotonic):
    """Expose only atomic numeric progress, never text or arbitrary trainer logs."""
    path = Path(path)
    if wall_seconds is not None and (type(wall_seconds) is not int or wall_seconds < 30):
        raise ValueError('invalid training wall-time allowance')

    class Progress(callback_type):
        def write(self, state, phase, logs=None):
            step = getattr(state, 'global_step', 0)
            maximum = getattr(state, 'max_steps', 0)
            if type(step) is not int or type(maximum) is not int or not 0 <= step <= maximum:
                raise ValueError('invalid trainer progress')
            value = {'schema_version': 1, 'phase': phase, 'steps_completed': step,
                     'max_steps': maximum, 'elapsed_seconds': max(0, int(clock() - started))}
            value.update({key: number for key, number in safe_loss_metrics([logs or {}]).items()
                          if number is not None})
            temporary = path.with_name(path.name + '.tmp')
            temporary.write_text(json.dumps(value, allow_nan=False), encoding='utf8')
            os.replace(temporary, path)

        def on_train_begin(self, args, state, control, **kwargs):
            self.write(state, 'training')

        def on_step_end(self, args, state, control, **kwargs):
            self.write(state, 'training')
            if wall_seconds is not None and state.global_step > 0 and clock() - started >= wall_seconds:
                control.should_training_stop = True
            return control

        def on_log(self, args, state, control, logs=None, **kwargs):
            self.write(state, 'training', logs)

        def on_train_end(self, args, state, control, **kwargs):
            self.write(state, 'training_ended')

    return Progress()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', choices=BASES, default='chat')
    ap.add_argument('data')
    ap.add_argument('out')
    ap.add_argument('--rank', type=int)
    ap.add_argument('--epochs', type=float, default=2)
    ap.add_argument('--lr', type=float, default=1e-4)
    ap.add_argument('--max-len', type=int)
    ap.add_argument('--holdout', type=float, default=0.05)
    ap.add_argument('--format', choices=('chat', 'text'), default='chat',
                    help='chat SFT or textbook language-model training; never invents Q&A')
    ap.add_argument('--validation-data', help='separately prepared validation JSONL; never use the test set')
    ap.add_argument('--prepare-only', action='store_true', help='validate/summarize without model downloads or GPU work')
    ap.add_argument('--max-steps', type=int, default=-1, help='bound a first GPU experiment; -1 uses epochs')
    ap.add_argument('--progress-json', help='private numeric-only progress file for the supervising worker')
    ap.add_argument('--train-wall-seconds', type=int, help='stop cleanly after a completed optimizer step, leaving time to save')
    ap.add_argument('--assistant-only-loss', choices=('auto', 'required', 'off'), default='auto',
                    help='use only officially supported generation masks for chat; never handcraft masks')
    a = ap.parse_args(argv)
    config = validate_role_format(a.base, a.format)
    a.rank = config['default_rank'] if a.rank is None else a.rank
    a.max_len = config['max_length'] if a.max_len is None else a.max_len
    if not 1 <= a.rank <= 32 or a.max_len < 1 or a.max_steps == 0 or a.max_steps < -1 or a.epochs <= 0 or a.lr <= 0:
        ap.error('invalid training hyperparameters')
    if a.train_wall_seconds is not None and (a.train_wall_seconds < 30 or not a.progress_json):
        ap.error('a wall-time allowance requires private progress output and at least 30 seconds')

    train, held = load(a.data, a.holdout, a.format, a.validation_data, role=a.base)
    summary = dataset_summary(train, held, a.format)
    summary.update(role=a.base, base=config['base_model'], base_model=config['base_model'],
                   precision=config['precision'], training_method=config['training_method'], loader=config['loader'],
                   rank=a.rank, max_length=a.max_len, max_steps=a.max_steps, steps_completed=0,
                   epochs=a.epochs, learning_rate=a.lr, training_sha256=file_sha256(a.data),
                   validation_sha256=file_sha256(a.validation_data) if a.validation_data else None,
                   dataset_sha256=selected_dataset_sha256(train, a.format),
                   validation_dataset_sha256=selected_dataset_sha256(held, a.format) if held else None,
                   assistant_only_loss=False, assistant_loss_status='not_checked_in_prepare_only',
                   test_records_used=0, train_loss=None, eval_loss=None)
    summary.update(warmup_policy(a.max_steps))
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    if a.prepare_only:
        return
    private_adapter_output(a.out)
    if a.progress_json:
        private_adapter_output(a.progress_json)
    started = time.monotonic()

    import unsloth
    import torch
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    bf16 = unsloth.is_bfloat16_supported()
    if config['precision'] == 'bf16' and not bf16:
        raise ValueError('chat BF16 LoRA requires a BF16-capable GPU; precision is not downgraded automatically')
    loader = choose_loader(unsloth, config)
    model, tok = loader.from_pretrained(**loader_kwargs(config, a.max_len, torch.bfloat16))
    model = loader.get_peft_model(model, **peft_kwargs(config, a.rank, a.max_len))
    mask_enabled, patched_template, mask_reason = False, None, 'plain_text_full_sequence_loss'
    if a.format == 'chat' and a.assistant_only_loss != 'off':
        try:
            from trl import get_training_chat_template
        except ImportError:
            get_training_chat_template = None
        mask_enabled, patched_template, mask_reason = assistant_loss_support(tok, get_training_chat_template)
        if mask_enabled and 'assistant_only_loss' not in inspect.signature(SFTConfig).parameters:
            mask_enabled, patched_template, mask_reason = False, None, 'installed_trl_has_no_assistant_only_loss'
        if a.assistant_only_loss == 'required' and not mask_enabled:
            raise ValueError('official assistant-only generation mask is unavailable')
    elif a.format == 'chat':
        mask_reason = 'explicit_full_sequence_loss'
    if mask_enabled and patched_template is not None:
        tok.chat_template = patched_template
        if hasattr(tok, 'tokenizer'):
            tok.tokenizer.chat_template = patched_template
    summary.update(assistant_only_loss=mask_enabled, assistant_loss_status=mask_reason)
    def fmt(rows):
        if a.format == 'chat':
            return Dataset.from_list([{'messages': r['messages']} for r in rows])
        return Dataset.from_list([{'text': r['text'] + (tok.eos_token or '')} for r in rows])
    training_options = dict(output_dir=a.out + '-run', num_train_epochs=a.epochs, learning_rate=a.lr,
                           per_device_train_batch_size=1, gradient_accumulation_steps=8,
                           lr_scheduler_type='cosine', logging_steps=5, save_strategy='no', bf16=bf16, fp16=not bf16,
                           dataset_text_field='text', max_length=a.max_len, max_steps=a.max_steps,
                           eval_strategy='epoch' if held else 'no', report_to='none')
    training_options.update(warmup_training_options(a.max_steps, SFTConfig))
    if 'assistant_only_loss' in inspect.signature(SFTConfig).parameters:
        training_options['assistant_only_loss'] = mask_enabled
    trainer = SFTTrainer(model=model, processing_class=tok, train_dataset=fmt(train), eval_dataset=fmt(held) if held else None,
                         args=SFTConfig(**training_options))
    if a.progress_json:
        from transformers import TrainerCallback
        trainer.add_callback(progress_callback(TrainerCallback, a.progress_json, started=started,
                                              wall_seconds=a.train_wall_seconds))
    training_result = trainer.train()
    summary['steps_completed'] = int(trainer.state.global_step)
    summary['scheduled_steps_completed'] = a.max_steps > 0 and summary['steps_completed'] == a.max_steps
    if summary['steps_completed'] < 1:
        raise ValueError('trainer completed no optimizer steps')
    if a.max_steps > 0 and summary['steps_completed'] > a.max_steps:
        raise ValueError('trainer exceeded its requested optimizer-step limit')
    if a.max_steps == -1:
        scheduled_steps = getattr(trainer.state, 'max_steps', None)
        if type(scheduled_steps) is int and scheduled_steps > 0:
            summary['warmup_steps'] = math.ceil(0.05 * scheduled_steps)
    summary.update(safe_loss_metrics(getattr(trainer.state, 'log_history', []),
                                    getattr(training_result, 'metrics', None)))
    model.save_pretrained(a.out)      # adapter_config.json + adapter_model.safetensors
    tok.save_pretrained(a.out)
    summary['weights_updated'] = True
    Path(a.out, 'hasla_training_manifest.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('adapter saved to', a.out)


if __name__ == '__main__':
    main()

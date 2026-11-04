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

from role_config import BASES, GEMMA_26B_QLORA_V1, QWQ_32B_QLORA_48GB_V1, get_role_config, validate_role_format


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
    if config.get('training_profile') in (GEMMA_26B_QLORA_V1, QWQ_32B_QLORA_48GB_V1):
        options.update(dtype=bf16_dtype, fast_inference=False, device_map={'': 0}, use_exact_model_name=True)
    if config.get('training_profile') == QWQ_32B_QLORA_48GB_V1:
        options['offload_embedding'] = False
    return options


def gemma_quantized_expert_proof(model, params4bit_type):
    """Inspect actual packed experts; a requested quantization flag is no proof."""
    blocks = [m for m in model.modules() if type(m).__name__ == 'Gemma4TextExperts']
    if len(blocks) != 30 or not isinstance(params4bit_type, type):
        raise ValueError('Gemma QLoRA requires all 30 recognized expert blocks')
    expected = {'gate_up_proj': (128, 1408, 2816), 'down_proj': (128, 2816, 704)}
    count = 0
    for block in blocks:
        for name, shape in expected.items():
            weight = getattr(block, name, None)
            state = getattr(weight, 'quant_state', None)
            logical = getattr(weight, '_original_shape', None)
            if logical is None:
                logical = getattr(state, 'shape', None)
            if (not isinstance(weight, params4bit_type) or state is None or tuple(logical or ()) != shape
                    or getattr(state, 'quant_type', None) != 'nf4' or weight.requires_grad
                    or weight.numel() * weight.element_size() > math.prod(shape)
                    or getattr(weight.device, 'type', None) != 'cuda'
                    or getattr(weight.device, 'index', None) != 0):
                raise ValueError('Gemma expert weights are not verified packed frozen CUDA NF4')
            count += 1
    return {'expert_quantization_verified': True, 'expert_blocks': len(blocks), 'quantized_expert_tensors': count}


def gemma_moe_patch_provenance(module, installed_version):
    """Record actual installed source bytes; do not invent a preapproved pin."""
    if not callable(getattr(module, 'replace_expert_params_with_bnb_params', None)):
        raise ValueError('required Gemma MoE NF4 quantizer patch is unavailable')
    source = Path(module.__file__)
    if (source.is_symlink() or not source.is_file() or source.suffix != '.py'
            or not 0 < source.stat().st_size <= 1024**2
            or not isinstance(installed_version, str) or not re.fullmatch(r'[0-9A-Za-z.+_-]{1,80}', installed_version)):
        raise ValueError('Gemma MoE quantizer source provenance is unavailable')
    return {'expert_quantizer_module_sha256': file_sha256(source), 'unsloth_zoo_version': installed_version,
            'expert_quantizer_upstream_fix': '9adee9372d5d86749e757d5a91c6bfa30c2ff674'}


def qwq_quantized_linear_proof(model, params4bit_type):
    """Verify dense QwQ's actual frozen CUDA NF4 projections, not a loader flag.

    This opt-in trial uses standard NF4 of the exact Qwen base. Dynamic quants
    that leave a projection in BF16 are deliberately outside this contract.
    First-step memory evidence is still required; CPU checks prove no GPU fit.
    """
    config = model.config
    expected_config = {'model_type': 'qwen2', 'num_hidden_layers': 64, 'hidden_size': 5120,
                       'intermediate_size': 27648, 'num_attention_heads': 40, 'num_key_value_heads': 8}
    if not isinstance(params4bit_type, type) or any(getattr(config, k, None) != v for k, v in expected_config.items()):
        raise ValueError('QwQ low-memory profile requires the exact dense 32B architecture')
    shapes = {'self_attn.q_proj': (5120, 5120), 'self_attn.k_proj': (1024, 5120),
              'self_attn.v_proj': (1024, 5120), 'self_attn.o_proj': (5120, 5120),
              'mlp.gate_proj': (27648, 5120), 'mlp.up_proj': (27648, 5120), 'mlp.down_proj': (5120, 27648)}
    found, weights = set(), set()
    for name, module in model.named_modules():
        match = re.search(r'(?:^|\.)layers\.([0-9]+)\.(self_attn\.[qkvo]_proj|mlp\.(?:gate|up|down)_proj)$', name)
        if not match:
            continue
        key = (int(match[1]), match[2])
        weight = getattr(module, 'weight', None)
        state = getattr(weight, 'quant_state', None)
        shape = shapes[match[2]]
        logical = getattr(state, 'shape', None)
        if (key in found or not 0 <= key[0] < 64 or id(weight) in weights
                or not isinstance(weight, params4bit_type) or state is None or tuple(logical or ()) != shape
                or getattr(state, 'quant_type', None) != 'nf4' or weight.requires_grad
                or weight.numel() * weight.element_size() > math.prod(shape)
                or getattr(weight.device, 'type', None) != 'cuda' or getattr(weight.device, 'index', None) != 0):
            raise ValueError('QwQ projections are not verified packed frozen CUDA NF4')
        found.add(key)
        weights.add(id(weight))
    if found != {(layer, name) for layer in range(64) for name in shapes}:
        raise ValueError('QwQ low-memory profile requires all 448 dense NF4 projections')
    validate_loaded_adapter_trainability(model)
    return {'dense_quantization_verified': True, 'dense_layers': 64, 'quantized_linear_tensors': len(found),
            'base_parameters_frozen': True}


def gemma_single_gpu_proof(torch_module, model=None):
    cuda = torch_module.cuda
    if not cuda.is_available() or cuda.device_count() != 1:
        raise ValueError('Gemma QLoRA profile requires exactly one CUDA GPU')
    props = cuda.get_device_properties(0)
    names = ('NVIDIA A100-PCIE-40GB', 'NVIDIA L40S', 'NVIDIA L40', 'NVIDIA A40')
    if (props.name not in names or type(props.total_memory) is not int
            or not 37 * 1024**3 <= props.total_memory <= 49 * 1024**3):
        raise ValueError('Gemma QLoRA GPU is outside the approved 40/48GB hardware')
    if model is not None:
        mapping = getattr(model, 'hf_device_map', None)
        if mapping is not None and (not isinstance(mapping, dict) or any(str(v) not in ('0', 'cuda', 'cuda:0') for v in mapping.values())):
            raise ValueError('Gemma QLoRA cannot silently offload model weights')
        if any(getattr(p.device, 'type', None) != 'cuda' or getattr(p.device, 'index', None) != 0
               for p in model.parameters()):
            raise ValueError('Gemma QLoRA model parameters must stay on CUDA GPU zero')
    return {'gpu_count': 1, 'gpu_name': props.name, 'physical_vram_bytes': props.total_memory,
            'cpu_or_disk_offload_used': False}


def gemma_first_step_callback(callback_type, summary, torch_module):
    class Proof(callback_type):
        def on_step_end(self, args, state, control, **kwargs):
            if state.global_step >= 1 and not summary.get('first_optimizer_step_completed'):
                allocated = torch_module.cuda.max_memory_allocated(0)
                reserved = torch_module.cuda.max_memory_reserved(0)
                if (type(allocated) is not int or type(reserved) is not int
                        or not 0 < allocated <= reserved <= summary['physical_vram_bytes']):
                    raise ValueError('invalid first optimizer-step GPU memory proof')
                summary.update(first_optimizer_step_completed=True,
                               first_step_peak_allocated_bytes=allocated, first_step_peak_reserved_bytes=reserved)
            return control
    return Proof()


def initial_adapter(path, config, rank, output):
    """Accept only a private, unchanged QwQ adapter; reset no model weights."""
    if config['role'] != 'solver' or rank != config['default_rank']:
        raise ValueError('continued adapter training requires the fixed solver contract')
    path = private_adapter_output(path)
    output = private_adapter_output(output)
    if path.is_relative_to(output) or output.is_relative_to(path) or not path.is_dir():
        raise ValueError('initial adapter and output directories must be separate')
    for name, limit in (('adapter_config.json', 1024**2), ('adapter_model.safetensors', 2 * 1024**3)):
        file = path / name
        if file.is_symlink() or not file.is_file() or not 0 < file.stat().st_size <= limit:
            raise ValueError('initial adapter file is missing or invalid')
    peft = json.loads((path / 'adapter_config.json').read_text(encoding='utf8'))
    if (peft.get('base_model_name_or_path') not in config['base_aliases'] or peft.get('peft_type') != 'LORA'
            or type(peft.get('r')) is not int or peft['r'] != rank or peft.get('rank_pattern')):
        raise ValueError('initial adapter does not match the fixed solver contract')
    return path, file_sha256(path / 'adapter_model.safetensors')


def validate_loaded_adapter_trainability(model):
    active = []
    for name, parameter in model.named_parameters():
        if parameter.requires_grad:
            if not re.search(r'(^|\.)lora_[AB](?=\.|$)', name):
                raise ValueError('continuation must freeze every base model parameter')
            active.append(name)
    if not any('.lora_A.' in '.' + name for name in active) or not any('.lora_B.' in '.' + name for name in active):
        raise ValueError('loaded adapter has no trainable LoRA A/B parameters')


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


def assistant_loss_support(processor, template_provider=None, probe=None):
    """Use only library-provided generation masks, verified on nonsensitive text.

    TRL's documented get_training_chat_template recognizes supported families.
    We never insert custom Jinja spans or infer token boundaries ourselves.
    """
    probe = {} if probe is None else probe
    probe.update(mask_probe_dimensions=0, mask_probe_batch_size=0,
                 mask_probe_token_count=0, mask_probe_assistant_tokens=0)
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
                    add_generation_prompt=False, return_assistant_tokens_mask=True, return_tensors=None, chat_template=candidate)
        mask, tokens = encoded.get('assistant_masks'), encoded.get('input_ids')
        if not isinstance(mask, (list, tuple)) or not isinstance(tokens, (list, tuple)):
            return False, None, 'generation_mask_not_available'
        nested = any(isinstance(value, (list, tuple)) for value in [*mask, *tokens])
        if nested:
            probe.update(mask_probe_dimensions=2, mask_probe_batch_size=min(len(tokens), 4096))
            if len(mask) != 1 or len(tokens) != 1 or not isinstance(mask[0], (list, tuple)) or not isinstance(tokens[0], (list, tuple)):
                return False, None, 'generation_mask_shape_invalid'
            mask, tokens = mask[0], tokens[0]
        else:
            probe.update(mask_probe_dimensions=1, mask_probe_batch_size=1)
        if (len(mask) != len(tokens) or len(tokens) > 4096
                or any(type(value) is not int or value < 0 for value in tokens)
                or any(type(value) is not int or value not in (0, 1) for value in mask)):
            return False, None, 'generation_mask_shape_invalid'
        probe.update(mask_probe_token_count=len(tokens), mask_probe_assistant_tokens=sum(mask))
        if not mask or not 0 < sum(mask) < len(mask):
            return False, None, 'generation_mask_not_selective'
    except Exception:
        return False, None, 'generation_mask_check_failed'
    return True, candidate, 'library_generation_mask_verified'


def label_diagnostics(processor, enabled, reason, probe, data_format):
    """Only hashes, fixed statuses, class names and numeric synthetic-probe counts."""
    tokenizer = getattr(processor, 'tokenizer', processor)
    template = getattr(processor, 'chat_template', None)
    if template is None:
        template = getattr(tokenizer, 'chat_template', None)
    if isinstance(template, dict):
        template = template.get('default')
    if data_format == 'chat' and (not isinstance(template, str) or not 0 < len(template.encode()) <= 256 * 1024):
        raise ValueError('selected chat template cannot be identified')
    def class_name(value):
        name = type(value).__name__
        return name if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,79}', name) else 'unknown'
    return {'version': 1, 'assistant_only_loss': enabled, 'assistant_loss_status': reason,
            'selected_template_sha256': hashlib.sha256(template.encode()).hexdigest() if isinstance(template, str) else None,
            'processor_class': class_name(processor), 'tokenizer_class': class_name(tokenizer), **probe}


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
    ap.add_argument('--training-profile', choices=(GEMMA_26B_QLORA_V1, QWQ_32B_QLORA_48GB_V1), default=None)
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
    ap.add_argument('--resume-adapter', help='continue a pinned private solver adapter with a fresh optimizer')
    ap.add_argument('--assistant-only-loss', choices=('auto', 'required', 'off'), default='auto',
                    help='use only officially supported generation masks for chat; never handcraft masks')
    a = ap.parse_args(argv)
    config = validate_role_format(a.base, a.format, a.training_profile)
    a.rank = config['default_rank'] if a.rank is None else a.rank
    a.max_len = config['max_length'] if a.max_len is None else a.max_len
    if not 1 <= a.rank <= 32 or a.max_len < 1 or a.max_steps == 0 or a.max_steps < -1 or a.epochs <= 0 or a.lr <= 0:
        ap.error('invalid training hyperparameters')
    if a.train_wall_seconds is not None and (a.train_wall_seconds < 30 or not a.progress_json):
        ap.error('a wall-time allowance requires private progress output and at least 30 seconds')
    if a.training_profile and (a.rank != config['default_rank'] or a.max_len != 1024):
        ap.error('low-memory QLoRA profile requires its fixed rank and length1024')

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
    if a.training_profile:
        summary['training_profile'] = a.training_profile
    initial_path, initial_sha = initial_adapter(a.resume_adapter, config, a.rank, a.out) if a.resume_adapter else (None, None)
    initial_config_sha = file_sha256(initial_path / 'adapter_config.json') if initial_path else None
    summary.update(initial_adapter_model_sha256=initial_sha, initial_adapter_config_sha256=initial_config_sha,
                   optimizer_state_restored=False)
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
    if (config['precision'] == 'bf16' or a.training_profile) and not bf16:
        raise ValueError('this training contract requires a BF16-capable GPU; precision is not downgraded automatically')
    if a.training_profile:
        from bitsandbytes.nn import Params4bit
        if a.training_profile == GEMMA_26B_QLORA_V1:
            from importlib.metadata import version
            from unsloth_zoo.temporary_patches import moe_utils_bnb4bit
            summary.update(gemma_moe_patch_provenance(moe_utils_bnb4bit, version('unsloth_zoo')))
        summary.update(gemma_single_gpu_proof(torch))
        torch.cuda.reset_peak_memory_stats(0)
    loader = choose_loader(unsloth, config)
    options = loader_kwargs(config, a.max_len, torch.bfloat16)
    canonical_continuation = initial_path is not None and a.training_profile == QWQ_32B_QLORA_48GB_V1
    if initial_path and not canonical_continuation:
        options['model_name'] = str(initial_path)
    model, tok = loader.from_pretrained(**options)
    if canonical_continuation:
        # An adapter's recorded alias may name a dynamic quant. Load the exact
        # Qwen base above, then attach the unchanged original private adapter.
        # Match Unsloth's own adapter loader: PEFT attach followed by its k-bit
        # training patch, never get_peft_model (which could initialize anew).
        # https://github.com/unslothai/unsloth/blob/main/unsloth/models/loader.py
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, str(initial_path), is_trainable=True, local_files_only=True)
        model = loader.patch_peft_model(model, use_gradient_checkpointing='unsloth')
        if (file_sha256(initial_path / 'adapter_config.json') != initial_config_sha
                or file_sha256(initial_path / 'adapter_model.safetensors') != initial_sha):
            raise ValueError('initial adapter files changed while attaching continuation')
    if a.training_profile == GEMMA_26B_QLORA_V1:
        summary.update(gemma_single_gpu_proof(torch, model))
        summary.update(gemma_quantized_expert_proof(model, Params4bit))
    if initial_path:
        validate_loaded_adapter_trainability(model)
    else:
        model = loader.get_peft_model(model, **peft_kwargs(config, a.rank, a.max_len))
    if a.training_profile == QWQ_32B_QLORA_48GB_V1:
        summary.update(gemma_single_gpu_proof(torch, model))
        summary.update(qwq_quantized_linear_proof(model, Params4bit))
    mask_enabled, patched_template, mask_reason = False, None, 'plain_text_full_sequence_loss'
    mask_probe = {'mask_probe_dimensions': 0, 'mask_probe_batch_size': 0,
                  'mask_probe_token_count': 0, 'mask_probe_assistant_tokens': 0}
    if a.format == 'chat' and a.assistant_only_loss != 'off':
        try:
            from trl import get_training_chat_template
        except ImportError:
            get_training_chat_template = None
        mask_enabled, patched_template, mask_reason = assistant_loss_support(tok, get_training_chat_template, mask_probe)
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
    if a.training_profile == QWQ_32B_QLORA_48GB_V1:
        # Transformers otherwise defaults evaluation to a larger batch than
        # this bounded single-example training profile.
        training_options['per_device_eval_batch_size'] = 1
    if 'assistant_only_loss' in inspect.signature(SFTConfig).parameters:
        training_options['assistant_only_loss'] = mask_enabled
    trainer = SFTTrainer(model=model, processing_class=tok, train_dataset=fmt(train), eval_dataset=fmt(held) if held else None,
                         args=SFTConfig(**training_options))
    effective_mask = getattr(getattr(trainer, 'args', None), 'assistant_only_loss', mask_enabled)
    if type(effective_mask) is not bool or effective_mask != mask_enabled:
        raise ValueError('trainer assistant masking configuration changed unexpectedly')
    summary['label_diagnostics'] = label_diagnostics(getattr(trainer, 'processing_class', tok), effective_mask,
                                                     mask_reason, mask_probe, a.format)
    if mask_enabled and summary['label_diagnostics']['selected_template_sha256'] != hashlib.sha256(patched_template.encode()).hexdigest():
        raise ValueError('trainer changed the probed assistant-loss template')
    if a.training_profile:
        from transformers import TrainerCallback
        gemma_single_gpu_proof(torch, model)
        trainer.add_callback(gemma_first_step_callback(TrainerCallback, summary, torch))
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
    if a.training_profile and summary.get('first_optimizer_step_completed') is not True:
        raise ValueError('QLoRA first optimizer-step proof is missing')
    if a.max_steps == -1:
        scheduled_steps = getattr(trainer.state, 'max_steps', None)
        if type(scheduled_steps) is int and scheduled_steps > 0:
            summary['warmup_steps'] = math.ceil(0.05 * scheduled_steps)
    summary.update(safe_loss_metrics(getattr(trainer.state, 'log_history', []),
                                    getattr(training_result, 'metrics', None)))
    if initial_path and (file_sha256(initial_path / 'adapter_model.safetensors') != initial_sha
                         or file_sha256(initial_path / 'adapter_config.json') != initial_config_sha):
        raise ValueError('initial adapter file changed during continuation')
    model.save_pretrained(a.out)      # adapter_config.json + adapter_model.safetensors
    tok.save_pretrained(a.out)
    if initial_path and (file_sha256(initial_path / 'adapter_model.safetensors') != initial_sha
                         or file_sha256(initial_path / 'adapter_config.json') != initial_config_sha):
        raise ValueError('initial adapter file changed while saving continuation')
    summary['weights_updated'] = True
    Path(a.out, 'hasla_training_manifest.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('adapter saved to', a.out)


if __name__ == '__main__':
    main()

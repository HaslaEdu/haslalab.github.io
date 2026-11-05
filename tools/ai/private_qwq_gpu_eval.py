"""One-model, inference-only QwQ NF4 comparison. No GPU-provider API exists here.

The caller allocates and cleans up hardware. This worker accepts one fixed job,
uses one canonical foundation and one immutable adapter, and publishes only
post-thinking final answers in a private evaluation artifact. CPU evaluation
source files and their 1024-token plan are never modified.
"""
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import signal
import sys
import time

import private_resume_adapter as resume

FOUNDATION = "Qwen/QwQ-32B"
REVISION = "976055f8c83f394f35dbd3ab09a285a984907bd0"
COMPARISON_SHA = "280bfeef08d8bd9d26feddc784cf4724687373ae4c186302bc0d171b103298db"
RESUME_SHA = "e52f9e5c31d938c98b7f3215761e3a3ccee616c645b74bd4cfa899cb34b551af"
CONFIG_SHA = "61feaaef406a79c195ba8629921e99ad27753434c1e7bf60f5809cd73a86de68"
TOKENIZER_CONFIG_SHA = "ab43f460108ca40fbb09fa537696baf862b6a9b46a2c6688b9de711293e3ddc4"
CASE_SHA = "71645d51a6b4ebeefbba10cda43a9d6d58752c019fd5aae5e9c1a548f427f6b0"
ENTITY = "mimgyuson-haslaedu"
GIB = 1024**3
CONTEXT = 4096
MAX_NEW_TOKENS = 2048
SCRIPT_FILES = ("private_qwq_gpu_eval.py", "private_qwq_comparison.py", "private_resume_adapter.py",
                "private_verify_adapter.py", "role_config.py")
SOURCE = {
    "kind": "private_adapter_continuation", "version": 1, "role": "solver",
    "base_model": FOUNDATION, "rank": 16, "source_training_run_id": "41931877157",
    "prior_verification_run_id": "41943069583", "entity": ENTITY,
    "artifact": ENTITY + "/hasla-ai-private-training/hasla-private-books-41931877157-solver-lora:v0",
    "files": [
        {"name": "adapter_config.json", "bytes": 1322,
         "sha256": "1954f97392fb7b1873ad5f399febbb894a79a387b5dbf98785434d850a02801e"},
        {"name": "adapter_model.safetensors", "bytes": 536991984,
         "sha256": "5b4c2e755930a30298927cdf905fd158c4745473eea7c41f87630183729d0112"}],
    "adapter_inventory_sha256": "c295c61015ebc1d1b1e32cfe7f535c1336ba536c4902645146f15a5f0df5de8f",
}
# Public Hugging Face LFS metadata for exactly REVISION, not another quant repo.
_WEIGHT_ROWS = (
    (4891730992, "004d2070959177a0beeac5c01f4934fb5bb2c12ad36184dc58b5f23ab8f70f3a"),
    (4876059352, "20bdb326a9dc6cd8b6438584471967995ec4a5e905ed06ef82354c248a389d65"),
    (4876059384, "85ccdd3199b1fec121c0344b334342d945d4190305875619fea0c3db6da49109"),
    (4876059416, "0f105c2f63b39f327844cbb79997cc1cf9b72778d51a26bdd7f170683c3b2a26"),
    (4876059416, "47701383600a7476fd83a95d0954f8a08ba61e7e6cbe7d7c9ceae98cac32fac9"),
    (4876059416, "1656c1ba7072ef5b615cb927e6c9c67901387effe3dcf6ce6d0347d9af9e4776"),
    (4876059416, "12fedbbc4ba346d4400e8ab47b93333f46694b49354266a20ad831086badda48"),
    (4876059416, "b8d62faefa13bb43a049a4400f32774097c5567294b5173217c538c02fb0b167"),
    (4876059416, "30bdb6ea3dde6992437d078539faeb900001ffc81df85e31cd570b8a8473c299"),
    (4876059416, "bc1dde8498e337d943ece97c7e34a9128212c0b2a78e54544db70b180356fe6b"),
    (4876059416, "4d02e7eff51f87d899d814e4e626aa0b500c2ed66281338501a6cbd1c0e39948"),
    (4876059416, "1509466dac374077451838262cca4d09d79b78cfd390f4ecb24dbee83d4614e3"),
    (4876059416, "5e43e88f59bcdaedd173d60e76ef428583dac88bc864786e5d7ee9420edbb094"),
    (2123397800, "a567a635b6c4846070fff9d7b28823d7a332235d854e71d355e0140d2e9dcc2f"),
)
BASE_FILES = [{"name": f"model-{i:05d}-of-00014.safetensors", "bytes": size, "sha256": digest}
              for i, (size, digest) in enumerate(_WEIGHT_ROWS, 1)]


class EvaluationError(RuntimeError):
    """Fixed nonsensitive error codes only."""


def require(condition, code):
    if not condition:
        raise EvaluationError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def file_sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def comparison_module():
    path = Path(__file__).with_name("private_qwq_comparison.py")
    require(file_sha(path) == COMPARISON_SHA, "comparison_source_pin_mismatch")
    spec = importlib.util.spec_from_file_location("qwq_gpu_isolated_comparison_v2", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # This is a new module namespace; the CPU module's globals remain untouched.
    module.SETTINGS = {**module.SETTINGS, "max_new_tokens": MAX_NEW_TOKENS}
    require(module.build_plan()["case_set_sha256"] == CASE_SHA, "frozen_case_set_mismatch")
    return module


def plan(comparison):
    inner = comparison.build_plan(SOURCE["files"][1]["sha256"], SOURCE["files"][0]["sha256"])
    return {"version": 2, "kind": "private_qwq_gpu_nf4_comparison_plan",
            "execution_profile": "canonical_qwq_nf4_bf16_double_quant_v1",
            "comparison": inner, "foundation_revision": REVISION, "context": CONTEXT,
            "source_adapter": copy.deepcopy(SOURCE), "base_weight_inventory_sha256": digest(canonical(BASE_FILES)),
            "optimizer_steps": 0, "model_instances_at_once": 1,
            "interpretation": "same_canonical_nf4_inference_condition_not_bit_identical_training_claim"}


def evaluation_plan():
    """CPU-safe pure factory shared by provider parent and local controller."""
    return plan(comparison_module())


def validate_job(job, now=None):
    keys = {"version", "kind", "run_id", "code_commit", "runtime_seconds", "base_model", "rank",
            "source_adapter", "optimizer_steps", "script_sha256", "deadline_unix"}
    require(type(job) is dict and set(job) == keys and type(job["version"]) is int and job["version"] == 1
            and job["kind"] == "private_qwq_gpu_evaluation_job", "invalid_evaluation_job")
    require(type(job["run_id"]) is str and re.fullmatch(r"[1-9][0-9]{0,31}", job["run_id"])
            and type(job["code_commit"]) is str and re.fullmatch(r"[0-9a-f]{40}", job["code_commit"]),
            "invalid_evaluation_identity")
    require(type(job["runtime_seconds"]) is int and 120 <= job["runtime_seconds"] <= 2700,
            "evaluation_wall_cap_invalid")
    remaining = job["deadline_unix"] - (time.time() if now is None else now) if type(job["deadline_unix"]) is int else -1
    require(120 <= remaining <= 3600, "evaluation_absolute_deadline_invalid")
    require(job["base_model"] == FOUNDATION and type(job["rank"]) is int and job["rank"] == 16
            and job["source_adapter"] == SOURCE and type(job["optimizer_steps"]) is int
            and job["optimizer_steps"] == 0, "evaluation_cohort_or_training_mutation")
    pins = job["script_sha256"]
    require(type(pins) is dict and set(pins) == set(SCRIPT_FILES) and all(
        type(pins[name]) is str and re.fullmatch(r"[0-9a-f]{64}", pins[name]) and
        file_sha(Path(__file__).with_name(name)) == pins[name] for name in SCRIPT_FILES) and
        pins["private_qwq_comparison.py"] == COMPARISON_SHA and pins["private_resume_adapter.py"] == RESUME_SHA,
        "evaluation_script_pin_mismatch")
    return copy.deepcopy(job)


@contextmanager
def hard_wall(seconds):
    require(hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer"), "posix_wall_guard_required")
    def expired(_number, _frame):
        raise EvaluationError("evaluation_wall_cap_reached")
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def gpu_proof(torch, model=None):
    require(torch.cuda.is_available() and torch.cuda.device_count() == 1, "exactly_one_cuda_gpu_required")
    props = torch.cuda.get_device_properties(0)
    require(props.name == "NVIDIA A40"
            and type(props.total_memory) is int and 37 * GIB <= props.total_memory <= 49 * GIB,
            "gpu_outside_40_48gb_cohort")
    if model is not None:
        mapping = getattr(model, "hf_device_map", None)
        require(mapping is None or type(mapping) is dict and all(
            str(value) in {"0", "cuda", "cuda:0"} for value in mapping.values()), "cpu_or_disk_offload_forbidden")
        require(all(parameter.device.type == "cuda" and parameter.device.index == 0
                    and not parameter.requires_grad for parameter in model.parameters()),
                "model_must_be_frozen_on_cuda_zero")
    return {"gpu_count": 1, "gpu_name": props.name, "physical_vram_bytes": props.total_memory,
            "cpu_or_disk_offload_used": False}


def nf4_proof(model, params4bit, bf16, retained=None):
    config = model.config
    required = {"model_type": "qwen2", "num_hidden_layers": 64, "hidden_size": 5120,
                "intermediate_size": 27648, "num_attention_heads": 40, "num_key_value_heads": 8}
    require(all(getattr(config, key, None) == value for key, value in required.items()), "qwq_architecture_mismatch")
    shapes = {"self_attn.q_proj": (5120, 5120), "self_attn.k_proj": (1024, 5120),
              "self_attn.v_proj": (1024, 5120), "self_attn.o_proj": (5120, 5120),
              "mlp.gate_proj": (27648, 5120), "mlp.up_proj": (27648, 5120), "mlp.down_proj": (5120, 27648)}
    found = {}
    for name, module in model.named_modules():
        match = re.search(r"(?:^|\.)layers\.([0-9]+)\.(self_attn\.[qkvo]_proj|mlp\.(?:gate|up|down)_proj)$", name)
        if not match:
            continue
        key, weight = (int(match[1]), match[2]), getattr(module, "weight", None)
        # PEFT Linear4bit exposes weight but keeps compute_dtype on its wrapped
        # bitsandbytes layer. Verify that both paths identify the same weight.
        getter = getattr(module, "get_base_layer", None)
        base_layer = getter() if callable(getter) else module
        state = getattr(weight, "quant_state", None)
        shape = shapes[match[2]]
        require(key not in found and 0 <= key[0] < 64 and isinstance(weight, params4bit)
                and state is not None and tuple(getattr(state, "shape", ())) == shape
                and getattr(state, "quant_type", None) == "nf4" and getattr(state, "nested", None) is True
                and getattr(state, "state2", None) is not None and getattr(base_layer, "weight", None) is weight
                and getattr(base_layer, "compute_dtype", None) == bf16
                and weight.numel() * weight.element_size() <= math.prod(shape) and not weight.requires_grad
                and weight.device.type == "cuda" and weight.device.index == 0,
                "dense_projection_not_frozen_bf16_double_nf4")
        found[key] = weight
    require(set(found) == {(layer, name) for layer in range(64) for name in shapes}
            and len({id(value) for value in found.values()}) == 448, "all_448_nf4_projections_required")
    if retained is not None:
        require(set(retained) == set(found) and all(found[key] is retained[key] for key in found),
                "foundation_parameters_replaced")
    return {"dense_layers": 64, "quantized_linear_tensors": 448, "quant_type": "nf4",
            "double_quant": True, "compute_dtype": "bfloat16", "all_base_parameters_frozen": True}, found


def adapter_file_proof(directory):
    directory = Path(directory)
    for row in SOURCE["files"]:
        path = directory / row["name"]
        require(path.is_file() and not path.is_symlink() and path.stat().st_size == row["bytes"]
                and file_sha(path) == row["sha256"], "immutable_adapter_file_mismatch")
    value = resume._json((directory / "adapter_config.json").read_bytes())
    require(value.get("base_model_name_or_path") in resume.QWQ_BASES and type(value.get("r")) is int
            and value["r"] == 16 and value.get("peft_type") == "LORA" and not value.get("rank_pattern")
            and not value.get("use_dora", False), "adapter_configuration_mismatch")
    _, _, tensors, bs = resume._layout(directory / "adapter_model.safetensors", 16)
    require(len(tensors) == 896 and len(bs) == 448, "adapter_inventory_layout_mismatch")


def exact_loaded_adapter(model, directory, torch, safe_open):
    runtime = {}
    for name, parameter in model.named_parameters():
        if re.search(r"\.lora_[AB]\.", name):
            canonical_name = name.replace(".lora_A.default.", ".lora_A.").replace(".lora_B.default.", ".lora_B.")
            require(canonical_name not in runtime and not parameter.requires_grad, "loaded_adapter_names_invalid")
            runtime[canonical_name] = parameter
    with safe_open(str(Path(directory) / "adapter_model.safetensors"), framework="pt", device="cpu") as source:
        keys = set(source.keys())
        require(keys == set(runtime) and len(keys) == 896, "loaded_adapter_tensor_inventory_mismatch")
        for name in sorted(keys):
            original = source.get_tensor(name)
            current = runtime[name].detach().cpu()
            require(current.dtype == original.dtype and current.shape == original.shape
                    and bool(torch.isfinite(current).all()) and torch.equal(current, original),
                    "loaded_adapter_values_changed")
    return {"tensor_count": 896, "lora_pairs": 448, "loaded_values_equal_source": True,
            "source_model_sha256": SOURCE["files"][1]["sha256"], "optimizer_steps": 0}


def adapter_state(model, disabled):
    modules = [module for module in model.modules() if hasattr(module, "lora_A") and hasattr(module, "lora_B")
               and len(module.lora_A) and len(module.lora_B)]
    require(len(modules) == 448 and all(getattr(module, "disable_adapters", None) is disabled
            and not getattr(module, "merged", False) and not getattr(module, "merged_adapters", [])
            for module in modules), "adapter_enable_disable_state_unverified")


def loader_options(torch, quantization_config, cache_dir=None):
    return {"model_name": FOUNDATION, "revision": REVISION, "max_seq_length": CONTEXT,
            "load_in_4bit": True, "load_in_16bit": False, "dtype": torch.bfloat16,
            "quantization_config": quantization_config, "full_finetuning": False,
            "fast_inference": False, "device_map": {"": 0}, "use_exact_model_name": True,
            "offload_embedding": False, "trust_remote_code": False, "token": False,
            "cache_dir": cache_dir}


def package_versions(torch):
    names = ("unsloth", "torch", "transformers", "peft", "bitsandbytes", "accelerate",
             "huggingface_hub", "safetensors", "wandb")
    values = {name: importlib.metadata.version(name) for name in names}
    values["cuda_runtime"] = torch.version.cuda
    require(all(type(value) is str and re.fullmatch(r"[A-Za-z0-9.+_-]{1,80}", value)
                for value in values.values()), "runtime_package_version_invalid")
    return values


def private_clients(env):
    from private_verify_adapter import PrivateReader, credentials
    key = credentials(env)
    require(env.get("WANDB_ENTITY") == ENTITY, "private_entity_mismatch")
    reader = PrivateReader(key)
    def privacy(entity):
        require(entity == ENTITY, "private_entity_mismatch")
        reader.assert_private(entity)
        return {"entity": ENTITY, "project": resume.PROJECT, "access": "PRIVATE"}
    privacy(ENTITY)
    with resume._quiet():
        import wandb
        api = wandb.Api(api_key=key, timeout=60)
    return api, privacy, wandb


def materialize_base(hub, cache_dir):
    snapshot = Path(hub.snapshot_download(repo_id=FOUNDATION, revision=REVISION, token=False,
        cache_dir=cache_dir, allow_patterns=[row["name"] for row in BASE_FILES] +
        ["config.json", "tokenizer_config.json", "tokenizer.json", "vocab.json", "merges.txt",
         "generation_config.json", "model.safetensors.index.json"], max_workers=4))
    require(snapshot.name == REVISION, "foundation_snapshot_revision_mismatch")
    for row in BASE_FILES:
        path = snapshot / row["name"]
        require(path.is_file() and path.stat().st_size == row["bytes"] and file_sha(path) == row["sha256"],
                "foundation_weight_pin_mismatch")
    for name, pin in (("config.json", CONFIG_SHA), ("tokenizer_config.json", TOKENIZER_CONFIG_SHA)):
        require(file_sha(snapshot / name) == pin, "foundation_metadata_pin_mismatch")
    return snapshot


def deadline_criterion(torch, base_class, deadline, clock=time.monotonic):
    class Deadline(base_class):
        def __call__(self, input_ids, scores, **kwargs):
            return torch.full((input_ids.shape[0],), clock() >= deadline,
                              device=input_ids.device, dtype=torch.bool)
    return Deadline()


def generate_one(model, tokenizer, messages, mode, deadline, torch, stopping_class, stopping_list,
                 clock=time.monotonic):
    encoded = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                             return_tensors="pt", return_dict=True)
    prompt_length = encoded["input_ids"].shape[-1]
    require(encoded["input_ids"].shape[0] == 1 and prompt_length + MAX_NEW_TOKENS <= CONTEXT,
            "prompt_exceeds_frozen_context")
    rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    require(rendered.endswith("<|im_start|>assistant\n<think>\n"), "official_thinking_prefix_missing")
    encoded = {key: value.to("cuda:0") for key, value in encoded.items()}
    torch.manual_seed(20261105)
    torch.cuda.manual_seed_all(20261105)
    eos = model.generation_config.eos_token_id
    eos = [eos] if type(eos) is int else eos
    require(type(eos) is list and eos and all(type(value) is int and value > 0 for value in eos), "eos_ids_invalid")
    options = {"max_new_tokens": MAX_NEW_TOKENS, "do_sample": False, "num_beams": 1,
               "use_cache": True, "repetition_penalty": 1.0, "eos_token_id": eos,
               "pad_token_id": tokenizer.pad_token_id or eos[0],
               "stopping_criteria": stopping_list([deadline_criterion(torch, stopping_class, deadline, clock)])}
    context = model.disable_adapter() if mode == "base" else _enabled_adapter(model)
    try:
        with context:
            for parameter in model.parameters(): parameter.requires_grad_(False)
            adapter_state(model, mode == "base")
            with torch.inference_mode():
                generated = model.generate(**encoded, **options)
    finally:
        # PEFT re-enables adapter gradients while restoring active adapters.
        # Evaluation keeps both the foundation and loaded adapter immutable,
        # including when generation or context restoration raises.
        for parameter in model.parameters(): parameter.requires_grad_(False)
        adapter_state(model, False)
    ids = generated[0, prompt_length:].detach().cpu().tolist()
    reason = "timeout" if clock() >= deadline else "stop" if ids and ids[-1] in eos else "length"
    # Decoding only new tokens retains the official </think> boundary, while
    # special EOS tokens disappear. Raw reasoning is not persisted or logged.
    text = tokenizer.decode(ids, skip_special_tokens=True)
    return {"generated_text": text, "finish_reason": reason, "completion_tokens": len(ids),
            "thinking_format": "qwq_open_think"}


@contextmanager
def _enabled_adapter(model):
    adapter_state(model, False)
    yield


def run_pairs(comparison, inner_plan, identity, generate, deadline, progress,
              clock=time.monotonic):
    bundles = {}
    for mode in ("base", "adapted"):
        bundles[mode] = {"version": 1, "mode": mode, "plan_sha256": digest(canonical(inner_plan)),
            "foundation_id": FOUNDATION, "generation_settings": copy.deepcopy(comparison.SETTINGS),
            "adapter_model_sha256": SOURCE["files"][1]["sha256"] if mode == "adapted" else None,
            "adapter_config_sha256": SOURCE["files"][0]["sha256"] if mode == "adapted" else None,
            "inference_identity": copy.deepcopy(identity), "cases": [{
                "case_id": case["case_id"], "prompt_sha256": case["prompt_sha256"],
                "generated_text": "", "finish_reason": "not_run", "completion_tokens": 0,
                "thinking_format": "qwq_open_think"} for case in comparison.cases()]}
    count = 0
    stop = False
    for index, case in enumerate(comparison.cases()):
        for mode in ("base", "adapted"):
            if deadline - clock() < 30:
                stop = True
                break
            try:
                result = generate(case["messages"], mode)
            except EvaluationError:
                raise
            except Exception:
                result = {"generated_text": "", "finish_reason": "error", "completion_tokens": 0,
                          "thinking_format": "qwq_open_think"}
                stop = True
            bundles[mode]["cases"][index].update(result)
            count += 1
            progress({"phase": "evaluating", "case_id": case["case_id"], "mode": mode,
                      "completed_attempts": count, "paired_completed_cases": count // 2,
                      "finish_reason": result["finish_reason"], "completion_tokens": result["completion_tokens"]})
            if stop or result["finish_reason"] == "timeout":
                stop = True
                break
        if stop:
            break
    return comparison.score_comparison(inner_plan, bundles["base"], bundles["adapted"])


def write_json(path, value):
    with Path(path).open("xb") as stream:
        stream.write(canonical(value) + b"\n")


def execute(job, output, *, clients=private_clients, imports=None, clock=time.monotonic):
    job = validate_job(job)
    comparison = comparison_module()
    frozen_plan = plan(comparison)
    root = resume._private_root(output)
    require(not root.exists(), "evaluation_output_already_exists")
    root.mkdir()
    write_json(root / "plan.json", frozen_plan)
    effective_seconds = min(job["runtime_seconds"], int(job["deadline_unix"] - time.time()))
    require(effective_seconds >= 120, "evaluation_absolute_deadline_invalid")
    started, deadline = clock(), clock() + effective_seconds
    metadata = {"version": 2, "kind": "private_qwq_gpu_evaluation_metadata", "run_id": job["run_id"],
        "code_commit": job["code_commit"], "status": "not_executed", "evaluation_only": True,
        "optimizer_steps": 0, "weights_updated": False, "provider_created_by_worker": False,
        "case_set_sha256": CASE_SHA, "plan_sha256": digest(canonical(frozen_plan)),
        "source_adapter": copy.deepcopy(SOURCE), "generation_max_new_tokens": MAX_NEW_TOKENS,
        "context": CONTEXT, "foundation_revision": REVISION, "raw_reasoning_persisted": False,
        "effective_runtime_seconds": effective_seconds, "absolute_deadline_unix": job["deadline_unix"],
        "condition": frozen_plan["interpretation"], "coverage_definition": frozen_plan["comparison"]["coverage_definition"]}
    run, model, torch, artifact_reference = None, None, None, None
    report = {"version": 2, "kind": "private_qwq_gpu_comparison_not_executed",
              "case_set_sha256": CASE_SHA, "paired_completed_cases": 0, "reasoning_included": False}
    try:
        with hard_wall(max(1, effective_seconds - 120)):
            api, privacy, sdk = clients(os.environ)
            name = "hasla-qwq-gpu-comparison-" + job["run_id"]
            with resume._quiet():
                run = sdk.init(entity=ENTITY, project=resume.PROJECT, name=name, id=name, resume="never",
                               job_type="gpu-evaluation", config={"evaluation_only": True, "optimizer_steps": 0},
                               mode="online", reinit=True)
            def progress(value):
                safe = {"phase": value["phase"], "case_id": value.get("case_id"), "mode": value.get("mode"),
                        "completed_attempts": value["completed_attempts"],
                        "paired_completed_cases": value["paired_completed_cases"],
                        "evaluation_only": True, "weights_updated": False}
                with resume._quiet():
                    run.summary.update({"private_qwq_gpu_progress": safe})
                print(json.dumps(safe), flush=True)
            progress({"phase": "downloading_source", "completed_attempts": 0, "paired_completed_cases": 0})
            directory = root / "source-adapter"
            from role_config import get_role_config
            resume.download_initial_adapter(SOURCE, get_role_config("solver"), directory, api, privacy)
            adapter_file_proof(directory)
            # Import Unsloth before Transformers/PEFT, as required by its patcher.
            with resume._quiet():
                if imports is None:
                    import unsloth
                    import torch
                    import huggingface_hub as hub
                    from transformers import (AutoTokenizer, BitsAndBytesConfig, StoppingCriteria, StoppingCriteriaList)
                    from peft import PeftModel
                    from bitsandbytes.nn import Params4bit
                    from safetensors import safe_open
                    imports = {"loader": unsloth.FastLanguageModel, "torch": torch, "hub": hub,
                        "AutoTokenizer": AutoTokenizer, "BitsAndBytesConfig": BitsAndBytesConfig,
                        "StoppingCriteria": StoppingCriteria, "StoppingCriteriaList": StoppingCriteriaList,
                        "PeftModel": PeftModel, "Params4bit": Params4bit, "safe_open": safe_open}
                torch = imports["torch"]
                metadata["packages"] = package_versions(torch)
                metadata["gpu"] = gpu_proof(torch)
                torch.cuda.reset_peak_memory_stats(0)
                snapshot = materialize_base(imports["hub"], None)
                metadata["foundation_sources_verified"] = True
                tokenizer_config = resume._json((snapshot / "tokenizer_config.json").read_bytes())
                tokenizer = imports["AutoTokenizer"].from_pretrained(FOUNDATION, revision=REVISION,
                    token=False, trust_remote_code=False)
                require(tokenizer.chat_template == tokenizer_config["chat_template"], "official_tokenizer_template_mismatch")
                quant = imports["BitsAndBytesConfig"](load_in_4bit=True, bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)
                loader = imports["loader"]
                model, _ = loader.from_pretrained(**loader_options(torch, quant))
                require(getattr(model.config, "_commit_hash", None) == REVISION, "loaded_foundation_revision_mismatch")
                for parameter in model.parameters(): parameter.requires_grad_(False)
                _, retained = nf4_proof(model, imports["Params4bit"], torch.bfloat16)
                model = imports["PeftModel"].from_pretrained(model, str(directory), is_trainable=False,
                    local_files_only=True, trust_remote_code=False, autocast_adapter_dtype=True)
                for parameter in model.parameters(): parameter.requires_grad_(False)
                loader.for_inference(model)
                model.eval()
                metadata["gpu"] = gpu_proof(torch, model)
                metadata["nf4"], _ = nf4_proof(model, imports["Params4bit"], torch.bfloat16, retained)
                metadata["adapter"] = exact_loaded_adapter(model, directory, torch, imports["safe_open"])
                adapter_state(model, False)
            progress({"phase": "ready", "completed_attempts": 0, "paired_completed_cases": 0})
            identity = {"engine": "unsloth_single_gpu", "engine_version": importlib.metadata.version("unsloth"),
                "base_weights_sha256": digest(canonical(BASE_FILES)), "tokenizer_sha256": TOKENIZER_CONFIG_SHA,
                "chat_template_sha256": digest(tokenizer.chat_template.encode()),
                "quantization": "canonical_bnb_nf4_double_quant_bfloat16"}
            def generate(messages, mode):
                with resume._quiet():
                    return generate_one(model, tokenizer, messages, mode, deadline - 150, torch,
                        imports["StoppingCriteria"], imports["StoppingCriteriaList"], clock)
            inner_report = run_pairs(comparison, frozen_plan["comparison"], identity, generate,
                                     deadline - 150, progress, clock)
            comparison.validate_final_only_report(inner_report)
            report = {"version": 2, "kind": "private_qwq_gpu_comparison_report", "comparison": inner_report,
                      "reasoning_included": False, "execution_profile": frozen_plan["execution_profile"]}
            metadata["status"] = "completed" if inner_report["coverage_complete"] else "partial"
            metadata["paired_completed_cases"] = inner_report["paired_completed_cases"]
            with resume._quiet():
                adapter_file_proof(directory)
                nf4_proof(model, imports["Params4bit"], torch.bfloat16, retained)
                metadata["adapter"] = exact_loaded_adapter(model, directory, torch, imports["safe_open"])
                torch.cuda.synchronize()
                metadata["peak_allocated_bytes"] = torch.cuda.max_memory_allocated(0)
                metadata["peak_reserved_bytes"] = torch.cuda.max_memory_reserved(0)
            require(0 < metadata["peak_allocated_bytes"] <= metadata["peak_reserved_bytes"] <=
                    metadata["gpu"]["physical_vram_bytes"], "gpu_peak_memory_proof_invalid")
    except EvaluationError as error:
        metadata.update(status="failed", failure_code=str(error))
    except Exception:
        metadata.update(status="failed", failure_code="gpu_evaluation_failed")
    finally:
        if model is not None:
            del model
        retained = None
        _ = None
        if torch is not None:
            try:
                with resume._quiet(): torch.cuda.empty_cache()
            except Exception:
                pass
        metadata["elapsed_seconds"] = round(clock() - started, 3)
        write_json(root / "report.json", report)
        write_json(root / "metadata.json", metadata)
        if run is not None:
            publication_guard = None
            try:
                require(deadline - clock() > 5, "evaluation_wall_cap_reached")
                publication_guard = hard_wall(max(1, int(deadline - clock()) - 1))
                publication_guard.__enter__()
                validate_outputs(root, comparison)
                privacy(ENTITY)
                with resume._quiet():
                    artifact = sdk.Artifact(name, type="evaluation", metadata={
                        "private": True, "evaluation_only": True, "optimizer_steps": 0,
                        "run_id": job["run_id"], "code_commit": job["code_commit"],
                        "case_set_sha256": CASE_SHA, "source_adapter_inventory_sha256": SOURCE["adapter_inventory_sha256"],
                        "files": [{"name": path.name, "sha256": file_sha(path), "bytes": path.stat().st_size}
                                  for path in (root / "report.json", root / "metadata.json")]})
                    for path in (root / "report.json", root / "metadata.json"):
                        artifact.add_file(str(path), name=path.name)
                    saved = run.log_artifact(artifact).wait(timeout=max(1, min(60, int(deadline - clock()) - 5)))
                    reference = str(saved.qualified_name)
                    require(saved.state == "COMMITTED" and re.fullmatch(
                        re.escape(ENTITY + "/" + resume.PROJECT + "/" + name) + r":v[0-9]+", reference),
                        "evaluation_artifact_commit_unverified")
                privacy(ENTITY)
                artifact_reference = reference
                result = result_event(job, metadata, report, root, artifact_reference)
                with resume._quiet():
                    run.summary.update({"private_qwq_gpu_result_json": result,
                        "private_qwq_gpu_progress": {"phase": "uploaded", "case_id": None, "mode": None,
                            "completed_attempts": 2 * metadata.get("paired_completed_cases", 0),
                            "paired_completed_cases": metadata.get("paired_completed_cases", 0),
                            "evaluation_only": True, "weights_updated": False}})
            except Exception:
                metadata["publication_failed"] = True
            finally:
                if publication_guard is not None:
                    publication_guard.__exit__(None, None, None)
                try:
                    if deadline - clock() > 5:
                        with hard_wall(max(1, min(10, int(deadline - clock()) - 1))):
                            with resume._quiet(): run.finish()
                except Exception:
                    pass
    return result_event(job, metadata, report, root, artifact_reference)


def result_event(job, metadata, report, root, artifact_reference):
    metrics = {}
    if report.get("kind") == "private_qwq_gpu_comparison_report":
        for mode, group in report["comparison"]["results"].items():
            metrics[mode] = {key: group[key] for key in ("paired_passed_cases", "paired_correct_numeric_quantities",
                                                       "abstention_passed", "failures")}
    return {"version": 1, "kind": "private_qwq_gpu_evaluation_result", "run_id": job["run_id"],
            "status": "uploaded" if artifact_reference else "failed", "execution_status": metadata["status"],
            "artifact": artifact_reference, "files": [{"name": path.name, "bytes": path.stat().st_size,
                "sha256": file_sha(path)} for path in (root / "report.json", root / "metadata.json")],
            "evaluation_only": True, "optimizer_steps": 0, "weights_updated": False,
            "paired_completed_cases": metadata.get("paired_completed_cases", 0), "case_set_sha256": CASE_SHA,
            "comparison_plan_sha256": metadata["plan_sha256"], "metrics": metrics,
            "raw_reasoning_included": False}


def validate_result(value, run_id):
    keys = {"version", "kind", "run_id", "status", "execution_status", "artifact", "files",
            "evaluation_only", "optimizer_steps", "weights_updated", "paired_completed_cases",
            "case_set_sha256", "comparison_plan_sha256", "metrics", "raw_reasoning_included"}
    require(type(value) is dict and set(value) == keys and value["version"] == 1
            and value["kind"] == "private_qwq_gpu_evaluation_result" and value["run_id"] == str(run_id)
            and value["status"] in {"uploaded", "failed"} and value["execution_status"] in {"completed", "partial", "failed"}
            and value["evaluation_only"] is True and type(value["optimizer_steps"]) is int and value["optimizer_steps"] == 0
            and value["weights_updated"] is False and value["raw_reasoning_included"] is False
            and type(value["paired_completed_cases"]) is int and 0 <= value["paired_completed_cases"] <= 8
            and value["case_set_sha256"] == CASE_SHA and value["comparison_plan_sha256"] == digest(canonical(evaluation_plan())),
            "invalid_gpu_result")
    reference = value["artifact"]
    require(reference is None if value["status"] == "failed" else type(reference) is str and re.fullmatch(
        re.escape(ENTITY + "/" + resume.PROJECT + "/hasla-qwq-gpu-comparison-" + str(run_id)) + r":v[0-9]+", reference),
        "invalid_gpu_result_artifact")
    require(type(value["files"]) is list and len(value["files"]) == 2, "invalid_gpu_result_files")
    for name, row in zip(("report.json", "metadata.json"), value["files"]):
        require(type(row) is dict and set(row) == {"name", "bytes", "sha256"} and row["name"] == name
                and type(row["bytes"]) is int and 0 < row["bytes"] <= 4 * 1024**2
                and type(row["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]), "invalid_gpu_result_files")
    metrics = value["metrics"]
    require(type(metrics) is dict and set(metrics) in (set(), {"base", "adapted"}), "invalid_gpu_result_metrics")
    allowed_failures = {"length", "timeout", "error", "not_run", "unknown_finish_reason", "invalid_token_count",
        "invalid_generated_text", "unsupported_thinking_format", "thinking_not_closed", "final_answer_missing",
        "fabricated_score_or_missing_abstention", "numeric_or_unit_error", "format_error"}
    for group in metrics.values():
        require(type(group) is dict and set(group) == {"paired_passed_cases", "paired_correct_numeric_quantities",
                                                      "abstention_passed", "failures"}
                and type(group["paired_passed_cases"]) is int and 0 <= group["paired_passed_cases"] <= value["paired_completed_cases"]
                and type(group["paired_correct_numeric_quantities"]) is int and 0 <= group["paired_correct_numeric_quantities"] <= 10
                and type(group["abstention_passed"]) is bool and type(group["failures"]) is dict
                and all(key in allowed_failures and type(count) is int and 1 <= count <= 8
                        for key, count in group["failures"].items()), "invalid_gpu_result_metrics")
    return copy.deepcopy(value)


def validate_outputs(directory, comparison=None):
    comparison = comparison or comparison_module()
    report = comparison.load_json(Path(directory) / "report.json")
    metadata = comparison.load_json(Path(directory) / "metadata.json")
    if report.get("kind") == "private_qwq_gpu_comparison_report":
        require(set(report) == {"version", "kind", "comparison", "reasoning_included", "execution_profile"}
                and report["version"] == 2 and report["reasoning_included"] is False
                and report["execution_profile"] == plan(comparison)["execution_profile"], "gpu_report_schema_invalid")
        comparison.validate_final_only_report(report["comparison"])
    else:
        require(report == {"version": 2, "kind": "private_qwq_gpu_comparison_not_executed",
            "case_set_sha256": CASE_SHA, "paired_completed_cases": 0, "reasoning_included": False},
            "gpu_not_executed_report_invalid")
    fixed = {"version": 2, "kind": "private_qwq_gpu_evaluation_metadata", "evaluation_only": True,
        "optimizer_steps": 0, "weights_updated": False, "provider_created_by_worker": False,
        "case_set_sha256": CASE_SHA, "plan_sha256": digest(canonical(plan(comparison))), "source_adapter": SOURCE,
        "generation_max_new_tokens": MAX_NEW_TOKENS, "context": CONTEXT, "foundation_revision": REVISION,
        "raw_reasoning_persisted": False, "condition": plan(comparison)["interpretation"],
        "coverage_definition": plan(comparison)["comparison"]["coverage_definition"]}
    required = set(fixed) | {"run_id", "code_commit", "status", "elapsed_seconds", "effective_runtime_seconds", "absolute_deadline_unix"}
    optional = {"gpu", "nf4", "adapter", "packages", "paired_completed_cases", "failure_code", "foundation_sources_verified",
                "peak_allocated_bytes", "peak_reserved_bytes"}
    require(required <= set(metadata) <= required | optional and all(metadata[key] == value for key, value in fixed.items())
            and metadata["status"] in {"failed", "partial", "completed"}
            and type(metadata["run_id"]) is str and re.fullmatch(r"[1-9][0-9]{0,31}", metadata["run_id"])
            and type(metadata["code_commit"]) is str and re.fullmatch(r"[0-9a-f]{40}", metadata["code_commit"])
            and type(metadata["effective_runtime_seconds"]) is int and 120 <= metadata["effective_runtime_seconds"] <= 2700
            and type(metadata["absolute_deadline_unix"]) is int
            and type(metadata["elapsed_seconds"]) in {int, float} and 0 <= metadata["elapsed_seconds"] <= 2800,
            "gpu_metadata_schema_invalid")
    if "failure_code" in metadata:
        require(type(metadata["failure_code"]) is str and re.fullmatch(r"[a-z_]{1,80}", metadata["failure_code"]),
                "gpu_failure_code_invalid")
    # Proof objects contain only fixed booleans/counts/digests, no arbitrary text.
    if "gpu" in metadata:
        proof = metadata["gpu"]
        require(type(proof) is dict and set(proof) == {"gpu_count", "gpu_name", "physical_vram_bytes", "cpu_or_disk_offload_used"}
                and proof["gpu_count"] == 1 and proof["gpu_name"] == "NVIDIA A40"
                and type(proof["physical_vram_bytes"]) is int and 37 * GIB <= proof["physical_vram_bytes"] <= 49 * GIB
                and proof["cpu_or_disk_offload_used"] is False, "gpu_hardware_proof_invalid")
    if "packages" in metadata:
        packages = metadata["packages"]
        require(type(packages) is dict and set(packages) == {"unsloth", "torch", "transformers", "peft",
            "bitsandbytes", "accelerate", "huggingface_hub", "safetensors", "wandb", "cuda_runtime"}
            and all(type(value) is str and re.fullmatch(r"[A-Za-z0-9.+_-]{1,80}", value)
                    for value in packages.values()), "runtime_package_version_invalid")
    if "nf4" in metadata:
        require(metadata["nf4"] == {"dense_layers": 64, "quantized_linear_tensors": 448, "quant_type": "nf4",
                "double_quant": True, "compute_dtype": "bfloat16", "all_base_parameters_frozen": True},
                "gpu_nf4_proof_invalid")
    if "adapter" in metadata:
        require(metadata["adapter"] == {"tensor_count": 896, "lora_pairs": 448, "loaded_values_equal_source": True,
                "source_model_sha256": SOURCE["files"][1]["sha256"], "optimizer_steps": 0}, "gpu_adapter_proof_invalid")
    if "paired_completed_cases" in metadata:
        require(type(metadata["paired_completed_cases"]) is int and 0 <= metadata["paired_completed_cases"] <= 8,
                "gpu_pair_count_invalid")
    if "foundation_sources_verified" in metadata:
        require(metadata["foundation_sources_verified"] is True, "foundation_source_proof_invalid")
    if metadata["status"] in {"partial", "completed"}:
        require({"gpu", "nf4", "adapter", "packages", "paired_completed_cases", "peak_allocated_bytes", "peak_reserved_bytes"} <= set(metadata)
                and report["kind"] == "private_qwq_gpu_comparison_report"
                and metadata["paired_completed_cases"] == report["comparison"]["paired_completed_cases"]
                and type(metadata["peak_allocated_bytes"]) is int and type(metadata["peak_reserved_bytes"]) is int
                and 0 < metadata["peak_allocated_bytes"] <= metadata["peak_reserved_bytes"] <= metadata["gpu"]["physical_vram_bytes"],
                "gpu_success_proofs_missing")
    return [Path(directory) / "report.json", Path(directory) / "metadata.json"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path)
    parser.add_argument("--prepare-only", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.prepare_only:
            require(args.job is None and not os.environ.get("HASLA_QWQ_GPU_EVAL_JOB"), "conflicting_gpu_modes")
            comparison = comparison_module()
            root = resume._private_root(args.prepare_only)
            root.mkdir()
            write_json(root / "plan.json", plan(comparison))
            print(json.dumps({"phase": "prepared", "inference_executed": False, "provider_created": False}))
            return 0
        raw = args.job.read_bytes() if args.job else os.environ.get("HASLA_QWQ_GPU_EVAL_JOB", "").encode()
        require(0 < len(raw) <= 32768, "job_size_invalid")
        job = validate_job(resume._json(raw))
        result = execute(job, Path("/workspace") / ("hasla-qwq-gpu-eval-" + job["run_id"]))
        print(json.dumps(result), flush=True)
        return 0 if result["status"] == "uploaded" else 1
    except Exception as error:
        print(json.dumps({"phase": "failed", "failure_code": str(error) if isinstance(error, EvaluationError)
            else "gpu_evaluation_failed", "evaluation_only": True, "optimizer_steps": 0, "automatic_retry": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

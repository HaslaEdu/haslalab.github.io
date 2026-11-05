"""Pinned CPU-only llama.cpp comparison worker; downloads and billing are absent.

Inputs are supplied locally by a separately reviewed workflow.  The only HTTP
destination used here is the worker's own 127.0.0.1 llama-server.  No raw model
reasoning or subprocess output is written to logs or files.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import private_qwq_comparison as comparison

LLAMA_COMMIT = "3de52ac38818978d6da8f386eda43a856e53714a"
CONVERTER_SHA = "ddb143ac34022b0646e51d9c35e9cfa3ec3d0a36091975ebc88f553dd18ca350"
MODEL_REPO = "unsloth/QwQ-32B-GGUF"
MODEL_REVISION = "d5faedaaaae5cdacdc487b53d90dcc7210ca218c"
MODEL_FILES = {
    "iq3_xxs": {"name": "QwQ-32B-UD-IQ3_XXS.gguf", "bytes": 13052652128,
                "sha256": "40e30d9b5ea5cabb5a252e587750b9b3dc7aaf3a86dd27fcd9eddca9f406ddbc"},
    "iq2_xxs": {"name": "QwQ-32B-UD-IQ2_XXS.gguf", "bytes": 9336801888,
                "sha256": "dde2f99a431ae8dd14652f96c85855a1b07831de6a0e8b03b11af78af4ec7789"},
}
BASE_REVISION = "976055f8c83f394f35dbd3ab09a285a984907bd0"
BASE_CONFIG_SHA = "61feaaef406a79c195ba8629921e99ad27753434c1e7bf60f5809cd73a86de68"
TOKENIZER_CONFIG_SHA = "ab43f460108ca40fbb09fa537696baf862b6a9b46a2c6688b9de711293e3ddc4"
ADAPTER_MODEL_SHA = "c3821d50ae7255e7fc296a421af7e7c9c2677ad530a1b9895c616ff9bf208bd9"
ADAPTER_CONFIG_SHA = "f9392d8f82273d1142deee6742dbf6c38697697c00264a7257c1582676f50372"
ADAPTER_INVENTORY_SHA = "36d6116f3ac8e78d207dfc045c9f33e00a342c978041adc5b54cec23f0d0a9b8"
ADAPTER_MODEL_BYTES = 536991984
ADAPTER_CONFIG_BYTES = 1322
ADAPTER_TENSORS = 896
ADAPTER_PAIRS = 448
GIB = 1024**3
MAX_RESPONSE = 512 * 1024


class EvaluationError(RuntimeError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise EvaluationError(code)


def file_sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pinned_file(path: Path, digest: str, size: int | None = None) -> None:
    require(path.is_file() and not path.is_symlink(), "input_regular_file_required")
    require(size is None or path.stat().st_size == size, "input_bytes_mismatch")
    require(file_sha(path) == digest, "input_sha256_mismatch")


def validate_adapter(directory: Path) -> None:
    pinned_file(directory / "adapter_model.safetensors", ADAPTER_MODEL_SHA, ADAPTER_MODEL_BYTES)
    pinned_file(directory / "adapter_config.json", ADAPTER_CONFIG_SHA, ADAPTER_CONFIG_BYTES)
    config = comparison.load_json(directory / "adapter_config.json")
    from private_resume_adapter import QWQ_BASES, _layout
    require(config.get("base_model_name_or_path") in QWQ_BASES and
            type(config.get("r")) is int and config["r"] == 16 and
            config.get("peft_type") == "LORA" and config.get("task_type") == "CAUSAL_LM" and
            config.get("use_dora", False) is False, "adapter_base_rank_or_type_mismatch")
    _, _, tensors, bs = _layout(directory / "adapter_model.safetensors", 16)
    require(len(tensors) == ADAPTER_TENSORS and len(bs) == ADAPTER_PAIRS,
            "source_adapter_tensor_count_mismatch")


def validate_source(llama_dir: Path, binary: Path) -> None:
    require(binary.is_file() and not binary.is_symlink(), "server_binary_required")
    require(binary.resolve().is_relative_to(llama_dir.resolve()), "server_outside_pinned_source")
    pinned_file(llama_dir / "convert_lora_to_gguf.py", CONVERTER_SHA)
    result = subprocess.run(["git", "-C", str(llama_dir), "rev-parse", "HEAD"],
                            capture_output=True, timeout=10, check=False)
    require(result.returncode == 0 and result.stdout.decode().strip() == LLAMA_COMMIT,
            "llama_source_revision_mismatch")
    result = subprocess.run(["git", "-C", str(llama_dir), "diff", "--quiet", "HEAD", "--"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            timeout=10, check=False)
    require(result.returncode == 0, "llama_source_modified")


def memory_status() -> dict:
    path = Path("/proc/meminfo")
    require(path.is_file(), "linux_memory_proof_required")
    values = {}
    for line in path.read_text(encoding="ascii").splitlines():
        if line.startswith(("MemTotal:", "MemAvailable:")):
            key, number, unit = line.split()
            require(unit == "kB", "memory_units_unknown")
            values[key[:-1]] = int(number) * 1024
    require(set(values) == {"MemTotal", "MemAvailable"}, "memory_proof_incomplete")
    return values


def validate_resources(quant: str, memory: dict, disk_free: int) -> None:
    require(quant in MODEL_FILES, "quant_not_allowlisted")
    minimum_total = 15 * GIB if quant == "iq3_xxs" else 14 * GIB
    minimum_available = 14 * GIB if quant == "iq3_xxs" else 11 * GIB
    require(memory.get("MemTotal", 0) >= minimum_total and
            memory.get("MemAvailable", 0) >= minimum_available, "insufficient_cpu_ram")
    require(disk_free >= 2 * GIB, "insufficient_conversion_disk")


def child_environment() -> dict:
    # In particular W&B/HF/RunPod credentials and LLAMA_ARG_* overrides cannot
    # reach the converter or the model server.  Neither child needs networking.
    allowed = {"PATH", "HOME", "USER", "TMPDIR", "TMP", "TEMP", "SYSTEMROOT",
               "LD_LIBRARY_PATH", "VIRTUAL_ENV", "PYTHONPATH", "LANG", "LC_ALL"}
    env = {key: value for key, value in os.environ.items() if key in allowed}
    env.update({"CUDA_VISIBLE_DEVICES": "", "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false",
                "PYTHONDONTWRITEBYTECODE": "1"})
    return env


def render_prompt(messages: list[dict], tokenizer_config: dict) -> str:
    require([row.get("role") for row in messages] == ["system", "user"], "prompt_roles_changed")
    from jinja2 import Environment, StrictUndefined
    environment = Environment(undefined=StrictUndefined)
    template = environment.from_string(tokenizer_config["chat_template"])
    rendered = template.render(messages=messages, tools=None, add_generation_prompt=True)
    # The official template for exactly system+user must have this byte form.
    expected = ("<|im_start|>system\n" + messages[0]["content"] + "<|im_end|>\n" +
                "<|im_start|>user\n" + messages[1]["content"] + "<|im_end|>\n" +
                "<|im_start|>assistant\n<think>\n")
    require(rendered == expected, "official_template_render_mismatch")
    return rendered


def converter_command(args, output: Path) -> list[str]:
    return [sys.executable, "-B", str(args.llama_dir / "convert_lora_to_gguf.py"),
            "--base", str(args.base_config_dir), "--outfile", str(output),
            "--outtype", "f32", str(args.adapter_dir)]


def verify_converted_adapter(path: Path, llama_dir: Path) -> dict:
    require(path.is_file() and not path.is_symlink() and 8 < path.stat().st_size < GIB,
            "converted_adapter_size_invalid")
    with path.open("rb") as stream:
        require(stream.read(4) == b"GGUF", "converted_adapter_not_gguf")
    sys.path.insert(0, str(llama_dir / "gguf-py"))
    try:
        from gguf import GGUFReader
        import numpy as np
        reader = GGUFReader(str(path))
        require(len(reader.tensors) == ADAPTER_TENSORS and
                all(int(tensor.tensor_type) == 0 for tensor in reader.tensors),
                "converted_adapter_not_all_f32")
        names = [tensor.name for tensor in reader.tensors]
        require(len(names) == len(set(names)) and all(
            name.endswith((".lora_a", ".lora_b")) for name in names), "converted_adapter_tensor_names_invalid")
        a_prefixes = {name[:-7] for name in names if name.endswith(".lora_a")}
        b_prefixes = {name[:-7] for name in names if name.endswith(".lora_b")}
        require(a_prefixes == b_prefixes and len(a_prefixes) == ADAPTER_PAIRS,
                "converted_adapter_pairs_missing")
        by_name = {tensor.name: tensor for tensor in reader.tensors}
        for prefix in a_prefixes:
            a, b = by_name[prefix + ".lora_a"].data, by_name[prefix + ".lora_b"].data
            require(a.ndim == b.ndim == 2 and a.shape[0] == b.shape[1] == 16 and
                    a.size > 0 and b.size > 0, "converted_adapter_pair_shape_invalid")
        for tensor in reader.tensors:
            flat = tensor.data.reshape(-1)
            for offset in range(0, flat.size, 1024**2):
                require(bool(np.isfinite(flat[offset:offset + 1024**2]).all()),
                        "converted_adapter_nonfinite")
        count = len(names)
        del reader
    finally:
        sys.path.pop(0)
    return {"sha256": file_sha(path), "bytes": path.stat().st_size,
            "tensor_count": count, "pair_count": len(a_prefixes),
            "all_tensors_f32": True, "all_tensors_finite": True}


def server_command(args, converted: Path, port: int) -> list[str]:
    return [str(args.server_binary), "--model", str(args.model_path),
            "--lora", str(converted), "--lora-init-without-apply",
            "--host", "127.0.0.1", "--port", str(port), "--parallel", "1",
            "--ctx-size", str(args.context), "--threads", str(args.threads),
            "--threads-batch", str(args.threads), "--n-gpu-layers", "0",
            "--cache-type-k", "f16", "--cache-type-v", "f16",
            "--no-context-shift", "--no-webui", "--log-disable"]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise EvaluationError("local_server_redirect_rejected")


class LocalServer:
    def __init__(self, port: int):
        require(type(port) is int and 1024 <= port <= 65535, "invalid_local_port")
        self.url = "http://127.0.0.1:" + str(port)
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, endpoint: str, timeout: float, payload=None):
        require(endpoint in {"/health", "/lora-adapters", "/tokenize", "/completion"},
                "local_endpoint_not_allowlisted")
        require(0 < timeout <= 1200, "invalid_local_timeout")
        data = None if payload is None else comparison.canonical(payload)
        request = urllib.request.Request(self.url + endpoint, data=data,
                                         headers={"Content-Type": "application/json"})
        with self.opener.open(request, timeout=timeout) as response:
            require(response.status == 200, "local_server_http_failure")
            raw = response.read(MAX_RESPONSE + 1)
        require(len(raw) <= MAX_RESPONSE, "local_server_response_too_large")
        return json.loads(raw, object_pairs_hook=comparison.unique_object,
                          parse_constant=comparison.reject_constant)


def request_payload(prompt: str, mode: str) -> dict:
    require(mode in {"base", "adapted"}, "invalid_comparison_mode")
    return {"prompt": prompt, "n_predict": comparison.SETTINGS["max_new_tokens"],
            "temperature": 0, "top_k": 1, "top_p": 1, "min_p": 0,
            "repeat_penalty": 1, "samplers": ["temperature"],
            "seed": comparison.SETTINGS["seed"], "stream": False,
            "cache_prompt": False, "return_tokens": True,
            "stop": ["<|im_end|>", "<|endoftext|>"],
            "lora": [{"id": 0, "scale": 0 if mode == "base" else 1}]}


def normalize_completion(response: dict) -> dict:
    require(isinstance(response, dict), "invalid_local_completion")
    content, tokens = response.get("content"), response.get("tokens")
    require(isinstance(content, str) and len(content.encode()) <= comparison.MAX_RESULT_TEXT and
            isinstance(tokens, list) and all(type(token) is int for token in tokens),
            "invalid_completion_content_or_tokens")
    stop_type = response.get("stop_type")
    if response.get("truncated") is True or stop_type == "limit":
        reason = "length"
    elif stop_type in {"eos", "word"}:
        reason = "stop"
    else:
        reason = "error"
    return {"generated_text": content, "completion_tokens": len(tokens),
            "finish_reason": reason, "thinking_format": "qwq_open_think"}


def empty_generation(reason="not_run") -> dict:
    return {"generated_text": "", "completion_tokens": 0, "finish_reason": reason,
            "thinking_format": "qwq_open_think"}


def run_pairs(plan: dict, identity: dict, prompts: list[str], server, deadline: float,
              clock=time.monotonic, progress=lambda value: None) -> tuple[dict, dict]:
    comparison.validate_plan(plan, ready=True)
    comparison.validate_identity(identity)
    require(len(prompts) == 8, "wrong_rendered_prompt_count")
    bundles = {}
    for mode in ("base", "adapted"):
        bundles[mode] = {"version": 1, "mode": mode,
            "plan_sha256": comparison.sha256(comparison.canonical(plan)),
            "foundation_id": comparison.FOUNDATION,
            "generation_settings": copy.deepcopy(comparison.SETTINGS),
            "adapter_model_sha256": plan["adapter_model_sha256"] if mode == "adapted" else None,
            "adapter_config_sha256": plan["adapter_config_sha256"] if mode == "adapted" else None,
            "inference_identity": copy.deepcopy(identity),
            "cases": [{"case_id": case["case_id"], "prompt_sha256": case["prompt_sha256"],
                       **empty_generation()} for case in comparison.cases()]}
    stopped = False
    for index, prompt in enumerate(prompts):
        for mode in ("base", "adapted"):
            remaining = deadline - clock()
            if remaining <= 5:
                stopped = True
                break
            try:
                response = server.request("/completion", min(remaining - 1, 1200), request_payload(prompt, mode))
                generation = normalize_completion(response)
            except (TimeoutError, socket.timeout, urllib.error.URLError):
                generation, stopped = empty_generation("timeout"), True
            except Exception:
                generation, stopped = empty_generation("error"), True
            bundles[mode]["cases"][index].update(generation)
            progress({"stage": "case_finished", "case_index": index, "mode": mode,
                      "finish_reason": generation["finish_reason"],
                      "completion_tokens": generation["completion_tokens"]})
            if stopped:
                break
        if stopped:
            break
    return bundles["base"], bundles["adapted"]


def write_json(path: Path, value) -> None:
    with path.open("xb") as stream:
        stream.write(comparison.canonical(value) + b"\n")


def validate_upload_bundle(directory: Path) -> list[Path]:
    """Only these two final-only files may enter the private report artifact."""
    report_path, metadata_path = directory / "report.json", directory / "metadata.json"
    report, metadata = comparison.load_json(report_path), comparison.load_json(metadata_path)
    if report.get("kind") == "private_qwq_comparison_not_executed":
        require(set(report) == {"version", "kind", "reasoning_included", "frozen_cases",
                                "paired_completed_cases", "scientific_verification"} and
                report["version"] == 1 and report["reasoning_included"] is False and
                report["frozen_cases"] == 8 and report["paired_completed_cases"] == 0 and
                report["scientific_verification"] == "pending", "invalid_not_executed_report")
    else:
        comparison.validate_final_only_report(report)
    fixed = {
        "version": 1, "kind": "private_qwq_cpu_comparison_execution", "gpu_count": 0,
        "provider_created": False, "foundation_id": comparison.FOUNDATION,
        "foundation_revision": BASE_REVISION, "gguf_repo": MODEL_REPO,
        "gguf_revision": MODEL_REVISION, "llama_commit": LLAMA_COMMIT,
        "adapter_training_run_id": comparison.ADAPTER_RUN,
        "adapter_artifact": comparison.ADAPTER_ARTIFACT,
        "adapter_inventory_sha256": ADAPTER_INVENTORY_SHA, "same_model_process": True,
        "execution_order": "case_paired_base_then_adapted", "cache_prompt": False,
        "optimizer_steps": 0, "raw_reasoning_persisted": False,
        "quality_scope": "same_dynamic_quantization_toy_cases_not_nf4_quality",
        "scientific_verification": "pending",
    }
    optional = {"memory_before_conversion", "server_binary_sha256", "converted_adapter", "prompt_tokens",
                "paired_completed_cases", "frozen_cases", "report_sha256", "failure_code"}
    required = set(fixed) | {"status", "gguf_quant", "server_process_stopped", "elapsed_seconds"}
    require(required <= set(metadata) <= required | optional and
            all(metadata[key] == value for key, value in fixed.items()) and
            metadata["gguf_quant"] in MODEL_FILES and metadata["status"] in {"completed", "partial", "failed"} and
            metadata["server_process_stopped"] is True and
            type(metadata["elapsed_seconds"]) in {int, float} and 0 <= metadata["elapsed_seconds"] <= 9700,
            "upload_metadata_fields_invalid")
    if "report_sha256" in metadata:
        require(metadata["report_sha256"] == file_sha(report_path), "upload_report_hash_mismatch")
    if "failure_code" in metadata:
        require(metadata["failure_code"] in {
            "input_regular_file_required", "input_bytes_mismatch", "input_sha256_mismatch",
            "adapter_base_rank_or_type_mismatch", "source_adapter_tensor_count_mismatch",
            "server_binary_required", "server_outside_pinned_source",
            "llama_source_revision_mismatch", "llama_source_modified", "linux_memory_proof_required",
            "memory_units_unknown", "memory_proof_incomplete", "quant_not_allowlisted",
            "insufficient_cpu_ram", "insufficient_conversion_disk", "prompt_roles_changed",
            "official_template_render_mismatch", "converted_adapter_size_invalid", "converted_adapter_not_gguf",
            "converted_adapter_not_all_f32", "converted_adapter_tensor_names_invalid", "converted_adapter_pairs_missing",
            "converted_adapter_pair_shape_invalid", "converted_adapter_nonfinite",
            "wall_cap_before_conversion", "adapter_conversion_failed", "cpu_server_exited_before_ready",
            "cpu_server_load_timeout", "server_adapter_not_exact_disabled_single", "prompt_tokenization_invalid",
            "prompt_generation_exceeds_context", "local_subprocess_timeout", "cpu_evaluation_failed",
        }, "upload_failure_code_invalid")
    for key in ("server_binary_sha256", "report_sha256"):
        if key in metadata:
            require(comparison.is_sha(metadata[key]), "upload_hash_invalid")
    if "memory_before_conversion" in metadata:
        memory = metadata["memory_before_conversion"]
        require(isinstance(memory, dict) and set(memory) == {"MemTotal", "MemAvailable"} and
                all(type(value) is int and 0 <= value <= 1024 * GIB for value in memory.values()),
                "upload_memory_invalid")
    if "converted_adapter" in metadata:
        value = metadata["converted_adapter"]
        require(isinstance(value, dict) and set(value) == {"sha256", "bytes", "tensor_count", "pair_count",
                                                       "all_tensors_f32", "all_tensors_finite"} and
                comparison.is_sha(value["sha256"]) and type(value["bytes"]) is int and 8 < value["bytes"] < GIB and
                type(value["tensor_count"]) is int and value["tensor_count"] == ADAPTER_TENSORS and
                type(value["pair_count"]) is int and value["pair_count"] == ADAPTER_PAIRS and
                value["all_tensors_f32"] is True and value["all_tensors_finite"] is True,
                "upload_converted_adapter_invalid")
    if "prompt_tokens" in metadata:
        require(isinstance(metadata["prompt_tokens"], list) and len(metadata["prompt_tokens"]) == 8 and
                all(type(value) is int and 0 < value <= 1016 for value in metadata["prompt_tokens"]),
                "upload_prompt_counts_invalid")
    for key in ("paired_completed_cases", "frozen_cases"):
        if key in metadata:
            require(type(metadata[key]) is int and 0 <= metadata[key] <= 8, "upload_count_invalid")
    return [report_path, metadata_path]


def stop_process(process) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def execute(args) -> dict:
    started = time.monotonic()
    require(60 <= args.max_wall_seconds <= 9600, "wall_cap_out_of_range")
    require(type(args.threads) is int and 1 <= args.threads <= 8 and
            args.context == 2048, "cpu_threads_or_context_not_allowed")
    require(args.quant in MODEL_FILES, "quant_not_allowlisted")
    args.work_dir.mkdir(parents=True, exist_ok=False)
    metadata = {"version": 1, "kind": "private_qwq_cpu_comparison_execution",
                "status": "preflight", "gpu_count": 0, "provider_created": False,
                "foundation_id": comparison.FOUNDATION, "foundation_revision": BASE_REVISION,
                "gguf_repo": MODEL_REPO, "gguf_revision": MODEL_REVISION,
                "gguf_quant": args.quant, "llama_commit": LLAMA_COMMIT,
                "adapter_training_run_id": comparison.ADAPTER_RUN,
                "adapter_artifact": comparison.ADAPTER_ARTIFACT,
                "adapter_inventory_sha256": ADAPTER_INVENTORY_SHA,
                "same_model_process": True, "execution_order": "case_paired_base_then_adapted",
                "cache_prompt": False, "optimizer_steps": 0,
                "raw_reasoning_persisted": False,
                "quality_scope": "same_dynamic_quantization_toy_cases_not_nf4_quality",
                "scientific_verification": "pending"}
    process = None
    try:
        memory = memory_status()
        metadata["memory_before_conversion"] = memory
        validate_resources(args.quant, memory, shutil.disk_usage(args.work_dir).free)
        spec = MODEL_FILES[args.quant]
        pinned_file(args.model_path, spec["sha256"], spec["bytes"])
        validate_adapter(args.adapter_dir)
        pinned_file(args.tokenizer_config, TOKENIZER_CONFIG_SHA)
        pinned_file(args.base_config_dir / "config.json", BASE_CONFIG_SHA, 662)
        validate_source(args.llama_dir, args.server_binary)
        metadata["server_binary_sha256"] = file_sha(args.server_binary)
        tokenizer = comparison.load_json(args.tokenizer_config)
        prompts = [render_prompt(case["messages"], tokenizer) for case in comparison.cases()]
        plan = comparison.build_plan(ADAPTER_MODEL_SHA, ADAPTER_CONFIG_SHA)
        write_json(args.work_dir / "plan.json", plan)
        write_json(args.work_dir / "cases.json", comparison.cases())
        converted = args.work_dir / "adapter-f32.gguf"
        remaining = args.max_wall_seconds - (time.monotonic() - started)
        require(remaining > 30, "wall_cap_before_conversion")
        result = subprocess.run(converter_command(args, converted), cwd=args.llama_dir,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                env=child_environment(), timeout=min(remaining - 10, 600), check=False)
        require(result.returncode == 0, "adapter_conversion_failed")
        metadata["converted_adapter"] = verify_converted_adapter(converted, args.llama_dir)
        validate_adapter(args.adapter_dir)  # Original files must still have exact bytes.
        validate_resources(args.quant, memory_status(), shutil.disk_usage(args.work_dir).free)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = LocalServer(port)
        process = subprocess.Popen(server_command(args, converted, port), cwd=args.llama_dir,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   env=child_environment())
        deadline = started + args.max_wall_seconds
        ready_deadline = min(deadline - 15, time.monotonic() + 600)
        while True:
            require(process.poll() is None, "cpu_server_exited_before_ready")
            require(time.monotonic() < ready_deadline, "cpu_server_load_timeout")
            try:
                health = server.request("/health", 2)
                if isinstance(health, dict) and health.get("status") == "ok":
                    break
            except (urllib.error.URLError, TimeoutError):
                pass
            time.sleep(1)
        adapters = server.request("/lora-adapters", 10)
        require(isinstance(adapters, list) and len(adapters) == 1 and
                adapters[0].get("id") == 0 and adapters[0].get("scale") == 0 and
                Path(adapters[0].get("path", "")).resolve() == converted.resolve(),
                "server_adapter_not_exact_disabled_single")
        prompt_tokens = []
        for prompt in prompts:
            response = server.request("/tokenize", 10, {"content": prompt, "add_special": True})
            tokens = response.get("tokens") if isinstance(response, dict) else None
            require(isinstance(tokens, list) and all(type(token) is int for token in tokens),
                    "prompt_tokenization_invalid")
            require(len(tokens) + comparison.SETTINGS["max_new_tokens"] + 8 <= args.context,
                    "prompt_generation_exceeds_context")
            prompt_tokens.append(len(tokens))
        metadata["prompt_tokens"] = prompt_tokens
        identity = {"engine": "llama.cpp_cpu", "engine_version": LLAMA_COMMIT,
                    "base_weights_sha256": spec["sha256"],
                    "tokenizer_sha256": TOKENIZER_CONFIG_SHA,
                    "chat_template_sha256": comparison.sha256(tokenizer["chat_template"].encode()),
                    "quantization": "unsloth_dynamic_" + args.quant + "_external_lora_f32"}
        base, adapted = run_pairs(plan, identity, prompts, server, deadline,
                                  progress=lambda value: print(json.dumps(value), flush=True))
        report = comparison.score_comparison(plan, base, adapted)
        write_json(args.work_dir / "report.json", report)
        metadata.update({"status": "completed" if report["coverage_complete"] else "partial",
                         "paired_completed_cases": report["paired_completed_cases"],
                         "frozen_cases": 8,
                         "report_sha256": file_sha(args.work_dir / "report.json")})
    except EvaluationError as error:
        metadata.update(status="failed", failure_code=str(error))
    except subprocess.TimeoutExpired:
        metadata.update(status="failed", failure_code="local_subprocess_timeout")
    except Exception:
        metadata.update(status="failed", failure_code="cpu_evaluation_failed")
    finally:
        stop_process(process)
        metadata["server_process_stopped"] = process is None or process.poll() is not None
        metadata["elapsed_seconds"] = round(time.monotonic() - started, 3)
        if not (args.work_dir / "report.json").exists():
            write_json(args.work_dir / "report.json", {
                "version": 1, "kind": "private_qwq_comparison_not_executed",
                "reasoning_included": False, "frozen_cases": 8, "paired_completed_cases": 0,
                "scientific_verification": "pending"})
        write_json(args.work_dir / "metadata.json", metadata)
    return metadata


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", "--output-dir", dest="work_dir", type=Path, required=True)
    parser.add_argument("--prepared-dir", type=Path)
    for name in ("adapter-dir", "llama-dir", "server-binary", "model-path",
                 "tokenizer-config", "base-config-dir"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--quant", choices=tuple(MODEL_FILES))
    parser.add_argument("--max-wall-seconds", type=int, default=9000)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--context", type=int, default=2048)
    args = parser.parse_args(argv)
    try:
        path_fields = {"adapter_dir": "adapter_dir", "llama_dir": "llama_cpp_dir",
                       "server_binary": "llama_server_path", "model_path": "base_gguf_path",
                       "tokenizer_config": "tokenizer_config_path", "base_config_dir": "base_config_dir"}
        if args.prepared_dir:
            prepared = comparison.load_json(args.prepared_dir / "prepared.json")
            require(not any(getattr(args, key) is not None for key in path_fields) and args.quant is None,
                    "prepared_and_explicit_inputs_conflict")
            for target, source in path_fields.items():
                value = prepared.get(source)
                require(isinstance(value, str) and Path(value).is_absolute(), "prepared_path_invalid")
                setattr(args, target, Path(value))
            args.quant = prepared.get("quant")
        else:
            require(all(getattr(args, key) is not None for key in path_fields), "local_inputs_missing")
            args.quant = args.quant or "iq3_xxs"
        metadata = execute(args)
    except Exception:
        print(json.dumps({"status": "failed", "failure_code": "invalid_execution_setup"}))
        return 1
    print(json.dumps({key: metadata[key] for key in (
        "status", "gpu_count", "provider_created", "server_process_stopped", "elapsed_seconds"
    )}), flush=True)
    return 0 if metadata["status"] in {"completed", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

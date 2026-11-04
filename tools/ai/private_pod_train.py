"""One bounded, single-role private LoRA pilot inside an authorized GPU pod.

The parent supplies base64(gzip(JSONL)) shards through HASLA_DATA_00, _01, ...
and HASLA_DATA_SHA256 (the uncompressed bytes). Validation uses the optional
HASLA_VALIDATION_* prefix. Alternatively HASLA_INPUT_ARTIFACT identifies an
immutable dataset artifact in that same PRIVATE W&B project. Input hashes
are always required. Neither test data nor raw text is logged by this pod.
Only adapter files are uploaded to the existing PRIVATE W&B project. This
program never deploys, promotes, starts, or deletes a GPU pod.
"""
from __future__ import annotations

import base64
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request


MAX_COMPRESSED_BYTES = 4 * 1024 * 1024
MAX_RAW_BYTES = 16 * 1024 * 1024
MAX_ARTIFACT_RAW_BYTES = 256 * 1024 * 1024
MAX_SCRIPT_BYTES = 256 * 1024
MAX_PARTS = 100
ADAPTER_TOTAL_LIMITS = {"solver": 2 * 1024**3, "chat": 4 * 1024**3}
MAX_ADAPTER_CONFIG_BYTES = 1024 * 1024
ADAPTER_FILENAMES = ("adapter_config.json", "adapter_model.safetensors")
MAX_TRAINER_DIAGNOSTIC_BYTES = 64 * 1024
# train_lora.py pins per-device batch=1 and gradient accumulation=8.
# Keep this local policy independent of caller-provided environment settings.
PILOT_EFFECTIVE_BATCH_ROWS = 8
ALLOWED_WANDB_BASES = {"https://api.wandb.ai", "https://api.forge.coreweave.com"}
CODE_ROOT = "https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io"
SHA_PATTERN = re.compile(r"[a-f0-9]{64}\Z")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")


class PilotError(RuntimeError):
    """Only fixed, nonsensitive error codes may be passed to this exception."""


class AdapterSizeError(PilotError):
    """An invalid-size error with only fixed filenames and byte counts attached."""
    def __init__(self, filename, file_bytes, total_bytes, limit_bytes):
        super().__init__("invalid_adapter_size")
        self.safe_details = {"adapter_size_filename": filename if filename in ADAPTER_FILENAMES else "adapter_model.safetensors",
                             "observed_file_bytes": int(file_bytes), "observed_total_bytes": int(total_bytes),
                             "adapter_size_limit_bytes": int(limit_bytes)}


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha_file(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def required_name(env, key):
    value = env.get(key, "")
    if not SAFE_NAME.fullmatch(value):
        raise PilotError("missing_or_invalid_run_identity")
    return value


def decode_payload(env, prefix="HASLA_DATA", optional=False,
                   max_compressed=MAX_COMPRESSED_BYTES, max_raw=MAX_RAW_BYTES):
    pattern = re.compile(re.escape(prefix) + r"_(\d{2})\Z")
    parts = sorted((int(m.group(1)), value) for key, value in env.items()
                   if (m := pattern.fullmatch(key)))
    if not parts:
        if optional and not env.get(prefix + "_SHA256"):
            return None
        raise PilotError("missing_payload_shards")
    if len(parts) > MAX_PARTS or [n for n, _ in parts] != list(range(len(parts))):
        raise PilotError("noncontiguous_payload_shards")
    declared_parts = env.get(prefix + "_PARTS", env.get(prefix + "_COUNT"))
    if declared_parts is not None and declared_parts != str(len(parts)):
        raise PilotError("payload_part_count_mismatch")
    digest = env.get(prefix + "_SHA256", "").lower()
    if not SHA_PATTERN.fullmatch(digest):
        raise PilotError("missing_or_invalid_payload_hash")
    if any(not isinstance(value, str) for _, value in parts):
        raise PilotError("invalid_payload_encoding")
    if sum(len(value) for _, value in parts) > ((max_compressed + 2) // 3) * 4:
        raise PilotError("compressed_payload_limit")
    try:
        compressed = base64.b64decode("".join(v for _, v in parts), validate=True)
    except (ValueError, TypeError):
        raise PilotError("invalid_payload_encoding") from None
    if len(compressed) > max_compressed:
        raise PilotError("compressed_payload_limit")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as handle:
            raw = handle.read(max_raw + 1)
    except (OSError, EOFError):
        raise PilotError("invalid_payload_gzip") from None
    if len(raw) > max_raw:
        raise PilotError("uncompressed_payload_limit")
    if sha_bytes(raw) != digest:
        raise PilotError("payload_hash_mismatch")
    return raw


def rows_from_payload(raw, expected_split, data_format="text"):
    if data_format not in ("text", "chat"):
        raise PilotError("unsupported_payload_format")
    try:
        # JSON Lines uses LF delimiters. U+0085/U+2028/U+2029 may legally occur
        # inside JSON strings and must not be treated as record boundaries.
        lines = raw.decode("utf-8-sig").split("\n")
    except UnicodeError:
        raise PilotError("payload_not_utf8") from None
    rows = []
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            raise PilotError("payload_invalid_jsonl") from None
        if not isinstance(row, dict):
            raise PilotError("payload_invalid_record")
        if data_format == "text":
            if not isinstance(row.get("text"), str) or not row["text"].strip() or "messages" in row:
                raise PilotError("payload_invalid_text_record")
        else:
            messages = row.get("messages")
            if (not isinstance(messages, list) or not 2 <= len(messages) <= 512 or "text" in row
                    or any(not isinstance(m, dict) or m.get("role") not in ("system", "user", "assistant")
                           or not isinstance(m.get("content"), str) or not m["content"].strip() for m in messages)
                    or not any(m["role"] == "user" for m in messages) or messages[-1]["role"] != "assistant"):
                raise PilotError("payload_invalid_chat_record")
        metadata = row.get("metadata", {})
        if not isinstance(metadata, dict):
            raise PilotError("payload_invalid_metadata")
        labels = [v for v in (row.get("split"), metadata.get("split")) if v is not None]
        if any(label != expected_split for label in labels):
            raise PilotError("test_or_wrong_split_in_payload")
        rows.append(row)
    if not rows:
        raise PilotError("payload_has_no_records")
    return rows


def row_content(row):
    if isinstance(row.get("text"), str):
        return row["text"]
    return json.dumps(row.get("messages"), sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def row_group(row):
    meta = row.get("metadata", {})
    for key in ("group_id", "duplicate_cluster_id", "document_id", "thread_id", "conversation_id", "source_id"):
        if meta.get(key) or row.get(key):
            return str(meta.get(key) or row[key])
    return sha_bytes(row_content(row).encode("utf-8"))


def verify_partitions(training, validation):
    if not validation:
        return
    if {row_group(r) for r in training} & {row_group(r) for r in validation}:
        raise PilotError("training_validation_group_overlap")
    if {sha_bytes(row_content(r).encode("utf-8")) for r in training} & {
            sha_bytes(row_content(r).encode("utf-8")) for r in validation}:
        raise PilotError("training_validation_content_overlap")


def role_input(env):
    role, data_format = env.get("ROLE"), env.get("HASLA_DATA_FORMAT")
    if role not in ("chat", "solver") or data_format not in ("chat", "text"):
        raise PilotError("missing_or_invalid_training_role_format")
    if role == "chat" and data_format != "chat":
        raise PilotError("role_format_mismatch")
    return role, data_format


def validate_row_roles(rows, role, data_format):
    for row in rows:
        metadata = row.get("metadata", {})
        labels = (row.get("training_role"), row.get("target_role"),
                  metadata.get("training_role"), metadata.get("target_role"))
        if any(label is not None and label != role for label in labels):
            raise PilotError("payload_training_role_mismatch")
        if role == "solver" and data_format == "chat":
            reviewed = row.get("review_status", metadata.get("review_status"))
            if reviewed not in ("verified", "approved"):
                raise PilotError("solver_chat_requires_verified_solution")


def assert_private_project(env, opener=None):
    """Fail closed: do not create/change a project or infer its privacy.

    W&B's default Project fragment omits access, so query the project access
    explicitly. The parent creates/verifies the project before provisioning.
    Official SDK project query shape: wandb/wandb/apis/public/projects.py.
    """
    entity = required_name(env, "WANDB_ENTITY")
    project = required_name(env, "WANDB_PROJECT")
    base = env.get("WANDB_BASE_URL", "https://api.wandb.ai").rstrip("/")
    if base not in ALLOWED_WANDB_BASES or not env.get("WANDB_API_KEY"):
        raise PilotError("missing_or_invalid_wandb_configuration")
    request = urllib.request.Request(base + "/graphql", method="POST", data=json.dumps({
        "query": "query PrivateProject($entity:String!,$project:String!){project(name:$project,entityName:$entity){name access}}",
        "variables": {"entity": entity, "project": project},
    }).encode(), headers={
        "Content-Type": "application/json",
        "Authorization": "Basic " + base64.b64encode(("api:" + env["WANDB_API_KEY"]).encode()).decode(),
    })
    try:
        with (opener or urllib.request.urlopen)(request, timeout=45) as response:
            data = json.loads(response.read(256 * 1024))
    except Exception:
        raise PilotError("wandb_privacy_check_failed") from None
    project_data = (data.get("data") or {}).get("project") if isinstance(data, dict) else None
    if data.get("errors") or not isinstance(project_data, dict) or project_data.get("name") != project:
        raise PilotError("wandb_project_not_verified")
    if project_data.get("access") != "PRIVATE":
        raise PilotError("wandb_project_not_private")
    return {"entity": entity, "project": project, "base_url": base, "access": "PRIVATE"}


def validate_input_artifact_reference(env):
    entity = required_name(env, "WANDB_ENTITY")
    project = required_name(env, "WANDB_PROJECT")
    reference = env.get("HASLA_INPUT_ARTIFACT", "")
    prefix = f"{entity}/{project}/"
    if not reference.startswith(prefix):
        raise PilotError("input_artifact_outside_private_project")
    tail = reference[len(prefix):]
    match = re.fullmatch(r"([A-Za-z0-9][A-Za-z0-9_.-]{0,127}):(v\d+)", tail)
    if not match:
        raise PilotError("input_artifact_requires_exact_version")
    return reference


def artifact_payloads(env, workspace, wandb_module, private):
    """Download only two allowlisted immutable dataset files, then verify bytes.

    The caller must first perform the live PRIVATE project check. W&B's SDK
    Artifact.download(root=..., allow_missing_references=False, skip_cache=True)
    is documented at docs.coreweave.com/products/wandb/ref/python/experiments/artifact.
    """
    if private.get("access") != "PRIVATE":
        raise PilotError("wandb_project_not_private")
    reference = validate_input_artifact_reference(env)
    _, data_format = role_input(env)
    train_name, validation_name = f"train.{data_format}.jsonl", f"validation.{data_format}.jsonl"
    expected = {train_name: env.get("HASLA_DATA_SHA256", "").lower()}
    validation_hash = env.get("HASLA_VALIDATION_SHA256", env.get("HASLA_DATA_VALIDATION_SHA256", ""))
    if validation_hash:
        expected[validation_name] = validation_hash.lower()
    if any(not SHA_PATTERN.fullmatch(digest) for digest in expected.values()):
        raise PilotError("missing_or_invalid_payload_hash")
    root = Path(workspace) / "input-artifact"
    if root.exists() or root.is_symlink():
        raise PilotError("input_artifact_directory_already_exists")
    api = wandb_module.Api(api_key=env["WANDB_API_KEY"],
                           overrides={"base_url": private["base_url"]}, timeout=45)
    artifact = api.artifact(reference, type="dataset")
    if artifact.qualified_name != reference or artifact.type != "dataset" or artifact.state != "COMMITTED":
        raise PilotError("input_artifact_identity_mismatch")
    if getattr(artifact, "is_link", False):
        raise PilotError("input_artifact_links_not_allowed")
    entries = artifact.manifest.entries
    if set(entries) != set(expected):
        raise PilotError("input_artifact_unexpected_files")
    for entry in entries.values():
        if getattr(entry, "ref", None):
            raise PilotError("input_artifact_external_reference")
        size = getattr(entry, "size", None)
        if type(size) is not int or not 0 < size <= MAX_ARTIFACT_RAW_BYTES:
            raise PilotError("input_artifact_file_size_limit")
    downloaded = artifact.download(root=str(root), allow_missing_references=False, skip_cache=True)
    if root.is_symlink() or not root.is_dir() or Path(downloaded).resolve() != root.resolve():
        raise PilotError("input_artifact_unsafe_download_path")
    actual = list(root.iterdir())
    if {path.name for path in actual} != set(expected):
        raise PilotError("input_artifact_unexpected_files")
    payloads = {}
    for path in actual:
        if path.is_symlink() or not path.is_file() or path.resolve().parent != root.resolve():
            raise PilotError("input_artifact_unsafe_file")
        if path.stat().st_size != entries[path.name].size or not 0 < path.stat().st_size <= MAX_ARTIFACT_RAW_BYTES:
            raise PilotError("input_artifact_file_size_limit")
        raw = path.read_bytes()
        if sha_bytes(raw) != expected[path.name]:
            raise PilotError("payload_hash_mismatch")
        payloads[path.name] = raw
    return payloads[train_name], payloads.get(validation_name)


def fetch_pinned_code(env, destination, filename, hash_key, opener=None):
    commit = env.get("REPO_SHA", env.get("GITHUB_SHA", ""))
    digest = env.get(hash_key, "").lower()
    if not re.fullmatch(r"[a-f0-9]{40}", commit) or not SHA_PATTERN.fullmatch(digest):
        raise PilotError("missing_or_invalid_pinned_training_code")
    request = urllib.request.Request(f"{CODE_ROOT}/{commit}/tools/ai/{filename}")
    try:
        with (opener or urllib.request.urlopen)(request, timeout=45) as response:
            raw = response.read(MAX_SCRIPT_BYTES + 1)
    except Exception:
        raise PilotError("training_code_download_failed") from None
    if len(raw) > MAX_SCRIPT_BYTES or sha_bytes(raw) != digest:
        raise PilotError("training_code_hash_mismatch")
    Path(destination).write_bytes(raw)
    return digest


def fetch_training_script(env, destination, opener=None):
    return fetch_pinned_code(env, destination, "train_lora.py", "HASLA_TRAIN_SCRIPT_SHA256", opener)


def fetch_role_config(env, destination, opener=None):
    return fetch_pinned_code(env, destination, "role_config.py", "HASLA_ROLE_CONFIG_SHA256", opener)


def pinned_role_settings(path, role, data_format):
    # Execute only the pure configuration file whose full bytes were SHA-checked.
    name = "_hasla_pinned_role_config_" + sha_file(path)
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise PilotError("invalid_pinned_role_configuration")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    try:
        config = dict(module.validate_role_format(role, data_format))
    except (ValueError, KeyError, TypeError):
        raise PilotError("role_format_mismatch") from None
    if (config.get("role") != role or data_format not in config.get("allowed_formats", ())
            or type(config.get("default_rank")) is not int or not 1 <= config["default_rank"] <= 32
            or type(config.get("max_steps")) is not int or not 1 <= config["max_steps"] <= 32768
            or type(config.get("max_length")) is not int or not 128 <= config["max_length"] <= 4096
            or not isinstance(config.get("base_model"), str) or not config["base_model"]
            or not isinstance(config.get("base_aliases"), list) or config["base_model"] not in config["base_aliases"]
            or any(not isinstance(alias, str) or not alias for alias in config["base_aliases"])):
        raise PilotError("invalid_pinned_role_configuration")
    expected_precision = "bf16" if role == "chat" else "4bit"
    if (config.get("precision") != expected_precision or config.get("load_in_4bit") is not (role == "solver")
            or config.get("load_in_16bit") is not (role == "chat")
            or config.get("loader") != ("FastModel" if role == "chat" else "FastLanguageModel")
            or config.get("training_method") != ("lora" if role == "chat" else "qlora")):
        raise PilotError("training_role_precision_mismatch")
    return config


def training_command(script, data, adapter, validation=None, config=None, data_format="text"):
    if config is None:
        raise PilotError("validated_role_configuration_required")
    command = [sys.executable, str(script), "--base", config["role"], "--format", data_format,
               "--rank", str(config["default_rank"]), "--max-steps", str(config["max_steps"]),
               "--epochs", "1", "--lr", "1e-5", "--max-len", str(config["max_length"]),
               "--holdout", "0", str(data), str(adapter)]
    if validation is not None:
        command.extend(["--validation-data", str(validation)])
    return command


def data_bounded_settings(config, training_rows):
    """Cap a pilot at approximately one pass over the validated input rows.

    A copied configuration drives the trainer command, report verification and
    public-safe result metadata so a tiny corpus cannot silently cycle to the
    role's full step cap. No environment override can increase this bound.
    """
    if type(training_rows) is not int or training_rows < 1:
        raise PilotError("invalid_validated_training_row_count")
    if type(config.get("max_steps")) is not int or not 1 <= config["max_steps"] <= 32768:
        raise PilotError("invalid_pinned_role_configuration")
    bounded = dict(config)
    bounded["role_max_steps"] = config["max_steps"]
    bounded["effective_batch_rows"] = PILOT_EFFECTIVE_BATCH_ROWS
    bounded["max_steps"] = min(config["max_steps"],
                               (training_rows + PILOT_EFFECTIVE_BATCH_ROWS - 1) // PILOT_EFFECTIVE_BATCH_ROWS)
    return bounded


def training_environment(env):
    # Only the local JSONL file is needed by the trainer; do not forward corpus shards.
    child = {key: value for key, value in env.items()
             if not key.startswith(("HASLA_DATA_", "HASLA_VALIDATION_"))
             and key not in ("WANDB_API_KEY", "RUNPOD_API_KEY", "HASLA_INPUT_ARTIFACT", "HASLA_INITIAL_ADAPTER",
                             "HASLA_RESUME_SCRIPT_SHA256")}
    child.update({"WANDB_MODE": "disabled", "WANDB_DISABLED": "true", "WANDB_CONSOLE": "off",
                  "WANDB_DISABLE_CODE": "true", "WANDB_SILENT": "true", "HF_HUB_DISABLE_TELEMETRY": "1",
                  "TOKENIZERS_PARALLELISM": "false"})
    return child


def adapter_inventory(adapter, config=None):
    if config is None:
        raise PilotError("validated_role_configuration_required")
    adapter = Path(adapter)
    role = config.get("role")
    if role not in ADAPTER_TOTAL_LIMITS:
        raise PilotError("validated_role_configuration_required")
    total_limit = ADAPTER_TOTAL_LIMITS[role]
    # Inspect all sizes before hashing anything. The bounded limit includes the
    # PEFT header/config, while the JSON config also has its own small limit.
    sizes = {}
    for name in ADAPTER_FILENAMES:
        path = adapter / name
        if not path.is_file() or path.is_symlink():
            raise PilotError("expected_adapter_file_missing")
        sizes[name] = path.stat().st_size
    total = sum(sizes.values())
    for name, size in sizes.items():
        limit = MAX_ADAPTER_CONFIG_BYTES if name == "adapter_config.json" else total_limit
        if not 0 < size <= limit:
            raise AdapterSizeError(name, size, total, limit)
    if total > total_limit:
        raise AdapterSizeError("adapter_model.safetensors", sizes["adapter_model.safetensors"], total, total_limit)
    files = [{"name": name, "bytes": sizes[name], "sha256": sha_file(adapter / name)} for name in ADAPTER_FILENAMES]
    peft = json.loads((adapter / "adapter_config.json").read_text(encoding="utf-8"))
    # Validate rather than silently relabeling an adapter trained against another base.
    if peft.get("base_model_name_or_path") not in config["base_aliases"]:
        raise PilotError("adapter_base_model_mismatch")
    if peft.get("peft_type") != "LORA":
        raise PilotError("adapter_type_mismatch")
    if type(peft.get("r")) is not int or peft["r"] != config["default_rank"]:
        raise PilotError("adapter_rank_mismatch")
    return files, sha_bytes(json.dumps(files, sort_keys=True, separators=(",", ":")).encode())


def training_report(adapter, config, data_format, training_sha, validation_sha, initial_model_sha=None):
    path = Path(adapter) / "hasla_training_manifest.json"
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= 64 * 1024:
        raise PilotError("verified_training_report_missing")
    report = json.loads(path.read_text(encoding="utf-8"))
    expected = {"role": config["role"], "base_model": config["base_model"],
                "format": data_format, "precision": config["precision"],
                "training_method": config["training_method"], "rank": config["default_rank"],
                "max_length": config["max_length"], "max_steps": config["max_steps"],
                "training_sha256": training_sha, "validation_sha256": validation_sha}
    if not isinstance(report, dict) or any(report.get(k) != value for k, value in expected.items()):
        raise PilotError("training_report_role_or_input_mismatch")
    if report.get('initial_adapter_model_sha256') != initial_model_sha or report.get('optimizer_state_restored') is True:
        raise PilotError('training_report_initial_adapter_mismatch')
    steps = report.get("steps_completed")
    if report.get("weights_updated") is not True or type(steps) is not int or not 1 <= steps <= config["max_steps"]:
        raise PilotError("training_report_has_no_bounded_weight_update")
    losses = {}
    for name in ("train_loss", "eval_loss"):
        value = report.get(name)
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise PilotError("training_report_invalid_loss")
            losses[name] = float(value)
        else:
            losses[name] = None
    return {**expected, "steps_completed": steps, "scheduled_steps_completed": steps == config['max_steps'], **losses}


def safe_failure(error, stage):
    result = {"status": "failed", "stage": stage,
            "error_code": str(error) if isinstance(error, PilotError) else type(error).__name__,
            "trace": [{"file": Path(frame.filename).name, "line": frame.lineno, "function": frame.name}
                      for frame in traceback.extract_tb(error.__traceback__)[-6:]],
            "deployed": False, "promoted": False}
    if isinstance(error, AdapterSizeError):
        result.update(error.safe_details)
    return result


DIAGNOSTIC_MODULES = frozenset(("unsloth", "unsloth_zoo", "torch", "torchao", "transformers", "trl",
    "datasets", "peft", "accelerate", "triton", "bitsandbytes", "flash_attn", "xformers", "wandb",
    "safetensors", "tokenizers", "sentencepiece", "huggingface_hub", "numpy", "PIL", "packaging",
    "cut_cross_entropy", "psutil", "requests", "sacremoses"))
DIAGNOSTIC_SYMBOLS = frozenset(("FastModel", "FastLanguageModel", "SFTTrainer", "SFTConfig", "HybridCache",
    "DynamicCache", "AutoModelForCausalLM", "AutoProcessor", "Gemma4ForConditionalGeneration",
    "Gemma4Config", "Qwen2ForCausalLM", "ROPE_INIT_FUNCTIONS", "is_torchdynamo_compiling",
    "DistributedDataParallelKwargs", "BloomPreTrainedModel", "prepare_model_for_kbit_training"))
DIAGNOSTIC_KEYWORDS = frozenset(("tokenizer", "processing_class", "max_seq_length", "max_length",
    "dataset_text_field", "eval_strategy", "evaluation_strategy", "load_in_4bit", "load_in_16bit",
    "model_name", "trust_remote_code", "attn_implementation", "torch_dtype", "dtype",
    "use_gradient_checkpointing", "packing", "formatting_func", "dataset_kwargs"))


def classify_trainer_stderr(raw):
    """Return fixed public diagnostics, never an arbitrary captured identifier.

    Module/symbol/keyword names are emitted only when present in the explicit
    public-library allowlists above. Unknown names, paths, values and error text
    remain private even if they look like valid Python identifiers.
    """
    text = raw[-MAX_TRAINER_DIAGNOSTIC_BYTES:].decode("utf-8", errors="replace") if isinstance(raw, bytes) else ""
    if re.search(r"CUDA (?:error:\s*)?out of memory|torch\.OutOfMemoryError:.*CUDA", text, re.I):
        return {"trainer_error_kind": "cuda_out_of_memory", "trainer_error_subject": "cuda"}
    for marker, subject in (("GatedRepoError", "gated_repository"),
                            ("RepositoryNotFoundError", "repository_not_found"),
                            ("HFValidationError", "repository_identifier"),
                            ("HfHubHTTPError", "huggingface_http")):
        if re.search(r"\b" + marker + r"\b", text):
            return {"trainer_error_kind": "huggingface_access", "trainer_error_subject": subject}
    match = re.search(r"ModuleNotFoundError:\s*No module named ['\"]([A-Za-z0-9_.]+)['\"]", text)
    if match:
        module = match.group(1).split(".")[0]
        return {"trainer_error_kind": "missing_module", "trainer_error_subject": module if module in DIAGNOSTIC_MODULES else "unknown_module"}
    match = re.search(r"ImportError:\s*cannot import name ['\"]([A-Za-z0-9_]+)['\"]", text)
    if match:
        name = match.group(1)
        return {"trainer_error_kind": "missing_import_symbol", "trainer_error_subject": name if name in DIAGNOSTIC_SYMBOLS else "unknown_symbol"}
    match = re.search(r"TypeError:[^\n]{0,256}unexpected keyword argument ['\"]([A-Za-z0-9_]+)['\"]", text)
    if match:
        name = match.group(1)
        return {"trainer_error_kind": "unexpected_keyword", "trainer_error_subject": name if name in DIAGNOSTIC_KEYWORDS else "unknown_keyword"}
    match = re.search(r"AttributeError:\s*module ['\"]([A-Za-z0-9_.]+)['\"] has no attribute ['\"]([A-Za-z0-9_]+)['\"]", text)
    if match and match.group(1).split(".")[0] in DIAGNOSTIC_MODULES:
        name = match.group(2)
        return {"trainer_error_kind": "missing_library_attribute", "trainer_error_subject": name if name in DIAGNOSTIC_SYMBOLS else "unknown_symbol"}
    if re.search(r"(?im)^(?:ValueError|NotImplementedError|RuntimeError):[^\n]{0,512}(?:unsupported model|unrecognized configuration class|model[^\n]{0,150}not supported|Unsloth[^\n]{0,150}not support)", text):
        subject = "gemma4" if re.search(r"gemma[_ -]?4", text, re.I) else "qwq" if re.search(r"\bQwQ\b", text, re.I) else "unknown_model"
        return {"trainer_error_kind": "unsupported_model", "trainer_error_subject": subject}
    if "Cannot copy out of meta tensor" in text:
        return {"trainer_error_kind": "model_initialization", "trainer_error_subject": "meta_tensor"}
    if re.search(r"bfloat16[^\n]{0,120}not supported|does not support[^\n]{0,120}bfloat16", text, re.I):
        return {"trainer_error_kind": "unsupported_precision", "trainer_error_subject": "bf16"}
    if "CUDA Setup failed despite GPU being available" in text:
        return {"trainer_error_kind": "quantization_setup", "trainer_error_subject": "bitsandbytes"}
    public_errors = ("TypeError", "ValueError", "ImportError", "RuntimeError", "AssertionError",
                     "NotImplementedError", "FileNotFoundError", "PermissionError", "IndexError", "KeyError", "AttributeError")
    matches = re.findall(r"(?m)^(?:[A-Za-z0-9_.]+\.)?(" + "|".join(public_errors) + r"):", text)
    if matches:
        return {"trainer_error_kind": "python_error", "trainer_error_subject": matches[-1]}
    return {"trainer_error_kind": "unclassified", "trainer_error_subject": "not_disclosed"}


def diagnostic_from_private_stderr(stream):
    try:
        stream.flush()
        stream.seek(0, io.SEEK_END)
        stream.seek(max(0, stream.tell() - MAX_TRAINER_DIAGNOSTIC_BYTES))
        return classify_trainer_stderr(stream.read(MAX_TRAINER_DIAGNOSTIC_BYTES))
    except (OSError, ValueError):
        return {"trainer_error_kind": "unclassified", "trainer_error_subject": "not_disclosed"}


def read_numeric_progress(path):
    """Read a tiny fixed schema from our trainer; discard unexpected fields."""
    try:
        path = Path(path)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 8192:
            return None
        value = json.loads(path.read_text(encoding='utf8'))
        if (not isinstance(value, dict) or type(value.get('schema_version')) is not int or value['schema_version'] != 1
                or value.get('phase') not in ('training', 'training_ended')
                or type(value.get('max_steps')) is not int or not 1 <= value['max_steps'] <= 32768
                or type(value.get('steps_completed')) is not int
                or not 0 <= value['steps_completed'] <= value['max_steps']
                or type(value.get('elapsed_seconds')) is not int or not 0 <= value['elapsed_seconds'] <= 18000):
            return None
        result = {key: value[key] for key in ('schema_version', 'phase', 'max_steps', 'steps_completed', 'elapsed_seconds')}
        for key in ('train_loss', 'eval_loss'):
            number = value.get(key)
            if type(number) in (int, float) and math.isfinite(number) and abs(number) <= 1000000:
                result[key] = number
        return result
    except (OSError, ValueError, TypeError):
        return None


def supervise_training(command, *, cwd, env, stderr, timeout, run, progress_path,
                       popen=subprocess.Popen, clock=time.monotonic, interval=30):
    """Send safe heartbeats while waiting; kill and reap on timeout or error."""
    started = clock()
    process = popen(command, cwd=cwd, env=env, stdout=subprocess.DEVNULL, stderr=stderr,
                    start_new_session=os.name == 'posix')
    try:
        while True:
            remaining = timeout - (clock() - started)
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            try:
                code = process.wait(timeout=min(interval, remaining))
                return subprocess.CompletedProcess(command, code)
            except subprocess.TimeoutExpired:
                progress = read_numeric_progress(progress_path)
                heartbeat = {'worker_supervisor_alive_seconds': max(0, int(clock() - started))}
                if progress:
                    heartbeat['optimizer_steps_completed'] = progress['steps_completed']
                try:
                    if progress:
                        run.summary['optimizer_progress_json'] = json.dumps(progress, allow_nan=False)
                    run.log(heartbeat, commit=True)
                except Exception:
                    pass
    finally:
        if process.poll() is None:
            if os.name == 'posix' and type(getattr(process, 'pid', None)) is int:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                process.kill()
            process.wait()


def store_private_result(run, result):
    # GraphQL summaryMetrics may omit nested summary values. Persist a scalar
    # representation first so the parent can always observe terminal state.
    run.summary["private_training_result_json"] = json.dumps(result, ensure_ascii=True, separators=(",", ":"))
    run.summary["private_training_result"] = result
    if result.get("status") == "failed":
        run.summary["failure_stage"] = result["stage"]
        run.summary["failure_code"] = result["error_code"]
        for key in ("trainer_error_kind", "trainer_error_subject", "adapter_size_filename",
                    "observed_file_bytes", "observed_total_bytes", "adapter_size_limit_bytes",
                    "role", "steps_completed", "train_loss", "eval_loss", "weights_updated"):
            if key in result:
                run.summary[key] = result[key]


def publish_early_failure(env, workspace, private, result, wandb_module=None, opener=None):
    """Expose a pre-trainer failure to the parent only in a verified PRIVATE run.

    Code/input failures can occur before the normal model run is initialized.
    Publishing this minimal fixed-code summary lets the parent stop the paid Pod
    promptly. It never creates a project, changes visibility, or uploads data.
    A missing/unverified configuration performs no reporting network operation.
    """
    if not isinstance(private, dict) or private.get("access") != "PRIVATE":
        return
    try:
        role, data_format = role_input(env)
        run_id = required_name(env, "RUN")
        required_name(env, "ARTIFACT")
        entity, project = required_name(env, "WANDB_ENTITY"), required_name(env, "WANDB_PROJECT")
        base = env.get("WANDB_BASE_URL", "https://api.wandb.ai").rstrip("/")
        if (private.get("entity") != entity or private.get("project") != project
                or private.get("base_url") != base or base not in ALLOWED_WANDB_BASES
                or not env.get("WANDB_API_KEY") or result.get("status") != "failed"):
            return
        # Verify again immediately before initializing the minimal reporting run.
        if assert_private_project(env, opener) != private:
            return
        os.environ.update({"WANDB_CONSOLE": "off", "WANDB_DISABLE_CODE": "true",
                           "WANDB_SILENT": "true", "WANDB_BASE_URL": private["base_url"]})
        if wandb_module is None:
            import wandb as wandb_module
        settings = wandb_module.Settings(console="off", disable_code=True, save_code=False,
                                         disable_git=True, disable_job_creation=True,
                                         x_disable_meta=True, x_disable_stats=True, silent=True,
                                         base_url=private["base_url"])
        run = wandb_module.init(entity=entity, project=project, id=run_id, name=run_id,
                                resume="never", job_type="private-" + role + "-pilot-early-failure",
                                config={"role": role, "format": data_format, "private": True,
                                        "training_started": False, "weights_updated": False,
                                        "test_records_used": 0, "deploy": False, "promote": False},
                                settings=settings, dir=str(workspace))
        store_private_result(run, {**result, "training_started": False, "weights_updated": False})
        run.summary["status"] = "failed"
        run.finish(exit_code=1)
    except Exception:
        # Reporting is best effort; never expose an SDK's echoed request/secret.
        return


def run_pilot(env=None, workspace=Path("/workspace"), wandb_module=None,
              opener=None, runner=None):
    env = dict(os.environ if env is None else env)
    workspace = Path(workspace)
    run, stage, private = None, "configuration", None
    trainer_diagnostic = None
    verified_training = None
    initial_spec, initial_directory, resume_sha = None, None, None
    result_path = workspace / "result.json"
    try:
        role, data_format = role_input(env)
        required_name(env, "RUN")
        required_name(env, "ARTIFACT")
        if not env.get("HF_TOKEN"):
            raise PilotError("missing_huggingface_credential")
        if not workspace.is_dir():
            raise PilotError("workspace_not_found")
        stage = "payload_validation"
        if env.get("HASLA_INPUT_ARTIFACT"):
            # Check project visibility before downloading any private input artifact.
            validate_input_artifact_reference(env)
            stage = "privacy_verification"
            private = assert_private_project(env, opener)
            os.environ.update({"WANDB_CONSOLE": "off", "WANDB_DISABLE_CODE": "true",
                               "WANDB_SILENT": "true", "WANDB_BASE_URL": private["base_url"]})
            if wandb_module is None:
                import wandb as wandb_module
            stage = "input_artifact_verification"
            data, validation_data = artifact_payloads(env, workspace, wandb_module, private)
        else:
            data = decode_payload(env)
            validation_prefix = "HASLA_DATA_VALIDATION" if any(
                key.startswith("HASLA_DATA_VALIDATION_") for key in env) else "HASLA_VALIDATION"
            validation_data = decode_payload(env, validation_prefix, optional=True)
        stage = "payload_validation"
        training = rows_from_payload(data, "train", data_format)
        validation = rows_from_payload(validation_data, "validation", data_format) if validation_data is not None else []
        validate_row_roles(training + validation, role, data_format)
        verify_partitions(training, validation)
        stage = "privacy_verification"
        private = private or assert_private_project(env, opener)
        stage = "training_code_verification"
        script = workspace / "train_lora.py"
        script_sha = fetch_training_script(env, script, opener)
        stage = "role_config_verification"
        role_path = workspace / "role_config.py"
        role_sha = fetch_role_config(env, role_path, opener)
        config = data_bounded_settings(pinned_role_settings(role_path, role, data_format), len(training))
        if env.get('HASLA_INITIAL_ADAPTER') is not None:
            stage = 'initial_adapter_verification'
            try:
                raw_initial = env['HASLA_INITIAL_ADAPTER']
                if role != 'solver' or not isinstance(raw_initial, str) or len(raw_initial.encode()) > 16384:
                    raise ValueError('invalid solver continuation')
                helper_path = workspace / 'private_resume_adapter.py'
                resume_sha = fetch_pinned_code(env, helper_path, 'private_resume_adapter.py',
                                               'HASLA_RESUME_SCRIPT_SHA256', opener)
                spec = importlib.util.spec_from_file_location('_hasla_resume_' + resume_sha, helper_path)
                helper = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(helper)
                initial_spec = helper.validate_spec(json.loads(raw_initial), config)
                if initial_spec['entity'] != private['entity']:
                    raise ValueError('initial adapter project mismatch')
                if wandb_module is None:
                    import wandb as wandb_module
                api = wandb_module.Api(api_key=env['WANDB_API_KEY'], overrides={'base_url': private['base_url']}, timeout=30)
                initial_directory = workspace / 'initial-adapter'
                def checked_initial_privacy(requested):
                    if requested != private['entity']:
                        raise ValueError('initial adapter project mismatch')
                    return assert_private_project(env, opener)
                helper.download_initial_adapter(initial_spec, config, initial_directory, api, checked_initial_privacy)
            except Exception:
                raise PilotError('initial_adapter_verification_failed') from None
        data_path, validation_path, adapter = workspace / f"train.{data_format}.jsonl", None, workspace / "adapter"
        if adapter.exists():
            raise PilotError("adapter_output_already_exists")
        data_path.write_bytes(data)
        if validation_data is not None:
            validation_path = workspace / f"validation.{data_format}.jsonl"
            validation_path.write_bytes(validation_data)

        stage = "run_initialization"
        # Disable console, code, git, and runtime metadata capture. Do not log text/data artifacts.
        os.environ.update({"WANDB_CONSOLE": "off", "WANDB_DISABLE_CODE": "true", "WANDB_SILENT": "true",
                           "WANDB_BASE_URL": private["base_url"]})
        if wandb_module is None:
            import wandb as wandb_module
        settings = wandb_module.Settings(console="off", disable_code=True, save_code=False,
                                         disable_git=True, disable_job_creation=True,
                                         x_disable_meta=True, x_disable_stats=True, silent=True,
                                         base_url=private["base_url"])
        safe_config = {"role": role, "base_model": config["base_model"], "format": data_format,
                       "precision": config["precision"], "training_method": config["training_method"],
                       "rank": config["default_rank"], "max_steps": config["max_steps"],
                       "role_max_steps": config["role_max_steps"], "effective_batch_rows": config["effective_batch_rows"],
                       "epochs": 1, "learning_rate": 1e-5, "max_length": config["max_length"],
                       "training_records": len(training), "validation_records": len(validation),
                       "training_sha256": sha_bytes(data),
                       "input_artifact": env.get("HASLA_INPUT_ARTIFACT"),
                       "validation_sha256": sha_bytes(validation_data) if validation_data is not None else None,
                       "training_code_sha256": script_sha, "role_config_sha256": role_sha,
                       "repo_sha": env.get("REPO_SHA", env.get("GITHUB_SHA")),
                       "test_records_used": 0, "private": True, "deploy": False, "promote": False}
        run = wandb_module.init(entity=private["entity"], project=private["project"],
                                id=env["RUN"], name=env["RUN"], resume="never",
                                job_type="private-" + role + "-pilot", config=safe_config,
                                settings=settings, dir=str(workspace))
        stage = "training"
        run.summary["status"] = stage
        timeout = int(env.get("HASLA_TRAIN_TIMEOUT_SECONDS", "1200" if role == "chat" else "3600"))
        maximum_timeout = 1800 if role == "chat" else 14400
        if not 60 <= timeout <= maximum_timeout:
            raise PilotError("invalid_training_timeout")
        # The trainer's stdout remains discarded. Its stderr is private and
        # temporary; only a classified tail (never raw text) can leave this scope.
        with tempfile.SpooledTemporaryFile(max_size=MAX_TRAINER_DIAGNOSTIC_BYTES, mode="w+b") as private_stderr:
            try:
                command = training_command(script, data_path, adapter, validation_path, config, data_format)
                if initial_directory:
                    command.extend(['--resume-adapter', str(initial_directory)])
                if runner is not None:
                    completed = runner(command, cwd=str(workspace), env=training_environment(env),
                        stdout=subprocess.DEVNULL, stderr=private_stderr, timeout=timeout, check=False)
                else:
                    progress_path = workspace / 'optimizer-progress.json'
                    command.extend(['--progress-json', str(progress_path),
                                    '--train-wall-seconds', str(max(30, timeout - 600))])
                    completed = supervise_training(command, cwd=str(workspace), env=training_environment(env),
                        stderr=private_stderr, timeout=timeout, run=run, progress_path=progress_path)
            except Exception:
                trainer_diagnostic = diagnostic_from_private_stderr(private_stderr)
                raise
            if completed.returncode:
                trainer_diagnostic = diagnostic_from_private_stderr(private_stderr)
                raise PilotError("trainer_process_failed")

        stage = "adapter_validation"
        run.summary["status"] = stage
        report = verified_training = training_report(adapter, config, data_format, sha_bytes(data),
                                                     sha_bytes(validation_data) if validation_data is not None else None,
                                                     initial_spec['files'][1]['sha256'] if initial_spec else None)
        files, adapter_sha = adapter_inventory(adapter, config)
        # Check again immediately before uploading an adapter; never change project visibility here.
        assert_private_project(env, opener)
        stage = "uploading_adapter"
        run.summary["status"] = stage
        artifact = wandb_module.Artifact(env["ARTIFACT"], type="lora", metadata={
            "role": role, "base_model": config["base_model"], "format": data_format,
            "precision": config["precision"], "training_method": config["training_method"],
            "rank": config["default_rank"], "max_steps": config["max_steps"],
            "role_max_steps": config["role_max_steps"], "effective_batch_rows": config["effective_batch_rows"],
            "steps_completed": report["steps_completed"],
            "scheduled_steps_completed": report['scheduled_steps_completed'],
            "train_loss": report["train_loss"], "eval_loss": report["eval_loss"],
            "training_records": len(training), "validation_records": len(validation),
            "training_sha256": sha_bytes(data), "adapter_sha256": adapter_sha,
            "test_records_used": 0, "private": True, "promoted": False})
        if initial_spec:
            artifact.metadata.update(initial_adapter=initial_spec, resume_script_sha256=resume_sha,
                                     initial_adapter_model_sha256=initial_spec['files'][1]['sha256'], optimizer_state_restored=False)
        for file in files:
            artifact.add_file(str(adapter / file["name"]), name=file["name"])
        run.log_artifact(artifact, aliases=["pilot"])
        artifact.wait(timeout=600)
        exact = artifact.qualified_name
        expected_prefix = f"{private['entity']}/{private['project']}/{env['ARTIFACT']}:"
        if not isinstance(exact, str) or not exact.startswith(expected_prefix) or not re.fullmatch(
                r"v\d+", exact[len(expected_prefix):]):
            raise PilotError("artifact_exact_version_missing")
        result = {"status": "uploaded", "artifact": exact, "adapter_sha256": adapter_sha,
                  "role": role, "base_model": config["base_model"], "format": data_format,
                  "precision": config["precision"], "training_method": config["training_method"],
                  "rank": config["default_rank"], "max_steps": config["max_steps"],
                  "role_max_steps": config["role_max_steps"], "effective_batch_rows": config["effective_batch_rows"],
                  "steps_completed": report["steps_completed"],
                  "scheduled_steps_completed": report['scheduled_steps_completed'],
                  "train_loss": report["train_loss"], "eval_loss": report["eval_loss"],
                  "adapter_files": files, "training_records": len(training),
                  "validation_records": len(validation), "training_sha256": sha_bytes(data),
                  "test_records_used": 0, "weights_updated": True, "deployed": False, "promoted": False}
        if initial_spec:
            result.update(initial_adapter=initial_spec, resume_script_sha256=resume_sha,
                          initial_adapter_model_sha256=initial_spec['files'][1]['sha256'], optimizer_state_restored=False)
        store_private_result(run, result)
        run.summary["status"] = "uploaded"
        result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        run.finish()
        return result
    except Exception as error:
        result = safe_failure(error, stage)
        if trainer_diagnostic is not None:
            result.update(trainer_diagnostic)
        if verified_training is not None:
            result.update({key: verified_training[key] for key in ("role", "steps_completed", "train_loss", "eval_loss")})
            result["weights_updated"] = True
        if workspace.is_dir():
            try:
                result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            except OSError:
                pass
        if run is not None:
            try:
                store_private_result(run, result)
                run.summary["status"] = "failed"
                run.finish(exit_code=1)
            except Exception:
                pass
        else:
            publish_early_failure(env, workspace, private, result, wandb_module, opener)
        return result


def workspace_from_environment(env):
    selected = env.get("HASLA_WORKSPACE")
    if selected is None:
        return Path("/workspace")
    role, _ = role_input(env)
    if selected != f"/workspace/{role}":
        raise PilotError("invalid_role_workspace")
    return Path(selected)


def main():
    # SDK/third-party output is suppressed too, including any unexpected exception text.
    with open(os.devnull, "w") as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        try:
            workspace = workspace_from_environment(os.environ)
            if workspace.is_symlink():
                raise PilotError("invalid_role_workspace")
            workspace.mkdir(parents=True, exist_ok=True)
            result = run_pilot(workspace=workspace)
        except Exception as error:
            result = safe_failure(error, "configuration")
    print(json.dumps({"status": result["status"], "artifact": result.get("artifact"),
                      "error_code": result.get("error_code"), "stage": result.get("stage")}), flush=True)
    return 0 if result["status"] == "uploaded" else 1


if __name__ == "__main__":
    raise SystemExit(main())

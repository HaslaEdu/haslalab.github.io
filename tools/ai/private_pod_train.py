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
import subprocess
import sys
import traceback
import urllib.request


MAX_COMPRESSED_BYTES = 4 * 1024 * 1024
MAX_RAW_BYTES = 16 * 1024 * 1024
MAX_SCRIPT_BYTES = 256 * 1024
MAX_PARTS = 100
MAX_ADAPTER_BYTES = 512 * 1024 * 1024
# train_lora.py pins per-device batch=1 and gradient accumulation=8.
# Keep this local policy independent of caller-provided environment settings.
PILOT_EFFECTIVE_BATCH_ROWS = 8
ALLOWED_WANDB_BASES = {"https://api.wandb.ai", "https://api.forge.coreweave.com"}
CODE_ROOT = "https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io"
SHA_PATTERN = re.compile(r"[a-f0-9]{64}\Z")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")


class PilotError(RuntimeError):
    """Only fixed, nonsensitive error codes may be passed to this exception."""


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
        lines = raw.decode("utf-8-sig").splitlines()
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
        if type(size) is not int or not 0 < size <= MAX_RAW_BYTES:
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
        if path.stat().st_size != entries[path.name].size or not 0 < path.stat().st_size <= MAX_RAW_BYTES:
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
        module.validate_role_format(role, data_format)
        config = dict(module.get_role_config(role))
    except (ValueError, KeyError, TypeError):
        raise PilotError("role_format_mismatch") from None
    if (config.get("role") != role or data_format not in config.get("allowed_formats", ())
            or type(config.get("default_rank")) is not int or not 1 <= config["default_rank"] <= 32
            or type(config.get("max_steps")) is not int or not 1 <= config["max_steps"] <= 32
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
    if type(config.get("max_steps")) is not int or not 1 <= config["max_steps"] <= 32:
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
             and key not in ("WANDB_API_KEY", "RUNPOD_API_KEY", "HASLA_INPUT_ARTIFACT")}
    child.update({"WANDB_MODE": "disabled", "WANDB_DISABLED": "true", "WANDB_CONSOLE": "off",
                  "WANDB_DISABLE_CODE": "true", "WANDB_SILENT": "true", "HF_HUB_DISABLE_TELEMETRY": "1",
                  "TOKENIZERS_PARALLELISM": "false"})
    return child


def adapter_inventory(adapter, config=None):
    if config is None:
        raise PilotError("validated_role_configuration_required")
    adapter = Path(adapter)
    files = []
    for name in ("adapter_config.json", "adapter_model.safetensors"):
        path = adapter / name
        if not path.is_file() or path.is_symlink():
            raise PilotError("expected_adapter_file_missing")
        size = path.stat().st_size
        if not 0 < size <= MAX_ADAPTER_BYTES:
            raise PilotError("invalid_adapter_size")
        files.append({"name": name, "bytes": size, "sha256": sha_file(path)})
    if sum(f["bytes"] for f in files) > MAX_ADAPTER_BYTES:
        raise PilotError("invalid_adapter_size")
    peft = json.loads((adapter / "adapter_config.json").read_text(encoding="utf-8"))
    # Validate rather than silently relabeling an adapter trained against another base.
    if peft.get("base_model_name_or_path") not in config["base_aliases"]:
        raise PilotError("adapter_base_model_mismatch")
    if peft.get("peft_type") != "LORA":
        raise PilotError("adapter_type_mismatch")
    if type(peft.get("r")) is not int or peft["r"] != config["default_rank"]:
        raise PilotError("adapter_rank_mismatch")
    return files, sha_bytes(json.dumps(files, sort_keys=True, separators=(",", ":")).encode())


def training_report(adapter, config, data_format, training_sha, validation_sha):
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
    return {**expected, "steps_completed": steps, **losses}


def safe_failure(error, stage):
    return {"status": "failed", "stage": stage,
            "error_code": str(error) if isinstance(error, PilotError) else type(error).__name__,
            "trace": [{"file": Path(frame.filename).name, "line": frame.lineno, "function": frame.name}
                      for frame in traceback.extract_tb(error.__traceback__)[-6:]],
            "deployed": False, "promoted": False}


def run_pilot(env=None, workspace=Path("/workspace"), wandb_module=None,
              opener=None, runner=None):
    env = dict(os.environ if env is None else env)
    workspace = Path(workspace)
    run, stage, private = None, "configuration", None
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
        timeout = int(env.get("HASLA_TRAIN_TIMEOUT_SECONDS", "3600"))
        if not 60 <= timeout <= 5400:
            raise PilotError("invalid_training_timeout")
        completed = (runner or subprocess.run)(training_command(script, data_path, adapter, validation_path, config, data_format),
            cwd=str(workspace), env=training_environment(env), stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=timeout, check=False)
        if completed.returncode:
            raise PilotError("trainer_process_failed")

        stage = "adapter_validation"
        run.summary["status"] = stage
        files, adapter_sha = adapter_inventory(adapter, config)
        report = training_report(adapter, config, data_format, sha_bytes(data),
                                 sha_bytes(validation_data) if validation_data is not None else None)
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
            "train_loss": report["train_loss"], "eval_loss": report["eval_loss"],
            "training_records": len(training), "validation_records": len(validation),
            "training_sha256": sha_bytes(data), "adapter_sha256": adapter_sha,
            "test_records_used": 0, "private": True, "promoted": False})
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
                  "train_loss": report["train_loss"], "eval_loss": report["eval_loss"],
                  "adapter_files": files, "training_records": len(training),
                  "validation_records": len(validation), "training_sha256": sha_bytes(data),
                  "test_records_used": 0, "weights_updated": True, "deployed": False, "promoted": False}
        run.summary["private_training_result"] = result
        run.summary["status"] = "uploaded"
        result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        run.finish()
        return result
    except Exception as error:
        result = safe_failure(error, stage)
        if workspace.is_dir():
            result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        if run is not None:
            try:
                run.summary["private_training_result"] = result
                run.summary["status"] = "failed"
                run.finish(exit_code=1)
            except Exception:
                pass
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

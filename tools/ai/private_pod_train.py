"""One bounded private textbook LoRA pilot inside an already authorized GPU pod.

The parent supplies base64(gzip(JSONL)) shards through HASLA_DATA_00, _01, ...
and HASLA_DATA_SHA256 (the uncompressed bytes). Validation uses the optional
HASLA_VALIDATION_* prefix. Neither test data nor raw text is logged/uploaded.
Only adapter files are uploaded to an existing PRIVATE W&B project. This
program never deploys, promotes, starts, or deletes a GPU pod.
"""
from __future__ import annotations

import base64
import contextlib
import gzip
import hashlib
import io
import json
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
BASE_MODEL = "Qwen/QwQ-32B"
BASE_ALIASES = {BASE_MODEL, "unsloth/QwQ-32B", "unsloth/QwQ-32B-bnb-4bit",
                "unsloth/QwQ-32B-unsloth-bnb-4bit"}
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


def rows_from_payload(raw, expected_split):
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
        if not isinstance(row, dict) or not isinstance(row.get("text"), str) or not row["text"].strip():
            raise PilotError("payload_invalid_text_record")
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


def row_group(row):
    meta = row.get("metadata", {})
    for key in ("group_id", "duplicate_cluster_id", "document_id", "thread_id", "conversation_id", "source_id"):
        if meta.get(key) or row.get(key):
            return str(meta.get(key) or row[key])
    return sha_bytes(row["text"].encode("utf-8"))


def verify_partitions(training, validation):
    if not validation:
        return
    if {row_group(r) for r in training} & {row_group(r) for r in validation}:
        raise PilotError("training_validation_group_overlap")
    if {sha_bytes(r["text"].encode("utf-8")) for r in training} & {
            sha_bytes(r["text"].encode("utf-8")) for r in validation}:
        raise PilotError("training_validation_content_overlap")


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


def fetch_training_script(env, destination, opener=None):
    commit = env.get("REPO_SHA", env.get("GITHUB_SHA", ""))
    digest = env.get("HASLA_TRAIN_SCRIPT_SHA256", "").lower()
    if not re.fullmatch(r"[a-f0-9]{40}", commit) or not SHA_PATTERN.fullmatch(digest):
        raise PilotError("missing_or_invalid_pinned_training_code")
    request = urllib.request.Request(f"{CODE_ROOT}/{commit}/tools/ai/train_lora.py")
    try:
        with (opener or urllib.request.urlopen)(request, timeout=45) as response:
            raw = response.read(MAX_SCRIPT_BYTES + 1)
    except Exception:
        raise PilotError("training_code_download_failed") from None
    if len(raw) > MAX_SCRIPT_BYTES or sha_bytes(raw) != digest:
        raise PilotError("training_code_hash_mismatch")
    Path(destination).write_bytes(raw)
    return digest


def training_command(script, data, adapter, validation=None):
    command = [sys.executable, str(script), "--base", "solver", "--format", "text",
               "--max-steps", "32", "--epochs", "1", "--lr", "1e-5", "--max-len", "1024",
               "--holdout", "0", str(data), str(adapter)]
    if validation is not None:
        command.extend(["--validation-data", str(validation)])
    return command


def training_environment(env):
    # Only the local JSONL file is needed by the trainer; do not forward corpus shards.
    child = {key: value for key, value in env.items()
             if not key.startswith(("HASLA_DATA_", "HASLA_VALIDATION_"))
             and key not in ("WANDB_API_KEY", "RUNPOD_API_KEY")}
    child.update({"WANDB_MODE": "disabled", "WANDB_DISABLED": "true", "WANDB_CONSOLE": "off",
                  "WANDB_DISABLE_CODE": "true", "WANDB_SILENT": "true", "HF_HUB_DISABLE_TELEMETRY": "1",
                  "TOKENIZERS_PARALLELISM": "false"})
    return child


def adapter_inventory(adapter):
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
    config = json.loads((adapter / "adapter_config.json").read_text(encoding="utf-8"))
    # Validate rather than silently relabeling an adapter trained against another base.
    if config.get("base_model_name_or_path") not in BASE_ALIASES:
        raise PilotError("adapter_base_model_mismatch")
    if config.get("peft_type") != "LORA":
        raise PilotError("adapter_type_mismatch")
    return files, sha_bytes(json.dumps(files, sort_keys=True, separators=(",", ":")).encode())


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
    run, stage = None, "configuration"
    result_path = workspace / "result.json"
    try:
        required_name(env, "RUN")
        required_name(env, "ARTIFACT")
        if not env.get("HF_TOKEN"):
            raise PilotError("missing_huggingface_credential")
        if not workspace.is_dir():
            raise PilotError("workspace_not_found")
        stage = "payload_validation"
        data = decode_payload(env)
        validation_prefix = "HASLA_DATA_VALIDATION" if any(
            key.startswith("HASLA_DATA_VALIDATION_") for key in env) else "HASLA_VALIDATION"
        validation_data = decode_payload(env, validation_prefix, optional=True)
        training = rows_from_payload(data, "train")
        validation = rows_from_payload(validation_data, "validation") if validation_data is not None else []
        verify_partitions(training, validation)
        stage = "privacy_verification"
        private = assert_private_project(env, opener)
        stage = "training_code_verification"
        script = workspace / "train_lora.py"
        script_sha = fetch_training_script(env, script, opener)
        data_path, validation_path, adapter = workspace / "data.jsonl", None, workspace / "adapter"
        if adapter.exists():
            raise PilotError("adapter_output_already_exists")
        data_path.write_bytes(data)
        if validation_data is not None:
            validation_path = workspace / "validation.jsonl"
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
        safe_config = {"base_model": BASE_MODEL, "format": "text", "max_steps": 32,
                       "epochs": 1, "learning_rate": 1e-5, "max_length": 1024,
                       "training_records": len(training), "validation_records": len(validation),
                       "training_sha256": sha_bytes(data),
                       "validation_sha256": sha_bytes(validation_data) if validation_data is not None else None,
                       "training_code_sha256": script_sha, "repo_sha": env.get("REPO_SHA", env.get("GITHUB_SHA")),
                       "test_records_used": 0, "private": True, "deploy": False, "promote": False}
        run = wandb_module.init(entity=private["entity"], project=private["project"],
                                id=env["RUN"], name=env["RUN"], resume="never",
                                job_type="private-textbook-pilot", config=safe_config,
                                settings=settings, dir=str(workspace))
        stage = "training"
        run.summary["status"] = stage
        timeout = int(env.get("HASLA_TRAIN_TIMEOUT_SECONDS", "3600"))
        if not 60 <= timeout <= 5400:
            raise PilotError("invalid_training_timeout")
        completed = (runner or subprocess.run)(training_command(script, data_path, adapter, validation_path),
            cwd=str(workspace), env=training_environment(env), stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=timeout, check=False)
        if completed.returncode:
            raise PilotError("trainer_process_failed")

        stage = "adapter_validation"
        run.summary["status"] = stage
        files, adapter_sha = adapter_inventory(adapter)
        # Check again immediately before uploading an adapter; never change project visibility here.
        assert_private_project(env, opener)
        stage = "uploading_adapter"
        run.summary["status"] = stage
        artifact = wandb_module.Artifact(env["ARTIFACT"], type="lora", metadata={
            "base_model": BASE_MODEL, "training_records": len(training), "validation_records": len(validation),
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


def main():
    # SDK/third-party output is suppressed too, including any unexpected exception text.
    with open(os.devnull, "w") as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        result = run_pilot()
    print(json.dumps({"status": result["status"], "artifact": result.get("artifact"),
                      "error_code": result.get("error_code"), "stage": result.get("stage")}), flush=True)
    return 0 if result["status"] == "uploaded" else 1


if __name__ == "__main__":
    raise SystemExit(main())

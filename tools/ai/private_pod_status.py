"""Print one allowlisted status event for one private-training Actions run.

This command uses only RunPod GET requests. It deliberately discards upstream
diagnostic output, which can contain environment variables or network details.
"""
import contextlib
import json
import math
import os
import re
import signal
import sys
import threading
import time

import private_corpus_run as cloud


class StatusError(ValueError):
    """An error code that is safe to print without upstream exception text."""


class _StreamDeadline(TimeoutError):
    pass


class _Discard:
    def write(self, value):
        return len(value)

    def flush(self):
        pass


def validate_run_id(run_id):
    if not isinstance(run_id, str) or re.fullmatch(r"[0-9]{1,30}", run_id) is None:
        raise StatusError("invalid_run_id")
    return run_id


def _number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value) is None:
            return None
        try:
            value = float(value)
        except (ValueError, OverflowError):
            return None
    if not isinstance(value, (int, float)):
        return None
    try:
        return value if math.isfinite(value) and value >= 0 else None
    except (ValueError, OverflowError):
        return None


def _runtime(value):
    if not isinstance(value, dict):
        return None
    result = {}
    uptime = _number(value.get("uptime", value.get("uptimeInSeconds")))
    if uptime is not None:
        result["uptimeInSeconds"] = uptime
    utilization, memory_utilization = [], []
    for gpu in value.get("gpus", []) if isinstance(value.get("gpus"), list) else []:
        if not isinstance(gpu, dict):
            continue
        number = _number(gpu.get("util", gpu.get("gpuUtilPercent")))
        if number is not None and number <= 100:
            utilization.append(number)
        memory = _number(gpu.get("memoryUtil", gpu.get("memoryUtilPercent")))
        if memory is not None and memory <= 100:
            memory_utilization.append(memory)
    if utilization:
        result["gpuUtilPercent"] = utilization
    if memory_utilization:
        result["memoryUtilPercent"] = memory_utilization
    return result or None


_STAGES = frozenset({
    "configuration", "payload_validation", "privacy_verification", "input_artifact_verification",
    "training_code_verification", "role_config_verification", "run_initialization", "training",
    "adapter_validation", "uploading_adapter", "uploaded", "failed",
})
_RUN_STATES = frozenset({"running", "finished", "failed", "crashed", "killed", "pending", "preempted", "queued"})
_ERROR_CODES = frozenset({
    "missing_or_invalid_run_identity", "missing_payload_shards", "noncontiguous_payload_shards",
    "payload_part_count_mismatch", "missing_or_invalid_payload_hash", "invalid_payload_encoding",
    "compressed_payload_limit", "invalid_payload_gzip", "uncompressed_payload_limit", "payload_hash_mismatch",
    "unsupported_payload_format", "payload_not_utf8", "payload_invalid_jsonl", "payload_invalid_record",
    "payload_invalid_text_record", "payload_invalid_chat_record", "payload_invalid_metadata",
    "test_or_wrong_split_in_payload", "payload_has_no_records", "training_validation_group_overlap",
    "training_validation_content_overlap", "missing_or_invalid_training_role_format", "role_format_mismatch",
    "payload_training_role_mismatch", "solver_chat_requires_verified_solution",
    "missing_or_invalid_wandb_configuration", "wandb_privacy_check_failed", "wandb_project_not_verified",
    "wandb_project_not_private", "input_artifact_outside_private_project", "input_artifact_requires_exact_version",
    "input_artifact_directory_already_exists", "input_artifact_identity_mismatch", "input_artifact_links_not_allowed",
    "input_artifact_unexpected_files", "input_artifact_external_reference", "input_artifact_file_size_limit",
    "input_artifact_unsafe_download_path", "input_artifact_unsafe_file", "missing_or_invalid_pinned_training_code",
    "training_code_download_failed", "training_code_hash_mismatch", "invalid_pinned_role_configuration",
    "training_role_precision_mismatch", "validated_role_configuration_required", "invalid_validated_training_row_count",
    "expected_adapter_file_missing", "invalid_adapter_size", "adapter_base_model_mismatch", "adapter_type_mismatch",
    "adapter_rank_mismatch", "verified_training_report_missing", "training_report_role_or_input_mismatch",
    "training_report_has_no_bounded_weight_update", "training_report_invalid_loss", "missing_huggingface_credential",
    "workspace_not_found", "adapter_output_already_exists", "invalid_training_timeout", "trainer_process_failed",
    "artifact_exact_version_missing", "invalid_role_workspace",
    "RuntimeError", "ValueError", "TypeError", "KeyError", "IndexError", "AttributeError", "AssertionError",
    "OSError", "IOError", "FileNotFoundError", "PermissionError", "IsADirectoryError", "NotADirectoryError",
    "TimeoutError", "TimeoutExpired", "ConnectionError", "HTTPError", "URLError", "RequestException",
    "ReadTimeout", "ConnectTimeout", "SSLError", "ImportError", "ModuleNotFoundError", "MemoryError",
    "OverflowError", "UnicodeDecodeError", "JSONDecodeError", "CalledProcessError", "CommError", "UsageError",
})


def _decode_mapping(value):
    for _ in range(3):
        if isinstance(value, dict):
            return value
        if not isinstance(value, str) or len(value) > 1048576:
            return None
        try:
            value = json.loads(value)
        except (ValueError, UnicodeError):
            return None
    return value if isinstance(value, dict) else None


def _value_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, (int, float)):
        return "number"
    return "other"


def _summary_shape(summary):
    shape = {}
    for key in ("status", "stage", "error_code", "private_training_result", "private_training_result_json"):
        if key in summary:
            shape[key] = _value_type(summary[key])
    for root in ("private_training_result", "private_training_result_json"):
        nested = _decode_mapping(summary.get(root))
        for leaf in ("status", "stage", "error_code"):
            if nested is not None and leaf in nested:
                shape[root + "." + leaf] = _value_type(nested[leaf])
            for separator in (".", "/"):
                key = root + separator + leaf
                if key in summary:
                    shape[key] = _value_type(summary[key])
    return shape


def _safe_training_result(value, entity, run_name, role):
    value = _decode_mapping(value)
    if value is None or value.get("role", role) != role:
        return None
    result = {}
    for key, allowed in (("status", _STAGES), ("stage", _STAGES), ("error_code", _ERROR_CODES)):
        entry = value.get(key)
        if isinstance(entry, str) and entry in allowed:
            result[key] = entry
    steps = value.get("steps_completed")
    if type(steps) is int and 0 <= steps <= 100000:
        result["steps_completed"] = steps
    updated = value.get("weights_updated")
    if type(updated) is bool and (updated is False or result.get("steps_completed", 0) > 0):
        result["weights_updated"] = updated
    artifact = value.get("artifact")
    expected = entity + "/" + cloud.PROJECT + "/" + run_name + "-lora:"
    if isinstance(artifact, str) and re.fullmatch(re.escape(expected) + r"v[0-9]{1,10}", artifact):
        result["artifact"] = artifact
    for name in ("train_loss", "eval_loss"):
        loss = value.get(name)
        if type(loss) in (int, float) and _number(loss) is not None and loss <= 1000000:
            result[name] = loss
    return result or None


def _training_row(row, entity, run_name, role):
    if row is None:
        return {"role": role, "state": "not_started_or_not_initialized"}
    if not isinstance(row, dict):
        raise StatusError("invalid_training_status")
    state = row.get("state")
    state = state.lower() if isinstance(state, str) else "unknown"
    raw_summary = row.get("summaryMetrics")
    summary = {} if raw_summary is None else _decode_mapping(raw_summary)
    if summary is None:
        raise StatusError("invalid_training_status")
    stage = summary.get("status")
    result = {"role": role, "state": state if state in _RUN_STATES else "unknown",
              "status": stage if isinstance(stage, str) and stage in _STAGES else "unreported"}
    shape = _summary_shape(summary)
    if shape:
        result["summary_key_shape"] = shape
    candidates = [summary.get("private_training_result"), summary.get("private_training_result_json")]
    for root in ("private_training_result", "private_training_result_json"):
        for separator in (".", "/"):
            candidates.append({key: summary[root + separator + key] for key in ("status", "stage", "error_code")
                               if root + separator + key in summary})
    candidates.append({key: summary[key] for key in ("stage", "error_code") if key in summary})
    training = {}
    for candidate in candidates:
        safe = _safe_training_result(candidate, entity, run_name, role)
        for key, value in (safe or {}).items():
            training.setdefault(key, value)
    if training:
        result["private_training_result"] = training
    return result


def collect_training_status(run_id, *, query=None):
    """Read existing W&B runs only; never initialize runs or change privacy."""
    validate_run_id(run_id)
    query = cloud.wandb_query if query is None else query
    unavailable = [{"role": role, "state": "monitoring_unavailable"} for role in ("chat", "solver")]
    with contextlib.redirect_stdout(_Discard()), contextlib.redirect_stderr(_Discard()):
        try:
            viewer = query("{viewer{entity}}")
            entity = viewer.get("viewer", {}).get("entity")
            if not isinstance(entity, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", entity) is None:
                return unavailable
            runs = {role: cloud.PREFIX + run_id + "-" + role for role in ("chat", "solver")}
            data = query(
                "query($e:String!,$p:String!,$chat:String!,$solver:String!){"
                "project(name:$p,entityName:$e){access "
                "chat:run(name:$chat){state summaryMetrics} solver:run(name:$solver){state summaryMetrics}}}",
                {"e": entity, "p": cloud.PROJECT, **runs})
            project = data.get("project")
            if not isinstance(project, dict) or project.get("access") != "PRIVATE":
                return unavailable
            if any(role not in project for role in runs):
                return unavailable
            results = []
            for role, run_name in runs.items():
                try:
                    results.append(_training_row(project[role], entity, run_name, role))
                except Exception:
                    results.append({"role": role, "state": "monitoring_unavailable"})
            return results
        except Exception:
            return unavailable


def _system_stage(value, secrets):
    """Classify transient system text; never return any text from the provider."""
    if not isinstance(value, str):
        return None
    line = value[:8192]
    for secret in sorted((str(item) for item in secrets if item), key=len, reverse=True):
        line = line.replace(secret, "[redacted]")
    line = re.sub(r"(?i)(?:hf_|rpa_|rp_|wandb_)[A-Za-z0-9_-]{8,}", "[redacted]", line)
    line = re.sub(r"(?i)https?://\S+", "[url]", line)
    line = re.sub(r"(?<!\w)(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?(?!\w)", "[ip]", line)
    line = re.sub(r"\[[0-9a-fA-F:]+\](?::\d+)?|\b(?:[0-9a-fA-F]{0,4}:){2,}[0-9a-fA-F]{0,4}\b", "[ip]", line)
    lowered = line.lower()
    if any(term in lowered for term in ("failed to pull", "error pulling", "pull access denied", "manifest unknown", "image pull failed")):
        code = "image_pull_failed"
    elif any(term in lowered for term in ("failed to create", "failed to start", "runtime error", "runtimeerror", "oci runtime", "out of memory")):
        code = "runtime_error"
    elif "container exited" in lowered:
        code = "container_exited"
    elif "container started" in lowered:
        code = "container_started"
    elif any(term in lowered for term in ("starting container", "start container")):
        code = "container_starting"
    elif any(term in lowered for term in ("extracting", "unpacking", "decompressing")):
        code = "extracting_image"
    elif any(term in lowered for term in ("pull complete", "download complete", "image is up to date", "downloaded newer image")):
        code = "image_ready"
    elif any(term in lowered for term in ("pulling", "downloading", "pull image")):
        code = "pulling_image"
    else:
        return None
    result = {"code": code}
    percent = re.search(r"(?<![\d.])([0-9]{1,3}(?:\.[0-9]{1,2})?)\s*%", line)
    if percent and float(percent.group(1)) <= 100:
        result["progress_percent"] = float(percent.group(1))
    return result


def collect_system_status(pod, env, *, get=None, clock=None, deadline=None):
    """Bounded SSE observation of a previously identity-checked pod's system log."""
    get = cloud.requests.get if get is None else get
    clock = time.monotonic if clock is None else clock
    deadline = clock() + 8 if deadline is None else deadline
    secrets = list((pod.get("env") or {}).values()) if isinstance(pod.get("env"), dict) else []
    secrets.extend(value for key, value in env.items() if re.search(r"KEY|TOKEN|SECRET|PASSWORD", key, re.I))
    response, stages, total, events, buffered, data = None, [], 0, 0, b"", []
    alarm_handler = None
    stop = "stream_ended"
    with contextlib.redirect_stdout(_Discard()), contextlib.redirect_stderr(_Discard()):
        try:
            remaining = deadline - clock()
            if remaining <= 0:
                return {"state": "bounded", "stop": "deadline", "events_read": 0, "stages": []}
            # The dedicated Linux CI command can interrupt a blocked socket at
            # the overall deadline, rather than waiting for another read timeout.
            # Other platforms retain the monotonic checks and bounded sockets.
            if (hasattr(signal, "setitimer") and threading.current_thread() is threading.main_thread()
                    and signal.getitimer(signal.ITIMER_REAL)[0] == 0):
                def expired(signum, frame):
                    raise _StreamDeadline()
                alarm_handler = signal.getsignal(signal.SIGALRM)
                signal.signal(signal.SIGALRM, expired)
                signal.setitimer(signal.ITIMER_REAL, remaining)
            response = get(cloud.REST + "/pods/" + pod["id"] + "/logs", params={"source": "system", "tail": 40},
                           headers={"Authorization": "Bearer " + env["RUNPOD_API_KEY"], "Accept": "text/event-stream"},
                           stream=True, timeout=(min(5, remaining), min(5, remaining)), allow_redirects=False)
            if response.status_code != 200:
                return {"state": "monitoring_unavailable", "stages": []}
            # One-byte reads expose short SSE events immediately and avoid buffering
            # indefinitely while a live stream waits to fill a large read chunk.
            for chunk in response.iter_content(chunk_size=1):
                if clock() >= deadline:
                    stop = "deadline"
                    break
                if not isinstance(chunk, bytes):
                    continue
                total += len(chunk)
                if total > 32768:
                    stop = "byte_limit"
                    break
                buffered += chunk
                while b"\n" in buffered:
                    line, buffered = buffered.split(b"\n", 1)
                    line = line.rstrip(b"\r")
                    if line.startswith(b"data:"):
                        data.append(line[5:].lstrip())
                    elif not line and data:
                        events += 1
                        try:
                            event = json.loads(b"\n".join(data))
                            if isinstance(event, dict) and event.get("source") == "system":
                                stage = _system_stage(event.get("line"), secrets)
                                if stage and stage not in stages:
                                    stages.append(stage)
                        except (ValueError, UnicodeError):
                            pass
                        data = []
                        if events >= 40:
                            stop = "event_limit"
                            break
                if stop == "event_limit":
                    break
        except _StreamDeadline:
            stop = "deadline"
        except Exception:
            stop = "read_timeout_or_error"
        finally:
            if alarm_handler is not None:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, alarm_handler)
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
    return {"state": "observed" if stages else "no_known_system_stage", "stop": stop,
            "events_read": events, "stages": stages}


def _safe_pod(pod, pod_id, expected_name):
    if not isinstance(pod, dict) or pod.get("id") != pod_id or pod.get("name") != expected_name:
        raise StatusError("pod_identity_mismatch")
    gpu = pod.get("gpu") if isinstance(pod.get("gpu"), dict) else {}
    count = gpu.get("count")
    safe_gpu = {
        "id": gpu.get("id") if gpu.get("id") in cloud.GPU_IDS else None,
        "count": count if type(count) is int and 0 < count <= 128 else None,
    }
    state = pod.get("status", pod.get("desiredStatus"))
    if state not in {"PROVISIONING", "STARTING", "RUNNING", "EXITED", "ERROR", "TERMINATED", "CREATED", "STOPPED"}:
        state = "UNKNOWN"
    result = {
        "id": pod_id,
        "name": expected_name,
        "gpu": safe_gpu,
        "status": state,
        "costPerHr": _number(pod.get("costPerHr", pod.get("cost"))),
        "containerDiskInGb": _number(pod.get("containerDiskInGb", pod.get("disk"))),
        "volumeInGb": _number(pod.get("volumeInGb")),
    }
    runtime = _runtime(pod.get("runtime"))
    if runtime:
        result["runtime"] = runtime
    return result


def collect_status(run_id, *, api=None, env=None, wandb_query=None, system_logs=False, log_get=None, clock=None):
    """Resolve exact-name matches and fetch their details, without mutations."""
    run_id = validate_run_id(run_id)
    env = os.environ if env is None else env
    if not isinstance(env.get("RUNPOD_API_KEY"), str) or not env["RUNPOD_API_KEY"].strip():
        raise StatusError("missing_runpod_api_key")
    api = cloud.runpod if api is None else api
    name = cloud.PREFIX + run_id
    # cloud.runpod emits provider diagnostics on failure; none are safe here.
    with contextlib.redirect_stdout(_Discard()), contextlib.redirect_stderr(_Discard()):
        rows = api("GET", "/pods")
        if not isinstance(rows, list):
            raise StatusError("invalid_pod_list")
        pod_ids = []
        for row in rows:
            if not isinstance(row, dict) or row.get("name") != name:
                continue
            pod_id = row.get("id")
            if not isinstance(pod_id, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", pod_id) is None:
                raise StatusError("invalid_pod_id")
            if pod_id not in pod_ids:
                pod_ids.append(pod_id)
        pods, raw_pods = [], []
        for pod_id in pod_ids:
            raw = api("GET", "/pods/" + pod_id)
            pods.append(_safe_pod(raw, pod_id, name))
            raw_pods.append(raw)
        if system_logs:
            now = time.monotonic if clock is None else clock
            deadline = now() + 8
            for safe, raw in zip(pods, raw_pods):
                safe["system"] = collect_system_status(raw, env, get=log_get, clock=now, deadline=deadline)
    result = {"event": "pod_status", "run_id": run_id, "state": "present" if pods else "absent", "pods": pods}
    if isinstance(env.get("WANDB_API_KEY"), str) and env["WANDB_API_KEY"].strip():
        result["training"] = collect_training_status(run_id, query=wandb_query)
    return result


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    run_id = None
    try:
        if len(args) not in (2, 3) or args[0] != "--run-id" or (len(args) == 3 and args[2] != "--system-logs"):
            raise StatusError("invalid_arguments")
        run_id = validate_run_id(args[1])
        event = collect_status(run_id, system_logs=len(args) == 3)
        code = 0
    except StatusError as error:
        event = {"event": "pod_status", "state": "error", "error": str(error)}
        code = 2
    except Exception:
        event = {"event": "pod_status", "state": "error", "error": "provider_request_failed"}
        code = 1
    if run_id is not None:
        event["run_id"] = run_id
    print(json.dumps(event, ensure_ascii=True, allow_nan=False), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

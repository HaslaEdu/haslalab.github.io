"""Print one allowlisted status event for one private-training Actions run.

This command uses only RunPod GET requests. It deliberately discards upstream
diagnostic output, which can contain environment variables or network details.
"""
import contextlib
import json
import math
import os
import re
import sys

import private_corpus_run as cloud


class StatusError(ValueError):
    """An error code that is safe to print without upstream exception text."""


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


def _safe_training_result(value, entity, run_name, role):
    if not isinstance(value, dict) or value.get("role", role) != role:
        return None
    result = {}
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
    summary = row.get("summaryMetrics")
    if isinstance(summary, str):
        if len(summary) > 1048576:
            raise StatusError("invalid_training_status")
        summary = json.loads(summary)
    if summary is None:
        summary = {}
    if not isinstance(summary, dict):
        raise StatusError("invalid_training_status")
    stage = summary.get("status")
    result = {"role": role, "state": state if state in _RUN_STATES else "unknown",
              "status": stage if isinstance(stage, str) and stage in _STAGES else "unreported"}
    training = _safe_training_result(summary.get("private_training_result"), entity, run_name, role)
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


def collect_status(run_id, *, api=None, env=None, wandb_query=None):
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
        pods = [_safe_pod(api("GET", "/pods/" + pod_id), pod_id, name) for pod_id in pod_ids]
    result = {"event": "pod_status", "run_id": run_id, "state": "present" if pods else "absent", "pods": pods}
    if isinstance(env.get("WANDB_API_KEY"), str) and env["WANDB_API_KEY"].strip():
        result["training"] = collect_training_status(run_id, query=wandb_query)
    return result


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    run_id = None
    try:
        if len(args) != 2 or args[0] != "--run-id":
            raise StatusError("invalid_arguments")
        run_id = validate_run_id(args[1])
        event = collect_status(run_id)
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

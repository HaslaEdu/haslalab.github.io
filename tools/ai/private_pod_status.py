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
    uptime = _number(value.get("uptimeInSeconds"))
    if uptime is not None:
        result["uptimeInSeconds"] = uptime
    utilization = []
    for gpu in value.get("gpus", []) if isinstance(value.get("gpus"), list) else []:
        if not isinstance(gpu, dict):
            continue
        number = _number(gpu.get("gpuUtilPercent"))
        if number is not None and number <= 100:
            utilization.append(number)
    if utilization:
        result["gpuUtilPercent"] = utilization
    return result or None


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


def collect_status(run_id, *, api=None, env=None):
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
    return {"event": "pod_status", "run_id": run_id, "state": "present" if pods else "absent", "pods": pods}


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

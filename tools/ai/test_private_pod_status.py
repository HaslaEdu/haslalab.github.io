"""Offline checks: status observations must never mutate RunPod resources."""
import contextlib
import io
import json
import os
import unittest
from unittest.mock import patch

import private_pod_status as status


class PrivatePodStatusTests(unittest.TestCase):
    def setUp(self):
        self.env = {"RUNPOD_API_KEY": "fixture-runpod-secret"}
        self.name = status.cloud.PREFIX + "41810732513"
        self.addCleanup(patch.stopall)
        for method in ("request", "get", "post", "patch", "delete"):
            patch.object(status.cloud.requests, method, side_effect=AssertionError("external I/O forbidden")).start()

    def pod(self, **fields):
        return {"id": "fixture-pod", "name": self.name, "gpu": {"id": status.cloud.GPU_IDS[0], "count": 1},
                "status": "RUNNING", "costPerHr": 1.79, "containerDiskInGb": 200, "volumeInGb": 0, **fields}

    def test_exact_match_and_only_gets_and_safe_fields(self):
        calls = []
        pod = self.pod(env=self.env, ssh={"host": "PRIVATE_ADDRESS"}, ip="PRIVATE_ADDRESS",
                       logs="PRIVATE_LOG", runtime={"uptimeInSeconds": 60, "gpus": [{"gpuUtilPercent": 7}], "address": "PRIVATE_ADDRESS"})
        def api(method, path):
            self.assertEqual(method, "GET")
            calls.append((method, path))
            if path == "/pods":
                return [pod, pod, self.pod(id="other", name=self.name + "-chat"), self.pod(id="unrelated", name="other")]
            self.assertEqual(path, "/pods/fixture-pod")
            return pod
        event = status.collect_status("41810732513", api=api, env=self.env)
        self.assertEqual(calls, [("GET", "/pods"), ("GET", "/pods/fixture-pod")])
        self.assertEqual(event["state"], "present")
        self.assertEqual(event["pods"][0]["runtime"], {"uptimeInSeconds": 60, "gpuUtilPercent": [7]})
        encoded = json.dumps(event)
        for secret in [*self.env.values(), "PRIVATE_ADDRESS", "PRIVATE_LOG", '"ssh"', '"env"']:
            self.assertNotIn(secret, encoded)

    def test_absence_does_not_claim_cleanup(self):
        event = status.collect_status("41810732513", api=lambda method, path: [], env=self.env)
        self.assertEqual(event["state"], "absent")
        self.assertEqual(event["pods"], [])
        self.assertNotIn("clean", json.dumps(event))

    def test_bad_run_ids_and_missing_key_fail_before_io(self):
        def forbidden(*args):
            self.fail("invalid input reached provider")
        for run_id in ["", "123/other", "123?all", "123\n", "１２３", "1 2", 123, None]:
            with self.subTest(run_id=run_id), self.assertRaisesRegex(status.StatusError, "invalid_run_id"):
                status.collect_status(run_id, api=forbidden, env=self.env)
        with self.assertRaisesRegex(status.StatusError, "missing_runpod_api_key"):
            status.collect_status("123", api=forbidden, env={})

    def test_upstream_failure_prints_only_generic_one_line_event(self):
        def unsafe(*args):
            print("PRIVATE_UPSTREAM_BODY", self.env)
            print("PRIVATE_STDERR", file=status.sys.stderr)
            raise RuntimeError("PRIVATE_EXCEPTION " + self.env["RUNPOD_API_KEY"])
        output, errors = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, self.env, clear=True), patch.object(status.cloud, "runpod", side_effect=unsafe), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = status.main(["--run-id", "41810732513"])
        self.assertEqual(code, 1)
        self.assertEqual(errors.getvalue(), "")
        self.assertEqual(len(output.getvalue().splitlines()), 1)
        self.assertEqual(json.loads(output.getvalue()), {"event": "pod_status", "state": "error", "error": "provider_request_failed", "run_id": "41810732513"})

    def test_details_cannot_escape_exact_scope_or_inject_id_path(self):
        for bad in [self.pod(id="../other"), self.pod(id="a?all=true")]:
            with self.assertRaisesRegex(status.StatusError, "invalid_pod_id"):
                status.collect_status("41810732513", api=lambda method, path: [bad], env=self.env)
        calls = []
        def mismatch(method, path):
            calls.append((method, path))
            return [self.pod()] if path == "/pods" else self.pod(name="other")
        with self.assertRaisesRegex(status.StatusError, "pod_identity_mismatch"):
            status.collect_status("41810732513", api=mismatch, env=self.env)
        self.assertTrue(all(method == "GET" for method, _ in calls))

    def test_untrusted_fields_and_nonfinite_metrics_cannot_leak(self):
        pod = self.pod(gpu={"id": "PRIVATE_GPU_STRING", "count": True}, status="PRIVATE_STATUS", costPerHr=float("nan"),
                       containerDiskInGb=-1, runtime={"uptimeInSeconds": float("inf"), "gpus": [{"gpuUtilPercent": 101}, {"gpuUtilPercent": "PRIVATE_UTIL"}]})
        event = status.collect_status("41810732513", api=lambda method, path: [pod] if path == "/pods" else pod, env=self.env)
        encoded = json.dumps(event, allow_nan=False)
        self.assertNotIn("PRIVATE_", encoded)
        self.assertEqual(event["pods"][0]["status"], "UNKNOWN")
        self.assertIsNone(event["pods"][0]["costPerHr"])
        self.assertNotIn("runtime", event["pods"][0])

    def test_cli_invalid_id_has_no_provider_io(self):
        output = io.StringIO()
        with patch.object(status.cloud, "runpod", side_effect=AssertionError("I/O forbidden")) as api, contextlib.redirect_stdout(output):
            code = status.main(["--run-id", "PRIVATE_BAD_ID"])
        self.assertEqual(code, 2)
        api.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["error"], "invalid_run_id")
        self.assertNotIn("PRIVATE_BAD_ID", output.getvalue())

    def test_v2_runtime_metrics_normalize_without_network_fields(self):
        pod = self.pod(runtime={"uptime": 123, "gpus": [{"util": 18.5, "memoryUtil": 72, "address": "PRIVATE_IP"}], "ssh": "PRIVATE_SSH"})
        event = status.collect_status("41810732513", api=lambda method, path: [pod] if path == "/pods" else pod, env=self.env)
        self.assertEqual(event["pods"][0]["runtime"], {"uptimeInSeconds": 123, "gpuUtilPercent": [18.5], "memoryUtilPercent": [72]})
        self.assertNotIn("PRIVATE_", json.dumps(event))

    def test_optional_training_query_is_read_only_private_and_allowlisted(self):
        calls = []
        run_name = self.name + "-chat"
        artifact = "fixture-entity/" + status.cloud.PROJECT + "/" + run_name + "-lora:v2"
        def query(document, variables=None):
            self.assertNotIn("mutation", document.lower())
            calls.append((document, variables))
            if variables is None:
                return {"viewer": {"entity": "fixture-entity"}}
            self.assertEqual(variables, {"e": "fixture-entity", "p": status.cloud.PROJECT, "chat": self.name + "-chat", "solver": self.name + "-solver"})
            summary = {"status": "uploaded", "PRIVATE_ARBITRARY": "PRIVATE_TEXT", "private_training_result": {
                "role": "chat", "steps_completed": 1, "weights_updated": True, "artifact": artifact,
                "train_loss": 1.4, "eval_loss": 1.6, "env": {"token": "PRIVATE_TOKEN"}, "trace": "PRIVATE_TRACE"}}
            return {"project": {"access": "PRIVATE", "chat": {"state": "finished", "summaryMetrics": json.dumps(summary)}, "solver": None}}
        with patch.object(status.cloud, "private_project", side_effect=AssertionError("W&B writes forbidden")):
            event = status.collect_status("41810732513", api=lambda method, path: [], env={**self.env, "WANDB_API_KEY": "PRIVATE_WANDB_KEY", "HF_TOKEN": "PRIVATE_UNUSED_HF"}, wandb_query=query)
        self.assertEqual(len(calls), 2)
        self.assertEqual(event["training"][0], {"role": "chat", "state": "finished", "status": "uploaded", "private_training_result": {
            "steps_completed": 1, "weights_updated": True, "artifact": artifact, "train_loss": 1.4, "eval_loss": 1.6}})
        self.assertEqual(event["training"][1]["state"], "not_started_or_not_initialized")
        self.assertNotIn("PRIVATE_", json.dumps(event))

    def test_training_no_key_does_not_query_and_failures_do_not_claim_absence(self):
        with patch.object(status.cloud, "wandb_query", side_effect=AssertionError("optional query forbidden")) as query:
            event = status.collect_status("41810732513", api=lambda method, path: [], env=self.env)
        self.assertNotIn("training", event)
        query.assert_not_called()
        output, errors = io.StringIO(), io.StringIO()
        def broken(document, variables=None):
            print("PRIVATE_DIAGNOSTIC")
            print("PRIVATE_ERROR", file=status.sys.stderr)
            raise RuntimeError("PRIVATE_CREDENTIAL")
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            training = status.collect_training_status("41810732513", query=broken)
        self.assertEqual(output.getvalue() + errors.getvalue(), "")
        self.assertTrue(all(row["state"] == "monitoring_unavailable" for row in training))

    def test_training_nonprivate_schema_and_bad_summary_are_unavailable(self):
        for project in [{"access": "PUBLIC", "chat": None, "solver": None}, {"access": "PRIVATE"}, None]:
            def query(document, variables=None):
                return {"viewer": {"entity": "fixture-entity"}} if variables is None else {"project": project}
            with self.subTest(project=project):
                rows = status.collect_training_status("41810732513", query=query)
                self.assertTrue(all(row["state"] == "monitoring_unavailable" for row in rows))
        def malformed(document, variables=None):
            return {"viewer": {"entity": "fixture-entity"}} if variables is None else {"project": {"access": "PRIVATE", "chat": {"state": "running", "summaryMetrics": "PRIVATE_INVALID_JSON"}, "solver": None}}
        rows = status.collect_training_status("41810732513", query=malformed)
        self.assertEqual(rows[0]["state"], "monitoring_unavailable")
        self.assertEqual(rows[1]["state"], "not_started_or_not_initialized")

    def test_training_rejects_arbitrary_result_strings_and_false_step_evidence(self):
        summary = {"status": "PRIVATE_STAGE", "private_training_result": {"steps_completed": True, "weights_updated": True,
                   "artifact": "PRIVATE_ARTIFACT", "train_loss": float("nan"), "eval_loss": "PRIVATE_LOSS"}}
        row = status._training_row({"state": "PRIVATE_STATE", "summaryMetrics": summary}, "fixture-entity", self.name + "-chat", "chat")
        self.assertEqual(row, {"role": "chat", "state": "unknown", "status": "unreported"})
        self.assertNotIn("PRIVATE_", json.dumps(row, allow_nan=False))


if __name__ == "__main__":
    unittest.main()

"""Offline parent-runner fixtures: no keys, external requests, GPUs or uploads."""
import base64
import contextlib
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import private_corpus_run as runner
from training_budget import BudgetError


PRIVATE_TEXT = "SYNTHETIC_PRIVATE_TEXT_MUST_NEVER_BE_LOGGED"
FAKE_KEY = "fixture-credential-not-a-real-secret"


def fixture_environment():
    manifest = {"format": "text", "budget_krw": 30000,
                "dataset_version": "synthetic-private-fixture-v1",
                "train_script_sha256": "1" * 64, "pod_script_sha256": "2" * 64}
    env = {"RUNPOD_API_KEY": FAKE_KEY, "WANDB_API_KEY": FAKE_KEY, "HF_TOKEN": FAKE_KEY,
           "GITHUB_SHA": "a" * 40, "GITHUB_RUN_ID": "12345", "HASLA_PREFLIGHT_ONLY": "true"}
    for label, prefix, group in (("train", "HASLA_DATA", "book-a"),
                                 ("validation", "HASLA_VALIDATION", "book-b")):
        rows = [{"text": PRIVATE_TEXT + label, "metadata": {"group_id": group, "split": label}}]
        raw = (json.dumps(rows[0]) + "\n").encode()
        encoded = base64.b64encode(gzip.compress(raw)).decode()
        env[prefix + "_00"] = encoded
        manifest[label] = {"parts": 1, "records": 1, "encoded_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
                           "raw_sha256": hashlib.sha256(raw).hexdigest()}
    env["HASLA_CORPUS_MANIFEST"] = json.dumps(manifest)
    return env, manifest


def response(status=200, data=None):
    return SimpleNamespace(status_code=status, ok=200 <= status < 300,
                           content=b"fixture", json=lambda: data)


class PrivateCorpusRunnerTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(self.temp.name)
        self.env, self.manifest = fixture_environment()
        patch.object(runner, "E", self.env).start()
        patch.object(runner.sys, "argv", ["private_corpus_run.py"]).start()
        # A forgotten mock must fail immediately instead of reaching the internet.
        for name in ("request", "post", "get", "delete", "head"):
            patch.object(runner.requests, name, side_effect=AssertionError("external I/O was not mocked")).start()
        self.now = 100.0
        patch.object(runner.time, "monotonic", side_effect=lambda: self.now).start()
        patch.object(runner.time, "sleep", side_effect=self.advance).start()

    def advance(self, seconds):
        self.now += seconds

    def save_manifest(self):
        self.env["HASLA_CORPUS_MANIFEST"] = json.dumps(self.manifest)

    def valid_pod(self, **kwargs):
        return {"id": "fixture-pod", "name": runner.PREFIX + "12345", "costPerHr": "2.5",
                "containerDiskInGb": 200, "volumeInGb": 0, "gpu": {"count": 1},
                "desiredStatus": "RUNNING", **kwargs}

    @contextlib.contextmanager
    def ready_main(self, *, create=None, existing=None, result=None):
        calls = []

        def pod_api(method, path, **kwargs):
            calls.append((method, path, kwargs))
            if (method, path) == ("GET", "/pods"):
                return existing or []
            if (method, path) == ("POST", "/pods"):
                return self.valid_pod() if create is None else create
            if method == "GET" and path == "/pods/fixture-pod":
                return self.valid_pod()
            raise AssertionError("unexpected mocked Runpod operation")

        patches = [patch.object(runner, "runpod", side_effect=pod_api),
                   patch.object(runner, "private_project", return_value="fixture-entity"),
                   patch.object(runner.requests, "head", return_value=response()),
                   patch.object(runner, "delete_and_confirm", return_value=True),
                   patch.object(runner, "result_for", return_value=result)]
        mocks = [p.start() for p in patches]
        try:
            yield SimpleNamespace(calls=calls, pod=mocks[0], privacy=mocks[1], head=mocks[2],
                                  delete=mocks[3], result=mocks[4])
        finally:
            for p in reversed(patches):
                p.stop()

    def test_preflight_checks_credentials_models_privacy_but_never_creates_gpu(self):
        output = io.StringIO()
        with self.ready_main() as mocks, contextlib.redirect_stdout(output):
            self.assertEqual(runner.main(), 0)
        self.assertEqual([(m, p) for m, p, _ in mocks.calls], [("GET", "/pods")])
        self.assertEqual(mocks.head.call_count, 2)
        mocks.privacy.assert_called_once()
        mocks.delete.assert_not_called()
        events = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertTrue(any(e.get("event") == "preflight" and e.get("production_promotion") is False for e in events))
        self.assertNotIn(PRIVATE_TEXT, output.getvalue())
        self.assertNotIn(FAKE_KEY, output.getvalue())
        self.assertFalse(Path("private-pilot-state.json").exists())

    def test_manifest_checksums_and_pinned_script_digests_are_checked_before_api(self):
        cases = [("train", "encoded_sha256", "0" * 64), ("train", "raw_sha256", "not-a-hash"),
                 (None, "train_script_sha256", "invalid"),
                 (None, "pod_script_sha256", '$(echo do-not-execute)')]
        for section, key, bad in cases:
            with self.subTest(section=section, key=key):
                self.env, self.manifest = fixture_environment()
                runner.E = self.env
                target = self.manifest[section] if section else self.manifest
                target[key] = bad
                self.save_manifest()
                with self.assertRaises((ValueError, RuntimeError)):
                    runner.data_environment()

    def test_boolean_shard_count_is_not_a_valid_integer_count(self):
        self.manifest["train"]["parts"] = True
        self.save_manifest()
        with self.assertRaises((ValueError, RuntimeError)):
            runner.data_environment()

    def test_missing_credentials_or_existing_named_pod_prevent_creation(self):
        del self.env["HF_TOKEN"]
        with self.ready_main() as mocks, self.assertRaisesRegex(ValueError, "credential"):
            runner.main()
        mocks.pod.assert_not_called()
        self.env["HF_TOKEN"] = FAKE_KEY
        with self.ready_main(existing=[self.valid_pod()]) as mocks, self.assertRaisesRegex(RuntimeError, "already"):
            runner.main()
        self.assertFalse(any(m == "POST" for m, _, _ in mocks.calls))
        mocks.privacy.assert_not_called()

    def test_private_project_refuses_public_missing_or_graphql_error(self):
        fake_run = SimpleNamespace(finish=Mock())
        fake_wandb = SimpleNamespace(init=Mock(return_value=fake_run), Settings=lambda **kw: kw)
        for project in ({"name": runner.PROJECT, "access": "PUBLIC"}, None, {"name": runner.PROJECT}):
            with self.subTest(project=project), patch.dict("sys.modules", {"wandb": fake_wandb}), \
                    patch.object(runner, "wandb_query", side_effect=[{"viewer": {"entity": "fixture-entity"}}, {"project": project}]), \
                    self.assertRaisesRegex(RuntimeError, "PRIVATE"):
                runner.private_project()
        output = io.StringIO()
        with patch.object(runner.requests, "post", return_value=response(data={"errors": [{"message": PRIVATE_TEXT}]})), \
                contextlib.redirect_stdout(output), \
                self.assertRaises(RuntimeError) as caught:
            runner.wandb_query("query Fixture {viewer{entity}}")
        self.assertNotIn(PRIVATE_TEXT, str(caught.exception))
        self.assertNotIn(PRIVATE_TEXT, output.getvalue())

    def test_private_project_verifies_explicit_access_field(self):
        fake_run = SimpleNamespace(finish=Mock())
        fake_wandb = SimpleNamespace(init=Mock(return_value=fake_run), Settings=lambda **kw: kw)
        with patch.dict("sys.modules", {"wandb": fake_wandb}), patch.object(runner, "wandb_query", side_effect=[
                {"viewer": {"entity": "fixture-entity"}}, {"project": {"name": runner.PROJECT, "access": "PRIVATE"}}]) as query:
            self.assertEqual(runner.private_project(), "fixture-entity")
        self.assertIn("access", query.call_args_list[-1].args[0])
        self.assertEqual(query.call_args_list[-1].args[1], {"e": "fixture-entity", "p": runner.PROJECT})

    def test_runpod_error_does_not_echo_upstream_environment_or_key(self):
        with patch.object(runner.requests, "request", return_value=response(500, {"error": PRIVATE_TEXT})), \
                self.assertRaises(RuntimeError) as caught:
            runner.runpod("POST", "/pods", json={"env": {"private": PRIVATE_TEXT}})
        self.assertNotIn(PRIVATE_TEXT, str(caught.exception))
        self.assertNotIn(FAKE_KEY, str(caught.exception))

    def test_over_ceiling_creation_response_is_deleted_before_polling(self):
        self.env["HASLA_PREFLIGHT_ONLY"] = "false"
        with self.ready_main(create=self.valid_pod(costPerHr="3.01")) as mocks, contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaises(BudgetError):
            runner.main()
        mocks.delete.assert_called_once_with("fixture-pod")
        mocks.result.assert_not_called()
        self.assertEqual(sum(m == "POST" for m, _, _ in mocks.calls), 1)

    def test_completed_adapter_always_deletes_and_never_promotes_or_copies_dataset_to_result(self):
        self.env["HASLA_PREFLIGHT_ONLY"] = "false"
        result = {"status": "uploaded", "artifact": "fixture-entity/private-project/fixture-lora:v0",
                  "training_records": 1, "validation_records": 1, "weights_updated": True,
                  "production_promotion": False}
        output = io.StringIO()
        with self.ready_main(result=result) as mocks, contextlib.redirect_stdout(output):
            self.assertEqual(runner.main(), 0)
        mocks.delete.assert_called_once_with("fixture-pod")
        self.assertEqual(sum(m == "POST" for m, _, _ in mocks.calls), 1)
        payload = next(kw["json"] for m, _, kw in mocks.calls if m == "POST")
        self.assertEqual(payload["gpuCount"], 1)
        self.assertEqual(payload["volumeInGb"], 0)
        self.assertIn("timeout", payload["dockerStartCmd"][-1])
        self.assertNotIn("RUNPOD_API_KEY", payload["env"])
        self.assertEqual(payload["env"]["HASLA_MAX_STEPS"], "32")
        self.assertNotIn("CLOUDFLARE_API_TOKEN", payload["env"])
        self.assertNotIn(PRIVATE_TEXT, output.getvalue())
        self.assertNotIn(FAKE_KEY, output.getvalue())
        self.assertNotIn(PRIVATE_TEXT, Path("private-pilot-result.json").read_text())
        self.assertFalse(any("promote" in p or "ai-train" in p for _, p, _ in mocks.calls))

    def test_unfinished_training_and_failed_cleanup_never_return_success(self):
        self.env["HASLA_PREFLIGHT_ONLY"] = "false"
        with self.ready_main() as mocks, contextlib.redirect_stdout(io.StringIO()):
            def no_result(*args, **kwargs):
                self.now += 4000
                return None
            mocks.result.side_effect = no_result
            with self.assertRaisesRegex(RuntimeError, "deadline"):
                runner.main()
        mocks.delete.assert_called_once_with("fixture-pod")
        completed = {"status": "uploaded", "artifact": "fixture"}
        with self.ready_main(result=completed) as mocks, contextlib.redirect_stdout(io.StringIO()):
            mocks.delete.return_value = False
            with self.assertRaisesRegex(RuntimeError, "deletion"):
                runner.main()

    def test_lost_create_response_finds_exact_named_pod_and_never_retries_creation(self):
        self.env["HASLA_PREFLIGHT_ONLY"] = "false"
        creates = []
        lists = []
        def pod_api(method, path, **kwargs):
            if method == "GET" and path == "/pods":
                lists.append(True)
                return [] if len(lists) == 1 else [self.valid_pod(), self.valid_pod(id="unrelated", name="other-job")]
            if method == "POST" and path == "/pods":
                creates.append(True)
                raise runner.requests.Timeout("synthetic create response lost")
            raise AssertionError("unexpected request")
        with self.ready_main() as mocks, patch.object(runner, "runpod", side_effect=pod_api), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(runner.requests.Timeout):
            runner.main()
        self.assertEqual(len(creates), 1)
        mocks.delete.assert_called_once_with("fixture-pod")

    def test_cleanup_matches_exact_name_and_attempts_every_match_even_after_failure(self):
        name = runner.PREFIX + "12345"
        pods = [self.valid_pod(id="first", name=name), self.valid_pod(id="second", name=name),
                self.valid_pod(id="other-batch", name=runner.PREFIX + "99999"), self.valid_pod(id="unrelated", name="other")]
        with patch.object(runner, "runpod", return_value=pods), \
                patch.object(runner, "delete_and_confirm", side_effect=[False, True]) as delete, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.cleanup(), 1)
        self.assertEqual([c.args[0] for c in delete.call_args_list], ["first", "second"])

    def test_delete_requires_provider_absence_and_retries_only_deletion(self):
        with patch.object(runner.requests, "delete", return_value=response(204)) as delete, \
                patch.object(runner.requests, "get", return_value=response(404)) as get:
            self.assertTrue(runner.delete_and_confirm("fixture-pod"))
        self.assertEqual(delete.call_count, 1)
        self.assertEqual(get.call_count, 1)
        with patch.object(runner.requests, "delete", return_value=response(500)) as delete, \
                patch.object(runner.requests, "get") as get:
            self.assertFalse(runner.delete_and_confirm("fixture-pod"))
        self.assertEqual(delete.call_count, 3)
        get.assert_not_called()

    def upload_sdk(self, reference=None, wait_error=None):
        events, artifacts = [], []
        reference = reference or f"fixture-entity/{runner.PROJECT}/{runner.PREFIX}12345-data:v7"
        run = SimpleNamespace(log_artifact=Mock(side_effect=lambda *a, **kw: events.append("upload")),
                              finish=Mock(side_effect=lambda *a, **kw: events.append("finish")))

        class Artifact:
            def __init__(self, name, type, metadata):
                self.name, self.type, self.metadata = name, type, metadata
                self.qualified_name = reference
                self.files = {}
                self.paths = []
                artifacts.append(self)

            def add_file(self, path, name):
                self.files[name] = Path(path).read_bytes()
                self.paths.append(Path(path))

            def wait(self, timeout):
                events.append("committed")
                if wait_error:
                    raise wait_error
                if timeout > 180:
                    raise AssertionError("unbounded upload wait")

        sdk = SimpleNamespace(Artifact=Artifact, Settings=lambda **kw: kw,
                              init=Mock(side_effect=lambda **kw: events.append("init") or run))
        return sdk, run, artifacts, events

    def test_private_input_upload_verifies_privacy_then_transfers_exactly_two_hashed_files(self):
        manifest, data_env = runner.data_environment()
        sdk, run, artifacts, events = self.upload_sdk()
        def privacy(*a, **kw):
            events.append("privacy")
            return {"project": {"name": runner.PROJECT, "access": "PRIVATE"}}
        output = io.StringIO()
        with patch.dict("sys.modules", {"wandb": sdk}), patch.object(runner, "wandb_query", side_effect=privacy), \
                contextlib.redirect_stdout(output):
            pointer = runner.publish_private_input("fixture-entity", runner.PREFIX + "12345", manifest, data_env)
        self.assertEqual(events, ["privacy", "init", "upload", "committed", "finish"])
        self.assertEqual(set(pointer), {"HASLA_INPUT_ARTIFACT", "HASLA_DATA_SHA256", "HASLA_VALIDATION_SHA256"})
        self.assertTrue(pointer["HASLA_INPUT_ARTIFACT"].endswith(":v7"))
        self.assertEqual(set(artifacts[0].files), {"train.text.jsonl", "validation.text.jsonl"})
        for label in ("train", "validation"):
            raw = artifacts[0].files[label + ".text.jsonl"]
            self.assertEqual(hashlib.sha256(raw).hexdigest(), manifest[label]["raw_sha256"])
        self.assertTrue(all(not p.exists() for p in artifacts[0].paths))
        self.assertEqual(artifacts[0].type, "dataset")
        self.assertNotIn(PRIVATE_TEXT, json.dumps(artifacts[0].metadata))
        self.assertNotIn(PRIVATE_TEXT, output.getvalue())
        self.assertNotIn(FAKE_KEY, output.getvalue())
        settings = sdk.init.call_args.kwargs["settings"]
        self.assertEqual(settings["console"], "off")
        self.assertTrue(settings["disable_code"])
        self.assertTrue(settings["disable_git"])
        run.finish.assert_called_once()

    def test_private_input_upload_rejects_foreign_or_public_projects_before_initializing_sdk(self):
        manifest, data_env = runner.data_environment()
        for project in (None, {"name": runner.PROJECT, "access": "PUBLIC"},
                        {"name": "another-project", "access": "PRIVATE"}):
            sdk, run, artifacts, events = self.upload_sdk()
            with self.subTest(project=project), patch.dict("sys.modules", {"wandb": sdk}), \
                    patch.object(runner, "wandb_query", return_value={"project": project}), \
                    self.assertRaisesRegex(RuntimeError, "verified"):
                runner.publish_private_input("fixture-entity", runner.PREFIX + "12345", manifest, data_env)
            sdk.init.assert_not_called()
            self.assertEqual(artifacts, [])

    def test_private_input_upload_requires_immutable_reference_in_the_same_private_project(self):
        manifest, data_env = runner.data_environment()
        base = f"fixture-entity/{runner.PROJECT}/{runner.PREFIX}12345-data"
        for reference in (base + ":latest", base + ":v1-extra", "foreign/project/data:v1"):
            sdk, run, artifacts, events = self.upload_sdk(reference=reference)
            with self.subTest(reference=reference), patch.dict("sys.modules", {"wandb": sdk}), \
                    patch.object(runner, "wandb_query", return_value={"project": {"name": runner.PROJECT, "access": "PRIVATE"}}), \
                    self.assertRaisesRegex(RuntimeError, "immutable"):
                runner.publish_private_input("fixture-entity", runner.PREFIX + "12345", manifest, data_env)
            run.finish.assert_called_once()
            self.assertTrue(all(not p.exists() for p in artifacts[0].paths))

    def test_private_input_upload_failure_closes_run_and_never_returns_a_pointer(self):
        manifest, data_env = runner.data_environment()
        sdk, run, artifacts, events = self.upload_sdk(wait_error=TimeoutError("synthetic upload did not commit"))
        with patch.dict("sys.modules", {"wandb": sdk}), \
                patch.object(runner, "wandb_query", return_value={"project": {"name": runner.PROJECT, "access": "PRIVATE"}}), \
                self.assertRaises(TimeoutError):
            runner.publish_private_input("fixture-entity", runner.PREFIX + "12345", manifest, data_env)
        run.finish.assert_called_once()
        self.assertTrue(all(not p.exists() for p in artifacts[0].paths))

    def test_artifact_transport_places_only_immutable_pointer_and_hashes_in_gpu_environment(self):
        self.env.update({"HASLA_PREFLIGHT_ONLY": "false", "HASLA_INPUT_TRANSPORT": "artifact"})
        pointer = {"HASLA_INPUT_ARTIFACT": f"fixture-entity/{runner.PROJECT}/fixture-data:v4",
                   "HASLA_DATA_SHA256": self.manifest["train"]["raw_sha256"],
                   "HASLA_VALIDATION_SHA256": self.manifest["validation"]["raw_sha256"]}
        with self.ready_main(result={"status": "uploaded", "artifact": "fixture-lora:v0"}) as mocks, \
                patch.object(runner, "publish_private_input", return_value=pointer) as upload, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(), 0)
        upload.assert_called_once()
        payload = next(kw["json"] for method, _, kw in mocks.calls if method == "POST")
        gpu_env = payload["env"]
        self.assertEqual(gpu_env["HASLA_INPUT_ARTIFACT"], pointer["HASLA_INPUT_ARTIFACT"])
        self.assertFalse(any(key.startswith("HASLA_DATA_0") or key.startswith("HASLA_VALIDATION_0") for key in gpu_env))
        self.assertNotIn("HASLA_DATA_PARTS", gpu_env)
        self.assertLess(len(json.dumps(gpu_env)), 4000)
        self.assertNotIn(PRIVATE_TEXT, json.dumps(gpu_env))

    def test_preflight_only_artifact_mode_does_not_upload_private_input(self):
        self.env["HASLA_INPUT_TRANSPORT"] = "artifact"
        with self.ready_main() as mocks, patch.object(runner, "publish_private_input") as upload, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(), 0)
        upload.assert_not_called()
        self.assertFalse(any(method == "POST" for method, _, _ in mocks.calls))

    def test_failed_private_input_upload_cannot_start_a_paid_pod(self):
        self.env.update({"HASLA_PREFLIGHT_ONLY": "false", "HASLA_INPUT_TRANSPORT": "artifact"})
        with self.ready_main() as mocks, \
                patch.object(runner, "publish_private_input", side_effect=RuntimeError("private transfer failed")), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
            runner.main()
        self.assertFalse(any(method == "POST" for method, _, _ in mocks.calls))
        mocks.delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()

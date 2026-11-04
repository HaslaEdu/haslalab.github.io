"""Offline dual-role parent checks: no credentials, network, GPUs or uploads."""
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
from unittest.mock import patch

import private_dual_run as dual


PRIVATE = "SYNTHETIC_PRIVATE_DUAL_FIXTURE"


def fixture():
    env = {"GITHUB_SHA": "a" * 40, "GITHUB_RUN_ID": "12345", "HASLA_PREFLIGHT_ONLY": "false",
           "RUNPOD_API_KEY": "fixture-key", "WANDB_API_KEY": "fixture-key", "HF_TOKEN": "fixture-key"}
    manifest = {"budget_krw": 30000, "prior_upper_krw": 10,
                **{key: "1" * 64 for key in ("train_script_sha256", "role_config_sha256", "pod_script_sha256", "dual_pod_sha256")},
                "roles": {}}
    for role in ("chat", "solver"):
        spec = {"role": role, "format": "chat" if role == "chat" else "text", "dataset_version": "fixture-v1"}
        for split in ("train", "validation"):
            row = {"metadata": {"group_id": f"{role}-{split}", "split": split}}
            if role == "chat":
                row["metadata"].update(derivation="paraphrase_observed_exchange", reconstructed=True,
                    old_synthetic_seed=False, observed_reply_link="fixture top-level body reply",
                    reviewer="agent:fixture", review_status="approved", collected_at="2026-11-04T00:00:00Z",
                    source_url="https://orbi.kr/00079999827", question_sha256="a" * 64, answer_sha256="b" * 64)
                row["messages"] = [{"role": "user", "content": "fixture question " + split},
                                   {"role": "assistant", "content": PRIVATE + split}]
            else:
                row["metadata"].update(drive_provenance={"drive_file_id": "fixture-drive-book", "local_original_pdf_sha256": "c" * 64}, page_number=10)
                row["text"] = PRIVATE + role + split
            raw = (json.dumps(row) + "\n").encode()
            encoded = base64.b64encode(gzip.compress(raw)).decode()
            prefix = f"HASLA_{role.upper()}_" + ("DATA" if split == "train" else "VALIDATION")
            env[prefix + "_00"] = encoded
            spec[split] = {"parts": 1, "records": 1, "raw_sha256": hashlib.sha256(raw).hexdigest(),
                           "encoded_sha256": hashlib.sha256(encoded.encode()).hexdigest()}
        manifest["roles"][role] = spec
    env["HASLA_DUAL_MANIFEST"] = json.dumps(manifest)
    return env, manifest


class PrivateDualParentTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(self.temp.name)
        self.env, self.manifest = fixture()
        patch.dict(os.environ, self.env, clear=True).start()
        patch.object(dual.sys, "argv", ["private_dual_run.py"]).start()
        patch.object(dual.cloud, "E", {}).start()
        for name in ("request", "post", "get", "delete", "head"):
            patch.object(dual.cloud.requests, name, side_effect=AssertionError("external I/O forbidden in tests")).start()
        patch.object(dual.time, "monotonic", return_value=100).start()
        patch.object(dual.time, "sleep", side_effect=AssertionError("unexpected polling wait")).start()

    def pod(self, **kw):
        return {"id": "fixture-pod", "name": dual.cloud.PREFIX + "12345", "costPerHr": "2.5",
                "containerDiskInGb": 200, "volumeInGb": 0, "gpu": {"count": 1}, "desiredStatus": "RUNNING", **kw}

    @contextlib.contextmanager
    def ready(self, failed=False, lost=False):
        operations, lists = [], []
        def api(method, path, **kw):
            operations.append((method, path))
            if path == "/pods":
                lists.append(True)
                return [] if len(lists) == 1 else [self.pod(), self.pod(id="other", name="unrelated")]
            if path == "/pods/fixture-pod":
                return self.pod()
            raise AssertionError("unexpected Runpod operation")
        def create(*args, **kwargs):
            if lost:
                raise dual.cloud.requests.Timeout("synthetic lost response")
            return {"id": "fixture-pod"}
        def publish(entity, run, spec, data):
            return {"HASLA_INPUT_ARTIFACT": f"{entity}/{dual.cloud.PROJECT}/{run}-data:v2"}
        def result(entity, run, **kwargs):
            role = "chat" if run.endswith("-chat") else "solver"
            return {"role": role, "status": "failed" if failed else "uploaded", "artifact": role + "-adapter:v0"}
        patches = [patch.object(dual.cloud, "runpod", side_effect=api),
                   patch.object(dual.cloud, "graphql_create_pod", side_effect=create),
                   patch.object(dual.cloud, "capacity_preflight", return_value=dual.cloud.GPU_IDS[1]),
                   patch.object(dual.cloud, "private_project", return_value="fixture-entity"),
                   patch.object(dual.cloud.requests, "head", return_value=SimpleNamespace(ok=True)),
                   patch.object(dual.cloud, "publish_private_input", side_effect=publish),
                   patch.object(dual.cloud, "result_for", side_effect=result),
                   patch.object(dual.cloud, "delete_and_confirm", return_value=True)]
        mocks = [p.start() for p in patches]
        try:
            yield SimpleNamespace(operations=operations, api=mocks[0], create=mocks[1], publish=mocks[5],
                                  result=mocks[6], delete=mocks[7])
        finally:
            for p in reversed(patches):
                p.stop()

    def test_role_specific_inputs_reject_hash_format_and_group_contamination(self):
        manifest, payloads = dual.load_inputs(self.env)
        self.assertEqual(list(payloads), ["chat", "solver"])
        for role in ("chat", "solver"):
            broken = json.loads(json.dumps(self.manifest))
            broken["roles"][role]["train"]["raw_sha256"] = "0" * 64
            with self.subTest(role=role), self.assertRaises(RuntimeError):
                dual.load_inputs({**self.env, "HASLA_DUAL_MANIFEST": json.dumps(broken)})
        broken = json.loads(json.dumps(self.manifest))
        broken["roles"]["chat"]["format"] = "text"
        with self.assertRaises(ValueError):
            dual.load_inputs({**self.env, "HASLA_DUAL_MANIFEST": json.dumps(broken)})
        # Validation is an intact, correctly hashed JSONL, but belongs to a training group.
        row = {"text": "different passage", "metadata": {"group_id": "solver-train", "split": "validation",
            "drive_provenance": {"drive_file_id": "fixture-drive-book", "local_original_pdf_sha256": "c" * 64}, "page_number": 11}}
        raw = (json.dumps(row) + "\n").encode()
        encoded = base64.b64encode(gzip.compress(raw)).decode()
        broken = json.loads(json.dumps(self.manifest))
        broken["roles"]["solver"]["validation"].update(raw_sha256=hashlib.sha256(raw).hexdigest(),
                                                            encoded_sha256=hashlib.sha256(encoded.encode()).hexdigest())
        with self.assertRaisesRegex(RuntimeError, "group_overlap"):
            dual.load_inputs({**self.env, "HASLA_SOLVER_VALIDATION_00": encoded, "HASLA_DUAL_MANIFEST": json.dumps(broken)})

    def test_preflight_is_zero_gpu_and_uses_one_shared_two_hour_budget(self):
        os.environ["HASLA_PREFLIGHT_ONLY"] = "true"
        output = io.StringIO()
        with self.ready() as mocks, contextlib.redirect_stdout(output):
            self.assertEqual(dual.main(), 0)
        mocks.create.assert_not_called()
        mocks.publish.assert_not_called()
        event = next(json.loads(line) for line in output.getvalue().splitlines() if json.loads(line)["event"] == "dual_preflight")
        self.assertEqual(event["runtime_seconds"], 7200)
        self.assertLess(int(event["reserved_upper_krw"]) + 5000 + 10, 30000)

    def test_authored_seed_or_source_less_book_cannot_masquerade_as_collected_material(self):
        for role in ('chat', 'solver'):
            spec = self.manifest['roles'][role]['train']
            prefix = f'HASLA_{role.upper()}_DATA_00'
            row = json.loads(gzip.decompress(base64.b64decode(self.env[prefix])).decode())
            if role == 'chat':
                row['metadata']['old_synthetic_seed'] = True
            else:
                row['metadata'].pop('drive_provenance')
            raw = (json.dumps(row) + '\n').encode()
            encoded = base64.b64encode(gzip.compress(raw)).decode()
            changed = json.loads(json.dumps(self.manifest))
            changed['roles'][role]['train'].update(raw_sha256=hashlib.sha256(raw).hexdigest(),
                encoded_sha256=hashlib.sha256(encoded.encode()).hexdigest())
            with self.subTest(role=role), self.assertRaisesRegex(ValueError, 'requires'):
                dual.load_inputs({**self.env, prefix: encoded, 'HASLA_DUAL_MANIFEST': json.dumps(changed)})

    def test_one_pod_handles_two_references_and_results_then_always_cleans_up(self):
        output = io.StringIO()
        with self.ready() as mocks, contextlib.redirect_stdout(output):
            self.assertEqual(dual.main(), 0)
        mocks.create.assert_called_once()
        self.assertEqual(mocks.publish.call_count, 2)
        gpu_env = mocks.create.call_args.args[1]
        jobs = json.loads(gpu_env["HASLA_ROLE_JOBS"])
        self.assertEqual([j["role"] for j in jobs], ["chat", "solver"])
        self.assertTrue(all(j["input_artifact"].endswith(":v2") for j in jobs))
        self.assertFalse(any(repr(gpu_env).find(value) >= 0 for key, value in self.env.items()
                             if key.startswith(("HASLA_CHAT_DATA_", "HASLA_SOLVER_DATA_"))))
        self.assertFalse(any(key.startswith(("HASLA_CHAT_", "HASLA_SOLVER_", "HASLA_DATA_00")) for key in gpu_env))
        self.assertNotIn("RUNPOD_API_KEY", gpu_env)
        self.assertNotIn(PRIVATE, output.getvalue())
        results = json.loads(Path("private-dual-result.json").read_text())
        self.assertEqual(set(results), {"chat", "solver"})
        mocks.delete.assert_called_once_with("fixture-pod")

    def test_first_role_failure_does_not_wait_for_second_and_still_deletes(self):
        with self.ready(failed=True) as mocks, contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaisesRegex(RuntimeError, "one model"):
            dual.main()
        mocks.result.assert_called_once()
        self.assertTrue(mocks.result.call_args.args[1].endswith("-chat"))
        mocks.delete.assert_called_once_with("fixture-pod")
        self.assertFalse(Path("private-dual-result.json").exists())

    def test_lost_creation_response_recovers_only_exact_name_without_recreation(self):
        with self.ready(lost=True) as mocks, contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaises(dual.cloud.requests.Timeout):
            dual.main()
        mocks.create.assert_called_once()
        mocks.delete.assert_called_once_with("fixture-pod")


if __name__ == "__main__":
    unittest.main()

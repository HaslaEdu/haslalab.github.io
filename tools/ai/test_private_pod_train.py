"""Offline fixtures only; no credential, network, model download, GPU, or upload."""
import base64
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import private_pod_train as pod


def payload_environment(rows, prefix="HASLA_DATA", shards=2):
    raw = ("\n".join(json.dumps(r) for r in rows) + "\n").encode()
    encoded = base64.b64encode(gzip.compress(raw)).decode()
    step = (len(encoded) + shards - 1) // shards
    parts = [encoded[i:i + step] for i in range(0, len(encoded), step)]
    return {**{f"{prefix}_{i:02d}": part for i, part in enumerate(parts)},
            prefix + "_SHA256": hashlib.sha256(raw).hexdigest(),
            prefix + "_PARTS": str(len(parts))}, raw


class FakeRun:
    def __init__(self):
        self.summary = {}
        self.artifacts = []
        self.exit_codes = []

    def log_artifact(self, artifact, aliases):
        self.artifacts.append((artifact, aliases))

    def finish(self, exit_code=0):
        self.exit_codes.append(exit_code)


class FakeArtifact:
    def __init__(self, name, type, metadata):
        self.name, self.type, self.metadata = name, type, metadata
        self.files = []
        self.qualified_name = f"fixture-entity/private-project/{name}:v3"

    def add_file(self, path, name):
        self.files.append((path, name))

    def wait(self, timeout):
        self.timeout = timeout


class FakeWandb:
    def __init__(self):
        self.run = FakeRun()
        self.init_kwargs = None

    @staticmethod
    def Settings(**kwargs):
        return kwargs

    def init(self, **kwargs):
        self.init_kwargs = kwargs
        return self.run

    Artifact = FakeArtifact


class PrivatePodTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, {}, clear=False).start()
        self.secret_text = "PRIVATE_FIXTURE_BODY_MUST_NEVER_APPEAR_IN_RESULT"
        self.train = [{"text": self.secret_text, "split": "train", "metadata": {"document_id": "book-a"}}]
        self.env, self.raw = payload_environment(self.train)
        self.script = b"# synthetic public training code fixture\n"
        self.env.update({"REPO_SHA": "a" * 40,
                         "HASLA_TRAIN_SCRIPT_SHA256": hashlib.sha256(self.script).hexdigest(),
                         "WANDB_ENTITY": "fixture-entity", "WANDB_PROJECT": "private-project",
                         "WANDB_API_KEY": "fixture-only-wandb-key", "HF_TOKEN": "fixture-only-hf-token",
                         "RUN": "pilot-fixture", "ARTIFACT": "fixture-lora"})
        self.requests, self.calls = [], []
        self.wandb = FakeWandb()

    def opener(self, request, timeout):
        self.requests.append(request)
        if request.full_url.endswith("/graphql"):
            return io.BytesIO(json.dumps({"data": {"project": {"name": "private-project", "access": "PRIVATE"}}}).encode())
        self.assertNotIn("Authorization", dict(request.header_items()))
        self.assertIn("/" + "a" * 40 + "/tools/ai/train_lora.py", request.full_url)
        return io.BytesIO(self.script)

    def runner(self, command, **kwargs):
        self.calls.append((command, kwargs))
        adapter = self.root / "adapter"
        adapter.mkdir()
        (adapter / "adapter_config.json").write_text(json.dumps({"base_model_name_or_path": pod.BASE_MODEL, "peft_type": "LORA"}))
        (adapter / "adapter_model.safetensors").write_bytes(b"synthetic-adapter-file")
        # A raw-data file in the output directory must not become an artifact file.
        (adapter / "do-not-upload.jsonl").write_text(self.secret_text)
        return SimpleNamespace(returncode=0)

    def test_payload_roundtrip_and_bounded_decompression(self):
        self.assertEqual(pod.decode_payload(self.env), self.raw)
        with self.assertRaisesRegex(pod.PilotError, "uncompressed_payload_limit"):
            pod.decode_payload(self.env, max_raw=10)
        with self.assertRaisesRegex(pod.PilotError, "compressed_payload_limit"):
            pod.decode_payload(self.env, max_compressed=5)

    def test_gap_hash_and_invalid_encoding_are_rejected(self):
        broken = dict(self.env)
        broken["HASLA_DATA_02"] = broken.pop("HASLA_DATA_01")
        with self.assertRaisesRegex(pod.PilotError, "noncontiguous"):
            pod.decode_payload(broken)
        broken = {**self.env, "HASLA_DATA_SHA256": "0" * 64}
        with self.assertRaisesRegex(pod.PilotError, "hash_mismatch"):
            pod.decode_payload(broken)
        broken = {**self.env, "HASLA_DATA_00": "not base64$"}
        with self.assertRaisesRegex(pod.PilotError, "invalid_payload_encoding"):
            pod.decode_payload(broken)

    def test_test_and_validation_rows_never_enter_training(self):
        for split in ("test", "validation"):
            for location in ("top", "metadata"):
                row = {"text": "synthetic text", "metadata": {}}
                if location == "top":
                    row["split"] = split
                else:
                    row["metadata"]["split"] = split
                raw = json.dumps(row).encode()
                with self.assertRaisesRegex(pod.PilotError, "wrong_split"):
                    pod.rows_from_payload(raw, "train")

    def test_validation_overlapping_book_or_content_is_rejected(self):
        with self.assertRaisesRegex(pod.PilotError, "group_overlap"):
            pod.verify_partitions(self.train, [{"text": "different text", "metadata": {"document_id": "book-a"}}])
        with self.assertRaisesRegex(pod.PilotError, "content_overlap"):
            pod.verify_partitions(self.train, [{"text": self.secret_text, "metadata": {"document_id": "book-b"}}])

    def test_public_project_stops_before_code_download_or_training(self):
        def public(request, timeout):
            self.requests.append(request)
            return io.BytesIO(json.dumps({"data": {"project": {"name": "private-project", "access": "PUBLIC"}}}).encode())
        result = pod.run_pilot(self.env, self.root, self.wandb, public, self.runner)
        self.assertEqual(result["error_code"], "wandb_project_not_private")
        self.assertEqual(len(self.requests), 1)
        self.assertFalse(self.calls)
        self.assertIsNone(self.wandb.init_kwargs)
        self.assertFalse((self.root / "data.jsonl").exists())

    def test_success_only_uploads_adapter_and_safe_exact_result(self):
        validation_env, validation_raw = payload_environment([
            {"text": "synthetic validation document", "split": "validation", "metadata": {"document_id": "book-b"}}
        ], "HASLA_VALIDATION")
        self.env.update(validation_env)
        result = pod.run_pilot(self.env, self.root, self.wandb, self.opener, self.runner)
        self.assertEqual(result["status"], "uploaded")
        self.assertEqual(result["artifact"], "fixture-entity/private-project/fixture-lora:v3")
        self.assertFalse(result["deployed"])
        self.assertFalse(result["promoted"])
        self.assertEqual(result["test_records_used"], 0)
        self.assertEqual((self.root / "data.jsonl").read_bytes(), self.raw)
        self.assertEqual((self.root / "validation.jsonl").read_bytes(), validation_raw)
        command, kwargs = self.calls[0]
        for option, value in (("--base", "solver"), ("--format", "text"), ("--max-steps", "32"),
                              ("--epochs", "1"), ("--lr", "1e-5"), ("--max-len", "1024")):
            self.assertEqual(command[command.index(option) + 1], value)
        self.assertIn("--validation-data", command)
        self.assertEqual(kwargs["stdout"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)
        self.assertEqual(kwargs["env"]["WANDB_MODE"], "disabled")
        self.assertFalse(any(k.startswith("HASLA_DATA_") for k in kwargs["env"]))
        self.assertNotIn("WANDB_API_KEY", kwargs["env"])
        uploaded = self.wandb.run.artifacts[0][0]
        self.assertEqual({name for _, name in uploaded.files}, {"adapter_config.json", "adapter_model.safetensors"})
        logged = json.dumps({"summary": self.wandb.run.summary, "config": self.wandb.init_kwargs["config"],
                            "artifact_metadata": uploaded.metadata, "result": result})
        self.assertNotIn(self.secret_text, logged)
        self.assertNotIn(self.env["WANDB_API_KEY"], logged)
        self.assertEqual(self.wandb.init_kwargs["settings"]["console"], "off")

    def test_unverified_public_code_cannot_execute(self):
        self.env["HASLA_TRAIN_SCRIPT_SHA256"] = "0" * 64
        result = pod.run_pilot(self.env, self.root, self.wandb, self.opener, self.runner)
        self.assertEqual(result["error_code"], "training_code_hash_mismatch")
        self.assertFalse(self.calls)

    def test_unexpected_exception_text_is_not_logged(self):
        def failing_runner(*args, **kwargs):
            raise RuntimeError(self.secret_text + " " + self.env["WANDB_API_KEY"])
        result = pod.run_pilot(self.env, self.root, self.wandb, self.opener, failing_runner)
        serialized = (self.root / "result.json").read_text()
        self.assertEqual(result["error_code"], "RuntimeError")
        self.assertNotIn(self.secret_text, serialized)
        self.assertNotIn(self.env["WANDB_API_KEY"], serialized)
        self.assertNotIn(str(self.root), serialized)
        self.assertEqual(self.wandb.run.summary["status"], "failed")

    def test_known_unsloth_base_alias_is_preserved(self):
        self.runner([], env={})
        path = self.root / "adapter" / "adapter_config.json"
        value = {"base_model_name_or_path": "unsloth/QwQ-32B-unsloth-bnb-4bit", "peft_type": "LORA"}
        path.write_text(json.dumps(value))
        pod.adapter_inventory(path.parent)
        self.assertEqual(json.loads(path.read_text()), value)
        path.write_text(json.dumps({**value, "base_model_name_or_path": "unrelated/model"}))
        with self.assertRaisesRegex(pod.PilotError, "base_model_mismatch"):
            pod.adapter_inventory(path.parent)

    def test_arbitrary_wandb_endpoint_cannot_receive_credentials(self):
        self.env["WANDB_BASE_URL"] = "https://example.test"
        with self.assertRaisesRegex(pod.PilotError, "wandb_configuration"):
            pod.assert_private_project(self.env, self.opener)
        self.assertFalse(self.requests)


if __name__ == "__main__":
    unittest.main()

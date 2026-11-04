"""Offline fixtures only; no credential, network, model download, GPU, or upload."""
import base64
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import private_pod_train as pod
from role_config import get_role_config


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


class FakeDatasetArtifact:
    def __init__(self, files, reference="fixture-entity/private-project/private-input:v2"):
        self.files = files
        self.qualified_name = reference
        self.type, self.state, self.is_link = "dataset", "COMMITTED", False
        self.manifest = SimpleNamespace(entries={
            name: SimpleNamespace(size=len(data), ref=None) for name, data in files.items()})
        self.downloads = []

    def download(self, **kwargs):
        self.downloads.append(kwargs)
        root = Path(kwargs["root"])
        root.mkdir()
        for name, data in self.files.items():
            (root / name).write_bytes(data)
        return str(root)


class FakeWandb:
    def __init__(self):
        self.run = FakeRun()
        self.init_kwargs = None
        self.dataset_artifact = None
        self.api_requests = []

    @staticmethod
    def Settings(**kwargs):
        return kwargs

    def init(self, **kwargs):
        self.init_kwargs = kwargs
        return self.run

    Artifact = FakeArtifact

    def Api(self, **kwargs):
        self.api_kwargs = kwargs

        def artifact(reference, type):
            self.api_requests.append((reference, type))
            return self.dataset_artifact
        return SimpleNamespace(artifact=artifact)


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
        self.role_script = Path(pod.__file__).with_name("role_config.py").read_bytes()
        self.env.update({"REPO_SHA": "a" * 40,
                         "ROLE": "solver", "HASLA_DATA_FORMAT": "text",
                         "HASLA_TRAIN_SCRIPT_SHA256": hashlib.sha256(self.script).hexdigest(),
                         "HASLA_ROLE_CONFIG_SHA256": hashlib.sha256(self.role_script).hexdigest(),
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
        self.assertIn("/" + "a" * 40 + "/tools/ai/", request.full_url)
        if request.full_url.endswith("/role_config.py"):
            return io.BytesIO(self.role_script)
        self.assertTrue(request.full_url.endswith("/train_lora.py"))
        return io.BytesIO(self.script)

    def runner(self, command, **kwargs):
        self.calls.append((command, kwargs))
        config = get_role_config(command[command.index("--base") + 1]) if "--base" in command else get_role_config("solver")
        data_format = command[command.index("--format") + 1] if "--format" in command else "text"
        max_steps = int(command[command.index("--max-steps") + 1]) if "--max-steps" in command else config["max_steps"]
        adapter = self.root / "adapter"
        adapter.mkdir()
        (adapter / "adapter_config.json").write_text(json.dumps({"base_model_name_or_path": config["base_model"],
                                                                 "peft_type": "LORA", "r": config["default_rank"]}))
        (adapter / "adapter_model.safetensors").write_bytes(b"synthetic-adapter-file")
        # A raw-data file in the output directory must not become an artifact file.
        (adapter / "do-not-upload.jsonl").write_text(self.secret_text)
        training_file = self.root / f"train.{data_format}.jsonl"
        validation_file = self.root / f"validation.{data_format}.jsonl"
        report = {"role": config["role"], "base_model": config["base_model"], "precision": config["precision"],
                  "training_method": config["training_method"], "rank": config["default_rank"],
                  "max_length": config["max_length"], "max_steps": max_steps, "format": data_format,
                  "steps_completed": max_steps, "weights_updated": True,
                  "training_sha256": hashlib.sha256(training_file.read_bytes()).hexdigest() if training_file.exists() else None,
                  "validation_sha256": hashlib.sha256(validation_file.read_bytes()).hexdigest() if validation_file.exists() else None}
        (adapter / "hasla_training_manifest.json").write_text(json.dumps(report))
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
        self.assertFalse((self.root / "train.text.jsonl").exists())

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
        self.assertEqual((self.root / "train.text.jsonl").read_bytes(), self.raw)
        self.assertEqual((self.root / "validation.text.jsonl").read_bytes(), validation_raw)
        command, kwargs = self.calls[0]
        for option, value in (("--base", "solver"), ("--format", "text"), ("--max-steps", "1"),
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
        self.assertEqual(result["role"], "solver")
        self.assertEqual(result["precision"], "4bit")
        self.assertEqual(result["steps_completed"], 1)
        self.assertEqual(result["max_steps"], 1)
        self.assertEqual(result["role_max_steps"], get_role_config("solver")["max_steps"])
        self.assertEqual(self.wandb.init_kwargs["config"]["max_steps"], 1)
        self.assertEqual(uploaded.metadata["max_steps"], 1)

    def test_unverified_public_code_cannot_execute(self):
        self.env["HASLA_TRAIN_SCRIPT_SHA256"] = "0" * 64
        result = pod.run_pilot(self.env, self.root, self.wandb, self.opener, self.runner)
        self.assertEqual(result["error_code"], "training_code_hash_mismatch")
        self.assertFalse(self.calls)
        self.assertEqual(self.wandb.init_kwargs["id"], self.env["RUN"])
        self.assertEqual(self.wandb.init_kwargs["job_type"], "private-solver-pilot-early-failure")
        logged = self.wandb.run.summary["private_training_result"]
        self.assertEqual(logged["status"], "failed")
        self.assertEqual(logged["stage"], "training_code_verification")
        self.assertFalse(logged["training_started"])
        self.assertFalse(logged["weights_updated"])
        self.assertFalse(self.wandb.run.artifacts)
        self.assertEqual(self.wandb.run.exit_codes, [1])
        serialized = json.dumps({"config": self.wandb.init_kwargs["config"], "summary": self.wandb.run.summary})
        self.assertNotIn(self.secret_text, serialized)
        self.assertNotIn(self.env["WANDB_API_KEY"], serialized)
        self.assertNotIn(self.env["HF_TOKEN"], serialized)
        for key in ("console", "disable_code", "save_code", "disable_git", "disable_job_creation", "x_disable_meta", "x_disable_stats"):
            self.assertEqual(self.wandb.init_kwargs["settings"][key], "off" if key == "console" else False if key == "save_code" else True)
        self.assertEqual(sum(r.full_url.endswith("/graphql") for r in self.requests), 2)

    def test_early_failure_is_not_published_if_project_privacy_changed(self):
        self.env["HASLA_TRAIN_SCRIPT_SHA256"] = "0" * 64
        privacy_checks = []
        def changed_privacy(request, timeout):
            if request.full_url.endswith("/graphql"):
                privacy_checks.append(request)
                access = "PRIVATE" if len(privacy_checks) == 1 else "PUBLIC"
                return io.BytesIO(json.dumps({"data": {"project": {"name": "private-project", "access": access}}}).encode())
            return self.opener(request, timeout)
        result = pod.run_pilot(self.env, self.root, self.wandb, changed_privacy, self.runner)
        self.assertEqual(result["error_code"], "training_code_hash_mismatch")
        self.assertEqual(len(privacy_checks), 2)
        self.assertIsNone(self.wandb.init_kwargs)
        self.assertFalse(self.calls)

    def test_missing_or_unverified_early_failure_configuration_never_contacts_reporter(self):
        private = {"entity": "fixture-entity", "project": "private-project",
                   "base_url": "https://api.wandb.ai", "access": "PRIVATE"}
        result = pod.safe_failure(pod.PilotError("training_code_hash_mismatch"), "training_code_verification")
        for state, env in ((None, self.env), ({**private, "access": "PUBLIC"}, self.env),
                           (private, {**self.env, "RUN": "../unsafe"}),
                           (private, {**self.env, "WANDB_API_KEY": ""}),
                           (private, {**self.env, "ROLE": "invalid"})):
            with self.subTest(state=state, run=env.get("RUN")):
                pod.publish_early_failure(env, self.root, state, result, self.wandb, self.opener)
        self.assertFalse(self.requests)
        self.assertIsNone(self.wandb.init_kwargs)

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
        value = {"base_model_name_or_path": "unsloth/QwQ-32B-unsloth-bnb-4bit", "peft_type": "LORA", "r": 16}
        path.write_text(json.dumps(value))
        pod.adapter_inventory(path.parent, get_role_config("solver"))
        self.assertEqual(json.loads(path.read_text()), value)
        path.write_text(json.dumps({**value, "base_model_name_or_path": "unrelated/model"}))
        with self.assertRaisesRegex(pod.PilotError, "base_model_mismatch"):
            pod.adapter_inventory(path.parent, get_role_config("solver"))

    def test_arbitrary_wandb_endpoint_cannot_receive_credentials(self):
        self.env["WANDB_BASE_URL"] = "https://example.test"
        with self.assertRaisesRegex(pod.PilotError, "wandb_configuration"):
            pod.assert_private_project(self.env, self.opener)
        self.assertFalse(self.requests)

    def configure_dataset_input(self, validation=False):
        for key in list(self.env):
            if re.fullmatch(r"HASLA_DATA_\d{2}", key):
                del self.env[key]
        reference = "fixture-entity/private-project/private-input:v2"
        self.env["HASLA_INPUT_ARTIFACT"] = reference
        data_format = self.env["HASLA_DATA_FORMAT"]
        files = {f"train.{data_format}.jsonl": self.raw}
        if validation:
            record = {"text": "separate validation book", "split": "validation", "metadata": {"document_id": "book-b"}}
            if data_format == "chat":
                record = {"messages": [{"role": "user", "content": "validation question"},
                                       {"role": "assistant", "content": "validation reply"}],
                          "split": "validation", "metadata": {"conversation_id": "chat-b"}}
            validation_env, data = payload_environment([record], "HASLA_VALIDATION")
            self.env["HASLA_VALIDATION_SHA256"] = validation_env["HASLA_VALIDATION_SHA256"]
            files[f"validation.{data_format}.jsonl"] = data
        self.wandb.dataset_artifact = FakeDatasetArtifact(files, reference)
        return self.wandb.dataset_artifact

    def test_private_input_artifact_downloads_exact_files_then_trains(self):
        dataset = self.configure_dataset_input(validation=True)
        result = pod.run_pilot(self.env, self.root, self.wandb, self.opener, self.runner)
        self.assertEqual(result["status"], "uploaded")
        self.assertEqual(self.wandb.api_requests, [(self.env["HASLA_INPUT_ARTIFACT"], "dataset")])
        self.assertEqual(len(dataset.downloads), 1)
        self.assertTrue(dataset.downloads[0]["skip_cache"])
        self.assertFalse(dataset.downloads[0]["allow_missing_references"])
        self.assertEqual((self.root / "train.text.jsonl").read_bytes(), self.raw)
        self.assertIn("--validation-data", self.calls[0][0])
        serialized = json.dumps(self.wandb.run.summary)
        self.assertNotIn(self.secret_text, serialized)
        self.assertNotIn(self.env["WANDB_API_KEY"], serialized)

    def test_artifact_other_project_and_latest_never_download(self):
        self.configure_dataset_input()
        for bad in ("other/private-project/data:v2", "fixture-entity/public-project/data:v2",
                    "fixture-entity/private-project/data:latest", "fixture-entity/private-project/../data:v2"):
            self.env["HASLA_INPUT_ARTIFACT"] = bad
            result = pod.run_pilot(self.env, self.root, self.wandb, self.opener, self.runner)
            self.assertEqual(result["status"], "failed")
        self.assertFalse(self.requests)
        self.assertFalse(self.wandb.api_requests)
        self.assertFalse(self.calls)

    def test_artifact_unexpected_test_file_is_rejected_before_download(self):
        artifact = self.configure_dataset_input()
        artifact.manifest.entries["test.text.jsonl"] = SimpleNamespace(size=20, ref=None)
        result = pod.run_pilot(self.env, self.root, self.wandb, self.opener, self.runner)
        self.assertEqual(result["error_code"], "input_artifact_unexpected_files")
        self.assertFalse(artifact.downloads)
        self.assertFalse(self.calls)

    def test_artifact_external_references_are_not_fetched(self):
        artifact = self.configure_dataset_input()
        artifact.manifest.entries["train.text.jsonl"].ref = "https://untrusted.example/data"
        result = pod.run_pilot(self.env, self.root, self.wandb, self.opener, self.runner)
        self.assertEqual(result["error_code"], "input_artifact_external_reference")
        self.assertFalse(artifact.downloads)

    def test_artifact_size_and_raw_hash_are_both_checked(self):
        artifact = self.configure_dataset_input()
        artifact.manifest.entries["train.text.jsonl"].size = pod.MAX_RAW_BYTES + 1
        result = pod.run_pilot(self.env, self.root, self.wandb, self.opener, self.runner)
        self.assertEqual(result["error_code"], "input_artifact_file_size_limit")
        self.assertFalse(artifact.downloads)
        artifact.manifest.entries["train.text.jsonl"].size = len(self.raw)
        self.env["HASLA_DATA_SHA256"] = "0" * 64
        result = pod.run_pilot(self.env, self.root, self.wandb, self.opener, self.runner)
        self.assertEqual(result["error_code"], "payload_hash_mismatch")
        self.assertFalse(self.calls)

    def test_downloaded_symlink_is_rejected(self):
        self.configure_dataset_input()
        original = Path.is_symlink
        with patch.object(Path, "is_symlink", lambda path: path.name == "train.text.jsonl" or original(path)):
            result = pod.run_pilot(self.env, self.root, self.wandb, self.opener, self.runner)
        self.assertEqual(result["error_code"], "input_artifact_unsafe_file")
        self.assertFalse(self.calls)

    def test_downloaded_artifact_test_split_still_cannot_train(self):
        artifact = self.configure_dataset_input()
        raw = (json.dumps({"text": "held-out example", "split": "test"}) + "\n").encode()
        artifact.files["train.text.jsonl"] = raw
        artifact.manifest.entries["train.text.jsonl"].size = len(raw)
        self.env["HASLA_DATA_SHA256"] = hashlib.sha256(raw).hexdigest()
        result = pod.run_pilot(self.env, self.root, self.wandb, self.opener, self.runner)
        self.assertEqual(result["error_code"], "test_or_wrong_split_in_payload")
        self.assertFalse(self.calls)

    def configure_chat(self):
        self.train = [{"messages": [{"role": "user", "content": "안녕, 질문해도 돼?"},
                                    {"role": "assistant", "content": self.secret_text}],
                       "split": "train", "metadata": {"conversation_id": "chat-a", "training_role": "chat"}}]
        data_env, self.raw = payload_environment(self.train)
        for key in list(self.env):
            if key.startswith("HASLA_DATA_"):
                del self.env[key]
        self.env.update(data_env)
        self.env.update({"ROLE": "chat", "HASLA_DATA_FORMAT": "chat"})

    def test_chat_role_uses_gemma_bf16_rank8_and_never_loads_solver(self):
        self.configure_chat()
        self.configure_dataset_input(validation=True)
        result = pod.run_pilot(self.env, self.root, self.wandb, self.opener, self.runner)
        self.assertEqual(result["status"], "uploaded")
        self.assertEqual(result["role"], "chat")
        self.assertEqual(result["base_model"], "google/gemma-4-26B-A4B-it")
        self.assertEqual(result["precision"], "bf16")
        self.assertEqual(result["training_method"], "lora")
        self.assertEqual(result["rank"], 8)
        self.assertEqual(result["steps_completed"], 1)
        self.assertEqual(result["role_max_steps"], get_role_config("chat")["max_steps"])
        self.assertEqual(len(self.calls), 1)
        command, kwargs = self.calls[0]
        for flag, expected in (("--base", "chat"), ("--format", "chat"), ("--rank", "8")):
            self.assertEqual(command[command.index(flag) + 1], expected)
        self.assertIn("train.chat.jsonl", " ".join(command))
        self.assertEqual(self.wandb.init_kwargs["config"]["precision"], "bf16")
        uploaded = self.wandb.run.artifacts[0][0]
        self.assertEqual(uploaded.metadata["role"], "chat")
        self.assertEqual(uploaded.metadata["base_model"], result["base_model"])
        self.assertNotIn("HASLA_INPUT_ARTIFACT", kwargs["env"])
        self.assertNotIn(self.secret_text, json.dumps(result))

    def test_data_bounded_steps_copy_config_and_never_exceed_role_caps(self):
        for role, n, expected in (("chat", 1, 1), ("chat", 8, 1), ("chat", 9, 2),
                                  ("chat", 17, 3), ("chat", 64, 8), ("chat", 1000, 8),
                                  ("solver", 1, 1), ("solver", 9, 2), ("solver", 255, 32),
                                  ("solver", 256, 32), ("solver", 1000, 32)):
            with self.subTest(role=role, n=n):
                original = get_role_config(role)
                capped = pod.data_bounded_settings(original, n)
                self.assertEqual(capped["max_steps"], expected)
                self.assertEqual(capped["role_max_steps"], original["max_steps"])
                self.assertNotIn("role_max_steps", original)
                self.assertEqual(capped["effective_batch_rows"], 8)
        for bad in (0, -1, True, 1.5, "8"):
            with self.subTest(bad=bad), self.assertRaisesRegex(pod.PilotError, "row_count"):
                pod.data_bounded_settings(get_role_config("chat"), bad)

    def test_tiny_chat_steps_use_validated_count_and_ignore_environment_overrides(self):
        self.configure_chat()
        rows = [{"messages": [{"role": "user", "content": "synthetic question " + str(i)},
                               {"role": "assistant", "content": "synthetic reply " + str(i)}],
                 "split": "train", "metadata": {"conversation_id": "chat-" + str(i), "training_role": "chat"}}
                for i in range(9)]
        data_env, self.raw = payload_environment(rows)
        for key in list(self.env):
            if key.startswith("HASLA_DATA_"):
                del self.env[key]
        self.env.update(data_env)
        self.env["HASLA_DATA_FORMAT"] = "chat"
        self.env.update({"MAX_STEPS": "9999", "HASLA_MAX_STEPS": "9999", "GRADIENT_ACCUMULATION_STEPS": "1"})
        result = pod.run_pilot(self.env, self.root, self.wandb, self.opener, self.runner)
        self.assertEqual(result["status"], "uploaded")
        command = self.calls[0][0]
        self.assertEqual(command[command.index("--max-steps") + 1], "2")
        self.assertEqual(result["training_records"], 9)
        self.assertEqual(result["max_steps"], 2)
        self.assertEqual(result["steps_completed"], 2)
        self.assertEqual(self.wandb.init_kwargs["config"]["max_steps"], 2)
        self.assertEqual(self.wandb.run.artifacts[0][0].metadata["max_steps"], 2)

    def test_solver_256_rows_retains_the_32_step_cap(self):
        rows = [{"text": "synthetic native textbook row " + str(i), "split": "train",
                 "metadata": {"document_id": "book-" + str(i)}} for i in range(256)]
        data_env, self.raw = payload_environment(rows)
        for key in list(self.env):
            if key.startswith("HASLA_DATA_"):
                del self.env[key]
        self.env.update(data_env)
        self.env["HASLA_DATA_FORMAT"] = "text"
        result = pod.run_pilot(self.env, self.root, self.wandb, self.opener, self.runner)
        self.assertEqual(result["status"], "uploaded")
        command = self.calls[0][0]
        self.assertEqual(command[command.index("--max-steps") + 1], "32")
        self.assertEqual(result["training_records"], 256)
        self.assertEqual(result["steps_completed"], 32)

    def test_trainer_cannot_report_full_role_cap_after_a_tiny_data_limit(self):
        def ignores_bounded_steps(command, **kwargs):
            completed = self.runner(command, **kwargs)
            path = self.root / "adapter" / "hasla_training_manifest.json"
            report = json.loads(path.read_text())
            report.update({"max_steps": 32, "steps_completed": 32})
            path.write_text(json.dumps(report))
            return completed
        result = pod.run_pilot(self.env, self.root, self.wandb, self.opener, ignores_bounded_steps)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_code"], "training_report_role_or_input_mismatch")
        self.assertFalse(self.wandb.run.artifacts)

    def test_missing_or_crossed_role_format_is_rejected_before_private_data_access(self):
        for role, data_format in ((None, "text"), ("chat", "text"), ("solver", None), ("both", "text")):
            with self.subTest(role=role, data_format=data_format):
                result = pod.run_pilot({**self.env, "ROLE": role, "HASLA_DATA_FORMAT": data_format},
                                       self.root, self.wandb, self.opener, self.runner)
                self.assertEqual(result["status"], "failed")
        self.assertFalse(self.requests)
        self.assertFalse(self.calls)

    def test_chat_records_require_messages_and_solver_chat_requires_verified_solutions(self):
        with self.assertRaisesRegex(pod.PilotError, "invalid_chat"):
            pod.rows_from_payload(self.raw, "train", "chat")
        unpaired = {"messages": [{"role": "user", "content": "question"}]}
        with self.assertRaisesRegex(pod.PilotError, "invalid_chat"):
            pod.rows_from_payload(json.dumps(unpaired).encode(), "train", "chat")
        self.configure_chat()
        self.train[0]["metadata"].pop("training_role")
        with self.assertRaisesRegex(pod.PilotError, "verified_solution"):
            pod.validate_row_roles(self.train, "solver", "chat")
        self.train[0]["metadata"]["review_status"] = "verified"
        pod.validate_row_roles(self.train, "solver", "chat")
        self.train[0]["metadata"]["training_role"] = "chat"
        with self.assertRaisesRegex(pod.PilotError, "role_mismatch"):
            pod.validate_row_roles(self.train, "solver", "chat")

    def test_chat_partition_checks_thread_and_exact_message_overlap(self):
        self.configure_chat()
        with self.assertRaisesRegex(pod.PilotError, "group_overlap"):
            pod.verify_partitions(self.train, [{"messages": [{"role": "assistant", "content": "different"}],
                                               "metadata": {"conversation_id": "chat-a"}}])
        with self.assertRaisesRegex(pod.PilotError, "content_overlap"):
            pod.verify_partitions(self.train, [{"messages": self.train[0]["messages"],
                                               "metadata": {"conversation_id": "chat-b"}}])

    def test_role_configuration_is_pinned_separately_before_trainer_execution(self):
        self.env["HASLA_ROLE_CONFIG_SHA256"] = "0" * 64
        result = pod.run_pilot(self.env, self.root, self.wandb, self.opener, self.runner)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["stage"], "role_config_verification")
        self.assertEqual(result["error_code"], "training_code_hash_mismatch")
        self.assertFalse(self.calls)
        self.assertEqual(self.wandb.run.summary["private_training_result"]["stage"], "role_config_verification")
        self.assertFalse(self.wandb.run.summary["private_training_result"]["training_started"])

    def test_adapter_cross_role_base_and_incorrect_rank_are_rejected(self):
        self.runner([], env={})
        path = self.root / "adapter" / "adapter_config.json"
        for changed, error in (({"base_model_name_or_path": get_role_config("chat")["base_model"]}, "base_model"),
                               ({"r": 8}, "rank"), ({"r": True}, "rank")):
            path.write_text(json.dumps({"base_model_name_or_path": get_role_config("solver")["base_model"],
                                        "peft_type": "LORA", "r": 16, **changed}))
            with self.subTest(changed=changed), self.assertRaisesRegex(pod.PilotError, error):
                pod.adapter_inventory(path.parent, get_role_config("solver"))

    def test_trainer_report_must_confirm_role_precision_hash_and_actual_bounded_steps(self):
        for changed in ({"steps_completed": 0}, {"steps_completed": 33}, {"steps_completed": True},
                        {"role": "chat"}, {"precision": "bf16"}, {"training_sha256": "0" * 64},
                        {"weights_updated": False}, {"eval_loss": float("nan")}, {"train_loss": True}):
            self.runner([], env={})
            adapter = self.root / "adapter"
            path = adapter / "hasla_training_manifest.json"
            report = json.loads(path.read_text())
            report.update({"training_sha256": "1" * 64, **changed})
            path.write_text(json.dumps(report))
            with self.subTest(changed=changed), self.assertRaises(pod.PilotError):
                pod.training_report(adapter, get_role_config("solver"), "text", "1" * 64, None)
            for child in adapter.iterdir():
                child.unlink()
            adapter.rmdir()

    def test_role_workspaces_are_fixed_separate_paths(self):
        self.assertEqual(pod.workspace_from_environment({}), Path("/workspace"))
        self.assertEqual(pod.workspace_from_environment({"ROLE": "chat", "HASLA_DATA_FORMAT": "chat",
                                                        "HASLA_WORKSPACE": "/workspace/chat"}), Path("/workspace/chat"))
        for bad in ("/workspace/solver", "/workspace/chat/../solver", "/tmp/private", "/workspace/chat/"):
            with self.subTest(path=bad), self.assertRaisesRegex(pod.PilotError, "workspace"):
                pod.workspace_from_environment({"ROLE": "chat", "HASLA_DATA_FORMAT": "chat", "HASLA_WORKSPACE": bad})


if __name__ == "__main__":
    unittest.main()

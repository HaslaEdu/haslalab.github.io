"""Tiny offline fixtures only: no W&B SDK, network, model, GPU, or real adapter."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import private_verify_adapter as verify


def container(tensors):
    header, data = {}, bytearray()
    for name, dtype, shape, values in tensors:
        start = len(data)
        width = verify.DTYPES[dtype][0]
        for value in values:
            data.extend(value.to_bytes(width, "little"))
        header[name] = {"dtype": dtype, "shape": shape, "data_offsets": [start, len(data)]}
    return encoded(header, bytes(data))


def encoded(header, data=b""):
    body = json.dumps(header, separators=(",", ":")).encode()
    body += b" " * ((-len(body)) % 8)
    return struct.pack("<Q", len(body)) + body + data


def adapter(dtype="F32", bits=None, rank=8, embedding=False):
    stem = "lora_embedding" if embedding else "lora"
    bits = [0] * rank if bits is None else bits
    return container([("base.block." + stem + "_A.weight", dtype, [rank, 1], [0] * rank),
                      ("base.block." + stem + "_B.weight", dtype, [1, rank], bits)])


class Entry:
    def __init__(self, name, data, tracker):
        self.path, self.data, self.size, self.ref = name, data, len(data), None
        self.tracker = tracker
        self.parent_bound = False

    def download(self, root, skip_cache):
        if not self.parent_bound:
            raise AssertionError("get_entry must bind the parent artifact before download")
        if skip_cache is not True:
            raise AssertionError("cache must not be used")
        self.tracker.append(self.path)
        path = Path(root) / self.path
        path.write_bytes(self.data)
        return str(path)


class Fixture:
    def __init__(self, role="chat", model=None, initializer=True):
        self.downloads, self.api_calls, self.checks = [], [], 0
        self.fail_private_at = None
        self.results = {}
        self.artifacts = {}
        self.add_role(role, model, initializer)

    def add_role(self, role, model=None, initializer=True):
        config = verify.get_role_config(role)
        rank = config["default_rank"]
        peft = {"peft_type": "LORA", "r": rank, "base_model_name_or_path": config["base_model"]}
        if initializer is not None:
            peft["init_lora_weights"] = initializer
        blobs = {verify.FILES[0]: json.dumps(peft).encode(),
                 verify.FILES[1]: model if model is not None else adapter(bits=[1] + [0] * (rank - 1), rank=rank)}
        inventory = [{"name": name, "bytes": len(blobs[name]),
                      "sha256": hashlib.sha256(blobs[name]).hexdigest()} for name in verify.FILES]
        combined = hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        ref = f"fixture-entity/{verify.PROJECT}/hasla-private-books-123-{role}-lora:v0"
        result = {"status": "uploaded", "artifact": ref, "role": role,
                  "base_model": config["base_model"], "rank": rank, "steps_completed": 1,
                  "adapter_files": inventory, "adapter_sha256": combined}
        self.results[role] = result
        metadata = {key: result[key] for key in ("role", "base_model", "rank", "steps_completed", "adapter_sha256")}
        metadata["private"] = True
        entries = {name: Entry(name, blob, self.downloads) for name, blob in blobs.items()}
        # A private artifact may contain other files; these must never be downloaded.
        entries["do-not-download.txt"] = Entry("do-not-download.txt", b"PRIVATE RAW LOG", self.downloads)
        def get_entry(name):
            entry = entries[name]
            entry.parent_bound = True
            return entry
        self.artifacts[ref] = SimpleNamespace(qualified_name=ref, type="lora", state="COMMITTED",
                                              is_link=False, metadata=metadata,
                                              manifest=SimpleNamespace(entries=entries), get_entry=get_entry)

    def entity(self):
        return "fixture-entity"

    def assert_private(self, entity):
        self.checks += 1
        if self.checks == self.fail_private_at:
            raise verify.VerificationError("private_project_required")

    def result(self, entity, run_id, role):
        return self.results.get(role)

    def artifact(self, reference, type):
        self.api_calls.append(reference)
        return self.artifacts[reference]

    def run(self, roles="chat", sdk_factory=None):
        return verify.verify("123", roles, {"WANDB_API_KEY": "fixture-key-never-print"},
                             reader_factory=lambda key: self,
                             sdk_factory=sdk_factory or (lambda key: self))


class SafetensorsTests(unittest.TestCase):
    def test_legacy_result_cannot_hide_unknown_or_stripped_artifact_profile(self):
        for extra in ({'training_profile': 'unknown'},
                      {'training_profile': 'gemma-26b-qlora-v1'},
                      {'runtime_profile_proof': {'arbitrary_raw_text': 'synthetic-private-must-not-emit'}}):
            fixture = Fixture()
            artifact = fixture.artifacts[fixture.results['chat']['artifact']]
            artifact.metadata.update(extra)
            outcome = fixture.run()
            self.assertEqual(outcome['roles'][0]['code'], 'artifact_training_profile_mismatch')
            self.assertEqual(fixture.downloads, [])
            self.assertNotIn('synthetic-private-must-not-emit', json.dumps(outcome))

    def test_chat_quantized_profile_verifies_same_base_weights_and_binds_private_proof(self):
        fixture = Fixture()
        profile = 'gemma-26b-qlora-v1'
        proof = {'expert_quantization_verified': True, 'expert_blocks': 30, 'quantized_expert_tensors': 60,
                 'first_optimizer_step_completed': True, 'gpu_count': 1, 'cpu_or_disk_offload_used': False,
                 'gpu_name': 'NVIDIA A40', 'physical_vram_bytes': 48 * 1024**3,
                 'first_step_peak_allocated_bytes': 16 * 1024**3, 'first_step_peak_reserved_bytes': 18 * 1024**3,
                 'expert_quantizer_module_sha256': 'a' * 64, 'unsloth_zoo_version': '2026.11.2',
                 'expert_quantizer_upstream_fix': '9adee9372d5d86749e757d5a91c6bfa30c2ff674'}
        fields = dict(training_profile=profile, precision='4bit', training_method='qlora', runtime_profile_proof=proof)
        result = fixture.results['chat']
        result.update(fields)
        artifact = fixture.artifacts[result['artifact']]
        artifact.metadata.update(fields)
        outcome = fixture.run()['roles'][0]
        self.assertEqual(outcome['status'], 'verified')
        self.assertEqual(outcome['training_profile'], profile)
        self.assertEqual(outcome['runtime_profile_proof'], proof)
        artifact.metadata['training_profile'] = 'unknown'
        self.assertEqual(fixture.run()['roles'][0]['code'], 'artifact_training_profile_mismatch')
        for change in ({'training_profile': 'unknown'}, {'runtime_profile_proof': {**proof, 'expert_blocks': 29}},
                       {'runtime_profile_proof': {**proof, 'arbitrary_raw_text': 'must-not-emit'}},
                       {'runtime_profile_proof': {**proof, 'gpu_name': 'NVIDIA H200'}}):
            with self.subTest(change=change), self.assertRaises(verify.VerificationError):
                verify.expected_result({**result, **change}, 'fixture-entity', '123', 'chat')
        with self.assertRaises(verify.VerificationError):
            verify.expected_result({**result, 'role': 'solver'}, 'fixture-entity', '123', 'solver')

    def inspect(self, blob, rank=8, maximum=4096):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.safetensors"
            path.write_bytes(blob)
            return verify.inspect_safetensors(path, rank, maximum)

    def failure(self, blob, code, **kwargs):
        with self.assertRaises(verify.VerificationError) as raised:
            self.inspect(blob, **kwargs)
        self.assertEqual(raised.exception.code, code)

    def test_zero_and_negative_zero_for_all_permitted_dtypes(self):
        for dtype, negative_zero in (("F32", 0x80000000), ("F16", 0x8000), ("BF16", 0x8000)):
            with self.subTest(dtype=dtype):
                row = self.inspect(adapter(dtype, [0, negative_zero] * 4))
                self.assertEqual(row["b_nonzero_elements"], 0)
                self.assertEqual(row["b_finite_elements"], 8)

    def test_subnormal_and_negative_nonzero_remain_nonzero(self):
        for dtype, sign in (("F32", 0x80000000), ("F16", 0x8000), ("BF16", 0x8000)):
            with self.subTest(dtype=dtype):
                row = self.inspect(adapter(dtype, [1, sign | 1] + [0] * 6))
                self.assertEqual(row["b_nonzero_elements"], 2)

    def test_nonfinite_at_end_cannot_hide_after_nonzero(self):
        for dtype, exponent in (("F32", 0x7F800000), ("F16", 0x7C00), ("BF16", 0x7F80)):
            for nonfinite in (exponent, exponent | 1):
                with self.subTest(dtype=dtype, nonfinite=nonfinite), patch.object(verify, "CHUNK", 4):
                    self.failure(adapter(dtype, [1] + [0] * 6 + [nonfinite]), "lora_b_nonfinite")

    def test_every_b_tensor_including_embedding_is_scanned(self):
        tensors = []
        for stem, bits in (("lora", [0] * 8), ("lora_embedding", [1] + [0] * 7)):
            tensors.extend([("base." + stem + "_A.weight", "BF16", [8, 1], [0] * 8),
                            ("base." + stem + "_B.weight", "BF16", [1, 8], bits)])
        row = self.inspect(container(tensors))
        self.assertEqual((row["b_tensor_count"], row["b_elements"], row["b_nonzero_elements"]), (2, 16, 1))

    def test_bad_header_prefix_length_duplicates_and_trailing_text(self):
        self.failure(b"short", "safetensors_size_limit")
        self.failure(struct.pack("<Q", verify.HEADER_LIMIT + 1) + b"{}", "safetensors_header_size_invalid",
                     maximum=verify.HEADER_LIMIT + 32)
        self.failure(struct.pack("<Q", 8) + b"{}      x", "tensor_layout_invalid")
        self.failure(struct.pack("<Q", 7) + b" {}    ", "safetensors_header_invalid")
        duplicate = b'{"x":{},"x":{}}'
        self.failure(struct.pack("<Q", len(duplicate)) + duplicate, "json_duplicate_key")
        self.failure(struct.pack("<Q", 5) + b"{} {}", "safetensors_header_invalid")

    def test_offsets_shapes_dtype_and_coverage_are_strict(self):
        base = {"x": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]}}
        mutations = [({"dtype": "I32", "shape": [1], "data_offsets": [0, 4]}, b"\0" * 4, "tensor_dtype_unsupported"),
                     ({"dtype": "F32", "shape": [True], "data_offsets": [0, 4]}, b"\0" * 4, "tensor_shape_invalid"),
                     ({"dtype": "F32", "shape": [2], "data_offsets": [0, 4]}, b"\0" * 4, "tensor_size_mismatch"),
                     ({"dtype": "F32", "shape": [1], "data_offsets": [-1, 3]}, b"\0" * 4, "tensor_offsets_invalid"),
                     ({"dtype": "F32", "shape": [1], "data_offsets": [0, 8]}, b"\0" * 4, "tensor_offsets_invalid"),
                     ({"dtype": "F32", "shape": [1], "data_offsets": [4, 8]}, b"\0" * 8, "tensor_layout_invalid")]
        for tensor, data, code in mutations:
            with self.subTest(code=code):
                self.failure(encoded({"x": tensor}, data), code)
        self.failure(encoded(base, b"\0" * 8), "tensor_layout_invalid")
        overlap = {**base, "y": base["x"]}
        self.failure(encoded(overlap, b"\0" * 4), "tensor_layout_invalid")
        self.failure(encoded(base, b"\0" * 4), "lora_b_missing")
        self.failure(adapter(), "safetensors_size_limit", maximum=16)

    def test_pair_rank_and_name_are_checked(self):
        self.failure(adapter(rank=16), "lora_pair_invalid", rank=8)
        self.failure(container([("not_lora_B.weight", "F32", [1, 8], [1] * 8)]), "lora_b_missing")
        self.failure(container([("base.lora_B.weight", "F32", [1, 8], [1] * 8)]), "lora_pair_invalid")

    def test_moe_three_dimensional_and_folded_expert_pairs(self):
        fused = container([("base.experts.lora_A.weight", "BF16", [2, 8, 1], [0] * 16),
                           ("base.experts.lora_B.weight", "BF16", [2, 1, 8], [1] + [0] * 15)])
        folded = container([("base.experts.lora_A.weight", "BF16", [16, 1], [0] * 16),
                            ("base.experts.lora_B.weight", "BF16", [1, 16], [1] + [0] * 15)])
        for model in (fused, folded):
            with self.subTest(layout=model[:8]):
                row = self.inspect(model)
                self.assertEqual(row["b_nonzero_elements"], 1)
                self.assertTrue(row["pair_shapes_supported"])
                self.assertTrue(Fixture(model=model).run()["all_verified"])

    def test_unknown_moe_shape_is_unverifiable_but_payload_is_still_scanned(self):
        unknown = container([("base.experts.lora_A.weight", "BF16", [2, 8, 1], [0] * 16),
                             ("base.experts.lora_B.weight", "BF16", [2, 8, 1], [1] + [0] * 15)])
        row = Fixture(model=unknown).run()["roles"][0]
        self.assertEqual((row["status"], row["code"], row["b_nonzero_elements"]),
                         ("unverifiable", "lora_pair_shape_unsupported", 1))


class PrivateReaderTests(unittest.TestCase):
    def test_verified_checkpoint_and_only_allowlisted_files(self):
        fixture = Fixture()
        event = fixture.run()
        row = event["roles"][0]
        self.assertTrue(event["all_verified"])
        self.assertFalse(event["quality_verified"])
        self.assertEqual(row["b_nonzero_elements"], 1)
        self.assertTrue(row["weights_updated"])
        self.assertEqual(fixture.downloads, list(verify.FILES))
        self.assertGreaterEqual(fixture.checks, 5)
        self.assertNotIn("sha256", json.dumps(event))

    def test_zero_checkpoint_fails_and_defaults_gaussian_are_supported(self):
        row = Fixture(model=adapter()).run()["roles"][0]
        self.assertEqual((row["status"], row["code"], row["weights_updated"]),
                         ("failed", "lora_b_all_zero", False))
        for initializer in (None, "gaussian"):
            with self.subTest(initializer=initializer):
                self.assertTrue(Fixture(initializer=initializer).run()["all_verified"])

    def test_other_initializers_are_unverifiable_even_with_nonzero_b(self):
        for initializer in (False, "true", "pissa", "olora", 1):
            with self.subTest(initializer=initializer):
                row = Fixture(initializer=initializer).run()["roles"][0]
                self.assertEqual(row["status"], "unverifiable")
                self.assertFalse(row["weights_updated"])

    def test_embedding_b_nonzero_is_not_training_evidence(self):
        model = adapter(bits=[1] * 8, embedding=True)
        row = Fixture(model=model).run()["roles"][0]
        self.assertEqual(row["b_nonzero_elements"], 8)
        self.assertEqual(row["standard_b_nonzero_elements"], 0)
        self.assertEqual(row["status"], "unverifiable")
        self.assertFalse(row["weights_updated"])

    def test_solver_only_or_ordered_roles_and_missing_checkpoint(self):
        fixture = Fixture("solver")
        fixture.add_role("chat")
        event = fixture.run("solver,chat")
        self.assertTrue(event["all_verified"])
        self.assertEqual([row["role"] for row in event["roles"]], ["solver", "chat"])
        missing = Fixture().run("solver")["roles"][0]
        self.assertEqual((missing["status"], missing["code"]), ("pending", "checkpoint_pending"))

    def test_privacy_denial_precedes_sdk_and_later_gate_precedes_download(self):
        fixture = Fixture()
        fixture.fail_private_at = 1
        called = []
        with self.assertRaises(verify.VerificationError):
            fixture.run(sdk_factory=lambda key: called.append(key))
        self.assertEqual(called, [])
        self.assertEqual(fixture.downloads, [])
        fixture = Fixture()
        fixture.fail_private_at = 4
        row = fixture.run()["roles"][0]
        self.assertEqual(row["code"], "private_project_required")
        self.assertEqual(fixture.downloads, [verify.FILES[0]])

    def test_immutable_same_scope_and_role_refs_required(self):
        for bad in ("fixture-entity/other/hasla-private-books-123-chat-lora:v0",
                    f"fixture-entity/{verify.PROJECT}/hasla-private-books-123-chat-lora:latest",
                    f"fixture-entity/{verify.PROJECT}/hasla-private-books-123-solver-lora:v0",
                    f"other/{verify.PROJECT}/hasla-private-books-123-chat-lora:v0"):
            fixture = Fixture()
            fixture.results["chat"]["artifact"] = bad
            self.assertEqual(fixture.run()["roles"][0]["code"], "artifact_reference_invalid")
            self.assertEqual(fixture.downloads, [])

    def test_provenance_sizes_hashes_and_metadata_are_checked(self):
        fixture = Fixture()
        fixture.results["chat"]["adapter_sha256"] = "0" * 64
        self.assertEqual(fixture.run()["roles"][0]["code"], "result_inventory_hash_mismatch")
        fixture = Fixture()
        artifact = next(iter(fixture.artifacts.values()))
        artifact.metadata["steps_completed"] = 0
        self.assertEqual(fixture.run()["roles"][0]["code"], "artifact_metadata_mismatch")
        fixture = Fixture()
        artifact = next(iter(fixture.artifacts.values()))
        artifact.manifest.entries[verify.FILES[1]].data += b"x"
        self.assertEqual(fixture.run()["roles"][0]["code"], "downloaded_file_invalid")
        fixture = Fixture()
        artifact = next(iter(fixture.artifacts.values()))
        entry = artifact.manifest.entries[verify.FILES[1]]
        entry.data = entry.data[:-1] + bytes([entry.data[-1] ^ 1])
        self.assertEqual(fixture.run()["roles"][0]["code"], "downloaded_file_hash_mismatch")
        fixture = Fixture()
        next(iter(fixture.artifacts.values())).manifest.entries[verify.FILES[0]].ref = "https://private.invalid"
        self.assertEqual(fixture.run()["roles"][0]["code"], "artifact_entry_invalid")
        self.assertEqual(fixture.downloads, [])

    def test_result_and_config_roles_base_rank_steps_are_strict(self):
        for key, bad, code in (("role", "solver", "result_role_or_base_mismatch"),
                              ("base_model", "unknown", "result_role_or_base_mismatch"),
                              ("rank", True, "result_rank_mismatch"),
                              ("steps_completed", 0, "result_steps_invalid")):
            fixture = Fixture()
            fixture.results["chat"][key] = bad
            self.assertEqual(fixture.run()["roles"][0]["code"], code)
            self.assertEqual(fixture.downloads, [])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "adapter_config.json"
            for changes, code in (({"peft_type": "OTHER"}, "adapter_type_invalid"),
                                  ({"r": 16}, "adapter_rank_mismatch"),
                                  ({"base_model_name_or_path": "unknown"}, "adapter_base_mismatch")):
                config = {"peft_type": "LORA", "r": 8,
                          "base_model_name_or_path": verify.get_role_config("chat")["base_model"], **changes}
                path.write_text(json.dumps(config))
                with self.assertRaises(verify.VerificationError) as raised:
                    verify.config_check(path, "chat", 8)
                self.assertEqual(raised.exception.code, code)

    def test_sdk_output_and_upstream_exception_are_never_exposed(self):
        fixture = Fixture()
        secret = "PRIVATE-URL-TENSOR-SECRET"
        def sdk(key):
            print(secret)
            print(secret, file=verify.sys.stderr)
            class Failing:
                def artifact(self, *args, **kwargs):
                    raise RuntimeError(secret)
            return Failing()
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            event = fixture.run(sdk_factory=sdk)
        self.assertEqual(stdout.getvalue() + stderr.getvalue(), "")
        self.assertNotIn(secret, json.dumps(event))
        self.assertEqual(event["roles"][0]["code"], "private_reader_failed")

    def test_scalar_nested_and_flat_summaries(self):
        result = Fixture().results["chat"]
        variants = [{"private_training_result_json": json.dumps(result)},
                    {"private_training_result": result},
                    {"private_training_result": json.dumps(json.dumps(result))}]
        variants.extend({"private_training_result" + separator + key: value for key, value in result.items()}
                        for separator in (".", "/"))
        for summary in variants:
            with self.subTest(summary_type=list(summary)[0]):
                self.assertEqual(verify.summary_result(json.dumps(summary)), result)
        self.assertIsNone(verify.summary_result("not JSON"))

    def test_arguments_credentials_and_safe_cli_errors(self):
        for run_id in ("123/x", "１２３", "", "1" * 33):
            with self.assertRaises(verify.VerificationError):
                verify.validate_arguments(run_id, "chat")
        for roles in ("chat,chat", "fast", "chat,solver,chat", "chat, solver"):
            with self.assertRaises(verify.VerificationError):
                verify.validate_arguments("123", roles)
        for name in ("RUNPOD_API_KEY", "RUNPOD_TOKEN", "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
            with self.subTest(name=name), self.assertRaises(verify.VerificationError):
                verify.credentials({"WANDB_API_KEY": "fixture", name: "never-print"})
        with self.assertRaises(verify.VerificationError):
            verify.credentials({"WANDB_API_KEY": "fixture", "WANDB_BASE_URL": "https://other.invalid"})
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = verify.main(["--run-id", "secret-should-not-appear", "--roles", "chat"])
        event = json.loads(stream.getvalue())
        self.assertEqual((code, event["event"], event["code"]), (1, "private_adapter_verification", "run_id_invalid"))
        self.assertNotIn("secret-should-not-appear", stream.getvalue())

    def test_pending_cli_exit_and_readonly_privacy_response(self):
        pending = {"event": "private_adapter_verification", "all_verified": False,
                   "roles": [{"status": "pending"}]}
        with patch.object(verify, "verify", return_value=pending), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(verify.main(["--run-id", "123"]), 2)
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return json.dumps({"data": {"project": {"name": verify.PROJECT,
                                                                             "access": "PUBLIC"}}}).encode()
        class Opener:
            def open(self, request, timeout): return Response()
        with self.assertRaises(verify.VerificationError) as raised:
            verify.PrivateReader("fixture", opener=Opener()).assert_private("fixture-entity")
        self.assertEqual(raised.exception.code, "private_project_required")


if __name__ == "__main__":
    unittest.main()

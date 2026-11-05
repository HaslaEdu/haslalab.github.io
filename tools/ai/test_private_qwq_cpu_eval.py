import argparse
import copy
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import private_qwq_comparison as comparison
import private_qwq_cpu_eval as worker
from test_private_qwq_comparison import IDENTITY, bundle, good_generation


class FakeServer:
    def __init__(self, action=None):
        self.calls = []
        self.action = action

    def request(self, endpoint, timeout, payload=None):
        self.calls.append((endpoint, timeout, copy.deepcopy(payload)))
        if self.action:
            return self.action(len(self.calls) - 1)
        case = comparison.cases()[(len(self.calls) - 1) // 2]
        return {"content": good_generation(case)["generated_text"], "tokens": [1] * 70,
                "stop_type": "eos", "truncated": False}


class CpuEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.plan = comparison.build_plan(worker.ADAPTER_MODEL_SHA, worker.ADAPTER_CONFIG_SHA)

    def test_exact_model_and_adapter_pins_no_automatic_quant_fallback(self):
        self.assertEqual(worker.MODEL_FILES["iq3_xxs"]["bytes"], 13052652128)
        self.assertEqual(worker.MODEL_FILES["iq2_xxs"]["bytes"], 9336801888)
        self.assertEqual(len(worker.ADAPTER_MODEL_SHA), 64)
        with self.assertRaisesRegex(worker.EvaluationError, "insufficient_cpu_ram"):
            worker.validate_resources("iq3_xxs", {"MemTotal": 16 * worker.GIB,
                                                  "MemAvailable": 13 * worker.GIB}, 20 * worker.GIB)
        worker.validate_resources("iq2_xxs", {"MemTotal": 16 * worker.GIB,
                                               "MemAvailable": 13 * worker.GIB}, 20 * worker.GIB)
        with self.assertRaisesRegex(worker.EvaluationError, "quant_not_allowlisted"):
            worker.validate_resources("smaller-model", {}, 20 * worker.GIB)

    def test_cpu_memory_and_disk_boundaries(self):
        memory = {"MemTotal": 15 * worker.GIB, "MemAvailable": 14 * worker.GIB}
        worker.validate_resources("iq3_xxs", memory, 2 * worker.GIB)
        for values, disk in (({**memory, "MemTotal": 15 * worker.GIB - 1}, 2 * worker.GIB),
                             ({**memory, "MemAvailable": 14 * worker.GIB - 1}, 2 * worker.GIB),
                             (memory, 2 * worker.GIB - 1)):
            with self.assertRaises(worker.EvaluationError):
                worker.validate_resources("iq3_xxs", values, disk)

    def test_child_environment_has_no_provider_secrets_or_llama_overrides(self):
        with patch.dict("os.environ", {"PATH": "/bin", "WANDB_API_KEY": "SECRET",
                                      "RUNPOD_API_KEY": "SECRET", "HF_TOKEN": "SECRET",
                                      "LLAMA_ARG_N_GPU_LAYERS": "99", "CUDA_VISIBLE_DEVICES": "0"}, clear=True):
            environment = worker.child_environment()
        self.assertEqual(environment["PATH"], "/bin")
        self.assertEqual(environment["CUDA_VISIBLE_DEVICES"], "")
        self.assertEqual(environment["HF_HUB_OFFLINE"], "1")
        self.assertFalse(any("SECRET" in value for value in environment.values()))
        self.assertNotIn("LLAMA_ARG_N_GPU_LAYERS", environment)

    def test_converter_uses_local_base_f32_and_no_remote_base_or_merge(self):
        args = argparse.Namespace(llama_dir=Path("/llama"), base_config_dir=Path("/base"),
                                  adapter_dir=Path("/original-adapter"))
        command = worker.converter_command(args, Path("/new/adapter.gguf"))
        self.assertEqual(command[command.index("--outtype") + 1], "f32")
        self.assertEqual(command[command.index("--base") + 1], str(Path("/base")))
        self.assertNotIn("--base-model-id", command)
        self.assertEqual(command[-1], str(Path("/original-adapter")))

    def test_converted_adapter_requires_all_source_pairs_exact_f32_finite_shapes(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "adapter.gguf"
            path.write_bytes(b"GGUF" + b"0" * 16)
            def tensors():
                rows = []
                for index in range(worker.ADAPTER_PAIRS):
                    for suffix, shape in (("a", (16, 2)), ("b", (2, 16))):
                        rows.append(SimpleNamespace(name=f"blk.{index}.attn_q.weight.lora_{suffix}",
                                                    tensor_type=0, data=np.ones(shape, dtype=np.float32)))
                return rows
            rows = tensors()
            module = SimpleNamespace(GGUFReader=lambda _: SimpleNamespace(tensors=rows))
            with patch.dict("sys.modules", {"gguf": module}):
                evidence = worker.verify_converted_adapter(path, root)
            self.assertEqual(evidence["tensor_count"], 896)
            self.assertEqual(evidence["pair_count"], 448)
            self.assertTrue(evidence["all_tensors_finite"])
            for kind in ("dropped_pair", "unmatched_prefix", "nan", "wrong_dtype", "wrong_rank"):
                rows = tensors()
                if kind == "dropped_pair": rows = rows[:-2]
                elif kind == "unmatched_prefix": rows[1].name = "other.weight.lora_b"
                elif kind == "nan": rows[1].data[0, 0] = np.nan
                elif kind == "wrong_dtype": rows[0].tensor_type = 1
                else: rows[0].data = np.ones((15, 2), dtype=np.float32)
                module = SimpleNamespace(GGUFReader=lambda _: SimpleNamespace(tensors=rows))
                with self.subTest(kind=kind), patch.dict("sys.modules", {"gguf": module}), \
                        self.assertRaises(worker.EvaluationError):
                    worker.verify_converted_adapter(path, root)

    def test_server_is_cpu_loopback_single_slot_disabled_adapter_no_prompt_logs(self):
        args = argparse.Namespace(server_binary=Path("/llama/build/bin/llama-server"),
                                  model_path=Path("/base.gguf"), context=2048, threads=4)
        command = worker.server_command(args, Path("/adapter.gguf"), 8080)
        for flag, value in (("--host", "127.0.0.1"), ("--parallel", "1"),
                            ("--n-gpu-layers", "0"), ("--ctx-size", "2048")):
            self.assertEqual(command[command.index(flag) + 1], value)
        for flag in ("--lora-init-without-apply", "--log-disable", "--no-webui", "--no-context-shift"):
            self.assertIn(flag, command)
        self.assertNotIn("--log-prompts-dir", command)

    def test_pair_payloads_change_only_lora_scale(self):
        base, adapted = worker.request_payload("same prompt", "base"), worker.request_payload("same prompt", "adapted")
        self.assertEqual(base.pop("lora"), [{"id": 0, "scale": 0}])
        self.assertEqual(adapted.pop("lora"), [{"id": 0, "scale": 1}])
        self.assertEqual(base, adapted)
        self.assertFalse(base["cache_prompt"])
        self.assertEqual(base["temperature"], 0)
        self.assertEqual(base["n_predict"], 1024)
        self.assertEqual(base["seed"], 20261105)

    def test_fixed_eight_pair_order_and_same_one_server(self):
        server = FakeServer()
        base, adapted = worker.run_pairs(self.plan, IDENTITY, ["p" + str(i) for i in range(8)],
                                         server, 10000, clock=lambda: 0)
        self.assertEqual(len(server.calls), 16)
        self.assertEqual([call[2]["lora"][0]["scale"] for call in server.calls], [0, 1] * 8)
        self.assertEqual([call[2]["prompt"] for call in server.calls],
                         ["p" + str(i) for i in range(8) for _ in range(2)])
        report = comparison.score_comparison(self.plan, base, adapted)
        self.assertEqual(report["paired_completed_cases"], 8)
        self.assertTrue(report["coverage_complete"])
        self.assertEqual(report["results"]["base"]["paired_passed_cases"], 8)

    def test_deadline_reports_prefix_pair_coverage_without_cherry_picking(self):
        times = iter([0, 0, 0, 96])
        server = FakeServer()
        base, adapted = worker.run_pairs(self.plan, IDENTITY, ["prompt"] * 8,
                                         server, 100, clock=lambda: next(times))
        report = comparison.score_comparison(self.plan, base, adapted)
        self.assertEqual(len(server.calls), 3)
        self.assertEqual(report["paired_completed_cases"], 1)
        self.assertEqual(report["paired_case_ids"], ["momentum_energy"])
        self.assertFalse(report["coverage_complete"])
        self.assertEqual(report["results"]["base"]["paired_passed_cases"], 1)
        self.assertEqual(report["results"]["adapted"]["paired_passed_cases"], 1)
        self.assertEqual(report["results"]["adapted"]["failures"]["not_run"], 7)

    def test_timeout_stops_more_requests_and_partial_reasoning_is_not_reported(self):
        def action(index):
            if index == 1:
                raise TimeoutError()
            return {"content": good_generation(comparison.cases()[0])["generated_text"],
                    "tokens": [1] * 70, "stop_type": "eos", "truncated": False}
        server = FakeServer(action)
        base, adapted = worker.run_pairs(self.plan, IDENTITY, ["prompt"] * 8, server, 10000, clock=lambda: 0)
        report = comparison.score_comparison(self.plan, base, adapted)
        self.assertEqual(len(server.calls), 2)
        self.assertEqual(report["paired_completed_cases"], 0)
        self.assertEqual(report["results"]["adapted"]["failures"]["timeout"], 1)
        self.assertNotIn("PRIVATE_HIDDEN_REASONING", json.dumps(report))

    def test_limit_and_context_truncation_are_failed_attempts_not_silent_success(self):
        for response in ({"content": "</think>{}", "tokens": [1], "stop_type": "limit"},
                         {"content": "</think>{}", "tokens": [1], "stop_type": "eos", "truncated": True}):
            self.assertEqual(worker.normalize_completion(response)["finish_reason"], "length")
        self.assertEqual(worker.normalize_completion({"content": "x", "tokens": [1],
                                                      "stop_type": "none"})["finish_reason"], "error")

    def test_redirects_and_remote_or_unknown_endpoints_rejected(self):
        server = worker.LocalServer(8080)
        self.assertEqual(server.url, "http://127.0.0.1:8080")
        with self.assertRaises(worker.EvaluationError):
            server.request("https://external.invalid/", 1)
        with self.assertRaises(worker.EvaluationError):
            worker.NoRedirect().redirect_request(None, None, None, None, None, None)

    def test_scoped_server_cleanup_terminates_then_kills_only_owned_process(self):
        class Process:
            def __init__(self): self.events = []; self.alive = True
            def poll(self): return None if self.alive else 0
            def terminate(self): self.events.append("terminate")
            def wait(self, timeout):
                self.events.append(("wait", timeout))
                if self.alive: raise subprocess.TimeoutExpired("synthetic", timeout)
            def kill(self): self.events.append("kill"); self.alive = False
        process = Process()
        worker.stop_process(process)
        self.assertEqual(process.events, ["terminate", ("wait", 15), "kill", ("wait", 10)])
        self.assertEqual(process.poll(), 0)

    def test_final_only_validator_rejects_thinking_and_unknown_extra_fields(self):
        # Use fixture pins for its matching result bundle, then validate report only.
        fixture_plan = comparison.build_plan("c" * 64, "f" * 64)
        report = comparison.score_comparison(fixture_plan, bundle(fixture_plan, "base"),
                                             bundle(fixture_plan, "adapted"))
        comparison.validate_final_only_report(report)
        for mutation in ("root_extra", "case_extra", "thinking"):
            changed = copy.deepcopy(report)
            if mutation == "root_extra": changed["raw_thinking"] = "SECRET"
            elif mutation == "case_extra": changed["results"]["base"]["cases"][0]["reasoning"] = "SECRET"
            else: changed["results"]["base"]["cases"][0]["final_answer"] = "<think>SECRET</think>answer"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                comparison.validate_final_only_report(changed)

    def test_prepared_contract_projects_only_absolute_paths_and_quant(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepared = {"adapter_dir": str(root / "adapter"), "base_gguf_path": str(root / "model"),
                        "base_config_dir": str(root / "base"), "llama_cpp_dir": str(root / "llama"),
                        "llama_server_path": str(root / "llama" / "server"),
                        "tokenizer_config_path": str(root / "base" / "tokenizer_config.json"),
                        "quant": "iq3_xxs"}
            (root / "prepared.json").write_text(json.dumps(prepared))
            with patch.object(worker, "execute", return_value={
                "status": "completed", "gpu_count": 0, "provider_created": False,
                "server_process_stopped": True, "elapsed_seconds": 1}) as execute, patch("builtins.print"):
                self.assertEqual(worker.main(["--prepared-dir", str(root), "--output-dir", str(root / "result")]), 0)
                args = execute.call_args.args[0]
                self.assertEqual(args.model_path, root / "model")
                self.assertEqual(args.quant, "iq3_xxs")
                self.assertEqual(worker.main(["--prepared-dir", str(root), "--output-dir", str(root / "other"),
                                              "--quant", "iq2_xxs"]), 1)
                self.assertEqual(execute.call_count, 1)

    def test_failure_before_model_execution_writes_safe_report_and_no_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = argparse.Namespace(work_dir=Path(temporary) / "result", max_wall_seconds=9000,
                                      threads=4, context=2048, quant="iq3_xxs")
            with patch.object(worker, "memory_status", return_value={"MemTotal": 1, "MemAvailable": 1}), \
                    patch.object(worker.subprocess, "Popen") as process:
                metadata = worker.execute(args)
            self.assertEqual(metadata["failure_code"], "insufficient_cpu_ram")
            self.assertEqual(metadata["gpu_count"], 0)
            self.assertTrue(metadata["server_process_stopped"])
            self.assertEqual(process.call_count, 0)
            self.assertEqual(worker.validate_upload_bundle(args.work_dir),
                             [args.work_dir / "report.json", args.work_dir / "metadata.json"])

    def test_whole_execute_conversion_single_server_scoring_and_private_upload_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / "llama-server"
            binary.write_bytes(b"synthetic-not-an-executable")
            tokenizer = root / "tokenizer_config.json"
            tokenizer.write_text('{"chat_template":"synthetic"}')
            args = argparse.Namespace(work_dir=root / "result", max_wall_seconds=9000,
                                      threads=4, context=2048, quant="iq3_xxs",
                                      model_path=root / "model.gguf", adapter_dir=root / "adapter",
                                      tokenizer_config=tokenizer, base_config_dir=root / "base",
                                      llama_dir=root / "llama", server_binary=binary)
            class Process:
                alive = True
                def poll(self): return None if self.alive else 0
                def terminate(self): self.alive = False
                def wait(self, timeout): return 0
            process = Process()
            completion_server = FakeServer()
            class Server:
                def __init__(self, port): self.port = port
                def request(self, endpoint, timeout, payload=None):
                    if endpoint == "/health": return {"status": "ok"}
                    if endpoint == "/lora-adapters":
                        return [{"id": 0, "scale": 0, "path": str(args.work_dir / "adapter-f32.gguf")}]
                    if endpoint == "/tokenize": return {"tokens": [1] * 300}
                    return completion_server.request(endpoint, timeout, payload)
            with patch.object(worker, "memory_status", return_value={"MemTotal": 16 * worker.GIB,
                                                                      "MemAvailable": 15 * worker.GIB}), \
                    patch.object(worker, "pinned_file") as pinned, \
                    patch.object(worker, "validate_adapter") as adapter_check, \
                    patch.object(worker, "validate_source") as source_check, \
                    patch.object(worker, "render_prompt", side_effect=lambda messages, _: str(messages)), \
                    patch.object(worker.subprocess, "run", return_value=argparse.Namespace(returncode=0)) as conversion, \
                    patch.object(worker, "verify_converted_adapter", return_value={"sha256": "e" * 64,
                        "bytes": 512, "tensor_count": 896, "pair_count": 448,
                        "all_tensors_f32": True, "all_tensors_finite": True}), \
                    patch.object(worker.subprocess, "Popen", return_value=process) as launch, \
                    patch.object(worker, "LocalServer", Server), patch("builtins.print"):
                metadata = worker.execute(args)
            self.assertEqual(metadata["status"], "completed")
            self.assertEqual(metadata["paired_completed_cases"], 8)
            self.assertTrue(metadata["server_process_stopped"])
            self.assertFalse(process.alive)
            self.assertEqual(conversion.call_count, 1)
            self.assertEqual(launch.call_count, 1)
            self.assertEqual(adapter_check.call_count, 2)
            self.assertEqual(source_check.call_count, 1)
            self.assertEqual(pinned.call_count, 3)
            self.assertEqual(len(completion_server.calls), 16)
            self.assertEqual(conversion.call_args.kwargs["stdout"], subprocess.DEVNULL)
            self.assertEqual(launch.call_args.kwargs["stderr"], subprocess.DEVNULL)
            self.assertEqual(worker.validate_upload_bundle(args.work_dir),
                             [args.work_dir / "report.json", args.work_dir / "metadata.json"])
            saved = (args.work_dir / "report.json").read_text()
            self.assertNotIn("PRIVATE_HIDDEN_REASONING", saved)
            self.assertFalse(any(path.name in {"base-results.json", "adapted-results.json"}
                                 for path in args.work_dir.iterdir()))


if __name__ == "__main__":
    unittest.main()

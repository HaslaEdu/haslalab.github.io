"""Synthetic CPU tests only. No model, credential, download or provider calls."""
from contextlib import contextmanager, nullcontext, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import private_qwq_gpu_eval as gpu


def job():
    return {"version": 1, "kind": "private_qwq_gpu_evaluation_job", "run_id": "123456789",
        "code_commit": "a" * 40, "runtime_seconds": 2700, "deadline_unix": int(time.time()) + 3300,
        "base_model": gpu.FOUNDATION, "rank": 16,
        "source_adapter": deepcopy(gpu.SOURCE), "optimizer_steps": 0,
        "script_sha256": {name: gpu.file_sha(Path(gpu.__file__).with_name(name)) for name in gpu.SCRIPT_FILES}}


def good_generation(case):
    expected = case["expected"]
    answer = {"values": {key: value["value"] for key, value in expected.items()},
              "units": {key: value["unit"] for key, value in expected.items()}} if case["kind"] == "numeric" else expected
    return {"generated_text": "HIDDEN_REASONING_DO_NOT_SAVE</think>" + json.dumps(answer),
            "completion_tokens": 80, "finish_reason": "stop", "thinking_format": "qwq_open_think"}


class FakeWeight:
    def __init__(self, shape):
        self.requires_grad = False
        self.device = SimpleNamespace(type="cuda", index=0)
        self.quant_state = SimpleNamespace(shape=shape, quant_type="nf4", nested=True, state2=object())
        self.shape = shape
    def numel(self): return self.shape[0] * self.shape[1] // 2
    def element_size(self): return 1
    def requires_grad_(self, value): self.requires_grad = value; return self


class FakeModel:
    def __init__(self):
        self.config = SimpleNamespace(model_type="qwen2", num_hidden_layers=64, hidden_size=5120,
            intermediate_size=27648, num_attention_heads=40, num_key_value_heads=8, _commit_hash=gpu.REVISION)
        self.hf_device_map = {"": 0}
        self.rows = []
        shapes = {"self_attn.q_proj": (5120, 5120), "self_attn.k_proj": (1024, 5120),
                  "self_attn.v_proj": (1024, 5120), "self_attn.o_proj": (5120, 5120),
                  "mlp.gate_proj": (27648, 5120), "mlp.up_proj": (27648, 5120), "mlp.down_proj": (5120, 27648)}
        for layer in range(64):
            for name, shape in shapes.items():
                self.rows.append((f"model.layers.{layer}.{name}", SimpleNamespace(weight=FakeWeight(shape),
                    compute_dtype="bf16", lora_A={"default": object()}, lora_B={"default": object()},
                    disable_adapters=False, merged=False, merged_adapters=[])))
        self.generation_config = SimpleNamespace(eos_token_id=[151645, 151643])
    def named_modules(self): return iter(self.rows)
    def modules(self): return [module for _, module in self.rows]
    def parameters(self): return [module.weight for _, module in self.rows]
    def eval(self): return self
    @contextmanager
    def disable_adapter(self):
        for module in self.modules(): module.disable_adapters = True
        try: yield
        finally:
            for module in self.modules(): module.disable_adapters = False


def fake_torch(model=None):
    cuda = SimpleNamespace(is_available=lambda: True, device_count=lambda: 1,
        get_device_properties=lambda index: SimpleNamespace(name="NVIDIA A40", total_memory=45 * gpu.GIB),
        reset_peak_memory_stats=Mock(), max_memory_allocated=lambda index: 20 * gpu.GIB,
        max_memory_reserved=lambda index: 24 * gpu.GIB, synchronize=Mock(), empty_cache=Mock(), manual_seed_all=Mock())
    return SimpleNamespace(cuda=cuda, version=SimpleNamespace(cuda="12.8"), bfloat16="bf16", bool="bool", manual_seed=Mock(),
                           inference_mode=lambda: nullcontext(), full=lambda shape, value, **kwargs: [value] * shape[0])


class FakePeftOuter:
    """PEFT shape: weight delegates; compute_dtype belongs to base_layer only."""
    def __init__(self, base):
        self.base_layer = SimpleNamespace(weight=base.weight, compute_dtype=base.compute_dtype)
        self.lora_A, self.lora_B = base.lora_A, base.lora_B
        self.disable_adapters, self.merged, self.merged_adapters = False, False, []
    @property
    def weight(self): return self.base_layer.weight
    def get_base_layer(self): return self.base_layer


class GpuEvaluationTests(unittest.TestCase):
    def test_versioned_plan_preserves_cpu_global_settings_and_all_eight_case_hashes(self):
        import private_qwq_comparison as cpu
        before = deepcopy(cpu.SETTINGS)
        plan = gpu.evaluation_plan()
        self.assertEqual(cpu.SETTINGS, before)
        self.assertEqual(before["max_new_tokens"], 1024)
        self.assertEqual(plan["version"], 2)
        self.assertEqual(plan["comparison"]["generation_settings"]["max_new_tokens"], 2048)
        self.assertEqual(plan["context"], 4096)
        self.assertEqual(plan["comparison"]["case_set_sha256"], gpu.CASE_SHA)
        self.assertEqual(plan["comparison"]["case_set_sha256"], cpu.build_plan()["case_set_sha256"])
        self.assertEqual(plan["comparison"]["max_total_generated_tokens"], 32768)
        self.assertEqual(gpu.digest(gpu.canonical(plan)), "b22d2a1430b009930331d16933b76db30c2807a09cbea77d359bc6a9c27c8c24")

    def test_job_fixed_cohort_script_closure_and_runtime_boundaries(self):
        original = job()
        self.assertEqual(gpu.validate_job(original), original)
        for field, value in (("runtime_seconds", 2701), ("runtime_seconds", True), ("rank", 8),
                             ("base_model", "other"), ("optimizer_steps", 1), ("run_id", "001")):
            changed = deepcopy(original); changed[field] = value
            with self.subTest(field=field), self.assertRaises(gpu.EvaluationError): gpu.validate_job(changed)
        for changed in ({**original, "unexpected": "data"}, {**original, "source_adapter": {}},
                        {**original, "script_sha256": {**original["script_sha256"], "role_config.py": "0" * 64}}):
            with self.assertRaises(gpu.EvaluationError): gpu.validate_job(changed)

    def test_absolute_deadline_expired_too_far_and_too_little_headroom_rejected(self):
        value = job()
        for deadline in (999, 1119, 4601, True, "4300"):
            changed = deepcopy(value); changed["deadline_unix"] = deadline
            with self.subTest(deadline=deadline), self.assertRaises(gpu.EvaluationError):
                gpu.validate_job(changed, now=1000)
        value["deadline_unix"] = 4300
        gpu.validate_job(value, now=1000)

    def test_only_one_40_or_48gb_cuda_gpu_no_offload_no_trainable_base(self):
        torch, model = fake_torch(), FakeModel()
        self.assertEqual(gpu.gpu_proof(torch, model)["gpu_count"], 1)
        for count, name, memory in ((2, "NVIDIA A40", 45 * gpu.GIB), (1, "NVIDIA H100", 80 * gpu.GIB),
                                    (1, "NVIDIA A100-PCIE-40GB", 40 * gpu.GIB),
                                    (1, "NVIDIA A40", 24 * gpu.GIB)):
            torch = fake_torch(); torch.cuda.device_count = lambda: count
            torch.cuda.get_device_properties = lambda index: SimpleNamespace(name=name, total_memory=memory)
            with self.assertRaises(gpu.EvaluationError): gpu.gpu_proof(torch)
        model.hf_device_map = {"layer": "cpu"}
        with self.assertRaises(gpu.EvaluationError): gpu.gpu_proof(fake_torch(), model)
        model.hf_device_map = {"": 0}; model.rows[0][1].weight.requires_grad = True
        with self.assertRaises(gpu.EvaluationError): gpu.gpu_proof(fake_torch(), model)

    def test_actual_all_448_nf4_double_quant_bf16_frozen_projection_proof(self):
        model = FakeModel()
        proof, retained = gpu.nf4_proof(model, FakeWeight, "bf16")
        self.assertEqual(proof["quantized_linear_tensors"], 448)
        self.assertTrue(proof["double_quant"])
        gpu.nf4_proof(model, FakeWeight, "bf16", retained)
        for kind in ("missing", "fp4", "not_nested", "compute_fp16", "cpu", "trainable", "replaced"):
            changed = FakeModel()
            if kind == "missing": changed.rows.pop()
            elif kind == "fp4": changed.rows[0][1].weight.quant_state.quant_type = "fp4"
            elif kind == "not_nested": changed.rows[0][1].weight.quant_state.nested = False
            elif kind == "compute_fp16": changed.rows[0][1].compute_dtype = "fp16"
            elif kind == "cpu": changed.rows[0][1].weight.device.type = "cpu"
            elif kind == "trainable": changed.rows[0][1].weight.requires_grad = True
            with self.subTest(kind=kind), self.assertRaises(gpu.EvaluationError):
                gpu.nf4_proof(changed, FakeWeight, "bf16", retained if kind == "replaced" else None)

    def test_adapter_disable_context_unmerged_and_exact_count(self):
        model = FakeModel()
        gpu.adapter_state(model, False)
        with model.disable_adapter(): gpu.adapter_state(model, True)
        gpu.adapter_state(model, False)
        model.rows[0][1].merged = True
        with self.assertRaises(gpu.EvaluationError): gpu.adapter_state(model, False)

    def test_peft_wrapper_base_compute_dtype_and_same_weight_identity(self):
        model = FakeModel()
        _, retained = gpu.nf4_proof(model, FakeWeight, "bf16")
        model.rows = [(name, FakePeftOuter(base)) for name, base in model.rows]
        self.assertFalse(hasattr(model.rows[0][1], "compute_dtype"))
        gpu.nf4_proof(model, FakeWeight, "bf16", retained)
        model.rows[0][1].base_layer.compute_dtype = "fp16"
        with self.assertRaises(gpu.EvaluationError): gpu.nf4_proof(model, FakeWeight, "bf16", retained)
        model.rows[0][1].base_layer.compute_dtype = "bf16"
        model.rows[0][1].get_base_layer = lambda: SimpleNamespace(
            weight=FakeWeight((5120, 5120)), compute_dtype="bf16")
        with self.assertRaises(gpu.EvaluationError): gpu.nf4_proof(model, FakeWeight, "bf16", retained)

    def test_loader_exact_foundation_revision_explicit_quant_configuration(self):
        marker = object(); options = gpu.loader_options(fake_torch(), marker)
        self.assertEqual(options["model_name"], "Qwen/QwQ-32B")
        self.assertEqual(options["revision"], gpu.REVISION)
        self.assertIs(options["quantization_config"], marker)
        self.assertTrue(options["use_exact_model_name"])
        self.assertFalse(options["fast_inference"])
        self.assertFalse(options["offload_embedding"])
        self.assertFalse(options["token"])
        self.assertEqual(options["device_map"], {"": 0})

    def test_runtime_versions_complete_safe_observations_not_invented_pins(self):
        with patch.object(gpu.importlib.metadata, "version", side_effect=lambda name: "1.2.3+fixture"):
            values = gpu.package_versions(fake_torch())
        self.assertEqual(len(values), 10)
        self.assertEqual(values["cuda_runtime"], "12.8")
        with patch.object(gpu.importlib.metadata, "version", return_value="unsafe secret value"):
            with self.assertRaises(gpu.EvaluationError): gpu.package_versions(fake_torch())

    def test_deadline_criterion_and_eos_or_truncation_generation(self):
        torch = fake_torch()
        criterion = gpu.deadline_criterion(torch, object, 100, clock=lambda: 101)
        self.assertEqual(criterion(SimpleNamespace(shape=(1, 4), device="cuda:0"), None), [True])
        class Tensor:
            shape = (1, 5)
            def to(self, device): return self
            def detach(self): return self
            def cpu(self): return self
            def tolist(self): return [50, 151645]
        class Generated:
            def __getitem__(self, index): self.index = index; return Tensor()
        tokenizer = SimpleNamespace(pad_token_id=151643,
            apply_chat_template=lambda messages, tokenize, **kwargs:
                {"input_ids": Tensor(), "attention_mask": Tensor()} if tokenize else "<|im_start|>assistant\n<think>\n",
            decode=lambda ids, **kwargs: "reason</think>answer")
        model = FakeModel(); calls = []
        def generate(**kwargs):
            calls.append(kwargs)
            self.assertTrue(all(module.disable_adapters for module in model.modules()))
            return Generated()
        model.generate = generate
        result = gpu.generate_one(model, tokenizer, [], "base", 100, torch, object, list, clock=lambda: 0)
        self.assertEqual(result["finish_reason"], "stop")
        self.assertEqual(calls[0]["max_new_tokens"], 2048)
        self.assertFalse(calls[0]["do_sample"])
        self.assertEqual(torch.manual_seed.call_args.args[0], 20261105)
        gpu.adapter_state(model, False)
        result = gpu.generate_one(model, tokenizer, [], "base", 100, torch, object, list, clock=lambda: 101)
        self.assertEqual(result["finish_reason"], "timeout")

    def test_fixed_pair_order_partial_prefix_and_no_hidden_reasoning_report(self):
        comparison = gpu.comparison_module(); frozen = gpu.plan(comparison)["comparison"]
        identity = {"engine": "synthetic", "engine_version": "1", "base_weights_sha256": "a" * 64,
                    "tokenizer_sha256": "b" * 64, "chat_template_sha256": "c" * 64, "quantization": "nf4"}
        calls = []
        def generate(messages, mode):
            index = len(calls) // 2; calls.append(mode)
            return good_generation(comparison.cases()[index])
        report = gpu.run_pairs(comparison, frozen, identity, generate, 1000, lambda _: None, clock=lambda: 0)
        self.assertEqual(calls, ["base", "adapted"] * 8)
        self.assertEqual(report["results"]["base"]["paired_passed_cases"], 8)
        self.assertNotIn("HIDDEN_REASONING", json.dumps(report))
        times = iter([0, 0, 990]); calls.clear()
        partial = gpu.run_pairs(comparison, frozen, identity, generate, 1000, lambda _: None, clock=lambda: next(times))
        self.assertEqual(partial["paired_completed_cases"], 1)
        self.assertFalse(partial["coverage_complete"])

    def test_peft_context_reenable_gradients_are_refrozen_on_success_and_exception(self):
        class ReenablingModel(FakeModel):
            def __init__(self):
                super().__init__()
                self.adapter_parameters = [FakeWeight((2, 2)), FakeWeight((2, 2))]
                for parameter in self.adapter_parameters: parameter.requires_grad = True
            def parameters(self): return super().parameters() + self.adapter_parameters
            @contextmanager
            def disable_adapter(self):
                try:
                    with super().disable_adapter(): yield
                finally:
                    # Match PEFT enable_adapters(True) -> set_adapter() behavior.
                    for parameter in self.adapter_parameters: parameter.requires_grad = True
        class Tensor:
            shape = (1, 5)
            def to(self, device): return self
            def detach(self): return self
            def cpu(self): return self
            def tolist(self): return [50, 151645]
        class Generated:
            def __getitem__(self, index): return Tensor()
        tokenizer = SimpleNamespace(pad_token_id=151643,
            apply_chat_template=lambda messages, tokenize, **kwargs:
                {"input_ids": Tensor()} if tokenize else "<|im_start|>assistant\n<think>\n",
            decode=lambda ids, **kwargs: "reason</think>answer")
        for mode, raises in (("base", False), ("base", True), ("adapted", False), ("adapted", True)):
            model = ReenablingModel()
            def generate(**kwargs):
                self.assertTrue(all(not parameter.requires_grad for parameter in model.parameters()))
                if raises: raise RuntimeError("synthetic generation failure")
                return Generated()
            model.generate = generate
            if raises:
                with self.assertRaisesRegex(RuntimeError, "synthetic generation failure"):
                    gpu.generate_one(model, tokenizer, [], mode, 100, fake_torch(), object, list, clock=lambda: 0)
            else:
                gpu.generate_one(model, tokenizer, [], mode, 100, fake_torch(), object, list, clock=lambda: 0)
            self.assertTrue(all(not parameter.requires_grad for parameter in model.parameters()))
            gpu.adapter_state(model, False)

    def test_loaded_adapter_values_exact_source_not_only_nonzero(self):
        import numpy as np
        rows = {}
        for index in range(448):
            for letter, shape in (("A", (16, 2)), ("B", (2, 16))):
                rows[f"base_model.model.layers.{index}.q.lora_{letter}.weight"] = np.ones(shape, dtype=np.float32)
        class Parameter:
            requires_grad = False
            def __init__(self, value): self.value = value; self.dtype = value.dtype; self.shape = value.shape
            def detach(self): return self
            def cpu(self): return self
        model = SimpleNamespace(named_parameters=lambda: [
            (name.replace(".weight", ".default.weight"), Parameter(value)) for name, value in rows.items()])
        source = SimpleNamespace(keys=lambda: list(rows), get_tensor=lambda key: Parameter(rows[key].copy()))
        @contextmanager
        def safe_open(*args, **kwargs): yield source
        torch = SimpleNamespace(isfinite=lambda value: np.isfinite(value.value),
                                equal=lambda a, b: np.array_equal(a.value, b.value))
        result = gpu.exact_loaded_adapter(model, Path("synthetic"), torch, safe_open)
        self.assertTrue(result["loaded_values_equal_source"])
        first = next(iter(rows)); original = source.get_tensor
        source.get_tensor = lambda key: Parameter(np.zeros_like(rows[key])) if key == first else original(key)
        with self.assertRaises(gpu.EvaluationError): gpu.exact_loaded_adapter(model, Path("synthetic"), torch, safe_open)

    def test_invalid_job_causes_no_client_model_or_output_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "new"; bad = job(); bad["optimizer_steps"] = 1
            clients = Mock()
            with self.assertRaises(gpu.EvaluationError): gpu.execute(bad, output, clients=clients)
            clients.assert_not_called(); self.assertFalse(output.exists())

    def test_fp32_checkpoint_preserved_before_load_onto_bf16_base(self):
        import numpy as np
        originals = {}
        for index in range(448):
            for letter, shape in (("A", (16, 2)), ("B", (2, 16))):
                originals[f"base_model.model.layers.{index}.q.lora_{letter}.weight"] = np.full(shape, 1.0001, dtype=np.float32)
        class Parameter:
            requires_grad = False
            def __init__(self, value): self.value = value; self.dtype = value.dtype; self.shape = value.shape
            def detach(self): return self
            def cpu(self): return self
        @contextmanager
        def source_file(*args, **kwargs):
            yield SimpleNamespace(keys=lambda: originals.keys(), get_tensor=lambda name: Parameter(originals[name]))
        torch = SimpleNamespace(isfinite=lambda value: np.isfinite(value.value),
                                equal=lambda a, b: np.array_equal(a.value, b.value))
        # PEFT's default upcast creates FP32 adapter destinations before loading
        # an FP32 checkpoint. Turning it off can round into BF16 first; even a
        # subsequent FP32 upcast cannot recover the checkpoint's original bits.
        def load(autocast_adapter_dtype):
            require_base = SimpleNamespace(compute_dtype="bf16")
            self.assertEqual(require_base.compute_dtype, "bf16")
            runtime = {}
            for name, original in originals.items():
                value = original.copy()
                if not autocast_adapter_dtype:
                    value = (value.view(np.uint32) & np.uint32(0xffff0000)).view(np.float32)
                runtime[name.replace(".weight", ".default.weight")] = Parameter(value)
            return SimpleNamespace(named_parameters=lambda: runtime.items())
        gpu.exact_loaded_adapter(load(True), Path("synthetic"), torch, source_file)
        with self.assertRaisesRegex(gpu.EvaluationError, "values_changed"):
            gpu.exact_loaded_adapter(load(False), Path("synthetic"), torch, source_file)

    def test_whole_fake_pipeline_load_once_attach_once_no_optimizer_private_only_two_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); output = root / "result"; snapshot = root / "snapshot"; snapshot.mkdir()
            (snapshot / "tokenizer_config.json").write_text('{"chat_template":"synthetic-official-template"}')
            model, torch = FakeModel(), fake_torch()
            tokenizer = SimpleNamespace(chat_template="synthetic-official-template")
            loader = SimpleNamespace(from_pretrained=Mock(return_value=(model, object())), for_inference=Mock())
            def attach(base, *args, **kwargs):
                self.assertIs(base, model)
                self.assertTrue(kwargs["autocast_adapter_dtype"])
                self.assertEqual(model.rows[0][1].compute_dtype, "bf16")
                model.rows = [(name, FakePeftOuter(layer)) for name, layer in model.rows]
                return model
            peft = SimpleNamespace(from_pretrained=Mock(side_effect=attach))
            summary = {}; artifact_files = []
            saved = SimpleNamespace(state="COMMITTED", qualified_name=
                gpu.ENTITY + "/" + gpu.resume.PROJECT + "/hasla-qwq-gpu-comparison-123456789:v0")
            sdk_run = SimpleNamespace(summary=summary, log_artifact=Mock(return_value=SimpleNamespace(wait=lambda **kwargs: saved)),
                                      finish=Mock())
            artifact = SimpleNamespace(add_file=lambda path, name: artifact_files.append((path, name)))
            sdk = SimpleNamespace(init=Mock(return_value=sdk_run), Artifact=Mock(return_value=artifact))
            privacy = Mock(return_value=True)
            counter = [0]
            generation_deadlines, wall_guards = [], []
            def generate(*args):
                index = counter[0] // 2; counter[0] += 1
                generation_deadlines.append(args[4])
                return good_generation(gpu.comparison_module().cases()[index])
            def download(spec, config, directory, api, privacy): directory.mkdir()
            imports = {"torch": torch, "hub": object(), "loader": loader, "PeftModel": peft,
                       "AutoTokenizer": SimpleNamespace(from_pretrained=Mock(return_value=tokenizer)),
                       "BitsAndBytesConfig": lambda **kwargs: kwargs, "Params4bit": FakeWeight,
                       "safe_open": object(), "StoppingCriteria": object, "StoppingCriteriaList": list}
            adapter_proof = {"tensor_count": 896, "lora_pairs": 448, "loaded_values_equal_source": True,
                             "source_model_sha256": gpu.SOURCE["files"][1]["sha256"], "optimizer_steps": 0}
            def guard(seconds): wall_guards.append(seconds); return nullcontext()
            with patch.object(gpu, "hard_wall", guard), \
                    patch.object(gpu.resume, "download_initial_adapter", side_effect=download), \
                    patch.object(gpu, "adapter_file_proof") as original_files, \
                    patch.object(gpu, "materialize_base", return_value=snapshot), \
                    patch.object(gpu, "exact_loaded_adapter", return_value=adapter_proof) as value_check, \
                    patch.object(gpu, "generate_one", side_effect=generate), \
                    patch.object(gpu.importlib.metadata, "version", return_value="synthetic1"), redirect_stdout(io.StringIO()):
                result = gpu.execute(job(), output, clients=lambda _: (object(), privacy, sdk), imports=imports, clock=lambda: 100)
            self.assertEqual(result["status"], "uploaded")
            self.assertEqual(result["execution_status"], "completed")
            self.assertEqual(result["paired_completed_cases"], 8)
            self.assertEqual(loader.from_pretrained.call_count, 1)
            self.assertEqual(peft.from_pretrained.call_count, 1)
            self.assertEqual(loader.for_inference.call_count, 1)
            self.assertFalse(peft.from_pretrained.call_args.kwargs["is_trainable"])
            self.assertEqual(original_files.call_count, 2)
            self.assertEqual(value_check.call_count, 2)
            self.assertEqual(counter[0], 16)
            self.assertEqual(set(generation_deadlines), {2650})
            self.assertEqual(wall_guards[0], 2580)
            self.assertEqual(sdk.init.call_args.kwargs["id"], "hasla-qwq-gpu-comparison-123456789")
            self.assertEqual([name for _, name in artifact_files], ["report.json", "metadata.json"])
            self.assertNotIn("HIDDEN_REASONING", (output / "report.json").read_text())
            self.assertNotIn("HIDDEN_REASONING", json.dumps(summary))
            gpu.validate_outputs(output)
            self.assertEqual(summary["private_qwq_gpu_result_json"]["status"], "uploaded")
            gpu.validate_result(result, "123456789")
            for kind in ("raw", "wrong_run", "wrong_plan", "wrong_file", "raw_metric"):
                changed = deepcopy(result)
                if kind == "raw": changed["raw_thought"] = "private"
                elif kind == "wrong_run": changed["run_id"] = "999"
                elif kind == "wrong_plan": changed["comparison_plan_sha256"] = "0" * 64
                elif kind == "wrong_file": changed["files"][0]["name"] = "source-adapter.safetensors"
                else: changed["metrics"]["base"]["reasoning"] = "private"
                with self.subTest(kind=kind), self.assertRaises(gpu.EvaluationError):
                    gpu.validate_result(changed, "123456789")
            changed = json.loads((output / "metadata.json").read_text()); changed["raw_thinking"] = "secret"
            (output / "metadata.json").write_text(json.dumps(changed))
            with self.assertRaises(gpu.EvaluationError): gpu.validate_outputs(output)


if __name__ == "__main__":
    unittest.main()

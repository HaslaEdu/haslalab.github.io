"""CPU-only synthetic QwQ 48GB profile contracts; no real model/GPU/API/fit proof."""
import copy
import contextlib
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import private_dedicated_run as dedicated
import private_dual_pod as bootstrap
import private_dual_run as parent
import private_pod_train as pod
import private_resume_adapter as resume
import private_verify_adapter as verifier
import role_config
import train_lora as train
from test_private_dual_run import fixture
import test_private_pod_train as pod_fixtures
from test_private_training_continuation import source_spec, continued_verifier, verify_fixture


PROFILE = role_config.QWQ_32B_QLORA_48GB_V1
GPU = 'NVIDIA L40S'
SHAPES = {'self_attn.q_proj': (5120, 5120), 'self_attn.k_proj': (1024, 5120),
          'self_attn.v_proj': (1024, 5120), 'self_attn.o_proj': (5120, 5120),
          'mlp.gate_proj': (27648, 5120), 'mlp.up_proj': (27648, 5120), 'mlp.down_proj': (5120, 27648)}


class Packed:
    def __init__(self, shape):
        self.quant_state = NS(shape=shape, quant_type='nf4')
        self.requires_grad = False
        self.device = NS(type='cuda', index=0)
    def numel(self):
        return math.prod(self.quant_state.shape) // 2
    def element_size(self):
        return 1


class DenseModel:
    def __init__(self):
        self.config = NS(model_type='qwen2', num_hidden_layers=64, hidden_size=5120,
                         intermediate_size=27648, num_attention_heads=40, num_key_value_heads=8)
        self.hf_device_map = {'': 0}
        self.layers = [(f'base_model.model.model.layers.{layer}.{name}', NS(weight=Packed(shape)))
                       for layer in range(64) for name, shape in SHAPES.items()]
        self.other = [('base.embed_tokens.weight', NS(requires_grad=False, device=NS(type='cuda', index=0))),
                      ('base.layers.lora_A.default.weight', NS(requires_grad=True, device=NS(type='cuda', index=0))),
                      ('base.layers.lora_B.default.weight', NS(requires_grad=True, device=NS(type='cuda', index=0)))]
    def named_modules(self):
        return self.layers
    def named_parameters(self):
        return [(name + '.base_layer.weight', module.weight) for name, module in self.layers] + self.other
    def parameters(self):
        return [value for _, value in self.named_parameters()]
    def save_pretrained(self, out):
        Path(out).mkdir()
        (Path(out) / 'adapter_model.safetensors').write_bytes(b'synthetic-not-real-weights')


def fake_torch():
    return NS(bfloat16='synthetic-bf16', cuda=NS(is_available=lambda: True, device_count=lambda: 1,
        get_device_properties=lambda _: NS(name=GPU, total_memory=48 * 1024**3),
        reset_peak_memory_stats=lambda _: None, max_memory_allocated=lambda _: 24 * 1024**3,
        max_memory_reserved=lambda _: 28 * 1024**3))


def proof():
    return {**train.gemma_single_gpu_proof(fake_torch()),
            'dense_quantization_verified': True, 'dense_layers': 64, 'quantized_linear_tensors': 448,
            'base_parameters_frozen': True, 'first_optimizer_step_completed': True,
            'first_step_peak_allocated_bytes': 24 * 1024**3, 'first_step_peak_reserved_bytes': 28 * 1024**3}


class QwqTrainingProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_fixed_same_base_and_default_contracts_are_preserved(self):
        before = role_config.get_role_config('solver')
        config = role_config.validate_role_format('solver', 'text', PROFILE)
        for key in ('base_model', 'base_aliases', 'loader', 'precision', 'training_method', 'default_rank', 'max_length'):
            self.assertEqual(config[key], before[key])
        self.assertEqual((config['base_model'], config['default_rank'], config['max_length']), ('Qwen/QwQ-32B', 16, 1024))
        self.assertTrue(config['load_in_4bit'])
        self.assertFalse(config['load_in_16bit'])
        self.assertEqual(role_config.get_role_config('solver'), before)
        self.assertEqual(role_config.validate_role_format('solver', 'chat')['max_length'], 4096)
        self.assertEqual(role_config.get_role_config('chat', role_config.GEMMA_26B_QLORA_V1)['default_rank'], 8)
        for role, profile, fmt in (('chat', PROFILE, 'chat'), ('solver', 'unknown', 'text'),
                                   ('solver', role_config.GEMMA_26B_QLORA_V1, 'text'), ('solver', PROFILE, 'chat')):
            with self.subTest(role=role, profile=profile, fmt=fmt), self.assertRaises(ValueError):
                role_config.validate_role_format(role, fmt, profile)

    def test_cli_rejects_rank_or_length_changes_before_loading_data_or_models(self):
        for option in (['--rank', '8'], ['--max-len', '4096'], ['--training-profile', 'unknown']):
            args = ['--base', 'solver', '--format', 'text', '--training-profile', PROFILE,
                    *option, str(self.root / 'nonexistent.jsonl'), str(self.root / 'out')]
            with self.subTest(option=option), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                train.main(args)

    def manifest(self):
        env, manifest = fixture()
        manifest.update(selected_roles=['solver'], budget_krw=100000, authorized_budget_krw=100000, prior_upper_krw=60000)
        manifest['roles']['solver'].update(training_profile=PROFILE, gpu_ids=[GPU],
            gpu_usd_per_hour_upper='1.2', runtime_seconds=10800)
        return env, manifest

    def test_manifest_gpu_price_and_runtime_are_role_bound_and_budgeted(self):
        env, manifest = self.manifest()
        loaded, _ = parent.load_inputs({**env, 'HASLA_DUAL_MANIFEST': json.dumps(manifest)})
        ledger, quote, seconds, gpus = parent.resource_settings(loaded, 'solver')
        self.assertEqual((seconds, gpus), (10800, [GPU]))
        reserved = parent.reserve_run(ledger, 'synthetic-qwq48', 'solver', quote, 0, seconds, seconds)
        self.assertLessEqual(reserved.prior_spend_krw + reserved.reserved_krw + 5000, 100000)
        for gpu in ('NVIDIA A100-PCIE-40GB', 'NVIDIA L40', 'NVIDIA A40', GPU):
            manifest['roles']['solver']['gpu_ids'] = [gpu]
            self.assertEqual(parent.resource_settings(manifest, 'solver')[3], [gpu])
        for update in ({'gpu_ids': ['NVIDIA A100-SXM4-80GB']}, {'gpu_ids': ['NVIDIA H200']},
                       {'gpu_ids': [GPU, 'NVIDIA A100-SXM4-80GB']}, {'gpu_usd_per_hour_upper': '1.20001'},
                       {'runtime_seconds': 14401}, {'format': 'chat'}, {'training_profile': 'unknown'}):
            bad = copy.deepcopy(manifest)
            bad['roles']['solver'].update(update)
            with self.subTest(update=update), self.assertRaises(ValueError):
                parent.resource_settings(bad, 'solver')
        manifest['roles']['solver']['runtime_seconds'] = 14400
        self.assertEqual(parent.resource_settings(manifest, 'solver')[2], 14400)
        manifest['roles']['solver'].pop('training_profile')
        with self.assertRaises(ValueError):
            parent.resource_settings(manifest, 'solver')

    def test_profile_and_continuation_cross_bootstrap_and_pinned_worker(self):
        env, manifest = self.manifest()
        initial, _ = source_spec()
        manifest['roles']['solver']['initial_adapter'] = initial
        manifest['resume_script_sha256'] = 'b' * 64
        child = dedicated.pod_environment(env, manifest, 'fixture', 'solver', 'synthetic-solver48',
                                          'fixture/private/solver:v0', 10800)
        job = json.loads(child['HASLA_ROLE_JOBS'])[0]
        self.assertEqual((job['training_profile'], job['initial_adapter'], job['runtime_seconds']), (PROFILE, initial, 10200))
        code = b'# synthetic pinned child\n'
        child['HASLA_POD_SCRIPT_SHA256'] = hashlib.sha256(code).hexdigest()
        with patch.dict(os.environ, child, clear=True), patch.object(bootstrap.urllib.request, 'urlopen', return_value=io.BytesIO(code)), \
                patch.object(Path, 'write_bytes'), patch.object(Path, 'mkdir'), \
                patch.object(bootstrap.subprocess, 'run', return_value=NS(returncode=0)) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bootstrap.main(), 0)
        forwarded = run.call_args.kwargs['env']
        self.assertEqual(forwarded['HASLA_TRAINING_PROFILE'], PROFILE)
        self.assertEqual(json.loads(forwarded['HASLA_INITIAL_ADAPTER']), initial)
        self.assertEqual(forwarded['HASLA_TRAIN_TIMEOUT_SECONDS'], '10200')
        config = pod.pinned_role_settings(Path(role_config.__file__), 'solver', 'text', PROFILE)
        self.assertEqual(resume.validate_spec(initial, config)['rank'], 16)
        command = pod.training_command('train.py', 'train.jsonl', 'out', config=config, data_format='text')
        self.assertEqual(command[command.index('--training-profile') + 1], PROFILE)
        for change in ({'role': 'chat', 'format': 'chat'}, {'format': 'chat'}, {'training_profile': 'unknown'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                bootstrap.role_jobs({'HASLA_ROLE_JOBS': json.dumps([{**job, **change}]), 'HASLA_RESUME_SCRIPT_SHA256': 'b' * 64})

    def test_all_448_actual_dense_projection_weights_require_frozen_cuda_nf4(self):
        self.assertEqual(train.qwq_quantized_linear_proof(DenseModel(), Packed)['quantized_linear_tensors'], 448)
        for mutate in (lambda m: m.layers.pop(), lambda m: setattr(m.config, 'model_type', 'qwen3'),
                       lambda m: setattr(m.layers[-1][1].weight, 'quant_state', None),
                       lambda m: setattr(m.layers[-1][1].weight.quant_state, 'quant_type', 'fp4'),
                       lambda m: setattr(m.layers[-1][1].weight, 'requires_grad', True),
                       lambda m: setattr(m.layers[-1][1].weight, 'device', NS(type='cpu', index=None)),
                       lambda m: setattr(m.layers[-1][1].weight, 'numel', lambda: 10**12),
                       lambda m: setattr(m.layers[-1][1].weight.quant_state, 'shape', (5120, 5120)),
                       lambda m: setattr(m.other[0][1], 'requires_grad', True),
                       lambda m: m.layers.append(m.layers[0])):
            model = DenseModel()
            mutate(model)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                train.qwq_quantized_linear_proof(model, Packed)

    def test_hardware_cannot_use_two_gpus_offload_or_80gb(self):
        for mapping in ({'': 'cpu'}, {'': 'disk'}, {'': 'meta'}, {'': 1}):
            model = DenseModel()
            model.hf_device_map = mapping
            with self.subTest(mapping=mapping), self.assertRaises(ValueError):
                train.gemma_single_gpu_proof(fake_torch(), model)
        for change in ({'device_count': lambda: 2},
                       {'get_device_properties': lambda _: NS(name=GPU, total_memory=80 * 1024**3)},
                       {'get_device_properties': lambda _: NS(name='NVIDIA H100', total_memory=48 * 1024**3)}):
            torch = fake_torch()
            torch.cuda.__dict__.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                train.gemma_single_gpu_proof(torch)
        model = DenseModel()
        model.other[0][1].device = NS(type='cpu', index=None)
        with self.assertRaises(ValueError):
            train.gemma_single_gpu_proof(fake_torch(), model)

    def test_private_worker_preserves_only_validated_profile_proof(self):
        harness = pod_fixtures.PrivatePodTests('test_success_only_uploads_adapter_and_safe_exact_result')
        harness.setUp()
        self.addCleanup(harness.doCleanups)
        harness.env['HASLA_TRAINING_PROFILE'] = PROFILE
        def runner(command, **kwargs):
            result = harness.runner(command, **kwargs)
            path = harness.root / 'adapter' / 'hasla_training_manifest.json'
            data = json.loads(path.read_text())
            path.write_text(json.dumps({**data, 'training_profile': PROFILE, **proof()}))
            return result
        result = pod.run_pilot(harness.env, harness.root, harness.wandb, harness.opener, runner)
        self.assertEqual(result['status'], 'uploaded')
        self.assertEqual(result['runtime_profile_proof'], proof())
        self.assertEqual(harness.wandb.run.artifacts[0][0].metadata['runtime_profile_proof'], proof())
        report = harness.root / 'adapter' / 'hasla_training_manifest.json'
        original = json.loads(report.read_text())
        config = pod.data_bounded_settings(role_config.get_role_config('solver', PROFILE), 1)
        for key, value in (('dense_layers', 63), ('quantized_linear_tensors', 447), ('base_parameters_frozen', 1),
                           ('first_optimizer_step_completed', False), ('gpu_count', 2), ('physical_vram_bytes', 80 * 1024**3),
                           ('first_step_peak_reserved_bytes', 80 * 1024**3)):
            report.write_text(json.dumps({**original, key: value}))
            with self.subTest(key=key), self.assertRaises(pod.PilotError):
                pod.training_report(report.parent, config, 'text', harness.env['HASLA_DATA_SHA256'], None)

    def test_cpu_verifier_binds_dense_profile_and_continued_adapter_update(self):
        fixture = continued_verifier()
        result = fixture.results['solver']
        fields = {'training_profile': PROFILE, 'precision': '4bit', 'training_method': 'qlora',
                  'format': 'text', 'runtime_profile_proof': proof()}
        result.update(fields)
        artifact = fixture.artifacts[result['artifact']]
        artifact.metadata.update(fields)
        checked = verify_fixture(fixture)['roles'][0]
        self.assertEqual((checked['status'], checked['training_profile']), ('verified', PROFILE))
        self.assertEqual(checked['runtime_profile_proof'], proof())
        artifact.metadata['runtime_profile_proof'] = {**proof(), 'dense_layers': 63}
        self.assertEqual(verify_fixture(fixture)['roles'][0]['code'], 'artifact_training_profile_mismatch')
        for change in ({'training_profile': 'unknown'}, {'format': 'chat'}, {'rank': 8},
                       {'runtime_profile_proof': {**proof(), 'dense_layers': 63}},
                       {'runtime_profile_proof': {**proof(), 'raw_text': 'must-not-emit'}},
                       {'runtime_profile_proof': {**proof(), 'first_optimizer_step_completed': False}}):
            with self.subTest(change=change), self.assertRaises(verifier.VerificationError):
                verifier.expected_result({**result, **change}, 'fixture-entity', '123', 'solver')

    def test_real_trainer_path_keeps_rank_batch_length_and_continuation(self):
        for source_alias in (None, 'Qwen/QwQ-32B', 'unsloth/QwQ-32B-unsloth-bnb-4bit'):
            continuing = source_alias is not None
            with self.subTest(source_alias=source_alias), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                data = root / 'train.text.jsonl'
                data.write_text(json.dumps({'text': 'Synthetic native fixture only', 'metadata': {'split': 'train'}}) + '\n')
                model, calls = DenseModel(), {}
                class Loader:
                    @staticmethod
                    def from_pretrained(**kwargs):
                        if kwargs['model_name'] != 'Qwen/QwQ-32B':
                            raise AssertionError('the dense NF4 base must be the exact Qwen original')
                        calls['loader'] = kwargs
                        return model, NS(eos_token='<eos>', save_pretrained=lambda _: None)
                    @staticmethod
                    def get_peft_model(value, **kwargs):
                        if continuing:
                            raise AssertionError('continuation must not reset LoRA')
                        calls['peft'] = kwargs
                        return value
                    @staticmethod
                    def patch_peft_model(value, **kwargs):
                        calls['patch'] = (value, kwargs)
                        return value
                def attach(value, source, **kwargs):
                    calls['attach'] = (value, source, kwargs)
                    self.assertEqual(json.loads((Path(source) / 'adapter_config.json').read_text())['base_model_name_or_path'], source_alias)
                    self.assertEqual((Path(source) / 'adapter_model.safetensors').read_bytes(), before)
                    return value
                class Trainer:
                    def __init__(self, **kwargs):
                        calls['trainer'] = kwargs
                        self.callbacks = []
                        self.state = NS(global_step=0, log_history=[])
                    def add_callback(self, cb):
                        self.callbacks.append(cb)
                    def train(self):
                        self.state.global_step = 1
                        for cb in self.callbacks:
                            cb.on_step_end(None, self.state, NS())
                        return NS(metrics={'train_loss': 1.0})
                modules = {'unsloth': NS(FastLanguageModel=Loader, is_bfloat16_supported=lambda: True), 'torch': fake_torch(),
                           'datasets': NS(Dataset=NS(from_list=lambda rows: rows)), 'bitsandbytes': NS(),
                           'bitsandbytes.nn': NS(Params4bit=Packed), 'transformers': NS(TrainerCallback=object),
                           'peft': NS(PeftModel=NS(from_pretrained=attach)),
                           'trl': NS(SFTConfig=lambda **kw: NS(**kw), SFTTrainer=Trainer)}
                out = root / 'out'
                args = ['--base', 'solver', '--format', 'text', '--training-profile', PROFILE,
                        '--holdout', '0', '--max-steps', '1']
                if continuing:
                    initial = root / 'initial'
                    initial.mkdir()
                    _, blobs = source_spec()
                    config = json.loads(blobs['adapter_config.json'])
                    config['base_model_name_or_path'] = source_alias
                    blobs['adapter_config.json'] = json.dumps(config).encode()
                    for name, raw in blobs.items():
                        (initial / name).write_bytes(raw)
                    before = (initial / 'adapter_model.safetensors').read_bytes()
                    before_config = (initial / 'adapter_config.json').read_bytes()
                    args += ['--resume-adapter', str(initial)]
                with patch.dict(sys.modules, modules), contextlib.redirect_stdout(io.StringIO()):
                    train.main(args + [str(data), str(out)])
                saved = json.loads((out / 'hasla_training_manifest.json').read_text())
                self.assertEqual((saved['base_model'], saved['rank'], saved['max_length']), ('Qwen/QwQ-32B', 16, 1024))
                self.assertEqual(saved['training_profile'], PROFILE)
                self.assertEqual(saved['quantized_linear_tensors'], 448)
                self.assertTrue(saved['first_optimizer_step_completed'])
                self.assertEqual(calls['loader']['device_map'], {'': 0})
                self.assertTrue(calls['loader']['use_exact_model_name'])
                self.assertFalse(calls['loader']['offload_embedding'])
                self.assertEqual(calls['trainer']['args'].per_device_train_batch_size, 1)
                self.assertEqual(calls['trainer']['args'].per_device_eval_batch_size, 1)
                self.assertEqual(calls['trainer']['args'].gradient_accumulation_steps, 8)
                if continuing:
                    self.assertEqual(calls['loader']['model_name'], 'Qwen/QwQ-32B')
                    self.assertEqual(calls['attach'], (model, str(initial), {'is_trainable': True, 'local_files_only': True}))
                    self.assertEqual(calls['patch'], (model, {'use_gradient_checkpointing': 'unsloth'}))
                    self.assertEqual((initial / 'adapter_model.safetensors').read_bytes(), before)
                    self.assertEqual((initial / 'adapter_config.json').read_bytes(), before_config)
                    self.assertEqual(saved['initial_adapter_config_sha256'], hashlib.sha256(before_config).hexdigest())
                    self.assertFalse(saved['optimizer_state_restored'])
                else:
                    self.assertEqual(calls['loader']['model_name'], 'Qwen/QwQ-32B')
                    self.assertEqual(calls['peft']['r'], 16)


if __name__ == '__main__':
    unittest.main()

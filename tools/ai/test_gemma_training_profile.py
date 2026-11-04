"""Synthetic CPU profile plumbing/proof tests. No model, GPU, or network work."""
import copy
import contextlib
from dataclasses import replace
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
import private_dual_run as inputs
import private_pod_train as pod
import role_config
import train_lora
from test_private_dual_run import fixture


PROFILE = role_config.GEMMA_26B_QLORA_V1
GPU = 'NVIDIA A40'


class Packed:
    def __init__(self, shape):
        self._original_shape = shape
        self.quant_state = NS(shape=shape, quant_type='nf4')
        self.requires_grad = False
        self.device = NS(type='cuda', index=0)
    def numel(self):
        return math.prod(self._original_shape) // 2
    def element_size(self):
        return 1


def synthetic_model():
    experts_type = type('Gemma4TextExperts', (), {})
    blocks = []
    for _ in range(30):
        block = experts_type()
        block.gate_up_proj = Packed((128, 1408, 2816))
        block.down_proj = Packed((128, 2816, 704))
        blocks.append(block)
    model = NS(hf_device_map={'': 0}, modules=lambda: blocks,
               parameters=lambda: [p for b in blocks for p in (b.gate_up_proj, b.down_proj)])
    return model, blocks


def synthetic_torch():
    return NS(bfloat16='synthetic-bf16', cuda=NS(is_available=lambda: True, device_count=lambda: 1,
        get_device_properties=lambda _: NS(name=GPU, total_memory=48 * 1024**3),
        reset_peak_memory_stats=lambda _: None, max_memory_allocated=lambda _: 16 * 1024**3,
        max_memory_reserved=lambda _: 18 * 1024**3))


class GemmaTrainingProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_profile_preserves_base_and_default_contracts(self):
        before = role_config.get_role_config('chat')
        config = role_config.get_role_config('chat', PROFILE)
        self.assertEqual(config['base_model'], before['base_model'])
        self.assertEqual(config['base_aliases'], before['base_aliases'])
        self.assertEqual((config['precision'], config['training_method'], config['default_rank'], config['max_length']),
                         ('4bit', 'qlora', 8, 1024))
        self.assertTrue(config['load_in_4bit'])
        self.assertFalse(config['load_in_16bit'])
        self.assertEqual(role_config.get_role_config('chat'), before)
        for role, profile in [('solver', PROFILE), ('fast', PROFILE), ('chat', ''), ('chat', 'unknown')]:
            with self.subTest(role=role, profile=profile), self.assertRaises(ValueError):
                role_config.get_role_config(role, profile)

    def test_manifest_profile_allows_only_approved_40_48gb_pool_and_four_dollars(self):
        env, manifest = fixture()
        manifest.update(selected_roles=['chat'], budget_krw=100000, authorized_budget_krw=100000,
                        prior_upper_krw=52842)
        spec = manifest['roles']['chat']
        spec.update(training_profile=PROFILE, gpu_ids=['NVIDIA A100-PCIE-40GB', 'NVIDIA L40S', 'NVIDIA L40', GPU],
                    runtime_seconds=1800, gpu_usd_per_hour_upper='4')
        loaded, _ = inputs.load_inputs({**env, 'HASLA_DUAL_MANIFEST': json.dumps(manifest)})
        ledger, quote, seconds, preferences = inputs.resource_settings(loaded, 'chat')
        reserved = inputs.reserve_run(ledger, 'synthetic-chat', 'chat', quote, 0, seconds, seconds)
        self.assertEqual(reserved.reserved_krw, 4944)
        self.assertEqual(preferences, spec['gpu_ids'])
        for update in ({'gpu_ids': ['NVIDIA H200']}, {'gpu_ids': ['NVIDIA A100 80GB PCIe']},
                       {'gpu_usd_per_hour_upper': '4.01'}, {'runtime_seconds': 3601},
                       {'training_profile': 'unknown'}):
            bad = copy.deepcopy(manifest)
            bad['roles']['chat'].update(update)
            with self.subTest(update=update), self.assertRaises(ValueError):
                inputs.resource_settings(bad, 'chat')

    def test_profile_crosses_dedicated_job_bootstrap_pinned_config_and_trainer_command(self):
        env, manifest = fixture()
        spec = manifest['roles']['chat']
        spec['training_profile'] = PROFILE
        child = dedicated.pod_environment(env, manifest, 'fixture', 'chat', 'synthetic-chat',
                                          'fixture/private/chat:v0', 3600)
        job = json.loads(child['HASLA_ROLE_JOBS'])[0]
        self.assertEqual(job['training_profile'], PROFILE)
        self.assertEqual(job['runtime_seconds'], 3000)
        with self.assertRaises(ValueError):
            bootstrap.role_jobs({'HASLA_ROLE_JOBS': json.dumps([{**job, 'runtime_seconds': 3001}])})
        code = b'# synthetic pinned child\n'
        child.update(REPO_SHA='a' * 40, HASLA_POD_SCRIPT_SHA256=hashlib.sha256(code).hexdigest(),
                     HASLA_TRAINING_PROFILE='stale-untrusted-profile')
        with patch.dict(os.environ, child, clear=True), patch.object(bootstrap.urllib.request, 'urlopen', return_value=io.BytesIO(code)), \
                patch.object(Path, 'write_bytes'), patch.object(Path, 'mkdir'), \
                patch.object(bootstrap.subprocess, 'run', return_value=NS(returncode=0)) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bootstrap.main(), 0)
        forwarded = run.call_args.kwargs['env']
        self.assertEqual(forwarded['HASLA_TRAINING_PROFILE'], PROFILE)
        self.assertEqual(forwarded['HASLA_TRAIN_TIMEOUT_SECONDS'], '3000')
        self.assertEqual(run.call_args.kwargs['timeout'], 3300)
        config = pod.pinned_role_settings(Path(role_config.__file__), 'chat', 'chat', forwarded['HASLA_TRAINING_PROFILE'])
        command = pod.training_command('train.py', 'train.jsonl', 'out', config=config, data_format='chat')
        self.assertEqual(command[command.index('--training-profile') + 1], PROFILE)
        options = train_lora.loader_kwargs(config, 1024, 'synthetic-bf16')
        self.assertEqual(options['model_name'], 'google/gemma-4-26B-A4B-it')
        self.assertEqual(options['device_map'], {'': 0})
        self.assertTrue(options['use_exact_model_name'])
        self.assertFalse(options['fast_inference'])
        self.assertTrue(options['load_in_4bit'])
        self.assertFalse(options['load_in_16bit'])

    def test_parent_runtime_extension_is_only_for_the_qlora_profile(self):
        _, manifest = fixture()
        manifest.update(budget_krw=100000, authorized_budget_krw=100000, prior_upper_krw=49979)
        chat = manifest['roles']['chat']
        chat.update(training_profile=PROFILE, gpu_ids=[GPU], gpu_usd_per_hour_upper='1.2', runtime_seconds=3600)
        ledger, quote, seconds, _ = inputs.resource_settings(manifest, 'chat')
        self.assertEqual(seconds, 3600)
        reserved = inputs.reserve_run(ledger, 'synthetic-extended-chat', 'chat', quote, 0, seconds, seconds)
        self.assertLessEqual(reserved.prior_spend_krw + reserved.reserved_krw + 5000, 100000)
        chat['runtime_seconds'] = 3601
        with self.assertRaises(ValueError):
            inputs.resource_settings(manifest, 'chat')
        del chat['training_profile']
        chat.update(gpu_ids=['NVIDIA A100-SXM4-80GB'], runtime_seconds=1800)
        self.assertEqual(inputs.resource_settings(manifest, 'chat')[2], 1800)
        chat['runtime_seconds'] = 1801
        with self.assertRaises(ValueError):
            inputs.resource_settings(manifest, 'chat')
        manifest['roles']['solver']['runtime_seconds'] = 14400
        self.assertEqual(inputs.resource_settings(manifest, 'solver')[2], 14400)
        manifest['roles']['solver']['runtime_seconds'] = 14401
        with self.assertRaises(ValueError):
            inputs.resource_settings(manifest, 'solver')

    def test_worker_timeout_extension_is_only_for_the_qlora_profile(self):
        from test_private_pod_train import FakeWandb
        env = {'ROLE': 'chat', 'HASLA_DATA_FORMAT': 'chat', 'RUN': 'synthetic-timeout',
               'ARTIFACT': 'synthetic-timeout-lora', 'HF_TOKEN': 'synthetic-only'}
        for profile, seconds, allowed in ((PROFILE, 3000, True), (PROFILE, 3001, False),
                                           (None, 1800, True), (None, 1801, False)):
            config = pod.data_bounded_settings(role_config.get_role_config('chat', profile), 1)
            with self.subTest(profile=profile, seconds=seconds), tempfile.TemporaryDirectory() as directory, \
                    patch.object(pod, 'decode_payload', return_value=b'{}'), \
                    patch.object(pod, 'rows_from_payload', return_value=[{}]), \
                    patch.object(pod, 'validate_row_roles'), patch.object(pod, 'verify_partitions'), \
                    patch.object(pod, 'assert_private_project', return_value={'base_url': 'https://api.wandb.ai', 'entity': 'fixture', 'project': 'private'}), \
                    patch.object(pod, 'fetch_training_script', return_value='a' * 64), \
                    patch.object(pod, 'fetch_role_config', return_value='b' * 64), \
                    patch.object(pod, 'pinned_role_settings', return_value=config), \
                    patch.object(pod, 'supervise_training', return_value=NS(returncode=1)) as run, \
                    patch.dict(os.environ, {}, clear=False):
                result = pod.run_pilot({**env, 'HASLA_TRAIN_TIMEOUT_SECONDS': str(seconds)}, Path(directory), FakeWandb())
                self.assertEqual(run.called, allowed)
                if allowed:
                    self.assertEqual(run.call_args.kwargs['timeout'], seconds)
                    command = run.call_args.args[0]
                    self.assertEqual(command[command.index('--train-wall-seconds') + 1], str(seconds - 600))
                else:
                    self.assertEqual(result['error_code'], 'invalid_training_timeout')

    def test_new_two_role_batch_keeps_profile_chat_and_solver_separate_without_old_sibling(self):
        env, manifest = fixture()
        env['HASLA_TRAINING_ROLE'] = 'both'
        manifest.update(selected_roles=['chat', 'solver'], budget_krw=100000,
                        authorized_budget_krw=100000, prior_upper_krw=49979)
        manifest['roles']['chat'].update(training_profile=PROFILE, runtime_seconds=1800,
                                        gpu_ids=[GPU], gpu_usd_per_hour_upper='4')
        manifest['roles']['solver'].update(runtime_seconds=5400, gpu_ids=['NVIDIA A100-SXM4-80GB'],
                                          gpu_usd_per_hour_upper='1.8')
        loaded, _ = inputs.load_inputs({**env, 'HASLA_DUAL_MANIFEST': json.dumps(manifest)})
        self.assertIsNone(dedicated.sibling_allowance(env, loaded))
        ledger = None
        for role in ('chat', 'solver'):
            initial, quote, seconds, _ = inputs.resource_settings(loaded, role)
            if ledger is None:
                ledger = replace(initial, policy=replace(initial.policy, max_active_pods=2))
            ledger = inputs.reserve_run(ledger, 'synthetic-new-' + role, role, quote, 0, seconds, seconds)
            child = dedicated.pod_environment(env, loaded, 'fixture', role, 'synthetic-new-' + role,
                                               'fixture/private/' + role + ':v0', seconds)
            job = json.loads(child['HASLA_ROLE_JOBS'])[0]
            self.assertEqual(job.get('training_profile'), PROFILE if role == 'chat' else None)
        self.assertLessEqual(ledger.prior_spend_krw + ledger.reserved_krw + 5000, 100000)
        self.assertEqual(len(ledger.runs), 2)

    def test_default_job_does_not_inherit_a_stale_profile(self):
        job = {'role': 'solver', 'format': 'text', 'run': 'synthetic-solver',
               'input_artifact': 'fixture/private/solver:v0', 'training_sha256': '1' * 64,
               'validation_sha256': '2' * 64}
        code = b'# synthetic child\n'
        env = {'HASLA_ROLE_JOBS': json.dumps([job]), 'REPO_SHA': 'a' * 40,
               'HASLA_POD_SCRIPT_SHA256': hashlib.sha256(code).hexdigest(), 'HASLA_TRAINING_PROFILE': PROFILE}
        with patch.dict(os.environ, env, clear=True), patch.object(bootstrap.urllib.request, 'urlopen', return_value=io.BytesIO(code)), \
                patch.object(Path, 'write_bytes'), patch.object(Path, 'mkdir'), \
                patch.object(bootstrap.subprocess, 'run', return_value=NS(returncode=0)) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bootstrap.main(), 0)
        self.assertNotIn('HASLA_TRAINING_PROFILE', run.call_args.kwargs['env'])
        with self.assertRaises(ValueError):
            bootstrap.role_jobs({'HASLA_ROLE_JOBS': json.dumps([{**job, 'training_profile': PROFILE}])})

    def test_every_expert_tensor_requires_real_packed_nf4_state(self):
        model, blocks = synthetic_model()
        self.assertEqual(train_lora.gemma_quantized_expert_proof(model, Packed)['quantized_expert_tensors'], 60)
        for mutate in (lambda p: setattr(p, 'quant_state', None), lambda p: setattr(p, 'requires_grad', True),
                       lambda p: setattr(p, 'device', NS(type='cpu', index=None)),
                       lambda p: setattr(p, 'numel', lambda: math.prod(p._original_shape) * 2),
                       lambda p: setattr(p.quant_state, 'quant_type', 'fp4')):
            model, blocks = synthetic_model()
            mutate(blocks[-1].down_proj)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                train_lora.gemma_quantized_expert_proof(model, Packed)
        model, blocks = synthetic_model()
        blocks.pop()
        with self.assertRaises(ValueError):
            train_lora.gemma_quantized_expert_proof(model, Packed)

    def test_single_gpu_and_no_cpu_disk_meta_or_large_gpu_fallback(self):
        model, blocks = synthetic_model()
        torch = synthetic_torch()
        self.assertEqual(train_lora.gemma_single_gpu_proof(torch, model)['gpu_name'], GPU)
        for change in ({'device_count': lambda: 2},
                       {'get_device_properties': lambda _: NS(name='NVIDIA H200', total_memory=141 * 1024**3)}):
            with patch.dict(torch.cuda.__dict__, change), self.assertRaises(ValueError):
                train_lora.gemma_single_gpu_proof(torch, model)
        for mapping in ({'': 'cpu'}, {'': 'disk'}):
            model.hf_device_map = mapping
            with self.assertRaises(ValueError):
                train_lora.gemma_single_gpu_proof(torch, model)

    def test_first_step_memory_is_captured_once_and_validated_in_worker_report(self):
        config = role_config.get_role_config('chat', PROFILE)
        summary = {**train_lora.gemma_single_gpu_proof(synthetic_torch()),
                   **train_lora.gemma_quantized_expert_proof(synthetic_model()[0], Packed)}
        callback = train_lora.gemma_first_step_callback(object, summary, synthetic_torch())
        callback.on_step_end(None, NS(global_step=1), NS())
        first = summary['first_step_peak_reserved_bytes']
        callback.on_step_end(None, NS(global_step=2), NS())
        self.assertEqual(summary['first_step_peak_reserved_bytes'], first)
        report = {**summary, 'training_profile': PROFILE, 'role': 'chat', 'base_model': config['base_model'],
                  'format': 'chat', 'precision': '4bit', 'training_method': 'qlora', 'rank': 8,
                  'max_length': 1024, 'max_steps': config['max_steps'], 'training_sha256': '1' * 64,
                  'validation_sha256': '2' * 64, 'steps_completed': 1, 'weights_updated': True,
                  'expert_quantizer_module_sha256': 'a' * 64, 'unsloth_zoo_version': '2026.11.2',
                  'expert_quantizer_upstream_fix': '9adee9372d5d86749e757d5a91c6bfa30c2ff674'}
        target = self.root / 'hasla_training_manifest.json'
        target.write_text(json.dumps(report))
        checked = pod.training_report(self.root, config, 'chat', '1' * 64, '2' * 64)
        self.assertTrue(checked['expert_quantization_verified'])
        self.assertEqual(checked['physical_vram_bytes'], 48 * 1024**3)
        for key, value in [('quantized_expert_tensors', 59), ('expert_quantization_verified', 1),
                           ('gpu_count', 2), ('gpu_name', 'NVIDIA H200'),
                           ('first_step_peak_reserved_bytes', 80 * 1024**3),
                           ('expert_quantizer_module_sha256', None), ('unsloth_zoo_version', 'raw arbitrary text'),
                           ('first_optimizer_step_completed', False), ('training_profile', None)]:
            target.write_text(json.dumps({**report, key: value}))
            with self.subTest(key=key), self.assertRaises(pod.PilotError):
                pod.training_report(self.root, config, 'chat', '1' * 64, '2' * 64)

    def test_full_synthetic_trainer_uses_profile_and_saves_actual_proof(self):
        path = self.root / 'synthetic-chat.jsonl'
        path.write_text(json.dumps({'messages': [{'role': 'user', 'content': 'Synthetic question'},
            {'role': 'assistant', 'content': 'Synthetic answer'}],
            'metadata': {'group_id': 'synthetic-training-only', 'split': 'train'}}) + '\n')
        source = self.root / 'synthetic_quantizer.py'
        source.write_text('# synthetic CPU-only quantizer provenance fixture\n')
        quantizer = NS(__file__=str(source), replace_expert_params_with_bnb_params=lambda: None)
        torch = synthetic_torch()
        model, _ = synthetic_model()
        calls = {}
        def save(out):
            Path(out).mkdir()
            (Path(out) / 'adapter_model.safetensors').write_bytes(b'synthetic-not-real-weights')
        model.save_pretrained = save
        processor = NS(eos_token='<eos>', chat_template='synthetic CPU-only template', save_pretrained=lambda _: None)
        class Loader:
            @staticmethod
            def from_pretrained(**kwargs):
                calls['loader'] = kwargs
                return model, processor
            @staticmethod
            def get_peft_model(value, **kwargs):
                calls['peft'] = kwargs
                return value
        class Trainer:
            def __init__(self, **kwargs):
                calls['trainer'] = kwargs
                self.state = NS(global_step=0, max_steps=1, log_history=[{'loss': 1.0}])
                self.callbacks = []
            def add_callback(self, callback):
                self.callbacks.append(callback)
            def train(self):
                self.state.global_step = 1
                for callback in self.callbacks:
                    callback.on_step_end(None, self.state, NS())
                return NS(metrics={'train_loss': 1.0})
        modules = {'unsloth': NS(FastModel=Loader, is_bfloat16_supported=lambda: True), 'torch': torch,
                   'datasets': NS(Dataset=NS(from_list=lambda rows: rows)),
                   'trl': NS(SFTConfig=lambda **kw: NS(**kw), SFTTrainer=Trainer),
                   'transformers': NS(TrainerCallback=object),
                   'unsloth_zoo': NS(), 'unsloth_zoo.temporary_patches': NS(moe_utils_bnb4bit=quantizer),
                   'bitsandbytes': NS(), 'bitsandbytes.nn': NS(Params4bit=Packed)}
        out = self.root / 'adapter'
        with patch.dict(sys.modules, modules), patch('importlib.metadata.version', return_value='2026.11.2'), \
                contextlib.redirect_stdout(io.StringIO()):
            train_lora.main(['--base', 'chat', '--training-profile', PROFILE, '--format', 'chat',
                             '--holdout', '0', '--max-steps', '1', '--assistant-only-loss', 'off', str(path), str(out)])
        report = json.loads((out / 'hasla_training_manifest.json').read_text())
        self.assertEqual((report['base_model'], report['training_profile'], report['precision']),
                         ('google/gemma-4-26B-A4B-it', PROFILE, '4bit'))
        self.assertEqual(report['expert_blocks'], 30)
        self.assertEqual(report['quantized_expert_tensors'], 60)
        self.assertTrue(report['first_optimizer_step_completed'])
        self.assertEqual(report['expert_quantizer_module_sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(calls['loader']['device_map'], {'': 0})
        self.assertFalse(calls['loader']['load_in_16bit'])
        self.assertTrue(calls['trainer']['args'].bf16)
        self.assertTrue(report['weights_updated'])
        self.assertEqual(report['label_diagnostics']['assistant_loss_status'], 'explicit_full_sequence_loss')
        self.assertEqual(report['label_diagnostics']['selected_template_sha256'],
                         hashlib.sha256(processor.chat_template.encode()).hexdigest())


if __name__ == '__main__':
    unittest.main()

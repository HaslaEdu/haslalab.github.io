"""Synthetic rank8 continuation contracts; never loads a model, GPU or SDK."""
import copy
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import private_dual_pod as bootstrap
import private_dual_run as parent
import private_pod_train as pod
import private_resume_adapter as resume
import private_verify_adapter as verify
from role_config import get_role_config, GEMMA_26B_QLORA_V1 as PROFILE
import train_lora as train
import test_private_resume_adapter as af
import test_private_verify_adapter as vf
from test_private_dual_run import fixture as input_fixture
from test_gemma_training_profile import synthetic_model, synthetic_torch, Packed
from test_gemma_formatter import formatter_receipt, labels


def chat_source(model=None):
    model = model or af.container([('base.experts.lora_A.weight', 'F32', [2, 8, 1], [1] * 16),
                                  ('base.experts.lora_B.weight', 'F32', [2, 1, 8], [1] * 16)])
    blobs = {'adapter_config.json': json.dumps({'peft_type': 'LORA', 'r': 8,
        'base_model_name_or_path': 'google/gemma-4-26B-A4B-it'}).encode(), 'adapter_model.safetensors': model}
    inventory = [{'name': n, 'bytes': len(blobs[n]), 'sha256': af.sha(blobs[n])} for n in resume.FILES]
    spec = {'kind': resume.KIND, 'version': 1, 'role': 'chat', 'rank': 8,
        'base_model': 'google/gemma-4-26B-A4B-it', 'source_training_run_id': '122',
        'entity': 'fixture-entity', 'artifact': 'fixture-entity/hasla-ai-private-training/hasla-private-books-122-chat-lora:v0',
        'files': inventory, 'adapter_inventory_sha256': resume._inventory_sha(inventory)}
    return spec, blobs


def skipped(initial):
    return {'version': 1, 'baseline_eval_loss': None, 'baseline_method': 'continued_adapter_baseline_not_measured_v1',
        'same_validation_sha256': '2' * 64, 'validation_records': 1,
        'initial_adapter_model_sha256': initial, 'reason': 'nonzero_adapter_continuation'}


class GemmaContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.config = get_role_config('chat', PROFILE)
        self.spec, self.blobs = chat_source()

    def test_fixed_profile_role_rank_base_and_artifact_namespace(self):
        self.assertEqual(resume.validate_spec(self.spec, self.config)['rank'], 8)
        for config in (get_role_config('chat'), get_role_config('solver'),
                       {**self.config, 'default_rank': 16}, {**self.config, 'load_in_4bit': False}):
            with self.subTest(config=config['role']), self.assertRaises(resume.ResumeError):
                resume.validate_spec(self.spec, config)
        for field, value in (('rank', 16), ('role', 'solver'), ('base_model', 'Qwen/QwQ-32B'),
                             ('artifact', self.spec['artifact'].replace('-chat-', '-solver-'))):
            with self.subTest(field=field), self.assertRaises(resume.ResumeError):
                resume.validate_spec({**self.spec, field: value}, self.config)

    def test_private_two_file_download_requires_chat_nf4_source_metadata(self):
        fixture = vf.Fixture('chat', model=self.blobs['adapter_model.safetensors'])
        original_ref = fixture.results['chat']['artifact']; artifact = fixture.artifacts[original_ref]
        self.spec['files'] = fixture.results['chat']['adapter_files']
        self.spec['adapter_inventory_sha256'] = fixture.results['chat']['adapter_sha256']
        artifact.qualified_name = self.spec['artifact']; artifact.manifest.entries.pop('do-not-download.txt')
        artifact.metadata.update(training_profile=PROFILE, precision='4bit', training_method='qlora')
        api = NS(artifact=Mock(return_value=artifact))
        result = resume.download_initial_adapter(self.spec, self.config, self.root / 'initial', api, lambda _: True)
        self.assertEqual(result['role'], 'chat'); self.assertEqual(result['rank'], 8)
        self.assertFalse(result['optimizer_state_restored']); self.assertFalse(result['relative_weight_change_verified'])
        for field, value in (('role', 'solver'), ('rank', 16), ('training_profile', None)):
            changed = dict(artifact.metadata); artifact.metadata[field] = value
            with self.subTest(field=field), self.assertRaises(resume.ResumeError):
                resume.download_initial_adapter(self.spec, self.config, self.root / ('bad-' + field), api, lambda _: True)
            artifact.metadata = changed

    def test_gemma_alternate_initializer_is_rejected_before_model_loading(self):
        initial = self.root / 'initial'; initial.mkdir()
        for name, raw in self.blobs.items(): (initial / name).write_bytes(raw)
        config = json.loads(self.blobs['adapter_config.json'])
        for initializer in ('pissa', 'olora', False):
            (initial / 'adapter_config.json').write_text(json.dumps({**config, 'init_lora_weights': initializer}))
            with self.subTest(initializer=initializer), self.assertRaises(ValueError):
                train.initial_adapter(initial, self.config, 8, self.root / 'output')

    def test_all_530_rank8_tensors_with_3d_and_folded_experts_have_relative_update_evidence(self):
        tensors = []
        for i in range(265):
            stem = f'base.layers.{i}.experts' if i < 60 else f'base.layers.{i}.attn'
            ashape, bshape, count = ([2, 8, 1], [2, 1, 8], 16) if i < 30 else (
                ([16, 1], [1, 16], 16) if i < 60 else ([8, 1], [1, 8], 8))
            tensors += [(stem + '.lora_A.weight', 'F32', ashape, [1] * count),
                        (stem + '.lora_B.weight', 'F32', bshape, [1] * count)]
        before = self.root / 'before.safetensors'; after = self.root / 'after.safetensors'
        before.write_bytes(af.container(tensors)); after.write_bytes(af.container(tensors))
        self.assertEqual(verify.inspect_safetensors(before, 8, 2 * 1024**3)['tensor_count'], 530)
        self.assertFalse(resume.compare_lora_b(before, after, 8)['weights_updated'])
        tensors[1] = (*tensors[1][:3], [2] + [1] * 15); after.write_bytes(af.container(tensors))
        proof = resume.compare_lora_b(before, after, 8)
        self.assertTrue(proof['relative_weight_change_verified']); self.assertEqual(proof['standard_b_changed_tensors'], 1)

    def test_manifest_and_bootstrap_accept_only_pinned_chat_nf4_continuation(self):
        env, manifest = input_fixture(); manifest.update(selected_roles=['chat'], budget_krw=100000,
            authorized_budget_krw=100000, prior_upper_krw=0, resume_script_sha256='a' * 64)
        spec = manifest['roles']['chat']; spec.update(training_profile=PROFILE, initial_adapter=self.spec,
            gpu_ids=['NVIDIA A40'], gpu_usd_per_hour_upper='1.2')
        checked, _ = parent.load_inputs({**env, 'HASLA_DUAL_MANIFEST': json.dumps(manifest)})
        self.assertEqual(checked['roles']['chat']['initial_adapter']['rank'], 8)
        job = {'role': 'chat', 'format': 'chat', 'training_profile': PROFILE, 'run': 'fixture-chat',
            'input_artifact': 'fixture/private/data:v0', 'training_sha256': '1' * 64,
            'validation_sha256': '2' * 64, 'initial_adapter': self.spec}
        self.assertEqual(bootstrap.role_jobs({'HASLA_ROLE_JOBS': json.dumps([job]),
            'HASLA_RESUME_SCRIPT_SHA256': 'a' * 64})[0]['initial_adapter']['role'], 'chat')
        spec.pop('training_profile')
        with self.assertRaises((ValueError, resume.ResumeError)): parent.load_inputs({**env, 'HASLA_DUAL_MANIFEST': json.dumps(manifest)})

    def test_skip_baseline_is_explicit_null_loss_same_validation_and_pinned_initial_weights(self):
        report = {'formatter_provenance': formatter_receipt(), 'label_diagnostics': labels(),
            'initial_adapter_model_sha256': 'a' * 64, 'optimizer_state_restored': False,
            'baseline_evaluation': skipped('a' * 64)}
        for validator in (pod.validated_gemma_receipts, verify.validated_gemma_receipts):
            checked = validator(report, 'chat', PROFILE, 2, 1, '2' * 64)
            self.assertIsNone(checked['baseline_evaluation']['baseline_eval_loss'])
            for field, value in (('baseline_eval_loss', 1.0), ('same_validation_sha256', 'b' * 64),
                                 ('initial_adapter_model_sha256', 'b' * 64), ('validation_records', True), ('zero_b_tensors', 1)):
                bad = copy.deepcopy(report); bad['baseline_evaluation'][field] = value
                with self.subTest(field=field), self.assertRaises(ValueError): validator(bad, 'chat', PROFILE, 2, 1)

    def test_official_grouped_and_clippable_attach_restores_method_and_never_reinitializes(self):
        calls = []; model = object(); grouped = object()
        class Clippable:
            linear = object()
        class Lora:
            def _create_and_replace(self, *args, **kwargs): calls.append(('replace', args)); return None
        original = Lora._create_and_replace
        def attach(value, path, **kwargs):
            calls.append(('peft', value, path, kwargs)); Lora()._create_and_replace(None, 'default', Clippable(), 'gate', None)
            return value
        registry = Mock(return_value=grouped)
        modules = {'peft': NS(PeftModel=NS(from_pretrained=attach)), 'peft.tuners': NS(), 'peft.tuners.lora': NS(),
            'peft.tuners.lora.model': NS(LoraModel=Lora), 'transformers.models': NS(), 'transformers.models.gemma4': NS(),
            'transformers.models.gemma4.modeling_gemma4': NS(Gemma4ClippableLinear=Clippable),
            'unsloth.models': NS(), 'unsloth.models.grouped_linear_lora': NS(register_grouped_linear_lora_for_adapter=registry)}
        post = Mock(side_effect=lambda value, **_: value)
        with patch.dict(sys.modules, modules):
            self.assertIs(train.attach_gemma_continuation(model, self.root, NS(post_patch_model=post)), model)
        registry.assert_called_once_with(model, str(self.root), local_files_only=True)
        peft = next(x for x in calls if x[0] == 'peft')
        self.assertEqual(peft[3], {'is_trainable': True, 'local_files_only': True, 'trust_remote_code': False, 'config': grouped})
        self.assertIs(next(x for x in calls if x[0] == 'replace')[1][2], Clippable.linear)
        self.assertIs(Lora._create_and_replace, original); post.assert_called_once()

    def test_quantized_base_expert_objects_are_retained_through_adapter_wrappers(self):
        model, _ = synthetic_model(); _, weights = train.gemma_continuation_expert_snapshot(model, Packed)
        train.verify_retained_gemma_experts(model, weights, Packed)
        retained = list(model.parameters()); model.parameters = lambda: retained[:-1]
        with self.assertRaises(ValueError): train.verify_retained_gemma_experts(model, weights, Packed)

    def test_chat_inventory_export_and_continued_cpu_verifier_require_actual_relative_b_change(self):
        for changed in (False, True):
            before = af.container([('base.experts.lora_A.weight', 'F32', [2, 8, 1], [1] * 16),
                                   ('base.experts.lora_B.weight', 'F32', [2, 1, 8], [1] * 16)])
            after = af.container([('base.experts.lora_A.weight', 'F32', [2, 8, 1], [1] * 16),
                                  ('base.experts.lora_B.weight', 'F32', [2, 1, 8], ([2] + [1] * 15) if changed else [1] * 16)])
            current, initial = vf.Fixture('chat', model=after), vf.Fixture('chat', model=before)
            spec, _ = chat_source(before)
            source = initial.results['chat']; spec.update(files=source['adapter_files'], adapter_inventory_sha256=source['adapter_sha256'])
            artifact = initial.artifacts[source['artifact']]; artifact.qualified_name = spec['artifact']
            artifact.manifest.entries.pop('do-not-download.txt')
            artifact.metadata.update(training_profile=PROFILE, precision='4bit', training_method='qlora')
            current.artifacts[spec['artifact']] = artifact
            from test_gemma_formatter import GemmaFormatterTests
            _, report = GemmaFormatterTests().complete_report()
            result = current.results['chat']
            result.update(training_profile=PROFILE, precision='4bit', training_method='qlora', format='chat',
                training_records=2, validation_records=1, initial_adapter=spec,
                initial_adapter_model_sha256=spec['files'][1]['sha256'], optimizer_state_restored=False,
                resume_script_sha256=af.sha(Path(resume.__file__).read_bytes()),
                runtime_profile_proof={k: report[k] for k in pod.runtime_profile_proof_keys(PROFILE)},
                formatter_provenance=formatter_receipt(), label_diagnostics=labels(),
                baseline_evaluation=skipped(spec['files'][1]['sha256']))
            current.artifacts[result['artifact']].metadata.update(result)
            outcome = verify.verify('123', 'chat', {'WANDB_API_KEY': 'synthetic'},
                reader_factory=lambda _: current, sdk_factory=lambda _: current, continuation_inventory=True)
            row = outcome['roles'][0]
            self.assertEqual(row['weights_updated'], changed)
            self.assertEqual(row['status'], 'verified' if changed else 'failed')
            self.assertEqual(row['rank'], 8); self.assertIn('adapter_files', row)
            self.assertEqual(row['baseline_evaluation']['baseline_method'], 'continued_adapter_baseline_not_measured_v1')
            if changed:
                for helper_pin in (verify.LEGACY_QWQ_CONTINUATION_HELPER_SHA256, 'f' * 64):
                    result['resume_script_sha256'] = helper_pin
                    current.artifacts[result['artifact']].metadata['resume_script_sha256'] = helper_pin
                    rejected = verify.verify('123', 'chat', {'WANDB_API_KEY': 'synthetic'},
                        reader_factory=lambda _: current, sdk_factory=lambda _: current)
                    self.assertEqual(rejected['roles'][0]['code'], 'continuation_helper_pin_mismatch')

    def test_only_the_exact_reviewed_legacy_solver_helper_is_compatible(self):
        from test_private_training_continuation import continued_verifier, verify_fixture
        for pin, accepted in ((verify.LEGACY_QWQ_CONTINUATION_HELPER_SHA256, True), ('f' * 64, False)):
            fixture = continued_verifier(True); result = fixture.results['solver']
            result['resume_script_sha256'] = pin
            fixture.artifacts[result['artifact']].metadata['resume_script_sha256'] = pin
            event = verify_fixture(fixture)
            self.assertEqual(event['all_verified'], accepted)
            if not accepted: self.assertEqual(event['roles'][0]['code'], 'continuation_helper_pin_mismatch')

    def test_full_synthetic_trainer_loads_original_google_base_attaches_nonzero_and_uses_fresh_optimizer(self):
        initial = self.root / 'initial'; initial.mkdir()
        for name, raw in self.blobs.items(): (initial / name).write_bytes(raw)
        train_file, held_file = self.root / 'train.jsonl', self.root / 'held.jsonl'
        for path, split in ((train_file, 'train'), (held_file, 'validation')):
            path.write_text(json.dumps({'messages': [{'role': 'user', 'content': 'Synthetic ' + split},
                {'role': 'assistant', 'content': 'Synthetic answer'}],
                'metadata': {'group_id': 'synthetic-' + split, 'split': split}}) + '\n')
        module = self.root / 'synthetic_quantizer.py'; module.write_text('# synthetic only\n')
        quantizer = NS(__file__=str(module), replace_expert_params_with_bnb_params=lambda: None)
        model, _ = synthetic_model(); calls = {}; adapters = []
        model.named_parameters = lambda: [('base.lora_A.default.weight', p) if i == 0 else
            ('base.lora_B.default.weight', p) for i, p in enumerate(adapters)]
        original_parameters = list(model.parameters())
        model.parameters = lambda: original_parameters + adapters
        processor = NS(eos_token='<eos>', chat_template='synthetic', save_pretrained=lambda _: None)
        class Loader:
            @staticmethod
            def from_pretrained(**kwargs): calls['load'] = kwargs; return model, processor
            @staticmethod
            def get_peft_model(*args, **kwargs): raise AssertionError('must not initialize a new LoRA')
        def attach(value, path, loader):
            calls['attach'] = (value, path, loader)
            adapters.extend([NS(requires_grad=True, device=NS(type='cuda', index=0), value=17),
                             NS(requires_grad=True, device=NS(type='cuda', index=0), value=23)])
            return value
        def save(path):
            Path(path).mkdir(); (Path(path) / 'adapter_model.safetensors').write_bytes(b'synthetic-new-weights')
        model.save_pretrained = save
        class Trainer:
            def __init__(self, **kwargs):
                calls['trainer'] = kwargs; self.state = NS(global_step=0, max_steps=1, log_history=[]); self.callbacks=[]
            def add_callback(self, value): self.callbacks.append(value)
            def train(self, *args, **kwargs):
                calls['train_call'] = (args, kwargs); self.asserted_nonzero = adapters[1].value == 23
                if not self.asserted_nonzero: raise AssertionError('loaded B was reset')
                self.state.global_step=1
                for callback in self.callbacks: callback.on_step_end(None, self.state, NS())
                return NS(metrics={'train_loss':1.0})
            def evaluate(self): return {'eval_loss':1.0}
        modules = {'unsloth':NS(FastModel=Loader, is_bfloat16_supported=lambda:True, chat_templates=NS()),
            'torch':synthetic_torch(), 'datasets':NS(Dataset=NS(from_list=lambda rows:rows)),
            'trl':NS(SFTConfig=lambda **kwargs:NS(**kwargs), SFTTrainer=Trainer), 'transformers':NS(TrainerCallback=object),
            'unsloth_zoo':NS(), 'unsloth_zoo.temporary_patches':NS(moe_utils_bnb4bit=quantizer),
            'bitsandbytes':NS(), 'bitsandbytes.nn':NS(Params4bit=Packed)}
        output = self.root / 'continued'
        with patch.dict(sys.modules, modules), patch('importlib.metadata.version', return_value='2026.11.2'), \
                patch.object(train, 'attach_gemma_continuation', side_effect=attach), \
                patch.object(train, 'fresh_zero_b_tensors', side_effect=AssertionError('nonzero continuation is not a fresh baseline')), \
                patch.object(train, 'configure_gemma_formatter', return_value=(processor,
                    {'selected_template_sha256': hashlib.sha256(processor.chat_template.encode()).hexdigest()})), \
                contextlib.redirect_stdout(io.StringIO()):
            train.main(['--base','chat','--training-profile',PROFILE,'--format','chat','--max-steps','1',
                '--assistant-only-loss','off','--resume-adapter',str(initial),'--validation-data',str(held_file),str(train_file),str(output)])
        report=json.loads((output/'hasla_training_manifest.json').read_text())
        self.assertEqual(calls['load']['model_name'],'google/gemma-4-26B-A4B-it')
        self.assertTrue(calls['load']['load_in_4bit']); self.assertFalse(calls['load']['load_in_16bit'])
        self.assertEqual(calls['attach'][1],initial); self.assertEqual(calls['train_call'],((),{}))
        self.assertFalse(report['optimizer_state_restored']); self.assertEqual(report['rank'],8)
        self.assertEqual(report['baseline_evaluation']['baseline_eval_loss'],None)
        self.assertEqual(report['initial_adapter_model_sha256'],self.spec['files'][1]['sha256'])
        self.assertEqual((initial/'adapter_model.safetensors').read_bytes(),self.blobs['adapter_model.safetensors'])


if __name__ == '__main__': unittest.main()

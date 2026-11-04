"""Pure synthetic official-helper contracts. No real tokenizer/corpus/model/GPU/API."""
import copy
import hashlib
import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import private_pod_train as pod
import private_verify_adapter as verify
import role_config
import train_lora as train
import test_private_verify_adapter as fixtures


SELECTED = '6971ec85ae5b8a161889e66720199f18ccf0ff8232909a01e0bdce244e507ab1'
SOURCE = 'ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4'
EMPTY = '<|channel>thought\n<channel|>'


def formatter_receipt():
    return {'version': 1, 'policy': 'official_unsloth_gemma4_empty_thought_v1', 'helper_module_sha256': 'a' * 64,
        'unsloth_version': '2026.11.2', 'source_template_sha256': SOURCE, 'selected_template_sha256': SELECTED,
        'vocabulary_sha256': 'b' * 64, 'special_tokens_sha256': 'c' * 64, 'processor_wrapper_preserved': True,
        'single_bos_verified': True, 'prefix_consistency_verified': True, 'records_checked': 3,
        'training_records': 2, 'validation_records': 1, 'validation_sha256': '2' * 64, 'enable_thinking': False,
        'official_template_replacement': True, 'upstream_fix': '3182f568d4e2e87b0945168e04f6e6265700f117'}


def baseline_receipt():
    return {'version': 1, 'baseline_eval_loss': 13.0, 'baseline_method': 'fresh_zero_b_before_optimizer_v1',
            'same_validation_sha256': '2' * 64, 'validation_records': 1, 'zero_b_tensors': 1}


def labels():
    return {'version': 1, 'assistant_only_loss': False, 'assistant_loss_status': 'explicit_full_sequence_loss',
            'selected_template_sha256': SELECTED, 'processor_class': 'FixtureProcessor', 'tokenizer_class': 'FixtureTokenizer',
            'mask_probe_dimensions': 0, 'mask_probe_batch_size': 0, 'mask_probe_token_count': 0, 'mask_probe_assistant_tokens': 0}


class Tokenizer:
    bos_token, bos_token_id, eos_token, eos_token_id, pad_token, pad_token_id = '<bos>', 2, '<eos>', 1, '<pad>', 0
    def __init__(self):
        self.chat_template = 'synthetic-source'
        self.vocab = {'<bos>': 2, '<eos>': 1, '<pad>': 0}
    def get_vocab(self):
        return dict(self.vocab)
    def encode(self, text, **kwargs):
        return ([2] if text.startswith('<bos>') else []) + [ord(c) + 10 for c in text.removeprefix('<bos>')]


class Processor:
    def __init__(self):
        self.tokenizer = Tokenizer()
        self.chat_template = 'synthetic-source'
        self.bad_prompt = False
    def apply_chat_template(self, messages, *, tokenize, add_generation_prompt, enable_thinking, preserve_thinking):
        if tokenize or enable_thinking or preserve_thinking:
            raise AssertionError('unexpected formatting mode')
        text = '<bos>'
        selected = self.chat_template == 'synthetic-selected'
        for message in messages:
            role = 'model' if message['role'] == 'assistant' else message['role']
            text += '<|turn>' + role + '\n' + (EMPTY if selected and role == 'model' else '')
            text += message['content'].strip() + '<turn|>\n'
        if add_generation_prompt:
            text += '<|turn>model\n' + (EMPTY if selected else '')
            if self.bad_prompt:
                text += 'bad'
        return text


class Scalar:
    def __init__(self, value):
        self.value = value
    def item(self):
        return self.value
    def all(self):
        return self


class Tensor:
    requires_grad = True
    def __init__(self, value=0.0):
        self.value = value
    def detach(self):
        return self
    def numel(self):
        return 1
    def isfinite(self):
        return Scalar(math.isfinite(self.value))
    def count_nonzero(self):
        return Scalar(int(self.value != 0))


class GemmaFormatterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def configure(self, mutation=None):
        source = self.root / 'synthetic-official-module.py'
        source.write_text('# synthetic source only\n')
        processor = Processor()
        calls = []
        def official(value, **kwargs):
            calls.append(kwargs)
            value.chat_template = value.tokenizer.chat_template = 'synthetic-selected'
            return mutation(value) if mutation else value
        module = NS(__file__=str(source), get_chat_template=official)
        row = lambda q: {'messages': [{'role': 'user', 'content': q}, {'role': 'assistant', 'content': 'Synthetic answer'}]}
        training, validation = [row('Q1'), row('Q2')], [row('Q3')]
        original = json.dumps(training + validation)
        with patch.object(train, 'GEMMA_SOURCE_TEMPLATE_SHA256', hashlib.sha256(b'synthetic-source').hexdigest()), \
                patch.object(train, 'GEMMA_FORMATTER_TEMPLATE_SHA256', hashlib.sha256(b'synthetic-selected').hexdigest()):
            selected, receipt = train.configure_gemma_formatter(processor, training, validation, '2' * 64, module, '2026.11.2')
        self.assertEqual(json.dumps(training + validation), original)
        return processor, selected, receipt, calls, source

    def test_official_helper_preserves_wrapper_vocabulary_special_ids_and_every_provided_prefix(self):
        original, selected, receipt, calls, source = self.configure()
        self.assertIs(selected, original)
        self.assertEqual(calls, [{'chat_template': 'gemma4', 'map_eos_token': False, 'patch_saving': False}])
        self.assertEqual(receipt['records_checked'], 3)
        self.assertEqual(receipt['helper_module_sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertTrue(receipt['official_template_replacement'])
        self.assertTrue(receipt['prefix_consistency_verified'])
        self.assertNotIn('Synthetic answer', json.dumps(receipt))

    def test_replaced_wrapper_mutated_vocabulary_or_special_ids_or_bad_prefix_fail_closed(self):
        for mutation in (lambda p: Processor(),
                         lambda p: (p.tokenizer.vocab.update({'bad': 10}) or p),
                         lambda p: (setattr(p.tokenizer, 'eos_token_id', 99) or p),
                         lambda p: (setattr(p, 'bad_prompt', True) or p),
                         lambda p: (setattr(p, 'chat_template', 'unreviewed-template') or p)):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.configure(mutation)

    def test_baseline_only_evaluates_fresh_zero_b_without_optimizer_updates(self):
        a, b = Tensor(1.0), Tensor(0.0)
        model = NS(named_parameters=lambda: [('layer.lora_A.default.weight', a), ('layer.lora_B.default.weight', b)])
        calls = []
        trainer = NS(state=NS(global_step=0), optimizer=None,
                     evaluate=lambda **kwargs: (calls.append(kwargs) or {'baseline_eval_loss': 13.0}))
        value = train.evaluate_fresh_gemma_baseline(trainer, model, '2' * 64, 17)
        self.assertEqual(calls, [{'metric_key_prefix': 'baseline_eval'}])
        self.assertEqual(value['validation_records'], 17)
        self.assertEqual(value['zero_b_tensors'], 1)
        self.assertEqual(trainer.state.global_step, 0)
        for mutate in (lambda: setattr(trainer.state, 'global_step', 1), lambda: setattr(trainer, 'optimizer', object()),
                       lambda: setattr(b, 'value', 1.0), lambda: setattr(b, 'value', float('nan'))):
            trainer.state.global_step = 0;trainer.optimizer = None;b.value = 0.0
            mutate()
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                train.evaluate_fresh_gemma_baseline(trainer, model, '2' * 64, 17)
        trainer.state.global_step = 0;trainer.optimizer = None;b.value = 0.0
        def changed(**kwargs):
            b.value = 1.0
            return {'baseline_eval_loss': 1.0}
        trainer.evaluate = changed
        with self.assertRaises(ValueError):
            train.evaluate_fresh_gemma_baseline(trainer, model, '2' * 64, 17)

    def complete_report(self):
        config = role_config.get_role_config('chat', role_config.GEMMA_26B_QLORA_V1)
        report = {'role': 'chat', 'base_model': config['base_model'], 'format': 'chat', 'precision': '4bit',
            'training_method': 'qlora', 'rank': 8, 'max_length': 1024, 'max_steps': config['max_steps'],
            'training_sha256': '1' * 64, 'validation_sha256': '2' * 64, 'steps_completed': 1, 'weights_updated': True,
            'training_profile': role_config.GEMMA_26B_QLORA_V1, 'expert_quantization_verified': True,
            'expert_blocks': 30, 'quantized_expert_tensors': 60, 'first_optimizer_step_completed': True,
            'gpu_count': 1, 'cpu_or_disk_offload_used': False, 'gpu_name': 'NVIDIA A40', 'physical_vram_bytes': 48 * 1024**3,
            'first_step_peak_allocated_bytes': 18 * 1024**3, 'first_step_peak_reserved_bytes': 20 * 1024**3,
            'expert_quantizer_module_sha256': 'a' * 64, 'unsloth_zoo_version': '2026.11.2',
            'expert_quantizer_upstream_fix': '9adee9372d5d86749e757d5a91c6bfa30c2ff674',
            'label_diagnostics': labels(), 'formatter_provenance': formatter_receipt(), 'baseline_evaluation': baseline_receipt()}
        return config, report

    def test_worker_validates_and_preserves_finite_baseline_and_formatter_receipts(self):
        config, report = self.complete_report()
        path = self.root / 'hasla_training_manifest.json'
        path.write_text(json.dumps(report))
        checked = pod.training_report(self.root, config, 'chat', '1' * 64, '2' * 64, training_records=2, validation_records=1)
        self.assertEqual(checked['baseline_evaluation'], baseline_receipt())
        self.assertEqual(checked['formatter_provenance'], formatter_receipt())
        for target, key, value in [('formatter_provenance', 'processor_wrapper_preserved', False),
                                  ('formatter_provenance', 'selected_template_sha256', 'a' * 64),
                                  ('formatter_provenance', 'records_checked', 4),
                                  ('formatter_provenance', 'raw_text', 'PRIVATE'),
                                  ('baseline_evaluation', 'baseline_eval_loss', float('nan')),
                                  ('baseline_evaluation', 'same_validation_sha256', '3' * 64),
                                  ('baseline_evaluation', 'baseline_method', 'unknown'),
                                  ('baseline_evaluation', 'zero_b_tensors', 0)]:
            bad = copy.deepcopy(report);bad[target][key] = value;path.write_text(json.dumps(bad))
            with self.subTest(target=target, key=key), self.assertRaises(pod.PilotError):
                pod.training_report(self.root, config, 'chat', '1' * 64, '2' * 64, training_records=2, validation_records=1)

    def test_cpu_verifier_keeps_old_artifacts_and_binds_optional_new_receipts(self):
        self.assertEqual(fixtures.Fixture().run()['roles'][0]['status'], 'verified')
        _, report = self.complete_report()
        for mode in ('valid', 'missing_metadata', 'changed_baseline', 'unexpected_qwq'):
            fixture = fixtures.Fixture('solver' if mode == 'unexpected_qwq' else 'chat')
            role = 'solver' if mode == 'unexpected_qwq' else 'chat'
            result = fixture.results[role]
            result.update({key: report[key] for key in ('training_profile', 'format', 'precision', 'training_method',
                'label_diagnostics', 'formatter_provenance', 'baseline_evaluation')})
            result.update(training_records=2, validation_records=1)
            if mode == 'unexpected_qwq':
                result['training_profile'] = role_config.QWQ_32B_QLORA_48GB_V1
            result['runtime_profile_proof'] = {k: report[k] for k in pod.runtime_profile_proof_keys(role_config.GEMMA_26B_QLORA_V1)}
            artifact = fixture.artifacts[result['artifact']]
            artifact.metadata.update({key: copy.deepcopy(value) for key, value in result.items() if key not in ('status', 'artifact', 'adapter_files')})
            if mode == 'missing_metadata':
                artifact.metadata.pop('formatter_provenance')
            if mode == 'changed_baseline':
                artifact.metadata['baseline_evaluation']['baseline_eval_loss'] = 1.0
            value = fixture.run(role)['roles'][0]
            with self.subTest(mode=mode):
                self.assertEqual(value['status'], 'verified' if mode == 'valid' else 'failed')
                if mode == 'valid':
                    self.assertEqual(value['baseline_evaluation'], baseline_receipt())
                else:
                    self.assertEqual(fixture.downloads, [])


if __name__ == '__main__':
    unittest.main()

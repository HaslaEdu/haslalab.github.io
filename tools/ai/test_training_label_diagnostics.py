"""Synthetic CPU label-probe and private-receipt tests; no corpus/model/GPU/API."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace as NS
import sys
import unittest
from unittest.mock import patch

import private_pod_train as pod
import private_verify_adapter as verify
import role_config
import train_lora as train
import test_private_pod_train as pod_fixtures
import test_private_verify_adapter as verify_fixtures
import test_train_lora_data as train_fixtures


TEMPLATE = '{% generation %}synthetic answer{% endgeneration %}'


def diagnostic(data_format='chat'):
    value = {'version': 1, 'assistant_only_loss': True, 'assistant_loss_status': 'library_generation_mask_verified',
            'selected_template_sha256': hashlib.sha256(TEMPLATE.encode()).hexdigest(),
            'processor_class': 'SyntheticProcessor', 'tokenizer_class': 'SyntheticTokenizer',
            'mask_probe_dimensions': 2, 'mask_probe_batch_size': 1,
            'mask_probe_token_count': 4, 'mask_probe_assistant_tokens': 2}
    if data_format == 'text':
        value.update(assistant_only_loss=False, assistant_loss_status='plain_text_full_sequence_loss',
                     selected_template_sha256=None, mask_probe_dimensions=0, mask_probe_batch_size=0,
                     mask_probe_token_count=0, mask_probe_assistant_tokens=0)
    return value


class LabelDiagnosticsTests(unittest.TestCase):
    def probe(self, mask, tokens):
        def apply(*args, **kwargs):
            self.last_probe_kwargs = kwargs
            return {'assistant_masks': mask, 'input_ids': tokens}
        processor = NS(chat_template=TEMPLATE, apply_chat_template=apply)
        counts = {}
        enabled, template, reason = train.assistant_loss_support(processor, probe=counts)
        return enabled, template, reason, counts

    def test_flat_and_exact_single_batch_masks_preserve_selectivity(self):
        for dimensions, mask, tokens in ((1, [0, 0, 1, 1], [1, 2, 3, 4]),
                                         (2, [[0, 0, 1, 1]], [[1, 2, 3, 4]])):
            with self.subTest(dimensions=dimensions):
                enabled, template, reason, counts = self.probe(mask, tokens)
                self.assertTrue(enabled)
                self.assertEqual(template, TEMPLATE)
                self.assertEqual(reason, 'library_generation_mask_verified')
                self.assertIsNone(self.last_probe_kwargs['return_tensors'])
                self.assertEqual(counts, {'mask_probe_dimensions': dimensions, 'mask_probe_batch_size': 1,
                                         'mask_probe_token_count': 4, 'mask_probe_assistant_tokens': 2})

    def test_multi_ragged_nonbinary_misaligned_or_nonselective_masks_are_rejected(self):
        cases = [([[0, 1], [0, 1]], [[1, 2], [3, 4]]),
                 ([[[0, 1]]], [[1, 2]]), ([[0, 1]], [1, 2]),
                 ([0, 1], [[1, 2]]), ([0, 1, 1], [1, 2]),
                 ([0, 2], [1, 2]), ([0, 1.0], [1, 2]), ([0, 1], ['private text', 2]),
                 ([0, 0], [1, 2]), ([1, 1], [1, 2]), ([], [])]
        for mask, tokens in cases:
            with self.subTest(mask=mask, tokens=tokens):
                enabled, selected, reason, counts = self.probe(mask, tokens)
                self.assertFalse(enabled)
                self.assertIsNone(selected)
                self.assertIn(reason, {'generation_mask_shape_invalid', 'generation_mask_not_selective'})
                self.assertTrue(all(type(value) is int for value in counts.values()))
                self.assertNotIn('private text', json.dumps(counts))

    def test_template_hash_safe_classes_and_numeric_probe_are_the_only_diagnostics(self):
        enabled, _, reason, counts = self.probe([[0, 0, 1, 1]], [[1, 2, 3, 4]])
        processor = NS(chat_template=TEMPLATE, tokenizer=NS())
        value = train.label_diagnostics(processor, enabled, reason, counts, 'chat')
        self.assertEqual(value['selected_template_sha256'], hashlib.sha256(TEMPLATE.encode()).hexdigest())
        self.assertEqual(value['processor_class'], 'SimpleNamespace')
        self.assertEqual(value['tokenizer_class'], 'SimpleNamespace')
        self.assertNotIn(TEMPLATE, json.dumps(value))
        self.assertEqual(pod.validated_label_diagnostics(value, 'chat'), value)
        self.assertEqual(verify.validated_label_diagnostics(value, 'chat'), value)
        bad_class = type('private class path must not emit', (), {'chat_template': TEMPLATE})()
        self.assertEqual(train.label_diagnostics(bad_class, enabled, reason, counts, 'chat')['processor_class'], 'unknown')

    def test_invalid_status_raw_keys_and_false_proof_are_rejected_by_both_consumers(self):
        for change in ({'assistant_loss_status': 'PRIVATE_RAW_TEXT'}, {'assistant_loss_status': {}},
                       {'raw_token_ids': [1, 2]}, {'selected_template_sha256': 'bad'},
                       {'selected_template_sha256': None}, {'processor_class': '/private/path'},
                       {'mask_probe_dimensions': 3}, {'mask_probe_batch_size': 2},
                       {'mask_probe_token_count': True}, {'mask_probe_assistant_tokens': 4},
                       {'assistant_only_loss': False}, {'version': True}):
            value = {**diagnostic(), **change}
            for consumer in (pod.validated_label_diagnostics, verify.validated_label_diagnostics):
                with self.subTest(change=change, consumer=consumer.__module__), self.assertRaises(ValueError):
                    consumer(value, 'chat')

    def test_private_worker_binds_diagnostics_to_metadata_and_result(self):
        harness = pod_fixtures.PrivatePodTests('test_success_only_uploads_adapter_and_safe_exact_result')
        harness.setUp()
        self.addCleanup(harness.doCleanups)
        value = diagnostic('text')
        def runner(command, **kwargs):
            result = harness.runner(command, **kwargs)
            report = harness.root / 'adapter' / 'hasla_training_manifest.json'
            content = json.loads(report.read_text())
            report.write_text(json.dumps({**content, 'label_diagnostics': value}))
            return result
        result = pod.run_pilot(harness.env, harness.root, harness.wandb, harness.opener, runner)
        self.assertEqual(result['status'], 'uploaded')
        self.assertEqual(result['label_diagnostics'], value)
        self.assertEqual(harness.wandb.run.artifacts[0][0].metadata['label_diagnostics'], value)
        self.assertEqual(json.loads(harness.wandb.run.summary['private_training_result_json'])['label_diagnostics'], value)
        report = harness.root / 'adapter' / 'hasla_training_manifest.json'
        original = json.loads(report.read_text())
        config = pod.data_bounded_settings(role_config.get_role_config('solver'), 1)
        report.write_text(json.dumps({**original, 'label_diagnostics': {**value, 'raw_text': 'PRIVATE'}}))
        with self.assertRaisesRegex(pod.PilotError, 'training_label_diagnostics_invalid'):
            pod.training_report(report.parent, config, 'text', harness.env['HASLA_DATA_SHA256'], None)

    def test_mocked_trainer_records_single_batch_shape_and_effective_mask_setting(self):
        harness = train_fixtures.DatasetChecks('test_mocked_chat_training_uses_structured_data_and_records_actual_steps')
        harness.setUp()
        self.addCleanup(harness.doCleanups)
        data = harness.write('synthetic-label-probe.jsonl', [harness.chat_row('synthetic-only')])
        out = harness.root / 'synthetic-adapter'
        modules, calls = harness.fake_training_modules()
        loader = modules['unsloth'].FastModel
        original = loader.from_pretrained
        def nested_loader(**kwargs):
            model, processor = original(**kwargs)
            processor.apply_chat_template = lambda *a, **k: {'input_ids': [[1, 2, 3, 4]], 'assistant_masks': [[0, 0, 1, 1]]}
            return model, processor
        with patch.dict(sys.modules, modules), patch.object(loader, 'from_pretrained', side_effect=nested_loader), \
                contextlib.redirect_stdout(io.StringIO()):
            train.main(['--base', 'chat', '--format', 'chat', '--holdout', '0', '--max-steps', '2', str(data), str(out)])
        report = json.loads((out / 'hasla_training_manifest.json').read_text())
        value = report['label_diagnostics']
        self.assertTrue(calls['training_options']['assistant_only_loss'])
        self.assertTrue(value['assistant_only_loss'])
        self.assertEqual(value['mask_probe_dimensions'], 2)
        self.assertEqual((value['mask_probe_batch_size'], value['mask_probe_token_count'], value['mask_probe_assistant_tokens']), (1, 4, 2))
        self.assertEqual(pod.validated_label_diagnostics(value, 'chat'), value)

    def test_cpu_verifier_allows_old_missing_pair_and_rejects_one_sided_or_changed_receipts(self):
        old = verify_fixtures.Fixture()
        self.assertEqual(old.run()['roles'][0]['status'], 'verified')
        for mode in ('valid', 'result_only', 'artifact_only', 'changed', 'invalid'):
            fixture = verify_fixtures.Fixture()
            result = fixture.results['chat']
            result['format'] = 'chat'
            artifact = fixture.artifacts[result['artifact']]
            if mode != 'artifact_only':
                result['label_diagnostics'] = diagnostic()
            if mode != 'result_only':
                artifact.metadata['label_diagnostics'] = copy.deepcopy(diagnostic())
            if mode == 'changed':
                artifact.metadata['label_diagnostics']['selected_template_sha256'] = 'a' * 64
            if mode == 'invalid':
                result['label_diagnostics']['arbitrary_raw_text'] = 'PRIVATE_DO_NOT_EMIT'
                artifact.metadata['label_diagnostics'] = copy.deepcopy(result['label_diagnostics'])
            observed = fixture.run()['roles'][0]
            with self.subTest(mode=mode):
                self.assertEqual(observed['status'], 'verified' if mode == 'valid' else 'failed')
                if mode == 'valid':
                    self.assertEqual(observed['label_diagnostics'], diagnostic())
                else:
                    self.assertEqual(fixture.downloads, [])
                self.assertNotIn('PRIVATE_DO_NOT_EMIT', json.dumps(observed))


if __name__ == '__main__':
    unittest.main()

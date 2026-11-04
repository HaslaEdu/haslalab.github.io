import contextlib
import importlib.metadata
import io
import json
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

import private_ocr_probe as probe


SENSITIVE = 'PRIVATE_DATASET_SENTINEL sk-credential-placeholder https://example.invalid/?secret=placeholder nickname-placeholder'


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='hasla-ocr-unit-')
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def versions(self, name):
        if name == 'paddlepaddle-gpu':
            raise importlib.metadata.PackageNotFoundError(name)
        return probe.PINNED_PACKAGES[name]

    def page(self):
        return {'input_path': SENSITIVE, 'model_settings': {'use_layout_detection': True},
                'layout_det_res': {'private_ignored': SENSITIVE},
                'parsing_res_list': [{'block_label': 'text', 'block_content': SENSITIVE},
                                     types.SimpleNamespace(label='display_formula', content='E = mc²')],
                'other_untrusted': SENSITIVE}

    def result(self):
        value = probe.base_summary('succeeded', 'complete')
        value.update(probe.summarize_page(self.page()), initialization_seconds=1.5,
                     prediction_seconds=2.5, total_seconds=4.0)
        return value

    def test_default_plan_imports_no_model_and_rejects_private_input_argument(self):
        stream = io.StringIO()
        with patch.object(probe, 'run_isolated', side_effect=AssertionError('must not execute')):
            with contextlib.redirect_stdout(stream):
                self.assertEqual(probe.main([]), 0)
                self.assertEqual(probe.main(['--input', SENSITIVE]), 2)
        self.assertNotIn(SENSITIVE, stream.getvalue())
        events = [json.loads(line) for line in stream.getvalue().splitlines()]
        self.assertEqual(events[0]['status'], 'prepared')
        self.assertFalse(events[0]['model_downloads_started'])
        self.assertEqual(events[1]['error_code'], 'configuration_invalid')

    def test_pinned_cpu_dependencies_and_python_required(self):
        probe.check_dependencies(self.versions, (3, 11))
        for python, getter, error in [((3, 12), self.versions, 'python_version_mismatch'),
                ((3, 11), lambda name: 'arbitrary-secret-version', 'gpu_package_installed')]:
            with self.subTest(error=error), self.assertRaises(probe.ProbeFailure) as caught:
                probe.check_dependencies(getter, python)
            self.assertEqual(caught.exception.code, error)

    def test_missing_and_mismatched_dependencies_fail_before_model_load(self):
        def missing(name):
            raise importlib.metadata.PackageNotFoundError(SENSITIVE)
        def mismatch(name):
            return self.versions(name) if name != 'paddleocr' else SENSITIVE
        for getter, error in [(missing, 'dependency_missing'), (mismatch, 'dependency_version_mismatch')]:
            result = probe.perform_probe(dependency_checker=lambda: probe.check_dependencies(getter, (3, 11)),
                                         pipeline_factory=lambda **_: self.fail('model initialized'))
            self.assertEqual(result['error_code'], error)
            self.assertNotIn(SENSITIVE, json.dumps(result))

    def test_full_pipeline_and_only_official_fixed_sample(self):
        captured = {}
        def factory(**options):
            captured['options'] = options
            def predict(**arguments):
                captured['predict'] = arguments
                return [self.page()]
            return types.SimpleNamespace(predict=predict)
        result = probe.perform_probe(dependency_checker=lambda: None, pipeline_factory=factory)
        self.assertEqual(captured['options'], probe.PIPELINE_OPTIONS)
        self.assertTrue(captured['options']['use_layout_detection'])
        self.assertEqual(captured['options']['vl_rec_backend'], 'native')
        self.assertEqual(captured['predict'], {'input': probe.DEMO_URL})
        self.assertEqual(result['status'], 'succeeded')
        self.assertEqual(result['blocks'], 2)
        self.assertNotIn(SENSITIVE, json.dumps(result))

    def test_layout_missing_or_empty_recognition_cannot_claim_success(self):
        for page, code in [({**self.page(), 'layout_det_res': None}, 'layout_stage_missing'),
                ({**self.page(), 'model_settings': {'use_layout_detection': False}}, 'layout_stage_missing'),
                ({**self.page(), 'parsing_res_list': []}, 'no_text')]:
            result = probe.perform_probe(dependency_checker=lambda: None,
                pipeline_factory=lambda **_: types.SimpleNamespace(predict=lambda **__: [page]))
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['error_code'], code)

    def test_worker_suppresses_python_logs_and_raw_exceptions(self):
        output, errors = io.StringIO(), io.StringIO()
        def bad_factory(**_):
            print(SENSITIVE)
            import sys
            print(SENSITIVE, file=sys.stderr)
            raise RuntimeError(SENSITIVE)
        path = self.root / 'safe.json'
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = probe.worker_main(path, dependency_checker=lambda: None, pipeline_factory=bad_factory)
        self.assertEqual(code, 1)
        self.assertEqual(output.getvalue(), '')
        self.assertEqual(errors.getvalue(), '')
        text = path.read_text(encoding='utf-8')
        self.assertNotIn(SENSITIVE, text)
        self.assertEqual(json.loads(text)['error_code'], 'pipeline_initialization_failed')

    def test_prediction_exception_contains_no_raw_content(self):
        def predict(**_):
            raise RuntimeError(SENSITIVE)
        result = probe.perform_probe(dependency_checker=lambda: None,
            pipeline_factory=lambda **_: types.SimpleNamespace(predict=predict))
        self.assertEqual(result['error_code'], 'prediction_failed')
        self.assertNotIn(SENSITIVE, json.dumps(result))

    def test_sanitizer_strips_unknown_strings_and_rejects_injected_labels(self):
        value = {**self.result(), 'raw_text': SENSITIVE, 'url': SENSITIVE}
        clean = probe.sanitize_summary(value)
        self.assertNotIn(SENSITIVE, json.dumps(clean))
        for changes in [{'error_code': SENSITIVE}, {'stage': SENSITIVE}, {'characters': float('nan')},
                        {'pages': 2}, {'block_types': {SENSITIVE: 2}}, {'private_inputs_read': 1},
                        {'device': 'gpu'}, {'full_layout_and_vlm_pipeline': False}]:
            with self.subTest(fields=list(changes)), self.assertRaises(probe.ProbeFailure):
                probe.sanitize_summary({**value, **changes})

    def test_isolation_native_output_devnull_and_no_credentials_forwarded(self):
        def runner(command, **options):
            self.assertEqual(options['stdout'], subprocess.DEVNULL)
            self.assertEqual(options['stderr'], subprocess.DEVNULL)
            self.assertEqual(options['stdin'], subprocess.DEVNULL)
            self.assertNotIn('WANDB_API_KEY', options['env'])
            self.assertNotIn('HF_TOKEN', options['env'])
            self.assertEqual(options['env']['CUDA_VISIBLE_DEVICES'], '')
            Path(command[-1]).write_text(json.dumps(self.result()), encoding='utf-8')
            return types.SimpleNamespace(returncode=0)
        with patch.dict('os.environ', WANDB_API_KEY=SENSITIVE, HF_TOKEN=SENSITIVE):
            result = probe.run_isolated(runner=runner)
        self.assertEqual(result['status'], 'succeeded')
        self.assertNotIn(SENSITIVE, json.dumps(result))

    def test_timeout_or_invalid_worker_receipt_is_safe_failure(self):
        def timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(SENSITIVE, 1, output=SENSITIVE, stderr=SENSITIVE)
        self.assertEqual(probe.run_isolated(runner=timeout)['error_code'], 'child_timeout')
        def invalid(command, **kwargs):
            Path(command[-1]).write_text(SENSITIVE, encoding='utf-8')
            return types.SimpleNamespace(returncode=0)
        self.assertEqual(probe.run_isolated(runner=invalid)['error_code'], 'child_invalid_receipt')

    def test_summary_output_does_not_overwrite_existing_file(self):
        target = self.root / 'keep.json'
        target.write_text(SENSITIVE, encoding='utf-8')
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.assertEqual(probe.main(['--output', str(target)]), 1)
        self.assertEqual(target.read_text(encoding='utf-8'), SENSITIVE)
        self.assertNotIn(SENSITIVE, stream.getvalue())
        self.assertEqual(json.loads(stream.getvalue())['error_code'], 'output_write_failed')


if __name__ == '__main__':
    unittest.main()

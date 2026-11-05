import json
from pathlib import Path
import unittest
import private_qwq_dependency_details as details


class Tests(unittest.TestCase):
    def test_standard_public_requirement_messages_become_typed_records(self):
        value = details.parse_lines(b'vllm 0.19.1 has requirement transformers<5,>=4.57.0, but you have transformers 5.17.0.\nfoo 1.0 requires missing-package, which is not installed.\nfoo 1.0 is not supported on this platform\n')
        self.assertEqual([r['kind'] for r in value['requirements']], ['version_mismatch', 'missing_requirement', 'unsupported_platform'])
        self.assertEqual(value['requirements'][0]['requirement'], 'transformers<5,>=4.57.0')
        self.assertEqual(value['unparsed_lines'], 0)

    def test_unrecognized_private_text_is_hashed_not_emitted_and_input_is_bounded(self):
        result = details.parse_lines(b'API_KEY=PRIVATE_RAW https://signed.test\n'+b'x'*70000)
        self.assertNotIn('PRIVATE_RAW', json.dumps(result)); self.assertNotIn('signed.test', json.dumps(result))
        self.assertEqual(result['captured_bytes'], 65536); self.assertTrue(result['output_truncated'])
        self.assertEqual(result['requirements'], []); self.assertLessEqual(len(result['unparsed_line_sha256']), 16)

    def test_strict_output_schema_rejects_arbitrary_fields_credentials_and_raw_lines(self):
        value = {'version': 1, 'kind': 'public_image_pipcheck_details', 'image': details.IMAGE,
            'package_installations': 0, 'model_calls': 0, 'gpu_provider_calls': 0, 'credentials_passed': False,
            'pip_check_exit_code': 1, 'wandb_metadata_version': None,
            'details': details.parse_lines(b'foo 1.0 requires bar, which is not installed.\n')}
        self.assertEqual(details.validate(value), value)
        for bad in ({**value, 'raw_log': 'PRIVATE_RAW'}, {**value, 'credentials_passed': True},
                    {**value, 'pip_check_exit_code': True}, {**value, 'wandb_metadata_version': 'https://private.test'}):
            with self.subTest(bad=bad), self.assertRaises(ValueError): details.validate(bad)

    def test_registered_workflow_has_only_cpu_no_credentials_or_model_command(self):
        text = (Path(__file__).parents[2]/'.github/workflows/train-ai.yml').read_text()
        self.assertEqual(text.count('    runs-on:'), 1); self.assertIn('timeout-minutes: 25', text)
        self.assertNotIn('secrets.', text); self.assertNotIn('upload-artifact', text)
        self.assertIn('private_qwq_dependency_details.py', text)


if __name__ == '__main__': unittest.main()

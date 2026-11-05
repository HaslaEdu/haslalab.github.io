"""Offline guards for the nonproduction teacher controller; no credentials/API calls."""
import copy
import base64
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('teacher_control', Path(__file__).with_name('hasla-ai-teacher-version-control.py'))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


class Reply:
    def __init__(self, value, status=200):
        self.value, self.status_code = value, status
        self.content = json.dumps(value).encode()
        self.closed = False
    def json(self):
        return self.value
    def close(self):
        self.closed = True


class TeacherControllerTests(unittest.TestCase):
    def snapshot(self):
        return {'compatibility_date': '2026-10-30', 'compatibility_flags': [],
                'production_deployment_id': 'fixture-deployment',
                'production_versions': [{'version_id': '11111111-1111-1111-1111-111111111111', 'percentage': 100}],
                'latest_uploaded_version': '22222222-2222-2222-2222-222222222222', 'subdomain': 'fixture'}

    def test_teacher_reserves_fit_combined_budget_or_fail_before_calls(self):
        value = control.cost_bound(88000)
        self.assertLessEqual(value['modeled_model_upper_krw'], 1000)
        self.assertEqual(value['teacher_reserved_upper_krw'], 1000)
        for value in (94001, 100000, -1, True):
            with self.subTest(value=value), self.assertRaises(control.TeacherControlError):
                control.cost_bound(value)

    def test_cf_client_allows_only_get_and_undeployed_version_creation(self):
        calls = []
        session = SimpleNamespace(request=lambda *a, **k: calls.append((a, k)) or Reply({'success': True, 'result': {}}))
        client = control.Cloudflare('fixture-private-token', session)
        for method, path in (('POST', '/workers/scripts/haslalab-community/deployments'),
                             ('PUT', '/workers/scripts/haslalab-community'),
                             ('PATCH', '/workers/scripts/haslalab-community/subdomain'),
                             ('GET', '/workers/scripts/haslalab-community/secrets/OPENAI_API_KEY')):
            with self.subTest(method=method, path=path), self.assertRaises(control.TeacherControlError):
                client.call(method, path)
        self.assertFalse(calls)
        client.call('POST', '/workers/scripts/haslalab-community/versions?bindings_inherit=strict', files={'fixture': 'only'})
        self.assertFalse(calls[0][1]['allow_redirects'])

    def test_upload_inherits_only_two_existing_keys_and_binds_exact_request(self):
        body, token = b'{"task":"heat_exchange_review"}', 'private-runtime-bearer'
        files = control.make_upload(b'export default {}', body, token, 12345, self.snapshot())
        metadata = json.loads(files['metadata'][1])
        bindings = metadata['bindings']
        self.assertEqual([x for x in bindings if x['type'] == 'inherit'],
                         [{'name': 'OPENAI_API_KEY', 'type': 'inherit'}, {'name': 'DEEPSEEK_API_KEY', 'type': 'inherit'}])
        self.assertEqual(len(bindings), 5)
        self.assertNotIn(token, json.dumps(metadata))
        self.assertNotIn('D1', json.dumps(metadata))
        self.assertEqual(next(x['text'] for x in bindings if x['name'] == 'HASLA_TEACHER_REQUEST_SHA256'), control.sha(body))
        self.assertEqual(metadata['main_module'], 'teacher-entry.mjs')
        entry = files['teacher-entry.mjs'][1].decode()
        self.assertIn('export class StudioProvider extends WorkerEntrypoint', entry)
        self.assertIn('fetch: teacher.fetch', entry)
        self.assertIn('teacher_preview_rpc_disabled', entry)
        self.assertIn('teacher_preview_queue_disabled', entry)
        self.assertIn('teacher_preview_cron_disabled', entry)
        self.assertNotIn('env.DB', entry)

    def test_cloudflare_failure_keeps_only_numeric_codes_and_safe_phase(self):
        response = Reply({'success': False, 'errors': [{'code': 10021, 'message': 'private bearer must not appear'},
                          {'code': True}, {'code': 'secret'}, {'code': 10021}]}, 400)
        client = control.Cloudflare('fixture-key', SimpleNamespace(request=lambda *a, **k: response))
        with self.assertRaises(control.TeacherControlError) as raised:
            client.call('POST', '/workers/scripts/haslalab-community/versions?bindings_inherit=strict', files={'fixture': 'only'})
        self.assertEqual(raised.exception.phase, 'cloudflare_upload_version')
        self.assertEqual(raised.exception.cloudflare_error_codes, [10021])
        self.assertEqual(raised.exception.http_status, 400)
        self.assertNotIn('private bearer', str(raised.exception))
        self.assertTrue(response.closed)

    def test_uploaded_source_manifest_distinguishes_handler_from_entry_shim(self):
        source = b'export default {}'
        manifest = control.source_manifest(source)
        self.assertEqual(manifest['uploaded_source_manifest'][0]['sha256'], control.sha(source))
        self.assertEqual(manifest['uploaded_source_manifest'][1]['sha256'], control.sha(control.ENTRY))
        self.assertEqual(manifest['uploaded_source_sha256'], control.sha(control.canonical(manifest['uploaded_source_manifest'])))

    def test_readonly_snapshot_checks_bindings_preview_and_stable_single_production(self):
        snap = self.snapshot()
        responses = {
            '/settings': {'bindings': [{'name': n, 'type': 'secret_text'} for n in ('OPENAI_API_KEY', 'DEEPSEEK_API_KEY')],
                          'compatibility_date': snap['compatibility_date']},
            '/deployments': {'deployments': [{'id': snap['production_deployment_id'], 'versions': snap['production_versions']}]},
            '/versions': {'items': [{'id': snap['latest_uploaded_version']}]},
            '/subdomain': {'previews_enabled': True},
        }
        def request(method, path):
            self.assertEqual(method, 'GET')
            return {'subdomain': 'fixture'} if path == '/workers/subdomain' else responses['/' + path.rsplit('/', 1)[-1]]
        cf = SimpleNamespace(call=request)
        self.assertEqual(control.snapshot(cf)['latest_uploaded_version'], snap['latest_uploaded_version'])
        responses['/subdomain']['previews_enabled'] = False
        with self.assertRaisesRegex(control.TeacherControlError, 'existing_version_urls_disabled'):
            control.snapshot(cf)

    def test_result_cannot_swap_models_echo_keys_or_include_reasoning(self):
        result = {'task': 'heat_exchange_review', 'nonce': 'fixture', 'mathematics_verified': False, 'fixture': False,
                  'admitted_to_training': False, 'results': [{'provider': provider, 'requested_model': model,
                  'status': 'ok', 'usage': {}, 'fixture': False} for provider, model in control.MODELS.items()]}
        self.assertEqual(control.bounded_result(Reply(result), result['task'], result['nonce']), result)
        for change in ({'reasoning_content': 'private'}, {'task': 'unfrozen'}, {'nonce': 'replayed'}):
            altered = {**result, **change}
            with self.subTest(change=change), self.assertRaises(control.TeacherControlError):
                control.bounded_result(Reply(altered), result['task'], result['nonce'])
        altered = copy.deepcopy(result)
        altered['results'][0]['requested_model'] = 'gpt-6-astra'
        with self.assertRaises(control.TeacherControlError):
            control.bounded_result(Reply(altered), result['task'], result['nonce'])

    def test_export_key_is_public_raw_32_bytes_and_invalid_inputs_fail(self):
        key = bytes(range(32))
        self.assertEqual(control.export_key(base64.b64encode(key).decode()), key)
        for value in ('', 'bad-key', base64.b64encode(b'short').decode()):
            with self.subTest(value=value), self.assertRaises(control.TeacherControlError):
                control.export_key(value)

    def test_encrypted_export_contains_no_plaintext_and_binds_root_key_and_manifest(self):
        try:
            from nacl.public import PrivateKey, SealedBox
        except ImportError:
            self.skipTest('PyNaCl is installed by the workflow; optional local CPU dependency')
        key = PrivateKey.generate()
        record = {'teacher_result': {'final': 'SYNTHETIC PUBLIC PROOF'}, 'code_commit': 'a' * 40,
                  'workflow_run_id': '1234', 'private_artifact': 'fixture:v0', 'source_sha256': 'b' * 64,
                  'request_sha256': 'c' * 64}
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'export'
            manifest = control.export_encrypted(record, bytes(key.public_key), target)
            cipher = (target / 'final-proofs.sealed').read_bytes()
            self.assertNotIn(b'SYNTHETIC PUBLIC PROOF', cipher)
            self.assertEqual(json.loads(SealedBox(key).decrypt(cipher)), record)
            self.assertEqual(set(p.name for p in target.iterdir()), {'final-proofs.sealed', 'manifest.json'})
            self.assertEqual(manifest['cipher_sha256'], control.sha(cipher))
            self.assertEqual(manifest['export_public_key_sha256'], control.sha(bytes(key.public_key)))


if __name__ == '__main__':
    unittest.main()

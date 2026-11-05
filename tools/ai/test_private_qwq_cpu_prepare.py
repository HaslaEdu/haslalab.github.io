import copy
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

import private_qwq_cpu_prepare as prep


class Response:
    def __init__(self, data=b'', status=200, headers=None):
        self.status_code, self.headers = status, headers or {}
        self.data, self.closed = data, False

    def iter_content(self, chunk_size):
        for index in range(0, len(self.data), 3):
            yield self.data[index:index + 3]

    def close(self):
        self.closed = True


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = {'WANDB_API_KEY': 'synthetic-key', 'WANDB_ENTITY': prep.ENTITY}

    def tearDown(self):
        self.temp.cleanup()

    def fixture_spec(self, data=b'public-fixture'):
        return {'repo': 'Qwen/QwQ-32B', 'revision': 'a' * 40, 'name': 'config.json',
                'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

    def test_fixed_adapter_spec_is_exact_verified_rank16_inventory(self):
        from role_config import get_role_config
        from private_resume_adapter import validate_spec
        checked = validate_spec(copy.deepcopy(prep.ADAPTER_SPEC), get_role_config('solver'))
        self.assertEqual(checked['source_training_run_id'], '41931877157')
        self.assertEqual(checked['prior_verification_run_id'], '41943069583')
        self.assertEqual(checked['rank'], 16)
        self.assertTrue(checked['artifact'].endswith(':v0'))
        self.assertEqual([r['name'] for r in checked['files']],
                         ['adapter_config.json', 'adapter_model.safetensors'])

    def test_actual_physical_memory_and_disk_boundary_before_downloads(self):
        mem = self.root / 'meminfo'
        mem.write_text('MemTotal: 15728640 kB\nMemAvailable: 1 kB\n')
        disk = lambda _: SimpleNamespace(free=prep.DISK_MIN)
        got = prep.hardware_preflight(self.root, meminfo=mem, disk_usage=disk, gpu_devices=[])
        self.assertEqual(got['physical_memory_bytes'], prep.MEMORY_MIN)
        mem.write_text('MemTotal: 15728639 kB\n')
        with self.assertRaisesRegex(prep.PreparationError, 'physical_memory_below'):
            prep.hardware_preflight(self.root, meminfo=mem, disk_usage=disk, gpu_devices=[])
        mem.write_text('MemTotal: 15728640 kB\n')
        with self.assertRaisesRegex(prep.PreparationError, 'free_disk_below'):
            prep.hardware_preflight(self.root, meminfo=mem,
                disk_usage=lambda _: SimpleNamespace(free=prep.DISK_MIN - 1), gpu_devices=[])
        with self.assertRaisesRegex(prep.PreparationError, 'gpu_device_present'):
            prep.hardware_preflight(self.root, meminfo=mem, disk_usage=disk, gpu_devices=['fake'])

    def test_provider_keys_hf_tokens_and_wrong_entity_are_rejected(self):
        for name in ('RUNPOD_API_KEY', 'HF_TOKEN', 'HUGGINGFACEHUB_API_TOKEN',
                     'OPENAI_API_KEY', 'CLOUDFLARE_API_TOKEN'):
            with self.subTest(name=name), self.assertRaises(Exception):
                prep.checked_credentials({**self.env, name: 'must-not-log'})
        with self.assertRaisesRegex(prep.PreparationError, 'private_entity_mismatch'):
            prep.checked_credentials({**self.env, 'WANDB_ENTITY': 'different'})
        self.assertEqual(prep.checked_credentials(self.env), 'synthetic-key')

    def test_child_environment_never_passes_sdk_or_provider_credentials(self):
        child = prep.child_environment({**self.env, 'RUNPOD_API_KEY': 'secret',
                    'HF_TOKEN': 'secret', 'PATH': 'fixture', 'HOME': 'fixture'})
        self.assertNotIn('WANDB_API_KEY', child)
        self.assertNotIn('RUNPOD_API_KEY', child)
        self.assertNotIn('HF_TOKEN', child)
        self.assertEqual(child['CUDA_VISIBLE_DEVICES'], '')
        self.assertEqual(child['HF_HUB_OFFLINE'], '1')

    def test_stream_download_hash_size_and_legitimate_hf_redirect(self):
        data = b'public-fixture'
        redirect = Response(status=302, headers={'Location': 'https://cas-bridge.xethub.hf.co/fixture?signature=synthetic'})
        good = Response(data, headers={'Content-Length': str(len(data))})
        session = SimpleNamespace(get=Mock(side_effect=[redirect, good]))
        target = self.root / 'config.json'
        result = prep.download_public(self.fixture_spec(data), target, session=session)
        self.assertEqual(target.read_bytes(), data)
        self.assertEqual(result['sha256'], hashlib.sha256(data).hexdigest())
        self.assertTrue(redirect.closed and good.closed)
        for call in session.get.call_args_list:
            self.assertFalse(call.kwargs['allow_redirects'])
            self.assertNotIn('Authorization', call.kwargs['headers'])
        self.assertFalse((self.root / 'config.json.partial').exists())

    def test_untrusted_redirect_is_never_requested(self):
        for url in ('http://huggingface.co/a', 'https://hf.co.evil.test/a',
                    'https://user:secret@huggingface.co/a', 'https://example.test/a'):
            session = SimpleNamespace(get=Mock(return_value=Response(status=302, headers={'Location': url})))
            with self.subTest(url=url), self.assertRaisesRegex(prep.PreparationError, 'public_redirect_invalid'):
                prep.download_public(self.fixture_spec(), self.root / 'config.json', session=session)
            self.assertEqual(session.get.call_count, 1)

    def test_corrupt_truncated_oversized_and_http_failure_leave_no_final_file(self):
        for response in (Response(b'bad'), Response(b'public-fixture-extra'),
                         Response(b'public-fixture', headers={'Content-Length': '999'}), Response(status=403)):
            session = SimpleNamespace(get=Mock(return_value=response))
            with self.subTest(response=response), self.assertRaises(prep.PreparationError):
                prep.download_public(self.fixture_spec(), self.root / 'config.json', session=session)
            self.assertFalse((self.root / 'config.json').exists())
            self.assertFalse((self.root / 'config.json.partial').exists())

    def test_preexisting_file_is_preserved_without_network(self):
        target = self.root / 'config.json'
        target.write_bytes(b'preserve')
        session = SimpleNamespace(get=Mock())
        with self.assertRaisesRegex(prep.PreparationError, 'already_exists'):
            prep.download_public(self.fixture_spec(), target, session=session)
        session.get.assert_not_called()
        self.assertEqual(target.read_bytes(), b'preserve')

    def test_failed_resource_gate_makes_no_sdk_or_download_call(self):
        clients, downloader = Mock(), Mock()
        with self.assertRaisesRegex(prep.PreparationError, 'resource_fixture'):
            prep.prepare(self.root / 'new', self.env, clients=clients, downloader=downloader,
                         preflight=Mock(side_effect=prep.PreparationError('resource_fixture')))
        clients.assert_not_called()
        downloader.assert_not_called()
        self.assertFalse((self.root / 'new').exists())

    def test_prepare_writes_only_metadata_and_fixed_inputs_no_corpus(self):
        calls = []
        def download(spec, target):
            calls.append(('public', spec['name']))
            target.write_bytes(b'fixture')
            return {k: spec[k] for k in ('name', 'bytes', 'sha256')}
        def adapter(spec, config, path, api, privacy):
            self.assertEqual(spec, prep.ADAPTER_SPEC)
            self.assertEqual(config['default_rank'], 16)
            calls.append(('adapter', spec['source_training_run_id']))
            path.mkdir()
        def build(path):
            path.mkdir()
            return path / 'build/bin/llama-server'
        privacy = Mock(return_value=True)
        result = prep.prepare(self.root / 'new', self.env, downloader=download, builder=build,
                             preflight=lambda _: {'gpu_count': 0},
                             clients=lambda _: (object(), privacy), adapter_downloader=adapter)
        self.assertEqual(len(calls), 4)
        self.assertEqual(result['quant'], 'iq3_xxs')
        self.assertFalse(result['training_corpus_accessed'])
        saved = json.loads((self.root / 'new/prepared.json').read_bytes())
        self.assertEqual(saved, result)
        self.assertNotIn('synthetic-key', json.dumps(saved))
        privacy.assert_called_once_with(prep.ENTITY)

    def test_build_cpu_pinned_source_no_accelerator_and_no_secret_environment(self):
        destination = self.root / 'llama'
        commands = []
        def runner(command, **kwargs):
            commands.append(command)
            self.assertNotIn('WANDB_API_KEY', kwargs['env'])
            if 'rev-parse' in command:
                return SimpleNamespace(returncode=0, stdout=(prep.LLAMA_COMMIT + '\n').encode())
            if command[:2] == ['cmake', '--build']:
                binary = destination / 'build/bin/llama-server'
                binary.parent.mkdir(parents=True)
                binary.write_bytes(b'cpu')
                (destination / 'convert_lora_to_gguf.py').write_text('# official fixture')
            return SimpleNamespace(returncode=0)
        binary = prep.build_cpu(destination, runner=runner)
        self.assertTrue(binary.exists())
        self.assertTrue(any(prep.LLAMA_COMMIT in command for command in commands))
        configure = next(command for command in commands if command[:2] == ['cmake', '-S'])
        self.assertIn('-DGGML_CUDA=OFF', configure)
        self.assertIn('-DGGML_VULKAN=OFF', configure)
        self.assertIn('-DLLAMA_OPENSSL=OFF', configure)
        self.assertIn('-DLLAMA_USE_PREBUILT_UI=OFF', configure)

    def report_fixture(self):
        import private_qwq_cpu_eval as worker
        args = argparse.Namespace(work_dir=self.root / 'report', max_wall_seconds=9000,
                                  threads=4, context=2048, quant='iq3_xxs')
        with patch.object(worker, 'memory_status', return_value={'MemTotal': 1, 'MemAvailable': 1}):
            worker.execute(args)
        return args.work_dir

    def sdk_fixture(self, *, finish_failure=False):
        name = prep.ENTITY + '/' + prep.resume.PROJECT + '/hasla-qwq-cpu-comparison-123:v0'
        saved = SimpleNamespace(state='COMMITTED', qualified_name=name)
        logged = SimpleNamespace(wait=Mock(return_value=saved))
        run = SimpleNamespace(log_artifact=Mock(return_value=logged), finish=Mock())
        if finish_failure:
            run.finish.side_effect = RuntimeError('must-never-log-upstream-error')
        artifact = SimpleNamespace(add_file=Mock())
        sdk = SimpleNamespace(init=Mock(return_value=run), Artifact=Mock(return_value=artifact))
        return sdk, run, artifact

    def publish_env(self):
        return {**self.env, 'GITHUB_RUN_ID': '123', 'GITHUB_SHA': 'a' * 40,
                'HASLA_CPU_COMPARE_LAUNCH_ID': 'synthetic-launch-123'}

    def test_final_private_publication_rechecks_privacy_and_uploads_only_two_json_files(self):
        directory = self.report_fixture()
        sdk, run, artifact = self.sdk_fixture()
        privacy = Mock(return_value=True)
        result = prep.publish_report(directory, self.publish_env(), clients=lambda _: (object(), privacy), sdk=sdk)
        self.assertEqual(result['event'], 'private_qwq_cpu_comparison')
        self.assertEqual(result['status'], 'uploaded')
        self.assertEqual(result['paired_completed_cases'], 0)
        self.assertEqual(result['execution_status'], 'failed')
        self.assertEqual(result['scores'], {})
        self.assertNotIn('final_answer', result)
        self.assertFalse(result['final_answers_included'])
        self.assertNotIn('must-never-log', json.dumps(result))
        self.assertEqual(privacy.call_count, 3)
        self.assertEqual([call.kwargs['name'] for call in artifact.add_file.call_args_list],
                         ['report.json', 'metadata.json'])
        run.log_artifact.assert_called_once_with(artifact)
        self.assertEqual(sdk.init.call_args.kwargs['project'], prep.resume.PROJECT)

    def test_private_gate_and_raw_reasoning_rejection_precede_any_publication(self):
        directory = self.report_fixture()
        sdk, _, _ = self.sdk_fixture()
        privacy = Mock(side_effect=prep.PreparationError('private_project_required'))
        with self.assertRaisesRegex(prep.PreparationError, 'private_project_required'):
            prep.publish_report(directory, self.publish_env(), clients=lambda _: (object(), privacy), sdk=sdk)
        sdk.init.assert_not_called()
        metadata = directory / 'metadata.json'
        value = json.loads(metadata.read_bytes())
        value['raw_thinking'] = 'must-never-upload'
        metadata.write_text(json.dumps(value))
        clients = Mock()
        with self.assertRaises(Exception):
            prep.publish_report(directory, self.publish_env(), clients=clients, sdk=sdk)
        clients.assert_not_called()
        sdk.init.assert_not_called()

    def test_committed_receipt_survives_sdk_finish_failure(self):
        directory = self.report_fixture()
        sdk, run, _ = self.sdk_fixture(finish_failure=True)
        result = prep.publish_report(directory, self.publish_env(),
                                     clients=lambda _: (object(), Mock(return_value=True)), sdk=sdk)
        self.assertEqual(result['status'], 'uploaded')
        self.assertTrue(result['sdk_finish_failed_after_commit'])
        self.assertTrue(result['artifact'].endswith(':v0'))
        run.finish.assert_called_once()

    def test_completed_scores_event_drops_every_final_answer_and_hidden_reasoning(self):
        import private_qwq_comparison as comparison
        from test_private_qwq_comparison import bundle
        directory = self.report_fixture()
        plan = comparison.build_plan(prep.ADAPTER_SPEC['files'][1]['sha256'],
                                     prep.ADAPTER_SPEC['files'][0]['sha256'])
        base, adapted = bundle(plan, 'base'), bundle(plan, 'adapted')
        adapted['adapter_model_sha256'] = plan['adapter_model_sha256']
        adapted['adapter_config_sha256'] = plan['adapter_config_sha256']
        report = comparison.score_comparison(plan, base, adapted)
        raw = comparison.canonical(report) + b'\n'
        (directory / 'report.json').write_bytes(raw)
        metadata_path = directory / 'metadata.json'
        metadata = json.loads(metadata_path.read_bytes())
        metadata.pop('failure_code')
        metadata.update(status='completed', paired_completed_cases=8, frozen_cases=8,
                        report_sha256=hashlib.sha256(raw).hexdigest())
        metadata_path.write_text(json.dumps(metadata))
        sdk, _, _ = self.sdk_fixture()
        result = prep.publish_report(directory, self.publish_env(),
                                     clients=lambda _: (object(), Mock(return_value=True)), sdk=sdk)
        self.assertEqual(result['scores']['base']['passed_cases'], 8)
        self.assertEqual(result['scores']['adapted']['correct_units'], 10)
        self.assertTrue(result['scores']['adapted']['abstention_passed'])
        self.assertTrue(result['coverage_complete'])
        self.assertTrue(all('final_answer' not in row for group in result['scores'].values()
                            for row in group['cases']))
        self.assertNotIn('PRIVATE_HIDDEN_REASONING', json.dumps(result))


class WorkflowTests(unittest.TestCase):
    def test_cpu_flag_is_exclusive_and_cpu_job_has_only_two_private_secrets(self):
        path = Path(__file__).resolve().parents[2] / '.github/workflows/train-ai-private.yml'
        text = path.read_text(encoding='utf8')
        sections = __import__('re').split(r'(?m)^  (?=[a-z][a-z0-9-]+:\s*$)', text.split('jobs:\n', 1)[1])
        jobs = [part for part in sections if part.strip()]
        cpu = next(part for part in jobs if part.startswith('compare-qwq-cpu:'))
        self.assertIn('runs-on: ubuntu-24.04', cpu)
        self.assertIn('timeout-minutes: 180', cpu)
        self.assertIn('group: hasla-private-qwq-cpu-comparison', cpu)
        self.assertEqual(set(__import__('re').findall(r'secrets\.([A-Z0-9_]+)', cpu)),
                         {'WANDB_API_KEY'})
        self.assertNotIn('upload-artifact', cpu)
        for part in jobs:
            if part is not cpu:
                first_if = next(line for line in part.splitlines() if line.startswith('    if:'))
                self.assertIn('!inputs.compare_qwq_cpu', first_if)


if __name__ == '__main__':
    unittest.main()

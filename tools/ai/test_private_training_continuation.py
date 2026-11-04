"""Independent CPU fixtures for the integrated solver continuation path."""
import copy
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import private_dedicated_run as dedicated
import private_dual_pod as bootstrap
import private_dual_run as parent
import private_pod_train as pod
import private_resume_adapter as continuation
import private_verify_adapter as verifier
from role_config import get_role_config
import test_private_dual_run as parent_fixtures
import test_private_pod_train as pod_fixtures
import test_private_resume_adapter as adapter_fixtures
import test_private_verify_adapter as verifier_fixtures
import train_lora as train


PRIVATE = 'SYNTHETIC_PRIVATE_CONTINUATION_TEXT_NEVER_LOG'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_spec(entity='fixture-entity', run_id='122', model=None):
    model = model or adapter_fixtures.container(adapter_fixtures.tensors())
    config = json.dumps({'peft_type': 'LORA', 'base_model_name_or_path': 'Qwen/QwQ-32B', 'r': 16}).encode()
    blobs = dict(zip(continuation.FILES, (config, model)))
    files = [{'name': name, 'bytes': len(blobs[name]), 'sha256': sha(blobs[name])} for name in continuation.FILES]
    return {'kind': continuation.KIND, 'version': 1, 'role': 'solver', 'base_model': 'Qwen/QwQ-32B',
            'rank': 16, 'entity': entity, 'source_training_run_id': run_id,
            'artifact': f'{entity}/{continuation.PROJECT}/hasla-private-books-{run_id}-solver-lora:v0',
            'files': files, 'adapter_inventory_sha256': sha(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()),
            'prior_verification_run_id': '100'}, blobs


def continued_verifier(changed=True):
    before = verifier_fixtures.adapter(rank=16, bits=[1] * 16)
    after = verifier_fixtures.adapter(rank=16, bits=([2] + [1] * 15) if changed else [1] * 16)
    fixture = verifier_fixtures.Fixture('solver', model=after)
    baseline = verifier_fixtures.Fixture('solver', model=before)
    old_ref = baseline.results['solver']['artifact']
    spec, _ = source_spec(model=before)
    # Bind exactly the actual fixture bytes/inventory, including the PEFT JSON.
    spec['files'] = baseline.results['solver']['adapter_files']
    spec['adapter_inventory_sha256'] = baseline.results['solver']['adapter_sha256']
    base_artifact = baseline.artifacts[old_ref]
    base_artifact.qualified_name = spec['artifact']
    base_artifact.manifest.entries.pop('do-not-download.txt')
    fixture.artifacts[spec['artifact']] = base_artifact
    result = fixture.results['solver']
    result.update(initial_adapter=spec, resume_script_sha256=sha(Path(continuation.__file__).read_bytes()),
                  initial_adapter_model_sha256=spec['files'][1]['sha256'], optimizer_state_restored=False)
    fixture.artifacts[result['artifact']].metadata.update({key: result[key] for key in (
        'initial_adapter', 'resume_script_sha256', 'initial_adapter_model_sha256', 'optimizer_state_restored')})
    return fixture


def verify_fixture(fixture, explicit=False):
    return verifier.verify('123', 'solver', {'WANDB_API_KEY': 'fixture-key'},
        reader_factory=lambda _: fixture, sdk_factory=lambda _: fixture, continuation_inventory=explicit)


class TrainerContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.initial = self.root / 'initial-adapter'
        self.initial.mkdir()
        self.spec, blobs = source_spec()
        for name, raw in blobs.items():
            (self.initial / name).write_bytes(raw)
        self.data = self.root / 'train.text.jsonl'
        self.data.write_text(json.dumps({'text': PRIVATE, 'metadata': {'group_id': 'fixture-a', 'split': 'train'}}) + '\n')
        self.out = self.root / 'new-adapter'
        self.before = self.data.read_bytes()
        self.initial_before = (self.initial / continuation.FILES[1]).read_bytes()

    def modules(self, *, base_trainable=False, mutate_on_save=False):
        calls = {}
        initial, out = self.initial, self.out
        class Model:
            def named_parameters(self):
                return [('base.layers.weight', SimpleNamespace(requires_grad=base_trainable)),
                        ('base.layers.lora_A.default.weight', SimpleNamespace(requires_grad=True)),
                        ('base.layers.lora_B.default.weight', SimpleNamespace(requires_grad=True))]
            def save_pretrained(self, path):
                calls['saved_path'] = path
                if mutate_on_save:
                    (initial / 'adapter_model.safetensors').write_bytes(b'altered-at-save')
                Path(path).mkdir()
                (Path(path) / 'adapter_config.json').write_text(json.dumps({
                    'peft_type': 'LORA', 'base_model_name_or_path': 'Qwen/QwQ-32B', 'r': 16}))
                (Path(path) / 'adapter_model.safetensors').write_bytes(b'synthetic-new-adapter')
        class Tokenizer:
            eos_token = '<EOS>'
            def save_pretrained(self, path):
                calls['tokenizer_saved'] = path
        class Loader:
            @staticmethod
            def from_pretrained(**kwargs):
                calls['loader'] = kwargs
                return Model(), Tokenizer()
            @staticmethod
            def get_peft_model(*_, **__):
                raise AssertionError('a continuation must never reset or rewrap its LoRA')
        def config(**kwargs):
            calls['training_options'] = kwargs
            return SimpleNamespace(**kwargs)
        class Trainer:
            def __init__(self, **kwargs):
                calls['trainer'] = kwargs
                self.state = SimpleNamespace(global_step=2, log_history=[])
            def train(self, *args, **kwargs):
                calls['train_call'] = (args, kwargs)
                return SimpleNamespace(metrics={'train_loss': 1.0})
        return {'unsloth': SimpleNamespace(FastLanguageModel=Loader, is_bfloat16_supported=lambda: True),
                'torch': SimpleNamespace(bfloat16='fixture-bf16'),
                'datasets': SimpleNamespace(Dataset=SimpleNamespace(from_list=lambda rows: rows)),
                'trl': SimpleNamespace(SFTConfig=config, SFTTrainer=Trainer)}, calls

    def args(self):
        return ['--base', 'solver', '--format', 'text', '--holdout', '0', '--max-steps', '2',
                '--resume-adapter', str(self.initial), str(self.data), str(self.out)]

    def test_loader_receives_local_adapter_without_peft_reset_and_inputs_remain_unchanged(self):
        modules, calls = self.modules()
        output = io.StringIO()
        with patch.dict('sys.modules', modules), redirect_stdout(output):
            train.main(self.args())
        self.assertEqual(calls['loader']['model_name'], str(self.initial))
        self.assertTrue(calls['loader']['load_in_4bit'])
        self.assertFalse(calls['loader']['full_finetuning'])
        self.assertEqual(calls['train_call'], ((), {}))
        self.assertEqual(self.data.read_bytes(), self.before)
        self.assertEqual((self.initial / continuation.FILES[1]).read_bytes(), self.initial_before)
        report = json.loads((self.out / 'hasla_training_manifest.json').read_text())
        self.assertEqual(report['initial_adapter_model_sha256'], sha(self.initial_before))
        self.assertFalse(report['optimizer_state_restored'])
        self.assertEqual(report['steps_completed'], 2)
        self.assertNotIn(PRIVATE, output.getvalue())

    def test_any_unfrozen_base_parameter_aborts_before_trainer_or_save(self):
        modules, calls = self.modules(base_trainable=True)
        with patch.dict('sys.modules', modules), redirect_stdout(io.StringIO()), \
                self.assertRaisesRegex(ValueError, 'freeze every base'):
            train.main(self.args())
        self.assertNotIn('trainer', calls)
        self.assertFalse(self.out.exists())

    def test_initial_weight_change_during_model_save_is_rejected_before_success_manifest(self):
        modules, _ = self.modules(mutate_on_save=True)
        with patch.dict('sys.modules', modules), redirect_stdout(io.StringIO()), \
                self.assertRaisesRegex(ValueError, 'initial adapter file changed'):
            train.main(self.args())
        self.assertFalse((self.out / 'hasla_training_manifest.json').exists())

    def test_resume_role_rank_and_overlapping_output_are_rejected_before_model_import(self):
        for config, rank, out in ((get_role_config('chat'), 8, self.out), (get_role_config('solver'), 8, self.out),
                                  (get_role_config('solver'), 16, self.initial / 'nested')):
            with self.subTest(role=config['role'], rank=rank), self.assertRaises(ValueError):
                train.initial_adapter(self.initial, config, rank, out)


class ContinuationTransportTests(unittest.TestCase):
    def pod_fixture(self, *, bad_helper_pin=False, bad_report_sha=False):
        harness = pod_fixtures.PrivatePodTests('test_success_only_uploads_adapter_and_safe_exact_result')
        harness.setUp()
        self.addCleanup(harness.doCleanups)
        initial, blobs = source_spec()
        helper = ("from pathlib import Path\n"
            "def validate_spec(spec, config):\n    return dict(spec)\n"
            "def download_initial_adapter(spec, config, root, api, privacy):\n"
            "    assert privacy(spec['entity'])['access'] == 'PRIVATE'\n"
            "    root = Path(root)\n    root.mkdir()\n"
            + ''.join(f"    (root / {name!r}).write_bytes({raw!r})\n" for name, raw in blobs.items())).encode()
        harness.env.update(WANDB_PROJECT=continuation.PROJECT, HASLA_INITIAL_ADAPTER=json.dumps(initial),
            HASLA_RESUME_SCRIPT_SHA256='0' * 64 if bad_helper_pin else sha(helper))
        def opener(request, timeout):
            if request.full_url.endswith('/graphql'):
                return io.BytesIO(json.dumps({'data': {'project': {'name': continuation.PROJECT, 'access': 'PRIVATE'}}}).encode())
            if request.full_url.endswith('/private_resume_adapter.py'):
                return io.BytesIO(helper)
            return harness.opener(request, timeout)
        def runner(command, **kwargs):
            result = harness.runner(command, **kwargs)
            path = harness.root / 'adapter/hasla_training_manifest.json'
            report = json.loads(path.read_text())
            report.update(initial_adapter_model_sha256='0' * 64 if bad_report_sha else initial['files'][1]['sha256'],
                          optimizer_state_restored=False)
            path.write_text(json.dumps(report))
            return result
        def artifact(name, type, metadata):
            value = pod_fixtures.FakeArtifact(name, type, metadata)
            value.qualified_name = f'fixture-entity/{continuation.PROJECT}/{name}:v3'
            return value
        harness.wandb.Artifact = artifact
        return harness, initial, helper, opener, runner

    def test_full_pod_wiring_downloads_fifth_pin_and_passes_local_adapter_without_env_spec(self):
        harness, initial, helper, opener, runner = self.pod_fixture()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = pod.run_pilot(harness.env, harness.root, harness.wandb, opener, runner)
        self.assertEqual(result['status'], 'uploaded')
        command, kwargs = harness.calls[0]
        self.assertEqual(command[command.index('--resume-adapter') + 1], str(harness.root / 'initial-adapter'))
        self.assertNotIn('HASLA_INITIAL_ADAPTER', kwargs['env'])
        self.assertNotIn('HASLA_RESUME_SCRIPT_SHA256', kwargs['env'])
        self.assertNotIn('WANDB_API_KEY', kwargs['env'])
        self.assertEqual(result['initial_adapter'], initial)
        self.assertEqual(result['resume_script_sha256'], sha(helper))
        self.assertEqual(result['initial_adapter_model_sha256'], initial['files'][1]['sha256'])
        self.assertFalse(result['optimizer_state_restored'])

    def test_full_pod_bad_fifth_pin_aborts_before_the_trainer(self):
        harness, _, _, opener, runner = self.pod_fixture(bad_helper_pin=True)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = pod.run_pilot(harness.env, harness.root, harness.wandb, opener, runner)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['stage'], 'initial_adapter_verification')
        self.assertEqual(harness.calls, [])
        self.assertEqual(harness.wandb.run.artifacts, [])

    def test_full_pod_wrong_training_report_initial_sha_never_uploads_an_adapter(self):
        harness, _, _, opener, runner = self.pod_fixture(bad_report_sha=True)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = pod.run_pilot(harness.env, harness.root, harness.wandb, opener, runner)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_code'], 'training_report_initial_adapter_mismatch')
        self.assertEqual(harness.wandb.run.artifacts, [])

    def test_parent_requires_solver_spec_and_fifth_helper_pin(self):
        env, manifest = parent_fixtures.fixture()
        initial, _ = source_spec()
        manifest['roles']['solver']['initial_adapter'] = initial
        manifest['resume_script_sha256'] = sha(Path(continuation.__file__).read_bytes())
        env['HASLA_DUAL_MANIFEST'] = json.dumps(manifest)
        checked, payloads = parent.load_inputs(env)
        self.assertEqual(checked['roles']['solver']['initial_adapter'], initial)
        self.assertEqual(list(payloads), ['solver'])
        for bad in ('', 'not-a-sha'):
            manifest['resume_script_sha256'] = bad
            with self.assertRaises(ValueError):
                parent.load_inputs({**env, 'HASLA_DUAL_MANIFEST': json.dumps(manifest)})

    def test_fifth_pin_download_is_required_and_mismatch_stops_preflight(self):
        env, manifest = parent_fixtures.fixture()
        manifest['roles']['solver']['initial_adapter'] = source_spec()[0]
        mapping = {'train_script_sha256': 'train_lora.py', 'role_config_sha256': 'role_config.py',
                   'pod_script_sha256': 'private_pod_train.py', 'dual_pod_sha256': 'private_dual_pod.py',
                   'resume_script_sha256': 'private_resume_adapter.py'}
        blobs = {name: ('synthetic:' + name).encode() for name in mapping.values()}
        for key, name in mapping.items():
            manifest[key] = sha(blobs[name])
        def get(url, **_):
            return SimpleNamespace(status_code=200, content=blobs[url.rsplit('/', 1)[-1]])
        with patch.object(parent.cloud.requests, 'get', side_effect=get) as api:
            parent.verify_pinned_scripts(manifest, env['GITHUB_SHA'])
        self.assertEqual(api.call_count, 5)
        manifest['resume_script_sha256'] = '0' * 64
        with patch.object(parent.cloud.requests, 'get', side_effect=get), self.assertRaises(ValueError):
            parent.verify_pinned_scripts(manifest, env['GITHUB_SHA'])

    def test_dedicated_environment_propagates_single_solver_spec_and_no_other_role(self):
        env, manifest = parent_fixtures.fixture()
        initial, _ = source_spec()
        manifest['roles']['solver']['initial_adapter'] = initial
        manifest['resume_script_sha256'] = 'b' * 64
        child = dedicated.pod_environment(env, manifest, 'fixture-entity', 'solver', 'fixture-run',
            f'fixture-entity/{continuation.PROJECT}/fixture-data:v1', 3600)
        jobs = bootstrap.role_jobs(child)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['initial_adapter'], initial)
        self.assertEqual(child['HASLA_RESUME_SCRIPT_SHA256'], 'b' * 64)
        self.assertNotIn('RUNPOD_API_KEY', child)
        bad = {**child, 'HASLA_RESUME_SCRIPT_SHA256': ''}
        with self.assertRaises(ValueError):
            bootstrap.role_jobs(bad)
        jobs[0].update(role='chat', format='chat')
        with self.assertRaises(ValueError):
            bootstrap.role_jobs({**child, 'HASLA_ROLE_JOBS': json.dumps(jobs)})

    def test_pod_training_report_rejects_wrong_initial_hash_or_restored_optimizer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = pod.data_bounded_settings(get_role_config('solver'), 16)
            report = {'role': 'solver', 'base_model': config['base_model'], 'format': 'text', 'precision': '4bit',
                'training_method': 'qlora', 'rank': 16, 'max_length': config['max_length'], 'max_steps': config['max_steps'],
                'training_sha256': 'a' * 64, 'validation_sha256': 'b' * 64, 'steps_completed': 1,
                'weights_updated': True, 'initial_adapter_model_sha256': 'c' * 64, 'optimizer_state_restored': False}
            path = root / 'hasla_training_manifest.json'
            path.write_text(json.dumps(report))
            pod.training_report(root, config, 'text', 'a' * 64, 'b' * 64, 'c' * 64)
            for changes in ({'initial_adapter_model_sha256': '0' * 64}, {'optimizer_state_restored': True},
                            {'initial_adapter_model_sha256': None}):
                path.write_text(json.dumps({**report, **changes}))
                with self.subTest(changes=changes), self.assertRaises(pod.PilotError):
                    pod.training_report(root, config, 'text', 'a' * 64, 'b' * 64, 'c' * 64)


class ContinuedArtifactVerificationTests(unittest.TestCase):
    def test_unchanged_nonzero_baseline_fails_and_changed_b_passes(self):
        unchanged = verify_fixture(continued_verifier(False))
        self.assertFalse(unchanged['all_verified'])
        self.assertEqual(unchanged['roles'][0]['code'], 'continued_lora_b_unchanged')
        self.assertFalse(unchanged['roles'][0]['weights_updated'])
        changed = verify_fixture(continued_verifier(True))
        self.assertTrue(changed['all_verified'])
        self.assertEqual(changed['roles'][0]['code'], 'relative_lora_b_change')
        self.assertEqual(changed['roles'][0]['standard_b_changed_elements'], 1)
        self.assertFalse(changed['quality_verified'])

    def test_default_digest_stripping_and_explicit_solver_inventory(self):
        default = verify_fixture(continued_verifier(True))
        self.assertNotIn('sha256', json.dumps(default))
        self.assertNotIn('adapter_files', default['roles'][0])
        explicit = verify_fixture(continued_verifier(True), True)
        self.assertTrue(explicit['all_verified'])
        self.assertEqual(set(row['name'] for row in explicit['roles'][0]['adapter_files']), set(continuation.FILES))
        self.assertIn('before_file_sha256', explicit['roles'][0])
        reader = Mock()
        with self.assertRaises(verifier.VerificationError):
            verifier.verify('123', 'chat,solver', {'WANDB_API_KEY': 'fixture'}, reader_factory=reader, continuation_inventory=True)
        reader.assert_not_called()

    def test_metadata_chain_fields_and_helper_pin_must_match_result(self):
        for field, value in (('resume_script_sha256', '0' * 64), ('initial_adapter_model_sha256', '0' * 64),
                             ('optimizer_state_restored', True)):
            fixture = continued_verifier(True)
            result = fixture.results['solver']
            fixture.artifacts[result['artifact']].metadata[field] = value
            with self.subTest(field=field):
                event = verify_fixture(fixture)
                self.assertFalse(event['all_verified'])
        fixture = continued_verifier(True)
        result = fixture.results['solver']
        result['resume_script_sha256'] = '0' * 64
        fixture.artifacts[result['artifact']].metadata['resume_script_sha256'] = '0' * 64
        self.assertEqual(verify_fixture(fixture)['roles'][0]['code'], 'continuation_helper_pin_mismatch')

    def test_continuation_markers_without_initial_spec_never_fall_through_to_zero_initializer(self):
        fixture = continued_verifier(False)
        result = fixture.results['solver']
        result.pop('initial_adapter')
        fixture.artifacts[result['artifact']].metadata.pop('initial_adapter')
        event = verify_fixture(fixture)
        self.assertFalse(event['all_verified'])
        self.assertFalse(event['roles'][0]['weights_updated'])

    def test_flat_summary_continuation_preserves_the_complete_source_chain(self):
        result = continued_verifier(True).results['solver']
        summary = {'private_training_result.' + key: value for key, value in result.items()}
        decoded = verifier.summary_result(summary)
        for key in ('initial_adapter', 'resume_script_sha256', 'initial_adapter_model_sha256', 'optimizer_state_restored'):
            self.assertEqual(decoded[key], result[key])

    def test_explicit_inventory_cli_flag_is_forwarded_without_enabling_it_by_default(self):
        event = {'event': 'private_adapter_verification', 'roles': [{'status': 'verified'}],
                 'all_verified': True, 'quality_verified': False}
        for flags, expected in (([], False), (['--continuation-inventory'], True)):
            with patch.object(verifier, 'verify', return_value=event) as verify_call, redirect_stdout(io.StringIO()):
                self.assertEqual(verifier.main(['--run-id', '123', '--roles', 'solver', *flags]), 0)
            self.assertEqual(verify_call.call_args.kwargs['continuation_inventory'], expected)

    def test_baseline_model_sha_must_match_pinned_source_even_when_metadata_agrees(self):
        fixture = continued_verifier(True)
        result = fixture.results['solver']
        result['initial_adapter_model_sha256'] = '0' * 64
        fixture.artifacts[result['artifact']].metadata['initial_adapter_model_sha256'] = '0' * 64
        event = verify_fixture(fixture)
        self.assertFalse(event['all_verified'])
        self.assertEqual(event['roles'][0]['code'], 'continuation_source_mismatch')


if __name__ == '__main__':
    unittest.main()

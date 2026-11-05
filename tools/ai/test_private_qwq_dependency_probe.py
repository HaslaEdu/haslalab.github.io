from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

import private_qwq_dependency_probe as probe


def fixture():
    env = {'venv_bin_present': True, 'cuda_bin_present': True, 'cuda_library_present': True,
           'tool_roots': {'python': 'venv', 'pip': 'venv', 'nvcc': 'cuda', 'ptxas': 'cuda'}}
    return {'version': 1, 'kind': 'fixed_cpu_dependency_probe', 'image': probe.IMAGE,
            'core_before': dict.fromkeys(probe.CORE, '1.2.3'), 'core_after': dict.fromkeys(probe.CORE, '1.2.3'),
            'changed_core_packages': [], 'all_core_metadata_present': True, 'core_versions_unchanged': True,
            'pip_exit_code': 0, 'pip_exception_type': None,
            'imports': {'wandb': {'status': 'imported', 'version': '0.31.0', 'exception_type': None},
                        'torch': {'status': 'imported', 'version': '2.11.0+cu128', 'exception_type': None, 'compiled_cuda': '12.8'}},
            'unsloth_import_attempted': False, 'gpu_assertion_attempted': False, 'model_calls': 0, 'credentials_passed': False,
            'aux_before': dict.fromkeys(probe.AUX, None), 'aux_after': dict.fromkeys(probe.AUX, None),
            'changed_aux_packages': [], 'pip_check_before_exit': 1, 'pip_check_after_exit': 1,
            'environment': {'image_env': env, 'login_shell': deepcopy(env), 'double_login_shell': deepcopy(env)}}


class Tests(unittest.TestCase):
    def test_strict_projection_and_truthful_diff(self):
        value = fixture(); self.assertEqual(probe.validate(value), value)
        for bad in ({**value, 'raw_pip': 'secret'}, {**value, 'core_versions_unchanged': False},
                    {**value, 'pip_exit_code': True}, {**value, 'credentials_passed': True}):
            with self.subTest(bad=bad), self.assertRaises(ValueError): probe.validate(bad)
        value['core_after']['torch'] = '2.12'; value['changed_core_packages'] = ['torch']; value['core_versions_unchanged'] = False
        self.assertEqual(probe.validate(value)['changed_core_packages'], ['torch'])

    def test_import_failure_only_class_and_never_unsloth(self):
        def fail(name): raise RuntimeError('PRIVATE_RAW_ERROR')
        result = probe.import_probe('wandb', fail)
        self.assertEqual(result['exception_type'], 'RuntimeError')
        self.assertNotIn('PRIVATE_RAW_ERROR', json.dumps(result))
        with self.assertRaises(ValueError): probe.import_probe('unsloth', fail)
        torch = SimpleNamespace(__version__='2.11.0', version=SimpleNamespace(cuda='12.8'))
        self.assertEqual(probe.import_probe('torch', lambda _: torch)['compiled_cuda'], '12.8')

    def test_public_environment_projection_never_emits_path_or_credentials(self):
        result = probe.environment_snapshot({'PATH': os.pathsep.join(['/opt/unsloth-venv/bin', '/usr/local/cuda/bin', '/private/secret']),
            'LD_LIBRARY_PATH': '/usr/local/cuda/lib64', 'WANDB_API_KEY': 'PRIVATE_RAW'}, lambda _: '/private/secret/python')
        self.assertTrue(result['venv_bin_present']); self.assertTrue(result['cuda_bin_present'])
        self.assertNotIn('PRIVATE_RAW', json.dumps(result)); self.assertNotIn('/private', json.dumps(result))

    def test_disk_gate_precedes_every_docker_call(self):
        result = probe.host({'GITHUB_ACTIONS': 'true', 'RUNNER_OS': 'Linux', 'HASLA_DEPENDENCY_PROBE_LAUNCH_ID': 'a'*32},
            run=lambda *a, **k: self.fail('must not run'), disk_usage=lambda _: SimpleNamespace(free=44*1024**3))
        self.assertEqual(result['failure_code'], 'disk_below_45gib')

    def test_whole_host_fake_has_no_gpu_or_secret_and_cleans_exact_container(self):
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            if command[1] == 'run':
                mount = next(c for c in command if c.startswith('type=bind,src=') and c.endswith(',dst=/probe-output'))
                root = Path(mount[len('type=bind,src='):-len(',dst=/probe-output')])
                (root/'result.json').write_text(json.dumps(fixture()))
            return SimpleNamespace(returncode=0)
        result = probe.host({'GITHUB_ACTIONS': 'true', 'RUNNER_OS': 'Linux', 'HASLA_DEPENDENCY_PROBE_LAUNCH_ID': 'a'*32,
                             'WANDB_API_KEY': 'PRIVATE_RAW'}, run=run, disk_usage=lambda _: SimpleNamespace(free=50*1024**3))
        self.assertEqual(result['status'], 'observed')
        self.assertNotIn('PRIVATE_RAW', json.dumps(calls)); self.assertNotIn('--gpus', json.dumps(calls))
        self.assertEqual(calls[0], ['docker', 'pull', '--platform', 'linux/amd64', probe.IMAGE])
        self.assertIn(probe.PYTHON, calls[1]); self.assertIn('--entrypoint', calls[1])
        self.assertEqual(calls[-1], ['docker', 'rm', '-f', 'hasla-qwq-dependency-probe-'+'a'*32])

    def test_registered_workflow_is_one_free_cpu_job_and_no_secret_or_public_artifact(self):
        text = (Path(__file__).parents[2]/'.github/workflows/train-ai.yml').read_text()
        self.assertEqual(text.count('    runs-on:'), 1)
        self.assertIn('runs-on: ubuntu-24.04', text); self.assertIn('timeout-minutes: 25', text)
        self.assertIn('persist-credentials: false', text); self.assertNotIn('secrets.', text)
        self.assertNotIn('upload-artifact', text); self.assertNotIn('RUNPOD_API_KEY', text)


if __name__ == '__main__': unittest.main()

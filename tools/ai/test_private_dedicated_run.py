"""Offline checks for two separately allocated GPUs sharing one hard budget."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from decimal import Decimal
import unittest
from unittest.mock import patch

import private_dedicated_run as runner
from test_private_dual_run import fixture


class DedicatedGpuTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        previous = os.getcwd()
        self.addCleanup(os.chdir, previous)
        os.chdir(self.temp.name)
        self.env, self.manifest = fixture()
        self.manifest.update(budget_krw=100000, authorized_budget_krw=100000, prior_upper_krw=7653,
                             selected_roles=['chat', 'solver'])
        self.manifest['roles']['chat']['runtime_seconds'] = 1800
        self.manifest['roles']['solver']['runtime_seconds'] = 14400
        self.env['HASLA_DUAL_MANIFEST'] = json.dumps(self.manifest)
        patch.dict(os.environ, self.env, clear=True).start()
        patch.object(runner.sys, 'argv', ['private_dedicated_run.py']).start()
        patch.object(runner.time, 'monotonic', return_value=100).start()
        patch.object(runner.time, 'sleep', side_effect=AssertionError('unexpected polling wait')).start()
        for method in ('get', 'post', 'head', 'request', 'delete'):
            patch.object(runner.cloud.requests, method, side_effect=AssertionError('external I/O forbidden')).start()

    @contextlib.contextmanager
    def ready(self, *, failed_role=None, creation_failure=None, overprice_role=None, ended=False):
        trace, environments, pod_names = [], {}, {}
        def pod(role):
            return {'id': role + '-pod', 'name': pod_names[role], 'costPerHr': '9.99' if role == overprice_role else '3.99',
                    'containerDiskInGb': 200, 'volumeInGb': 0,
                    'gpu': {'id': runner.cloud.GPU_IDS[2], 'count': 1},
                    'desiredStatus': 'EXITED' if ended else 'RUNNING'}
        def api(method, path, **kwargs):
            trace.append((method, path))
            if path == '/pods':
                return []
            role = path.rsplit('/', 1)[-1].removesuffix('-pod')
            return pod(role)
        def create(name, env, command, gpu_id):
            role = json.loads(env['HASLA_ROLE_JOBS'])[0]['role']
            trace.append(('CREATE', role))
            environments[role] = env
            pod_names[role] = name
            if role == creation_failure:
                raise RuntimeError('RunPod POST status 400')
            return pod(role)
        def result(entity, name, **kwargs):
            role = name.rsplit('-', 1)[-1]
            trace.append(('RESULT', role))
            if ended:
                return None
            return {'status': 'failed' if role == failed_role else 'uploaded',
                    'role': role, 'artifact': role + '-lora:v0', 'stage': 'fixture', 'error_code': 'fixture'}
        def delete(pod_id):
            trace.append(('DELETE', pod_id))
            return True
        patches = [patch.object(runner.inputs, 'verify_pinned_scripts'),
                   patch.object(runner.inputs, 'verify_staged_inputs'),
                   patch.object(runner.cloud, 'private_project', return_value='fixture-entity'),
                   patch.object(runner.cloud, 'capacity_preflight', return_value=runner.cloud.GPU_IDS[2]),
                   patch.object(runner.cloud.requests, 'head', return_value=SimpleNamespace(ok=True)),
                   patch.object(runner.cloud, 'runpod', side_effect=api),
                   patch.object(runner.cloud, 'graphql_create_pod', side_effect=create),
                   patch.object(runner.cloud, 'publish_private_input', side_effect=lambda entity, name, *_:
                       {'HASLA_INPUT_ARTIFACT': f'{entity}/{runner.cloud.PROJECT}/{name}-data:v0'}),
                   patch.object(runner.cloud, 'result_for', side_effect=result),
                   patch.object(runner.cloud, 'delete_and_confirm', side_effect=delete),
                   patch.object(runner.cloud, 'reconcile_created_pods', return_value=[]),
                   patch.object(runner, 'verify_reserved_funding')]
        mocks = [item.start() for item in patches]
        try:
            yield SimpleNamespace(trace=trace, environments=environments, create=mocks[6], publish=mocks[7], delete=mocks[9])
        finally:
            for item in reversed(patches):
                item.stop()

    def test_two_distinct_single_model_pods_exist_before_monitoring_and_each_is_deleted(self):
        output = io.StringIO()
        with self.ready() as state, contextlib.redirect_stdout(output):
            self.assertEqual(runner.main(), 0)
        self.assertEqual([value for event, value in state.trace if event == 'CREATE'], ['chat', 'solver'])
        self.assertLess(state.trace.index(('CREATE', 'solver')), state.trace.index(('RESULT', 'chat')))
        for role, env in state.environments.items():
            jobs = json.loads(env['HASLA_ROLE_JOBS'])
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]['role'], role)
            self.assertEqual(jobs[0]['run'], 'hasla-private-books-12345-' + role)
            self.assertNotIn('RUNPOD_API_KEY', env)
        self.assertEqual(state.delete.call_count, 2)
        events = [json.loads(line) for line in output.getvalue().splitlines()]
        preflight = next(row for row in events if row['event'] == 'dual_preflight')
        self.assertTrue(preflight['dedicated_pods'])
        self.assertLess(sum(int(row['reserved_upper_krw']) for row in preflight['roles'].values()) + 7653 + 5000, 100000)
        self.assertNotIn('SYNTHETIC_PRIVATE', output.getvalue())

    def test_gpu_free_preflight_never_creates_or_publishes(self):
        os.environ['HASLA_PREFLIGHT_ONLY'] = 'true'
        with self.ready() as state, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(), 0)
        state.create.assert_not_called()
        state.publish.assert_not_called()
        state.delete.assert_not_called()

    def test_prepaid_check_covers_full_reserved_caps_without_disclosing_balance(self):
        ledger = SimpleNamespace(reserved_krw=Decimal('23000'), policy=SimpleNamespace(
            fx_krw_per_usd_upper=Decimal('2000'), tax_multiplier=Decimal('1.15')))
        for balance, under, expected in [('10', False, True), ('9.99', False, False),
                                          (True, False, False), ('NaN', False, False),
                                          ('1000000', True, False), ('1000000', None, False)]:
            response = SimpleNamespace(ok=True, close=lambda: None,
                json=lambda: {'data': {'myself': {'clientBalance': balance, 'underBalance': under}}})
            output = io.StringIO()
            with self.subTest(balance=balance, under=under), patch.object(runner.cloud, 'E', self.env), \
                    patch.object(runner.cloud.requests, 'post', return_value=response), contextlib.redirect_stdout(output):
                if expected:
                    runner.verify_reserved_funding(ledger)
                else:
                    with self.assertRaises(RuntimeError):
                        runner.verify_reserved_funding(ledger)
            event = json.loads(output.getvalue())
            self.assertEqual(event['sufficient_for_full_caps'], expected)
            self.assertFalse(event['balance_disclosed'])
            self.assertNotIn('1000000', output.getvalue())

    def test_training_failure_preserves_other_model_success_and_closes_both(self):
        with self.ready(failed_role='chat') as state, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(), 1)
        self.assertEqual(json.loads(Path('private-dual-result.json').read_text())['solver']['artifact'], 'solver-lora:v0')
        self.assertEqual(state.delete.call_count, 2)

    def test_one_creation_rejection_does_not_cancel_other_model(self):
        with self.ready(creation_failure='chat') as state, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(), 1)
        self.assertIn(('RESULT', 'solver'), state.trace)
        state.delete.assert_called_once_with('solver-pod')

    def test_over_ceiling_response_is_deleted_before_results_for_that_model(self):
        with self.ready(overprice_role='chat') as state, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(), 1)
        self.assertIn(('DELETE', 'chat-pod'), state.trace)
        self.assertNotIn(('RESULT', 'chat'), state.trace)
        self.assertIn(('RESULT', 'solver'), state.trace)

    def test_exit_without_verified_result_closes_both_instead_of_waiting(self):
        with self.ready(ended=True) as state, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(), 1)
        self.assertEqual(state.delete.call_count, 2)

    def test_cleanup_accepts_only_two_exact_names(self):
        base = 'hasla-private-books-12345'
        pods = [{'name': base + suffix, 'id': str(i)} for i, suffix in enumerate(('-chat', '-solver', '-other', '6-chat'))]
        with patch.object(runner.cloud, 'runpod', return_value=pods), \
                patch.object(runner.cloud, 'delete_and_confirm', return_value=True) as delete, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.cleanup({'GITHUB_RUN_ID': '12345'}), 0)
        self.assertEqual([call.args[0] for call in delete.call_args_list], ['0', '1'])
        for bad in ('', '../123', '１２３', '123-chat'):
            with self.assertRaises(ValueError):
                runner.target_names(bad)

    def test_lost_creation_response_keeps_unknown_state_until_late_pod_is_deleted(self):
        late = {'id': 'late-chat', 'name': 'hasla-private-books-12345-chat'}
        observations = []
        def reconcile(name):
            observations.append(name)
            if len(observations) == 1:
                return []
            self.assertEqual(json.loads(Path('private-dedicated-pending.json').read_text()), [late['name']])
            return [late]
        with self.ready() as state, \
                patch.object(runner.cloud, 'graphql_create_pod', side_effect=runner.cloud.requests.Timeout('synthetic lost response')) as create, \
                patch.object(runner.cloud, 'reconcile_created_pods', side_effect=reconcile), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, 'unknown creation outcome'):
            runner.main()
        create.assert_called_once()
        state.delete.assert_called_once_with('late-chat')
        self.assertEqual(json.loads(Path('private-dedicated-pending.json').read_text()), [])

    def test_unresolved_creation_is_not_reported_as_deletion_or_released_cost(self):
        output = io.StringIO()
        with self.ready() as state, \
                patch.object(runner.cloud, 'graphql_create_pod', side_effect=runner.cloud.requests.Timeout('synthetic lost response')), \
                contextlib.redirect_stdout(output), self.assertRaisesRegex(RuntimeError, 'still need cleanup'):
            runner.main()
        state.delete.assert_not_called()
        self.assertNotIn('cost_estimate_upper', output.getvalue())
        self.assertNotIn('"deletion_confirmed": true', output.getvalue())
        self.assertEqual(json.loads(Path('private-dedicated-pending.json').read_text()), ['hasla-private-books-12345-chat'])
        with patch.object(runner.cloud, 'runpod', return_value=[]), \
                patch.object(runner.time, 'sleep'), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.cleanup({'GITHUB_RUN_ID': '12345'}), 1)

    def test_role_deadline_is_checked_before_result_query(self):
        with self.ready() as state:
            def stopped(plan, now):
                return plan.role == 'chat' and ('CREATE', 'chat') in state.trace
            with patch.object(runner, 'should_stop', side_effect=stopped), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(runner.main(), 1)
        self.assertNotIn(('RESULT', 'chat'), state.trace)
        self.assertIn(('RESULT', 'solver'), state.trace)


if __name__ == '__main__':
    unittest.main()

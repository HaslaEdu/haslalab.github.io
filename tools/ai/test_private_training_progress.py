"""Offline progress/heartbeat fixtures; no models, credentials or paid I/O."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import private_pod_train as pod
import train_lora as trainer


PRIVATE = 'FIXTURE_PRIVATE_TEXT_HF_TOKEN_MUST_NOT_LEAVE_THE_PROCESS'


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class Process:
    """A process whose wait consumes virtual time and deterministic actions."""
    def __init__(self, clock, actions):
        self.clock = clock
        self.actions = list(actions)
        self.returncode = None
        self.waits = []
        self.killed = False
        self.reaped = False

    def wait(self, timeout=None):
        self.waits.append(timeout)
        if self.killed:
            self.returncode = -9
            self.reaped = True
            return self.returncode
        action = self.actions.pop(0)
        if callable(action):
            action = action()
        kind, value = action
        if kind == 'timeout':
            if timeout is None:
                raise AssertionError('an active process must be waited on with a deadline')
            self.clock.now += timeout
            raise subprocess.TimeoutExpired('fixture-trainer', timeout)
        if kind == 'error':
            raise value
        self.returncode = value
        self.reaped = True
        return value

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed = True


class TrainingProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'optimizer-progress.json'
        self.clock = Clock()
        self.run = SimpleNamespace(summary={}, log=Mock())
        self.output = io.StringIO()
        self.errors = io.StringIO()
        self.addCleanup(patch.stopall)
        patch.object(pod.urllib.request, 'urlopen', side_effect=AssertionError('network forbidden')).start()

    def progress(self, **changes):
        value = {'schema_version': 1, 'phase': 'training', 'steps_completed': 3,
                 'max_steps': 32, 'elapsed_seconds': 30, **changes}
        self.path.write_text(json.dumps(value), encoding='utf8')
        return value

    def supervise(self, process, timeout=120):
        factory = Mock(return_value=process)
        with contextlib.redirect_stdout(self.output), contextlib.redirect_stderr(self.errors):
            result = pod.supervise_training(['fixture-trainer'], cwd=str(self.root),
                env={'HF_TOKEN': PRIVATE}, stderr=io.BytesIO(), timeout=timeout,
                run=self.run, progress_path=self.path, popen=factory, clock=self.clock)
        self.assertEqual(factory.call_args.kwargs['stdout'], subprocess.DEVNULL)
        return result

    def assert_private(self):
        exposed = self.output.getvalue() + self.errors.getvalue() + json.dumps(self.run.summary)
        exposed += repr(self.run.log.call_args_list)
        self.assertNotIn(PRIVATE, exposed)

    def test_heartbeats_continue_until_exit_and_use_actual_optimizer_steps(self):
        self.progress(text=PRIVATE, loss=PRIVATE)
        def later_progress():
            self.progress(steps_completed=7, elapsed_seconds=60)
            return 'timeout', None
        process = Process(self.clock, [('timeout', None), later_progress, ('exit', 0)])
        result = self.supervise(process)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(process.waits, [30, 30, 30])
        self.assertEqual([call.args[0] for call in self.run.log.call_args_list], [
            {'worker_supervisor_alive_seconds': 30, 'optimizer_steps_completed': 3},
            {'worker_supervisor_alive_seconds': 60, 'optimizer_steps_completed': 7},
        ])
        self.assertTrue(all(call.kwargs == {'commit': True} for call in self.run.log.call_args_list))
        self.assertEqual(json.loads(self.run.summary['optimizer_progress_json'])['steps_completed'], 7)
        self.assertTrue(process.reaped)
        self.assertFalse(process.killed)
        self.assert_private()

    def test_missing_or_invalid_progress_only_reports_supervisor_liveness(self):
        for contents in (None, '{"text":"' + PRIVATE + '"}', 'not-json'):
            with self.subTest(contents=contents):
                if contents is None:
                    self.path.unlink(missing_ok=True)
                else:
                    self.path.write_text(contents, encoding='utf8')
                self.run.log.reset_mock()
                process = Process(self.clock, [('timeout', None), ('exit', 0)])
                self.supervise(process)
                self.assertEqual(self.run.log.call_args.args[0], {'worker_supervisor_alive_seconds': 30})
                self.assertNotIn('optimizer_progress_json', self.run.summary)
                self.assert_private()

    def test_reporting_failure_does_not_abort_a_healthy_trainer(self):
        self.progress()
        self.run.log.side_effect = RuntimeError(PRIVATE)
        process = Process(self.clock, [('timeout', None), ('timeout', None), ('exit', 0)])
        self.assertEqual(self.supervise(process).returncode, 0)
        self.assertEqual(self.run.log.call_count, 2)
        self.assertFalse(process.killed)
        self.assert_private()

    def test_deadline_kills_and_reaps_without_extending_the_original_timeout(self):
        process = Process(self.clock, [('timeout', None), ('timeout', None), ('timeout', None)])
        with self.assertRaises(subprocess.TimeoutExpired):
            self.supervise(process, timeout=65)
        self.assertEqual(process.waits[:3], [30, 30, 5])
        self.assertEqual(self.clock.now, 165)
        self.assertTrue(process.killed)
        self.assertTrue(process.reaped)
        self.assert_private()

    def test_wait_exception_still_kills_and_reaps_without_printing_its_message(self):
        process = Process(self.clock, [('error', RuntimeError(PRIVATE))])
        with self.assertRaises(RuntimeError):
            self.supervise(process)
        self.assertTrue(process.killed)
        self.assertTrue(process.reaped)
        self.assert_private()

    def test_nonzero_exit_remains_nonzero_for_existing_failure_classifier(self):
        process = Process(self.clock, [('exit', 17)])
        self.assertEqual(self.supervise(process).returncode, 17)
        self.run.log.assert_not_called()
        self.assertFalse(process.killed)
        self.assertTrue(process.reaped)

    def test_reader_drops_unexpected_fields_and_nonfinite_or_boolean_losses(self):
        self.progress(text=PRIVATE, token=PRIVATE, train_loss=float('nan'), eval_loss=True)
        value = pod.read_numeric_progress(self.path)
        self.assertEqual(set(value), {'schema_version', 'phase', 'steps_completed', 'max_steps', 'elapsed_seconds'})
        self.progress(train_loss=2.5, eval_loss=3, arbitrary_nested={'secret': PRIVATE})
        value = pod.read_numeric_progress(self.path)
        self.assertEqual((value['train_loss'], value['eval_loss']), (2.5, 3))
        self.assertNotIn(PRIVATE, json.dumps(value))

    def test_reader_rejects_wrong_phase_counts_bounds_and_oversized_files(self):
        invalid = ({'phase': PRIVATE}, {'steps_completed': True}, {'steps_completed': -1},
                   {'steps_completed': 33}, {'max_steps': True}, {'max_steps': 32769},
                   {'elapsed_seconds': -1}, {'elapsed_seconds': 18001}, {'schema_version': 2})
        for changes in invalid:
            with self.subTest(changes=changes):
                self.progress(**changes)
                self.assertIsNone(pod.read_numeric_progress(self.path))
        self.path.write_bytes(b' ' * 8193)
        self.assertIsNone(pod.read_numeric_progress(self.path))
        self.progress()
        with patch.object(Path, 'is_symlink', return_value=True):
            self.assertIsNone(pod.read_numeric_progress(self.path))

    def test_callback_writes_only_atomic_numeric_progress_and_safe_losses(self):
        callback = trainer.progress_callback(object, self.path, started=100, clock=self.clock)
        state = SimpleNamespace(global_step=2, max_steps=32)
        control = SimpleNamespace(should_training_stop=False)
        self.clock.now = 130
        callback.on_log(None, state, control, logs={'loss': 2.25, 'eval_loss': float('inf'),
            'text': PRIVATE, 'messages': [PRIVATE], 'train_loss': True})
        value = json.loads(self.path.read_text(encoding='utf8'))
        self.assertEqual(value, {'schema_version': 1, 'phase': 'training', 'steps_completed': 2,
                                'max_steps': 32, 'elapsed_seconds': 30, 'train_loss': 2.25})
        self.assertFalse(self.path.with_name(self.path.name + '.tmp').exists())
        callback.on_train_end(None, state, control)
        self.assertEqual(json.loads(self.path.read_text())['phase'], 'training_ended')
        self.assertNotIn(PRIVATE, self.path.read_text())

    def test_wall_allowance_stops_only_after_a_completed_optimizer_step(self):
        callback = trainer.progress_callback(object, self.path, started=100, wall_seconds=30, clock=self.clock)
        state = SimpleNamespace(global_step=0, max_steps=32)
        control = SimpleNamespace(should_training_stop=False)
        self.clock.now = 145
        callback.on_train_begin(None, state, control)
        callback.on_log(None, state, control, logs={'text': PRIVATE})
        self.assertFalse(control.should_training_stop)
        callback.on_step_end(None, state, control)
        self.assertFalse(control.should_training_stop)
        state.global_step = 1
        self.assertIs(callback.on_step_end(None, state, control), control)
        self.assertTrue(control.should_training_stop)
        self.assertEqual(json.loads(self.path.read_text())['steps_completed'], 1)

    def test_callback_does_not_stop_early_and_rejects_non_integer_step_counts(self):
        callback = trainer.progress_callback(object, self.path, started=100, wall_seconds=60, clock=self.clock)
        control = SimpleNamespace(should_training_stop=False)
        state = SimpleNamespace(global_step=3, max_steps=32)
        self.clock.now = 130
        callback.on_step_end(None, state, control)
        self.assertFalse(control.should_training_stop)
        for step, maximum in ((True, 32), (-1, 32), (33, 32), (1, True)):
            with self.subTest(step=step, maximum=maximum), self.assertRaises(ValueError):
                callback.on_step_end(None, SimpleNamespace(global_step=step, max_steps=maximum), control)


if __name__ == '__main__':
    unittest.main()

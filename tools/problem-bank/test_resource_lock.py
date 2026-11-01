"""Synthetic process checks; no book contents, OCR, network, or model calls."""
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


WRAPPER = Path(__file__).with_name('with-resource-lock.py')


class ResourceLockTests(unittest.TestCase):
    def command(self, root, code, *arguments, wait='5'):
        return [sys.executable, str(WRAPPER), '--lock-file', str(root / 'resource.lock'),
                '--wait-seconds', wait, '--', sys.executable, '-c', code, *arguments]

    def test_jobs_sharing_a_lock_cannot_overlap(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            event = root / 'events.jsonl'
            code = ("import json,sys,time; from pathlib import Path; p=Path(sys.argv[1]); "
                    "f=p.open('a'); f.write(json.dumps([sys.argv[2],'start'])+'\\n'); f.flush(); "
                    "time.sleep(.4); f.write(json.dumps([sys.argv[2],'end'])+'\\n'); f.close()")
            first = subprocess.Popen(self.command(root, code, str(event), 'A'),
                                     stdout=subprocess.DEVNULL)
            second = None
            try:
                deadline = time.monotonic() + 5
                while not event.exists() and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(event.exists())
                second = subprocess.Popen(self.command(root, code, str(event), 'B'),
                                          stdout=subprocess.DEVNULL)
                self.assertEqual(first.wait(timeout=10), 0)
                self.assertEqual(second.wait(timeout=10), 0)
                self.assertEqual([json.loads(line) for line in event.read_text().splitlines()],
                                 [['A', 'start'], ['A', 'end'], ['B', 'start'], ['B', 'end']])
            finally:
                for process in (first, second):
                    if process is not None and process.poll() is None:
                        process.terminate()
                        process.wait(timeout=5)

    def test_child_failure_releases_the_lock_and_preserves_exit_code(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            failed = subprocess.run(self.command(root, 'raise SystemExit(7)'),
                                    capture_output=True)
            self.assertEqual(failed.returncode, 7)
            following = subprocess.run(self.command(root, 'pass'), capture_output=True)
            self.assertEqual(following.returncode, 0, following.stderr)
            self.assertTrue((root / 'resource.lock').exists())

    def test_timeout_does_not_start_the_waiting_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / 'locked'
            first = subprocess.Popen(self.command(root,
                "from pathlib import Path; import sys,time; Path(sys.argv[1]).touch(); time.sleep(.8)",
                str(marker)), stdout=subprocess.DEVNULL)
            try:
                deadline = time.monotonic() + 5
                while not marker.exists() and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(marker.exists())
                waiting = subprocess.run(self.command(root, 'raise RuntimeError("must not run")',
                                                       wait='.01'), capture_output=True)
                self.assertNotEqual(waiting.returncode, 0)
                self.assertIn(b'Timed out', waiting.stderr)
                self.assertNotIn(b'must not run', waiting.stderr)
            finally:
                first.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()

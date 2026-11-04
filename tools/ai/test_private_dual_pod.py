"""Bootstrap fixtures only; child processes, code downloads and GPU work are mocked."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import private_dual_pod as bootstrap


class PrivateDualBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        self.code = b"# synthetic pinned public child fixture\n"
        self.jobs = [{"role": role, "format": "chat" if role == "chat" else "text", "run": "fixture-" + role,
                      "input_artifact": f"fixture-entity/private-project/{role}-data:v1",
                      "training_sha256": "1" * 64, "validation_sha256": "2" * 64} for role in ("chat", "solver")]
        self.env = {"HASLA_ROLE_JOBS": json.dumps(self.jobs), "REPO_SHA": "a" * 40,
                    "HASLA_POD_SCRIPT_SHA256": hashlib.sha256(self.code).hexdigest(), "HF_TOKEN": "fixture-key"}
        patch.dict(os.environ, self.env, clear=True).start()
        patch.object(bootstrap.urllib.request, "urlopen", side_effect=AssertionError("external request forbidden")).start()
        patch.object(bootstrap.subprocess, "run", side_effect=AssertionError("real child process forbidden")).start()

    def test_order_format_and_hash_schema_are_validated_before_any_child(self):
        for jobs in (list(reversed(self.jobs)), [self.jobs[0]],
                     [{**self.jobs[0], "format": "text"}, self.jobs[1]],
                     [{**self.jobs[0], "training_sha256": "bad"}, self.jobs[1]]):
            with self.subTest(jobs=jobs), self.assertRaises(ValueError):
                bootstrap.role_jobs({"HASLA_ROLE_JOBS": json.dumps(jobs)})

    def test_children_run_sequentially_in_separate_role_workspaces_and_environments(self):
        calls = []
        def run(command, **kwargs):
            calls.append((command, kwargs))
            return SimpleNamespace(returncode=0)
        with patch.object(bootstrap.urllib.request, "urlopen", return_value=io.BytesIO(self.code)), \
                patch.object(Path, "write_bytes") as write, patch.object(bootstrap.subprocess, "run", side_effect=run), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bootstrap.main(), 0)
        write.assert_called_once_with(self.code)
        self.assertEqual([call[1]["env"]["ROLE"] for call in calls], ["chat", "solver"])
        for (command, kwargs), role in zip(calls, ("chat", "solver")):
            self.assertEqual(kwargs["env"]["HASLA_WORKSPACE"], "/workspace/" + role)
            self.assertEqual(kwargs["env"]["RUN"], "fixture-" + role)
            self.assertEqual(kwargs["env"]["HASLA_TRAIN_TIMEOUT_SECONDS"], "2700")
            self.assertNotIn("HASLA_ROLE_JOBS", kwargs["env"])
            self.assertEqual(kwargs["timeout"], 3000)

    def test_failed_first_child_or_unverified_code_never_starts_second_child(self):
        with patch.object(bootstrap.urllib.request, "urlopen", return_value=io.BytesIO(self.code)), \
                patch.object(Path, "write_bytes"), \
                patch.object(bootstrap.subprocess, "run", return_value=SimpleNamespace(returncode=1)) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bootstrap.main(), 1)
        run.assert_called_once()
        with patch.object(bootstrap.urllib.request, "urlopen", return_value=io.BytesIO(b"changed code")), \
                patch.object(Path, "write_bytes") as write, patch.object(bootstrap.subprocess, "run") as run, \
                self.assertRaisesRegex(ValueError, "checksum"):
            bootstrap.main()
        write.assert_not_called()
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()

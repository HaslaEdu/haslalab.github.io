"""Bootstrap fixtures only; child processes, code downloads and GPU work are mocked."""
import contextlib
import hashlib
import io
import json
import os
import subprocess
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
        patch.object(Path, "mkdir").start()

    def test_one_role_and_solver_first_keep_the_explicit_provided_order(self):
        for jobs in ([self.jobs[0]], [self.jobs[1]], list(reversed(self.jobs)), self.jobs):
            with self.subTest(jobs=jobs):
                self.assertEqual(bootstrap.role_jobs({"HASLA_ROLE_JOBS": json.dumps(jobs)}), jobs)

    def test_duplicate_wrong_role_format_hash_run_and_artifact_are_rejected(self):
        for jobs in ([], self.jobs + [self.jobs[0]], [self.jobs[0], self.jobs[0]],
                     [{**self.jobs[0], "role": "fast"}], ["not-a-job"],
                     [{**self.jobs[0], "format": "text"}, self.jobs[1]],
                     [{**self.jobs[0], "training_sha256": "bad"}, self.jobs[1]],
                     [{**self.jobs[0], "run": "private run with spaces"}],
                     [self.jobs[0], {**self.jobs[1], "run": self.jobs[0]["run"]}],
                     [{**self.jobs[0], "input_artifact": "fixture/private/input:latest"}]):
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
            self.assertEqual(kwargs["cwd"], "/workspace/" + role)
            self.assertEqual(kwargs["env"]["RUN"], "fixture-" + role)
            self.assertEqual(kwargs["env"]["HASLA_TRAIN_TIMEOUT_SECONDS"], "2700")
            self.assertNotIn("HASLA_ROLE_JOBS", kwargs["env"])
            self.assertEqual(kwargs["timeout"], 3000)
            self.assertEqual(kwargs["stdout"], subprocess.DEVNULL)
            self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)

    def test_chat_failure_still_starts_solver_and_returns_failure_with_safe_role_logs(self):
        output = io.StringIO()
        with patch.object(bootstrap.urllib.request, "urlopen", return_value=io.BytesIO(self.code)), \
                patch.object(Path, "write_bytes"), \
                patch.object(bootstrap.subprocess, "run", side_effect=[SimpleNamespace(returncode=1), SimpleNamespace(returncode=0)]) as run, \
                contextlib.redirect_stdout(output):
            self.assertEqual(bootstrap.main(), 1)
        self.assertEqual([call.kwargs["env"]["ROLE"] for call in run.call_args_list], ["chat", "solver"])
        self.assertEqual([json.loads(line) for line in output.getvalue().splitlines()],
                         [{"status": "failed", "role": "chat"}, {"status": "uploaded", "role": "solver"}])
        self.assertNotIn("fixture-key", output.getvalue())
        self.assertNotIn("input_artifact", output.getvalue())

    def test_single_solver_job_launches_only_solver(self):
        with patch.dict(os.environ, {"HASLA_ROLE_JOBS": json.dumps([self.jobs[1]])}), \
                patch.object(bootstrap.urllib.request, "urlopen", return_value=io.BytesIO(self.code)), \
                patch.object(Path, "write_bytes"), \
                patch.object(bootstrap.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bootstrap.main(), 0)
        run.assert_called_once()
        self.assertEqual(run.call_args.kwargs["env"]["ROLE"], "solver")
        self.assertEqual(run.call_args.kwargs["cwd"], "/workspace/solver")

    def test_solver_first_execution_is_sequential_in_provided_order(self):
        with patch.dict(os.environ, {"HASLA_ROLE_JOBS": json.dumps(list(reversed(self.jobs)))}), \
                patch.object(bootstrap.urllib.request, "urlopen", return_value=io.BytesIO(self.code)), \
                patch.object(Path, "write_bytes"), \
                patch.object(bootstrap.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bootstrap.main(), 0)
        self.assertEqual([call.kwargs["env"]["ROLE"] for call in run.call_args_list], ["solver", "chat"])

    def test_timeout_or_launch_failure_continues_next_independent_child(self):
        for exception in (subprocess.TimeoutExpired(["fixture-python"], 3000), OSError("private launch detail")):
            with self.subTest(exception=type(exception).__name__), \
                    patch.object(bootstrap.urllib.request, "urlopen", return_value=io.BytesIO(self.code)), \
                    patch.object(Path, "write_bytes"), \
                    patch.object(bootstrap.subprocess, "run", side_effect=[exception, SimpleNamespace(returncode=0)]) as run, \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(bootstrap.main(), 1)
                self.assertEqual(run.call_count, 2)
                self.assertEqual([call.kwargs["env"]["ROLE"] for call in run.call_args_list], ["chat", "solver"])
                self.assertNotIn("private launch detail", output.getvalue())

    def test_unverified_code_never_starts_any_child(self):
        with patch.object(bootstrap.urllib.request, "urlopen", return_value=io.BytesIO(b"changed code")), \
                patch.object(Path, "write_bytes") as write, patch.object(bootstrap.subprocess, "run") as run, \
                self.assertRaisesRegex(ValueError, "checksum"):
            bootstrap.main()
        write.assert_not_called()
        run.assert_not_called()

    def test_bootstrap_directory_failure_aborts_before_gpu_children(self):
        with patch.object(bootstrap.urllib.request, "urlopen", return_value=io.BytesIO(self.code)), \
                patch.object(Path, "write_bytes"), patch.object(Path, "mkdir", side_effect=OSError("private path")), \
                patch.object(bootstrap.subprocess, "run") as run, self.assertRaises(OSError):
            bootstrap.main()
        run.assert_not_called()

    def test_unknown_exception_aborts_globally_without_logging_data_or_environment(self):
        with patch.object(bootstrap.urllib.request, "urlopen", return_value=io.BytesIO(self.code)), \
                patch.object(Path, "write_bytes"), \
                patch.object(bootstrap.subprocess, "run", side_effect=RuntimeError("PRIVATE DATA fixture-key")) as run, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(bootstrap.entrypoint(), 1)
        run.assert_called_once()
        self.assertEqual(json.loads(output.getvalue()), {"status": "failed", "role": "bootstrap"})
        self.assertNotIn("PRIVATE DATA", output.getvalue())
        self.assertNotIn("fixture-key", output.getvalue())


if __name__ == "__main__":
    unittest.main()

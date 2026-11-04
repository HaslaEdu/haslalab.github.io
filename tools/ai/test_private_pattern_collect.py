"""Offline privacy, immutable-artifact and no-GPU checks; no SDK/API calls."""
import contextlib
import io
import json
import os
import unittest
from unittest.mock import patch

import community_collect as collector
import private_pattern_collect as remote


class Service:
    def __init__(self, fail_on=None):
        self.checks, self.fail_on = 0, fail_on
    def entity(self):
        return "fixture-entity"
    def require_private(self, entity):
        self.checks += 1
        if self.checks == self.fail_on:
            raise remote.CollectionError("existing_project_not_verified_private")


class Artifact:
    def __init__(self, name, type, metadata):
        self.name, self.type, self.metadata, self.files = name, type, metadata, []
    def add_file(self, path, name):
        self.files.append(name)


class Logged:
    version = "v0"
    qualified_name = "fixture-entity/hasla-ai-private-training/fixture-run:v0"
    url = "https://wandb.ai/fixture-entity/hasla-ai-private-training/artifacts/dataset-pattern/fixture-run/v0"
    digest = "fixture-manifest-digest"
    def wait(self, timeout=None):
        pass


class SDK:
    Artifact = Artifact
    def __init__(self):
        self.summary, self.finished, self.logged, self.init_kwargs, self.settings = {}, False, [], None, None
    def Settings(self, **kwargs):
        self.settings = kwargs
        return kwargs
    def init(self, **kwargs):
        self.init_kwargs = kwargs
        return self
    def log_artifact(self, artifact, aliases=None):
        self.logged.append((artifact, aliases))
        return Logged()
    def finish(self):
        self.finished = True


class PrivatePatternTests(unittest.TestCase):
    def env(self, **kwargs):
        return {"WANDB_API_KEY": "fixture-never-log-this-key", "HASLA_PATTERN_RUN_ID": "fixture-run", **kwargs}
    def config(self):
        return remote.configuration(self.env())
    def fixture_result(self, *args, **kwargs):
        url = "https://orbi.kr/0006658324"
        html = '<div class="layout-board-read"><div class="content-wrap">왜 맞나요?</div></div>'
        row = collector.extract_pattern("orbi", url, html, collector.source_metadata("orbi"))
        return {"patterns": [row], "pattern_records": 1, "raw_content_saved": False, "training_performed": False,
                "sources": [{"source_id": "orbi", "status": "patterns_collected", "patterns": 1}]}

    def test_preflight_performs_no_network_sdk_or_collection(self):
        output = io.StringIO()
        with patch.dict(os.environ, self.env(), clear=True), patch.object(remote, "PrivateWandb", side_effect=AssertionError("network")), patch.object(remote, "execute", side_effect=AssertionError("collection")), contextlib.redirect_stdout(output):
            self.assertEqual(remote.main(["--preflight"]), 0)
        data = json.loads(output.getvalue())
        self.assertEqual(data["network_calls"], 0)
        self.assertFalse(data["privacy_verified"])
        self.assertNotIn("fixture-never-log-this-key", output.getvalue())

    def test_config_rejects_gpu_secrets_invalid_limits_and_unproven_cursor(self):
        for extra in ({"RUNPOD_API_KEY": "never"}, {"HF_TOKEN": "never"}, {"HASLA_PATTERN_MAX_POSTS": "51"},
                      {"HASLA_PATTERN_MAX_PAGES": "4"}, {"HASLA_PATTERN_SOURCES": "reddit"},
                      {"HASLA_PATTERN_CURSORS": json.dumps({"orbi": "https://orbi.kr/list?page=2"})}):
            with self.subTest(extra=extra), self.assertRaises(remote.CollectionError):
                remote.configuration(self.env(**extra))

    def test_exclusion_and_observed_cursor_config_round_trip_without_secret_in_config(self):
        env = self.env(HASLA_PATTERN_EXCLUDED_URLS=json.dumps(["https://orbi.kr/0006658324", "https://orbi.kr/0006658324/title"]),
                       HASLA_PATTERN_CURSORS=json.dumps({"dcinside": "https://gall.dcinside.com/mgallery/board/lists/?id=physics&page=2"}),
                       HASLA_PATTERN_OBSERVED_LISTING_URLS=json.dumps({"dcinside": ["https://gall.dcinside.com/mgallery/board/lists/?id=physics&page=2"]}))
        config = remote.configuration(env)
        self.assertEqual(config["exclude_urls"], {"https://orbi.kr/0006658324"})
        self.assertNotIn(env["WANDB_API_KEY"], repr(config))

    def test_project_privacy_failure_prevents_collection_and_run_creation(self):
        sdk = SDK()
        with self.assertRaises(remote.CollectionError):
            remote.execute(self.config(), Service(fail_on=1), sdk,
                           lambda *args, **kwargs: self.fail("must not collect"))
        self.assertIsNone(sdk.init_kwargs)
        self.assertEqual(sdk.logged, [])

    def test_only_two_files_upload_as_untrainable_immutable_private_artifact(self):
        sdk, service = SDK(), Service()
        with patch.dict(os.environ, {}, clear=True), patch.object(remote, "DeadlineClient", return_value=object()):
            result = remote.execute(self.config(), service, sdk, self.fixture_result)
        self.assertEqual(service.checks, 3)
        self.assertEqual(sdk.logged[0][0].files, ["patterns.jsonl", "collection-report.json"])
        self.assertEqual(sdk.logged[0][1], [])
        self.assertEqual(sdk.logged[0][0].type, "dataset-pattern")
        self.assertFalse(result["trainable"])
        self.assertFalse(result["gpu_used"])
        self.assertTrue(result["artifact"].endswith(":v0"))
        self.assertEqual(set(result["files_sha256"]), {"patterns.jsonl", "collection-report.json"})
        self.assertTrue(sdk.finished)
        self.assertEqual(sdk.settings["console"], "off")
        self.assertTrue(sdk.settings["disable_code"] and sdk.settings["disable_git"])
        self.assertIn("private_collection_result", sdk.summary)

    def test_privacy_change_before_upload_prevents_log_and_finishes_run(self):
        sdk = SDK()
        with patch.dict(os.environ, {}, clear=True), patch.object(remote, "DeadlineClient", return_value=object()), self.assertRaises(remote.CollectionError):
            remote.execute(self.config(), Service(fail_on=3), sdk, self.fixture_result)
        self.assertEqual(sdk.logged, [])
        self.assertTrue(sdk.finished)

    def test_raw_nested_content_and_fabricated_permission_are_rejected(self):
        raw = self.fixture_result()
        raw["patterns"][0]["body"]["text"] = "should never upload"
        with self.assertRaises(remote.CollectionError):
            remote.validate_result(raw)
        forged = self.fixture_result()
        forged["patterns"][0]["metadata"]["rights_status"] = "owned"
        with self.assertRaises(remote.CollectionError):
            remote.validate_result(forged)

    def test_sdk_exception_text_and_credentials_never_reach_public_failure_output(self):
        output = io.StringIO()
        with patch.dict(os.environ, self.env(), clear=True), patch.object(remote, "execute", side_effect=RuntimeError("fixture-never-log-this-key")), contextlib.redirect_stdout(output):
            self.assertEqual(remote.main([]), 1)
        self.assertNotIn("fixture-never-log-this-key", output.getvalue())
        self.assertIn("collection_failed_RuntimeError", output.getvalue())


if __name__ == "__main__":
    unittest.main()

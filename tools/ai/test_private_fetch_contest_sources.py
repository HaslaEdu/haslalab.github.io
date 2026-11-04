"""Offline synthetic fixtures only; never fetch an archive or use credentials."""
from contextlib import redirect_stderr, redirect_stdout
import base64
import copy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import private_fetch_contest_sources as worker


PRIVATE = 'FIXTURE_PRIVATE_BODY_AND_CREDENTIAL_MUST_NOT_BE_PRINTED'
PDF_A = b'%PDF-1.4\nSYNTHETIC_FIXTURE_A'
PDF_B = b'%PDF-1.4\nSYNTHETIC_FIXTURE_B'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def plan_for(*bodies):
    records = [{'alias': f'source_{i:06d}.pdf', 'filename': f'fixture_{i}.pdf',
                'archive_url': f'https://{worker.ARCHIVE_HOST}/pdf/fixture_{i}.pdf',
                'declared_bytes': len(body), 'declared_sha256': None} for i, body in enumerate(bodies)]
    return {'schema_version': 1, 'kind': 'contest_source_fetch_plan', 'private': True,
            'source_catalog_sha256': 'a' * 64, 'records': records, 'exclude_sha256': [],
            'total_declared_bytes': sum(len(b) for b in bodies), 'excluded_cached_aliases': 0, 'excluded_delta_names': 0}


def inline_environment(plan):
    raw = worker.canonical(plan)
    encoded = base64.b64encode(gzip.compress(raw, mtime=0)).decode('ascii')
    parts = [encoded[i:i + 40000] for i in range(0, len(encoded), 40000)]
    manifest = {'version': 1, 'kind': 'contest_source_fetch_plan', 'raw_bytes': len(raw),
                'raw_sha256': sha(raw), 'encoded_sha256': sha(encoded.encode()), 'parts': len(parts)}
    return {worker.INLINE_MANIFEST: json.dumps(manifest),
            **{f'{worker.INLINE_PREFIX}{i:02d}': value for i, value in enumerate(parts)}}


class Response:
    def __init__(self, body=PDF_A, *, status=200, url=None, chunks=None, headers=None):
        self.status_code = status
        self.url = url
        self.headers = {} if headers is None else headers
        self.chunks = [body] if chunks is None else chunks
        self.closed = False

    def iter_content(self, **kwargs):
        yield from self.chunks

    def close(self):
        self.closed = True


class ContestFetchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'private-output'
        self.calls = []
        self.clock = Mock(return_value=100.0)
        self.env = {'WANDB_API_KEY': 'fixture-only-key'}
        self.addCleanup(patch.stopall)
        import requests
        for method in ('get', 'post', 'request', 'delete', 'patch', 'put'):
            patch.object(requests, method, side_effect=AssertionError('network forbidden')).start()

    def run_fetch(self, plan, responses, *, extractor=None, validator=None, deadline=200, disk_free=None):
        queue = iter(responses)
        def get(url, **kwargs):
            self.calls.append((url, kwargs))
            result = next(queue)
            result.url = result.url or url
            return result
        def extract(path, digest, size, stream, deadline, clock):
            stream.write(gzip.compress(b'{"synthetic":true}\n', mtime=0))
            return {'pages': 1, 'native_characters': 80, 'quality_counts': {'text_ready': 1}}
        return worker.fetch_sources(plan, self.output, get=get, deadline=deadline, clock=self.clock,
            pdf_validator=validator or Mock(), extractor=extractor or extract,
            disk_free=disk_free or (lambda _: 20 * 1024**3))

    def test_urls_are_exact_catalogued_https_archive_paths(self):
        valid = plan_for(PDF_A)
        worker.validate_plan(valid)
        for url in ('http://' + worker.ARCHIVE_HOST + '/pdf/fixture_0.pdf',
                    'https://evil.example/pdf/fixture_0.pdf',
                    'https://' + worker.ARCHIVE_HOST + ':443/pdf/fixture_0.pdf',
                    'https://user@' + worker.ARCHIVE_HOST + '/pdf/fixture_0.pdf',
                    'https://' + worker.ARCHIVE_HOST + '/pdf/fixture_0.pdf?token=private',
                    'https://' + worker.ARCHIVE_HOST + '/other/fixture_0.pdf',
                    'https://' + worker.ARCHIVE_HOST + '/pdf/../fixture_0.pdf'):
            with self.subTest(url=url):
                bad = copy.deepcopy(valid)
                bad['records'][0]['archive_url'] = url
                with self.assertRaises(worker.FetchError):
                    worker.validate_plan(bad)
        self.assertFalse(worker.safe_filename('../escape.pdf'))
        self.assertFalse(worker.safe_filename('double%2fescape.pdf'))

    def test_plan_rejects_bool_sizes_aliases_totals_and_duplicate_names(self):
        for field, value in (('declared_bytes', True), ('declared_bytes', 0),
                             ('declared_bytes', worker.MAX_PDF_BYTES + 1), ('alias', '../bad.pdf')):
            plan = plan_for(PDF_A)
            plan['records'][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(worker.FetchError):
                worker.validate_plan(plan)
        plan = plan_for(PDF_A)
        plan['total_declared_bytes'] += 1
        with self.assertRaises(worker.FetchError):
            worker.validate_plan(plan)
        plan = plan_for(PDF_A, PDF_A)
        plan['records'][1]['filename'] = plan['records'][0]['filename']
        with self.assertRaises(worker.FetchError):
            worker.validate_plan(plan)

    def test_prepare_only_reads_metadata_and_excludes_cached_and_verified_delta_names(self):
        catalog = self.root / 'catalog.jsonl'
        rows = []
        for ordinal in range(3):
            rows.append({'filename': f'fixture_{ordinal}.pdf',
                'archive_url': f'https://{worker.ARCHIVE_HOST}/pdf/fixture_{ordinal}.pdf',
                'declared_bytes': 100, 'declared_sha256_candidates': [], 'local_candidates': [PRIVATE],
                'source_references': [{'private_unused': PRIVATE}]})
        catalog.write_text('\n'.join(json.dumps(r) for r in rows), encoding='utf8')
        statuses = self.root / 'status'
        statuses.mkdir()
        (statuses / 'cached.json').write_text(json.dumps({'filename': 'fixture_0.pdf', 'sha256': 'b' * 64}))
        delta = self.root / 'delta.jsonl'
        delta.write_text(json.dumps({'filename': 'fixture_1.pdf', 'sha256': 'c' * 64,
            'status': 'declared_hash_verified_native_extracted', 'declared_sha256_match': True,
            'original_unchanged_verified': True}), encoding='utf8')
        target = self.root / worker.PLAN_FILE
        with patch.object(worker, 'load_private_plan', side_effect=AssertionError('private API forbidden')):
            result = worker.prepare_plan(catalog, statuses, delta, target)
        plan = json.loads(target.read_text(encoding='utf8'))
        self.assertEqual(result['source_names'], 1)
        self.assertTrue(result['not_proven_unique'])
        self.assertEqual(plan['records'][0]['filename'], 'fixture_2.pdf')
        self.assertEqual(plan['exclude_sha256'], ['b' * 64, 'c' * 64])
        self.assertNotIn(PRIVATE, target.read_text())
        self.assertNotIn(str(self.root), target.read_text())
        self.assertEqual(result['plan_sha256'], worker.digest(target))
        with self.assertRaises(FileExistsError):
            worker.prepare_plan(catalog, statuses, delta, target)

    def test_404_skips_and_success_uses_only_get_without_authorization_or_redirects(self):
        missing, success = Response(status=404), Response(PDF_B)
        report, files = self.run_fetch(plan_for(PDF_A, PDF_B), [missing, success])
        self.assertTrue(report['complete'])
        self.assertEqual(report['status_counts'], {'archive_not_found': 1, 'verified_native_extracted': 1})
        self.assertTrue(missing.closed and success.closed)
        self.assertEqual(len(files), 3)
        for _, kwargs in self.calls:
            self.assertFalse(kwargs['allow_redirects'])
            self.assertTrue(kwargs['stream'])
            self.assertNotIn('Authorization', kwargs['headers'])
            self.assertEqual(kwargs['headers']['Accept-Encoding'], 'identity')
        self.assertNotIn(str(self.root), json.dumps(report))

    def test_access_denial_stops_without_retry_or_later_sources(self):
        for status in (403, 429):
            with self.subTest(status=status):
                self.output = self.root / ('status-' + str(status))
                self.calls.clear()
                denied = Response(status=status)
                report, _ = self.run_fetch(plan_for(PDF_A, PDF_B), [denied])
                self.assertFalse(report['complete'])
                self.assertEqual(report['stop_code'], 'archive_access_stopped')
                self.assertEqual(report['remaining_source_names'], 1)
                self.assertEqual(len(self.calls), 1)
                self.assertTrue(denied.closed)

    def test_redirect_foreign_response_and_encoded_content_are_rejected(self):
        cases = [Response(status=302), Response(url='https://evil.example/fixture.pdf'),
                 Response(headers={'Content-Encoding': 'gzip'})]
        for ordinal, response in enumerate(cases):
            self.output = self.root / ('response-' + str(ordinal))
            report, _ = self.run_fetch(plan_for(PDF_A), [response])
            self.assertFalse(report['complete'])
            self.assertTrue(response.closed)
            self.assertEqual(list((self.output / 'pdf').iterdir()), [])

    def test_overlong_short_and_wrong_declared_length_bodies_are_not_retained(self):
        cases = [Response(PDF_A + b'EXTRA'), Response(PDF_A[:-1]),
                 Response(PDF_A, headers={'Content-Length': str(len(PDF_A) + 1)})]
        for ordinal, response in enumerate(cases):
            self.output = self.root / ('size-' + str(ordinal))
            report, _ = self.run_fetch(plan_for(PDF_A), [response])
            self.assertTrue(report['complete'])
            self.assertIsNone(report['stop_code'])
            self.assertIn(report['sources'][0]['failure_code'], ('archive_item_size_limit', 'archive_size_mismatch'))
            self.assertEqual(report['sources'][0]['status'], 'quarantined')
            self.assertEqual(list((self.output / 'pdf').iterdir()), [])

    def test_declared_hash_is_mandatory_when_present_and_magic_is_checked(self):
        plan = plan_for(PDF_A)
        plan['records'][0]['declared_sha256'] = '0' * 64
        report, _ = self.run_fetch(plan, [Response()])
        self.assertEqual(report['sources'][0]['failure_code'], 'archive_sha256_mismatch')
        self.assertEqual(report['sources'][0]['status'], 'quarantined')
        self.output = self.root / 'not-pdf'
        report, _ = self.run_fetch(plan_for(b'not-pdf'), [Response(b'not-pdf')])
        self.assertEqual(report['sources'][0]['failure_code'], 'archive_pdf_magic_mismatch')

    def test_only_actual_sha_deduplicates_existing_and_within_batch(self):
        plan = plan_for(PDF_A, PDF_B, PDF_B)
        plan['exclude_sha256'] = [sha(PDF_A)]
        validator = Mock()
        report, files = self.run_fetch(plan, [Response(PDF_A), Response(PDF_B), Response(PDF_B)], validator=validator)
        self.assertTrue(report['complete'])
        self.assertEqual(report['status_counts'], {'duplicate_existing_sha256': 1,
            'verified_native_extracted': 1, 'duplicate_batch_sha256': 1})
        self.assertEqual(report['sources'][2]['canonical_alias'], 'source_000001.pdf')
        self.assertEqual(validator.call_count, 3)
        self.assertEqual(len(list((self.output / 'pdf').iterdir())), 1)
        self.assertEqual(len(files), 3)
        self.assertEqual(report['sources'][0]['integrity_basis'], 'catalogued_archive_download_local_sha256')

    def test_pdf_exception_and_partial_native_write_are_silent_and_removed(self):
        def bad_extract(path, digest, size, stream, *_):
            print(PRIVATE)
            os.write(2, PRIVATE.encode())
            stream.write(b'partial')
            raise RuntimeError(PRIVATE)
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            report, _ = self.run_fetch(plan_for(PDF_A), [Response()], extractor=bad_extract)
        self.assertEqual(report['sources'][0]['failure_code'], 'native_parse_failed')
        self.assertEqual(report['sources'][0]['status'], 'quarantined')
        self.assertTrue(report['complete'])
        self.assertEqual(list((self.output / 'pdf').iterdir()), [])
        self.assertEqual(list((self.output / 'native').iterdir()), [])
        self.assertNotIn(PRIVATE, output.getvalue() + errors.getvalue() + json.dumps(report))

    def test_partial_failure_keeps_earlier_verified_source_and_partial_inventory(self):
        report, _ = self.run_fetch(plan_for(PDF_A, PDF_B), [Response(), Response(status=503)])
        self.assertFalse(report['complete'])
        self.assertEqual(report['status_counts'], {'verified_native_extracted': 1, 'failed': 1})
        self.assertTrue((self.output / 'pdf/source_000000.pdf').is_file())
        self.assertTrue((self.output / 'native/source_000000.jsonl.gz').is_file())
        self.assertEqual(json.loads((self.output / 'inventory.json').read_text())['complete'], False)

    def test_each_success_is_checkpointed_before_the_next_source_request(self):
        calls = []
        def get(url, **_):
            calls.append(url)
            if len(calls) == 2:
                snapshot = json.loads((self.output / 'inventory.json').read_text())
                self.assertFalse(snapshot['complete'])
                self.assertEqual(snapshot['processed_source_names'], 1)
                self.assertEqual(snapshot['status_counts'], {'verified_native_extracted': 1})
            return Response(url=url, status=404 if len(calls) == 2 else 200)
        def extract(path, digest, size, stream, *_):
            stream.write(b'synthetic')
            return {'pages': 1, 'quality_counts': {'text_ready': 1}, 'native_characters': 80}
        report, _ = worker.fetch_sources(plan_for(PDF_A, PDF_B), self.output, get=get,
            deadline=200, clock=self.clock, extractor=extract, pdf_validator=Mock(), disk_free=lambda _: 10**12)
        self.assertTrue(report['complete'])
        self.assertFalse((self.output / 'inventory.pending.json').exists())

    def test_collision_file_is_preserved_instead_of_becoming_owned_cleanup(self):
        def collide(_):
            (self.output / 'native/source_000000.jsonl.gz').write_text(PRIVATE)
        report, _ = self.run_fetch(plan_for(PDF_A), [Response()], validator=collide)
        self.assertFalse(report['complete'])
        self.assertEqual((self.output / 'native/source_000000.jsonl.gz').read_text(), PRIVATE)
        self.assertEqual(list((self.output / 'pdf').iterdir()), [])

    def test_insufficient_disk_existing_directory_and_deadline_fail_before_get(self):
        get = Mock(side_effect=AssertionError('I/O forbidden'))
        with self.assertRaisesRegex(worker.FetchError, 'insufficient_private_disk_space'):
            worker.fetch_sources(plan_for(PDF_A), self.output, get=get, deadline=200, disk_free=lambda _: 1)
        self.output.mkdir()
        (self.output / 'existing').write_text(PRIVATE)
        with self.assertRaises(FileExistsError):
            worker.fetch_sources(plan_for(PDF_A), self.output, get=get, deadline=200, disk_free=lambda _: 10**12)
        self.assertEqual((self.output / 'existing').read_text(), PRIVATE)
        self.output = self.root / 'deadline'
        report, _ = self.run_fetch(plan_for(PDF_A), [], deadline=99)
        self.assertEqual(report['stop_code'], 'transfer_deadline')
        get.assert_not_called()

    def test_compressed_native_writer_enforces_bound_before_oversized_write(self):
        def extract(path, digest, size, stream, *_):
            stream.write(b'a' * 17)
        with patch.object(worker, 'MAX_TOTAL_NATIVE_BYTES', 16):
            report, _ = self.run_fetch(plan_for(PDF_A), [Response()], extractor=extract)
        self.assertEqual(report['stop_code'], 'native_total_size_limit')
        self.assertEqual(list((self.output / 'native').iterdir()), [])

    def private_artifact(self, plan, *, reference=None, entry_names=None, is_link=False):
        reference = reference or f'fixture/{worker.PROJECT}/fixture-plan:v1'
        raw = worker.canonical(plan)
        entry = SimpleNamespace(size=len(raw), ref=None)
        def download(root):
            path = Path(root) / worker.PLAN_FILE
            path.write_bytes(raw)
            return str(path)
        artifact = SimpleNamespace(qualified_name=reference, type=worker.PLAN_TYPE, state='COMMITTED',
            is_link=is_link, manifest=SimpleNamespace(entries={name: entry for name in (entry_names or [worker.PLAN_FILE])}),
            get_entry=Mock(return_value=SimpleNamespace(download=download)))
        sdk = SimpleNamespace(Api=Mock(return_value=SimpleNamespace(artifact=Mock(return_value=artifact))))
        return reference, sha(raw), artifact, sdk

    def test_private_gate_precedes_sdk_import_or_download_and_pinned_plan_is_exact(self):
        trace = []
        reference, expected, artifact, sdk = self.private_artifact(plan_for(PDF_A))
        def privacy(*_):
            trace.append('privacy')
        def load():
            trace.append('sdk')
            return sdk
        entity, plan, _ = worker.load_private_plan(reference, expected, self.env, self.root, 200,
            self.clock, privacy=privacy, sdk_loader=load)
        self.assertEqual(trace, ['privacy', 'sdk'])
        self.assertEqual(entity, 'fixture')
        self.assertEqual(plan, plan_for(PDF_A))
        self.assertEqual(sdk.Api.call_args.kwargs['overrides'], {'base_url': 'https://api.wandb.ai'})
        artifact.get_entry.assert_called_once_with(worker.PLAN_FILE)
        blocked = Mock(side_effect=worker.FetchError('private_project_not_verified'))
        loader = Mock()
        with self.assertRaises(worker.FetchError):
            worker.load_private_plan(reference, expected, self.env, self.root, 200,
                self.clock, privacy=blocked, sdk_loader=loader)
        loader.assert_not_called()

    def test_input_artifact_links_extra_files_bad_sha_and_foreign_projects_are_rejected(self):
        for changes in ({'is_link': True}, {'entry_names': [worker.PLAN_FILE, 'raw-secret.jsonl']}):
            reference, expected, artifact, sdk = self.private_artifact(plan_for(PDF_A), **changes)
            with self.subTest(changes=changes), self.assertRaises(worker.FetchError):
                worker.load_private_plan(reference, expected, self.env, self.root, 200,
                    self.clock, privacy=Mock(), sdk_loader=lambda: sdk)
            artifact.get_entry.assert_not_called()
        reference, _, artifact, sdk = self.private_artifact(plan_for(PDF_A))
        with self.assertRaisesRegex(worker.FetchError, 'input_plan_hash_mismatch'):
            worker.load_private_plan(reference, '0' * 64, self.env, self.root, 200,
                self.clock, privacy=Mock(), sdk_loader=lambda: sdk)
        for ref in ('fixture/public-project/name:v1', reference.replace(':v1', ':latest'), 'https://private.example/x'):
            with self.assertRaises(worker.FetchError):
                worker.reference_parts(ref)

    def test_wandb_only_credentials_reject_gpu_and_hf_aliases(self):
        for name in worker.FORBIDDEN_CREDENTIALS:
            with self.subTest(name=name), self.assertRaises(worker.FetchError):
                worker.credentials({**self.env, name: PRIVATE})
        worker.credentials(self.env)

    def test_publish_is_private_versioned_and_partial_has_a_distinct_type_and_name(self):
        report, files = self.run_fetch(plan_for(PDF_A), [Response()])
        trace = []
        artifact = SimpleNamespace(add_file=Mock(), wait=Mock(),
            qualified_name=f'fixture/{worker.PROJECT}/hasla-contest-sources-123:v2')
        run = SimpleNamespace(log_artifact=Mock(side_effect=lambda *_: trace.append('upload')), finish=Mock())
        sdk = SimpleNamespace(init=Mock(side_effect=lambda **_: trace.append('init') or run),
            Artifact=Mock(return_value=artifact), Settings=lambda **kw: kw)
        ref = worker.publish_private_sources('fixture', '123', report, files, sdk, self.env, 200,
            self.clock, privacy=lambda *_: trace.append('privacy'))
        self.assertEqual(trace, ['privacy', 'init', 'privacy', 'upload'])
        self.assertTrue(ref.endswith(':v2'))
        self.assertEqual(sdk.init.call_args.kwargs['settings']['base_url'], 'https://api.wandb.ai')
        self.assertEqual(sdk.init.call_args.kwargs['settings']['finish_timeout'], 30)
        self.assertEqual(sdk.init.call_args.kwargs['dir'], str(self.output))
        self.assertEqual(artifact.add_file.call_count, 3)
        self.assertTrue(all(call.kwargs['policy'] == 'immutable' for call in artifact.add_file.call_args_list))
        run.finish.assert_called_once()
        artifact.qualified_name = f'fixture/{worker.PROJECT}/hasla-contest-sources-partial-123:v1'
        ref = worker.publish_private_sources('fixture', '123', {**report, 'complete': False,
            'stop_code': 'transfer_deadline'}, files, sdk, self.env, 200, self.clock, privacy=Mock())
        self.assertIn('sources-partial-', ref)
        self.assertEqual(sdk.Artifact.call_args.kwargs['type'], 'contest-source-partial')
        self.assertFalse(sdk.Artifact.call_args.kwargs['metadata']['complete'])

    def test_native_quality_matches_existing_text_and_private_use_glyph_gates(self):
        class Page:
            rect = SimpleNamespace(width=600, height=800)
            rotation = 0
            def __init__(self, text):
                self.text = text
            def get_text(self, kind, **_):
                return self.text if kind == 'text' else {'width': 600, 'height': 800, 'blocks': []}
            def get_images(self, **_):
                return []
        class Document(list):
            needs_pass = False
            def __enter__(self):
                return self
            def __exit__(self, *_):
                pass
        fake = SimpleNamespace(open=lambda *_: Document([Page('a' * 100), Page('a' * 90 + '\ue001' * 10)]),
                               TEXTFLAGS_DICT=255, TEXT_PRESERVE_IMAGES=4)
        target = io.BytesIO()
        with patch.dict('sys.modules', {'pymupdf': fake}):
            result = worker.extract_native(self.root / 'fixture.pdf', 'a' * 64, 1, target, 200, self.clock)
        rows = [json.loads(line) for line in gzip.decompress(target.getvalue()).decode().splitlines()]
        self.assertEqual(result['quality_counts'], {'text_ready': 1, 'sparse_or_damaged': 1})
        self.assertIn('private_use_glyph_ratio', rows[1]['quality_gate']['issues'])
        self.assertTrue(all(row['independent_scientific_review'] is False for row in rows))

    def test_cli_failure_emits_only_fixed_code_without_exception_text(self):
        output = io.StringIO()
        with patch.object(worker, 'credentials', side_effect=RuntimeError(PRIVATE)), redirect_stdout(output):
            code = worker.main(['--input-artifact', 'fixture', '--manifest-sha256', 'a' * 64, '--out', str(self.output)])
        self.assertEqual(code, 1)
        value = json.loads(output.getvalue())
        self.assertEqual(value, {'event': 'private_contest_fetch_failed', 'code': 'contest_preparation_failed'})
        self.assertNotIn(PRIVATE, output.getvalue())

    def test_bounded_worker_waits_once_and_does_not_launch_resources_or_kill_success(self):
        process = SimpleNamespace(pid=123, wait=Mock(return_value=0))
        factory, kill = Mock(return_value=process), Mock()
        self.assertEqual(worker.bounded_worker(['fixture-worker'], self.env, popen=factory, kill_group=kill), 0)
        process.wait.assert_called_once_with(timeout=3600)
        self.assertTrue(factory.call_args.kwargs['start_new_session'])
        kill.assert_not_called()

    def test_bounded_worker_timeout_kills_only_its_process_group_and_reaps(self):
        process = SimpleNamespace(pid=123, wait=Mock(side_effect=[subprocess.TimeoutExpired('fixture', 3600), -9]))
        kill = Mock()
        with self.assertRaisesRegex(worker.FetchError, 'transfer_deadline'):
            worker.bounded_worker(['fixture-worker'], self.env, popen=Mock(return_value=process), kill_group=kill)
        kill.assert_called_once_with(123)
        self.assertEqual([call.kwargs['timeout'] for call in process.wait.call_args_list], [3600, 10])

    def test_bounded_worker_wait_error_also_kills_and_reaps(self):
        process = SimpleNamespace(pid=456, wait=Mock(side_effect=[RuntimeError(PRIVATE), -9]))
        kill = Mock()
        with self.assertRaises(RuntimeError):
            worker.bounded_worker(['fixture-worker'], self.env, popen=Mock(return_value=process), kill_group=kill)
        kill.assert_called_once_with(456)
        self.assertEqual(process.wait.call_count, 2)

    def test_inline_plan_roundtrip_preserves_the_exact_raw_hash_without_files(self):
        plan = plan_for(PDF_A)
        env = inline_environment(plan)
        decoded, raw_sha = worker.decode_inline_plan(env)
        self.assertEqual(decoded, plan)
        self.assertEqual(raw_sha, sha(worker.canonical(plan)))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_inline_plan_rejects_gaps_extra_parts_oversize_and_boolean_counts(self):
        valid = inline_environment(plan_for(PDF_A))
        cases = [{worker.INLINE_PREFIX + '01': valid[worker.INLINE_PREFIX + '00']},
                 {**valid, worker.INLINE_PREFIX + '01': 'EXTRA'},
                 {**valid, worker.INLINE_PREFIX + '00': 'A' * 40001}]
        for field, value in (('parts', True), ('parts', 17), ('raw_bytes', True), ('raw_bytes', 2 * 1024**2 + 1)):
            env = dict(valid)
            manifest = json.loads(env[worker.INLINE_MANIFEST])
            manifest[field] = value
            env[worker.INLINE_MANIFEST] = json.dumps(manifest)
            cases.append(env)
        for env in cases:
            with self.subTest(fields=list(env)), self.assertRaises(worker.FetchError):
                worker.decode_inline_plan(env)

    def test_inline_hashes_and_bounded_gzip_expansion_fail_closed(self):
        for field in ('raw_sha256', 'encoded_sha256', 'raw_bytes'):
            env = inline_environment(plan_for(PDF_A))
            manifest = json.loads(env[worker.INLINE_MANIFEST])
            manifest[field] = '0' * 64 if field.endswith('sha256') else 1
            env[worker.INLINE_MANIFEST] = json.dumps(manifest)
            with self.subTest(field=field), self.assertRaises(worker.FetchError):
                worker.decode_inline_plan(env)
        # An attacker-declared one-byte payload cannot expand a large gzip in memory.
        encoded = base64.b64encode(gzip.compress(b'X' * (3 * 1024**2), mtime=0)).decode()
        env = {worker.INLINE_PREFIX + '00': encoded, worker.INLINE_MANIFEST: json.dumps({
            'version': 1, 'kind': 'contest_source_fetch_plan', 'parts': 1, 'raw_bytes': 1,
            'raw_sha256': sha(b'X'), 'encoded_sha256': sha(encoded.encode())})}
        with self.assertRaisesRegex(worker.FetchError, 'inline_raw_hash_or_size_mismatch'):
            worker.decode_inline_plan(env)

    def test_inline_preflight_validates_private_project_and_disk_without_fetch_or_sdk(self):
        env = {**self.env, **inline_environment(plan_for(PDF_A))}
        output = io.StringIO()
        with patch.dict(os.environ, env, clear=True), patch.object(worker, 'private_entity', return_value='fixture'), \
                patch.object(worker, 'assert_private') as privacy, \
                patch.object(worker.shutil, 'disk_usage', return_value=SimpleNamespace(free=10**12)), \
                patch.object(worker, 'fetch_sources', side_effect=AssertionError('archive GET forbidden')), \
                patch.object(worker, 'publish_private_sources', side_effect=AssertionError('SDK mutation forbidden')), \
                redirect_stdout(output):
            code = worker.main(['--preflight', '--out', str(self.output)])
        self.assertEqual(code, 0)
        privacy.assert_called_once()
        self.assertFalse(self.output.exists())
        result = json.loads(output.getvalue())
        self.assertEqual(result['event'], 'private_contest_fetch_preflight')
        self.assertTrue(result['free_space_sufficient'])
        self.assertNotIn(worker.ARCHIVE_HOST, output.getvalue())
        self.assertNotIn(PRIVATE, output.getvalue())

    def test_inline_and_artifact_together_fail_before_any_network_or_sdk(self):
        env = {**self.env, **inline_environment(plan_for(PDF_A))}
        output = io.StringIO()
        with patch.dict(os.environ, env, clear=True), patch.object(worker, 'private_entity') as query, redirect_stdout(output):
            code = worker.main(['--preflight', '--out', str(self.output), '--input-artifact',
                f'fixture/{worker.PROJECT}/fixture:v1', '--manifest-sha256', 'a' * 64])
        self.assertEqual(code, 1)
        query.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())['code'], 'invalid_transfer_arguments')

    def test_private_project_query_rejects_public_and_never_echoes_upstream_fields(self):
        for project in (None, {'name': worker.PROJECT, 'access': 'PUBLIC'},
                        {'name': 'foreign', 'access': 'PRIVATE'}):
            response = SimpleNamespace(ok=True, json=lambda: {'data': {'project': project}, 'private': PRIVATE}, close=Mock())
            post = Mock(return_value=response)
            output = io.StringIO()
            with self.subTest(project=project), redirect_stdout(output), self.assertRaises(worker.FetchError):
                worker.assert_private('fixture', self.env, 200, self.clock, post=post)
            response.close.assert_called_once()
            self.assertEqual(post.call_args.args[0], 'https://api.wandb.ai/graphql')
            self.assertNotIn(PRIVATE, output.getvalue())

    def test_entity_discovery_is_only_readonly_viewer_entity_and_validates_its_shape(self):
        response = SimpleNamespace(ok=True, json=lambda: {'data': {'viewer': {'entity': 'fixture'}}}, close=Mock())
        post = Mock(return_value=response)
        entity = worker.private_entity(self.env, 200, self.clock, post=post)
        self.assertEqual(entity, 'fixture')
        self.assertEqual(post.call_args.kwargs['json'], {'query': '{viewer{entity}}'})
        response.close.assert_called_once()

    def test_corrupt_item_is_quarantined_but_next_valid_source_is_processed(self):
        plan = plan_for(PDF_A, PDF_B)
        plan['records'][0]['declared_sha256'] = '0' * 64
        report, files = self.run_fetch(plan, [Response(PDF_A), Response(PDF_B)])
        self.assertTrue(report['complete'])
        self.assertEqual(report['complete_means'], 'all_plan_names_processed_not_all_valid')
        self.assertEqual(report['status_counts'], {'quarantined': 1, 'verified_native_extracted': 1})
        self.assertEqual(len(files), 3)
        self.assertFalse((self.output / 'pdf/source_000000.pdf').exists())
        self.assertTrue((self.output / 'pdf/source_000001.pdf').exists())

    def test_native_parse_error_continues_but_disk_error_stops_the_task(self):
        count = 0
        def extract(path, digest, size, stream, *_):
            nonlocal count
            count += 1
            stream.write(b'partial')
            if count == 1:
                raise ValueError(PRIVATE)
            return {'pages': 1, 'quality_counts': {'text_ready': 1}, 'native_characters': 80}
        report, _ = self.run_fetch(plan_for(PDF_A, PDF_B), [Response(PDF_A), Response(PDF_B)], extractor=extract)
        self.assertEqual(report['status_counts'], {'quarantined': 1, 'verified_native_extracted': 1})
        self.assertTrue(report['complete'])
        self.output = self.root / 'disk-error'
        def disk_error(*_):
            raise OSError(28, PRIVATE)
        report, _ = self.run_fetch(plan_for(PDF_A, PDF_B), [Response(PDF_A)], extractor=disk_error)
        self.assertFalse(report['complete'])
        self.assertEqual(report['stop_code'], 'private_storage_or_transfer_failed')
        self.assertEqual(report['remaining_source_names'], 1)

    def test_global_download_cap_still_stops_instead_of_quarantining(self):
        plan = plan_for(PDF_A)
        with patch.object(worker, 'MAX_TOTAL_PDF_BYTES', len(PDF_A)):
            report, _ = self.run_fetch(plan, [Response(PDF_A + b'X')])
        self.assertFalse(report['complete'])
        self.assertEqual(report['stop_code'], 'archive_total_size_limit')

    def partial_fixture(self):
        plan = plan_for(PDF_A, PDF_B)
        self.run_fetch(plan, [Response(PDF_A), Response(status=403)])
        path = self.output / 'inventory.json'
        report = json.loads(path.read_text())
        report.update(sources=report['sources'][:1], processed_source_names=1, remaining_source_names=1,
                      status_counts={'verified_native_extracted': 1}, stop_code=None)
        path.write_bytes(worker.canonical(report))
        # A killed parser can leave unregistered PDF/gzip partials. Never upload them.
        (self.output / 'pdf/source_000001.pdf.part').write_text(PRIVATE)
        (self.output / 'native/source_000001.jsonl.gz').write_text(PRIVATE)
        return plan

    def test_reaped_worker_partial_checkpoint_only_registers_stable_hashed_files(self):
        plan = self.partial_fixture()
        report, files = worker.load_checkpoint(self.output, plan, 'transfer_deadline')
        self.assertFalse(report['complete'])
        self.assertEqual(report['remaining_source_names'], 1)
        self.assertEqual(report['stop_code'], 'transfer_deadline')
        self.assertEqual([name for _, name in files], ['pdf/source_000000.pdf', 'native/source_000000.jsonl.gz'])
        self.assertNotIn(PRIVATE, json.dumps(report))
        self.assertTrue((self.output / 'pdf/source_000001.pdf.part').is_file())

    def test_checkpoint_hash_mismatch_or_plan_mismatch_prevents_publication(self):
        plan = self.partial_fixture()
        (self.output / 'pdf/source_000000.pdf').write_bytes(PDF_B)
        with self.assertRaisesRegex(worker.FetchError, 'checkpoint_file_rejected'):
            worker.load_checkpoint(self.output, plan)
        wrong = copy.deepcopy(plan)
        wrong['source_catalog_sha256'] = 'd' * 64
        with self.assertRaisesRegex(worker.FetchError, 'checkpoint_plan_mismatch'):
            worker.load_checkpoint(self.output, wrong)

    def test_timeout_controller_still_runs_bounded_private_partial_publisher(self):
        plan = plan_for(PDF_A, PDF_B)
        env = {**self.env, **inline_environment(plan), 'GITHUB_RUN_ID': '123'}
        calls = []
        def child(command, child_env, **kwargs):
            calls.append((command, child_env, kwargs))
            if '--publish-worker' not in command:
                self.partial_fixture()
                self.assertNotIn('WANDB_API_KEY', child_env)
                self.assertFalse(worker.inline_present(child_env))
                raise worker.FetchError('transfer_deadline')
            self.assertEqual(child_env['WANDB_API_KEY'], self.env['WANDB_API_KEY'])
            self.assertEqual(child_env['HASLA_CONTEST_CPU_CHILD'], 'publish')
            self.assertEqual(command[-2:], ['--worker-error', 'transfer_deadline'])
            checked, files = worker.load_checkpoint(self.output, plan, 'transfer_deadline')
            self.assertFalse(checked['complete'])
            self.assertEqual(len(files), 2)
            self.assertLessEqual(kwargs['seconds'], 600)
            return 0
        with patch.dict(os.environ, env, clear=True), patch.object(worker, 'private_entity', return_value='fixture'), \
                patch.object(worker, 'assert_private'), patch.object(worker, 'bounded_worker', side_effect=child), \
                redirect_stdout(io.StringIO()):
            result = worker.main(['--out', str(self.output)])
        self.assertEqual(result, 1)
        self.assertEqual(len(calls), 2)

    def test_partial_publication_inventory_cannot_claim_complete_or_include_unregistered_files(self):
        plan = self.partial_fixture()
        reference = f'fixture/{worker.PROJECT}/hasla-contest-sources-partial-123:v0'
        output = io.StringIO()
        with patch.object(worker, 'private_entity', return_value='fixture'), \
                patch.object(worker, 'publish_private_sources', return_value=reference) as publish, \
                redirect_stdout(output):
            self.assertEqual(worker.publish_checkpoint(plan, self.output, {**self.env, 'GITHUB_RUN_ID': '123'},
                'transfer_deadline'), 0)
        report, files = publish.call_args.args[2:4]
        self.assertFalse(report['complete'])
        self.assertEqual(len(files), 3)
        self.assertTrue(all('.part' not in name and '000001' not in name for _, name in files))
        published = json.loads(files[-1][0].read_text())
        self.assertFalse(published['complete'])
        event = json.loads(output.getvalue())
        self.assertEqual(event['inventory_sha256'], sha(files[-1][0].read_bytes()))
        self.assertEqual(event['plan_sha256'], sha(worker.canonical(plan)))
        self.assertEqual(event['artifact_type'], 'contest-source-partial')
        self.assertFalse(event['complete'])
        self.assertNotIn(PRIVATE, output.getvalue())

    def test_publication_event_hashes_new_publication_bytes_not_prior_checkpoint(self):
        plan = plan_for(PDF_A)
        self.run_fetch(plan, [Response()])
        old_inventory = (self.output / 'inventory.json').read_bytes()
        reference = f'fixture/{worker.PROJECT}/hasla-contest-sources-partial-123:v0'
        output = io.StringIO()
        with patch.object(worker, 'private_entity', return_value='fixture'), \
                patch.object(worker, 'publish_private_sources', return_value=reference) as publish, \
                redirect_stdout(output):
            self.assertEqual(worker.publish_checkpoint(plan, self.output,
                {**self.env, 'GITHUB_RUN_ID': '123'}, 'worker_process_failed'), 0)
        published_path, published_name = publish.call_args.args[3][-1]
        published_raw = published_path.read_bytes()
        self.assertEqual(published_name, 'inventory.json')
        self.assertEqual(published_path.name, 'publication-inventory.json')
        self.assertNotEqual(published_raw, old_inventory)
        event = json.loads(output.getvalue())
        self.assertEqual(event['inventory_sha256'], sha(published_raw))
        self.assertNotEqual(event['inventory_sha256'], sha(old_inventory))
        self.assertEqual(event['plan_sha256'], json.loads(published_raw)['plan_sha256'])
        self.assertEqual(event['plan_sha256'], sha(worker.canonical(plan)))
        self.assertFalse(event['complete'])
        self.assertEqual(event['stop_code'], 'worker_process_failed')
        self.assertEqual((self.output / 'inventory.json').read_bytes(), old_inventory)
        self.assertNotIn(PRIVATE, output.getvalue())


if __name__ == '__main__':
    unittest.main()

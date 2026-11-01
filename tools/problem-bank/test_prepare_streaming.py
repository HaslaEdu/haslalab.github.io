"""Synthetic regression checks for private atomic streaming JSON output."""
import base64
import importlib.util
import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock


SPEC = importlib.util.spec_from_file_location(
    'prepare_extracted_streaming', Path(__file__).with_name('prepare-extracted.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class StreamingJsonTests(unittest.TestCase):
    def setUp(self):
        # CI may select a drive with space without putting corpus paths in tests.
        parent = os.environ.get('PROBLEM_BANK_TEST_TMPDIR') or None
        self.temporary = tempfile.TemporaryDirectory(
            prefix='synthetic-streaming-', dir=parent)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.target = self.root / 'snapshot.json'

    def assert_no_temporary_files(self):
        self.assertEqual({path.name for path in self.root.iterdir()},
                         {self.target.name})

    def test_unicode_and_base64_round_trip_replaces_previous_snapshot(self):
        binary = bytes(range(256)) * 256
        value = {'title': '한글 수식 Δψ · 🌌', 'questions': [
            {'text': '원문과 번역', 'inline_base64':
             base64.b64encode(binary).decode('ascii')}], 'ready': False}
        self.target.write_bytes(b'{"previous": true}\n')

        MODULE.write_json_atomic(self.target, value)

        text = self.target.read_text(encoding='utf-8')
        restored = json.loads(text)
        self.assertEqual(restored, value)
        self.assertIn('한글', text)
        self.assertIn('🌌', text)
        self.assertNotIn('\\ud55c', text)
        self.assertEqual(base64.b64decode(
            restored['questions'][0]['inline_base64'], validate=True), binary)
        self.assert_no_temporary_files()

    def test_circular_value_failure_keeps_previous_snapshot_and_cleans_tmp(self):
        previous = b'{"previous": "complete"}\n'
        self.target.write_bytes(previous)
        value = {'text': 'partial output before failure'}
        value['cycle'] = value

        with self.assertRaisesRegex(ValueError, 'Circular reference'):
            MODULE.write_json_atomic(self.target, value)

        self.assertEqual(self.target.read_bytes(), previous)
        self.assert_no_temporary_files()

    def test_utf8_encoding_failure_keeps_previous_snapshot_and_cleans_tmp(self):
        previous = b'{"previous": "complete"}\n'
        self.target.write_bytes(previous)

        with self.assertRaises(UnicodeEncodeError):
            MODULE.write_json_atomic(
                self.target, {'first': 'valid prefix', 'invalid': '\ud800'})

        self.assertEqual(self.target.read_bytes(), previous)
        self.assert_no_temporary_files()

    def test_replace_failure_keeps_previous_snapshot_and_cleans_tmp(self):
        previous = b'{"previous": "complete"}\n'
        self.target.write_bytes(previous)

        with mock.patch.object(MODULE.os, 'replace',
                               side_effect=OSError('synthetic replace failure')):
            with self.assertRaisesRegex(OSError, 'synthetic replace failure'):
                MODULE.write_json_atomic(self.target, {'next': '한글'})

        self.assertEqual(self.target.read_bytes(), previous)
        self.assert_no_temporary_files()

    def test_exclusive_temp_collision_preserves_the_other_writers_file(self):
        previous = b'{"previous": "complete"}\n'
        self.target.write_bytes(previous)
        identifier = mock.Mock(hex='synthetic-collision')
        occupied = self.target.with_name(
            f'.{self.target.name}.{identifier.hex}.tmp')
        occupied.write_bytes(b'owned by another writer')

        with mock.patch.object(MODULE.uuid, 'uuid4', return_value=identifier):
            with self.assertRaises(FileExistsError):
                MODULE.write_json_atomic(self.target, {'next': 'only'})

        self.assertEqual(self.target.read_bytes(), previous)
        self.assertEqual(occupied.read_bytes(), b'owned by another writer')
        self.assertEqual({p.name for p in self.root.iterdir()},
                         {self.target.name, occupied.name})

    def test_public_checkout_output_is_rejected_without_creating_files(self):
        public_parent = Path(__file__).resolve().parent
        name = f'synthetic-streaming-guard-{uuid.uuid4().hex}.json'
        target = public_parent / name
        self.addCleanup(target.unlink, missing_ok=True)

        with self.assertRaisesRegex(ValueError, 'public checkout'):
            MODULE.write_json_atomic(target, {'synthetic': 'only'})

        self.assertFalse(target.exists())
        self.assertEqual([p.name for p in public_parent.iterdir()
                          if p.name.startswith((name, '.' + name))], [])

    def test_streaming_writer_does_not_materialize_json_with_dumps(self):
        value = {'items': [{'n': n, 'text': '한글'} for n in range(250)]}

        with mock.patch.object(MODULE.json, 'dumps',
                               side_effect=AssertionError('whole-string JSON forbidden')):
            MODULE.write_json_atomic(self.target, value)

        self.assertEqual(json.loads(self.target.read_text(encoding='utf-8')), value)
        self.assert_no_temporary_files()


if __name__ == '__main__':
    unittest.main()

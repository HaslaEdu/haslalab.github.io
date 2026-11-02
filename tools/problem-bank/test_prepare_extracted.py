"""Synthetic import-adapter checks; no real book data or provider calls."""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SPEC = importlib.util.spec_from_file_location('prepare_extracted', Path(__file__).with_name('prepare-extracted.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AdapterTests(unittest.TestCase):
    def fixture(self, root):
        source = {'drive_id': 'synthetic-source-1', 'revision': 'synthetic-revision-1',
                  'sha256': '0' * 64, 'subjects': ['classical_mechanics'],
                  'source_language': 'en', 'level': 'undergraduate', 'page_count': 1}
        (root / 'manifest.json').write_text(json.dumps({'version': 1, 'sources': [source]}))
        folder = root / 'synthetic-book'
        folder.mkdir()
        path = folder / 'synthetic.png'
        Image.new('RGB', (1, 1), 'white').save(path)
        asset = {'local_path': str(path), 'mime_type': 'image/png',
                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                 'spans': [{'page': 1, 'bbox': [0, 0, 1, 1]}]}
        question = {'source': {key: source[key] for key in ('drive_id', 'revision')},
                    'source_language': 'en', 'locator': 'exercise-a', 'original_number': 'unnumbered',
                    'subjects': ['classical_mechanics'], 'level': 'undergraduate',
                    'spans': asset['spans'], 'context': {},
                    'versions': [{'language': 'en', 'role': 'original', 'text': 'A synthetic question.'}],
                    'assets': [dict(asset, role=role) for role in
                               ('source_figure', 'source_footnote', 'source_context')]}
        return folder, question

    def save(self, folder, questions):
        (folder / 'questions.raw.json').write_text(json.dumps({'questions': questions}))

    def prepared(self, root):
        return json.loads((root / 'import-questions.json').read_text())['questions']

    def test_source_roles_survive_full_and_text_only_updates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder, question = self.fixture(root)
            self.save(folder, [question])
            MODULE.prepare(root)
            full = self.prepared(root)[0]
            self.assertEqual([a['role'] for a in full['assets']], ['figure', 'question_crop', 'question_crop'])
            self.assertTrue(all(a.get('inline_base64') for a in full['assets']))
            details = full['context']['source_asset_details']
            self.assertEqual([d['source_role'] for d in details],
                             ['source_figure', 'source_footnote', 'source_context'])
            MODULE.prepare(root, text_only=True)
            update = self.prepared(root)[0]
            self.assertEqual(update['assets'], [])
            self.assertFalse(update['assets_complete'])
            self.assertEqual(update['context']['source_asset_details'], details)

    def test_repeated_printed_numbers_keep_their_locator_translations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder, first = self.fixture(root)
            second = copy.deepcopy(first)
            second['locator'] = 'exercise-b'
            self.save(folder, [first, second])
            (folder / 'translations').mkdir()
            (folder / 'translations/001-002.json').write_text(json.dumps({'items': [
                {'original_number': 'unnumbered', 'locator': 'exercise-a', 'en': 'Question A.', 'ko': '가 문항'},
                {'original_number': 'unnumbered', 'locator': 'exercise-b', 'en': 'Question B.', 'ko': '나 문항'}]}))
            MODULE.prepare(root, text_only=True)
            result = self.prepared(root)
            self.assertEqual([next(v['text'] for v in q['versions'] if v['language'] == 'ko') for q in result],
                             ['가 문항', '나 문항'])

    def test_scoped_question_update_preserves_other_reviewed_source_progress(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected, question = self.fixture(root)
            self.save(selected, [question])
            manifest = json.loads((root / 'manifest.json').read_text())
            other_source = dict(manifest['sources'][0], drive_id='synthetic-source-2')
            manifest['sources'].append(other_source)
            (root / 'manifest.json').write_text(json.dumps(manifest))
            other_folder = root / 'pns-optics'
            other_folder.mkdir()
            other_questions = [dict(copy.deepcopy(question), locator=f'problem-{i}',
                source={'drive_id': other_source['drive_id'], 'revision': other_source['revision']})
                for i in range(160)]
            self.save(other_folder, other_questions)
            MODULE.prepare(root, text_only=True, profiles=['synthetic-book'])
            self.assertEqual(len(self.prepared(root)), 1)
            prepared_manifest = json.loads((root / 'import-manifest.json').read_text())
            other = next(s for s in prepared_manifest['sources'] if s['drive_id'] == other_source['drive_id'])
            self.assertEqual(other['expected_question_count'], 160)
            self.assertTrue(other['extraction_complete'])
            self.save(other_folder, other_questions[:-1])
            MODULE.prepare(root, text_only=True, profiles=['synthetic-book'])
            prepared_manifest = json.loads((root / 'import-manifest.json').read_text())
            other = next(s for s in prepared_manifest['sources'] if s['drive_id'] == other_source['drive_id'])
            self.assertFalse(other['extraction_complete'])

    def test_unknown_scoped_folder_keeps_the_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder, question = self.fixture(root)
            self.save(folder, [question])
            MODULE.prepare(root)
            before = {name: (root / name).read_bytes() for name in
                      ('import-manifest.json', 'import-questions.json')}
            with self.assertRaisesRegex(ValueError, 'no question inventory'):
                MODULE.prepare(root, profiles=['synthetic-book', 'misspelled-book'])
            for name, content in before.items():
                self.assertEqual((root / name).read_bytes(), content)

    def test_empty_scoped_inventory_keeps_the_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder, question = self.fixture(root)
            self.save(folder, [question])
            MODULE.prepare(root)
            before = (root / 'import-questions.json').read_bytes()
            self.save(folder, [])
            with self.assertRaisesRegex(ValueError, 'contain no questions'):
                MODULE.prepare(root, profiles=['synthetic-book'])
            self.assertEqual((root / 'import-questions.json').read_bytes(), before)

    def test_explicit_context_overlay_survives_frozen_repreparation_without_changing_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder, question = self.fixture(root)
            self.save(folder, [question])
            original = (folder / 'questions.raw.json').read_bytes()
            manifest = json.loads((root / 'manifest.json').read_text())
            source = manifest['sources'][0]
            digest = lambda value: hashlib.sha256(value.encode('utf-8')).hexdigest()
            sid = 'src_' + digest(source['drive_id'] + '\0' + source['revision'])
            qid = 'q_' + digest(sid + '\0' + question['locator'])
            before = question['versions'][0]['text']
            after = before + '\n\nGiven $x=2$.'
            overlay = {'version': 1, 'items': [{'question_id': qid, 'source_id': sid,
                'source_sha256': source['sha256'], 'locator': question['locator'],
                'language': 'en', 'base_text_sha256': digest(before),
                'text_sha256': digest(after), 'text': after, 'review_status': 'pending'}]}
            overlay_path = root / 'context-text-overlays.json'
            overlay_path.write_text(json.dumps(overlay))
            MODULE.prepare(root, text_only=True)
            self.assertEqual(self.prepared(root)[0]['versions'][0]['text'], before)
            for _ in range(2):
                MODULE.prepare(root, text_only=True, context_text_overlays=overlay_path)
                version = self.prepared(root)[0]['versions'][0]
                self.assertEqual(version['text'], after)
                self.assertEqual(version['role'], 'original')
                self.assertEqual(version['review_status'], 'pending')
            MODULE.prepare(root, context_text_overlays=overlay_path)
            full = self.prepared(root)[0]
            self.assertTrue(full['assets_complete'])
            self.assertEqual(len(full['assets']), 3)
            self.assertTrue(all(a.get('inline_base64') for a in full['assets']))
            self.assertEqual((folder / 'questions.raw.json').read_bytes(), original)
            prior = (root / 'import-questions.json').read_bytes()
            prior_manifest = (root / 'import-manifest.json').read_bytes()
            overlay['items'][0]['base_text_sha256'] = 'b' * 64
            overlay_path.write_text(json.dumps(overlay))
            with self.assertRaisesRegex(ValueError, 'base text hash mismatch'):
                MODULE.prepare(root, context_text_overlays=overlay_path)
            self.assertEqual((root / 'import-questions.json').read_bytes(), prior)
            self.assertEqual((root / 'import-manifest.json').read_bytes(), prior_manifest)


if __name__ == '__main__':
    unittest.main()

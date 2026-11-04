"""CPU-only checks for the real trainer's private-corpus boundary and group splits."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import train_lora


class DatasetChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def write(self, name, rows):
        path = self.root / name
        path.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
        return path

    def row(self, text, group, split=None):
        return {'text': text, 'metadata': {'group_id': group, **({'split': split} if split else {})}}

    def test_book_pages_remain_together(self):
        rows = [self.row(f'book {book} page {page}', f'book-{book}') for book in range(60) for page in range(4)]
        path = self.write('books.jsonl', rows)
        train, held = train_lora.load(path, 0.2, 'text')
        self.assertTrue(train)
        self.assertTrue(held)
        self.assertFalse({r['metadata']['group_id'] for r in train} & {r['metadata']['group_id'] for r in held})
        self.assertEqual((train, held), train_lora.load(path, 0.2, 'text'))

    def test_fixed_test_split_is_not_used_for_training_or_validation(self):
        path = self.write('fixed.jsonl', [self.row('learn', 'a', 'train'), self.row('check', 'b', 'validation'),
                                         self.row('unseen', 'c', 'test')])
        train, held = train_lora.load(path, data_format='text')
        self.assertEqual([r['text'] for r in train], ['learn'])
        self.assertEqual([r['text'] for r in held], ['check'])

    def test_separate_validation_rejects_document_overlap(self):
        train = self.write('train.jsonl', [self.row('page one', 'same-book', 'train')])
        held = self.write('validation.jsonl', [self.row('page two', 'same-book', 'validation')])
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            train_lora.load(train, data_format='text', validation_path=held)

    def test_separate_validation_rejects_duplicate_content(self):
        train = self.write('train.jsonl', [self.row('identical content', 'a', 'train')])
        held = self.write('validation.jsonl', [self.row('identical content', 'b', 'validation')])
        with self.assertRaisesRegex(ValueError, 'duplicate content'):
            train_lora.load(train, data_format='text', validation_path=held)

    def test_mixed_split_metadata_is_rejected(self):
        path = self.write('mixed.jsonl', [self.row('one', 'a', 'train'), self.row('two', 'b')])
        with self.assertRaisesRegex(ValueError, 'all records'):
            train_lora.load(path, data_format='text')

    def test_chat_requires_user_and_final_assistant(self):
        path = self.write('invalid.jsonl', [{'messages': [{'role': 'assistant', 'content': 'unpaired reply'}]}])
        with self.assertRaisesRegex(ValueError, 'invalid chat'):
            train_lora.load(path)

    def test_prepare_only_runs_without_gpu_packages_and_never_prints_content(self):
        path = self.write('text.jsonl', [self.row('PRIVATE_BOOK_TEXT', 'a', 'train')])
        out = self.root / 'adapter'
        result = subprocess.run([sys.executable, str(Path(train_lora.__file__)), '--format', 'text',
                                 '--prepare-only', str(path), str(out)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['training_records'], 1)
        self.assertFalse(report['weights_updated'])
        self.assertNotIn('PRIVATE_BOOK_TEXT', result.stdout + result.stderr)
        self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()

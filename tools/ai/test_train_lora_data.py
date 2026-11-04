"""CPU-only checks for the real trainer's private-corpus boundary and group splits."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

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
        result = subprocess.run([sys.executable, str(Path(train_lora.__file__)), '--base', 'solver', '--format', 'text',
                                 '--prepare-only', str(path), str(out)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['training_records'], 1)
        self.assertFalse(report['weights_updated'])
        self.assertNotIn('PRIVATE_BOOK_TEXT', result.stdout + result.stderr)
        self.assertFalse(out.exists())
        self.assertEqual(report['role'], 'solver')
        self.assertEqual(report['base_model'], 'Qwen/QwQ-32B')
        self.assertEqual(report['precision'], '4bit')
        self.assertEqual(report['steps_completed'], 0)
        self.assertEqual(report['training_sha256'], train_lora.file_sha256(path))

    def chat_row(self, group, split='train', reviewed=None):
        row = {'messages': [{'role': 'system', 'content': 'A synthetic tutor.'},
                            {'role': 'user', 'content': 'A synthetic question?'},
                            {'role': 'assistant', 'content': 'A synthetic answer.'}],
               'metadata': {'group_id': group, 'split': split}}
        if reviewed:
            row['metadata']['review_status'] = reviewed
        return row

    def test_chat_role_rejects_text_before_any_gpu_import(self):
        path = self.write('book.jsonl', [self.row('PRIVATE_RAW_TEXT', 'a', 'train')])
        result = subprocess.run([sys.executable, str(Path(train_lora.__file__)), '--base', 'chat', '--format', 'text',
                                 '--prepare-only', str(path), str(self.root / 'adapter')], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('does not allow', result.stderr)
        self.assertNotIn('PRIVATE_RAW_TEXT', result.stdout + result.stderr)

    def test_chat_prepare_only_records_bf16_contract_without_loading_model(self):
        path = self.write('chat.jsonl', [self.chat_row('chat-a')])
        result = subprocess.run([sys.executable, str(Path(train_lora.__file__)), '--base', 'chat', '--format', 'chat',
                                 '--max-steps', '8', '--prepare-only', str(path), str(self.root / 'adapter')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual((report['role'], report['loader'], report['precision'], report['rank']),
                         ('chat', 'FastModel', 'bf16', 8))
        self.assertEqual(report['max_length'], 1024)
        self.assertEqual(report['max_steps'], 8)
        self.assertNotIn('A synthetic answer.', result.stdout + result.stderr)
        self.assertFalse((self.root / 'adapter').exists())

    def test_solver_chat_requires_verified_or_approved_solution(self):
        path = self.write('unreviewed.jsonl', [self.chat_row('s-a')])
        with self.assertRaisesRegex(ValueError, 'reviewed solution'):
            train_lora.load(path, 0, 'chat', role='solver')
        for status in ('verified', 'approved'):
            path = self.write(status + '.jsonl', [self.chat_row('s-a', reviewed=status)])
            rows, _ = train_lora.load(path, 0, 'chat', role='solver')
            self.assertEqual(len(rows), 1)

    def test_chat_schema_rejects_raw_text_and_incoherent_turns(self):
        row = self.chat_row('c-a')
        row['text'] = 'unrelated textbook paragraph'
        path = self.write('ambiguous.jsonl', [row])
        with self.assertRaisesRegex(ValueError, 'invalid chat'):
            train_lora.load(path, 0, 'chat', role='chat')
        row = self.chat_row('c-a')
        row['messages'].insert(2, {'role': 'user', 'content': 'A second unpaired question'})
        path = self.write('bad-turns.jsonl', [row])
        with self.assertRaisesRegex(ValueError, 'invalid chat'):
            train_lora.load(path, 0, 'chat', role='chat')

    def test_test_set_group_and_content_leakage_are_rejected(self):
        for test_row in (self.row('separate content', 'a', 'test'), self.row('same content', 'b', 'test')):
            path = self.write('test-leak.jsonl', [self.row('same content', 'a', 'train'), test_row])
            with self.assertRaisesRegex(ValueError, 'test set'):
                train_lora.load(path, 0, 'text')

    def test_role_specific_loader_flags_and_peft_targeting(self):
        chat = train_lora.get_role_config('chat')
        solver = train_lora.get_role_config('solver')
        fake = SimpleNamespace(FastModel='gemma-loader', FastLanguageModel='solver-loader')
        self.assertEqual(train_lora.choose_loader(fake, chat), 'gemma-loader')
        self.assertEqual(train_lora.choose_loader(fake, solver), 'solver-loader')
        opts = train_lora.loader_kwargs(chat, 1024, 'synthetic-bf16-dtype')
        self.assertEqual(opts['dtype'], 'synthetic-bf16-dtype')
        self.assertFalse(opts['load_in_4bit'])
        self.assertTrue(opts['load_in_16bit'])
        self.assertFalse(opts['full_finetuning'])
        self.assertTrue(train_lora.loader_kwargs(solver, 1024, None)['load_in_4bit'])
        self.assertFalse(train_lora.peft_kwargs(chat, 8, 1024)['finetune_vision_layers'])
        self.assertEqual(train_lora.peft_kwargs(solver, 16, 1024)['target_modules'][0], 'q_proj')

    def test_only_verified_library_generation_masks_are_used(self):
        template = '{% generation %}assistant content{% endgeneration %}'
        class Processor:
            chat_template = 'original template'
            def apply_chat_template(self, messages, **kwargs):
                self.messages = messages
                return {'input_ids': [1, 2, 3, 4], 'assistant_masks': [0, 0, 1, 1]}
        processor = Processor()
        enabled, selected, reason = train_lora.assistant_loss_support(processor, lambda _: template)
        self.assertTrue(enabled)
        self.assertEqual(selected, template)
        self.assertEqual(reason, 'library_generation_mask_verified')
        self.assertEqual(processor.chat_template, 'original template')
        self.assertNotIn('A synthetic answer.', json.dumps(processor.messages))
        self.assertFalse(train_lora.assistant_loss_support(processor)[0])
        processor.apply_chat_template = lambda *args, **kwargs: {'input_ids': [1, 2], 'assistant_masks': [0, 0]}
        self.assertFalse(train_lora.assistant_loss_support(processor, lambda _: template)[0])
        processor.apply_chat_template = lambda *args, **kwargs: {'input_ids': [1, 2], 'assistant_masks': [1, 1]}
        self.assertFalse(train_lora.assistant_loss_support(processor, lambda _: template)[0])

    def fake_training_modules(self, bf16=True):
        calls = {}
        class Model:
            def save_pretrained(self, out):
                Path(out).mkdir()
                (Path(out) / 'adapter_model.safetensors').write_bytes(b'synthetic')
        class Processor:
            chat_template = 'synthetic original template'
            eos_token = '<EOS>'
            def apply_chat_template(self, messages, **kwargs):
                return {'input_ids': [1, 2, 3, 4], 'assistant_masks': [0, 0, 1, 1]}
            def save_pretrained(self, out):
                pass
        class Loader:
            @staticmethod
            def from_pretrained(**kwargs):
                calls['loader_options'] = kwargs
                return Model(), Processor()
            @staticmethod
            def get_peft_model(model, **kwargs):
                calls['peft_options'] = kwargs
                return model
        def sft_config(assistant_only_loss=False, **kwargs):
            calls['training_options'] = {**kwargs, 'assistant_only_loss': assistant_only_loss}
            return SimpleNamespace(**calls['training_options'])
        class Trainer:
            def __init__(self, **kwargs):
                calls['trainer'] = kwargs
                self.state = SimpleNamespace(global_step=0, log_history=[])
            def train(self):
                self.state.global_step = calls['training_options']['max_steps']
                self.state.log_history = [{'loss': 2.0}, {'loss': 1.5}, {'eval_loss': 1.8, 'arbitrary': 'not copied'}]
                return SimpleNamespace(metrics={'train_loss': 1.6, 'other_field': 'not copied'})
        modules = {
            'unsloth': SimpleNamespace(FastModel=Loader, FastLanguageModel=Loader, is_bfloat16_supported=lambda: bf16),
            'torch': SimpleNamespace(bfloat16='fake-bfloat16'),
            'datasets': SimpleNamespace(Dataset=SimpleNamespace(from_list=lambda rows: rows)),
            'trl': SimpleNamespace(SFTConfig=sft_config, SFTTrainer=Trainer,
                       get_training_chat_template=lambda _: '{% generation %}answer{% endgeneration %}'),
        }
        return modules, calls

    def test_mocked_chat_training_uses_structured_data_and_records_actual_steps(self):
        path = self.write('chat-fixture.jsonl', [self.chat_row('c-a')])
        out = self.root / 'chat-adapter'
        modules, calls = self.fake_training_modules()
        with patch.dict(sys.modules, modules), contextlib.redirect_stdout(io.StringIO()):
            train_lora.main(['--base', 'chat', '--format', 'chat', '--holdout', '0',
                             '--max-steps', '8', str(path), str(out)])
        manifest = json.loads((out / 'hasla_training_manifest.json').read_text())
        self.assertEqual(manifest['steps_completed'], 8)
        self.assertTrue(manifest['weights_updated'])
        self.assertEqual(manifest['precision'], 'bf16')
        self.assertTrue(manifest['assistant_only_loss'])
        self.assertEqual(manifest['training_sha256'], train_lora.file_sha256(path))
        self.assertFalse(calls['loader_options']['load_in_4bit'])
        self.assertTrue(calls['loader_options']['load_in_16bit'])
        self.assertEqual(calls['loader_options']['dtype'], 'fake-bfloat16')
        self.assertEqual(set(calls['trainer']['train_dataset'][0]), {'messages'})
        self.assertEqual(calls['training_options']['report_to'], 'none')
        self.assertNotIn('A synthetic answer.', json.dumps(manifest))
        self.assertEqual(manifest['train_loss'], 1.6)
        self.assertEqual(manifest['eval_loss'], 1.8)
        self.assertNotIn('arbitrary', manifest)

    def test_mocked_solver_text_training_keeps_qlora_and_full_sequence_loss(self):
        path = self.write('solver-fixture.jsonl', [self.row('synthetic textbook paragraph', 'book-a', 'train')])
        out = self.root / 'solver-adapter'
        modules, calls = self.fake_training_modules()
        with patch.dict(sys.modules, modules), contextlib.redirect_stdout(io.StringIO()):
            train_lora.main(['--base', 'solver', '--format', 'text', '--max-steps', '32', str(path), str(out)])
        manifest = json.loads((out / 'hasla_training_manifest.json').read_text())
        self.assertTrue(calls['loader_options']['load_in_4bit'])
        self.assertFalse(calls['loader_options']['load_in_16bit'])
        self.assertEqual(manifest['precision'], '4bit')
        self.assertEqual(manifest['training_method'], 'qlora')
        self.assertEqual(manifest['steps_completed'], 32)
        self.assertFalse(manifest['assistant_only_loss'])
        self.assertEqual(set(calls['trainer']['train_dataset'][0]), {'text'})

    def test_chat_cannot_silently_fall_back_to_fp16_or_4bit(self):
        path = self.write('chat-bf16.jsonl', [self.chat_row('c-a')])
        modules, calls = self.fake_training_modules(bf16=False)
        with patch.dict(sys.modules, modules), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, 'BF16-capable'):
                train_lora.main(['--base', 'chat', '--holdout', '0', str(path), str(self.root / 'no-adapter')])
        self.assertNotIn('loader_options', calls)

    def test_loss_metrics_do_not_copy_text_nonfinite_or_arbitrary_fields(self):
        metrics = train_lora.safe_loss_metrics([
            {'loss': 2.1, 'input': 'PRIVATE_TEXT'}, {'loss': float('nan')},
            {'eval_loss': float('inf')}, {'eval_loss': 1.9}, {'loss': 'PRIVATE_TEXT'}],
            {'train_loss': 1.7, 'sample': 'PRIVATE_TEXT'})
        self.assertEqual(metrics, {'train_loss': 1.7, 'eval_loss': 1.9})
        self.assertNotIn('PRIVATE_TEXT', json.dumps(metrics))


if __name__ == '__main__':
    unittest.main()

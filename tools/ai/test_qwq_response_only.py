"""Boundary and tamper checks; real upstream/tokenizer CPU audit is a private receipt."""
import copy
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import private_pod_train
import private_verify_adapter
import train_lora


class Processor:
    chat_template = 'synthetic QwQ-format test fixture'
    eos_token_id = 256

    def encode(self, text, **kwargs):
        pieces = text.split('<|im_end|>')
        result = []
        for i, piece in enumerate(pieces):
            if i:
                result.append(self.eos_token_id)
            result.extend(piece.encode('utf8'))
        return result

    def decode(self, ids):
        return ''.join('<|im_end|>' if i == self.eos_token_id else chr(i) for i in ids)

    def apply_chat_template(self, messages, *, tokenize, add_generation_prompt):
        value = ''.join('<|im_start|>' + m['role'] + '\n' + m['content'] + '<|im_end|>\n' for m in messages)
        if add_generation_prompt:
            value += train_lora.QWQ_RESPONSE_PREFIX
        return value

    def save_pretrained(self, output):
        pass


def fixture_helper(_trainer, *, tokenizer, instruction_part, response_part, force_match, return_function):
    # This fake only exercises our independent boundary checks. It is not
    # evidence about the upstream library's mask behavior.
    def mask(batch):
        result = []
        for ids in batch['input_ids']:
            marker = tokenizer.encode(response_part)
            boundary = next(i + len(marker) for i in range(len(ids)) if ids[i:i + len(marker)] == marker)
            end = ids.index(tokenizer.eos_token_id, boundary) + 1
            result.append([-100] * boundary + ids[boundary:end] + [-100] * (len(ids) - end))
        return {'labels': result}
    return mask


class ResponseOnlyTests(unittest.TestCase):
    def setUp(self):
        self.processor = Processor()
        self.rows = [{'messages': [{'role': 'system', 'content': 'Use verified equations.'},
                                  {'role': 'user', 'content': 'Find x.'},
                                  {'role': 'assistant', 'content': 'x=2.'}]}]
        self.template = patch.object(train_lora, 'QWQ_TEMPLATE_SHA256',
                                     hashlib.sha256(self.processor.chat_template.encode()).hexdigest())
        self.template.start()
        self.addCleanup(self.template.stop)

    def prepare(self, rows=None, helper=fixture_helper, max_length=4096):
        return train_lora.qwq_response_only_rows(self.processor, self.rows if rows is None else rows, helper, max_length)

    def test_prompt_is_fully_masked_and_only_empty_thought_closer_and_final_answer_learn(self):
        original = copy.deepcopy(self.rows)
        row = self.prepare()[0]
        selected = self.processor.decode([i for i, label in zip(row['input_ids'], row['labels']) if label != -100])
        self.assertEqual(selected, '</think>\nx=2.<|im_end|>')
        self.assertEqual(self.rows, original)
        self.assertEqual(self.processor.chat_template, Processor.chat_template)

    def test_source_reasoning_channels_special_tokens_multiturn_and_truncation_rejected(self):
        for content in ('<think>private reasoning</think>x=2', '<|im_start|>assistant', '</think>x=2'):
            rows = copy.deepcopy(self.rows)
            rows[0]['messages'][-1]['content'] = content
            with self.subTest(content=content), self.assertRaisesRegex(ValueError, 'control or reasoning'):
                self.prepare(rows)
        rows = copy.deepcopy(self.rows)
        rows[0]['messages'].extend([{'role': 'user', 'content': 'More?'}, {'role': 'assistant', 'content': 'No.'}])
        with self.assertRaisesRegex(ValueError, 'single reviewed turn'):
            self.prepare(rows)
        with self.assertRaisesRegex(ValueError, 'no-truncation'):
            self.prepare(max_length=10)

    def test_unmasked_prompt_masked_answer_or_template_change_fails(self):
        for bad in ('full', 'none', 'one_prompt_token'):
            def helper(*args, **kwargs):
                official = fixture_helper(*args, **kwargs)
                def mask(batch):
                    labels = official(batch)['labels']
                    if bad == 'full':
                        labels = batch['input_ids']
                    elif bad == 'none':
                        labels = [[-100] * len(batch['input_ids'][0])]
                    else:
                        labels[0][0] = batch['input_ids'][0][0]
                    return {'labels': labels}
                return mask
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, 'mask did not preserve'):
                self.prepare(helper=helper)
        self.processor.chat_template += 'changed'
        with self.assertRaisesRegex(ValueError, 'official QwQ template'):
            self.prepare()

    def test_actual_collator_must_preserve_labels_and_mask_padding(self):
        rows = self.prepare()
        good = lambda batch: {key: [row[key] for row in batch] for key in ('input_ids', 'labels')}
        train_lora.verify_response_only_collation(good, rows)
        def bad(batch):
            result = good(batch)
            result['labels'] = result['input_ids']
            return result
        with self.assertRaisesRegex(ValueError, 'collator changed'):
            train_lora.verify_response_only_collation(bad, rows)

    def test_v2_receipts_distinguish_effective_labels_from_trainer_flags(self):
        probe = dict(mask_probe_dimensions=2, mask_probe_batch_size=1, mask_probe_token_count=80,
                     mask_probe_assistant_tokens=20)
        receipt = train_lora.label_diagnostics(self.processor, True, 'official_unsloth_responses_only_verified', probe, 'chat')
        receipt.update(version=2, mask_method='official_unsloth_responses_only', mask_helper_sha256='a' * 64,
                       records_verified=5, trainer_assistant_only_loss=False, trainer_completion_only_loss=False)
        for consumer in (private_pod_train, private_verify_adapter):
            self.assertEqual(consumer.validated_label_diagnostics(receipt, 'chat'), receipt)
            self.assertEqual(consumer.validated_label_diagnostics(receipt, 'chat', 'solver'), receipt)
            with self.assertRaises(ValueError):
                consumer.validated_label_diagnostics(receipt, 'chat', 'chat')
            for fields in ({'version': 1}, {'mask_method': 'made_up'}, {'trainer_assistant_only_loss': True},
                           {'records_verified': 0}, {'assistant_only_loss': False}):
                with self.subTest(consumer=consumer.__name__, fields=fields), self.assertRaises(ValueError):
                    consumer.validated_label_diagnostics({**receipt, **fields}, 'chat')

    def test_training_branch_passes_verified_labels_without_setting_trl_assistant_flag(self):
        calls = {}
        processor = self.processor
        class Model:
            def save_pretrained(self, output):
                Path(output).mkdir()
                (Path(output) / 'adapter_model.safetensors').write_bytes(b'fixture')
        class Loader:
            @staticmethod
            def from_pretrained(**kwargs):
                return Model(), processor
            @staticmethod
            def get_peft_model(model, **kwargs):
                return model
        def config(assistant_only_loss=False, **kwargs):
            return SimpleNamespace(assistant_only_loss=assistant_only_loss, **kwargs)
        class Trainer:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
                self.state = SimpleNamespace(global_step=0, log_history=[])
                calls['trainer'] = self
            def train(self):
                self.state.global_step = 1
                return SimpleNamespace(metrics={'train_loss': 0.5})
        collator = lambda batch: {key: [row[key] for row in batch] for key in ('input_ids', 'labels')}
        modules = {
            'unsloth': SimpleNamespace(FastLanguageModel=Loader, is_bfloat16_supported=lambda: True),
            'unsloth.chat_templates': SimpleNamespace(train_on_responses_only=fixture_helper),
            'torch': SimpleNamespace(bfloat16='fixture'),
            'datasets': SimpleNamespace(Dataset=SimpleNamespace(from_list=lambda rows: rows)),
            'trl': SimpleNamespace(SFTTrainer=Trainer, SFTConfig=config),
            'transformers': SimpleNamespace(DataCollatorForSeq2Seq=lambda **kwargs: collator),
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            row = {**self.rows[0], 'review_status': 'verified', 'metadata': {'group_id': 'fixture-a', 'split': 'train'}}
            data = root / 'train.chat.jsonl'
            data.write_text(json.dumps(row) + '\n', encoding='utf8')
            output = root / 'adapter'
            with patch.dict(sys.modules, modules), contextlib.redirect_stdout(io.StringIO()):
                train_lora.main(['--base', 'solver', '--format', 'chat', '--assistant-only-loss', 'required',
                                 '--max-steps', '1', '--holdout', '0', str(data), str(output)])
            receipt = json.loads((output / 'hasla_training_manifest.json').read_text())
        self.assertFalse(calls['trainer'].args.assistant_only_loss)
        self.assertEqual(set(calls['trainer'].train_dataset[0]), {'input_ids', 'attention_mask', 'labels'})
        self.assertEqual(receipt['label_diagnostics']['mask_method'], 'official_unsloth_responses_only')
        self.assertTrue(receipt['label_diagnostics']['assistant_only_loss'])
        self.assertEqual(receipt['steps_completed'], 1)


if __name__ == '__main__':
    unittest.main()

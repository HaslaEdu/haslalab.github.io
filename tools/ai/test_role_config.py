"""Pure contracts: chat BF16 LoRA and solver 4-bit QLoRA stay separate."""
import unittest

from role_config import BASES, get_role_config, validate_role_format


class RoleConfigTests(unittest.TestCase):
    def test_chat_is_bf16_moe_lora_with_small_initial_rank(self):
        c = get_role_config('chat')
        self.assertEqual(c['base_model'], 'google/gemma-4-26B-A4B-it')
        self.assertEqual(c['loader'], 'FastModel')
        self.assertEqual(c['precision'], 'bf16')
        self.assertEqual(c['training_method'], 'lora')
        self.assertFalse(c['load_in_4bit'])
        self.assertTrue(c['load_in_16bit'])
        self.assertEqual(c['default_rank'], 8)
        self.assertEqual(c['max_length'], 1024)
        self.assertEqual(c['max_steps'], 512)
        with self.assertRaisesRegex(ValueError, 'does not allow'):
            validate_role_format('chat', 'text')

    def test_solver_keeps_qwq_qlora_and_explicit_formats(self):
        c = get_role_config('solver')
        self.assertEqual(c['base_model'], 'Qwen/QwQ-32B')
        self.assertEqual(c['loader'], 'FastLanguageModel')
        self.assertEqual(c['precision'], '4bit')
        self.assertTrue(c['load_in_4bit'])
        self.assertFalse(c['load_in_16bit'])
        self.assertEqual(c['default_rank'], 16)
        self.assertEqual(validate_role_format('solver', 'text'), c)
        chat = validate_role_format('solver', 'chat')
        self.assertEqual(chat['max_length'], 4096)
        self.assertEqual({k: v for k, v in chat.items() if k != 'max_length'},
                         {k: v for k, v in c.items() if k != 'max_length'})
        self.assertEqual(get_role_config('solver')['max_length'], 1024)
        self.assertEqual(c['default_format'], 'text')

    def test_callers_cannot_mutate_shared_configs(self):
        c = get_role_config('chat')
        c['precision'] = '4bit'
        c['allowed_formats'].append('text')
        self.assertEqual(get_role_config('chat')['precision'], 'bf16')
        self.assertEqual(get_role_config('chat')['allowed_formats'], ['chat'])

    def test_legacy_fast_role_remains_separate(self):
        self.assertEqual(BASES['fast'], 'meta-llama/Llama-3.1-8B-Instruct')
        self.assertEqual(get_role_config('fast')['allowed_formats'], ['chat'])
        with self.assertRaisesRegex(ValueError, 'unknown'):
            get_role_config('unknown')


if __name__ == '__main__':
    unittest.main()

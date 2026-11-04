"""Pure role contracts shared by the local trainer and private GPU runner.

Gemma MoE guidance: https://unsloth.ai/docs/models/gemma-4/train
The chat model uses BF16 LoRA; the solver retains 4-bit QLoRA. No downloads,
GPU imports, credentials, or environment-dependent choices belong here.
"""
from copy import deepcopy


GEMMA_26B_QLORA_V1 = 'gemma-26b-qlora-v1'


_ROLES = {
    "chat": {
        "role": "chat", "base_model": "google/gemma-4-26B-A4B-it",
        "base_aliases": ["google/gemma-4-26B-A4B-it", "unsloth/gemma-4-26B-A4B-it",
                         "unsloth/Gemma-4-26B-A4B-it"],
        "loader": "FastModel", "precision": "bf16", "training_method": "lora",
        "load_in_4bit": False, "load_in_16bit": True,
        "default_rank": 8, "max_length": 1024, "max_steps": 512,
        "allowed_formats": ["chat"], "default_format": "chat",
    },
    "solver": {
        "role": "solver", "base_model": "Qwen/QwQ-32B",
        "base_aliases": ["Qwen/QwQ-32B", "unsloth/QwQ-32B", "unsloth/QwQ-32B-bnb-4bit",
                         "unsloth/QwQ-32B-unsloth-bnb-4bit"],
        "loader": "FastLanguageModel", "precision": "4bit", "training_method": "qlora",
        "load_in_4bit": True, "load_in_16bit": False,
        "default_rank": 16, "max_length": 1024, "max_steps": 32768,
        "allowed_formats": ["text", "chat"], "default_format": "text",
    },
    "fast": {
        "role": "fast", "base_model": "meta-llama/Llama-3.1-8B-Instruct",
        "base_aliases": ["meta-llama/Llama-3.1-8B-Instruct",
                         "unsloth/Meta-Llama-3.1-8B-Instruct",
                         "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit"],
        "loader": "FastLanguageModel", "precision": "4bit", "training_method": "qlora",
        "load_in_4bit": True, "load_in_16bit": False,
        "default_rank": 16, "max_length": 1024, "max_steps": 32,
        "allowed_formats": ["chat"], "default_format": "chat",
    },
}

BASES = {role: config["base_model"] for role, config in _ROLES.items()}


def get_role_config(role, training_profile=None):
    if role not in _ROLES:
        raise ValueError("unknown training role")
    config = deepcopy(_ROLES[role])
    if training_profile is not None:
        if role != 'chat' or training_profile != GEMMA_26B_QLORA_V1:
            raise ValueError('unknown or incompatible training profile')
        config.update(training_profile=training_profile, precision='4bit', training_method='qlora',
                      load_in_4bit=True, load_in_16bit=False, supported_gpu_memory_gb=[40, 48])
    return config


def validate_role_format(role, data_format, training_profile=None):
    config = get_role_config(role, training_profile)
    if data_format not in config["allowed_formats"]:
        raise ValueError(f"{role} role does not allow {data_format} format")
    # Reference-solution conversations retain the complete question and answer.
    # Native text remains separately packed at 1024; Gemma is unaffected.
    if role == 'solver' and data_format == 'chat':
        config['max_length'] = 4096
    return config


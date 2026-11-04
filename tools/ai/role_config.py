"""Pure role contracts shared by the local trainer and private GPU runner.

Gemma MoE guidance: https://unsloth.ai/docs/models/gemma-4/train
The chat model uses BF16 LoRA; the solver retains 4-bit QLoRA. No downloads,
GPU imports, credentials, or environment-dependent choices belong here.
"""
from copy import deepcopy


_ROLES = {
    "chat": {
        "role": "chat", "base_model": "google/gemma-4-26B-A4B-it",
        "base_aliases": ["google/gemma-4-26B-A4B-it", "unsloth/gemma-4-26B-A4B-it",
                         "unsloth/Gemma-4-26B-A4B-it"],
        "loader": "FastModel", "precision": "bf16", "training_method": "lora",
        "load_in_4bit": False, "load_in_16bit": True,
        "default_rank": 8, "max_length": 1024, "max_steps": 8,
        "allowed_formats": ["chat"], "default_format": "chat",
    },
    "solver": {
        "role": "solver", "base_model": "Qwen/QwQ-32B",
        "base_aliases": ["Qwen/QwQ-32B", "unsloth/QwQ-32B", "unsloth/QwQ-32B-bnb-4bit",
                         "unsloth/QwQ-32B-unsloth-bnb-4bit"],
        "loader": "FastLanguageModel", "precision": "4bit", "training_method": "qlora",
        "load_in_4bit": True, "load_in_16bit": False,
        "default_rank": 16, "max_length": 1024, "max_steps": 32,
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


def get_role_config(role):
    if role not in _ROLES:
        raise ValueError("unknown training role")
    return deepcopy(_ROLES[role])


def validate_role_format(role, data_format):
    config = get_role_config(role)
    if data_format not in config["allowed_formats"]:
        raise ValueError(f"{role} role does not allow {data_format} format")
    return config


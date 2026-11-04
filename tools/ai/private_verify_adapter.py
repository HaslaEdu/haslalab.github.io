"""Read-only CPU evidence check for private, immutable Hasla LoRA artifacts.

No run/project creation, GPU/model imports, corpus access, or artifact upload.
The only output is a fixed-schema event; SDK output and upstream errors are hidden.
Fresh adapters require departure from the zero B initializer. Continued adapters
require numeric B changes relative to their pinned input. Neither proves quality.
Safetensors format: https://github.com/safetensors/safetensors
PEFT initialization: https://huggingface.co/docs/peft/package_reference/lora
"""
from __future__ import annotations

import argparse
import array
import base64
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import struct
import sys
import tempfile
import urllib.request

from role_config import get_role_config


PROJECT = "hasla-ai-private-training"
GRAPHQL = "https://api.wandb.ai/graphql"
FILES = ("adapter_config.json", "adapter_model.safetensors")
LIMITS = {"chat": 4 * 1024**3, "solver": 2 * 1024**3}
CONFIG_LIMIT = 1024**2
HEADER_LIMIT = 8 * 1024**2
QUERY_LIMIT = 1024**2
CHUNK = 1024**2
DTYPES = {"F32": (4, "I", 0x7F800000, 0x7FFFFFFF),
          "F16": (2, "H", 0x7C00, 0x7FFF),
          "BF16": (2, "H", 0x7F80, 0x7FFF)}
B_NAME = re.compile(r"(^|\.)(lora_B|lora_embedding_B)(?=\.|$)")
A_NAME = re.compile(r"(^|\.)(lora_A|lora_embedding_A)(?=\.|$)")


class VerificationError(Exception):
    """Only a caller-supplied, fixed category can leave this module."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code):
    if not condition:
        raise VerificationError(code)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "json_duplicate_key")
        result[key] = value
    return result


def no_constant(_value):
    raise VerificationError("json_nonfinite_constant")


def json_value(value):
    try:
        return json.loads(value, object_pairs_hook=unique_object, parse_constant=no_constant)
    except VerificationError:
        raise
    except (ValueError, UnicodeError, TypeError, RecursionError):
        raise VerificationError("json_invalid") from None


def validate_arguments(run_id, roles):
    require(isinstance(run_id, str) and re.fullmatch(r"[0-9]{1,32}", run_id) is not None,
            "run_id_invalid")
    chosen = roles.split(",") if isinstance(roles, str) else []
    require(1 <= len(chosen) <= 2 and len(set(chosen)) == len(chosen)
            and all(role in LIMITS for role in chosen), "roles_invalid")
    return chosen


def credentials(env):
    forbidden = {"HF_TOKEN", "HF_API_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_TOKEN",
                 "HUGGINGFACEHUB_API_TOKEN", "HUGGINGFACE_API_KEY", "HF_API_KEY"}
    require(not any(value and (key.upper() in forbidden or
                ("RUNPOD" in key.upper() and any(x in key.upper() for x in ("KEY", "TOKEN"))))
                for key, value in env.items()), "unexpected_gpu_or_model_credential")
    key = env.get("WANDB_API_KEY", "")
    require(isinstance(key, str) and 0 < len(key) <= 1024 and key.isascii()
            and not any(character.isspace() for character in key), "wandb_credential_missing")
    require(env.get("WANDB_BASE_URL", "https://api.wandb.ai").rstrip("/") == "https://api.wandb.ai",
            "wandb_endpoint_invalid")
    return key


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PrivateReader:
    def __init__(self, key, opener=None):
        self.key = key
        self.opener = opener or urllib.request.build_opener(NoRedirect())

    def query(self, query, variables=None):
        payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
        token = base64.b64encode(("api:" + self.key).encode("ascii")).decode("ascii")
        request = urllib.request.Request(GRAPHQL, data=payload, method="POST", headers={
            "Authorization": "Basic " + token, "Content-Type": "application/json",
            "User-Agent": "HaslaPrivateAdapterVerification/1.0 (read-only)"})
        try:
            with self.opener.open(request, timeout=20) as response:
                require(response.status == 200, "private_query_failed")
                data = response.read(QUERY_LIMIT + 1)
            require(len(data) <= QUERY_LIMIT, "private_query_too_large")
            decoded = json_value(data)
            require(isinstance(decoded, dict) and not decoded.get("errors")
                    and isinstance(decoded.get("data"), dict), "private_query_failed")
            return decoded["data"]
        except VerificationError:
            raise
        except Exception:
            raise VerificationError("private_query_failed") from None

    def entity(self):
        entity = (self.query("{viewer{entity}}").get("viewer") or {}).get("entity")
        require(isinstance(entity, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", entity),
                "private_entity_invalid")
        return entity

    def assert_private(self, entity):
        data = self.query("query($e:String!,$p:String!){project(name:$p,entityName:$e){name access}}",
                          {"e": entity, "p": PROJECT})
        project = data.get("project")
        require(isinstance(project, dict) and project.get("name") == PROJECT
                and project.get("access") == "PRIVATE", "private_project_required")

    def result(self, entity, run_id, role):
        data = self.query("query($e:String!,$p:String!,$r:String!){project(name:$p,entityName:$e)"
                          "{run(name:$r){state summaryMetrics}}}",
                          {"e": entity, "p": PROJECT, "r": f"hasla-private-books-{run_id}-{role}"})
        project = data.get("project") or {}
        row = project.get("run")
        return summary_result(row.get("summaryMetrics")) if isinstance(row, dict) else None


def decoded_dict(value):
    for _ in range(3):
        if not isinstance(value, str):
            break
        try:
            value = json_value(value)
        except VerificationError:
            return None
    return value if isinstance(value, dict) else None


def summary_result(summary):
    summary = decoded_dict(summary)
    if summary is None:
        return None
    for key in ("private_training_result_json", "private_training_result"):
        result = decoded_dict(summary.get(key))
        if result is not None and result.get("status") in ("uploaded", "failed"):
            return result
    result = {}
    fields = ("status", "artifact", "role", "base_model", "rank", "steps_completed",
              "training_profile", "precision", "training_method", "runtime_profile_proof", "format", "label_diagnostics",
              "adapter_files", "adapter_sha256", "initial_adapter", "resume_script_sha256",
              "initial_adapter_model_sha256", "optimizer_state_restored", "formatter_provenance", "baseline_evaluation",
              "training_records", "validation_records")
    for field in fields:
        for separator in (".", "/"):
            key = "private_training_result" + separator + field
            if key in summary:
                result[field] = summary[key]
                break
    return result if result.get("status") in ("uploaded", "failed") else None


def validated_label_diagnostics(value, data_format):
    statuses = {'plain_text_full_sequence_loss', 'explicit_full_sequence_loss',
                'template_has_no_generation_markers', 'generation_mask_not_available',
                'generation_mask_not_selective', 'generation_mask_shape_invalid', 'generation_mask_check_failed',
                'library_generation_mask_verified', 'installed_trl_has_no_assistant_only_loss'}
    numbers = ('mask_probe_dimensions', 'mask_probe_batch_size', 'mask_probe_token_count', 'mask_probe_assistant_tokens')
    keys = {'version', 'assistant_only_loss', 'assistant_loss_status', 'selected_template_sha256',
            'processor_class', 'tokenizer_class', *numbers}
    if (not isinstance(value, dict) or set(value) != keys or type(value['version']) is not int or value['version'] != 1
            or type(value['assistant_only_loss']) is not bool or not isinstance(value['assistant_loss_status'], str)
            or value['assistant_loss_status'] not in statuses
            or data_format not in ('text', 'chat')):
        raise ValueError('invalid_label_diagnostics')
    template = value['selected_template_sha256']
    if not (isinstance(template, str) and re.fullmatch(r'[a-f0-9]{64}', template) or template is None and data_format == 'text'):
        raise ValueError('invalid_label_diagnostics')
    if any(not isinstance(value[k], str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,79}', value[k])
           for k in ('processor_class', 'tokenizer_class')):
        raise ValueError('invalid_label_diagnostics')
    if any(type(value[k]) is not int or not 0 <= value[k] <= 4096 for k in numbers):
        raise ValueError('invalid_label_diagnostics')
    dimensions, batch, tokens, selected = [value[k] for k in numbers]
    if (dimensions not in (0, 1, 2) or selected > tokens or dimensions == 0 and (batch or tokens or selected)
            or dimensions == 1 and batch != 1 or tokens and batch != 1):
        raise ValueError('invalid_label_diagnostics')
    verified = value['assistant_loss_status'] == 'library_generation_mask_verified'
    if value['assistant_only_loss'] != verified or verified and not (dimensions in (1, 2) and batch == 1 and 0 < selected < tokens):
        raise ValueError('invalid_label_diagnostics')
    if ((data_format == 'text') != (value['assistant_loss_status'] == 'plain_text_full_sequence_loss')
            or data_format == 'text' and (dimensions or batch or tokens or selected)):
        raise ValueError('invalid_label_diagnostics')
    return dict(value)
def validated_gemma_receipts(report, role, profile, training_records, validation_records, validation_sha=None):
    names = ('formatter_provenance', 'baseline_evaluation')
    if not any(name in report for name in names):
        return {}
    if role != 'chat' or profile != 'gemma-26b-qlora-v1' or 'formatter_provenance' not in report:
        raise ValueError('invalid_gemma_receipts')
    value = report['formatter_provenance']
    fixed = {'version': 1, 'policy': 'official_unsloth_gemma4_empty_thought_v1',
             'processor_wrapper_preserved': True, 'single_bos_verified': True,
             'prefix_consistency_verified': True, 'enable_thinking': False, 'official_template_replacement': True,
             'upstream_fix': '3182f568d4e2e87b0945168e04f6e6265700f117'}
    hashes = ('helper_module_sha256', 'source_template_sha256', 'selected_template_sha256',
              'vocabulary_sha256', 'special_tokens_sha256')
    extra = {'unsloth_version', 'records_checked', 'training_records', 'validation_records', 'validation_sha256', *hashes}
    if (not isinstance(value, dict) or set(value) != set(fixed) | extra
            or any(type(value.get(k)) is not type(v) or value[k] != v for k, v in fixed.items())
            or any(not isinstance(value[k], str) or not re.fullmatch(r'[0-9a-f]{64}', value[k]) for k in hashes)
            or value['source_template_sha256'] not in ('ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4',
                                                        '6971ec85ae5b8a161889e66720199f18ccf0ff8232909a01e0bdce244e507ab1')
            or value['selected_template_sha256'] != '6971ec85ae5b8a161889e66720199f18ccf0ff8232909a01e0bdce244e507ab1'
            or not isinstance(value['unsloth_version'], str) or not re.fullmatch(r'[0-9A-Za-z.+_-]{1,80}', value['unsloth_version'])
            or type(training_records) is not int or not 0 < training_records <= 1000000
            or type(validation_records) is not int or not 0 <= validation_records <= 1000000
            or any(type(value[k]) is not int for k in ('records_checked', 'training_records', 'validation_records'))
            or (value['training_records'], value['validation_records'], value['records_checked']) !=
               (training_records, validation_records, training_records + validation_records)):
        raise ValueError('invalid_gemma_receipts')
    digest = value['validation_sha256']
    if validation_records:
        if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('invalid_gemma_receipts')
    elif digest is not None:
        raise ValueError('invalid_gemma_receipts')
    if validation_sha is not None and digest != validation_sha:
        raise ValueError('invalid_gemma_receipts')
    labels = report.get('label_diagnostics')
    if not isinstance(labels, dict) or labels.get('selected_template_sha256') != value['selected_template_sha256']:
        raise ValueError('invalid_gemma_receipts')
    clean = {'formatter_provenance': dict(value)}
    if 'baseline_evaluation' in report:
        baseline = report['baseline_evaluation']
        required = {'version', 'baseline_eval_loss', 'baseline_method', 'same_validation_sha256', 'validation_records', 'zero_b_tensors'}
        if (not isinstance(baseline, dict) or set(baseline) != required
                or type(baseline['version']) is not int or baseline['version'] != 1
                or baseline['baseline_method'] != 'fresh_zero_b_before_optimizer_v1'
                or type(baseline['baseline_eval_loss']) not in (int, float) or not math.isfinite(baseline['baseline_eval_loss'])
                or baseline['baseline_eval_loss'] < 0 or not validation_records
                or baseline['same_validation_sha256'] != digest
                or type(baseline['validation_records']) is not int or baseline['validation_records'] != validation_records
                or type(baseline['zero_b_tensors']) is not int or not 0 < baseline['zero_b_tensors'] <= 10000):
            raise ValueError('invalid_gemma_receipts')
        clean['baseline_evaluation'] = dict(baseline)
    elif validation_records:
        raise ValueError('invalid_gemma_receipts')
    return clean
def expected_result(result, entity, run_id, role):
    try:
        validated_gemma_receipts(result, role, result.get('training_profile'),
                                 result.get('training_records'), result.get('validation_records'))
    except ValueError:
        raise VerificationError('result_gemma_receipts_invalid') from None
    if 'label_diagnostics' in result:
        try:
            validated_label_diagnostics(result['label_diagnostics'], result.get('format'))
        except ValueError:
            raise VerificationError('result_label_diagnostics_invalid') from None
    try:
        config = get_role_config(role, result.get('training_profile'))
    except ValueError:
        raise VerificationError('result_training_profile_invalid') from None
    if result.get('training_profile') is not None:
        require(result.get('precision') == config['precision']
                and result.get('training_method') == config['training_method'], 'result_training_profile_invalid')
        proof = result.get('runtime_profile_proof')
        fixed = {'first_optimizer_step_completed': True, 'gpu_count': 1, 'cpu_or_disk_offload_used': False}
        extra = {'gpu_name', 'physical_vram_bytes', 'first_step_peak_allocated_bytes',
                 'first_step_peak_reserved_bytes'}
        dense = result['training_profile'] == 'qwq-32b-qlora-48gb-v1'
        if dense:
            require(result.get('format') == 'text', 'result_training_profile_invalid')
            fixed.update(dense_quantization_verified=True, dense_layers=64, quantized_linear_tensors=448,
                         base_parameters_frozen=True)
        else:
            fixed.update(expert_quantization_verified=True, expert_blocks=30, quantized_expert_tensors=60)
            extra.update(('expert_quantizer_module_sha256', 'unsloth_zoo_version', 'expert_quantizer_upstream_fix'))
        require(isinstance(proof, dict) and set(proof) == set(fixed) | extra
                and all(type(proof.get(k)) is type(v) and proof[k] == v for k, v in fixed.items()),
                'result_training_profile_proof_invalid')
        physical, allocated, reserved = [proof[k] for k in ('physical_vram_bytes',
                                         'first_step_peak_allocated_bytes', 'first_step_peak_reserved_bytes')]
        require(proof['gpu_name'] in ('NVIDIA A100-PCIE-40GB', 'NVIDIA L40S', 'NVIDIA L40', 'NVIDIA A40')
                and all(type(v) is int for v in (physical, allocated, reserved))
                and 37 * 1024**3 <= physical <= 49 * 1024**3 and 0 < allocated <= reserved <= physical,
                'result_training_profile_proof_invalid')
        if not dense:
            require(isinstance(proof['expert_quantizer_module_sha256'], str)
                and re.fullmatch(r'[0-9a-f]{64}', proof['expert_quantizer_module_sha256'])
                and isinstance(proof['unsloth_zoo_version'], str)
                and re.fullmatch(r'[0-9A-Za-z.+_-]{1,80}', proof['unsloth_zoo_version'])
                and proof['expert_quantizer_upstream_fix'] == '9adee9372d5d86749e757d5a91c6bfa30c2ff674',
                'result_training_profile_proof_invalid')
    require(result.get("role") == role and result.get("base_model") in config["base_aliases"],
            "result_role_or_base_mismatch")
    require(type(result.get("rank")) is int and result["rank"] in (8, 16)
            and result["rank"] == config["default_rank"], "result_rank_mismatch")
    require(type(result.get("steps_completed")) is int and 0 < result["steps_completed"] <= 10**7,
            "result_steps_invalid")
    prefix = f"{entity}/{PROJECT}/hasla-private-books-{run_id}-{role}-lora:"
    artifact = result.get("artifact")
    require(isinstance(artifact, str) and artifact.startswith(prefix)
            and re.fullmatch(r"v[0-9]+", artifact[len(prefix):]), "artifact_reference_invalid")
    inventory = result.get("adapter_files")
    require(isinstance(inventory, list) and len(inventory) == len(FILES), "result_inventory_invalid")
    clean = []
    for name, row in zip(FILES, inventory):
        cap = CONFIG_LIMIT if name == FILES[0] else LIMITS[role]
        require(isinstance(row, dict) and set(row) == {"name", "bytes", "sha256"}
                and row["name"] == name and type(row["bytes"]) is int and 0 < row["bytes"] <= cap
                and isinstance(row["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]),
                "result_inventory_invalid")
        clean.append(row)
    require(sum(row["bytes"] for row in clean) <= LIMITS[role], "adapter_size_limit")
    digest = hashlib.sha256(json.dumps(clean, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(result.get("adapter_sha256") == digest, "result_inventory_hash_mismatch")
    return artifact, clean


def config_check(path, role, rank):
    require(0 < path.stat().st_size <= CONFIG_LIMIT, "config_size_limit")
    config = json_value(path.read_bytes())
    require(isinstance(config, dict) and config.get("peft_type") == "LORA", "adapter_type_invalid")
    require(config.get("base_model_name_or_path") in get_role_config(role)["base_aliases"],
            "adapter_base_mismatch")
    require(type(config.get("r")) is int and config["r"] == rank and rank in (8, 16),
            "adapter_rank_mismatch")
    require(not config.get("rank_pattern"), "adapter_rank_pattern_unsupported")
    initializer = config.get("init_lora_weights", True)
    return initializer is True or (type(initializer) is str and initializer == "gaussian")


def inspect_safetensors(path, rank, maximum):
    """Validate the complete container, then inspect every B element without conversions."""
    size = path.stat().st_size
    require(8 < size <= maximum, "safetensors_size_limit")
    with path.open("rb") as handle:
        prefix = handle.read(8)
        require(len(prefix) == 8, "safetensors_prefix_invalid")
        header_length = struct.unpack("<Q", prefix)[0]
        require(2 <= header_length <= HEADER_LIMIT and 8 + header_length <= size,
                "safetensors_header_size_invalid")
        header_bytes = handle.read(header_length)
        require(header_bytes.startswith(b"{"), "safetensors_header_invalid")
        # The format permits space padding only, not arbitrary trailing JSON data.
        try:
            text = header_bytes.decode("utf-8")
            header, end = json.JSONDecoder(object_pairs_hook=unique_object,
                                          parse_constant=no_constant).raw_decode(text)
        except VerificationError:
            raise
        except (ValueError, UnicodeError, RecursionError):
            raise VerificationError("safetensors_header_invalid") from None
        require(all(character == " " for character in text[end:]) and isinstance(header, dict)
                and len(header) <= 100000, "safetensors_header_invalid")
        data_start = 8 + header_length
        data_size = size - data_start
        tensors = {}
        for name, tensor in header.items():
            if name == "__metadata__":
                require(isinstance(tensor, dict) and all(isinstance(k, str) and isinstance(v, str)
                        for k, v in tensor.items()), "safetensors_metadata_invalid")
                continue
            require(isinstance(name, str) and 0 < len(name) <= 4096 and isinstance(tensor, dict)
                    and set(tensor) == {"dtype", "shape", "data_offsets"}, "tensor_header_invalid")
            dtype, shape, offsets = tensor["dtype"], tensor["shape"], tensor["data_offsets"]
            require(isinstance(dtype, str) and dtype in DTYPES, "tensor_dtype_unsupported")
            require(isinstance(shape, list) and len(shape) <= 32
                    and all(type(dim) is int and 0 <= dim <= maximum for dim in shape),
                    "tensor_shape_invalid")
            require(isinstance(offsets, list) and len(offsets) == 2
                    and all(type(offset) is int for offset in offsets)
                    and 0 <= offsets[0] <= offsets[1] <= data_size, "tensor_offsets_invalid")
            elements = 1
            for dimension in shape:
                elements *= dimension
            require(elements * DTYPES[dtype][0] == offsets[1] - offsets[0], "tensor_size_mismatch")
            tensors[name] = (dtype, shape, offsets, elements)
        cursor = 0
        for _, _, offsets, _ in sorted(tensors.values(), key=lambda tensor: (tensor[2][0], tensor[2][1])):
            require(offsets[0] == cursor, "tensor_layout_invalid")
            cursor = offsets[1]
        require(cursor == data_size, "tensor_layout_invalid")
        b_tensors = {name: tensor for name, tensor in tensors.items() if B_NAME.search(name)}
        require(bool(b_tensors), "lora_b_missing")
        a_names = {name for name in tensors if A_NAME.search(name)}
        paired_a = set()
        shapes_supported = True
        for name, (_, shape, _, elements) in b_tensors.items():
            a_name = B_NAME.sub(lambda match: match[1] + match[2].replace("_B", "_A"), name, count=1)
            if name.endswith(".bias"):
                a_name = a_name[:-4] + "weight"
                shapes_supported = False
            require(a_name in tensors and elements > 0, "lora_pair_invalid")
            a_shape = tensors[a_name][1]
            if len(shape) == len(a_shape) == 2:
                # Standard linear/embedding factors, or the PEFT ParamWrapper
                # folded expert layout A[E*r,I], B[O,E*r]. Other 2D rank
                # mismatches are invalid, rather than silently reinterpreted.
                effective_rank = shape[1]
                require(a_shape[0] == effective_rank, "lora_pair_invalid")
                require(effective_rank == rank or (".experts." in name
                        and effective_rank > rank and effective_rank % rank == 0),
                        "lora_pair_invalid")
            elif len(shape) == len(a_shape) == 3:
                # Fused expert factors A[E,r,I], B[E,O,r]. Unknown layouts are
                # still scanned for finite B values, but cannot verify an update.
                shapes_supported &= (shape[0] == a_shape[0] and shape[0] > 0
                                     and shape[2] == a_shape[1] == rank)
            else:
                shapes_supported = False
            paired_a.add(a_name)
        require(paired_a == a_names, "lora_pair_invalid")
        finite = nonzero = inspected = standard_nonzero = embedding_nonzero = embedding_tensors = 0
        for name, (dtype, _, offsets, _) in b_tensors.items():
            embedding = B_NAME.search(name)[2] == "lora_embedding_B"
            embedding_tensors += embedding
            width, typecode, exponent_mask, magnitude_mask = DTYPES[dtype]
            handle.seek(data_start + offsets[0])
            remaining = offsets[1] - offsets[0]
            while remaining:
                chunk = handle.read(min(CHUNK, remaining))
                require(len(chunk) == min(CHUNK, remaining), "tensor_read_truncated")
                bits = array.array(typecode)
                require(bits.itemsize == width, "cpu_word_size_unsupported")
                bits.frombytes(chunk)
                if sys.byteorder != "little":
                    bits.byteswap()
                for value in bits:
                    require(value & exponent_mask != exponent_mask, "lora_b_nonfinite")
                    finite += 1
                    changed = bool(value & magnitude_mask)
                    nonzero += changed
                    if embedding:
                        embedding_nonzero += changed
                    else:
                        standard_nonzero += changed
                remaining -= len(chunk)
                inspected += len(chunk)
        return {"tensor_count": len(tensors), "b_tensor_count": len(b_tensors),
                "b_elements": finite, "b_finite_elements": finite,
                "b_nonzero_elements": nonzero, "b_bytes": inspected,
                "standard_b_nonzero_elements": standard_nonzero,
                "embedding_b_nonzero_elements": embedding_nonzero,
                "embedding_b_tensor_count": embedding_tensors,
                "pair_shapes_supported": shapes_supported,
                "model_bytes": size, "b_all_finite": True}


def sha_file(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


@contextmanager
def quiet_sdk(root):
    values = {"WANDB_BASE_URL": "https://api.wandb.ai", "WANDB_CONSOLE": "off",
              "WANDB_SILENT": "true", "WANDB_DISABLE_CODE": "true", "WANDB_DISABLE_GIT": "true",
              "WANDB_ERROR_REPORTING": "false", "WANDB_DIR": str(root),
              "WANDB_CACHE_DIR": str(root / "cache"), "WANDB_DATA_DIR": str(root / "data"),
              "WANDB_CONFIG_DIR": str(root / "config")}
    previous = {key: os.environ.get(key) for key in values}
    disabled = logging.root.manager.disable
    try:
        os.environ.update(values)
        logging.disable(logging.CRITICAL)
        with open(os.devnull, "w", encoding="utf-8") as sink, redirect_stdout(sink), redirect_stderr(sink):
            yield
    finally:
        logging.disable(disabled)
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def sdk_reader(key):
    import wandb  # Import only after the existing project passed the private check.
    return wandb.Api(api_key=key, overrides={"base_url": "https://api.wandb.ai"}, timeout=45)


def private_temp_parent():
    parent = Path(tempfile.gettempdir()).resolve()
    repository = Path(__file__).resolve().parents[2]
    require(not parent.is_relative_to(repository)
            and not any((candidate / ".git").exists() for candidate in (parent, *parent.parents)),
            "temporary_directory_in_repository")
    return parent


def verify_role(reader, api, entity, run_id, role, root):
    result = reader.result(entity, run_id, role)
    output = {"role": role, "status": "pending", "code": "checkpoint_pending",
              "weights_updated": False}
    if result is None:
        return output
    if result.get("status") == "failed":
        return {**output, "status": "failed", "code": "training_failed"}
    reference, inventory = expected_result(result, entity, run_id, role)
    if result.get('training_profile') is not None:
        output.update(training_profile=result['training_profile'], runtime_profile_proof=result['runtime_profile_proof'])
    if 'label_diagnostics' in result:
        output['label_diagnostics'] = validated_label_diagnostics(result['label_diagnostics'], result.get('format'))
    output.update(validated_gemma_receipts(result, role, result.get('training_profile'),
                                           result.get('training_records'), result.get('validation_records')))
    output["artifact"] = reference
    reader.assert_private(entity)
    artifact = api.artifact(reference, type="lora")
    require(artifact.qualified_name == reference and artifact.type == "lora"
            and artifact.state == "COMMITTED" and not artifact.is_link, "artifact_identity_invalid")
    metadata = artifact.metadata
    require(isinstance(metadata, dict) and metadata.get("private") is True
            and all(metadata.get(key) == result[key] for key in
                    ("role", "base_model", "rank", "steps_completed", "adapter_sha256")),
            "artifact_metadata_mismatch")
    require(metadata.get('training_profile') == result.get('training_profile'),
            'artifact_training_profile_mismatch')
    require(('label_diagnostics' in metadata) == ('label_diagnostics' in result)
            and metadata.get('label_diagnostics') == result.get('label_diagnostics'),
            'artifact_label_diagnostics_mismatch')
    require(all((k in metadata) == (k in result) and metadata.get(k) == result.get(k)
                for k in ('formatter_provenance', 'baseline_evaluation')), 'artifact_gemma_receipts_mismatch')
    if result.get('training_profile') is None:
        require('runtime_profile_proof' not in result and 'runtime_profile_proof' not in metadata,
                'artifact_training_profile_mismatch')
    else:
        require(all(metadata.get(k) == result.get(k) for k in ('training_profile', 'runtime_profile_proof',
                    'precision', 'training_method')), 'artifact_training_profile_mismatch')
    entries = artifact.manifest.entries
    require(isinstance(entries, dict), "artifact_manifest_invalid")
    initial = result.get('initial_adapter')
    require(metadata.get('initial_adapter') == initial and metadata.get('resume_script_sha256') == result.get('resume_script_sha256'),
            'artifact_initialization_mismatch')
    if initial is None:
        markers = ('resume_script_sha256', 'initial_adapter_model_sha256', 'optimizer_state_restored')
        require(not any(key in result or key in metadata for key in markers), 'continuation_contract_invalid')
    else:
        require(all(metadata.get(key) == result.get(key) for key in
                    ('initial_adapter_model_sha256', 'optimizer_state_restored')),
                'artifact_initialization_mismatch')
    for row in inventory:
        entry = entries.get(row["name"])
        require(entry is not None and str(entry.path) == row["name"] and entry.ref is None
                and type(entry.size) is int and entry.size == row["bytes"], "artifact_entry_invalid")
    root.mkdir()
    for row in inventory:
        reader.assert_private(entity)
        # get_entry attaches the parent artifact required by the SDK downloader;
        # raw manifest entries alone do not have that binding.
        entry = artifact.get_entry(row["name"])
        require(str(entry.path) == row["name"] and entry.ref is None
                and type(entry.size) is int and entry.size == row["bytes"], "artifact_entry_invalid")
        path = Path(entry.download(root=str(root), skip_cache=True))
        expected = root / row["name"]
        require(path.absolute() == expected.absolute() and not path.is_symlink()
                and path.is_file() and path.resolve() == expected.resolve()
                and path.stat().st_size == row["bytes"], "downloaded_file_invalid")
        require(sha_file(path) == row["sha256"], "downloaded_file_hash_mismatch")
    zero_initializer = config_check(root / FILES[0], role, result["rank"])
    counts = inspect_safetensors(root / FILES[1], result["rank"], LIMITS[role])
    reader.assert_private(entity)
    output.update(counts, config_bytes=inventory[0]["bytes"], zero_initializer=zero_initializer,
                  steps_completed=result["steps_completed"], base_model=result['base_model'], rank=result['rank'],
                  adapter_files=inventory, adapter_inventory_sha256=result['adapter_sha256'])
    if initial is not None:
        require(role == 'solver' and result.get('optimizer_state_restored') is False
                and metadata.get('optimizer_state_restored') is False, 'continuation_contract_invalid')
        import private_resume_adapter as continuation
        require(result.get('resume_script_sha256') == sha_file(Path(continuation.__file__)), 'continuation_helper_pin_mismatch')
        try:
            spec = continuation.validate_spec(initial, get_role_config(role))
            require(spec['entity'] == entity and result.get('initial_adapter_model_sha256') == spec['files'][1]['sha256'],
                    'continuation_source_mismatch')
            def checked_initial_privacy(requested):
                require(requested == entity, 'continuation_source_mismatch')
                reader.assert_private(entity)
                return True
            baseline = root.parent / (role + '-initial')
            continuation.download_initial_adapter(spec, get_role_config(role), baseline, api, checked_initial_privacy)
            evidence = continuation.compare_lora_b(baseline / FILES[1], root / FILES[1], rank=result['rank'])
        except continuation.ResumeError:
            raise VerificationError('continuation_verification_failed') from None
        output.update(evidence, zero_initializer=False, configured_peft_initializer_is_zero=zero_initializer,
                      initial_adapter_artifact=spec['artifact'], optimizer_state_restored=False)
        output.update(status='verified' if evidence['weights_updated'] else 'failed',
                      code='relative_lora_b_change' if evidence['weights_updated'] else 'continued_lora_b_unchanged')
        return output
    if not zero_initializer:
        output.update(status="unverifiable", code="initializer_not_zero_b")
    elif not counts["pair_shapes_supported"]:
        output.update(status="unverifiable", code="lora_pair_shape_unsupported")
    elif counts["standard_b_nonzero_elements"] > 0:
        output.update(status="verified", code="nonzero_b_from_zero_initializer", weights_updated=True)
    elif counts["embedding_b_tensor_count"]:
        # PEFT initializes embedding A to zero and embedding B to normal, even
        # when init_lora_weights=True/'gaussian'. B alone is no evidence there.
        output.update(status="unverifiable", code="embedding_b_initialization_unverifiable")
    else:
        output.update(status="failed", code="lora_b_all_zero")
    return output


def verify(run_id, roles, env=None, reader_factory=PrivateReader, sdk_factory=sdk_reader, *, continuation_inventory=False):
    selected = validate_arguments(run_id, roles)
    require(type(continuation_inventory) is bool and (not continuation_inventory or selected == ['solver']),
            'continuation_inventory_requires_solver')
    key = credentials(os.environ if env is None else env)
    reader = reader_factory(key)
    entity = reader.entity()
    reader.assert_private(entity)  # No SDK import/construction before this gate.
    results = []
    with tempfile.TemporaryDirectory(prefix="hasla-adapter-verify-", dir=private_temp_parent()) as directory:
        root = Path(directory)
        with quiet_sdk(root):
            api = sdk_factory(key)
            for role in selected:
                try:
                    results.append(verify_role(reader, api, entity, run_id, role, root / role))
                except VerificationError as error:
                    results.append({"role": role, "status": "failed", "code": error.code,
                                    "weights_updated": False})
                except Exception:
                    results.append({"role": role, "status": "failed", "code": "private_reader_failed",
                                    "weights_updated": False})
    if not continuation_inventory:
        results = [{key: value for key, value in row.items()
                    if key != 'adapter_files' and not key.endswith('_sha256')} for row in results]
    event = {"event": "private_adapter_verification", "run_id": run_id, "roles": results,
             "all_verified": all(row["status"] == "verified" for row in results),
             "quality_verified": False}
    return event


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise VerificationError("arguments_invalid")


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        parser.add_argument("--run-id", required=True)
        parser.add_argument("--roles", default="chat,solver")
        parser.add_argument('--continuation-inventory', action='store_true',
                            help='explicit solver-only export of file digests for the next pinned continuation')
        args = parser.parse_args(argv)
        event = verify(args.run_id, args.roles, continuation_inventory=args.continuation_inventory)
    except VerificationError as error:
        event = {"event": "private_adapter_verification", "roles": [], "all_verified": False,
                 "quality_verified": False, "code": error.code}
    except Exception:
        event = {"event": "private_adapter_verification", "roles": [], "all_verified": False,
                 "quality_verified": False, "code": "private_reader_failed"}
    print(json.dumps(event, sort_keys=True, separators=(",", ":")))
    if event["all_verified"]:
        return 0
    return 2 if event["roles"] and all(row["status"] == "pending" for row in event["roles"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())

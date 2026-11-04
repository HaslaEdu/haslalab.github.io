"""One public-page CPU probe for the complete PaddleOCR-VL-1.6 pipeline.

This script accepts no document, image, URL, API endpoint, or model override.
Without --run it checks the plan only and imports no OCR/model dependencies.
Run the real probe in a disposable Python 3.11 x64 CPU environment, not on the
space-constrained private source workstation:

  python -m pip install paddlepaddle==3.2.1 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
  python -m pip install 'paddleocr[doc-parser]==3.6.0' 'paddlex==3.6.0'
  python tools/ai/private_ocr_probe.py --run --output /tmp/ocr-probe-summary.json

Official source references (checked 2026-11-04):
https://github.com/PaddlePaddle/PaddleOCR/blob/v3.6.0/paddleocr/_pipelines/paddleocr_vl.py
https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PaddleOCR-VL.en.md
https://github.com/PaddlePaddle/PaddleX/blob/release/3.6/paddlex/configs/pipelines/PaddleOCR-VL-1.6.yaml

Model initialization may download official layout and 0.9B recognition weights.
Nothing is installed by this script. No private material is read or uploaded.
Library stdout/stderr and native child-process output never reach the console.
Only validated counts, fixed statuses, and measured timings leave the worker.
"""
import argparse
from collections import Counter
from collections.abc import Mapping
import contextlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


DEMO_URL = 'https://paddle-model-ecology.bj.bcebos.com/paddlex/imgs/demo_image/paddleocr_vl_demo.png'
PINNED_PACKAGES = {'paddlepaddle': '3.2.1', 'paddleocr': '3.6.0', 'paddlex': '3.6.0'}
PIPELINE_OPTIONS = {'device': 'cpu', 'pipeline_version': 'v1.6', 'vl_rec_backend': 'native',
                    'layout_detection_model_name': 'PP-DocLayoutV3',
                    'vl_rec_model_name': 'PaddleOCR-VL-1.6-0.9B',
                    'use_layout_detection': True, 'use_doc_orientation_classify': False,
                    'use_doc_unwarping': False}
STAGES = frozenset(('configuration', 'dependencies', 'model_initialization', 'prediction', 'result_validation', 'complete'))
ERRORS = frozenset(('configuration_invalid', 'python_version_mismatch', 'dependency_missing',
                    'dependency_version_mismatch', 'gpu_package_installed', 'pipeline_initialization_failed',
                    'prediction_failed', 'unsupported_result', 'no_result', 'no_text', 'layout_stage_missing',
                    'child_timeout', 'child_failed', 'child_invalid_receipt', 'output_write_failed'))
TIMING_KEYS = frozenset(('initialization_seconds', 'prediction_seconds', 'total_seconds'))
INTEGER_KEYS = frozenset(('pages', 'blocks', 'characters'))
BLOCK_TYPES = frozenset(('text', 'formula', 'table', 'other'))


class ProbeFailure(Exception):
    def __init__(self, code):
        if code not in ERRORS:
            raise ValueError('unknown safe OCR probe error')
        self.code = code
        super().__init__(code)


def base_summary(status, stage, error_code=None):
    result = {'event': 'public_ocr_probe', 'probe': 'paddleocr-vl1.6-public-cpu-v1', 'status': status, 'stage': stage,
              'public_sample_only': True, 'private_inputs_read': 0, 'private_uploads': 0,
              'device': 'cpu', 'pipeline_version': 'v1.6', 'full_layout_and_vlm_pipeline': True,
              'layout_model': 'PP-DocLayoutV3', 'recognition_model': 'PaddleOCR-VL-1.6-0.9B',
              'python': '3.11', 'pinned_packages': dict(PINNED_PACKAGES)}
    if error_code is not None:
        result['error_code'] = error_code
    return result


def check_dependencies(version_getter=importlib.metadata.version, python_version=None):
    actual_python = sys.version_info[:2] if python_version is None else python_version
    if tuple(actual_python) != (3, 11):
        raise ProbeFailure('python_version_mismatch')
    try:
        version_getter('paddlepaddle-gpu')
    except importlib.metadata.PackageNotFoundError:
        pass
    else:
        raise ProbeFailure('gpu_package_installed')
    for package, expected in PINNED_PACKAGES.items():
        try:
            actual = version_getter(package)
        except importlib.metadata.PackageNotFoundError:
            raise ProbeFailure('dependency_missing') from None
        if actual != expected:
            raise ProbeFailure('dependency_version_mismatch')


def default_pipeline_factory(**options):
    # Import only inside an explicitly requested, isolated real probe worker.
    from paddleocr import PaddleOCRVL
    return PaddleOCRVL(**options)


def summarize_page(page):
    """Read structured in-memory results without printing or saving any text."""
    if not isinstance(page, Mapping):
        raise ProbeFailure('unsupported_result')
    settings = page.get('model_settings')
    if (not isinstance(settings, Mapping) or settings.get('use_layout_detection') is not True
            or page.get('layout_det_res') is None):
        raise ProbeFailure('layout_stage_missing')
    blocks = page.get('parsing_res_list')
    if not isinstance(blocks, (list, tuple)):
        raise ProbeFailure('unsupported_result')
    kinds, characters = Counter(), 0
    for block in blocks:
        if isinstance(block, Mapping):
            label, content = block.get('block_label'), block.get('block_content')
        else:
            # PaddleX 3.6 returns PaddleOCRVLBlock objects before JSON export.
            label, content = getattr(block, 'label', None), getattr(block, 'content', None)
        if not isinstance(content, str):
            raise ProbeFailure('unsupported_result')
        characters += len(content)
        if label in ('table',):
            kind = 'table'
        elif label in ('formula', 'inline_formula', 'display_formula', 'formula_number'):
            kind = 'formula'
        elif label in ('text', 'content', 'doc_title', 'paragraph_title', 'reference', 'reference_content', 'ocr'):
            kind = 'text'
        else:
            kind = 'other'
        kinds[kind] += 1
    return {'pages': 1, 'blocks': len(blocks), 'characters': characters, 'block_types': dict(kinds),
            'layout_stage_present': True}


def perform_probe(dependency_checker=check_dependencies, pipeline_factory=default_pipeline_factory, clock=time.monotonic):
    started, stage = clock(), 'dependencies'
    try:
        dependency_checker()
        stage = 'model_initialization'
        before_init = clock()
        pipeline = pipeline_factory(**dict(PIPELINE_OPTIONS))
        after_init = clock()
        stage = 'prediction'
        # The only permitted input is the one official public demo image.
        pages = list(pipeline.predict(input=DEMO_URL))
        after_prediction = clock()
        stage = 'result_validation'
        if len(pages) != 1:
            raise ProbeFailure('no_result')
        counts = summarize_page(pages[0])
        if counts['characters'] < 1 or counts['blocks'] < 1:
            raise ProbeFailure('no_text')
        result = base_summary('succeeded', 'complete')
        result.update(counts, initialization_seconds=round(after_init - before_init, 3),
                      prediction_seconds=round(after_prediction - after_init, 3),
                      total_seconds=round(clock() - started, 3))
        return result
    except ProbeFailure as exc:
        return base_summary('failed', stage, exc.code)
    except Exception:
        code = 'pipeline_initialization_failed' if stage == 'model_initialization' else (
            'prediction_failed' if stage == 'prediction' else 'unsupported_result')
        return base_summary('failed', stage, code)


def sanitize_summary(value):
    """Rebuild an allowlisted receipt; never forward arbitrary worker strings."""
    if not isinstance(value, dict):
        raise ProbeFailure('child_invalid_receipt')
    status, stage = value.get('status'), value.get('stage')
    if status not in ('succeeded', 'failed') or stage not in STAGES:
        raise ProbeFailure('child_invalid_receipt')
    code = value.get('error_code')
    if status == 'failed' and code not in ERRORS:
        raise ProbeFailure('child_invalid_receipt')
    if status == 'succeeded' and (stage != 'complete' or code is not None):
        raise ProbeFailure('child_invalid_receipt')
    result = base_summary(status, stage, code)
    if any(value.get(key) != expected for key, expected in result.items()):
        raise ProbeFailure('child_invalid_receipt')
    if status == 'failed':
        return result
    for key in INTEGER_KEYS:
        number = value.get(key)
        if type(number) is not int or not 1 <= number <= 10000000 or (key == 'pages' and number != 1):
            raise ProbeFailure('child_invalid_receipt')
        result[key] = number
    for key in TIMING_KEYS:
        number = value.get(key)
        if type(number) not in (int, float) or not math.isfinite(number) or not 0 <= number <= 86400:
            raise ProbeFailure('child_invalid_receipt')
        result[key] = number
    types = value.get('block_types')
    if (not isinstance(types, dict) or any(k not in BLOCK_TYPES or type(v) is not int or not 0 <= v <= 10000000 for k,v in types.items())
            or sum(types.values()) != result['blocks'] or value.get('layout_stage_present') is not True):
        raise ProbeFailure('child_invalid_receipt')
    result.update(block_types=dict(types), layout_stage_present=True)
    return result


def worker_environment(environment):
    keep = ('PATH', 'HOME', 'USERPROFILE', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'TMPDIR',
            'LD_LIBRARY_PATH', 'LANG', 'LC_ALL', 'HF_HOME', 'PADDLE_PDX_CACHE_HOME')
    result = {key: environment[key] for key in keep if key in environment}
    result.update(CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void', HF_HUB_DISABLE_TELEMETRY='1',
                  DO_NOT_TRACK='1', WANDB_MODE='disabled', PYTHONIOENCODING='utf-8')
    return result


def worker_main(receipt_path, **kwargs):
    # Python logging is suppressed as well as the OS-level DEVNULL parent pipe.
    with open(os.devnull, 'w', encoding='utf-8') as sink:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            result = sanitize_summary(perform_probe(**kwargs))
            try:
                with Path(receipt_path).open('x', encoding='utf-8', newline='\n') as handle:
                    handle.write(json.dumps(result, ensure_ascii=True) + '\n')
            except Exception:
                return 1
    return 0 if result['status'] == 'succeeded' else 1


def run_isolated(timeout_seconds=1500, runner=subprocess.run):
    with tempfile.TemporaryDirectory(prefix='hasla-public-ocr-probe-') as temporary:
        receipt = Path(temporary) / 'summary.json'
        command = [sys.executable, str(Path(__file__).resolve()), '--_worker', str(receipt)]
        try:
            completed = runner(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               stdin=subprocess.DEVNULL, timeout=timeout_seconds, check=False,
                               env=worker_environment(os.environ))
        except subprocess.TimeoutExpired:
            return base_summary('failed', 'prediction', 'child_timeout')
        except Exception:
            return base_summary('failed', 'configuration', 'child_failed')
        try:
            if not receipt.is_file() or receipt.stat().st_size > 16384:
                raise ProbeFailure('child_invalid_receipt')
            result = sanitize_summary(json.loads(receipt.read_text(encoding='utf-8')))
            if completed.returncode != (0 if result['status'] == 'succeeded' else 1):
                raise ProbeFailure('child_invalid_receipt')
            return result
        except Exception:
            return base_summary('failed', 'result_validation', 'child_invalid_receipt')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Public fixed-page CPU full-pipeline probe; no private inputs.', exit_on_error=False)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--output')
    parser.add_argument('--_worker', help=argparse.SUPPRESS)
    try:
        args, unknown = parser.parse_known_args(argv)
        if unknown or (args._worker and (args.run or args.output)):
            raise ProbeFailure('configuration_invalid')
    except (argparse.ArgumentError, ProbeFailure):
        print(json.dumps(base_summary('failed', 'configuration', 'configuration_invalid'), ensure_ascii=True))
        return 2
    if args._worker:
        return worker_main(args._worker)
    if args.run:
        result = run_isolated()
    else:
        result = base_summary('prepared', 'configuration')
        result.update(model_downloads_started=False, inference_started=False, allowed_sample_pages=1)
    if args.output:
        try:
            with Path(args.output).open('x', encoding='utf-8', newline='\n') as handle:
                handle.write(json.dumps(result, ensure_ascii=True) + '\n')
        except Exception:
            result = base_summary('failed', 'configuration', 'output_write_failed')
    print(json.dumps(result, ensure_ascii=True), flush=True)
    return 0 if result['status'] in ('succeeded', 'prepared') else 1


if __name__ == '__main__':
    raise SystemExit(main())

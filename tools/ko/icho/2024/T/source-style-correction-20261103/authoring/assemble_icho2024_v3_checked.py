"""Join actual reviewed final62 proofs and retain the executed assembler binding.

Invoke this wrapper through the shared pdf_memory_gate, after final READY exists.
The immutable production freeze and assembler are never edited by this wrapper.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import subprocess
import sys

BASE = Path(__file__).resolve().parents[1]
O = BASE / 'style-corrections/icho2024-20261103'
R = O / 'revisions/final62-v3'
F = O / 'final/2024-v3'
ASM = BASE / 'engine/assemble_natural.py'
ASM_SHA = '098286bc8fa1a3ac5805006b95484c5dd279a6fac4e1fc5c109e86e7f976954f'
FREEZE = 'fd600ecbd54dc70bf25033bf9eebf4a065ac3256175ecfdf3ff70954361625e4'
SOURCE = '959174ab5ddc8be71c251c8fe95a12c810ba730edbcbbef3b771197e32929a4a'
HELPER = R / 'working/style-engine/native_proof.py'
DEPENDENCIES = [BASE / 'engine/source_path_resolver.py',
                BASE / 'engine/prose_decoration_publication.py',
                BASE / 'engine/icho2024_prose_decoration_publication.py',
                Path('D:/CodexBuilds/Hasla-plancks-ortvay-icho-20261102/engine/native_proof.py'),
                Path('D:/CodexBuilds/Hasla-plancks-ortvay-icho-20261102/engine/pdf_latex_text_ops.py')]


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text('utf8'))


def pin(path, digest=None):
    path = Path(path).resolve()
    actual = sha(path)
    assert digest is None or actual == digest, ('Stale assembly input', path)
    return dict(path=str(path), sha256=actual, bytes=path.stat().st_size)


def checked(value):
    actual = pin(value['path'], value['sha256'])
    assert actual['bytes'] == value['bytes']
    return Path(actual['path'])


def argv(python, output_dir):
    return [str(Path(python).resolve()), '-B', '-X', 'utf8', str(ASM),
            'icho', 'IChO', '2024', '62', '--proof-dir', str(F),
            '--proof-helper', str(HELPER), '--output-dir', str(Path(output_dir).resolve()),
            '--visual-review', str(F / 'visual-review-all62-v3.json')]


def validate_receipt(receipt, qa, pdf_pin, ready_pin, bridge_pin, check_pin=checked):
    """Reject stale joins and successful joins made by a different assembler."""
    assert receipt['schema'] == 'icho2024-final62-v3-actual-assembly-receipt-v1'
    assert receipt['status'] == 'ACTUAL_ASSEMBLER_COMPLETED_AND_OUTPUTS_REHASHED'
    assert receipt['competition'] == 'icho' and receipt['year'] == 2024 and receipt['pages'] == 62
    assert receipt['subprocess_returncode'] == 0
    assert receipt['assembler']['sha256'] == ASM_SHA
    assert Path(receipt['assembler']['path']).resolve() == ASM
    assert receipt['assembler_sha256_after'] == ASM_SHA
    assert receipt['code_input_freeze']['sha256'] == FREEZE
    assert receipt['ready'] == ready_pin and receipt['visual_bridge'] == bridge_pin
    assert receipt['output_pdf'] == pdf_pin
    assert receipt['output_qa']['sha256'] == sha(Path(pdf_pin['path']).with_suffix('.qa.json'))
    assert receipt['argv'] == argv(receipt['python'], Path(pdf_pin['path']).parent)
    assert Path(receipt['cwd']).resolve() == BASE
    assert Path(receipt['wrapper']['path']).resolve() == Path(__file__).resolve()
    assert receipt['wrapper']['sha256'] == sha(__file__)
    assert qa['schema'] == 'natural-source-native-joined-v1' and qa['status'] == 'READY'
    assert qa['sha256'] == pdf_pin['sha256'] and qa['bytes'] == pdf_pin['bytes']
    assert qa['source_sha256'] == SOURCE and qa['pages'] == 62
    assert qa['visual_review_required'] is False and qa['all_pages_visually_reviewed'] is True
    assert len(qa['page_audits']) == len(receipt['page_inputs']) == 62
    input_by_path = {}
    for item in receipt['input_files']:
        check_pin(item)
        key = str(Path(item['path']).resolve()).casefold()
        assert key not in input_by_path, ('Duplicate assembly input path', key)
        input_by_path[key] = item
    required = [receipt[k] for k in ['assembler', 'wrapper', 'code_input_freeze', 'ready', 'visual_bridge', 'proof_helper']]
    required += receipt['assembly_dependencies']
    for n, (row, page) in enumerate(zip(receipt['page_inputs'], qa['page_audits']), 1):
        assert row['page'] == page['page'] == n
        assert row['proof']['sha256'] == page['proof_sha256']
        assert row['layout']['sha256'] == page['qa_sha256']
        assert Path(row['proof']['path']).resolve() == F / f'page{n:02}.pdf'
        assert Path(row['layout']['path']).resolve() == F / f'page{n:02}.layout.json'
        assert page['final_vs_reviewed_proof_changed_pixels'] == 0
        assert page['final_vs_reviewed_proof_all_glyph_geometry_identical'] is True
        required += [row['proof'], row['layout']]
    for item in required:
        assert input_by_path[str(Path(item['path']).resolve()).casefold()] == item
    assert Path(receipt['code_input_freeze']['path']).resolve() == R / 'FINAL-CODE-INPUT-FREEZE.json'
    freeze = read(receipt['code_input_freeze']['path'])
    for field, count in [('current_program_and_input_sha256', 249),
                         ('preserved_input_sha256', 204), ('preserved_prior_output_sha256', 206)]:
        assert len(freeze[field]) == count
        for path, digest in freeze[field].items():
            assert input_by_path[str(Path(path).resolve()).casefold()]['sha256'] == digest
    assert Path(receipt['proof_helper']['path']).resolve() == HELPER
    assert receipt['proof_helper']['sha256'] == freeze['current_program_and_input_sha256'][str(HELPER)]
    assert len(receipt['assembly_dependencies']) == len(DEPENDENCIES)
    assert {Path(p['path']).resolve() for p in receipt['assembly_dependencies']} == set(DEPENDENCIES)
    for key in ['output_pdf', 'output_qa', 'attempt']:
        check_pin(receipt[key])
    attempt = read(receipt['attempt']['path'])
    assert attempt['schema'] == 'icho2024-final62-v3-assembly-attempt-v1'
    for key in ['started_utc', 'argv', 'cwd', 'wrapper', 'assembler',
                'code_input_freeze', 'ready', 'visual_bridge', 'input_files']:
        assert attempt[key] == receipt[key], ('Execution attempt/receipt mismatch', key)
    return True


def assemble(output_dir):
    for name in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS']:
        os.environ[name] = '1'
    output_dir = Path(output_dir).resolve()
    assert output_dir.is_relative_to(O / 'root-assembled'), 'Use a new private IChO24 root assembly directory'
    target = output_dir / 'IChO_2024_T_KO.pdf'
    receipt_path = target.with_suffix('.assembly-receipt.json')
    attempt_path = target.with_suffix('.assembly-attempt.json')
    assert all(not p.exists() for p in [target, target.with_suffix('.qa.json'), receipt_path, attempt_path])
    ready_pin = pin(F / 'READY.json')
    ready = read(ready_pin['path'])
    assert ready['status'] == 'YEAR_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_ROOT_ASSEMBLY_REVIEW'
    assert ready['pages'] == 62 and ready['year'] == 2024 and ready['source']['sha256'] == SOURCE
    freeze_pin = pin(R / 'FINAL-CODE-INPUT-FREEZE.json', FREEZE)
    freeze = read(freeze_pin['path'])
    assert ready['code_input_freeze']['sha256'] == FREEZE
    bridge_pin = pin(F / 'visual-review-all62-v3.json', ready['normalized_visual_bridge']['sha256'])
    assert Path(ready['normalized_visual_bridge']['path']).resolve() == Path(bridge_pin['path'])
    bridge = read(bridge_pin['path'])
    assert bridge['source_sha256'] == SOURCE and len(bridge['pages']) == 62
    assert len(ready['page_results']) == 62
    input_files = {}

    def add(path, digest=None):
        item = pin(path, digest)
        key = str(Path(item['path']).resolve()).casefold()
        assert key not in input_files or input_files[key] == item
        input_files[key] = item
        return item

    wrapper_pin = add(__file__)
    assembler_pin = add(ASM, ASM_SHA)
    for item in [ready_pin, freeze_pin, bridge_pin]:
        add(item['path'], item['sha256'])
    for field, count in [('current_program_and_input_sha256', 249),
                         ('preserved_input_sha256', 204), ('preserved_prior_output_sha256', 206)]:
        assert len(freeze[field]) == count
        for path, digest in freeze[field].items():
            add(path, digest)
    dependencies = [add(path) for path in DEPENDENCIES]
    add(ready['source']['path'], SOURCE)
    page_inputs = []
    helper_pin = add(HELPER, freeze['current_program_and_input_sha256'][str(HELPER)])
    for n, (row, review) in enumerate(zip(ready['page_results'], bridge['pages']), 1):
        assert row['page'] == review['page'] == n and review['reviewed'] is True
        proof = add(F / f'page{n:02}.pdf', row['proof']['sha256'])
        layout = add(F / f'page{n:02}.layout.json', row['layout']['sha256'])
        assert Path(row['proof']['path']).resolve() == Path(proof['path'])
        assert Path(row['layout']['path']).resolve() == Path(layout['path'])
        q = read(layout['path'])
        assert q['page'] == n and q['output_sha256'] == review['proof_sha256'] == proof['sha256']
        assert layout['sha256'] == review['layout_sha256']
        assert q['native_proof_helper_sha256'] == helper_pin['sha256']
        page_inputs.append(dict(page=n, proof=proof, layout=layout))
    command = argv(sys.executable, output_dir)
    start = datetime.now(timezone.utc).isoformat()
    attempt = dict(schema='icho2024-final62-v3-assembly-attempt-v1', started_utc=start,
                   argv=command, cwd=str(BASE), wrapper=wrapper_pin, assembler=assembler_pin,
                   code_input_freeze=freeze_pin, ready=ready_pin, visual_bridge=bridge_pin,
                   input_files=list(input_files.values()))
    output_dir.mkdir(parents=True, exist_ok=True)
    with attempt_path.open('x', encoding='utf8') as stream:
        stream.write(json.dumps(attempt, ensure_ascii=False, indent=2) + '\n')
    subprocess.run(command, cwd=BASE, check=True)
    for item in input_files.values():
        checked(item)
    pdf_pin = pin(target)
    qa_pin = pin(target.with_suffix('.qa.json'))
    report = dict(schema='icho2024-final62-v3-actual-assembly-receipt-v1',
                  status='ACTUAL_ASSEMBLER_COMPLETED_AND_OUTPUTS_REHASHED',
                  competition='icho', year=2024, pages=62, started_utc=start,
                  completed_utc=datetime.now(timezone.utc).isoformat(),
                  python=str(Path(sys.executable).resolve()), argv=command, cwd=str(BASE),
                  subprocess_returncode=0, wrapper=wrapper_pin, assembler=assembler_pin,
                  assembler_sha256_after=sha(ASM), code_input_freeze=freeze_pin,
                  ready=ready_pin, visual_bridge=bridge_pin, proof_helper=helper_pin,
                  assembly_dependencies=dependencies, page_inputs=page_inputs,
                  input_files=list(input_files.values()), output_pdf=pdf_pin, output_qa=qa_pin,
                  attempt=pin(attempt_path))
    validate_receipt(report, read(qa_pin['path']), pdf_pin, ready_pin, bridge_pin)
    with receipt_path.open('x', encoding='utf8') as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(status='ROOT_ACTUAL_ASSEMBLY_RECEIPT_WRITTEN_NOT_STAGED',
                          receipt=pin(receipt_path), output_pdf=pdf_pin)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    assemble(args.output_dir)

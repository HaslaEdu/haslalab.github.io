"""Resumable frozen final62 driver; no input edits, staging or publication."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import argparse
import shutil
import time
sys.dont_write_bytecode = True
R = Path(__file__).resolve().parent
O = R.parents[1]
F = O / 'final/2024-v3'
GATE = Path('D:/CodexBuilds/Hasla-publish-20261031/tools/pdf_memory_gate.py')


def sha(p):
    with Path(p).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read(p):
    return json.loads(Path(p).read_text('utf8'))


freeze = read(R / 'FINAL-CODE-INPUT-FREEZE.json')
parser = argparse.ArgumentParser()
parser.add_argument('--root-go-freeze-sha', required=True)
args = parser.parse_args()
assert args.root_go_freeze_sha == sha(R / 'FINAL-CODE-INPUT-FREEZE.json')
assert freeze['status'] == 'FROZEN_FINAL62_V3_PREPARED_PENDING_ROOT_GENERATION_GO'
# This explicit argument is supplied only after root approves this exact immutable freeze.
pins = freeze['current_program_and_input_sha256']


def verify_current():
    for path, expected in {**pins, **freeze['preserved_input_sha256']}.items():
        assert sha(path) == expected, path


protected = []
for name in ['protection-pins.json', 'supplementary-path-pins.json', 'visual-reference-pins.json']:
    protected.extend(read(O / name)['original_files'])
assert len(protected) == 910


def verify_originals():
    for item in protected:
        assert sha(item['source']) == sha(item['copy']) == item['sha256'], item['source']
    for item in read(O / 'protection-pins.json')['working_copies']:
        assert sha(item['path']) == sha(item['frozen']) == item['sha256'], item['path']
    for path, expected in freeze['preserved_prior_output_sha256'].items():
        assert sha(path) == expected, path


verify_current()
verify_originals()
completed = []
progress = F / 'driver-progress.json'
if progress.exists():
    old = read(progress)
    assert old['code_input_freeze_sha256'] == sha(R / 'FINAL-CODE-INPUT-FREEZE.json')
    completed = old['complete']
    for n in completed:
        for path, expected in old['completed_page_artifact_sha256'][str(n)].items():
            assert sha(path) == expected, path
artifacts = read(progress)['completed_page_artifact_sha256'] if progress.exists() else {}


def stop_at_page_boundary():
    if not (F / 'STOP-AFTER-CURRENT-PAGE').exists():
        return False
    verify_current()
    verify_originals()
    report = dict(status='SAFE_STOP_AT_COMPLETE_PAGE_BOUNDARY_NO_READY',
        complete=completed, current_page_worker_and_gate_finished=True,
        all910_originals_and_copies_unchanged=True, all171_initial_working_copies_unchanged=True,
        frozen_runtime_and_inputs_unchanged=True,
        code_input_freeze_sha256=sha(R / 'FINAL-CODE-INPUT-FREEZE.json'),
        completed_page_artifact_sha256=artifacts, program_sha256=sha(__file__))
    out = F / 'SAFE-STOP-CHECKPOINT.json'
    out.write_text(json.dumps(report, indent=2) + '\n', 'utf8')
    print('SAFE-STOP', completed, out, sha(out), flush=True)
    return True


for n in range(1, 63):
    if stop_at_page_boundary():
        sys.exit(0)
    if n in completed:
        continue
    verify_current()
    assert shutil.disk_usage(F).free >= 256 * 1024 * 1024, 'D drive guard 256MiB'
    print('FINAL-START', n, flush=True)
    subprocess.run([sys.executable, '-X', 'utf8', str(GATE), '--', sys.executable,
        '-X', 'utf8', str(R / 'run_page.py'), str(n)], cwd=R, check=True)
    verify_current()
    q = read(F / f'page{n:02}.layout.json')
    for name in ['source', 'plan', 'effective_plan', 'overrides', 'composer']:
        path = q[name if name == 'source' else name + '_path']
        assert sha(path) == q[name + '_sha256'], (n, name)
    assert q['output_sha256'] == sha(F / f'page{n:02}.pdf')
    files = sorted(p for p in F.glob(f'page{n:02}*') if p.is_file())
    artifacts[str(n)] = {str(p): sha(p) for p in files}
    completed.append(n)
    data = dict(status='FROZEN_FINAL62_IN_PROGRESS_PENDING_MANUAL_REVIEW',
        code_input_freeze_sha256=sha(R / 'FINAL-CODE-INPUT-FREEZE.json'), complete=completed,
        remaining=[v for v in range(1, 63) if v not in completed],
        completed_page_artifact_sha256=artifacts, protected_original_files=910,
        program_sha256=sha(__file__))
    progress.write_text(json.dumps(data, indent=2) + '\n', 'utf8')
    print('FINAL-PAGE-PASS', n, flush=True)
    if stop_at_page_boundary():
        sys.exit(0)
    if n < 62:
        print('OUTSIDE-GATE-YIELD-SECONDS', 8, flush=True)
        time.sleep(8)
verify_current()
verify_originals()
out = F / 'ALL62-MACHINE-QA-PASS.json'
assert not out.exists()
out.write_text(json.dumps(dict(status='ALL62_MACHINE_QA_PASS_PENDING_ALL62_MANUAL_PNG_REVIEW',
    pages=completed, all910_originals_and_frozen_copies_unchanged=True,
    all171_initial_working_copies_unchanged=True, all_frozen_runtime_and_inputs_unchanged=True,
    code_input_freeze_sha256=sha(R / 'FINAL-CODE-INPUT-FREEZE.json'),
    final_page_artifact_sha256=artifacts, program_sha256=sha(__file__)), indent=2) + '\n', 'utf8')
print('FINAL62-MACHINE-PASS', out, sha(out), flush=True)

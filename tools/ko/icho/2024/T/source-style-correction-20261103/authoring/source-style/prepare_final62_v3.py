"""Prepare an immutable final input set; does not render or launch page workers."""
from pathlib import Path
import ast
import hashlib
import json
import shutil
import sys
sys.dont_write_bytecode = True
O = Path(__file__).resolve().parent
R2 = O / 'revisions/final62-v2'
R7 = O / 'revisions/native-d-p7-v7'
R = O / 'revisions/final62-v3'
F = O / 'final/2024-v3'


def sha(p):
    with Path(p).open('rb') as h:
        return hashlib.file_digest(h, 'sha256').hexdigest()


def read(p):
    return json.loads(Path(p).read_text('utf8'))


def write(p, value):
    assert not p.exists(), p
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', 'utf8')


assert not R.exists() and not F.exists()
old = read(R2 / 'FINAL-CODE-INPUT-FREEZE.json')
assert sha(R2 / 'FINAL-CODE-INPUT-FREEZE.json') == 'ec90c4dd31ca726e6fced818b9245ca0dc147aac9be5a1bd452e9b554989b987'
peer = O.parents[1] / 'engine/publication-transition/icho2024-p57-external-v2-peer-review.json'
assert sha(peer) == '6b451aa08bf7b472f56babe3f9fdf2c3a66654857573ce168a65fd43db4295d4'
assert sha(O / 'audit_p57_actual_native_atom_v2.py') == 'f3129c8888eedf9a9d51c82c5533e6f4bcb50a74d84c8cc44dff3f23da5b3207'
legacy = {}
for p, key in [(R2 / 'FINAL-CODE-INPUT-FREEZE.json', 'current_program_and_input_sha256'),
               (R7 / 'PROBE-CODE-INPUT-FREEZE.json', 'program_and_input_sha256'),
               (O / 'experiments/v7/ACTUAL-NATIVE-AUDIT-FREEZE-V2.json', None)]:
    obj = read(p)
    if key is None:
        candidates = [v for k, v in obj.items() if isinstance(v, dict) and 'sha256' in k]
        assert len(candidates) == 1, obj.keys()
        table = candidates[0]
    else:
        table = obj[key]
    legacy[str(p)] = sha(p)
    for path, expected in table.items():
        assert path not in legacy or legacy[path] == expected
        legacy[path] = expected
for path, expected in legacy.items():
    assert sha(path) == expected, path

R.mkdir(parents=True)
F.mkdir(parents=True)
shutil.copytree(R2 / 'working', R / 'working', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
for n in [7, 57]:
    for stem, suffix in [('plans', 'plan'), ('overrides', 'overrides')]:
        rel = Path('working') / stem / f'page{n:02}.{suffix}.json'
        shutil.copyfile(R7 / rel, R / rel)
for rel in ['approved-translation-manifest.json', 'p39-reviewed-whole-inline-wedge-atom-v2.json',
            'working/style-engine/prose_style_rules_icho2024.py']:
    shutil.copyfile(R7 / rel, R / rel)
guard = R / 'working/authoring/icho2024_style_experiment_guard.py'
text = guard.read_text('utf8')
assert text.count('final/2024-v2') == 1
guard.write_text(text.replace('final/2024-v2', 'final/2024-v3'), 'utf8')
assert sha(R / 'approved-translation-manifest.json') == 'bc06cca28d8b2f3ed93b437a5c3ed12f37cc8dd40d096f174314e5e2dffa68b2'
assert len(read(R / 'approved-translation-manifest.json')['edits']) == 54

# Use accepted actual probes; unchanged early pages also retain their exact visual trace.
refs = {n: 'experiments/v4' for n in [5, 13, 19, 21, 27, 28, 37, 39, 43, 45, 46, 55, 58]}
refs.update({1: 'experiments/v6', 7: 'experiments/v7', 57: 'experiments/v7', 15: 'experiments/v5'})
refs.update({n: 'final/2024-v2' for n in [2, 3, 4, 6, 8, 9, 10]})
write(R / 'selected-prototype-references.json', {str(k): v for k, v in sorted(refs.items())})
worker = (R2 / 'run_page.py').read_text('utf8').replace('final/2024-v2', 'final/2024-v3')
worker = worker.replace('import sys\n', 'import sys\nimport subprocess\n', 1)
start = worker.index('representatives = ')
end = worker.index('    previous = ', start)
worker = worker[:start] + "references = json.loads((R / 'selected-prototype-references.json').read_text('utf8'))\nif str(n) in references:\n    previous_folder = references[str(n)]\n" + worker[end:]
needle = "if n == 39:\n    atom.run(F)\n"
assert worker.count(needle) == 1
worker = worker.replace(needle, needle + "if n == 57:\n    subprocess.run([sys.executable, '-X', 'utf8', str(O / 'audit_p57_actual_native_atom_v2.py'), str(target)], cwd=R, check=True)\n")
(R / 'run_page.py').write_text(worker, 'utf8')

# subprocess.run inherits stdout: the outer process always drains naturally and never suspends.
driver = (R2 / 'run_all_pages.py').read_text('utf8').replace('final/2024-v2', 'final/2024-v3')
driver = driver.replace('import sys\n', 'import sys\nimport argparse\nimport time\n', 1)
driver = driver.replace("assert freeze['root_final62_GO'] is True\nassert freeze['status'] == 'FROZEN_ALL62_SINGLE_PRODUCER_AND_INPUTS'",
    "parser = argparse.ArgumentParser()\nparser.add_argument('--root-go-freeze-sha', required=True)\nargs = parser.parse_args()\nassert args.root_go_freeze_sha == sha(R / 'FINAL-CODE-INPUT-FREEZE.json')\nassert freeze['status'] == 'FROZEN_FINAL62_V3_PREPARED_PENDING_ROOT_GENERATION_GO'\n# This explicit argument is supplied only after root approves this exact immutable freeze.")
driver = driver.replace("    for path, expected in pins.items():", "    for path, expected in {**pins, **freeze['preserved_input_sha256']}.items():")
needle = "    for item in read(O / 'protection-pins.json')['working_copies']:\n        assert sha(item['path']) == sha(item['frozen']) == item['sha256'], item['path']\n"
assert driver.count(needle) == 1
driver = driver.replace(needle, needle + "    for path, expected in freeze['preserved_prior_output_sha256'].items():\n        assert sha(path) == expected, path\n")
needle = "    if stop_at_page_boundary():\n        sys.exit(0)\nverify_current()"
assert driver.count(needle) == 1
driver = driver.replace(needle, "    if stop_at_page_boundary():\n        sys.exit(0)\n    if n < 62:\n        print('OUTSIDE-GATE-YIELD-SECONDS', 8, flush=True)\n        time.sleep(8)\nverify_current()")
driver = driver.replace("    print('FINAL-START', n, flush=True)", "    assert shutil.disk_usage(F).free >= 256 * 1024 * 1024, 'D drive guard 256MiB'\n    print('FINAL-START', n, flush=True)")
driver = driver.replace('import argparse\n', 'import argparse\nimport shutil\n', 1)
(R / 'run_all_pages.py').write_text(driver, 'utf8')

changes = []
for p in sorted((R / 'working').rglob('*')):
    if p.is_file():
        previous = R2 / p.relative_to(R)
        if sha(p) != sha(previous):
            changes.append(dict(path=str(p.relative_to(R)), before=sha(previous), after=sha(p)))
assert {v['path'].replace('\\', '/') for v in changes} == {
    'working/plans/page07.plan.json', 'working/plans/page57.plan.json',
    'working/overrides/page07.overrides.json', 'working/overrides/page57.overrides.json',
    'working/style-engine/prose_style_rules_icho2024.py',
    'working/authoring/icho2024_style_experiment_guard.py'}
for name, expected in [('working/authoring/natural_plan_compose_icho2024_style.py', old['composer_sha256']),
                       ('working/style-engine/latex_native_motion.py', old['native_motion_engine_sha256'])]:
    assert sha(R / name) == expected
for p in R.rglob('*.py'):
    ast.parse(p.read_text('utf8'), filename=str(p))
write(R / 'PREPARATION-CHANGES.json', dict(status='PREPARATION_ONLY_NO_PAGE_WORKERS_STARTED',
    working_files_differing_from_v2=changes, exact_approved_slot_count=54,
    only_two_added_approved_slots=['p7:b6:l1:s0-0:c0-33', 'p57:b11:l3:s0-0'],
    source_native_p57_d_restored_using_existing_skip_emptyextra_char_range=True,
    producer_composer_and_motion_byte_identical=True, all_python_files_AST_parse=True,
    single_page_gate_stdout_inherited_no_suspension=True, outside_gate_yield_seconds=8,
    special_p57_auditor_mandatory_on_actual_new_final_proof=True, root_final62_generation_GO_pending=True))

pins = {str(p): sha(p) for p in sorted(R.rglob('*')) if p.is_file()}
# Retain all original evidence pins in addition to the new set, including old frozen code.
extra = [O / 'audit_p57_actual_native_atom_v2.py', O / 'test_p57_actual_native_atom_v2.py', peer,
    O / 'readonly-hold-review-20261103/p57-native-d-existing-interface-design.json',
    O / 'experiments/v7/PROBE-V7-HANDOFF.json', O / 'experiments/v7/PROTECTED-INPUTS-POST-PROBE-REHASH.json',
    O / 'experiments/v7/page57.actual-native-atom-v2.json',
    O / 'experiments/v7/p57-actual-native-atom-v2-negative-regressions.json',
    O / 'root-review-v7/root-page07-oxidation-review.json',
    O / 'root-review-v7/root-page57-native-d-visual-review.json',
    Path(__file__)]
for n, folder in refs.items():
    extra.extend(O / folder / f'page{n:02}{suffix}' for suffix in ['.pdf', '.png', '.layout.json'])
for p in extra:
    pins[str(p)] = sha(p)
previous_outputs = {str(p): sha(p) for folder in ['final/2024-v1', 'final/2024-v2']
                    for p in sorted((O / folder).glob('page*')) if p.is_file()}
freeze = {k: v for k, v in old.items() if k not in ['current_program_and_input_sha256', 'root_GO_scope', 'allowed_differences_from_v1_runtime']}
freeze.update(schema='icho2024-final62-single-producer-code-input-freeze-v3',
    status='FROZEN_FINAL62_V3_PREPARED_PENDING_ROOT_GENERATION_GO', root_final62_GO=False,
    exact_approved_slot_edits=54, total_approved_clause_cases=29,
    approved_clause_changed_pages=sorted(set(old['approved_clause_changed_pages'] + [57])),
    approved_source_clause_manifest_sha256=sha(R / 'approved-translation-manifest.json'),
    p7_actual_oxidation_verb_restored=True, p57_original_d_and_five_subscripts_one_native_atom=True,
    p57_external_actual_auditor=dict(path=str(O / 'audit_p57_actual_native_atom_v2.py'), sha256=sha(O / 'audit_p57_actual_native_atom_v2.py')),
    p57_original_source_profile=dict(path=str(extra[3]), sha256=sha(extra[3])),
    peer_review=dict(path=str(peer), sha256=sha(peer)),
    current_program_and_input_sha256=pins, preserved_input_sha256=legacy,
    preserved_prior_output_sha256=previous_outputs, private_final_output=str(F),
    all_previous_v1_v2_and_v7_outputs_retained=True,
    prepared_execution_command=[sys.executable, '-X', 'utf8', str(R / 'run_all_pages.py'), '--root-go-freeze-sha', '<exact SHA after root GO>'])
write(R / 'FINAL-CODE-INPUT-FREEZE.json', freeze)
print(json.dumps(dict(status='FINAL62_V3_PREPARED_NO_GENERATION', freeze=str(R / 'FINAL-CODE-INPUT-FREEZE.json'),
    sha256=sha(R / 'FINAL-CODE-INPUT-FREEZE.json'), current_pins=len(pins), preserved_pins=len(legacy),
    prior_output_pins=len(previous_outputs), working_changed_files=len(changes), pages_started=0), indent=2), flush=True)

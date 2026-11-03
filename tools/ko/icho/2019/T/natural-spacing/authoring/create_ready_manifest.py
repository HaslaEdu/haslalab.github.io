"""Create a source-bound handoff only after all final R2 page audits pass."""
from pathlib import Path
import datetime, hashlib, json, sys

B = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(B))
import icho2019_write_guard as g

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_text('utf8'))

def pin(path):
    path = Path(path).resolve()
    assert path.is_file(), path
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)

freeze_path = B / 'final-code-freeze-r2.json'
freeze = read(freeze_path)
assert sha(freeze_path) == '81156ebe66c0872dd0301e5a22d0b72f8e29dd8ba56ed3eae60b87d3422ba49a'
amend_path = B / 'final-r2-page53-semantics-amendment.json'
amend = read(amend_path)
assert sha(amend_path) == '95f51bb3527ea0f83202c4c071e01b884a09369c615b7de5cd628896b3083f39'
columns_path = B / 'final-r2-source-checkbox-columns-amendment.json'
columns = read(columns_path)
assert sha(columns_path) == '22eebd85186fae16a0c31ad8d3b23e8e67d5f015e2efd7eddbf730a0694faee7'
column_pins = {Path(e['changed_input']).resolve(): e['after_sha256'] for e in columns['pages']}
second_path = B / 'final-r2-page51-second-answer-row-amendment.json'
second = read(second_path)
steps_path = B / 'final-r2-page54-starting-compound-amendment.json'
steps = read(steps_path)
assert sha(second_path) == 'cd50b0b21e8fba85c47bc79923453aab684d379676830d61c2ae98aa7e45a9f2'
assert sha(steps_path) == 'fc26e9089730d02d6c03c7f052b194c6c5366548267ead8a2faba220250b8475'
column_pins[Path(second['changed_input']).resolve()] = second['after_sha256']
column_pins[Path(steps['changed_input']).resolve()] = steps['after_sha256']
for entry in freeze['files']:
    path = Path(entry['path'])
    expected = amend['after_sha256'] if path.resolve() == Path(amend['changed_input']).resolve() else entry['sha256']
    if path.resolve() in column_pins:
        expected = column_pins[path.resolve()]
    assert sha(path) == expected, path
g.assert_protected_2024()
assert sha(g.SOURCE) == g.SOURCE_SHA == freeze['source_sha256']

verification_path = B / 'final-60-page-proof-verification.json'
verification = read(verification_path)
visual_path = B / 'final-r2-visual-review.json'
visual = read(visual_path)
fresh_path = B / 'final-r2-fresh-visual-review.json'
fresh = read(fresh_path)
assert verification['passed'] and verification['verified_pages'] == 60 and not verification['failures']
assert verification['freeze_sha256'] == visual['freeze_sha256'] == sha(freeze_path)
assert verification['approved_page53_amendment_sha256'] == sha(amend_path)
assert verification['source_checkbox_columns_amendment_sha256'] == sha(columns_path)
assert verification['page51_second_answer_row_amendment_sha256'] == sha(second_path)
assert verification['page54_starting_compound_amendment_sha256'] == sha(steps_path)
actual_changes = [dict(path=e['path'], before_sha256=e['sha256'], after_sha256=sha(e['path'])) for e in freeze['files'] if sha(e['path']) != e['sha256']]
assert actual_changes == verification['actual_changed_R2_inputs']
assert sorted(Path(e['path']).name for e in actual_changes) == [f'page{n:02}.overrides.json' for n in [13, 45, 46, 51, 53, 54]]
assert visual['passed'] and visual['reviewed_pages'] == 60 and not visual['remaining_pages']
assert sorted(row['page'] for row in fresh['pages']) == [13, 27, 28, 45, 46, 51, 52, 53, 54, 57, 58, 60]
assert all(row['passed'] for row in fresh['pages'])
for row in verification['rows']:
    for artifact in row['artifacts']:
        assert sha(artifact['path']) == artifact['sha256'], artifact['path']
for row in visual['pages']:
    n = row['page']
    for suffix, key in [('.pdf', 'pdf_sha256'), ('.png', 'png_sha256'), ('.layout.json', 'layout_sha256'), ('.render.json', 'render_sha256')]:
        assert sha(g.PROOFS / f'page{n:02}{suffix}') == row[key]
    assert sha(B / f'page{n:02}.diagnostic.json') == row['diagnostic_sha256']

semantic = read(B / 'source-emphasis-meaning-review.json')
assert semantic['all_source_target_mappings_manually_read'] and semantic['reviewed_source_paths'] == len(semantic['rows']) == 143
negative = read(B / 'final-r2-code-review/actual-source-opacity-guard-regressions.json')
assert negative['all_passed'] and negative['source_original_pdf_unchanged']
assert len(negative['tests']) == 4 and all(t['passed'] for t in negative['tests'])
assert negative['positive_pdf_sha256'] == sha(g.PROOFS / 'page28.pdf')
assert negative['auditor_sha256'] == sha(B / 'verify_native_vectors_icho2019.py')
font_roles = read(B / 'final-r2-code-review/source-font-style-role-audit.json')
assert font_roles['passed'] and not font_roles['errors']
assert read(g.PROOFS / 'page31.answer-field-audit.json')['passed']
assert read(g.PROOFS / 'page45.answer-columns-audit.json')['passed']
assert read(B / 'final-r2-code-review/all-source-checkbox-coordinate-audit.json')['passed']

evidence = [
    freeze_path, amend_path, columns_path, second_path, steps_path, verification_path, visual_path, fresh_path,
    B / 'source-emphasis-meaning-review.json',
    B / 'source-prose-transform-guard-regressions.json',
    B / 'final-r2-code-review/actual-source-opacity-guard-regressions.json',
    B / 'final-r2-code-review/non-underlined-emphasis-pages01-02-review.json',
    B / 'final-r2-code-review/source-font-style-role-audit.json',
    B / 'final-r2-code-review/all-source-checkbox-coordinate-audit.json',
    B / 'final-r2-page45-answer-columns-amendment.json',
    B / 'final-r2-code-review/eight-graphic-trial-review.json',
    B / 'final-r2-code-review/source-fragment-review-reference.json',
    B / 'italic-direction-repro/italic-direction-actual-ink-measurement.json',
    g.PROOFS / 'page31.answer-field-audit.json',
    g.PROOFS / 'page45.answer-columns-audit.json',
    B / 'graphic-source-font-role-inference.json',
    B / 'final-root-visual-review-pages03-08.json',
    B / 'final-peer-visual-review-pages29-35.json',
    B / 'final-r2-code-review/pre-R2-human-visual-review.json',
    B / 'final-r2-code-review/fair-schedule-journal.json',
    Path(__file__),
]
report = dict(
    status='READY_FOR_ROOT_ASSEMBLY', year=2019, pages=60,
    created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    source=pin(g.SOURCE), proof_root=str(g.PROOFS),
    intro_pages=list(range(1, 8)), body_pages=list(range(8, 61)), contains_solutions=False,
    same_frozen_production_Python_programs=69,
    unchanged_R2_inputs_except_exact_six_page_amendments=191,
    actual_changed_R2_inputs=actual_changes,
    semantic_underline_mappings=143,
    outlined_source_path_modes=verification['outlined_path_mode_counts'],
    exact_mixed_source_paths=verification['exact_mixed_paths'],
    page_artifacts=verification['rows'], evidence=[pin(p) for p in evidence],
    scope='Proof handoff only. Root owns assembly, staging and publishing. No other year is started by this child. Authoring/proofs remain in their original D-drive locations; no OneDrive files are created.',
    font_evidence='Selectable prose and native scientific notation use directly inspected original source metadata and independently measured emitted glyph/font/point/baseline/outline evidence. Source outlined/raster-only language labels have no original font metadata: their face/size inference is explicitly recorded separately; no exact-source-font claim is made for those labels.',
    visual_evidence='All original source pages/clauses were actually read. Eight changed graphic pages, page53 and all four corrected checkbox pages were freshly read after final generation (12 pages in total). Other final pages are rebound only to byte-identical previously actually read PNGs, with new current PDF/layout/render/actual-QA hashes. Independent root/peer reviews remain explicitly identified.',
    root_publication_requirement='Use this exact proof/manifest set and final code lineage. Rerun final publisher assembly validation and Python/CJS semantic decoration contracts. Parent publication worktree and global assembler are outside this child handoff.'
)
target = B / 'READY-for-root-assembly-r2.json'
target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf8')
print(json.dumps(dict(status=report['status'], path=str(target), sha256=sha(target), pages=60)))

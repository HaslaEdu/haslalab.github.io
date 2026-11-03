"""QA-only bridge of earlier real reads; final compositor and inputs stay frozen."""
from pathlib import Path
import hashlib
import json
import sys
sys.dont_write_bytecode = True
import qa3_common as g
O = g.O
R = O / 'revisions/final62-v3'
F = O / 'final/2024-v3'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_text('utf8'))


p = F / 'manual-review-checkpoints.json'
out = read(p) if p.exists() else dict(schema='icho2024-final62-source-target-PNG-review-v3',
    status='FINAL62_IN_PROGRESS_ACTUAL_READ_AND_EXACT_REBIND_ONLY', reviewer='/root/ortvay_current', reviewed=[])
complete = g.complete_pages()
refs = read(R / 'selected-prototype-references.json')
existing = {v['page'] for v in out['reviewed']}
done = []
for n in complete:
    if n in existing or str(n) not in refs:
        continue
    previous = O / refs[str(n)]
    before = read(previous / f'page{n:02}.render.json')
    current = read(F / f'page{n:02}.render.json')
    ep = F / f'page{n:02}.prototype-equivalence.json'
    eq = read(ep)
    assert eq['passed'] and eq['actual_1_5x_RGB_pixels_identical'] and eq['all_visible_actual_glyph_geometry_identical']
    assert current['image_sha256'] == before['image_sha256'] == sha(F / f'page{n:02}.png') == sha(previous / f'page{n:02}.png')
    assert current['source_image_sha256'] == before['source_image_sha256'] == sha(F / f'page{n:02}-source.png') == sha(previous / f'page{n:02}-source.png')
    assert current['proof_sha256'] == sha(F / f'page{n:02}.pdf') and current['layout_sha256'] == sha(F / f'page{n:02}.layout.json')
    assert eq['previous_selected_proof_sha256'] == sha(previous / f'page{n:02}.pdf')
    if n == 1:
        evidence = previous / 'P1-FOUR-CLAUSE-HANDOFF.json'
        prior = read(evidence)
        assert prior['source_and_candidate_actual_original_resolution_PNG_read']
        note, status = prior['manual_observation'], prior['status']
    elif n in [7, 57]:
        evidence = previous / 'PROBE-V7-HANDOFF.json'
        prior = next(v for v in read(evidence)['page_results'] if v['page'] == n)
        assert prior['actual_original_resolution_source_and_target_PNG_read'] and prior['producer_and_generic_machine_QA_passed']
        note, status = prior['manual_observation'], 'PASS'
    else:
        evidence = previous / 'manual-review-checkpoints.json'
        prior = next(v for v in read(evidence)['reviewed'] if v['page'] == n)
        assert prior['status'] in ['PASS', 'PASS_FOR_CHANGED_SCOPE']
        note, status = prior['observation'], prior['status']
    row = dict(page=n, status='PASS', reviewer='/root/ortvay_current',
        review_mode='PRIOR_ACTUAL_ORIGINAL_RESOLUTION_READ_REBOUND_ONLY_AFTER_IDENTICAL_IMAGE_BYTES_AND_ACTUAL_GLYPH_GEOMETRY',
        actual_original_resolution_source_and_candidate_images_read=True, current_file_reopened_for_this_rebinding=False,
        proof_sha256=current['proof_sha256'], layout_sha256=current['layout_sha256'],
        composer_sha256=current['composer_sha256'], source_sha256=current['source_sha256'],
        image_sha256=current['image_sha256'], source_image_sha256=current['source_image_sha256'],
        code_input_freeze_sha256=sha(R / 'FINAL-CODE-INPUT-FREEZE.json'),
        qa_amendment_code_input_freeze_sha256=sha(g.C / 'CODE-INPUT-FREEZE.json'),
        previous_actual_review_evidence=dict(path=str(evidence), sha256=sha(evidence), status=status),
        previous_proof=dict(path=str(previous / f'page{n:02}.pdf'), sha256=sha(previous / f'page{n:02}.pdf')),
        current_actual_pixel_and_glyph_equivalence=dict(path=str(ep), sha256=sha(ep)),
        observation=note, review_rebinding_program_sha256=sha(__file__))
    if n == 57:
        native = F / 'page57.actual-native-atom-v2.json'
        report = read(native)
        assert report['status'] == 'PASS' and report['proof_sha256'] == current['proof_sha256'] and report['layout_sha256'] == current['layout_sha256']
        row['new_final_actual_native_atom_audit'] = dict(path=str(native), sha256=sha(native))
    out['reviewed'].append(row)
    done.append(n)
out['reviewed'].sort(key=lambda v: v['page'])
if done or not p.exists():
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', 'utf8')
print('EXACT-REBIND', done, 'reviewed', len(out['reviewed']), flush=True)

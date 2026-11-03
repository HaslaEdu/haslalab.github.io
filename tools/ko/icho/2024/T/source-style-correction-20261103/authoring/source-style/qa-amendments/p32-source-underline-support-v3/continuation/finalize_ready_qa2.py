"""Read-only final artifact checks, then normalized visual bridge and READY sidecars.

No PDF parsing, rendering, composition, assembly, staging, or publication.
"""
from pathlib import Path
import hashlib
import json
import sys
sys.dont_write_bytecode = True
import argparse
import qa3_common as g
O = g.O
R = O / 'revisions/final62-v3'
F = O / 'final/2024-v3'
FREEZE = 'fd600ecbd54dc70bf25033bf9eebf4a065ac3256175ecfdf3ff70954361625e4'
SOURCE = '959174ab5ddc8be71c251c8fe95a12c810ba730edbcbbef3b771197e32929a4a'
APP = 'bc06cca28d8b2f3ed93b437a5c3ed12f37cc8dd40d096f174314e5e2dffa68b2'


def sha(p):
    with Path(p).open('rb') as h:
        return hashlib.file_digest(h, 'sha256').hexdigest()


def read(p):
    return json.loads(Path(p).read_text('utf8'))


def item(p):
    return dict(path=str(p), sha256=sha(p))


def write(p, value):
    assert not p.exists(), p
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', 'utf8')


parser=argparse.ArgumentParser()
parser.add_argument('--root-go-sha',required=True)
args=parser.parse_args()
g.verify_go(args.root_go_sha)
assert sha(R / 'FINAL-CODE-INPUT-FREEZE.json') == FREEZE
freeze = read(R / 'FINAL-CODE-INPUT-FREEZE.json')
assert sha(R / 'ROOT-GO-FINAL62.json') == '6c9d7e2a43a2615a69a0da3b4f62bed0c8522a4413fdf9b8c1c3471819ae3051'
assert read(F / 'driver-progress.json')['complete'] == list(range(1, 32))
assert g.complete_pages() == list(range(1, 63))
machine = read(F / 'ALL62-MACHINE-QA-PASS.json')
assert machine['pages'] == list(range(1, 63)) and machine['code_input_freeze_sha256'] == FREEZE
for table in ['current_program_and_input_sha256', 'preserved_input_sha256', 'preserved_prior_output_sha256']:
    for path, expected in freeze[table].items():
        assert sha(path) == expected, path
for table in machine['final_page_artifact_sha256'].values():
    for path, expected in table.items():
        assert sha(path) == expected, path
manual_path = F / 'manual-review-checkpoints.json'
manual = read(manual_path)
assert sorted(v['page'] for v in manual['reviewed']) == list(range(1, 63))
assert len(manual['reviewed']) == 62
reviews = {v['page']: v for v in manual['reviewed']}
rows, visual, glyphs, underlines, italics, edits, pairs = [], [], 0, 0, 0, 0, 0
for n in range(1, 63):
    stem = F / f'page{n:02}'
    pdf, lp, png = stem.with_suffix('.pdf'), stem.with_suffix('.layout.json'), stem.with_suffix('.png')
    render = read(stem.with_suffix('.render.json'))
    q = read(lp)
    semantic_path, style_path, pixel_path = [stem.with_suffix(s) for s in ['.semantic-style-audit.json', '.underline-style-audit.json', '.pixel-KK-audit.json']]
    semantic, style, pixel = read(semantic_path), read(style_path), read(pixel_path)
    review = reviews[n]
    assert review['status'] == 'PASS' and review['actual_original_resolution_source_and_candidate_images_read'] is True
    for evidence in review.get('additional_actual_read_evidence', []):
        assert sha(evidence['path']) == evidence['sha256']
    if review.get('review_recording_program_path'):
        assert sha(review['review_recording_program_path']) == review['review_recording_program_sha256']
    assert review['code_input_freeze_sha256'] == FREEZE
    assert q['page'] == n and q['source_sha256'] == SOURCE
    assert q['composer_sha256'] == freeze['composer_sha256'] and q['native_motion_engine_sha256'] == freeze['native_motion_engine_sha256']
    assert q['approved_source_clause_manifest_sha256'] == APP
    assert sha(pdf) == q['output_sha256'] == render['proof_sha256'] == review['proof_sha256']
    assert sha(lp) == render['layout_sha256'] == review['layout_sha256']
    assert sha(png) == render['image_sha256'] == review['image_sha256']
    source_png = F / f'page{n:02}-source.png'
    assert sha(source_png) == render['source_image_sha256'] == review['source_image_sha256']
    assert render['source_sha256'] == review['source_sha256'] == SOURCE
    for obj in [semantic, style, pixel]:
        assert obj['page'] == n and obj['passed'] is True and obj['proof_sha256'] == sha(pdf)
    assert semantic['approved_source_clause_manifest_sha256'] == APP
    assert style['underline_coverage_tolerance_pt'] == .001 and style['source_native_vector_tolerance_pt'] == 1e-7
    assert pixel['changed_pixels_outside_named_source_rows'] == 0 and pixel['kk']['passed'] and pixel['kk']['failures'] == []
    if n == 32:
        assert sha(pixel_path) == g.POSITIVE and pixel['layout_sha256'] == sha(lp)
        assert pixel['program_sha256'] == g.AUDITOR and pixel['source_stroke_program_sha256'] == '8756e7deb5c4dd9e6d470d9fc562f58398996bc4a34371ebcd759b4da9be9477'
        assert sha(pdf) == '295d4bcd98d367c2cc0a140ba5d824fdf3345407500b03a127e04d1d2b159219' and sha(lp) == '1b5cdf8f40e8774344d024a5ccdbde997137be37a0f18027000619cfc2971eea'
    assert pixel['kk']['tested_close_row_pairs'] == len(pixel['kk']['pairs'])
    assert all(v['contact_pixels_2x'] == 0 for v in pixel['kk']['pairs'])
    assert q['new_korean_intrusion_on_native_ink_pixels'] == 0
    assert q['original_font_sizes_and_baselines_identical'] and q['source_font_programs_preserved'] and q['original_image_encoded_bytes_and_filters_preserved']
    actual = q['new_korean_glyph_and_geometry_audit']
    assert actual['passed'] and actual['missing_or_notdef_glyphs'] == [] and actual['geometry_errors'] == [] and actual['position_tolerance_pt'] == .001
    assert q['final_native_geometry']['missing'] == [] and q['final_native_geometry']['extra'] == 0
    vectors = q['actual_native_vector_coordinate_audit']
    assert vectors['coordinate_errors'] == [] and vectors['max_coordinate_tolerance_pt'] == 1e-7
    row = dict(page=n, proof=item(pdf), layout=item(lp), png=item(png), source_png=item(source_png),
        pixel_audit=item(pixel_path), semantic_audit=item(semantic_path), underline_style_audit=item(style_path),
        render_metadata=item(stem.with_suffix('.render.json')), actual_PNG_review=review)
    if n == 39:
        p = F / 'page39.native-atom-appearance-audit.json'
        a = read(p)
        assert a['passed'] and a['proof_sha256'] == sha(pdf) and a['layout_sha256'] == sha(lp)
        assert a['actual_grayscale_pixels_different'] == 0 and a['comparison_scale'] == 4
        assert a['source_profile_sha256'] == '60f010c33b97f27a5347f187c141dddc46e740bb3023cb98ba66f43413f5153e'
        row['inline_native_atom_audit'] = item(p)
    if n == 57:
        p = F / 'page57.actual-native-atom-v2.json'
        a = read(p)
        assert a['status'] == 'PASS' and a['page'] == 57 and a['source_sha256'] == SOURCE
        assert a['proof_sha256'] == sha(pdf) and a['layout_sha256'] == sha(lp)
        assert a['program_sha256'] == 'f3129c8888eedf9a9d51c82c5533e6f4bcb50a74d84c8cc44dff3f23da5b3207'
        assert a['source_profile_sha256'] == 'f3efb347598737eb8505f8f529e044e15ee4307a8bdf5caaced7e88f2b09ff3d'
        assert a['actual_original_native_glyphs'] == 6 and a['actual_common_dx_spread_pt'] <= .001
        assert a['actual_visible_new_Korean_d_count_at_orbital_row'] == a['measured_source_ordinary_space_glyphs_between_d_and_subscript'] == a['measured_actual_ordinary_space_glyphs_between_d_and_subscript'] == 0
        row['native_prefix_audit'] = item(p)
    rows.append(row)
    visual.append(dict(page=n, reviewed=True, proof_sha256=sha(pdf), layout_sha256=sha(lp),
        effective_plan_sha256=q['effective_plan_sha256'], composer_sha256=q['composer_sha256'],
        render_image=str(png), render_image_sha256=sha(png), source_render_image=str(source_png),
        source_render_image_sha256=sha(source_png), review_mode=review['review_mode'], reviewer=review['reviewer']))
    glyphs += style['all_authored_glyphs_verified']
    underlines += len(style['underline_rows'])
    italics += semantic['new_Korean_italic_placements']
    edits += semantic['exact_approved_text_edits']
    pairs += pixel['kk']['tested_close_row_pairs']
assert (underlines, italics, edits) == (68, 9, 54)
protected = []
for name in ['protection-pins.json', 'supplementary-path-pins.json', 'visual-reference-pins.json']:
    protected.extend(read(O / name)['original_files'])
assert len(protected) == 910
for v in protected:
    assert sha(v['source']) == sha(v['copy']) == v['sha256'], v['source']
working = read(O / 'protection-pins.json')['working_copies']
assert len(working) == 171
for v in working:
    assert sha(v['path']) == sha(v['frozen']) == v['sha256'], v['path']
g.verify_code()
g.verify_originals()
manual['status'] = 'ALL62_ACTUAL_SOURCE_TARGET_PNG_REVIEWS_PASS'
manual_path.write_text(json.dumps(manual, ensure_ascii=False, indent=2) + '\n', 'utf8')
bridge = F / 'visual-review-all62-v3.json'
write(bridge, dict(status='PASS', source_sha256=SOURCE, pages=visual, qa_amendment=g.lineage(),
    manual_review=item(manual_path), program_sha256=sha(__file__), code_input_freeze=item(R / 'FINAL-CODE-INPUT-FREEZE.json')))
ready = dict(status='YEAR_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_ROOT_ASSEMBLY_REVIEW', year=2024, pages=62,
    source=item(O / 'frozen/source/IChO_2024_T_EN.pdf'), old_published_pdf_sha256='78d869b01f48bd1e050f2b8697900c757f4987331b1895026173e4b3258fe024',
    code_input_freeze=item(R / 'FINAL-CODE-INPUT-FREEZE.json'), root_generation_GO=item(R / 'ROOT-GO-FINAL62.json'),
    program_path=str(Path(__file__).resolve()), program_sha256=sha(__file__), qa_amendment=g.lineage(), composer_sha256=freeze['composer_sha256'], native_motion_engine_sha256=freeze['native_motion_engine_sha256'],
    approved_translation_manifest=item(R / 'approved-translation-manifest.json'), source_semantic_mapping=item(O / 'semantic-underline-mapping-68-v2.json'),
    source_bound_underlines=underlines, new_Korean_only_italic_runs=italics, approved_text_slots=edits,
    actual_authored_glyphs=glyphs, tested_actual_KK_pairs=pairs, all62_actual_visual_reviews=item(manual_path),
    normalized_visual_bridge=item(bridge), all62_machine_QA=item(F / 'ALL62-MACHINE-QA-PASS.json'),
    original910_and_initial171_and_all_frozen_inputs_and_prior_outputs_rehashed_unchanged=True,
    glyph_tolerance_pt=.001, native_vector_tolerance_pt=1e-7, no_tolerance_relaxation=True,
    page_results=rows, scope='Private final proof set only; assembly, staging, and publication remain root-owned.')
write(F / 'READY.json', ready)
print('ALL62-READY', F / 'READY.json', sha(F / 'READY.json'), flush=True)

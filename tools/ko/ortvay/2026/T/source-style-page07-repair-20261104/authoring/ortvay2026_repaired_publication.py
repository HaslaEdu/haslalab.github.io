"""Draft, fail-closed publication support for the separate 2026 page-7 repair.

No renderer or producer is invoked. Original publication modules stay frozen.
The production GO must be reviewed and pinned before this module can stage.
"""
from pathlib import Path
from copy import deepcopy
import json

from build_ortvay_r4_publication_config import (
    BASE, R4, Pins, FIXED, READY_STATUS, fixed_inputs, same_pin, contains_reference, sha, read,
)
from build_ortvay_r4_ctm_publication_config import (
    PROFILE_FIELDS, ARTIFACTS, runtime_snapshot, json_aliases,
)
from ortvay_source_style_publication import (
    PUBLISHED, validate_ctm_profile, validate_ctm_page_lineage, validate_page, effective_plan_binding,
)
import ortvay_full_ctm_publication as full_ctm

APPROVED_REPAIR_GO_SHA256 = '345cb2fe09b90a178c9f87176cfc7fc3307a957d8c45087359f746e01e89a730'
NUMERIC_SHA = 'b552b2f0cc95c1f0e8aae8bfdfc34fddae4037ce88703eca33f7fe61c914b24c'
FAILED_PDF_SHA = 'fccac3dc419fcb1bf1ee6aa3ed42d38ea1565e9416ddba3e7f7ec3e457cb169f'
FAILED_LAYOUT_SHA = '98454b83b490e8f2e42dc01b08d66b6d8788706643a9e5c31bb902e2e5783e79'
REPAIR = R4 / 'page-repairs/2026-page07-postprocess-v1-20261104'
MIXED = R4 / 'mixed-year-bridges/2026-postprocess-v1-20261104'
PRODUCTION = R4 / 'production-continuation/full-ctm-v1-20261103'
READY_SCHEMA = 'ortvay-source-style-width-correction-ready-v3-mixed-ctm-page-repair'
CONFIG_SCHEMA = 'ortvay2026-repaired-source-style-publication-config-v1'
MANIFEST_SCHEMA = 'ortvay2026-source-style-page-repair-publication-v1'
PROGRAM_NAMES = {'postprocess_page07.py', 'audit_page07_repair.py', 'continue_and_bridge_2026.py'}
AMENDMENT_KEYS = {'numeric_spec', 'repair_freeze', 'repair_GO', 'copy_receipt', 'positive', 'negatives',
                  'postprocessor', 'auditor', 'bridge'}
COPY_SUFFIX = {'proof': '.pdf', 'layout': '.layout.json', 'effective_plan': '.effective-plan.json'}
PDF_NEGATIVES = {'old_failed_P1_no_shift', 'dx_3.1875_two_x_contact', 'wrong_upper_row_moved',
                 'only_three_of_four_glyphs_shifted', 'other_KO_glyph_moved',
                 'original_native_glyph_changed', 'font_program_or_W_changed'}
BINDING_NEGATIVES = {'wrong_or_stale_repair_root_GO', 'wrong_runtime_program_sha',
                     'wrong_copy_origin_or_copy_SHA', 'wrong_page_origin_mapping'}


def real_document(doc):
    """A design template can never become evidence by filling just a hash."""
    assert isinstance(doc, dict)
    assert not str(doc.get('status', '')).startswith('DESIGN_TEMPLATE')
    assert not doc.get('unresolved_proposal')
    assert not any(key.endswith('_example_only') and value for key, value in doc.items())


def numeric_spec(pins, pin):
    assert pin['sha256'] == NUMERIC_SHA
    value, checked = pins.document(pin['path'], NUMERIC_SHA, evidence=True)
    assert value['status'] == 'ROOT_APPROVED_EXACT_NUMERIC_REPAIR_SPEC_NOT_PRODUCTION_GO'
    assert value['year'] == 2026 and value['page'] == 7 and value['dx'] == 3.3125
    assert value['selected_slot_id'] == 'p7:b5:l6:s0-0' and value['selected_text'] == '논하라.'
    assert value['selected_baseline'] == 421.5059509277344 and value['source_size_pt'] == 11.9552001953125
    assert value['angle'] == 0 and value['fixed_scales'] == [2, 4, 8]
    assert value['fixed_KO_threshold'] == 220 and value['fixed_native_threshold'] == 180
    assert value['production_repair_authorized'] is False
    pins.references(value, evidence=True)
    return value, checked


def check_original_runtime(pins, pin, year, code):
    return runtime_snapshot(pins, pin, year, code)


def validate_repaired_body(previous, body, spec, proof_sha256, profile):
    """Only the reviewed logical x delta and explicit new lineage may differ."""
    expected = deepcopy(previous)
    rows = [p for p in expected['placements'] if abs(p['baseline'] - 421.5059509277344) < .001]
    assert rows == [spec['old_logical_placement']]
    row = rows[0]
    for field in ('point', 'draw_point'):
        if field in row: row[field][0] += 3.3125
    lines = [v for v in expected['line_reports'] if abs(v['baseline'] - 421.5059509277344) < .001]
    assert len(lines) == 1 and all(t['kind'] == 'prose' for t in lines[0]['tokens'])
    lines[0]['left'] += 3.3125; lines[0]['right'] += 3.3125
    for token in lines[0]['tokens']: token['new_x'] += 3.3125
    expected['output_sha256'] = proof_sha256
    actual = deepcopy(body); extra = actual.pop('r4_page07_exact_row_postprocess')
    assert actual == expected, 'Other base body fields changed during the row repair'
    assert extra['schema'] == 'ortvay-page07-exact-row-postprocess-v1'
    assert extra['slot_id'] == 'p7:b5:l6:s0-0'
    assert extra['baseline'] == 421.5059509277344 and extra['point_size'] == 11.9552001953125
    assert extra['dx'] == 3.3125 and extra['selected_stream_xrefs'] == [317, 318, 319, 320]
    assert extra['original_composer_is_base_provenance'] is True
    assert extra['inherited_QA_claims_require_fresh_independent_revalidation'] is True
    for key in ('numeric_spec', 'repair_code_input_freeze', 'root_GO', 'base_failed_proof', 'base_failed_layout'):
        same_pin(extra[key], profile[key])
    same_pin(extra['repair_runtime_snapshot'], profile['repair_runtime_snapshot'])
    postprocessor = next(p for p in profile['additional_runtime_files'] if Path(p['path']).name == 'postprocess_page07.py')
    same_pin(extra['postprocessor'], postprocessor)
    assert spec['source_column'][0] <= row['point'][0]
    assert row['point'][0] + row['advance'] <= spec['source_column'][1]
    return extra


def validate_repair_profile(pins, profile, binding):
    assert_production_go_available()
    assert profile['schema'] == 'ortvay-one-page-postprocess-profile-v1'
    assert profile['year'] == 2026 and profile['page'] == 7
    spec, spec_pin = numeric_spec(pins, profile['numeric_spec'])
    for key, expected, path in (
        ('base_failed_proof', FAILED_PDF_SHA, R4 / '2026/proofs/ortvay/2026/page07.pdf'),
        ('base_failed_layout', FAILED_LAYOUT_SHA, R4 / '2026/proofs/ortvay/2026/page07.layout.json'),
        ('failed_metadata', '1e4619352ef7c57505cb0c72b4173ed0ede971434b3d8148236ba235fea83e06',
         PRODUCTION / 'pages/2026/page07/FAILED.json'),
        ('base_failed_runtime_snapshot', '7f8d0cd7f032cb633f082ea9e2b7eeae2bf7bc58ae72954243cc2a05d5ab117e',
         PRODUCTION / 'pages/2026/page07/production-runtime-snapshot.json'),
        ('base_original_build_snapshot', '98a4bfcf985e35346dd32e5c1389975e070a686b722b5b81d41175f193437efa',
         R4 / 'experiments/ctm-production-runtime-v1/2026/page07/build/runtime-snapshot.json'),
    ):
        assert profile[key]['sha256'] == expected
        assert Path(profile[key]['path']).resolve() == path
        pins.checked(profile[key])
        if path.suffix == '.json': pins.document(path, expected, evidence=True)
    freeze, freeze_pin = pins.document(profile['repair_code_input_freeze']['path'],
                                      profile['repair_code_input_freeze']['sha256'], evidence=True)
    real_document(freeze)
    assert Path(freeze_pin['path']) == REPAIR / 'REPAIR-CODE-INPUT-FROZEN.json'
    assert freeze['schema'] == 'ortvay-2026-page07-repair-code-input-freeze-v1'
    assert freeze['status'] == 'PAGE07_REPAIR_CODE_INPUT_FROZEN_FOR_ROOT_REVIEW'
    assert len(freeze['base_runtime_programs']) == 46
    assert {Path(p).resolve(): s for p, s in freeze['base_runtime_programs'].items()} == binding['runtime_programs']
    same_pin(freeze['numeric_spec'], spec_pin)
    assert Path(freeze['permitted_output_directory']).resolve() == REPAIR / 'page07'
    assert Path(freeze['mixed_bridge_directory']).resolve() == MIXED
    operation = freeze['allowed_operation']
    assert operation == dict(year=2026, page=7, slot_id='p7:b5:l6:s0-0', text='논하라.', baseline=421.5059509277344,
        point_size=11.9552001953125, dx=3.3125, selected_original_stream_xrefs=[317, 318, 319, 320],
        only_four_original_KO_Tm_e_operands_may_change=True,
        all_other_failed_P1_actual_glyphs_including_spaces_and_effective_objects_exact=True)
    code = {Path(p['path']).resolve(): p['sha256'] for p in freeze['additional_runtime_files']}
    assert len(code) == 3 and set(code) == {REPAIR / name for name in PROGRAM_NAMES}
    assert {Path(p['path']).resolve(): p['sha256'] for p in profile['additional_runtime_files']} == code
    for path, digest in code.items(): pins.add(path, digest)
    for name, value in binding['profile'].items(): same_pin(freeze['base_profile'][name], value)
    pins.references(freeze, evidence=True)
    ledger, _ = pins.document(freeze['preserved_input_ledger']['path'],
                              freeze['preserved_input_ledger']['sha256'], evidence=True)
    assert ledger['production_authorized'] is False
    assert ledger['preserved_inputs']
    for value in ledger['preserved_inputs']: pins.checked(value)
    go, go_pin = pins.document(profile['root_GO']['path'], APPROVED_REPAIR_GO_SHA256, evidence=True)
    assert profile['root_GO']['sha256'] == APPROVED_REPAIR_GO_SHA256
    assert Path(go_pin['path']) == REPAIR / 'ROOT-GO.json'
    assert go['status'] == 'ROOT_GO_2026_PAGE07_EXACT_ROW_POSTPROCESS'
    assert go['production_repair_authorized'] is True
    assert go['existing_source_or_runtime_programs_may_change'] is False
    assert go['original_proofs_or_global_lifecycle_may_change'] is False
    assert go['year'] == 2026 and go['page'] == 7
    same_pin(go['numeric_spec'], spec_pin); same_pin(go['repair_code_input_freeze'], freeze_pin)
    assert Path(go['permitted_output_directory']).resolve() == REPAIR / 'page07'
    base_own, _ = pins.document(profile['base_failed_runtime_snapshot']['path'],
                                profile['base_failed_runtime_snapshot']['sha256'], evidence=True)
    assert {Path(p).resolve(): v['sha256'] for p, v in base_own['files'].items()} == binding['additional_programs']
    for path, value in base_own['files'].items():
        pins.add(path, value['sha256']); pins.add(value['retained_copy'], value['sha256'])
    check_original_runtime(pins, profile['base_original_build_snapshot'], 2026, binding['original_code'])
    runtime, runtime_pin = pins.document(profile['repair_runtime_snapshot']['path'],
                                         profile['repair_runtime_snapshot']['sha256'], evidence=True)
    assert runtime['schema'] == 'ortvay-page07-additional-runtime-snapshot-v1'
    assert runtime['additional_runtime_count'] == 3 and runtime['base_original_runtime_count'] == 46
    assert runtime['base46_is_provenance_not_a_claim_of_old_only_execution'] is True
    assert {Path(p).resolve(): v['sha256'] for p, v in runtime['files'].items()} == code
    for key, value in [('numeric_spec', spec_pin), ('repair_code_input_freeze', freeze_pin), ('root_GO', go_pin)]:
        same_pin(runtime[key], value)
    for path, value in runtime['files'].items():
        pins.add(path, value['sha256']); pins.add(value['retained_copy'], value['sha256'])
    return dict(spec=spec, spec_pin=spec_pin, freeze=freeze, freeze_pin=freeze_pin, go=go,
                go_pin=go_pin, additional_programs=code, runtime=runtime, runtime_pin=runtime_pin)


def validate_positive(pins, value, body, body_pin, origin, profile, repair, previous_page):
    real_document(value)
    assert value['schema'] == 'ortvay-2026-page07-additive-repair-audit-v1'
    assert value['status'] == 'PAGE07_ADDITIVE_REPAIR_ALL_STRICT_CHECKS_PASS'
    assert value['passed'] is True and value['year'] == 2026 and value['page'] == 7
    assert value['proof_sha256'] == value['target']['sha256'] == origin['proof']['sha256'] == body['output_sha256']
    same_pin(value['proof'], origin['proof']); same_pin(value['layout'], body_pin)
    for key in ('numeric_spec', 'repair_code_input_freeze', 'root_GO', 'base_failed_proof',
                'base_failed_layout', 'base_failed_runtime_snapshot', 'base_original_build_snapshot', 'repair_runtime_snapshot'):
        same_pin(value[key], profile[key])
    auditor = next(p for p in profile['additional_runtime_files'] if Path(p['path']).name == 'audit_page07_repair.py')
    same_pin(value['auditor_program'], auditor)
    previous = read(pins.checked(profile['base_failed_layout'])['path'])
    validate_repaired_body(previous, body, repair['spec'], origin['proof']['sha256'], profile)
    effective, effective_pin = pins.document(origin['effective_plan']['path'], origin['effective_plan']['sha256'])
    full_ctm.validate(value, body, 2026, body_pin['sha256'],
                      effective_plan_binding(effective_pin['path'], effective_pin['sha256'], effective))
    vector = value['actual_native_vector_coordinate_audit']
    assert vector == body['actual_native_vector_coordinate_audit']
    assert vector['coordinate_errors'] == [] and 0 < vector['max_coordinate_tolerance_pt'] <= 1e-7
    validate_native_replay(pins, value['native_vector_readonly_replay'], origin['proof'], body_pin, vector)
    objects = value['decoded_object_and_stream_preservation']
    for key in ('passed', 'all_other_effective_objects_exact', 'all_other_raw_and_decoded_streams_exact',
                'font_programs_and_encoded_images_exact', 'extra_structural_xref_objects_only', 'original_PDF_prefix_exact'):
        assert objects[key] is True
    assert objects['selected_stream_count'] == 4
    assert [s['xref'] for s in objects['selected_streams']] == [317, 318, 319, 320]
    for stream in objects['selected_streams']:
        assert stream['exact_decimal_Tm_e_delta'] == '3.3125' and stream['all_other_decoded_bytes_identical'] is True
        assert stream['before_sha256'] != stream['after_sha256']
    assert objects['unchanged_effective_objects'] > 0 and objects['unchanged_streams'] > 0
    delta = value['P1_failed_exact_delta_comparison']
    assert delta['passed'] is True
    same_pin(delta['reference_proof'], profile['base_failed_proof'])
    same_pin(delta['reference_layout'], profile['base_failed_layout'])
    assert delta['selected_new_KO_glyphs'] == 4 and delta['selected_GIDs'] == [9170, 18350, 10706, 85]
    assert delta['exact_decimal_Tm_e_delta'] == '3.3125'
    assert 0 <= delta['max_actual_selected_dx_residual_pt'] <= .001
    for key in ('nonselected_glyph_attributes_bit_exact', 'original_native_glyphs_bit_exact',
                'selected_y_size_font_GID_color_opacity_paint_direction_exact'):
        assert delta[key] is True
    physical = value['actual_full_Tm_CTM_physical_transform_audit']
    assert delta['nonselected_new_KO_glyphs_including_spaces'] == physical['all_KO_glyphs_including_spaces_verified'] - 4
    assert delta['all_visible_glyphs_including_spaces'] >= physical['all_KO_glyphs_including_spaces_verified']
    assert [row['scale'] for row in delta['pixel_union_by_scale']] == [2, 4, 8]
    for row in delta['pixel_union_by_scale']:
        assert row['changed_pixels_outside_exact_old_new_row_ink_union'] == 0 and row['total_changed_pixels'] > 0
    special = value['actual_stream_interrow_ink']['corrected_special_pair_multiscale']
    assert len(special) == 1 and special[0]['upper_baseline'] == 410.8339538574219
    assert special[0]['lower_baseline'] == 421.5059509277344
    assert special[0]['contact_pixels_by_scale'] == {'2': 0, '4': 0, '8': 0}
    native = value['actual_target_language_vs_native_ink']
    assert native['contact_pixels_by_scale'] == {'2': 0, '4': 0, '8': 0}
    assert native['KO_threshold'] == 220 and native['native_threshold'] == 180
    assert [row['scale'] for row in native['fixed_multiscale_native_contact']] == [2, 4, 8]
    assert all(row['threshold'] == 180 and row['contact_pixels'] == 0 for row in native['fixed_multiscale_native_contact'])
    inherited = value['P0_inherited_W_precision_plus_exact_repair_union_comparison']
    assert inherited['passed'] is True and inherited['P0_origin_bit_exact_claimed'] is False
    assert inherited['P0']['sha256'] == previous_page['proof_sha256']
    same_pin(inherited['failed_P1'], profile['base_failed_proof']); same_pin(inherited['target'], origin['proof'])
    assert inherited['native_fonts_images_exact'] is True
    base_comparison = inherited['inherited_base_comparison']
    assert base_comparison['reference_sha256'] == previous_page['proof_sha256']
    for key in ('passed', 'native_glyphs_exact', 'source_and_new_font_program_binaries_exact',
                'encoded_images_and_placements_exact', 'native_shifts_exact',
                'planned_words_point_sizes_styles_word_spaces_and_all_other_placement_fields_exact'):
        assert base_comparison[key] is True
    assert base_comparison['changed_pixels_outside_explicit_glyph_union'] == 0 and base_comparison['pixel_scale'] == 2
    # The separate aggregate P0 rendering may use a full KO-ink envelope.
    # The exact P1 object/glyph delta above remains the narrow repair guard.
    assert inherited['actual_pixel_mask_scope'] == 'all_actual_P0_and_target_KO_stream_RGB_ink_support'
    assert inherited['exact_exception_mask_claimed'] is False
    assert inherited['change_scope_independently_restricted_by'] == [
        'unmodified_P0_to_failed_P1_reference_contract', 'exact_failed_P1_to_target_four_glyph_and_object_contract']
    assert [row['scale'] for row in inherited['pixel_union_by_scale']] == [2, 4, 8]
    assert all(row['changed_pixels_outside_actual_P0_target_all_KO_ink_support'] == 0
               for row in inherited['pixel_union_by_scale'])


def validate_native_replay(pins, replay, proof_pin, layout_pin, vector):
    assert replay['passed'] is True
    for key in ('input_pdf', 'input_pdf_after'): same_pin(replay[key], proof_pin)
    for key in ('input_layout', 'input_layout_after'): same_pin(replay[key], layout_pin)
    assert replay['scratch_pdf_byte_identical_to_input'] is True
    assert replay['only_refreshed_semantic_field'] == 'actual_native_vector_coordinate_audit'
    assert replay['all_other_layout_fields_exact'] is True
    assert replay['frozen_native_math_and_tolerances_unchanged'] is True
    source = pins.checked(replay['frozen_verifier_program'])
    assert Path(source['path']) == R4 / '2026/composer/verify_native_vectors.py'
    before, before_pin = pins.document(replay['scratch_layout_input']['path'],
                                      replay['scratch_layout_input']['sha256'], evidence=True)
    after, after_pin = pins.document(replay['scratch_layout_after']['path'],
                                    replay['scratch_layout_after']['sha256'], evidence=True)
    copied = pins.checked(replay['scratch_pdf'])
    assert copied['sha256'] == proof_pin['sha256'] and before_pin['sha256'] == layout_pin['sha256']
    for value in (copied, before_pin, after_pin):
        assert Path(value['path']).is_relative_to(REPAIR / 'audit-scratch')
    assert Path(copied['path']).read_bytes() == Path(proof_pin['path']).read_bytes()
    assert Path(before_pin['path']).read_bytes() == Path(layout_pin['path']).read_bytes()
    expected = deepcopy(before); expected['actual_native_vector_coordinate_audit'] = vector
    assert after == expected
    receipt, receipt_pin = pins.document(replay['receipt']['path'], replay['receipt']['sha256'], evidence=True)
    assert Path(receipt_pin['path']).parent == Path(copied['path']).parent
    assert receipt == {key: value for key, value in replay.items() if key != 'receipt'}
    pins.references(replay, evidence=True)


def validate_negatives(pins, profile):
    value, value_pin = pins.document(profile['actual_negative_regressions']['path'],
                                     profile['actual_negative_regressions']['sha256'], evidence=True)
    real_document(value)
    assert value['schema'] == 'ortvay-2026-page07-actual-repair-negative-regressions-v1'
    assert value['status'] == 'ALL_REQUIRED_ACTUAL_PDF_AND_BINDING_NEGATIVES_REJECTED'
    same_pin(value['repair_code_input_freeze'], profile['repair_code_input_freeze'])
    same_pin(value['numeric_spec'], profile['numeric_spec'])
    same_pin(value['root_GO'], profile['root_GO']); same_pin(value['actual_positive'], profile['actual_positive'])
    auditor = next(p for p in profile['additional_runtime_files'] if Path(p['path']).name == 'audit_page07_repair.py')
    same_pin(value['program'], auditor)
    assert value['no_missing_file_or_import_failure_counted'] is True
    protected = value['positive_files_rehashed_unchanged']; assert protected
    assert protected[profile['actual_positive']['path']] == profile['actual_positive']['sha256']
    positive_dir = REPAIR / 'page07'
    expected_names = {'page07.pdf', 'page07.layout.json', 'page07.authoring-draft.json',
                      'page07.effective-plan.json', 'page07.png', 'independent-qa.json',
                      'postprocess-receipt.json', 'repair-runtime-snapshot.json'}
    expected_paths = {positive_dir / name for name in expected_names}
    expected_paths.update(positive_dir / 'runtime-sources/additional' / name for name in PROGRAM_NAMES)
    assert len(protected) == 11 and {Path(p).resolve() for p in protected} == expected_paths
    for path, digest in protected.items():
        pins.add(path, digest)
        if Path(path).suffix == '.json': pins.document(path, digest, evidence=True)
    for program in profile['additional_runtime_files']:
        path = positive_dir / 'runtime-sources/additional' / Path(program['path']).name
        assert protected[str(path)] == program['sha256']
    assert protected[str(positive_dir / 'repair-runtime-snapshot.json')] == profile['repair_runtime_snapshot']['sha256']
    assert len(value['cases']) == 11 and {r['name'] for r in value['cases']} == PDF_NEGATIVES | BINDING_NEGATIVES
    for row in value['cases']:
        assert row['rejected'] is True and row['expected_guard']
        error = row['actual_error']
        assert error['exception_type'] == 'AssertionError' and isinstance(error['message'], str) and error['stage']
        if row['name'] in PDF_NEGATIVES:
            assert row.get('binding_only', False) is False
            proof = pins.checked(row['candidate_proof'])
            candidate, candidate_pin = pins.document(row['candidate_layout']['path'],
                                                      row['candidate_layout']['sha256'], evidence=True)
            assert Path(proof['path']).is_relative_to(REPAIR / 'regressions')
            assert Path(candidate_pin['path']).is_relative_to(REPAIR / 'regressions')
            assert candidate['output_sha256'] == proof['sha256']
            assert row['fresh_layout_output_sha_matches_candidate_pdf'] is True
        else:
            assert row['binding_only'] is True
    valid, valid_pin = pins.document(value['valid_candidate_read_only_control']['path'],
                                    value['valid_candidate_read_only_control']['sha256'], evidence=True)
    real_document(valid)
    assert valid['status'] == 'VALID_CANDIDATE_FULL_AUDIT_PASS_INPUTS_AND_POSITIVE_TREE_UNCHANGED'
    assert valid['passed'] is True and valid['candidate_core_passed'] is True
    assert valid['before'] == valid['after']
    assert valid['positive_tree_sha256_before'] == valid['positive_tree_sha256_after'] == protected
    positive = read(profile['actual_positive']['path'])
    assert protected[str(positive_dir / 'page07.pdf')] == positive['proof']['sha256']
    assert protected[str(positive_dir / 'page07.layout.json')] == positive['layout']['sha256']
    assert protected[str(positive_dir / 'page07.authoring-draft.json')] == positive['layout']['sha256']
    for key in ('proof', 'layout'):
        item = pins.checked(valid['before'][key])
        assert Path(item['path']).is_relative_to(REPAIR / 'regressions/valid-candidate-read-only')
        assert item['sha256'] == positive[key]['sha256']
        assert Path(item['path']).read_bytes() == Path(positive[key]['path']).read_bytes()
    same_pin(valid['repair_code_input_freeze'], profile['repair_code_input_freeze'])
    same_pin(valid['program'], auditor)
    validate_native_replay(pins, valid['native_vector_readonly_replay'], valid['before']['proof'],
                           valid['before']['layout'], positive['actual_native_vector_coordinate_audit'])
    pins.references(valid, evidence=True)
    pins.references(value, evidence=True)
    return value, value_pin


def validate_copies(pins, ready, qa):
    """Keep original and assembly paths distinct and prove every exact copy."""
    assert Path(ready['assembly_proof_dir']).resolve() == MIXED / 'proofs'
    receipt, receipt_pin = pins.document(ready['assembly_copy_receipt']['path'],
                                       ready['assembly_copy_receipt']['sha256'], evidence=True)
    real_document(receipt)
    assert receipt['schema'] == 'ortvay-mixed-origin-proof-copy-receipt-v1'
    assert receipt['status'] == 'ALL10_ORIGIN_TO_ASSEMBLY_COPIES_BYTE_IDENTICAL'
    assert receipt['year'] == 2026 and receipt['pages'] == 10
    assert receipt['body_embedded_paths_rewritten'] is False
    assert Path(receipt['assembly_proof_dir']).resolve() == MIXED / 'proofs'
    assert len(receipt['copies']) == 30
    copies = {(r['page'], r['key']): r for r in receipt['copies']}
    assert len(copies) == 30 and set(copies) == {(n, k) for n in range(1, 11) for k in COPY_SUFFIX}
    assert len(ready['page_results']) == len(ready['assembly_page_results']) == len(qa['page_audits']) == 10
    for number, (origin, assembly, page) in enumerate(zip(
            ready['page_results'], ready['assembly_page_results'], qa['page_audits'], strict=True), 1):
        assert origin['page'] == assembly['page'] == page['page'] == number
        assert assembly['historical_body_paths_rewritten'] is False
        same_pin(assembly['copy_receipt'], receipt_pin)
        origin_dir = REPAIR / 'page07' if number == 7 else R4 / f'2026/proofs/ortvay/2026'
        for key, suffix in COPY_SUFFIX.items():
            before = pins.checked(origin[key]); after = pins.checked(assembly['copied_artifacts'][key])
            same_pin(assembly['origin_artifacts'][key], before)
            assert Path(before['path']) == origin_dir / f'page{number:02}{suffix}'
            assert Path(after['path']) == MIXED / f'proofs/page{number:02}{suffix}'
            assert before['sha256'] == after['sha256'] and before['bytes'] == after['bytes']
            assert Path(before['path']).read_bytes() == Path(after['path']).read_bytes()
            row = copies[number, key]
            assert row['byte_equal'] is True and row['bytes'] == before['bytes']
            same_pin(row['origin'], before); same_pin(row['copied'], after)
            same_pin(row['origin_machine'], origin['machine_result'])
            same_pin(row['origin_visual_read'], origin['visual_review'])
            field, digest = {'proof': ('proof_path', 'proof_sha256'), 'layout': ('qa_path', 'qa_sha256'),
                             'effective_plan': ('effective_plan_path', 'effective_plan_sha256')}[key]
            consumed = pins.add(page[field], page[digest])
            if key == 'effective_plan':
                # ASM98 reads the unchanged historical path embedded in body.
                # Its separately prepared assembly copy has the exact same bytes.
                body = read(origin['layout']['path'])
                same_pin(consumed, dict(path=body['effective_plan_path'], sha256=body['effective_plan_sha256']))
                assert consumed['sha256'] == after['sha256']
                assert Path(consumed['path']).read_bytes() == Path(after['path']).read_bytes()
            else:
                same_pin(consumed, after)
    pins.references(receipt, evidence=True)
    return receipt, receipt_pin


def validate_origin_page(pins, origin, page, visual, binding):
    """Validate one unmodified original page, independently of assembly copies."""
    number = origin['page']; assert number in (1, 2, 3, 4, 5, 6, 8, 9, 10)
    assert origin['qa_lineage'] == 'external_full_ctm_v1'
    assert origin['reviewed'] is True and origin['human_read_pending'] is False
    machine, machine_pin = pins.document(origin['machine_result']['path'], origin['machine_result']['sha256'], evidence=True)
    assert machine['status'] == 'PAGE_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_HUMAN_REVIEW'
    assert machine['year'] == 2026 and machine['page'] == number and machine['human_read_pending'] is True
    review, review_pin = pins.document(origin['visual_review']['path'], origin['visual_review']['sha256'], evidence=True)
    assert review['status'] == 'ACTUAL_FINAL_PNG_ORIGINAL_RESOLUTION_READ_PASS'
    assert review['year'] == 2026 and review['page'] == number and review['reviewer']
    assert contains_reference(visual, review_pin) and contains_reference(visual, machine_pin)
    for key in ARTIFACTS:
        same_pin(machine[key], origin[key]); pins.checked(origin[key])
        same_pin(review.get('artifacts', review.get('artifact_pins'))[key], origin[key])
        if 'artifacts' in review and 'artifact_pins' in review:
            same_pin(review['artifacts'][key], review['artifact_pins'][key])
    own, _ = pins.document(origin['production_runtime_snapshot']['path'],
                           origin['production_runtime_snapshot']['sha256'], evidence=True)
    body, body_pin = pins.document(origin['layout']['path'], origin['layout']['sha256'])
    audit, audit_pin = pins.document(origin['independent_audit']['path'], origin['independent_audit']['sha256'], evidence=True)
    assert body['output_sha256'] == origin['proof']['sha256'] == page['proof_sha256']
    assert body_pin['sha256'] == page['qa_sha256']
    validate_ctm_page_lineage(audit, machine, own, binding, 2026, number)
    for value in (origin['runtime_snapshot'], dict(path=audit['audit_runtime_snapshot'], sha256=audit['audit_runtime_snapshot_sha256'])):
        check_original_runtime(pins, value, 2026, binding['original_code'])
    for path, value in own['files'].items():
        pins.add(path, value['sha256']); pins.add(value['retained_copy'], value['sha256'])
    effective, effective_pin = pins.document(origin['effective_plan']['path'], origin['effective_plan']['sha256'])
    validate_page(audit, body, 2026, body_pin['sha256'],
                  effective_plan_binding(effective_pin['path'], effective_pin['sha256'], effective))
    return dict(page=number, independent_audit=audit_pin, machine_result=machine_pin,
                visual_review=review_pin, proof_sha256=origin['proof']['sha256'], layout_sha256=body_pin['sha256'])


def assert_production_go_available():
    assert isinstance(APPROVED_REPAIR_GO_SHA256, str) and len(APPROVED_REPAIR_GO_SHA256) == 64, \
        'The reviewed actual repair GO has not been pinned. Draft support cannot stage.'


def collect(pdf, qa, ready_path, pins, root):
    """Read all original/repair/assembly evidence before any mutable staging."""
    assert_production_go_available()
    ready_path = Path(ready_path).resolve(); pdf = Path(pdf).resolve(); root = Path(root).resolve()
    assert ready_path == MIXED / 'READY.json' and pdf.name == 'Ortvay_2026_T_KO.pdf'
    ready, ready_pin = pins.document(ready_path, evidence=True); real_document(ready)
    assert ready['schema'] == READY_SCHEMA and ready['status'] == READY_STATUS
    assert ready['competition'] == 'Ortvay' and ready['year'] == 2026 and ready['pages'] == 10
    assert ready['human_read_pending'] is False and ready['all_pages_actual_original_resolution_png_read'] is True
    ledger, runtime, preparation = fixed_inputs(pins)
    rules, _ = pins.document(ledger['years']['2026']['rules_path'], ledger['years']['2026']['rules_sha256'])
    source_pin = pins.checked(ready['source'])
    assert Path(source_pin['path']) == Path(rules['source_path']).resolve()
    assert source_pin['sha256'] == ready['source_sha256'] == rules['source_sha256'] == qa['source_sha256']
    pdf_pin = pins.add(pdf); joined, joined_pin = pins.document(pdf.with_suffix('.qa.json'), evidence=True)
    assert joined == qa and qa['schema'] == 'natural-source-native-joined-v1' and qa['status'] == 'READY'
    assert qa['sha256'] == pdf_pin['sha256'] and qa['bytes'] == pdf_pin['bytes'] and qa['pages'] == 10
    assert qa['visual_review_required'] is False and qa['all_pages_visually_reviewed'] is True
    original_code = {Path(p).resolve(): s for p, s in runtime['runtime_code_sha256'].items()}
    binding = validate_ctm_profile(ready, lambda p: pins.document(p['path'], p['sha256'], evidence=True)[0], pins.checked)
    binding['original_code'] = original_code
    for key, pin in binding['profile'].items(): same_pin(ready['base_profile'][key], pin)
    repair = validate_repair_profile(pins, ready['page_repair_profile'], binding)
    negatives, negatives_pin = validate_negatives(pins, ready['page_repair_profile'])
    previous_item = next(r for r in read(root / 'tools/original_style_publication.json') if r['file'] == pdf.name)
    assert previous_item['sha256'] == PUBLISHED[2026], 'Stage only against the retained previous published edition'
    previous_path = root / previous_item['qa']; previous = read(previous_path)
    assert previous['pages'] == 10 and previous['sha256'] == PUBLISHED[2026]
    previous_pin = pins.add(previous_path)
    normalized, normalized_pin = pins.document(ready['visual_review_normalized']['path'],
                                              ready['visual_review_normalized']['sha256'], evidence=True)
    assert Path(normalized_pin['path']) == MIXED / 'visual-review-mixed-normalized.json'
    assert normalized['source_sha256'] == source_pin['sha256'] and normalized['year'] == 2026 and len(normalized['pages']) == 10
    assert Path(normalized_pin['path']) in {Path(p).resolve() for p in qa['visual_review_files']}
    copy_doc, copy_pin = validate_copies(pins, ready, qa)
    pages = []; composer = None
    for number, (origin, assembly, page, visual) in enumerate(zip(
            ready['page_results'], ready['assembly_page_results'], qa['page_audits'], normalized['pages'], strict=True), 1):
        assert origin['year'] == 2026 and origin['page'] == assembly['page'] == page['page'] == visual['page'] == number
        assert origin['reviewed'] is True and origin['human_read_pending'] is False and visual['reviewed'] is True
        assert visual['proof_sha256'] == page['proof_sha256'] == origin['proof']['sha256']
        assert visual['layout_sha256'] == page['qa_sha256'] == origin['layout']['sha256']
        assert visual['effective_plan_sha256'] == page['effective_plan_sha256'] == origin['effective_plan']['sha256']
        assert Path(visual['proof_path']).resolve() == Path(page['proof_path']).resolve()
        assert Path(visual['layout_path']).resolve() == Path(page['qa_path']).resolve()
        assert page['final_vs_reviewed_proof_changed_pixels'] == 0
        assert page['final_vs_reviewed_proof_all_glyph_geometry_identical'] is True
        body, body_pin = pins.document(origin['layout']['path'], origin['layout']['sha256'])
        assert body['page'] == number and body['source_sha256'] == source_pin['sha256']
        assert body['output_sha256'] == origin['proof']['sha256']
        current = pins.add(body['composer_path'], body['composer_sha256'])
        assert original_code[Path(current['path'])] == current['sha256']
        if composer is None: composer = current
        assert current == composer and ready['composer_sha256'] == current['sha256']
        assert visual['composer_sha256'] == current['sha256']
        base_plan = pins.checked(rules['base_plans'][str(number)])
        assert body['plan_sha256'] == page['plan_sha256'] == base_plan['sha256']
        same_pin(pins.add(page['plan_path'], page['plan_sha256']), base_plan)
        override = rules['overrides'].get(str(number))
        if override:
            checked = pins.checked(override); assert body['overrides_sha256'] == page['overrides_sha256'] == checked['sha256']
            same_pin(pins.add(page['overrides_path'], page['overrides_sha256']), checked)
        else:
            assert not body.get('overrides_sha256') and not page.get('overrides_sha256') and not page.get('overrides_path')
        if number != 7:
            assert 'page_repair_profile' not in visual and 'page_repair_profile' not in origin
            row = validate_origin_page(pins, origin, page, visual, binding)
            audit = read(row['independent_audit']['path'])
            assert audit['current_published_complete_document_lineage']['P0_frozen_page_sha256'] == previous['page_audits'][number-1]['proof_sha256']
        else:
            assert visual['page_repair_profile'] == ready['page_repair_profile']
            assert origin['qa_lineage'] == 'external_full_ctm_v1_plus_exact_row_postprocess'
            assert origin['page_repair_profile'] == ready['page_repair_profile']
            machine, machine_pin = pins.document(origin['machine_result']['path'], origin['machine_result']['sha256'], evidence=True)
            assert machine['schema'] == 'ortvay-one-page-postprocess-machine-result-v1'
            assert machine['status'] == 'PAGE_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_HUMAN_REVIEW'
            assert machine['year'] == 2026 and machine['page'] == 7 and machine['human_read_pending'] is True
            assert machine['qa_lineage'] == origin['qa_lineage'] and machine['page_repair_profile'] == ready['page_repair_profile']
            review, review_pin = pins.document(origin['visual_review']['path'], origin['visual_review']['sha256'], evidence=True)
            assert review['status'] == 'ACTUAL_FINAL_PNG_ORIGINAL_RESOLUTION_READ_PASS' and review['reviewer']
            assert review['year'] == 2026 and review['page'] == 7
            assert contains_reference(visual, machine_pin) and contains_reference(visual, review_pin)
            for key in ARTIFACTS:
                same_pin(machine[key], origin[key]); pins.checked(origin[key])
                same_pin(review['artifacts'][key], origin[key])
            same_pin(review['machine_result'], machine_pin)
            same_pin(machine['repair_runtime_snapshot'], ready['page_repair_profile']['repair_runtime_snapshot'])
            audit, audit_pin = pins.document(origin['independent_audit']['path'], origin['independent_audit']['sha256'], evidence=True)
            same_pin(audit_pin, ready['page_repair_profile']['actual_positive'])
            validate_positive(pins, audit, body, body_pin, origin, ready['page_repair_profile'], repair,
                              previous['page_audits'][number-1])
            row = dict(page=7, independent_audit=audit_pin, machine_result=machine_pin, visual_review=review_pin,
                       proof_sha256=origin['proof']['sha256'], layout_sha256=body_pin['sha256'])
        row.update(qa_lineage=origin['qa_lineage'],
                   origin_artifacts={k: origin[k] for k in COPY_SUFFIX},
                   assembly_artifacts=assembly['copied_artifacts'])
        pages.append(row)
    base_runtime = [dict(**pins.add(path, digest), relative_path=path.relative_to(R4).as_posix())
                    for path, digest in sorted(binding['runtime_programs'].items())]
    assert len(base_runtime) == 46
    pins.references(ready, evidence=True)
    return dict(ready=ready, ready_pin=ready_pin, pages=pages, binding=binding, repair=repair,
                base_runtime=base_runtime, previous=previous_item, previous_pin=previous_pin,
                pdf_pin=pdf_pin, joined_pin=joined_pin, normalized_pin=normalized_pin, copy_pin=copy_pin,
                negatives=negatives, negatives_pin=negatives_pin)


def prepare(comp, year, pdf, qa, config_path, root, base):
    assert_production_go_available()
    assert comp == 'ortvay' and year == 2026 and Path(base).resolve() == BASE
    config_path = Path(config_path).resolve(); config = read(config_path)
    assert config['schema'] == CONFIG_SCHEMA and config['year'] == 2026
    assert config['publication_subdir'] == 'source-style-page07-repair-20261104'
    assert config['output_sha256'] == sha(pdf) == qa['sha256']
    assert config['source_sha256'] == qa['source_sha256']
    seen = set()
    for row in config['pins']:
        path = Path(row['path']).resolve(); assert path not in seen; seen.add(path)
        assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes'], ('Stale repaired publication input', path)
    pins = Pins()
    result = collect(pdf, qa, config['original_ready']['path'], pins, root)
    assert config['original_ready']['sha256'] == result['ready_pin']['sha256'] == config['ready']['sha256']
    assert sha(config['ready']['path']) == config['ready']['sha256']
    evidence = []
    by_digest = {}
    for pin in config['evidence']:
        checked = pins.checked(pin); path = Path(checked['path'])
        assert path.suffix == '.json'
        by_digest.setdefault(checked['sha256'], []).append(checked)
        evidence.append(path)
    def staged_json(pin):
        matches = by_digest.get(pin['sha256'], [])
        assert matches, ('Missing staged JSON evidence', pin)
        for match in matches: assert read(match['path']) == read(pin['path'])
        return matches[0]
    assert len(config['pages']) == 10
    pages = []
    for actual, stored in zip(result['pages'], config['pages'], strict=True):
        assert actual['page'] == stored['page']
        page = dict(page=actual['page'], qa_lineage=actual['qa_lineage'],
                    proof_sha256=actual['proof_sha256'], layout_sha256=actual['layout_sha256'],
                    origin_artifacts=actual['origin_artifacts'], assembly_artifacts=actual['assembly_artifacts'])
        for key in ('independent_audit', 'machine_result', 'visual_review'):
            assert actual[key]['sha256'] == stored[key]['sha256']
            alias = pins.checked(stored[key]); assert read(alias['path']) == read(actual[key]['path'])
            assert alias['sha256'] in by_digest
            page[key + '_source'] = alias['path']; page[key + '_sha256'] = alias['sha256']
        pages.append(page)
    runtime = config['runtime_files']
    assert len(runtime) == 46
    assert {Path(p['path']).resolve(): p['sha256'] for p in runtime} == result['binding']['runtime_programs']
    for row in runtime:
        pins.checked(row); assert row['relative_path'] == Path(row['path']).resolve().relative_to(R4).as_posix()
    programs = [Path(__file__), BASE / 'engine/ortvay_source_style_publication.py',
                BASE / 'engine/ortvay_full_ctm_publication.py', Path(config['builder']['path'])]
    programs.extend(result['repair']['additional_programs'])
    for path in programs:
        assert path.resolve() in seen, ('Unpinned publication program', path)
        pins.add(path)
    profile = result['ready']['page_repair_profile']
    amendments = dict(numeric_spec=staged_json(profile['numeric_spec']),
        repair_freeze=staged_json(profile['repair_code_input_freeze']), repair_GO=staged_json(profile['root_GO']),
        copy_receipt=staged_json(result['copy_pin']), positive=staged_json(profile['actual_positive']),
        negatives=staged_json(profile['actual_negative_regressions']))
    for key, filename in [('postprocessor', 'postprocess_page07.py'), ('auditor', 'audit_page07_repair.py'),
                          ('bridge', 'continue_and_bridge_2026.py')]:
        matches = [p for p in profile['additional_runtime_files'] if Path(p['path']).name == filename]
        assert len(matches) == 1; amendments[key] = pins.checked(matches[0])
    assert set(amendments) == AMENDMENT_KEYS
    manifest = dict(schema=MANIFEST_SCHEMA, year=2026, source_sha256=qa['source_sha256'],
        original_published_sha256=PUBLISHED[2026],
        reference_publication=dict(path=result['previous']['qa'], sha256=result['previous_pin']['sha256']),
        ready_source=config['ready']['path'], ready_sha256=config['ready']['sha256'], pages=pages,
        qa_amendment=amendments)
    for key, pin in result['binding']['profile'].items():
        alias = staged_json(pin); manifest[key + '_source'] = alias['path']; manifest[key + '_sha256'] = alias['sha256']
    return dict(kind='source_style', config=config, manifest=manifest, evidence=list(dict.fromkeys(evidence)),
                programs=list(dict.fromkeys(programs)), runtime_files=runtime)

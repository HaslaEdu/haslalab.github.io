"""Publication contract for independent Ortvay R4 actual-PDF evidence."""
import math
import hashlib
import json
from pathlib import Path
import ortvay_full_ctm_publication as full_ctm

PUBLISHED = {
    2023: 'a0dd0bc102765652ef05d3ac9f3c1c1d855980cbda601227ee0c76771be08051',
    2024: '60324d40a7432d2fff694516fb8b244c58f6d6070510bde6291da5313b0f39e0',
    2025: '754b6ecf1d74b178a279476b49ae608988f2507ddff3ffbbcf409545e52454b8',
    2026: '075b32d0a3cba93748a289dafda2e150f5de0803356c055b2b252dddf79955a6',
}

R4 = Path(__file__).resolve().parents[1] / 'layout-corrections/ortvay-title-20261103/revisions/source-style-widths-r4-20261103'
CTM_QA = R4 / 'qa-amendments/full-ctm-rotation-v1-20261103'
CTM_PRODUCTION = R4 / 'production-continuation/full-ctm-v1-20261103'
CTM_PROFILE = {
    'qa_profile_freeze': (CTM_QA / 'AMENDMENT-FROZEN.json', 'a02844e98ef9a0e332f10312ec66a48fac5d87338e2d414c6ec24338f3c652a7'),
    'qa_profile_root_go': (CTM_PRODUCTION / 'ROOT-GO.json', '8f56f0f8a6db8400c0d9ee2a9b6c62026f2e50984e7b669e5e1c12f4282ea0d4'),
    'qa_profile_actual_regressions': (CTM_QA / 'runs/prototype03/BATCH-RESULTS.json', '13a4269f16d8697cccd951840be944fadb6cb6c206516ec71c45ba1b946f02ea'),
    'qa_profile_post_freeze_guard': (CTM_QA / 'runs/frozen-guard01/p7_rotated_label/audit.json', '26ff348ad46c4c38dcc61b2c4ca8176e833737ba5831f60874cb84233e2ae61d'),
    'code_input_freeze': (CTM_PRODUCTION / 'CODE-INPUT-FROZEN.json', 'ad9b4855ac822214da7ecca0955af9abb3a1fecae4dbb33827ecb9ee59554079'),
    'original_code_input_freeze': (R4 / 'PREPARATION-FROZEN.json', 'ff8c247d3e072c9a031e7e68589958b2f3eebfb8764722dde61c5681ec46d47a'),
    'original_runtime_freeze': (R4 / 'PROTOTYPE-RUNTIME-FROZEN.json', '27b5df6951f5ce45d390f51aa2d193bdd22c0740163846add788060e2972132b'),
}


def same_source_pin(left, right):
    assert Path(left['path']).resolve() == Path(right['path']).resolve()
    assert left['sha256'] == right['sha256']


def validate_ctm_profile(profile, document, checked):
    """Exact root-approved profile, independent of alias filenames.

    document(pin) reads a hash-checked JSON and registers public evidence;
    checked(pin) checks other original/private/program bytes without copying.
    Neither callback may render or execute a producer.
    """
    canonical = {name: dict(path=str(path), sha256=digest) for name, (path, digest) in CTM_PROFILE.items()}
    docs = {}
    for name, expected in canonical.items():
        assert profile[name]['sha256'] == expected['sha256'], ('Unapproved CTM profile', name)
        docs[name] = document(profile[name])
    qa = docs['qa_profile_freeze']; production = docs['code_input_freeze']; token = docs['qa_profile_root_go']
    original = docs['original_runtime_freeze']; preparation = docs['original_code_input_freeze']
    assert qa['status'] == 'EXTERNAL_FULL_CTM_QA_PROFILE_FROZEN_AFTER_19_ACTUAL_CASES'
    assert qa['production_resume_authorized'] is False and qa['post_freeze_guard_confirmation_required'] is True
    assert qa['all19_actual_case_results_same_code_and_CASES'] is True
    assert qa['per_case_source_target_code_before_after_assertions_passed'] is True
    assert qa['unchanged_original_unique_files'] == 1534 and qa['unchanged_private_inputs'] == 597
    assert len(qa['code_sha256']) == len(qa['retained_code_copies']) == 6
    qa_code = {Path(path).resolve(): digest for path, digest in qa['code_sha256'].items()}
    assert {path.name for path in qa_code} == {'amended_actual_paint.py', 'amended_independent_qa.py', 'amended_outline_qa.py', 'make_actual_controls.py', 'run_amended_audit.py', 'transform_guard.py'}
    assert all(path.parent == CTM_QA for path in qa_code)
    for source, digest in qa_code.items():
        checked(dict(path=str(source), sha256=digest))
        retained = qa['retained_code_copies'][str(source)]
        assert retained['sha256'] == digest
        checked(retained)
    assert len(qa['actual_regression_inputs_sha256']) == 38
    for path, digest in qa['actual_regression_inputs_sha256'].items():
        checked(dict(path=path, sha256=digest))
    for key in ('matrix_regressions', 'actual_control_creation', 'byte_identical_control_native_layout_copies', 'base_source_diff'):
        if Path(qa[key]['path']).suffix == '.json': document(qa[key])
        else: checked(qa[key])
    cases_pin = dict(path=str(CTM_QA / 'CASES.json'), sha256=qa['cases_sha256'])
    cases = document(cases_pin)['cases']
    document(dict(path=str(CTM_QA / 'FROZEN-BASE-SOURCES.json'), sha256=qa['base_sources_sha256']))
    same_source_pin(qa['actual_regressions'], canonical['qa_profile_actual_regressions'])
    batch = docs['qa_profile_actual_regressions']
    assert batch['passed'] is True and batch['cases'] == 19 and batch['positive'] == 9 and batch['negative'] == 10
    assert batch['external_code_sha256'] == qa['code_sha256'] and batch['cases_manifest_sha256'] == qa['cases_sha256']
    assert len(batch['page_results']) == len(cases) == 19 and batch['no_producer_or_publication_resume'] is True
    seen = set(); positives = negatives = 0
    for row in batch['page_results']:
        name = row['case']; assert name not in seen; seen.add(name)
        assert row['matched_expected'] is True and row['expected'] == cases[name]['expected']
        result = document(row['result'])
        assert result['case'] == name and result['external_code_sha256'] == qa['code_sha256']
        assert result['target'] == cases[name]['target'] and result['layout'] == cases[name]['layout']
        snapshot = document(result['snapshot'])
        assert snapshot['code_sha256'] == qa['code_sha256'] and snapshot['case_manifest']['sha256'] == qa['cases_sha256']
        assert snapshot['case_spec'] == cases[name]
        if row['expected'] == 'PASS':
            assert result['passed'] is True and result['status'] == 'EXTERNAL_FULL_CTM_AMENDMENT_QA_PASS_NOT_PRODUCER_RESUME'
            positives += 1
        else:
            assert row['expected'] == 'REJECT' and result['status'] == 'EXTERNAL_AMENDMENT_QA_REJECTED_NOT_READY'
            assert result['exception_type'] == 'AssertionError'
            assert result['stage'] in ('original_full_master_glyph_geometry', 'amended_full_CTM_independent_audit')
            negatives += 1
    assert positives == 9 and negatives == 10 and seen == set(cases)
    guard = docs['qa_profile_post_freeze_guard']
    assert guard['passed'] is True and guard['year'] == 2025 and guard['page'] == 7 and guard['case'] == 'p7_rotated_label'
    assert guard['external_code_sha256'] == qa['code_sha256']
    same_source_pin(guard['external_amendment_freeze'], canonical['qa_profile_freeze'])
    guard_body = document(guard['layout'])
    validate_page(guard, guard_body, 2025, guard['layout']['sha256'])
    guard_snapshot = document(guard['snapshot'])
    same_source_pin(guard_snapshot['external_amendment_freeze'], canonical['qa_profile_freeze'])
    assert guard_snapshot['code_sha256'] == qa['code_sha256']
    roster = [dict(year=2025, page=p) for p in range(7, 13)] + [dict(year=2026, page=p) for p in range(1, 11)]
    assert production['status'] == 'R4_MIXED_LINEAGE_CONTINUATION_CODE_AND_INPUT_FROZEN'
    assert production['allowed_pages'] == token['allowed_pages'] == roster
    assert production['production_was_not_run'] is True and production['no_publication_tools_are_execution_dependencies'] is True
    production_code = {CTM_PRODUCTION / 'continue_and_finalize.py': 'baf8c139979721a1e0209b51c0a443a7f9dff24cb1be6dff5e770e2cf6c708e4'}
    assert {Path(path).resolve(): digest for path, digest in production['code_sha256'].items()} == production_code
    for path, digest in production_code.items(): checked(dict(path=str(path), sha256=digest))
    static = ('qa_profile_freeze', 'qa_profile_actual_regressions', 'qa_profile_post_freeze_guard', 'original_code_input_freeze', 'original_runtime_freeze')
    for name in static:
        same_source_pin(production[name], canonical[name]); same_source_pin(token[name], canonical[name])
    assert token['status'] == 'ROOT_GO_R4_MIXED_LINEAGE_FULL_CTM_CONTINUATION'
    same_source_pin(token['code_input_freeze'], canonical['code_input_freeze'])
    assert token['original_producer_code_may_change'] is False
    assert token['existing_proof_layout_ready_and_original_failure_may_change'] is False
    assert len(production['preserved_files_sha256']) == 241
    for path, digest in production['preserved_files_sha256'].items(): checked(dict(path=path, sha256=digest))
    document(production['p7_original_build_snapshot'])
    original_code = {Path(path).resolve(): digest for path, digest in original['runtime_code_sha256'].items()}
    assert len(original_code) == 39 and len(original['runtime_input_sha256']) == 15
    assert preparation['runtime_code_sha256'] == original['runtime_code_sha256']
    assert preparation['runtime_input_sha256'] == original['runtime_input_sha256']
    for path, digest in original_code.items(): checked(dict(path=str(path), sha256=digest))
    assert set(original_code).isdisjoint(qa_code) and set(original_code).isdisjoint(production_code)
    return dict(profile=canonical, additional_programs={**qa_code, **production_code},
                external_audit_programs=qa_code, production_programs=production_code,
                runtime_programs={**original_code, **qa_code, **production_code})


def validate_ctm_page_lineage(audit, machine, snapshot, binding, year, page):
    for name, expected in binding['profile'].items():
        same_source_pin(audit[name], expected); same_source_pin(machine[name], expected); same_source_pin(snapshot[name], expected)
    assert audit['status'] == 'EXTERNAL_FULL_CTM_PRODUCTION_AUDIT_PASSED'
    assert {Path(path).resolve(): digest for path, digest in audit['qa_profile_code_sha256'].items()} == binding['external_audit_programs']
    assert {Path(path).resolve(): digest for path, digest in audit['production_code_sha256'].items()} == binding['production_programs']
    assert machine['qa_lineage'] == 'external_full_ctm_v1' and machine['year'] == year and machine['page'] == page
    files = {Path(path).resolve(): row['sha256'] for path, row in snapshot['files'].items()}
    assert len(files) == len(snapshot['files']) and files == binding['additional_programs']
    original_audit = {path: digest for path, digest in binding['runtime_programs'].items()
                      if path.parent == R4 / 'common' or path == R4 / 'audit_final_page.py'}
    assert {Path(path).resolve(): digest for path, digest in audit['audit_code_sha256'].items()} == {**original_audit, **binding['additional_programs']}
    same_source_pin(machine['audit_runtime_snapshot'], dict(path=audit['audit_runtime_snapshot'], sha256=audit['audit_runtime_snapshot_sha256']))
    if year == 2025 and page == 7:
        assert audit['original_failed_audit_preserved'] is True
    assert 'actual_full_Tm_CTM_physical_transform_audit' in audit


def validate_original_runtime_snapshot(snapshot, binding, year, checked):
    assert snapshot['schema'] == 'r4-live-runtime-source-snapshot-v1' and snapshot['year'] == year
    assert snapshot['input_ledger_sha256'] == '500bab6a7ef21470c9e4dbf427a6046641a5603cb935c3588dee8d948e9c0656'
    expected = {path: digest for path, digest in binding['runtime_programs'].items()
                if path.parent == R4 / 'common' or path.is_relative_to(R4 / str(year) / 'composer')}
    actual = {Path(path).resolve(): row['sha256'] for path, row in snapshot['files'].items()}
    assert len(actual) == len(snapshot['files']) and actual == expected
    for source, row in snapshot['files'].items():
        checked(dict(path=source, sha256=row['sha256']))
        checked(dict(path=row['retained_copy'], sha256=row['sha256']))


def validate_ctm_runtime_files(runtime, binding):
    actual = {Path(row['path']).resolve(): row['sha256'] for row in runtime}
    assert len(actual) == len(runtime) == 46 and actual == binding['runtime_programs']
    for row in runtime:
        assert row['relative_path'] == Path(row['path']).resolve().relative_to(R4).as_posix()

def effective_plan_binding(path, expected_sha256, document=None):
    """Keep exact UTF-8 file bytes for the pure wrap-space contract."""
    raw=Path(path).read_bytes().decode('utf8')
    assert hashlib.sha256(raw.encode('utf8')).hexdigest()==expected_sha256
    parsed=json.loads(raw.removeprefix('\ufeff'))
    if document is not None:assert parsed==document
    return dict(path=str(Path(path).resolve()),sha256=expected_sha256,raw_utf8=raw,document=parsed)


def validate_page(audit, body, year, layout_sha256=None, effective_plan=None):
    assert year in PUBLISHED and audit['year'] == year
    assert audit['passed'] is True and audit['page'] == body['page']
    assert audit['proof_sha256'] == body['output_sha256']
    geometry = audit['original_full_master_geometry']
    authored = body['placements'] + body.get('raster_labels', [])
    actual = sum(sum(not c.isspace() for c in item['text']) for item in authored)
    if body.get('new_korean_glyph_and_geometry_audit'):
        assert body['new_korean_glyph_and_geometry_audit']['actual_glyphs'] == actual
    assert geometry['passed'] is True
    assert geometry['planned_glyphs'] == geometry['actual_glyphs'] == actual
    assert geometry['original_full_font_gids_verified'] == actual
    assert geometry['geometry_errors'] == geometry['original_full_font_gid_errors'] == []
    assert 0 <= geometry['max_position_error_pt'] <= .001
    assert 0 < geometry['position_tolerance_pt'] <= .001
    assert audit['actual_outline_and_encoded_W_audit_pending'] is False
    outline = audit['actual_outline_and_encoded_W_audit']
    assert outline['passed'] is True and outline['errors'] == []
    assert outline['actual_CID_TJ_W_glyphs_verified'] == outline['actual_master_outline_bounds_verified'] == actual
    assert outline['master_hmtx_and_gid_exact'] is True
    assert 0 <= outline['actual_W_TJ_replay_max_origin_error_pt'] <= .001
    assert 0 <= outline['max_transformed_outline_error_pt'] <= .001
    assert 0 < outline['tolerance_pt'] <= .001
    authored_italics = body['r4_source_style_corrections']
    actual_italics = audit['actual_target_physical_shear']
    for authored in authored_italics:
        assert authored['original_descriptor_angle'] == -14 and authored['physical_target_angle'] == 14
        assert authored['original_point_size_and_logical_origin_unchanged'] is True
        assert any(abs(actual['baseline']-authored['baseline']) <= .001 for actual in actual_italics)
    for italic in actual_italics:
        assert any(abs(italic['baseline']-authored['baseline']) <= .001 for authored in authored_italics)
        tangent = italic['physical_pdf_cm_c']
        assert math.isfinite(tangent) and tangent > 0
        assert abs(tangent - math.tan(math.radians(14))) <= 1e-5
    ink = audit['actual_stream_interrow_ink']
    for key in ['passed', 'all_target_KO_glyphs_accounted_for', 'each_extracted_row_glyph_trace_matches_target']:
        assert ink[key] is True
    assert ink['scale'] == 2 and ink['threshold'] == 220
    assert ink['tested_close_row_pairs'] == len(ink['pairs'])
    assert all(pair['contact_pixels_2x'] == 0 for pair in ink['pairs'])
    native = audit['actual_target_language_vs_native_ink']
    assert native['passed'] is True
    assert native['actual_KO_vs_original_remaining_ink_contact_pixels_2x'] == 0
    assert native['original_font_resources_preserved_in_both_controls'] is True
    lineage = audit['current_published_complete_document_lineage']
    assert lineage['passed'] is True and lineage['published_document_sha256'] == PUBLISHED[year]
    assert lineage['published_page_index'] == body['page'] - 1
    assert lineage['published_page_trace_exact'] is True and lineage['published_page_pixels_2x_exact'] is True
    references = audit['direct_reference_comparisons']
    expected = ['P0_current_published'] + (['P1_approved_intermediate'] if year in (2024, 2025) else [])
    if year==2026 and body['page']==1:
        expected.append('P2_precise_Tm_precontact_failed_AA_control')
        row=audit['preexisting_AA_contact_KO_row_correction']
        assert row['baseline']==683.5799560546875 and row['dx']==-.5625
        assert row['source_size_pt']==11.9552001953125 and row['whitelist_glyphs']==29
        assert row['source_slot_id']=='p1:b8:l2:s0-30' and row['native_source_atoms_on_this_row']==0
        assert row['logical_KO_row_horizontal_translation_only']is True
        assert row['authorization_sha256']=='88e28a759dafc97838cd039fc07941a31ef3cdb8d805a1c55c9c2bf36045e9c7'
        assert references[-1]['reference_sha256']=='ae1e8529fcada7735b77652d0a79a5a91164a06af3b365e480c9d1ab13b12ea1'
    assert [row['lineage'] for row in references] == expected
    assert references[0]['reference_sha256'] == lineage['P0_frozen_page_sha256']
    for reference in references:
        for key in ['passed', 'native_glyphs_exact', 'source_and_new_font_program_binaries_exact',
                    'encoded_images_and_placements_exact', 'native_shifts_exact',
                    'planned_words_point_sizes_styles_word_spaces_and_all_other_placement_fields_exact']:
            assert reference[key] is True
        assert reference['actual_new_glyphs_compared'] == actual
        assert reference['pixel_scale'] == 2 and reference['changed_pixels_outside_explicit_glyph_union'] == 0
        if reference['lineage'] == 'P1_approved_intermediate':
            assert reference['approved_intermediate_titles_preserved'] is True
        assert len(reference['title_centers']) == (4 if body['page'] == 1 and year != 2023 else 0)
        for title in reference['title_centers']:
            assert abs(title['error']) <= .001
            assert abs(title['actual_center'] - title['original_center'] - title['error']) <= 1e-9
    vector = audit['actual_native_vector_coordinate_audit']
    assert vector['coordinate_errors'] == []
    assert 0 < vector['max_coordinate_tolerance_pt'] <= 1e-7
    assert vector == body['actual_native_vector_coordinate_audit']
    full_transform = 'actual_full_Tm_CTM_physical_transform_audit'
    if year == 2025 and body['page'] == 7:
        assert full_transform in audit, 'Missing mandatory full-Tm/CTM audit for Ortvay 2025 page 7'
    if full_transform in audit:
        # The caller has just checked these layout bytes.  Do not accept an
        # unbound report-only layout hash in the additive transform contract.
        assert isinstance(layout_sha256, str) and len(layout_sha256) == 64
        full_ctm.validate(audit, body, year, layout_sha256, effective_plan)

def prepare(comp, year, pdf, qa, config_path, root, base):
    """Check every live input before the mutable publication tree is touched."""
    def sha(path):
        with Path(path).open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()
    def read(path):
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    def checked(pin):
        path=Path(pin['path']).resolve()
        assert path.is_file() and sha(path)==pin['sha256'], ('Stale source-style evidence',path)
        if 'bytes' in pin: assert path.stat().st_size==pin['bytes']
        return path
    assert comp=='ortvay' and year in PUBLISHED
    config=read(config_path)
    assert config['schema']=='ortvay-source-style-publication-config-v1'
    assert config['year']==year and config['publication_subdir']=='source-style-correction-r4-20261103'
    assert config['source_sha256']==qa['source_sha256']
    assert config['output_sha256']==qa['sha256']==sha(pdf)
    registry=read(root/'tools/original_style_publication.json')
    previous_item=next(row for row in registry if row['file']==Path(pdf).name)
    assert previous_item['sha256']==PUBLISHED[year]
    previous_path=root/previous_item['qa'];previous=read(previous_path)
    assert previous['sha256']==PUBLISHED[year] and previous['source_sha256']==qa['source_sha256']
    assert previous['pages']==qa['pages']
    # All frozen source/private/runtime ledgers are flattened explicitly in
    # the root-produced config. No stale boolean replaces checking the bytes.
    assert config['pins']
    for pin in config['pins']: checked(pin)
    ready_path=checked(config['ready']);ready=read(ready_path)
    assert ready['status']=='YEAR_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_ROOT_ASSEMBLY_REVIEW'
    assert ready['year']==year and ready['pages']==qa['pages']
    assert ready['source']['sha256']==qa['source_sha256']
    assert len(ready['page_results'])==len(config['pages'])==qa['pages']
    evidence=[ready_path]
    ctm_binding=None
    if year in (2025,2026):
        assert ready['schema']=='ortvay-source-style-width-correction-ready-v2-mixed-ctm'
        def profile_document(pin):
            # The raw D references and the byte-identical public alias must both
            # exist; append only the alias to avoid raw basename collisions.
            original_path=checked(pin)
            matches=[row for row in config['evidence']if row['sha256']==pin['sha256']]
            assert matches,('Unstaged mandatory CTM evidence',original_path)
            public_path=checked(matches[0]);assert public_path.suffix=='.json'
            evidence.append(public_path)
            return read(original_path)
        ctm_binding=validate_ctm_profile(config,profile_document,checked)
        for name,expected in ctm_binding['profile'].items():
            same_source_pin(ready[name],expected)
    pages=[];italic_count=0;uses_full_ctm=False
    for index,(pin,page,ready_page)in enumerate(zip(config['pages'],qa['page_audits'],ready['page_results'])):
        assert pin['page']==ready_page['page']==page['page']==index+1
        assert ready_page['proof']['sha256']==page['proof_sha256']
        assert ready_page['layout']['sha256']==page['qa_sha256']
        checked(ready_page['proof']);checked(ready_page['layout'])
        audit_path=checked(pin['independent_audit']);audit=read(audit_path)
        body_path=Path(page['qa_path']);layout_sha256=sha(body_path)
        assert layout_sha256==page['qa_sha256'];body=read(body_path)
        assert body['page']==index+1 and body['output_sha256']==page['proof_sha256']
        plan_path=checked(dict(path=page['effective_plan_path'],sha256=page['effective_plan_sha256']))
        assert page['effective_plan_sha256']==body['effective_plan_sha256']
        plan=effective_plan_binding(plan_path,page['effective_plan_sha256'])
        validate_page(audit,body,year,layout_sha256,plan)
        uses_full_ctm|='actual_full_Tm_CTM_physical_transform_audit'in audit
        page_extra={}
        if ctm_binding:
            amended=not(year==2025 and index<6)
            assert ready_page['qa_lineage']==('external_full_ctm_v1'if amended else'old_frozen_r4')
            machine_path=checked(pin['machine_result']);review_path=checked(pin['visual_review'])
            assert ready_page['machine_result']['sha256']==pin['machine_result']['sha256']
            assert ready_page['visual_review']['sha256']==pin['visual_review']['sha256']
            checked(ready_page['machine_result']);checked(ready_page['visual_review'])
            machine=read(machine_path);review=read(review_path)
            assert machine['status']=='PAGE_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_HUMAN_REVIEW'
            assert machine['human_read_pending']is True and machine['year']==year and machine['page']==index+1
            assert ready_page['reviewed']is True and ready_page['human_read_pending']is False
            assert review['year']==year and review['page']==index+1 and review['reviewer']
            assert review.get('passed')is True or review.get('status')=='ACTUAL_FINAL_PNG_ORIGINAL_RESOLUTION_READ_PASS'
            artifacts=review.get('artifacts',review.get('artifact_pins'))
            for key in('proof','layout','png','effective_plan','independent_audit','runtime_snapshot'):
                same_source_pin(machine[key],ready_page[key]);checked(machine[key])
                same_source_pin(artifacts[key],ready_page[key]);checked(artifacts[key])
            proof_dir=R4/str(year)/f'proofs/ortvay/{year}'
            pdir=CTM_PRODUCTION/f'pages/{year}/page{index+1:02}'
            for key,suffix in [('proof','.pdf'),('layout','.layout.json'),('effective_plan','.effective-plan.json')]:
                assert Path(ready_page[key]['path']).resolve()==proof_dir/f'page{index+1:02}{suffix}'
            png_path=proof_dir/f'page{index+1:02}.png'if year==2025 and index<7 else pdir/f'page{index+1:02}.png'
            assert Path(ready_page['png']['path']).resolve()==png_path
            assert Path(ready_page['machine_result']['path']).resolve()==(pdir/'result.json'if amended else proof_dir/f'page{index+1:02}.result.json')
            assert Path(ready_page['visual_review']['path']).resolve()==(pdir/'visual-read.json'if amended else R4/'2025'/f'visual-reads/page{index+1:02}.json')
            if amended:
                assert Path(ready_page['independent_audit']['path']).resolve()==pdir/'independent-qa.json'
                own=profile_document(machine['production_runtime_snapshot'])
                same_source_pin(audit['production_runtime_snapshot'],machine['production_runtime_snapshot'])
                validate_ctm_page_lineage(audit,machine,own,ctm_binding,year,index+1)
                for path,row in own['files'].items():
                    source=Path(path).resolve();folder='qa'if source.parent==CTM_QA else'production'
                    assert Path(row['retained_copy']).resolve()==pdir/'runtime-sources'/folder/source.name
                    checked(dict(path=row['retained_copy'],sha256=row['sha256']))
            for snapshot_pin in(machine['runtime_snapshot'],dict(path=audit['audit_runtime_snapshot'],sha256=audit['audit_runtime_snapshot_sha256'])):
                validate_original_runtime_snapshot(profile_document(snapshot_pin),ctm_binding,year,checked)
            evidence.extend([machine_path,review_path])
            page_extra=dict(qa_lineage=ready_page['qa_lineage'],machine_result_source=str(machine_path),
                            machine_result_sha256=sha(machine_path),visual_review_source=str(review_path),visual_review_sha256=sha(review_path))
        assert audit['current_published_complete_document_lineage']['P0_frozen_page_sha256']==previous['page_audits'][index]['proof_sha256']
        for code_path,digest in audit['audit_code_sha256'].items():assert sha(code_path)==digest
        evidence.append(audit_path)
        italic_count+=len(body['r4_source_style_corrections'])
        pages.append(dict(page=index+1,proof_sha256=page['proof_sha256'],layout_sha256=page['qa_sha256'],
                          independent_audit_source=str(audit_path),independent_audit_sha256=sha(audit_path),**page_extra))
    assert italic_count=={2023:22,2024:11,2025:11,2026:1}[year]
    for pin in config['evidence']: evidence.append(checked(pin))
    runtime=[];destinations={}
    for pin in config['runtime_files']:
        source=checked(pin);relative=Path(pin['relative_path'])
        assert not relative.is_absolute() and '..' not in relative.parts and source.suffix=='.py'
        assert relative.as_posix() not in destinations or destinations[relative.as_posix()]==pin['sha256']
        destinations[relative.as_posix()]=pin['sha256']
        runtime.append(dict(path=str(source),sha256=pin['sha256'],relative_path=relative.as_posix()))
    assert runtime
    if ctm_binding:
        validate_ctm_runtime_files(runtime,ctm_binding)
    runtime_hashes={pin['sha256']for pin in runtime}
    for page in config['pages']:
        audit=read(page['independent_audit']['path'])
        assert set(audit['audit_code_sha256'].values())<=runtime_hashes
    link_programs=[]
    if year in(2023,2024,2025):
        regression=read(checked(config['link_regression']))
        test=checked(config['link_test'])
        assert regression['status']=='PASS'and regression['changed_pixels']==0
        assert regression['assembler_sha256']==sha(base/'engine/assemble_natural.py')
        assert regression['program_sha256']==sha(test)
        assert regression['source_sha256']==qa['source_sha256']
        assert regression['all_nonrect_annotation_settings_identical_after_save']is True
        assert regression['all_visible_glyph_geometry_identical']is True
        assert regression['year']==year and regression['ready_manifest']['sha256']==sha(ready_path)
        assert regression['annotation_P_same_page_semantics_verified']is True
        assert regression['all_annotation_rectangles_checked_after_save']is True
        for path,digest in regression['inputs_rehashed_after_run'].items():
            assert sha(path)==digest,('Changed fresh annotation regression input',path)
        negatives=regression['negative_regression_details']
        assert len(negatives)>={2023:18,2024:10,2025:9}[year]
        assert all(row['rejected']is True for row in negatives)
        checked(dict(path=regression['core_program_path'],sha256=regression['core_program_sha256'])) if 'core_program_path'in regression else None
        core=test.parent/'r4_private_link_regression.py'
        assert sha(core)==regression['core_program_sha256']
        link_programs.extend([test,core])
        legacy_test=base/'engine'/(f'test_ortvay{year}_link_subsets.py'if year in(2023,2024)else'test_ortvay2025_link.py')
        assert regression['inputs_rehashed_after_run'][str(legacy_test.resolve())]==sha(legacy_test)
        link_programs.append(legacy_test)
        if year==2023:
            assert [row['page']for row in regression['pages']]==[1,6]
            for row in regression['pages']:
                actual=qa['page_audits'][row['page']-1]
                assert row['proof_sha256']==actual['proof_sha256'] and row['layout_sha256']==actual['qa_sha256']
            aggregate=checked(dict(path=regression['aggregation_program_path'],sha256=regression['aggregation_program_sha256']))
            link_programs.append(aggregate)
        else:
            actual=qa['page_audits'][{2024:1,2025:9}[year]]
            assert regression['proof_sha256']==actual['proof_sha256'] and regression['layout_sha256']==actual['qa_sha256']
        evidence.append(Path(config['link_regression']['path']))
    evidence=list(dict.fromkeys(evidence))
    by_name={}
    for path in evidence:
        assert path.suffix=='.json',('Public supplemental evidence must be JSON',path)
        assert path.name not in by_name or by_name[path.name]==sha(path),('Evidence basename collision',path)
        by_name[path.name]=sha(path)
    manifest=dict(schema='ortvay-source-style-publication-v1',year=year,source_sha256=qa['source_sha256'],
                  original_published_sha256=PUBLISHED[year],
                  reference_publication=dict(path=previous_item['qa'],sha256=sha(previous_path)),
                  ready_source=str(ready_path),ready_sha256=sha(ready_path),pages=pages)
    if ctm_binding:
        for name in CTM_PROFILE:
            profile_path=checked(config[name])
            manifest[name+'_source']=str(profile_path);manifest[name+'_sha256']=sha(profile_path)
    return dict(kind='source_style',config=config,manifest=manifest,evidence=evidence,
                programs=[Path(__file__)]+([Path(full_ctm.__file__)]if uses_full_ctm else[])+list(dict.fromkeys(link_programs)),runtime_files=runtime)

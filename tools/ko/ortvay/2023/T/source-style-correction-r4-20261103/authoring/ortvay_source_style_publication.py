"""Publication contract for independent Ortvay R4 actual-PDF evidence."""
import math
import hashlib
import json
from pathlib import Path

PUBLISHED = {
    2023: 'a0dd0bc102765652ef05d3ac9f3c1c1d855980cbda601227ee0c76771be08051',
    2024: '60324d40a7432d2fff694516fb8b244c58f6d6070510bde6291da5313b0f39e0',
    2025: '754b6ecf1d74b178a279476b49ae608988f2507ddff3ffbbcf409545e52454b8',
    2026: '075b32d0a3cba93748a289dafda2e150f5de0803356c055b2b252dddf79955a6',
}

def validate_page(audit, body, year):
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
    pages=[];italic_count=0
    for index,(pin,page,ready_page)in enumerate(zip(config['pages'],qa['page_audits'],ready['page_results'])):
        assert pin['page']==ready_page['page']==page['page']==index+1
        assert ready_page['proof']['sha256']==page['proof_sha256']
        assert ready_page['layout']['sha256']==page['qa_sha256']
        checked(ready_page['proof']);checked(ready_page['layout'])
        audit_path=checked(pin['independent_audit']);audit=read(audit_path)
        body_path=Path(page['qa_path']);assert sha(body_path)==page['qa_sha256'];body=read(body_path)
        assert body['page']==index+1 and body['output_sha256']==page['proof_sha256']
        validate_page(audit,body,year)
        assert audit['current_published_complete_document_lineage']['P0_frozen_page_sha256']==previous['page_audits'][index]['proof_sha256']
        for code_path,digest in audit['audit_code_sha256'].items():assert sha(code_path)==digest
        evidence.append(audit_path)
        italic_count+=len(body['r4_source_style_corrections'])
        pages.append(dict(page=index+1,proof_sha256=page['proof_sha256'],layout_sha256=page['qa_sha256'],
                          independent_audit_source=str(audit_path),independent_audit_sha256=sha(audit_path)))
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
    return dict(kind='source_style',config=config,manifest=manifest,evidence=evidence,
                programs=[Path(__file__)]+list(dict.fromkeys(link_programs)),runtime_files=runtime)

"""Strict contract for the68 source-bound IChO2024 prose stroke paths."""
import hashlib
import math

SOURCE='959174ab5ddc8be71c251c8fe95a12c810ba730edbcbbef3b771197e32929a4a'
MEASUREMENT='9f7397f1437c9c78b383d2f6624d1cee64472930f849cad6a7f972bd2625ecb4'
CURVE_READER='8e032abc9060b2be0a2af658cb7b1a6e2edb333aa0b7a228e40bdd60c1705799'
MAPPING='ad5990b8ceb44b2dabbfc7a53ce8c344907d4b5b243f58e4e7cd88fba0dfde8a'
SEMANTIC='bbc753360d5c243a4ca31fede8047b67b212cecea704bfae275521e82b8082e4'
AFFINE='aecd02348c9130307402f372cbe7e740f15e1210759b9acc3bf2970f69e232d2'

def one(rows,key,value):
    matches=[row for row in rows if row[key]==value]
    assert len(matches)==1
    return matches[0]

def validate_contact(q,contact,decoration):
    assert q['source_sha256']==SOURCE
    assert contact['source_bound_prose_x_affine_only']is True
    audit=q['actual_prose_underline_coverage_and_style_audit']
    assert audit['passed']is True and audit['proof_sha256']==q['output_sha256']
    assert audit['source_sha256']==SOURCE and audit['page']==q['page']
    assert audit['measurement_code_sha256']==MEASUREMENT and audit['actual_curve_reader_sha256']==CURVE_READER
    assert 0<audit['underline_coverage_tolerance_pt']<=.001 and 0<audit['source_native_vector_tolerance_pt']<=1e-7
    assert audit['protected_native_ink_contact_pixels']==0
    assert audit['all_actual_curve_bboxes_match_requested_full_font_and_matrix']is True
    semantic=q['independent_source_semantic_style_audit']
    assert semantic['passed']is True and semantic['proof_sha256']==q['output_sha256']
    assert semantic['source_sha256']==SOURCE and semantic['mapping_sha256']==MAPPING
    assert semantic['program_sha256']==SEMANTIC
    for key in ['all_requested_font_roles_bound_to_actual_original_source_styles',
                'exact_original_sizes_and_raw_prose_baseline_pool_membership_preserved','no_other_bold_or_italic_changes']:
        assert semantic[key]is True
    row=one(audit['underline_rows'],'id',contact['id'])
    mapped=one(semantic['semantic_mappings'],'index',decoration['semantic_mapping_index'])
    assert mapped['target_literal']==decoration['target_text']
    assert mapped['target_fragment_id']==decoration['slot_id']
    assert mapped['target_font_role']==decoration['target_font_role']
    assert abs(mapped['source_pointsize']-decoration['target_pointsize'])<=.001
    assert abs(mapped['source_original_baseline']-decoration['target_baseline'])<=.001
    assert abs(mapped['actual_target_baseline']-decoration['target_baseline'])<=.001
    assert row['actual_native_path_index']==contact['source_path_index']
    assert row['original_y_thickness_black_stroke_and_paint_preserved']is True
    assert row['actual32x_vertical_stroke_sample_byte_equal']is True
    assert row['source_English_glyph_path_guards_verified']is True
    assert row['all_Korean_used_glyph_GIDs_outlines_and_hmtx_match_pinned_full_font']is True
    assert row['actual32x_samples']
    for sample in row['actual32x_samples']:
        assert sample['byte_identical']is True and sample['source']==sample['candidate']
        assert sample['source'][1] and min(sample['source'][1])<255
    program=decoration['source_program']
    assert program['source_text'].strip()==mapped['source_English'].strip()
    assert program['slot_id']==decoration['original_source_slot_id']
    assert program['source_is_pure_top_level_horizontal_m_l_S']is True
    assert program['source_operator_names']==['m','l','S']
    assert program['source_operator_indices']==decoration['operator_indices']
    assert decoration['paint_operator']=='S' and decoration['source_construction_and_paint_bytes_preserved']is True
    fragment=program['source_construction_and_paint_fragment_latin1'].encode('latin1')
    assert hashlib.sha256(fragment).hexdigest()==program['source_construction_and_paint_fragment_sha256']
    drawing=program['source_drawing']
    assert abs(drawing['width']-.398499995470047)<=1e-9
    assert drawing['color']==[0,0,0] and drawing['fill']is None
    assert drawing['lineCap']==[0,0,0] and drawing['lineJoin']==0
    affine=q['source_prose_underline_affine_audit']
    assert affine['passed']is True and affine['source_sha256']==SOURCE and affine['program_sha256']==AFFINE
    assert affine['input_moved_sha256']==q['native_motion_before_prose_underline_affine_sha256']
    assert affine['all_other_source_content_bytes_preserved_by_exact_splices']is True
    path=one(affine['paths'],'id',contact['id'])
    assert path['source_fragment_sha256']==program['source_construction_and_paint_fragment_sha256']
    assert path['source_fragment_literal_preserved']is True and path['source_y_and_vertical_stroke_scale_unchanged']is True
    assert path['source_operator_names']==['m','l','S']
    source,target=decoration['source_rect'],decoration['target_rect']
    assert source==program['source_exact_path_rect']==path['source_rect']==row['source_rect']
    assert target==path['target_rect']
    matrix=path['page_x_affine']
    assert matrix[1:4]==[0,0,1] and matrix[5]==0 and math.isfinite(matrix[0])and matrix[0]>0
    assert abs(matrix[0]-decoration['x_scale'])<=1e-9
    for index in(0,2):
        assert abs(source[index]*matrix[0]+matrix[4]-target[index])<=1e-7
        assert abs(row['actual_underline_bbox'][index]-target[index])<=.001
        assert abs(row['actual_underline_bbox'][index]-row['actual_emphasized_glyph_curve_union_bbox'][index])<=.001
    for index in(1,3):
        assert source[index]==target[index] and abs(row['actual_underline_bbox'][index]-source[index])<=1e-7
    assert 0<=row['actual_horizontal_ink_coverage_error_pt']<=.001

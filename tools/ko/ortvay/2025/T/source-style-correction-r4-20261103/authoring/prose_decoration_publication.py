"""Validate narrowly reviewed IChO2019 prose underlines during publication.

The source underline may fit translated word ink horizontally. Its original
vertical geometry and paint remain fixed; scientific paths keep strict checks.
"""
import math

SOURCE_2019 = '5821bab3b65b216cc74df99d7ec643389d212c15b4d88c95a7da22de8baf97d8'
MEASUREMENT_2019 = '79729dd00f2f9c5f14b8ef9657ee4ebd186c0cb2043c64b7806bd2a0b4aeeda4'
CURVE_READER_2019 = '13c5fb97d4faa712dba8361565fd30cae3b886e7ec37b83ab55a7425e2e0fa3c'

def validate_contact(q, contact):
    assert contact['source_path_bytes_and_paint_and_y_preserved'] is True
    decorations = [d for d in q['prose_vector_decorations'] if d['id'] == contact['id']]
    assert len(decorations) == 1
    decoration = decorations[0]
    assert contact['source_path_index'] == decoration['source_path_index']
    assert contact['observed_contact_pixels'] == len(contact['contact_pixels_pdf_pt'])
    # A Boolean must not downgrade measured affine evidence to the legacy
    # translation-only contract. Legacy records have no affine fields.
    affine = (q['source_sha256'] == SOURCE_2019 or
              'actual_prose_underline_coverage_and_style_audit' in q or
              any(k in decoration for k in ('prose_decoration_x_scale',
                  'source_bound_prose_x_affine_only', 'source_program',
                  'fit_source_prose_underline_to_translated_phrase')) or
              'prose_decoration_x_scale' in contact)
    if contact['x_translation_only'] is True:
        assert not affine, 'Affine evidence cannot use the legacy Boolean bypass'
        assert math.isfinite(decoration['dx'])
        for key in ('actual_prose_underline_protected_native_ink_contact_pixels',):
            if key in q:
                assert q[key] == 0
        return
    assert contact['x_translation_only'] is False
    if q['source_sha256']=='959174ab5ddc8be71c251c8fe95a12c810ba730edbcbbef3b771197e32929a4a':
        from icho2024_prose_decoration_publication import validate_contact as validate_icho2024
        validate_icho2024(q,contact,decoration)
        return
    assert q['source_sha256'] == SOURCE_2019
    audit = q['actual_prose_underline_coverage_and_style_audit']
    assert audit['passed'] is True
    assert audit['source_sha256'] == SOURCE_2019 and audit['page'] == q['page']
    assert audit['proof_sha256'] == q['output_sha256']
    assert audit['measurement_code_sha256'] == MEASUREMENT_2019
    assert audit['actual_curve_reader_sha256'] == CURVE_READER_2019
    assert 0 < audit['underline_coverage_tolerance_pt'] <= .001
    assert 0 < audit['source_native_vector_tolerance_pt'] <= 1e-7
    assert audit['protected_native_ink_contact_pixels'] == 0
    assert q['actual_prose_underline_protected_native_ink_contact_pixels'] == 0
    rows = [r for r in audit['underline_rows'] if r['id'] == contact['id']]
    scopes = [s for s in q['reviewed_moving_prose_decoration_paths'] if s['id'] == contact['id']]
    assert len(rows) == len(scopes) == 1
    row, scope = rows[0], scopes[0]
    assert scope['source_sha256'] == SOURCE_2019
    assert scope['source_prose_glyphs'] and decoration['target_ink_records']
    assert scope['vector_path']['operator_indices'] == decoration['operator_indices']
    assert scope['vector_path']['paint_operator'] == decoration['paint_operator']
    assert scope['vector_path']['rect'] == decoration['source_rect'] == row['source_rect']
    assert row['actual_native_path_index'] == contact['source_path_index']
    assert decoration['fit_source_prose_underline_to_translated_phrase'] is True
    scale = contact['prose_decoration_x_scale']
    assert math.isfinite(scale) and scale > 0
    assert scale == decoration['prose_decoration_x_scale'] == scope['source_prose_decoration_x_scale']
    source, target = decoration['source_rect'], decoration['target_rect']
    assert source[2] > source[0] and target[2] > target[0]
    assert abs((target[2]-target[0]) / (source[2]-source[0]) - scale) <= 1e-9
    for i in (1, 3):
        assert abs(source[i] - target[i]) <= 1e-7
        assert abs(source[i] - row['actual_underline_bbox'][i]) <= 1e-7
    assert row['original_y_thickness_black_fill_and_paint_preserved'] is True
    assert row['source_English_glyph_path_guards_verified'] is True
    assert row['all_Korean_used_glyph_GIDs_outlines_and_hmtx_match_pinned_full_font'] is True
    assert 0 <= row['actual_horizontal_ink_coverage_error_pt'] <= .001
    for i in (0, 2):
        assert abs(row['actual_underline_bbox'][i] - row['actual_emphasized_glyph_curve_union_bbox'][i]) <= .001
        assert abs(row['actual_underline_bbox'][i] - target[i]) <= .001

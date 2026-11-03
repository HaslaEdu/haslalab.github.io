const assert = require('node:assert/strict');

module.exports = function validateProseDecoration(body, contact, qa) {
  assert.equal(contact.source_path_bytes_and_paint_and_y_preserved, true);
  const matches = body.prose_vector_decorations.filter(d => d.id === contact.id);
  assert.equal(matches.length, 1);
  const decoration = matches[0];
  assert.equal(contact.source_path_index, decoration.source_path_index);
  assert.equal(contact.observed_contact_pixels, contact.contact_pixels_pdf_pt.length);
  const affine = body.source_sha256 === '5821bab3b65b216cc74df99d7ec643389d212c15b4d88c95a7da22de8baf97d8' ||
    Object.hasOwn(body, 'actual_prose_underline_coverage_and_style_audit') ||
    ['prose_decoration_x_scale', 'source_bound_prose_x_affine_only', 'source_program',
      'fit_source_prose_underline_to_translated_phrase'].some(k => Object.hasOwn(decoration, k)) ||
    Object.hasOwn(contact, 'prose_decoration_x_scale');
  if (contact.x_translation_only === true) {
    assert.equal(affine, false, 'Affine evidence cannot use the legacy Boolean bypass');
    assert.ok(Number.isFinite(decoration.dx));
    if (Object.hasOwn(body, 'actual_prose_underline_protected_native_ink_contact_pixels'))
      assert.equal(body.actual_prose_underline_protected_native_ink_contact_pixels, 0);
    return;
  }
  assert.equal(contact.x_translation_only, false);
  if(body.source_sha256==='959174ab5ddc8be71c251c8fe95a12c810ba730edbcbbef3b771197e32929a4a') {
    require('./icho2024-prose-decoration-publication.cjs')(body,contact,decoration,qa);
    return;
  }
  const source = '5821bab3b65b216cc74df99d7ec643389d212c15b4d88c95a7da22de8baf97d8';
  const measurement = '79729dd00f2f9c5f14b8ef9657ee4ebd186c0cb2043c64b7806bd2a0b4aeeda4';
  const curveReader = '13c5fb97d4faa712dba8361565fd30cae3b886e7ec37b83ab55a7425e2e0fa3c';
  assert.equal(body.source_sha256, source);
  const audit = body.actual_prose_underline_coverage_and_style_audit;
  assert.equal(audit.passed, true);
  assert.equal(audit.source_sha256, source);
  assert.equal(audit.page, body.page);
  assert.equal(audit.proof_sha256, body.output_sha256);
  assert.equal(audit.measurement_code_sha256, measurement);
  assert.equal(audit.actual_curve_reader_sha256, curveReader);
  for (const [filename, digest] of [['verify_prose_underline_and_style.py', measurement],
    ['actual_prose_ink_icho2019.py', curveReader]]) {
    const program = qa.authoring_programs.find(p => p.path.endsWith('/' + filename));
    assert.ok(program);
    assert.equal(program.sha256, digest);
  }
  assert.ok(audit.underline_coverage_tolerance_pt > 0 && audit.underline_coverage_tolerance_pt <= .001);
  assert.ok(audit.source_native_vector_tolerance_pt > 0 && audit.source_native_vector_tolerance_pt <= 1e-7);
  assert.equal(audit.protected_native_ink_contact_pixels, 0);
  assert.equal(body.actual_prose_underline_protected_native_ink_contact_pixels, 0);
  const rows = audit.underline_rows.filter(r => r.id === contact.id);
  const scopes = body.reviewed_moving_prose_decoration_paths.filter(s => s.id === contact.id);
  assert.equal(rows.length, 1);
  assert.equal(scopes.length, 1);
  const row = rows[0], scope = scopes[0];
  assert.equal(scope.source_sha256, source);
  assert.ok(scope.source_prose_glyphs.length && decoration.target_ink_records.length);
  assert.deepEqual(scope.vector_path.operator_indices, decoration.operator_indices);
  assert.equal(scope.vector_path.paint_operator, decoration.paint_operator);
  assert.deepEqual(scope.vector_path.rect, decoration.source_rect);
  assert.deepEqual(row.source_rect, decoration.source_rect);
  assert.equal(row.actual_native_path_index, contact.source_path_index);
  assert.equal(decoration.fit_source_prose_underline_to_translated_phrase, true);
  const scale = contact.prose_decoration_x_scale;
  assert.ok(Number.isFinite(scale) && scale > 0);
  assert.equal(scale, decoration.prose_decoration_x_scale);
  assert.equal(scale, scope.source_prose_decoration_x_scale);
  const src = decoration.source_rect, target = decoration.target_rect;
  assert.ok(src[2] > src[0] && target[2] > target[0]);
  assert.ok(Math.abs((target[2] - target[0]) / (src[2] - src[0]) - scale) <= 1e-9);
  for (const i of [1, 3]) {
    assert.ok(Math.abs(src[i] - target[i]) <= 1e-7);
    assert.ok(Math.abs(src[i] - row.actual_underline_bbox[i]) <= 1e-7);
  }
  for (const key of ['original_y_thickness_black_fill_and_paint_preserved',
    'source_English_glyph_path_guards_verified',
    'all_Korean_used_glyph_GIDs_outlines_and_hmtx_match_pinned_full_font']) assert.equal(row[key], true);
  assert.ok(row.actual_horizontal_ink_coverage_error_pt >= 0 && row.actual_horizontal_ink_coverage_error_pt <= .001);
  for (const i of [0, 2]) {
    assert.ok(Math.abs(row.actual_underline_bbox[i] - row.actual_emphasized_glyph_curve_union_bbox[i]) <= .001);
    assert.ok(Math.abs(row.actual_underline_bbox[i] - target[i]) <= .001);
  }
};

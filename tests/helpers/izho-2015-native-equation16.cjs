const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const SOURCE = 'c1bc32cc38c3f3b65121439f41feee3a8bcb48dcce1a41e14b16ba177eccbcde';
const PROOF = 'c23df8d2bd30a7d6cf91edab4344d742f79c95835f40656c6e6d03d6ebee8494';
const RAW_CONTROL = 'be5d302f81073c438d3a4ec302119a6a04bb1c5c4319e86a5fa0419eaaccadcd';
const REFERENCE = 'f24582eb19736980e358865bffd3224049a9e2ab8f5637883a78cf9032c2485c';
const WITNESS = '9af9ef1e30b4bad1f914eaaa5f00bfad7be51a1ce1cc5e4c82a276e44a457147';
const PROGRAMS = '202632e91be229333cdc6ce0929bc30bcff82d814a9485228743e9d864b0ba2b', NEGATIVES = 'f864666b104a6e695c0b5beabd10940e795cca8c9712574540e6da8aaaf26a8b';
const digest = value => crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
const kind = 'source2015-complete-original-equation16-native-program-v1';
function validate(profile, witness, raw, page, item) {
  assert.equal(item.file, 'IZhO_2015_TS_KO.pdf');
  assert.equal(page.page, 4); assert.equal(page.source_pdf_sha256, SOURCE); assert.equal(page.proof_sha256, PROOF);
  assert.equal(profile.kind, kind); assert.equal(profile.witness_sha256, WITNESS);
  assert.equal(profile.exact_original_native_expression_glyphs, 40); assert.equal(profile.mathematical_ink_excluded, false);
  assert.equal(witness.kind, kind); assert.equal(witness.original_source_sha256, SOURCE);
  assert.equal(witness.original_English_source_sha256, SOURCE);
  // Four separate immutable files have different roles. Never equate the
  // complete English source SHA with the one-page raw outline control SHA.
  assert.equal(witness.original_input_page_sha256, RAW_CONTROL); assert.equal(witness.raw_outline_control_source_sha256, RAW_CONTROL);
  assert.equal(raw.source_sha256, RAW_CONTROL); assert.equal(witness.source_reference_sha256, REFERENCE);
  assert.equal(witness.source_native_reference_guard.output_sha256, REFERENCE);
  assert.equal(witness.proof_sha256, PROOF); assert.equal(witness.source_page, 4);
  assert.equal(witness.passed, true); assert.equal(witness.proof_unmodified, true);
  for (const key of ['delivered_pdf_modified','mathematics_retyped','source_font_programs_substituted']) assert.equal(witness[key], false);
  assert.equal(raw.protected_native_glyphs, 528); assert.equal(raw.newly_missing_native_ink_pixels, 1);
  assert.deepEqual(raw.missing_bbox, [368.75,763.5,369,763.75]);
  assert.deepEqual(raw.missing_requested_source_glyphs, []); assert.deepEqual(raw.missing_final_native_glyphs, []);
  assert.equal(raw.source_outline_audit.passed, true);
  const guard = witness.source_native_reference_guard;
  for (const key of ['passed','font_programs_unchanged','original_form_streams_unchanged','original_image_streams_unchanged','native_vector_path_bytes_preserved','native_atomic_clip_bytes_preserved']) assert.equal(guard[key], true);
  for (const key of ['shifted_top_level_glyphs','shifted_form_instances','shifted_reviewed_vector_paths','max_visible_position_error_x_pt','max_visible_position_error_y_pt']) assert.equal(guard[key], 0);
  assert.equal(witness.exact_original_CID_programs_checked, 40);
  assert.equal(witness.all_original_encoded_CIDs_Tf_Tm_CTM_paint_and_fractional_points_preserved, true);
  assert.equal(witness.complete_original_display_expression_glyphs.length, 40);
  const programs = witness.exact_original_CID_programs;
  assert.equal(programs.length, 40); assert.equal(digest(programs), PROGRAMS);
  const glyphFields = ['c','font','size','trace_gid','origin','render_mode','color','opacity','linewidth','direction','stroke_color','stroke_opacity','wmode','colorspace'];
  const stateFields = ['source_encoded_CID_hex','original_code','source_font_resource','source_Tf','source_Tm_linear','source_text_matrix','source_CTM','source_text_character_space','source_text_word_space','source_text_horizontal_scale','source_text_rise','source_text_render_mode'];
  for (const row of programs) {
    assert.equal(row.exact_original_CID_font_Tf_Tm_CTM_and_paint_preserved, true); assert.equal(row.requested_dx, 0);
    for (const key of glyphFields) assert.deepEqual(row.source_glyph[key],row.actual_target_glyph[key]);
    assert.ok(witness.complete_original_display_expression_glyphs.some(g => glyphFields.every(key => JSON.stringify(g[key]) === JSON.stringify(row.source_glyph[key]))));
    for (const key of stateFields) {
      assert.deepEqual(row.original_source_encoded_program[key], row.independent_original_reference_encoded_program[key]);
      assert.deepEqual(row.original_source_encoded_program[key], row.actual_final_encoded_program[key]);
    }
    assert.ok(/^[a-f0-9]+$/.test(row.original_source_encoded_program.source_encoded_CID_hex));
  }
  assert.deepEqual(witness.source_math_expression_point_sizes, [6.960000038146973,8.399999618530273,12]);
  assert.deepEqual(witness.same_integer_page_crop, [130,750,515,790]);
  const expected = new Map([
    ['MuPDF:4',[9849,5383]], ['Poppler:4',[9592,5678]],
    ['MuPDF:8',[34284,25319]], ['Poppler:8',[33238,25299]],
    ['MuPDF:12',[73025,59862]], ['Poppler:12',[71467,59836]],
  ]);
  assert.equal(witness.native_original_program_reference_measurements.length,6);
  for (const row of witness.native_original_program_reference_measurements) {
    const key = `${row.renderer}:${row.scale}`; assert.ok(expected.has(key));
    assert.deepEqual([row.reference_original_program_nonwhite_pixels,row.reference_original_program_deep_dark_pixels],expected.get(key)); expected.delete(key);
    assert.equal(row.missing_original_native_program_pixels,0); assert.equal(row.actual_reference_nonwhite_RGB_errors,0); assert.equal(row.passed,true);
  }
  assert.equal(expected.size,0);
  assert.deepEqual(Object.keys(witness.svg_reference_scales).sort(),['12','4','8']);
  for (const row of Object.values(witness.svg_reference_scales)) {
    assert.equal(row.passed,true); assert.equal(row.protected_native_glyphs,40); assert.equal(row.newly_missing_native_ink_pixels,0);
    assert.deepEqual(row.missing_requested_source_glyphs,[]); assert.deepEqual(row.missing_final_native_glyphs,[]); assert.equal(row.source_outline_audit.passed,true);
  }
  validateNegatives(witness.actual_bad_PDF_controls);
}
function validateNegatives(negative) {
  assert.equal(negative.passed,true); assert.equal(negative.all_actual_bad_PDFs_rejected,true);
  assert.equal(negative.rows.length,5); assert.equal(digest(negative),NEGATIVES);
  const ids = ['fraction-bar-only-motion','actual-fraction-numerator-only-drift','actual-native-Form-mathematical-point-damage','actual-native-displayed-counter-drift','actual-native-math-covered-metadata-unchanged'];
  assert.deepEqual(negative.rows.map(row=>row.id),ids);
  for (const row of negative.rows) {assert.equal(row.negative_rejected,true);assert.equal(row.delivered_proof_unmodified,true);assert.notEqual(row.proof_sha256,row.mutant_sha256);}
  const covered=negative.rows[4];assert.equal(covered.all_original_glyph_font_GID_point_Y_metadata_unchanged,true);assert.ok(covered.missing_actual_native_ink_pixels>0);
}
module.exports=validate;
module.exports.validateNegatives=validateNegatives;
module.exports.pins={SOURCE,PROOF,RAW_CONTROL,REFERENCE,WITNESS,PROGRAMS,NEGATIVES};

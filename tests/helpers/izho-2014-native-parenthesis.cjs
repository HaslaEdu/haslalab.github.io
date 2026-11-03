const assert = require('node:assert/strict');

module.exports = function validate(profile, witness, raw, page, item) {
  const source = '1e526966f308280accc9fe747d08259279f35324e7e7f2e0290271adcaf6536c';
  const proof = 'bfeda4e1facf5b4555781d2c517dae2d1140a7e14aee428fe05ecfee297da3c2';
  assert.equal(item.file, 'IZhO_2014_TS_KO.pdf');
  assert.equal(page.page, 2);
  assert.equal(page.source_pdf_sha256, source);
  assert.equal(page.proof_sha256, proof);
  assert.equal(profile.witness_sha256, '1623586cf1a6d2067ce9b50494a9e8a41a89e122ee3cf4b9c59c933516074d4d');
  // The replay uses the complete original English PDF. The raw outline
  // comparison uses its separately frozen, one-page source control.
  assert.equal(witness.original_language_source_sha256, source);
  assert.equal(raw.source_sha256, '9343ce36f66d0bbdb9aee69d64cd08672bca50765173f4503ca9402189c952a2');
  assert.equal(raw.protected_native_glyphs, 262);
  assert.equal(raw.newly_missing_native_ink_pixels, 1);
  assert.deepEqual(raw.missing_bbox, [196.5,753.75,196.75,754]);
  assert.equal(raw.source_outline_audit.passed, true);
  assert.deepEqual(raw.missing_requested_source_glyphs, []);
  assert.deepEqual(raw.missing_final_native_glyphs, []);
  assert.equal(witness.source_page, 2);
  assert.equal(witness.proof_sha256, proof);
  assert.equal(witness.passed, true);
  assert.equal(witness.proof_unmodified, true);
  for (const key of ['delivered_pdf_modified','mathematics_retyped','source_font_programs_substituted']) assert.equal(witness[key], false);
  const cid = witness.native_CID_reference;
  assert.equal(cid.source_sha256, source);
  assert.equal(cid.proof_sha256, proof);
  assert.equal(cid.source_page, 2);
  assert.equal(cid.passed, true);
  assert.equal(cid.publication_PDF_modified, false);
  assert.equal(cid.original_font_programs_unchanged, true);
  assert.equal(cid.source_encoded_cid_hex, '28');
  assert.equal(cid.source_font_resource, '/TT2');
  assert.equal(cid.form_sha256, '10229a40fe787cd317bbd9499a8e3d95263c1a95fad542a265759d947f81e496');
  assert.equal(cid.source_Tf, 1);
  assert.deepEqual(cid.source_Tm_linear, [12,0,0,12.0774]);
  assert.equal(cid.c, '(');
  assert.equal(cid.gid, 9);
  assert.equal(cid.font, 'TimesNewRomanPSMT');
  assert.equal(cid.size, 12);
  assert.equal(cid.native_reference_dark_pixels, 85);
  assert.equal(cid.missing_native_CID_reference_pixels, 0);
  const original = witness.source_glyph, actual = witness.actual_target_glyph;
  for (const key of ['c','font','size','trace_gid','render_mode','color','opacity','linewidth','direction','stroke_color','stroke_opacity','wmode','colorspace']) assert.deepEqual(actual[key], original[key]);
  assert.equal(original.c, '('); assert.equal(original.trace_gid, 9);
  assert.equal(original.font, cid.font); assert.equal(original.size, 12);
  assert.deepEqual(original.origin, [257.8475036621094,760.8822631835938]);
  assert.deepEqual(actual.origin, [194.39556884765625,760.8822631835938]);
  assert.equal(witness.requested_dx, -63.451934814453125);
  assert.deepEqual(witness.same_integer_page_crop, [180,740,315,777]);
  const native = witness.cropped_native_CID_reference_scales;
  assert.deepEqual(Object.keys(native).sort(), ['12','4','8']);
  for (const scale of ['4','8','12']) {
    const row = native[scale];
    assert.equal(row.passed, true);
    assert.equal(row.missing_native_CID_reference_pixels, 0);
    assert.ok(row.native_reference_dark_pixels > 0);
    assert.equal(row.original_font_programs_unchanged, true);
    assert.equal(row.source_encoded_cid_hex, '28');
    assert.equal(row.source_font_resource, '/TT2');
    assert.equal(row.source_Tf, 1);
    assert.deepEqual(row.source_Tm_linear, [12,0,0,12.0774]);
  }
  for (const scale of ['8','12']) {
    assert.equal(witness.svg_reference_scales[scale].passed, true);
    assert.equal(witness.svg_reference_scales[scale].newly_missing_native_ink_pixels, 0);
  }
};

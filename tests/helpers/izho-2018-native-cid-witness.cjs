const assert = require('node:assert/strict');
module.exports = function validate(profile, witness, raw, page, item) {
  const source = '0782ab2ced4c911ce92b550aa2fd86cb7f6c9a6e24d7a60f64b13275df1e38ba';
  const pins = {
    3: {proof: '158a40a7f283452974ac1930cb41e5304bb13acf220032600023a8cb0de34f41', count: 1, gid: 887, c: '5', cid: '0377', y: 631.63, delta: 1, protected: 216, bbox: [275,627.75,275.25,628]},
    4: {proof: '6e42e9c12e1094dc5654040f5ba69445b3502349130e55eb1a7db2f8746b343d', count: 3, gid: 885, c: '3', cid: '0375', y: 124.37, delta: 2, protected: 229, bbox: [143.75,123.25,429,125.75]}
  };
  const p = pins[page.page]; assert.ok(p);
  assert.equal(item.file, 'IZhO_2018_T_KO.pdf');
  assert.equal(page.source_pdf_sha256, source); assert.equal(page.proof_sha256, p.proof);
  assert.equal(raw.protected_native_glyphs, p.protected);
  assert.equal(raw.newly_missing_native_ink_pixels, p.delta); assert.deepEqual(raw.missing_bbox, p.bbox);
  assert.equal(witness.kind, 'original-native-Cambria-digit-phase-diagnostic-v1');
  assert.equal(witness.original_language_source_sha256, source); assert.equal(witness.source_page, page.page);
  assert.equal(witness.source_base_page_sha256, raw.source_sha256);
  assert.equal(witness.proof_sha256, p.proof); assert.equal(witness.passed, true);
  assert.equal(witness.proof_unmodified, true); assert.equal(witness.delivered_pdf_modified, false); assert.equal(witness.mathematics_retyped, false);
  assert.equal(witness.source_move_qa.passed, true); assert.equal(witness.other_text_erasure.passed, true);
  const promotion = witness.original_CID_promotion;
  for (const k of ['passed','original_font_programs_unchanged','no_new_unicode_or_font_program','native_encoded_CIDs_preserved','positions_unchanged']) assert.equal(promotion[k], true);
  assert.equal(promotion.promoted_native_paints.length, p.count);
  for (const row of promotion.promoted_native_paints) {
    assert.equal(row.c,p.c); assert.equal(row.gid,p.gid); assert.equal(row.size,12); assert.equal(row.source_Tf,12);
    assert.equal(row.source_encoded_cid_hex,p.cid); assert.equal(row.source_font_resource,'/F9'); assert.deepEqual(row.source_Tm_linear,[1,0,0,1]);
  }
  assert.equal(witness.checks.length,p.count);
  for (const row of witness.checks) {
    const a=row.source,b=row.actual_destination;
    for (const k of ['c','font','size','trace_gid','render_mode','color','opacity']) assert.deepEqual(a[k],b[k]);
    assert.equal(a.c,p.c); assert.equal(a.font,'Cambria Math'); assert.equal(a.size,12); assert.equal(a.trace_gid,p.gid);
    assert.ok(Math.abs(a.origin[1]-p.y)<.005); assert.ok(Math.abs(b.origin[1]-a.origin[1])<.001);
    assert.ok(Math.abs(b.origin[0]-a.origin[0]-row.requested_dx)<.001);
  }
  const expected=[]; for (const renderer of ['MuPDF','Poppler']) for (const scale of [4,8,12]) for (let i=0;i<p.count;i++) expected.push(`${renderer}/${scale}/${i}`);
  assert.deepEqual(witness.native_CID_reference_measurements.map(r=>`${r.renderer}/${r.scale}/${r.index}`).sort(),expected.sort());
  for (const r of witness.native_CID_reference_measurements) {
    assert.ok(r.reference_deep_dark_pixels>0); assert.equal(r.missing_original_CID_pixels,0); assert.equal(r.actual_reference_nonwhite_RGB_errors,0);
  }
  const svg=[];for(let i=0;i<p.count;i++)for(const scale of [8,12])svg.push(`${i}/${scale}`);
  assert.deepEqual(witness.high_resolution_unhinted_SVG.map(r=>`${r.index}/${r.scale}`).sort(),svg.sort());
  for (const r of witness.high_resolution_unhinted_SVG) {assert.equal(r.passed,true);assert.equal(r.svg_missing,0);}
  const negative=witness.negative_actual_original_CID_omission;
  assert.equal(negative.passed,true);assert.equal(negative.native_erasure_qa.passed,true);
  assert.deepEqual(negative.checks.map(r=>r.renderer).sort(),['MuPDF','Poppler']);
  for(const r of negative.checks){assert.equal(r.rejected,true);assert.ok(r.reference_dark_pixels_missing>0);assert.equal(r.omitted_original_source_character,p.c);assert.equal(r.omitted_original_source_GID,p.gid);}
  assert.equal(profile.native_reference_nonwhite_RGB_errors,0);assert.equal(profile.original_4x_svg_dark_pixel_delta,p.delta);
};

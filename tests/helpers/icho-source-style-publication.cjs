const assert=require('node:assert/strict');
const SOURCE='959174ab5ddc8be71c251c8fe95a12c810ba730edbcbbef3b771197e32929a4a';
const PUBLISHED='78d869b01f48bd1e050f2b8697900c757f4987331b1895026173e4b3258fe024';
const APPROVED='9745a31abcc918a057a4fe2a6589003a8d6a7c2ad1c56b75ff394859352f0803';
const FREEZE='ec90c4dd31ca726e6fced818b9245ca0dc147aac9be5a1bd452e9b554989b987';
const MEASUREMENT='9f7397f1437c9c78b383d2f6624d1cee64472930f849cad6a7f972bd2625ecb4';
const CURVE='8e032abc9060b2be0a2af658cb7b1a6e2edb333aa0b7a228e40bdd60c1705799';
const MAP='ad5990b8ceb44b2dabbfc7a53ce8c344907d4b5b243f58e4e7cd88fba0dfde8a';
const SEMANTIC='bbc753360d5c243a4ca31fede8047b67b212cecea704bfae275521e82b8082e4';
const ATOM_PROFILE='60f010c33b97f27a5347f187c141dddc46e740bb3023cb98ba66f43413f5153e';
function validatePage(q,pixel,reference,qa,atom) {
  assert.equal(q.source_sha256,SOURCE);
  const g=q.new_korean_glyph_and_geometry_audit,actual=g.actual_glyphs;
  assert.equal(g.passed,true);assert.equal(g.planned_glyphs,actual);
  assert.deepEqual(g.geometry_errors,[]);assert.deepEqual(g.missing_or_notdef_glyphs,[]);
  assert.ok(g.max_position_error_pt>=0&&g.max_position_error_pt<=.001);
  assert.ok(g.position_tolerance_pt>0&&g.position_tolerance_pt<=.001);
  const a=q.actual_prose_underline_coverage_and_style_audit;
  assert.equal(a.passed,true);assert.equal(a.proof_sha256,q.output_sha256);
  assert.equal(a.page,q.page);assert.equal(a.source_sha256,SOURCE);
  assert.equal(a.measurement_code_sha256,MEASUREMENT);assert.equal(a.actual_curve_reader_sha256,CURVE);
  assert.equal(a.all_authored_glyphs_verified,actual);assert.equal(a.all_actual_curve_bboxes_match_requested_full_font_and_matrix,true);
  assert.equal(a.protected_native_ink_contact_pixels,0);assert.equal(a.authored_word_style_samples.length,actual);
  assert.ok(a.actual_shear_tangent_tolerance>0&&a.actual_shear_tangent_tolerance<=1e-9);
  for(const sample of a.authored_word_style_samples) {
    assert.ok(sample.actual_glyph.gid>0);assert.notEqual(sample.actual_glyph.c,'\ufffd');
    assert.ok(sample.actual_curve_bbox_error_pt>=0&&sample.actual_curve_bbox_error_pt<=.001);
    assert.ok(Math.abs(sample.actual_pdf_shear_tangent-sample.expected_pdf_shear_tangent)<=1e-9);
    assert.ok(Math.abs(sample.expected_pdf_shear_tangent-Math.tan(sample.authored_pdf_shear_angle*Math.PI/180))<=1e-9);
    if(sample.original_source_descriptor_ItalicAngle)assert.equal(sample.authored_pdf_shear_angle,Math.abs(sample.original_source_descriptor_ItalicAngle));
    if(sample.original_source_descriptor_ItalicAngle||/(italic|oblique|slanted)/i.test(sample.original_source_font))assert.ok(sample.authored_pdf_shear_angle>0);
  }
  const s=q.independent_source_semantic_style_audit;
  assert.equal(s.passed,true);assert.equal(s.proof_sha256,q.output_sha256);assert.equal(s.source_sha256,SOURCE);
  assert.equal(s.mapping_sha256,MAP);assert.equal(s.approved_source_clause_manifest_sha256,APPROVED);assert.equal(s.program_sha256,SEMANTIC);
  assert.equal(s.all_expected_Korean_nonspace_characters_preserved_once,actual);
  for(const key of ['all_requested_font_roles_bound_to_actual_original_source_styles','exact_original_sizes_and_raw_prose_baseline_pool_membership_preserved','no_other_bold_or_italic_changes'])assert.equal(s[key],true);
  for(const contact of q.intentional_prose_decoration_contacts||[])require('./prose-decoration-publication.cjs')(q,contact,qa);
  assert.equal(a.underline_rows.length,s.semantic_mappings.length);assert.equal(a.underline_rows.length,q.prose_vector_decorations.length);
  assert.equal(pixel.passed,true);assert.equal(pixel.proof_sha256,q.output_sha256);assert.equal(pixel.page,q.page);
  assert.equal(pixel.protected_source_sha256,SOURCE);assert.equal(pixel.reference_proof_sha256,reference);
  assert.equal(pixel.pixel_scale,2);assert.ok(pixel.anti_alias_support_pad_pt<=.5);
  assert.equal(pixel.changed_pixels_outside_named_source_rows,0);assert.equal(pixel.visible_glyph_geometry_outside_rows_exactly_equal,true);
  assert.equal(pixel.source_font_programs_images_and_image_placements_preserved,true);
  const kk=pixel.kk;assert.equal(kk.passed,true);assert.equal(kk.proof_sha256,q.output_sha256);
  assert.equal(kk.scale,2);assert.equal(kk.threshold,220);assert.equal(kk.pairs.length,kk.tested_close_row_pairs);
  for(const pair of kk.pairs)assert.equal(pair.contact_pixels_2x,0);
  const vector=q.actual_native_vector_coordinate_audit;assert.deepEqual(vector.coordinate_errors,[]);
  assert.ok(vector.max_coordinate_tolerance_pt>0&&vector.max_coordinate_tolerance_pt<=1e-7);
  if(q.page===39) {
    assert.ok(atom);assert.equal(atom.passed,true);assert.equal(atom.page,39);
    assert.equal(atom.proof_sha256,q.output_sha256);assert.equal(atom.source_sha256,SOURCE);assert.equal(atom.source_profile_sha256,ATOM_PROFILE);
    assert.equal(atom.comparison_scale,4);assert.equal(atom.actual_grayscale_pixels_different,0);assert.ok(atom.nonempty_original_native_atom_ink_pixels>0);
    assert.equal(atom.expected_image_sha256,atom.candidate_image_sha256);assert.equal(atom.source_glyph_font_size_baselines_and_both_native_graphic_programs_compared,true);
    assert.equal(atom.program_sha256,'df0a8297cf4d0ea4142f07e31d49881c0301a20656f7e883b03d4edd06634e44');
  }
}
module.exports=function validatePublication(root,qa,item,read) {
  const style=qa.source_style_correction;
  assert.equal(item.file,'IChO_2024_T_KO.pdf');assert.equal(style.schema,'icho2024-source-style-publication-v1');
  assert.equal(style.year,2024);assert.equal(style.source_sha256,SOURCE);assert.equal(style.original_published_sha256,PUBLISHED);
  const old=read(style.reference_publication.path,style.reference_publication.sha256);
  assert.equal(old.sha256,PUBLISHED);assert.equal(old.source_sha256,SOURCE);assert.equal(old.pages,62);
  assert.equal(style.freeze.sha256,FREEZE);const freeze=read(style.freeze.path,FREEZE);
  assert.equal(freeze.approved_source_clause_manifest_sha256,APPROVED);assert.equal(freeze.source_semantic_mapping_sha256,MAP);
  assert.equal(style.approved_clauses.sha256,APPROVED);read(style.approved_clauses.path,APPROVED);
  assert.equal(style.inline_atom_profile.sha256,ATOM_PROFILE);read(style.inline_atom_profile.path,ATOM_PROFILE);
  const ready=read(style.ready.path,style.ready.sha256);
  assert.equal(ready.status,'YEAR_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_ROOT_ASSEMBLY_REVIEW');
  assert.equal(ready.year,2024);assert.equal(ready.pages,62);assert.equal(ready.source.sha256,SOURCE);
  assert.equal(style.pages.length,62);assert.equal(ready.page_results.length,62);
  for(const digest of [MEASUREMENT,CURVE,SEMANTIC])assert.ok(qa.authoring_programs.some(p=>p.sha256===digest));
  let underlines=0,italics=0,edits=0;
  for(const[index,pin]of style.pages.entries()) {
    const page=qa.page_audits[index];assert.equal(pin.page,index+1);assert.equal(pin.proof_sha256,page.proof_sha256);assert.equal(pin.layout_sha256,page.qa_sha256);
    const body=read(page.qa_path,page.qa_sha256),pixel=read(pin.pixel_audit.path,pin.pixel_audit.sha256);
    const atom=pin.inline_atom_audit?read(pin.inline_atom_audit.path,pin.inline_atom_audit.sha256):undefined;
    if(atom)assert.equal(atom.layout_sha256,page.qa_sha256);
    validatePage(body,pixel,old.page_audits[index].proof_sha256,qa,atom);
    assert.equal(ready.page_results[index].proof.sha256,page.proof_sha256);assert.equal(ready.page_results[index].layout.sha256,page.qa_sha256);
    underlines+=body.independent_source_semantic_style_audit.semantic_mappings.length;
    italics+=body.independent_source_semantic_style_audit.new_Korean_italic_placements;
    edits+=body.independent_source_semantic_style_audit.exact_approved_text_edits;
  }
  assert.equal(underlines,68);assert.equal(italics,9);assert.equal(edits,52);
};
module.exports.validatePage=validatePage;

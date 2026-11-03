const assert = require('node:assert/strict');
const PUBLISHED = {
  2023:'a0dd0bc102765652ef05d3ac9f3c1c1d855980cbda601227ee0c76771be08051',
  2024:'60324d40a7432d2fff694516fb8b244c58f6d6070510bde6291da5313b0f39e0',
  2025:'754b6ecf1d74b178a279476b49ae608988f2507ddff3ffbbcf409545e52454b8',
  2026:'075b32d0a3cba93748a289dafda2e150f5de0803356c055b2b252dddf79955a6',
};
function validatePage(audit, body, year) {
  assert.ok(Object.hasOwn(PUBLISHED,year));
  assert.equal(audit.year,year);
  assert.equal(audit.passed,true);
  assert.equal(audit.page,body.page);
  assert.equal(audit.proof_sha256,body.output_sha256);
  const geometry=audit.original_full_master_geometry;
  const authored=[...body.placements,...(body.raster_labels||[])];
  const actual=authored.reduce((total,item)=>total+Array.from(item.text).filter(c=>!(/\s/u.test(c))).length,0);
  if(body.new_korean_glyph_and_geometry_audit) assert.equal(body.new_korean_glyph_and_geometry_audit.actual_glyphs,actual);
  assert.equal(geometry.passed,true);
  for (const key of ['planned_glyphs','actual_glyphs','original_full_font_gids_verified']) assert.equal(geometry[key],actual);
  assert.deepEqual(geometry.geometry_errors,[]);
  assert.deepEqual(geometry.original_full_font_gid_errors,[]);
  assert.ok(geometry.max_position_error_pt>=0 && geometry.max_position_error_pt<=.001);
  assert.ok(geometry.position_tolerance_pt>0 && geometry.position_tolerance_pt<=.001);
  assert.equal(audit.actual_outline_and_encoded_W_audit_pending,false);
  const outline=audit.actual_outline_and_encoded_W_audit;
  assert.equal(outline.passed,true);
  assert.deepEqual(outline.errors,[]);
  assert.equal(outline.actual_CID_TJ_W_glyphs_verified,actual);
  assert.equal(outline.actual_master_outline_bounds_verified,actual);
  assert.equal(outline.master_hmtx_and_gid_exact,true);
  for (const key of ['actual_W_TJ_replay_max_origin_error_pt','max_transformed_outline_error_pt']) assert.ok(outline[key]>=0 && outline[key]<=.001);
  assert.ok(outline.tolerance_pt>0 && outline.tolerance_pt<=.001);
  const authoredItalics=body.r4_source_style_corrections;
  const actualItalics=audit.actual_target_physical_shear;
  for(const authored of authoredItalics) {
    assert.equal(authored.original_descriptor_angle,-14);
    assert.equal(authored.physical_target_angle,14);
    assert.equal(authored.original_point_size_and_logical_origin_unchanged,true);
    assert.ok(actualItalics.some(actual=>Math.abs(actual.baseline-authored.baseline)<=.001));
  }
  for (const italic of actualItalics) {
    assert.ok(authoredItalics.some(authored=>Math.abs(italic.baseline-authored.baseline)<=.001));
    const tangent=italic.physical_pdf_cm_c;
    assert.ok(Number.isFinite(tangent) && tangent>0);
    assert.ok(Math.abs(tangent-Math.tan(14*Math.PI/180))<=1e-5);
  }
  const ink=audit.actual_stream_interrow_ink;
  for (const key of ['passed','all_target_KO_glyphs_accounted_for','each_extracted_row_glyph_trace_matches_target']) assert.equal(ink[key],true);
  assert.equal(ink.scale,2); assert.equal(ink.threshold,220);
  assert.equal(ink.tested_close_row_pairs,ink.pairs.length);
  for (const pair of ink.pairs) assert.equal(pair.contact_pixels_2x,0);
  const native=audit.actual_target_language_vs_native_ink;
  assert.equal(native.passed,true);
  assert.equal(native.actual_KO_vs_original_remaining_ink_contact_pixels_2x,0);
  assert.equal(native.original_font_resources_preserved_in_both_controls,true);
  const lineage=audit.current_published_complete_document_lineage;
  assert.equal(lineage.passed,true);
  assert.equal(lineage.published_document_sha256,PUBLISHED[year]);
  assert.equal(lineage.published_page_index,body.page-1);
  assert.equal(lineage.published_page_trace_exact,true);
  assert.equal(lineage.published_page_pixels_2x_exact,true);
  const expected=['P0_current_published',...([2024,2025].includes(year)?['P1_approved_intermediate']:[])];
  if(year===2026 && body.page===1) {
    expected.push('P2_precise_Tm_precontact_failed_AA_control');
    const row=audit.preexisting_AA_contact_KO_row_correction;
    assert.equal(row.baseline,683.5799560546875);assert.equal(row.dx,-.5625);
    assert.equal(row.source_size_pt,11.9552001953125);assert.equal(row.whitelist_glyphs,29);
    assert.equal(row.source_slot_id,'p1:b8:l2:s0-30');assert.equal(row.native_source_atoms_on_this_row,0);
    assert.equal(row.logical_KO_row_horizontal_translation_only,true);
    assert.equal(row.authorization_sha256,'88e28a759dafc97838cd039fc07941a31ef3cdb8d805a1c55c9c2bf36045e9c7');
    assert.equal(audit.direct_reference_comparisons.at(-1).reference_sha256,'ae1e8529fcada7735b77652d0a79a5a91164a06af3b365e480c9d1ab13b12ea1');
  }
  assert.deepEqual(audit.direct_reference_comparisons.map(r=>r.lineage),expected);
  assert.equal(audit.direct_reference_comparisons[0].reference_sha256,lineage.P0_frozen_page_sha256);
  for (const reference of audit.direct_reference_comparisons) {
    for (const key of ['passed','native_glyphs_exact','source_and_new_font_program_binaries_exact',
      'encoded_images_and_placements_exact','native_shifts_exact',
      'planned_words_point_sizes_styles_word_spaces_and_all_other_placement_fields_exact']) assert.equal(reference[key],true);
    assert.equal(reference.actual_new_glyphs_compared,actual);
    assert.equal(reference.pixel_scale,2);
    assert.equal(reference.changed_pixels_outside_explicit_glyph_union,0);
    if(reference.lineage==='P1_approved_intermediate') assert.equal(reference.approved_intermediate_titles_preserved,true);
    assert.equal(reference.title_centers.length,body.page===1 && year!==2023?4:0);
    for(const title of reference.title_centers) {
      assert.ok(Math.abs(title.error)<=.001);
      assert.ok(Math.abs(title.actual_center-title.original_center-title.error)<=1e-9);
    }
  }
  const vector=audit.actual_native_vector_coordinate_audit;
  assert.deepEqual(vector.coordinate_errors,[]);
  assert.ok(vector.max_coordinate_tolerance_pt>0 && vector.max_coordinate_tolerance_pt<=1e-7);
  assert.deepEqual(vector,body.actual_native_vector_coordinate_audit);
}
module.exports=function validatePublication(root,qa,item,read) {
  const style=qa.source_style_correction;
  assert.equal(style.schema,'ortvay-source-style-publication-v1');
  const year=Number(item.file.split('_')[1]);
  assert.equal(style.year,year);
  assert.equal(style.original_published_sha256,PUBLISHED[year]);
  assert.equal(style.source_sha256,qa.source_sha256);
  const previous=read(style.reference_publication.path,style.reference_publication.sha256);
  assert.equal(previous.sha256,PUBLISHED[year]);
  assert.equal(previous.source_sha256,qa.source_sha256);
  assert.equal(previous.pages,item.pages);
  const ready=read(style.ready.path,style.ready.sha256);
  assert.equal(ready.status,'YEAR_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_ROOT_ASSEMBLY_REVIEW');
  assert.equal(ready.year,year);assert.equal(ready.pages,item.pages);
  assert.equal(ready.source.sha256,qa.source_sha256);
  if([2023,2024,2025].includes(year)) {
    const pin=year===2025?qa.link_annotation_regression:qa.link_annotation_subset_regression;
    assert.ok(pin,'Missing fresh source-style annotation regression');
    const regression=read(pin.path,pin.sha256);
    assert.equal(regression.status,'PASS');assert.equal(regression.year,year);
    assert.equal(regression.source_sha256,qa.source_sha256);
    assert.equal(regression.ready_manifest.sha256,style.ready.sha256);
    assert.equal(regression.changed_pixels,0);
    for(const key of ['all_visible_glyph_geometry_identical','all_nonrect_annotation_settings_identical_after_save',
      'annotation_P_same_page_semantics_verified','all_annotation_rectangles_checked_after_save']) assert.equal(regression[key],true);
    for(const digest of [regression.program_sha256,regression.core_program_sha256,regression.assembler_sha256,
      ...(year===2023?[regression.aggregation_program_sha256]:[])])
      assert.ok(typeof digest==='string' && qa.authoring_programs.some(p=>p.sha256===digest),'Missing link regression program');
    assert.ok(regression.negative_regression_details.length>=({2023:18,2024:10,2025:9})[year]);
    for(const negative of regression.negative_regression_details) assert.equal(negative.rejected,true);
    const legacyName=year===2025?'test_ortvay2025_link.py':`test_ortvay${year}_link_subsets.py`;
    const legacyPins=Object.entries(regression.inputs_rehashed_after_run).filter(([file])=>file.replaceAll('\\','/').endsWith('/'+legacyName));
    assert.equal(legacyPins.length,1);
    assert.ok(qa.authoring_programs.some(p=>p.path.endsWith('/'+legacyName)&&p.sha256===legacyPins[0][1]),'Missing pinned regression input program');
    if(year===2023) {
      assert.deepEqual(regression.pages.map(row=>row.page),[1,6]);
      for(const row of regression.pages) {
        const actual=qa.page_audits[row.page-1];
        assert.equal(row.proof_sha256,actual.proof_sha256);assert.equal(row.layout_sha256,actual.qa_sha256);
      }
    } else {
      const actual=qa.page_audits[year===2024?1:9];
      assert.equal(regression.proof_sha256,actual.proof_sha256);assert.equal(regression.layout_sha256,actual.qa_sha256);
    }
  }
  assert.equal(style.pages.length,item.pages);
  assert.equal(ready.page_results.length,item.pages);
  let authoredItalicCount=0;
  for(const [index,pin]of style.pages.entries()) {
    const page=qa.page_audits[index];
    assert.equal(pin.page,index+1);
    assert.equal(pin.proof_sha256,page.proof_sha256);
    assert.equal(pin.layout_sha256,page.qa_sha256);
    const audit=read(pin.independent_audit.path,pin.independent_audit.sha256);
    const body=read(page.qa_path,page.qa_sha256);
    assert.equal(body.page,index+1);assert.equal(body.output_sha256,page.proof_sha256);
    validatePage(audit,body,year);
    authoredItalicCount+=body.r4_source_style_corrections.length;
    assert.equal(audit.current_published_complete_document_lineage.P0_frozen_page_sha256,previous.page_audits[index].proof_sha256);
    assert.equal(ready.page_results[index].proof.sha256,page.proof_sha256);
    assert.equal(ready.page_results[index].layout.sha256,page.qa_sha256);
    for(const digest of Object.values(audit.audit_code_sha256)) assert.ok(qa.authoring_programs.some(p=>p.sha256===digest),'Unfrozen independent audit dependency');
  }
  assert.equal(authoredItalicCount,({2023:22,2024:11,2025:11,2026:1})[year]);
};
module.exports.validatePage=validatePage;

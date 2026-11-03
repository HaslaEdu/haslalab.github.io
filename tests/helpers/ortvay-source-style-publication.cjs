// DRAFT D-only integration; ROOT-GO/profile/production READY binding is pending.
const assert = require('node:assert/strict');
const fullCTM = require('./ortvay-full-ctm-publication.cjs');
const PUBLISHED = {
  2023:'a0dd0bc102765652ef05d3ac9f3c1c1d855980cbda601227ee0c76771be08051',
  2024:'60324d40a7432d2fff694516fb8b244c58f6d6070510bde6291da5313b0f39e0',
  2025:'754b6ecf1d74b178a279476b49ae608988f2507ddff3ffbbcf409545e52454b8',
  2026:'075b32d0a3cba93748a289dafda2e150f5de0803356c055b2b252dddf79955a6',
};
const R4='D:/CodexBuilds/Hasla-poi-natural-20261102/layout-corrections/ortvay-title-20261103/revisions/source-style-widths-r4-20261103';
const QA=R4+'/qa-amendments/full-ctm-rotation-v1-20261103';
const PRODUCTION=R4+'/production-continuation/full-ctm-v1-20261103';
const CTM_PROFILE={
  qa_profile_freeze:[QA+'/AMENDMENT-FROZEN.json','a02844e98ef9a0e332f10312ec66a48fac5d87338e2d414c6ec24338f3c652a7'],
  qa_profile_root_go:[PRODUCTION+'/ROOT-GO.json','8f56f0f8a6db8400c0d9ee2a9b6c62026f2e50984e7b669e5e1c12f4282ea0d4'],
  qa_profile_actual_regressions:[QA+'/runs/prototype03/BATCH-RESULTS.json','13a4269f16d8697cccd951840be944fadb6cb6c206516ec71c45ba1b946f02ea'],
  qa_profile_post_freeze_guard:[QA+'/runs/frozen-guard01/p7_rotated_label/audit.json','26ff348ad46c4c38dcc61b2c4ca8176e833737ba5831f60874cb84233e2ae61d'],
  code_input_freeze:[PRODUCTION+'/CODE-INPUT-FROZEN.json','ad9b4855ac822214da7ecca0955af9abb3a1fecae4dbb33827ecb9ee59554079'],
  original_code_input_freeze:[R4+'/PREPARATION-FROZEN.json','ff8c247d3e072c9a031e7e68589958b2f3eebfb8764722dde61c5681ec46d47a'],
  original_runtime_freeze:[R4+'/PROTOTYPE-RUNTIME-FROZEN.json','27b5df6951f5ce45d390f51aa2d193bdd22c0740163846add788060e2972132b'],
};
const sourcePath=p=>require('node:path').win32.normalize(p).replaceAll('\\','/').toLowerCase();
function sameSourcePin(a,b){assert.equal(sourcePath(a.path),sourcePath(b.path));assert.equal(a.sha256,b.sha256);}
function sourceMap(value){return Object.fromEntries(Object.entries(value).map(([p,s])=>[sourcePath(p),s]));}
function validateCTMProfile(profile,qa,read){
  const canonical=Object.fromEntries(Object.entries(CTM_PROFILE).map(([k,[p,s]])=>[k,{path:p,sha256:s}]));
  const document=pin=>{
    const matches=(qa.supplemental_evidence||[]).filter(row=>row.sha256===pin.sha256);
    assert.ok(matches.length,'Missing copied mandatory CTM evidence '+pin.path);
    return read(matches[0].path,pin.sha256);
  };
  const docs={};for(const[name,pin]of Object.entries(canonical)){assert.equal(profile[name].sha256,pin.sha256,'Unapproved CTM profile '+name);docs[name]=document(profile[name]);}
  const q=docs.qa_profile_freeze,p=docs.code_input_freeze,token=docs.qa_profile_root_go,original=docs.original_runtime_freeze,prep=docs.original_code_input_freeze;
  assert.equal(q.status,'EXTERNAL_FULL_CTM_QA_PROFILE_FROZEN_AFTER_19_ACTUAL_CASES');
  assert.equal(q.production_resume_authorized,false);assert.equal(q.post_freeze_guard_confirmation_required,true);
  assert.equal(q.all19_actual_case_results_same_code_and_CASES,true);assert.equal(q.per_case_source_target_code_before_after_assertions_passed,true);
  assert.equal(q.unchanged_original_unique_files,1534);assert.equal(q.unchanged_private_inputs,597);
  assert.equal(Object.keys(q.code_sha256).length,6);assert.equal(Object.keys(q.retained_code_copies).length,6);
  const qaCode=sourceMap(q.code_sha256),prodCode={[sourcePath(PRODUCTION+'/continue_and_finalize.py')]:'baf8c139979721a1e0209b51c0a443a7f9dff24cb1be6dff5e770e2cf6c708e4'};
  assert.deepEqual(Object.keys(qaCode).map(p=>p.slice(p.lastIndexOf('/')+1)).sort(),['amended_actual_paint.py','amended_independent_qa.py','amended_outline_qa.py','make_actual_controls.py','run_amended_audit.py','transform_guard.py'].sort());
  for(const[file,digest]of Object.entries(q.code_sha256)){assert.equal(sourcePath(file.slice(0,Math.max(file.lastIndexOf('\\'),file.lastIndexOf('/')))),sourcePath(QA));assert.equal(q.retained_code_copies[file].sha256,digest);}
  assert.equal(Object.keys(q.actual_regression_inputs_sha256).length,38);
  for(const key of ['matrix_regressions','actual_control_creation','byte_identical_control_native_layout_copies'])document(q[key]);
  const cases=document({path:QA+'/CASES.json',sha256:q.cases_sha256}).cases;
  document({path:QA+'/FROZEN-BASE-SOURCES.json',sha256:q.base_sources_sha256});
  sameSourcePin(q.actual_regressions,canonical.qa_profile_actual_regressions);
  const batch=docs.qa_profile_actual_regressions;
  assert.equal(batch.passed,true);assert.equal(batch.cases,19);assert.equal(batch.positive,9);assert.equal(batch.negative,10);
  assert.deepEqual(batch.external_code_sha256,q.code_sha256);assert.equal(batch.cases_manifest_sha256,q.cases_sha256);
  assert.equal(batch.page_results.length,19);assert.equal(Object.keys(cases).length,19);assert.equal(batch.no_producer_or_publication_resume,true);
  const seen=new Set();let positive=0,negative=0;
  for(const row of batch.page_results){
    assert.ok(!seen.has(row.case));seen.add(row.case);assert.equal(row.matched_expected,true);assert.equal(row.expected,cases[row.case].expected);
    const result=document(row.result),snapshot=document(result.snapshot);
    assert.equal(result.case,row.case);assert.deepEqual(result.external_code_sha256,q.code_sha256);
    assert.deepEqual(result.target,cases[row.case].target);assert.deepEqual(result.layout,cases[row.case].layout);
    assert.deepEqual(snapshot.code_sha256,q.code_sha256);assert.equal(snapshot.case_manifest.sha256,q.cases_sha256);assert.deepEqual(snapshot.case_spec,cases[row.case]);
    if(row.expected==='PASS'){assert.equal(result.passed,true);assert.equal(result.status,'EXTERNAL_FULL_CTM_AMENDMENT_QA_PASS_NOT_PRODUCER_RESUME');positive++;}
    else{assert.equal(row.expected,'REJECT');assert.equal(result.status,'EXTERNAL_AMENDMENT_QA_REJECTED_NOT_READY');assert.equal(result.exception_type,'AssertionError');assert.ok(['original_full_master_glyph_geometry','amended_full_CTM_independent_audit'].includes(result.stage));negative++;}
  }
  assert.equal(positive,9);assert.equal(negative,10);assert.deepEqual([...seen].sort(),Object.keys(cases).sort());
  const guard=docs.qa_profile_post_freeze_guard;
  assert.equal(guard.passed,true);assert.equal(guard.year,2025);assert.equal(guard.page,7);assert.equal(guard.case,'p7_rotated_label');
  assert.deepEqual(guard.external_code_sha256,q.code_sha256);sameSourcePin(guard.external_amendment_freeze,canonical.qa_profile_freeze);
  validatePage(guard,document(guard.layout),2025,guard.layout.sha256);
  const guardSnapshot=document(guard.snapshot);sameSourcePin(guardSnapshot.external_amendment_freeze,canonical.qa_profile_freeze);assert.deepEqual(guardSnapshot.code_sha256,q.code_sha256);
  const roster=[...Array.from({length:6},(_,i)=>({year:2025,page:i+7})),...Array.from({length:10},(_,i)=>({year:2026,page:i+1}))];
  assert.equal(p.status,'R4_MIXED_LINEAGE_CONTINUATION_CODE_AND_INPUT_FROZEN');assert.deepEqual(p.allowed_pages,roster);assert.deepEqual(token.allowed_pages,roster);
  assert.equal(p.production_was_not_run,true);assert.equal(p.no_publication_tools_are_execution_dependencies,true);assert.deepEqual(sourceMap(p.code_sha256),prodCode);
  for(const name of ['qa_profile_freeze','qa_profile_actual_regressions','qa_profile_post_freeze_guard','original_code_input_freeze','original_runtime_freeze']){sameSourcePin(p[name],canonical[name]);sameSourcePin(token[name],canonical[name]);}
  assert.equal(token.status,'ROOT_GO_R4_MIXED_LINEAGE_FULL_CTM_CONTINUATION');sameSourcePin(token.code_input_freeze,canonical.code_input_freeze);
  assert.equal(token.original_producer_code_may_change,false);assert.equal(token.existing_proof_layout_ready_and_original_failure_may_change,false);
  assert.equal(Object.keys(p.preserved_files_sha256).length,241);document(p.p7_original_build_snapshot);
  assert.equal(Object.keys(original.runtime_code_sha256).length,39);assert.equal(Object.keys(original.runtime_input_sha256).length,15);
  assert.deepEqual(prep.runtime_code_sha256,original.runtime_code_sha256);assert.deepEqual(prep.runtime_input_sha256,original.runtime_input_sha256);
  const originalCode=sourceMap(original.runtime_code_sha256),additional={...qaCode,...prodCode},runtime={...originalCode,...additional};
  assert.equal(Object.keys(runtime).length,46);
  const staged=(qa.authoring_programs||[]).filter(row=>row.path.replaceAll('\\','/').includes('/authoring/source-style/'));
  assert.equal(staged.length,46);assert.equal(new Set(staged.map(row=>sourcePath(row.path))).size,46);
  for(const[file,digest]of Object.entries(runtime)){
    assert.ok(file.startsWith(sourcePath(R4)+'/'));const relative=file.slice(sourcePath(R4).length+1);
    const matches=staged.filter(row=>sourcePath(row.path).endsWith('/authoring/source-style/'+relative));
    assert.equal(matches.length,1,'Missing/ambiguous frozen runtime relative path '+relative);assert.equal(matches[0].sha256,digest);
  }
  return{profile:canonical,additional_programs:additional,external_audit_programs:qaCode,production_programs:prodCode,runtime_programs:runtime,document};
}
function validateCTMPageLineage(audit,machine,snapshot,binding,year,page){
  for(const[name,pin]of Object.entries(binding.profile)){sameSourcePin(audit[name],pin);sameSourcePin(machine[name],pin);sameSourcePin(snapshot[name],pin);}
  assert.equal(audit.status,'EXTERNAL_FULL_CTM_PRODUCTION_AUDIT_PASSED');assert.deepEqual(sourceMap(audit.qa_profile_code_sha256),binding.external_audit_programs);assert.deepEqual(sourceMap(audit.production_code_sha256),binding.production_programs);
  assert.equal(machine.qa_lineage,'external_full_ctm_v1');assert.equal(machine.year,year);assert.equal(machine.page,page);
  assert.deepEqual(sourceMap(Object.fromEntries(Object.entries(snapshot.files).map(([p,row])=>[p,row.sha256]))),binding.additional_programs);
  const core=Object.fromEntries(Object.entries(binding.runtime_programs).filter(([file])=>file.startsWith(sourcePath(R4+'/common')+'/')||file===sourcePath(R4+'/audit_final_page.py')));
  assert.deepEqual(sourceMap(audit.audit_code_sha256),{...core,...binding.additional_programs});
  sameSourcePin(machine.audit_runtime_snapshot,{path:audit.audit_runtime_snapshot,sha256:audit.audit_runtime_snapshot_sha256});
  if(year===2025&&page===7)assert.equal(audit.original_failed_audit_preserved,true);
  assert.ok(Object.hasOwn(audit,'actual_full_Tm_CTM_physical_transform_audit'));
}
function validatePage(audit, body, year, layoutSHA=null, effectivePlan=null) {
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
  const fullTransform='actual_full_Tm_CTM_physical_transform_audit';
  if(year===2025 && body.page===7) assert.ok(Object.hasOwn(audit,fullTransform),'Missing mandatory full-Tm/CTM audit for Ortvay 2025 page 7');
  if(Object.hasOwn(audit,fullTransform)) {
    assert.ok(typeof layoutSHA==='string' && /^[0-9a-f]{64}$/.test(layoutSHA),'Actual layout hash is required for full-Tm/CTM validation');
    fullCTM(audit,body,year,layoutSHA,effectivePlan);
  }
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
  let ctmBinding=null;
  if([2025,2026].includes(year)) {
    assert.equal(ready.schema,'ortvay-source-style-width-correction-ready-v2-mixed-ctm');
    ctmBinding=validateCTMProfile(style,qa,read);
    for(const[name,pin]of Object.entries(ctmBinding.profile))sameSourcePin(ready[name],pin);
  }
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
    const planDocument=read(page.effective_plan_path,page.effective_plan_sha256);
    assert.equal(page.effective_plan_sha256,body.effective_plan_sha256);
    const rawPlan=require('node:fs').readFileSync(require('node:path').resolve(root,page.effective_plan_path),'utf8');
    const effectivePlan={path:page.effective_plan_path,sha256:page.effective_plan_sha256,raw_utf8:rawPlan,document:planDocument};
    validatePage(audit,body,year,page.qa_sha256,effectivePlan);
    if(ctmBinding) {
      const source=ready.page_results[index],amended=!(year===2025&&index<6),lineage=amended?'external_full_ctm_v1':'old_frozen_r4';
      assert.equal(source.qa_lineage,lineage);assert.equal(pin.qa_lineage,lineage);assert.equal(source.reviewed,true);assert.equal(source.human_read_pending,false);
      const machine=read(pin.machine_result.path,pin.machine_result.sha256),review=read(pin.visual_review.path,pin.visual_review.sha256);
      assert.equal(source.machine_result.sha256,pin.machine_result.sha256);assert.equal(source.visual_review.sha256,pin.visual_review.sha256);
      assert.equal(machine.status,'PAGE_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_HUMAN_REVIEW');assert.equal(machine.human_read_pending,true);assert.equal(machine.year,year);assert.equal(machine.page,index+1);
      assert.equal(review.year,year);assert.equal(review.page,index+1);assert.ok(review.reviewer);assert.ok(review.passed===true||review.status==='ACTUAL_FINAL_PNG_ORIGINAL_RESOLUTION_READ_PASS');
      const artifacts=review.artifacts||review.artifact_pins;
      for(const key of ['proof','layout','png','effective_plan','independent_audit','runtime_snapshot']){sameSourcePin(machine[key],source[key]);sameSourcePin(artifacts[key],source[key]);}
      const proofDir=R4+'/'+year+'/proofs/ortvay/'+year,pdir=PRODUCTION+'/pages/'+year+'/page'+String(index+1).padStart(2,'0');
      const stem='page'+String(index+1).padStart(2,'0');
      for(const[key,suffix]of [['proof','.pdf'],['layout','.layout.json'],['effective_plan','.effective-plan.json']])assert.equal(sourcePath(source[key].path),sourcePath(proofDir+'/'+stem+suffix));
      const png=year===2025&&index<7?proofDir+'/'+stem+'.png':pdir+'/'+stem+'.png';assert.equal(sourcePath(source.png.path),sourcePath(png));
      assert.equal(sourcePath(source.machine_result.path),sourcePath(amended?pdir+'/result.json':proofDir+'/'+stem+'.result.json'));
      assert.equal(sourcePath(source.visual_review.path),sourcePath(amended?pdir+'/visual-read.json':R4+'/2025/visual-reads/'+stem+'.json'));
      if(amended) {
        assert.equal(sourcePath(source.independent_audit.path),sourcePath(pdir+'/independent-qa.json'));
        const own=ctmBinding.document(machine.production_runtime_snapshot);sameSourcePin(audit.production_runtime_snapshot,machine.production_runtime_snapshot);
        validateCTMPageLineage(audit,machine,own,ctmBinding,year,index+1);
        for(const[file,row]of Object.entries(own.files)){const folder=sourcePath(file).startsWith(sourcePath(QA)+'/')?'qa':'production';const name=sourcePath(file).slice(sourcePath(file).lastIndexOf('/')+1);assert.equal(sourcePath(row.retained_copy),sourcePath(pdir+'/runtime-sources/'+folder+'/'+name));}
      }
      for(const value of [machine.runtime_snapshot,{path:audit.audit_runtime_snapshot,sha256:audit.audit_runtime_snapshot_sha256}]) {
        const snapshot=ctmBinding.document(value);assert.equal(snapshot.schema,'r4-live-runtime-source-snapshot-v1');assert.equal(snapshot.year,year);assert.equal(snapshot.input_ledger_sha256,'500bab6a7ef21470c9e4dbf427a6046641a5603cb935c3588dee8d948e9c0656');
        const expected=Object.fromEntries(Object.entries(ctmBinding.runtime_programs).filter(([file])=>file.startsWith(sourcePath(R4+'/common')+'/')||file.startsWith(sourcePath(R4+'/'+year+'/composer')+'/')));
        assert.deepEqual(sourceMap(Object.fromEntries(Object.entries(snapshot.files).map(([file,row])=>[file,row.sha256]))),expected);
      }
    }
    authoredItalicCount+=body.r4_source_style_corrections.length;
    assert.equal(audit.current_published_complete_document_lineage.P0_frozen_page_sha256,previous.page_audits[index].proof_sha256);
    assert.equal(ready.page_results[index].proof.sha256,page.proof_sha256);
    assert.equal(ready.page_results[index].layout.sha256,page.qa_sha256);
    for(const digest of Object.values(audit.audit_code_sha256)) assert.ok(qa.authoring_programs.some(p=>p.sha256===digest),'Unfrozen independent audit dependency');
  }
  assert.equal(authoredItalicCount,({2023:22,2024:11,2025:11,2026:1})[year]);
};
module.exports.validatePage=validatePage;
module.exports.validateCTMProfile=validateCTMProfile;
module.exports.validateCTMPageLineage=validateCTMPageLineage;

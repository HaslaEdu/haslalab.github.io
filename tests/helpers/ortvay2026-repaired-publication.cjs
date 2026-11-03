'use strict';
/* D-only draft. This report contract does not authorize repair or publication. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');

const APPROVED_REPAIR_GO_SHA256='345cb2fe09b90a178c9f87176cfc7fc3307a957d8c45087359f746e01e89a730'; // Reviewed root production GO; complete actual publication evidence is still mandatory.
const R4='D:/CodexBuilds/Hasla-poi-natural-20261102/layout-corrections/ortvay-title-20261103/revisions/source-style-widths-r4-20261103';
const PRODUCTION=R4+'/production-continuation/full-ctm-v1-20261103';
const QA_PROFILE=R4+'/qa-amendments/full-ctm-rotation-v1-20261103';
const REPAIR=R4+'/page-repairs/2026-page07-postprocess-v1-20261104';
const MIXED=R4+'/mixed-year-bridges/2026-postprocess-v1-20261104';
const NUMERIC_SHA='b552b2f0cc95c1f0e8aae8bfdfc34fddae4037ce88703eca33f7fe61c914b24c';
const SOURCE_SHA='ea61fafa8228c3ed2a890e5c2f65ed8853f41d2c39e60d8b0957edfeac4dfba3';
const PUBLISHED_SHA='075b32d0a3cba93748a289dafda2e150f5de0803356c055b2b252dddf79955a6';
const FAILED_PDF_SHA='fccac3dc419fcb1bf1ee6aa3ed42d38ea1565e9416ddba3e7f7ec3e457cb169f';
const FAILED_LAYOUT_SHA='98454b83b490e8f2e42dc01b08d66b6d8788706643a9e5c31bb902e2e5783e79';
const BASE_PROFILE_KEYS=['qa_profile_freeze','qa_profile_root_go','qa_profile_actual_regressions',
  'qa_profile_post_freeze_guard','code_input_freeze','original_code_input_freeze','original_runtime_freeze'];
const AMENDMENT_KEYS=['numeric_spec','repair_freeze','repair_GO','copy_receipt','positive','negatives','postprocessor','auditor','bridge'];
const COPY_SUFFIX={proof:'.pdf',layout:'.layout.json',effective_plan:'.effective-plan.json'};
const ARTIFACTS=['proof','layout','png','independent_audit','effective_plan','runtime_snapshot'];
const PROGRAMS={postprocessor:'postprocess_page07.py',auditor:'audit_page07_repair.py',bridge:'continue_and_bridge_2026.py'};
const OLD_PAGES=[1,2,3,4,5,6,8,9,10];
const PDF_NEGATIVES=['old_failed_P1_no_shift','dx_3.1875_two_x_contact','wrong_upper_row_moved',
  'only_three_of_four_glyphs_shifted','other_KO_glyph_moved','original_native_glyph_changed','font_program_or_W_changed'];
const BINDING_NEGATIVES=['wrong_or_stale_repair_root_GO','wrong_runtime_program_sha','wrong_copy_origin_or_copy_SHA','wrong_page_origin_mapping'];
const BASELINE=421.5059509277344,SIZE=11.9552001953125,DX=3.3125,SLOT='p7:b5:l6:s0-0';
const GIDS=[9170,18350,10706,85],XREFS=[317,318,319,320];
const PDF_GUARDS={old_failed_P1_no_shift:['exact_Decimal_Tm_e_delta','verify'],'dx_3.1875_two_x_contact':['exact_Decimal_Tm_e_delta','verify'],wrong_upper_row_moved:['nonselected_effective_object_or_stream_exact','object_delta'],only_three_of_four_glyphs_shifted:['exact_Decimal_Tm_e_delta','verify'],other_KO_glyph_moved:['nonselected_effective_object_or_stream_exact','object_delta'],original_native_glyph_changed:['native_effective_object_or_stream_exact','object_delta'],font_program_or_W_changed:['font_resource_effective_object_exact','object_delta']};
const BINDING_STAGES={wrong_or_stale_repair_root_GO:['audit_page07_repair.py','validate_marker'],wrong_runtime_program_sha:['audit_page07_repair.py','validate_marker'],wrong_copy_origin_or_copy_SHA:['postprocess_page07.py','checked'],wrong_page_origin_mapping:['continue_and_bridge_2026.py','origin_row']};
const sourcePath=p=>{assert.equal(typeof p,'string');return path.win32.normalize(p).replaceAll('\\','/').toLowerCase();};
const basename=p=>sourcePath(p).split('/').at(-1);
const number=x=>{assert.equal(typeof x,'number');assert.ok(Number.isFinite(x));return x;};
const integer=(x,min=0)=>{number(x);assert.ok(Number.isInteger(x)&&x>=min);return x;};
const hash=x=>{assert.equal(typeof x,'string');assert.match(x,/^[a-f0-9]{64}$/);return x;};
const keys=(value,expected)=>assert.deepEqual(Object.keys(value).sort(),[...expected].sort());
const near=(a,b,t)=>assert.ok(Math.abs(number(a)-number(b))<=t);
function pin(value){assert.ok(value&&typeof value==='object'&&!Array.isArray(value));assert.ok(value.path);sourcePath(value.path);hash(value.sha256);assert.notEqual(value.unresolved_proposal,true);return value;}
function samePin(a,b){pin(a);pin(b);assert.equal(sourcePath(a.path),sourcePath(b.path));assert.equal(a.sha256,b.sha256);}
function sameSHA(a,b){pin(a);pin(b);assert.equal(a.sha256,b.sha256);}
function realDocument(doc){assert.ok(doc&&typeof doc==='object'&&!Array.isArray(doc));assert.equal(typeof doc.status,'string');assert.ok(doc.status&&!doc.status.startsWith('DESIGN_TEMPLATE'));assert.notEqual(doc.unresolved_proposal,true);for(const[k,v]of Object.entries(doc))if(k.endsWith('_example_only'))assert.notEqual(v,true);return doc;}
function zeroScales(rows,key){assert.ok(Array.isArray(rows));assert.equal(rows.length,3);assert.deepEqual(rows.map(v=>v.scale),[2,4,8]);for(const row of rows)assert.equal(row[key],0);}
function sourceProfile(value,binding){for(const key of BASE_PROFILE_KEYS)samePin(value[key],binding.profile[key]);}
function approvedGO(value){pin(value);assert.ok(typeof APPROVED_REPAIR_GO_SHA256==='string','Actual reviewed repair GO has not been pinned; draft cannot pass publication');assert.equal(value.sha256,APPROVED_REPAIR_GO_SHA256);}
function validateItem(item){assert.equal(item.file,'Ortvay_2026_T_KO.pdf');assert.equal(item.pages,10);}
function stagedBytes(root,relative){
  assert.equal(typeof relative,'string');assert.ok(relative&&!path.win32.isAbsolute(relative));
  const filename=path.resolve(root,relative),within=path.relative(fs.realpathSync(root),fs.realpathSync(filename));
  assert.ok(within&&!within.startsWith('..')&&!path.isAbsolute(within));return fs.readFileSync(filename);
}
function readNormalizedFile(root,qa,ready,read){
  pin(ready.visual_review_normalized);assert.ok(Array.isArray(qa.visual_review_files)&&qa.visual_review_files.length);
  const found=[];for(const filename of qa.visual_review_files){const raw=stagedBytes(root,filename);if(crypto.createHash('sha256').update(raw).digest('hex')===ready.visual_review_normalized.sha256)found.push({filename,raw});}
  assert.equal(found.length,1,'Exactly one staged visual-review file must have the raw READY-pinned SHA');
  const value=read(found[0].filename,ready.visual_review_normalized.sha256),actual=JSON.parse(found[0].raw.toString('utf8').replace(/^\uFEFF/,''));assert.deepEqual(value,actual);return value;
}
function validateNormalizedHeader(normalized,ready){
  assert.equal(ready.human_read_pending,false);assert.equal(ready.all_pages_actual_original_resolution_png_read,true);
  assert.ok(normalized&&typeof normalized==='object'&&!Array.isArray(normalized));assert.notEqual(normalized.unresolved_proposal,true);assert.ok(!String(normalized.status||'').startsWith('DESIGN_TEMPLATE'));
  for(const[k,v]of Object.entries(normalized))if(k.endsWith('_example_only'))assert.notEqual(v,true);
  assert.equal(normalized.source_sha256,SOURCE_SHA);assert.equal(normalized.year,2026);assert.ok(Array.isArray(normalized.pages));assert.equal(normalized.pages.length,10);assert.deepEqual(normalized.pages.map(v=>v.page),[1,2,3,4,5,6,7,8,9,10]);
  assert.equal(normalized.original_machine_read_body_paths_and_snapshots_unchanged,true);samePin(normalized.assembly_copy_receipt,ready.assembly_copy_receipt);
  assert.equal(sourcePath(ready.visual_review_normalized.path),sourcePath(MIXED+'/visual-review-mixed-normalized.json'));
}
function validateNormalizedRow(normalized,origin,assembly,page,manifest,receipt,body,review){
  const n=origin.page;assert.equal(normalized.page,n);assert.equal(normalized.reviewed,true);assert.equal(normalized.qa_lineage,origin.qa_lineage);
  if(n===7){assert.ok(origin.page_repair_profile&&typeof origin.page_repair_profile==='object');assert.deepEqual(normalized.page_repair_profile,origin.page_repair_profile);}else assert.ok(!Object.hasOwn(normalized,'page_repair_profile'),'Unmodified normalized rows must not claim page-repair lineage');
  assert.equal(sourcePath(normalized.proof_path),sourcePath(assembly.copied_artifacts.proof.path));assert.equal(normalized.proof_sha256,assembly.copied_artifacts.proof.sha256);assert.equal(normalized.proof_sha256,page.proof_sha256);assert.equal(normalized.proof_sha256,manifest.proof_sha256);
  assert.equal(sourcePath(normalized.layout_path),sourcePath(assembly.copied_artifacts.layout.path));assert.equal(normalized.layout_sha256,assembly.copied_artifacts.layout.sha256);assert.equal(normalized.layout_sha256,page.qa_sha256);assert.equal(normalized.layout_sha256,manifest.layout_sha256);
  // qa_path/effective_plan_path in page are staged C-relative paths. Bind their
  // hashes; preserve the original D path embedded in the unchanged body.
  assert.equal(normalized.effective_plan_sha256,assembly.copied_artifacts.effective_plan.sha256);assert.equal(normalized.effective_plan_sha256,page.effective_plan_sha256);assert.equal(normalized.effective_plan_sha256,body.effective_plan_sha256);
  assert.equal(sourcePath(normalized.effective_plan_path),sourcePath(body.effective_plan_path));samePin(normalized.assembly_effective_plan_copy,assembly.copied_artifacts.effective_plan);
  samePin(normalized.composer,origin.composer);samePin(normalized.composer,{path:body.composer_path,sha256:body.composer_sha256});assert.equal(normalized.composer_sha256,origin.composer.sha256);
  samePin(normalized.machine_result,origin.machine_result);samePin(normalized.visual_review,origin.visual_review);samePin(normalized.assembly_copy_receipt,receipt);
  keys(normalized.origin_artifacts,Object.keys(COPY_SUFFIX));for(const key of Object.keys(COPY_SUFFIX)){samePin(normalized.origin_artifacts[key],origin[key]);samePin(normalized.origin_artifacts[key],assembly.origin_artifacts[key]);}
  assert.equal(sourcePath(normalized.render_image),sourcePath(origin.png.path));assert.equal(normalized.render_image_sha256,origin.png.sha256);assert.deepEqual(normalized.review,review.notes);
}
function validateP1PixelRows(rows){zeroScales(rows,'changed_pixels_outside_exact_old_new_row_ink_union');for(const row of rows)integer(row.total_changed_pixels,1);}
function validateNegativeCase(c,document){
  assert.equal(c.rejected,true);assert.ok(c.actual_error&&typeof c.actual_error==='object'&&!Array.isArray(c.actual_error));keys(c.actual_error,['exception_type','message','stage']);const e=c.actual_error;
  assert.equal(e.exception_type,'AssertionError');assert.ok(typeof e.message==='string'&&e.message.trim());assert.equal(typeof e.stage,'string');
  let file,fn;if(Object.hasOwn(PDF_GUARDS,c.name)){
    assert.equal(c.binding_only,false);const[guard,functionName]=PDF_GUARDS[c.name];assert.equal(c.expected_guard,guard);file='audit_page07_repair.py';fn=functionName;
    pin(c.candidate_proof);pin(c.candidate_layout);assert.equal(c.fresh_layout_output_sha_matches_candidate_pdf,true);
    const layout=document(c.candidate_layout);assert.ok(layout&&typeof layout==='object');assert.notEqual(layout.unresolved_proposal,true);assert.equal(layout.output_sha256,c.candidate_proof.sha256,'Fresh staged candidate layout must bind the actual candidate PDF SHA');
    if(fn==='verify')assert.equal(e.message,'Exact approved Decimal Tm e delta required');
    if(c.name==='original_native_glyph_changed'){
      assert.ok(typeof c.actual_mutation==='string'&&c.actual_mutation);const details=c.mutation_details;integer(details.native_stream_xref,1);assert.equal(details.inside_actual_selected_row_mask_pixel_8x.length,2);for(const x of details.inside_actual_selected_row_mask_pixel_8x)integer(x);assert.ok(number(details.original_row_pixel_intensity)>=0&&details.original_row_pixel_intensity<220);
    }
  }else{
    assert.ok(Object.hasOwn(BINDING_STAGES,c.name),'Unapproved negative control name');assert.equal(c.binding_only,true);assert.equal(c.expected_guard,c.name);[file,fn]=BINDING_STAGES[c.name];
    for(const key of['candidate_proof','candidate_layout','fresh_layout_output_sha_matches_candidate_pdf'])assert.ok(!Object.hasOwn(c,key),'Metadata-only binding control cannot claim a PDF candidate');
  }
  const prefix=file+':'+fn+':';assert.ok(e.stage.startsWith(prefix),'Wrong rejection stage for '+c.name);assert.match(e.stage.slice(prefix.length),/^[1-9][0-9]*$/);
}
function validateNegativeCases(cases,document){
  const names=[...PDF_NEGATIVES,...BINDING_NEGATIVES];assert.ok(Array.isArray(cases));assert.equal(cases.length,11);assert.deepEqual(cases.map(v=>v.name).sort(),names.sort());
  for(const c of cases)validateNegativeCase(c,document);
}
function validateNativeReadonlyReplay(replay,proof,layout,nativeAudit,binding,document,context){
  assert.ok(replay&&typeof replay==='object');assert.equal(replay.passed,true);samePin(replay.input_pdf,proof);samePin(replay.input_layout,layout);samePin(replay.input_pdf_after,proof);samePin(replay.input_layout_after,layout);
  for(const k of['scratch_pdf','scratch_layout_input','scratch_layout_after','frozen_verifier_program','receipt'])pin(replay[k]);
  for(const k of['scratch_pdf_byte_identical_to_input','all_other_layout_fields_exact','frozen_native_math_and_tolerances_unchanged'])assert.equal(replay[k],true);
  assert.equal(replay.only_refreshed_semantic_field,'actual_native_vector_coordinate_audit');sameSHA(replay.scratch_pdf,proof);sameSHA(replay.scratch_layout_input,layout);
  assert.ok(['positive','candidate'].includes(context));const folder=sourcePath(replay.scratch_pdf.path).slice(0,-'/page07.pdf'.length);
  const prefix=sourcePath(REPAIR+'/audit-scratch/'+context+'-'+proof.sha256.slice(0,12)+'-');assert.ok(folder.startsWith(prefix));assert.match(folder.slice(prefix.length),/^[a-f0-9]{32}$/);
  for(const[k,name]of[['scratch_pdf','page07.pdf'],['scratch_layout_input','page07.layout.input.json'],['scratch_layout_after','page07.layout.json'],['receipt','NATIVE-REPLAY.json']])assert.equal(sourcePath(replay[k].path),folder+'/'+name.toLowerCase());
  const verifier=pin(replay.frozen_verifier_program);assert.equal(sourcePath(verifier.path),sourcePath(R4+'/2026/composer/verify_native_vectors.py'));assert.equal(verifier.sha256,binding.runtime_programs[sourcePath(verifier.path)]);
  const input=document(replay.input_layout),retained=document(replay.scratch_layout_input),after=document(replay.scratch_layout_after);assert.deepEqual(retained,input);
  const fresh=after.actual_native_vector_coordinate_audit;assert.ok(fresh&&typeof fresh==='object');assert.equal(fresh.audit_code_sha256,verifier.sha256);assert.deepEqual(fresh.coordinate_errors,[]);assert.ok(number(fresh.max_coordinate_tolerance_pt)>0&&fresh.max_coordinate_tolerance_pt<=1e-7);
  if(nativeAudit!==null)assert.deepEqual(fresh,nativeAudit);
  const expected=structuredClone(input);expected.actual_native_vector_coordinate_audit=fresh;assert.deepEqual(after,expected,'Native scratch refresh changed a second semantic field');
  const base=structuredClone(replay);delete base.receipt;assert.deepEqual(document(replay.receipt),base);return fresh;
}
function validateValidCandidateControl(control,negatives,profile,positive,binding,document,origin){
  realDocument(control);assert.equal(control.status,'VALID_CANDIDATE_FULL_AUDIT_PASS_INPUTS_AND_POSITIVE_TREE_UNCHANGED');assert.equal(control.passed,true);assert.equal(control.candidate_core_passed,true);
  keys(control.before,['proof','layout']);keys(control.after,['proof','layout']);for(const k of['proof','layout'])samePin(control.before[k],control.after[k]);
  assert.equal(sourcePath(control.before.proof.path),sourcePath(REPAIR+'/regressions/valid-candidate-read-only/page07.pdf'));assert.equal(sourcePath(control.before.layout.path),sourcePath(REPAIR+'/regressions/valid-candidate-read-only/page07.layout.json'));
  sameSHA(control.before.proof,positive.proof);sameSHA(control.before.layout,positive.layout);samePin(control.repair_code_input_freeze,profile.repair_code_input_freeze);
  const auditor=profile.additional_runtime_files.filter(p=>basename(p.path)===PROGRAMS.auditor);assert.equal(auditor.length,1);samePin(control.program,auditor[0]);
  assert.deepEqual(control.positive_tree_sha256_before,control.positive_tree_sha256_after);assert.deepEqual(control.positive_tree_sha256_before,negatives.positive_files_rehashed_unchanged);
  const tree=Object.fromEntries(Object.entries(control.positive_tree_sha256_before).map(([p,s])=>[sourcePath(p),hash(s)]));assert.ok(Object.keys(tree).length);
  const directory=REPAIR+'/page07',inventory=['page07.pdf','page07.layout.json','page07.authoring-draft.json','page07.effective-plan.json','page07.png','independent-qa.json','postprocess-receipt.json','repair-runtime-snapshot.json',...Object.values(PROGRAMS).map(n=>'runtime-sources/additional/'+n)];
  assert.deepEqual(Object.keys(tree).sort(),inventory.map(n=>sourcePath(directory+'/'+n)).sort(),'Phase03 positive inventory must contain all11 files exactly');
  assert.equal(origin.page,7);samePin(origin.proof,positive.proof);samePin(origin.layout,positive.layout);samePin(origin.independent_audit,profile.actual_positive);
  for(const p of[positive.proof,positive.layout,profile.actual_positive,origin.effective_plan,origin.png,profile.repair_runtime_snapshot])assert.equal(tree[sourcePath(p.path)],p.sha256);
  assert.equal(tree[sourcePath(directory+'/page07.authoring-draft.json')],positive.layout.sha256);
  const runtime=document(profile.repair_runtime_snapshot);assert.equal(Object.keys(runtime.files).length,3);
  for(const program of profile.additional_runtime_files){
    const entries=Object.entries(runtime.files).filter(([p])=>sourcePath(p)===sourcePath(program.path));assert.equal(entries.length,1);const value=entries[0][1];assert.equal(value.sha256,program.sha256);
    assert.equal(sourcePath(value.retained_copy),sourcePath(directory+'/runtime-sources/additional/'+basename(program.path)));assert.equal(tree[sourcePath(value.retained_copy)],program.sha256);
  }
  const receipt=document({path:directory+'/postprocess-receipt.json',sha256:tree[sourcePath(directory+'/postprocess-receipt.json')]});assert.equal(receipt.schema,'ortvay-page07-postprocess-receipt-v1');assert.equal(receipt.status,'PDF_CREATED_IN_NEW_DIRECTORY_INDEPENDENT_AUDIT_PENDING');
  samePin(receipt.proof,positive.proof);samePin(receipt.base_failed_proof,profile.base_failed_proof);samePin(receipt.base_failed_layout,profile.base_failed_layout);samePin(receipt.numeric_spec,profile.numeric_spec);samePin(receipt.repair_runtime_snapshot,profile.repair_runtime_snapshot);assert.equal(receipt.original_file_prefix_exact,true);
  assert.equal(sourcePath(receipt.draft_layout.path),sourcePath(directory+'/page07.authoring-draft.json'));assert.equal(receipt.draft_layout.sha256,tree[sourcePath(receipt.draft_layout.path)]);
  const draft=document(receipt.draft_layout),marker=draft.r4_page07_exact_row_postprocess,post=profile.additional_runtime_files.filter(p=>basename(p.path)===PROGRAMS.postprocessor);assert.equal(post.length,1);samePin(marker.postprocessor,post[0]);
  for(const key of['numeric_spec','repair_code_input_freeze','root_GO','base_failed_proof','base_failed_layout','repair_runtime_snapshot'])samePin(marker[key],profile[key]);
  assert.deepEqual(receipt.changed_streams.map(v=>v.xref),XREFS);for(const r of receipt.changed_streams){const observed=positive.decoded_object_and_stream_preservation.selected_streams.filter(v=>v.xref===r.xref);assert.equal(observed.length,1);assert.equal(r.before_sha256,observed[0].before_sha256);assert.equal(r.after_sha256,observed[0].after_sha256);}
  const fresh=document(control.before.layout);assert.equal(fresh.output_sha256,control.before.proof.sha256);
  validateNativeReadonlyReplay(control.native_vector_readonly_replay,control.before.proof,control.before.layout,null,binding,document,'candidate');
}
function validateRepairFreeze(freeze,profile,binding){
  realDocument(freeze);assert.equal(freeze.schema,'ortvay-2026-page07-repair-code-input-freeze-v1');assert.equal(freeze.production_authorized,false);sourceProfile(freeze.base_profile,binding);
  assert.deepEqual(freeze.base_runtime_counts,{original:39,QA:6,production:1,total:46});
  const code=Object.fromEntries(Object.entries(freeze.base_runtime_programs).map(([p,s])=>[sourcePath(p),hash(s)]));assert.deepEqual(code,binding.runtime_programs);
  samePin(freeze.numeric_spec,profile.numeric_spec);assert.deepEqual(freeze.additional_runtime_files,profile.additional_runtime_files);
  assert.equal(sourcePath(freeze.permitted_output_directory),sourcePath(REPAIR+'/page07'));assert.equal(sourcePath(freeze.mixed_bridge_directory),sourcePath(MIXED));
  assert.equal(freeze.existing_source_or_runtime_programs_may_change,false);assert.equal(freeze.original_proofs_or_global_lifecycle_may_change,false);
  assert.deepEqual(freeze.allowed_operation,{year:2026,page:7,slot_id:SLOT,text:'논하라.',baseline:BASELINE,point_size:SIZE,dx:DX,
    selected_original_stream_xrefs:XREFS,only_four_original_KO_Tm_e_operands_may_change:true,all_other_failed_P1_actual_glyphs_including_spaces_and_effective_objects_exact:true});
}
function numericSpec(value){
  realDocument(value);assert.equal(value.status,'ROOT_APPROVED_EXACT_NUMERIC_REPAIR_SPEC_NOT_PRODUCTION_GO');
  assert.equal(value.year,2026);assert.equal(value.page,7);assert.equal(value.selected_slot_id,SLOT);assert.equal(value.selected_text,'논하라.');
  assert.equal(value.selected_baseline,BASELINE);assert.equal(value.source_size_pt,SIZE);assert.equal(value.dx,DX);assert.equal(value.angle,0);
  assert.deepEqual(value.fixed_scales,[2,4,8]);assert.equal(value.fixed_KO_threshold,220);assert.equal(value.fixed_native_threshold,180);
  assert.equal(value.production_repair_authorized,false);assert.deepEqual(value.source_column,[73.541015625,124.33867645263672]);
  assert.equal(value.precontact_proof.sha256,FAILED_PDF_SHA);assert.equal(value.precontact_layout.sha256,FAILED_LAYOUT_SHA);
  assert.deepEqual(value.selected_actual_trial.actual_master_trace.map(g=>g.gid),GIDS);
  return value;
}
function validateRepairedBody(previous,body,spec,proofSHA,profile){
  const expected=structuredClone(previous),selected=expected.placements.filter(p=>Math.abs(p.baseline-BASELINE)<.001);
  assert.deepEqual(selected,[spec.old_logical_placement]);const row=selected[0];
  for(const field of['point','draw_point'])if(Object.hasOwn(row,field))row[field][0]+=DX;
  const lines=expected.line_reports.filter(v=>Math.abs(v.baseline-BASELINE)<.001);assert.equal(lines.length,1);
  assert.ok(lines[0].tokens.every(t=>t.kind==='prose'));lines[0].left+=DX;lines[0].right+=DX;for(const t of lines[0].tokens)t.new_x+=DX;
  expected.output_sha256=hash(proofSHA);const actual=structuredClone(body),extra=actual.r4_page07_exact_row_postprocess;delete actual.r4_page07_exact_row_postprocess;
  assert.deepEqual(actual,expected,'Only the approved row x fields, proof SHA and typed repair lineage may change');
  assert.equal(extra.schema,'ortvay-page07-exact-row-postprocess-v1');assert.equal(extra.slot_id,SLOT);assert.equal(extra.baseline,BASELINE);assert.equal(extra.point_size,SIZE);assert.equal(extra.dx,DX);
  assert.deepEqual(extra.selected_stream_xrefs,XREFS);assert.equal(extra.original_composer_is_base_provenance,true);assert.equal(extra.inherited_QA_claims_require_fresh_independent_revalidation,true);
  for(const key of['numeric_spec','repair_code_input_freeze','root_GO','base_failed_proof','base_failed_layout','repair_runtime_snapshot'])samePin(extra[key],profile[key]);
  const post=profile.additional_runtime_files.filter(p=>basename(p.path)===PROGRAMS.postprocessor);assert.equal(post.length,1);samePin(extra.postprocessor,post[0]);
  assert.ok(row.point[0]>=spec.source_column[0]&&row.point[0]+row.advance<=spec.source_column[1]);return extra;
}
function validateOriginalRuntime(snapshot,binding){
  assert.equal(snapshot.schema,'r4-live-runtime-source-snapshot-v1');assert.equal(snapshot.year,2026);
  assert.equal(snapshot.input_ledger_sha256,'500bab6a7ef21470c9e4dbf427a6046641a5603cb935c3588dee8d948e9c0656');
  const observed=Object.fromEntries(Object.entries(snapshot.files).map(([file,row])=>[sourcePath(file),hash(row.sha256)]));
  const expected=Object.fromEntries(Object.entries(binding.runtime_programs).filter(([file])=>file.startsWith(sourcePath(R4+'/common')+'/')||file.startsWith(sourcePath(R4+'/2026/composer')+'/')));
  assert.deepEqual(observed,expected);for(const row of Object.values(snapshot.files))assert.ok(typeof row.retained_copy==='string');
}
function validateOriginalOrigin(meta,oldStyle){
  const{origin,machine,review,audit,body,own,buildSnapshot,auditSnapshot,binding,effectivePlan}=meta;
  const n=integer(origin.page,1);assert.ok(OLD_PAGES.includes(n));assert.equal(origin.qa_lineage,'external_full_ctm_v1');assert.equal(origin.reviewed,true);assert.equal(origin.human_read_pending,false);
  assert.equal(machine.status,'PAGE_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_HUMAN_REVIEW');assert.equal(machine.year,2026);assert.equal(machine.page,n);assert.equal(machine.human_read_pending,true);
  assert.equal(review.status,'ACTUAL_FINAL_PNG_ORIGINAL_RESOLUTION_READ_PASS');assert.equal(review.year,2026);assert.equal(review.page,n);assert.ok(typeof review.reviewer==='string'&&review.reviewer);
  const artifacts=review.artifacts||review.artifact_pins;for(const key of ARTIFACTS){samePin(machine[key],origin[key]);samePin(artifacts[key],origin[key]);if(review.artifacts&&review.artifact_pins)samePin(review.artifacts[key],review.artifact_pins[key]);}
  samePin(review.machine_result,origin.machine_result);assert.equal(body.page,n);assert.equal(body.source_sha256,SOURCE_SHA);assert.equal(body.output_sha256,origin.proof.sha256);
  samePin(review.composer,{path:body.composer_path,sha256:body.composer_sha256});assert.equal(binding.runtime_programs[sourcePath(body.composer_path)],body.composer_sha256);
  samePin(audit.target,origin.proof);samePin(audit.layout,origin.layout);samePin(machine.production_runtime_snapshot,origin.production_runtime_snapshot);samePin(audit.production_runtime_snapshot,machine.production_runtime_snapshot);
  samePin(machine.audit_runtime_snapshot,origin.audit_runtime_snapshot);samePin(machine.audit_runtime_snapshot,{path:audit.audit_runtime_snapshot,sha256:audit.audit_runtime_snapshot_sha256});
  const stem='page'+String(n).padStart(2,'0'),pdir=PRODUCTION+'/pages/2026/'+stem,proofdir=R4+'/2026/proofs/ortvay/2026';
  for(const[key,suffix]of Object.entries(COPY_SUFFIX))assert.equal(sourcePath(origin[key].path),sourcePath(proofdir+'/'+stem+suffix));
  for(const[key,file]of[['png',stem+'.png'],['independent_audit','independent-qa.json'],['machine_result','result.json'],['visual_review','visual-read.json'],['production_runtime_snapshot','production-runtime-snapshot.json']])assert.equal(sourcePath(origin[key].path),sourcePath(pdir+'/'+file));
  sourceProfile(origin,binding);oldStyle.validateCTMPageLineage(audit,machine,own,binding,2026,n);
  for(const[file,row]of Object.entries(own.files)){const folder=sourcePath(file).startsWith(sourcePath(QA_PROFILE)+'/')?'qa':'production';assert.equal(sourcePath(row.retained_copy),sourcePath(pdir+'/runtime-sources/'+folder+'/'+basename(file)));}
  validateOriginalRuntime(buildSnapshot,binding);validateOriginalRuntime(auditSnapshot,binding);
  oldStyle.validatePage(audit,body,2026,origin.layout.sha256,effectivePlan);
  return{status:'ORIGINAL_PAGE_METADATA_CONTRACT_PASS_NOT_PUBLICATION_AUTHORIZATION',page:n};
}
function validateCopyReceipt(receipt,ready,style,qa){
  realDocument(receipt);assert.equal(receipt.schema,'ortvay-mixed-origin-proof-copy-receipt-v1');assert.equal(receipt.status,'ALL10_ORIGIN_TO_ASSEMBLY_COPIES_BYTE_IDENTICAL');
  assert.equal(receipt.year,2026);assert.equal(receipt.pages,10);assert.equal(receipt.body_embedded_paths_rewritten,false);assert.equal(sourcePath(receipt.assembly_proof_dir),sourcePath(MIXED+'/proofs'));
  assert.equal(sourcePath(ready.assembly_proof_dir),sourcePath(MIXED+'/proofs'));assert.equal(receipt.copies.length,30);if(Object.hasOwn(receipt,'expected_copy_records'))assert.equal(receipt.expected_copy_records,30);
  for(const values of[ready.page_results,ready.assembly_page_results,style.pages,qa.page_audits])assert.equal(values.length,10);
  const seen=new Set();for(const row of receipt.copies){assert.ok(Number.isInteger(row.page)&&row.page>=1&&row.page<=10);assert.ok(Object.hasOwn(COPY_SUFFIX,row.key));const key=row.page+':'+row.key;assert.ok(!seen.has(key));seen.add(key);}
  for(let i=0;i<10;i++){
    const origin=ready.page_results[i],assembly=ready.assembly_page_results[i],manifest=style.pages[i],page=qa.page_audits[i],n=i+1,stem='page'+String(n).padStart(2,'0');
    for(const x of[origin,assembly,manifest,page])assert.equal(x.page,n);
    for(const x of[manifest.origin_artifacts,manifest.assembly_artifacts,assembly.origin_artifacts,assembly.copied_artifacts])keys(x,Object.keys(COPY_SUFFIX));
    assert.equal(assembly.historical_body_paths_rewritten,false);samePin(assembly.copy_receipt,ready.assembly_copy_receipt);
    for(const[key,suffix]of Object.entries(COPY_SUFFIX)){
      const before=pin(origin[key]),after=pin(assembly.copied_artifacts[key]);samePin(assembly.origin_artifacts[key],before);samePin(manifest.origin_artifacts[key],before);samePin(manifest.assembly_artifacts[key],after);
      const originDir=n===7?REPAIR+'/page07':R4+'/2026/proofs/ortvay/2026';assert.equal(sourcePath(before.path),sourcePath(originDir+'/'+stem+suffix));assert.equal(sourcePath(after.path),sourcePath(MIXED+'/proofs/'+stem+suffix));assert.equal(before.sha256,after.sha256);
      const rows=receipt.copies.filter(r=>r.page===n&&r.key===key);assert.equal(rows.length,1);const r=rows[0];assert.equal(r.byte_equal,true);integer(r.bytes,1);samePin(r.origin,before);samePin(r.copied,after);samePin(r.origin_machine,origin.machine_result);samePin(r.origin_visual_read,origin.visual_review);
      for(const p of[before,after])if(Object.hasOwn(p,'bytes'))assert.equal(p.bytes,r.bytes);
      const digest={proof:'proof_sha256',layout:'qa_sha256',effective_plan:'effective_plan_sha256'}[key];assert.equal(page[digest],after.sha256);
    }
    assert.equal(sourcePath(page.proof_path),sourcePath(assembly.copied_artifacts.proof.path));assert.equal(manifest.proof_sha256,page.proof_sha256);assert.equal(manifest.layout_sha256,page.qa_sha256);
  }
  return{status:'COPY_RECEIPT_METADATA_CONTRACT_PASS_NOT_PUBLICATION_AUTHORIZATION',copies:30};
}
function validateRepairAudit(audit,body,spec,profile,positivePin,origin,previous,previousPublication,fullCTM,effectivePlan,binding,document){
  realDocument(audit);assert.equal(audit.schema,'ortvay-2026-page07-additive-repair-audit-v1');assert.equal(audit.status,'PAGE07_ADDITIVE_REPAIR_ALL_STRICT_CHECKS_PASS');assert.equal(audit.passed,true);assert.equal(audit.year,2026);assert.equal(audit.page,7);
  samePin(audit.numeric_spec,profile.numeric_spec);samePin(audit.repair_code_input_freeze,profile.repair_code_input_freeze);samePin(audit.root_GO,profile.root_GO);samePin(audit.base_failed_proof,profile.base_failed_proof);samePin(audit.base_failed_layout,profile.base_failed_layout);
  assert.equal(audit.proof_sha256,body.output_sha256);samePin(audit.target,audit.proof);samePin(audit.proof,origin.proof);samePin(audit.layout,origin.layout);assert.equal(audit.proof.sha256,body.output_sha256);
  assert.equal(positivePin.sha256,profile.actual_positive.sha256);
  const auditor=profile.additional_runtime_files.filter(p=>basename(p.path)===PROGRAMS.auditor);assert.equal(auditor.length,1);samePin(audit.auditor_program,auditor[0]);
  fullCTM(audit,body,2026,origin.layout.sha256,effectivePlan);
  const special=audit.actual_stream_interrow_ink.corrected_special_pair_multiscale.filter(p=>Math.abs(p.upper_baseline-410.8339538574219)<.001&&Math.abs(p.lower_baseline-BASELINE)<.001);assert.equal(special.length,1);assert.deepEqual(special[0].contact_pixels_by_scale,{'2':0,'4':0,'8':0});
  const nativeInk=audit.actual_target_language_vs_native_ink;assert.equal(nativeInk.KO_threshold,220);assert.equal(nativeInk.native_threshold,180);assert.deepEqual(nativeInk.contact_pixels_by_scale,{'2':0,'4':0,'8':0});zeroScales(nativeInk.fixed_multiscale_native_contact,'contact_pixels');for(const p of nativeInk.fixed_multiscale_native_contact)assert.equal(p.threshold,180);
  const p1=audit.P1_failed_exact_delta_comparison;assert.equal(p1.passed,true);samePin(p1.reference_proof,profile.base_failed_proof);samePin(p1.reference_layout,profile.base_failed_layout);
  integer(p1.all_visible_glyphs_including_spaces,539);assert.equal(p1.selected_new_KO_glyphs,4);assert.equal(p1.nonselected_new_KO_glyphs_including_spaces,535);assert.deepEqual(p1.selected_GIDs,GIDS);assert.equal(p1.exact_decimal_Tm_e_delta,'3.3125');
  for(const k of['nonselected_glyph_attributes_bit_exact','original_native_glyphs_bit_exact','selected_y_size_font_GID_color_opacity_paint_direction_exact'])assert.equal(p1[k],true);
  assert.ok(number(p1.max_actual_selected_dx_residual_pt)>=0&&p1.max_actual_selected_dx_residual_pt<=.001);validateP1PixelRows(p1.pixel_union_by_scale);
  const d=audit.decoded_object_and_stream_preservation;assert.equal(d.passed,true);assert.equal(d.selected_stream_count,4);assert.equal(d.selected_streams.length,4);assert.deepEqual(d.selected_streams.map(v=>v.xref).sort((a,b)=>a-b),XREFS);
  for(const k of['original_PDF_prefix_exact','all_other_effective_objects_exact','all_other_raw_and_decoded_streams_exact','font_programs_and_encoded_images_exact','extra_structural_xref_objects_only'])assert.equal(d[k],true);
  integer(d.unchanged_effective_objects,1);integer(d.unchanged_streams,1);
  for(const stream of d.selected_streams){hash(stream.before_sha256);hash(stream.after_sha256);assert.notEqual(stream.before_sha256,stream.after_sha256);assert.equal(stream.exact_decimal_Tm_e_delta,'3.3125');assert.equal(stream.all_other_decoded_bytes_identical,true);}
  const p0=audit.P0_inherited_W_precision_plus_exact_repair_union_comparison;assert.equal(p0.passed,true);samePin(p0.failed_P1,profile.base_failed_proof);samePin(p0.target,audit.proof);assert.equal(p0.P0.sha256,previousPublication.page_audits[6].proof_sha256);assert.equal(p0.P0_origin_bit_exact_claimed,false);assert.equal(p0.native_fonts_images_exact,true);
  // This aggregate P0 mask covers all actual KO ink. The exact repair scope is
  // independently restricted by the failed-P1 glyph/object and row-ink checks.
  assert.equal(p0.actual_pixel_mask_scope,'all_actual_P0_and_target_KO_stream_RGB_ink_support');assert.equal(p0.exact_exception_mask_claimed,false);
  assert.deepEqual(p0.change_scope_independently_restricted_by,['unmodified_P0_to_failed_P1_reference_contract','exact_failed_P1_to_target_four_glyph_and_object_contract']);
  zeroScales(p0.pixel_union_by_scale,'changed_pixels_outside_actual_P0_target_all_KO_ink_support');
  const base=p0.inherited_base_comparison;assert.equal(base.passed,true);assert.equal(base.lineage,'P0_current_published');assert.equal(base.reference_sha256,p0.P0.sha256);assert.equal(base.pixel_scale,2);assert.equal(base.changed_pixels_outside_explicit_glyph_union,0);
  for(const k of['native_glyphs_exact','source_and_new_font_program_binaries_exact','encoded_images_and_placements_exact','native_shifts_exact','planned_words_point_sizes_styles_word_spaces_and_all_other_placement_fields_exact'])assert.equal(base[k],true);
  const native=audit.actual_native_vector_coordinate_audit;assert.deepEqual(native.coordinate_errors,[]);assert.ok(number(native.max_coordinate_tolerance_pt)>0&&native.max_coordinate_tolerance_pt<=1e-7);assert.deepEqual(native,body.actual_native_vector_coordinate_audit);
  validateNativeReadonlyReplay(audit.native_vector_readonly_replay,origin.proof,origin.layout,native,binding,document,'positive');
  validateRepairedBody(previous,body,spec,body.output_sha256,profile);
}

function createValidator(dependencies={}){
  const oldStyle=dependencies.oldStyle||require('./ortvay-source-style-publication.cjs');
  const fullCTM=dependencies.fullCTM||require('./ortvay-full-ctm-publication.cjs');
  function validatePublication(root,qa,item,read){
    const style=qa.source_style_correction;assert.equal(style.schema,'ortvay2026-source-style-page-repair-publication-v1');assert.equal(style.year,2026);validateItem(item);
    assert.equal(style.source_sha256,SOURCE_SHA);assert.equal(qa.source_sha256,SOURCE_SHA);assert.equal(style.original_published_sha256,PUBLISHED_SHA);keys(style.qa_amendment,AMENDMENT_KEYS);
    for(const v of Object.values(style.qa_amendment))pin(v);approvedGO(style.qa_amendment.repair_GO);
    const previous=read(style.reference_publication.path,style.reference_publication.sha256);assert.equal(previous.sha256,PUBLISHED_SHA);assert.equal(previous.source_sha256,SOURCE_SHA);assert.equal(previous.pages,10);
    const ready=realDocument(read(style.ready.path,style.ready.sha256));assert.equal(ready.schema,'ortvay-source-style-width-correction-ready-v3-mixed-ctm-page-repair');assert.equal(ready.status,'YEAR_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_ROOT_ASSEMBLY_REVIEW');assert.equal(ready.year,2026);assert.equal(ready.pages,10);assert.equal(ready.source.sha256,SOURCE_SHA);
    const binding=oldStyle.validateCTMProfile(style,qa,read);sourceProfile(ready,binding);sourceProfile(ready.base_profile,binding);assert.equal(ready.base_profile_runtime_count,46);
    const document=value=>{pin(value);const matches=(qa.supplemental_evidence||[]).filter(v=>v.sha256===value.sha256);assert.ok(matches.length,'Missing copied JSON evidence '+value.path);const documents=matches.map(v=>read(v.path,v.sha256));for(const v of documents.slice(1))assert.deepEqual(v,documents[0]);return documents[0];};
    const stagedJSON=value=>{pin(value);assert.ok((qa.supplemental_evidence||[]).some(v=>v.path===value.path&&v.sha256===value.sha256),'Mandatory repair JSON was not staged as supplemental evidence');return realDocument(read(value.path,value.sha256));};
    const docs=Object.fromEntries(AMENDMENT_KEYS.slice(0,6).map(k=>[k,stagedJSON(style.qa_amendment[k])]));
    assert.equal(style.qa_amendment.numeric_spec.sha256,NUMERIC_SHA);const spec=numericSpec(docs.numeric_spec),profile=ready.page_repair_profile;
    assert.equal(profile.schema,'ortvay-one-page-postprocess-profile-v1');assert.equal(profile.year,2026);assert.equal(profile.page,7);
    for(const[k,p]of Object.entries({numeric_spec:profile.numeric_spec,repair_freeze:profile.repair_code_input_freeze,repair_GO:profile.root_GO,positive:profile.actual_positive,negatives:profile.actual_negative_regressions,copy_receipt:ready.assembly_copy_receipt}))sameSHA(style.qa_amendment[k],p);
    assert.equal(profile.base_failed_proof.sha256,FAILED_PDF_SHA);assert.equal(profile.base_failed_layout.sha256,FAILED_LAYOUT_SHA);
    assert.equal(sourcePath(profile.base_failed_proof.path),sourcePath(R4+'/2026/proofs/ortvay/2026/page07.pdf'));assert.equal(sourcePath(profile.base_failed_layout.path),sourcePath(R4+'/2026/proofs/ortvay/2026/page07.layout.json'));
    for(const[key,expected,file]of[['failed_metadata','1e4619352ef7c57505cb0c72b4173ed0ede971434b3d8148236ba235fea83e06',PRODUCTION+'/pages/2026/page07/FAILED.json'],['base_failed_runtime_snapshot','7f8d0cd7f032cb633f082ea9e2b7eeae2bf7bc58ae72954243cc2a05d5ab117e',PRODUCTION+'/pages/2026/page07/production-runtime-snapshot.json'],['base_original_build_snapshot','98a4bfcf985e35346dd32e5c1389975e070a686b722b5b81d41175f193437efa',R4+'/experiments/ctm-production-runtime-v1/2026/page07/build/runtime-snapshot.json']]){assert.equal(profile[key].sha256,expected);assert.equal(sourcePath(profile[key].path),sourcePath(file));document(profile[key]);}
    for(const[key,file]of[['repair_code_input_freeze','REPAIR-CODE-INPUT-FROZEN.json'],['root_GO','ROOT-GO.json'],['repair_runtime_snapshot','page07/repair-runtime-snapshot.json']])assert.equal(sourcePath(profile[key].path),sourcePath(REPAIR+'/'+file));
    assert.equal(profile.additional_runtime_files.length,3);assert.deepEqual(profile.additional_runtime_files.map(v=>basename(v.path)).sort(),Object.values(PROGRAMS).sort());
    const rawPrograms={};for(const[role,name]of Object.entries(PROGRAMS)){
      const raw=profile.additional_runtime_files.find(v=>basename(v.path)===name);pin(raw);assert.equal(sourcePath(raw.path),sourcePath(REPAIR+'/'+name));sameSHA(style.qa_amendment[role],raw);
      const matches=(qa.authoring_programs||[]).filter(v=>v.sha256===raw.sha256&&basename(v.path)===name&&!sourcePath(v.path).includes('/authoring/source-style/'));assert.equal(matches.length,1,'Missing/ambiguous additional repair program '+name);samePin(matches[0],style.qa_amendment[role]);
      const filename=path.resolve(root,matches[0].path),relative=path.relative(fs.realpathSync(root),fs.realpathSync(filename));assert.ok(relative&&!relative.startsWith('..')&&!path.isAbsolute(relative));assert.equal(crypto.createHash('sha256').update(fs.readFileSync(filename)).digest('hex'),raw.sha256);rawPrograms[raw.path]=raw.sha256;
    }
    const freeze=docs.repair_freeze;validateRepairFreeze(freeze,profile,binding);
    const ledger=document(freeze.preserved_input_ledger);assert.equal(ledger.production_authorized,false);assert.ok(Array.isArray(ledger.preserved_inputs)&&ledger.preserved_inputs.length);for(const v of ledger.preserved_inputs)pin(v);
    const go=docs.repair_GO;assert.equal(go.status,'ROOT_GO_2026_PAGE07_EXACT_ROW_POSTPROCESS');assert.equal(go.year,2026);assert.equal(go.page,7);samePin(go.repair_code_input_freeze,profile.repair_code_input_freeze);samePin(go.numeric_spec,profile.numeric_spec);assert.equal(sourcePath(go.permitted_output_directory),sourcePath(REPAIR+'/page07'));
    assert.equal(go.existing_source_or_runtime_programs_may_change,false);assert.equal(go.original_proofs_or_global_lifecycle_may_change,false);
    const baseOwn=document(profile.base_failed_runtime_snapshot);sourceProfile(baseOwn,binding);assert.deepEqual(Object.fromEntries(Object.entries(baseOwn.files).map(([p,v])=>[sourcePath(p),v.sha256])),binding.additional_programs);validateOriginalRuntime(document(profile.base_original_build_snapshot),binding);
    sourceProfile(docs.copy_receipt.base_profile,binding);assert.deepEqual(docs.copy_receipt.page_repair_profile,profile);validateCopyReceipt(docs.copy_receipt,ready,style,qa);
    const normalized=readNormalizedFile(root,qa,ready,read);validateNormalizedHeader(normalized,ready);
    const negatives=docs.negatives;assert.equal(negatives.schema,'ortvay-2026-page07-actual-repair-negative-regressions-v1');assert.equal(negatives.status,'ALL_REQUIRED_ACTUAL_PDF_AND_BINDING_NEGATIVES_REJECTED');if(Object.hasOwn(negatives,'passed'))assert.equal(negatives.passed,true);samePin(negatives.repair_code_input_freeze,profile.repair_code_input_freeze);samePin(negatives.numeric_spec,profile.numeric_spec);
    samePin(negatives.root_GO,profile.root_GO);samePin(negatives.actual_positive,profile.actual_positive);samePin(negatives.program,profile.additional_runtime_files.find(v=>basename(v.path)===PROGRAMS.auditor));assert.equal(negatives.no_missing_file_or_import_failure_counted,true);
    const protectedPositive=Object.fromEntries(Object.entries(negatives.positive_files_rehashed_unchanged).map(([p,s])=>[sourcePath(p),hash(s)]));assert.ok(Object.keys(protectedPositive).length);assert.equal(protectedPositive[sourcePath(profile.actual_positive.path)],profile.actual_positive.sha256);assert.equal(protectedPositive[sourcePath(docs.positive.proof.path)],docs.positive.proof.sha256);
    validateNegativeCases(negatives.cases,document);
    assert.equal(sourcePath(negatives.valid_candidate_read_only_control.path),sourcePath(REPAIR+'/regressions/valid-candidate-read-only/VALID-CANDIDATE-PASS.json'));
    validateValidCandidateControl(realDocument(document(negatives.valid_candidate_read_only_control)),negatives,profile,docs.positive,binding,document,ready.page_results[6]);
    let italicCount=0;
    for(let i=0;i<10;i++){
      const n=i+1,origin=ready.page_results[i],manifest=style.pages[i],page=qa.page_audits[i];assert.equal(origin.reviewed,true);assert.equal(origin.human_read_pending,false);
      const audit=read(manifest.independent_audit.path,manifest.independent_audit.sha256),machine=read(manifest.machine_result.path,manifest.machine_result.sha256),review=read(manifest.visual_review.path,manifest.visual_review.sha256),body=read(page.qa_path,page.qa_sha256);
      validateNormalizedRow(normalized.pages[i],origin,ready.assembly_page_results[i],page,manifest,ready.assembly_copy_receipt,body,review);
      sameSHA(manifest.independent_audit,origin.independent_audit);sameSHA(manifest.machine_result,origin.machine_result);sameSHA(manifest.visual_review,origin.visual_review);assert.equal(body.output_sha256,page.proof_sha256);assert.equal(body.source_sha256,SOURCE_SHA);assert.equal(body.page,n);
      const plan=read(page.effective_plan_path,page.effective_plan_sha256),raw=fs.readFileSync(path.resolve(root,page.effective_plan_path),'utf8');const effectivePlan={path:page.effective_plan_path,sha256:page.effective_plan_sha256,raw_utf8:raw,document:plan};
      if(n!==7){assert.equal(manifest.qa_lineage,'external_full_ctm_v1');validateOriginalOrigin({origin,machine,review,audit,body,own:document(machine.production_runtime_snapshot),buildSnapshot:document(machine.runtime_snapshot),auditSnapshot:document(machine.audit_runtime_snapshot),binding,effectivePlan},oldStyle);}
      else{
        assert.equal(manifest.qa_lineage,'external_full_ctm_v1_plus_exact_row_postprocess');assert.equal(machine.qa_lineage,manifest.qa_lineage);assert.equal(origin.qa_lineage,manifest.qa_lineage);assert.equal(machine.schema,'ortvay-one-page-postprocess-machine-result-v1');assert.equal(machine.status,'PAGE_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_HUMAN_REVIEW');assert.equal(machine.human_read_pending,true);assert.equal(machine.year,2026);assert.equal(machine.page,7);sourceProfile(machine,binding);
        assert.equal(review.schema,'ortvay-page07-actual-repair-PNG-read-v1');assert.equal(review.status,'ACTUAL_FINAL_PNG_ORIGINAL_RESOLUTION_READ_PASS');assert.equal(review.year,2026);assert.equal(review.page,7);assert.ok(typeof review.reviewer==='string'&&review.reviewer);samePin(review.machine_result,origin.machine_result);
        for(const k of ARTIFACTS){samePin(machine[k],origin[k]);samePin(review.artifacts[k],origin[k]);}
        samePin(review.composer,{path:body.composer_path,sha256:body.composer_sha256});assert.equal(binding.runtime_programs[sourcePath(body.composer_path)],body.composer_sha256);
        assert.deepEqual(origin.page_repair_profile,profile);assert.deepEqual(machine.page_repair_profile,profile);assert.deepEqual(review.additional_authoring_lineage,profile);
        samePin(machine.runtime_snapshot,profile.base_original_build_snapshot);samePin(machine.base_failed_runtime_snapshot,profile.base_failed_runtime_snapshot);samePin(audit.base_failed_runtime_snapshot,profile.base_failed_runtime_snapshot);samePin(audit.base_original_build_snapshot,profile.base_original_build_snapshot);validateOriginalRuntime(document(profile.base_original_build_snapshot),binding);
        sameSHA(manifest.independent_audit,style.qa_amendment.positive);samePin(machine.repair_runtime_snapshot,profile.repair_runtime_snapshot);samePin(audit.repair_runtime_snapshot,profile.repair_runtime_snapshot);
        sourceProfile(audit.base_profile,binding);
        const own=document(profile.repair_runtime_snapshot);assert.equal(own.schema,'ortvay-page07-additional-runtime-snapshot-v1');assert.equal(own.additional_runtime_count,3);assert.equal(own.base_original_runtime_count,46);assert.equal(own.base46_is_provenance_not_a_claim_of_old_only_execution,true);sourceProfile(own.base_profile,binding);samePin(own.numeric_spec,profile.numeric_spec);samePin(own.repair_code_input_freeze,profile.repair_code_input_freeze);samePin(own.root_GO,profile.root_GO);assert.deepEqual(Object.fromEntries(Object.entries(own.files).map(([p,v])=>[p,v.sha256])),rawPrograms);
        for(const[p,v]of Object.entries(own.files))assert.equal(sourcePath(v.retained_copy),sourcePath(REPAIR+'/page07/runtime-sources/additional/'+basename(p)));
        validateRepairAudit(audit,body,spec,profile,manifest.independent_audit,origin,document(profile.base_failed_layout),previous,fullCTM,effectivePlan,binding,document);
      }
      italicCount+=body.r4_source_style_corrections.length;
    }
    assert.equal(italicCount,1);return{status:'REPAIRED_PUBLICATION_CONTRACT_PASS',year:2026,pages:10};
  }
  validatePublication.validateOriginalOrigin=meta=>validateOriginalOrigin(meta,oldStyle);
  return validatePublication;
}
module.exports=(...args)=>createValidator()(...args);
module.exports.createValidator=createValidator;
module.exports.validateRepairedBody=validateRepairedBody;
module.exports.validateCopyReceipt=validateCopyReceipt;
module.exports.validateNumericSpec=numericSpec;
module.exports.assertApprovedRepairGO=approvedGO;
module.exports.assertActualDocument=realDocument;
module.exports.validateItem=validateItem;
module.exports.readNormalizedFile=readNormalizedFile;
module.exports.validateNormalizedHeader=validateNormalizedHeader;
module.exports.validateNormalizedRow=validateNormalizedRow;
module.exports.validateP1PixelRows=validateP1PixelRows;
module.exports.validateNegativeCase=validateNegativeCase;
module.exports.validateNegativeCases=validateNegativeCases;
module.exports.validateNativeReadonlyReplay=validateNativeReadonlyReplay;
module.exports.validateValidCandidateControl=validateValidCandidateControl;
module.exports.validateRepairFreeze=validateRepairFreeze;
module.exports.constants=Object.freeze({APPROVED_REPAIR_GO_SHA256,NUMERIC_SHA,SOURCE_SHA,PUBLISHED_SHA,FAILED_PDF_SHA,FAILED_LAYOUT_SHA,BASELINE,SIZE,DX,SLOT,GIDS,XREFS,OLD_PAGES,ARTIFACTS});

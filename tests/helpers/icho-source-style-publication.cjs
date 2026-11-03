const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const SOURCE='959174ab5ddc8be71c251c8fe95a12c810ba730edbcbbef3b771197e32929a4a';
const PUBLISHED='78d869b01f48bd1e050f2b8697900c757f4987331b1895026173e4b3258fe024';
const APPROVED='bc06cca28d8b2f3ed93b437a5c3ed12f37cc8dd40d096f174314e5e2dffa68b2';
const FREEZE='fd600ecbd54dc70bf25033bf9eebf4a065ac3256175ecfdf3ff70954361625e4';
const MEASUREMENT='9f7397f1437c9c78b383d2f6624d1cee64472930f849cad6a7f972bd2625ecb4';
const CURVE='8e032abc9060b2be0a2af658cb7b1a6e2edb333aa0b7a228e40bdd60c1705799';
const MAP='ad5990b8ceb44b2dabbfc7a53ce8c344907d4b5b243f58e4e7cd88fba0dfde8a';
const SEMANTIC='bbc753360d5c243a4ca31fede8047b67b212cecea704bfae275521e82b8082e4';
const ATOM_PROFILE='60f010c33b97f27a5347f187c141dddc46e740bb3023cb98ba66f43413f5153e';
const P32_PROOF='295d4bcd98d367c2cc0a140ba5d824fdf3345407500b03a127e04d1d2b159219';
const P32_LAYOUT='1b5cdf8f40e8774344d024a5ccdbde997137be37a0f18027000619cfc2971eea';
const P32_AUDITOR='71a4437ddf0a99abc9585ef3585c26c668e42fc891ee0148f7cf6e44f153f21b';
const P32_STROKE='8756e7deb5c4dd9e6d470d9fc562f58398996bc4a34371ebcd759b4da9be9477';
const QA3_PINS={
  auditor_code_input_freeze:'cf9cbf12fc44e398d55869c8d0be416c85c6ec347a962567e14376fd406f4ffe',
  continuation_code_input_freeze:'14461ddd3d1cde2dd46b3253ba397de18257feeec1602b8a40c569becf45d18a',
  root_GO:'ae675aad54054e8392469c5371907a3936feb9a33df797516237203b0796f245',
  actual_positive:'1badd547ccd6b1a0a8a624819469da05b5b28376389ae41a9df81c91e77ee382',
  actual_negative_regressions:'ad132f31de1cb85bddfe3631efa3d12876084fc4a5eae216dc3e06399a5a6445',
  auditor_program:P32_AUDITOR,
};
function validateQa3Amendment(root,qa,ready,read) {
  const profile=qa.source_style_correction.qa_amendment;
  assert.deepEqual(Object.keys(profile).sort(),Object.keys(QA3_PINS).sort());
  assert.deepEqual(Object.keys(ready.qa_amendment).sort(),Object.keys(QA3_PINS).sort());
  const program=(name,digest,exactPath)=>{
    const found=qa.authoring_programs.filter(p=>p.sha256===digest&&path.posix.basename(p.path.replace(/\\/g,'/'))===name);
    assert.ok(found.length,'Missing reviewed QA3 runtime: '+name);
    if(exactPath)assert.ok(found.some(p=>p.path===exactPath));
    for(const p of found){
      assert.ok(!path.isAbsolute(p.path)&&!p.path.split(/[/\\]/).includes('..'));
      assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.resolve(root,p.path))).digest('hex'),digest);
    }
  };
  const documents={};
  for(const[key,digest]of Object.entries(QA3_PINS)) {
    assert.equal(profile[key].sha256,digest);assert.equal(ready.qa_amendment[key].sha256,digest);
    if(key==='auditor_program')program('audit_p32_source_stroke_support.py',digest,profile[key].path);
    else documents[key]=read(profile[key].path,digest);
  }
  const go=documents.root_GO;
  assert.equal(go.status,'ROOT_GO_QA3_CONTINUATION_OF_FROZEN_FINAL62_V3');
  assert.equal(go.production_freeze_sha256,FREEZE);
  for(const key of ['auditor_code_input_freeze','continuation_code_input_freeze','actual_positive','actual_negative_regressions'])assert.equal(go[key+'_sha256'],QA3_PINS[key]);
  assert.equal(Object.keys(documents.auditor_code_input_freeze.program_and_input_sha256).length,274);
  const table=documents.continuation_code_input_freeze.program_and_input_sha256;
  assert.equal(Object.keys(table).length,648);
  const normalize=p=>p.replace(/\\/g,'/').toLowerCase();
  const directory=normalize(ASSEMBLY_BASE+'/style-corrections/icho2024-20261103/qa-amendments/p32-source-underline-support-v3/continuation/');
  const active=Object.entries(table).filter(([p])=>normalize(p).startsWith(directory)&&normalize(p).slice(directory.length).match(/^[^/]+\.py$/));
  assert.equal(active.length,6);
  for(const[p,digest]of active)program(path.posix.basename(p.replace(/\\/g,'/')),digest);
  const finalizer=active.find(([p])=>normalize(p)===directory+'finalize_ready_qa2.py');assert.ok(finalizer);
  assert.equal(normalize(ready.program_path),normalize(finalizer[0]));assert.equal(ready.program_sha256,finalizer[1]);
  program('test_p32_source_stroke_support.py','0735e1cca3fe0b681ee5e166596635ac8dc365547cb8ac548416d608c008fd8f');
  const positive=documents.actual_positive,negative=documents.actual_negative_regressions;
  assert.equal(positive.proof_sha256,P32_PROOF);assert.equal(positive.layout_sha256,P32_LAYOUT);
  assert.equal(positive.program_sha256,P32_AUDITOR);assert.equal(positive.passed,true);
  assert.equal(negative.status,'PASS');assert.equal(negative.all_rejected,true);
  assert.equal(negative.actual_PDF_counterexamples,3);assert.equal(negative.additional_layout_binding_counterexamples,1);
}
function validateP32PixelAudit(q,pixel,qa) {
  assert.equal(q.page,32);assert.equal(pixel.page,32);assert.equal(q.output_sha256,P32_PROOF);
  for(const key of ['proof_sha256','certified_full_font_curve_proof_sha256'])assert.equal(pixel[key],P32_PROOF);
  for(const key of ['layout_sha256','certified_original_layout_sha256'])assert.equal(pixel[key],P32_LAYOUT);
  assert.equal(pixel.program_sha256,P32_AUDITOR);
  assert.ok(qa.authoring_programs.some(p=>p.sha256===P32_AUDITOR),'Missing actual p32 external pixel auditor');
  assert.equal(pixel.frozen_pixel_auditor_sha256,'da97a0ca5a5e425f2dbcb640f274ae48610c4ee55780837e9c71150c1c28e37e');
  assert.equal(pixel.source_semantic_mapping_sha256,MAP);assert.equal(pixel.source_mapping_index,34);
  assert.equal(pixel.source_stroke_program_sha256,P32_STROKE);assert.deepEqual(pixel.source_operator_indices,[392,393,394]);
  assert.equal(pixel.anti_alias_support_pad_pt,.5);
  assert.deepEqual(pixel.original_source_stroke_support_rect,[56.193,663.8417646507025,109.463,665.2402646461726]);
  assert.deepEqual(pixel.source_bound_changed_row_baselines,[486.906982421875,663.0490112304688]);
  assert.deepEqual(pixel.source_bound_row_rects,[[114.19246673583984,475.7569580078125,267.2073256720969,490.3260498046875],
    [56.192962646484375,651.8989868164062,107.48416717546957,666.4680786132812]]);
  assert.equal(pixel.unchanged_frozen_mask_original_outside_pixels,6);assert.equal(pixel.changed_pixels_outside_named_source_rows,0);
  assert.deepEqual(pixel.admitted_original_underline_tail_pixel_yx,[[1328,215],[1328,216],[1328,217],[1329,215],[1329,216],[1329,217]]);
  assert.equal(pixel.all_admitted_pixels_exact_original_source_and_P0_stroke_erasure,true);
  assert.equal(pixel.all_actual_glyphs_equal_to_full_font_curve_audited_immutable_proof,true);
  assert.equal(pixel.glyph_tolerance_pt,.001);assert.equal(pixel.native_vector_tolerance_pt,1e-7);
  assert.deepEqual(pixel.actual32x_vertical_stroke_samples.map(s=>s.fraction),[.1,.25,.5,.75,.9]);
  for(const sample of pixel.actual32x_vertical_stroke_samples){assert.equal(sample.byte_identical,true);assert.deepEqual(sample.source,sample.candidate);assert.ok(sample.source[1].length&&Math.min(...sample.source[1])<220);}
  assert.equal(pixel.kk.actual_embedded_subset_fonts,true);assert.equal(pixel.kk.unchanged_word_space_size_shear_paints,true);
  const specs=q.prose_vector_decorations.filter(s=>s.semantic_mapping_index===34);assert.equal(specs.length,1);
  const spec=specs[0],program=spec.source_program;
  assert.equal(program.source_construction_and_paint_fragment_sha256,P32_STROKE);
  assert.deepEqual(program.source_operator_indices,[392,393,394]);assert.deepEqual(program.source_operator_names,['m','l','S']);
  assert.equal(crypto.createHash('sha256').update(Buffer.from(program.source_construction_and_paint_fragment_latin1,'latin1')).digest('hex'),P32_STROKE);
  assert.deepEqual(spec.source_rect,[56.693,664.5410146484376,108.963,664.5410146484376]);
}
const ASSEMBLER='098286bc8fa1a3ac5805006b95484c5dd279a6fac4e1fc5c109e86e7f976954f';
const ASSEMBLY_WRAPPER='5110db69ac0faadd62dcc5baf903ce65dfdec79508b4ef1e4b1a105e8dae9fb7';
const ASSEMBLY_BASE='D:/CodexBuilds/Hasla-poi-natural-20261102';
const ASSEMBLY_O=ASSEMBLY_BASE+'/style-corrections/icho2024-20261103';
const ASSEMBLY_R=ASSEMBLY_O+'/revisions/final62-v3';
const ASSEMBLY_F=ASSEMBLY_O+'/final/2024-v3';
const originalPath=p=>{
  assert.equal(typeof p,'string');assert.ok(path.win32.isAbsolute(p));
  return path.win32.resolve(p).replaceAll('\\','/').toLowerCase();
};
function validateAssemblyReceipt(root,qa,item,read,ready,freeze) {
  const style=qa.source_style_correction,pin=style.assembly_receipt;
  assert.ok(pin&&pin.path&&pin.sha256,'Missing actual IChO2024 assembly receipt');
  assert.ok(qa.supplemental_evidence.some(p=>p.path===pin.path&&p.sha256===pin.sha256));
  const receipt=read(pin.path,pin.sha256);
  const hash=raw=>crypto.createHash('sha256').update(raw).digest('hex');
  const publicBytes=file=>{
    const absolute=path.resolve(root,file),relative=path.relative(root,absolute);
    assert.ok(relative&&!relative.startsWith('..'+path.sep)&&!path.isAbsolute(relative));
    return fs.readFileSync(absolute);
  };
  const document=p=>{
    const copied=qa.supplemental_evidence.find(e=>e.sha256===p.sha256);
    assert.ok(copied,'Missing copied assembly document: '+p.path);
    const raw=publicBytes(copied.path);assert.equal(hash(raw),p.sha256);
    if(p.bytes!==undefined)assert.equal(raw.length,p.bytes);
    return read(copied.path,p.sha256);
  };
  const program=(p,dependency=false)=>{
    const name=p.path.replaceAll('\\','/').split('/').at(-1);
    const stored=qa.authoring_programs.find(x=>x.sha256===p.sha256&&
      (dependency?x.path.replaceAll('\\','/').includes('/authoring/source-style/assembly-dependencies/')&&
        x.path.endsWith('-'+name):x.path.endsWith('/'+name)));
    assert.ok(stored,'Missing actual assembly program: '+name);
    const raw=publicBytes(stored.path);assert.equal(hash(raw),p.sha256);assert.equal(raw.length,p.bytes);
  };
  assert.equal(receipt.schema,'icho2024-final62-v3-actual-assembly-receipt-v1');
  assert.equal(receipt.status,'ACTUAL_ASSEMBLER_COMPLETED_AND_OUTPUTS_REHASHED');
  assert.equal(receipt.competition,'icho');assert.equal(receipt.year,2024);assert.equal(receipt.pages,62);
  assert.equal(receipt.subprocess_returncode,0);
  assert.equal(receipt.assembler.sha256,ASSEMBLER);assert.equal(receipt.assembler_sha256_after,ASSEMBLER);
  assert.equal(originalPath(receipt.assembler.path),originalPath(ASSEMBLY_BASE+'/engine/assemble_natural.py'));
  assert.equal(receipt.wrapper.sha256,ASSEMBLY_WRAPPER);
  assert.equal(originalPath(receipt.wrapper.path),originalPath(ASSEMBLY_BASE+'/engine/assemble_icho2024_v3_checked.py'));
  program(receipt.assembler);program(receipt.wrapper);
  assert.equal(receipt.code_input_freeze.sha256,FREEZE);
  assert.equal(originalPath(receipt.code_input_freeze.path),originalPath(ASSEMBLY_R+'/FINAL-CODE-INPUT-FREEZE.json'));
  document(receipt.code_input_freeze);
  assert.equal(receipt.ready.sha256,style.ready.sha256);
  assert.equal(originalPath(receipt.ready.path),originalPath(ASSEMBLY_F+'/READY.json'));
  assert.deepEqual(document(receipt.ready),ready);
  assert.equal(ready.code_input_freeze.sha256,FREEZE);
  assert.equal(ready.source.sha256,SOURCE);
  assert.equal(receipt.visual_bridge.sha256,ready.normalized_visual_bridge.sha256);
  assert.equal(originalPath(receipt.visual_bridge.path),originalPath(ASSEMBLY_F+'/visual-review-all62-v3.json'));
  assert.equal(originalPath(receipt.visual_bridge.path),originalPath(ready.normalized_visual_bridge.path));
  const bridge=document(receipt.visual_bridge);
  assert.equal(bridge.source_sha256,SOURCE);assert.equal(bridge.code_input_freeze.sha256,FREEZE);
  assert.equal(bridge.pages.length,62);assert.equal(ready.page_results.length,62);
  const pdf=receipt.output_pdf;
  assert.equal(path.win32.basename(pdf.path),'IChO_2024_T_KO.pdf');
  assert.ok(originalPath(pdf.path).startsWith(originalPath(ASSEMBLY_O+'/root-assembled')+'/'));
  assert.equal(pdf.sha256,qa.sha256);assert.equal(pdf.sha256,item.sha256);
  assert.equal(pdf.bytes,qa.bytes);assert.equal(pdf.bytes,item.bytes);
  assert.equal(qa.source_sha256,SOURCE);assert.equal(qa.pages,62);assert.equal(item.pages,62);
  assert.equal(qa.visual_review_required,false);assert.equal(qa.all_pages_visually_reviewed,true);
  const qaPath=pdf.path.slice(0,-4)+'.qa.json';
  assert.equal(originalPath(receipt.output_qa.path),originalPath(qaPath));
  const joined=document(receipt.output_qa);
  assert.equal(joined.schema,'natural-source-native-joined-v1');assert.equal(joined.status,'READY');
  assert.equal(joined.sha256,pdf.sha256);assert.equal(joined.bytes,pdf.bytes);
  assert.equal(joined.source_sha256,SOURCE);assert.equal(joined.pages,62);
  assert.equal(joined.visual_review_required,false);assert.equal(joined.all_pages_visually_reviewed,true);
  assert.ok(joined.visual_review_files.some(p=>originalPath(p)===originalPath(receipt.visual_bridge.path)));
  assert.equal(originalPath(receipt.cwd),originalPath(ASSEMBLY_BASE));
  const args=receipt.argv;assert.equal(args.length,17);
  for(const[index,value]of [[1,'-B'],[2,'-X'],[3,'utf8'],[5,'icho'],[6,'IChO'],[7,'2024'],[8,'62'],[9,'--proof-dir'],[11,'--proof-helper'],[13,'--output-dir'],[15,'--visual-review']])assert.equal(args[index],value);
  for(const[index,value]of [[0,receipt.python],[4,receipt.assembler.path],[10,ASSEMBLY_F],[12,ASSEMBLY_R+'/working/style-engine/native_proof.py'],[14,path.win32.dirname(pdf.path)],[16,receipt.visual_bridge.path]])assert.equal(originalPath(args[index]),originalPath(value));
  const inputs=new Map();
  for(const input of receipt.input_files) {
    const key=originalPath(input.path);assert.ok(!inputs.has(key),'Duplicate assembly input');
    assert.match(input.sha256,/^[0-9a-f]{64}$/);assert.ok(Number.isSafeInteger(input.bytes)&&input.bytes>=0);
    inputs.set(key,input);
  }
  const required=p=>assert.deepEqual(inputs.get(originalPath(p.path)),p,'Assembly input absent or changed: '+p.path);
  for(const key of ['assembler','wrapper','code_input_freeze','ready','visual_bridge','proof_helper'])required(receipt[key]);
  assert.equal(inputs.get(originalPath(ready.source.path)).sha256,SOURCE);
  for(const[field,count]of [['current_program_and_input_sha256',249],['preserved_input_sha256',204],['preserved_prior_output_sha256',206]]) {
    assert.equal(Object.keys(freeze[field]).length,count);
    for(const[file,digest]of Object.entries(freeze[field]))assert.equal(inputs.get(originalPath(file)).sha256,digest);
  }
  const helper=ASSEMBLY_R+'/working/style-engine/native_proof.py';
  assert.equal(originalPath(receipt.proof_helper.path),originalPath(helper));
  const frozenHelper=Object.entries(freeze.current_program_and_input_sha256).find(([p])=>originalPath(p)===originalPath(helper));
  assert.ok(frozenHelper);assert.equal(receipt.proof_helper.sha256,frozenHelper[1]);
  const dependencyPaths=[ASSEMBLY_BASE+'/engine/source_path_resolver.py',ASSEMBLY_BASE+'/engine/prose_decoration_publication.py',ASSEMBLY_BASE+'/engine/icho2024_prose_decoration_publication.py',
    'D:/CodexBuilds/Hasla-plancks-ortvay-icho-20261102/engine/native_proof.py','D:/CodexBuilds/Hasla-plancks-ortvay-icho-20261102/engine/pdf_latex_text_ops.py'];
  assert.equal(receipt.assembly_dependencies.length,5);
  assert.deepEqual(receipt.assembly_dependencies.map(p=>originalPath(p.path)).sort(),dependencyPaths.map(originalPath).sort());
  for(const dependency of receipt.assembly_dependencies){required(dependency);program(dependency,true);}
  assert.equal(receipt.page_inputs.length,62);assert.equal(qa.page_audits.length,62);assert.equal(joined.page_audits.length,62);
  for(const[index,row]of receipt.page_inputs.entries()) {
    const n=index+1,page=qa.page_audits[index],original=joined.page_audits[index],review=bridge.pages[index],readyPage=ready.page_results[index];
    assert.equal(row.page,n);assert.equal(page.page,n);assert.equal(original.page,n);assert.equal(review.page,n);assert.equal(readyPage.page,n);
    assert.equal(originalPath(row.proof.path),originalPath(ASSEMBLY_F+'/page'+String(n).padStart(2,'0')+'.pdf'));
    assert.equal(originalPath(row.layout.path),originalPath(ASSEMBLY_F+'/page'+String(n).padStart(2,'0')+'.layout.json'));
    required(row.proof);required(row.layout);
    for(const p of [page,original]) {
      assert.equal(row.proof.sha256,p.proof_sha256);assert.equal(row.layout.sha256,p.qa_sha256);
      assert.equal(p.final_vs_reviewed_proof_changed_pixels,0);assert.equal(p.final_vs_reviewed_proof_all_glyph_geometry_identical,true);
    }
    assert.equal(readyPage.proof.sha256,row.proof.sha256);assert.equal(readyPage.layout.sha256,row.layout.sha256);
    assert.equal(review.reviewed,true);assert.equal(review.proof_sha256,row.proof.sha256);assert.equal(review.layout_sha256,row.layout.sha256);
    assert.equal(review.effective_plan_sha256,page.effective_plan_sha256);assert.equal(review.composer_sha256,page.composer_sha256);
  }
  assert.equal(originalPath(receipt.attempt.path),originalPath(pdf.path.slice(0,-4)+'.assembly-attempt.json'));
  const attempt=document(receipt.attempt);
  assert.equal(attempt.schema,'icho2024-final62-v3-assembly-attempt-v1');
  for(const key of ['started_utc','argv','cwd','wrapper','assembler','code_input_freeze','ready','visual_bridge','input_files'])assert.deepEqual(attempt[key],receipt[key],'Execution attempt/receipt mismatch: '+key);
  assert.ok(Number.isFinite(Date.parse(receipt.started_utc))&&Date.parse(receipt.completed_utc)>=Date.parse(receipt.started_utc));
}
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
  if(q.page===32)validateP32PixelAudit(q,pixel,qa);
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
  for(const [file,digest]of Object.entries(freeze.current_program_and_input_sha256)) {
    if(file.endsWith('.py')) {
      const name=file.replaceAll('\\','/').split('/').at(-1);
      assert.ok(qa.authoring_programs.some(p=>p.path.endsWith('/'+name)&&p.sha256===digest),'Missing frozen source-style program: '+name);
    }
  }
  assert.equal(style.approved_clauses.sha256,APPROVED);read(style.approved_clauses.path,APPROVED);
  assert.equal(style.inline_atom_profile.sha256,ATOM_PROFILE);read(style.inline_atom_profile.path,ATOM_PROFILE);
  assert.equal(style.native_prefix_profile.sha256,'f3efb347598737eb8505f8f529e044e15ee4307a8bdf5caaced7e88f2b09ff3d');
  const prefixProfile=read(style.native_prefix_profile.path,style.native_prefix_profile.sha256);
  const ready=read(style.ready.path,style.ready.sha256);
  assert.equal(ready.status,'YEAR_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_ROOT_ASSEMBLY_REVIEW');
  assert.equal(ready.year,2024);assert.equal(ready.pages,62);assert.equal(ready.source.sha256,SOURCE);
  validateAssemblyReceipt(root,qa,item,read,ready,freeze);
  validateQa3Amendment(root,qa,ready,read);
  assert.equal(style.pages.length,62);assert.equal(ready.page_results.length,62);
  for(const digest of [MEASUREMENT,CURVE,SEMANTIC])assert.ok(qa.authoring_programs.some(p=>p.sha256===digest));
  let underlines=0,italics=0,edits=0;
  for(const[index,pin]of style.pages.entries()) {
    const page=qa.page_audits[index];assert.equal(pin.page,index+1);assert.equal(pin.proof_sha256,page.proof_sha256);assert.equal(pin.layout_sha256,page.qa_sha256);
    const body=read(page.qa_path,page.qa_sha256),pixel=read(pin.pixel_audit.path,pin.pixel_audit.sha256);
    assert.equal(body.page,index+1);assert.equal(body.output_sha256,page.proof_sha256);
    if(index===31)assert.equal(page.qa_sha256,P32_LAYOUT);
    const atom=pin.inline_atom_audit?read(pin.inline_atom_audit.path,pin.inline_atom_audit.sha256):undefined;
    if(atom)assert.equal(atom.layout_sha256,page.qa_sha256);
    if(index===56) {
      const prefix=read(pin.native_prefix_audit.path,pin.native_prefix_audit.sha256);
      require('./icho2024-native-d-publication.cjs')(body,prefix,prefixProfile,page.qa_sha256,qa);
    }
    validatePage(body,pixel,old.page_audits[index].proof_sha256,qa,atom);
    assert.equal(ready.page_results[index].proof.sha256,page.proof_sha256);assert.equal(ready.page_results[index].layout.sha256,page.qa_sha256);
    underlines+=body.independent_source_semantic_style_audit.semantic_mappings.length;
    italics+=body.independent_source_semantic_style_audit.new_Korean_italic_placements;
    edits+=body.independent_source_semantic_style_audit.exact_approved_text_edits;
  }
  assert.equal(underlines,68);assert.equal(italics,9);assert.equal(edits,54);
};
module.exports.validatePage=validatePage;
module.exports.validateAssemblyReceipt=validateAssemblyReceipt;
module.exports.validateP32PixelAudit=validateP32PixelAudit;
module.exports.validateQa3Amendment=validateQa3Amendment;

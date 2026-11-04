const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const SOURCE='fb90239d8da3dea3dcfe104551243f444802632a74a47a139374013aa16080f1';
const PROOF='c0e885db8f0d7c54b5576f1e0e4f9dd3a214dbf685149261b1c73a2b10089310';
const WITNESS='f65c81b69610a32acf275ff23d06fc4174e2611b20ed49dd0b86db1793cca5a8';
const RAW='af09dc3f15fd8eaeda6ad489893506d841d77c15829802006f9152897792451b';
const REFERENCE='ee7f4f21bb19f493ec58e5c3256a00af2008bc103d815840865f085a8835e37c';
const FORM='779c8e3f588127389d4cc28e758da76ecd30c5897231adb1fbbb86535e7e473f';
const kind='source2017-page11-complete-original-inline-lambda-native-Form-program-v1';
function validate(profile,w,raw,page,item){
 assert.equal(item.file,'IZhO_2017_TS_KO.pdf');assert.equal(page.page,11);assert.equal(page.source_pdf_sha256,SOURCE);assert.equal(page.proof_sha256,PROOF);
 assert.equal(profile.kind,kind);assert.equal(profile.witness_sha256,WITNESS);assert.equal(profile.exact_original_native_expression_glyphs,7);assert.equal(profile.mathematical_ink_excluded,false);
 assert.equal(w.kind,kind);assert.equal(w.original_source_sha256,SOURCE);assert.equal(w.original_input_page_sha256,RAW);assert.equal(raw.source_sha256,RAW);assert.equal(w.source_reference_sha256,REFERENCE);assert.equal(w.proof_sha256,PROOF);assert.equal(w.source_page,11);
 assert.equal(w.passed,true);assert.equal(w.proof_unmodified,true);for(const key of ['delivered_pdf_modified','mathematics_retyped','source_font_programs_substituted'])assert.equal(w[key],false);
 assert.equal(raw.protected_native_glyphs,354);assert.equal(raw.newly_missing_native_ink_pixels,1);assert.deepEqual(raw.missing_bbox,[158.5,739.25,158.75,739.5]);assert.deepEqual(raw.missing_requested_source_glyphs,[]);assert.deepEqual(raw.missing_final_native_glyphs,[]);assert.equal(raw.source_outline_audit.passed,true);
 const guard=w.source_native_reference_guard;assert.equal(guard.literal_original_Form_raw_sha256,FORM);assert.equal(guard.complete_original_expression_CIDs_and_internal_programs_unchanged,true);assert.equal(w.original_form.original_raw_sha256,FORM);assert.equal(w.all_original_target_Form_bytes_and_native_ancestor_context_preserved,true);
 const digest=x=>crypto.createHash('sha256').update(JSON.stringify(x)).digest('hex');
 assert.equal(digest(w.original_form),'38f0850358b5651ad883fd3a4875d3354e689403a4a5d131104252e88c5ec409');
 assert.equal(digest(w.complete_original_expression_glyphs),'72a3051a74898f5f3d521d8a64ac5cf5305d0c873989d3b19d36b70288573af9');
 assert.ok(Math.abs(w.independently_inferred_whole_original_expression_dx-6.504005432128906)<1e-10);assert.deepEqual(w.source_math_expression_point_sizes,[12.472784996032715]);assert.deepEqual(w.same_integer_page_crop,[109,730,185,753]);
 const expected=[['1','Times New Roman',18],['2','Times New Roman',19],['3','Times New Roman',20],['\uf02b','Symbol',14],['\uf03d','Symbol',32],['\uf03e','Symbol',33],['\uf06c','Symbol',79]].map(r=>JSON.stringify(r)).sort();
 for(const glyphs of [w.complete_original_expression_glyphs,w.original_form.glyphs]){
  assert.equal(glyphs.length,7);assert.deepEqual(glyphs.map(g=>JSON.stringify([g.c,g.font,g.trace_gid])).sort(),expected);
  for(const g of glyphs){assert.equal(g.size,12.472784996032715);assert.equal(g.render_mode,0);assert.equal(g.opacity,1);assert.deepEqual(g.color,[0,0,0]);assert.ok(g.origin[0]>=104&&g.origin[0]<=175);assert.ok(g.origin[1]>=732&&g.origin[1]<=751);}
 }
 assert.equal(w.original_form.own_vector_paths.length,4);for(const p of w.original_form.own_vector_paths)assert.equal(p.paint_operator,'S');
 const samples=new Map([['MuPDF:4',[1886,947]],['Poppler:4',[1884,945]],['MuPDF:8',[6327,4510]],['Poppler:8',[6329,4550]],['MuPDF:12',[13521,10691]],['Poppler:12',[13555,10768]]]);
 assert.equal(w.native_original_program_reference_measurements.length,6);
 for(const r of w.native_original_program_reference_measurements){const key=`${r.renderer}:${r.scale}`;assert.ok(samples.has(key));assert.deepEqual([r.reference_original_program_nonwhite_pixels,r.reference_original_program_deep_dark_pixels],samples.get(key));samples.delete(key);assert.equal(r.missing_original_native_program_pixels,0);assert.equal(r.actual_reference_nonwhite_RGB_errors,0);assert.equal(r.passed,true);}assert.equal(samples.size,0);
 assert.deepEqual(Object.keys(w.svg_reference_scales).sort(),['12','4','8']);for(const q of Object.values(w.svg_reference_scales)){assert.equal(q.protected_native_glyphs,7);assert.equal(q.passed,true);assert.equal(q.newly_missing_native_ink_pixels,0);assert.deepEqual(q.missing_requested_source_glyphs,[]);assert.deepEqual(q.missing_final_native_glyphs,[]);assert.equal(q.source_outline_audit.passed,true);}
 assert.equal(profile.original_native_reference_missing_pixels,0);assert.equal(profile.native_reference_nonwhite_RGB_errors,0);assert.deepEqual(profile.native_reference_renderers,['MuPDF','Poppler']);assert.deepEqual(profile.native_reference_scales,[4,8,12]);assert.deepEqual(profile.cropped_SVG_reference_scales,[4,8,12]);assert.equal(profile.cropped_SVG_native_ink_missing_pixels,0);
}
module.exports=validate;
module.exports.kind=kind;

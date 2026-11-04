'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const validate=require('./helpers/cpho2003-native-inline-publication.cjs'),root=path.resolve(__dirname,'..');
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8')),clone=x=>JSON.parse(JSON.stringify(x)),sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const items=read('tools/original_style_publication.json').filter(i=>i.audit_schema==='cpho2003-native-inline-original-v1');assert.equal(items.length,2);let positives=0,rejected=0;
for(const item of items){assert.equal(validate(root,read(item.qa),item).passed,true);positives++;}
const item=items.find(i=>i.language==='ko'),original=read(item.qa),reject=(label,fn)=>{assert.throws(fn,undefined,label);console.log('REJECTED',label);rejected++;};
for(const[k,v]of [['original_math_retyped',true],['original_math_y_changed',true],['translated_point_sizes_fitted',true],['added_editorial_notes',1],['pages',2],['source_original_sha256','0'.repeat(64)],['original_source_page_group_retained',false]]){const q=clone(original);q[k]=v;reject(k,()=>validate(root,q,item));}
{const q=clone(original);q.page_proofs.pop();reject('drop mostly blank source page3 with the final two prompts',()=>validate(root,q,item));}
{const q=clone(original);q.page_proofs[0]=q.page_proofs[1];reject('swap original physical pages',()=>validate(root,q,item));}
{const q=clone(original);q.page_proofs[0].proof.sha256='0'.repeat(64);reject('wrong exact proof hash',()=>validate(root,q,item));}
const temp=path.join(root,`.cpho2003-contract-mutations-${process.pid}`);assert.ok(!fs.existsSync(temp));fs.mkdirSync(temp);let index=0;
const mutate=(ref,change)=>{const value=read(ref.path);change(value);const raw=Buffer.from(JSON.stringify(value)+'\n'),out=path.join(temp,`mutation${index++}.json`);fs.writeFileSync(out,raw);return{...ref,path:path.relative(root,out).replaceAll('\\','/'),sha256:sha(raw),bytes:raw.length};};
const sharedChange=fn=>{const q=clone(original);q.shared=mutate(q.shared,fn);return q;};
try{
 const changes=[
  ['nonzero original native ink','source_native_ink',q=>q.newly_missing_native_ink_pixels=1],
  ['missing original source glyph','source_native_ink',q=>q.missing_final_native_glyphs=[{c:'x'}]],
  ['source Group mismatch','source_programs_and_advances',q=>q.original_media_crop_rotation_group_and_colorspace_preserved=false],
  ['source font program mismatch','source_programs_and_advances',q=>q.all_original_font_programs_names_and_ToUnicode_preserved=false],
  ['new horizontal font fitting','source_programs_and_advances',q=>q.glyph_checks[0].actual_trace_advance_width*=.8],
  ['wrong new point size','actual_style',q=>q.actual_glyph_style_checks[0].actual_point_size=9.5],
  ['wrong new font face','actual_style',q=>q.actual_glyph_style_checks[0].actual_font='Arial'],
  ['source Tr2 section stroke removed','actual_style',q=>{const g=q.actual_glyph_style_checks.find(g=>g.actual_render_mode===2);g.actual_render_mode=0;}],
  ['title shifted off original center','actual_style',q=>q.actual_centered_heading_checks[0].actual_center+=1],
  ['wrong script relative geometry','audit',q=>q.original_native_expression_relative_geometry.passed=false],
  ['unreviewed extra graphic','audit',q=>q.native_graphics_motion_audit.changed_nonselected_native_graphical_pixels=1],
  ['new prose over source math','prose_native_text_collision',q=>q.dark_prose_pixels_over_native_text=1],
  ['missing native clip bytes','composition',q=>q.native_move_qa.native_atomic_clip_bytes_preserved=false],
  ['nonzero final Poppler difference','assembly',q=>q.Poppler144_RGB_difference_pixels=1],
  ['wrong authored source','source_authored_prose',q=>q.source_sha256='0'.repeat(64)],
 ];
 for(const[label,key,change]of changes){const q=clone(original);q.page_proofs[0][key]=mutate(q.page_proofs[0][key],change);reject(label+' with rebased JSON hash',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.master_manifest=mutate(s.master_manifest,m=>m.files[0].sha256='0'.repeat(64)));reject('rebase entire trusted source master',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.source_classification=mutate(s.source_classification,m=>m.theory_problem_physical_pages=[1,2]));reject('invent available source split',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.font_source_pins=mutate(s.font_source_pins,m=>m[0].full_font_copied=true));reject('exported installed full font claimed',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.visual_review=mutate(s.visual_review,m=>m.pages[0].full_original_and_current_proof_144dpi_visually_reviewed=false));reject('unreviewed current full page',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.stationary_math_Poppler=mutate(s.stationary_math_Poppler,m=>m.pages[0].rois[0].changed_RGB_pixels=1));reject('original stationary math Poppler mismatch',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.negative_controls.pop());reject('drop actual bad PDF control',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.negative_controls[0].fixture=s.negative_controls[1].fixture);reject('transplant another actual negative fixture',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.negative_manifest=mutate(s.negative_manifest,m=>m.diagnostic_false_alarm_not_counted=false));reject('misclassify diagnostic as real negative',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.authoring_closure=s.authoring_closure.filter(r=>!r.frozen_path.endsWith('/pdf_native_inline_reposition.py')));reject('missing exact unchanged native guard',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.source_original_pdf.path='../outside.pdf');reject('source evidence path escape',()=>validate(root,q,item));}
}finally{assert.ok(path.resolve(temp).startsWith(root+path.sep));for(const file of fs.readdirSync(temp)){assert.match(file,/^mutation\d+\.json$/);fs.unlinkSync(path.join(temp,file));}fs.rmdirSync(temp);}
console.log(JSON.stringify({passed:true,positive_editions:positives,rejected_mutations:rejected,actual_bad_PDF_controls:5}));

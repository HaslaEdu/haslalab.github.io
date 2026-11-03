'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const validate=require('./helpers/cpho2007-native-inline-publication.cjs');
const root=path.resolve(__dirname,'..');
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const items=read('tools/original_style_publication.json').filter(r=>r.audit_schema==='cpho2007-native-inline-original-v1');assert.equal(items.length,2);
const clone=x=>JSON.parse(JSON.stringify(x));
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
let positive=0,rejected=0;
for(const item of items){assert.equal(validate(root,read(item.qa),item).passed,true);positive++;}
const item=items.find(e=>e.language==='ko'),original=read(item.qa);
const reject=(label,fn)=>{assert.throws(fn,undefined,label);rejected++;console.log('REJECTED',label);};
for(const [key,value]of [['original_math_retyped',true],['translated_point_sizes_fitted',true],['added_editorial_notes',1],['pages',15],['source_original_sha256','0'.repeat(64)]]){
 const q=clone(original);q[key]=value;reject(key,()=>validate(root,q,item));
}
{const q=clone(original);q.page_proofs.pop();reject('drop original blank folio20',()=>validate(root,q,item));}
{const q=clone(original);q.page_proofs[0]=q.page_proofs[1];reject('swap source pages',()=>validate(root,q,item));}
{const q=clone(original);q.page_proofs[0].proof.sha256='0'.repeat(64);reject('wrong proof digest',()=>validate(root,q,item));}
const temp=path.join(root,`.cpho2007-contract-mutations-${process.pid}`);assert.ok(!fs.existsSync(temp));fs.mkdirSync(temp);
let seq=0;
const mutated=(ref,change)=>{const q=read(ref.path);change(q);const raw=Buffer.from(JSON.stringify(q)+'\n');const out=path.join(temp,`mutation${seq++}.json`);fs.writeFileSync(out,raw);return {...ref,path:path.relative(root,out).replaceAll('\\','/'),sha256:sha(raw),bytes:raw.length};};
const withShared=(change)=>{const q=clone(original);q.shared=mutated(q.shared,change);return q;};
try{
 const variants=[
  ['audit: rebase native missing ink to positive','audit',q=>q.original_physical_native_ink.newly_missing_native_ink_pixels=1],
  ['audit: erase actual script geometry failures','audit',q=>q.original_native_expression_relative_geometry.passed=false],
  ['audit: prose over mathematics','audit',q=>q.independent_actual_new_prose_native_text_ink.dark_prose_pixels_over_native_text=1],
  ['composition: remove source font binding','composition',q=>q.native_move_qa.font_programs_unchanged=false],
  ['assembly: nonzero Poppler diff','assembly',q=>q.Poppler144_RGB_difference_pixels=1],
  ['actual style: substituted face with same size','actual_style',q=>q.actual_glyph_style_checks[0].actual_font='Arial'],
  ['actual style: changed point size','actual_style',q=>q.actual_glyph_style_checks[0].actual_point_size=9],
  ['plan: transplanted original','plan',q=>q.original_sha256='0'.repeat(64)],
 ];
 for(const [label,field,change]of variants){const q=clone(original);q.page_proofs[0][field]=mutated(q.page_proofs[0][field],change);reject(label,()=>validate(root,q,item));}
 {const q=clone(original);q.page_proofs[1].audit=mutated(q.page_proofs[1].audit,a=>a.native_graphics_motion_audit.no_metric_bbox_cropping=false);reject('radical cropped metric rectangle rebased digest',()=>validate(root,q,item));}
 {const q=clone(original);q.page_proofs[15].audit=mutated(q.page_proofs[15].audit,a=>a.source_blank_page_preserved=false);reject('blank folio edited rebased digest',()=>validate(root,q,item));}
 {const q=withShared(s=>s.frozen_master_manifest=mutated(s.frozen_master_manifest,m=>m.files[0].sha256='0'.repeat(64)));reject('rebase entire trusted master manifest',()=>validate(root,q,item));}
 {const q=withShared(s=>s.supplemental_style_manifest=mutated(s.supplemental_style_manifest,m=>m.files[0].sha256='0'.repeat(64)));reject('rebase supplemental style manifest',()=>validate(root,q,item));}
 {const q=withShared(s=>s.negative_controls.pop());reject('drop actual negative fixture',()=>validate(root,q,item));}
 {const q=withShared(s=>s.negative_controls[0].fixture=s.negative_controls[1].fixture);reject('transplant different real negative PDF',()=>validate(root,q,item));}
 {const q=withShared(s=>s.negative_manifests[1]=mutated(s.negative_manifests[1],m=>m.controls[1].nonselected_graphics_changed_pixels=0));reject('rebase failed unselected graphic control',()=>validate(root,q,item));}
 {const q=withShared(s=>s.visual_review=mutated(s.visual_review,v=>v.pages[0].full_original_and_current_proof_144dpi_visually_reviewed=false));reject('unreviewed proof rebased visual manifest',()=>validate(root,q,item));}
 {const q=withShared(s=>s.authoring_closure=s.authoring_closure.filter(r=>!r.frozen_path.endsWith('/pdf_native_inline_reposition.py')));reject('missing frozen native guard',()=>validate(root,q,item));}
 {const q=withShared(s=>s.source_original_pdf.path='../outside.pdf');reject('path escape',()=>validate(root,q,item));}
}finally{
 // Only files created by this test in its verified owned scratch directory.
 assert.ok(path.resolve(temp).startsWith(root+path.sep));
 for(const file of fs.readdirSync(temp)){assert.match(file,/^mutation\d+\.json$/);fs.unlinkSync(path.join(temp,file));}fs.rmdirSync(temp);
}
console.log(JSON.stringify({passed:true,positive_editions:positive,rejected_mutations:rejected,actual_bad_pdf_controls:5}));

'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const validate=require('./helpers/cpho2003-scanned-solutions-publication.cjs'),root=path.resolve(__dirname,'..');
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8')),clone=x=>JSON.parse(JSON.stringify(x)),sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const items=read('tools/original_style_publication.json').filter(r=>r.audit_schema==='cpho2003-scanned-solutions-original-v1');assert.equal(items.length,2);let positives=0;const rejected=[];
for(const item of items){assert.equal(validate(root,read(item.qa),item).passed,true);positives++;}
const item=items.find(i=>i.language==='ko'),original=read(item.qa),reject=(label,fn)=>{assert.throws(fn,undefined,label);rejected.push(label);};
for(const[k,v]of [['original_math_retyped',true],['original_math_y_changed',true],['translated_point_sizes_fitted',true],['original_math_resampled',true],['original_figures_redrawn',true],['added_editorial_notes',1],['pages',6],['source_original_sha256','0'.repeat(64)],['original_source_page_groups_retained',false],['source_O_label_before_P_equations_retained',false]]){const q=clone(original);q[k]=v;reject(k,()=>validate(root,q,item));}
{const q=clone(original);q.page_proofs.pop();reject('drop final hybrid source page and its blank area',()=>validate(root,q,item));}
{const q=clone(original);q.page_proofs[0]=q.page_proofs[1];reject('swap original physical pages',()=>validate(root,q,item));}
{const q=clone(original);q.page_proofs[0].proof.sha256='0'.repeat(64);reject('wrong exact reviewed proof hash',()=>validate(root,q,item));}
const temp=path.join(root,`.cpho2003-ts-contract-mutations-${process.pid}`);assert.ok(!fs.existsSync(temp));fs.mkdirSync(temp);let index=0;
const mutate=(ref,change)=>{const value=read(ref.path);change(value);const raw=Buffer.from(JSON.stringify(value)+'\n'),out=path.join(temp,`mutation${index++}.json`);fs.writeFileSync(out,raw);return{...ref,path:path.relative(root,out).replaceAll('\\','/'),sha256:sha(raw),bytes:raw.length};};
const sharedChange=fn=>{const q=clone(original);q.shared=mutate(q.shared,fn);return q;};
try{
 const changes=[
  ['nonzero native ink loss','source_native_ink',q=>q.newly_missing_native_ink_pixels=1],
  ['missing original native glyph','source_native_ink',q=>q.missing_final_native_glyphs=[{c:'0'}]],
  ['source Group changed','source_QA',q=>q.original_pagegroup_unchanged=false],
  ['source encoded image changed','source_QA',q=>q.original_encoded_image_programs_masks_palettes_icc_and_declared_ctms_retained=false],
  ['source native font program changed','source_QA',q=>q.original_native_font_program_changes=[{}]],
  ['unreviewed source stationary ink loss','source_QA',q=>q.stationary_original_dark_ink_lost.pixels=1],
  ['missing original figure','source_QA',q=>q.independent_protected_source_ink_lost.pixels=1],
  ['new prose over original math','source_QA',q=>q.new_prose_overlap_original_or_replayed_nonlanguage_ink.pixels=1],
  ['nonzero single-source math RGB','source_QA',q=>q.actual_final_math_single_native_source_controls.records[0].changed_RGB_pixels=1],
  ['Poppler source ink loss','Poppler_QA',q=>q.stationary_source_ink_lost.pixels=1],
  ['Poppler math mismatch','Poppler_QA',q=>q.actual_single_source_math_controls[0].RGB_errors=1],
  ['claim incomplete raw receipt is publication-ready','Poppler_QA',q=>q.publication_ready=true],
  ['wrong new point size','actual_style',q=>q.glyphs[0].actual_point-=1],
  ['wrong new face outline','actual_style',q=>q.glyphs[0].actual_outline_matches_full_donor=false],
  ['wrong embedded glyph id','actual_style',q=>q.glyphs[0].actual_gid+=1],
  ['horizontal font fitting','actual_style',q=>q.glyphs[0].actual_trace_advance*=.8],
  ['title off original center','actual_style',q=>q.original_title_footer_centers[0].actual_center+=1],
  ['original clip bytes changed','composition',q=>q.header.native_digit_motion.native_atomic_clip_bytes_preserved=false],
  ['math expression Y changed','composition',q=>q.inline_math_replay.atoms[0].destination_rect[1]+=1],
  ['math bitmap rescaled','composition',q=>q.inline_math_replay.atoms[0].linear_scale=.9],
  ['drop radical paint piece','composition',q=>q.inline_math_replay.atoms.pop()],
  ['unnatural expanded word space','composition',q=>q.body_placements[0].word_space=10],
  ['nonzero final Poppler assembly difference','assembly',q=>q.Poppler144_RGB_difference_pixels=1],
  ['nonzero final MuPDF assembly difference','assembly',q=>q.fresh_separate_process_MuPDF4x_RGB_difference_pixels=1],
  ['wrong original math atom in layout','layout',q=>q.rows.find(r=>r.atoms.length).atoms[0].rect[1]+=1],
 ];
 for(const[label,key,change]of changes){const q=clone(original);q.page_proofs[0][key]=mutate(q.page_proofs[0][key],change);reject(label+' with rebased JSON hash',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.master_manifest=mutate(s.master_manifest,m=>m.files[0].sha256='0'.repeat(64)));reject('rebase entire trusted immutable master',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.source_classification=mutate(s.source_classification,m=>m.theory_solution_physical_pages=[5,6,7,8,9,10]));reject('invent source split',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.font_source_pins=mutate(s.font_source_pins,m=>m[0].full_font_copied=true));reject('export full installed donor',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.visual_review=mutate(s.visual_review,m=>m.pages[0].full_original_and_current_proof_144dpi_visually_reviewed=false));reject('unreviewed current full page',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.linked_prose_review=mutate(s.linked_prose_review,m=>m.all_original_point_width_advisory_overflows=[{}]));reject('ignore fixed-point prose overflow',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.authoring_closure=s.authoring_closure.filter(r=>!r.frozen_path.endsWith('/pdf_native_inline_reposition.py')));reject('missing unchanged native guard',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.negative_controls.pop());reject('drop actual bad PDF fixture',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.negative_controls[0].fixture=s.negative_controls[1].fixture);reject('transplant actual bad PDF fixture',()=>validate(root,q,item));}
 {const q=sharedChange(s=>s.source_original_pdf.path='../outside.pdf');reject('source path escape',()=>validate(root,q,item));}
 // All five exported actual bad PDFs are independently bound to the positive
 // proof they corrupt. None can be substituted as a reviewed positive page.
 const shared=read(original.shared.path);for(const c of shared.negative_controls){const q=clone(original),i=c.case==='missing-original-native-subscript'?6:2;q.page_proofs[i].proof=c.fixture;reject('actual bad PDF substituted: '+c.case,()=>validate(root,q,item));}
}finally{assert.ok(path.resolve(temp).startsWith(root+path.sep));for(const file of fs.readdirSync(temp)){assert.match(file,/^mutation\d+\.json$/);fs.unlinkSync(path.join(temp,file));}fs.rmdirSync(temp);}
const result={passed:true,positive_editions:positives,rejected_mutations:rejected.length,rejected_labels:rejected,actual_bad_PDF_controls:5};
console.log(JSON.stringify(result));

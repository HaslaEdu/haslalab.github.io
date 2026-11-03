'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const SCHEMA='cpho2007-native-inline-original-v1';
const SOURCE='2e30b56ab9274363686cbf5bc1ef7532dcf579e0703de2c01098b003ab70cdd9';
const MASTER='10803de2bf7546f9e3cf998edde220f561eee73317f38e58c1f91eda51befaf4';
const READY='84ef18623536aa27bffbd6765502de38627f33c5c429037fe243b776de8cf7e8';
const STYLE_MANIFEST='8597f825fb701558f06d640af149f14e02402ca0a5d478421141e524d224d7cd';
const EDITIONS={ko:{sha256:'1676a8ed09162db5081baa3e5eb8a1da5d5cae2db55e728b7adb359b708ae8e5',bytes:24044591},en:{sha256:'cd10904adce375d359c90b682d37d23715b0fe4227aa2245e0b1316acd1b9dd5',bytes:3255502}};
const GUARD='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f';
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const yes=(o,ks)=>{for(const k of ks)assert.equal(o[k],true,k);};
const zero=(o,ks)=>{for(const k of ks)assert.equal(o[k],0,k);};
const empty=(o,ks)=>{for(const k of ks)assert.deepEqual(o[k],[],k);};
const digest=x=>assert.match(x,/^[a-f0-9]{64}$/);
module.exports=function validateCpho2007NativeInline(root,qa,item){
 root=fs.realpathSync(root);
 const bytes=ref=>{
  assert.ok(ref&&typeof ref.path==='string'&&!path.isAbsolute(ref.path));
  const absolute=fs.realpathSync(path.resolve(root,ref.path));
  const relative=path.relative(root,absolute);assert.ok(relative&&!relative.startsWith('..')&&!path.isAbsolute(relative),'evidence must stay inside staging root');
  const raw=fs.readFileSync(absolute);digest(ref.sha256);assert.equal(sha(raw),ref.sha256,ref.path);assert.equal(raw.length,ref.bytes,ref.path);return raw;
 };
 const read=ref=>JSON.parse(bytes(ref));
 assert.equal(item.audit_schema,SCHEMA);assert.equal(qa.schema,SCHEMA);assert.equal(qa.status,'READY');
 assert.equal(qa.year,2007);assert.equal(qa.competition,'cpho');assert.equal(qa.kind,'TS');assert.ok(Object.hasOwn(EDITIONS,item.language));
 for(const k of ['file','sha256','bytes','pages','language'])assert.equal(qa[k],item[k]);
 assert.equal(item.file,`CPhO_2007_TS_${item.language.toUpperCase()}.pdf`);assert.equal(item.pages,16);
 for(const [k,v]of Object.entries(EDITIONS[item.language]))assert.equal(item[k],v);
 assert.equal(qa.source_original_sha256,SOURCE);assert.deepEqual(qa.source_physical_pages,Array.from({length:16},(_,i)=>i+5));
 for(const k of ['original_math_retyped','original_math_resampled','original_math_y_changed','translated_point_sizes_fitted'])assert.equal(qa[k],false,k);
 zero(qa,['added_editorial_notes']);yes(qa,['original_blank_final_folio20_retained','original_unmapped_comparison_square_on_source18_retained']);
 const shared=read(qa.shared);assert.equal(shared.schema,SCHEMA);assert.equal(shared.source_sha256,SOURCE);
 assert.equal(shared.frozen_master_manifest.sha256,MASTER);const master=read(shared.frozen_master_manifest);
 assert.equal(master.source_sha256,SOURCE);assert.equal(master.files.length,612);
 const leaves=new Map();for(const row of master.files){const k=row.path.replaceAll('\\','/');assert.ok(!leaves.has(k)&&!k.startsWith('/')&&!k.split('/').includes('..'));digest(row.sha256);assert.ok(Number.isInteger(row.bytes)&&row.bytes>0);leaves.set(k,row);}
 const pinned=(ref,expected)=>{
  assert.equal(ref.frozen_path,expected);const leaf=leaves.get(expected);assert.ok(leaf,expected);assert.equal(ref.sha256,leaf.sha256,expected);assert.equal(ref.bytes,leaf.bytes,expected);return bytes(ref);
 };
 const evidence=(ref,expected)=>JSON.parse(pinned(ref,expected));
 const f='authoring-frozen/';
 assert.equal(shared.source_ready.sha256,READY);const ready=read(shared.source_ready);assert.equal(ready.status,'READY_PRIVATE_FOR_PARENT_PUBLICATION');assert.equal(ready.snapshot_manifest_sha256,MASTER);assert.equal(ready.snapshot_files,612);assert.equal(ready.source_sha256,SOURCE);assert.equal(ready.combined_verified_pages,32);
 yes(ready,['native_script_graphics_original_font_image_and_actual_prose_over_math_ink_audits_passed','all5_actual_negative_controls_rejected','original_blank_final_folio20_retained','original_unmapped_comparison_square_on_source18_retained','original_math_CID_font_point_paint_Y_and_graphic_programs_preserved']);
 zero(ready,['combined_fresh_MuPDF4x_RGB_difference_pixels','combined_Poppler144_RGB_difference_pixels']);
 assert.equal(qa.font_policy,ready.new_Hangul_font_roles);
 assert.equal(sha(pinned(shared.source_original_pdf,f+'inputs/CPhO_2007_Chinese_original.pdf')),SOURCE);
 assert.equal(bytes(shared.source_original_pdf).subarray(0,4).toString(),'%PDF');
 const slots=evidence(shared.source_slots,f+'inputs/original-all20-source-slots.json');assert.equal(slots.source_sha256,SOURCE);assert.equal(slots.pages.length,20);
 const fontPins=evidence(shared.external_font_source_pins,f+'external-font-source-pins.json');assert.equal(fontPins.length,5);for(const pin of fontPins){assert.equal(pin.full_font_copied,false);digest(pin.sha256);}
 const fontHashes=new Set(fontPins.map(p=>p.sha256));
 evidence(shared.atomic_inline,f+'tools/ko/cpho/2007/natural/atomic-inline.json');
 const closure=new Map();for(const ref of shared.authoring_closure){assert.match(ref.frozen_path,/^authoring-frozen\/(engine|drivers|authoring)\//);assert.match(ref.frozen_path,/\.(py|json|tsv|txt)$/);assert.ok(!closure.has(ref.frozen_path));pinned(ref,ref.frozen_path);closure.set(ref.frozen_path,ref);}
 assert.equal(closure.get(f+'engine/pdf_native_inline_reposition.py').sha256,GUARD);
 assert.ok(closure.has(f+'engine/cpho2007_complete_vector_motion.py'));
 const visual=evidence(shared.visual_review,f+'authoring/full144-visual-review-complete.json');assert.equal(visual.source_sha256,SOURCE);assert.equal(visual.status,'ALL32_CURRENT_FULL_PAGE_VISUALS_REVIEWED');assert.equal(visual.pages.length,32);assert.equal(visual.total_proof_pages,32);assert.equal(visual.pages_per_language,16);assert.equal(ready.visual_review_manifest_sha256,shared.visual_review.sha256);
 const visualKeys=new Set(visual.pages.map(p=>p.language+':'+p.source_page));assert.equal(visualKeys.size,32);
 const summary=evidence(shared.assembly_summary,'verification/summary.json');yes(summary,['passed','native_content_font_glyph_and_image_programs_identical']);zero(summary,['MuPDF4x_RGB_difference_pixels','Poppler144_RGB_difference_pixels']);assert.equal(summary.pages,32);assert.equal(summary.individual_pages.length,32);
 assert.equal(shared.supplemental_style_manifest.sha256,STYLE_MANIFEST);const supplement=read(shared.supplemental_style_manifest);assert.equal(supplement.schema,'cpho2007-supplemental-style-manifest-v1');assert.equal(supplement.source_sha256,SOURCE);assert.equal(supplement.master_manifest_sha256,MASTER);assert.equal(supplement.files.length,31);assert.equal(supplement.full_installed_font_programs_exported,false);
 const styles=new Map(supplement.files.map(row=>[row.path,row]));assert.equal(styles.size,31);const styleDriver=styles.get('supplemental-authoring/audit-cpho2007-publication-actual-style.py');assert.equal(shared.supplemental_style_driver.sha256,styleDriver.sha256);assert.equal(shared.supplemental_style_driver.bytes,styleDriver.bytes);bytes(shared.supplemental_style_driver);
 assert.equal(qa.page_proofs.length,16);
 for(const [i,p]of qa.page_proofs.entries()){
  const n=i+5,lang=item.language,stem=f+`natural/2007/${lang}/page${String(n).padStart(2,'0')}`;
  assert.equal(p.page,i+1);assert.equal(p.source_page,n);assert.equal(pinned(p.proof,stem+'.pdf').subarray(0,4).toString(),'%PDF');
  const a=evidence(p.audit,stem+'.audit.json');yes(a,['passed']);assert.equal(a.output_sha256,p.proof.sha256);
  const assembly=evidence(p.assembly,`verification/${lang}-page${String(n).padStart(2,'0')}.json`);
  yes(assembly,['passed','native_page_content_stream_bytes_identical','all_native_glyph_traces_and_font_programs_identical','all_image_programs_identical']);zero(assembly,['fresh_separate_process_MuPDF4x_RGB_difference_pixels','Poppler144_RGB_difference_pixels']);assert.equal(assembly.language,lang);assert.equal(assembly.source_page,n);assert.equal(assembly.edition_page,i+1);assert.equal(assembly.edition_sha256,item.sha256);assert.equal(assembly.reviewed_proof_sha256,p.proof.sha256);
  const visualRow=visual.pages.find(v=>v.language===lang&&v.source_page===n);yes(visualRow,['passed','full_original_and_current_proof_144dpi_visually_reviewed']);assert.equal(visualRow.visual_review_pending,false);assert.equal(visualRow.dpi,144);assert.equal(visualRow.proof_sha256,p.proof.sha256);assert.equal(assembly.reviewed_proof_poppler_png_sha256,visualRow.png_sha256);
  const pngName=visualRow.png.split(/[\\/]/).at(-1);assert.equal(leaves.get(f+`reviewed-proofs144/${lang}/${pngName}`).sha256,visualRow.png_sha256);assert.equal(leaves.get(f+`source-renders/page${String(n).padStart(2,'0')}.png`).sha256,visualRow.source_png_sha256);
  const sr=summary.individual_pages.find(r=>r.language===lang&&r.source_page===n);assert.equal(sr.proof_sha256,p.proof.sha256);assert.equal(sr.audit_sha256,p.audit.sha256);yes(sr,['full144_visual_review_passed','strict_page_QA_passed']);
  const modules=evidence(p.loaded_modules,`verification/${lang}-page${String(n).padStart(2,'0')}-loaded-modules.json`);assert.ok(modules.length>0);for(const mod of modules){const name=mod.path.split(/[\\/]/).at(-1);assert.equal(leaves.get(f+'engine/'+name).sha256,mod.sha256);assert.equal(closure.get(f+'engine/'+name).sha256,mod.sha256);}
  if(n===20){
   assert.equal(p.composition,undefined);assert.equal(p.actual_style,undefined);assert.equal(a.source_page,20);assert.equal(a.language,lang);assert.equal(a.source_sha256,SOURCE);yes(a,['source_blank_page_preserved','native_font_programs_unchanged','unchanged_decoded_native_content','fresh_MuPDF_4x_RGB_pixels_equal']);assert.equal(a.source_folio20_glyphs.filter(g=>g.c.trim()).map(g=>g.c).join(''),'20');assert.equal(a.output_sha256,'2454c6f53f84729748344df34f96c519350edfb5ada8f32d56d78e441218d34a');continue;
  }
  const q=evidence(p.composition,stem+'.qa.json'),plan=evidence(p.plan,stem+'.plan.json');assert.equal(q.output_sha256,p.proof.sha256);assert.equal(q.original_sha256,SOURCE);assert.equal(plan.original_sha256,SOURCE);assert.equal(plan.year,2007);assert.equal(plan.language,lang);assert.equal(plan.page,n);assert.equal(q.input_sha256,a.immutable_input_sha256);assert.equal(plan.input_sha256,a.immutable_input_sha256);
  yes(q,['no_font_scaling','original_native_ascii_latin_math_programs_retained','initial_source_slot_suffix_verified']);empty(q,['caption_regions_pending']);zero(q,['retained_native_style_or_geometry_mismatches_after_insertion','empty_new_batang_outlines','new_non_hangul_font_replacements']);assert.match(q.word_spacing,/quarter.*original prose point size/);
  for(const line of q.lines){assert.ok(line.new_right<=line.rect[2]+.01);for(const gap of line.gaps)assert.ok(gap.new_gap>=0&&gap.new_gap<=3.781);}
  for(const row of q.initial_fixed_slot_source_prose_order)yes(row,['exact_prose_trace_suffix_verified']);
  const stages=[q.native_move_qa];if(q.picture_language_and_caption_stage)stages.push(q.picture_language_and_caption_stage.native_move_qa);
  for(const motion of stages){yes(motion,['passed','font_programs_unchanged','original_form_streams_unchanged','original_image_streams_unchanged','native_vector_path_bytes_preserved','native_atomic_clip_bytes_preserved']);empty(motion,['native_glyph_mismatches']);zero(motion,['unexpected_glyphs','max_position_error_y_pt','max_visible_position_error_y_pt']);assert.ok(motion.max_visible_position_error_x_pt<=.001);}
  assert.equal(a.year,2007);assert.equal(a.language,lang);assert.equal(a.page,n);zero(a,['changed_pixels_outside_old_and_new_text_ink','unexpected_Hangul_visibility_components','NUL_glyphs']);assert.equal(a.outside_bbox,null);empty(a,['remaining_regular_NotoSerif_Hangul']);yes(a,['verified_original_native_ink_passed','original_font_programs_and_names_retained','original_image_programs_retained','page_group_preserved','colorspace_resources_preserved','native_move_stages_passed','fresh_process_RGB_render']);zero(a.hangul_visibility,['flagged_components']);
  const ink=a.original_physical_native_ink;yes(ink,['passed']);assert.equal(ink.output_sha256,p.proof.sha256);assert.ok(ink.protected_native_glyphs>0);zero(ink,['newly_missing_native_ink_pixels']);empty(ink,['missing_requested_source_glyphs','missing_final_native_glyphs']);yes(ink.source_outline_audit,['passed']);empty(ink.source_outline_audit,['missing_source_outline_signatures']);
  const geo=a.original_native_expression_relative_geometry;yes(geo,['passed']);assert.equal(geo.final_sha256,p.proof.sha256);empty(geo,['glyph_signature_or_position_errors','relative_geometry_failures']);for(const row of [...geo.script_base_pairs,...geo.reviewed_expression_groups])yes(row,['passed']);
  const graphics=a.native_graphics_motion_audit;zero(graphics,['changed_nonselected_native_graphical_pixels']);for(const image of a.image_palette_icc_mask_and_motion_audits){yes(image,['full_palette_icc_mask_image_graph_preserved']);assert.ok(image.rect_preserved||image.rect_matches_declared_native_math_dx);}
  if(n===6){yes(graphics,['actual_selected_path_paint_objects_only','no_metric_bbox_cropping','no_rectangle_or_threshold_exception']);assert.equal(graphics.selected_native_math_groups.length,16);for(const stroke of graphics.selected_native_math_groups){assert.equal(stroke.kind,'exact original radical stroke object');yes(stroke,['path_operands_and_paint_unchanged','stroke_style_unchanged']);digest(stroke.path_program_sha256);assert.deepEqual(stroke.stroke_style.color,[0,0,0]);assert.equal(stroke.operator_indices.length,3);assert.equal(stroke.target_operator_indices.length,3);assert.ok(Number.isFinite(stroke.dx));}}
  else if(graphics.changed_actual_inline_math_graphical_pixels>0)assert.ok(graphics.selected_native_math_groups.length>0);
  const collision=evidence(p.prose_native_text_collision,stem+'.prose-native-text-overlap.json');assert.deepEqual(collision,a.independent_actual_new_prose_native_text_ink);yes(collision,['passed']);assert.equal(collision.sha256,p.proof.sha256);zero(collision,['dark_prose_pixels_over_native_text']);yes(collision.prose_outline_match,['passed']);empty(collision.prose_outline_match,['missing_source_outline_signatures']);yes(collision.native_control_erasure_qa,['passed']);
  yes(a.new_prose_over_native_graphics,['passed']);zero(a.new_prose_over_native_graphics,['new_hangul_dark_pixels_over_native_foreground']);yes(a.new_prose_over_native_graphics.source_outline_match,['passed']);empty(a.new_prose_over_native_graphics.source_outline_match,['missing_source_outline_signatures']);
  const styleLeaf=styles.get(`actual-style/${lang}-page${String(n).padStart(2,'0')}.json`);assert.ok(styleLeaf);assert.equal(p.actual_style.sha256,styleLeaf.sha256);assert.equal(p.actual_style.bytes,styleLeaf.bytes);const style=read(p.actual_style);
  assert.equal(style.schema,'cpho2007-actual-embedded-prose-style-v1');yes(style,['passed','all_actual_embedded_outlines_match_pinned_donors','all_source_roles_and_point_sizes_and_paint_verified']);assert.equal(style.original_point_sizes_scaled,false);assert.equal(style.original_baselines_changed,false);assert.equal(style.full_installed_font_programs_exported,false);assert.equal(style.source_sha256,SOURCE);assert.equal(style.source_page,n);assert.equal(style.language,lang);assert.equal(style.proof_sha256,p.proof.sha256);assert.equal(style.source_plan_sha256,p.plan.sha256);assert.equal(style.source_slot_inventory_sha256,shared.source_slots.sha256);assert.equal(style.actual_nonspace_glyphs_checked,collision.translated_prose_glyphs);assert.equal(style.actual_glyph_style_checks.length,style.actual_nonspace_glyphs_checked);assert.equal(style.actual_centered_heading_checks.length,plan.centered_lines.length);for(const center of style.actual_centered_heading_checks){yes(center,['passed']);assert.ok(center.error_pt<=.001);const c=plan.centered_lines.find(r=>r.baseline===center.baseline);assert.ok(c);assert.equal(center.source_center,c.center);assert.ok(Math.abs((center.actual_left+center.actual_right)/2-center.source_center)<=.001);}
  for(const g of style.actual_glyph_style_checks){yes(g,['actual_embedded_outline_matches_pinned_full_role_donor']);assert.ok(g.actual_gid>=0);assert.equal(g.actual_point_size,g.source_point_size);assert.ok(Math.abs(g.actual_origin[1]-g.source_baseline)<=.002);assert.equal(g.actual_render_mode,0);assert.deepEqual(g.actual_fill_color.map(v=>Math.round(v*255)),g.source_original_color);assert.equal(g.actual_fill_opacity,1);assert.ok(fontHashes.has(g.donor_full_face_sha256));digest(g.actual_embedded_program_sha256);digest(g.decomposed_outline_sha256);assert.ok(g.source_slots.length>0);let paintWitness=false;for(const id of g.source_slots){const slot=slots.pages[n-1].slots.find(s=>s.id===id);assert.ok(slot);assert.equal(slot.size,g.source_point_size);assert.equal(slot.family,g.source_family);assert.ok(Math.abs(slot.origin[1]-g.source_baseline)<=.002);paintWitness ||= slot.source_characters.some(c=>{const v=c.color??slot.color;return JSON.stringify([(v>>16)&255,(v>>8)&255,v&255])===JSON.stringify(g.source_original_color);});}assert.ok(paintWitness);if(lang==='en')assert.ok(['SimSun','SimHei'].includes(g.actual_font));if(lang==='ko'&&/[가-힣]/.test(g.character)&&g.source_family==='serif')assert.equal(g.actual_font,'Batang');}
 }
 assert.equal(shared.negative_manifests.length,2);const neg=evidence(shared.negative_manifests[0],f+'negative-controls/negative-control-manifest.json');const radical=evidence(shared.negative_manifests[1],f+'negative-controls/page06-exact-radical-negative-control-manifest.json');yes(neg,['all_rejected']);yes(radical,['all_rejected']);assert.equal(neg.controls.length,3);assert.equal(radical.controls.length,2);
 assert.equal(shared.negative_controls.length,5);assert.deepEqual(shared.negative_controls.map(c=>c.type),['erased-native-E','prose-over-native-E','native-comma-geometry','radical-stroke-style','unselected-graphic']);
 for(const [i,c]of shared.negative_controls.entries()){
  const raw=pinned(c.fixture,f+'negative-controls/'+c.fixture.frozen_path.split('/').at(-1));assert.equal(raw.subarray(0,4).toString(),'%PDF');const control=i<3?neg.controls[i]:radical.controls[i-3];assert.equal(control.rejected,true);assert.equal(c.fixture.sha256,control.fixture_sha256||control.proof_sha256);
  if(i<3){const report=evidence(c.report,f+'negative-controls/'+c.report.frozen_path.split('/').at(-1));assert.equal(report.passed,false);assert.equal(report.output_sha256||report.sha256,c.fixture.sha256);if(i===0)assert.ok(report.missing_final_native_glyphs.some(g=>g.c==='E'));if(i===1){assert.ok(report.dark_prose_pixels_over_native_text>0);yes(report.prose_outline_match,['passed']);yes(report.native_control_erasure_qa,['passed']);}if(i===2){assert.equal(report.original_native_expression_relative_geometry.passed,false);assert.ok(report.original_native_expression_relative_geometry.reviewed_expression_groups.some(g=>g.passed===false&&g.label==='Original complete inline expression 5-6-0'&&g.physical_glyphs===2&&g.matched_glyphs===2&&g.relative_x_spread_pt>100));}}
  if(i===3)assert.match(control.reason,/Original radical stroke style changed/);
  if(i===4){assert.ok(control.nonselected_graphics_changed_pixels>0);assert.equal(control.report.changed_nonselected_native_graphical_pixels,control.nonselected_graphics_changed_pixels);assert.equal(control.report.selected_native_math_groups.length,16);}
 }
 return {passed:true,language:item.language,pages:16,master_files:612,source_sha256:SOURCE};
};

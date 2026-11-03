const assert=require('node:assert/strict'),crypto=require('node:crypto');
const SOURCE='959174ab5ddc8be71c251c8fe95a12c810ba730edbcbbef3b771197e32929a4a';
const MEASUREMENT='9f7397f1437c9c78b383d2f6624d1cee64472930f849cad6a7f972bd2625ecb4';
const CURVE='8e032abc9060b2be0a2af658cb7b1a6e2edb333aa0b7a228e40bdd60c1705799';
const MAP='ad5990b8ceb44b2dabbfc7a53ce8c344907d4b5b243f58e4e7cd88fba0dfde8a';
const SEMANTIC='bbc753360d5c243a4ca31fede8047b67b212cecea704bfae275521e82b8082e4';
const AFFINE='aecd02348c9130307402f372cbe7e740f15e1210759b9acc3bf2970f69e232d2';
const one=(rows,key,value)=>{const found=rows.filter(r=>r[key]===value);assert.equal(found.length,1);return found[0];};
module.exports=function validate(q,contact,d,qa) {
  assert.equal(q.source_sha256,SOURCE);assert.equal(contact.source_bound_prose_x_affine_only,true);
  const a=q.actual_prose_underline_coverage_and_style_audit;
  assert.equal(a.passed,true);assert.equal(a.proof_sha256,q.output_sha256);
  assert.equal(a.source_sha256,SOURCE);assert.equal(a.page,q.page);
  assert.equal(a.measurement_code_sha256,MEASUREMENT);assert.equal(a.actual_curve_reader_sha256,CURVE);
  for(const [name,digest]of [['verify_prose_underline_and_style_icho2024.py',MEASUREMENT],['actual_prose_ink_icho2024_style.py',CURVE],['verify_semantic_bindings_icho2024.py',SEMANTIC],['prose_underline_affine_icho2024.py',AFFINE]]) {
    assert.ok(qa.authoring_programs.some(p=>p.path.endsWith('/'+name)&&p.sha256===digest));
  }
  assert.ok(a.underline_coverage_tolerance_pt>0&&a.underline_coverage_tolerance_pt<=.001);
  assert.ok(a.source_native_vector_tolerance_pt>0&&a.source_native_vector_tolerance_pt<=1e-7);
  assert.equal(a.protected_native_ink_contact_pixels,0);assert.equal(a.all_actual_curve_bboxes_match_requested_full_font_and_matrix,true);
  const semantic=q.independent_source_semantic_style_audit;
  assert.equal(semantic.passed,true);assert.equal(semantic.proof_sha256,q.output_sha256);
  assert.equal(semantic.source_sha256,SOURCE);assert.equal(semantic.mapping_sha256,MAP);assert.equal(semantic.program_sha256,SEMANTIC);
  for(const key of ['all_requested_font_roles_bound_to_actual_original_source_styles','exact_original_sizes_and_raw_prose_baseline_pool_membership_preserved','no_other_bold_or_italic_changes'])assert.equal(semantic[key],true);
  const row=one(a.underline_rows,'id',contact.id),mapped=one(semantic.semantic_mappings,'index',d.semantic_mapping_index);
  assert.equal(mapped.target_literal,d.target_text);assert.equal(mapped.target_fragment_id,d.slot_id);assert.equal(mapped.target_font_role,d.target_font_role);
  assert.ok(Math.abs(mapped.source_pointsize-d.target_pointsize)<=.001);
  assert.ok(Math.abs(mapped.source_original_baseline-d.target_baseline)<=.001);
  assert.ok(Math.abs(mapped.actual_target_baseline-d.target_baseline)<=.001);
  assert.equal(row.actual_native_path_index,contact.source_path_index);
  for(const key of ['original_y_thickness_black_stroke_and_paint_preserved','actual32x_vertical_stroke_sample_byte_equal','source_English_glyph_path_guards_verified','all_Korean_used_glyph_GIDs_outlines_and_hmtx_match_pinned_full_font'])assert.equal(row[key],true);
  assert.ok(row.actual32x_samples.length);
  for(const sample of row.actual32x_samples) {
    assert.equal(sample.byte_identical,true);assert.deepEqual(sample.source,sample.candidate);
    assert.ok(sample.source[1].length&&Math.min(...sample.source[1])<255);
  }
  const program=d.source_program;
  assert.equal(program.source_text.trim(),mapped.source_English.trim());assert.equal(program.slot_id,d.original_source_slot_id);
  assert.equal(program.source_is_pure_top_level_horizontal_m_l_S,true);
  assert.deepEqual(program.source_operator_names,['m','l','S']);assert.deepEqual(program.source_operator_indices,d.operator_indices);
  assert.equal(d.paint_operator,'S');assert.equal(d.source_construction_and_paint_bytes_preserved,true);
  assert.equal(crypto.createHash('sha256').update(Buffer.from(program.source_construction_and_paint_fragment_latin1,'latin1')).digest('hex'),program.source_construction_and_paint_fragment_sha256);
  const drawing=program.source_drawing;
  assert.ok(Math.abs(drawing.width-.398499995470047)<=1e-9);assert.deepEqual(drawing.color,[0,0,0]);assert.equal(drawing.fill,null);
  assert.deepEqual(drawing.lineCap,[0,0,0]);assert.equal(drawing.lineJoin,0);
  const affine=q.source_prose_underline_affine_audit;
  assert.equal(affine.passed,true);assert.equal(affine.source_sha256,SOURCE);assert.equal(affine.program_sha256,AFFINE);
  assert.equal(affine.input_moved_sha256,q.native_motion_before_prose_underline_affine_sha256);
  assert.equal(affine.all_other_source_content_bytes_preserved_by_exact_splices,true);
  const p=one(affine.paths,'id',contact.id);
  assert.equal(p.source_fragment_sha256,program.source_construction_and_paint_fragment_sha256);
  assert.equal(p.source_fragment_literal_preserved,true);assert.equal(p.source_y_and_vertical_stroke_scale_unchanged,true);
  assert.deepEqual(p.source_operator_names,['m','l','S']);
  const src=d.source_rect,target=d.target_rect;
  assert.deepEqual(src,program.source_exact_path_rect);assert.deepEqual(src,p.source_rect);assert.deepEqual(src,row.source_rect);assert.deepEqual(target,p.target_rect);
  const matrix=p.page_x_affine;
  assert.deepEqual(matrix.slice(1,4),[0,0,1]);assert.equal(matrix[5],0);assert.ok(Number.isFinite(matrix[0])&&matrix[0]>0);
  assert.ok(Math.abs(matrix[0]-d.x_scale)<=1e-9);
  for(const i of [0,2]) {
    assert.ok(Math.abs(src[i]*matrix[0]+matrix[4]-target[i])<=1e-7);
    assert.ok(Math.abs(row.actual_underline_bbox[i]-target[i])<=.001);
    assert.ok(Math.abs(row.actual_underline_bbox[i]-row.actual_emphasized_glyph_curve_union_bbox[i])<=.001);
  }
  for(const i of [1,3]){assert.equal(src[i],target[i]);assert.ok(Math.abs(row.actual_underline_bbox[i]-src[i])<=1e-7);}
  assert.ok(row.actual_horizontal_ink_coverage_error_pt>=0&&row.actual_horizontal_ink_coverage_error_pt<=.001);
};

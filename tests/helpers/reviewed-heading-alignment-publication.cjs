const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

module.exports = function validate(root, qa, item) {
  const evidence = ref => {
    const file = path.resolve(root, ref.path);
    assert.ok(file.startsWith(root + path.sep));
    const raw = fs.readFileSync(file);
    assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), ref.sha256, ref.path);
    return JSON.parse(raw);
  };
  const yes = (q, keys) => { for (const k of keys) assert.equal(q[k], true, k); };
  const zero = (q, keys) => { for (const k of keys) assert.equal(q[k], 0, k); };
  assert.equal(qa.status, 'READY');
  for (const k of ['file','language','sha256','bytes','pages']) assert.equal(qa[k],item[k]);
  yes(qa,['complete_existing_headings_moved_horizontally_only','fonts_points_paint_baselines_math_images_and_other_page_content_retained']);
  const baseline = evidence(qa.baseline_publication);
  const helper = {
    'natural-spacing-v2':'natural-spacing-publication.cjs',
    'natural-spacing-reviewed':'natural-spacing-reviewed-publication.cjs',
    'reviewed-figure-language-v1':'reviewed-figure-language-publication.cjs'
  }[qa.baseline_item.audit_schema];
  assert.ok(helper,qa.baseline_item.audit_schema);
  assert.equal(qa.baseline_item.file,item.file);
  assert.equal(qa.baseline_item.pages,item.pages);
  require('./'+helper)(root,baseline,qa.baseline_item);
  const ready=evidence(qa.source_ready); assert.equal(ready.schema,'reviewed-heading-alignment-v1');
  const assembly=evidence(qa.assembly_qa);yes(assembly,['passed']);
  assert.equal(assembly.sha256,item.sha256);assert.equal(assembly.bytes,item.bytes);
  assert.equal(assembly.pages.length,item.pages);
  const visual=evidence(qa.visual_review);assert.equal(visual.pages.length,item.pages);
  let count=0;
  assert.equal(qa.page_proofs.length,item.pages);
  for (const [index,page] of qa.page_proofs.entries()) {
    assert.equal(page.page,index+1);
    const joined=assembly.pages[index];assert.equal(joined.proof_sha256,page.proof_sha256);
    yes(joined,['passed','actual_font_programs_and_glyph_metadata_identical','original_encoded_images_masks_icc_and_ctms_identical','page_group_identical']);
    zero(joined,['mupdf_4x_changed_pixels','poppler_144dpi_changed_pixels']);
    assert.equal(visual.pages[index].proof_sha256,page.proof_sha256);
    yes(visual.pages[index],['reviewed']);
    if (!page.alignment_qa) continue;
    const q=evidence(page.alignment_qa);yes(q,['passed']);
    assert.equal(q.proof_sha256,page.proof_sha256);
    assert.equal(q.source_pdf_sha256,qa.baseline_item.sha256);
    assert.equal(qa.authoring_snapshot_sha256['heading-alignment/natural-spacing/authoring/scripts/producer-versions/'+q.producer_sha256+'.py'],q.producer_sha256);
    const move=q.native_move_qa;
    yes(move,['passed','font_programs_unchanged','original_image_streams_unchanged','native_vector_path_bytes_preserved']);
    assert.deepEqual(move.native_glyph_mismatches,[]);
    if(q.stationary_original_nonpainting_clipped_spaces) {
      const blank=q.stationary_original_nonpainting_clipped_spaces;
      yes(blank,['passed','original_encoded_CIDs_and_native_font_programs_retained','all_original_clipped_space_CIDs_remain_stationary']);
      assert.equal(blank.actual_4x_nonwhite_pixels,0);
      for(const glyph of blank.glyphs) assert.equal(glyph.c.trim(),'');
    }
    const ink=q.pixel_audit;yes(ink,['passed','independent_actual_original_encoded_CID_references']);
    assert.equal(ink.mask_derived_from_observed_difference,false);
    zero(ink,['changed_pixels_outside_source_and_target_heading_ink','missing_target_native_heading_ink_pixels','missing_source_reference_ink_pixels','unexpected_pixels_inside_independent_heading_reference']);
    for (const ref of [ink.source_reference,ink.target_reference,ink.stationary_background_reference]) {
      yes(ref,['passed','original_encoded_CIDs_and_native_font_programs_retained','no_unicode_retyping','original_text_show_bytes_and_all_original_advances_and_clips_replayed']);
      yes(ref.metadata_audit,['passed']);assert.deepEqual(ref.metadata_audit.native_glyph_mismatches,[]);
    }
    const control=ink.independent_full_native_control;
    yes(control,['passed','original_source_entire_native_text_shows_replayed','not_the_publication_producer','source_text_show_bytes_retained','only_declared_complete_heading_shows_shifted']);
    assert.deepEqual(control.metadata_audit.native_glyph_mismatches,[]);
    assert.equal(control.metadata_audit.unexpected_glyphs,0);
    for (const heading of q.headings) {
      yes(heading,['passed']);assert.ok(heading.glyphs>0);
      assert.ok(Math.abs(heading.actual_center-heading.source_nonspace_center)<=.001);
      assert.ok(Math.abs(heading.center_error_pt)<=.001);
    }
    count+=q.headings.length;
  }
  assert.equal(count,qa.aligned_headings);
  const negative=evidence(qa.negative_control);yes(negative,['passed','publication_pdf_unmodified','independent_original_source_center_rejected','native_metadata_and_other_graphics_retained']);
  assert.equal(negative.actual_heading_shift_pt,-8);
  assert.ok(Math.abs(negative.rejected_center_error_pt+8)<=.001);
  assert.equal(negative.canonical_proof_sha256,ready.editions.find(e=>e.file==='IZhO_2012_T_KO.pdf').proofs[1].proof_sha256);
  for (const [file,digest] of Object.entries(qa.authoring_snapshot_sha256)) {
    const raw=fs.readFileSync(path.join(root,qa.authoring_snapshotroot,file));
    assert.equal(crypto.createHash('sha256').update(raw).digest('hex'),digest,file);
  }
};

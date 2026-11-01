const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

module.exports = function validateNativeOriginalPublication(root, qa, item) {
  const rawEvidence = ref => {
    assert.ok(ref && typeof ref.path === 'string');
    const absolute = path.resolve(root, ref.path);
    assert.ok(absolute.startsWith(root + path.sep));
    const raw = fs.readFileSync(absolute);
    assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), ref.sha256, ref.path);
    return raw;
  };
  const evidence = ref => JSON.parse(rawEvidence(ref));
  const yes = (obj, keys) => { for (const key of keys) assert.equal(obj[key], true, key); };
  const zero = (obj, keys) => { for (const key of keys) assert.equal(obj[key], 0, key); };
  const empty = (obj, keys) => { for (const key of keys) assert.deepEqual(obj[key], [], key); };
  assert.equal(qa.status, 'READY');
  for (const key of ['file','sha256','bytes','pages','language']) assert.equal(qa[key], item[key]);
  for (const key of ['original_math_retyped','original_math_resampled','original_math_y_changed','translated_point_sizes_fitted']) assert.equal(qa[key], false, key);
  assert.equal(qa.added_editorial_notes, 0);
  const ready = evidence(qa.source_ready);
  assert.equal(ready.status, 'READY');
  assert.equal(ready.schema, 'native-original-preserved-v1');
  assert.equal(ready.source_original_sha256, qa.source_original_sha256);
  const visual = evidence(qa.visual_review);
  const assembly = evidence(qa.assembly_qa);
  assert.equal(visual.source_sha256, qa.source_original_sha256);
  assert.equal(assembly.passed, true);
  assert.equal(assembly.sha256, item.sha256);
  assert.equal(assembly.bytes, item.bytes);
  assert.equal(assembly.pages.length, item.pages);
  assert.equal(visual.pages.length, item.pages);
  assert.equal(qa.page_proofs.length, item.pages);
  const labelNegative = evidence(qa.label_mask_negative_control);
  yes(labelNegative, ['passed','publication_pdf_unmodified','negative_preserves_all_original_glyphs_fonts_images_and_ctms','negative_unrelated_actual_new_drawing_rejected']);
  assert.equal(labelNegative.source_canonical_proof_sha256, ready.editions.find(e => e.language === 'ko').proofs[0].sha256);
  assert.ok(labelNegative.negative_added_ink_outside_reference > 0);
  assert.ok(labelNegative.negative_changed_pixels_outside_reviewed_language > 0);
  let totalLabels = 0;
  for (const [index, page] of qa.page_proofs.entries()) {
    assert.equal(page.page, index + 1);
    const body = evidence(page.body_qa);
    const style = evidence(page.actual_style_qa);
    const labels = evidence(page.figure_language_qa);
    const composition = evidence(page.body_composition);
    const labelComposition = evidence(page.figure_composition);
    assert.equal(body.qa_mode, 'publication');
    assert.equal(body.source_sha256, qa.source_original_sha256);
    assert.equal(body.source_page, page.source_page);
    assert.equal(body.language.toLowerCase(), item.language);
    assert.equal(body.proof_sha256, page.body_sha256);
    assert.equal(body.unmodified_canonical_proof_sha256, page.body_sha256);
    yes(body, ['passed','original_fonts_retained','original_images_retained','original_full_image_palette_ICC_mask_graphs_retained','original_page_group_retained','original_colorspace_resources_retained','ordinary_word_spaces_quarter_em']);
    zero(body, ['changed_pixels_outside_prose_and_whole_math_motion','verified_new_prose_over_native_geometry_pixels']);
    empty(body, ['new_prose_word_bbox_overlaps']);
    assert.equal(body.original_point_sizes_scaled, false);
    assert.equal(body.equations_retyped, false);
    const motion = body.source_native_metadata;
    yes(motion, ['passed','font_programs_unchanged','original_form_streams_unchanged','original_image_streams_unchanged','native_vector_path_bytes_preserved','native_atomic_clip_bytes_preserved']);
    empty(motion, ['native_glyph_mismatches']);
    const ink = body.original_native_ink;
    yes(ink, ['passed']);
    assert.equal(ink.output_sha256, page.body_sha256);
    assert.equal(ink.protected_native_glyphs, body.original_native_glyphs);
    assert.ok(ink.protected_native_glyphs > 0);
    zero(ink, ['newly_missing_native_ink_pixels']);
    empty(ink, ['missing_requested_source_glyphs','missing_final_native_glyphs']);
    yes(ink.source_outline_audit, ['passed']);
    empty(ink.source_outline_audit, ['missing_source_outline_signatures']);
    zero(body.original_graphics_motion, ['changed_nonselected_native_graphical_pixels']);
    // Whole original equation graphics move horizontally with their source
    // glyphs. Their old/new locations differ; unselected graphics must not.
    if (body.original_graphics_motion.changed_actual_inline_math_graphical_pixels > 0) {
      assert.ok(body.original_graphics_motion.selected_native_math_groups.length > 0);
      assert.ok(body.original_graphics_motion.original_native_math_actual_graphics_pixels > 0);
      assert.ok(body.original_graphics_motion.new_native_math_actual_graphics_pixels > 0);
    }
    const geometry = body.native_script_and_complete_expression_geometry;
    yes(geometry, ['passed']);
    assert.equal(geometry.final_sha256, page.body_sha256);
    empty(geometry, ['glyph_signature_or_position_errors','relative_geometry_failures']);
    for (const row of [...geometry.script_base_pairs, ...geometry.reviewed_expression_groups]) yes(row, ['passed']);
    for (const picture of body.original_picture_pixels) zero(picture, ['changed_pixels']);
    yes(body.translated_prose_outlines, ['passed']);
    assert.equal(body.translated_prose_outlines.sha256, page.body_sha256);
    assert.equal(body.translated_prose_outlines.delivered_pdf_modified, false);
    for (const row of body.translated_prose_outlines.pages) empty(row, ['empty_outlines']);
    yes(body.new_prose_native_text_collision, ['passed']);
    zero(body.new_prose_native_text_collision, ['dark_prose_pixels_over_native_text']);
    yes(body.new_prose_native_graphics_collision, ['passed']);
    zero(body.new_prose_native_graphics_collision, ['new_hangul_dark_pixels_over_native_foreground']);
    if (body.new_prose_over_any_nonwhite_native_graphics_pixels !== 0) {
      // A strictly scoped source-image pale edge is retained as a raw diagnostic.
      assert.equal(qa.year, 2024); assert.equal(page.page, 3); assert.equal(item.language, 'ko');
      const profile = body.source_caption_background_profile;
      yes(profile, ['passed','point_sizes_and_source_baselines_unchanged','original_image_programs_and_CTMs_unchanged','raw_diagnostic_retained']);
      yes(profile.actual_new_caption_outline_match, ['passed']);
      empty(profile.actual_new_caption_outline_match, ['missing_source_outline_signatures']);
      assert.equal(profile.source_sha256, qa.source_original_sha256);
      assert.equal(profile.raw_any_nonwhite_samples, 38);
      assert.equal(profile.proved_original_pale_caption_background_samples, 38);
      zero(profile, ['unexplained_or_drawing_overlap_samples']);
      const negative = evidence(qa.caption_background_negative_control);
      yes(negative, ['passed','publication_pdf_unmodified','negative_preserves_all_original_font_programs_and_native_CID_geometry','negative_real_new_graphic_stroke_rejected']);
      assert.equal(negative.source_canonical_proof_sha256, page.body_sha256);
      assert.ok(negative.negative_actual_drawing_overlap_samples > 0);
      assert.ok(negative.negative_nonselected_graphic_changes > 0);
    } else zero(body, ['new_prose_over_any_nonwhite_native_graphics_pixels']);

    assert.equal(style.proof_sha256, page.body_sha256);
    assert.equal(style.source_sha256, qa.source_original_sha256);
    yes(style, ['passed','original_source_point_baseline_paint_and_stroke_checked','source_roles_recovered_from_actual_embedded_font_programs','all_actual_embedded_GID_outlines_match_full_role_donor']);
    assert.equal(style.original_font_sizes_scaled, false);
    assert.equal(style.actual_nonspace_glyphs_checked, body.translated_prose_nonspace_glyphs);
    assert.equal(style.actual_glyph_style_checks.length, style.actual_nonspace_glyphs_checked);
    for (const glyph of style.actual_glyph_style_checks) {
      yes(glyph, ['actual_embedded_outline_matches_complete_source_role_donor']);
      assert.ok(Math.abs(glyph.actual_point_size - glyph.source_point_size) < 1e-6);
      assert.ok(Math.abs(glyph.actual_baseline - glyph.source_baseline) <= .001);
      assert.equal(glyph.actual_render_mode, glyph.source_render_mode);
      assert.ok(glyph.actual_GID >= 0);
    }
    assert.equal(composition.output_sha256, page.body_sha256);
    assert.equal(composition.source_sha256, qa.source_original_sha256);
    yes(composition, ['no_scaling','no_math_retyping','no_automatic_wrap']);
    for (const row of composition.rows) assert.ok(row.overflow <= .01);

    assert.equal(labels.body_sha256, page.body_sha256);
    assert.equal(labels.proof_sha256, page.proof_sha256);
    assert.equal(labels.qa_mode, 'publication');
    assert.equal(labels.unmodified_canonical_proof_sha256, page.proof_sha256);
    assert.equal(labels.language.toLowerCase(), item.language);
    yes(labels, ['passed','original_body_glyph_metadata_unchanged','all_original_font_programs_unchanged','all_original_image_palette_ICC_mask_graphs_unchanged','all_original_image_CTMs_unchanged','original_page_group_and_colorspace_unchanged','source_font_measurement_is_estimate','no_original_mathematical_text_retyped']);
    assert.equal(labels.translation_font_sizes_fitted, false);
    empty(labels, ['new_label_actual_empty_outlines']);
    zero(labels.pixel_audit, ['changed_pixels_outside_source_words_new_labels_and_reviewed_symbol_motion','new_label_over_preserved_original_dark_ink','new_actual_font_label_ink_missing']);
    yes(labels.pixel_audit, ['nonlanguage_pixels_preserved']);
    assert.equal(labels.new_label_glyph_style_checks.length, labels.new_label_actual_nonspace_glyphs_checked);
    for (const glyph of labels.new_label_glyph_style_checks) {
      yes(glyph, ['actual_embedded_outline_matches_full_role_donor','PDF_width_integer_quantization_verified']);
      assert.ok(Math.abs(glyph.actual_point_size - glyph.source_measured_point_size) < 1e-6);
      assert.ok(glyph.actual_gid >= 0);
      assert.ok(glyph.actual_position.every((v, i) => Math.abs(v - glyph.source_measured_position[i]) <= .002));
    }
    for (const reuse of labels.reviewed_original_native_bitmap_symbol_reuse) yes(reuse, ['passed','source_original_raw_image_bytes_identical','original_CTM_scale_and_y_unchanged','source_native_clipping_preserved']);
    if (labels.labels === 0) {
      assert.equal(page.proof_sha256, page.body_sha256);
      yes(labels.pixel_audit, ['byte_identical_no_label_page']);
    } else {
      yes(labels.pixel_audit, ['actual_source_word_regions_only']);
      yes(labels.pixel_audit, ['independent_reference_contains_only_verified_actual_label_glyphs']);
      zero(labels.pixel_audit, ['added_ink_outside_independent_actual_font_reference','native_symbol_motion_outside_reviewed_source_and_destination_clips']);
      assert.equal(page.label_reference_pdf.sha256, labels.pixel_audit.reference_sha256);
      assert.equal(rawEvidence(page.label_reference_pdf).subarray(0, 4).toString(), '%PDF');
      yes(labels.pixel_audit.source_outline_metadata_match, ['passed']);
      empty(labels.pixel_audit.source_outline_metadata_match, ['missing_source_outline_signatures']);
    }
    assert.equal(labelComposition.source_body_sha256, page.body_sha256);
    assert.equal(labelComposition.output_sha256, page.proof_sha256);
    yes(labelComposition, ['original_encoded_images_not_modified','original_mathematical_text_not_retyped']);
    assert.equal(labelComposition.new_geometry_drawn, false);
    assert.equal(labelComposition.label_records.length, labels.labels);
    totalLabels += labels.labels;
    const joined = assembly.pages[index];
    assert.equal(joined.proof_sha256, page.proof_sha256);
    yes(joined, ['passed','actual_font_programs_and_glyph_metadata_identical','original_encoded_images_masks_icc_and_ctms_identical','page_group_identical']);
    zero(joined, ['mupdf_4x_changed_pixels','poppler_144dpi_changed_pixels']);
    const reviewed = visual.pages[index];
    assert.equal(reviewed.page, page.page);
    assert.equal(reviewed.source_page, page.source_page);
    assert.equal(reviewed.proof_sha256, page.proof_sha256);
    yes(reviewed, ['reviewed','source_math_atoms_reviewed','title_and_caption_alignment_reviewed','word_spacing_reviewed','original_figures_and_translated_labels_reviewed']);
  }
  const words = evidence(qa.source_word_component_review);
  yes(words, ['passed','source_only']);
  assert.equal(words.labels.length, totalLabels);
  for (const word of words.labels) {
    yes(word, ['passed']); empty(word, ['clipped_or_nonlanguage_components']);
    for (const partition of word.reviewed_source_word_component_partitions) {
      yes(partition.review, ['reviewed']);
      assert.ok(partition.remaining_source_component_pixels > 0);
    }
  }
  assert.ok(Object.keys(qa.authoring_snapshot_sha256).length > 0);
  for (const [file, hash] of Object.entries(qa.authoring_snapshot_sha256)) {
    const raw = fs.readFileSync(path.join(root, qa.authoring_snapshotroot, file));
    assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), hash, file);
  }
};

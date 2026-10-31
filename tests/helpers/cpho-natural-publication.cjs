const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
module.exports = (root, record, item) => {
  const pinned = (file, hash) => {
    const bytes = fs.readFileSync(path.join(root, file.replaceAll('\\', '/')));
    assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), hash, file);
    return JSON.parse(bytes);
  };
  assert.equal(record.status, 'READY');
  for (const key of ['sha256', 'bytes', 'pages']) assert.equal(record[key], item[key]);
  const source = pinned(record.source_inventory, record.source_inventory_sha256);
  assert.equal(source.status, 'READY_NATURAL_SPACING_ORIGINAL_RESOURCES');
  const qa = pinned(record.combined_qa, record.combined_qa_sha256);
  assert.equal(qa.passed, true);
  assert.equal(qa.output_sha256, item.sha256);
  assert.equal(qa.pages.length, item.pages);
  assert.ok(qa.visual_review);
  assert.equal(record.page_proofs.length, item.pages);
  for (const page of qa.pages) {
    assert.equal(page.passed, true);
    for (const key of ['changed_pixels_outside_old_and_new_text_ink', 'NUL_glyphs', 'combined_vs_proof_MuPDF_4x_changed_pixels', 'combined_vs_proof_Poppler_144dpi_changed_pixels']) assert.equal(page[key], 0, key);
    for (const key of ['original_font_programs_and_names_retained', 'original_image_programs_retained', 'page_group_preserved', 'colorspace_resources_preserved', 'native_move_stages_passed', 'fresh_process_RGB_render']) assert.equal(page[key], true, key);
    assert.deepEqual(page.remaining_regular_NotoSerif_Hangul, []);
    assert.equal(page.unexpected_Hangul_visibility_components, 0);
    const footer = page.inherited_original_footer_overlay;
    if (page.hangul_visibility.flagged_components > 0) {
      assert.equal(source.year, 2006);
      assert.equal(page.page, 2);
      assert.equal(footer.raw_visibility_components, page.hangul_visibility.flagged_components);
      assert.equal(footer.inherited_source_image_occlusion_components, footer.raw_visibility_components);
      assert.equal(footer.unexpected_visibility_components, 0);
      assert.equal(footer.original_source_paint_order_preserved, true);
      assert.equal(footer.original_picture_opaque_interior_pixels_changed, 0);
      assert.equal(footer.source_bitmap_and_SMask_programs_preserved, true);
      assert.equal(footer.original_picture_pixels_in_footer_band_changed, footer.picture_edge_antialias_pixels_over_changed_underlay);
    }

    const ink = page.original_physical_native_ink;
    assert.equal(page.verified_original_native_ink_passed, true);
    if (ink.newly_missing_native_ink_pixels === 0) {
      assert.equal(ink.passed, true);
    } else {
      // Preserve the raw one-pixel SVG diagnostic; the independently replayed
      // original encoded R retains its actual hinted native dark ink.
      const witness = page.exact_native_CID_raster_phase_witness;
      assert.equal(source.year, 2006);
      assert.equal(item.language, 'ko');
      assert.equal(page.page, 1);
      assert.equal(ink.newly_missing_native_ink_pixels, 1);
      assert.equal(witness.passed, true);
      assert.equal(witness.c, 'R');
      assert.equal(witness.gid, 179);
      assert.equal(witness.size, 12);
      assert.equal(witness.source_encoded_cid_hex, '00b3');
      assert.equal(witness.source_font_resource, '/F5');
      assert.equal(witness.source_Tf, 1);
      assert.deepEqual(witness.source_Tm_linear, [12, 0, 0, 12]);
      assert.equal(witness.original_font_programs_unchanged, true);
      assert.equal(witness.publication_PDF_modified, false);
      assert.equal(witness.missing_native_CID_reference_pixels, 0);
      assert.ok(witness.native_reference_dark_pixels > 0);
      assert.equal(witness.source_sha256, ink.source_sha256);
      assert.equal(witness.proof_sha256, page.output_sha256);
    }

    for (const key of ['missing_requested_source_glyphs', 'missing_final_native_glyphs']) assert.deepEqual(ink[key], []);
    assert.deepEqual(ink.source_outline_audit.missing_source_outline_signatures, []);
    assert.equal(page.native_graphics_motion_audit.changed_nonselected_native_graphical_pixels, 0);
    const geometry = page.original_native_expression_relative_geometry;
    assert.equal(geometry.passed, true);
    assert.equal(geometry.final_sha256, page.output_sha256);
    assert.deepEqual(geometry.glyph_signature_or_position_errors, []);
    assert.deepEqual(geometry.relative_geometry_failures, []);
    for (const pair of geometry.script_base_pairs) assert.equal(pair.passed, true);
    for (const group of geometry.reviewed_expression_groups) assert.equal(group.passed, true);

    for (const image of page.image_palette_icc_mask_and_motion_audits) {
      assert.ok(image.rect_preserved || image.rect_matches_declared_native_math_dx);
      assert.equal(image.full_palette_icc_mask_image_graph_preserved, true);
    }
    const proof = record.page_proofs.find(p => p.page === page.page);
    assert.equal(proof.proof_sha256, page.output_sha256);
    const composition = pinned(proof.composition, proof.composition_sha256);
    assert.equal(composition.output_sha256, page.output_sha256);
    const stages = [composition.native_move_qa];
    if (composition.picture_language_and_caption_stage) stages.push(composition.picture_language_and_caption_stage.native_move_qa);
    for (const move of stages) {
      assert.equal(move.passed, true);
      assert.equal(move.font_programs_unchanged, true);
      assert.equal(move.native_vector_path_bytes_preserved, true);
      assert.deepEqual(move.native_glyph_mismatches, []);
    }
  }
  for (const [file, hash] of Object.entries(record.authoring_snapshot_sha256)) {
    const bytes = fs.readFileSync(path.join(root, record.authoring_snapshotroot, file.replaceAll('\\', '/')));
    assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), hash, file);
  }
};

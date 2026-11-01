const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
module.exports = function validateFigureLanguagePublication(root, qa, item) {
  const rawEvidence = ref => {
    assert.ok(ref && typeof ref.path === 'string');
    const absolute = path.resolve(root, ref.path); assert.ok(absolute.startsWith(root + path.sep));
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
  yes(qa, ['body_fonts_and_word_spacing_unchanged']);
  for (const key of ['original_equations_retyped','new_diagram_geometry','point_sizes_fitted']) assert.equal(qa[key], false);
  assert.equal(qa.added_editorial_notes, 0);
  const ready = evidence(qa.source_ready); assert.equal(ready.status, 'READY');
  assert.equal(ready.schema, 'reviewed-figure-language-v1');
  const baseline = evidence(qa.baseline_publication);
  assert.equal(qa.baseline_item.audit_schema, 'natural-spacing-v2');
  assert.equal(qa.baseline_item.file, item.file);
  assert.equal(qa.baseline_item.pages, item.pages);
  require('./natural-spacing-publication.cjs')(root, baseline, qa.baseline_item);
  const visual = evidence(qa.visual_review); const assembly = evidence(qa.assembly_qa);
  assert.equal(assembly.sha256, item.sha256); assert.equal(assembly.bytes, item.bytes); yes(assembly, ['passed']);
  assert.equal(assembly.pages.length, item.pages); assert.equal(visual.pages.length, item.pages);
  assert.equal(qa.page_proofs.length, item.pages);
  const complete2010Solutions = qa.year === 2010 && qa.kind === 'TS';
  if (complete2010Solutions) {
    assert.equal(qa.pages, 11);
    const bodyReady = evidence({ path: baseline.source_ready, sha256: baseline.source_ready_sha256 });
    yes(bodyReady, ['original_source_heading_centers_verified','actual_heading_alignment_negative_rejected']);
    const bodyEvidence = name => {
      const file = 'independent-additional-audits/' + name;
      return evidence({ path: baseline.authoring_snapshotroot + '/' + file, sha256: baseline.authoring_snapshot_sha256[file] });
    };
    const alignment = bodyEvidence('final-extra-checks.json'); yes(alignment, ['passed']);
    assert.equal(alignment.pages.length, 11);
    let centers = 0;
    for (const [index, row] of alignment.pages.entries()) {
      const actual = row.original_source_heading_alignment; yes(actual, ['passed']);
      assert.equal(actual.source_page, index + 1);
      assert.equal(actual.proof_sha256, baseline.page_proofs[index].proof_sha256);
      assert.equal(actual.source_sha256, baseline.page_proofs[index].source_pdf_sha256);
      assert.equal(actual.headings_and_captions_checked, actual.rows.length);
      for (const heading of actual.rows) {
        yes(heading, ['passed','source_center_matches_original_glyphs','original_alignment_frame_resolves_to_active_composer_scope']);
        assert.ok(heading.glyphs > 0);
        assert.ok(Math.abs(heading.actual_center - heading.source_center) <= .001);
        assert.ok(Math.abs(heading.center_error_pt) <= .001);
        assert.ok(heading.independent_original_source_centers.length > 0);
        for (const center of heading.independent_original_source_centers) assert.ok(Math.abs(center - heading.source_center) <= .001);
      }
      centers += actual.rows.length;
    }
    assert.equal(centers, 31); assert.equal(bodyReady.original_source_heading_and_caption_centers_checked, centers);
    const regression = bodyEvidence('heading-alignment-regression.json');
    yes(regression, ['passed','publication_pdf_unmodified','all_original_font_glyph_point_and_baseline_metadata_retained','original_encoded_images_and_diagram_geometry_retained','independent_source_center_rejected']);
    assert.equal(regression.canonical_proof_sha256, baseline.page_proofs[3].proof_sha256);
    assert.equal(regression.actual_heading_shift_pt, -8);
    yes(regression.native_move_qa, ['passed','font_programs_unchanged','original_image_streams_unchanged','native_vector_path_bytes_preserved']);
    empty(regression.native_move_qa, ['native_glyph_mismatches']);
    const rejected = bodyEvidence('heading-alignment-negative-audit.json');
    assert.equal(rejected.passed, false);
    assert.equal(rejected.proof_sha256, regression.native_move_qa.output_sha256);
    const failed = rejected.rows.filter(row => !row.passed); assert.equal(failed.length, 1);
    yes(failed[0], ['source_center_matches_original_glyphs','original_alignment_frame_resolves_to_active_composer_scope']);
    assert.ok(Math.abs(failed[0].center_error_pt + 8) <= .001);
  }
  const negative = evidence(qa.negative_control); yes(negative, ['passed']); assert.equal(negative.rows.length, complete2010Solutions ? 1 : 2);
  for (const row of negative.rows) {
    yes(row, ['all_original_glyphs_fonts_images_and_caption_positions_retained','real_extra_drawing_rejected','publication_pdf_unmodified','passed']);
    assert.ok(row.negative_added_ink_outside_reference > 0);
    assert.equal(row.canonical_proof_sha256, ready.editions.find(e => e.year === row.year).proofs.find(p => p.page === row.page).sha256);
  }
  let totalLabels = 0;
  for (const [index, page] of qa.page_proofs.entries()) {
    assert.equal(page.page, index + 1);
    assert.equal(page.body_sha256, baseline.page_proofs[index].proof_sha256);
    const audit = evidence(page.figure_language_qa); const composition = evidence(page.composition);
    yes(audit, ['passed']); assert.equal(audit.qa_mode, 'publication');
    assert.equal(audit.body_sha256, page.body_sha256); assert.equal(audit.proof_sha256, page.proof_sha256);
    assert.equal(composition.body_sha256, page.body_sha256); assert.equal(composition.proof_sha256, page.proof_sha256);
    assert.equal(composition.placements.length, audit.labels);
    const reviewed = visual.pages[index]; assert.equal(reviewed.page, page.page);
    assert.equal(reviewed.proof_sha256, page.proof_sha256); assert.equal(reviewed.body_sha256, page.body_sha256);
    yes(reviewed, ['reviewed','original_math_and_body_unchanged']);
    if (audit.labels === 0) {
      assert.equal(page.proof_sha256, page.body_sha256);
      yes(audit, ['byte_identical_no_label_page']);
    } else {
      assert.equal(audit.unmodified_canonical_proof_sha256, page.proof_sha256);
      yes(audit, ['original_body_glyph_font_GID_point_paint_and_y_preserved','only_reviewed_caption_digits_moved_horizontally','all_original_font_programs_retained','all_original_image_palette_ICC_mask_graphs_and_CTMs_retained','original_page_group_and_colorspace_retained']);
      assert.equal(audit.point_sizes_fitted, false);
      yes(composition, ['body_and_equation_fonts_not_changed','original_encoded_images_not_modified','no_new_diagram_geometry','point_sizes_not_fitted']);
      const pixel = audit.pixel_audit;
      zero(pixel, ['native_control_changed_outside_erased_source_native_words_and_original_caption_digits','bitmap_word_erasure_outside_reviewed_source_words','added_ink_outside_independent_actual_font_reference','final_changed_outside_reviewed_words_caption_digits_and_reference','new_label_over_preserved_original_ink','actual_new_label_ink_missing']);
      yes(pixel, ['independent_reference_contains_only_verified_actual_label_glyphs']);
      assert.equal(page.actual_font_reference_pdf.sha256, pixel.reference_sha256);
      assert.equal(rawEvidence(page.actual_font_reference_pdf).subarray(0,4).toString(), '%PDF');
      const ink = audit.original_native_ink; yes(ink, ['passed']);
      assert.equal(ink.output_sha256, page.proof_sha256);
      assert.equal(ink.protected_native_glyphs, audit.original_physical_body_glyphs_checked);
      assert.ok(ink.protected_native_glyphs > 0);
      zero(ink, ['newly_missing_native_ink_pixels']); empty(ink, ['missing_requested_source_glyphs','missing_final_native_glyphs']);
      yes(ink.source_outline_audit, ['passed']); empty(ink.source_outline_audit, ['missing_source_outline_signatures']);
      yes(audit.actual_label_outline_source_match, ['passed']); empty(audit.actual_label_outline_source_match, ['missing_source_outline_signatures']);
      assert.equal(audit.actual_label_glyph_style_checks.length, audit.actual_label_glyphs_checked);
      for (const glyph of audit.actual_label_glyph_style_checks) {
        yes(glyph, ['actual_outline_matches_complete_role_donor']); assert.ok(glyph.actual_gid >= 0);
        assert.ok(Math.abs(glyph.actual_point_size - glyph.source_point_size) < 1e-6);
        assert.ok(Math.abs(glyph.actual_baseline - glyph.source_baseline) <= .001);
      }
      assert.equal(audit.actual_label_font_basis_checks.length, audit.labels);
      for (const basis of audit.actual_label_font_basis_checks) yes(basis, ['passed','no_font_scale_or_added_tracking']);
      for (const placement of composition.placements) {
        assert.equal(placement.target_point_size_fitted, false);
        if (placement.source_kind === 'bitmap-source-measured') {
          assert.equal(placement.source_point_size_is_estimate, true);
          yes(placement.source_font_measurement, ['source_text_only_no_translated_box_fit']);
          assert.equal(placement.source_font_measurement.metadata_available, false);
        } else assert.equal(placement.source_kind, 'native-source-metadata');
      }
      if (qa.year === 2011) {
        assert.equal(page.page, 3); assert.equal(audit.erased_native_language_only_glyphs, 19);
        assert.equal(composition.original_caption_digit_shifts.length, 2);
        for (const [index, shift] of composition.original_caption_digit_shifts.entries()) {
          assert.equal(shift.glyphs.length, 1); assert.equal(shift.glyphs[0].c, String(index + 1));
        }
        assert.equal(composition.reviewed_stationary_caption_frames.length, 2);
        yes(composition.native_move_qa, ['passed','font_programs_unchanged','native_vector_path_bytes_preserved']);
        empty(composition.native_move_qa, ['native_glyph_mismatches']);
      } else assert.equal(audit.erased_native_language_only_glyphs, 0);
      yes(reviewed, ['native_figure_lines_and_variables_reviewed','word_spacing_reviewed']);
    }
    const joined = assembly.pages[index]; assert.equal(joined.proof_sha256, page.proof_sha256);
    yes(joined, ['passed','actual_font_programs_and_glyph_metadata_identical','original_encoded_images_masks_icc_and_ctms_identical','page_group_identical']);
    zero(joined, ['mupdf_4x_changed_pixels','poppler_144dpi_changed_pixels']);
    totalLabels += audit.labels;
  }
  assert.equal(totalLabels, complete2010Solutions ? 1 : qa.year === 2010 ? 7 : 4);
  const words = evidence(qa.source_word_component_review); yes(words, ['passed','source_only']);
  assert.equal(words.labels.length, complete2010Solutions ? 1 : 7);
  for (const word of words.labels) { yes(word, ['passed','source_only']); empty(word, ['intersecting_nonword_components']); }
  assert.ok(Object.keys(qa.authoring_snapshot_sha256).length > 0);
  for (const [file, hash] of Object.entries(qa.authoring_snapshot_sha256)) {
    const raw = fs.readFileSync(path.join(root, qa.authoring_snapshotroot, file));
    assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), hash, file);
  }
};

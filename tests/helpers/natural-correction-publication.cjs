const assert = require('node:assert/strict');

module.exports = function validateCorrection(root, qa, item, read) {
  const correction = qa.layout_correction;
  assert.equal(correction.schema, 'source-pinned-title-contact-publication-v1');
  const year = correction.year;
  assert.ok([2024, 2025, 2026].includes(year));
  assert.equal(item.file, `Ortvay_${year}_T_KO.pdf`);
  assert.equal(correction.source_sha256, qa.source_sha256);
  assert.ok(item.qa.includes('/natural-spacing-title-correction-20261103/'));
  assert.deepEqual(correction.root_visually_read_pages, [1]);
  const ready = read(correction.ready_path, correction.ready_sha256);
  assert.equal(ready.status, 'YEAR_STRICT_TITLE_CORRECTION_READY_FOR_ROOT_ASSEMBLY_REVIEW');
  assert.equal(ready.year, year);
  assert.equal(ready.pages, qa.pages);
  assert.equal(ready.source.sha256, qa.source_sha256);
  const rootReview = read(correction.root_review_path, correction.root_review_sha256);
  assert.equal(rootReview.status, 'PASS');
  assert.equal(rootReview.source_sha256, qa.source_sha256);
  assert.deepEqual(rootReview.root_visually_read_pages, [1]);
  assert.equal(rootReview.proof_sha256, qa.page_audits[0].proof_sha256);
  assert.equal(rootReview.png_sha256, ready.page_results[0].png.sha256);
  assert.equal(rootReview.layout_sha256, qa.page_audits[0].qa_sha256);
  assert.equal(rootReview.composer_sha256, qa.page_audits[0].composer_sha256);
  assert.ok(qa.authoring_programs.some(program => program.path.endsWith('/record_ortvay_title_root_review.py') && program.sha256 === rootReview.program_sha256));
  const previous = read(correction.previous_publication_qa, correction.previous_publication_qa_sha256);
  assert.equal(previous.sha256, correction.previous_pdf_sha256);
  assert.equal(previous.file, item.file);
  assert.notEqual(previous.sha256, qa.sha256);
  const rules = read(correction.rules_path, correction.rules_sha256);
  assert.equal(rules.year, year);
  assert.equal(rules.source_sha256, qa.source_sha256);
  assert.equal(rules.rows.length, 4);
  assert.deepEqual(correction.all_three_completed_and_original_pins_rehashed.map(row => row.year), [2024, 2025, 2026]);
  for (const row of correction.all_three_completed_and_original_pins_rehashed) {
    assert.ok(row.original_input_pins_rehashed >= 329);
    assert.ok(row.final_working_input_pins_rehashed > 0);
    const complete = read(row.public_ready_path, row.ready_sha256);
    assert.equal(complete.year, row.year);
    assert.equal(complete.status, 'YEAR_STRICT_TITLE_CORRECTION_READY_FOR_ROOT_ASSEMBLY_REVIEW');
    if (row.year === year) assert.equal(row.ready_sha256, correction.ready_sha256);
  }
  const bodyRows = year === 2025 ? [{ page: 1, baseline: 231.3990478515625, dx: .75 }] : [];
  assert.deepEqual(correction.authorized_body_rows, bodyRows);
  if (year !== 2026) {
    const pin = year === 2024 ? qa.link_annotation_subset_regression : qa.link_annotation_regression;
    const links = read(pin.path, pin.sha256);
    assert.equal(links.schema, 'parameterized-private-ortvay-link-regression-v1');
    assert.equal(links.status, 'PASS');
    assert.equal(links.passed, true);
    assert.equal(links.year, year);
    const number = year === 2024 ? 2 : 10;
    assert.equal(links.page, number);
    assert.equal(links.source_sha256, qa.source_sha256);
    assert.equal(links.proof_sha256, qa.page_audits[number - 1].proof_sha256);
    assert.equal(links.layout_sha256, qa.page_audits[number - 1].qa_sha256);
    assert.equal(links.changed_pixels, 0);
    assert.equal(links.all_visible_glyph_geometry_identical, true);
    assert.equal(links.all_nonrect_annotation_settings_identical_after_save, true);
    assert.equal(links.annotation_P_same_page_semantics_verified, true);
    assert.equal(links.all_annotation_rectangles_checked_after_save, true);
    assert.equal(links.before_nonrect_semantics_sha256, links.after_nonrect_semantics_sha256);
    assert.equal(links.ready_manifest.sha256, correction.ready_sha256);
    assert.equal(links.no_input_or_frozen_file_written, true);
    for (const [field, suffix] of [['assembler_sha256', '/assemble_natural.py'], ['core_program_sha256', '/ortvay_private_link_regression.py']]) {
      assert.ok(qa.authoring_programs.some(program => program.path.endsWith(suffix) && program.sha256 === links[field]));
    }
    assert.equal(links.test_program_sha256, pin.test_program_sha256);
    assert.equal(links.program_sha256, pin.test_program_sha256);
    assert.ok(links.negative_regressions.length >= 9);
    assert.equal(links.negative_regression_details.length, links.negative_regressions.length);
    for (const failure of links.negative_regression_details) assert.equal(failure.rejected, true);
    const required = ['missing native URL movement rejected', 'URL glyph incorrectly hidden as prose rejected'];
    if (year === 2024) required.push('wrong shared-URI shift on stationary second rectangle rejected');
    for (const name of required) assert.ok(links.negative_regressions.includes(name));
    assert.equal(links.links.length, year === 2024 ? 6 : 1);
    for (const row of links.links) {
      const glyphs = row.independent_native_url_glyph_audit;
      assert.ok(glyphs);
      assert.equal(glyphs.native_url_glyphs_verified_in_proof, true);
      assert.ok(glyphs.max_url_glyph_geometry_error_pt <= .001 && glyphs.position_tolerance_pt <= .001);
      assert.equal(glyphs.uri, row.uri);
      assert.equal(glyphs.dx, row.dx);
      assert.equal(glyphs.source_url_glyphs, glyphs.glyph_references.length);
      assert.equal(glyphs.display_fragment, glyphs.glyph_references.map(ref => ref.source_glyph.c).join(''));
      if (year === 2024) {
        const projected = glyphs.glyph_references.map(ref => {
          const { opacity, render_type, ...source_glyph } = ref.source_glyph;
          assert.equal(opacity, 1);
          assert.equal(render_type, 0);
          return { ...ref, source_glyph };
        });
        assert.deepEqual(projected, row.glyph_references);
      } else {
        const joined = qa.page_audits[9];
        const body = read(joined.qa_path, joined.qa_sha256);
        assert.equal(glyphs.display_fragment, row.uri);
        assert.equal(glyphs.source_url_glyphs, row.native_url_glyphs);
        assert.ok(row.native_url_glyphs > 0);
        for (const ref of glyphs.glyph_references) {
          assert.equal(ref.native_shift_index, row.native_shift_index);
          const shift = body.native_shifts[ref.native_shift_index];
          assert.equal(ref.dx, shift.dx);
          const original = shift.glyphs[ref.shift_glyph_index];
          assert.ok(original);
          for (const key of ['c', 'gid', 'font', 'size', 'origin', 'bbox']) assert.deepEqual(ref.source_glyph[key], original[key]);
          assert.deepEqual(ref.source_glyph.color, [0, 0, 1]);
          assert.equal(ref.source_glyph.opacity, 1);
          assert.equal(ref.source_glyph.render_type, original.paint);
          assert.equal(original.paint, 0);
        }
        const { independent_native_url_glyph_audit, ...helperOnly } = row;
        assert.deepEqual(joined.link_annotation_adjustments, [helperOnly]);
      }
    }
  }
  assert.equal(correction.pages.length, qa.pages);
  let glyphs = 0;
  let closePairs = 0;
  for (const [index, page] of correction.pages.entries()) {
    const joined = qa.page_audits[index];
    assert.equal(page.page, index + 1);
    assert.equal(page.proof_sha256, joined.proof_sha256);
    assert.equal(page.layout_sha256, joined.qa_sha256);
    const visual = read(qa.visual_review_files[0]).pages[index];
    assert.equal(visual.png_sha256, ready.page_results[index].png.sha256);
    assert.equal(visual.correction_audit_sha256, ready.page_results[index].correction_audit.sha256);
    const body = read(joined.qa_path, joined.qa_sha256);
    const audit = read(page.correction_audit_path, page.correction_audit_sha256);
    const { layout_sha256, png_sha256, ...embedded } = audit;
    assert.equal(layout_sha256, joined.qa_sha256);
    assert.equal(png_sha256, ready.page_results[index].png.sha256);
    assert.deepEqual(embedded, body.title_correction_independent_audit);
    assert.equal(audit.passed, true);
    assert.equal(audit.output_sha256, page.proof_sha256);
    assert.equal(audit.reference_sha256, page.reference_proof_sha256);
    assert.equal(audit.reference_sha256, previous.page_audits[index].proof_sha256);
    assert.ok(qa.authoring_programs.some(program => program.sha256 === audit.measurement_code_sha256));
    assert.equal(audit.native_shifts_identical, true);
    assert.equal(audit.original_font_programs_images_and_placements_identical, true);
    assert.deepEqual(audit.korean_actual_glyph_geometry, body.new_korean_glyph_and_geometry_audit);
    assert.deepEqual(audit.korean_actual_glyph_geometry.original_full_font_gid_errors, []);
    assert.equal(audit.korean_actual_glyph_geometry.original_full_font_gids_verified, audit.korean_actual_glyph_geometry.actual_glyphs);
    glyphs += audit.korean_actual_glyph_geometry.actual_glyphs;
    const ink = audit.korean_inter_row_ink_audit;
    assert.equal(ink.passed, true);
    assert.deepEqual(ink.failures, []);
    assert.equal(ink.proof_sha256, page.proof_sha256);
    assert.equal(ink.pairs.length, ink.tested_close_row_pairs);
    assert.equal(ink.actual_embedded_subset_fonts, true);
    for (const pair of ink.pairs) assert.equal(pair.contact_pixels_2x, 0);
    closePairs += ink.tested_close_row_pairs;
    const allowedBody = bodyRows.filter(row => row.page === page.page);
    const actualBody = audit.body_row_audits || [];
    assert.equal(actualBody.length, allowedBody.length);
    for (const [i, row] of actualBody.entries()) {
      assert.equal(row.baseline, allowedBody[i].baseline);
      assert.equal(row.whole_row_dx, allowedBody[i].dx);
      assert.equal(row.whole_row_horizontal_translation_only, true);
      assert.ok(row.actual_dx_em <= .4);
    }
    assert.equal(audit.changed_pixels_outside_authorized_rows ?? audit.changed_pixels_outside_title_rows, 0);
    const multiscale = audit.corrected_row_multiscale_contact_audits || [];
    assert.equal(multiscale.length, allowedBody.length);
    for (const row of multiscale) {
      assert.equal(row.passed, true);
      assert.deepEqual(row.contact_pixels_by_scale, { 2: 0, 4: 0, 8: 0 });
      assert.equal(row.actual_embedded_subset_font_programs, true);
    }
    if (page.page === 1) {
      assert.equal(audit.title_row_audits.length, 4);
      for (const [i, row] of audit.title_row_audits.entries()) {
        const source = rules.rows[i];
        assert.equal(row.baseline, source.baseline);
        assert.ok(Math.abs(row.actual_target_center_pt - source.source_center_pt) <= .001);
        assert.equal(row.whole_row_horizontal_translation_only, true);
        const placements = body.placements.filter(p => Math.abs(p.baseline - source.baseline) <= .001);
        assert.ok(placements.length > 0);
        for (const placement of placements) {
          assert.ok(Math.abs(placement.size - source.source_size_pt) <= .000001);
          assert.ok(Math.abs(placement.point[1] - source.baseline) <= .000001);
        }
      }
    } else {
      assert.deepEqual(audit.title_row_audits, []);
      assert.equal(audit.total_changed_pixels, 0);
      assert.equal(audit.non_title_page_all_pixels_identical, true);
      assert.equal(audit.non_title_glyph_traces_identical, true);
    }
  }
  assert.equal(glyphs, correction.actual_full_font_gids_verified);
  assert.equal(glyphs, ready.actual_new_glyphs_and_original_full_font_gids_verified);
  assert.equal(closePairs, correction.tested_close_row_pairs);
  assert.equal(closePairs, ready.tested_close_row_pairs);
};

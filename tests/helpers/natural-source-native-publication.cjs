const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

module.exports = function validateNaturalSourceNative(root, qa, item) {
  const hash = raw => crypto.createHash('sha256').update(raw).digest('hex');
  const read = (file, expected) => {
    const absolute = path.resolve(root, file);
    assert.ok(absolute.startsWith(root + path.sep));
    const raw = fs.readFileSync(absolute);
    if (expected) assert.equal(hash(raw), expected, file);
    return JSON.parse(raw);
  };
  for (const key of ['file', 'pages', 'bytes', 'sha256', 'language']) assert.equal(qa[key], item[key]);
  assert.equal(qa.schema, 'natural-source-native-joined-v1');
  assert.equal(qa.status, 'READY');
  assert.equal(qa.visual_review_required, false);
  for (const key of ['no_font_shrink', 'no_math_rasterization', 'no_reserved_english_widths',
    'inline_native_math_moved_as_whole_expressions', 'stationary_display_equations_and_figures',
    'original_font_sizes_and_baselines_preserved', 'hidden_original_prose_has_empty_ActualText',
    'no_added_editorial_notes', 'all_pages_visually_reviewed']) assert.equal(qa[key], true, key);
  assert.equal(qa.page_audits.length, item.pages);
  for (const program of qa.authoring_programs) {
    assert.equal(hash(fs.readFileSync(path.join(root, program.path))), program.sha256);
  }
  if (qa.source_path_resolver_sha256) {
    const resolver = qa.authoring_programs.find(p => /\/source_path_resolver\.py$/.test(p.path));
    assert.ok(resolver, 'Source path mapping program is frozen with the publication');
    assert.equal(resolver.sha256, qa.source_path_resolver_sha256);
  }
  const folder = path.dirname(path.join(root, item.qa));
  const reviews = fs.readdirSync(folder).filter(f => /^visual-review.*\.json$/.test(f)).flatMap(f => {
    const review = JSON.parse(fs.readFileSync(path.join(folder, f), 'utf8'));
    assert.equal(review.source_sha256, qa.source_sha256);
    return review.pages;
  });
  for (const [index, page] of qa.page_audits.entries()) {
    assert.equal(page.page, index + 1);
    assert.equal(page.final_vs_reviewed_proof_changed_pixels, 0);
    assert.equal(page.missing_hangul_glyphs, 0);
    assert.ok(page.visible_hangul_characters > 0);
    for (const key of ['final_vs_reviewed_proof_all_glyph_geometry_identical', 'page_box_preserved',
      'original_font_programs_preserved', 'original_image_encoded_streams_and_filters_preserved',
      'original_image_geometry_preserved']) assert.equal(page[key], true, key);
    const body = read(page.qa_path, page.qa_sha256);
    for (const link of page.link_annotation_adjustments || []) {
      assert.equal(link.page, page.page);
      assert.equal(link.passed, true);
      assert.equal(link.only_horizontal_rect_translation, true);
      assert.equal(link.other_annotation_settings_preserved, true);
      const shift = body.native_shifts[link.native_shift_index];
      assert.equal(shift.glyphs.map(g => g.c).join(''), link.uri);
      assert.equal(shift.glyphs.length, link.native_url_glyphs);
      assert.equal(shift.dx, link.dx);
      for (let n = 0; n < 4; n++) {
        const expected = link.source_rect_mupdf[n] + (n % 2 === 0 ? link.dx : 0);
        assert.ok(Math.abs(link.actual_target_rect_mupdf[n] - expected) < 0.001);
      }
    }
    const plan = read(page.plan_path, page.plan_sha256);
    const effective = read(page.effective_plan_path, page.effective_plan_sha256);
    assert.equal(body.schema, 'natural-source-native-v1');
    assert.equal(body.source, qa.source);
    assert.equal(body.source_sha256, qa.source_sha256);
    assert.equal(body.page, page.page);
    for (const p of [plan, effective]) {
      assert.equal(p.page, page.page);
      assert.equal(p.source, qa.source);
      assert.equal(p.source_sha256, qa.source_sha256);
    }
    assert.equal(body.output_sha256, page.proof_sha256);
    assert.equal(body.plan_sha256, page.plan_sha256);
    assert.equal(body.composer_sha256, page.composer_sha256);
    assert.equal(hash(fs.readFileSync(path.join(root, page.composer_path))), page.composer_sha256);
    assert.equal(body.effective_plan_sha256, page.effective_plan_sha256);
    if (page.overrides_path) {
      read(page.overrides_path, page.overrides_sha256);
      assert.equal(body.overrides_sha256, page.overrides_sha256);
    }
    for (const scope of page.source_scopes || []) read(scope.path, scope.sha256);
    if (page.raster_label_manifest) {
      read(page.raster_label_manifest.path, page.raster_label_manifest.sha256);
      assert.equal(body.reviewed_raster_label_manifest.sha256, page.raster_label_manifest.sha256);
    }
    if (qa.strict_korean_glyph_geometry_audit) {
      const audit = body.new_korean_glyph_and_geometry_audit;
      assert.equal(audit.passed, true);
      assert.deepEqual(audit.missing_or_notdef_glyphs, []);
      assert.deepEqual(audit.geometry_errors, []);
      assert.equal(audit.planned_glyphs, audit.actual_glyphs);
      assert.ok(audit.max_position_error_pt <= 0.001 && audit.position_tolerance_pt <= 0.001);
      for (const key of ['paragraph_text_conservation_verified', 'inline_native_math_assignment_complete',
        'native_atom_source_prose_seams_clear', 'new_korean_font_subsets_retain_original_gids']) assert.equal(body[key], true, key);
      const baseline = page.original_prose_baseline_audit;
      assert.equal(baseline.passed, true);
      assert.equal(baseline.placements, body.placements.length);
      assert.ok(baseline.max_selected_source_prose_baseline_delta_pt <= 0.001);
      assert.ok(baseline.max_actual_source_char_baseline_delta_pt <= 0.001 && baseline.tolerance_pt <= 0.001);
      for (const [field, filename] of [['native_motion_engine_sha256', 'latex_native_motion.py'],
        ['native_ink_bounds_engine_sha256', 'native_ink_bounds.py'], ['native_proof_helper_sha256', 'native_proof.py']]) {
        assert.equal(body[field], qa.authoring_programs.find(p => p.path.endsWith('/' + filename)).sha256);
      }
    }
    if (body.native_type3_profile_sha256) {
      const profile = qa.authoring_programs.find(p => p.path.endsWith('/native_type3_profile.py'));
      assert.ok(profile);
      assert.equal(profile.sha256, body.native_type3_profile_sha256);
    }
    for (const contact of body.intentional_prose_decoration_contacts || []) {
      assert.equal(contact.x_translation_only, true);
      assert.equal(contact.source_path_bytes_and_paint_and_y_preserved, true);
      const decoration = body.prose_vector_decorations.find(d => d.id === contact.id);
      assert.ok(decoration);
      assert.equal(contact.source_path_index, decoration.source_path_index);
      assert.equal(contact.observed_contact_pixels, contact.contact_pixels_pdf_pt.length);
    }
    for (const key of ['no_reserved_english_widths', 'no_font_shrink', 'source_font_programs_preserved',
      'original_image_encoded_bytes_and_filters_preserved', 'source_image_placements_preserved',
      'source_glyph_moves_restricted_to_authored_prose_line_bounds', 'stationary_display_equations_and_figures',
      'original_font_sizes_and_baselines_identical', 'native_horizontal_moves_only']) assert.equal(body[key], true, key);
    assert.deepEqual(body.stationary_display_glyphs_missing_or_moved, []);
    assert.deepEqual(body.stationary_figure_glyphs_missing_or_moved, []);
    assert.deepEqual(body.final_native_geometry.missing, []);
    assert.equal(body.final_native_geometry.extra, 0);
    assert.ok(body.final_native_geometry.max_delta_pt <= 0.001);
    assert.equal(body.motion_qa.passed, true);
    assert.equal(body.motion_qa.text_shift_mode, 'ctm');
    assert.equal(body.motion_qa.erased_glyphs, 0);
    assert.deepEqual(body.actual_native_vector_coordinate_audit.coordinate_errors, []);
    if (body.actual_native_vector_coordinate_audit.audit_code_sha256) {
      assert.equal(body.actual_native_vector_coordinate_audit.audit_code_sha256,
        qa.authoring_programs.find(p => /\/verify_native_vectors(?:_[a-z]+\d+)?\.py$/.test(p.path)).sha256);
    }
    assert.ok(body.actual_native_vector_coordinate_audit.max_coordinate_tolerance_pt <= 0.000001);
    assert.equal(body.new_korean_intrusion_on_native_ink_pixels, 0);
    assert.equal(body.new_body_korean_ink_inside_protected_figure_pixels, 0);
    let boundaries = 0;
    for (const line of body.line_reports) {
      if (line.fixed_design_cells) continue;
      for (const gap of line.gaps) {
        assert.ok(gap.new_gap >= -0.001 && gap.new_gap <= gap.ordinary_space + 0.001,
          `Excessive prose gap on page ${page.page}: ${gap.left} | ${gap.right}`);
        boundaries++;
      }
    }
    assert.equal(body.ordinary_gap_boundaries_verified, boundaries);
    const review = reviews.find(r => r.page === page.page && r.reviewed === true && r.proof_sha256 === page.proof_sha256);
    assert.ok(review, `Unreviewed natural-spacing page ${page.page}`);
    assert.equal(review.layout_sha256, page.qa_sha256);
    assert.equal(review.effective_plan_sha256, page.effective_plan_sha256);
    assert.equal(review.composer_sha256, page.composer_sha256);
  }
};

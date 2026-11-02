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
        qa.authoring_programs.find(p => p.path.endsWith('/verify_native_vectors.py')).sha256);
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

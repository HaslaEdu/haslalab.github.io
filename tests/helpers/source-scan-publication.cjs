const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

module.exports = function validateSourceScanPublication(root, qa, item) {
  const seen = new Map();
  function evidence(ref) {
    assert.ok(ref && typeof ref.path === 'string');
    assert.match(ref.sha256, /^[a-f0-9]{64}$/);
    const absolute = path.resolve(root, ref.path);
    assert.ok(absolute.startsWith(root + path.sep), 'Evidence must belong to this publication');
    let data = seen.get(ref.path);
    if (!data) {
      const raw = fs.readFileSync(absolute);
      assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), ref.sha256);
      data = JSON.parse(raw);
      seen.set(ref.path, data);
    } else {
      const raw = fs.readFileSync(absolute);
      assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), ref.sha256);
    }
    return ref.selector ? ref.selector.split('.').reduce((value, key) => {
      assert.ok(value && Object.hasOwn(value, key), 'Required actual QA field is missing: ' + key);
      return value[key];
    }, data) : data;
  }
  function zero(object, key) {
    assert.ok(Object.hasOwn(object, key), 'Required pixel comparison is missing: ' + key);
    assert.equal(object[key].pixels, 0, key);
  }
  assert.equal(qa.status, 'READY');
  assert.equal(qa.file, item.file);
  assert.equal(qa.sha256, item.sha256);
  assert.equal(qa.bytes, item.bytes);
  assert.equal(qa.pages, item.pages);
  assert.equal(qa.original_math_retyped, false);
  assert.equal(qa.original_math_resampled, false);
  assert.equal(qa.original_math_y_changed, false);
  assert.equal(qa.translated_point_sizes_fitted, false);
  assert.equal(qa.added_editorial_notes, 0);
  assert.match(qa.source_original_sha256, /^[a-f0-9]{64}$/);
  assert.match(qa.source_audited_sha256, /^[a-f0-9]{64}$/);
  if (qa.source_original_sha256 !== qa.source_audited_sha256) {
    const normalized = evidence(qa.source_normalization_qa);
    assert.equal(normalized.source_sha256, qa.source_original_sha256);
    assert.equal(normalized.normalized_sha256, qa.source_audited_sha256);
    assert.equal(normalized.original_bitmap_programs_retained, true);
    assert.equal(normalized.mathematics_recognized_or_retyped, false);
    assert.ok(normalized.render_validation.length >= item.pages);
    for (const row of normalized.render_validation) {
      assert.equal(row.scale, 4);
      assert.equal(row.changed_pixels, 0);
      assert.equal(row.original_rgb_sha256, row.normalized_rgb_sha256);
    }
  }
  evidence(qa.source_ready);
  const visual = evidence(qa.visual_review);
  const assembly = evidence(qa.assembly_qa);
  assert.equal(assembly.sha256, item.sha256);
  assert.equal(assembly.passed, true);
  assert.equal(assembly.pages.length, item.pages);
  assert.equal(visual.pages.length, item.pages);
  assert.equal(qa.page_proofs.length, item.pages);
  for (const [index, page] of qa.page_proofs.entries()) {
    assert.equal(page.page, index + 1);
    assert.match(page.proof_sha256, /^[a-f0-9]{64}$/);
    const scan = evidence(page.source_scan_qa);
    assert.equal(scan.passed, true);
    assert.equal(scan.final_sha256, page.proof_sha256);
    assert.equal(scan.source_sha256, qa.source_audited_sha256);
    assert.equal(scan.source_page, page.source_page);
    assert.equal(scan.render_scale, 4);
    assert.equal(scan.original_encoded_image_programs_masks_palettes_icc_and_declared_ctms_retained, true);
    assert.deepEqual(scan.original_native_font_program_changes, []);
    assert.equal(scan.original_pagegroup_unchanged, true);
    for (const key of ['outside_declared_language_and_math_motion', 'stationary_original_dark_ink_lost', 'independent_protected_source_ink_lost', 'new_prose_overlap_original_or_replayed_nonlanguage_ink', 'new_prose_expected_dark_pixels_missing']) zero(scan, key);
    assert.deepEqual(scan.thresholds, {source_deep_dark:160,new_prose_and_existing_ink:180,actual_missing_white:240});
    const style = evidence(page.actual_style_qa);
    assert.equal(style.passed, true);
    const signatures = [
      ['actual_new_prose_glyphs_checked','style_size_baseline_paint_or_sequence_failures'],
      ['actual_new_glyphs_checked','style_size_baseline_gid_or_stroke_errors'],
      ['actual_new_prose_glyph_paints_checked','style_font_size_baseline_or_stroke_failures']
    ];
    const profile = signatures.find(([count, failures]) => Object.hasOwn(style,count) && Object.hasOwn(style,failures));
    assert.ok(profile, 'Actual source-style GID/point/baseline/stroke audit is required');
    assert.ok(style[profile[0]] > 0);
    assert.deepEqual(style[profile[1]], []);
    if (Object.hasOwn(style,'invalid_actual_character_advances')) assert.deepEqual(style.invalid_actual_character_advances, []);
    if (Object.hasOwn(style,'unmatched_actual_glyphs')) assert.deepEqual(style.unmatched_actual_glyphs, []);
    const outlines = evidence(page.actual_outline_qa);
    assert.equal(outlines.passed, true);
    assert.equal(outlines.sha256, page.proof_sha256);
    assert.equal(outlines.delivered_pdf_modified, false);
    for (const row of outlines.pages) assert.deepEqual(row.empty_outlines, []);
    const math = evidence(page.independent_math_union_qa);
    assert.equal(math.passed, true);
    assert.ok(math.original_math_ink_expected_pixels > 0);
    assert.match(math.reference_sha256, /^[a-f0-9]{64}$/);
    if (Object.hasOwn(math,'missing_original_replayed_math_ink')) {
      zero(math,'missing_original_replayed_math_ink');
      zero(math,'new_prose_overlap_independent_math_union');
    } else {
      zero(math,'missing');
      zero(math,'overlap_new_prose');
    }
    if (item.language === 'ko') {
      const hangul = evidence(page.hangul_visibility_qa);
      assert.equal(hangul.sha256, page.proof_sha256);
      assert.equal(hangul.flagged_components, 0);
    }
    const joined = assembly.pages[index];
    assert.equal(joined.proof_sha256, page.proof_sha256);
    for (const key of ['mupdf_4x_changed_pixels','poppler_144dpi_changed_pixels']) assert.equal(joined[key], 0);
    for (const key of ['actual_font_programs_and_glyph_metadata_identical','original_encoded_images_masks_icc_and_ctms_identical','page_group_identical']) assert.equal(joined[key], true);
    const viewed = visual.pages[index];
    assert.equal(viewed.page, page.page);
    assert.equal(viewed.source_page, page.source_page);
    assert.equal(viewed.proof_sha256, page.proof_sha256);
    assert.equal(viewed.reviewed, true);
    assert.equal(viewed.source_math_atoms_reviewed, true);
  }
  assert.ok(qa.authoring_snapshots.length > 0);
  for (const snapshot of qa.authoring_snapshots) {
    assert.ok(Object.keys(snapshot.files).length > 0);
    for (const [file, hash] of Object.entries(snapshot.files)) {
      const raw = fs.readFileSync(path.join(root, snapshot.root, file));
      assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), hash);
    }
  }
};

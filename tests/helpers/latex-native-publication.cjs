const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

module.exports = function validateLatexNative(root, qa, item) {
  const hash = raw => crypto.createHash('sha256').update(raw).digest('hex');
  const read = (file, expected) => {
    const absolute = path.resolve(root, file);
    assert.ok(absolute.startsWith(root + path.sep));
    const raw = fs.readFileSync(absolute);
    if (expected) assert.equal(hash(raw), expected, file);
    return JSON.parse(raw);
  };
  for (const key of ['file', 'pages', 'bytes', 'sha256', 'language']) assert.equal(qa[key], item[key]);
  assert.equal(qa.schema, 'latex-native-joined-v1');
  assert.equal(qa.status, 'READY');
  assert.equal(qa.visual_review_required, false);
  for (const key of ['no_autoshrink', 'no_math_rasterization', 'no_paragraph_reflow', 'no_added_editorial_notes',
    'original_source_text_advances_preserved_by_nonpainting_encoded_prose', 'hidden_original_prose_has_empty_ActualText', 'all_pages_visually_reviewed']) assert.equal(qa[key], true, key);
  assert.match(qa.source_sha256, /^[a-f0-9]{64}$/);
  assert.equal(qa.page_audits.length, item.pages);
  const folder = path.dirname(path.join(root, item.qa));
  const reviews = fs.readdirSync(folder).filter(f => /^visual-review.*\.json$/.test(f))
    .flatMap(f => {
      const review = JSON.parse(fs.readFileSync(path.join(folder, f), 'utf8'));
      assert.equal(review.source_sha256, qa.source_sha256);
      return review.pages;
    });
  for (const [index, page] of qa.page_audits.entries()) {
    assert.equal(page.page, index + 1);
    assert.equal(page.final_vs_reviewed_proof_changed_pixels, 0);
    assert.equal(page.missing_hangul_glyphs, 0);
    assert.ok(page.visible_hangul_characters > 0);
    for (const key of ['final_vs_reviewed_proof_all_glyph_geometry_identical', 'page_box_preserved', 'original_font_programs_preserved',
      'original_image_encoded_streams_and_filters_preserved', 'original_image_geometry_preserved']) assert.equal(page[key], true, key);
    const body = read(page.qa_path, page.qa_sha256);
    const plan = read(page.plan_path, page.plan_sha256);
    assert.equal(plan.page, page.page);
    assert.equal(plan.source_sha256, qa.source_sha256);
    assert.equal(plan.source, body.source);
    assert.equal(body.source, qa.source);
    assert.equal(body.source_page_1based, page.page);
    assert.equal(body.source_sha256, qa.source_sha256);
    assert.equal(body.output_sha256, page.proof_sha256);
    assert.equal(body.plan_sha256, page.plan_sha256);
    for (const key of ['source_font_programs_preserved', 'source_images_preserved', 'source_drawings_preserved',
      'original_page_box_preserved', 'no_autoshrink', 'no_math_rasterization']) assert.equal(body[key], true, key);
    for (const key of ['suppression_control_native_geometry', 'final_native_geometry', 'selected_source_hidden_geometry']) {
      assert.deepEqual(body[key].missing, []);
      assert.equal(body[key].extra, 0);
      assert.equal(body[key].max_delta_pt, 0);
    }
    assert.equal(body.new_korean_intrusion_on_native_ink_pixels, 0);
    const plannedLabels = plan.raster_labels || [];
    if (plannedLabels.length) {
      assert.equal((body.raster_labels || []).length, plannedLabels.length);
      assert.equal(body.raster_language_changed_pixels_outside_reviewed_boxes, 0);
      assert.equal(body.original_image_encoded_stream_bytes_and_filters_preserved, true);
    } else {
      // Early body-only proofs predate the optional raster overlay fields.
      // Their hash-matched plans must independently confirm no label overlay.
      assert.deepEqual(body.raster_labels || [], []);
      if (Object.hasOwn(body, 'raster_language_changed_pixels_outside_reviewed_boxes')) {
        assert.equal(body.raster_language_changed_pixels_outside_reviewed_boxes, 0);
      }
    }
    assert.ok(reviews.some(r => r.page === page.page && r.reviewed === true && r.proof_sha256 === page.proof_sha256), `Unreviewed page ${page.page}`);
  }
};

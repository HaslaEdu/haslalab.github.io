const assert = require('node:assert/strict');

module.exports = function validateOfficialKorean(root, qa, item) {
  for (const key of ['file', 'pages', 'bytes', 'sha256', 'language']) assert.equal(qa[key], item[key]);
  assert.equal(qa.schema, 'official-korean-original-v1');
  assert.equal(qa.status, 'READY');
  assert.equal(qa.source_sha256, item.sha256);
  assert.equal(qa.output_sha256, item.sha256);
  assert.equal(qa.source.sha256, item.sha256);
  assert.equal(qa.source.pages, item.pages);
  assert.equal(qa.source.bytes, item.bytes);
  assert.equal(new URL(qa.source.url).hostname, 'olympiad.kchem.org');
  for (const key of ['untouched_official_original', 'all_pages_text_extracted', 'all_hangul_nonzero_glyph_ids', 'no_replacement_or_null_glyphs']) assert.equal(qa[key], true, key);
  assert.equal(qa.visual_review_pending, false);
  assert.equal(qa.visual_review.reviewed_all_46_pages, true);
  assert.equal(qa.visual_review.missing_or_corrupt_glyphs_observed, false);
  assert.equal(qa.visual_review.clipping_or_overlap_observed, false);
  assert.equal(qa.per_page.length, item.pages);
  for (const [index, page] of qa.per_page.entries()) {
    assert.equal(page.page, index + 1);
    assert.ok(page.hangul_characters > 0);
    assert.equal(page.zero_gid_hangul, 0);
    assert.deepEqual(page.potential_missing_glyphs, []);
  }
};

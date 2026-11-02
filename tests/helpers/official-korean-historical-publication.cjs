const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

module.exports = function validateOfficialHistorical(root, qa, item) {
  const read = (file, sha) => {
    const absolute = path.resolve(root, file);
    assert.ok(absolute.startsWith(root + path.sep));
    const raw = fs.readFileSync(absolute);
    assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), sha);
    return JSON.parse(raw);
  };
  for (const key of ['file', 'pages', 'bytes', 'sha256', 'language']) assert.equal(qa[key], item[key]);
  assert.equal(qa.schema, 'official-korean-historical-v1');
  assert.equal(qa.status, 'READY');
  assert.equal(qa.output_sha256, item.sha256);
  assert.ok(['olympiad.kchem.org', 'icho2020.tubitak.gov.tr'].includes(new URL(qa.source.url).hostname));
  assert.equal(qa.source_bytes_unchanged, true);
  assert.equal(qa.no_new_translation_or_typesetting, true);
  assert.equal(qa.all_pages_visually_reviewed, true);
  assert.equal(qa.visual_review_pending, false);
  const report = read(qa.source_report.path, qa.source_report.sha256);
  assert.equal(report.pages, item.pages);
  assert.equal(report.visual_review_pending, false);
  assert.equal(report.output_sha256 || report.sha256, item.sha256);
  assert.equal(report.per_page.length, item.pages);
  if (qa.preservation_mode === 'untouched-official-pdf') {
    assert.equal(qa.source.sha256, item.sha256);
    assert.ok(report.untouched_official_original || report.source_byte_identical);
    assert.equal(report.source_sha256, item.sha256);
  } else {
    assert.equal(qa.preservation_mode, 'native-office-export');
    assert.equal(report.source_office_sha256, qa.source.sha256);
    assert.equal(report.source_unchanged, true);
    assert.equal(report.all_pages_match_native_export, true);
    assert.equal(report.all_hangul_have_valid_visible_glyphs, true);
    assert.equal(report.selected_source_pdf_pages.length, item.pages);
    for (const row of report.per_page) assert.equal(row.native_export_page_render_identical, true);
    for (const glyph of Object.values(report.type3_code_zero_validation || {})) {
      assert.equal(glyph.is_not_notdef, true);
      assert.equal(glyph.code0_has_drawing_operators, true);
      assert.ok(glyph.code0_charproc_bytes > 0);
    }
  }
  const review = report.visual_review;
  assert.ok(review.reviewed || review.all_pages_reviewed);
  if (review.reviewed_pages) assert.deepEqual(review.reviewed_pages, Array.from({length:item.pages}, (_,i) => i + 1));
  for (const key of ['missing_visible_glyphs_observed', 'clipped_or_overlapping_content_observed',
    'observed_missing_visible_glyphs', 'observed_clipping', 'observed_overlapping_text']) {
    if (Object.hasOwn(review, key)) assert.equal(review[key], false);
  }
  for (const contact of qa.visual_evidence) {
    const raw = fs.readFileSync(path.join(root, contact.path));
    assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), contact.sha256);
  }
};

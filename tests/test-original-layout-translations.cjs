const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const read = file => JSON.parse(fs.readFileSync(path.join(root, file), 'utf8'));
const assets = read('pdf-assets.json');
const fonts = read('tools/translation_font_validation.json').files;
const published = read('tools/original_style_publication.json');
assert.ok(published.length > 0);
for (const item of published) {
  const qa = read(item.qa);
  const font = fonts.find(row => row.file === item.file);
  assert.ok(font, item.file);
  assert.equal(assets[item.file], item.bytes, 'Released bytes must match the reviewed original-layout PDF');
  assert.equal(font.bytes, item.bytes);
  assert.equal(font.sha256, item.sha256);
  assert.equal(qa.sha256, item.sha256);
  assert.equal(qa.pages, item.pages);
  assert.equal(qa.page_audits.length, item.pages, 'Every page needs a final joined-PDF audit');
  for (const key of ['native_glyphs_changed', 'protected_glyphs_selected_for_erasure', 'changed_pixels_in_native_glyph_neighborhood', 'changed_pixels_outside_prose', 'hangul_visibility_candidates', 'equation_images']) {
    assert.equal(qa[key], 0, `${item.file}: ${key}`);
  }
  assert.equal(qa.autoshrink, false);
  assert.equal(qa.reflow, false);
  assert.equal(qa.added_titles_or_errata, false);
  for (const page of qa.page_audits) {
    assert.equal(page.proof_sha256, item.sha256, 'Page proofs must audit the released joined file');
    assert.deepEqual(page.native_glyphs_changed, []);
    assert.deepEqual(page.protected_glyphs_selected_for_erasure, []);
    assert.equal(page.changed_pixels_in_native_glyph_neighborhood, 0);
    assert.equal(page.changed_pixels_outside_prose, 0);
  }
}
for (const font of read('tools/ko/fonts/NOTO_CJK_PROVENANCE.json')) {
  const data = fs.readFileSync(path.join(root, 'tools/ko/fonts', font.file));
  assert.equal(crypto.createHash('sha256').update(data).digest('hex'), font.sha256);
  assert.ok([400, 700].includes(font.weight), 'Use the actual static regular/bold font masters');
}
console.log(JSON.stringify({originalLayoutEditions: published.length, pages: published.reduce((n, p) => n + p.pages, 0)}));

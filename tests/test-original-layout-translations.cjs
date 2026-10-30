const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const read = file => JSON.parse(fs.readFileSync(path.join(root, file), 'utf8'));
const assets = read('pdf-assets.json');
const fonts = read('tools/translation_font_validation.json').files;
const published = read('tools/original_style_publication.json');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const versions = html.match(/const ORIGINAL_LAYOUT_PDF_VERSIONS=(\{[^;]+\});/);
assert.ok(versions, 'Restored PDFs need distinct browser-cache URLs');
const revisions = JSON.parse(versions[1]);
const begin = html.indexOf('const thyUrl=');
const end = html.indexOf('/* Competition or organiser websites', begin);
const base = 'https://haslalab-pdf.haslalab.workers.dev/pdf/';
const thyUrl = vm.runInNewContext(html.slice(begin, end) + '\nthyUrl;', {PDF_BASE: base, ORIGINAL_LAYOUT_PDF_VERSIONS: revisions, window: {KPHE_PDF_VERSIONS: {'pdfx/kphe/existing.pdf': 'existing'}}});
assert.ok(published.length > 0);
for (const item of published) {
  const qa = read(item.qa);
  const font = fonts.find(row => row.file === item.file);
  assert.equal(revisions[item.file], item.sha256.slice(0, 16));
  assert.equal(thyUrl(item.file), base + item.file + '?v=' + item.sha256.slice(0, 16));
  assert.equal(thyUrl(base + item.file), thyUrl(item.file));
  assert.ok(font, item.file);
  assert.equal(assets[item.file], item.bytes, 'Released bytes must match the reviewed original-layout PDF');
  assert.equal(font.bytes, item.bytes);
  assert.equal(font.sha256, item.sha256);
  for (const alias of item.aliases || []) {
    assert.equal(assets[alias], item.bytes);
    assert.equal(revisions[alias], item.sha256.slice(0, 16));
    assert.equal(fonts.find(row => row.file === alias).sha256, item.sha256);
  }
  if (['cpho-native-problems', 'cpho-native-raster-problems'].includes(item.audit_schema)) {
    assert.equal(qa.sha256, item.sha256);
    assert.equal(qa.passed, true);
    assert.equal(qa.pages.length, item.pages);
    for (const page of qa.pages) {
      assert.equal(page.proof_sha256, item.sha256);
      assert.equal(page.passed, true);
      for (const key of ['native_glyphs_changed', 'bit_exact_native_nonspace_glyphs_changed', 'protected_glyphs_selected_for_erasure', 'remaining_han']) assert.deepEqual(page[key], []);
      for (const key of ['changed_pixels_in_native_glyph_neighborhood', 'changed_pixels_outside_prose', 'unexpected_nul']) assert.equal(page[key], 0);
      assert.equal(page.original_images_identical, true);
      assert.equal(page.original_font_programs_identical, true);
    }
    if (item.audit_schema === 'cpho-native-raster-problems') {
      for (const page of qa.pages) {
        assert.equal(page.unexplained_original_image_pixel_changes, 0);
        assert.equal(page.original_image_pixels_changed_outside_caption_text, page.inherited_footer_prose_at_image_antialias_edge);
        assert.ok(page.caption_number_pixels_changed.every(x => x.changed_pixels === 0));
        assert.deepEqual(page.translation_style_violations, []);
        assert.ok(page.translation_baseline_max_delta_pt < 0.0001);
        assert.ok(page.translation_size_max_delta_pt < 0.0001);
      }
      if (item.language === 'ko') {
        assert.deepEqual(qa.hangul_visibility.unexpected_components, []);
        assert.equal(qa.hangul_visibility.flagged_components, qa.hangul_visibility.inherited_source_footer_occlusion.length);
        assert.ok(qa.hangul_visibility.inherited_source_footer_occlusion.every(x => x.page === 2 && x.rect[1] > 750));
      }
      const poppler = read(item.poppler_qa).filter(row => row.lang === item.language.toUpperCase());
      assert.equal(poppler.length, item.pages);
      assert.ok(poppler.every(row => row.outside_prose_changed_pixels === 0));
      continue;
    }
    if (item.language === 'ko') assert.equal(qa.hangul_visibility.flagged_components, 0);
    const poppler = read(item.poppler_qa).filter(row => row.lang === item.language.toUpperCase());
    assert.equal(poppler.length, item.pages);
    assert.ok(poppler.every(row => row.outside_changed === 0));
    const identity = read(item.render_identity_qa).filter(row => row.lang === item.language.toUpperCase());
    assert.equal(identity.length, item.pages);
    assert.ok(identity.every(row => row.entire_page_changed_pixels === 0));
    continue;
  }
  if (item.audit_schema === 'native-outlines-and-control') {
    assert.equal(qa.output_sha256, item.sha256);
    assert.equal(qa.pages, item.pages);
    assert.equal(qa.page_audits.length, item.pages);
    for (const key of ['no_autoshrink', 'no_equation_rasterization', 'no_paragraph_reflow', 'no_added_editorial_notes']) assert.equal(qa[key], true);
    assert.equal(qa.visual_review_required, false);
    assert.deepEqual(qa.visual_review.reviewed_pages, Array.from({length: item.pages}, (_, i) => i + 1));
    for (const page of qa.page_audits) {
      for (const key of ['outside_prose_changed_pixels', 'missing_or_moved_native_glyphs', 'missing_or_moved_math_glyphs', 'original_math_ink_changed_pixels', 'original_native_ink_changed_pixels', 'original_figure_ink_changed_pixels', 'source_to_suppression_control_native_ink_changed_pixels', 'korean_intrusion_on_native_ink_pixels', 'final_vs_reviewed_proof_changed_pixels']) assert.equal(page[key], 0, `${item.file}: ${key}`);
      for (const key of ['native_images_unchanged', 'native_vector_drawings_unchanged', 'suppression_control_native_geometry_unchanged', 'suppression_control_source_font_programs_unchanged', 'final_vs_reviewed_proof_glyph_geometry_identical', 'original_font_sizes_and_baselines_identical']) assert.equal(page[key], true);
      const plan = fs.readFileSync(path.join(root, page.plan.replaceAll('\\', '/')));
      assert.equal(crypto.createHash('sha256').update(plan).digest('hex'), page.plan_sha256);
    }
    const hangul = read(item.hangul_qa);
    assert.equal(hangul.sha256, item.sha256);
    assert.equal(hangul.flagged_components, 0);
    if (item.native_ascii_qa) {
      const ascii = read(item.native_ascii_qa);
      assert.equal(ascii.sha256, item.sha256);
      assert.equal(ascii.nonpositive_or_missing_width_count, 0);
      assert.ok(ascii.page_audits.every(page => page.nonpositive_or_missing_widths.length === 0));
    }
    continue;
  }
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
assert.equal(thyUrl('pdfx/kphe/existing.pdf'), 'pdfx/kphe/existing.pdf?v=existing');
assert.equal(thyUrl('unchanged.pdf'), base + 'unchanged.pdf');
for (const font of read('tools/ko/fonts/NOTO_CJK_PROVENANCE.json')) {
  const data = fs.readFileSync(path.join(root, 'tools/ko/fonts', font.file));
  assert.equal(crypto.createHash('sha256').update(data).digest('hex'), font.sha256);
  assert.ok([400, 700].includes(font.weight), 'Use the actual static regular/bold font masters');
}
console.log(JSON.stringify({originalLayoutEditions: published.length, pages: published.reduce((n, p) => n + p.pages, 0)}));

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
  const record = read(item.qa);
  const assignedReady = item.audit_schema === 'legacy-reviewed-ready';
  const qa = assignedReady ? record.source_audit : record;
  if (assignedReady) {
    assert.equal(record.status, 'READY');
    assert.equal(record.sha256, item.sha256);
    assert.equal(record.pages, item.pages);
    assert.equal(record.final_vs_reviewed_proof_changed_pixels, 0);
    const review = read(record.visual_review_file);
    assert.equal(review.source_sha256, qa.source_sha256);
    assert.deepEqual(review.pages.map(page => page.page).sort((a,b) => a-b), Array.from({length:item.pages}, (_,i) => i+1));
    for (const page of qa.page_audits) {
      const checked = review.pages.find(row => row.page === page.source_page);
      assert.equal(checked.reviewed, true);
      assert.equal(checked.proof_sha256, page.proof_sha256);
    }
  }
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
  if (item.audit_schema === 'cpho-original-combined') {
    assert.equal(qa.sha256, item.sha256);
    assert.equal(qa.bytes, item.bytes);
    assert.equal(qa.pages, item.pages);
    assert.equal(qa.passed, true);
    assert.equal(qa.page_audits.length, item.pages);
    for (const flag of ['original_page_order', 'original_shared_resources_retained', 'no_autoshrink', 'no_reflow', 'no_equation_rasterization']) assert.equal(qa[flag], true);
    assert.equal(qa.redrawn_figures, 0);
    assert.equal(qa.printed_editorial_notes, 0);
    for (const page of qa.page_audits) {
      assert.equal(page.passed, true);
      for (const key of ['native_glyphs_changed', 'protected_glyphs_selected_for_erasure', 'original_form_glyph_metadata_changed', 'final_vs_reviewed_proof_glyph_metadata_changed', 'unexpected_untranslated_body_han']) assert.deepEqual(page[key], []);
      for (const key of ['changed_pixels_outside_prose', 'changed_pixels_in_native_glyph_neighborhood', 'final_vs_reviewed_proof_changed_pixels']) assert.equal(page[key], 0);
      assert.equal(page.original_font_programs_identical, true);
      assert.equal(page.original_form_raw_and_decoded_programs_identical, true);
      assert.equal(page.graphics_audit.original_graphics_ink_changed_pixels, 0);
      assert.equal(page.graphics_audit.original_image_and_smask_programs_and_positions_identical, true);
      assert.equal(page.autoshrink, false);
      assert.equal(page.reflow, false);
      assert.equal(page.math_images, false);
      for (const run of page.placements) assert.equal(run.size, run.source_size);
    }
    const poppler = read(item.poppler_qa);
    assert.equal(poppler.sha256, item.sha256);
    assert.equal(poppler.passed, true);
    assert.equal(poppler.pages.length, item.pages);
    for (const page of poppler.pages) {
      assert.equal(page.changed_pixels_outside_prose, 0);
      assert.equal(page.changed_pixels_in_native_control_ink, 0);
      assert.equal(page.coarse_fringe_control_pixels_at_least_250, true);
    }
    const ink = read(item.font_ink_qa);
    assert.equal(ink.sha256, item.sha256);
    assert.equal(ink.passed, true);
    assert.equal(ink.pages.length, item.pages);
    for (const key of ['nonpositive_width_codes', 'new_missing_or_han_glyphs', 'empty_new_nonspace_glyphs']) assert.deepEqual(ink[key], []);
    const review = read(item.visual_qa);
    assert.equal(review.sha256, item.sha256);
    assert.deepEqual(review.pages.map(p => p.page), Array.from({length:item.pages}, (_,i) => i+1));
    for (const row of review.pages) {
      assert.equal(row.reviewed, true);
      assert.equal(row.proof_sha256, qa.page_audits[row.page-1].proof_sha256);
    }
    if (item.language === 'ko') {
      const hangul = read(item.hangul_qa);
      assert.equal(hangul.sha256, item.sha256);
      assert.equal(hangul.pages.length, item.pages);
      assert.equal(hangul.flagged_components, 0);
    }
    continue;
  }
  if (item.audit_schema === 'cpho-native-labelled-problems') {
    assert.equal(qa.sha256, item.sha256);
    assert.equal(qa.passed, true);
    assert.equal(qa.pages.length, item.pages);
    assert.equal(qa.final_file_byte_identical_to_verified_preview, true);
    assert.equal(qa.verified_preview_sha256, item.sha256);
    for (const page of qa.pages) {
      assert.equal(page.proof_sha256, item.sha256);
      assert.equal(page.passed, true);
      for (const key of ['native_glyphs_changed', 'bit_exact_native_nonspace_glyphs_changed', 'protected_glyphs_selected_for_erasure', 'unexpected_han', 'unexpected_nul', 'translation_style_violations', 'graphic_collision_components']) assert.deepEqual(page[key], []);
      for (const key of ['changed_pixels_in_native_glyph_neighborhood', 'changed_pixels_outside_prose', 'changed_pixels_in_native_bitmap_ink_outside_language', 'changed_pixels_in_native_vector_graphics']) assert.equal(page[key], 0);
      assert.ok(page.translation_size_max_delta_pt < 0.0001);
      // Body baselines are checked to 0.0001pt by the style audit. Its
      // inferred, rotated bitmap-label baselines allow 0.005pt rounding.
      assert.ok(page.translation_baseline_max_delta_pt < 0.005);
      assert.equal(page.original_font_programs_identical, true);
      assert.equal(page.original_images_and_smask_streams_identical, true);
    }
    if (item.language === 'ko') assert.equal(qa.hangul_visibility.flagged_components, 0);
    const poppler = read(item.poppler_qa);
    assert.equal(poppler.passed, true);
    assert.equal(poppler.prose_antialias_guard_px, 1);
    const rendered = poppler.files.find(row => row.file === item.file);
    assert.equal(rendered.sha256, item.sha256);
    assert.equal(rendered.pages.length, item.pages);
    assert.ok(rendered.pages.every(page => page.changed_pixels_outside_prose === 0 && page.changed_pixels_in_native_actual_ink === 0 && page.maximum_fringe_distance_px <= 1));
    const identity = read(item.render_identity_qa).files.find(row => row.file === item.file);
    assert.equal(identity.sha256, item.sha256);
    assert.equal(identity.byte_identical, true);
    assert.deepEqual(identity.reviewed_pages, Array.from({length:item.pages}, (_,i) => i+1));
    continue;
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
  if (['native-outlines-and-control', 'legacy-fixed-native', 'legacy-reviewed-ready'].includes(item.audit_schema)) {
    assert.equal(qa.output_sha256, item.sha256);
    assert.equal(qa.pages, item.pages);
    assert.equal(qa.page_audits.length, item.pages);
    for (const key of ['no_autoshrink', 'no_equation_rasterization', 'no_paragraph_reflow', 'no_added_editorial_notes']) assert.equal(qa[key], true);
    if (qa.source_page_count && qa.source_page_count !== qa.pages) {
      assert.ok(qa.source_page_selection_note, 'A multilingual original requires an explicit subsection selection');
      assert.equal(new Set(qa.source_pages_1based).size, qa.pages);
      assert.ok(qa.source_pages_1based.every(page => page > 0 && page <= qa.source_page_count));
    }
    if (!assignedReady) {
      assert.equal(qa.visual_review_required, false);
      assert.deepEqual(qa.visual_review.reviewed_pages, Array.from({length: item.pages}, (_, i) => i + 1));
    }
    for (const page of qa.page_audits) {
      if (['legacy-fixed-native', 'legacy-reviewed-ready'].includes(item.audit_schema)) {
        for (const key of ['native_glyphs_changed', 'protected_glyphs_selected_for_erasure', 'unreviewed_english_prose_runs']) assert.deepEqual(page[key], []);
        for (const key of ['changed_pixels_in_native_glyph_neighborhood', 'changed_pixels_outside_prose', 'final_vs_reviewed_proof_changed_pixels', 'equation_images']) assert.equal(page[key], 0);
        for (const key of ['source_font_programs_and_names_unchanged', 'source_images_bytes_and_rects_unchanged']) assert.equal(page[key], true);
        if (page.raster_language_overlays) assert.equal(page.source_original_vector_drawings_preserved, true);
        else assert.equal(page.source_vector_drawings_unchanged, true);
        assert.equal(page.autoshrink, false);
        assert.equal(page.reflow, false);
        if (page.raster_language_overlays) {
          assert.equal(page.raster_language_region_count, page.raster_language_overlays.length);
          for (const key of ['changed_pixels_outside_raster_language_regions', 'changed_pixels_in_visible_raster_graphics', 'changed_native_picture_feature_pixels_inside_language_regions', 'changed_native_picture_feature_pixels_outside_language_regions', 'additional_clipped_reuses_of_unchanged_original_image']) assert.equal(page[key], 0);
          for (const key of ['original_bitmap_visual_pixels_unchanged_outside_language_regions', 'no_new_bitmap_pixel_data']) assert.equal(page[key], true);
          assert.equal(typeof page.original_visible_raster_graphics_excluded_from_new_paint, 'boolean');
          if (page.native_picture_feature_masks.length) assert.equal(page.original_visible_raster_graphics_excluded_from_new_paint, true);
          assert.ok(page.raster_font_metadata_note, 'Bitmap font measurements must record their inferred provenance');
        }
        const plan = fs.readFileSync(path.join(root, page.plan.replaceAll('\\', '/')));
        assert.equal(crypto.createHash('sha256').update(plan).digest('hex'), page.plan_sha256);
        const spaces = page.mutable_prose_whitespace_glyphs || [];
        if (spaces.length) {
          assert.ok(JSON.parse(plan).journal_selected_prose_whitespace, 'Mutable spaces need an explicitly selected prose journal');
          assert.equal(page.selected_prose_actual_whitespace_glyphs_checked, spaces.length);
          assert.ok(spaces.every(glyph => glyph.c.length > 0 && glyph.c.trim() === '' && typeof glyph.font === 'string' && glyph.size > 0 && glyph.origin.length === 2 && glyph.origin.every(Number.isFinite)));
        }
        continue;
      }
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

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
  if (item.audit_schema === 'natural-spacing-v2') {
    require('./helpers/natural-spacing-publication.cjs')(root, qa, item);
    continue;
  }
  if (item.audit_schema === 'natural-spacing-cpho') {
    require('./helpers/cpho-natural-publication.cjs')(root, qa, item);
    continue;
  }
  if (item.audit_schema === 'natural-spacing-reviewed') {
    assert.equal(qa.status, 'READY');
    assert.equal(qa.sha256, item.sha256);
    assert.equal(qa.bytes, item.bytes);
    assert.equal(qa.pages, item.pages);
    for (const key of ['native_actual_glyph_missing', 'new_batang_empty_outlines', 'hangul_visibility_loss_candidates', 'outside_motion_ink_pixels', 'figure_changed_pixels']) assert.equal(qa[key], 0, key);
    for (const key of ['original_fonts_and_image_programs_retained', 'page_groups_preserved', 'no_added_editorial_notes']) assert.equal(qa[key], true, key);
    assert.equal(qa.original_point_sizes_scaled, false);
    assert.equal(qa.page_proofs.length, item.pages);
    for (const page of qa.page_proofs) {
      assert.equal(page.final_vs_reviewed_proof_changed_pixels, 0);
      assert.match(page.source_pdf_sha256, /^[a-f0-9]{64}$/);
      assert.equal(page.native_move_qa.passed, true);
      assert.equal(page.native_move_qa.font_programs_unchanged, true);
      assert.equal(page.native_move_qa.native_vector_path_bytes_preserved, true);
      assert.deepEqual(page.native_move_qa.native_glyph_mismatches, []);
      assert.equal(page.new_empty_hangul_outlines, 0);
    }
    for (const [file, hash] of Object.entries(qa.authoring_snapshot_sha256)) {
      const raw = fs.readFileSync(path.join(root, qa.authoring_snapshotroot, file.replaceAll('\\', '/')));
      assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), hash);
    }
    for (const page of qa.page_audits) {
      const raw = fs.readFileSync(path.join(root, page.path));
      assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), page.sha256);
    }
    assert.equal(qa.independent_original_input_moved_math_audits.length, item.pages);
    for (const row of qa.independent_original_input_moved_math_audits) {
      const raw = fs.readFileSync(path.join(root, row.path));
      assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), row.sha256);
      const ink = JSON.parse(raw);
      assert.equal(ink.passed, true);
      assert.equal(ink.newly_missing_native_ink_pixels, 0);
      assert.deepEqual(ink.missing_final_native_glyphs, []);
      assert.deepEqual(ink.source_outline_audit.missing_source_outline_signatures, []);
    }
    const review = read(item.visual_qa);
    assert.ok(review);
    continue;
  }
  if (item.audit_schema === 'cpho-2013-reviewed-problems') {
    assert.equal(qa.status, 'READY');
    assert.equal(qa.sha256, item.sha256);
    assert.equal(qa.bytes, item.bytes);
    assert.equal(qa.pages, item.pages);
    assert.equal(qa.added_editorial_notes, 0);
    assert.equal(qa.all_source_proof_audits_passed, true);
    assert.equal(qa.source_audits.length, item.pages);
    assert.equal(qa.joined_vs_reviewed_proofs.length, item.pages);
    const poppler = read(item.poppler_qa).pages.filter(p => p.language === item.language);
    const visual = read(item.visual_qa).pages.filter(p => p.language === item.language);
    assert.equal(poppler.length, item.pages);
    assert.equal(visual.length, item.pages);
    for (let i = 0; i < item.pages; i++) {
      const page = qa.source_audits[i];
      assert.equal(page.passed, true);
      assert.equal(page.translation_scope_complete, true);
      for (const key of ['native_glyphs_changed', 'protected_glyphs_selected_for_erasure', 'bit_exact_native_nonspace_glyphs_changed', 'translation_style_violations', 'translation_stroke_width_violations']) assert.deepEqual(page[key], []);
      assert.equal(page.changed_pixels_in_native_glyph_neighborhood, 0);
      assert.equal(page.changed_pixels_outside_prose, 0);
      assert.equal(page.original_font_programs_identical, true);
      assert.equal(page.original_page_group_unchanged, true);
      assert.equal(page.original_graphics.original_image_and_smask_programs_and_positions_identical, true);
      assert.deepEqual(page.new_ascii_widths.nonpositive_or_missing_widths, []);
      if (page.reviewed_original_prose_guard_profile) {
        const witness = page.reviewed_original_prose_guard_profile;
        assert.equal(witness.source_sha256, qa.source_sha256);
        assert.equal(witness.passed, true);
        assert.equal(witness.source_to_proof_actual_nontext_changed, 0);
        assert.equal(witness.control_to_proof_actual_nontext_changed, 0);
        assert.equal(witness.control_to_proof_guard_changed, 0);
        assert.deepEqual(witness.source_to_control_guard_pixels_xy, witness.source_to_proof_guard_pixels_xy);
        assert.deepEqual(witness.isolated_glyph_suppression_guard_pixels_xy, witness.source_to_proof_guard_pixels_xy);
      } else if (page.reviewed_raster_language_audit) {
        const raster = page.reviewed_raster_language_audit;
        assert.equal(raster.document_specific_preservation_passed, true);
        for (const key of ['autoshrink', 'reflow', 'original_image_replacement']) assert.equal(raster[key], false);
        assert.equal(raster.new_equation_images, 0);
        for (const key of ['changed_pixels_outside_old_and_new_language', 'changed_original_actual_nonlanguage_ink_pixels', 'changed_pixels_in_explicit_math_protection']) assert.equal(raster.checks[key], 0);
        assert.equal(raster.checks.original_image_programs_and_raw_bytes_and_filters_and_smask_and_ctm_unchanged, true);
        const witness = raster.document_specific_old_prose_guard_witness;
        assert.equal(witness.passed, true);
        assert.equal(witness.source_sha256, qa.source_sha256);
        assert.equal(witness.proof_sha256, page.proof_sha256);
        for (const key of ['old_language_erasure_actual_native_ink_changed', 'new_language_actual_native_ink_changed', 'new_language_expanded_guard_changed', 'source_to_proof_actual_native_ink_changed']) assert.equal(witness[key], 0);
        assert.deepEqual(witness.old_language_erasure_guard_pixels_xy, witness.source_to_proof_coarse_guard_pixels_xy);
      } else assert.equal(page.original_graphics.original_graphics_ink_changed_pixels, 0);
      const joined = qa.joined_vs_reviewed_proofs[i];
      assert.equal(joined.passed, true);
      assert.equal(joined.reviewed_proof_sha256, page.proof_sha256);
      assert.equal(joined.joined_vs_reviewed_proof_changed_pixels_4x, 0);
      for (const key of ['glyph_metadata_identical', 'original_image_and_smask_programs_identical', 'original_font_programs_identical', 'page_group_identical']) assert.equal(joined[key], true);
      assert.deepEqual(joined.new_ascii_widths.nonpositive_or_missing_widths, []);
      const rendered = poppler.find(p => p.source_page === page.source_page);
      assert.equal(rendered.proof_sha256, page.proof_sha256);
      assert.equal(rendered.passed, true);
      assert.equal(rendered.outside_prose_pixels, 0);
      assert.equal(rendered.changed_visible_native_ink_pixels, 0);
      const viewed = visual.find(p => p.source_page === page.source_page);
      assert.equal(viewed.reviewed, true);
      assert.equal(viewed.proof_sha256, page.proof_sha256);
    }
    const outlines = read(item.font_ink_qa);
    assert.equal(outlines.sha256, item.sha256);
    assert.equal(outlines.passed, true);
    assert.equal(outlines.pages.length, item.pages);
    for (const page of outlines.pages) assert.deepEqual(page.empty_outlines, []);
    if (item.language === 'ko') {
      assert.equal(qa.hangul_visibility.sha256, item.sha256);
      assert.equal(qa.hangul_visibility.flagged_components, 0);
    }
    continue;
  }
  if (item.audit_schema === 'cpho-2005-native-problems') {
    assert.equal(qa.sha256, item.sha256);
    assert.equal(qa.bytes, item.bytes);
    assert.equal(qa.pages, item.pages);
    for (const flag of ['autoshrink', 'new_equation_rasterisation', 'paragraph_reflow', 'new_editorial_notes', 'visual_review_required']) assert.equal(qa[flag], false);
    assert.equal(qa.native_source_fonts_and_math_and_figures_preserved, true);
    assert.equal(qa.new_empty_outline_count, 0);
    assert.equal(qa.page_audits.length, item.pages);
    assert.equal(qa.final_assembly_audits.length, item.pages);
    for (const page of qa.page_audits) {
      assert.equal(page.passed, true);
      assert.equal(page.translation_scope_complete, true);
      for (const key of ['native_glyphs_changed', 'protected_glyphs_selected_for_erasure', 'bit_exact_native_nonspace_glyphs_changed', 'translation_style_violations', 'translation_stroke_width_violations']) assert.deepEqual(page[key], []);
      for (const key of ['changed_pixels_in_native_glyph_neighborhood', 'changed_pixels_outside_prose']) assert.equal(page[key], 0);
      assert.equal(page.original_font_programs_identical, true);
      assert.equal(page.original_page_group_unchanged, true);
      assert.equal(page.original_graphics.original_graphics_ink_changed_pixels, 0);
      assert.equal(page.original_graphics.original_image_and_smask_programs_and_positions_identical, true);
      assert.deepEqual(page.new_ascii_widths.nonpositive_or_missing_widths, []);
      assert.equal(page.new_outline_ink.empty_outline_count, 0);
    }
    for (const page of qa.final_assembly_audits) {
      assert.equal(page.passed, true);
      assert.equal(page.final_vs_reviewed_proof_changed_pixels, 0);
      for (const flag of ['all_trace_glyph_metadata_identical', 'all_actual_font_programs_identical', 'new_translation_pdf_widths_and_cmaps_identical', 'all_image_and_smask_raw_decoded_programs_and_positions_identical', 'original_font_programs_identical']) assert.equal(page[flag], true);
      assert.equal(page.original_graphics.original_graphics_ink_changed_pixels, 0);
    }
    assert.equal(qa.visual_review.reviewed, true);
    assert.equal(qa.visual_review.overflow_or_occlusion_observed, false);
    const poppler = read(item.poppler_qa).pages.filter(p => p.language === item.language);
    assert.equal(poppler.length, item.pages);
    for (const page of poppler) {
      assert.equal(page.final_sha256, item.sha256);
      assert.equal(page.passed, true);
      for (const key of ['changed_pixels_outside_prose_aa_guard', 'changed_original_actual_control_ink_pixels', 'source_to_control_actual_native_ink_changes', 'new_translation_on_actual_native_ink_pixels']) assert.equal(page[key], 0);
      assert.deepEqual(page.explicit_native_pixel_exclusions, []);
    }
    const images = read(item.image_render_qa);
    assert.equal(images.passed, true);
    const pages = images.pages.filter(p => p.language === item.language);
    assert.equal(pages.length, item.pages);
    for (const page of pages) {
      assert.equal(page.final_sha256, item.sha256);
      assert.equal(page.passed, true);
      for (const image of page.image_audits) {
        assert.equal(image.whole_image_bbox_changed_pixels, 0);
        assert.equal(image.full_image_dictionary_and_raw_decoded_palette_icc_mask_program_graph_identical, true);
      }
    }
    if (item.language === 'ko') {
      const h = read(item.hangul_qa);
      assert.equal(h.sha256, item.sha256);
      assert.equal(h.flagged_components, 0);
    }
    continue;
  }
  if (item.audit_schema === 'cpho-same-face-problems') {
    assert.equal(qa.sha256, item.sha256);
    assert.equal(qa.passed, true);
    assert.equal(qa.pages.length, item.pages);
    for (const page of qa.pages) {
      assert.equal(page.proof_sha256, item.sha256);
      assert.equal(page.passed, true);
      for (const key of ['native_glyphs_changed', 'bit_exact_native_nonspace_glyphs_changed', 'protected_glyphs_selected_for_erasure', 'translation_style_violations']) assert.deepEqual(page[key], []);
      for (const key of ['changed_pixels_in_native_glyph_neighborhood', 'changed_pixels_outside_prose', 'unexpected_nul']) assert.equal(Array.isArray(page[key]) ? page[key].length : page[key], 0, `${item.file}: ${key}`);
      assert.equal(page.original_font_programs_identical, true);
      assert.ok(page.translation_size_max_delta_pt < 0.0001);
      // Native transformed annotation coordinates accumulate PDF float
      // rounding below 0.002pt; independent rendered-ink checks still apply.
      assert.ok(page.translation_baseline_max_delta_pt < 0.002);
      if (page.original_images_identical !== undefined) assert.equal(page.original_images_identical, true);
      if (page.unexplained_original_image_pixel_changes !== undefined) assert.equal(page.unexplained_original_image_pixel_changes, 0);
      if (page.original_images_and_smask_streams_identical !== undefined) assert.equal(page.original_images_and_smask_streams_identical, true);
      if (page.changed_pixels_in_native_vector_graphics !== undefined) assert.equal(page.changed_pixels_in_native_vector_graphics, 0);
      if (page.changed_pixels_in_native_bitmap_ink_outside_language !== undefined) assert.equal(page.changed_pixels_in_native_bitmap_ink_outside_language, 0);
    }
    const poppler = read(item.poppler_qa);
    assert.equal(poppler.sha256, item.sha256);
    assert.equal(poppler.passed, true);
    assert.equal(poppler.pages.length, item.pages);
    assert.equal(poppler.prose_antialias_guard_px, 1);
    for (const page of poppler.pages) {
      assert.equal(page.passed, true);
      assert.equal(page.changed_pixels_outside_prose, 0);
      assert.equal(page.changed_pixels_in_original_visible_ink, 0);
      assert.equal(page.original_page_group_identical, true);
      assert.equal(page.original_image_and_smask_programs_identical, true);
      assert.deepEqual(page.real_glyphs.failures, []);
      assert.equal(page.real_glyphs.actual_outlines_and_advances_checked, page.real_glyphs.new_nonspace_glyphs);
    }
    continue;
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

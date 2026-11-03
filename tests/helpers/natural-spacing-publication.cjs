const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

module.exports = function validate(root, record, item) {
  const pinned = (file, hash) => {
    const raw = fs.readFileSync(path.join(root, file.replaceAll('\\', '/')));
    assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), hash, file);
    return JSON.parse(raw);
  };
  assert.equal(record.status, 'READY');
  for (const key of ['sha256', 'bytes', 'pages']) assert.equal(record[key], item[key]);
  const v = record.validation;
  for (const key of ['native_ink_missing_pixels', 'new_batang_empty_outlines', 'hangul_visibility_loss_candidates', 'outside_text_and_intended_math_motion', 'changed_figures']) assert.equal(v[key], 0, key);
  assert.equal(v.original_point_sizes_scaled, false);
  assert.equal(v.original_font_image_programs_and_page_groups_retained, true);
  assert.equal(v.no_added_editorial_notes, true);
  assert.equal(record.page_proofs.length, item.pages);
  for (const page of record.page_proofs) {
    assert.equal(page.final_vs_reviewed_proof_changed_pixels, 0);
    assert.match(page.proof_sha256, /^[a-f0-9]{64}$/);
    assert.match(page.source_pdf_sha256, /^[a-f0-9]{64}$/);
    const move = page.native_move_qa;
    assert.equal(move.passed, true);
    assert.equal(move.font_programs_unchanged, true);
    assert.equal(move.native_vector_path_bytes_preserved, true);
    assert.deepEqual(move.native_glyph_mismatches, []);
    const full = pinned(page.qa, page.qa_sha256);
    assert.equal(full.passed, true);
    if (full.reviewed_bitmap_language_labels) {
      const labels = full.reviewed_bitmap_language_labels;
      assert.ok(labels.labels > 0);
      assert.equal(labels.actual_ink_only_masks, true);
      assert.equal(labels.source_background_restored_exactly, true);
      assert.equal(labels.source_nonlanguage_geometry_within_and_outside_language_regions_protected, true);
      assert.equal(labels.new_label_over_original_nonlanguage_foreground_pixels, 0);
      assert.equal(labels.source_background_rgb_samples.length, labels.labels);
      assert.ok(full.figure_pixel_audits.some(figure => figure.intentionally_translated_language_changed_pixels > 0));
      for (const figure of full.figure_pixel_audits) {
        assert.equal(figure.changed_pixels, 0, 'Translated labels must retain every original nonlanguage figure pixel');
        assert.equal(figure.raw_whole_figure_changed_pixels, figure.intentionally_translated_language_changed_pixels);
      }
      assert.equal(full.native_graphics_motion_audit.changed_nonselected_native_graphical_pixels, 0);
    }
    if (full.reviewed_native_figure_language_labels) {
      const labels = full.reviewed_native_figure_language_labels;
      assert.equal(labels.actual_source_and_translated_language_glyph_ink_only, true);
      assert.equal(labels.nonlanguage_picture_geometry_and_variables_protected, true);
      assert.equal(labels.new_label_over_any_original_nontype_graphic_ink_pixels, 0);
      assert.ok(labels.labels.length > 0);
      for (const label of labels.labels) {
        assert.equal(label.source_point_size, label.target_point_size);
        assert.ok(Math.abs(label.source_baseline - label.target_baseline) < .001);
      }
      for (const figure of full.figure_pixel_audits) {
        assert.equal(figure.changed_pixels, 0);
        assert.equal(figure.raw_whole_figure_changed_pixels, figure.intentionally_translated_language_changed_pixels);
      }
    }
    if (Object.hasOwn(full,'original_pattern_programs_and_ctms_retained')) assert.equal(full.original_pattern_programs_and_ctms_retained, true);
    if (full.native_script_motion_audit) {
      const geometry = full.native_script_motion_audit;
      assert.equal(geometry.passed, true);
      assert.equal(geometry.final_sha256, page.proof_sha256);
      assert.deepEqual(geometry.glyph_signature_or_position_errors, []);
      assert.deepEqual(geometry.relative_geometry_failures, []);
      for (const pair of geometry.script_base_pairs) assert.equal(pair.passed, true);
    }
    if (full.display_equation_number_audit) {
      assert.equal(full.display_equation_number_audit.passed, true);
      assert.deepEqual(full.display_equation_number_audit.changed_marker_glyphs, []);
    }
    for (const key of ['source_math_internal_geometry', 'reviewed_inline_expression_geometry']) {
      if (!full[key]) continue;
      assert.equal(full[key].passed, true);
      assert.equal(full[key].mismatched_groups, 0);
    }
    const ledger = pinned(page.original_native_ink, page.original_native_ink_sha256);
    assert.equal(ledger.output_sha256, page.proof_sha256);
    assert.equal(ledger.verified_native_ink_missing_pixels, 0);
    const raw = ledger.raw_svg_audit;
    assert.deepEqual(raw.missing_requested_source_glyphs, []);
    assert.deepEqual(raw.missing_final_native_glyphs, []);
    assert.deepEqual(raw.source_outline_audit.missing_source_outline_signatures, []);
    if (raw.newly_missing_native_ink_pixels === 0) {
      assert.equal(raw.passed, true);
    } else if (ledger.original_native_cid_profile) {
      const profile = ledger.original_native_cid_profile;
      assert.equal(profile.original_4x_svg_dark_pixel_delta, raw.newly_missing_native_ink_pixels);
      if (profile.kind === '2018-original-native-Cambria-digit-phase-v1') assert.equal(profile.native_reference_nonwhite_RGB_errors, 0);
      else assert.equal(profile.native_original_CID_reference_missing_pixels, 0);
      if (profile.kind !== 'original-native-CID-reference-all') {
        assert.equal(profile.svg_8x_missing_pixels, 0);
        assert.equal(profile.svg_12x_missing_pixels, 0);
      }
      const witness = pinned(profile.path, profile.witness_sha256);
      assert.equal(witness.passed, true);
      assert.equal(witness.proof_sha256, page.proof_sha256);
      assert.equal(witness.proof_unmodified, true);
      if (profile.kind === '2018-original-native-Cambria-digit-phase-v1') {
        require('./izho-2018-native-cid-witness.cjs')(profile,witness,raw,page,item);
      } else if (profile.kind === 'original-native-CID-reference-all') {
        assert.equal(witness.kind, 'all-original-instruction-native-CIDs-v1');
        assert.equal(witness.delivered_pdf_modified, false);
        assert.equal(witness.mathematics_retyped, false);
        assert.equal(witness.source_native_glyphs, raw.protected_native_glyphs);
        assert.equal(witness.original_CID_checks.length, raw.protected_native_glyphs);
        assert.equal(witness.source_CID_promotion.original_font_programs_unchanged, true);
        assert.equal(witness.source_move_qa.passed, true);
        assert.equal(witness.reference_other_text_suppression.passed, true);
        for (const row of witness.original_CID_checks) {
          assert.equal(row.original_source_CID_gid_Tf_exact, true);
          const a = row.source, b = row.actual_destination;
          for (const key of ['c','font','size','trace_gid','render_mode','color','opacity']) assert.deepEqual(a[key],b[key]);
          assert.ok(Math.abs(a.origin[1]-b.origin[1]) < .001);
          assert.ok(Math.abs(b.origin[0]-a.origin[0]-row.requested_dx) < .001);
        }
        assert.deepEqual(Object.keys(witness.native_reference_scales).sort(), ['12','4','8']);
        for (const scale of Object.values(witness.native_reference_scales)) {
          assert.equal(scale.passed, true);
          assert.ok(scale.native_reference_dark_pixels > 0);
          assert.equal(scale.missing_original_encoded_CID_pixels, 0);
          for (const strip of scale.strips) assert.equal(strip.missing_original_encoded_CID_pixels, 0);
        }
      } else if (profile.kind === 'multiple-original-native-CID-references') {
        assert.equal(item.file, 'IZhO_2020_TS_KO.pdf'); assert.equal(page.page, 3);
        assert.equal(page.source_pdf_sha256, '2b553d707456ac992698b78d2ef94bd1a81994833b4815a3a0a60884b88823e9');
        assert.equal(raw.protected_native_glyphs, 422); assert.equal(raw.newly_missing_native_ink_pixels, 2);
        assert.deepEqual(raw.missing_bbox, [95.75,498,102,738.25]);
        assert.equal(witness.kind, 'multiple-original-native-CID-references-v1');
        assert.equal(witness.source_page, 3); assert.equal(witness.original_language_source_sha256, page.source_pdf_sha256);
        assert.equal(witness.rows.length, 2); assert.equal(profile.original_glyphs_independently_checked, 2);
        for (const [index, row] of witness.rows.entries()) {
          assert.equal(row.passed, true);
          const cid = row.native_CID_reference, original = row.source_glyph, actual = row.actual_target_glyph;
          assert.equal(cid.passed, true); assert.equal(cid.proof_sha256, page.proof_sha256);
          assert.equal(cid.source_sha256, raw.source_sha256); assert.equal(cid.publication_PDF_modified, false);
          assert.equal(cid.original_font_programs_unchanged, true); assert.equal(cid.missing_native_CID_reference_pixels, 0);
          assert.equal(cid.native_reference_dark_pixels, 87); assert.equal(cid.source_font_resource, '/TT2');
          assert.equal(cid.source_encoded_cid_hex, '29'); assert.equal(cid.gid, 10);
          assert.equal(cid.font, 'TimesNewRomanPSMT'); assert.equal(cid.size, 12);
          for (const key of ['c','font','size','trace_gid','render_mode','color','opacity']) assert.deepEqual(actual[key], original[key]);
          assert.equal(original.c, ')'); assert.equal(original.font, cid.font); assert.equal(original.size, cid.size); assert.equal(original.trace_gid, cid.gid);
          const [sx,tx,y] = [[121.68,93.12,503.64],[127.68,99.12,743.64]][index];
          assert.ok(Math.abs(original.origin[0]-sx) < .001); assert.ok(Math.abs(actual.origin[0]-tx) < .001);
          assert.ok(Math.abs(original.origin[1]-y) < .001); assert.ok(Math.abs(actual.origin[1]-y) < .001);
          assert.ok(Math.abs(actual.origin[0]-original.origin[0]-row.requested_dx) < .001);
          for (const scale of ['8','12']) {
            assert.equal(row.svg_reference_scales[scale].passed, true);
            assert.equal(row.svg_reference_scales[scale].newly_missing_native_ink_pixels, 0);
            assert.deepEqual(row.svg_reference_scales[scale].missing_requested_source_glyphs, []);
            assert.deepEqual(row.svg_reference_scales[scale].missing_final_native_glyphs, []);
          }
        }
      } else if (item.file === 'IZhO_2014_TS_KO.pdf' && page.page === 2) {
        require('./izho-2014-native-parenthesis.cjs')(profile,witness,raw,page,item);
      } else if (witness.native_CID_reference) {
        const cid = witness.native_CID_reference;
        assert.equal(cid.passed, true);
        assert.equal(cid.proof_sha256, page.proof_sha256);
        assert.equal(cid.source_sha256, raw.source_sha256);
        assert.equal(cid.publication_PDF_modified, false);
        assert.equal(cid.original_font_programs_unchanged, true);
        assert.equal(cid.missing_native_CID_reference_pixels, 0);
        assert.ok(cid.native_reference_dark_pixels > 0);
        assert.equal(cid.source_font_resource, profile.original_font_resource);
        assert.equal(cid.source_encoded_cid_hex, profile.original_encoded_CID);
        assert.equal(cid.gid, profile.original_gid);
        assert.equal(cid.font, profile.original_font);
        assert.equal(cid.size, profile.original_point_size);
        const original = witness.source_glyph, actual = witness.actual_target_glyph;
        for (const key of ['c', 'font', 'size', 'trace_gid', 'render_mode', 'color', 'opacity']) assert.deepEqual(actual[key], original[key]);
        assert.equal(original.trace_gid, cid.gid);
        assert.equal(original.size, cid.size);
        assert.equal(original.font, cid.font);
        assert.ok(Math.abs(actual.origin[1] - original.origin[1]) < .001);
        assert.ok(Math.abs(actual.origin[0] - original.origin[0] - witness.requested_dx) < .001);
        for (const scale of ['8', '12']) {
          assert.equal(witness.svg_reference_scales[scale].passed, true);
          assert.equal(witness.svg_reference_scales[scale].newly_missing_native_ink_pixels, 0);
        }
      } else {
        assert.equal(witness.native_cid_reference_missing_pixels, 0);
        assert.ok(witness.native_reference_dark_pixels > 0);
      }
    } else {
      const witnesses = ledger.original_native_form_witnesses;
      assert.ok(witnesses.length > 0);
      assert.equal(witnesses.reduce((n, w) => n + w.diagnostic_pixels.length, 0), raw.newly_missing_native_ink_pixels);
      for (const witness of witnesses) {
        assert.equal(witness.passed, true);
        assert.equal(witness.source_native_form_raw_program_retained, true);
        assert.equal(witness.source_ancestor_ctm_and_clip_preserved, true);
        assert.equal(witness.font_gid_size_baseline_and_requested_dx_verified, true);
        assert.equal(witness.actual_original_native_replay_missing_dark_pixels, 0);
        assert.ok(witness.replay_glyphs > 0);
        for (const pixel of witness.diagnostic_pixels) assert.deepEqual(pixel.native_rgb, pixel.final_rgb);
      }
    }
  }
  pinned(record.source_ready, record.source_ready_sha256);
  const visual = pinned(record.visual_review, record.visual_review_sha256);
  assert.equal(visual.pages.length, item.pages);
  for (const page of visual.pages) {
    assert.equal(page.reviewed, true);
    assert.equal(page.proof_sha256, record.page_proofs.find(r => r.page === page.page).proof_sha256);
  }
  for (const [file, hash] of Object.entries(record.authoring_snapshot_sha256)) {
    const raw = fs.readFileSync(path.join(root, record.authoring_snapshotroot, file.replaceAll('\\', '/')));
    assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), hash, file);
  }
  for (const row of record.extra_evidence) {
    const evidence = pinned(row.path, row.sha256);
    if (row.kind === 'stationary-display-equation-numbers') {
      assert.equal(evidence.passed, true);
      assert.equal(evidence.proof_sha256, record.page_proofs.find(p => p.page === row.page).proof_sha256);
      assert.deepEqual(evidence.changed_marker_glyphs, []);
      assert.match(evidence.original_english_source_sha256, /^[a-f0-9]{64}$/);
    }
    if (row.kind === 'native-script-relative-geometry') {
      assert.equal(evidence.passed, true);
      assert.equal(evidence.final_sha256, record.page_proofs.find(p => p.page === row.page).proof_sha256);
      assert.deepEqual(evidence.glyph_signature_or_position_errors, []);
      assert.deepEqual(evidence.relative_geometry_failures, []);
      for (const pair of evidence.script_base_pairs) assert.equal(pair.passed, true);
      for (const group of evidence.reviewed_expression_groups) assert.equal(group.passed, true);
    }
  }
};

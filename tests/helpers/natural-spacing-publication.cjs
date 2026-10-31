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
    assert.equal(pinned(page.qa, page.qa_sha256).passed, true);
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
      assert.equal(profile.native_original_CID_reference_missing_pixels, 0);
      assert.equal(profile.svg_8x_missing_pixels, 0);
      assert.equal(profile.svg_12x_missing_pixels, 0);
      const witness = pinned(profile.path, profile.witness_sha256);
      assert.equal(witness.passed, true);
      assert.equal(witness.proof_sha256, page.proof_sha256);
      assert.equal(witness.proof_unmodified, true);
      assert.equal(witness.native_cid_reference_missing_pixels, 0);
      assert.ok(witness.native_reference_dark_pixels > 0);
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
  for (const row of record.extra_evidence) pinned(row.path, row.sha256);
};

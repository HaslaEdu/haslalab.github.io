const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
module.exports = function validate(root, qa, item) {
  const read = file => JSON.parse(fs.readFileSync(path.join(root, file), 'utf8'));
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
    if (qa.independent_display_equation_number_audits) {
      assert.equal(qa.independent_display_equation_number_audits.length, item.pages);
      for (const row of qa.independent_display_equation_number_audits) {
        const raw = fs.readFileSync(path.join(root, row.path));
        assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), row.sha256);
        const checked = JSON.parse(raw);
        assert.equal(checked.passed, true);
        assert.equal(checked.proof_sha256, qa.page_proofs.find(p => p.page === row.page).proof_sha256);
        assert.deepEqual(checked.changed_marker_glyphs, []);
        assert.match(checked.original_english_source_sha256, /^[a-f0-9]{64}$/);
      }
    }
    if (qa.independent_native_script_geometry_audits) {
      assert.equal(qa.independent_native_script_geometry_audits.length, item.pages);
      for (const row of qa.independent_native_script_geometry_audits) {
        const raw = fs.readFileSync(path.join(root, row.path));
        assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), row.sha256);
        const geometry = JSON.parse(raw);
        assert.equal(geometry.passed, true);
        assert.equal(geometry.final_sha256, qa.page_proofs.find(p => p.page === row.page).proof_sha256);
        assert.deepEqual(geometry.glyph_signature_or_position_errors, []);
        assert.deepEqual(geometry.relative_geometry_failures, []);
        for (const pair of geometry.script_base_pairs) assert.equal(pair.passed, true);
        for (const group of geometry.reviewed_expression_groups) assert.equal(group.passed, true);
      }
    }
    const review = read(item.visual_qa);
    assert.ok(review);
};

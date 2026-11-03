const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

module.exports = function validateNaturalSourceNative(root, qa, item) {
  const hash = raw => crypto.createHash('sha256').update(raw).digest('hex');
  const read = (file, expected) => {
    const absolute = path.resolve(root, file);
    assert.ok(absolute.startsWith(root + path.sep));
    const raw = fs.readFileSync(absolute);
    if (expected) assert.equal(hash(raw), expected, file);
    return JSON.parse(raw);
  };
  for (const key of ['file', 'pages', 'bytes', 'sha256', 'language']) assert.equal(qa[key], item[key]);
  assert.equal(qa.schema, 'natural-source-native-joined-v1');
  assert.equal(qa.status, 'READY');
  assert.equal(qa.visual_review_required, false);
  for (const key of ['no_font_shrink', 'no_math_rasterization', 'no_reserved_english_widths',
    'inline_native_math_moved_as_whole_expressions', 'stationary_display_equations_and_figures',
    'original_font_sizes_and_baselines_preserved', 'hidden_original_prose_has_empty_ActualText',
    'no_added_editorial_notes', 'all_pages_visually_reviewed']) assert.equal(qa[key], true, key);
  assert.equal(qa.page_audits.length, item.pages);
  if(item.file==='IChO_2019_T_KO.pdf') require('./icho2019-final-publication.cjs')(qa,item,read);
  for (const program of qa.authoring_programs) {
    assert.equal(hash(fs.readFileSync(path.join(root, program.path))), program.sha256);
  }
  for (const evidence of qa.supplemental_evidence || []) {
    const document = read(evidence.path, evidence.sha256);
    if (evidence.path.endsWith('/root-independent-final-review.json')) {
      assert.equal(document.status, 'PASS');
      assert.equal(document.source_sha256, qa.source_sha256);
      assert.equal(document.pages.length, qa.page_audits.length);
      for (const [i, row] of document.pages.entries()) assert.equal(row.proof_sha256, qa.page_audits[i].proof_sha256);
    }
    if (document.schema === 'ortvay2023-independent-actual-source-title-center-audit-v1') {
      assert.equal(item.file, 'Ortvay_2023_T_KO.pdf');
      assert.equal(document.passed, true);
      assert.equal(document.source_sha256, qa.source_sha256);
      assert.equal(document.proof_sha256, qa.page_audits[0].proof_sha256);
      assert.equal(document.layout_sha256, qa.page_audits[0].qa_sha256);
      assert.equal(document.composer_sha256, qa.page_audits[0].composer_sha256);
      assert.equal(document.program_sha256, qa.authoring_programs.find(p => p.path.endsWith('/audit_ortvay2023_title_centers.py')).sha256);
      assert.ok(document.position_tolerance_pt <= .001);
      assert.equal(document.rows.length, 4);
      assert.equal(document.nonheader_all_glyph_traces_identical, true);
      assert.equal(document.nonheader_changed_pixels, 0);
      for (const row of document.rows) {
        assert.ok(Math.abs(row.actual_target_center_pt - row.source_center_pt) <= .001);
        assert.ok(row.center_error_pt <= .001 && row.max_glyph_translation_error_pt <= .001);
        assert.equal(row.original_source_point_size_pt, row.actual_target_point_size_pt);
        assert.equal(row.unchanged_glyphs_font_GIDs_size_baseline, true);
      }
    }
    if (document.schema === 'actual-subset-font-korean-inter-row-ink-2x-v1') {
      assert.equal(document.passed, true);
      assert.deepEqual(document.stale_pages, []);
      assert.equal(document.pages.length, qa.pages);
      assert.deepEqual(document.pages.map(row => row.page), qa.page_audits.map(row => row.page));
      for (const row of document.pages) {
        assert.equal(row.passed, true);
        assert.deepEqual(row.failures, []);
        assert.equal(row.proof_sha256, qa.page_audits[row.page - 1].proof_sha256);
        assert.ok(qa.authoring_programs.some(program => program.sha256 === row.measurement_code_sha256));
        assert.equal(row.pairs.length, row.tested_close_row_pairs);
        for (const pair of row.pairs) assert.equal(pair.contact_pixels_2x, 0);
      }
    }
  }
  if (qa.link_annotation_subset_regression) {
    const pin = qa.link_annotation_subset_regression;
    const regression = read(pin.path, pin.sha256);
    assert.equal(regression.status, 'PASS');
    assert.equal(regression.changed_pixels, 0);
    assert.equal(regression.all_visible_glyph_geometry_identical, true);
    assert.equal(regression.helper_sha256, pin.helper_sha256);
    assert.equal(regression.program_sha256, pin.test_program_sha256);
    assert.equal(hash(fs.readFileSync(path.join(root, pin.test_program_path))), pin.test_program_sha256);
    if (item.file === 'Ortvay_2023_T_KO.pdf') {
      assert.equal(regression.source_sha256, qa.source_sha256);
      assert.equal(regression.all_nonrect_annotation_settings_identical_after_save, true);
      assert.equal(qa.authoring_programs.find(p => p.path.endsWith('/ortvay2023_link_annotations.py')).sha256, pin.helper_sha256);
      assert.deepEqual(regression.pages.map(row => row.page), [1, 6]);
      assert.equal(regression.links.length, 3);
      if (qa.source_style_correction) assert.ok(regression.negative_regressions.length >= 6);
      else assert.equal(regression.negative_regressions.length, 6);
      for (const row of regression.pages) {
        const page = qa.page_audits[row.page - 1];
        assert.equal(row.proof_sha256, page.proof_sha256);
        assert.equal(row.layout_sha256, page.qa_sha256);
        assert.equal(row.changed_pixels, 0);
        assert.equal(row.all_visible_glyph_geometry_identical, true);
        assert.equal(row.all_nonrect_annotation_settings_identical_after_save, true);
        if (qa.source_style_correction) assert.ok(row.negative_regressions.length >= 3);
        else assert.equal(row.negative_regressions.length, 3);
        const helperRows=qa.source_style_correction?row.links.map(link=>{
          const {independent_native_url_glyph_audit,...helper}=link;
          assert.ok(independent_native_url_glyph_audit);
          return helper;
        }):row.links;
        assert.deepEqual(page.link_annotation_geometry_audits, helperRows);
      }
      assert.deepEqual(regression.links, regression.pages.flatMap(row => row.links));
    } else {
      assert.equal(item.file, 'Ortvay_2024_T_KO.pdf');
      assert.equal(regression.proof_sha256, qa.page_audits[1].proof_sha256);
      assert.equal(qa.authoring_programs.find(p => p.path.endsWith('/ortvay2024_link_annotations.py')).sha256, pin.helper_sha256);
      assert.equal(regression.links.length, 6);
      if (qa.layout_correction || qa.source_style_correction) assert.ok(regression.negative_regressions.length >= 3);
      else assert.equal(regression.negative_regressions.length, 3);
      const helperRows = (qa.layout_correction || qa.source_style_correction) ? regression.links.map(row => {
        const { independent_native_url_glyph_audit, ...helper } = row;
        assert.ok(independent_native_url_glyph_audit);
        return helper;
      }) : regression.links;
      assert.deepEqual(qa.page_audits[1].link_annotation_geometry_audits, helperRows);
    }
  }
  if (qa.source_path_resolver_sha256) {
    const resolver = qa.authoring_programs.find(p => /\/source_path_resolver\.py$/.test(p.path));
    assert.ok(resolver, 'Source path mapping program is frozen with the publication');
    assert.equal(resolver.sha256, qa.source_path_resolver_sha256);
  }
  const canonicalMigratedSource = value => {
    const source = value.replace(/\\/g, '/').toLowerCase();
    const oldParent = 'c:/users/andre/onedrive/문서/chatgpt/hasla 노술/';
    const newParent = 'c:/users/andre/codexwork/haslalab/';
    for (const repo of ['haslalab', 'haslalab-translations', 'haslalab-design-release', 'haslalab-chem-kmo-exams']) {
      const prefix = oldParent + repo + '/';
      if (source.startsWith(prefix)) return newParent + repo + '/' + source.slice(prefix.length);
    }
    // The reviewed style worktree retains an exact copy of this EN source.
    // Keep historical plan provenance immutable and recognize only this pair.
    if (item.file === 'IChO_2024_T_KO.pdf' && qa.source_style_correction &&
        qa.source_sha256 === '959174ab5ddc8be71c251c8fe95a12c810ba730edbcbbef3b771197e32929a4a') {
      const original = 'd:/codexbuilds/hasla-poi-natural-20261102/historical/icho/english-missing/icho_2024_t_en.pdf';
      const retained = 'd:/codexbuilds/hasla-poi-natural-20261102/style-corrections/icho2024-20261103/frozen/source/icho_2024_t_en.pdf';
      if (source === original || source === retained) return original;
    }
    return source;
  };
  const assertSourcePath = source => {
    if (source === qa.source) return;
    assert.ok(qa.source_path_resolver_sha256 && qa.resolved_source_read_path,
      'Different provenance paths require the frozen migration resolver and verified read path');
    assert.equal(canonicalMigratedSource(source), canonicalMigratedSource(qa.source));
    assert.equal(canonicalMigratedSource(source), canonicalMigratedSource(qa.resolved_source_read_path));
  };
  const folder = path.dirname(path.join(root, item.qa));
  const reviews = fs.readdirSync(folder).filter(f => /^visual-review.*\.json$/.test(f)).flatMap(f => {
    const review = JSON.parse(fs.readFileSync(path.join(folder, f), 'utf8'));
    assert.equal(review.source_sha256, qa.source_sha256);
    return review.pages.map(row => {
      if (!Object.hasOwn(row, 'compositor_sha256')) return row;
      if (Object.hasOwn(row, 'composer_sha256')) assert.equal(row.composer_sha256, row.compositor_sha256);
      return { ...row, composer_sha256: row.compositor_sha256 };
    });
  });
  for (const [index, page] of qa.page_audits.entries()) {
    assert.equal(page.page, index + 1);
    assert.equal(page.final_vs_reviewed_proof_changed_pixels, 0);
    assert.equal(page.missing_hangul_glyphs, 0);
    assert.ok(page.visible_hangul_characters > 0);
    for (const key of ['final_vs_reviewed_proof_all_glyph_geometry_identical', 'page_box_preserved',
      'original_font_programs_preserved', 'original_image_encoded_streams_and_filters_preserved',
      'original_image_geometry_preserved']) assert.equal(page[key], true, key);
    const body = read(page.qa_path, page.qa_sha256);
    for (const link of page.link_annotation_adjustments || []) {
      assert.equal(link.page, page.page);
      assert.equal(link.passed, true);
      assert.equal(link.only_horizontal_rect_translation, true);
      assert.equal(link.other_annotation_settings_preserved, true);
      const shift = body.native_shifts[link.native_shift_index];
      assert.equal(shift.glyphs.map(g => g.c).join(''), link.uri);
      assert.equal(shift.glyphs.length, link.native_url_glyphs);
      assert.equal(shift.dx, link.dx);
      for (let n = 0; n < 4; n++) {
        const expected = link.source_rect_mupdf[n] + (n % 2 === 0 ? link.dx : 0);
        assert.ok(Math.abs(link.actual_target_rect_mupdf[n] - expected) < 0.001);
      }
    }
    for (const link of page.link_annotation_geometry_audits || []) {
      assert.equal(link.schema, 'reviewed-source-url-subset-v1');
      assert.equal(link.page, page.page);
      for (const key of ['passed', 'native_url_glyphs_verified_in_proof', 'only_horizontal_rect_translation', 'other_annotation_settings_preserved']) assert.equal(link[key], true);
      assert.ok(link.max_url_glyph_geometry_error_pt <= 0.001 && link.position_tolerance_pt <= 0.001);
      assert.equal(link.glyph_references.length, link.source_url_glyphs);
      assert.equal(link.glyph_references.map(r => r.source_glyph.c).join(''), link.display_fragment);
      for (const ref of link.glyph_references) {
        assert.equal(ref.dx, link.dx);
        const sameSource = glyph => glyph.c === ref.source_glyph.c && glyph.origin.every((n, i) => Math.abs(n - ref.source_glyph.origin[i]) < 0.00001);
        assert.equal(body.selected_glyphs.some(sameSource), false);
        if (ref.native_shift_index === null) {
          assert.equal(ref.dx, 0);
          assert.equal(ref.shift_glyph_index, null);
          assert.equal(body.native_shifts.some(s => s.glyphs.some(sameSource)), false);
        } else {
          const shift = body.native_shifts[ref.native_shift_index];
          assert.equal(shift.dx, ref.dx);
          assert.ok(sameSource(shift.glyphs[ref.shift_glyph_index]));
        }
      }
      for (let n = 0; n < 4; n++) {
        const delta = n % 2 === 0 ? link.dx : 0;
        assert.ok(Math.abs(link.target_rect_pdf[n] - link.source_rect_pdf[n] - delta) < 0.001);
        assert.ok(Math.abs(link.expected_target_rect_mupdf[n] - link.source_rect_mupdf[n] - delta) < 0.001);
        assert.ok(Math.abs(link.actual_target_rect_mupdf[n] - link.expected_target_rect_mupdf[n]) < 0.001);
      }
    }
    const plan = read(page.plan_path, page.plan_sha256);
    const effective = read(page.effective_plan_path, page.effective_plan_sha256);
    assert.equal(body.schema, 'natural-source-native-v1');
    assert.equal(body.source, qa.source);
    assert.equal(body.source_sha256, qa.source_sha256);
    assert.equal(body.page, page.page);
    for (const p of [plan, effective]) {
      assert.equal(p.page, page.page);
      assertSourcePath(p.source);
      assert.equal(p.source_sha256, qa.source_sha256);
    }
    assert.equal(body.output_sha256, page.proof_sha256);
    assert.equal(body.plan_sha256, page.plan_sha256);
    assert.equal(body.composer_sha256, page.composer_sha256);
    assert.equal(hash(fs.readFileSync(path.join(root, page.composer_path))), page.composer_sha256);
    assert.equal(body.effective_plan_sha256, page.effective_plan_sha256);
    if (page.overrides_path) {
      read(page.overrides_path, page.overrides_sha256);
      assert.equal(body.overrides_sha256, page.overrides_sha256);
    }
    for (const scope of page.source_scopes || []) read(scope.path, scope.sha256);
    if (page.raster_label_manifest) {
      read(page.raster_label_manifest.path, page.raster_label_manifest.sha256);
      assert.equal(body.reviewed_raster_label_manifest.sha256, page.raster_label_manifest.sha256);
    }
    if (qa.strict_korean_glyph_geometry_audit) {
      const audit = body.new_korean_glyph_and_geometry_audit;
      assert.equal(audit.passed, true);
      if (Object.hasOwn(audit, 'missing_or_notdef_glyphs')) {
        assert.deepEqual(audit.missing_or_notdef_glyphs, []);
      }
      if (qa.layout_correction) {
        assert.deepEqual(audit.original_full_font_gid_errors, []);
        assert.equal(audit.original_full_font_gids_verified, audit.actual_glyphs);
        assert.deepEqual(body.title_correction_independent_audit.korean_actual_glyph_geometry, audit);
      } else assert.ok(Object.hasOwn(audit, 'missing_or_notdef_glyphs'));
      assert.deepEqual(audit.geometry_errors, []);
      assert.equal(audit.planned_glyphs, audit.actual_glyphs);
      assert.ok(audit.max_position_error_pt <= 0.001 && audit.position_tolerance_pt <= 0.001);
      for (const key of ['paragraph_text_conservation_verified', 'inline_native_math_assignment_complete',
        'native_atom_source_prose_seams_clear', 'new_korean_font_subsets_retain_original_gids']) assert.equal(body[key], true, key);
      const baseline = page.original_prose_baseline_audit;
      assert.equal(baseline.passed, true);
      assert.equal(baseline.placements, body.placements.length);
      assert.ok(baseline.max_selected_source_prose_baseline_delta_pt <= 0.001);
      assert.ok(baseline.max_actual_source_char_baseline_delta_pt <= 0.001 && baseline.tolerance_pt <= 0.001);
      for (const [field, filename] of [['native_motion_engine_sha256', 'latex_native_motion.py'],
        ['native_ink_bounds_engine_sha256', 'native_ink_bounds.py'], ['native_proof_helper_sha256', 'native_proof.py']]) {
        assert.equal(body[field], qa.authoring_programs.find(p => p.path.endsWith('/' + filename)).sha256);
      }
    }
    if (body.native_text_ops_sha256) {
      const textOps = qa.authoring_programs.find(p => p.path.endsWith('/pdf_latex_text_ops.py'));
      assert.ok(textOps);
      assert.equal(textOps.sha256, body.native_text_ops_sha256);
    }
    if (body.native_type3_profile_sha256) {
      const profile = qa.authoring_programs.find(p => p.path.endsWith('/native_type3_profile.py'));
      assert.ok(profile);
      assert.equal(profile.sha256, body.native_type3_profile_sha256);
    }
    if (body.original_type3_program_preservation) {
      const type3 = body.original_type3_program_preservation;
      assert.equal(type3.passed, true);
      assert.deepEqual(type3.target, type3.source);
    }
    for (const contact of body.intentional_prose_decoration_contacts || []) {
      require('./prose-decoration-publication.cjs')(body, contact, qa);
    }
    for (const key of ['no_reserved_english_widths', 'no_font_shrink', 'source_font_programs_preserved',
      'original_image_encoded_bytes_and_filters_preserved', 'source_image_placements_preserved',
      'source_glyph_moves_restricted_to_authored_prose_line_bounds', 'stationary_display_equations_and_figures',
      'original_font_sizes_and_baselines_identical', 'native_horizontal_moves_only']) assert.equal(body[key], true, key);
    assert.deepEqual(body.stationary_display_glyphs_missing_or_moved, []);
    assert.deepEqual(body.stationary_figure_glyphs_missing_or_moved, []);
    assert.deepEqual(body.final_native_geometry.missing, []);
    assert.equal(body.final_native_geometry.extra, 0);
    assert.ok(body.final_native_geometry.max_delta_pt <= 0.001);
    assert.equal(body.motion_qa.passed, true);
    assert.equal(body.motion_qa.text_shift_mode, 'ctm');
    assert.equal(body.motion_qa.erased_glyphs, 0);
    assert.deepEqual(body.actual_native_vector_coordinate_audit.coordinate_errors, []);
    if (body.actual_native_vector_coordinate_audit.audit_code_sha256) {
      assert.ok(qa.authoring_programs.some(p => /\/verify_native_vectors(?:_[a-z]+\d+(?:_style)?)?\.py$/.test(p.path)
        && p.sha256 === body.actual_native_vector_coordinate_audit.audit_code_sha256));
    }
    assert.ok(body.actual_native_vector_coordinate_audit.max_coordinate_tolerance_pt <= 0.000001);
    assert.equal(body.new_korean_intrusion_on_native_ink_pixels, 0);
    assert.equal(body.new_body_korean_ink_inside_protected_figure_pixels, 0);
    let boundaries = 0;
    for (const line of body.line_reports) {
      if (line.fixed_design_cells) continue;
      for (const gap of line.gaps) {
        assert.ok(gap.new_gap >= -0.001 && gap.new_gap <= gap.ordinary_space + 0.001,
          `Excessive prose gap on page ${page.page}: ${gap.left} | ${gap.right}`);
        boundaries++;
      }
    }
    assert.equal(body.ordinary_gap_boundaries_verified, boundaries);
    const review = reviews.find(r => r.page === page.page && r.reviewed === true && r.proof_sha256 === page.proof_sha256);
    assert.ok(review, `Unreviewed natural-spacing page ${page.page}`);
    assert.equal(review.layout_sha256, page.qa_sha256);
    assert.equal(review.effective_plan_sha256, page.effective_plan_sha256);
    assert.equal(review.composer_sha256, page.composer_sha256);
  }
  if (qa.layout_correction) require('./natural-correction-publication.cjs')(root, qa, item, read);
  if (qa.source_style_correction) {
    if(qa.source_style_correction.schema==='ortvay2026-source-style-page-repair-publication-v1') {
      assert.equal(item.file,'Ortvay_2026_T_KO.pdf');
      require('./ortvay2026-repaired-publication.cjs')(root, qa, item, read);
    }
    else if(qa.source_style_correction.schema==='ortvay-source-style-publication-v1') require('./ortvay-source-style-publication.cjs')(root, qa, item, read);
    else {
      assert.equal(qa.source_style_correction.schema,'icho2024-source-style-publication-v1');
      require('./icho-source-style-publication.cjs')(root, qa, item, read);
    }
  }
};

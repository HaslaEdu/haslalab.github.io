const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname,'..');
const read = file => JSON.parse(fs.readFileSync(path.join(root,file),'utf8'));
const validate = require('./helpers/izho-2014-native-parenthesis.cjs');
const item = read('tools/original_style_publication.json').find(row => row.file === 'IZhO_2014_TS_KO.pdf');
const publication = read(item.qa);
const page = publication.page_proofs.find(row => row.page === 2);
const ledger = read(page.original_native_ink);
const profile = ledger.original_native_cid_profile;
const witness = read(profile.path);

test('IZhO2014: original full-source CID and one-page outline control have independently pinned provenance', () => {
  validate(profile,witness,ledger.raw_svg_audit,page,item);
  const files = publication.authoring_snapshot_sha256;
  assert.ok(Object.values(files).includes(witness.original_language_source_sha256));
  assert.equal(files['negative-controls/actual-source-specific-native-parenthesis-covered/2014/TS/page02.old-source.pdf'], ledger.raw_svg_audit.source_sha256);
  const negatives = read(path.join(publication.authoring_snapshotroot,'negative-controls/negative-controls.json'));
  assert.equal(negatives.passed, true);
  const covered = negatives.rows.find(row => row.id === 'actual-source-specific-native-parenthesis-covered');
  assert.equal(covered.proof_sha256, page.proof_sha256);
  assert.equal(covered.negative_rejected, true);
  assert.equal(covered.delivered_proof_unmodified, true);
  assert.ok(covered.missing_actual_native_pixels > 0 || covered.missing_original_outline_pixels > 0);
});

test('IZhO2014: rejects changed source, actual proof, native point, Tf/Tm, incomplete replay and missing ink', () => {
  for (const change of [
    w => { w.original_language_source_sha256 = '0'.repeat(64); },
    w => { w.proof_sha256 = '0'.repeat(64); },
    w => { w.actual_target_glyph.size = 11.9; },
    w => { w.native_CID_reference.source_Tm_linear[3] = 12; },
    w => { delete w.cropped_native_CID_reference_scales['8']; },
    w => { w.cropped_native_CID_reference_scales['12'].missing_native_CID_reference_pixels = 1; },
    w => { w.svg_reference_scales['8'].newly_missing_native_ink_pixels = 1; }
  ]) {
    const altered = structuredClone(witness); change(altered);
    assert.throws(() => validate(profile,altered,ledger.raw_svg_audit,page,item));
  }
  const altered = structuredClone(ledger.raw_svg_audit); altered.source_sha256 = witness.original_language_source_sha256;
  assert.throws(() => validate(profile,witness,altered,page,item));
});

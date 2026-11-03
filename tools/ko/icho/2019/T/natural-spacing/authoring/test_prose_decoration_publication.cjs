const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const base = path.resolve(__dirname, '..');
const helperPath = 'C:/Users/andre/CodexWork/HaslaLab/haslalab-poi-style-publication/tests/helpers/prose-decoration-publication.cjs';
const validate = require(helperPath);
const read = p => JSON.parse(fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, ''));
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const qa = {authoring_programs: [
  {path:'authoring/verify_prose_underline_and_style.py', sha256:'79729dd00f2f9c5f14b8ef9657ee4ebd186c0cb2043c64b7806bd2a0b4aeeda4'},
  {path:'authoring/actual_prose_ink_icho2019.py', sha256:'13c5fb97d4faa712dba8361565fd30cae3b886e7ec37b83ab55a7425e2e0fa3c'}
]};
const folder = path.join(base, 'proofs/icho/2019-final');
const accepted = [];
const regression = read(path.join(__dirname, 'publication-transition/prose-decoration-validator-regression.json'));
let contacts = 0;
for (const pin of regression.current_pages) {
  const p = path.join(folder, `page${String(pin.page).padStart(2,'0')}.layout.json`);
  assert.equal(hash(p), pin.layout_sha256);
  const q = read(p);
  for (const c of q.intentional_prose_decoration_contacts || []) {validate(q,c,qa); contacts++;}
  accepted.push(pin.page);
}
const q0 = read(path.join(folder,'page08.layout.json'));
const mutations = [
  ['affine flag downgrade', (q,c) => c.x_translation_only=true],
  ['affine flag downgrade with protected ink contact', (q,c) => {c.x_translation_only=true; q.actual_prose_underline_protected_native_ink_contact_pixels=1; q.actual_prose_underline_coverage_and_style_audit.protected_native_ink_contact_pixels=1;}],
  ['unreviewed source', (q,c) => q.source_sha256='0'.repeat(64)],
  ['stale proof binding', (q,c) => q.output_sha256='0'.repeat(64)],
  ['unbound source path', (q,c) => c.source_path_index=-1],
  ['changed source paint', (q,c) => q.reviewed_moving_prose_decoration_paths[0].vector_path.paint_operator='S'],
  ['moved underline baseline', (q,c) => q.prose_vector_decorations[0].target_rect[1]+=.01],
  ['actual underline thickness changed', (q,c) => q.actual_prose_underline_coverage_and_style_audit.underline_rows[0].actual_underline_bbox[3]+=.01],
  ['partial-word underline despite reported PASS', (q,c) => q.actual_prose_underline_coverage_and_style_audit.underline_rows[0].actual_emphasized_glyph_curve_union_bbox[0]=200],
  ['protected native ink contact', (q,c) => q.actual_prose_underline_protected_native_ink_contact_pixels=1],
  ['full font identity not verified', (q,c) => q.actual_prose_underline_coverage_and_style_audit.underline_rows[0].all_Korean_used_glyph_GIDs_outlines_and_hmtx_match_pinned_full_font=false],
  ['invalid nonpositive scale', (q,c) => c.prose_decoration_x_scale=0],
  ['missing actual curve measurements', (q,c) => delete q.actual_prose_underline_coverage_and_style_audit],
  ['widened coverage tolerance', (q,c) => q.actual_prose_underline_coverage_and_style_audit.underline_coverage_tolerance_pt=.1],
];
for (const [name, mutate] of mutations) {
  const q = structuredClone(q0), c = q.intentional_prose_decoration_contacts[0];
  mutate(q,c);
  assert.throws(() => validate(q,c,qa), undefined, name);
}
const report = {status:'PASS',helper_sha256:hash(helperPath), python_regression_sha256:hash(path.join(__dirname,'publication-transition/prose-decoration-validator-regression.json')),
  accepted_pages:accepted, checked_contacts:contacts, rejected_mutations:mutations.map(([name])=>name), scope:'Publication JSON contract regression; production actual-PDF audits remain required.'};
const out=path.join(__dirname,'publication-transition/prose-decoration-cjs-regression.json');
fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:'PASS',contacts,pages:accepted.length,rejected:mutations.length,report:out,sha256:hash(out)}));

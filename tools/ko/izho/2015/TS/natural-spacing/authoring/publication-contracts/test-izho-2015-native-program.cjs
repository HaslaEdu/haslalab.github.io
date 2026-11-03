const test=require('node:test');const assert=require('node:assert/strict');
const fixture=require('./exact-source-fixture.json');const validate=require('./izho-2015-native-equation16.cjs');
const run=x=>validate(x.profile,x.witness,x.raw,x.page,x.item);
test('all40 exact original CIDs/Tf/Tm/CTM/paint and both-renderer witnesses pass',()=>run(fixture));
const mutations=[
 ['complete original source changed',x=>x.witness.original_source_sha256='0'.repeat(64)],
 ['full source incorrectly substituted for one-page control',x=>x.raw.source_sha256=x.witness.original_source_sha256],
 ['proof pin changed',x=>x.page.proof_sha256='0'.repeat(64)],
 ['native reference source pin changed',x=>x.witness.source_reference_sha256='0'.repeat(64)],
 ['actual native ink loss',x=>x.witness.native_original_program_reference_measurements[0].missing_original_native_program_pixels=1],
 ['native nonwhite RGB coverage mismatch',x=>x.witness.native_original_program_reference_measurements[0].actual_reference_nonwhite_RGB_errors=1],
 ['one renderer-scale measurement missing',x=>x.witness.native_original_program_reference_measurements.pop()],
 ['reference pixel count forged',x=>x.witness.native_original_program_reference_measurements[0].reference_original_program_deep_dark_pixels--],
 ['SVG loss',x=>x.witness.svg_reference_scales['12'].newly_missing_native_ink_pixels=1],
 ['40CID coverage incomplete',x=>x.witness.exact_original_CID_programs.pop()],
 ['original encoded CID changed',x=>x.witness.exact_original_CID_programs[0].original_source_encoded_program.source_encoded_CID_hex='0000'],
 ['source mathematical point changed',x=>x.witness.exact_original_CID_programs[0].source_glyph.size=11],
 ['actual mathematical point changed',x=>x.witness.exact_original_CID_programs[0].actual_target_glyph.size=11],
 ['original Tf changed',x=>x.witness.exact_original_CID_programs[0].original_source_encoded_program.source_Tf=11],
 ['actual Tm changed',x=>x.witness.exact_original_CID_programs[0].actual_final_encoded_program.source_text_matrix[0]=.9],
 ['actual paint changed',x=>x.witness.exact_original_CID_programs[0].actual_target_glyph.color=[1,1,1]],
 ['actual coordinate changed',x=>x.witness.exact_original_CID_programs[0].actual_target_glyph.origin[0]+=1],
 ['actual covered-ink damage accepted',x=>x.witness.actual_bad_PDF_controls.rows[4].negative_rejected=false],
 ['actual covered-ink evidence removed',x=>x.witness.actual_bad_PDF_controls.rows[4].missing_actual_native_ink_pixels=0],
 ['native font program changed',x=>x.witness.source_native_reference_guard.font_programs_unchanged=false],
 ['new raw losses hidden by phase witness',x=>x.raw.newly_missing_native_ink_pixels=2],
 ['wrong raw loss location',x=>x.raw.missing_bbox[0]+=1],
];
for(const [name,change]of mutations)test(`reject ${name}`,()=>{const x=structuredClone(fixture);change(x);assert.throws(()=>run(x));});

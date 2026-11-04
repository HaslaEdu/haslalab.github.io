const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
let fixture;
if(process.env.HASLA2017_PRIVATE_PROOF_INPUT)fixture=JSON.parse(fs.readFileSync(process.env.HASLA2017_PRIVATE_PROOF_INPUT,'utf8'));
else{
 const read=f=>JSON.parse(fs.readFileSync(path.join(root,f),'utf8'));
 const item=read('tools/original_style_publication.json').find(r=>r.file==='IZhO_2017_TS_KO.pdf');assert.ok(item,'The PUBLIC ledger for the actual published edition is required');const record=read(item.qa),page=record.page_proofs.find(r=>r.page===11),ledger=read(page.original_native_ink),profile=ledger.original_native_cid_profile;fixture={profile,witness:read(profile.path),raw:ledger.raw_svg_audit,page,item};
}
const validate=require(process.env.HASLA2017_PRIVATE_PROOF_INPUT?'./izho-2017-native-lambda-program.cjs':'./helpers/izho-2017-native-lambda-program.cjs');
const run=x=>validate(x.profile,x.witness,x.raw,x.page,x.item);
test('All7 original native CIDs and complete root/Form/clips/points have six exact-RGB witnesses',()=>run(fixture));
const cases=[
 ['full source changed',x=>x.witness.original_source_sha256='0'.repeat(64)],
 ['one-page control confused with full source',x=>x.raw.source_sha256=x.witness.original_source_sha256],
 ['actual proof changed',x=>x.page.proof_sha256='0'.repeat(64)],
 ['witness pin rebased',x=>x.profile.witness_sha256='0'.repeat(64)],
 ['literal source Form program changed',x=>x.witness.source_native_reference_guard.literal_original_Form_raw_sha256='0'.repeat(64)],
 ['source native reference changed',x=>x.witness.source_reference_sha256='0'.repeat(64)],
 ['actual native ink missing',x=>x.witness.native_original_program_reference_measurements[0].missing_original_native_program_pixels=1],
 ['actual RGB mismatch',x=>x.witness.native_original_program_reference_measurements[5].actual_reference_nonwhite_RGB_errors=1],
 ['one native renderer/scale omitted',x=>x.witness.native_original_program_reference_measurements.pop()],
 ['nonwhite samples forged',x=>x.witness.native_original_program_reference_measurements[0].reference_original_program_nonwhite_pixels--],
 ['unhinted SVG loss',x=>x.witness.svg_reference_scales['12'].newly_missing_native_ink_pixels=1],
 ['physical math glyph omitted',x=>x.witness.complete_original_expression_glyphs.pop()],
 ['mathematical GID changed',x=>x.witness.complete_original_expression_glyphs[0].trace_gid++],
 ['fractional point changed',x=>x.witness.complete_original_expression_glyphs[0].size=12],
 ['source glyph coordinate changed',x=>x.witness.complete_original_expression_glyphs[0].origin[0]+=.01],
 ['source glyph painted white',x=>x.witness.complete_original_expression_glyphs[0].color=[1,1,1]],
 ['original Form CTM changed',x=>x.witness.original_form.entry_ctm[0]+=.001],
 ['original native root stroke geometry changed',x=>x.witness.original_form.own_vector_paths[0].rect[0]+=.01],
 ['original clipping context changed',x=>x.witness.original_form.invocation_ctm[0]+=.001],
 ['whole-program dx changed',x=>x.witness.independently_inferred_whole_original_expression_dx+=.001],
 ['new fullpage losses hidden',x=>x.raw.newly_missing_native_ink_pixels=2],
 ['wrong raw diagnostic pixel',x=>x.raw.missing_bbox[0]+=1],
 ['mathematical ink excluded',x=>x.profile.mathematical_ink_excluded=true],
 ['native source fonts substituted',x=>x.witness.source_font_programs_substituted=true],
];
for(const [name,change]of cases)test(`reject ${name}`,()=>{const x=structuredClone(fixture);change(x);assert.throws(()=>run(x));});

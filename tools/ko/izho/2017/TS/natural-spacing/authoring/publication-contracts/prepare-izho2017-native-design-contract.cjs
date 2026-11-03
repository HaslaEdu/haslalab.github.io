// Read actual accepted source files and proofs; this is not a detached fixture.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const B=path.resolve(__dirname,'..'),F=path.join(B,'natural/2017/TS'),O=__dirname;
const read=p=>JSON.parse(fs.readFileSync(p,'utf8')),hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex'),digest=x=>crypto.createHash('sha256').update(JSON.stringify(x)).digest('hex');
const SOURCE='fb90239d8da3dea3dcfe104551243f444802632a74a47a139374013aa16080f1',FULL='3a27a3561c779bb9fbc149387da370dfa9db10173dd9b24b055842ce62fa3b62',BYTES=52262121;
const ready=read(path.join(B,'natural/editions/IZhO_2017_TS_KO.ready.json'));
assert.equal(ready.sha256,FULL);assert.equal(hash(ready.output),FULL);assert.equal(fs.statSync(ready.output).size,BYTES);assert.equal(ready.original_source_sha256,SOURCE);
const artifacts=[];function artifact(id,role,p){p=path.resolve(p);assert.ok(!artifacts.some(a=>a.id===id),id);const a={id,role,sha256:hash(p),bytes:fs.statSync(p).size,source_path:p};artifacts.push(a);return a;}
artifact('full-edition','actual-reviewed-full-edition',ready.output);
const proofs={},raw_controls={},native_controls={},source_bases={},page_plans={};
for(let n=1;n<=14;n++){
 const s=String(n).padStart(2,'0'),p=read(path.join(F,'plans',`page${s}.json`));
 proofs[n]=artifact(`proof-${s}`,'actual-reviewed-page-proof',path.join(F,`page${s}.pdf`)).sha256;
 raw_controls[n]=artifact(`raw-control-${s}`,'actual-raw-one-page-outline-control',path.join(F,`page${s}.old-source.pdf`)).sha256;
 native_controls[n]=artifact(`native-control-${s}`,'actual-one-page-native-control',path.join(F,`page${s}.native-control.pdf`)).sha256;
 source_bases[n]=p.source_base_sha256;page_plans[n]=artifact(`plan-${s}`,'actual-accepted-original-source-prose-plan',path.join(F,'plans',`page${s}.json`)).sha256;
 artifact(`native-style-graphics-audit-${s}`,'actual-positive-original-input-audit',path.join(F,`page${s}.audit.json`));
}
for(const [i,a]of ready.input_archives.entries()){const x=artifact(`immutable-input-${i}`,'actual-immutable-original-or-native-source-base',a.path);assert.equal(x.sha256,a.sha256);}
const programmes={},orders={},geometry={};
for(const n of[6,7]){
 const s=String(n).padStart(2,'0'),plan=read(path.join(F,'plans',`page${s}.json`));
 const r=plan.reviewed_source2017_complete_original_expression_program_isolation;programmes[n]=r;
 const dir=path.dirname(r.programs[0].reference);
 artifact(`program-report-${s}`,'actual-original-CID-program-and-three-zeroRGB-roundtrips',path.join(dir,'source-program-and-zeroRGB-contract.json'));
 artifact(`pre-isolation-plan-${s}`,'actual-plan-before-original-program-promotion',path.join(dir,'pre-isolation-plan.json'));
 artifact(`isolated-one-page-${s}`,'actual-pre-motion-native-expression-wrapper-page',path.join(dir,`page${s}.pdf`));
 for(const g of r.programs){artifact(`original-reference-${s}-${g.index}`,'actual-official-CID-clips-Tf-Tm-and-path-reference-PDF',g.reference);const a=artifact(`original-program-${s}-${g.index}`,'actual-byte-identical-original-native-Form-program',path.join(O,`page${s}-expression${g.index}-actual-original-program.bin`));assert.equal(a.sha256,g.Form_raw_sha256);}
 orders[n]=read(path.join(F,`page${s}.native-prose-order.json`));artifact(`actual-prose-order-${s}`,'actual-independent-original-conjunction-order-and-natural-gaps',path.join(F,`page${s}.native-prose-order.json`));
 geometry[n]=read(path.join(F,`page${s}.independent-original-math-geometry.json`));artifact(`actual-native-geometry-${s}`,'actual-independent-official-source-math-program-glyph-and-rule-geometry',path.join(F,`page${s}.independent-original-math-geometry.json`));
}
const extraction=read(path.join(O,'actual-source-program-extraction.json'));artifact('actual-program-extraction','actual-official-CID-font-Tf-full-Tm-clips-final-program-invocation-extraction',path.join(O,'actual-source-program-extraction.json'));
const R=path.join(B,'page07-conjunction-repair');
const scope=read(path.join(R,'actual-source-row-scope-zero-outside.json')),other13=read(path.join(R,'other13-approved-proof-pins.json'));
artifact('scope-zero-outside-three-rows','actual-external-Poppler144-zero-pixels-outside-source-rows',path.join(R,'actual-source-row-scope-zero-outside.json'));artifact('other13-proof-pins','actual-prior-accepted-other13-proof-hashes',path.join(R,'other13-approved-proof-pins.json'));
const rootNeg=read(path.join(B,'natural/2017-native-design-negatives/negative-controls.json')),old7=read(path.join(R,'actual-prior-949b9-conjunction-order-negative.json')),bar=read(path.join(R,'one-native-fraction-rule-only-negative-summary.json'));
artifact('root-five-actual-negative-summary','actual-five-native-design-negative-results',path.join(B,'natural/2017-native-design-negatives/negative-controls.json'));
artifact('old-page07-actual-negative-report','actual-prior-wrong-conjunction-order-result',path.join(R,'actual-prior-949b9-conjunction-order-negative.json'));artifact('bar-only-actual-negative-report','actual-one-original-fraction-path-only-mutant-result',path.join(R,'one-native-fraction-rule-only-negative-summary.json'));
const negativeFiles=[
 ['bad-page06-order','natural/2017-native-design-negatives/actual-previous-conjunction-after-both-expressions/page06.pdf'],
 ['bad-page04-counter-drift','natural/2017-native-design-negatives/actual-native-counter12pt-drift/page04.pdf'],
 ['bad-page04-counter-covered','natural/2017-native-design-negatives/actual-native-counter-covered-metadata-unchanged/2017/TS/page04.pdf'],
 ['bad-page11-lambda-covered','natural/2017-native-design-negatives/actual-original-lambda-covered-metadata-unchanged/2017/TS/page11.pdf'],
 ['bad-page11-root-covered','natural/2017-native-design-negatives/actual-original-native-root-stroke-covered/2017/TS/page11.pdf'],
 ['bad-page07-order','natural/2017/TS/history/rejected-07-62f558aa0d342c1c/page07.pdf'],
 ['bad-page07-one-fraction-rule','page07-conjunction-repair/page07-only-one-original-equation10-fraction-rule-shifted-1pt.pdf']
];
const negative_pdfs=negativeFiles.map(([id,p])=>{const a=artifact(id,'actual-original-design-bad-PDF',path.join(B,p));return{id,sha256:a.sha256,bytes:a.bytes};});
const visual=read(path.join(F,'visual-review.json')),poppler=read(path.join(B,'natural/editions/IZhO_2017_TS_KO.poppler-assembly.json'));
artifact('full-source-final-visual-review','actual-all14-full-source-and-final-visual-review',path.join(F,'visual-review.json'));artifact('all14-Poppler-append-zeroRGB','actual-all14-native-append-independent-external-Poppler144',path.join(B,'natural/editions/IZhO_2017_TS_KO.poppler-assembly.json'));
const native_append=ready.page_audits.map(r=>({page:r.page,proof_sha256:r.proof_sha256,joined_vs_reviewed_proof_changed_pixels:r.joined_vs_reviewed_proof_changed_pixels,original_input_native_ink_missing:r.original_input_native_ink_missing,native_glyphs:r.native_glyphs}));
for(const name of['pdf_native_inline_reposition.py','pdf_original_text_ops.py','izho_2017_independent_original_math_geometry.py','izho_2017_original_formula_conjunction_order.py','izho_2017_page07_original_conjunction_order.py'])artifact(`engine-${name}`,'actual-unchanged-source-native-checker',path.join(B,'engine',name));
artifact('read-only-program-extractor','actual-source-specific-independent-program-extractor',path.join(O,'extract-izho2017-native-design-programs.py'));
artifacts.sort((a,b)=>a.id.localeCompare(b.id));
const b={kind:'source2017-complete-original-CID-program-conjunction-design-v1',file:'IZhO_2017_TS_KO.pdf',original_source_sha256:SOURCE,full_pdf_sha256:FULL,full_pdf_bytes:BYTES,pages:14,guard_sha256:hash(path.join(B,'engine/pdf_native_inline_reposition.py')),proofs,raw_controls,native_controls,source_bases,page_plans,programmes,actual_source_program_extraction:extraction,actual_conjunction_orders:orders,independent_original_math_geometry:geometry,page07_scope:scope,other13_prior_accepted_proofs:other13,actual_negatives:{root_five:rootNeg,prior_page07:old7,single_original_fraction_rule:bar,actual_unique_bad_PDFs:negative_pdfs},all14_visual_review:visual,native_append,independent_Poppler_append:poppler,artifacts};
fs.writeFileSync(path.join(O,'source-bound-native-design-contract.json'),JSON.stringify(b,null,2)+'\n');
const semantic={PROGRAMMES:digest(programmes),EXTRACTION:digest(extraction),ORDER:digest(orders),GEOMETRY:digest(geometry),SCOPE:digest(scope),OTHER13:digest(other13),NEGATIVES:digest(b.actual_negatives),VISUAL:digest(visual),NATIVE_APPEND:digest(native_append),POPPLER:digest(poppler),ARTIFACTS:digest(artifacts.map(({id,role,sha256,bytes})=>({id,role,sha256,bytes})))};
const pins={SOURCE,FULL,BYTES,GUARD:b.guard_sha256,PROOFS:proofs,RAW_CONTROLS:raw_controls,NATIVE_CONTROLS:native_controls,SOURCE_BASES:source_bases,PAGE_PLANS:page_plans,NEGATIVE_PDFS:negative_pdfs,...semantic};
fs.writeFileSync(path.join(O,'izho-2017-native-design-pins.cjs'),'// Closed exact actual source2017 artifacts. Source paths are never an authority.\nmodule.exports=Object.freeze('+JSON.stringify(pins,null,2)+');\n');
fs.writeFileSync(path.join(O,'actual-native-design-artifact-map.json'),JSON.stringify(artifacts,null,2)+'\n');
console.log('ACTUAL_SOURCE2017_DESIGN_CONTRACT_CREATED',artifacts.length,FULL);

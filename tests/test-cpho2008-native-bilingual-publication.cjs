'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),read=file=>JSON.parse(fs.readFileSync(path.join(root,file),'utf8'));
const bridge=require('./helpers/cpho2008-native-bilingual-publication.cjs');
const validate=require('./helpers/cpho-2008-source-native-design.cjs').validateEdition;
const items=read('tools/original_style_publication.json').filter(i=>i.audit_schema==='cpho2008-native-bilingual-original-v1');assert.equal(items.length,4);
const qa=read(items[0].qa),link=qa.source_native_contract;
const bundle=JSON.parse(bridge.readBound(root,link).toString('utf8'));
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),actual=new Map(),records=[];
for(const a of link.artifact_bindings){const raw=bridge.readBound(root,a);assert.equal(raw.length,a.bytes);assert.equal(sha(raw),a.sha256);assert.ok(!actual.has(a.id));actual.set(a.id,raw);}
const readActual=a=>{assert.ok(actual.has(a.id),a.id);return actual.get(a.id);};
const readArtifact=readActual;
for(const item of items){const ledger=read(item.qa);assert.deepEqual(ledger.source_native_contract,link);assert.equal(bridge(root,ledger,item),true);records.push({test:'positive-actual-public-ledger-'+item.file,passed:true});}
const item=items.find(i=>i.file===bundle.editions[0].file);assert.ok(item);
function reject(name,change,reader=readArtifact){const b=structuredClone(bundle);change(b);assert.throws(()=>validate(b,item,{readArtifact:reader}),name);records.push({test:name,actual_artifact_bytes_used:true,passed:true});}
assert.throws(()=>validate(bundle,item),/Resolve actual/);records.push({test:'reject-no-actual-ledger-reader',passed:true});
const privatePaths=structuredClone(bundle);for(const a of privatePaths.artifacts)a.source_path='Z:/ignored-detached-fixture-does-not-exist';assert.equal(validate(privatePaths,item,{readArtifact:readArtifact}),true);records.push({test:'actual-reader-ignores-all-private-source-paths',passed:true});
reject('reject-missing-source21',b=>b.classification.TS_source_pages.pop());
reject('reject-swapped-language-proof',b=>b.proofs['p01-ko']=b.proofs['p01-en']);
reject('reject-new-public-source-or-profile',b=>b.original_source_sha256='0'.repeat(64));
reject('reject-changed-full-edition-pin',b=>b.editions[0].sha256='1'.repeat(64));
function artifactMutant(name,id,edit){
 const data=JSON.parse(actual.get(id).toString('utf8'));edit(data);const changed=Buffer.from(JSON.stringify(data));
 reject(name,b=>{const a=b.artifacts.find(v=>v.id===id);a.sha256=sha(changed);a.bytes=changed.length;},a=>a.id===id?changed:readArtifact(a));
 records.at(-1).mutated_actual_artifact=id;records.at(-1).artifact_SHA_and_byte_pins_rebased=true;records.at(-1).mutated_actual_artifact_sha256=sha(changed);
}
artifactMutant('reject-rebased-encoded-CID','p01-ko-encoded',r=>r.original_CID_Tf_full_Tm_point_font_GID_paint_bindings[0].original_encoded_CID_hex='ffff');
artifactMutant('reject-rebased-original-font','p01-ko-encoded',r=>r.original_CID_Tf_full_Tm_point_font_GID_paint_bindings[0].font_resource='/NotTheOriginalFont');
artifactMutant('reject-rebased-fractional-Tf-point','p01-ko-encoded',r=>r.original_CID_Tf_full_Tm_point_font_GID_paint_bindings[0].original_Tf+=.125);
artifactMutant('reject-rebased-literal-Tm','p01-ko-encoded',r=>r.original_CID_Tf_full_Tm_point_font_GID_paint_bindings[0].original_literal_Tm[0]+=.125);
artifactMutant('reject-rebased-per-CID-Tm','p01-ko-encoded',r=>r.original_CID_Tf_full_Tm_point_font_GID_paint_bindings[0].actual_full_per_CID_Tm[4]+=.25);
artifactMutant('reject-rebased-original-GID','p01-ko-encoded',r=>r.original_CID_Tf_full_Tm_point_font_GID_paint_bindings[0].source_glyphs[0].trace_gid++);
artifactMutant('reject-rebased-ancestor-clip','p01-ko-encoded',r=>r.original_CID_Tf_full_Tm_point_font_GID_paint_bindings[0].actual_literal_ancestor_clip_programs.push({rect:[0,0,1,1],clip_operator:'W'}));
artifactMutant('reject-rebased-fraction-rule-shape','p15-ko-native',r=>r.independent_original_native_geometry.literal_original_vector_path_programs[0].source_rect[0]+=2);
artifactMutant('reject-rebased-prose-order','p01-en-plan',r=>{const row=r.rows.find(v=>v.id==='r06');row.en='Changed order '+row.en;});
artifactMutant('reject-rebased-natural-word-gap','p01-ko-prose',r=>r.source_point_baseline_center_and_quarter_em_word_gap_rows[0].expected_word_gap_pt+=1);
artifactMutant('reject-rebased-new-font-file','p01-ko-prose',r=>r.new_original_role_font_programs[0].actual_embedded_font_program_sha256='2'.repeat(64));
artifactMutant('reject-rebased-kept-ink-font-closure','p01-ko-kept',r=>r.source_and_known_new_font_resource_closure.push('/UnreviewedFont'));
artifactMutant('reject-rebased-added-PageGroup-policy','p01-ko-native',r=>r.original_source_to_initial_and_final_Page_Group_exact=false);
artifactMutant('reject-rebased-false-zero-native-RGB','p01-ko-native',r=>r.raw_original_input_native_ink.newly_missing_native_ink_pixels=1);
artifactMutant('reject-rebased-false-zero-graphics-RGB','p04-ko-bitmap',r=>r.changed_original_nonlanguage_graphics_RGB_pixels=1);
artifactMutant('reject-rebased-original-CJK-size','bitmap-source-only-language-policy',r=>r.labels[0].source_only_measured_size_pt-=.5);
artifactMutant('reject-rebased-bitmap-cover-over-wire','bitmap-source-only-language-policy',r=>r.labels[0].erase_rect_pt[2]+=3);
artifactMutant('reject-rebased-label-overlap-policy','p04-ko-bitmap',r=>r.new_label_over_original_nonlanguage_ink_pixels=1);
artifactMutant('reject-rebased-fake-final-zero-RGB','all4-final-append-zero-RGB',r=>r.editions[0].pages[0].native_MuPDF4x_changed_RGB_pixels=1);
artifactMutant('reject-rebased-actual-negative-pass','all7-actual-negative-PDFs',r=>r.actual_unique_bad_PDFs[0].actual_PDF_rejected=false);
const source=Buffer.from(actual.get('original-source'));source[source.length-17]^=1;
reject('reject-one-byte-actual-original-PDF',()=>{},a=>a.id==='original-source'?source:readArtifact(a));
const finalId=item.file,final=Buffer.from(actual.get(finalId));final[final.length-17]^=1;
reject('reject-one-byte-actual-final-PDF',()=>{},a=>a.id===finalId?final:readArtifact(a));
reject('reject-rebased-one-byte-actual-final-PDF',b=>{const a=b.artifacts.find(v=>v.id===finalId);a.sha256=sha(final);},a=>a.id===finalId?final:readArtifact(a));

const detached=structuredClone(qa);delete detached.source_native_contract;assert.throws(()=>bridge(root,detached,items[0]));records.push({test:'reject-detached-public-ledger',passed:true});
const missing=structuredClone(qa);missing.source_native_contract.artifact_bindings.pop();assert.throws(()=>bridge(root,missing,items[0]));records.push({test:'reject-missing-actual-public-artifact',passed:true});
const privatePath=structuredClone(qa);privatePath.source_native_contract.artifact_bindings[0].path='C:/private/detached-fixture.pdf';assert.throws(()=>bridge(root,privatePath,items[0]));records.push({test:'reject-private-source-path-as-staged-reader',passed:true});
console.log('C08_ACTUAL_PUBLIC_LEDGER_SOURCE_NATIVE_CONTRACTS',records.length,'artifacts',actual.size,'all passed');

const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const validate=require('./izho-2017-native-design-programs.cjs'),mutations=require('./izho-2017-native-design-mutations.cjs');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8')),hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const evidencePath=path.join(__dirname,'source-bound-native-design-contract.json'),b=read(evidencePath),actualMap=read(path.join(__dirname,'actual-native-design-artifact-map.json'));
// Private authoring runner only: binds the actual accepted input paths by
// their original hashes. Public caller MUST instead bind the frozen ledger.
const byId=new Map(actualMap.map(a=>[a.id,a])),item={file:b.file,sha256:b.full_pdf_sha256};
const resolver=a=>{const pinned=byId.get(a.id);assert.ok(pinned,a.id);assert.equal(a.sha256,pinned.sha256);assert.equal(a.bytes,pinned.bytes);return fs.readFileSync(pinned.source_path);};
assert.equal(validate.validateEdition(b,item,{readArtifact:resolver}),true);
const results=[{id:'actual-source-and-current-edition-positive',passed:true,actual_artifacts:b.artifacts.length}];
for(const [id,mutate]of mutations){const changed=structuredClone(b);mutate(changed);assert.throws(()=>validate.validateEdition(changed,item,{readArtifact:resolver}),undefined,id);results.push({id,mutation_rejected:true,passed:true});}
assert.throws(()=>validate.validateEdition(b,item),/actual frozen publication-ledger/);results.push({id:'resolver-required-no-detached-fixture',mutation_rejected:true,passed:true});
for(const id of['proof-07','original-program-07-1','bad-page07-one-fraction-rule']){
 const r=a=>{const bytes=resolver(a);if(a.id===id){const bad=Buffer.from(bytes);bad[Math.floor(bad.length/2)]^=1;return bad;}return bytes;};
 assert.throws(()=>validate.validateEdition(b,item,{readArtifact:r}));results.push({id:`actual-byte-mutation-${id}`,mutation_rejected:true,passed:true});
}
// source_path is a provenance hint only and is never dereferenced by the
// reusable public validator. A frozen-ledger resolver remains authoritative.
const noPrivatePaths=structuredClone(b);for(const a of noPrivatePaths.artifacts)a.source_path='X:/untrusted/does-not-exist';assert.equal(validate.validateEdition(noPrivatePaths,item,{readArtifact:resolver}),true);results.push({id:'private-source-path-never-trusted',passed:true});
const report={kind:b.kind,actual_bundle_sha256:hash(fs.readFileSync(evidencePath)),original_source_sha256:b.original_source_sha256,full_pdf_sha256:b.full_pdf_sha256,actual_artifacts:b.artifacts.length,actual_distinct_bad_PDFs:b.actual_negatives.actual_unique_bad_PDFs.length,semantic_mutations_rejected:mutations.length,actual_byte_mutations_rejected:3,required_resolver_checked:true,private_source_path_never_trusted:true,checks:results.length,results,passed:true};
fs.writeFileSync(path.join(__dirname,'actual-native-design-contract-verification.json'),JSON.stringify(report,null,2)+'\n');console.log('ACTUAL_SOURCE2017_DESIGN_CONTRACT_PASS',report.checks,'checks;',mutations.length,'semantic mutants;',b.artifacts.length,'actual artifact bindings;',report.full_pdf_sha256);

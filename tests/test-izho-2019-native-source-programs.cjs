const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),read=f=>JSON.parse(fs.readFileSync(path.join(root,f),'utf8'));
const item=read('tools/original_style_publication.json').find(r=>r.file==='IZhO_2019_TS_KO.pdf');assert.ok(item);
const record=read(item.qa),contract=record.source_native_contract;assert.ok(contract);const bundle=read(contract.path),bindings=new Map(contract.artifact_bindings.map(a=>[a.id,a]));
assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,contract.path))).digest('hex'),contract.sha256);
const readArtifact=a=>{const b=bindings.get(a.id);assert.ok(b);assert.equal(b.sha256,a.sha256);assert.equal(b.bytes,a.bytes);assert.ok(b.path.startsWith(record.authoring_snapshotroot+'/'));const target=path.resolve(root,b.path);assert.ok(target.startsWith(root+path.sep));return fs.readFileSync(target);};
const validate=require('./helpers/izho-2019-native-source-programs.cjs'),mutations=require('./helpers/izho-2019-native-source-mutations.cjs');
test('Actual public ledger preserves all source2019 native CIDs,32 painted-space heads, original clips and damaged-PDF controls',()=>{
 const page=record.page_proofs.find(p=>p.page===6),ledger=read(page.original_native_ink),profile=ledger.original_native_cid_profile;validate(profile,read(profile.path),ledger.raw_svg_audit,page,item);validate.validateEdition(bundle,item,{readArtifact});
});
for(const [name,change]of mutations)test(`reject ${name}`,()=>{const x=structuredClone(bundle);change(x);assert.throws(()=>validate.validateEdition(x,item,{readArtifact}),name);});
for(const role of ['exact-reviewed-page-proof','official-source-byte-identical-program'])test(`reject changed actual staged ${role} bytes with original metadata`,()=>{let changed=false;assert.throws(()=>validate.validateEdition(bundle,item,{readArtifact:a=>{const bytes=readArtifact(a);if(!changed&&a.role===role){changed=true;bytes[0]^=1;}return bytes;}}));assert.equal(changed,true);});
test('Reject detached contract without an actual staged ledger resolver',()=>assert.throws(()=>validate.validateEdition(bundle,item),/actual staged ledger artifacts/));

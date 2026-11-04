// Bind to the ACTUAL public edition item and its frozen ledger. Resolve each
// artifact's bytes through that ledger's artifact_bindings by SHA, byte count
// and id; never trust the private bundle's source_path. Keep the separate
// original p11 lambda phase validator unchanged.
function validateNativeDesign(actualLedger,actualItem,readFrozenArtifact){
 const fs=require('node:fs'),crypto=require('node:crypto'),assert=require('node:assert/strict');
 const validate=require('./izho-2017-native-design-programs.cjs');
 const link=actualLedger.source_native_contract;
 assert.ok(link&&link.path&&link.sha256&&Array.isArray(link.artifact_bindings));
 const raw=fs.readFileSync(link.path);assert.equal(crypto.createHash('sha256').update(raw).digest('hex'),link.sha256);
 const b=JSON.parse(raw.toString('utf8')),map=new Map(link.artifact_bindings.map(a=>[a.id,a]));
 return validate.validateEdition(b,actualItem,{readArtifact:a=>{const pinned=map.get(a.id);assert.ok(pinned);assert.equal(pinned.sha256,a.sha256);assert.equal(pinned.bytes,a.bytes);return readFrozenArtifact(pinned);}});
}
module.exports=validateNativeDesign;

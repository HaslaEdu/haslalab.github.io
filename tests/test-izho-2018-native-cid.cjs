const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const validate=require('./helpers/izho-2018-native-cid-witness.cjs');
const item=read('tools/original_style_publication.json').find(r=>r.file==='IZhO_2018_T_KO.pdf');
const publication=read(item.qa);
for(const n of [3,4]){
  const page=publication.page_proofs.find(r=>r.page===n);
  const ledger=read(page.original_native_ink);
  const profile=ledger.original_native_cid_profile;
  const witness=read(profile.path);
  test(`IZhO2018 page${n}: exact original CID reference and real omission negative`,()=>validate(profile,witness,ledger.raw_svg_audit,page,item));
  test(`IZhO2018 page${n}: rejects missing native ink, altered source point, incomplete independent coverage and changed proof`,()=>{
    const change=(mutate)=>{const w=structuredClone(witness);mutate(w);assert.throws(()=>validate(profile,w,ledger.raw_svg_audit,page,item));};
    change(w=>w.native_CID_reference_measurements[0].actual_reference_nonwhite_RGB_errors=1);
    change(w=>w.checks[0].actual_destination.size=11.9);
    change(w=>w.native_CID_reference_measurements.pop());
    change(w=>w.high_resolution_unhinted_SVG[0].svg_missing=1);
    change(w=>w.proof_sha256='0'.repeat(64));
    change(w=>w.negative_actual_original_CID_omission.checks[0].reference_dark_pixels_missing=0);
  });
}

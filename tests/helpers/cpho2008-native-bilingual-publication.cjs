'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const design=require('./cpho-2008-source-native-design.cjs');
const prefix='tools/ko/cpho/2008/native-bilingual-original-v1/';
const contractPath=prefix+'source-bound-native-bilingual-design-contract.json';
const contractSHA='7535baff7567ca228e01cd934e8f8bdeae94f7d9e4e74d1a82f06762314d4b51';
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
function readBound(root,binding){
  assert.equal(typeof binding.path,'string');
  assert.ok(!/^[a-z][a-z0-9+.-]*:/i.test(binding.path)&&!path.isAbsolute(binding.path),'Use only actual staged relative artifacts');
  const file=path.resolve(root,binding.path),relative=path.relative(root,file);
  assert.ok(relative&&relative!=='..'&&!relative.startsWith('..'+path.sep)&&!path.isAbsolute(relative));
  const raw=fs.readFileSync(file);
  if(binding.bytes!==undefined)assert.equal(raw.length,binding.bytes,binding.path);
  assert.equal(sha(raw),binding.sha256,binding.path);
  return raw;
}
function validate(root,record,item){
  assert.equal(item.audit_schema,'cpho2008-native-bilingual-original-v1');
  assert.equal(record.schema,item.audit_schema);assert.equal(record.status,'READY');
  for(const key of ['file','sha256','bytes','pages','language'])assert.equal(record[key],item[key],key);
  const expected=design.pins.EDITIONS.find(e=>e.file===item.file);assert.ok(expected);
  for(const key of ['sha256','bytes','pages','language'])assert.equal(item[key],expected[key],key);
  assert.equal(record.source_sha256,design.pins.SOURCE);
  assert.deepEqual(record.source_physical_pages,expected.kind==='T'?[1,2,3,4,5,6]:Array.from({length:15},(_,i)=>i+7));
  for(const key of ['original_native_math_fonts_fractional_points_clips_paths_images_and_Group_retained','original_title_caption_table_centers_and_prose_font_roles_retained','natural_quarter_em_word_spaces','bitmap_label_points_are_source_measured_estimates_not_native_metadata','all42_full_source_proof_visuals_reviewed','all42_final_append_MuPDF4x_and_Poppler144_RGB_differences_zero'])assert.equal(record[key],true,key);
  const link=record.source_native_contract;assert.ok(link&&Array.isArray(link.artifact_bindings));
  assert.equal(link.path,contractPath);assert.equal(link.sha256,contractSHA);
  const bundle=JSON.parse(readBound(root,link).toString('utf8'));
  const map=new Map(link.artifact_bindings.map(a=>[a.id,a]));
  assert.equal(map.size,link.artifact_bindings.length);assert.equal(map.size,793);
  assert.deepEqual([...map.keys()].sort(),bundle.artifacts.map(a=>a.id).sort());
  return design.validateEdition(bundle,item,{readArtifact:a=>{
    const actual=map.get(a.id);assert.ok(actual,a.id);assert.equal(actual.sha256,a.sha256);assert.equal(actual.bytes,a.bytes);
    assert.ok(actual.path.startsWith(prefix+'artifacts/'+a.sha256+'/'));
    return readBound(root,actual);
  }});
}
module.exports=validate;
module.exports.readBound=readBound;

'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const design=require('./cpho-2004-source-native-design.cjs');
const prefix='tools/ko/cpho/2004/native-bilingual-original-v1/';
const contractPath=prefix+'source-bound-native-bilingual-design-contract.json';
const contractSHA='7d645d6a6ef91d7fdb66497cabddf878ba2697fc3eebc4902f37717332299c9e';
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
function readBound(root,binding){
 assert.equal(typeof binding.path,'string');assert.ok(!/^[a-z][a-z0-9+.-]*:/i.test(binding.path)&&!path.isAbsolute(binding.path));
 const file=path.resolve(root,binding.path),relative=path.relative(root,file);
 assert.ok(relative&&relative!=='..'&&!relative.startsWith('..'+path.sep)&&!path.isAbsolute(relative));
 const raw=fs.readFileSync(file);assert.equal(raw.length,binding.bytes===undefined?raw.length:binding.bytes);assert.equal(sha(raw),binding.sha256,binding.path);return raw;
}
function validate(root,record,item){
 assert.equal(item.audit_schema,'cpho2004-native-bilingual-original-v1');assert.equal(record.schema,item.audit_schema);assert.equal(record.status,'READY');
 for(const key of ['file','sha256','bytes','pages','language'])assert.equal(record[key],item[key],key);
 const expected=design.pins.EDITIONS.find(e=>e.file===item.file);assert.ok(expected);
 for(const key of ['sha256','bytes','pages','language'])assert.equal(item[key],expected[key],key);
 assert.equal(record.source_sha256,design.pins.SOURCE);assert.equal(record.competition,'cpho');assert.equal(record.year,2004);assert.equal(record.kind,expected.kind);
 assert.deepEqual(record.source_physical_pages,expected.kind==='T'?[1,2,3,4]:Array.from({length:14},(_,i)=>i+5));
 for(const key of ['original_native_math_fonts_fractional_points_clips_paths_images_and_Group_retained','original_title_caption_table_centers_and_prose_font_roles_retained','natural_quarter_em_word_spaces','bitmap_label_points_are_source_measured_estimates_not_native_metadata','all36_full_source_proof_visuals_reviewed','all36_final_append_MuPDF4x_and_Poppler144_RGB_differences_zero','original_wrong28th_footer_and_blank_physical_tail_retained','private_inputs_metadata_only'])assert.equal(record[key],true,key);
 for(const key of ['full_installed_font_programs_exported','private_engine_programs_exported'])assert.equal(record[key],false,key);
 assert.equal(record.public_actual_artifact_count,2586);assert.equal(record.private_immutable_input_inventory_count,162);assert.equal(record.original_complete_private_artifact_inventory_count,2748);
 const link=record.source_native_contract;assert.ok(link&&Array.isArray(link.artifact_bindings));assert.equal(link.path,contractPath);assert.equal(link.sha256,contractSHA);
 const bundle=JSON.parse(readBound(root,link).toString('utf8')),privateIds=new Set(design.privateInputIds);
 const map=new Map(link.artifact_bindings.map(a=>[a.id,a]));assert.equal(map.size,link.artifact_bindings.length);assert.equal(map.size,2586);
 assert.deepEqual([...map.keys()].sort(),bundle.artifacts.filter(a=>!privateIds.has(a.id)).map(a=>a.id).sort());
 return design.validateEdition(bundle,item,{readArtifact:a=>{
  assert.ok(!privateIds.has(a.id),'Private engine / full-font bytes must never be public reader inputs');const actual=map.get(a.id);assert.ok(actual,a.id);assert.equal(actual.sha256,a.sha256);assert.equal(actual.bytes,a.bytes);assert.ok(actual.path.startsWith(prefix+'artifacts/'+a.sha256+'/'));assert.ok(!/\.(ttf|py)$/i.test(actual.path));return readBound(root,actual);
 }});
}
module.exports=validate;module.exports.readBound=readBound;

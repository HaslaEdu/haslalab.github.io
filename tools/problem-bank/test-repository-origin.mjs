import test from 'node:test';import assert from 'node:assert/strict';import {DatabaseSync} from 'node:sqlite';
import {normalizeImport,sourceId,applyImport,questionId} from './store.mjs';import {normalizeSolutions} from './solutions.mjs';
import {normalizeBankCatalogue} from '../../community/src/problem-bank-catalogue.js';
const sha='a'.repeat(64),origin={kind:'repository_asset',repository_url:'https://github.com/HaslaEdu/haslalab.github.io',repository_path:'pdf/Synthetic_2020_T1.pdf',commit:'b'.repeat(40),rights:{status:'not_established'}};
const source={origin,revision:'sha256:'+sha,title:'Synthetic contest 2020',sha256:sha,page_count:2,subjects:['classical_mechanics'],level:'olympiad',source_language:'en',catalogue:{kind:'contest',competition:'synthetic',year:2020,problem_type:'theory',discipline:'physics'}};
const q={source:{origin,revision:source.revision},locator:'theory/T1',original_number:'T1',spans:[{page:1,bbox:[0,0,1,.5]}],context:{catalogue:{competition:'synthetic',year:2020,problem_code:'T1',title_en:'Synthetic title',title_ko:'가상 문항',problem_type:'theory',discipline:'physics'}},versions:[{language:'en',role:'original',text:'Synthetic question.'},{language:'ko',role:'translation',text:'테스트용 가상 문항.'}]};
const normalize=(s=source,question=q)=>normalizeImport({version:1,sources:[s]},{version:1,questions:[question]});
test('repository PDF source persists exact typed provenance without a fictitious Drive ID or license',async()=>{
 const n=normalize(),db=new DatabaseSync(':memory:');try{await applyImport(db,n);const row=db.prepare('SELECT * FROM book_sources').get();assert.equal(n.sources[0].drive_id,null);assert.equal(row.drive_id,'repository_asset:'+origin.repository_url+'#'+origin.repository_path);assert.deepEqual(JSON.parse(db.prepare('SELECT origin_json FROM bank_source_origins').get().origin_json),origin);assert.equal(n.sources[0].origin.license_identifier,undefined);assert.equal(n.questions[0].context.catalogue.year,2020);assert.equal(n.questions[0].id,questionId(source,'theory/T1'));}finally{db.close();}
});
test('repository source identity binds repository, path and actual PDF revision while metadata edits keep IDs',()=>{
 const id=sourceId(source);assert.equal(sourceId({...source,catalogue:{...source.catalogue,title_en:'Corrected title'}}),id);assert.notEqual(sourceId({...source,origin:{...origin,repository_path:'pdf/Other.pdf'}}),id);assert.notEqual(sourceId({...source,revision:'sha256:'+'c'.repeat(64)}),id);
});
test('repository imports reject traversal, credentials, mixed Drive identity and false content revisions',()=>{
 for(const path of ['../x.pdf','/x.pdf','C:/private.pdf','pdf/../x.pdf'])assert.throws(()=>normalize({...source,origin:{...origin,repository_path:path}}));
 assert.throws(()=>normalize({...source,origin:{...origin,repository_url:'https://user:password@example.org/repo'}}));assert.throws(()=>normalize({...source,drive_id:'fake-drive'}));assert.throws(()=>normalize({...source,revision:'sha256:'+'d'.repeat(64)}));
});
test('catalogue validation keeps school subjects and problem types explicit without accepting private paths',()=>{
 for(const discipline of ['physics','astronomy','mathematics','chemistry','biology','earth_science','informatics'])assert.equal(normalizeBankCatalogue({kind:'contest',competition:'synthetic',discipline},{source:true}).discipline,discipline);
 for(const input of [{kind:'contest'},{year:'2020'},{year:1200},{problem_type:'written'},{title_en:'D:/private/source.pdf'},{discipline:'unknown'},{title_en:'test',secret:'value'}])assert.throws(()=>normalizeBankCatalogue(input,{source:!!input.kind}));
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createHash} from 'node:crypto';
import {normalizeImport,sourceId,applyImport,readInlineAsset} from './store.mjs';
import {splitImport,validateRoutes,verificationSql,expectedSnapshot,verifySnapshot,registrySql,canonicalProgressSql} from './route-import.mjs';

function fixture(){
  const databases=[{name:'haslalab-problem-bank',id:'00000000-0000-0000-0000-000000000001'},
    {name:'haslalab-problem-bank-02',id:'00000000-0000-0000-0000-000000000002'}];
  const sources=['one','two','inventory-only'].map(label=>({drive_id:'synthetic-'+label,revision:'v1',title:label,sha256:'a'.repeat(64),page_count:4,
    subjects:['classical_mechanics'],level:'undergraduate',source_language:'en',expected_question_count:1,extraction_complete:true}));
  const bytes=Buffer.from('synthetic private crop'),sha=createHash('sha256').update(bytes).digest('hex');
  const questions=sources.slice(0,2).map(source=>({source,locator:'chapter-1/problem-1',original_number:'1',spans:[{page:1,bbox:[0,0,1,1]}],
    context:{source_image_checked:true},assets_complete:true,
    versions:[{language:'en',role:'original',text:'Find $x$.'},{language:'ko',role:'translation',text:'$x$를 구하여라.'}],
    assets:[{asset_id:'crop',role:'question_crop',mime_type:'image/webp',private_object_key:'private/crop',sha256:sha,
      spans:[{page:1,bbox:[0,0,1,1]}],inline_base64:bytes.toString('base64')}]}));
  const normalized=normalizeImport({version:1,sources},{version:1,questions});
  const plan={version:1,registry_database:databases[0].name,databases,source_routes:sources.map((s,i)=>({source_id:sourceId(s),database:databases[i===1?1:0].name,question_count:1}))};
  return {normalized,plan,bytes};
}
async function copy(group){
  const database=new DatabaseSync(':memory:');await applyImport(database,group);
  const sql=verificationSql(group.sources.map(s=>s.id));assert.equal(sql.includes('UNION'),false);
  return {database,response:sql.split(';').filter(s=>s.trim()).map(query=>({success:true,results:database.prepare(query).all()}))};
}
test('fresh shards import only selected complete books, retaining IDs, both languages and crop bytes',async()=>{
  const f=fixture(),groups=splitImport(f.normalized,f.plan);
  assert.equal(groups.size,2);
  for(const [name,group] of groups){
    assert.equal(group.sources.length,1);assert.equal(group.questions.length,1);
    const {database,response}=await copy(group);
    try{
      assert.equal(database.prepare('SELECT count(*) n FROM book_sources').get().n,1);
      assert.equal(database.prepare('SELECT count(*) n FROM bank_question_versions').get().n,2);
      assert.deepEqual(readInlineAsset(database,group.questions[0].assets[0].id),f.bytes);
      const expected=expectedSnapshot(group,f.plan.databases.find(db=>db.name===name));
      assert.equal(verifySnapshot(expected,response).remote_metadata_verified,true);
      assert.equal(group.questions[0].id,f.normalized.questions.find(q=>q.source_id===group.sources[0].id).id);
    }finally{database.close();}
  }
});
test('unknown, missing, duplicate routes and aliased databases fail before export',()=>{
  for(const mutate of [p=>p.source_routes.pop(),p=>p.source_routes.push(p.source_routes[0]),p=>p.source_routes[0].source_id='unknown',
    p=>p.source_routes[0].database='community',p=>p.databases[1].id=p.databases[0].id,p=>p.databases[1].name='community']){
    const f=fixture();mutate(f.plan);assert.throws(()=>validateRoutes(f.normalized,f.plan));
  }
});
test('copy verification detects changed context, stale language, missing asset and additional question records',async()=>{
  const f=fixture(),group=splitImport(f.normalized,f.plan).get('haslalab-problem-bank-02');
  const {database,response}=await copy(group);
  try{
    const expected=expectedSnapshot(group,f.plan.databases[1]);
    for(const kind of ['context','version','asset','question']){
      const altered=structuredClone(response),result=altered.find(r=>r.results.some(row=>JSON.parse(row.record)[1]===kind));
      const index=result.results.findIndex(r=>JSON.parse(r.record)[1]===kind);
      if(kind==='asset')result.results.splice(index,1);
      else if(kind==='question')result.results.push(result.results[index]);
      else{const record=JSON.parse(result.results[index].record);record[record.length-1]='changed';result.results[index].record=JSON.stringify(record);}
      assert.throws(()=>verifySnapshot(expected,altered),/fingerprint mismatch/);
    }
    assert.throws(()=>verifySnapshot(expected,[{success:false,results:[]}]));
  }finally{database.close();}
});
test('canonical routing requires verified copy and crop readback; retained legacy copies never add routes',async()=>{
  const f=fixture(),group=splitImport(f.normalized,f.plan).get('haslalab-problem-bank-02');
  const {database,response}=await copy(group),registry=new DatabaseSync(':memory:');
  try{
    const receipt=verifySnapshot(expectedSnapshot(group,f.plan.databases[1]),response);
    assert.throws(()=>registrySql(f.normalized,f.plan),/Verified copy required/);
    assert.throws(()=>registrySql(f.normalized,f.plan,[receipt]),/crop readback required/);
    const sample={database:receipt.database.name,server_readback:true,hash_mismatches:0,image_decode_failures:0,sampled_sources:1,checked_at:new Date().toISOString()};
    registry.exec(registrySql(f.normalized,f.plan,[receipt],[sample]));
    registry.exec(registrySql(f.normalized,f.plan,[receipt],[sample]));
    assert.equal(registry.prepare('SELECT count(*) n FROM bank_source_routes').get().n,3);
    assert.equal(registry.prepare('SELECT database_name FROM bank_source_routes WHERE source_id=?').get(group.sources[0].id).database_name,receipt.database.name);
    assert.equal(database.prepare('SELECT count(*) n FROM bank_questions').get().n,1);
  }finally{database.close();registry.close();}
});
test('partial copies cannot activate a route and progress excludes retained copies',async()=>{
  const f=fixture(),groups=splitImport(f.normalized,f.plan),group=groups.get('haslalab-problem-bank-02');
  assert.throws(()=>expectedSnapshot({...group,questions:group.questions.map(q=>({...q,assets_complete:false}))},f.plan.databases[1]),/full snapshot/);
  const legacy=new DatabaseSync(':memory:');
  try{
    await applyImport(legacy,{...f.normalized,sources:f.normalized.sources.filter(s=>s.title!=='inventory-only')});
    assert.equal(legacy.prepare('SELECT count(*) n FROM bank_questions').get().n,2);
    const rows=legacy.prepare(canonicalProgressSql(f.normalized,f.plan).get('haslalab-problem-bank')).all();
    assert.equal(rows.reduce((n,row)=>n+row.questions,0),1);
    const {database,response}=await copy(group);
    try{
      const receipt=verifySnapshot(expectedSnapshot(group,f.plan.databases[1]),response);
      const sample={database:receipt.database.name,server_readback:true,hash_mismatches:0,image_decode_failures:0,sampled_sources:1,checked_at:new Date().toISOString()};
      const incomplete=structuredClone(receipt);incomplete.sources[0].question_count=0;
      assert.throws(()=>registrySql(f.normalized,f.plan,[incomplete],[sample]),/Incomplete question copy/);
    }finally{database.close();}
  }finally{legacy.close();}
});

// Private D1 book routing and copy verification. No network or billing actions.
import {createHash,randomUUID} from 'node:crypto';
import {readFile,open,rename,unlink} from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {normalizeImport,writeImportSql,privateOutput,sqlLiteral} from './store.mjs';

const digest=value=>createHash('sha256').update(value).digest('hex');
const fail=message=>{throw new Error(message);};
const encode=rows=>rows.map(row=>JSON.stringify(row)).sort();
const fingerprint=rows=>digest(JSON.stringify(encode(rows)));
const uuid=/^[a-f\d]{8}-(?:[a-f\d]{4}-){3}[a-f\d]{12}$/;
export function validateRoutes(normalized,plan){
  if(plan?.version!==1||!Array.isArray(plan.databases)||!Array.isArray(plan.source_routes))fail('Invalid routing format');
  const databases=new Map(),ids=new Set();
  for(const db of plan.databases){
    if(!/^haslalab-(?:private-)?problem-bank(?:-[a-z\d]+)*$/.test(db.name)||!uuid.test(db.id)||databases.has(db.name)||ids.has(db.id))fail('Duplicate or invalid private database');
    databases.set(db.name,{name:db.name,id:db.id});ids.add(db.id);
  }
  if(!databases.has(plan.registry_database))fail('Unknown registry database');
  const known=new Set(normalized.sources.map(s=>s.id)),routes=new Map();
  for(const route of plan.source_routes){
    if(!known.has(route.source_id)||routes.has(route.source_id)||!databases.has(route.database)||!Number.isSafeInteger(route.question_count)||route.question_count<0)fail('Unknown, incomplete or duplicate source route');
    routes.set(route.source_id,route.database);
  }
  if(routes.size!==known.size)fail('Every registered source requires exactly one route');
  return {databases,routes,registry_database:plan.registry_database};
}
export function splitImport(normalized,plan){
  const validated=validateRoutes(normalized,plan),groups=new Map();
  for(const q of normalized.questions){
    const name=validated.routes.get(q.source_id);
    if(!groups.has(name))groups.set(name,{sources:[],questions:[]});
    groups.get(name).questions.push(q);
  }
  for(const group of groups.values()){
    const selected=new Set(group.questions.map(q=>q.source_id));
    // Other complete books in the global inventory do not belong in a fresh shard.
    group.sources=normalized.sources.filter(s=>selected.has(s.id));
  }
  return groups;
}
export function canonicalProgressSql(normalized,plan){
  const {databases,routes}=validateRoutes(normalized,plan),queries=new Map();
  for(const name of databases.keys()){
    const ids=[...routes].filter(([,target])=>target===name).map(([id])=>sqlLiteral(id));
    if(!ids.length)continue;
    queries.set(name,`SELECT s.id AS source_id,s.title,s.expected_question_count,s.extraction_complete,
      (SELECT COUNT(*) FROM bank_questions q WHERE q.source_id=s.id) AS questions,
      (SELECT COUNT(*) FROM bank_questions q WHERE q.source_id=s.id
        AND EXISTS(SELECT 1 FROM bank_question_versions v WHERE v.question_id=q.id AND v.active=1 AND v.language='en')
        AND EXISTS(SELECT 1 FROM bank_question_versions v WHERE v.question_id=q.id AND v.active=1 AND v.language='ko')) AS bilingual_versions,
      (SELECT COUNT(*) FROM bank_assets a JOIN bank_questions q ON q.id=a.question_id WHERE q.source_id=s.id) AS assets,
      (SELECT ready FROM bank_source_readiness WHERE id=s.id) AS publication_ready
      FROM book_sources s WHERE s.id IN (${ids.join(',')}) ORDER BY s.id;\n`);
  }
  return queries;
}

// Hash all current content identities and crop/chunk metadata, excluding clocks
// and historical inactive versions. Text and bytes already have SHA-256 IDs.
export function snapshotRecords(normalized){
  const rows=[];
  for(const s of normalized.sources)rows.push([s.id,'source',s.id,s.sha256,s.page_count,s.source_language,s.expected_question_count,s.extraction_complete?1:0]);
  for(const q of normalized.questions){
    rows.push([q.source_id,'question',q.id,q.metadata_hash,q.review_status]);
    rows.push([q.source_id,'context',q.id,q.source_language,JSON.stringify(q.context)]);
    for(const v of q.versions)rows.push([q.source_id,'version',q.id,v.language,v.role,v.text_sha256,v.review_status]);
    for(const a of q.assets){
      rows.push([q.source_id,'asset',a.id,q.id,a.asset_id,a.role,a.private_object_key,a.mime_type,a.sha256,JSON.stringify(a.spans)]);
      if(a.inline){
        rows.push([q.source_id,'payload',a.id,a.inline.byte_length,a.inline.sha256,a.inline.chunks.length]);
        a.inline.chunks.forEach((c,i)=>rows.push([q.source_id,'chunk',a.id,i,c.bytes.length,c.sha256]));
      }
    }
  }
  return rows;
}
export function verificationSql(sourceIds){
  if(!sourceIds.length||sourceIds.some(id=>!/^src_[a-f\d]{64}$/.test(id)))fail('Invalid verification source IDs');
  const scope=sourceIds.map(sqlLiteral).join(','),where=`q.source_id IN (${scope})`;
  return [
    `SELECT json_array(s.id,'source',s.id,s.sha256,s.page_count,s.source_language,s.expected_question_count,s.extraction_complete) record FROM book_sources s WHERE s.id IN (${scope})`,
    `SELECT json_array(q.source_id,'question',q.id,q.metadata_hash,q.review_status) FROM bank_questions q WHERE ${where}`,
    `SELECT json_array(q.source_id,'context',q.id,c.source_language,c.context_json) FROM bank_question_context c JOIN bank_questions q ON q.id=c.question_id WHERE ${where}`,
    `SELECT json_array(q.source_id,'version',q.id,v.language,v.role,v.text_sha256,v.review_status) FROM bank_question_versions v JOIN bank_questions q ON q.id=v.question_id WHERE v.active=1 AND ${where}`,
    `SELECT json_array(q.source_id,'asset',a.id,q.id,a.asset_id,a.role,a.private_object_key,a.mime_type,a.sha256,a.spans_json) FROM bank_assets a JOIN bank_questions q ON q.id=a.question_id WHERE ${where}`,
    `SELECT json_array(q.source_id,'payload',a.id,p.byte_length,p.sha256,p.chunk_count) FROM bank_asset_payloads p JOIN bank_assets a ON a.id=p.asset_id JOIN bank_questions q ON q.id=a.question_id WHERE ${where}`,
    `SELECT json_array(q.source_id,'chunk',a.id,c.chunk_index,c.byte_length,c.sha256) FROM bank_asset_chunks c JOIN bank_assets a ON a.id=c.asset_id JOIN bank_questions q ON q.id=a.question_id WHERE ${where}`,
  // Separate bounded SELECTs also work on D1 deployments with a low compound
  // SELECT limit. Wrangler returns one result object per statement.
  ].map(query=>query.replace(') FROM ',') AS record FROM ')).join(';\n')+';\n';
}
export function expectedSnapshot(normalized,database){
  if(normalized.questions.some(q=>!q.assets_complete||!q.versions.length||!q.assets.length||q.assets.some(a=>!a.inline)))fail('Copy verification requires a full snapshot with crop payloads');
  const rows=snapshotRecords(normalized);
  return {version:1,database,sources:normalized.sources.map(s=>{
    const selected=rows.filter(row=>row[0]===s.id);
    return {source_id:s.id,question_count:normalized.questions.filter(q=>q.source_id===s.id).length,record_count:selected.length,sha256:fingerprint(selected)};
  })};
}
export function verifySnapshot(expected,response){
  if(expected?.version!==1||!expected.sources?.length||!Array.isArray(response)||!response.length||response.some(r=>!r.success))fail('Invalid or failed copy verification');
  const rows=response.flatMap(r=>r.results).map(r=>JSON.parse(r.record));
  const known=new Set(expected.sources.map(s=>s.source_id));
  if(rows.some(r=>!known.has(r[0])))fail('Unexpected source in copy verification');
  for(const source of expected.sources){
    const selected=rows.filter(row=>row[0]===source.source_id);
    if(selected.length!==source.record_count||fingerprint(selected)!==source.sha256)fail('Copy fingerprint mismatch: '+source.source_id);
  }
  return {...expected,verified_at:new Date().toISOString(),remote_metadata_verified:true};
}
export function registrySql(normalized,plan,receipts=[],samples=[]){
  const {databases,routes}=validateRoutes(normalized,plan),proof=new Map();
  for(const receipt of receipts){
    const db=databases.get(receipt.database?.name);
    if(!db||db.id!==receipt.database.id||receipt.remote_metadata_verified!==true||!Number.isFinite(Date.parse(receipt.verified_at)))fail('Invalid copy receipt');
    const sample=samples.find(s=>s.database===db.name&&s.server_readback===true&&s.hash_mismatches===0&&s.image_decode_failures===0&&s.sampled_sources>=receipt.sources.length);
    if(!sample)fail('Remote crop readback required before routing activation');
    for(const s of receipt.sources){
      if(!/^src_[a-f\d]{64}$/.test(s.source_id)||!/^[a-f\d]{64}$/.test(s.sha256)||!Number.isSafeInteger(s.record_count)||s.record_count<1)fail('Invalid source receipt');
      const key=db.name+'\0'+s.source_id;if(proof.has(key))fail('Duplicate copy receipt');
      proof.set(key,{...s,verified_at:receipt.verified_at,crop_readback_at:sample.checked_at});
    }
  }
  const statements=[`CREATE TABLE IF NOT EXISTS bank_source_routes(source_id TEXT PRIMARY KEY,source_json TEXT NOT NULL CHECK(json_valid(source_json)),database_name TEXT NOT NULL,database_id TEXT NOT NULL,proof_json TEXT NOT NULL CHECK(json_valid(proof_json)),updated_at TEXT NOT NULL);`];
  for(const s of normalized.sources){
    const db=databases.get(routes.get(s.id)),receipt=proof.get(db.name+'\0'+s.id);
    if(db.name!==plan.registry_database&&!receipt)fail('Verified copy required before routing activation: '+s.id);
    if(receipt&&receipt.question_count!==plan.source_routes.find(r=>r.source_id===s.id).question_count)fail('Incomplete question copy for route');
    const {local_path,...source}=s;
    const values=[s.id,JSON.stringify(source),db.name,db.id,JSON.stringify(receipt??{existing_registry_database:true}),new Date().toISOString()];
    statements.push(`INSERT INTO bank_source_routes VALUES(${values.map(sqlLiteral).join(',')}) ON CONFLICT(source_id) DO UPDATE SET source_json=excluded.source_json,database_name=excluded.database_name,database_id=excluded.database_id,proof_json=excluded.proof_json,updated_at=excluded.updated_at;`);
  }
  return statements.join('\n')+'\n';
}
async function atomicWrite(filename,value){
  const target=await privateOutput(filename),tmp=target+'.'+randomUUID()+'.tmp',handle=await open(tmp,'wx',0o600);
  try{await handle.writeFile(value);await handle.close();await rename(tmp,target);}catch(error){await handle.close().catch(()=>{});await unlink(tmp).catch(()=>{});throw error;}
}
async function main(argv){
  const json=async p=>JSON.parse((await readFile(p,'utf8')).replace(/^\uFEFF/,''));
  if(argv[0]==='--verify-expected'){
    if(argv.length!==6||argv[2]!=='--observed'||argv[4]!=='--out')fail('Expected --verify-expected FILE --observed FILE --out FILE');
    const receipt=verifySnapshot(await json(argv[1]),await json(argv[3]));
    await atomicWrite(argv[5],JSON.stringify(receipt,null,2));
    console.log(JSON.stringify({database:receipt.database.name,verified_sources:receipt.sources.length,remote_metadata_verified:true}));return;
  }
  if(argv[0]==='--registry-manifest'){
    if(argv.length!==10||argv[2]!=='--routes'||argv[4]!=='--receipts'||argv[6]!=='--samples'||argv[8]!=='--out')fail('Expected --registry-manifest FILE --routes FILE --receipts FILE --samples FILE --out FILE');
    const normalized=normalizeImport(await json(argv[1])),plan=await json(argv[3]);
    await atomicWrite(argv[9],registrySql(normalized,plan,await json(argv[5]),await json(argv[7])));
    console.log(JSON.stringify({routes:plan.source_routes.length,server_imported:false}));return;
  }
  const options={};
  for(let i=0;i<argv.length;i+=2){if(!['--manifest','--questions','--routes','--out-dir'].includes(argv[i])||!argv[i+1]||options[argv[i]])fail('Expected --manifest --questions --routes --out-dir');options[argv[i]]=argv[i+1];}
  if(Object.keys(options).length!==4)fail('Expected --manifest --questions --routes --out-dir');
  const normalized=normalizeImport(await json(options['--manifest']),await json(options['--questions'])),plan=await json(options['--routes']);
  const groups=splitImport(normalized,plan),{databases}=validateRoutes(normalized,plan);
  for(const [name,sql] of canonicalProgressSql(normalized,plan))await atomicWrite(path.join(options['--out-dir'],name+'.progress.sql'),sql);
  for(const [name,group] of groups){
    const base=path.join(options['--out-dir'],name);
    await writeImportSql(group,base+'.sql');
    await atomicWrite(base+'.expected.json',JSON.stringify(expectedSnapshot(group,databases.get(name))));
    await atomicWrite(base+'.verify.sql',verificationSql(group.sources.map(s=>s.id)));
    console.log(JSON.stringify({database:name,sources:group.sources.length,questions:group.questions.length,server_imported:false}));
  }
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href)main(process.argv.slice(2)).catch(error=>{console.error(error.message);process.exitCode=1;});

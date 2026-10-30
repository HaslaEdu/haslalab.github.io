// Real Worker/D1 contract tests with a local broker and provider stand-ins. No production requests or tokens.
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import worker from './src/index.js';
import {dispatchLabJobs,consumeLabJobs,enqueueLabJobs,LabJobDeferred} from './src/lab-jobs.js';

const sql=new DatabaseSync(':memory:');
for(const f of readdirSync(new URL('./migrations/',import.meta.url)).filter(f=>/^\d{4}_.*\.sql$/.test(f)).sort())sql.exec(readFileSync(new URL('./migrations/'+f,import.meta.url),'utf8'));
let queries=[];
const DB={prepare(query){const st=sql.prepare(query);const make=args=>({sql:query,bind:(...bound)=>make(bound),async first(){queries.push(query);return st.get(...args)||null;},async all(){queries.push(query);return{results:st.all(...args)};},async run(){return this.executeSync();},executeSync(){queries.push(query);if(st.columns().length)return{results:st.all(...args)};const r=st.run(...args);return{meta:{changes:r.changes,last_row_id:Number(r.lastInsertRowid)}};}});return make([]);},async batch(statements){sql.exec('BEGIN');try{const out=statements.map(s=>s.executeSync());sql.exec('COMMIT');return out;}catch(e){sql.exec('ROLLBACK');throw e;}}};
const pending=[],cache=new Map(),tokens={};let brokerDown=false,providerCalls=0,providerFailure=false;
const env={DB,LAB_KEEP_HOURS:'off',GEMINI_API_KEY:'local-test-key',ALLOWED_ORIGINS:'https://haslalab.org',LAB_JOBS:{async sendBatch(items){if(brokerDown)throw Error('fixture broker interruption');pending.push(...items);}}};
globalThis.caches={default:{async match(key){return cache.get(key.url)?.clone();},async put(key,response){cache.set(key.url,response.clone());}}};
const time=Math.floor(Date.now()/1000),hash=async v=>Buffer.from(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(v))).toString('base64url');
for(let id=1;id<=8;id++){tokens[id]=('local_owner_'+id).padEnd(48,'x');sql.prepare("INSERT INTO users(id,username,nickname,pw,role,created_at,exam_tokens,token_parts)VALUES(?,?,?,'unused','user',?,10,3)").run(id,'latency'+id,'Latency '+id,time);sql.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at)VALUES(?,?,?,?)').run(await hash(tokens[id]),id,time,time+3600);}
const originalFetch=globalThis.fetch;
globalThis.fetch=async(input,options={})=>{
  const url=String(input);if(/https:\/\/www\.(kms|kmo)\.or\.kr\//.test(url))return new Response('%PDF-1.7\nfixture');
  if(!url.includes(':generateContent'))throw Error('unexpected external request');
  providerCalls++;if(providerFailure){providerFailure=false;return new Response('{}',{status:503});}
  const req=JSON.parse(options.body),prompt=req.contents[0].parts.filter(p=>p.text).map(p=>p.text).join('\n');let value;
  if(prompt.startsWith('[TASK: read page]'))value={header:{task:'Q5',sheet:'answer',page:1},legible:'good',items:[{label:'proof',kind:'text',text:'Let n be an integer. Submitted proof.',crossed_out:false}]};
  else if(prompt.startsWith('[TASK: grade]'))value={items:[{id:'A',found:true,page:1,score:1,rules:[],checks_met:[],note:'submitted argument'}],feedback:[],review:null};
  else{const no=+(prompt.match(/Review ONLY problem (\d+)/)?.[1]||0),page=+(prompt.match(/\[Page (\d+);/)?.[1]||1);value={problem_no:no,score:7,confidence:.96,verdict:'valid',summary:'검토한 풀이',strengths:[],gaps:[],evidence:[{page,quote:'Let n be an integer.',note:'제출한 문장'}]};}
  return Response.json({candidates:[{content:{parts:[{text:JSON.stringify(value)}]}}],usageMetadata:{promptTokenCount:100,candidatesTokenCount:50}});
};
test.after(()=>{globalThis.fetch=originalFetch;sql.close();});
async function api(path,{id=1,body,method=body===undefined?'GET':'POST',headers={},settings=env,context}={}){
  const req=new Request('https://worker.local/api'+path,{method,headers:{...(id?{Authorization:'Bearer '+tokens[id]}:{}),...(body!==undefined?{'Content-Type':'application/json'}:{}),...headers},...(body===undefined?{}:{body:JSON.stringify(body)})});
  const response=await worker.fetch(req,settings,context);return{status:response.status,data:await response.json(),headers:response.headers};
}
async function start(id){return(await api('/lab/contest/start',{id,body:{examId:'kmo-2025-T2-s2',runId:'latency-'+id}})).data;}
async function save(sid,id,answers){return api(`/lab/contest/sessions/${sid}/text`,{id,body:{answers}});}
async function drain(settings=env){let safety=0;while(pending.length){assert.ok(++safety<100);const item=pending.shift();sql.prepare('UPDATE lab_jobs SET available_at=0 WHERE id=?').run(item.body.jobId);await worker.queue({messages:[{body:item.body,ack(){},retry(){pending.push(item);}}]},settings);}}
async function upload(code,task='Q5'){
  const response=await worker.fetch(new Request('https://worker.local/api/lab/up/pages?task='+task+'&kind=answer',{method:'PUT',headers:{'X-Lab-Token':code,'Content-Type':'image/jpeg'},body:new Uint8Array([255,216,255,224,0,16,74,70,73,70])}),env);
  return{status:response.status,data:await response.json()};
}

test('bootstrap batches only the signed-in account and keeps financial and selected answer data out of shared cache',async()=>{
  const a=await start(1);await save(a.session.id,1,{5:'Let n be an integer. Private submitted proof.'});
  const b=await start(2);await save(b.session.id,2,{5:'Another private answer.'});
  const first=await api('/lab/bootstrap?include=sessions,health,pages&id='+a.session.id);
  assert.equal(first.status,200);assert.equal(first.data.user.nickname,'Latency 1');assert.equal(first.data.tokens,10);assert.equal(first.data.parts,3);assert.equal(first.data.session.pages[0].text,'Let n be an integer. Private submitted proof.');assert.equal(first.data.active.pages.length,1);assert.ok(first.data.sessions.every(s=>s.id===a.session.id));assert.ok(first.data.sessions.every(s=>s.detail===undefined));assert.equal(first.data.health.jobs.available,true);
  assert.equal((await api('/lab/bootstrap?id='+a.session.id,{id:2})).status,404);
  const anon=await api('/lab/bootstrap?include=sessions',{id:null});assert.equal(anon.data.user,null);assert.deepEqual(anon.data.sessions,[]);
  assert.ok([...cache.keys()].every(key=>!key.includes('bootstrap')));
});

test('safe public lists share cache across accounts, skip auth DB reads, support mutation freshness and never block on cache writes',async()=>{
  cache.clear();queries=[];const queued=[];
  const r=await api('/posts?lang=ko',{context:{waitUntil:p=>queued.push(p)}});await Promise.all(queued);
  assert.equal(r.status,200);assert.ok(!queries.some(q=>q.includes('FROM sessions')));
  queries=[];const hit=await api('/posts?lang=ko',{id:2});assert.equal(hit.headers.get('X-Edge-Cache'),'hit');assert.equal(queries.length,0);
  sql.prepare("INSERT INTO posts(board,tag,lang,user_id,title,body,created_at)VALUES('free','gen','ko',1,'Fresh fixture','body',?)").run(time);
  const fresh=await api('/posts?lang=ko',{headers:{'Cache-Control':'no-cache'}});assert.equal(fresh.data.total,r.data.total+1);
  const health=await api('/health');assert.equal(health.headers.get('Cache-Control'),'public, max-age=300');assert.equal((await api('/health',{id:2})).headers.get('Cache-Control'),'public, max-age=300');
  const oldPut=caches.default.put;let release;const blocked=new Promise(resolve=>{release=resolve;});caches.default.put=async()=>blocked;
  const background=[];const result=await Promise.race([api('/boards?lang=en',{context:{waitUntil:p=>background.push(p)}}),new Promise(resolve=>setTimeout(()=>resolve(null),100))]);
  assert.ok(result,'response waits for business data, never the cache write');release();await Promise.all(background);caches.default.put=oldPut;
});

test('submit and status GETs never run AI; duplicate deliveries preserve one charge and checkpoint each written problem',async()=>{
  const a=await api('/lab/bootstrap');const sid=a.data.active.id;await save(sid,1,{5:'Let n be an integer. First proof.',6:'Let n be an integer. Second proof.'});
  const before=providerCalls,r=await api(`/lab/sessions/${sid}/submit`,{body:{}});
  assert.equal(r.status,200);assert.equal(r.data.session.status,'grading');assert.equal(r.data.queued,true);assert.equal(providerCalls,before);
  assert.equal((await api(`/lab/sessions/${sid}`)).data.session.status,'grading');await api('/lab/bootstrap?id='+sid);assert.equal(providerCalls,before);
  await api(`/lab/sessions/${sid}/submit`,{body:{}});assert.equal(pending.length,4);assert.equal(sql.prepare("SELECT COUNT(*) n FROM lab_ledger WHERE session_id=? AND reason='grade'").get(sid).n,1);
  assert.ok(pending.every(m=>Object.keys(m.body).sort().join(',')==='jobId,v'));
  const first=pending.shift(),duplicate={body:first.body,ack(){},retry(){}};
  await Promise.all([worker.queue({messages:[duplicate]},env),worker.queue({messages:[{...duplicate}]},env)]);await drain();
  const done=(await api(`/lab/sessions/${sid}`)).data.session;assert.equal(done.status,'graded');assert.equal(done.score,14);assert.equal(done.points,28);assert.equal(providerCalls-before,4);
  const saved=providerCalls;await worker.queue({messages:[duplicate]},env);assert.equal(providerCalls,saved);
});

test('queued OCR is explicit and checked in bulk; queued or wrong-owner confirmations cannot bypass recognition',async()=>{
  const a=await start(3),sid=a.session.id,p1=await upload(a.token),p2=await upload(a.token,'Q6');
  assert.equal(p1.data.ocr_status,'unpaid');const before=providerCalls;await api(`/lab/sessions/${sid}/pay`,{id:3,body:{}});assert.equal(providerCalls,before);
  const read=await api(`/lab/contest/sessions/${sid}/read`,{id:3,body:{}});assert.equal(read.data.queued,true);assert.ok(read.data.session.pages.every(p=>p.ocr_status==='queued'));assert.equal(providerCalls,before);
  const correction={pages:[{id:p1.data.id,task:'Q5',text:'Let n be an integer.'},{id:p2.data.id,task:'Q6',text:'Let n be an integer.'}]};
  assert.equal((await api(`/lab/contest/sessions/${sid}/confirm`,{id:3,body:correction})).status,409);
  assert.equal((await api(`/lab/contest/sessions/${sid}/pages/${p1.data.id}/confirm`,{id:3,body:correction.pages[0]})).status,409);
  assert.equal((await api(`/lab/sessions/${sid}/pages/${p1.data.id}`,{id:3,method:'PATCH',body:{task:'Q6'}})).status,409);
  assert.equal((await api(`/lab/sessions/${sid}/submit`,{id:3,body:{}})).data.error,'needs_confirmation');
  await drain();assert.equal(providerCalls-before,2);
  assert.equal((await api(`/lab/contest/sessions/${sid}/confirm`,{id:2,body:correction})).status,404);
  const invalid=structuredClone(correction);invalid.pages[1].task='Q99';assert.equal((await api(`/lab/contest/sessions/${sid}/confirm`,{id:3,body:invalid})).status,400);assert.equal(sql.prepare('SELECT SUM(edited) n FROM lab_pages WHERE session_id=?').get(sid).n,0);
  const confirmed=await api(`/lab/contest/sessions/${sid}/confirm`,{id:3,body:correction});assert.equal(confirmed.status,200);assert.ok(confirmed.data.session.pages.every(p=>p.confirmed));
});

test('broker interruption leaves a durable outbox, retries recover without charging again, and missing binding cannot spend tokens',async()=>{
  const a=await start(4),sid=a.session.id;await save(sid,4,{5:'Let n be an integer. Recoverable proof.'});brokerDown=true;
  const r=await api(`/lab/sessions/${sid}/submit`,{id:4,body:{}});assert.equal(r.status,200);assert.equal(r.data.session.status,'grading');assert.equal(sql.prepare("SELECT COUNT(*) n FROM lab_jobs WHERE session_id=? AND status='pending'").get(sid).n,4);
  brokerDown=false;sql.prepare('UPDATE lab_jobs SET available_at=0 WHERE session_id=?').run(sid);await dispatchLabJobs(env);providerFailure=true;await drain();
  assert.equal((await api(`/lab/sessions/${sid}`,{id:4})).data.session.status,'graded');assert.equal(sql.prepare('SELECT exam_tokens FROM users WHERE id=4').get().exam_tokens,9);assert.equal(sql.prepare("SELECT COUNT(*) n FROM lab_ledger WHERE session_id=? AND reason='grade'").get(sid).n,1);
  const b=await start(5);await save(b.session.id,5,{5:'Let n be an integer.'});const missing={...env};delete missing.LAB_JOBS;
  const rejected=await api(`/lab/sessions/${b.session.id}/pay`,{id:5,body:{},settings:missing});assert.equal(rejected.status,503);assert.equal(sql.prepare('SELECT exam_tokens FROM users WHERE id=5').get().exam_tokens,10);
});

test('dependency waits re-enqueue a delayed ID without spending the broker or provider retry budget',async()=>{
  const s=(await api('/lab/bootstrap',{id:5})).data.active;
  const rows=await enqueueLabJobs(env,[{key:'dependency-fixture',kind:'fixture',sessionId:s.id}]);pending.splice(0);
  let retried=false,acked=false;const seen=[];
  await consumeLabJobs({messages:[{body:{v:1,jobId:rows[0].id},ack(){acked=true;},retry(){retried=true;}}]},env,{async run(){throw new LabJobDeferred(20);},async statements(){return[];},async failure(){throw Error('not a failed provider call');}});
  assert.equal(acked,true);assert.equal(retried,false);assert.equal(sql.prepare('SELECT attempts FROM lab_jobs WHERE id=?').get(rows[0].id).attempts,0);assert.equal(pending[0].delaySeconds,20);assert.deepEqual(pending[0].body,{v:1,jobId:rows[0].id});pending.splice(0);
});

test('a stale worker lease can be recovered once and a duplicate completed delivery never repeats the provider step',async()=>{
  const s=(await api('/lab/bootstrap',{id:5})).data.active;
  const [job]=await enqueueLabJobs(env,[{key:'abandoned-worker-fixture',kind:'fixture',sessionId:s.id}]);pending.splice(0);
  sql.prepare("UPDATE lab_jobs SET status='running',lease_token='abandoned',lease_until=0,attempts=1 WHERE id=?").run(job.id);
  let runs=0,acks=0;const message={body:{v:1,jobId:job.id},ack(){acks++;},retry(){throw Error('expired lease must recover');}},handlers={async run(){runs++;return{ok:true};},async statements(){return[];},async failure(){throw Error('unexpected provider failure');}};
  await consumeLabJobs({messages:[message]},env,handlers);await consumeLabJobs({messages:[message]},env,handlers);
  assert.equal(runs,1);assert.equal(acks,2);assert.equal(sql.prepare('SELECT status FROM lab_jobs WHERE id=?').get(job.id).status,'done');
});

test('a failed ordinary scan with an error read object stays pending and cannot become an empty zero score',async()=>{
  const started=await api('/lab/start',{id:6,body:{comp:'ipho',year:2024,tasks:['E1'],sources:{E1:{kind:'theory'}},entry:'?c=ipho&y=2024'}}),sid=started.data.session.id;
  await api(`/lab/sessions/${sid}/pay`,{id:6,body:{}});sql.prepare("UPDATE lab_sessions SET status='scanning',scan_until=? WHERE id=?").run(time+1800,sid);
  const page=await upload(started.data.token,'E1');assert.equal(page.data.ocr_status,'queued');
  sql.prepare("UPDATE lab_pages SET ocr_status='failed',read=? WHERE id=?").run(JSON.stringify({items:[],structure_status:'failed',ocr:{error:'ocr_failed'}}),page.data.id);
  sql.prepare("UPDATE lab_jobs SET status='failed' WHERE page_id=?").run(page.data.id);pending.splice(0);
  const before=providerCalls,result=await api(`/lab/sessions/${sid}/submit`,{id:6,body:{}});assert.equal(result.data.session.status,'grading');assert.equal(providerCalls,before);
  await drain();const done=(await api(`/lab/sessions/${sid}`,{id:6})).data.session;
  assert.equal(done.status,'pending');assert.equal(done.score,null);assert.equal(done.detail.tasks.E1.why,'ocr_failed');assert.equal(providerCalls,before);
});

test('an admin may inspect another review while bootstrap balance and identity remain their own',async()=>{
  sql.prepare("UPDATE users SET role='admin',exam_tokens=2 WHERE id=8").run();
  const sid=sql.prepare('SELECT id FROM lab_sessions WHERE user_id=1').get().id;
  const record=await api('/lab/bootstrap?include=sessions&id='+sid,{id:8});
  assert.equal(record.status,200);assert.equal(record.data.user.nickname,'Latency 8');assert.equal(record.data.tokens,2);assert.equal(record.data.session.nickname,'Latency 1');assert.ok(Array.isArray(record.data.session.reviews));assert.equal(record.data.sessions.length,0);
});

test('an interruption immediately after the grading transition commit leaves every initial outbox job recoverable',async()=>{
  const a=await start(7),sid=a.session.id;await save(sid,7,{5:'Let n be an integer. Durable accepted proof.'});
  let interrupted=false;
  const interruptedEnv={...env,DB:{...DB,async batch(statements){
    const result=await DB.batch(statements);
    if(!interrupted&&statements.some(s=>s.sql?.includes("UPDATE lab_sessions SET status='grading'"))&&statements.some(s=>s.sql?.includes('INSERT OR IGNORE INTO lab_jobs'))){interrupted=true;throw Error('fixture termination after atomic commit');}
    return result;
  }}};
  const before=providerCalls,response=await api(`/lab/sessions/${sid}/submit`,{id:7,body:{},settings:interruptedEnv});
  assert.equal(response.status,500);assert.equal(interrupted,true);assert.equal(providerCalls,before);
  assert.equal(sql.prepare('SELECT status FROM lab_sessions WHERE id=?').get(sid).status,'grading');
  assert.equal(sql.prepare("SELECT COUNT(*) n FROM lab_jobs WHERE session_id=? AND kind='grade' AND status='pending'").get(sid).n,4);
  assert.equal(pending.filter(item=>sql.prepare('SELECT session_id FROM lab_jobs WHERE id=?').get(item.body.jobId)?.session_id===sid).length,0,'no broker operation was needed to retain accepted work');
  await dispatchLabJobs(env);await drain();
  const recovered=(await api(`/lab/sessions/${sid}`,{id:7})).data.session;assert.equal(recovered.status,'graded');assert.equal(recovered.score,7);
  assert.equal(sql.prepare("SELECT COUNT(*) n FROM lab_ledger WHERE session_id=? AND reason='grade'").get(sid).n,1);
});

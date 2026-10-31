// Actual Worker + SQLite + Queue with local provider fixtures only.
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import worker from './src/index.js';
import {VISION_MODELS} from './src/vision-provider.js';
import {safeOcrFailureCode,safeOcrFailureDetails} from './src/ocr-errors.js';
import {pdfiumVisualFixture} from './fixtures/pdfium-visual-fixture.mjs';
import {MODEL_TEST_EXAMS} from './src/model-test-catalog.js';
import {REG_VERSION} from './src/grading-rules.js';
const image=Uint8Array.from([255,216,255,224,0,16,74,70,73,70,1,4,7,9,29,83]);
async function fixture(providerResponse,run){
  const sql=new DatabaseSync(':memory:');
  for(const file of readdirSync(new URL('./migrations/',import.meta.url)).filter(file=>/^\d{4}_.*\.sql$/.test(file)).sort())sql.exec(readFileSync(new URL('./migrations/'+file,import.meta.url),'utf8'));
  const DB={prepare(query){const statement=sql.prepare(query),bound=args=>({query,bind:(...args)=>bound(args),async first(){return statement.get(...args)||null;},async all(){return{results:statement.all(...args)};},async run(){return this.executeSync();},executeSync(){if(statement.columns().length)return{results:statement.all(...args)};const result=statement.run(...args);return{results:[],meta:{changes:result.changes,last_row_id:Number(result.lastInsertRowid)}};}});return bound([]);},async batch(statements){sql.exec('BEGIN');try{const result=statements.map(statement=>statement.executeSync());sql.exec('COMMIT');return result;}catch(error){sql.exec('ROLLBACK');throw error;}}};
  const token='local_ocr_failure_owner'.padEnd(48,'x'),hash=Buffer.from(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(token))).toString('base64url'),at=Math.floor(Date.now()/1000);
  sql.prepare("INSERT INTO users(id,username,nickname,pw,created_at,exam_tokens)VALUES(1,'failuretest','Fixture','unused',?,5)").run(at);
  sql.prepare('INSERT INTO sessions VALUES(?,?,?,?)').run(hash,1,at,at+3600);
  const queue=[],calls=[],env={DB,DEEPSEEK_API_KEY:'fixture-secret-never-print',GEMINI_API_KEY:'fixture-gemini',LAB_KEEP_HOURS:'off',REFERENCE_PDFIUM_LOAD:async()=>pdfiumVisualFixture(),LAB_JOBS:{async sendBatch(items){queue.push(...items);}}};
  const previous={fetch:globalThis.fetch,caches:globalThis.caches};globalThis.caches={default:{async match(){},async put(){}}};
  globalThis.fetch=async(url,request)=>{
    if(String(url).startsWith('https://github.com/')||String(url).startsWith('https://haslalab.org/pdfx/'))return new Response('%PDF-1.4\nPublic canonical fixture');
    assert.match(String(url),/^https:\/\/api\.deepseek\.com\/chat\/completions$/);
    const body=JSON.parse(request.body);calls.push(body);assert.equal(body.model,'deepseek-flash');return providerResponse(body);
  };
  const api=async(path,body)=>{const response=await worker.fetch(new Request('https://ocr-fixture.local/api'+path,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+token,'Cache-Control':'no-cache',...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})}),env);return{status:response.status,data:await response.json()};};
  const drain=async()=>{let deliveries=0;while(queue.length){assert.ok(++deliveries<=64,'no unbounded paid retry loop');const item=queue.shift();sql.prepare('UPDATE lab_jobs SET available_at=0 WHERE id=?').run(item.body.jobId);await worker.queue({messages:[{body:item.body,ack(){},retry(){queue.push(item);}}]},env);}};
  try{
    const started=await api('/lab/start',{comp:'ipho',year:2025,tasks:['T1'],review:true,provider:'deepseek'});assert.equal(started.status,200);
    const sid=started.data.session.id,uploadToken=started.data.token;
    const uploaded=await worker.fetch(new Request('https://ocr-fixture.local/api/lab/up/pages?task=T1&kind=answer',{method:'PUT',headers:{'X-Lab-Token':uploadToken,'Content-Type':'image/jpeg'},body:image}),env);assert.equal(uploaded.status,200);
    assert.equal((await api('/lab/sessions/'+sid+'/pay',{provider:'deepseek'})).status,200);await drain();
    const session=await api('/lab/sessions/'+sid),phoneResponse=await worker.fetch(new Request('https://ocr-fixture.local/api/lab/up',{headers:{'X-Lab-Token':uploadToken}}),env);assert.equal(phoneResponse.status,200);
    await run({sql,env,api,sid,calls,queue,drain,respond:response=>{providerResponse=response;},session:session.data.session,phone:await phoneResponse.json()});
  }finally{Object.assign(globalThis,previous);sql.close();}
}
const jsonResponse=raw=>Response.json({model:VISION_MODELS.deepseek,choices:[{finish_reason:'stop',message:{content:JSON.stringify(raw)}}],usage:{prompt_tokens:100,completion_tokens:20,prompt_cache_hit_tokens:0,prompt_cache_miss_tokens:100}});
test('safe OCR details never expose untrusted provider messages, metadata or arbitrary stored codes',()=>{
  assert.equal(safeOcrFailureCode('sensitive arbitrary provider body'),'ocr_failed');
  assert.deepEqual(safeOcrFailureDetails({code:'vision_provider_auth',provider:'deepseek',provider_status:401,message:'secret',provider_code:'fixture-secret-never-print',raw:'student work'}),{error:'vision_provider_auth',provider_status:401,provider:'deepseek'});
  assert.deepEqual(safeOcrFailureDetails({code:'secret',provider:'someone',provider_status:999}),{error:'ocr_failed'});
});
test('DeepSeek authentication failure remains visible to its owner and QR phone with safe HTTP status',async()=>fixture(()=>new Response('fixture-secret-never-print',{status:401}),async({session,phone,sql,sid,calls})=>{
  assert.ok(calls.length>=1&&calls.length<=4);assert.equal(session.pages[0].ocr_status,'failed');assert.equal(session.pages[0].ocr_error,'vision_provider_auth');
  assert.equal(session.pages[0].ocr_provider_status,401);assert.equal(phone.pages[0].ocr_error,'vision_provider_auth');assert.equal(phone.pages[0].ocr_provider_status,401);
  assert.equal(sql.prepare("SELECT count(*) n FROM lab_ledger WHERE session_id=? AND reason='grade'").get(sid).n,1);
  assert.ok(!JSON.stringify({session,phone}).includes('fixture-secret-never-print'));
}));
test('a valid JSON object with the wrong page schema reports a schema failure, not unreadable handwriting',async()=>fixture(()=>jsonResponse({text:'Readable original answer',legible:true,items:[]}),async({session,phone,calls,sql})=>{
  assert.equal(session.pages[0].ocr_error,'vision_response_schema');assert.equal(phone.pages[0].ocr_error,'vision_response_schema');assert.equal(session.pages[0].ocr_provider_status,200);assert.equal(phone.pages[0].ocr_provider_status,200);
  assert.equal(sql.prepare("SELECT COUNT(*) n FROM lab_calls WHERE step='ocr' AND ok=1").get().n,0);
  const prompt=calls[0].messages[1].content.filter(part=>part.type==='text').map(part=>part.text).join('\n');assert.match(prompt,/JSON output format example/);assert.match(prompt,/["']legible["']:["']good["']/);
}));
test('a graph-only page with a valid OCR schema remains a successful image answer',async()=>fixture(()=>jsonResponse({text:'',legible:'good',items:[],header:{task:'T1',sheet:'answer',page:1}}),async({session,phone})=>{
  assert.equal(session.pages[0].ocr_status,'done');assert.equal(session.pages[0].text,'');assert.equal(session.pages[0].ocr_error,null);assert.equal(phone.pages[0].ocr_status,'done');
}));

function prepareRecovery(sql,sid,respond){
  sql.prepare("UPDATE lab_sessions SET status='pending',detail=? WHERE id=?").run(JSON.stringify({tasks:{T1:{status:'pending',why:'ocr_failed',score:null}}}),sid);
  const entry=MODEL_TEST_EXAMS.find(entry=>entry.comp==='ipho'&&entry.year===2025&&entry.task==='T1');
  const key=['deepseek',VISION_MODELS.deepseek,REG_VERSION,entry.solution,entry.mark||''].join(':');
  sql.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at)VALUES(?,?,?,?,?,?)').run('ipho2025','T1',key,JSON.stringify({points:2,items:[{id:'G',points:2,type:'graph',sheet:'answer',what:'Draw the requested graph.'}]}),'local-recovery-fixture',Math.floor(Date.now()/1000));
  respond(body=>{
    const prompt=body.messages[1].content.map(part=>part.text||'').join('\n');
    return jsonResponse(prompt.includes('[TASK: read page]')?{text:'',legible:'good',items:[],header:{task:'T1',sheet:'answer',page:1}}:{items:[{id:'G',found:false,page:null,label:null,score:0,rules:[],checks_met:[],note:'Requested graph is absent.'}],feedback:[],review:null});
  });
}

test('an explicit owner retry resets failed OCR atomically, queues once and retains the original photos without charging again',async()=>fixture(()=>new Response('{}',{status:503}),async({sql,env,api,sid,calls,queue,drain,respond})=>{
  prepareRecovery(sql,sid,respond);
  const completedTask={status:'graded',score:7,points:10,note:'Preserve the completed original task.'};
  sql.prepare('UPDATE lab_sessions SET tasks=?,detail=? WHERE id=?').run(JSON.stringify(['T1','T2']),JSON.stringify({tasks:{T1:{status:'pending',why:'ocr_failed',score:null},T2:completedTask}}),sid);
  const page=sql.prepare('SELECT * FROM lab_pages WHERE session_id=?').get(sid);
  for(let no=2;no<=4;no++)sql.prepare(`INSERT INTO lab_pages(session_id,no,task,kind,mime,data,ocr_status,read,created_at)VALUES(?,?,'T1','answer','image/jpeg',?,'failed',?,?)`).run(sid,no,image,page.read,page.created_at);
  const before=calls.length,balance=sql.prepare('SELECT exam_tokens,exam_half FROM users WHERE id=1').get();
  const originalSend=env.LAB_JOBS.sendBatch;
  env.LAB_JOBS.sendBatch=async items=>{
    assert.equal(sql.prepare('SELECT status FROM lab_sessions WHERE id=?').get(sid).status,'grading','queue delivery happens after committed session transition');
    assert.equal(sql.prepare("SELECT COUNT(*) n FROM lab_pages WHERE session_id=? AND ocr_status='queued' AND read IS NULL").get(sid).n,4);
    assert.equal(sql.prepare("SELECT COUNT(*) n FROM lab_jobs WHERE session_id=? AND job_key LIKE '%:manual:%'").get(sid).n,5,'OCR and grading outbox rows are durable before dispatch');
    await originalSend(items);
  };
  const responses=await Promise.all([1,2].map(()=>api('/lab/sessions/'+sid+'/retry-ocr',{provider:'deepseek'})));
  for(const response of responses){assert.equal(response.status,200);assert.equal(response.data.queued,true);assert.equal(response.data.session.status,'grading');}
  assert.equal(queue.length,5,'concurrent clicks share one manual generation');assert.equal(calls.length,before,'an explicit request only schedules stored images');
  const queued=sql.prepare('SELECT * FROM lab_pages WHERE session_id=?').all(sid);
  for(const p of queued){assert.equal(p.ocr_status,'queued');assert.equal(p.read,null);assert.deepEqual(new Uint8Array(p.data),image);}
  env.LAB_JOBS.sendBatch=originalSend;await drain();
  const done=(await api('/lab/sessions/'+sid)).data.session;assert.equal(done.status,'graded');assert.equal(done.pages.length,4);assert.ok(done.pages.every(page=>page.ocr_status==='done'));
  assert.deepEqual(done.tasks,['T1','T2']);assert.deepEqual(done.detail.tasks.T2,completedTask,'a completed other task is preserved without another grading call');
  assert.equal(calls.length,before+6,'four pages, one grade, and the Korean wording of the scheme once');assert.equal(sql.prepare("SELECT count(*) n FROM lab_ledger WHERE session_id=? AND reason='grade'").get(sid).n,1);assert.deepEqual(sql.prepare('SELECT exam_tokens,exam_half FROM users WHERE id=1').get(),balance);
  assert.equal((await api('/lab/sessions/'+sid+'/retry-ocr',{provider:'gemini'})).data.error,'provider_locked');
}));

test('admin regrade recovers failed OCR through the same committed queue before grading',async()=>fixture(()=>new Response('{}',{status:503}),async({sql,api,sid,calls,queue,drain,respond})=>{
  prepareRecovery(sql,sid,respond);sql.prepare("UPDATE users SET role='admin' WHERE id=1").run();
  const before=calls.length,response=await api('/admin/lab/'+sid,{task:'T1',regrade:true});
  assert.equal(response.status,200);assert.equal(response.data.session.status,'grading');assert.equal(queue.length,2);assert.equal(calls.length,before);
  assert.equal(sql.prepare('SELECT read FROM lab_pages WHERE session_id=?').get(sid).read,null);await drain();
  const done=(await api('/lab/sessions/'+sid)).data.session;assert.equal(done.status,'graded');assert.equal(done.pages[0].ocr_status,'done');assert.equal(calls.length,before+3,'one page, one grade, and the Korean wording of the scheme once');
  assert.equal(sql.prepare("SELECT count(*) n FROM lab_ledger WHERE session_id=? AND reason='grade'").get(sid).n,1);
}));

test('owner OCR recovery is bounded to three requests per hour and refuses missing or unpaid scans',async()=>fixture(()=>new Response('{}',{status:503}),async({sql,api,sid,calls,drain})=>{
  const failure=sql.prepare('SELECT read FROM lab_pages WHERE session_id=?').get(sid).read;
  const failAgain=()=>{
    sql.prepare("UPDATE lab_sessions SET status='pending',detail=? WHERE id=?").run(JSON.stringify({tasks:{T1:{status:'pending',why:'ocr_failed',score:null}}}),sid);
    sql.prepare("UPDATE lab_pages SET ocr_status='failed',read=? WHERE session_id=?").run(failure,sid);
  };
  for(let attempt=0;attempt<3;attempt++){
    failAgain();const response=await api('/lab/sessions/'+sid+'/retry-ocr',{provider:'deepseek'});assert.equal(response.status,200);await drain();
  }
  failAgain();const before=calls.length,blocked=await api('/lab/sessions/'+sid+'/retry-ocr',{provider:'deepseek'});
  assert.equal(blocked.status,429);assert.equal(blocked.data.error,'rate_limited');assert.equal(calls.length,before);
  sql.prepare('UPDATE lab_sessions SET charged=0 WHERE id=?').run(sid);
  assert.equal((await api('/lab/sessions/'+sid+'/retry-ocr',{provider:'deepseek'})).data.error,'not_paid');
  sql.prepare('UPDATE lab_sessions SET charged=1 WHERE id=?').run(sid);sql.prepare('DELETE FROM ratelimits WHERE k=?').run('labocrretry:'+sid);
  sql.prepare("UPDATE lab_pages SET data=X'',purged_at=? WHERE session_id=?").run(Math.floor(Date.now()/1000),sid);
  const missing=await api('/lab/sessions/'+sid+'/retry-ocr',{provider:'deepseek'});assert.equal(missing.status,410);assert.equal(missing.data.error,'scan_unavailable');assert.equal(calls.length,before);
  assert.equal(sql.prepare("SELECT count(*) n FROM lab_ledger WHERE session_id=? AND reason='grade'").get(sid).n,1);
}));

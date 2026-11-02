// node --test community/test-studio.mjs — mocks only; no provider or production credentials.
import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync,readdirSync } from 'node:fs';
import { studioRoute,inspectImage,readLimited,publicJob,STUDIO_LIMITS,cleanupStudioUser,sweepDeletedStudioUsers,deleteCommunityAccount } from './src/studio-gateway.js';
import { studioResponses,studioImageEdit,responsePayload,editPayload,purgeStudioReceipts } from './src/studio-provider.js';

const sqlite = new DatabaseSync(':memory:');
for (const file of readdirSync(new URL('./migrations/',import.meta.url)).filter(n=>n.endsWith('.sql')).sort())
  sqlite.exec(readFileSync(new URL('./migrations/'+file,import.meta.url),'utf8'));
const DB = {
  prepare(sql) { const stmt = sqlite.prepare(sql); const wrap = args => ({bind:(...bound)=>wrap(bound),
    async first(){return stmt.get(...args)||null;}, async all(){return {results:stmt.all(...args)};},
    async run(){const row=stmt.run(...args);return {meta:{changes:Number(row.changes),last_row_id:Number(row.lastInsertRowid)}};},
  }); return wrap([]); },
  async batch(statements){sqlite.exec('BEGIN');try{const out=[];for(const statement of statements)out.push(await statement.run());sqlite.exec('COMMIT');return out;}catch(error){sqlite.exec('ROLLBACK');throw error;}}
};
let counter=0; const jobs=new Map();
const env={DB,OPENAI_API_KEY:'mock-key-never-output',ALLOWED_ORIGINS:'https://haslalab.org,http://localhost:8765',
  STUDIO_ENGINE:{async fetch(request){
    const url=new URL(request.url),m=/\/internal\/jobs\/([^/]+)(?:\/(.*))?/.exec(url.pathname),id=m[1];
    assert.equal(request.headers.get('X-Studio-User-Id'),url.searchParams.get('userId'));
    if(request.method==='POST'&&!m[2]){const body=await request.json();assert.equal(body.userId,url.searchParams.get('userId'));
      assert.ok(!('OPENAI_API_KEY'in body));assert.ok(!('id'in body));assert.ok(!('expiresAt'in body));
      jobs.set(id,{id,mode:body.mode,subject:body.subject,status:'completed',stage:'done',createdAt:new Date().toISOString(),
        originalAssetId:body.image?'original':null,result:{title:'Result',subject:body.subject,problems:[{id:'p1',statement:'x+1=2',answer:'1',explanation:'Subtract 1.',figures:[],choices:[]}],review:{status:'passed',checks:[]}},
        debugPrompt:'PRIVATE SENTINEL',providerKey:'PRIVATE KEY'});}
    if(request.method==='DELETE'){jobs.delete(id);return Response.json({ok:true});}
    if(!jobs.has(id))return Response.json({error:'not_found'},{status:404});
    if(m[2]==='cancel')jobs.get(id).status='cancelled';
    return Response.json({job:jobs.get(id)});
  }}
};
async function user(){const id=++counter,token=`studio-user-token-${id}-`+'a'.repeat(32),timestamp=Math.floor(Date.now()/1000);
  sqlite.prepare('INSERT INTO users(id,username,nickname,pw,role,created_at) VALUES(?,?,?,?,?,?)').run(id,`studio${id}`,`Studio ${id}`,'unused','user',timestamp);
  const hashed=Buffer.from(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(token))).toString('base64url');
  sqlite.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)').run(hashed,id,timestamp,timestamp+3600);
  return{id,token};}
function request(path,token,init={}){const h=new Headers(init.headers);h.set('Origin','https://haslalab.org');if(token)h.set('Authorization','Bearer '+token);
  return new Request('https://api.example/api/studio'+path,{...init,headers:h});}
function form(requestId=crypto.randomUUID(),instruction='Create an elementary number theory problem.'){const f=new FormData();
  for(const[k,v]of Object.entries({requestId,mode:'generate',subject:'math',language:'en',difficulty:'similar',count:'1',instruction}))f.set(k,v);return f;}
async function create(who,body=form()){const response=await studioRoute(request('/jobs',who.token,{method:'POST',body}),env);return [response,await response.json()];}
function receipt(who,id=crypto.randomUUID()){const t=Math.floor(Date.now()/1000);
  sqlite.prepare("INSERT INTO studio_jobs(id,user_id,request_key,fingerprint,mode,subject,status,created_at,updated_at,expires_at) VALUES(?,?,?,?,?,?,'queued',?,?,?)")
    .run(id,who.id,crypto.randomUUID(),'receipt','generate','math',t,t,t+3600);return id;}
function payload(id,stage='read'){return{model:'gpt-6.1-terra',input:[{role:'user',content:[{type:'input_text',text:'Synthetic test'}]}],
  text:{format:{type:'json_schema',name:'test',strict:true,schema:{type:'object',properties:{x:{type:'number'}},required:['x'],additionalProperties:false}}},
  metadata:{studio_job_id:id,studio_stage:stage,studio_attempt:0},max_output_tokens:1000,store:false};}

test('authentication, origin checks, missing provider binding and public capabilities',async()=>{
  assert.equal((await studioRoute(request('/jobs'),env)).status,401);
  const foreign=new Request('https://api.example/api/studio/capabilities',{headers:{Origin:'https://evil.invalid'}});
  assert.equal((await studioRoute(foreign,env)).status,403);
  const cap=await studioRoute(request('/capabilities'),env);assert.equal((await cap.json()).maxImageBytes,4*1024*1024);
  const who=await user();assert.equal((await studioRoute(request('/jobs',who.token),{...env,STUDIO_ENGINE:null})).status,503);
});
test('jobs are owner-bound, redact internal fields and support deletion',async()=>{
  const a=await user(),b=await user(),[response,body]=await create(a);
  assert.equal(response.status,202);assert.equal(body.job.status,'completed');assert.ok(!JSON.stringify(body).includes('PRIVATE'));
  assert.equal((await studioRoute(request('/jobs/'+body.job.id,b.token),env)).status,404);
  assert.equal((await studioRoute(request('/jobs/'+body.job.id,a.token),env)).status,200);
  assert.equal((await studioRoute(request('/jobs/'+body.job.id,a.token,{method:'DELETE'}),env)).status,200);
  assert.equal((await studioRoute(request('/jobs/'+body.job.id,a.token),env)).status,404);
});
test('idempotency is per user, detects changed payload and reuses one reservation',async()=>{
  const a=await user(),key=crypto.randomUUID(),first=await create(a,form(key)),second=await create(a,form(key));
  assert.equal(first[1].job.id,second[1].job.id);assert.equal(second[1].reused,true);
  assert.equal((await create(a,form(key,'A different problem request.')))[0].status,409);
  assert.equal(sqlite.prepare('SELECT COUNT(*) n FROM studio_jobs WHERE user_id=?').get(a.id).n,1);
});

test('disabling new AI work preserves existing result access, cancellation and deletion',async()=>{
  const a=await user(),[,body]=await create(a),paused={...env,OPENAI_API_KEY:undefined,STUDIO_ENABLED:'false'};
  assert.equal((await studioRoute(request('/jobs',a.token,{method:'POST',body:form()}),paused)).status,503);
  assert.equal((await studioRoute(request('/jobs/'+body.job.id,a.token),paused)).status,200);
  assert.equal((await studioRoute(request('/jobs/'+body.job.id+'/cancel',a.token,{method:'POST'}),paused)).status,200);
  assert.equal((await studioRoute(request('/jobs/'+body.job.id,a.token,{method:'DELETE'}),paused)).status,200);
});
test('daily reservation is atomically bounded under parallel submissions',async()=>{
  const a=await user();const results=await Promise.all(Array.from({length:8},()=>create(a)));
  assert.equal(results.filter(([r])=>r.status===202).length,3); // completed mock jobs release concurrent slots
  assert.ok(results.some(([r])=>r.status===429));
  for(const row of sqlite.prepare('SELECT * FROM studio_jobs WHERE user_id=?').all(a.id))await studioRoute(request('/jobs/'+row.id,a.token),env);
  assert.equal(sqlite.prepare('SELECT COUNT(*) n FROM studio_jobs WHERE user_id=?').get(a.id).n,3);
  assert.equal((await create(a))[0].status,429);
});
test('image magic, MIME and decompression dimensions are checked before private processing',()=>{
  const png=new Uint8Array(33);png.set([137,80,78,71,13,10,26,10]);png.set(new TextEncoder().encode('IHDR'),12);
  const v=new DataView(png.buffer);v.setUint32(16,640);v.setUint32(20,480);assert.equal(inspectImage(png,'image/png').width,640);
  assert.throws(()=>inspectImage(png,'image/jpeg'));v.setUint32(16,20000);assert.throws(()=>inspectImage(png,'image/png'));
  assert.throws(()=>inspectImage(new TextEncoder().encode('<svg onload="alert(1)">'),'image/svg+xml'));
});
test('chunked bodies are bounded even without Content-Length',async()=>{
  const stream=new ReadableStream({start(c){c.enqueue(new Uint8Array(7));c.enqueue(new Uint8Array(7));c.close();}});
  const r=new Request('https://example.invalid',{method:'POST',body:stream,duplex:'half'});
  await assert.rejects(()=>readLimited(r,10),e=>e.code==='body_too_large');
});
test('public results use a projection and raw error messages are never reflected',()=>{
  const job=publicJob({id:'test',mode:'generate',status:'failed',error:{code:'SECRET_PROVIDER_TOKEN',message:'secret'},debug:'private',result:{title:'T',hidden:'PRIVATE',problems:[]}});
  assert.ok(!JSON.stringify(job).includes('SECRET'));assert.ok(!JSON.stringify(job).includes('PRIVATE'));
});
test('provider payloads deny remote images, tools, arbitrary models and persistent storage',()=>{
  const id=crypto.randomUUID(),p=payload(id);assert.equal(responsePayload({...p,store:true},env).store,false);
  assert.throws(()=>responsePayload({...p,tools:[{type:'web_search'}]},env));
  assert.throws(()=>responsePayload({...p,model:'arbitrary-model'},env));
  assert.throws(()=>responsePayload({...p,input:[{role:'user',content:[{type:'input_image',image_url:'https://evil.invalid/steal'}]}]},env));
  const edit=editPayload({prompt:'Restore labels.',image:{mime:'image/png',base64:'AAAA'}},env);
  assert.equal(edit.size,'auto');assert.equal(edit.quality,'high');assert.equal(edit.n,1);assert.ok(!('input_fidelity'in edit));
});
test('provider receipts prevent duplicate calls and never return prompt or key echoes',async()=>{
  const a=await user(),id=receipt(a),originalFetch=globalThis.fetch;let calls=0;
  globalThis.fetch=async(url,init)=>{calls++;assert.equal(url,'https://api.openai.com/v1/responses');assert.equal(JSON.parse(init.body).store,false);
    return Response.json({id:'resp-test',status:'completed',output:[{type:'message',content:[{type:'output_text',text:'{"x":1}'}]}],
      instructions:'PRIVATE PROMPT',input:'PRIVATE INPUT',usage:{input_tokens:10,output_tokens:5}});};
  try{const args={userId:String(a.id),jobId:id,request:payload(id)};const first=await studioResponses(env,args),again=await studioResponses(env,args);
    assert.equal(calls,1);assert.deepEqual(first,again);assert.ok(!JSON.stringify(first).includes('PRIVATE'));
    await assert.rejects(()=>studioResponses(env,{...args,userId:String(a.id+1000)}),e=>e.code==='job_inactive');
  }finally{globalThis.fetch=originalFetch;}
});
test('provider errors are sanitized and failed uncertain requests are not replayed',async()=>{
  const a=await user(),id=receipt(a),originalFetch=globalThis.fetch;let calls=0;
  globalThis.fetch=async()=>{calls++;return new Response('SECRET provider stack and key',{status:401});};
  try{const args={userId:String(a.id),jobId:id,request:payload(id)};
    await assert.rejects(()=>studioResponses(env,args),e=>e.message==='provider_access_denied');
    await assert.rejects(()=>studioResponses(env,args),e=>e.message==='provider_request_failed');assert.equal(calls,1);
  }finally{globalThis.fetch=originalFetch;}
});
test('image provider replay chunks survive large responses and only one image call is allowed',async()=>{
  const a=await user(),id=receipt(a),originalFetch=globalThis.fetch,b64='AAAA'.repeat(20000);let calls=0;
  globalThis.fetch=async()=>{calls++;return Response.json({data:[{b64_json:b64}],revised_prompt:'PRIVATE',size:'1024x1024'});};
  try{const args={userId:String(a.id),jobId:id,prompt:'Restore the synthetic diagram.',image:{mime:'image/png',base64:'AAAA'},requestId:id+':restore'};
    assert.equal((await studioImageEdit(env,args)).data[0].b64_json,b64);assert.equal((await studioImageEdit(env,args)).data[0].b64_json,b64);assert.equal(calls,1);
  }finally{globalThis.fetch=originalFetch;}
});
test('expired replay data is purged and expired jobs cannot call providers',async()=>{
  const a=await user(),id=receipt(a);sqlite.prepare('UPDATE studio_jobs SET expires_at=0 WHERE id=?').run(id);
  await purgeStudioReceipts(env);assert.equal(sqlite.prepare('SELECT id FROM studio_jobs WHERE id=?').get(id),undefined);
  await assert.rejects(()=>studioResponses(env,{userId:String(a.id),jobId:id,request:payload(id)}),e=>e.code==='job_inactive');
});

test('successful account deletion purges Studio for ordinary users without the preview admin gate',async()=>{
  const a=await user(),b=await user(),[,body]=await create(a),keep=receipt(b),id=body.job.id;
  // Also erase expired jobs: DO assets can survive until their expiry alarm runs.
  sqlite.prepare('UPDATE studio_jobs SET expires_at=1 WHERE id=?').run(id);
  const t=Math.floor(Date.now()/1000);
  sqlite.prepare("INSERT INTO studio_provider_calls(job_id,call_key,kind,status,result_json,created_at,updated_at) VALUES(?,'test','responses','completed','private',?,?)").run(id,t,t);
  sqlite.prepare("INSERT INTO studio_provider_chunks(job_id,call_key,part,value) VALUES(?,'test',0,'private image')").run(id);
  const seen=[],accountEnv={...env,STUDIO_ACCESS:'admin'};
  const originalResponse=Response.json({ok:true},{headers:{'X-Account-Handler':'preserved'}});
  const communityFetch=async request=>{
    seen.push(request.method);assert.equal(new URL(request.url).pathname,'/api/me');
    assert.equal(request.headers.get('Authorization'),'Bearer '+a.token);
    if(request.method==='GET')return Response.json({user:{id:a.id,role:'user'}});
    sqlite.prepare('UPDATE users SET deleted=1 WHERE id=?').run(a.id);
    sqlite.prepare('DELETE FROM sessions WHERE user_id=?').run(a.id);
    return originalResponse;
  };
  const response=await deleteCommunityAccount(new Request('https://api.example/api/me',{method:'DELETE',headers:{Authorization:'Bearer '+a.token}}),accountEnv,{},communityFetch);
  assert.equal(response,originalResponse);assert.deepEqual(seen,['GET','DELETE']);assert.equal(response.headers.get('X-Account-Handler'),'preserved');
  assert.equal(sqlite.prepare('SELECT COUNT(*) n FROM studio_jobs WHERE user_id=?').get(a.id).n,0);
  assert.equal(sqlite.prepare('SELECT COUNT(*) n FROM studio_provider_calls WHERE job_id=?').get(id).n,0);
  assert.equal(sqlite.prepare('SELECT COUNT(*) n FROM studio_provider_chunks WHERE job_id=?').get(id).n,0);
  assert.ok(!jobs.has(id));assert.ok(sqlite.prepare('SELECT id FROM studio_jobs WHERE id=?').get(keep));
});
test('failed account deletion leaves Studio content intact; failed DO deletion retries through the sweep',async()=>{
  const a=await user(),[,body]=await create(a),id=body.job.id;
  const failed=await deleteCommunityAccount(new Request('https://api.example/api/me',{method:'DELETE'}),env,{},async request=>request.method==='GET'?Response.json({user:{id:a.id}}):Response.json({error:'denied'},{status:403}));
  assert.equal(failed.status,403);assert.ok(jobs.has(id));
  sqlite.prepare('UPDATE users SET deleted=1 WHERE id=?').run(a.id);
  await cleanupStudioUser({...env,STUDIO_ENGINE:{async fetch(){throw new Error('offline');}}},a.id);
  assert.equal(sqlite.prepare('SELECT status FROM studio_jobs WHERE id=?').get(id).status,'deleted');assert.ok(jobs.has(id));
  await sweepDeletedStudioUsers(env);
  assert.equal(sqlite.prepare('SELECT id FROM studio_jobs WHERE id=?').get(id),undefined);assert.ok(!jobs.has(id));
});
test('an account deleted between authentication and reservation cannot create a new Studio job',async()=>{
  const a=await user();
  const raceDB={...DB,prepare(sql){const statement=DB.prepare(sql);if(!/INSERT OR IGNORE INTO studio_jobs/.test(sql))return statement;
    return{...statement,bind(...args){const bound=statement.bind(...args);return{...bound,async run(){sqlite.prepare('UPDATE users SET deleted=1 WHERE id=?').run(a.id);return bound.run();}};}};}};
  const response=await studioRoute(request('/jobs',a.token,{method:'POST',body:form()}),{...env,DB:raceDB});
  assert.notEqual(response.status,202);assert.equal(sqlite.prepare('SELECT COUNT(*) n FROM studio_jobs WHERE user_id=?').get(a.id).n,0);
});
test('in-flight text and image responses cannot repopulate receipts after account deletion',async()=>{
  const originalFetch=globalThis.fetch;
  try{for(const kind of ['responses','image_edit']){
    const a=await user(),id=receipt(a);let release,started;const ready=new Promise(resolve=>{started=resolve;});
    globalThis.fetch=()=>{started();return new Promise(resolve=>{release=resolve;});};
    const pending=kind==='responses'?studioResponses(env,{userId:String(a.id),jobId:id,request:payload(id)}):studioImageEdit(env,{userId:String(a.id),jobId:id,prompt:'Preserve labels.',image:{mime:'image/png',base64:'AAAA'},requestId:id+':restore'});
    await ready;sqlite.prepare('UPDATE users SET deleted=1 WHERE id=?').run(a.id);await cleanupStudioUser(env,a.id);
    release(Response.json(kind==='responses'?{status:'completed',output:[{content:[{type:'output_text',text:'{"x":1}'}]}]}:{data:[{b64_json:'AAAA'.repeat(20000)}]}));
    await assert.rejects(()=>pending,error=>error.code==='job_inactive');
    assert.equal(sqlite.prepare('SELECT COUNT(*) n FROM studio_provider_calls WHERE job_id=?').get(id).n,0);
    assert.equal(sqlite.prepare('SELECT COUNT(*) n FROM studio_provider_chunks WHERE job_id=?').get(id).n,0);
  }}finally{globalThis.fetch=originalFetch;}
});

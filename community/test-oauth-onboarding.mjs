// Real Worker, SQLite and mocked providers only. Never authenticates a real user.
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import worker from './src/index.js';
import {studioUser} from './src/studio-gateway.js';
const origin='https://haslalab.org',gateway='https://haslalab-community-edge.haslalab.workers.dev';
const b64=bytes=>Buffer.from(bytes).toString('base64url');
function setup(){
 const sql=new DatabaseSync(':memory:');for(const name of readdirSync(new URL('./migrations/',import.meta.url)).filter(name=>/^\d{4}_.*\.sql$/.test(name)).sort())sql.exec(readFileSync(new URL('./migrations/'+name,import.meta.url),'utf8'));
 const DB={prepare(query){const statement=sql.prepare(query),make=args=>({bind:(...values)=>make(values),async first(){return statement.get(...args)||null},async all(){return{results:statement.all(...args)}},async run(){return this.execute()},execute(){if(statement.columns().length)return{results:statement.all(...args),meta:{changes:sql.prepare('SELECT changes() n').get().n}};const out=statement.run(...args);return{results:[],meta:{changes:Number(out.changes),last_row_id:Number(out.lastInsertRowid)}}}});return make([])},async batch(statements){sql.exec('BEGIN');try{const out=statements.map(s=>s.execute());sql.exec('COMMIT');return out}catch(e){sql.exec('ROLLBACK');throw e}}};
 const env={DB,ALLOWED_ORIGINS:origin+',https://physleague.kr',GOOGLE_CLIENT_ID:'fixture-client',GOOGLE_CLIENT_SECRET:'fixture-secret',OAUTH_MOCK_BASE:'https://provider.invalid'};
 const api=async(method,path,body,token)=>{const r=await worker.fetch(new Request(gateway+'/api'+path,{method,headers:{Origin:origin,'CF-Connecting-IP':'192.0.2.88',...(body?{'Content-Type':'application/json'}:{}),...(token?{Authorization:'Bearer '+token}:{})},...(body?{body:JSON.stringify(body)}:{})}),env,{waitUntil(){}});return{status:r.status,data:await r.json()}};
 const get=path=>worker.fetch(new Request(path.startsWith('http')?path:gateway+path,{headers:{Origin:origin,'CF-Connecting-IP':'192.0.2.88'}}),env,{waitUntil(){}});
 const oauth=async(start,sub='new-social')=>{const original=globalThis.fetch;globalThis.fetch=async input=>{const url=new URL(input);assert.equal(url.origin,'https://provider.invalid');return Response.json(url.pathname.includes('token')?{access_token:'fixture-access'}:{sub,name:'소셜 사용자'})};try{const started=await get(start);assert.equal(started.status,302);const state=new URL(started.headers.get('Location')).searchParams.get('state');const finished=await get('/api/oauth/google/callback?state='+state+'&code=fixture');assert.equal(finished.status,302);assert.equal((await get('/api/oauth/google/callback?state='+state+'&code=fixture')).status,400);return new URL(finished.headers.get('Location'))}finally{globalThis.fetch=original}};
 return{sql,env,api,get,oauth,close(){sql.close()}};
}
test('social registration requires a unique chosen username before protected API use; existing admin identity is retained',async()=>{
 const s=setup();try{
  assert.equal((await s.api('POST','/signup',{nickname:'No ID',password:'fixture-password'})).data.error,'bad_username');
  const finish=await s.oauth('/api/oauth/google/start?return='+encodeURIComponent(origin+'/'));
  const code=new URLSearchParams(finish.hash.split('?')[1]).get('c');const signed=await s.api('POST','/oauth/redeem',{code});
  assert.equal(signed.status,200);assert.equal(signed.data.user.username,null);assert.equal(signed.data.user.username_required,true);const token=signed.data.token;
  assert.equal((await s.api('POST','/oauth/redeem',{code})).status,400);
  assert.equal((await s.api('GET','/me/security',undefined,token)).data.error,'username_required');
  await assert.rejects(studioUser(new Request(gateway+'/api/studio/capabilities',{headers:{Authorization:'Bearer '+token}}),s.env),error=>error.code==='username_required');
  assert.equal((await s.api('POST','/me/username',{username:'x'},token)).data.error,'bad_username');
  s.sql.prepare('INSERT INTO users(username,nickname,pw,created_at) VALUES(?,?,NULL,?)').run('taken_name','Taken name',Math.floor(Date.now()/1000));
  assert.equal((await s.api('POST','/me/username',{username:'TAKEN_NAME'},token)).data.error,'username_taken');
  const claimed=await s.api('POST','/me/username',{username:'chosen_name'},token);assert.equal(claimed.status,200);assert.equal(claimed.data.user.username,'chosen_name');assert.equal(claimed.data.user.username_required,undefined);
  assert.equal((await s.api('GET','/me/security',undefined,token)).status,200);
  assert.equal((await s.api('POST','/me/username',{username:'renamed_id'},token)).data.error,'username_already_set');
  const row=s.sql.prepare("INSERT INTO users(username,nickname,role,created_at) VALUES('g_QFAlJRmIyg','관리자','admin',?)").run(Math.floor(Date.now()/1000));const id=Number(row.lastInsertRowid);
  s.sql.prepare("INSERT INTO identities(provider,sub,user_id,created_at) VALUES('google','legacy-admin',?,?)").run(id,Math.floor(Date.now()/1000));
  const legacyFinish=await s.oauth('/api/oauth/google/start?return='+encodeURIComponent(origin+'/'),'legacy-admin');
  const legacy=await s.api('POST','/oauth/redeem',{code:new URLSearchParams(legacyFinish.hash.split('?')[1]).get('c')});assert.equal(legacy.data.user.id,id);assert.equal(legacy.data.user.role,'admin');assert.equal(legacy.data.user.username,'g_QFAlJRmIyg');assert.equal(legacy.data.user.username_required,undefined);
 }finally{s.close()}
});
test('desktop handoff accepts only fixed loopback callbacks and proof-bound, one-use codes',async()=>{
 const s=setup();try{
  const verifier='v'.repeat(64),state='s'.repeat(43),challenge=b64(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier)));
  const body={provider:'google',code_challenge:challenge,state,redirect_uri:'http://127.0.0.1:43210/oauth/callback'};
  for(const redirect_uri of ['https://evil.example/oauth/callback','http://localhost:43210/oauth/callback','http://127.0.0.1:80/oauth/callback','http://127.0.0.1:43210/other','http://127.0.0.1:43210/oauth/callback?next=evil'])assert.equal((await s.api('POST','/oauth/desktop/start',{...body,redirect_uri})).data.error,'bad_desktop_request');
  const start=await s.api('POST','/oauth/desktop/start',body);assert.equal(start.status,200);assert.equal(start.data.expires_in,300);const authorize=new URL(start.data.authorize_url);assert.equal(authorize.origin,gateway);assert.equal(authorize.pathname,'/api/oauth/google/start');assert.deepEqual([...authorize.searchParams.keys()],['desktop']);
  const finish=await s.oauth(authorize.href,'desktop-new');assert.equal(finish.origin,'http://127.0.0.1:43210');assert.equal(finish.pathname,'/oauth/callback');assert.equal(finish.hash,'');assert.equal(finish.searchParams.get('state'),state);assert.deepEqual([...finish.searchParams.keys()],['state','code']);
  assert.equal((await s.get(authorize.href)).status,400);
  const code=finish.searchParams.get('code');assert.equal((await s.api('POST','/oauth/redeem',{code})).data.error,'bad_code');
  assert.equal((await s.api('POST','/oauth/desktop/exchange',{code,code_verifier:'w'.repeat(64),state})).data.error,'bad_code');
  assert.equal((await s.api('POST','/oauth/desktop/exchange',{code,code_verifier:verifier,state:'q'.repeat(43)})).data.error,'bad_code');
  const answers=await Promise.all([s.api('POST','/oauth/desktop/exchange',{code,code_verifier:verifier,state}),s.api('POST','/oauth/desktop/exchange',{code,code_verifier:verifier,state})]);assert.deepEqual(answers.map(x=>x.status).sort(),[200,400]);const user=answers.find(x=>x.status===200).data.user;assert.equal(user.username_required,true);assert.equal(user.username,null);
  const row=s.sql.prepare('SELECT * FROM oauth_desktop_intents').get();assert.notEqual(row.code_hash,code);assert.notEqual(row.intent_hash,authorize.searchParams.get('desktop'));assert.equal(row.code_verifier,undefined);assert.ok(row.used_at);
 }finally{s.close()}
});
test('web OAuth requires an initiated proof, matching state and a trusted HTTPS return; it cannot redeem as desktop or legacy',async()=>{
 const s=setup();try{
  const verifier='w'.repeat(64),state='s'.repeat(43),challenge=b64(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier)));
  const body={provider:'google',code_challenge:challenge,state,redirect_uri:'https://physleague.kr/'};
  for(const redirect_uri of ['https://evil.example/','http://127.0.0.1:43210/oauth/callback','https://physleague.kr/other'])assert.equal((await s.api('POST','/oauth/web/start',{...body,redirect_uri})).status,400);
  const start=await s.api('POST','/oauth/web/start',body);assert.equal(start.status,200);const finish=await s.oauth(start.data.authorize_url,'web-new');assert.equal(finish.origin,'https://physleague.kr');assert.equal(finish.search,'');assert.ok(finish.hash.startsWith('#/oauth?'));const proof=new URLSearchParams(finish.hash.split('?')[1]),code=proof.get('c');assert.equal(proof.get('state'),state);
  assert.equal((await s.api('POST','/oauth/redeem',{code})).status,400);
  assert.equal((await s.api('POST','/oauth/desktop/exchange',{code,code_verifier:verifier,state})).status,400);
  assert.equal((await s.api('POST','/oauth/web/exchange',{code,state})).status,400);
  assert.equal((await s.api('POST','/oauth/web/exchange',{code,code_verifier:verifier,state:'z'.repeat(43)})).status,400);
  const result=await s.api('POST','/oauth/web/exchange',{code,code_verifier:verifier,state});assert.equal(result.status,200);assert.equal(result.data.user.username_required,true);assert.equal((await s.api('POST','/oauth/web/exchange',{code,code_verifier:verifier,state})).status,400);
 }finally{s.close()}
});
test('handoff JSON APIs enforce allowed Origin, JSON type and streaming body limit',async()=>{
 const s=setup();try{
  for(const headers of [{Origin:'https://evil.example','Content-Type':'application/json'},{Origin:origin,'Content-Type':'text/plain'},{'Content-Type':'application/json'}]){const response=await worker.fetch(new Request(gateway+'/api/oauth/desktop/start',{method:'POST',headers,body:'{}'}),s.env,{waitUntil(){}});assert.equal(response.status,403)}
  const response=await worker.fetch(new Request(gateway+'/api/oauth/desktop/start',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:JSON.stringify({extra:'x'.repeat(9000)})}),s.env,{waitUntil(){}});assert.equal(response.status,413);
 }finally{s.close()}
});

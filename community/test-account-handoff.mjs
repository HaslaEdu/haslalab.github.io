// Local SQLite and real Worker only. No browser, provider, mail or live account.
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import worker from './src/index.js';
const SOURCE='https://physleague.kr',TARGET='https://haslaedu.haslalab.workers.dev',GATEWAY='https://haslalab-community-edge.haslalab.workers.dev';
const base64=bytes=>Buffer.from(bytes).toString('base64url'),digest=async value=>base64(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)));
function fixture(){
 const sql=new DatabaseSync(':memory:');for(const name of readdirSync(new URL('./migrations/',import.meta.url)).filter(name=>/^\d{4}_.*\.sql$/.test(name)).sort())sql.exec(readFileSync(new URL('./migrations/'+name,import.meta.url),'utf8'));
 const DB={prepare(query){const statement=sql.prepare(query),make=args=>({bind:(...values)=>make(values),async first(){return statement.get(...args)||null},async all(){return{results:statement.all(...args)}},async run(){return this.execute()},execute(){if(statement.columns().length)return{results:statement.all(...args),meta:{changes:sql.prepare('SELECT changes() n').get().n}};const out=statement.run(...args);return{results:[],meta:{changes:Number(out.changes),last_row_id:Number(out.lastInsertRowid)}}}});return make([])},async batch(statements){sql.exec('BEGIN');try{const out=statements.map(s=>s.execute());sql.exec('COMMIT');return out}catch(error){sql.exec('ROLLBACK');throw error}}};
 const env={DB,ALLOWED_ORIGINS:'https://haslalab.org,'+SOURCE+','+TARGET+',https://www.physleague.kr'};
 const api=async(path,{body,token,method=body?'POST':'GET',origin=SOURCE,headers={}}={})=>{const response=await worker.fetch(new Request(GATEWAY+'/api'+path,{method,headers:{Origin:origin,'CF-Connecting-IP':'192.0.2.90',...(body?{'Content-Type':'application/json'}:{}),...(token?{Authorization:'Bearer '+token}:{}),...headers},...(body?{body:typeof body==='string'?body:JSON.stringify(body)}:{})}),env,{waitUntil(){}});return{status:response.status,data:await response.json(),headers:response.headers}};
 const signup=async(name='handoff_owner')=>api('/signup',{body:{username:name,nickname:name,password:'local-fixture-password',consent:{terms:true,privacy:true,age14:true}}});
 const start=async(token,{state='s'.repeat(43),verifier='v'.repeat(43),source=SOURCE,target=TARGET}={})=>{const body={source_origin:source,target_origin:target,code_challenge:await digest(verifier),state};return{result:await api('/auth/handoff/start',{token,body}),state,verifier,target}};
 const exchange=(flow,token,patch={})=>api('/auth/handoff/exchange',{token,origin:TARGET,body:{code:flow.result.data.code,code_verifier:flow.verifier,state:flow.state,target_origin:flow.target,...patch}});
 return{sql,api,signup,start,exchange,close(){sql.close()}};
}
test('a guest target receives a different server session with the source age and expiry; proofs are digest-only',async()=>{
 const f=fixture();try{
  const signed=await f.signup(),source=signed.data.token,t=Math.floor(Date.now()/1000),created=t-3600,expires=t+900;
  f.sql.prepare('UPDATE sessions SET created_at=?,expires_at=?').run(created,expires);
  f.sql.exec('DROP TABLE account_session_handoffs'); // First live use can create its additive schema safely.
  const flow=await f.start(source);assert.equal(flow.result.status,200);assert.equal(flow.result.data.expires_in,60);assert.match(flow.result.data.code,/^[A-Za-z0-9_-]{43}$/);
  const row=f.sql.prepare('SELECT * FROM account_session_handoffs').get();assert.notEqual(row.code_hash,flow.result.data.code);assert.notEqual(row.source_session_hash,source);assert.equal(row.code_verifier,undefined);
  const target=await f.exchange(flow);assert.equal(target.status,200);assert.notEqual(target.data.token,source);assert.equal(target.data.user.id,signed.data.user.id);
  const stored=f.sql.prepare('SELECT * FROM sessions WHERE token_hash=?').get(await digest(target.data.token));assert.equal(stored.created_at,created);assert.equal(stored.expires_at,expires);
  const context=await f.api('/me/auth-context',{token:target.data.token,origin:TARGET});assert.equal(context.status,200);assert.equal(context.data.recent_login,false);assert.equal(context.headers.get('Cache-Control'),'no-store');
  f.sql.prepare("INSERT INTO identities(provider,sub,user_id,created_at) VALUES('google','fixture-source-sub',?,?)").run(signed.data.user.id,t);assert.equal((await f.api('/me/identity-proof?provider=google',{token:target.data.token,origin:TARGET})).data.error,'recent_login_required');
  assert.equal((await f.exchange(flow)).status,400);assert.equal(f.sql.prepare('SELECT count(*) n FROM sessions').get().n,2);
 }finally{f.close()}
});
test('start requires authentication and exact allowed origins, JSON and a bounded body',async()=>{
 const f=fixture();try{
  const signed=await f.signup();assert.equal((await f.start(undefined)).result.status,401);
  for(const source of ['https://evil.example','https://physleague.kr/','http://physleague.kr'])assert.equal((await f.start(signed.data.token,{source})).result.status,400);
  for(const target of ['https://evil.example','https://physleague.kr:8443','https://physleague.kr/nonsul/'])assert.equal((await f.start(signed.data.token,{target})).result.status,400);
  const body={source_origin:SOURCE,target_origin:TARGET,code_challenge:'c'.repeat(43),state:'s'.repeat(43)};
  for(const headers of [{Origin:'https://evil.example'},{Origin:''},{'Content-Type':'text/plain'}])assert.equal((await f.api('/auth/handoff/start',{token:signed.data.token,body,headers})).status,403);
  assert.equal((await f.api('/auth/handoff/start',{token:signed.data.token,body:JSON.stringify({extra:'x'.repeat(9000)})})).status,413);
  assert.equal(f.sql.prepare('SELECT count(*) n FROM account_session_handoffs').get().n,0);
 }finally{f.close()}
});
test('wrong proof, state and audience cannot consume or exchange the code; OAuth codes are a separate namespace',async()=>{
 const f=fixture();try{
  const signed=await f.signup(),flow=await f.start(signed.data.token);
  for(const patch of [{code_verifier:'w'.repeat(43)},{state:'q'.repeat(43)},{target_origin:'https://www.physleague.kr'}])assert.equal((await f.exchange(flow,undefined,patch)).status,400);
  assert.equal((await f.api('/oauth/redeem',{body:{code:flow.result.data.code}})).status,400);
  const oauthCode='o'.repeat(43);f.sql.prepare('INSERT INTO oauth_codes(code_hash,user_id,fresh,created_at) VALUES(?,?,0,?)').run(await digest(oauthCode),signed.data.user.id,Math.floor(Date.now()/1000));
  assert.equal((await f.exchange(flow,undefined,{code:oauthCode})).status,400);
  assert.equal(f.sql.prepare('SELECT count(*) n FROM sessions').get().n,1);assert.equal(f.sql.prepare('SELECT used_at FROM account_session_handoffs').get().used_at,null);
  assert.equal((await f.exchange(flow)).status,200);
 }finally{f.close()}
});
test('source logout, expiry, deletion and the sixty-second code deadline revoke unused handoffs',async()=>{
 for(const scenario of ['logout','expiry','delete','deadline']){const f=fixture();try{
  const signed=await f.signup(),flow=await f.start(signed.data.token),t=Math.floor(Date.now()/1000);
  if(scenario==='logout')await f.api('/logout',{token:signed.data.token,body:{}});
  if(scenario==='expiry')f.sql.prepare('UPDATE sessions SET expires_at=?').run(t-1);
  if(scenario==='delete')f.sql.prepare('UPDATE users SET deleted=1').run();
  if(scenario==='deadline')f.sql.prepare('UPDATE account_session_handoffs SET created_at=?').run(t-61);
  const before=f.sql.prepare('SELECT count(*) n FROM sessions').get().n;assert.equal((await f.exchange(flow)).status,400,scenario);assert.equal(f.sql.prepare('SELECT count(*) n FROM sessions').get().n,before);
 }finally{f.close()}}
});
test('an already signed-in target is preserved, and a different target account is never replaced',async()=>{
 const f=fixture();try{
  const signed=await f.signup(),other=await f.signup('other_handoff'),flow=await f.start(signed.data.token);
  const conflict=await f.exchange(flow,other.data.token);assert.equal(conflict.status,409);assert.equal(conflict.data.error,'account_mismatch');assert.equal((await f.api('/me',{token:other.data.token})).data.user.id,other.data.user.id);
  const before=f.sql.prepare('SELECT count(*) n FROM sessions').get().n,same=await f.exchange(flow,signed.data.token);assert.equal(same.status,200);assert.equal(same.data.already_signed_in,true);assert.equal(same.data.token,undefined);assert.equal(same.data.user.id,signed.data.user.id);assert.equal(f.sql.prepare('SELECT count(*) n FROM sessions').get().n,before);assert.equal((await f.exchange(flow,signed.data.token)).status,400);
 }finally{f.close()}
});
test('concurrent exchanges mint exactly one session even within the same clock second',async()=>{
 const f=fixture();try{
  const signed=await f.signup(),flow=await f.start(signed.data.token),answers=await Promise.all([f.exchange(flow),f.exchange(flow)]);assert.deepEqual(answers.map(answer=>answer.status).sort(),[200,400]);assert.equal(f.sql.prepare('SELECT count(*) n FROM sessions').get().n,2);
  const success=answers.find(answer=>answer.status===200),row=f.sql.prepare('SELECT used_session_hash FROM account_session_handoffs').get();assert.equal(row.used_session_hash,await digest(success.data.token));
 }finally{f.close()}
});

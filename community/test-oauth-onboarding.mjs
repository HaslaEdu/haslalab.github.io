// Real Worker, SQLite and mocked providers only. Never authenticates a real user.
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import worker from './src/index.js';
import {studioUser} from './src/studio-gateway.js';
import {signupCode} from './fixtures/signup-code.mjs';
const origin='https://haslalab.org',gateway='https://haslalab-community-edge.haslalab.workers.dev';
const b64=bytes=>Buffer.from(bytes).toString('base64url');
function setup(){
 const sql=new DatabaseSync(':memory:');for(const name of readdirSync(new URL('./migrations/',import.meta.url)).filter(name=>/^\d{4}_.*\.sql$/.test(name)).sort())sql.exec(readFileSync(new URL('./migrations/'+name,import.meta.url),'utf8'));
 const DB={prepare(query){const statement=sql.prepare(query),make=args=>({bind:(...values)=>make(values),async first(){return statement.get(...args)||null},async all(){return{results:statement.all(...args)}},async run(){return this.execute()},execute(){if(statement.columns().length)return{results:statement.all(...args),meta:{changes:sql.prepare('SELECT changes() n').get().n}};const out=statement.run(...args);return{results:[],meta:{changes:Number(out.changes),last_row_id:Number(out.lastInsertRowid)}}}});return make([])},async batch(statements){sql.exec('BEGIN');try{const out=statements.map(s=>s.execute());sql.exec('COMMIT');return out}catch(e){sql.exec('ROLLBACK');throw e}}};
 const env={DB,ALLOWED_ORIGINS:origin+',https://physleague.kr',GOOGLE_CLIENT_ID:'fixture-client',GOOGLE_CLIENT_SECRET:'fixture-secret',OAUTH_MOCK_BASE:'https://provider.invalid'};
 const api=async(method,path,body,token)=>{const r=await worker.fetch(new Request(gateway+'/api'+path,{method,headers:{Origin:origin,'CF-Connecting-IP':'192.0.2.88',...(body?{'Content-Type':'application/json'}:{}),...(token?{Authorization:'Bearer '+token}:{})},...(body?{body:JSON.stringify(body)}:{})}),env,{waitUntil(){}});return{status:r.status,data:await r.json(),headers:r.headers}};
 const get=path=>worker.fetch(new Request(path.startsWith('http')?path:gateway+path,{headers:{Origin:origin,'CF-Connecting-IP':'192.0.2.88'}}),env,{waitUntil(){}});
 const oauth=async(start,sub='new-social')=>{const original=globalThis.fetch;globalThis.fetch=async input=>{const url=new URL(input);assert.equal(url.origin,'https://provider.invalid');return Response.json(url.pathname.includes('token')?{access_token:'fixture-access'}:{sub,name:'소셜 사용자'})};try{const started=await get(start);assert.equal(started.status,302);const state=new URL(started.headers.get('Location')).searchParams.get('state');const finished=await get('/api/oauth/google/callback?state='+state+'&code=fixture');assert.equal(finished.status,302);assert.equal((await get('/api/oauth/google/callback?state='+state+'&code=fixture')).status,400);return new URL(finished.headers.get('Location'))}finally{globalThis.fetch=original}};
 // a password sign-up also carries a mailed code (signup-email.js): `coded` adds a fresh address and its code row
 const coded=async body=>({...body,...await signupCode(sql)});
 return{sql,env,api,get,oauth,coded,close(){sql.close()}};
}
test('social registration requires a unique chosen username before protected API use; existing admin identity is retained',async()=>{
 const s=setup();try{
  assert.equal((await s.api('POST','/signup',{nickname:'No ID',password:'fixture-password'})).data.error,'bad_username');
  const finish=await s.oauth('/api/oauth/google/start?return='+encodeURIComponent(origin+'/'));
  const code=new URLSearchParams(finish.hash.split('?')[1]).get('c');const signed=await s.api('POST','/oauth/redeem',{code});
  assert.equal(signed.status,200);assert.equal(signed.data.user.username,null);assert.equal(signed.data.user.username_required,true);const token=signed.data.token;
  assert.equal((await s.api('POST','/oauth/redeem',{code})).status,400);
  assert.equal((await s.api('GET','/me/security',undefined,token)).data.error,'username_required');
  assert.equal((await s.api('GET','/me/auth-context',undefined,token)).data.error,'username_required');
  assert.equal((await s.api('GET','/me/identity-proof?provider=google',undefined,token)).data.error,'username_required');
  await assert.rejects(studioUser(new Request(gateway+'/api/studio/capabilities',{headers:{Authorization:'Bearer '+token}}),s.env),error=>error.code==='username_required');
  assert.equal((await s.api('POST','/me/username',{username:'x',consent:{terms:true,privacy:true,age14:true}},token)).data.error,'bad_username');
  s.sql.prepare('INSERT INTO users(username,nickname,pw,created_at) VALUES(?,?,NULL,?)').run('taken_name','Taken name',Math.floor(Date.now()/1000));
  assert.equal((await s.api('POST','/me/username',{username:'TAKEN_NAME',consent:{terms:true,privacy:true,age14:true}},token)).data.error,'username_taken');
  const claimed=await s.api('POST','/me/username',{username:'chosen_name',consent:{terms:true,privacy:true,age14:true}},token);assert.equal(claimed.status,200);assert.equal(claimed.data.user.username,'chosen_name');assert.equal(claimed.data.user.username_required,undefined);
  assert.equal((await s.api('GET','/me/security',undefined,token)).status,200);
  assert.equal((await s.api('POST','/me/username',{username:'renamed_id',consent:{terms:true,privacy:true,age14:true}},token)).data.error,'username_already_set');
  const row=s.sql.prepare("INSERT INTO users(username,nickname,role,created_at) VALUES('g_QFAlJRmIyg','관리자','admin',?)").run(Math.floor(Date.now()/1000));const id=Number(row.lastInsertRowid);
  s.sql.prepare("INSERT INTO identities(provider,sub,user_id,created_at) VALUES('google','legacy-admin',?,?)").run(id,Math.floor(Date.now()/1000));
  const legacyFinish=await s.oauth('/api/oauth/google/start?return='+encodeURIComponent(origin+'/'),'legacy-admin');
  const legacy=await s.api('POST','/oauth/redeem',{code:new URLSearchParams(legacyFinish.hash.split('?')[1]).get('c')});assert.equal(legacy.data.user.id,id);assert.equal(legacy.data.user.role,'admin');assert.equal(legacy.data.user.username,'g_QFAlJRmIyg');assert.equal(legacy.data.user.username_required,undefined);
 }finally{s.close()}
});
test('a historical social admin with a later password can choose a name once without losing identity, role or data',async()=>{
 const s=setup();try{
  const normal=await s.api('POST','/signup',await s.coded({username:'g_Member1234',nickname:'Chosen member',password:'fixture-password',consent:{terms:true,privacy:true,age14:true}}));
  assert.equal((await s.api('GET','/me',undefined,normal.data.token)).data.user.username_setup_available,undefined);
  assert.equal((await s.api('POST','/me/username',{username:'other_name',consent:{terms:true,privacy:true,age14:true}},normal.data.token)).data.error,'username_already_set');
  const created=Math.floor(Date.now()/1000)-86400,password=s.sql.prepare('SELECT pw FROM users WHERE id=?').get(normal.data.user.id).pw;
  const inserted=s.sql.prepare("INSERT INTO users(username,nickname,pw,role,created_at,exam_tokens) VALUES('g_QFAlJRmIyg','기존 관리자',?,'admin',?,7)").run(password,created),id=Number(inserted.lastInsertRowid);
  s.sql.prepare("INSERT INTO identities(provider,sub,user_id,created_at) VALUES('google','historical-admin',?,?)").run(id,created+1);
  s.sql.prepare("INSERT INTO posts(board,user_id,title,body,created_at) VALUES('free',?,'Fixture post','Owned fixture material',?)").run(id,created);
  const signIn=async()=>{const finish=await s.oauth('/api/oauth/google/start?return='+encodeURIComponent(origin+'/'),'historical-admin');return s.api('POST','/oauth/redeem',{code:new URLSearchParams(finish.hash.split('?')[1]).get('c')})};
  const signed=await signIn(),token=signed.data.token;assert.equal(signed.data.user.id,id);assert.equal(signed.data.user.role,'admin');assert.equal(signed.data.user.username,'g_QFAlJRmIyg');assert.equal(signed.data.user.username_required,undefined);assert.equal(signed.data.user.username_setup_available,true);assert.equal(signed.data.user.username_kind,'generated');assert.equal(signed.data.user.unique_identifier,'g_QFAlJRmIyg');
  assert.equal((await s.api('GET','/me/security',undefined,token)).status,200); // Existing work remains available before choosing.
  s.sql.prepare('UPDATE sessions SET created_at=? WHERE user_id=?').run(Math.floor(Date.now()/1000)-601,id);
  assert.equal((await s.api('POST','/me/username',{username:'chosen_owner',consent:{terms:true,privacy:true,age14:true}},token)).data.error,'recent_login_required');
  assert.equal((await s.api('GET','/me/auth-context',undefined,token)).data.recent_login,false);
  const refreshed=await signIn(),fresh=refreshed.data.token;
  assert.equal((await s.api('POST','/me/username',{username:'g_Member1234',consent:{terms:true,privacy:true,age14:true}},fresh)).data.error,'username_taken');
  assert.equal(s.sql.prepare('SELECT count(*) n FROM account_username_claims WHERE user_id=?').get(id).n,0); // Failed collision rolls the marker back.
  const before=s.sql.prepare('SELECT id,role,nickname,pw,avatar,created_at,exam_tokens FROM users WHERE id=?').get(id);
  const requests=await Promise.all([s.api('POST','/me/username',{username:'g_Chosen1234',consent:{terms:true,privacy:true,age14:true}},fresh),s.api('POST','/me/username',{username:'other_chosen',consent:{terms:true,privacy:true,age14:true}},fresh)]);assert.deepEqual(requests.map(result=>result.status).sort(),[200,409]);
  const changed=requests.find(result=>result.status===200).data.user;assert.equal(changed.id,id);assert.equal(changed.role,'admin');assert.equal(changed.unique_identifier,'g_QFAlJRmIyg');assert.equal(changed.username_setup_available,false);
  assert.deepEqual(s.sql.prepare('SELECT id,role,nickname,pw,avatar,created_at,exam_tokens FROM users WHERE id=?').get(id),before);
  assert.equal(s.sql.prepare('SELECT body FROM posts WHERE user_id=?').get(id).body,'Owned fixture material');
  const me=(await s.api('GET','/me',undefined,fresh)).data.user;assert.equal(me.username,changed.username);assert.equal(me.unique_identifier,'g_QFAlJRmIyg');assert.equal(me.username_kind,'chosen');assert.equal(me.username_setup_available,false);
  assert.equal((await s.api('POST','/me/username',{username:'claim_again',consent:{terms:true,privacy:true,age14:true}},fresh)).data.error,'username_already_set');
  assert.equal((await s.api('DELETE','/me',undefined,fresh)).status,200);assert.equal(s.sql.prepare('SELECT count(*) n FROM account_username_claims WHERE user_id=?').get(id).n,0);
 }finally{s.close()}
});
test('a manually chosen social-looking username with a later linked provider is not treated as generated',async()=>{
 const s=setup();try{
  const created=Math.floor(Date.now()/1000)-86400,row=s.sql.prepare("INSERT INTO users(username,nickname,pw,created_at) VALUES('g_Chosen5678','Manual fixture','fixture-hash',?)").run(created),id=Number(row.lastInsertRowid);
  s.sql.prepare("INSERT INTO identities(provider,sub,user_id,created_at) VALUES('google','linked-later',?,?)").run(id,created+600);
  const finish=await s.oauth('/api/oauth/google/start?return='+encodeURIComponent(origin+'/'),'linked-later'),signed=await s.api('POST','/oauth/redeem',{code:new URLSearchParams(finish.hash.split('?')[1]).get('c')});
  assert.equal(signed.data.user.username,'g_Chosen5678');assert.equal(signed.data.user.username_setup_available,undefined);assert.equal((await s.api('POST','/me/username',{username:'changed_later',consent:{terms:true,privacy:true,age14:true}},signed.data.token)).data.error,'username_already_set');
 }finally{s.close()}
});
test('auth-context contains only public user data and a fresh-login boolean; guests and pending members are denied',async()=>{
 const s=setup();try{
  assert.equal((await s.api('GET','/me/auth-context')).status,401);
  const signed=await s.api('POST','/signup',await s.coded({username:'context_owner',nickname:'Context fixture',password:'fixture-password',consent:{terms:true,privacy:true,age14:true}})),token=signed.data.token;
  s.sql.exec('DROP TABLE account_username_claims'); // A pre-migration deployment creates only its additive claim table on the first account read.
  const fresh=await s.api('GET','/me/auth-context',undefined,token);assert.equal(fresh.status,200);assert.deepEqual(Object.keys(fresh.data).sort(),['recent_login','user']);assert.equal(fresh.data.recent_login,true);assert.equal(fresh.data.user.id,signed.data.user.id);
  for(const key of ['token','tokenHash','sessionCreatedAt','pw','password'])assert.equal(fresh.data.user[key],undefined);
  s.sql.prepare('UPDATE sessions SET created_at=?').run(Math.floor(Date.now()/1000)-601);assert.equal((await s.api('GET','/me/auth-context',undefined,token)).data.recent_login,false);
 }finally{s.close()}
});
test('Google identity proof requires a recent completed login and binds only the authenticated owner',async()=>{
 const s=setup();try{
  assert.equal((await s.api('GET','/me/identity-proof?provider=google')).status,401);
  const owner=await s.api('POST','/signup',await s.coded({username:'proof_owner',nickname:'Proof fixture',password:'fixture-password',consent:{terms:true,privacy:true,age14:true}})),other=await s.api('POST','/signup',await s.coded({username:'proof_other',nickname:'Other fixture',password:'fixture-password',consent:{terms:true,privacy:true,age14:true}})),token=owner.data.token;
  assert.equal((await s.api('GET','/me/identity-proof?provider=google',undefined,token)).data.error,'provider_identity_required');
  s.sql.prepare("INSERT INTO identities(provider,sub,user_id,created_at) VALUES('google','fixture-owner-google-sub',?,?)").run(owner.data.user.id,Math.floor(Date.now()/1000));
  s.sql.prepare("INSERT INTO identities(provider,sub,user_id,created_at) VALUES('google','fixture-other-google-sub',?,?)").run(other.data.user.id,Math.floor(Date.now()/1000));
  const proof=await s.api('GET','/me/identity-proof?provider=google',undefined,token);assert.equal(proof.status,200);assert.deepEqual(proof.data,{provider:'google',subject:'fixture-owner-google-sub'});assert.equal(proof.headers.get('Cache-Control'),'no-store');
  for(const query of ['provider=github','provider=GOOGLE','provider=google&user_id=2','provider=google&provider=google',''])assert.equal((await s.api('GET','/me/identity-proof?'+query,undefined,token)).data.error,'bad_provider');
  s.sql.prepare('UPDATE sessions SET created_at=? WHERE user_id=?').run(Math.floor(Date.now()/1000)-601,owner.data.user.id);assert.equal((await s.api('GET','/me/identity-proof?provider=google',undefined,token)).data.error,'recent_login_required');
  s.sql.prepare('UPDATE sessions SET created_at=? WHERE user_id=?').run(Math.floor(Date.now()/1000),owner.data.user.id);s.sql.prepare("INSERT INTO identities(provider,sub,user_id,created_at) VALUES('google','fixture-second-google-sub',?,?)").run(owner.data.user.id,Math.floor(Date.now()/1000));assert.equal((await s.api('GET','/me/identity-proof?provider=google',undefined,token)).data.error,'provider_identity_ambiguous');
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
test('OAuth return address: listed providers use OAUTH_REDIRECT_ORIGIN for the authorize and token calls; others and bad values keep this Worker',async()=>{
 const s=setup();try{
  const start=async()=>{const r=await s.get('/api/oauth/google/start?return='+encodeURIComponent(origin+'/'));assert.equal(r.status,302);return new URL(r.headers.get('Location')).searchParams.get('redirect_uri');};
  assert.equal(await start(),gateway+'/api/oauth/google/callback','default: this Worker');
  Object.assign(s.env,{OAUTH_REDIRECT_ORIGIN:'https://haslaedu.kr',OAUTH_REDIRECT_PROVIDERS:'google'});
  assert.equal(await start(),'https://haslaedu.kr/api/oauth/google/callback');
  // the token exchange sends the same redirect_uri the provider saw
  const original=globalThis.fetch;let sent=null;
  globalThis.fetch=async(input,init)=>{const u=new URL(input);if(u.pathname.includes('token')){sent=new URLSearchParams(String(init?.body||''));return Response.json({access_token:'fixture-access'})}return Response.json({sub:'moved-origin',name:'소셜 사용자'})};
  try{const started=await s.get('/api/oauth/google/start?return='+encodeURIComponent(origin+'/'));const state=new URL(started.headers.get('Location')).searchParams.get('state');
   const finished=await s.get('/api/oauth/google/callback?state='+state+'&code=fixture');assert.equal(finished.status,302);assert.ok(finished.headers.get('Location').startsWith(origin+'/#/oauth?c='))}finally{globalThis.fetch=original}
  assert.equal(sent?.get('redirect_uri'),'https://haslaedu.kr/api/oauth/google/callback');
  for(const bad of ['http://haslaedu.kr','https://haslaedu.kr/path','not a url','']){s.env.OAUTH_REDIRECT_ORIGIN=bad;assert.equal(await start(),gateway+'/api/oauth/google/callback',bad);}
  Object.assign(s.env,{OAUTH_REDIRECT_ORIGIN:'https://haslaedu.kr',OAUTH_REDIRECT_PROVIDERS:'naver'});
  assert.equal(await start(),gateway+'/api/oauth/google/callback','unlisted provider keeps the old address');
 }finally{s.close()}
});
test('login CSRF: the nonce the page sent to the start comes back with the one-time code, and only then',async()=>{
 const s=setup();try{
  const nonce='N'.repeat(32),ret=encodeURIComponent(origin+'/');
  const back=await s.oauth('/api/oauth/google/start?return='+ret+'&nonce='+nonce,'nonce-member'),q=new URLSearchParams(back.hash.split('?')[1]);
  assert.ok(q.get('c'));assert.equal(q.get('n'),nonce,'the nonce returns beside the code');
  assert.equal(s.sql.prepare('SELECT count(*) n FROM oauth_states').get().n,0,'the state (and its nonce) is used up');
  const plain=new URLSearchParams((await s.oauth('/api/oauth/google/start?return='+ret,'nonce-member')).hash.split('?')[1]);
  assert.ok(plain.get('c'));assert.equal(plain.get('n'),null,'no nonce sent, none returned (the page then refuses the code)');
  for(const bad of ['short','x'.repeat(200),'bad%20chars%2Fhere%3Cscript%3E'])assert.equal(new URLSearchParams((await s.oauth('/api/oauth/google/start?return='+ret+'&nonce='+bad,'nonce-member')).hash.split('?')[1]).get('n'),null,bad);
 }finally{s.close()}
 // a deployment whose oauth_states predates the column gains it on the first start
 const old=setup();try{
  old.sql.exec('DROP TABLE oauth_states;CREATE TABLE oauth_states(state TEXT PRIMARY KEY,provider TEXT NOT NULL,verifier TEXT,return_to TEXT NOT NULL,link_user INTEGER,created_at INTEGER NOT NULL)');
  const q=new URLSearchParams((await old.oauth('/api/oauth/google/start?return='+encodeURIComponent(origin+'/')+'&nonce='+'M'.repeat(32),'old-schema')).hash.split('?')[1]);
  assert.equal(q.get('n'),'M'.repeat(32));assert.ok(old.sql.prepare('PRAGMA table_info(oauth_states)').all().some(c=>c.name==='nonce'));
 }finally{old.close()}
});
const codeOf=back=>new URLSearchParams(back.hash.split('?')[1]).get('c');
test('a social sign-up that has not chosen a username can still delete its account (and only that)',async()=>{
 const s=setup();try{
  const signed=await s.api('POST','/oauth/redeem',{code:codeOf(await s.oauth('/api/oauth/google/start?return='+encodeURIComponent(origin+'/'),'changed-mind'))});
  const token=signed.data.token,id=signed.data.user.id;assert.equal(signed.data.user.username_required,true);
  assert.equal((await s.api('PATCH','/me',{nickname:'Other name'},token)).data.error,'username_required','other account changes still wait for the username');
  s.sql.prepare('UPDATE sessions SET created_at=? WHERE user_id=?').run(Math.floor(Date.now()/1000)-901,id);
  assert.equal((await s.api('DELETE','/me',undefined,token)).data.error,'recent_login_required','a stale session still cannot delete');
  s.sql.prepare('UPDATE sessions SET created_at=? WHERE user_id=?').run(Math.floor(Date.now()/1000),id);
  const gone=await s.api('DELETE','/me',undefined,token);assert.equal(gone.status,200);assert.equal(gone.data.ok,true);
  assert.equal(s.sql.prepare('SELECT deleted FROM users WHERE id=?').get(id).deleted,1);
  assert.equal(s.sql.prepare('SELECT count(*) n FROM identities WHERE user_id=?').get(id).n,0);
  assert.equal(s.sql.prepare('SELECT count(*) n FROM sessions WHERE user_id=?').get(id).n,0);
  assert.equal((await s.api('DELETE','/me')).status,401);
  const again=await s.api('POST','/oauth/redeem',{code:codeOf(await s.oauth('/api/oauth/google/start?return='+encodeURIComponent(origin+'/'),'changed-mind'))});
  assert.equal(again.data.fresh,true);assert.notEqual(again.data.user.id,id,'the same Google account can sign up afresh');
 }finally{s.close()}
});
test('a suspended social account is answered with account_suspended and nothing is created',async()=>{
 const s=setup();try{
  const signIn=async()=>s.oauth('/api/oauth/google/start?return='+encodeURIComponent(origin+'/'),'suspended-sub');
  const first=await s.api('POST','/oauth/redeem',{code:codeOf(await signIn())});const id=first.data.user.id;
  await s.api('POST','/me/username',{username:'suspended_one',consent:{terms:true,privacy:true,age14:true}},first.data.token);
  s.sql.prepare('UPDATE users SET deleted=2 WHERE id=?').run(id);
  const count=()=>s.sql.prepare('SELECT (SELECT count(*) FROM users) u,(SELECT count(*) FROM identities) i,(SELECT count(*) FROM oauth_codes) c').get();
  const before=count();
  for(let i=0;i<3;i++){const back=await signIn(),q=new URLSearchParams(back.hash.split('?')[1]);assert.equal(back.origin,origin);assert.equal(q.get('e'),'account_suspended');assert.equal(q.get('c'),null);assert.equal(q.get('d'),null);}
  assert.deepEqual({...count()},{...before},'no pending user, identity or code');
  assert.equal(s.sql.prepare("SELECT count(*) n FROM users WHERE username LIKE '~pending_%'").get().n,0);
  // a link left behind by a deleted account does not block a new sign-up
  const dead=Number(s.sql.prepare("INSERT INTO users(username,nickname,pw,created_at,deleted) VALUES('deleted_x','deleted_x',NULL,?,1)").run(Math.floor(Date.now()/1000)).lastInsertRowid);
  s.sql.prepare("INSERT INTO identities(provider,sub,user_id,created_at) VALUES('google','orphan-sub',?,?)").run(dead,Math.floor(Date.now()/1000));
  const orphan=await s.api('POST','/oauth/redeem',{code:codeOf(await s.oauth('/api/oauth/google/start?return='+encodeURIComponent(origin+'/'),'orphan-sub'))});
  assert.equal(orphan.status,200);assert.equal(orphan.data.fresh,true);assert.notEqual(orphan.data.user.id,dead);
 }finally{s.close()}
});
test('deleting the account removes the HPhO entries, seats, phones, events and their stored proctoring files',async()=>{
 const s=setup();try{
  const {HPHO_SCHEMA}=await import('./src/hpho.js'),{HPHO_EXAM_SCHEMA}=await import('./src/hpho-exam.js');for(const q of [...HPHO_SCHEMA,...HPHO_EXAM_SCHEMA])s.sql.exec(q);
  const objects=new Map();s.env.HPHO_SNAPS={async put(k,v){objects.set(k,v)},async delete(keys){for(const k of [].concat(keys))objects.delete(k)},
   async list({prefix,cursor}){const all=[...objects.keys()].filter(k=>k.startsWith(prefix)).sort(),at=cursor?Number(cursor):0,page=all.slice(at,at+2);return{objects:page.map(key=>({key})),truncated:at+2<all.length,cursor:String(at+2)}}};
  const owner=await s.api('POST','/signup',await s.coded({username:'hpho_owner',nickname:'HPhO owner',password:'fixture-password',consent:{terms:true,privacy:true,age14:true}}));
  const other=await s.api('POST','/signup',await s.coded({username:'hpho_other',nickname:'HPhO other',password:'fixture-password',consent:{terms:true,privacy:true,age14:true}}));
  const me=owner.data.user.id,them=other.data.user.id,t=Math.floor(Date.now()/1000);
  for(const [user,no] of [[me,'H0007'],[them,'H00071']]){
   s.sql.prepare("INSERT INTO hpho_entries(round_id,user_id,candidate_no,country,level,birth_year,created_at) VALUES('2027-1',?,?,'KR','high',2008,?)").run(user,no,t);
   for(const track of ['theory','experiment']){
    s.sql.prepare("INSERT INTO hpho_seats(round_id,user_id,track,candidate_no,checked_in_at,ends_at,last_beat) VALUES('2027-1',?,?,?,?,?,?)").run(user,track,no,t,t+60,t);
    s.sql.prepare("INSERT INTO hpho_phones(round_id,user_id,track,candidate_no,code_hash,created_at) VALUES('2027-1',?,?,?,?,?)").run(user,track,no,'hash-'+user+track,t);
    s.sql.prepare("INSERT INTO hpho_mail(round_id,user_id,track,kind,sent_at) VALUES('2027-1',?,?,'eve',?)").run(user,track,t);
    for(const key of [`hpho-rec/2027-1/${track}/${no}/${t}-webcam.webm`,`hpho-answers/2027-1/${track}/${no}/001.jpg`])objects.set(key,'x');
   }
   s.sql.prepare("INSERT INTO hpho_events(round_id,user_id,seq,at,kind) VALUES('2027-1',?,1,?,'focus_lost')").run(user,t);
   s.sql.prepare("INSERT INTO hpho_sessions(round_id,user_id,candidate_no,started_at,ends_at,last_beat) VALUES('2026-2',?,?,?,?,?)").run(user,no,t,t,t);
   for(let i=0;i<5;i++)objects.set(`hpho/2027-1/${no}/${t+i}-webcam-random.jpg`,'x');
   objects.set(`hpho/2026-2/${no}/${t}-screen-random.jpg`,'x');
  }
  objects.set('hpho-docs/2027-1/theory/paper-ko.pdf','x');
  const gone=await s.api('DELETE','/me',undefined,owner.data.token);assert.equal(gone.status,200);
  for(const table of ['hpho_entries','hpho_seats','hpho_phones','hpho_events','hpho_mail','hpho_sessions']){
   assert.equal(s.sql.prepare(`SELECT count(*) n FROM ${table} WHERE user_id=?`).get(me).n,0,table);
   assert.ok(s.sql.prepare(`SELECT count(*) n FROM ${table} WHERE user_id=?`).get(them).n>0,table+' of another member stays');
  }
  const left=[...objects.keys()];
  assert.deepEqual(left.filter(k=>k.includes('/H0007/')),[],'every file under the deleted candidate number is gone');
  assert.equal(left.filter(k=>k.includes('/H00071/')).length,10,"a longer candidate number sharing the prefix is someone else's");
  assert.ok(left.includes('hpho-docs/2027-1/theory/paper-ko.pdf'),'the papers themselves stay');
 }finally{s.close()}
});

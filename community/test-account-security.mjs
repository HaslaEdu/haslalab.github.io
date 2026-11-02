// No outbound requests, real accounts or recipient addresses. Exercise actual
// SQL transactions against SQLite, including concurrent use of the same link.
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createHash} from 'node:crypto';
import {ACCOUNT_SECURITY_SCHEMA,createAccountSecurityRouter,accountMailAvailable,ensureAccountSecuritySchema} from './src/account-security.js';
class HttpError extends Error{constructor(status,code){super(code);this.status=status;this.code=code}}
test('a cold schema works with eager SQLite preparation and concurrent initializers share readiness',async()=>{
  const sql=new DatabaseSync(':memory:');sql.exec('CREATE TABLE users(id INTEGER PRIMARY KEY)');
  const db={prepare(query){const statement=sql.prepare(query);return{execute:()=>statement.run(),async run(){return statement.run()}}},async batch(statements){sql.exec('BEGIN');try{const result=statements.map(statement=>statement.execute());sql.exec('COMMIT');return result}catch(error){sql.exec('ROLLBACK');throw error}}};
  try{const first=ensureAccountSecuritySchema(db);assert.equal(ensureAccountSecuritySchema(db),first);await first;
    assert.deepEqual(sql.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'account_%' ORDER BY name").all().map(row=>row.name),['account_email_tokens','account_emails']);
    assert.deepEqual(sql.prepare("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'account_email_tokens_%' ORDER BY name").all().map(row=>row.name),['account_email_tokens_expiry','account_email_tokens_user']);
  }finally{sql.close()}
});
const hash=value=>createHash('sha256').update(value).digest('base64url');
function setup({mailer=true,password='pw:old-password'}={}){
  const sql=new DatabaseSync(':memory:');sql.exec(`CREATE TABLE users(id INTEGER PRIMARY KEY,pw TEXT,deleted INTEGER DEFAULT 0);
    CREATE TABLE sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER,created_at INTEGER,expires_at INTEGER);
    INSERT INTO users(id,pw) VALUES(1,${password===null?'NULL':"'"+password+"'"});INSERT INTO users(id,pw)VALUES(2,'pw:other-password');
    INSERT INTO sessions VALUES('current',1,1000,99999),('other-device',1,1000,99999),('other-user',2,1000,99999);`);
  let clock=2000,sequence=0;const delivered=[],limits=[];
  const db={prepare(query){return{query,args:[],bind(...args){return{...this,args}},async first(){return sql.prepare(this.query).get(...this.args)||null},async run(){const result=sql.prepare(this.query).run(...this.args);return {meta:{changes:Number(result.changes),last_row_id:Number(result.lastInsertRowid)}}}}},
    async batch(statements){sql.exec('BEGIN');try{const out=statements.map(s=>{const results=sql.prepare(s.query).all(...s.args);return {results,meta:{changes:sql.prepare('SELECT changes() n').get().n}}});sql.exec('COMMIT');return out}catch(error){sql.exec('ROLLBACK');throw error}}};
  const env={DB:db,AUTH_EMAIL_ENABLED:'on',AUTH_MAIL_FROM:'accounts@hasla.example',...(mailer?{ACCOUNT_EMAIL:{async send(message){delivered.push(message);return{messageId:'mock'}}}}:{})};
  const route=createAccountSecurityRouter({HttpError,now:()=>clock,limit:async(_env,key,max,seconds)=>limits.push({key,max,seconds}),sha256:async value=>hash(value),
    hashPw:async value=>'pw:'+value+':'+(++sequence),checkPw:async(value,stored)=>stored==='pw:'+value,pwOk:value=>typeof value==='string'&&value.length>=8&&value.length<=200});
  const me={id:1,tokenHash:'current',sessionCreatedAt:clock};
  const call=(path,body={},user=me,method='POST',ctx)=>route(new Request('https://api.example'+path,{method,headers:{'CF-Connecting-IP':'192.0.2.1'}}),env,{path,body,me:user,ctx});
  const token=()=>{const link=delivered.at(-1).text.split('\n\n').find(line=>line.startsWith('https://'));return new URLSearchParams(new URL(link).hash.split('?')[1]).get('token')};
  const verify=async()=>{await call('/api/me/email',{email:'Owner@Example.com',old:'old-password',return_origin:'https://physleague.kr'});const value=token();await call('/api/auth/verify-email',{token:value},null);return value};
  return{sql,env,call,me,delivered,limits,token,verify,time(value){clock=value},close(){sql.close()}};
}
test('existing password is required and checked; passwordless accounts cannot bypass email proof',async()=>{
  const s=setup();await assert.rejects(s.call('/api/me/password',{password:'new-password'}),e=>e.code==='current_password_required');
  await assert.rejects(s.call('/api/me/password',{old:'wrong',password:'new-password'}),e=>e.code==='bad_current_password');
  await s.call('/api/me/password',{old:'old-password',password:'new-password'});
  assert.deepEqual(s.sql.prepare('SELECT token_hash FROM sessions ORDER BY token_hash').all().map(x=>x.token_hash),['current','other-user']);
  const no=setup({password:null});await assert.rejects(no.call('/api/me/password',{old:'anything',password:'new-password'}),e=>e.code==='password_not_set');s.close();no.close();
});
test('email is not recovery-capable before single-use proof; links contain only a short-lived fragment token',async()=>{
  const s=setup();await s.call('/api/me/email',{email:'Owner@Example.com',old:'old-password',return_origin:'https://physleague.kr'});
  const status=await s.call('/api/me/security',{},s.me,'GET');assert.equal(status.email,null);assert.equal(status.pending_email,'owner@example.com');
  const raw=s.token(),stored=s.sql.prepare('SELECT * FROM account_email_tokens').get();assert.notEqual(stored.token_hash,raw);assert.equal(stored.token_hash,hash(raw));assert.equal(stored.expires_at-stored.created_at,1800);
  assert.ok(s.delivered[0].text.includes('https://physleague.kr/?lang=ko#/verify-email?token='));assert.ok(!s.delivered[0].html.includes('old-password'));
  const before=s.delivered.length;await s.call('/api/auth/forgot-password',{email:'owner@example.com'},null);assert.equal(s.delivered.length,before);
  await s.call('/api/auth/verify-email',{token:raw},null);await assert.rejects(s.call('/api/auth/verify-email',{token:raw},null),e=>e.code==='invalid_or_expired_link');
  const verified=await s.call('/api/me/security',{},s.me,'GET');assert.equal(verified.email,'owner@example.com');assert.equal(verified.email_verified,true);s.close();
});
test('reset consumes proof atomically and revokes every session; replay and concurrent attempts fail',async()=>{
  const s=setup();await s.verify();await s.call('/api/auth/forgot-password',{email:'owner@example.com',return_origin:'https://evil.example/path'},null);
  assert.ok(s.delivered.at(-1).text.includes('https://haslalab.org/account.html?lang=ko#/reset-password?token='));const raw=s.token();
  const outcomes=await Promise.allSettled([s.call('/api/auth/reset-password',{token:raw,password:'new-password-A'},null),s.call('/api/auth/reset-password',{token:raw,password:'new-password-B'},null)]);
  assert.equal(outcomes.filter(x=>x.status==='fulfilled').length,1);assert.equal(outcomes.filter(x=>x.status==='rejected'&&x.reason.code==='invalid_or_expired_link').length,1);
  assert.equal(s.sql.prepare('SELECT count(*) n FROM sessions WHERE user_id=1').get().n,0);assert.equal(s.sql.prepare('SELECT count(*) n FROM sessions WHERE user_id=2').get().n,1);
  await assert.rejects(s.call('/api/auth/reset-password',{token:raw,password:'another-password'},null),e=>e.code==='invalid_or_expired_link');s.close();
});
test('unverified or unknown addresses never receive reset mail and have identical responses; rate keys do not expose email',async()=>{
  const s=setup();await s.verify();const a=await s.call('/api/auth/forgot-password',{email:'owner@example.com'},null);const b=await s.call('/api/auth/forgot-password',{email:'unknown@example.com'},null);
  assert.deepEqual(a,b);assert.equal(s.delivered.length,2);assert.ok(s.limits.some(x=>x.key==='forgot-ip:192.0.2.1'&&x.max===5));assert.ok(s.limits.every(x=>!x.key.includes('@')));s.close();
});
test('expiry, password change, changed recovery email and deletion invalidate old links',async()=>{
  for(const reason of ['expired','password','email','deleted']){
    const s=setup();await s.verify();await s.call('/api/auth/forgot-password',{email:'owner@example.com'},null);const raw=s.token();
    if(reason==='expired')s.time(2901);if(reason==='password')s.sql.prepare('UPDATE users SET pw=? WHERE id=1').run('pw:changed');
    if(reason==='email')s.sql.prepare('UPDATE account_emails SET email=? WHERE user_id=1').run('changed@example.com');if(reason==='deleted')s.sql.exec('UPDATE users SET deleted=1 WHERE id=1');
    await assert.rejects(s.call('/api/auth/reset-password',{token:raw,password:'new-password'},null),e=>e.code==='invalid_or_expired_link');s.close();
  }
});
test('first password requires verified email; stale passwordless sessions cannot register recovery addresses',async()=>{
  const s=setup({password:null});s.me.sessionCreatedAt=1000;await assert.rejects(s.call('/api/me/email',{email:'owner@example.com'}),e=>e.code==='recent_login_required');
  s.me.sessionCreatedAt=2000;await s.call('/api/me/email',{email:'owner@example.com'});await s.call('/api/auth/verify-email',{token:s.token()},null);
  await s.call('/api/auth/forgot-password',{email:'owner@example.com'},null);await s.call('/api/auth/reset-password',{token:s.token(),password:'first-password'},null);
  assert.ok(s.sql.prepare('SELECT pw FROM users WHERE id=1').get().pw.startsWith('pw:first-password'));s.close();
});
test('mail unavailable/disabled never reports a sent link; provider errors invalidate undelivered tokens',async()=>{
  const s=setup({mailer:false});assert.equal(accountMailAvailable(s.env),false);await assert.rejects(s.call('/api/me/email',{email:'owner@example.com',old:'old-password'}),e=>e.code==='email_unavailable');
  const f=setup();f.env.ACCOUNT_EMAIL.send=async()=>{throw Error('provider details must stay private')};await assert.rejects(f.call('/api/me/email',{email:'owner@example.com',old:'old-password'}),e=>e.code==='email_unavailable');
  assert.equal(f.sql.prepare('SELECT count(*) n FROM account_email_tokens').get().n,0);assert.equal(accountMailAvailable({...f.env,AUTH_EMAIL_ENABLED:'off'}),false);s.close();f.close();
});
test('forgot-password responds before mail-provider latency and keeps failures opaque',async()=>{
  const s=setup();await s.verify();let finish;const jobs=[];s.env.ACCOUNT_EMAIL.send=()=>new Promise(resolve=>{finish=resolve});
  const result=await s.call('/api/auth/forgot-password',{email:'owner@example.com'},null,'POST',{waitUntil:job=>jobs.push(job)});
  assert.deepEqual(result,{ok:true});assert.equal(jobs.length,1);await new Promise(resolve=>setTimeout(resolve,0));finish({messageId:'mock'});await Promise.all(jobs);
  s.env.ACCOUNT_EMAIL.send=async()=>{throw Error('private provider failure')};
  const before=console.error;console.error=()=>{};try{assert.deepEqual(await s.call('/api/auth/forgot-password',{email:'owner@example.com'},null),{ok:true})}finally{console.error=before}
  assert.deepEqual(await s.call('/api/auth/forgot-password',{email:'absent@example.com'},null),{ok:true});s.close();
});

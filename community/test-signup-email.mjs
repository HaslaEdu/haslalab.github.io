// Email-verified password sign-up through the real Worker and SQLite. Mail is a local fixture binding; no provider,
// real address or account is used.
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import worker from './src/index.js';
import {signupCode} from './fixtures/signup-code.mjs';
const AGREE={terms:true,privacy:true,age14:true};
function setup(extra={}){
  const sql=new DatabaseSync(':memory:');for(const name of readdirSync(new URL('./migrations/',import.meta.url)).filter(name=>/^\d{4}_.*\.sql$/.test(name)).sort())sql.exec(readFileSync(new URL('./migrations/'+name,import.meta.url),'utf8'));
  const DB={prepare(query){const statement=sql.prepare(query),make=args=>({bind:(...values)=>make(values),async first(){return statement.get(...args)||null},async all(){return{results:statement.all(...args)}},async run(){return this.execute()},execute(){if(statement.columns().length)return{results:statement.all(...args),meta:{changes:sql.prepare('SELECT changes() n').get().n}};const out=statement.run(...args);return{results:[],meta:{changes:Number(out.changes),last_row_id:Number(out.lastInsertRowid)}}}});return make([])},
    async batch(statements){sql.exec('BEGIN');try{const out=statements.map(s=>s.execute());sql.exec('COMMIT');return out}catch(e){sql.exec('ROLLBACK');throw e}}};
  const mails=[],env={DB,ALLOWED_ORIGINS:'https://haslalab.org',AUTH_EMAIL_ENABLED:'on',AUTH_MAIL_FROM:'accounts@hasla.example',ACCOUNT_EMAIL:{async send(message){mails.push(message);return{messageId:'fixture'}}},...extra};
  let ip=10;
  // a fresh client address per call unless one is named, so the per-IP limits only bite where a test means them to
  const api=async(path,body,{address='192.0.2.'+(ip++),token}={})=>{const response=await worker.fetch(new Request('https://worker.invalid/api'+path,{method:body?'POST':'GET',headers:{Origin:'https://haslalab.org','CF-Connecting-IP':address,...(body?{'Content-Type':'application/json'}:{}),...(token?{Authorization:'Bearer '+token}:{})},body:body?JSON.stringify(body):undefined}),env,{waitUntil(){}});return{status:response.status,data:await response.json()}};
  const mailedCode=()=>mails.at(-1).text.split('\n\n').find(line=>/^\d{6}$/.test(line));
  const form=(name,email,code)=>({username:name,nickname:name+' n',password:'fixture-password',consent:AGREE,email,code});
  return{sql,env,mails,api,mailedCode,form,close(){sql.close()}};
}
const users=s=>s.sql.prepare('SELECT count(*) n FROM users').get().n;

test('a mailed code completes the sign-up; the address is stored verified and the code is spent',async()=>{
  const s=setup();try{
    const sent=await s.api('/signup/email-code',{email:'  Owner@Example.com ',lang:'ko'});
    assert.deepEqual(sent,{status:200,data:{ok:true}});
    assert.equal(s.mails.length,1);const mail=s.mails[0],code=s.mailedCode();
    assert.equal(mail.to,'owner@example.com');assert.match(mail.subject,/가입 인증 코드/);assert.ok(!mail.subject.includes(code));assert.ok(mail.html.includes(code));assert.match(mail.text,/10분/);
    const row=s.sql.prepare('SELECT * FROM signup_email_codes').get();
    assert.equal(row.email,'owner@example.com');assert.notEqual(row.code_hash,code);assert.ok(!JSON.stringify(row).includes(code),'only the digest is kept');assert.equal(row.attempts,0);
    assert.ok(row.expires_at-row.created_at===600);
    const done=await s.api('/signup',s.form('mail_owner','OWNER@example.com',code));
    assert.equal(done.status,200,JSON.stringify(done.data));assert.ok(done.data.token);
    const email=s.sql.prepare('SELECT * FROM account_emails WHERE user_id=?').get(done.data.user.id);
    assert.equal(email.email,'owner@example.com');assert.ok(email.verified_at>0);
    assert.equal(s.sql.prepare('SELECT exam_tokens FROM users WHERE id=?').get(done.data.user.id).exam_tokens,3);
    assert.equal(s.sql.prepare('SELECT count(*) n FROM signup_email_codes').get().n,0);
    // the account sees its address as a verified recovery email, and the code cannot make a second account
    assert.deepEqual((await s.api('/me/security',null,{token:done.data.token})).data,{has_password:true,email:'owner@example.com',email_verified:true,pending_email:null,mail_available:true});
    assert.equal((await s.api('/signup',s.form('mail_second','owner@example.com',code))).data.error,'email_taken');
    // English mail on request
    await s.api('/signup/email-code',{email:'en@example.com',lang:'en'});assert.match(s.mails.at(-1).subject,/Your sign-up code/);assert.match(s.mails.at(-1).text,/10 minutes/);
  }finally{s.close()}
});

test('a sign-up without an address or a code is refused before any account exists; other fields are checked first',async()=>{
  const s=setup();try{
    const {email}=await signupCode(s.sql,'first@example.com');
    assert.equal((await s.api('/signup',{...s.form('no_consent',email,'246810'),consent:undefined})).data.error,'consent_required');
    assert.equal((await s.api('/signup',{...s.form('bad pw',email,'246810')})).data.error,'bad_username');
    assert.equal((await s.api('/signup',s.form('no_email',undefined,'246810'))).data.error,'bad_email');
    assert.equal((await s.api('/signup',s.form('bad_email','not-an-address','246810'))).data.error,'bad_email');
    assert.equal((await s.api('/signup',s.form('no_code',email))).data.error,'code_required');
    assert.equal((await s.api('/signup',s.form('blank_code',email,'  '))).data.error,'code_required');
    assert.equal((await s.api('/signup',s.form('short_code',email,'12345'))).data.error,'code_invalid');
    assert.equal(users(s),0);
    // none of these spent a try
    assert.equal(s.sql.prepare('SELECT attempts FROM signup_email_codes').get().attempts,0);
    // a username clash is reported without touching the code either
    assert.equal((await s.api('/signup',s.form('first_user',email,'246 810'))).status,200);
    await signupCode(s.sql,'other@example.com');
    assert.equal((await s.api('/signup',s.form('first_user','other@example.com','246810'))).data.error,'username_taken');
    assert.equal(s.sql.prepare('SELECT attempts FROM signup_email_codes').get().attempts,0);
  }finally{s.close()}
});

test('a wrong code counts a try; the right one still works within five',async()=>{
  const s=setup();try{
    await s.api('/signup/email-code',{email:'wrong@example.com'});const code=s.mailedCode(),other=code==='000000'?'000001':'000000';
    const r=await s.api('/signup',s.form('wrong_code','wrong@example.com',other));assert.deepEqual([r.status,r.data.error],[400,'code_invalid']);
    assert.equal(s.sql.prepare('SELECT attempts FROM signup_email_codes').get().attempts,1);assert.equal(users(s),0);
    assert.equal((await s.api('/signup',s.form('wrong_code','wrong@example.com',code))).status,200);
  }finally{s.close()}
});

test('an expired code is refused',async()=>{
  const s=setup();try{
    await signupCode(s.sql,'late@example.com',{ttl:-1});
    const r=await s.api('/signup',s.form('late_user','late@example.com','246810'));assert.deepEqual([r.status,r.data.error],[400,'code_expired']);
    assert.equal(users(s),0);
    // a code never sent (or already spent) is simply invalid
    assert.equal((await s.api('/signup',s.form('late_user','never@example.com','246810'))).data.error,'code_invalid');
  }finally{s.close()}
});

test('five wrong tries lock the code, even against the right one; a new code starts over',async()=>{
  const s=setup();try{
    await signupCode(s.sql,'guess@example.com');
    for(let i=1;i<=4;i++)assert.equal((await s.api('/signup',s.form('guesser','guess@example.com',String(100000+i)))).data.error,'code_invalid');
    assert.equal((await s.api('/signup',s.form('guesser','guess@example.com','100005'))).data.error,'code_attempts');
    assert.equal((await s.api('/signup',s.form('guesser','guess@example.com','246810'))).data.error,'code_attempts');
    assert.equal(s.sql.prepare('SELECT attempts FROM signup_email_codes').get().attempts,5);assert.equal(users(s),0);
    await s.api('/signup/email-code',{email:'guess@example.com'});assert.equal(s.sql.prepare('SELECT attempts FROM signup_email_codes').get().attempts,0);
    assert.equal((await s.api('/signup',s.form('guesser','guess@example.com',s.mailedCode()))).status,200);
  }finally{s.close()}
});

test('an address already on an account gets no code and makes no second account',async()=>{
  const s=setup();try{
    const {email}=await signupCode(s.sql,'taken@example.com');const first=await s.api('/signup',s.form('taken_one',email,'246810'));assert.equal(first.status,200);
    const sent=await s.api('/signup/email-code',{email:'TAKEN@example.com'});assert.deepEqual([sent.status,sent.data.error],[409,'email_taken']);assert.equal(s.mails.length,0);
    // a verified recovery address of an older account counts too
    s.sql.prepare('INSERT INTO users(username,nickname,pw,created_at) VALUES(?,?,?,?)').run('legacy_pw','Legacy pw','unused',1);
    s.sql.prepare('INSERT INTO account_emails(user_id,email,verified_at) VALUES(last_insert_rowid(),?,1)').run('legacy@example.com');
    assert.equal((await s.api('/signup/email-code',{email:'legacy@example.com'})).data.error,'email_taken');
    await signupCode(s.sql,'legacy@example.com');
    assert.equal((await s.api('/signup',s.form('taken_two','legacy@example.com','246810'))).data.error,'email_taken');
    assert.equal(users(s),2);
  }finally{s.close()}
});

test('without a mail service the code route answers 503 and keeps nothing; a failed delivery drops its code',async()=>{
  for(const extra of [{AUTH_EMAIL_ENABLED:'off'},{ACCOUNT_EMAIL:undefined},{AUTH_MAIL_FROM:''}]){
    const s=setup(extra);try{
      const r=await s.api('/signup/email-code',{email:'nomail@example.com'});assert.deepEqual([r.status,r.data.error],[503,'mail_unavailable']);
      assert.equal(s.mails.length,0);
    }finally{s.close()}
  }
  const s=setup(),logged=[],error=console.error;s.env.ACCOUNT_EMAIL.send=async()=>{throw Error('provider said nomail@example.com 123456')};
  console.error=(...a)=>logged.push(a.join(' '));
  try{
    const r=await s.api('/signup/email-code',{email:'nomail@example.com'});assert.deepEqual([r.status,r.data.error],[503,'mail_unavailable']);
    assert.equal(s.sql.prepare('SELECT count(*) n FROM signup_email_codes').get().n,0);
    assert.ok(logged.every(line=>!line.includes('nomail')&&!/\d{6}/.test(line)),'neither the address nor a code is logged');
  }finally{console.error=error;s.close()}
});

test('codes are rate-limited per address and per client address; a bad address is refused',async()=>{
  const s=setup();try{
    assert.equal((await s.api('/signup/email-code',{email:'not an address'})).data.error,'bad_email');
    for(let i=0;i<5;i++)assert.equal((await s.api('/signup/email-code',{email:'flood@example.com'})).status,200);
    const sixth=await s.api('/signup/email-code',{email:'FLOOD@example.com'});assert.deepEqual([sixth.status,sixth.data.error],[429,'rate_limited']);
    assert.equal(s.mails.length,5);
    for(let i=0;i<20;i++)assert.equal((await s.api('/signup/email-code',{email:`ip${i}@example.com`},{address:'198.51.100.7'})).status,200);
    assert.equal((await s.api('/signup/email-code',{email:'ip20@example.com'},{address:'198.51.100.7'})).status,429);
    // the limit rows keep the address's digest, not the address
    assert.equal(s.sql.prepare("SELECT count(*) n FROM ratelimits WHERE k LIKE '%@%'").get().n,0);
  }finally{s.close()}
});

test('a new code clears expired ones; the purge leaves live codes; old password accounts without an address still sign in',async()=>{
  const s=setup();try{
    await signupCode(s.sql,'stale@example.com',{ttl:-5});await signupCode(s.sql,'live@example.com');
    await s.api('/signup/email-code',{email:'fresh@example.com'});
    assert.deepEqual(s.sql.prepare('SELECT email FROM signup_email_codes ORDER BY email').all().map(r=>r.email),['fresh@example.com','live@example.com']);
    // an account from before verified sign-up: a password, no address
    const {email}=await signupCode(s.sql,'pw_old@example.com'),made=await s.api('/signup',s.form('pw_old',email,'246810'));assert.equal(made.status,200);
    s.sql.prepare('DELETE FROM account_emails WHERE user_id=?').run(made.data.user.id);
    const login=await s.api('/login',{username:'pw_old',password:'fixture-password'});assert.equal(login.status,200);assert.ok(login.data.token);
    assert.equal((await s.api('/me/security',null,{token:login.data.token})).data.email,null);
  }finally{s.close()}
});

test('a per-IP daily cap bounds how many token-bearing accounts one address can mint in a day',async()=>{
  const s=setup({SIGNUP_DAY_CAP:2});try{
    const ip='203.0.113.9';
    for(let i=0;i<2;i++){
      const r=await s.api('/signup/email-code',{email:`farm${i}@example.com`},{address:ip});assert.equal(r.status,200);
      const made=await s.api('/signup',s.form('farm'+i,`farm${i}@example.com`,s.mailedCode()),{address:ip});
      assert.equal(made.status,200,JSON.stringify(made.data));
    }
    // the code for a third account mails fine, but creating it is refused for this IP today
    await s.api('/signup/email-code',{email:'farm2@example.com'},{address:ip});
    const blocked=await s.api('/signup',s.form('farm2','farm2@example.com',s.mailedCode()),{address:ip});
    assert.equal(blocked.status,429,JSON.stringify(blocked.data));assert.equal(blocked.data.error,'rate_limited');
    // a different address is unaffected
    await s.api('/signup/email-code',{email:'other@example.com'},{address:'203.0.113.10'});
    assert.equal((await s.api('/signup',s.form('other','other@example.com',s.mailedCode()),{address:'203.0.113.10'})).status,200);
  }finally{s.close()}
});

test('linking a provider needs a recent login: a stale session is refused, a fresh one passes',async()=>{
  const s=setup();try{
    await s.api('/signup/email-code',{email:'link@example.com'});
    const made=await s.api('/signup',s.form('linker','link@example.com',s.mailedCode()));assert.equal(made.status,200);
    const token=made.data.token;
    // fresh session → a ticket is minted
    assert.equal((await s.api('/oauth/ticket',{},{token})).status,200);
    // age the session past the window → the same token can no longer graft an identity on
    s.sql.prepare('UPDATE sessions SET created_at=created_at-100000').run();
    const stale=await s.api('/oauth/ticket',{},{token});
    assert.equal(stale.status,403);assert.equal(stale.data.error,'recent_login_required');
  }finally{s.close()}
});

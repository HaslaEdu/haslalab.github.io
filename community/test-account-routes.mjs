// Complete account API journey through the real Worker and real PBKDF2/SQLite.
// Mail is a local fixture binding; external provider and user accounts are never used.
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import worker from './src/index.js';
function setup(){
  const sql=new DatabaseSync(':memory:');for(const name of readdirSync(new URL('./migrations/',import.meta.url)).filter(name=>/^\d{4}_.*\.sql$/.test(name)).sort())sql.exec(readFileSync(new URL('./migrations/'+name,import.meta.url),'utf8'));
  const DB={
    prepare(query){
      const statement=sql.prepare(query),make=args=>({
        bind:(...values)=>make(values),
        async first(){return statement.get(...args)||null},
        async all(){return{results:statement.all(...args)}},
        async run(){return this.execute()},
        execute(){
          if(statement.columns().length)return{results:statement.all(...args),meta:{changes:sql.prepare('SELECT changes() n').get().n}};
          const out=statement.run(...args);return{results:[],meta:{changes:Number(out.changes),last_row_id:Number(out.lastInsertRowid)}};
        },
      });
      return make([]);
    },
    async batch(statements){sql.exec('BEGIN');try{const result=statements.map(s=>s.execute());sql.exec('COMMIT');return result}catch(e){sql.exec('ROLLBACK');throw e}},
  };
  const emails=[],jobs=[],env={DB,ALLOWED_ORIGINS:'https://haslalab.org',AUTH_EMAIL_ENABLED:'on',AUTH_MAIL_FROM:'accounts@hasla.example',ACCOUNT_EMAIL:{async send(message){emails.push(message);return{messageId:'fixture'}}}};
  const api=async(method,path,body,token)=>{const response=await worker.fetch(new Request('https://worker.invalid/api'+path,{method,headers:{Origin:'https://haslalab.org','CF-Connecting-IP':'192.0.2.77',...(body?{'Content-Type':'application/json'}:{}),...(token?{Authorization:'Bearer '+token}:{})},body:body?JSON.stringify(body):undefined}),env,{waitUntil:job=>jobs.push(job)});return{status:response.status,data:await response.json()}};
  const proof=()=>new URLSearchParams(new URL(emails.at(-1).text.split('\n\n').find(value=>value.startsWith('https://'))).hash.split('?')[1]).get('token');
  return{sql,api,emails,jobs,proof,close(){sql.close()}};
}
test('signup/login, old-password check, verified-email reset and revoked sessions work through the complete Worker',async()=>{
  const s=setup();try{
    assert.deepEqual(await s.api('GET','/auth/recovery'),{status:200,data:{mail_available:true}});
    // password sign-up spends a code mailed to its address (signup-email.js); that address becomes the verified recovery email
    assert.deepEqual(await s.api('POST','/signup/email-code',{email:'signup-owner@example.com'}),{status:200,data:{ok:true}});const code=s.emails.at(-1).text.split('\n\n').find(line=>/^\d{6}$/.test(line));
    const signup=await s.api('POST','/signup',{username:'recovery_owner',nickname:'복구 테스트',password:'old-password',consent:{terms:true,privacy:true,age14:true},email:'signup-owner@example.com',code});assert.equal(signup.status,200);const token=signup.data.token;assert.ok(token);assert.equal(signup.data.user.sessionCreatedAt,undefined);
    assert.equal((await s.api('GET','/me/security')).status,401);
    assert.equal((await s.api('POST','/me/password',{password:'new-password'},token)).data.error,'current_password_required');
    assert.equal((await s.api('POST','/me/password',{old:'wrong-password',password:'new-password'},token)).data.error,'bad_current_password');
    assert.equal((await s.api('POST','/me/password',{old:'old-password',password:'old-password'},token)).data.error,'password_unchanged');
    assert.equal((await s.api('GET','/me',undefined,token)).data.user.username,'recovery_owner');
    assert.equal((await s.api('POST','/me/email',{old:'old-password',email:'fixture-owner@example.com'},token)).status,200);
    const pending=(await s.api('GET','/me/security',undefined,token)).data;assert.equal(pending.email,'signup-owner@example.com');assert.equal(pending.pending_email,'fixture-owner@example.com');
    const verify=s.proof();assert.equal((await s.api('POST','/auth/verify-email',{token:verify})).status,200);assert.equal((await s.api('POST','/auth/verify-email',{token:verify})).status,400);
    assert.equal((await s.api('GET','/me/security',undefined,token)).data.email,'fixture-owner@example.com');
    const known=await s.api('POST','/auth/forgot-password',{email:'fixture-owner@example.com'});await Promise.all(s.jobs);const reset=s.proof();
    const unknown=await s.api('POST','/auth/forgot-password',{email:'fixture-absent@example.com'});assert.deepEqual(known,unknown);
    assert.equal((await s.api('POST','/auth/reset-password',{token:reset,password:'old-password'})).data.error,'password_unchanged');
    assert.equal((await s.api('POST','/auth/reset-password',{token:reset,password:'new-password'})).status,200);
    assert.equal((await s.api('GET','/me',undefined,token)).data.user,null);
    assert.equal((await s.api('POST','/login',{username:'recovery_owner',password:'old-password'})).status,401);
    const signed=await s.api('POST','/login',{username:'recovery_owner',password:'new-password'});assert.equal(signed.status,200);
    assert.equal((await s.api('POST','/auth/reset-password',{token:reset,password:'attacker-password'})).status,400);
    assert.equal(s.emails.length,3);
    assert.equal(s.sql.prepare('SELECT count(*) n FROM account_emails').get().n,1);assert.ok(s.sql.prepare('SELECT count(*) n FROM account_email_tokens').get().n>0);
    assert.equal((await s.api('DELETE','/me',undefined,signed.data.token)).status,200);
    assert.equal(s.sql.prepare('SELECT count(*) n FROM account_emails').get().n,0);assert.equal(s.sql.prepare('SELECT count(*) n FROM account_email_tokens').get().n,0);
  }finally{s.close()}
});

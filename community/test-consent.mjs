// Terms/privacy/age/training consent through the real Worker and SQLite. No provider, mail or real account is used.
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import worker from './src/index.js';
import {TERMS_VERSION,readConsent,consentInfo,consentOf,CONSENT_SQL} from './src/consent.js';
import {LAB_TRAIN_SQL} from './src/lab-train.js';
const fail=code=>{throw Object.assign(new Error(code),{code})};
const AGREE={terms:true,privacy:true,age14:true,train:false};
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
  const env={DB,ALLOWED_ORIGINS:'https://haslalab.org'};
  let ip=10;
  // a fresh address per call keeps the per-IP sign-up limit out of the way; `country` stands in for Cloudflare's request.cf
  const api=async(method,path,body,token,country)=>{
    const request=new Request('https://worker.invalid/api'+path,{method,headers:{Origin:'https://haslalab.org','CF-Connecting-IP':'192.0.2.'+(ip++),...(body?{'Content-Type':'application/json'}:{}),...(token?{Authorization:'Bearer '+token}:{})},body:body?JSON.stringify(body):undefined});
    if(country)Object.defineProperty(request,'cf',{value:{country}});
    const response=await worker.fetch(request,env,{waitUntil(){}});return{status:response.status,data:await response.json()};
  };
  return{sql,env,api,close(){sql.close()}};
}
const t=()=>Math.floor(Date.now()/1000);
async function legacyUser(s,name){       // an account from before the terms: a user and a session, no consent row
  const id=Number(s.sql.prepare('INSERT INTO users(username,nickname,pw,created_at,exam_tokens) VALUES(?,?,?,?,5)').run(name,name+' n','unused',t()).lastInsertRowid);
  const token=name.replace(/[^A-Za-z0-9_]/g,'').padEnd(48,'z'),hash=Buffer.from(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(token))).toString('base64url');
  s.sql.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)').run(hash,id,t(),t()+3600);
  return{id,token};
}

test('the validator takes only literal true for terms and privacy, and asks the age only in Korea',()=>{
  assert.throws(()=>readConsent(undefined,null,fail),{code:'consent_required'});
  assert.throws(()=>readConsent({terms:true},null,fail),{code:'consent_required'});
  assert.throws(()=>readConsent({terms:'true',privacy:true},null,fail),{code:'consent_required'});
  assert.throws(()=>readConsent([true],null,fail),{code:'consent_required'});
  assert.throws(()=>readConsent({terms:true,privacy:true},'KR',fail),{code:'age_required'});
  assert.throws(()=>readConsent({terms:true,privacy:true,age14:'yes'},'KR',fail),{code:'age_required'});
  assert.deepEqual(readConsent({terms:true,privacy:true},'US',fail),{age14:false,train:false,country:'US'});
  assert.deepEqual(readConsent({terms:true,privacy:true,age14:true,train:true},'KR',fail),{age14:true,train:true,country:'KR'});
  assert.deepEqual(consentInfo({cf:{country:'KR'}}),{version:TERMS_VERSION,country:'KR',age_required:true});
  assert.deepEqual(consentInfo({}),{version:TERMS_VERSION,country:null,age_required:false});
  assert.deepEqual(consentOf(null),{consent_required:true,train_ok:false});
  assert.deepEqual(consentOf({_consent_version:'2020-01-01',_consent_train:1}),{consent_required:true,train_ok:false});
  assert.deepEqual(consentOf({_consent_version:TERMS_VERSION,_consent_train:1}),{consent_required:false,train_ok:true});
});

test('sign-up needs the terms, privacy and (from Korea) the age; a refusal leaves no account',async()=>{
  const s=setup();try{
    const form={username:'consent_a',nickname:'동의 사용자',password:'fixture-password'};
    assert.equal((await s.api('POST','/signup',form)).data.error,'consent_required');
    assert.equal((await s.api('POST','/signup',{...form,consent:{terms:true}})).data.error,'consent_required');
    assert.equal((await s.api('POST','/signup',{...form,consent:{terms:true,privacy:true}},null,'KR')).data.error,'age_required');
    assert.equal(s.sql.prepare('SELECT count(*) n FROM users').get().n,0);
    assert.deepEqual((await s.api('GET','/consent/info',null,null,'KR')).data,{version:TERMS_VERSION,country:'KR',age_required:true});
    assert.equal((await s.api('GET','/consent/info')).data.age_required,false);
    // outside Korea the age box is not required
    const abroad=await s.api('POST','/signup',{username:'consent_b',nickname:'Abroad user',password:'fixture-password',consent:{terms:true,privacy:true}},null,'US');
    assert.equal(abroad.status,200);assert.equal(abroad.data.user.consent_required,undefined);assert.equal(abroad.data.user.train_ok,false);
    const kr=await s.api('POST','/signup',{...form,consent:{...AGREE,train:true}},null,'KR');assert.equal(kr.status,200);
    const row=s.sql.prepare('SELECT * FROM user_consents WHERE user_id=?').get(kr.data.user.id);
    assert.equal(row.terms_version,TERMS_VERSION);assert.equal(row.age_ok,1);assert.equal(row.train_ok,1);assert.equal(row.country,'KR');assert.ok(row.agreed_at>0);
    const me=(await s.api('GET','/me',null,kr.data.token)).data.user;assert.equal(me.consent_required,undefined);assert.equal(me.train_ok,true);
  }finally{s.close()}
});

test('an account without current consent is told so, cannot start grading, and agrees through /me/consent',async()=>{
  const s=setup();try{
    const u=await legacyUser(s,'legacy_one');
    const me=(await s.api('GET','/me',null,u.token)).data.user;assert.equal(me.consent_required,true);assert.equal(me.train_ok,false);
    assert.equal((await s.api('GET','/me/overview',null,u.token)).data.user.consent_required,true);
    assert.equal((await s.api('GET','/lab/bootstrap',null,u.token)).data.user.consent_required,true);
    const start={comp:'ipho',year:2019,tasks:['T1']};
    assert.deepEqual(await s.api('POST','/lab/start',start,u.token),{status:403,data:{error:'consent_required'}});
    assert.equal((await s.api('POST','/lab/contest/start',{},u.token)).data.error,'consent_required');
    assert.equal((await s.api('POST','/lab/sessions/1/pay',{},u.token)).data.error,'consent_required');
    assert.equal((await s.api('POST','/lab/sessions/1/submit',{},u.token)).data.error,'consent_required');
    assert.notEqual((await s.api('POST','/lab/sessions/1/submit',{grade:false},u.token)).data.error,'consent_required');   // ending ungraded is not grading
    assert.equal((await s.api('POST','/me/consent/train',{train:true},u.token)).data.error,'consent_required');
    assert.equal((await s.api('POST','/me/consent',{consent:{terms:true,privacy:true}},u.token,'KR')).data.error,'age_required');
    const agreed=await s.api('POST','/me/consent',{consent:{terms:true,privacy:true}},u.token);assert.equal(agreed.status,200);assert.equal(agreed.data.user.consent_required,undefined);
    assert.equal((await s.api('GET','/me',null,u.token)).data.user.consent_required,undefined);
    assert.notEqual((await s.api('POST','/lab/start',start,u.token)).data.error,'consent_required');
    // a new terms version asks again
    s.sql.prepare("UPDATE user_consents SET terms_version='2020-01-01' WHERE user_id=?").run(u.id);
    assert.equal((await s.api('GET','/me',null,u.token)).data.user.consent_required,true);
    assert.equal((await s.api('GET','/me/consent',null,u.token)).data.consent_required,true);
  }finally{s.close()}
});

test('training consent toggles; withdrawing deletes only this user\'s captured rows; capture rows expire after a year',async()=>{
  const s=setup();try{
    const a=await s.api('POST','/signup',{username:'train_a',nickname:'Train A',password:'fixture-password',consent:{...AGREE,train:true}});
    const b=await s.api('POST','/signup',{username:'train_b',nickname:'Train B',password:'fixture-password',consent:{...AGREE,train:true}});
    s.sql.exec(LAB_TRAIN_SQL);
    const sitting=id=>Number(s.sql.prepare("INSERT INTO lab_sessions(user_id,exam_key,comp,year,tasks,started_at,ended_at,scan_until,upload_hash,status,created_at) VALUES(?,'ipho2019','ipho',2019,'[\"T1\"]',?,?,0,'void:'||random(),'graded',?)").run(id,t(),t(),t()).lastInsertRowid);
    const sa=sitting(a.data.user.id),sb=sitting(b.data.user.id);
    for(const sid of [sa,sb])s.sql.prepare("INSERT INTO lab_train(kind,session_id,task,input,target) VALUES('grade',?,'T1','in','out')").run(sid);
    assert.equal((await s.api('POST','/me/consent/train',{train:'no'},a.data.token)).data.error,'bad_train');
    const off=await s.api('POST','/me/consent/train',{train:false},a.data.token);assert.deepEqual(off.data,{ok:true,train_ok:false});
    assert.equal(s.sql.prepare('SELECT count(*) n FROM lab_train WHERE session_id=?').get(sa).n,0);
    assert.equal(s.sql.prepare('SELECT count(*) n FROM lab_train WHERE session_id=?').get(sb).n,1);
    assert.equal((await s.api('GET','/me',null,a.data.token)).data.user.train_ok,false);
    const status=(await s.api('GET','/me/consent',null,a.data.token)).data;assert.equal(status.train_ok,false);assert.equal(status.consent_required,false);assert.ok(status.train_at>0);
    assert.equal((await s.api('POST','/me/consent/train',{train:true},a.data.token)).data.train_ok,true);
    assert.equal((await s.api('GET','/me',null,a.data.token)).data.user.train_ok,true);
    // the 15-minute cron removes rows older than a year
    s.sql.prepare("INSERT INTO lab_train(kind,session_id,task,input,target,created_at) VALUES('grade',?,'T1','old','old',?)").run(sb,t()-366*86400);
    // and rate-limit rows (they hold IP addresses) once they are two days old
    s.sql.prepare('INSERT INTO ratelimits(k,start,n) VALUES(?,?,1)').run('signup:198.51.100.7',t()-3*86400);
    const work=[];await worker.scheduled({scheduledTime:15*60000*2000000},s.env,{waitUntil:p=>work.push(p)});await Promise.all(work);
    assert.deepEqual(s.sql.prepare('SELECT input FROM lab_train ORDER BY id').all().map(r=>r.input),['in']);
    assert.equal(s.sql.prepare("SELECT count(*) n FROM ratelimits WHERE k='signup:198.51.100.7'").get().n,0);
    assert.ok(s.sql.prepare('SELECT count(*) n FROM ratelimits').get().n>0,'current windows stay');
  }finally{s.close()}
});

test('account deletion removes the consent row, training copies and bench rows of the sittings',async()=>{
  const s=setup();try{
    const a=await s.api('POST','/signup',{username:'gone_a',nickname:'Gone A',password:'fixture-password',consent:{...AGREE,train:true}});
    s.sql.exec(LAB_TRAIN_SQL);
    s.sql.exec("CREATE TABLE IF NOT EXISTS lab_bench (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, spec TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', output TEXT, created_at INTEGER NOT NULL DEFAULT (unixepoch()), finished_at INTEGER)");
    const sid=Number(s.sql.prepare("INSERT INTO lab_sessions(user_id,exam_key,comp,year,tasks,started_at,ended_at,scan_until,upload_hash,status,created_at) VALUES(?,'ipho2019','ipho',2019,'[\"T1\"]',?,?,0,'void:'||random(),'graded',?)").run(a.data.user.id,t(),t(),t()).lastInsertRowid);
    s.sql.prepare("INSERT INTO lab_train(kind,session_id,task,input,target) VALUES('grade',?,'T1','in','out')").run(sid);
    s.sql.prepare("INSERT INTO lab_bench(session_id,spec) VALUES(?,'{}')").run(sid);
    assert.equal((await s.api('DELETE','/me',null,a.data.token)).status,200);
    for(const table of ['user_consents','lab_train','lab_bench','lab_sessions'])assert.equal(s.sql.prepare(`SELECT count(*) n FROM ${table}`).get().n,0,table);
  }finally{s.close()}
});

test('a social sign-up agrees to the terms when it chooses its username',async()=>{
  const s=setup();try{
    // the state OAuth leaves behind: a ~pending_ account with a fresh session and no consent
    const u=await legacyUser(s,'~pending_fixture');
    const me=(await s.api('GET','/me',null,u.token)).data.user;assert.equal(me.username_required,true);assert.equal(me.consent_required,true);
    assert.equal((await s.api('GET','/consent/info',null,u.token)).status,200);
    assert.equal((await s.api('POST','/me/username',{username:'chosen_social'},u.token)).data.error,'consent_required');
    assert.equal((await s.api('POST','/me/username',{username:'chosen_social',consent:{terms:true,privacy:true}},u.token,'KR')).data.error,'age_required');
    assert.equal(s.sql.prepare('SELECT username FROM users WHERE id=?').get(u.id).username,'~pending_fixture');   // nothing was claimed
    const done=await s.api('POST','/me/username',{username:'chosen_social',consent:AGREE},u.token,'KR');
    assert.equal(done.status,200);assert.equal(done.data.user.username,'chosen_social');assert.equal(done.data.user.consent_required,undefined);
    assert.equal(s.sql.prepare('SELECT age_ok FROM user_consents WHERE user_id=?').get(u.id).age_ok,1);
  }finally{s.close()}
});

test('the schema is the one the module creates at run time',()=>{
  const sql=new DatabaseSync(':memory:');sql.exec('CREATE TABLE users(id INTEGER PRIMARY KEY)');sql.exec(CONSENT_SQL);sql.exec(CONSENT_SQL);
  assert.deepEqual(sql.prepare('PRAGMA table_info(user_consents)').all().map(c=>c.name),['user_id','terms_version','age_ok','train_ok','country','agreed_at','train_at']);sql.close();
});

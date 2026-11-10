// Admin statistics through the real Worker and SQLite: only an admin session reads them, admin accounts are left
// out of the counts, and the answer carries counts only (no username, nickname or answer text).
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import worker from './src/index.js';
const origin='https://haslalab.org',T=Math.floor(Date.now()/1000);
const b64u=bytes=>Buffer.from(bytes).toString('base64url');
const hash=async token=>b64u(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(token))));
async function setup(){
 const sql=new DatabaseSync(':memory:');for(const name of readdirSync(new URL('./migrations/',import.meta.url)).filter(name=>/^\d{4}_.*\.sql$/.test(name)).sort())sql.exec(readFileSync(new URL('./migrations/'+name,import.meta.url),'utf8'));
 const DB={prepare(query){const statement=sql.prepare(query),make=args=>({bind:(...values)=>make(values),async first(){return statement.get(...args)||null},async all(){return{results:statement.all(...args)}},async run(){return this.execute()},execute(){if(statement.columns().length)return{results:statement.all(...args),meta:{changes:sql.prepare('SELECT changes() n').get().n}};const out=statement.run(...args);return{results:[],meta:{changes:Number(out.changes),last_row_id:Number(out.lastInsertRowid)}}}});return make([])},async batch(statements){sql.exec('BEGIN');try{const out=statements.map(s=>s.execute());sql.exec('COMMIT');return out}catch(e){sql.exec('ROLLBACK');throw e}}};
 const env={DB,ALLOWED_ORIGINS:origin};
 const user=(id,username,{role='user',deleted=0,pw='x',at=T-3600}={})=>sql.prepare('INSERT INTO users(id,username,nickname,pw,role,created_at,deleted) VALUES(?,?,?,?,?,?,?)').run(id,username,'nick_'+username,pw,role,at,deleted);
 user(1,'boss_account',{role:'admin'});user(2,'student_one');user(3,'student_two',{pw:null});user(4,'gone_student',{deleted:1,at:T-40*86400});user(5,'~pending_abc',{pw:null});
 sql.prepare('INSERT INTO identities(provider,sub,user_id,created_at) VALUES(?,?,?,?)').run('google','g-3',3,T);
 sql.prepare('INSERT INTO identities(provider,sub,user_id,created_at) VALUES(?,?,?,?)').run('discord','d-5',5,T);
 let labN=0;const lab=(uid,status,key='ipho2011_E2')=>sql.prepare(`INSERT INTO lab_sessions(user_id,exam_key,comp,year,tasks,started_at,ended_at,scan_until,upload_hash,status,created_at,graded_at) VALUES(?,?,'ipho',2011,'[]',?,?,?,?,?,?,?)`).run(uid,key,T,T,T,'h'+(++labN),status,T-600,status==='graded'?T-60:null);
 lab(1,'graded');lab(1,'graded');lab(2,'graded');lab(2,'graded','apho2023_E1');lab(3,'cancelled');
 const tokens={};for(const [id,name] of [[1,'admin'],[2,'student']]){tokens[name]=name.padEnd(32,'k');sql.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)').run(await hash(tokens[name]),id,T,T+86400);}
 const get=async token=>{const r=await worker.fetch(new Request('https://worker.invalid/api/admin/stats',{headers:{Origin:origin,'CF-Connecting-IP':'192.0.2.44',...(token?{Authorization:'Bearer '+token}:{})}}),env,{waitUntil(){}});return{status:r.status,cache:r.headers.get('Cache-Control'),text:await r.text()}};
 const visit=async({first=0,country='KR',region='Seoul',ua='Mozilla/5.0 (Macintosh)',ip='192.0.2.50'}={})=>{const ctx={tasks:[],waitUntil(p){this.tasks.push(p)}};const r=await worker.fetch(new Request('https://worker.invalid/api/visit',{method:'POST',body:JSON.stringify({first}),headers:{Origin:origin,'Content-Type':'text/plain','User-Agent':ua,'CF-Connecting-IP':ip,...(country?{'CF-IPCountry':country}:{}),...(region?{'X-Hasla-Region':encodeURIComponent(region)}:{})}}),env,ctx);await Promise.all(ctx.tasks);return r.status};
 return{get,visit,sql,tokens,close(){sql.close()}};
}

test('admin stats: only an admin session reads them',async()=>{
 const s=await setup();try{
  assert.ok([401,403].includes((await s.get()).status),'no session');
  assert.equal((await s.get(s.tokens.student)).status,403,'a student');
  const ok=await s.get(s.tokens.admin);assert.equal(ok.status,200);assert.match(ok.cache||'',/no-store/);
 }finally{s.close()}
});

test('admin stats: people leave out admin accounts; grading, sign-in methods and the daily series add up',async()=>{
 const s=await setup();try{
  const r=await s.get(s.tokens.admin),d=JSON.parse(r.text);
  assert.equal(d.users.created,5);assert.equal(d.users.active,4);assert.equal(d.users.deleted,1);
  assert.equal(d.users.admins,1);assert.equal(d.users.people,3,'students 2, 3 and the pending one');
  assert.equal(d.users.pending_username,1);assert.equal(d.users.new_period,3,'the deleted account joined before the period; the admin is not counted');
  assert.deepEqual(d.users.methods,{password:1,google:1,discord:1});
  assert.equal(d.lab.graded,2,'the admin’s two graded exams are left out');assert.equal(d.lab.graded_people,1);assert.equal(d.graded.people,1);
  assert.deepEqual(d.lab.exams.map(x=>x.exam_key).sort(),['apho2023_E1','ipho2011_E2']);
  assert.equal(d.lab.statuses.graded.all,4);assert.equal(d.lab.statuses.graded.people,2);
  assert.equal(d.series.length,30);assert.equal(d.series.at(-1).day,d.today);
  assert.equal(d.series.reduce((a,x)=>a+x.lab,0),2);assert.equal(d.series.reduce((a,x)=>a+x.signups,0),3);
  assert.deepEqual(d.ai,{asked:0,guests:0,members:0,member_people:0,asked_7d:0,blocked:0},'no Hasla AI table yet reads as zero');
  for(const word of ['boss_account','student_one','nick_student_one','pending_abc'])assert.ok(!r.text.includes(word),'no account name in the answer: '+word);
 }finally{s.close()}
});

test('visits: counted by country and region only, once a day per browser; bots and floods are not counted',async()=>{
 const s=await setup();try{
  assert.equal(await s.visit({first:1}),204);assert.equal(await s.visit(),204);
  await s.visit({first:1,region:'Gyeonggi-do'});await s.visit({first:1,country:'US',region:'California',ip:'192.0.2.51'});
  await s.visit({first:1,country:'',region:''});
  await s.visit({first:1,ua:'Googlebot/2.1'});await s.visit({first:1,ua:''});
  const kept=s.sql.prepare('SELECT * FROM visit_days ORDER BY country,region').all();
  assert.deepEqual(kept.map(r=>[r.country,r.region,r.views,r.visitors]),[['KR','Gyeonggi-do',1,1],['KR','Seoul',2,1],['US','California',1,1],['XX','',1,1]]);
  assert.deepEqual(Object.keys(kept[0]).sort(),['country','day','region','views','visitors'],'no address or identifier column');
  for(let i=0;i<125;i++)await s.visit({ip:'192.0.2.99'});
  assert.equal(s.sql.prepare("SELECT views FROM visit_days WHERE region='Seoul'").get().views,2+120,'one address counts at most 120 an hour');
  const d=JSON.parse((await s.get(s.tokens.admin)).text).visits;
  assert.equal(d.visitors,4);assert.equal(d.countries,2,'unknown is not a country');assert.equal(d.visitors_today,4);
  assert.deepEqual(d.by_country.map(x=>x.country),['KR','US','XX']);
  assert.deepEqual(d.by_region.map(x=>x.region).sort(),['California','Gyeonggi-do','Seoul'],'the unknown country has no region');
  assert.equal(d.by_region.find(x=>x.region==='Seoul').views,122);
 }finally{s.close()}
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import {createRequire} from 'node:module';
import {publishWeeklyContent,migrateMonthlyPeriod,GREENHOUSE_MONTHLY_CONTENT,GREENHOUSE_PUBLICATION_ID,validateContent} from './src/weekly-content.js';
import {retireIntroMonthlyProblems} from './src/monthly-answers.js';
import {ensureAstronomyRevision,ASTRONOMY_REVISION_CONTENT,ASTRONOMY_REVISION_ID} from './src/astronomy-revision.js';
import {validateReviewedSources} from './weekly/build-seed.mjs';
const require=createRequire(import.meta.url),katex=require('../vendor/katex/katex.min.js');

function database(){
  const sql=new DatabaseSync(':memory:');
  for(const file of readdirSync(new URL('./migrations/',import.meta.url)).filter(name=>/^00(?:0[1-9]|1[01])_.*\.sql$/.test(name)).sort())sql.exec(readFileSync(new URL('./migrations/'+file,import.meta.url),'utf8'));
  let failMarker=false;
  const db={prepare(query){const st=sql.prepare(query),make=args=>({query,bind:(...values)=>make(values),async first(){return st.get(...args)||null;},async all(){return{results:st.all(...args)};},async run(){return this.runSync();},runSync(){if(failMarker&&query.includes('INSERT INTO weekly_publications(id,problems,created_at)')){failMarker=false;throw Error('test marker interruption');}if(st.columns().length)return{results:st.all(...args)};const r=st.run(...args);return{meta:{changes:r.changes,last_row_id:Number(r.lastInsertRowid)}};}});return make([]);},async batch(statements){sql.exec('BEGIN');try{const value=statements.map(st=>st.runSync());sql.exec('COMMIT');return value;}catch(e){sql.exec('ROLLBACK');throw e;}}};
  return{sql,db,interrupt:()=>{failMarker=true;}};
}
async function original(db){await publishWeeklyContent(db);await migrateMonthlyPeriod(db);await retireIntroMonthlyProblems(db);await publishWeeklyContent(db,GREENHOUSE_MONTHLY_CONTENT,GREENHOUSE_PUBLICATION_ID);}

test('the deployment seed check validates original publications and the separate astronomy revision',()=>{
  const {publications,revisions}=validateReviewedSources();
  assert.equal(publications.length,2);
  assert.equal(publications.reduce((sum,source)=>sum+source.problems.length,0),4);
  assert.equal(revisions.length,1);
  assert.deepEqual(revisions[0],ASTRONOMY_REVISION_CONTENT);
  assert.equal(publications[1].problems[0].subject,'physics');
  assert.equal(revisions[0].problems[0].subject,'astronomy');
});

test('the astronomy revision uses ten lettered quantitative tasks while retaining durable criterion IDs',()=>{
  validateContent(ASTRONOMY_REVISION_CONTENT);const p=ASTRONOMY_REVISION_CONTENT.problems[0];
  assert.equal(p.subject,'astronomy');assert.equal(p.points,100);
  assert.deepEqual(p.rubric.map(c=>c.id),['16','17','18','19','20a','20b','20c','21a','21b','21c']);
  for(const language of ['ko','en']){
    const body=p['body_'+language],model=p['model_'+language];
    assert.deepEqual([...body.matchAll(/^### \(([a-j])\)/gm)].map(m=>m[1]),[...'abcdefghij']);
    assert.deepEqual([...model.matchAll(/^## \(([a-j])\)/gm)].map(m=>m[1]),[...'abcdefghij']);
    assert.ok(!/논제\s*\d|Question\s*\d|설명하라|논하라|\bExplain\b/i.test(body));
    const b=body.split('### (b)')[1].split('### (c)')[0];assert.ok(!b.includes('cos'));
    assert.ok(body.includes('0.010'));assert.ok(body.includes('F_{disk}'));assert.ok(body.includes('P_{disk}/P_{rec}'));
    assert.ok(!/[\u0000-\u0008\u000b-\u001f]/.test(body+model));
    let count=0;for(const field of[body,model])for(const match of field.matchAll(/\$\$([\s\S]*?)\$\$|\$([^$\n]+)\$/g)){katex.renderToString(match[1]||match[2],{throwOnError:true,displayMode:!!match[1]});count++;}assert.ok(count>100);
  }
  assert.equal(GREENHOUSE_MONTHLY_CONTENT.problems[0].subject,'physics','original publication is a historical record');
  assert.match(GREENHOUSE_MONTHLY_CONTENT.problems[0].body_ko,/논제 17/);
});

test('a one-time live revision changes content and subject without touching accepted answers or scores',async()=>{
  const{sql,db}=database();try{
    await original(db);const p=sql.prepare("SELECT * FROM problems WHERE week='2026-11' AND no=4").get();
    sql.prepare("INSERT INTO users(id,username,nickname,pw,created_at) VALUES(1,'revision-owner','Owner','unused',1)").run();
    sql.prepare(`INSERT INTO submissions(id,problem_id,user_id,answer,via_ocr,status,score,detail,in_week,created_at,graded_at)
      VALUES(1,?,1,'original private answer',1,'graded',85,'{"scores":[{"id":"16","got":14}]}',1,1,1)`).run(p.id);
    const sheet=JSON.stringify({version:'2026-11-v1',parts:[{id:'16',answer:'old answer',working:'old proof'}]});
    sql.prepare(`INSERT INTO monthly_answer_requests(user_id,problem_id,request_id,submission_id,answer_sheet,answer_text,via_ocr,created_at)
      VALUES(1,?,'immutable-request-00000001',1,?,'original private answer',1,1)`).run(p.id,sheet);
    const before={sub:sql.prepare('SELECT * FROM submissions').get(),request:sql.prepare('SELECT * FROM monthly_answer_requests').get(),others:sql.prepare('SELECT * FROM problems WHERE id<>? ORDER BY id').all(p.id)};
    const changed=await ensureAstronomyRevision(db);assert.equal(changed.applied,true);assert.equal(changed.changed,1);
    const after=sql.prepare('SELECT * FROM problems WHERE id=?').get(p.id);assert.equal(after.subject,'astronomy');assert.match(after.body_ko,/### \(j\)/);
    assert.equal(after.opens_at,p.opens_at);assert.equal(after.closes_at,p.closes_at);assert.equal(after.source,p.source);
    assert.deepEqual(sql.prepare('SELECT * FROM submissions').get(),before.sub);assert.deepEqual(sql.prepare('SELECT * FROM monthly_answer_requests').get(),before.request);
    assert.deepEqual(sql.prepare('SELECT * FROM problems WHERE id<>? ORDER BY id').all(p.id),before.others);
    sql.prepare("UPDATE problems SET body_ko='later administrator edit',subject='maintained' WHERE id=?").run(p.id);
    const repeated=await ensureAstronomyRevision(db,{});assert.equal(repeated.applied,false);
    assert.equal(sql.prepare('SELECT body_ko FROM problems WHERE id=?').get(p.id).body_ko,'later administrator edit');
  }finally{sql.close();}
});

test('missing targets are not cached and unrelated ID7 does not receive the astronomy update',async()=>{
  const{sql,db}=database();try{
    const first=await ensureAstronomyRevision(db);assert.equal(first.ready,false);
    await publishWeeklyContent(db);await migrateMonthlyPeriod(db);await retireIntroMonthlyProblems(db);
    sql.prepare(`INSERT INTO problems(id,week,no,kind,subject,level,points,title_ko,title_en,body_ko,body_en,opens_at,closes_at,created_at)
      VALUES(7,'2027-03',1,'essay','physics',1,100,'other','Other','old','Old',1,2,1)`).run();
    await publishWeeklyContent(db,GREENHOUSE_MONTHLY_CONTENT,GREENHOUSE_PUBLICATION_ID);
    const result=await ensureAstronomyRevision(db);assert.equal(result.applied,true);
    assert.equal(sql.prepare('SELECT subject FROM problems WHERE id=7').get().subject,'physics');
    const target=sql.prepare("SELECT * FROM problems WHERE week='2026-11' AND no=4").get();assert.notEqual(target.id,7);assert.equal(target.subject,'astronomy');
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM weekly_publications WHERE id=?').get(ASTRONOMY_REVISION_ID).n,1);
  }finally{sql.close();}
});

test('the content update and durable marker roll back together and failed initialization can retry',async()=>{
  const{sql,db,interrupt}=database();try{
    await original(db);interrupt();await assert.rejects(ensureAstronomyRevision(db),/test marker interruption/);
    assert.equal(sql.prepare("SELECT subject FROM problems WHERE week='2026-11' AND no=4").get().subject,'physics');
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM weekly_publications WHERE id=?').get(ASTRONOMY_REVISION_ID).n,0);
    assert.equal((await ensureAstronomyRevision(db)).applied,true);
    await Promise.all(Array.from({length:4},()=>ensureAstronomyRevision(db,{})));
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM weekly_publications WHERE id=?').get(ASTRONOMY_REVISION_ID).n,1);
  }finally{sql.close();}
});

test('new sensitivity and flux-average references follow independent calculations',()=>{
  const S=5.67e-8*5770**4*(6.96e8/1.5e11)**2,eps=23.5*Math.PI/180,sigma=5.67e-8;
  const temperature=(sw,lw)=>((1+sw)*S/(2*sigma*(1+lw)))**.25,T=temperature(.9,.2),step=1e-5;
  assert.ok(Math.abs((temperature(.9+step,.2)-temperature(.9-step,.2))/(2*step)-T/(4*1.9))<1e-6);
  assert.ok(Math.abs((temperature(.9,.2+step)-temperature(.9,.2-step))/(2*step)+T/(4*1.2))<1e-6);
  assert.ok(Math.abs(T*.01/(4*1.9)-.4878168539054054)<1e-9);
  assert.ok(Math.abs(1-Math.cos(2*eps)-.3180016399375015)<1e-12);
  let integral=0;const n=4096;for(let k=0;k<n;k++)integral+=S/2*(Math.cos(eps)**2+Math.sin(eps)**2*Math.cos(2*Math.PI*(k+.5)/n))/n;
  assert.ok(Math.abs(integral-S*Math.cos(eps)**2/2)<1e-9);
  assert.ok(Math.abs(integral/((1-.3)*S/4)-2*Math.cos(eps)**2/(1-.3))<1e-12);
});

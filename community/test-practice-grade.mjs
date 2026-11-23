import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createGradeRouter, bandOf, cleanPages, cleanRubric, scoreOf, gradePolicy, gradeProvider} from './src/practice-grade.js';
import {createLearnRouter, GRADE_FREE, GRADE_PLAN} from './src/learn-services.js';
import {PRACTICE_SCHEMA} from './src/practice-progress.js';

class H extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
const bad=code=>{throw new H(400,code);};
const RUBRIC='{"items":[{"id":"a","desc":"Energy conservation $mgh=\\\\frac12 mv^2$","pts":3},{"id":"b","desc":"Sets up with $h=5$ m","pts":3},{"id":"c","desc":"Final $v\\\\approx 9.9$ m/s","pts":4}]}';
function setup({ai=()=>RUBRIC,vision}={}){
  const db=new DatabaseSync(':memory:');
  const D1={async batch(s){const out=[];for(const x of s)out.push(await x.all());return out;},prepare(sql){let args=[];return{bind(...a){args=a;return this;},async first(){return db.prepare(sql).get(...args)||null;},async all(){return{results:db.prepare(sql).all(...args)};},async run(){const r=db.prepare(sql).run(...args);return{meta:{last_row_id:Number(r.lastInsertRowid)}};}};}};
  let t=1_800_000_000;const aiCalls=[],visionCalls=[],counts=new Map();
  const AI={async run(model,input){aiCalls.push(input);return{response:ai(input)};}};
  const limit=async(env,key,max)=>{if(!key.startsWith('preport'))return;const n=(counts.get(key)||0)+1;counts.set(key,n);if(n>max)throw new H(429,'rate_limited');};
  const deps={HttpError:H,bad,now:()=>t,clientIp:req=>req?.ip||'1.2.3.4',needUser:u=>{if(!u)throw new H(401,'login_required');return u;},limit};
  const fakeVision=async(env,args)=>{visionCalls.push(args);return {raw:(vision||(()=>({transcript:'$v=\\sqrt{2gh}=9.9$',legible:true,items:[{id:'a',got:3,note:'ok'},{id:'b',got:3,note:'ok'},{id:'c',got:1,note:'unit missing'}],feedback:'Good.'})))(args)};};
  const grade=createGradeRouter({...deps,vision:fakeVision}),learn=createLearnRouter(deps);
  const env={DB:D1,AI,GEMINI_API_KEY:'test-dummy'};
  const route=async(p,m,b,me,req)=>{const r=await grade(p,m,b,me,req,env);return r!==undefined?r:learn(p,m,b,me,req,env);};
  return {db,env,aiCalls,visionCalls,route,tick:s=>{t+=s;},now:()=>t};
}
const me={id:7},staff={id:1,role:'admin'};
const fails=async(p,code)=>assert.rejects(p,e=>e.code===code);
/* a tiny but real JPEG header followed by padding */
const jpeg=(n=200)=>'data:image/jpeg;base64,'+Buffer.concat([Buffer.from([0xff,0xd8,0xff,0xe0]),Buffer.alloc(n)]).toString('base64');
const item=(over={})=>({id:'ap1-u1-001',source:'track',q:'A ball falls from $5$ m. Find its speed at the floor.',answer:'9.9 m/s',sol:'$v=\\sqrt{2gh}$',...over});
const body=(over={})=>({item:item(over.item),pages:[jpeg()],level:'L1',lang:'ko',...over,item:item(over.item)});

test('bands at the edges',()=>{
  assert.equal(bandOf(0.70),'pass');assert.equal(bandOf(0.69),'partial');
  assert.equal(bandOf(0.40),'partial');assert.equal(bandOf(0.39),'retry');
  const r=[{id:'a',desc:'x',pts:5},{id:'b',desc:'y',pts:5}];
  assert.equal(scoreOf(r,{items:[{id:'a',got:5},{id:'b',got:2}]}).band,'pass');
  assert.equal(scoreOf(r,{items:[{id:'a',got:4},{id:'b',got:2.9}]}).band,'partial');
  assert.equal(scoreOf(r,{items:[{id:'a',got:4}]}).band,'partial','a missing item scores 0');
  assert.equal(scoreOf(r,{items:[{id:'a',got:3.9},{id:'zz',got:99}]}).band,'retry','unknown ids are ignored');
  assert.equal(scoreOf(r,{items:[{id:'a',got:99},{id:'b',got:-3}]}).score,5,'marks are clamped to each item');
});

test('rubrics are 3-6 items scaled to the points',()=>{
  assert.equal(cleanRubric({items:[{desc:'a',pts:1},{desc:'b',pts:1}]},10),null);
  assert.equal(cleanRubric({items:[{desc:'a',pts:1},{desc:'',pts:1},{desc:'c',pts:1}]},10),null);
  const r=cleanRubric({items:[{id:'x',desc:'a',pts:1},{id:'x',desc:'b',pts:1},{desc:'c',pts:1}]},10);
  assert.equal(r.reduce((a,x)=>a+x.pts,0),10);assert.equal(new Set(r.map(x=>x.id)).size,3);
  assert.match(gradePolicy('ko'),/R13[\s\S]*Korean/);
  assert.equal(gradeProvider({}),null);assert.equal(gradeProvider({GEMINI_API_KEY:'k'}),'gemini');assert.equal(gradeProvider({DEEPSEEK_API_KEY:'k'}),'deepseek');
});

test('bad pages are rejected',async()=>{
  assert.equal(cleanPages([]),null);
  assert.equal(cleanPages(new Array(5).fill(jpeg())),null,'at most 4 pages');
  assert.equal(cleanPages(['https://example.com/a.jpg']),null,'no remote images');
  assert.equal(cleanPages(['data:image/jpeg;base64,'+Buffer.from('<svg>'+'x'.repeat(200)).toString('base64')]),null,'the bytes must be an image');
  assert.equal(cleanPages([jpeg(1.6*1024*1024)]),null,'at most 1.5 MB');
  assert.equal(cleanPages(['data:image/gif;base64,R0lGODlh']),null);
  assert.equal(cleanPages([jpeg(),jpeg()]).length,2);
  const {route,visionCalls}=setup();
  await fails(route('/api/learn/grade','POST',{...body(),pages:['nope']},me),'bad_pages');
  await fails(route('/api/learn/grade','POST',{...body(),item:{id:'x',source:'nowhere',q:'q'}},me),'bad_item');
  await fails(route('/api/learn/grade','POST',{item:{id:'ok-1',source:'track',q:''},pages:[jpeg()]},me),'bad_item');
  await fails(route('/api/learn/grade','POST',body(),null),'login_required');
  assert.equal(visionCalls.length,0);
  assert.equal((await route('/api/learn/plan','GET',null,me)).gradeLeft,GRADE_FREE,'nothing was counted');
});

test('the day has a quota, a plan has more, and a failure gives the grading back',async()=>{
  let mode='ok';
  const {route,db,now}=setup({vision:()=>{if(mode==='throw')throw Object.assign(new Error('x'),{code:'vision_provider_failed'});
    if(mode==='blank')return {transcript:'',legible:false,items:[],feedback:''};
    return {transcript:'v=9.9',legible:true,items:[{id:'a',got:3,note:''},{id:'b',got:3,note:''},{id:'c',got:4,note:''}],feedback:'Well done.'};}});
  const first=await route('/api/learn/grade','POST',body(),me);
  assert.equal(first.score,10);assert.equal(first.max,10);assert.equal(first.fraction,1);assert.equal(first.band,'pass');assert.equal(first.left,GRADE_FREE-1);
  assert.equal(first.items.length,3);assert.equal(first.items[2].desc.includes('9.9'),true);assert.equal(typeof first.attempt_id,'number');
  mode='throw';
  await fails(route('/api/learn/grade','POST',body(),me),'grade_failed');
  mode='blank';
  await fails(route('/api/learn/grade','POST',body(),me),'unreadable');
  assert.equal((await route('/api/learn/plan','GET',null,me)).gradeLeft,GRADE_FREE-1,'both failures were given back');
  mode='ok';
  for(let i=1;i<GRADE_FREE;i++)await route('/api/learn/grade','POST',body(),me);
  await fails(route('/api/learn/grade','POST',body(),me),'grade_limit');
  db.prepare('INSERT INTO entitlements(user_id,kind,starts_at,ends_at,source,created_at) VALUES(?,?,?,?,?,?)').run(7,'plus',now()-10,null,'test',now());
  assert.equal((await route('/api/learn/plan','GET',null,me)).gradeLeft,GRADE_PLAN-GRADE_FREE);
  assert.equal((await route('/api/learn/grade','POST',body(),me)).left,GRADE_PLAN-GRADE_FREE-1);
  const rows=db.prepare('SELECT * FROM practice_graded').all();
  assert.equal(rows.length,GRADE_FREE+1,'every grading is recorded, failures are not');
  assert.ok(rows.every(r=>r.level==='L1'&&r.band==='pass'));
  assert.ok(!JSON.stringify(db.prepare("SELECT * FROM practice_rubrics").all()).includes('base64'),'no image is stored');
});

test('a rubric is written once, then cached; other content under the same id gets its own',async()=>{
  const {route,aiCalls,db,visionCalls}=setup();
  const a=await route('/api/learn/grade','POST',body(),me);
  assert.equal(a.rubric_source,'generated');assert.equal(aiCalls.length,1);
  assert.match(aiCalls[0].messages[1].content,/Official answer: 9\.9 m\/s/);
  const b=await route('/api/learn/grade','POST',{...body(),rubric:[{id:'x',desc:'free marks',pts:10}]},{id:8});
  assert.equal(b.rubric_source,'cached');assert.equal(aiCalls.length,1,'the cache costs no model call');
  assert.deepEqual(b.items.map(x=>x.id),['a','b','c'],'a client cannot send its own rubric');
  assert.equal(visionCalls.at(-1).rubric.length,3);
  const c=await route('/api/learn/grade','POST',body({item:{q:'A ball falls from $20$ m. Find its speed.'}}),me);
  assert.equal(c.rubric_source,'generated');assert.equal(aiCalls.length,2);
  assert.equal(db.prepare('SELECT COUNT(*) AS n FROM practice_rubrics').get().n,2);
  const d=await route('/api/learn/grade','POST',body({item:{points:20}}),me);
  assert.equal(d.max,20,'the cached rubric is scaled to the points asked');assert.equal(d.rubric_source,'cached');
  /* scores 3+3+1 of 10 → 0.7 → pass */
  assert.equal(a.score,7);assert.equal(a.band,'pass');assert.match(a.transcript,/9\.9/);
  const list=await route('/api/learn/graded','GET',null,me,{url:'https://x/api/learn/graded?item=ap1-u1-001'});
  assert.equal(list.graded.length,3);assert.ok(list.graded.every(g=>g.item_id==='ap1-u1-001'));
  assert.equal((await route('/api/learn/graded','GET',null,me,{url:'https://x/api/learn/graded?item=other-1'})).graded.length,0);
  assert.equal((await route('/api/learn/graded','GET',null,{id:8},{url:'https://x/api/learn/graded'})).graded.length,1,'only the learner\'s own');
});

test('a broken rubric is retried once, then the grading fails and is given back',async()=>{
  const {route,aiCalls}=setup({ai:()=>'no json here'});
  await fails(route('/api/learn/grade','POST',body(),me),'grade_failed');
  assert.equal(aiCalls.length,2);
  assert.equal((await route('/api/learn/plan','GET',null,me)).gradeLeft,GRADE_FREE);
});

test('a grading with a unit and step moves that unit\'s rating like an attempt',async()=>{
  const {route,db}=setup();
  for(const s of PRACTICE_SCHEMA)db.exec(s);
  await route('/api/learn/grade','POST',body({item:{unit:'mechanics/kinematics',step:3}}),me);
  const s=db.prepare('SELECT * FROM practice_skills WHERE user_id=7').get();
  assert.equal(s.unit,'mechanics/kinematics');assert.equal(s.n,1);assert.equal(s.right_n,1);assert.ok(s.rating>1300);
  assert.equal(db.prepare("SELECT result FROM practice_attempts").get().result,'right');
});

test('problem reports: anyone can send, the day has a limit, staff read and close, members see their own',async()=>{
  const {route,db}=setup();
  const r=await route('/api/learn/report','POST',{item_id:'ap1-u1-001',source:'track',reason:'wrong_answer',note:'answer should be 9.9',page:'/practice.html#ap1',lang:'ko'},me);
  assert.equal(typeof r.id,'number');
  const g=await route('/api/learn/report','POST',{item_id:'jeem-x-2',reason:'typo',note:''},null,{ip:'5.6.7.8'});
  const row=db.prepare('SELECT * FROM problem_reports WHERE id=?').get(g.id);
  assert.equal(row.user_id,null);assert.equal(row.status,'open');assert.ok(row.ip_hash&&!row.ip_hash.includes('5.6.7.8'));
  await fails(route('/api/learn/report','POST',{item_id:'a',reason:'spam',note:''},me),'bad_report');
  await fails(route('/api/learn/report','POST',{item_id:'a',reason:'other',note:''},me),'bad_report');
  await fails(route('/api/learn/report','POST',{item_id:'a',reason:'typo',note:'x'.repeat(1001)},me),'bad_report');
  for(let i=0;i<20;i++)await route('/api/learn/report','POST',{item_id:'a1',reason:'typo',note:''},null,{ip:'9.9.9.9'});
  await fails(route('/api/learn/report','POST',{item_id:'a1',reason:'typo',note:''},null,{ip:'9.9.9.9'}),'rate_limited');
  await fails(route('/api/learn/reports','GET',null,me,{url:'https://x/api/learn/reports'}),'staff_only');
  await fails(route('/api/learn/reports','GET',null,null,{url:'https://x/api/learn/reports'}),'login_required');
  const all=await route('/api/learn/reports','GET',null,staff,{url:'https://x/api/learn/reports?status=open'});
  assert.equal(all.reports.length,22);assert.equal(all.reports[0].item_id,'a1','newest first');
  await fails(route(`/api/learn/reports/${r.id}`,'PATCH',{status:'fixed'},me),'staff_only');
  await fails(route(`/api/learn/reports/${r.id}`,'PATCH',{status:'done'},staff),'bad_status');
  await fails(route('/api/learn/reports/99999','PATCH',{status:'fixed'},staff),'report_not_found');
  assert.equal((await route(`/api/learn/reports/${r.id}`,'PATCH',{status:'fixed'},staff)).status,'fixed');
  assert.equal((await route('/api/learn/reports','GET',null,staff,{url:'https://x/api/learn/reports?status=open'})).reports.length,21);
  const mine=await route('/api/learn/reports/mine','GET',null,me);
  assert.equal(mine.reports.length,1);assert.equal(mine.reports[0].status,'fixed');
  await fails(route('/api/learn/reports/mine','GET',null,null),'login_required');
});

test('no vision provider: the grading is unavailable and not counted',async()=>{
  const {route,env}=setup();delete env.GEMINI_API_KEY;
  await fails(route('/api/learn/grade','POST',body(),me),'ai_unavailable');
  assert.equal((await route('/api/learn/plan','GET',null,me)).gradeLeft,GRADE_FREE);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createPracticeRouter, updateRating, ratingStep, stepRating, mergeState, START, dailyUpdate, dailyStart, dailyBounds, dailyK, LEVEL_STEPS, DAILY_RATED_PER_DAY} from './src/practice-progress.js';

class H extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
const bad=code=>{throw new H(400,code);};
function setup(){
  const db=new DatabaseSync(':memory:');
  const D1={async batch(s){const out=[];for(const x of s)out.push(await x.all());return out;},prepare(sql){let args=[];return{bind(...a){args=a;return this;},async first(){return db.prepare(sql).get(...args)||null;},async all(){return{results:db.prepare(sql).all(...args)};},async run(){const r=db.prepare(sql).run(...args);return{meta:{last_row_id:Number(r.lastInsertRowid)}};}};}};
  let t=1_000_000;
  const route=createPracticeRouter({HttpError:H,bad,now:()=>t,needUser:u=>{if(!u)throw new H(401,'login_required');return u;},limit:async()=>{}});
  return {db,env:{DB:D1},route,tick:s=>{t+=s;}};
}
const me={id:7},other={id:8};
const fails=async(p,code)=>assert.rejects(p,e=>e.code===code);

test('ratings rise with right answers above the learner, fall with wrong ones below, and skips change nothing',()=>{
  assert.equal(stepRating(3),1300);assert.equal(ratingStep(1300),3);assert.equal(ratingStep(5000),10);assert.equal(ratingStep(0),1);
  assert.ok(updateRating(START,6,'right')-START>updateRating(START,2,'right')-START,'a harder problem gains more');
  assert.ok(updateRating(START,2,'wrong')<START);assert.equal(updateRating(START,4,'skip'),START);
  assert.ok(Math.abs(updateRating(START,3,'solved')-START)<Math.abs(updateRating(START,3,'right')-START),'self-marking counts half');
});

test('attempts need an account, are validated, and update one rating per unit',async()=>{
  const {env,route,db}=setup();
  await fails(route('/api/practice/attempts','POST',{attempts:[]},null,env),'login_required');
  await fails(route('/api/practice/attempts','POST',{attempts:[{item_id:'x',mode:'exam',unit:'mechanics/energy',step:3,result:'right'}]},me,env),'bad_attempt');
  await fails(route('/api/practice/attempts','POST',{attempts:[{item_id:'kr-1',mode:'exam',unit:'drop table',step:3,result:'right'}]},me,env),'bad_attempt');
  const r=await route('/api/practice/attempts','POST',{attempts:[
    {item_id:'kr-1',mode:'exam',unit:'mechanics/energy',step:4,result:'right',at:999_000},
    {item_id:'kr-2',mode:'exam',unit:'mechanics/energy',step:4,result:'right'},
    {item_id:'kr-3',mode:'exam',unit:'em/induction',step:3,result:'skip'},
    {item_id:'q_abc',mode:'bank',unit:'mechanics/*',step:6,result:'missed'},
    {item_id:'eupho-2022-T3~T3',mode:'contest',unit:'contest/eupho',step:9,result:'solved'}]},me,env);
  assert.equal(r.recorded,5);
  const s=Object.fromEntries((await route('/api/practice/state','GET',{},me,env)).skills.map(x=>[x.unit,x]));
  assert.equal(s['mechanics/energy'].n,2);assert.ok(s['mechanics/energy'].rating>START);
  assert.equal(s['em/induction'],undefined,'a skip alone creates no rating');
  assert.ok(s['mechanics/*'].rating<START);assert.ok(s['contest/eupho'].rating>START);
  assert.equal(db.prepare('SELECT COUNT(*) n FROM practice_attempts WHERE user_id=7').get().n,5);
  assert.equal((await route('/api/practice/state','GET',{},other,env)).skills.length,0,'members see only their own');
});

test('the saved state merges with what another device sent, never losing progress',async()=>{
  const {env,route}=setup();
  await route('/api/practice/state','POST',{state:{xp:120,days:['2026-11-20'],level:{'em/induction':4},solved:{a:'em/induction'},bank:{done:{q1:1},stars:{optics:2}}}},me,env);
  const r=await route('/api/practice/state','POST',{state:{xp:80,days:['2026-11-21'],level:{'em/induction':3,'optics/lenses':2},solved:{b:'optics/lenses'},contest:{done:{'x~1':1}}}},me,env);
  assert.equal(r.state.xp,120);assert.deepEqual(r.state.days,['2026-11-20','2026-11-21']);
  assert.deepEqual(r.state.level,{'em/induction':4,'optics/lenses':2});
  assert.deepEqual(Object.keys(r.state.solved).sort(),['a','b']);assert.equal(r.state.bank.done.q1,1);assert.equal(r.state.contest.done['x~1'],1);
  await fails(route('/api/practice/state','POST',{state:'x'},me,env),'bad_state');
  assert.deepEqual(mergeState(null,{days:['bad']}).days,[]);
});

test('the placement test sets a starting rating only for units with no answers yet, and track and diagnostic attempts count',async()=>{
  const {env,route}=setup();
  await route('/api/practice/attempts','POST',{attempts:[{item_id:'kr-9',mode:'exam',unit:'waves/shm',step:3,result:'right'}]},me,env);
  const before=Object.fromEntries((await route('/api/practice/state','GET',{},me,env)).skills.map(x=>[x.unit,x]))['waves/shm'].rating;
  const r=await route('/api/practice/attempts','POST',{attempts:[
    {item_id:'diag-mechanics',mode:'diag',unit:'mechanics/kinematics',step:6,result:'place'},
    {item_id:'diag-waves',mode:'diag',unit:'waves/shm',step:8,result:'place'},
    {item_id:'ap1-u3-007',mode:'track',unit:'mechanics/energy',step:4,result:'right'}]},me,env);
  assert.equal(r.recorded,3);assert.ok(r.skills.every(s=>!('placed' in s)));
  const s=Object.fromEntries((await route('/api/practice/state','GET',{},me,env)).skills.map(x=>[x.unit,x]));
  assert.equal(s['mechanics/kinematics'].rating,stepRating(6));assert.equal(s['mechanics/kinematics'].n,0);
  assert.equal(s['waves/shm'].rating,before,'a unit with answers keeps its earned rating');
  assert.equal(s['mechanics/energy'].n,1);
  assert.equal(updateRating(START,9,'place'),START);
});

test('the first-visit profile follows the account: the newer answers win and anything else is dropped',()=>{
  const old={region:'kr',level:'high1',goal:'school',oly:0,daily:10,at:100},neu={region:'us',level:'high2',goal:'olympiad',oly:1,daily:20,at:200};
  assert.deepEqual(mergeState({profile:old},{profile:neu}).profile,neu);
  assert.deepEqual(mergeState({profile:neu},{profile:old}).profile,neu);
  assert.deepEqual(mergeState({},{profile:{...old,extra:'x',oly:9,daily:7}}).profile,{...old,oly:2,daily:10});
  assert.equal(mergeState({profile:{region:'mars',level:'high1',goal:'school',at:1}},{}).profile,undefined);
  assert.deepEqual(mergeState({profile:{region:'mars',at:999}},{profile:old}).profile,old,'a bad newer profile never replaces a good one');
});

test('the recent answers (the weekly set reads them): newest first, own only, no skips or placements, within 60 days and 60 rows',async()=>{
  const {env,route,tick}=setup();
  await fails(route('/api/practice/recent','GET',{},null,env),'login_required');
  await route('/api/practice/attempts','POST',{attempts:[
    {item_id:'opho-2020-T~1',mode:'contest',unit:'contest/opho',step:7,result:'solved',at:999_000},
    {item_id:'usapho-u1-001',mode:'track',unit:'mechanics/energy',step:7,result:'wrong',at:999_500},
    {item_id:'usapho-u1-002',mode:'track',unit:'mechanics/momentum',step:8,result:'skip',at:999_600},
    {item_id:'diag-waves',mode:'diag',unit:'waves/shm',step:8,result:'place',at:999_700}]},me,env);
  await route('/api/practice/attempts','POST',{attempts:[{item_id:'kr-1',mode:'exam',unit:'mechanics/energy',step:4,result:'right'}]},other,env);
  const r=await route('/api/practice/recent','GET',{},me,env);
  assert.deepEqual(r.attempts.map(a=>[a.item_id,a.result,a.at]),[['usapho-u1-001','wrong',999_500],['opho-2020-T~1','solved',999_000]]);
  assert.deepEqual(Object.keys(r.attempts[0]).sort(),['at','item_id','mode','result','step','unit']);
  const many=Array.from({length:50},(_,i)=>({item_id:'usapho-u2-'+String(i).padStart(3,'0'),mode:'track',unit:'waves/shm',step:6,result:'right'}));
  await route('/api/practice/attempts','POST',{attempts:many},me,env);await route('/api/practice/attempts','POST',{attempts:many},me,env);
  assert.equal((await route('/api/practice/recent','GET',{},me,env)).attempts.length,60);
  tick(61*86400);
  assert.equal((await route('/api/practice/recent','GET',{},me,env)).attempts.length,0,'older than 60 days: left out');
});

/* ── the daily problems' difficulty: one rating per study level, worked out here from the recorded answers ── */
test('daily difficulty math: medium start, up when right, down when wrong or given up, hints shrink a rise, bigger steps at first',()=>{
  assert.deepEqual(LEVEL_STEPS,{L1:[2,7],L2:[5,7],L3:[6,9],L4:[8,9]});
  assert.equal(dailyStart('L1'),1450);assert.equal(dailyStart('L3'),1750);assert.equal(dailyStart('nope'),1450);
  const r=dailyStart('L1'),step=4.5;
  const up=dailyUpdate(r,0,step,'right',0,'L1'),down=dailyUpdate(r,0,step,'wrong',0,'L1');
  assert.equal(up,r+24);assert.equal(down,r-24,'an even problem moves K/2 either way');
  assert.equal(dailyUpdate(r,0,step,'solved',0,'L1'),up,'a passed written answer counts as right');
  assert.equal(dailyUpdate(r,0,step,'skip',0,'L1'),r);assert.equal(dailyUpdate(r,0,step,'hint',0,'L1'),r);
  assert.equal(dailyUpdate(r,0,step,'right',1,'L1'),r+16,'one hint: two thirds of the rise');
  assert.equal(dailyUpdate(r,0,step,'right',3,'L1'),r,'three hints: no change');
  assert.ok(dailyUpdate(r,0,step,'right',5,'L1')>=r,'hints never turn a right answer into a fall');
  /* "I can't solve this" on a much easier problem falls like a miss; on a much harder one still at least K/2 */
  assert.ok(dailyUpdate(r,0,9,'wrong',0,'L1')>r-24);assert.equal(dailyUpdate(r,0,9,'giveup',0,'L1'),r-24);
  assert.equal(dailyK(0),48);assert.equal(dailyK(9),48);assert.equal(dailyK(10),20);
  assert.ok(Math.abs(dailyUpdate(r,20,step,'right',0,'L1')-r)<Math.abs(up-r),'smaller steps after ten answers');
  const [lo,hi]=dailyBounds('L1');assert.deepEqual([lo,hi],[1100,1800]);
  assert.equal(dailyUpdate(hi,0,10,'right',0,'L1'),hi);assert.equal(dailyUpdate(lo,0,1,'giveup',0,'L1'),lo,'kept inside the level');
});

test('daily difficulty on the server: worked out from recorded answers, once per problem a day, never taken from the page',async()=>{
  const {env,route,tick,db}=setup();
  const a=(item_id,result,over={})=>({item_id,mode:'track',unit:'mechanics/energy',step:4.5,result,ctx:'daily',level:'L1',...over});
  await fails(route('/api/practice/attempts','POST',{attempts:[a('ap1-u1-001','right',{hints:9})]},me,env),'bad_attempt');
  await fails(route('/api/practice/attempts','POST',{attempts:[a('ap1-u1-001','right',{ctx:'evil'})]},me,env),'bad_attempt');
  await fails(route('/api/practice/attempts','POST',{attempts:[a('ap1-u1-001','right',{level:'L9'})]},me,env),'bad_attempt');
  /* a new learner: the first answer starts from medium */
  let r=await route('/api/practice/attempts','POST',{attempts:[a('ap1-u1-001','right')]},me,env);
  assert.deepEqual(r.daily.L1,{rating:1474,n:1,dir:1,updated_at:1_000_000});
  /* the same problem again today, a hint, a skip: nothing moves */
  r=await route('/api/practice/attempts','POST',{attempts:[a('ap1-u1-001','right'),a('ap1-u1-002','hint'),a('ap1-u1-003','skip')]},me,env);
  assert.equal(r.daily.L1.rating,1474);assert.equal(r.daily.L1.n,1);
  /* "I can't solve this" lowers it; the page's own numbers are never read */
  r=await route('/api/practice/attempts','POST',{attempts:[a('ap1-u1-002','giveup',{rating:9999})]},me,env);
  assert.ok(r.daily.L1.rating<1474);assert.equal(r.daily.L1.dir,-1);
  await route('/api/practice/state','POST',{state:{dailyR:{L1:{r:2000,n:99}}}},me,env);
  const st=await route('/api/practice/state','GET',{},me,env);
  assert.equal(st.daily.L1.rating,r.daily.L1.rating);assert.equal(st.state.dailyR,undefined,'the state does not carry a rating');
  /* not daily: no rating */
  r=await route('/api/practice/attempts','POST',{attempts:[{item_id:'kr-5',mode:'exam',unit:'mechanics/energy',step:4,result:'right'}]},me,env);
  assert.equal(r.daily.L1.n,2);assert.equal(r.daily.L2,undefined);
  /* each level has its own; the next day the same problem counts again */
  tick(86401);
  r=await route('/api/practice/attempts','POST',{attempts:[a('ap1-u1-001','right'),a('jeem-u1-001','wrong',{level:'L2'})]},me,env);
  assert.equal(r.daily.L1.n,3);assert.equal(r.daily.L2.n,1);assert.ok(r.daily.L2.rating<dailyStart('L2'));
  /* at most DAILY_RATED_PER_DAY a day */
  const many=Array.from({length:50},(_,i)=>a('ap1-x-'+i,'right'));
  await route('/api/practice/attempts','POST',{attempts:many},me,env);r=await route('/api/practice/attempts','POST',{attempts:many.map(x=>({...x,item_id:x.item_id+'b'}))},me,env);
  assert.equal(r.daily.L1.n,3+DAILY_RATED_PER_DAY-2,'two of today\'s were rated already');
  /* hints and give-ups are kept on the attempts; the recent list leaves hints out and reads a give-up as a miss */
  assert.equal(db.prepare("SELECT hints FROM practice_attempts WHERE result='giveup'").get().hints,0);
  const rec=(await route('/api/practice/recent','GET',{},me,env)).attempts;
  assert.ok(!rec.some(x=>x.result==='hint'||x.result==='giveup'));
});

test('an older practice_attempts table gets the new columns',async()=>{
  const {env,route,db}=setup();
  db.exec('CREATE TABLE practice_attempts (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,item_id TEXT NOT NULL,mode TEXT NOT NULL,unit TEXT NOT NULL,step REAL NOT NULL,result TEXT NOT NULL,created_at INTEGER NOT NULL)');
  db.prepare("INSERT INTO practice_attempts(user_id,item_id,mode,unit,step,result,created_at) VALUES(7,'old-1','exam','mechanics/energy',3,'right',1)").run();
  await route('/api/practice/attempts','POST',{attempts:[{item_id:'ap1-u1-001',mode:'track',unit:'mechanics/energy',step:4,result:'right',hints:2,ctx:'daily',level:'L1'}]},me,env);
  const cols=db.prepare('PRAGMA table_info(practice_attempts)').all().map(c=>c.name);
  assert.ok(cols.includes('hints')&&cols.includes('ctx'));
  assert.deepEqual({...db.prepare("SELECT hints,ctx FROM practice_attempts WHERE item_id='ap1-u1-001'").get()},{hints:2,ctx:'daily'});
  assert.equal(db.prepare("SELECT hints FROM practice_attempts WHERE item_id='old-1'").get().hints,0);
});

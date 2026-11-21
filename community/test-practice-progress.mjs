import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createPracticeRouter, updateRating, ratingStep, stepRating, mergeState, START} from './src/practice-progress.js';

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

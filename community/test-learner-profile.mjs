import fs from 'node:fs';
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createRequire} from 'node:module';
import {createLearnerRouter, cleanLearner, COUNTRIES, DAILY_GOALS, LEARNER_SAVES_PER_DAY, readLearner, learnerDeletion} from './src/learner-profile.js';

class H extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
const bad=code=>{throw new H(400,code);};
function setup(){
  const db=new DatabaseSync(':memory:');
  const D1={async batch(s){const out=[];for(const x of s)out.push(await x.all());return out;},prepare(sql){let args=[];return{bind(...a){args=a;return this;},async first(){return db.prepare(sql).get(...args)||null;},async all(){return{results:db.prepare(sql).all(...args)};},async run(){const r=db.prepare(sql).run(...args);return{meta:{last_row_id:Number(r.lastInsertRowid)}};}};}};
  let t=1_800_000_000;const counts=new Map();
  const limit=async(env,key,max)=>{const n=(counts.get(key)||0)+1;counts.set(key,n);if(n>max)throw new H(429,'rate_limited');};
  const route=createLearnerRouter({HttpError:H,bad,now:()=>t,limit,needUser:u=>{if(!u)throw new H(401,'login_required');return u;}});
  const env={DB:D1};
  return {db,env,route:(p,m,b,me,req)=>route(p,m,b,me,req,env),tick:s=>{t+=s;}};
}
const me={id:7};
const fails=async(p,code)=>assert.rejects(p,e=>e.code===code);

test('country is an ISO 3166-1 alpha-2 code from the list, the goal one of 5, 10, 15, 20',()=>{
  assert.equal(COUNTRIES.length,249);assert.equal(new Set(COUNTRIES).size,249);
  assert.deepEqual(DAILY_GOALS,[5,10,15,20]);
  assert.deepEqual(cleanLearner({country:'kr',daily_goal:15},bad),{country:'KR',daily_goal:15});
  for(const country of ['XX','KOR','','UK',null,42])assert.throws(()=>cleanLearner({country,daily_goal:10},bad),e=>e.code==='bad_country',String(country));
  for(const daily_goal of [0,3,12,25,'ten',null])assert.throws(()=>cleanLearner({country:'US',daily_goal},bad),e=>e.code==='bad_daily_goal',String(daily_goal));
  assert.throws(()=>cleanLearner(null,bad),e=>e.code==='bad_learner');
});

/* the page's form exists only where the pages are (the preview branch); the server-only deploy skips this check */
test('the site\'s country list (learner-form.js) is the server\'s',{skip:!fs.existsSync(new URL('../learner-form.js',import.meta.url))},()=>{
  const require=createRequire(import.meta.url);
  const form=require('../learner-form.js');
  assert.deepEqual([...form.COUNTRIES],[...COUNTRIES]);
  assert.deepEqual([...form.DAILY_GOALS],[...DAILY_GOALS]);
});

test('read and save need an account; a PUT body is read from the request; saves are limited per day',async()=>{
  const {route,env}=setup();
  await fails(route('/api/me/learner','GET',{},null),'login_required');
  await fails(route('/api/me/learner','PUT',{},null),'login_required');
  assert.deepEqual(await route('/api/me/learner','GET',{},me),{country:null,daily_goal:null,updated_at:null});
  const req=body=>({json:async()=>body});
  const saved=await route('/api/me/learner','PUT',{},me,req({country:'IN',daily_goal:20}));
  assert.equal(saved.country,'IN');assert.equal(saved.daily_goal,20);
  assert.equal((await route('/api/me/learner','GET',{},me)).country,'IN');
  await fails(route('/api/me/learner','PUT',{},me,req({country:'ZZ',daily_goal:20})),'bad_country');
  await route('/api/me/learner','PUT',{},me,req({country:'KR',daily_goal:5}));
  assert.deepEqual(await readLearner(env,7).then(({country,daily_goal})=>({country,daily_goal})),{country:'KR',daily_goal:5},'changing it in settings replaces the row');
  for(let i=2;i<LEARNER_SAVES_PER_DAY;i++)await route('/api/me/learner','PUT',{},me,req({country:'KR',daily_goal:10}));
  await fails(route('/api/me/learner','PUT',{},me,req({country:'KR',daily_goal:10})),'rate_limited');
  assert.equal(await route('/api/other','GET',{},me),undefined,'other paths pass through');
});

test('account deletion removes the row',async()=>{
  const {route,env}=setup();
  await route('/api/me/learner','PUT',{},me,{json:async()=>({country:'FR',daily_goal:10})});
  await learnerDeletion(env,7).run();
  assert.equal((await readLearner(env,7)).country,null);
});

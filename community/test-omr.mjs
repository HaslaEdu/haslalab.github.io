import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {scoreOmr,percentileCounts,createOmrRouter} from './src/omr.js';
const exam={id:'kphe:2026-2:T2a',version:'test-v1',key:[1,2,3],penaltyRate:.25,
  policy:{verified:true,points:[4,8,12],fields:['mechanics','electricity','electricity']},fullCredit:[]};
test('verified item points produce raw, deduction, final and domain totals',()=>{
  const s=scoreOmr(exam,[1,3,null]);
  assert.equal(s.rawScore,4);assert.equal(s.penalty,2);assert.equal(s.officialScore,2);
  assert.deepEqual(s.fields.electricity,{raw:0,penalty:2,maximum:20,final:-2});
});
test('unknown official weights never become a fabricated official total',()=>{
  const s=scoreOmr({...exam,policy:{verified:false}},[1,3,null]);
  assert.equal(s.officialScore,null);assert.equal(s.maximum,null);assert.equal(s.fields,null);
  assert.equal(s.practice.score,.75);assert.equal(s.practice.official,false);
});
test('official alternatives and cancelled questions accept the published correction',()=>{
  const s=scoreOmr({...exam,key:[[1,2],2,3],fullCredit:[3]},[2,4,null]);
  assert.equal(s.correct,2);assert.equal(s.officialScore,14);assert.equal(s.blank,0);
});
test('invalid answer shapes and coercible non-numbers are rejected',()=>{
  for(const a of [[1],['1',2,3],[1,0,3],[1,6,3]])assert.throws(()=>scoreOmr(exam,a));
});
test('percentile is tie-inclusive and small cohorts have no pretend precision',()=>{
  assert.deepEqual(percentileCounts(1,2,5),{n:5,rank:2,upperPercent:60,ties:2,minimumSample:5});
  assert.equal(percentileCounts(0,1,1).upperPercent,null);
});
test('server recomputes scores, deduplicates attempts and compares one peer attempt per account',async()=>{
  const db=new DatabaseSync(':memory:');
  db.exec('CREATE TABLE users(id INTEGER PRIMARY KEY,deleted INTEGER DEFAULT 0);');
  const env={DB:{async batch(statements){const rows=[];for(const statement of statements)rows.push(await statement.run());return rows;},prepare(sql){let args=[];return {bind(...a){args=a;return this;},async first(){return db.prepare(sql).get(...args)||null;},async all(){return {results:db.prepare(sql).all(...args)};},async run(){const r=db.prepare(sql).run(...args);return {meta:{last_row_id:Number(r.lastInsertRowid)}};}};}}};
  class H extends Error{constructor(status,code){super(code);this.status=status;}}
  const route=createOmrRouter({HttpError:H,needUser:u=>{if(!u)throw new H(401,'login_required');},limit:async()=>{},now:()=>1000},{[exam.id]:exam});
  const call=(user,id,answers)=>route('/api/omr/attempts','POST',{exam_key:exam.id,client_id:id,answers,score:999999},user,{},env,new URL('https://api.test/api/omr/attempts'));
  await assert.rejects(call(null,'attempt-0',[1,2,3]),e=>e.status===401);
  for(let id=1;id<=5;id++){db.prepare('INSERT INTO users(id) VALUES(?)').run(id);await call({id},'attempt-'+id,[1,2,null]);}
  const duplicate=await call({id:1},'attempt-1',[1,2,3]);
  assert.equal(duplicate.attempt.score.officialScore,12,'a repeated id cannot overwrite saved answers');
  const repeat=await call({id:1},'attempt-repeat',[1,2,3]);
  assert.equal(repeat.attempt.score.officialScore,24,'the browser-supplied score is ignored');
  assert.equal(repeat.cohort.n,5,'extra attempts do not multiply peer samples');
  assert.equal(repeat.cohort.rank,1);assert.equal(repeat.cohort.upperPercent,20);
  db.prepare('UPDATE users SET deleted=1 WHERE id=5').run();
  const smaller=await call({id:1},'attempt-repeat',[1,2,3]);
  assert.equal(smaller.cohort.n,4,'deleted accounts leave the comparison group');
  assert.equal(smaller.cohort.upperPercent,null,'small groups stop displaying a percentile');
  db.close();
});

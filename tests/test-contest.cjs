const test = require('node:test');
const assert = require('node:assert/strict');
const core = require('../sim/contest-core.js');
const base = {id:'test-exam',minutes:120,questions:3,kind:'choice',choices:5};

test('unverified duration or answer format cannot start an official-timing attempt',()=>{
  for(const e of [{...base,minutes:null},{...base,questions:0},{...base,kind:'unknown'},{...base,practice:false}]){
    assert.equal(core.ready(e),false); assert.equal(core.create(e,1000),null);
  }
});
test('reloading and closed-tab time use the original deadline without a pause or upload grace period',()=>{
  const r=core.create(base,1000); r.marks={1:2}; r.deadline+=1800000;
  const loaded=core.normalize(r,base);
  assert.equal(loaded.deadline,7201000); assert.equal(core.remaining(loaded,3601000),3600000);
  assert.equal(core.remaining(loaded,7201000),0); assert.deepEqual(loaded.marks,{1:2});
  assert.equal(core.normalize({...r,examId:'another-exam'},base),null);
});
test('answers cannot be changed after the deadline or manual submission and finish is idempotent',()=>{
  const r=core.create(base,1000);
  assert.equal(core.setAnswer(r,base,1,3,2000),true);
  assert.equal(core.setAnswer(r,base,1,4,7201000),false);
  assert.equal(core.finish(r,7202000,'manual'),true);
  assert.deepEqual(r.done,{at:7201000,reason:'timeout'});
  assert.equal(core.setAnswer(r,base,2,4,7203000),false);
  assert.equal(core.finish(r,7204000),false);
  const early=core.create(base,1000);core.finish(early,2000);assert.equal(core.setAnswer(early,base,1,1,3000),false);
});
test('integer answers retain zero and leading zeroes; out-of-range answers are rejected',()=>{
  const e={...base,kind:'integer',answerMin:0,answerMax:999};
  assert.equal(core.answer(e,'000'),0); assert.equal(core.answer(e,0),0);
  for(const v of ['',true,-1,1000,'1e2','1.5','-2','2x'])assert.equal(core.answer(e,v),null);
  assert.equal(core.answer({...e,answerMax:99},'100'),null);
  assert.equal(core.answer({...e,answerMax:null},'40000'),40000);
  assert.equal(core.answer({...e,answerMax:null},'9007199254740992'),null);
});
test('grading requires an explicitly verified complete official answer key',()=>{
  assert.equal(core.grade({...base,answers:[1,2,3]},{}),null);
  assert.equal(core.grade({...base,answersVerified:true,answers:[1,2]},{}),null);
  assert.equal(core.grade({...base,answersVerified:true,answers:[1,null,3]},{}),null);
  assert.equal(core.grade({...base,kind:'proof',answersVerified:true,answers:[1,2,3]},{}),null);
});
test('chemistry scoring uses absolute wrong-answer deductions and leaves blanks at zero',()=>{
  const e={...base,answersVerified:true,answers:[1,[2,3],4],point:3,penalty:1};
  const g=core.grade(e,{1:1,2:5});
  assert.deepEqual([g.correct,g.wrong,g.blank,g.score,g.total],[1,1,1,2,9]);
  assert.equal(core.grade(e,{1:5,2:5,3:5}).score,-3);
  assert.equal(core.grade(e,{2:3}).correct,1);
});
test('KMO points can vary by question and unverified weighting only reports counts',()=>{
  const e={...base,kind:'integer',answersVerified:true,answers:[0,1,2],points:[4,5,6]};
  assert.equal(core.grade(e,{1:0,3:2}).score,10);
  const counts=core.grade({...e,scoringVerified:false},{1:0,3:2});
  assert.equal(counts.score,null);assert.equal(counts.correct,2);assert.equal(counts.total,null);
  assert.equal(core.grade({...e,points:[4,5]},{1:0}).weighted,false);
});
test('all-candidate credit includes blanks; excluded questions do not count toward scores or totals',()=>{
  const e={...base,answersVerified:true,answers:[null,null,2],point:3,penalty:1,fullCredit:[1],excluded:[2]};
  const g=core.grade(e,{});
  assert.deepEqual([g.correct,g.wrong,g.blank,g.score,g.total,g.gradedCount],[1,0,1,3,6,2]);
  assert.equal(g.rows[1].status,'excluded');
});
test('normalization limits saved answers to the configured sheet and deduplicates attempt history',()=>{
  const e={...base,kind:'proof'},r=core.create(e,1000);r.marks={1:'Proof',2:' ',4:'Extra'};r.q=4;
  const normalized=core.normalize(r,e);assert.deepEqual(normalized.marks,{1:'Proof'});assert.equal(normalized.q,3);
  assert.equal(core.appendHistory(core.appendHistory([],r),r).length,1);
});

test('paper mode remains paper after reload while pre-existing attempts keep online entry',()=>{
  const r=core.create(base,1000,'paper');
  assert.equal(core.normalize(r,base).mode,'paper');
  const old={...r};delete old.mode;assert.equal(core.normalize(old,base).mode,'online');
  assert.equal(core.setAnswer(r,base,1,2,2000),false);
});

test('paper scans are reviewed once after working time, without extending the original clock',()=>{
  const r=core.create(base,1000,'paper'),deadline=r.deadline;
  assert.equal(core.submitPaper(r,base,{1:2},2000,{complete:true}),false);
  core.finish(r,deadline,'timeout');
  assert.equal(core.submitPaper(r,base,{1:2},deadline+3000,{complete:false}),false);
  assert.equal(core.submitPaper(r,base,{1:9},deadline+3000,{complete:true}),false);
  assert.equal(core.submitPaper(r,base,{1:2},deadline+4000,{complete:true,pages:2}),true);
  assert.equal(core.submitPaper(r,base,{1:3},deadline+5000,{complete:true}),false);
  assert.equal(r.deadline,deadline);assert.deepEqual(r.marks,{1:2});
  const loaded=core.normalize(r,base);assert.deepEqual(loaded.paperSubmission,{at:deadline+4000,reviewed:true,pages:2});
  assert.equal(core.submitPaper(loaded,base,{1:1},deadline+6000,{complete:true}),false);
});

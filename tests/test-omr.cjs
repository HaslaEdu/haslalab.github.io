const test = require('node:test');
const assert = require('node:assert/strict');
const c = require('../sim/omr-core.js');

test('all levels receive only the 60 minute working period', () => {
  const r = c.create(1000);
  assert.equal(c.remaining(r, 1000), 3600000);
  assert.equal(c.remaining(r, 3600999), 1);
  assert.equal(c.remaining(r, 3601000), 0);
  assert.equal(c.remaining(r, 3901000), 0);
});
test('reload retains elapsed time and answers while old 90 minute sessions adopt 60 minutes', () => {
  const r = c.normalize({at:1000, minutes:90, marks:{1:2, 2:9, 3:'4', 4:1}, q:3}, 3);
  assert.deepEqual(r.marks, {1:2});
  assert.equal(c.remaining(r, 61000), 3540000);
  assert.equal(c.normalize({at:'bad'}, 2), null);
});
test('a PDF failure pauses once and retries resume without deducting load time', () => {
  const r = c.create(1000);
  c.pause(r, 61000); c.pause(r, 121000);
  assert.equal(c.remaining(r, 181000), 3540000);
  c.resume(r, 181000); c.resume(r, 241000);
  assert.equal(c.remaining(r, 241000), 3480000);
  c.pause(r, 4000000);
  assert.equal(r.pauseAt, null, 'an already expired attempt must not be revived');
});
test('grading distinguishes blanks, alternatives and 25 percent wrong-answer penalties', () => {
  const g = c.grade([1, [2,3], 4, 5], {1:1,2:3,3:2}, {penaltyRate:.25});
  assert.deepEqual([g.correct,g.wrong,g.blank,g.score,g.total,g.weighted], [2,1,1,1.75,4,false]);
  const w = c.grade([1,2,3], {1:1,2:4}, {penaltyRate:.25, points:[4,8,10]});
  assert.equal(w.score, 2); assert.equal(w.total,22); assert.equal(w.weighted,true);
  assert.equal(c.grade([1], {1:2}, {penaltyRate:.25}).score, -.25);
});
test('malformed weighting falls back to disclosed unit counts instead of claiming official points', () => {
  const g = c.grade([1,2], {1:1}, {points:[5],penaltyRate:.25});
  assert.equal(g.weighted,false); assert.equal(g.total,2);
});

test('official all-candidate credit includes unanswered questions, while alternative answers still require a choice', () => {
  const g = c.grade([[1,2,3,4,5], [2,3]], {}, {penaltyRate:.25, fullCredit:[1]});
  assert.equal(g.correct,1); assert.equal(g.blank,1); assert.equal(g.score,1);
  assert.equal(g.rows[0].fullCredit,true);
});
test('deadline and manual-submit races cannot submit or record an attempt twice', () => {
  const r = c.create(1000);
  assert.equal(c.finish(r,[1],{},3601000,'timeout'),true);
  assert.equal(c.finish(r,[1],{},3602000),false);
  assert.equal(r.done.reason,'timeout');
  let h = c.appendHistory([], {id:r.id,score:1});
  h = c.appendHistory(h,{id:r.id,score:1});
  assert.equal(h.length,1);
});

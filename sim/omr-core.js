/* Shared by the browser and the Node regression tests. No browser clock or storage side effects. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.OmrCore = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const MINUTES = 60;
  function validChoice(value) { return Number.isInteger(value) && value >= 1 && value <= 5; }
  function normalize(saved, count, minutes = MINUTES) {
    if (!saved || !Number.isFinite(saved.at) || saved.at <= 0) return null;
    const marks = {}, flags = {}, notes = {};
    for (let q = 1; q <= count; q++) {
      if (validChoice(saved.marks && saved.marks[q])) marks[q] = saved.marks[q];
      if (saved.flags && saved.flags[q]) flags[q] = true;
      if (saved.notes && typeof saved.notes[q] === 'string') notes[q] = saved.notes[q].slice(0, 4000);
    }
    return { id: saved.id || String(saved.at), at: saved.at, minutes,
      pausedMs: Math.max(0, Number(saved.pausedMs) || 0),
      pauseAt: Number.isFinite(saved.pauseAt) && saved.pauseAt >= saved.at ? saved.pauseAt : null,
      marks, flags, notes, q: Math.max(1, Math.min(count, Number(saved.q) || 1)),
      page: Math.max(1, Number(saved.page) || 1), done: saved.done || null };
  }
  function create(now, minutes = MINUTES) {
    return {id: String(now) + '-' + Math.random().toString(36).slice(2, 8), at: now, minutes,
      pausedMs: 0, pauseAt: null, marks: {}, flags: {}, notes: {}, q: 1, page: 1, done: null};
  }
  function remaining(run, now) {
    const clockAt = run.pauseAt == null ? now : run.pauseAt;
    return Math.max(0, run.at + run.minutes * 60000 + run.pausedMs - clockAt);
  }
  function pause(run, now) {
    if (!run.done && run.pauseAt == null && remaining(run, now) > 0) run.pauseAt = now;
    return run;
  }
  function resume(run, now) {
    if (run.pauseAt != null) {
      run.pausedMs += Math.max(0, now - run.pauseAt); run.pauseAt = null;
    }
    return run;
  }
  function matches(key, answer) { return Array.isArray(key) ? key.includes(answer) : key === answer; }
  function grade(key, marks, policy = {}) {
    const weighted = Array.isArray(policy.points) && policy.points.length === key.length && policy.points.every(p => Number.isFinite(p) && p > 0);
    const penaltyRate = Number.isFinite(policy.penaltyRate) && policy.penaltyRate >= 0 ? policy.penaltyRate : 0;
    let correct = 0, wrong = 0, blank = 0, score = 0, total = 0;
    const fullCredit = new Set(Array.isArray(policy.fullCredit) ? policy.fullCredit : []);
    const rows = key.map((answer, i) => {
      const mark = marks[i + 1], weight = weighted ? policy.points[i] : 1;
      const awarded = fullCredit.has(i + 1);
      const status = awarded ? 'correct' : !validChoice(mark) ? 'blank' : matches(answer, mark) ? 'correct' : 'wrong';
      const earned = status === 'correct' ? weight : status === 'wrong' ? -weight * penaltyRate : 0;
      if (status === 'correct') correct++; else if (status === 'wrong') wrong++; else blank++;
      score += earned; total += weight;
      return {q: i + 1, mark: validChoice(mark) ? mark : null, answer, status, earned, fullCredit: awarded};
    });
    return {correct, wrong, blank, score: Math.round(score * 10000) / 10000, total, weighted, penaltyRate, rows};
  }
  function finish(run, key, policy, now, reason = 'manual') {
    if (run.done) return false;
    run.done = {at: now, reason, ...grade(key, run.marks, policy)}; run.pauseAt = null;
    return true;
  }
  function appendHistory(history, entry, limit = 200) {
    return [...history.filter(item => item.id !== entry.id), entry].slice(-limit);
  }
  return {MINUTES, validChoice, normalize, create, remaining, pause, resume, matches, grade, finish, appendHistory};
});

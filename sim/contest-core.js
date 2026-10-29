/* Pure timing and answer handling for local contest practice. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ContestCore = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const kinds = new Set(['choice', 'integer', 'proof']);
  function ready(e) {
    return !!(e && e.practice !== false && typeof e.id === 'string' && e.id &&
      Number.isFinite(e.minutes) && e.minutes > 0 && Number.isInteger(e.questions) &&
      e.questions > 0 && e.questions <= 200 && kinds.has(e.kind));
  }
  function answer(e, value) {
    if (e.kind === 'proof') return typeof value === 'string' && value.trim() ? value.slice(0, 50000) : null;
    if (value === '' || value === null || value === undefined || typeof value === 'boolean') return null;
    const n = typeof value === 'number' ? value : /^\d+$/.test(String(value).trim()) ? Number(value) : NaN;
    const min = e.kind === 'choice' ? 1 : Number.isInteger(e.answerMin) ? e.answerMin : 0;
    const max = e.kind === 'choice' ? (e.choices || 5) : e.answerMax === null ? Number.MAX_SAFE_INTEGER : Number.isInteger(e.answerMax) ? e.answerMax : 999;
    return Number.isInteger(n) && n >= min && n <= max ? n : null;
  }
  function create(e, now) {
    if (!ready(e) || !Number.isFinite(now) || now <= 0) return null;
    return {version: 1, id: String(now) + '-' + Math.random().toString(36).slice(2, 8), examId: e.id,
      at: now, deadline: now + e.minutes * 60000, marks: {}, flags: {}, q: 1, done: null};
  }
  function normalize(saved, e) {
    if (!ready(e) || !saved || saved.examId !== e.id || !Number.isFinite(saved.at) || saved.at <= 0) return null;
    const run = create(e, saved.at);
    run.id = typeof saved.id === 'string' ? saved.id : String(saved.at);
    // The official configuration determines the duration; saved deadlines cannot add time.
    const marks = saved.marks && typeof saved.marks === 'object' ? saved.marks : {};
    for (let q = 1; q <= e.questions; q++) {
      const v = answer(e, marks[q]);
      if (v !== null) run.marks[q] = v;
      if (saved.flags && saved.flags[q]) run.flags[q] = true;
    }
    run.q = Math.max(1, Math.min(e.questions, Number.isInteger(saved.q) ? saved.q : 1));
    if (saved.done && Number.isFinite(saved.done.at) && saved.done.at >= run.at) {
      run.done = {at: Math.min(saved.done.at, run.deadline), reason: saved.done.reason === 'timeout' ? 'timeout' : 'manual'};
    }
    return run;
  }
  function remaining(run, now) { return Math.max(0, run.deadline - now); }
  function setAnswer(run, e, q, value, now) {
    if (!run || run.done || remaining(run, now) <= 0 || !Number.isInteger(q) || q < 1 || q > e.questions) return false;
    const v = answer(e, value);
    if (v === null) delete run.marks[q]; else run.marks[q] = v;
    return true;
  }
  function finish(run, now, reason = 'manual') {
    if (!run || run.done) return false;
    run.done = {at: Math.min(now, run.deadline), reason: remaining(run, now) <= 0 ? 'timeout' : reason};
    return true;
  }
  function hasKey(e) {
    const exempt = new Set([...(e.fullCredit || []), ...(e.excluded || [])]);
    return e.kind !== 'proof' && e.answersVerified === true && Array.isArray(e.answers) && e.answers.length === e.questions &&
      e.answers.every((a, i) => exempt.has(i + 1) || (Array.isArray(a) ? a.length > 0 && a.every(v => answer(e, v) !== null) : answer(e, a) !== null));
  }
  function grade(e, marks) {
    if (!hasKey(e)) return null;
    const points = e.scoringVerified === false ? null : Array.isArray(e.points) && e.points.length === e.questions && e.points.every(v => Number.isFinite(v) && v > 0) ? e.points :
      Number.isFinite(e.point) && e.point > 0 ? Array(e.questions).fill(e.point) : null;
    const penalty = Number.isFinite(e.penalty) && e.penalty >= 0 ? e.penalty : 0;
    const fullCredit = new Set(Array.isArray(e.fullCredit) ? e.fullCredit : []);
    const excluded = new Set(Array.isArray(e.excluded) ? e.excluded : []);
    let correct = 0, wrong = 0, blank = 0, score = 0;
    const rows = e.answers.map((key, i) => {
      const q = i + 1, mark = answer(e, marks[q]), accepted = Array.isArray(key) ? key.map(v => answer(e, v)) : [answer(e, key)];
      const status = excluded.has(q) ? 'excluded' : fullCredit.has(q) ? 'correct' : mark === null ? 'blank' : accepted.includes(mark) ? 'correct' : 'wrong';
      const earned = points ? status === 'correct' ? points[i] : status === 'wrong' ? -penalty : 0 : null;
      if (status === 'correct') correct++; else if (status === 'wrong') wrong++; else if (status === 'blank') blank++;
      if (earned !== null) score += earned;
      return {q, mark, answer: accepted.filter(v => v !== null), status, earned, fullCredit: fullCredit.has(q)};
    });
    return {correct, wrong, blank, weighted: !!points, score: points ? Math.round(score * 10000) / 10000 : null,
      total: points ? points.reduce((a, b, i) => a + (excluded.has(i + 1) ? 0 : b), 0) : null,
      gradedCount: correct + wrong + blank, penalty: points ? penalty : null, rows};
  }
  function appendHistory(history, run, limit = 100) {
    return [...(Array.isArray(history) ? history : []).filter(item => item && item.id !== run.id), run].slice(-limit);
  }
  return {ready, answer, create, normalize, remaining, setAnswer, finish, hasKey, grade, appendHistory};
});

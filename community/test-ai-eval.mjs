import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { aiEvalTick, runEvalCase, readVerdict, koreanClock, evalConfig, createAiEvalRouter, trainingLine, runSiteCase } from './src/ai-eval.js';

function d1(sql = new DatabaseSync(':memory:')) {
  const isRead = s => /^\s*(SELECT|PRAGMA|WITH)\b/i.test(s);
  const stmt = (s, args = []) => ({
    bind: (...a) => stmt(s, a),
    async all() { return {results: sql.prepare(s).all(...args).map(r => ({...r}))}; },
    async first() { const r = sql.prepare(s).get(...args); return r ? {...r} : null; },
    async run() { const r = sql.prepare(s).run(...args); return {meta: {changes: Number(r.changes)}}; },
    exec() { return isRead(s) ? this.all() : this.run(); },
  });
  return {sql, prepare: s => stmt(s), batch: async list => Promise.all(list.map(x => x.exec()))};
}
const GUARD = '@cf/meta/llama-guard-3-8b', JUDGE = '@cf/openai/gpt-oss-120b', CHAT = '@cf/meta/llama-3.3-70b-instruct-fp8-fast';
/* the models: guard says safe; the asker (chat model with a system prompt about playing a student) writes a line;
   the assistant answers; the judge returns JSON */
function fakeAI({answerText = '답: v = 2 m/s', judge = '{"score": 8, "correct": true, "issues": [], "reason": "맞음"}'} = {}) {
  const calls = [];
  return {calls, async run(model, input) {
    calls.push({model, input});
    if (model === GUARD) return {response: 'safe'};
    if (model === JUDGE) return {choices: [{message: {content: judge}}]};
    if (/You play a Korean high-school student/.test(input.messages[0].content)) return {response: '풀이 알려주세요'};
    return {response: answerText};
  }};
}
function bank({figure = false} = {}) {
  return {async fetch(url) {
    const u = new URL(url);
    if (u.pathname.endsWith('/recommendations')) return Response.json({items: ['q1', 'q2', 'q3'].map(id => ({id}))});
    if (/\/q\d\/solutions$/.test(u.pathname)) return Response.json({solutions: [{selected_version: {text: '에너지 보존으로 v = 2 m/s.'}}]});
    if (/\/q\d$/.test(u.pathname)) return Response.json({question: {figures: figure ? [{}] : [], assets: [], selected_version: {text: '질량 1 kg의 공이 높이 0.2 m에서 떨어진다. 바닥에서의 속력은?'}}});
    return new Response('{}', {status: 404});
  }};
}

test('the night runs from the set Korean hour, one case a tick, up to the day\'s total', async () => {
  assert.deepEqual(koreanClock(Date.UTC(2026, 10, 3, 17, 30)), {day: '2026-11-04', hour: 2});
  assert.equal(evalConfig({}).daily, 30);
  assert.equal(evalConfig({AI_EVAL_DAILY: '0'}).daily, 0);
  const env = {DB: d1(), AI: fakeAI(), PROBLEM_BANK: bank(), AI_EVAL_DAILY: '2'};
  assert.equal(await aiEvalTick(env, {now: Date.UTC(2026, 10, 3, 16, 0)}), null, '01:00 KST: not yet');
  const night = Date.UTC(2026, 10, 3, 17, 5);
  const a = await aiEvalTick(env, {now: night}), b = await aiEvalTick(env, {now: night});
  assert.ok(a && b);
  assert.equal(await aiEvalTick(env, {now: night}), null, 'two done');
  // a problem tested in the last 90 days is not asked again
  const refs = env.DB.sql.prepare("SELECT ref FROM ai_eval WHERE kind='bank'").all().map(r => r.ref);
  assert.equal(new Set(refs).size, refs.length);
  assert.equal(await aiEvalTick({...env, AI_EVAL_DAILY: '0'}, {now: night}), null);
  const rows = env.DB.sql.prepare('SELECT * FROM ai_eval').all();
  assert.equal(rows.length, 2);
  assert.ok(rows.every(r => r.day === '2026-11-04' && r.status === 'graded'));
});

test('a bank case asks, answers and is graded against the official solution', async () => {
  const env = {DB: d1(), AI: fakeAI(), PROBLEM_BANK: bank()};
  const r = await runEvalCase(env, {day: '2026-11-04', kind: 'bank'});
  assert.equal(r.status, 'graded');
  assert.match(r.ref, /^q\d$/);
  assert.match(r.question, /^풀이 알려주세요\n\n질량 1 kg/);
  assert.equal(r.answer, '답: v = 2 m/s');
  assert.equal(r.score, 0.8);
  assert.equal(r.verdict, 'correct');
  const judged = env.AI.calls.find(c => c.model === JUDGE);
  assert.match(judged.input.messages[1].content, /Official solution:\n에너지 보존/);
  assert.equal(judged.input.max_completion_tokens, 4096);
  assert.ok(env.AI.calls.filter(c => c.model === CHAT).every(c => c.input.max_tokens > 0), 'llama takes max_tokens');
  // a problem with a figure is not used (the models cannot see it): the case fails and says why
  const f = await runEvalCase({DB: d1(), AI: fakeAI(), PROBLEM_BANK: bank({figure: true})}, {day: 'd', kind: 'bank'});
  assert.equal(f.status, 'failed');
  assert.match(f.reason, /no problem/);
});

test('a site case passes only when the answer gives the problem\'s page', async () => {
  const exams = [{id: 'ipho-2025-T1', comp: 'ipho', year: 2025, task: 'T1', kind: 'theory', competition: {ko: '국제물리올림피아드'}, title: {ko: '수소와 은하'}, paper: 'https://x/y.pdf'}];
  const good = await runSiteCase({AI: fakeAI({answerText: 'https://haslalab.org/#/ipho/2025 에 있어요'})}, Math.random, exams);
  assert.equal(good.score, 1);
  assert.equal(good.verdict, 'correct');
  const bad = await runSiteCase({AI: fakeAI({answerText: '잘 모르겠어요'})}, Math.random, exams);
  assert.equal(bad.score, 0);
  assert.match(bad.reason, /#\/ipho\/2025/);
});

test('the judge\'s verdict is read through thinking and prose', () => {
  assert.deepEqual(readVerdict('<think>hmm</think>결과: {"score": 4, "correct": false, "issues": ["부호 오류"], "reason": "최종 답이 다름"}'),
    {score: 0.4, correct: false, reason: '최종 답이 다름\n· 부호 오류'});
  assert.equal(readVerdict('no json'), null);
  assert.equal(readVerdict('{"score": 15}').score, 1);
});

test('admins review the cases and export the approved ones as training data', async () => {
  class HttpError extends Error { constructor(status, code) { super(code); this.status = status; } }
  const users = {admin: {id: 1, role: 'admin'}, user: {id: 2, role: 'user'}};
  const route = createAiEvalRouter({HttpError, currentUser: async req => users[req.headers.get('X-Who')] || null});
  const env = {DB: d1(), AI: fakeAI(), PROBLEM_BANK: bank()};
  const req = (path, who, init = {}) => new Request('https://x/api/admin/ai-eval' + path, {...init, headers: {'X-Who': who}});
  await assert.rejects(route(req('', 'user'), env), e => e.status === 403);
  await assert.rejects(route(req('', ''), env), e => e.status === 401);
  const run = await route(req('/run', 'admin', {method: 'POST', body: '{"kind":"bank"}'}), env);
  assert.equal(run.day.length, 10);
  const list = await route(req('', 'admin'), env);
  assert.equal(list.items.length, 1);
  assert.equal(list.items[0].id, run.id);
  await assert.rejects(route(req(`/${run.id}`, 'admin', {method: 'POST', body: '{"action":"x"}'}), env), e => e.status === 400);
  const ok = await route(req(`/${run.id}`, 'admin', {method: 'POST', body: JSON.stringify({action: 'approve', corrected: '고친 답'})}), env);
  assert.equal(ok.status, 'approved');
  assert.equal(ok.reviewed_by, 1);
  const out = await route(req('/export', 'admin'), env);
  assert.ok(out instanceof Response);
  const lines = (await out.text()).trim().split('\n').map(l => JSON.parse(l));
  assert.deepEqual(lines[0].messages.map(m => m.role), ['user', 'assistant']);
  assert.equal(lines[0].messages[1].content, '고친 답');
  assert.equal(JSON.parse(trainingLine({question: 'q', answer: 'a'}, 'sys')).messages[0].role, 'system');
});

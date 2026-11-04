import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { createAiTrainRouter, aiSettings, forgetSettings } from './src/ai-train.js';
import { answer, SOLVER_MODEL } from './src/ai-assistant.js';

function d1(sql = new DatabaseSync(':memory:')) {
  const stmt = (q, args = []) => ({
    bind: (...a) => stmt(q, a),
    async all() { return {results: sql.prepare(q).all(...args).map(r => ({...r}))}; },
    async first() { const r = sql.prepare(q).get(...args); return r ? {...r} : null; },
    async run() { const r = sql.prepare(q).run(...args); return {meta: {changes: Number(r.changes)}}; },
  });
  return {sql, prepare: q => stmt(q), batch: async l => Promise.all(l.map(x => x.run()))};
}
class HttpError extends Error { constructor(status, code) { super(code); this.status = status; } }
const KEY = 'k'.repeat(40);
const GUARD = '@cf/meta/llama-guard-3-8b', JUDGE = '@cf/openai/gpt-oss-120b';
function fakeAI() {
  const calls = [];
  return {calls, async run(model, input) {
    calls.push({model, input});
    if (model === GUARD) return {response: 'safe'};
    if (model === JUDGE) return {choices: [{message: {content: JSON.stringify({score: /튜닝/.test(input.messages[1].content) ? 9 : 6})}}]};
    return {response: input.lora ? '<think>x</think>튜닝된 풀이' : '<think>x</think>기본 풀이'};
  }};
}
const bank = {async fetch(url) {
  const u = new URL(url);
  if (u.pathname.endsWith('/recommendations')) return Response.json({items: [{id: 'q1'}, {id: 'q2'}]});
  if (/\/solutions$/.test(u.pathname)) return Response.json({solutions: [{selected_version: {text: '에너지 보존으로 v = 2 m/s 이다.'}}]});
  return Response.json({question: {figures: [], assets: [], selected_version: {text: '질량 1 kg의 공이 높이 0.2 m에서 떨어질 때 바닥에서의 속력을 구하시오.'}}});
}};
const setup = () => {
  const DB = d1(), env = {DB, AI: fakeAI(), PROBLEM_BANK: bank, AI_TRAIN_KEY: KEY};
  const route = createAiTrainRouter({HttpError, currentUser: async req => (req.headers.get('X-Who') === 'admin' ? {id: 1, role: 'admin'} : req.headers.get('X-Who') ? {id: 2, role: 'user'} : null)});
  const call = (path, {method = 'GET', body, key = KEY, who} = {}) => route(new Request('https://x/api/admin/ai-train' + path, {method,
    headers: {...(key ? {'X-Hasla-Train-Key': key} : {}), ...(who ? {'X-Who': who} : {})}, ...(body ? {body: JSON.stringify(body)} : {})}), env);
  return {DB, env, call};
};

test('only the run\'s key or an admin may use the training routes', async () => {
  const {call} = setup();
  await assert.rejects(call('/status', {key: null}), e => e.status === 401);
  await assert.rejects(call('/status', {key: 'k'.repeat(39) + 'x'}), e => e.status === 401, 'a wrong key is no key');
  await assert.rejects(call('/status', {key: null, who: 'user'}), e => e.status === 403);
  assert.ok((await call('/status', {key: null, who: 'admin'})).counts);
  const short = setup();
  short.env.AI_TRAIN_KEY = 'short';
  await assert.rejects(short.call('/status', {key: 'short'}), e => e.status === 401, 'a short Worker key is never accepted');
});

test('the data for each role, and the count of approved examples since the last kept training', async () => {
  const {DB, call} = setup();
  await call('/status');
  const ins = DB.sql.prepare("INSERT INTO ai_eval (day, kind, question, answer, route, status) VALUES ('d', ?, ?, ?, ?, ?)");
  ins.run('bank', '문제 1', '풀이 1', 'solve', 'approved');
  ins.run('member', '안녕', '안녕하세요', 'chat', 'approved');
  ins.run('bank', '문제 2', '풀이 2', 'solve', 'graded');
  const st = await call('/status');
  assert.deepEqual([st.counts.solver.approved, st.counts.chat.approved], [1, 1]);
  const solver = (await (await call('/data?role=solver')).text()).trim().split('\n').map(l => JSON.parse(l));
  assert.deepEqual(solver.map(r => r.messages.at(-1).content), ['풀이 1']);
  const chat = (await (await call('/data?role=chat')).text()).trim().split('\n').map(l => JSON.parse(l));
  assert.deepEqual(chat.map(r => r.messages.at(-1).content), ['안녕하세요']);
});

test('a run is recorded, tried against the current setting, promoted, used by answers, and rolled back', async () => {
  const {DB, env, call} = setup();
  const rec = await call('/record', {method: 'POST', body: {run: 'run-20261104', role: 'solver', status: 'trained', examples: 512, data_max_id: 9,
    candidate: {AI_SOLVER_LORA: 'hasla-solver-20261104', AI_CHAT_URL: 'ignored for the solver'}, cost: 3.1}});
  assert.equal(rec.status, 'trained');
  assert.deepEqual(JSON.parse(rec.candidate), {AI_SOLVER_LORA: 'hasla-solver-20261104'}, 'only the role\'s own keys');
  await assert.rejects(call('/record', {method: 'POST', body: {run: 'x y', role: 'solver'}}), e => e.status === 400);
  // a trial: the same problem with and without the adapter, both graded
  const t = await call('/trial', {method: 'POST', body: {role: 'solver', candidate: {AI_SOLVER_LORA: 'hasla-solver-20261104'}}});
  assert.deepEqual([t.base, t.cand], [0.6, 0.9]);
  const solverCalls = env.AI.calls.filter(c => c.model === SOLVER_MODEL);
  assert.deepEqual(solverCalls.map(c => c.input.lora ?? null), [null, 'hasla-solver-20261104']);
  await assert.rejects(call('/trial', {method: 'POST', body: {role: 'solver', candidate: {}}}), e => e.status === 400);
  // promoted: every answer now uses it, until rolled back
  await call('/promote', {method: 'POST', body: {run: 'run-20261104'}});
  assert.deepEqual(await aiSettings(DB), {AI_SOLVER_LORA: 'hasla-solver-20261104'});
  env.AI.calls.length = 0;
  await answer(env, [{role: 'user', content: '이 문제 풀어줘'}], {route: 'solve', memory: false});
  assert.equal(env.AI.calls.find(c => c.model === SOLVER_MODEL).input.lora, 'hasla-solver-20261104');
  env.AI.calls.length = 0;
  await answer({...env, AI_SOLVER_LORA: 'manual'}, [{role: 'user', content: '이 문제 풀어줘'}], {route: 'solve', memory: false});
  assert.equal(env.AI.calls.find(c => c.model === SOLVER_MODEL).input.lora, 'manual', 'a Worker variable still wins');
  const st = await call('/status');
  assert.equal(st.runs[0].promoted, 1);
  await call('/rollback', {method: 'POST', body: {run: 'run-20261104'}});
  assert.deepEqual(await aiSettings(DB), {});
  assert.equal((await call('/status')).runs[0].status, 'rolled_back');
  forgetSettings();
});

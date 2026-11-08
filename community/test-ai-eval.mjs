import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { aiEvalTick, runEvalCase, readVerdict, koreanClock, evalConfig, createAiEvalRouter, trainingLine, runSiteCase, runBankCase, ensureAiEval } from './src/ai-eval.js';
import { answer } from './src/ai-assistant.js';
import { forgetMemoryCache, forgetFastCache, fastAllowed } from './src/ai-memory.js';

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
    if (model === '@cf/baai/bge-m3') return {data: input.text.map(t => /공/.test(t) ? [1, 0.1, 0] : [0, 1, 0])};
    if (model === JUDGE) return {choices: [{message: {content: judge}}]};
    if (/where on the site/.test(input.messages[0].content)) return {response: 'IPhO 2025 수소와 은하 문제 어디 있어요?'};
    if (/You play a Korean high-school student/.test(input.messages[0].content)) return {response: '풀이 알려주세요'};
    return {response: answerText};
  }};
}
function bank({figure = false} = {}) {
  return {async fetch(url) {
    const u = new URL(url);
    // like the real bank: more than 30 is refused (src/problem-bank.js, invalid_pagination)
    if (u.pathname.endsWith('/recommendations') && !(+u.searchParams.get('limit') <= 30)) return Response.json({error: 'invalid_pagination'}, {status: 400});
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
  assert.deepEqual(lines[0].messages.map(m => m.role), ['system', 'user', 'assistant']);
  assert.equal(lines[0].messages[2].content, '고친 답');
  assert.match(JSON.parse(trainingLine({question: 'q', answer: 'a', style: 'community'})).messages[0].content, /casual tone/);
  // the approved answer is now in memory: the same question gets it back without the chat model
  forgetMemoryCache();
  const calls = env.AI.calls.length;
  const again = await answer(env, [{role: 'user', content: run.question}], {style: run.style});
  assert.equal(again.route, 'cache');
  assert.equal(again.answer, '고친 답');
  assert.ok(!env.AI.calls.slice(calls).some(c => c.model === CHAT), 'no chat model call');
  const other = await answer(env, [{role: 'user', content: '전혀 다른 질문'}], {style: run.style});
  assert.notEqual((await answer(env, [{role: 'user', content: run.question}], {style: run.style === 'community' ? 'default' : 'community'})).route, 'cache', 'another tone is not reused');
  assert.notEqual(other.route, 'cache');
  // rejecting it takes it out of memory again
  await route(req(`/${run.id}`, 'admin', {method: 'POST', body: '{"action":"reject"}'}), env);
  forgetMemoryCache();
  assert.notEqual((await answer(env, [{role: 'user', content: run.question}], {style: run.style})).route, 'cache');
  const listed = await route(req('?status=all', 'admin'), env);
  assert.ok(listed.usage && typeof listed.usage.memory === 'number');
});

test('a table from before the new columns gets them; cases record their route and tone', async () => {
  const db = d1();
  db.sql.exec(`CREATE TABLE ai_eval (id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL, kind TEXT NOT NULL, ref TEXT,
    question TEXT NOT NULL DEFAULT '', answer TEXT, reference TEXT, tools TEXT, score REAL, verdict TEXT, reason TEXT,
    status TEXT NOT NULL DEFAULT 'running', corrected TEXT, note TEXT, created_at INTEGER NOT NULL DEFAULT (unixepoch()),
    reviewed_at INTEGER, reviewed_by INTEGER)`);
  await ensureAiEval(db);
  const cols = db.sql.prepare('PRAGMA table_info(ai_eval)').all().map(c => c.name);
  assert.ok(cols.includes('route') && cols.includes('style'));
  const env = {DB: db, AI: fakeAI(), PROBLEM_BANK: bank()};
  const r = await runBankCase(env, db, Math.random, {style: 'community'});
  assert.equal(r.style, 'community');
  // the problem goes to the reasoning model (sorted as solve), with the tone in its prompt and a reminder on the message
  const sys = env.AI.calls.find(c => /^You are an olympiad physics and mathematics tutor/.test(c.input.messages?.[0]?.content || ''));
  assert.match(sys.input.messages[0].content, /casual tone/);
  assert.match(sys.input.messages.at(-1).content, /커뮤 말투/);
  assert.equal(r.route, 'solve');
  assert.match(env.AI.calls.find(c => c.model === JUDGE).input.messages[1].content, /^Requested tone: Tone: the casual tone/);
});

test('location cases run on the direct site route half the time; a poor record turns that route off', async () => {
  const exams = [{id: 'ipho-2025-T1', comp: 'ipho', year: 2025, task: 'T1', kind: 'theory', competition: {ko: '국제물리올림피아드'}, title: {ko: '수소와 은하'}}];
  const fast = await runSiteCase({AI: fakeAI({answerText: 'https://haslalab.org/#/ipho/2025 에 있어요'})}, () => 0.1, exams, {route: 'fast'});
  assert.equal(fast.route, 'site');
  assert.equal(fast.score, 1);
  const db = d1();
  await ensureAiEval(db);
  for (let i = 0; i < 10; i++) db.sql.prepare("INSERT INTO ai_eval (day, kind, status, route, score) VALUES ('d', 'site', 'graded', 'site', 0)").run();
  forgetFastCache();
  assert.equal(await fastAllowed({}, db), false);
  forgetFastCache();
  assert.equal(await fastAllowed({AI_FAST: 'on'}, db), true);
  forgetFastCache();
});

test('members\' chats wait for review apart from the night\'s total; their earlier turns go into the training line', async () => {
  const {logMemberChat} = await import('./src/ai-memory.js');
  class HttpError extends Error { constructor(status, code) { super(code); this.status = status; } }
  const env = {DB: d1(), AI: fakeAI(), PROBLEM_BANK: bank(), AI_EVAL_DAILY: '1'};
  const id = await logMemberChat(env.DB, {user_id: 5, history: [{role: 'user', content: '앞 질문'}, {role: 'assistant', content: '앞 답'}, {role: 'user', content: '그럼 이건?'}], answer: '이건 이렇게', route: 'explain', style: 'default'});
  assert.ok(await aiEvalTick(env, {now: Date.UTC(2026, 10, 3, 17, 5)}), 'a member\'s chat does not use up the night\'s cases');
  const route = createAiEvalRouter({HttpError, currentUser: async () => ({id: 1, role: 'admin'})});
  const list = await route(new Request('https://x/api/admin/ai-eval?kind=member'), env);
  assert.deepEqual(list.items.map(i => i.id), [id]);
  await route(new Request(`https://x/api/admin/ai-eval/${id}`, {method: 'POST', body: '{"action":"approve"}'}), env);
  const line = JSON.parse((await (await route(new Request('https://x/api/admin/ai-eval/export'), env)).text()).trim());
  assert.deepEqual(line.messages.map(m => m.content).slice(1), ['앞 질문', '앞 답', '그럼 이건?', '이건 이렇게']);
  assert.equal(env.DB.sql.prepare('SELECT count(*) n FROM ai_memory').get().n, 0, 'an answer that needed earlier turns is not reused alone');
});

test('a teacher case: DeepSeek V4 Pro writes a short think and the answer; judged good, it is approved for the solver at once', async () => {
  const { runEvalCase, teacherText, teacherConfig, aiEvalTick } = await import('./src/ai-eval.js');
  const TEACH = '@cf/deepseek-ai/deepseek-v4-pro-0813';
  const ai = fakeAI(), run = ai.run;
  ai.run = async (model, input) => model === TEACH ? {choices: [{message: {content: '<think>\n에너지 보존: mgh = mv^2/2\n</think>\n\n$v=\\sqrt{2gh}=2$ m/s'}}]} : run(model, input);
  const env = {DB: d1(), AI: ai, PROBLEM_BANK: bank()};
  const r = await runEvalCase(env, {day: '2026-11-05', kind: 'teacher'});
  assert.equal(r.status, 'approved');
  assert.equal(r.route, 'solve');
  assert.match(r.answer, /^<think>\n에너지 보존[\s\S]*<\/think>\n\n\$v=/);
  const judged = ai.calls.find(c => c.model === JUDGE);
  assert.ok(!/<think>/.test(judged.input.messages[1].content), 'the judge sees only the answer');
  const row = env.DB.sql.prepare("SELECT kind, status, note, route FROM ai_eval").get();
  assert.deepEqual({...row}, {kind: 'teacher', status: 'approved', note: 'teacher_auto', route: 'solve'});
  // judged wrong: it waits for review; not in the form: ungraded
  const env2 = {DB: d1(), AI: fakeAI({judge: '{"score": 4, "correct": false, "reason": "틀림"}'}), PROBLEM_BANK: bank()};
  const run2 = env2.AI.run; env2.AI.run = async (m, i) => m === TEACH ? {response: '<think>x</think>\n답'} : run2(m, i);
  assert.equal((await runEvalCase(env2, {day: '2026-11-05', kind: 'teacher'})).status, 'graded');
  assert.equal(teacherText({response: '그냥 답'}), null);
  assert.equal(teacherText({response: 'a</think>b'}), '<think>\na\n</think>\n\nb');
  assert.equal(teacherConfig({}).daily, 0);
  assert.equal(teacherConfig({AI_TEACHER_DAILY: '40'}).daily, 40);
  // the night: the teacher's total runs beside the self-test's own
  const env3 = {DB: d1(), AI: ai, PROBLEM_BANK: bank(), AI_EVAL_DAILY: '0', AI_TEACHER_DAILY: '1'};
  const night = Date.UTC(2026, 10, 3, 17, 5);
  assert.equal((await aiEvalTick(env3, {now: night})).kind, 'teacher');
  assert.equal(await aiEvalTick(env3, {now: night}), null);
});

test('the problem picker looks past the first few problems and says why it found none', async () => {
  const { pickBankProblem } = await import('./src/ai-eval.js');
  const env = {DB: d1(), PROBLEM_BANK: bank({figure: true})};
  await ensureAiEval(env.DB);
  await assert.rejects(pickBankProblem(env, env.DB, () => 0.3, 'teacher'), /no problem with a text solution: seen=0 held_out=0 figure=\d+ length=0 no_solution=0 error=0/);
  const ok = {DB: d1(), PROBLEM_BANK: bank()};
  await ensureAiEval(ok.DB);
  assert.match((await pickBankProblem(ok, ok.DB, () => 0.3, 'teacher')).id, /^q\d$/);
});

test('a problem held out for Hasla AI\'s evaluation is never picked for a training case', async () => {
  const { pickBankProblem } = await import('./src/ai-eval.js');
  const { HOLDOUT_BANK_IDS } = await import('./src/ai-holdout.js');
  assert.equal(HOLDOUT_BANK_IDS.size, 30);
  const held = [...HOLDOUT_BANK_IDS][0];
  const real = bank();
  const env = {DB: d1(), PROBLEM_BANK: {async fetch(url) {
    const u = new URL(url);
    if (u.pathname.endsWith('/recommendations')) return Response.json({items: [{id: held}, {id: 'q1'}]});
    return real.fetch(url);
  }}};
  await ensureAiEval(env.DB);
  for (let i = 0; i < 5; i++) assert.equal((await pickBankProblem(env, env.DB, () => i / 5, 'teacher')).id, 'q1');
  const only = {DB: env.DB, PROBLEM_BANK: {async fetch(url) {
    return new URL(url).pathname.endsWith('/recommendations') ? Response.json({items: [{id: held}]}) : real.fetch(url);
  }}};
  await assert.rejects(pickBankProblem(only, only.DB, () => 0.3, 'teacher'), /held_out=3 /);
});

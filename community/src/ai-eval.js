// The assistant's nightly self-test, and the data its LoRA adapters are trained on.
// Every night (from AI_EVAL_HOUR, Korean time, default 02:00) the Worker's minute cron runs one case at a time until
// AI_EVAL_DAILY cases (default 30, 0 turns it off) are done:
//   · bank: a problem bank problem with an official solution and no figure; a model writes what a student would ask
//     about it, the assistant answers (answer() in ai-assistant.js, tools and all), and a judge model grades the answer
//     against the official solution (0–10, with its reasons)
//     (three in ten in the community tone the chat can be switched to, so that tone is learnt from checked answers)
//   · site: a competition problem from the site's catalogue; a model asks where it is; the answer must give its page
//     (graded by the link, no model). Half run on the small model's fast route, half on the big one: the fast route's
//     record decides whether members' questions may go to it (ai-memory.js)
// Admins review the cases (/api/admin/ai-eval, page ai-review.html): approve an answer, or correct it and approve, or
// reject it. The approved cases are the training data (GET …/export: chat JSONL for a LoRA of the chat model) and the
// answers the assistant reuses for the same question (ai-memory.js).
import { answer, runModel, readCompletion, stripThinking, findOlympiadProblems, STYLES, styleOf } from './ai-assistant.js';
import { remember, forget, usageStats, pruneUsage, forgetFastCache } from './ai-memory.js';
import { MODEL_TEST_EXAMS } from './model-test-catalog.js';
import { scrubPersonal } from './pii.js';
import { HOLDOUT_BANK_IDS } from './ai-holdout.js';

export const AI_EVAL_PATH = '/api/admin/ai-eval';
export { AI_EVAL_SQL, ensureAiEval } from './ai-memory.js';
import { ensureAiEval } from './ai-memory.js';
const DAILY = 30, START_HOUR = 2, PARALLEL = 2, STALE_SEC = 900, SITE_SHARE = 0.25, COMMUNITY_SHARE = 0.3, FAST_SHARE = 0.5;
const BANK = 'https://problem-bank/api/problem-bank';
const clip = (v, n) => String(v ?? '').slice(0, n);

export function evalConfig(env) {
  const n = env.AI_EVAL_DAILY == null || env.AI_EVAL_DAILY === '' ? DAILY : Math.max(0, Math.min(500, Math.floor(+env.AI_EVAL_DAILY) || 0));
  const hour = env.AI_EVAL_HOUR == null || env.AI_EVAL_HOUR === '' ? START_HOUR : Math.max(0, Math.min(23, Math.floor(+env.AI_EVAL_HOUR) || 0));
  return {daily: n, hour, parallel: Math.max(1, Math.min(5, +env.AI_EVAL_PARALLEL || PARALLEL))};
}
/* the Korean date and hour of a moment */
export function koreanClock(ms) {
  const k = new Date(ms + 9 * 3600e3);
  return {day: k.toISOString().slice(0, 10), hour: k.getUTCHours()};
}

/* ── one case ─────────────────────────────────────────────── */
const ASK_SYSTEM = `You play a Korean high-school student preparing for science olympiads, writing to a tutor about the
problem below. Write ONE short message (one or two sentences, in Korean) that asks for one of: the full solution, a hint,
a check of a final answer you propose, or the key idea. Do not copy the problem; do not answer it. Write only the message.`;
const SITE_ASK_SYSTEM = `You play a Korean high-school student using HaslaLab, a site of olympiad past papers. Write ONE short
message in Korean asking where on the site to find the problem described below (mention its topic or title, and the
competition or year if you like, as a student would). Write only the message.`;
const JUDGE_SYSTEM = `You grade a tutor's answer to a student's question about an olympiad problem, using the official
solution as the reference. Judge: is the physics or mathematics right; does the final result agree with the official one
(when the student asked for it); does it answer what the student asked (a good hint need not give everything away);
is it clear, in Korean, without invented links or facts; does it keep the requested tone (given below) without any
rude, insulting or vulgar word. Return only JSON:
{"score": <0-10>, "correct": <true|false>, "issues": ["<short issue>", ...], "reason": "<two or three sentences, Korean>"}`;

async function bankJson(env, path) {
  const r = await env.PROBLEM_BANK.fetch(BANK + path);
  if (!r.ok) throw new Error(`problem bank ${r.status} ${path.split('?')[0]}`);
  return r.json();
}
const versionText = x => x?.selected_version?.text || x?.versions?.find(v => v.language === 'ko')?.text || x?.versions?.[0]?.text || '';

/* a problem bank problem with a solution in text and no figure, not tested in the last 90 days */
/* a problem bank problem the assistant can be asked about in text: no figure, a statement of 20–6000 characters and a
   solution in text. Most problems fail one of these (the night of 2026-11-04: every case failed «no problem with a text
   solution» after looking at 4 recommendations), so it looks through up to 3 difficulty levels and 15 unseen problems on
   each, and a miss says why each problem was passed over. */
export async function pickBankProblem(env, db, rand = Math.random, kind = 'bank') {
  if (!env.PROBLEM_BANK) throw new Error('problem bank unavailable');
  const why = {seen: 0, held_out: 0, figure: 0, length: 0, no_solution: 0, error: 0}, start = Math.floor(rand() * 5);
  for (let step = 0; step < 3; step++) {
    const stars = 1 + (start + step * 2) % 5;
    /* 30 is the most the bank serves (more is a 400: invalid_pagination), so every case failed on 2026-11-07 */
    const {items = []} = await bankJson(env, `/recommendations?${new URLSearchParams({lang: 'ko', limit: '30', stars: String(stars)})}`).catch(() => ({items: []}));
    const all = [...new Set(items.map(i => i.id).filter(Boolean))];
    /* held out for Hasla AI's evaluation: never a training case (ai-holdout.js) */
    const ids = all.filter(id => !HOLDOUT_BANK_IDS.has(id));
    why.held_out += all.length - ids.length;
    if (!ids.length) continue;
    const seen = new Set((await db.prepare(`SELECT ref FROM ai_eval WHERE kind=? AND created_at>unixepoch()-7776000 AND ref IN (${ids.map(() => '?').join(',')})`)
      .bind(kind, ...ids).all()).results.map(r => r.ref));
    why.seen += seen.size;
    const order = ids.filter(id => !seen.has(id)).sort(() => rand() - 0.5);
    for (const id of order.slice(0, 15)) {
      try {
        const {question} = await bankJson(env, `/questions/${encodeURIComponent(id)}?lang=ko`);
        if (!question || question.figures?.length || question.assets?.some(a => a.role === 'figure')) { why.figure++; continue; }
        const text = versionText(question);
        if (text.trim().length < 20 || text.length > 6000) { why.length++; continue; }
        const {solutions = []} = await bankJson(env, `/questions/${encodeURIComponent(id)}/solutions?lang=ko`);
        const solution = solutions.map(versionText).find(t => t.trim().length >= 10);
        if (solution) return {id, text, solution};
        why.no_solution++;
      } catch { why.error++; }
    }
  }
  throw new Error('no problem with a text solution: ' + Object.entries(why).map(([k, v]) => `${k}=${v}`).join(' '));
}

async function ask(env, system, content, fallback) {
  try {
    const t = stripThinking(readCompletion(await runModel(env, 'ASKER', {messages: [{role: 'system', content: system}, {role: 'user', content}],
      temperature: 0.9}, 200)).text).replace(/^["'“]|["'”]$/g, '').trim();
    return t && t.length < 400 ? t : fallback;
  } catch { return fallback; }
}

/* the judge's JSON, from a reply that may wrap it in thinking or prose */
export function readVerdict(text) {
  const t = stripThinking(text), m = t.match(/\{[\s\S]*\}/);
  let o = null;
  if (m) { try { o = JSON.parse(m[0]); } catch {} }
  if (!o || !Number.isFinite(+o.score)) return null;
  const score = Math.max(0, Math.min(10, +o.score));
  return {score: score / 10, correct: o.correct === true || (o.correct == null && score >= 7),
    reason: clip([o.reason, ...(Array.isArray(o.issues) ? o.issues.map(i => '· ' + i) : [])].filter(Boolean).join('\n'), 3000)};
}

export async function runBankCase(env, db, rand = Math.random, {style} = {}) {
  style = styleOf(style ?? (rand() < COMMUNITY_SHARE ? 'community' : 'default'));
  const p = await pickBankProblem(env, db, rand);
  const line = await ask(env, ASK_SYSTEM, p.text, '이 문제 어떻게 풀어요? 풀이 과정을 자세히 설명해 주세요.');
  const question = `${line}\n\n${clip(p.text, 3400)}`;
  const r = await answer(env, [{role: 'user', content: question}], {lang: 'ko', style, memory: false});
  const base = {ref: p.id, question, answer: r.answer, reference: clip(p.solution, 8000), tools: JSON.stringify(r.tools || []), route: r.route, style};
  if (r.blocked) return {...base, score: 0, verdict: 'blocked', reason: `안전 검사에서 막힘 (${r.blocked})`};
  const judged = readVerdict(readCompletion(await runModel(env, 'JUDGE', {messages: [{role: 'system', content: JUDGE_SYSTEM},
    {role: 'user', content: `Requested tone: ${STYLES[style].split('\n')[0]}\n\nProblem:\n${clip(p.text, 5000)}\n\nOfficial solution:\n${clip(p.solution, 6000)}\n\nStudent's message:\n${line}\n\nTutor's answer:\n${clip(r.answer, 6000)}`}]}, 4096)).text);
  if (!judged) return {...base, score: null, verdict: 'ungraded', reason: '채점 모델의 답을 읽지 못함'};
  return {...base, score: judged.score, verdict: judged.correct ? 'correct' : 'wrong', reason: judged.reason};
}

/* ── teacher cases: DeepSeek V4 Pro writes the solution QwQ learns from ─────────────
   A problem bank problem and a student's question about it; the teacher answers the way the solver should: a short think
   (the principle, the equations, the checks: what QwQ's think should hold, not a monologue), then the answer to the
   student. The judge grades it against the official solution; one judged correct with 8/10 or more is approved for the
   solver's training at once (route 'solve', kind 'teacher'), the rest wait for an admin like any other case. */
export const TEACHER_SYSTEM = `You are the teacher whose answers train a smaller tutor model. Answer the student's question
about the olympiad problem below in exactly this form:
<think>
the reasoning the tutor needs and nothing more: the principle, the equations in order, a units or limit check — at most
about 250 words, no restating the problem, no hesitation
</think>
the answer to the student, in Korean, step by step, mathematics in LaTeX ($...$ inline, $$...$$ display), the final
result stated clearly; as long as the question needs and no longer.`;
/* AI_TEACHER_DAILY teacher cases a night (none without it; wrangler.toml sets it), on top of the self-test's own total */
export function teacherConfig(env) {
  const n = Math.max(0, Math.min(500, Math.floor(+env.AI_TEACHER_DAILY) || 0));
  return {daily: n};
}
/* the teacher's reply as «<think>…</think> answer», or null when it is not in that form */
export function teacherText(res) {
  const text = readCompletion(res).text;
  const k = text.indexOf('</think>');
  if (k < 0) return null;
  const think = text.slice(0, k).replace(/^[\s\S]*?<think>/, '').trim(), answer = text.slice(k + 8).trim();
  return think && answer ? `<think>\n${think}\n</think>\n\n${answer}` : null;
}
export async function runTeacherCase(env, db, rand = Math.random) {
  const p = await pickBankProblem(env, db, rand, 'teacher');
  const line = await ask(env, ASK_SYSTEM, p.text, '이 문제 어떻게 풀어요? 풀이 과정을 자세히 설명해 주세요.');
  const question = `${line}\n\n${clip(p.text, 3400)}`;
  const res = await runModel(env, 'TEACHER', {messages: [{role: 'system', content: TEACHER_SYSTEM}, {role: 'user', content: question}]}, 8192);
  const text = teacherText(res);
  const base = {ref: p.id, question, reference: clip(p.solution, 8000), tools: '[]', route: 'solve', style: 'default'};
  if (!text) return {...base, answer: clip(readCompletion(res).text, 12000), score: null, verdict: 'ungraded', reason: '선생 모델의 답이 <think> 형식이 아님'};
  const shown = text.slice(text.indexOf('</think>') + 8).trim();
  const judged = readVerdict(readCompletion(await runModel(env, 'JUDGE', {messages: [{role: 'system', content: JUDGE_SYSTEM},
    {role: 'user', content: `Requested tone: ${STYLES.default.split('\n')[0]}\n\nProblem:\n${clip(p.text, 5000)}\n\nOfficial solution:\n${clip(p.solution, 6000)}\n\nStudent's message:\n${line}\n\nTutor's answer:\n${clip(shown, 6000)}`}]}, 4096)).text);
  if (!judged) return {...base, answer: text, score: null, verdict: 'ungraded', reason: '채점 모델의 답을 읽지 못함'};
  const good = judged.correct && judged.score >= 0.8;
  return {...base, answer: text, score: judged.score, verdict: judged.correct ? 'correct' : 'wrong', reason: judged.reason,
    ...(good ? {status: 'approved', note: 'teacher_auto'} : {})};
}

export async function runSiteCase(env, rand = Math.random, exams = MODEL_TEST_EXAMS, {route} = {}) {
  route = {fast: 'site', big: 'tools'}[route] || route || (rand() < FAST_SHARE ? 'site' : 'tools');
  const pool = exams.filter(e => e.title?.ko || e.title?.en);
  const e = pool[Math.floor(rand() * pool.length)];
  const page = `#/${e.comp}/${e.year}`, title = e.title?.ko || e.title?.en;
  const desc = `${e.competition?.ko || e.comp} ${e.year} ${e.task} (${e.kind}): «${title}»`;
  const question = await ask(env, SITE_ASK_SYSTEM, desc, `${e.year}년 ${e.competition?.ko || e.comp.toUpperCase()} «${title}» 문제 어디서 볼 수 있어요?`);
  const r = await answer(env, [{role: 'user', content: question}], {lang: 'ko', route, memory: false});
  const found = r.answer.includes(page) || (r.sources || []).some(s => String(s.url).includes(page));
  const hit = findOlympiadProblems({query: title, comp: e.comp, year: e.year}, [e])[0];
  return {ref: e.id, question, answer: r.answer, tools: JSON.stringify(r.tools || []), route: r.route, style: 'default',
    reference: [desc, hit?.page, hit?.paper].filter(Boolean).join('\n'), score: found ? 1 : 0,
    verdict: r.blocked ? 'blocked' : found ? 'correct' : 'wrong',
    reason: found ? '문제 페이지 링크를 안내함' : r.blocked ? `안전 검사에서 막힘 (${r.blocked})` : `정답 링크(${SITE_URL}${page})가 답에 없음`};
}
const SITE_URL = 'https://haslalab.org/';

/* claim a slot (counted against today's total and the cases running now), run it, store the result */
export async function runEvalCase(env, {day, kind, rand = Math.random} = {}) {
  const db = env.DB, cfg = evalConfig(env);
  await ensureAiEval(db);
  kind ||= rand() < SITE_SHARE ? 'site' : 'bank';
  const claim = await db.prepare(`INSERT INTO ai_eval (day, kind, status) SELECT ?, ?, 'running'
      WHERE (SELECT count(*) FROM ai_eval WHERE status='running') < ? RETURNING id`).bind(day, kind, cfg.parallel).first();
  if (!claim) return null;
  if (rand() < 0.1) await pruneUsage(db).catch(() => {});
  let row;
  try {
    row = {status: 'graded', ...(kind === 'site' ? await runSiteCase(env, rand) : kind === 'teacher' ? await runTeacherCase(env, db, rand) : await runBankCase(env, db, rand))};
    if (/^(site|fast)/.test(row.route || '')) forgetFastCache();
  } catch (e) {
    row = {status: 'failed', reason: clip(e?.message || e, 300)};
  }
  await db.prepare(`UPDATE ai_eval SET route=?, style=?, ref=?, question=?, answer=?, reference=?, tools=?, score=?, verdict=?, reason=?, status=?, note=COALESCE(?, note) WHERE id=?`)
    .bind(row.route ?? null, row.style || 'default', row.ref ?? null, clip(row.question, 8000), row.answer == null ? null : clip(row.answer, 12000), row.reference == null ? null : clip(row.reference, 8000),
      row.tools ?? null, row.score ?? null, row.verdict ?? null, row.reason ?? null, row.status, row.note ?? null, claim.id).run();
  return {id: claim.id, kind, ...row};
}

/* the minute cron: tonight's cases, one per tick until the day's total is reached */
export async function aiEvalTick(env, {now = Date.now()} = {}) {
  if (!env.AI || !env.DB) return null;
  const cfg = evalConfig(env), {day, hour} = koreanClock(now);
  if ((!cfg.daily && !teacherConfig(env).daily) || hour < cfg.hour) return null;
  await ensureAiEval(env.DB);
  await env.DB.prepare(`UPDATE ai_eval SET status='failed', reason='timed out' WHERE status='running' AND created_at<unixepoch()-?`).bind(STALE_SEC).run();
  const {n} = await env.DB.prepare(`SELECT count(*) AS n FROM ai_eval WHERE day=? AND status!='failed' AND kind NOT IN ('member','teacher')`).bind(day).first();
  const {f} = await env.DB.prepare(`SELECT count(*) AS f FROM ai_eval WHERE day=? AND status='failed' AND kind NOT IN ('member','teacher')`).bind(day).first();
  /* the teacher's cases have their own night total and stop after as many failures */
  const t = teacherConfig(env), tc = t.daily ? await env.DB.prepare(`SELECT sum(status!='failed') AS n, sum(status='failed') AS f FROM ai_eval WHERE day=? AND kind='teacher'`).bind(day).first() : null;
  const teacherDue = !!tc && (tc.n || 0) < t.daily && (tc.f || 0) < t.daily;
  const selfDue = n < cfg.daily && f < cfg.daily;
  if (!selfDue && !teacherDue) return null;   // the day's totals, or a night of failures: stop until tomorrow
  return runEvalCase(env, {day, kind: teacherDue && (!selfDue || Math.random() < 0.5) ? 'teacher' : undefined});
}

/* ── admin review ─────────────────────────────────────────── */
const REVIEW = new Set(['approve', 'reject', 'reset']);
/* one chat-format training line; the system line names the tone, as the assistant's prompt does */
export function trainingLine(row) {
  const system = `You are Hasla AI (하슬라 AI), HaslaLab's assistant. ${STYLES[styleOf(row.style)].split('\n')[0]}`;
  let context = [];
  try { context = JSON.parse(row.context || '[]').filter(m => m && (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string'); } catch {}
  /* a member's name, school or contact written into a chat stays out of training (pii.js) */
  return JSON.stringify({messages: [{role: 'system', content: system}, ...context.map(m => ({role: m.role, content: scrubPersonal(m.content)})),
    {role: 'user', content: scrubPersonal(row.question)}, {role: 'assistant', content: scrubPersonal(row.corrected || row.answer)}]});
}

export function createAiEvalRouter({HttpError, currentUser}) {
  return async function aiEval(req, env) {
    const me = await currentUser(req, env);
    if (!me) throw new HttpError(401, 'login_required');
    if (me.role !== 'admin') throw new HttpError(403, 'forbidden');
    const db = env.DB, url = new URL(req.url), p = url.pathname.replace(/\/+$/, ''), m = req.method;
    await ensureAiEval(db);
    if (p === AI_EVAL_PATH && m === 'GET') {
      const status = url.searchParams.get('status') || 'graded', before = +url.searchParams.get('before') || 0;
      const lim = Math.max(1, Math.min(100, +url.searchParams.get('limit') || 30));
      const where = [], args = [];
      if (status !== 'all') { where.push('status=?'); args.push(status); }
      if (before) { where.push('id<?'); args.push(before); }
      const kind = url.searchParams.get('kind');
      if (kind === 'member') where.push("kind='member'");
      else if (kind === 'eval') where.push("kind!='member'");
      const verdict = url.searchParams.get('verdict');
      if (verdict) { where.push('verdict=?'); args.push(verdict); }
      const items = (await db.prepare(`SELECT * FROM ai_eval ${where.length ? 'WHERE ' + where.join(' AND ') : ''} ORDER BY id DESC LIMIT ?`).bind(...args, lim).all()).results;
      const days = (await db.prepare(`SELECT day, kind, coalesce(route,'') AS route, count(*) AS n, avg(score) AS avg, sum(verdict='correct') AS correct, sum(status='failed') AS failed,
          sum(status='approved') AS approved FROM ai_eval WHERE day>=date('now','-14 days') GROUP BY day, kind, route ORDER BY day DESC, kind, route`).all()).results;
      const counts = Object.fromEntries((await db.prepare(`SELECT status, count(*) AS n FROM ai_eval GROUP BY status`).all()).results.map(r => [r.status, r.n]));
      return {items, days, counts, config: evalConfig(env), usage: await usageStats(db, 7).catch(() => null)};
    }
    if (p === AI_EVAL_PATH + '/run' && m === 'POST') {
      const body = await req.json().catch(() => ({}));
      const r = await runEvalCase(env, {day: koreanClock(Date.now()).day, kind: ['bank', 'site'].includes(body?.kind) ? body.kind : undefined});
      if (!r) throw new HttpError(429, 'busy');
      return db.prepare('SELECT * FROM ai_eval WHERE id=?').bind(r.id).first();
    }
    if (p === AI_EVAL_PATH + '/export' && m === 'GET') {
      const style = url.searchParams.get('style');
      const rows = (await db.prepare(`SELECT question, answer, corrected, style, context FROM ai_eval WHERE status='approved' ${style ? 'AND style=?' : ''} ORDER BY id`)
        .bind(...(style ? [styleOf(style)] : [])).all()).results;
      return new Response(rows.map(r => trainingLine(r)).join('\n') + (rows.length ? '\n' : ''), {headers: {
        'Content-Type': 'application/x-ndjson; charset=utf-8', 'Content-Disposition': 'attachment; filename="haslalab-ai-train.jsonl"', 'Cache-Control': 'no-store'}});
    }
    const one = new RegExp(`^${AI_EVAL_PATH}/(\\d+)$`).exec(p);
    if (one && m === 'POST') {
      const body = await req.json().catch(() => null);
      if (!REVIEW.has(body?.action)) throw new HttpError(400, 'invalid_action');
      const corrected = typeof body.corrected === 'string' && body.corrected.trim() ? clip(body.corrected.trim(), 12000) : null;
      const status = {approve: 'approved', reject: 'rejected', reset: 'graded'}[body.action];
      const row = await db.prepare(`UPDATE ai_eval SET status=?, corrected=?, note=?, reviewed_at=unixepoch(), reviewed_by=?
          WHERE id=? AND status IN ('graded','approved','rejected') RETURNING *`)
        .bind(status, body.action === 'reset' ? null : corrected, clip(body.note, 1000) || null, me.id, +one[1]).first();
      if (!row) throw new HttpError(404, 'not_found');
      // an approved answer is reused for the same question; a rejected or reopened one is not
      if (status === 'approved') await remember(env, db, row).catch(e => console.error('ai-memory', String(e?.message || e).slice(0, 200)));
      else await forget(db, row.id).catch(() => {});
      return row;
    }
    throw new HttpError(404, 'not_found');
  };
}

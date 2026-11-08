// Hasla AI's automatic training (the GitHub workflow train-ai.yml with tools/ai/autotrain.py does the outside work:
// a RunPod GPU trains a LoRA on the approved conversations, then the adapter is uploaded to Cloudflare or W&B).
// This side keeps:
//   · ai_settings: which adapter each role uses now (AI_SOLVER_LORA, AI_CHAT_URL/AI_CHAT_REMOTE …), read by every
//     answer (cached for a minute) on top of the Worker's variables, so a promotion needs no deploy
//   · ai_train: one row per training run (data, cost, the two scores, promoted or not, what it replaced)
//   · /api/admin/ai-train/*: the training data, a trial (the same problem answered with and without the candidate,
//     both graded by the judge against the official solution), promote and rollback
// The workflow authenticates with a key it sets as the Worker secret AI_TRAIN_KEY for the run (X-Hasla-Train-Key);
// an admin's own login works too.
import { answer, runModel, readCompletion } from './ai-assistant.js';
import { pickBankProblem, readVerdict } from './ai-eval.js';
import { ensureAiEval } from './ai-memory.js';
import { trainingLine } from './ai-eval.js';
import { checkAiKeys } from './ai-keys.js';

export const AI_TRAIN_PATH = '/api/admin/ai-train';
export const SETTING_KEYS = ['AI_SOLVER_LORA', 'AI_CHAT_LORA', 'AI_GUARD_LORA', 'AI_CHAT_URL', 'AI_CHAT_REMOTE', 'AI_CHAT_PROJECT', 'AI_FAST_URL', 'AI_FAST_REMOTE', 'AI_FAST_PROJECT'];
export const AI_TRAIN_SQL = [
  `CREATE TABLE IF NOT EXISTS ai_settings (k TEXT PRIMARY KEY, v TEXT NOT NULL, updated_at INTEGER NOT NULL DEFAULT (unixepoch()))`,
  `CREATE TABLE IF NOT EXISTS ai_train (id INTEGER PRIMARY KEY AUTOINCREMENT, run TEXT NOT NULL UNIQUE, role TEXT NOT NULL,
    status TEXT NOT NULL, examples INTEGER, data_max_id INTEGER, artifact TEXT, candidate TEXT, prev TEXT, base_score REAL,
    cand_score REAL, trials INTEGER, promoted INTEGER NOT NULL DEFAULT 0, cost REAL, note TEXT,
    created_at INTEGER NOT NULL DEFAULT (unixepoch()), updated_at INTEGER NOT NULL DEFAULT (unixepoch()))`,
];
const SETTINGS_TTL = 60e3, MIN_KEY = 32;
const clip = (v, n) => String(v ?? '').slice(0, n);

const ready = new WeakMap();
export function ensureAiTrain(db) {
  if (!ready.has(db)) ready.set(db, (async () => { for (const q of AI_TRAIN_SQL) await db.prepare(q).run(); })().catch(e => { ready.delete(db); throw e; }));
  return ready.get(db);
}

/* the adapters in use, cached per isolate for a minute; a broken table never stops an answer */
let cache = null;
export function forgetSettings() { cache = null; }
export async function aiSettings(db) {
  if (!db) return {};
  if (cache && cache.db === db && Date.now() - cache.at < SETTINGS_TTL) return cache.v;
  let v = {};
  try {
    await ensureAiTrain(db);
    for (const r of (await db.prepare('SELECT k, v FROM ai_settings').all()).results) if (SETTING_KEYS.includes(r.k) && r.v) v[r.k] = r.v;
  } catch { v = {}; }
  cache = {db, at: Date.now(), v};
  return v;
}
/* the role's settings: a candidate (keys given) replaces the role's adapter keys entirely */
export const withSettings = (env, settings) => ({...env, ...settings});
async function writeSettings(db, settings, role) {
  const keys = SETTING_KEYS.filter(k => k.startsWith(`AI_${role.toUpperCase()}_`));
  for (const k of keys) {
    if (settings[k]) await db.prepare(`INSERT INTO ai_settings (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v, updated_at=unixepoch()`).bind(k, clip(settings[k], 500)).run();
    else await db.prepare('DELETE FROM ai_settings WHERE k=?').bind(k).run();
  }
  forgetSettings();
}
const roleSettings = (settings, role) => Object.fromEntries(SETTING_KEYS.filter(k => k.startsWith(`AI_${role.toUpperCase()}_`) && settings[k]).map(k => [k, settings[k]]));
const cleanCandidate = (c, role) => {
  const out = {};
  for (const k of SETTING_KEYS) if (k.startsWith(`AI_${role.toUpperCase()}_`) && typeof c?.[k] === 'string' && c[k].trim()) out[k] = clip(c[k].trim(), 500);
  return out;
};

/* which approved conversations train which role: the solver learns from worked solutions, the chat model from the rest */
const ROLE_WHERE = {
  solver: `(route='solve' OR (kind='bank' AND route IS NULL))`,
  chat: `NOT (route='solve' OR (kind='bank' AND route IS NULL))`,
};

/* one trial: the same problem and question answered by the current setting and by the candidate, both graded */
const JUDGE = `You grade a tutor's answer to a student's question about an olympiad problem against the official solution:
is the physics or mathematics right, does the final result agree with the official one when it was asked for, is it
clear and correct in the student's language, without invented facts. Return only JSON:
{"score": <0-10>, "correct": <true|false>, "issues": ["<short issue>"], "reason": "<one or two sentences>"}`;
/* the role's adapter keys pinned to exactly these settings ('' clears one), so neither the promoted settings nor a
   leftover key leaks into the side being tested */
const roleKeys = role => SETTING_KEYS.filter(k => k.startsWith(`AI_${role.toUpperCase()}_`));
export const pinned = (env, role, settings) => ({...env, ...Object.fromEntries(roleKeys(role).map(k => [k, settings[k] || '']))});
export async function trial(env, role, candidate, rand = Math.random, base = null) {
  const p = await pickBankProblem(env, env.DB, rand);
  const question = `이 문제 풀이 과정을 설명해 주세요.\n\n${clip(p.text, 3400)}`;
  const route = role === 'solver' ? 'solve' : 'explain';
  const grade = async text => {
    const v = readVerdict(readCompletion(await runModel(env, 'JUDGE', {messages: [{role: 'system', content: JUDGE},
      {role: 'user', content: `Problem:\n${clip(p.text, 5000)}\n\nOfficial solution:\n${clip(p.solution, 6000)}\n\nTutor's answer:\n${clip(text, 6000)}`}]}, 4096)).text);
    return v ? v.score : null;
  };
  const before = await answer(base ? pinned(env, role, base) : env, [{role: 'user', content: question}], {route, memory: false});
  const after = await answer(pinned(env, role, candidate), [{role: 'user', content: question}], {route, memory: false});
  const [b, c] = await Promise.all([grade(before.answer), grade(after.answer)]);
  return {ref: p.id, base: b, cand: c};
}

const sameKey = (a, b) => {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
};

export function createAiTrainRouter({HttpError, currentUser, monthlyTrial = null}) {
  return async function aiTrain(req, env) {
    const key = req.headers.get('X-Hasla-Train-Key');
    const machine = typeof env.AI_TRAIN_KEY === 'string' && env.AI_TRAIN_KEY.length >= MIN_KEY && sameKey(key || '', env.AI_TRAIN_KEY);
    if (!machine) {
      const me = await currentUser(req, env);
      if (!me) throw new HttpError(401, 'login_required');
      if (me.role !== 'admin') throw new HttpError(403, 'forbidden');
    }
    const db = env.DB, url = new URL(req.url), p = url.pathname.replace(/\/+$/, ''), m = req.method;
    /* do the AI and search keys work (statuses only; ai-keys.js) */
    if (p === AI_TRAIN_PATH + '/keys' && m === 'GET') return {keys: await checkAiKeys(env)};
    await ensureAiTrain(db);
    await ensureAiEval(db);
    const body = m === 'POST' ? await req.json().catch(() => ({})) : {};
    /* re-read and trial-grade stored monthly answer-sheet pages (index.js monthlyTrial) */
    if (p === AI_TRAIN_PATH + '/monthly-trial' && m === 'POST' && monthlyTrial) return monthlyTrial(env, body);
    const role = (m === 'POST' ? body.role : url.searchParams.get('role')) === 'chat' ? 'chat' : 'solver';

    if (p === AI_TRAIN_PATH + '/status' && m === 'GET') {
      const counts = {};
      for (const r of ['solver', 'chat']) {
        const last = await db.prepare(`SELECT max(data_max_id) AS id FROM ai_train WHERE role=? AND status IN ('promoted','rejected','rolled_back')`).bind(r).first();
        const c = await db.prepare(`SELECT count(*) AS n, sum(id>?) AS fresh, max(id) AS max_id FROM ai_eval WHERE status='approved' AND ${ROLE_WHERE[r]}`).bind(last?.id || 0).first();
        counts[r] = {approved: c.n || 0, new_since_last: c.fresh || 0, max_id: c.max_id || 0};
      }
      const runs = (await db.prepare('SELECT * FROM ai_train ORDER BY id DESC LIMIT 20').all()).results;
      const settings = (await db.prepare('SELECT k, v, updated_at FROM ai_settings ORDER BY k').all()).results;
      return {counts, runs, settings};
    }
    if (p === AI_TRAIN_PATH + '/data' && m === 'GET') {
      const rows = (await db.prepare(`SELECT id, question, answer, corrected, style, context FROM ai_eval WHERE status='approved' AND ${ROLE_WHERE[role]} ORDER BY id`).all()).results;
      return new Response(rows.map(r => trainingLine(r)).join('\n') + (rows.length ? '\n' : ''), {headers: {'Content-Type': 'application/x-ndjson; charset=utf-8', 'Cache-Control': 'no-store'}});
    }
    if (p === AI_TRAIN_PATH + '/record' && m === 'POST') {
      const run = clip(body.run, 80);
      if (!/^[\w.-]{6,80}$/.test(run)) throw new HttpError(400, 'invalid_run');
      const num = v => (Number.isFinite(+v) ? +v : null);
      await db.prepare(`INSERT INTO ai_train (run, role, status, examples, data_max_id, artifact, candidate, base_score, cand_score, trials, cost, note)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
          ON CONFLICT(run) DO UPDATE SET status=excluded.status, examples=coalesce(excluded.examples, examples), data_max_id=coalesce(excluded.data_max_id, data_max_id),
            artifact=coalesce(excluded.artifact, artifact), candidate=coalesce(excluded.candidate, candidate), base_score=coalesce(excluded.base_score, base_score),
            cand_score=coalesce(excluded.cand_score, cand_score), trials=coalesce(excluded.trials, trials), cost=coalesce(excluded.cost, cost),
            note=coalesce(excluded.note, note), updated_at=unixepoch()`)
        .bind(run, role, clip(body.status || 'started', 30), num(body.examples), num(body.data_max_id), body.artifact ? clip(body.artifact, 500) : null,
          body.candidate ? JSON.stringify(cleanCandidate(body.candidate, role)) : null, num(body.base_score), num(body.cand_score), num(body.trials), num(body.cost),
          body.note ? clip(body.note, 2000) : null).run();
      return db.prepare('SELECT * FROM ai_train WHERE run=?').bind(run).first();
    }
    if (p === AI_TRAIN_PATH + '/trial' && m === 'POST') {
      const candidate = cleanCandidate(body.candidate, role);
      if (!Object.keys(candidate).length) throw new HttpError(400, 'invalid_candidate');
      const current = await aiSettings(db);
      // base: the settings to compare against (after a promotion, the ones it replaced; {} is the untuned model)
      return trial(withSettings(env, current), role, candidate, Math.random, body.base && typeof body.base === 'object' ? cleanCandidate(body.base, role) : null);
    }
    /* does the new adapter answer at all, without the fallback to the untuned model hiding a failure? */
    if (p === AI_TRAIN_PATH + '/ping' && m === 'POST') {
      const candidate = cleanCandidate(body.candidate, role);
      if (!Object.keys(candidate).length) throw new HttpError(400, 'invalid_candidate');
      const probe = pinned(env, role, candidate);
      if (role === 'chat') probe.AI = {run: async () => { throw new Error('the remote endpoint did not answer'); }};
      try {
        const r = readCompletion(await runModel(probe, role === 'chat' ? 'CHAT' : 'SOLVER', {messages: [{role: 'user', content: '1+1은? 숫자만 답해.'}]}, role === 'chat' ? 32 : 2048));
        return {ok: !!r.text.trim(), text: clip(r.text, 200)};
      } catch (e) { return {ok: false, error: clip(e?.message || e, 300)}; }
    }
    const act = /\/(promote|rollback)$/.exec(p);
    if (act && p.startsWith(AI_TRAIN_PATH) && m === 'POST') {
      const row = await db.prepare('SELECT * FROM ai_train WHERE run=?').bind(clip(body.run, 80)).first();
      if (!row) throw new HttpError(404, 'not_found');
      const current = await aiSettings(db);
      if (act[1] === 'promote') {
        const cand = JSON.parse(row.candidate || '{}');
        if (!Object.keys(cand).length) throw new HttpError(400, 'invalid_candidate');
        await writeSettings(db, cand, row.role);
        await db.prepare(`UPDATE ai_train SET status='promoted', promoted=1, prev=?, updated_at=unixepoch() WHERE id=?`).bind(JSON.stringify(roleSettings(current, row.role)), row.id).run();
      } else {
        await writeSettings(db, JSON.parse(row.prev || '{}'), row.role);
        await db.prepare(`UPDATE ai_train SET status='rolled_back', promoted=0, updated_at=unixepoch() WHERE id=?`).bind(row.id).run();
      }
      return {ok: true, settings: await aiSettings(db)};
    }
    throw new HttpError(404, 'not_found');
  };
}

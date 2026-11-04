// What makes the assistant cheaper and faster as it is used (ai-assistant.js), Gemini-Flash style:
//   · memory: answers an admin approved (ai-eval.js) are kept with an embedding of their question (bge-m3); a
//     member's single question close enough to one of them (cosine ≥ AI_CACHE_MIN, default 0.92) gets the approved
//     answer at once, with no chat model call
//   · usage: every answer's route (cache, fast, big), time and tokens, for the admin review page
//   · site route watch: the nightly self-test also runs location questions on the direct site route; when it does worse
//     than 70 % over the last two weeks (10 cases or more), the router sends them to the orchestrator (AI_FAST=on/off overrides)
export const EMBED_MODEL = '@cf/baai/bge-m3';
export const AI_MEMORY_SQL = [
  `CREATE TABLE IF NOT EXISTS ai_memory (id INTEGER PRIMARY KEY AUTOINCREMENT, eval_id INTEGER UNIQUE, question TEXT NOT NULL,
    answer TEXT NOT NULL, style TEXT NOT NULL DEFAULT 'default', vec BLOB NOT NULL, hits INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL DEFAULT (unixepoch()))`,
  `CREATE TABLE IF NOT EXISTS ai_usage (id INTEGER PRIMARY KEY AUTOINCREMENT, at INTEGER NOT NULL DEFAULT (unixepoch()), user_id INTEGER,
    route TEXT NOT NULL, style TEXT, ms INTEGER, tokens_in INTEGER, tokens_out INTEGER, calls INTEGER, tools TEXT, blocked TEXT)`,
  `CREATE INDEX IF NOT EXISTS ai_usage_at ON ai_usage(at)`,
];
/* the self-test's cases and the members' conversations (kind 'member', kept only when the member allowed it in the
   chat), both reviewed by an admin on ai-review.html */
export const AI_EVAL_SQL = [
  `CREATE TABLE IF NOT EXISTS ai_eval (id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL, kind TEXT NOT NULL, ref TEXT,
    question TEXT NOT NULL DEFAULT '', answer TEXT, reference TEXT, tools TEXT, score REAL, verdict TEXT, reason TEXT,
    status TEXT NOT NULL DEFAULT 'running', corrected TEXT, note TEXT, created_at INTEGER NOT NULL DEFAULT (unixepoch()),
    reviewed_at INTEGER, reviewed_by INTEGER)`,
  `CREATE INDEX IF NOT EXISTS ai_eval_day ON ai_eval(day)`,
  `CREATE INDEX IF NOT EXISTS ai_eval_status ON ai_eval(status, id)`,
];
// columns added after the table first went out (a duplicate column error means it is there already)
const AI_EVAL_COLUMNS = [`ALTER TABLE ai_eval ADD COLUMN route TEXT`, `ALTER TABLE ai_eval ADD COLUMN style TEXT NOT NULL DEFAULT 'default'`,
  `ALTER TABLE ai_eval ADD COLUMN context TEXT`];
const evalReady = new WeakMap();
/* ALTER TABLE … ADD COLUMN that is already done elsewhere (another isolate) is fine */
export const addColumn = db => async q => { try { await db.prepare(q).run(); } catch (e) { if (!/duplicate column/i.test(String(e?.message || e))) throw e; } };
export function ensureAiEval(db) {
  if (!evalReady.has(db)) evalReady.set(db, runEach(db, AI_EVAL_SQL)
    .then(() => Promise.all(AI_EVAL_COLUMNS.map(addColumn(db))))
    .catch(e => { evalReady.delete(db); throw e; }));
  return evalReady.get(db);
}
const MEMBER_KEEP_DAYS = 365;   // a member's conversation not reviewed within a year is deleted (the privacy notice)

/* a member's exchange for review: the last message, the turns before it (context), the answer */
export async function logMemberChat(db, {user_id, history, answer, route, style}) {
  await ensureAiEval(db);
  const last = history[history.length - 1], before = history.slice(0, -1).slice(-6).map(m => ({role: m.role, content: String(m.content).slice(0, 2000)}));
  const day = new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
  const row = await db.prepare(`INSERT INTO ai_eval (day, kind, ref, question, answer, route, style, context, status) VALUES (?, 'member', ?, ?, ?, ?, ?, ?, 'graded') RETURNING id`)
    .bind(day, String(user_id), String(last.content).slice(0, 8000), String(answer || '').slice(0, 12000), route || null, style || 'default',
      before.length ? JSON.stringify(before) : null).first();
  return row?.id ?? null;
}
/* 👍/👎 on one's own logged answer */
export async function memberFeedback(db, userId, id, good) {
  if (!db) return false;
  await ensureAiEval(db);
  const r = await db.prepare(`UPDATE ai_eval SET verdict=? WHERE id=? AND kind='member' AND ref=?`).bind(good ? 'good' : 'bad', id, String(userId)).run();
  return (r?.meta?.changes ?? 0) > 0;
}
/* a member deleted (or edited away) one exchange in the chat: it goes from the review queue and the saved answers */
export async function forgetMemberChat(db, userId, ids) {
  if (!db || !ids.length) return 0;
  await ensureAiEval(db);
  await ensureAiMemory(db);
  const q = ids.map(() => '?').join(',');
  await db.prepare(`DELETE FROM ai_memory WHERE eval_id IN (SELECT id FROM ai_eval WHERE id IN (${q}) AND kind='member' AND ref=?)`).bind(...ids, String(userId)).run().catch(() => {});
  const r = await db.prepare(`DELETE FROM ai_eval WHERE id IN (${q}) AND kind='member' AND ref=?`).bind(...ids, String(userId)).run();
  forgetMemoryCache();
  return r?.meta?.changes ?? 0;
}
/* what a member's withdrawal of consent or deletion of the account removes */
export async function forgetMember(db, userId) {
  await ensureAiEval(db);
  await ensureAiMemory(db);
  await db.prepare(`DELETE FROM ai_memory WHERE eval_id IN (SELECT id FROM ai_eval WHERE kind='member' AND ref=?)`).bind(String(userId)).run().catch(() => {});
  await db.prepare(`DELETE FROM ai_eval WHERE kind='member' AND ref=?`).bind(String(userId)).run();
}

const CACHE_MIN = 0.92, MEMORY_TTL = 10 * 60e3, FAST_TTL = 10 * 60e3, KEEP_USAGE_DAYS = 90;

const ready = new WeakMap();
/* one statement after the other: an index is prepared only once its table is there */
async function runEach(db, list) { for (const q of list) await db.prepare(q).run(); }
export function ensureAiMemory(db) {
  if (!ready.has(db)) ready.set(db, runEach(db, AI_MEMORY_SQL).catch(e => { ready.delete(db); throw e; }));
  return ready.get(db);
}

export async function embed(env, text) {
  const r = await env.AI.run(env.AI_EMBED_MODEL || EMBED_MODEL, {text: [String(text).slice(0, 4000)]});
  const v = r?.data?.[0];
  if (!Array.isArray(v) && !ArrayBuffer.isView(v)) throw new Error('no embedding');
  return normalise(Float32Array.from(v));
}
function normalise(v) {
  let n = 0;
  for (const x of v) n += x * x;
  n = Math.sqrt(n) || 1;
  for (let i = 0; i < v.length; i++) v[i] /= n;
  return v;
}
const toBlob = v => new Uint8Array(v.buffer.slice(v.byteOffset, v.byteOffset + v.byteLength));
const fromBlob = b => {
  const bytes = b instanceof ArrayBuffer ? new Uint8Array(b) : ArrayBuffer.isView(b) ? new Uint8Array(b.buffer, b.byteOffset, b.byteLength) : Uint8Array.from(b || []);
  return new Float32Array(bytes.slice().buffer);
};
const dot = (a, b) => { let s = 0; for (let i = 0; i < a.length; i++) s += a[i] * b[i]; return s; };

/* the approved answers, read once per isolate every ten minutes (they change only when an admin reviews) */
let memory = null;
export function forgetMemoryCache() { memory = null; }
async function memoryRows(db) {
  if (memory && memory.db === db && Date.now() - memory.at < MEMORY_TTL) return memory.rows;
  await ensureAiMemory(db);
  // the answer's language: an English question must not get a Korean answer back
  const rows = (await db.prepare('SELECT id, answer, style, vec FROM ai_memory').all()).results
    .map(r => ({...r, vec: fromBlob(r.vec), lang: /[가-힣]/.test(r.answer) ? 'ko' : 'en'}));
  memory = {db, at: Date.now(), rows};
  return rows;
}

export async function recall(env, db, question, style = 'default', lang = null) {
  const rows = (await memoryRows(db)).filter(r => r.style === style && (!lang || r.lang === lang));
  if (!rows.length) return null;
  const q = await embed(env, question), min = +env.AI_CACHE_MIN || CACHE_MIN;
  let best = null, score = -1;
  for (const r of rows) { const s = r.vec.length === q.length ? dot(q, r.vec) : -1; if (s > score) { score = s; best = r; } }
  if (!best || score < min) return null;
  await db.prepare('UPDATE ai_memory SET hits=hits+1 WHERE id=?').bind(best.id).run().catch(() => {});
  return {answer: best.answer, score, id: best.id};
}

export async function remember(env, db, row) {
  await ensureAiMemory(db);
  const answer = row.corrected || row.answer;
  if (!row.question || !answer) return null;
  if (row.context && row.context !== '[]') return null;   // an answer that leaned on earlier turns is not reused alone
  const vec = await embed(env, row.question);
  await db.prepare(`INSERT INTO ai_memory (eval_id, question, answer, style, vec) VALUES (?, ?, ?, ?, ?)
      ON CONFLICT(eval_id) DO UPDATE SET question=excluded.question, answer=excluded.answer, style=excluded.style, vec=excluded.vec`)
    .bind(row.id, row.question, answer, row.style || 'default', toBlob(vec)).run();
  forgetMemoryCache();
  return true;
}
export async function forget(db, evalId) {
  await ensureAiMemory(db);
  await db.prepare('DELETE FROM ai_memory WHERE eval_id=?').bind(evalId).run();
  forgetMemoryCache();
}

export async function logUsage(db, u) {
  await ensureAiMemory(db);
  await db.prepare(`INSERT INTO ai_usage (user_id, route, style, ms, tokens_in, tokens_out, calls, tools, blocked) VALUES (?,?,?,?,?,?,?,?,?)`)
    .bind(u.user_id ?? null, u.route || 'big', u.style || 'default', u.ms ?? null, u.usage?.in ?? null, u.usage?.out ?? null, u.usage?.calls ?? null,
      JSON.stringify(u.tools || []), u.blocked || null).run();
}
export async function pruneUsage(db) {
  await ensureAiMemory(db);
  await db.prepare('DELETE FROM ai_usage WHERE at<unixepoch()-?').bind(KEEP_USAGE_DAYS * 86400).run();
  await ensureAiEval(db);
  await db.prepare(`DELETE FROM ai_eval WHERE kind='member' AND status='graded' AND created_at<unixepoch()-?`).bind(MEMBER_KEEP_DAYS * 86400).run();
}
export async function usageStats(db, days = 7) {
  await ensureAiMemory(db);
  const rows = (await db.prepare(`SELECT route, count(*) AS n, avg(ms) AS ms, avg(tokens_in) AS tokens_in, avg(tokens_out) AS tokens_out
      FROM ai_usage WHERE at>unixepoch()-? GROUP BY route ORDER BY n DESC`).bind(days * 86400).all()).results;
  const {m} = await db.prepare('SELECT count(*) AS m FROM ai_memory').first();
  return {days, routes: rows, memory: m};
}

/* may questions go to the small model? (from the self-test's location cases on it) */
let fast = null;
export async function fastAllowed(env, db) {
  if (env.AI_FAST === 'off') return false;
  if (env.AI_FAST === 'on' || !db) return true;
  if (fast && fast.db === db && Date.now() - fast.at < FAST_TTL) return fast.ok;
  let ok = true;
  try {
    const r = await db.prepare(`SELECT count(*) AS n, avg(score) AS s FROM ai_eval WHERE route IN ('fast','site') AND score IS NOT NULL
        AND status IN ('graded','approved','rejected') AND created_at>unixepoch()-1209600`).first();
    ok = !(r && r.n >= 10 && r.s < 0.7);
  } catch { ok = true; }   // no self-test yet
  fast = {db, at: Date.now(), ok};
  return ok;
}
export function forgetFastCache() { fast = null; }

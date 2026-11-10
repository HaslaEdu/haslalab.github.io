// An answer that tries to instruct the grader is not an answer: it is an attempt on the grading, and the account that
// sends one is suspended (the owner's rule, 2026-11-04). The grader already treats answer text as data, never instructions,
// and points need a quote the student actually wrote, so an attempt cannot raise a score; this takes the account out.
//
// Only unambiguous signals count. A physics answer writes «<<» for «much less than» and brackets for references, so a
// bare «<<» or «[1]» is never a signal; what is matched is our own prompt machinery (the fence names and section headers
// the prompts use) and plain instructions to the grader in English or Korean. Each match is kept with its passage, so an
// administrator can see why and lift the suspension (DELETE or lifted_at).
//
// A second tier (REVIEW) catches what is likely but not certain: nothing happens to the account and the answer is
// graded as usual (the grader never follows answer text), and the passage is kept in answer_flags for an
// administrator to look at and clear.
// The rules themselves: guard-rules.js (a public stub here; the private set is copied over it at deploy).
import { RULES, REVIEW, normalize } from './guard-rules.js';

export const SUSPENSION_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS account_suspensions (
    user_id INTEGER PRIMARY KEY,
    reason TEXT NOT NULL,
    source TEXT NOT NULL,
    evidence TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    lifted_at INTEGER
  )`,
  `CREATE TABLE IF NOT EXISTS answer_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    source TEXT NOT NULL,
    evidence TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    cleared_at INTEGER
  )`,
  `CREATE INDEX IF NOT EXISTS answer_flags_open ON answer_flags(cleared_at, created_at)`,
];
const ready = new WeakMap();
export function ensureSuspensionSchema(db, scope = db) {
  if (!ready.has(scope)) ready.set(scope, (async () => { for (const sql of SUSPENSION_SCHEMA) await db.prepare(sql).run(); })().catch(error => { ready.delete(scope); throw error; }));
  return ready.get(scope);
}


const signalsOf = (s, rules) => {
  const out = [];
  for (const [rule, re] of rules) {
    const m = re.exec(s);
    if (m && !out.some(x => x.passage === m[0])) {
      const at = m.index;
      out.push({ rule, passage: s.slice(Math.max(0, at - 40), at + m[0].length + 40).replace(/\s+/g, ' ').trim().slice(0, 240) });
    }
  }
  return out;
};
/** the injection signals in student-controlled text: [{rule, passage}], empty when there are none */
export function injectionSignals(text) {
  return screenAnswer(text).suspend;
}
/** both tiers at once: {suspend, review}; review is only looked at when nothing calls for a suspension */
export function screenAnswer(text) {
  const s = normalize(text);
  if (!s.trim()) return { suspend: [], review: [] };
  const suspend = signalsOf(s, RULES);
  return { suspend, review: suspend.length ? [] : signalsOf(s, REVIEW) };
}

/** keeps a likely attempt for an administrator to review; the account and the grading go on as usual */
export async function flagForReview(env, userId, source, signals, scope = env.DB) {
  if (!userId || !signals?.length) return false;
  await ensureSuspensionSchema(env.DB, scope);
  await env.DB.prepare('INSERT INTO answer_flags(user_id,source,evidence,created_at) VALUES(?,?,?,?)')
    .bind(userId, String(source).slice(0, 80), JSON.stringify(signals.slice(0, 5)), Math.floor(Date.now() / 1000)).run();
  console.warn('answer_flagged_for_review', userId, source, signals.map(x => x.rule).join(','));
  return true;
}
/** an administrator looked at the flag */
export async function clearFlag(env, id, scope = env.DB) {
  await ensureSuspensionSchema(env.DB, scope);
  const res = await env.DB.prepare('UPDATE answer_flags SET cleared_at=? WHERE id=? AND cleared_at IS NULL').bind(Math.floor(Date.now() / 1000), id).run();
  return !!res?.meta?.changes;
}

/** suspends the account for an injection attempt: users.deleted = 2 (every route already treats a non-zero «deleted» as
    no account, so sessions, rankings and rewards drop it with no extra query), the evidence row, and every session
    ended. Returns true when it was newly suspended. An administrator's account is never suspended by this (logged). */
export const SUSPENDED = 2;
export async function suspendForInjection(env, userId, source, signals, scope = env.DB) {
  if (!userId || !signals?.length) return false;
  await ensureSuspensionSchema(env.DB, scope);
  const u = await env.DB.prepare('SELECT role,deleted FROM users WHERE id=?').bind(userId).first();
  if (!u || u.deleted) return false;
  if (u.role === 'admin') { console.error('injection_signal_admin', source, signals.map(x => x.rule).join(',')); return false; }
  const now = Math.floor(Date.now() / 1000);
  const res = await env.DB.batch([
    env.DB.prepare(`UPDATE users SET deleted=${SUSPENDED} WHERE id=? AND deleted=0 AND role<>'admin'`).bind(userId),
    env.DB.prepare(`INSERT INTO account_suspensions(user_id,reason,source,evidence,created_at) VALUES(?,?,?,?,?)
      ON CONFLICT(user_id) DO UPDATE SET reason=excluded.reason,source=excluded.source,evidence=excluded.evidence,created_at=excluded.created_at,lifted_at=NULL`)
      .bind(userId, 'prompt_injection', String(source).slice(0, 80), JSON.stringify(signals.slice(0, 5)), now),
    env.DB.prepare('DELETE FROM sessions WHERE user_id=?').bind(userId),
  ]);
  console.error('account_suspended_prompt_injection', userId, source, signals.map(x => x.rule).join(','));
  return !!res[0]?.meta?.changes;
}
/** lifts a suspension: the account comes back as it was */
export async function liftSuspension(env, userId, scope = env.DB) {
  await ensureSuspensionSchema(env.DB, scope);
  const now = Math.floor(Date.now() / 1000);
  const res = await env.DB.batch([
    env.DB.prepare(`UPDATE users SET deleted=0 WHERE id=? AND deleted=${SUSPENDED}`).bind(userId),
    env.DB.prepare('UPDATE account_suspensions SET lifted_at=? WHERE user_id=? AND lifted_at IS NULL').bind(now, userId),
  ]);
  return !!res[0]?.meta?.changes;
}

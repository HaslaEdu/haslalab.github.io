/* Learn section progress on the member's account: every answered, self-marked or skipped practice problem,
   one rating per unit (Elo-style, the item's difficulty step against the learner), and the small state the
   practice page keeps (levels per unit, XP, study days, solved and missed problems) so it follows the member
   across devices. Guests keep the same data in their browser only; nothing here is required to practise. */
import { leagueFromAttempts } from './league.js';
export const PRACTICE_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS practice_attempts (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     user_id INTEGER NOT NULL,
     item_id TEXT NOT NULL,
     mode TEXT NOT NULL,
     unit TEXT NOT NULL,
     step REAL NOT NULL,
     result TEXT NOT NULL,
     created_at INTEGER NOT NULL)`,
  `CREATE INDEX IF NOT EXISTS practice_attempts_user ON practice_attempts(user_id, created_at DESC)`,
  `CREATE TABLE IF NOT EXISTS practice_skills (
     user_id INTEGER NOT NULL,
     unit TEXT NOT NULL,
     rating REAL NOT NULL,
     n INTEGER NOT NULL DEFAULT 0,
     right_n INTEGER NOT NULL DEFAULT 0,
     last_at INTEGER NOT NULL,
     PRIMARY KEY (user_id, unit))`,
  `CREATE TABLE IF NOT EXISTS practice_state (
     user_id INTEGER PRIMARY KEY,
     state TEXT NOT NULL,
     updated_at INTEGER NOT NULL)`
];
export const MODES = ['exam', 'bank', 'contest', 'track', 'diag'];
/* 'place': the placement test's verdict for a unit — the rating starts at that step if the unit has none yet */
export const RESULTS = ['right', 'wrong', 'solved', 'missed', 'skip', 'place'];
export const UNIT_RE = /^(?:[a-z]+\/[a-z_]+|[a-z]+\/\*|contest\/[a-z]+)$/;
const ITEM = /^[\w~.:-]{3,120}$/;
const MAX_BATCH = 50, MAX_STATE = 200000;

/* rating scale: a problem at step s sits at 1000 + 100·s; a learner starts at step 3 (1300) */
export const START = 1300;
export const stepRating = step => 1000 + 100 * step;
export const ratingStep = rating => Math.max(1, Math.min(10, Math.round((rating - 1000) / 100)));
export function updateRating(rating, step, result) {
  if (result === 'skip' || result === 'place') return rating;
  /* graded answers count fully; marking yourself counts half */
  return updateRatingBy(rating, step, result === 'right' || result === 'solved' ? 1 : 0, result === 'right' || result === 'wrong' ? 32 : 16);
}
/* the same move for a result between 0 and 1 (a photo-graded written answer: the fraction of its marks) */
export function updateRatingBy(rating, step, won, k = 32) {
  const expected = 1 / (1 + 10 ** ((stepRating(step) - rating) / 400));
  return Math.round((rating + k * (Math.max(0, Math.min(1, won)) - expected)) * 10) / 10;
}

const ready = new WeakSet();
export async function ensurePracticeSchema(env) {
  if (ready.has(env.DB)) return;
  /* one statement at a time: an index is prepared only after its table exists */
  for (const sql of PRACTICE_SCHEMA) await env.DB.prepare(sql).run();
  ready.add(env.DB);
}

/* the learner's answers to the first questions (learn-path.js): kept only in this shape, the newer one wins */
const PROFILE = {region: ['kr', 'in', 'us', 'global'], level: ['middle', 'high1', 'high2', 'uni', 'L1', 'L2', 'L3', 'L4'], goal: ['school', 'exam', 'olympiad', 'curious']};
function profileOf(p) {
  if (!p || typeof p !== 'object' || Object.entries(PROFILE).some(([k, ok]) => !ok.includes(p[k]))) return undefined;
  return {region: p.region, level: p.level, goal: p.goal, oly: Math.max(0, Math.min(2, p.oly | 0)), daily: [5, 10, 15, 20].includes(p.daily) ? p.daily : 10, at: Math.floor(Number(p.at) || 0)};
}
const newerProfile = (a, b) => (profileOf(b) && (Number(b.at) || 0) > (Number(a?.at) || 0)) || !profileOf(a) ? b : a;
/* the browser's state and the account's are merged so neither device loses progress */
export function mergeState(a, b) {
  const A = a && typeof a === 'object' ? a : {}, B = b && typeof b === 'object' ? b : {};
  const obj = (x, y, pick) => { const out = { ...(x || {}) }; for (const [k, v] of Object.entries(y || {})) out[k] = k in out ? pick(out[k], v) : v; return out; };
  return {
    profile: profileOf(newerProfile(A.profile, B.profile)),
    xp: Math.max(Number(A.xp) || 0, Number(B.xp) || 0),
    days: [...new Set([...(A.days || []), ...(B.days || [])])].filter(d => /^\d{4}-\d{2}-\d{2}$/.test(d)).sort().slice(-400),
    level: obj(A.level, B.level, (x, y) => Math.max(Number(x) || 0, Number(y) || 0)),
    solved: obj(A.solved, B.solved, x => x),
    wrong: obj(A.wrong, B.wrong, (x, y) => Math.max(Number(x) || 0, Number(y) || 0)),
    bank: { done: obj(A.bank?.done, B.bank?.done, (x, y) => Math.max(Number(x) || 0, Number(y) || 0)), stars: obj(A.bank?.stars, B.bank?.stars, (x, y) => y ?? x) },
    contest: { done: obj(A.contest?.done, B.contest?.done, (x, y) => Math.max(Number(x) || 0, Number(y) || 0)) }
  };
}

export function createPracticeRouter({ HttpError, needUser, limit, now, bad }) {
  async function skills(env, userId) {
    return (await env.DB.prepare('SELECT unit,rating,n,right_n,last_at FROM practice_skills WHERE user_id=?').bind(userId).all()).results;
  }
  return async function practiceRoute(p, m, body, me, env) {
    if (!p.startsWith('/api/practice/')) return undefined;
    needUser(me);
    await ensurePracticeSchema(env);
    if (p === '/api/practice/state' && m === 'GET') {
      const row = await env.DB.prepare('SELECT state FROM practice_state WHERE user_id=?').bind(me.id).first();
      let state = {}; try { state = row ? JSON.parse(row.state) : {}; } catch (e) { state = {}; }
      return { state, skills: await skills(env, me.id) };
    }
    if (p === '/api/practice/state' && m === 'POST') {
      const text = JSON.stringify(body?.state ?? null);
      if (!body || typeof body.state !== 'object' || body.state === null || text.length > MAX_STATE) bad('bad_state');
      await limit(env, 'practice-state:' + me.id, 120, 3600);
      const row = await env.DB.prepare('SELECT state FROM practice_state WHERE user_id=?').bind(me.id).first();
      let old = {}; try { old = row ? JSON.parse(row.state) : {}; } catch (e) { old = {}; }
      const merged = mergeState(old, body.state), out = JSON.stringify(merged);
      if (out.length > MAX_STATE) bad('bad_state');
      await env.DB.prepare('INSERT INTO practice_state(user_id,state,updated_at) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET state=excluded.state,updated_at=excluded.updated_at').bind(me.id, out, now()).run();
      return { state: merged };
    }
    if (p === '/api/practice/attempts' && m === 'POST') {
      const list = Array.isArray(body?.attempts) ? body.attempts : bad('bad_attempts');
      if (!list.length || list.length > MAX_BATCH) bad('bad_attempts');
      await limit(env, 'practice-attempts:' + me.id, 600, 3600);
      const t = now(), clean = list.map(a => {
        if (!a || !ITEM.test(a.item_id || '') || !MODES.includes(a.mode) || !RESULTS.includes(a.result) || !UNIT_RE.test(a.unit || '')) bad('bad_attempt');
        const step = Number(a.step); if (!(step >= 1 && step <= 10)) bad('bad_attempt');
        /* the browser's own clock, within the last two weeks and never ahead of the server */
        const at = Number.isFinite(a.at) ? Math.min(t, Math.max(t - 14 * 86400, Math.floor(a.at))) : t;
        return { item_id: a.item_id, mode: a.mode, unit: a.unit, step, result: a.result, at };
      });
      const current = new Map((await skills(env, me.id)).map(s => [s.unit, s]));
      const statements = [];
      for (const a of clean) {
        statements.push(env.DB.prepare('INSERT INTO practice_attempts(user_id,item_id,mode,unit,step,result,created_at) VALUES(?,?,?,?,?,?,?)').bind(me.id, a.item_id, a.mode, a.unit, a.step, a.result, a.at));
        if (a.result === 'skip') continue;
        if (a.result === 'place') {
          const had = current.get(a.unit);
          if (!had || !had.n) current.set(a.unit, { unit: a.unit, rating: stepRating(a.step), n: 0, right_n: 0, last_at: a.at, placed: true });
          continue;
        }
        const s = current.get(a.unit) || { unit: a.unit, rating: START, n: 0, right_n: 0, last_at: a.at };
        s.rating = updateRating(s.rating, a.step, a.result); s.n++; if (a.result === 'right' || a.result === 'solved') s.right_n++; s.last_at = Math.max(s.last_at, a.at);
        delete s.placed; current.set(a.unit, s);
      }
      for (const s of current.values()) if (clean.some(a => a.unit === s.unit && a.result !== 'skip' && (a.result !== 'place' || s.placed)))
        statements.push(env.DB.prepare('INSERT INTO practice_skills(user_id,unit,rating,n,right_n,last_at) VALUES(?,?,?,?,?,?) ON CONFLICT(user_id,unit) DO UPDATE SET rating=excluded.rating,n=excluded.n,right_n=excluded.right_n,last_at=excluded.last_at').bind(me.id, s.unit, s.rating, s.n, s.right_n, s.last_at));
      await env.DB.batch(statements);
      /* weekly league XP from these recorded attempts (league.js): right or solved ones only, capped per day */
      const league_xp = await leagueFromAttempts(env, me.id, clean, t);
      return { recorded: clean.length, league_xp, skills: [...current.values()].map(({ placed, ...s }) => s) };
    }
    throw new HttpError(404, 'not_found');
  };
}

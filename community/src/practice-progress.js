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
     updated_at INTEGER NOT NULL)`,
  /* the daily problems' difficulty, one per study level (L1-L4): worked out here from the recorded daily attempts,
     never taken from the page */
  `CREATE TABLE IF NOT EXISTS practice_daily (
     user_id INTEGER NOT NULL,
     level TEXT NOT NULL,
     rating REAL NOT NULL,
     n INTEGER NOT NULL DEFAULT 0,
     dir INTEGER NOT NULL DEFAULT 0,
     updated_at INTEGER NOT NULL,
     PRIMARY KEY (user_id, level))`
];
/* columns added to practice_attempts after it first shipped: hints seen on the problem, and where it was answered ('daily') */
const ATTEMPT_COLUMNS = [['hints', 'INTEGER NOT NULL DEFAULT 0'], ['ctx', 'TEXT']];
export const MODES = ['exam', 'bank', 'contest', 'track', 'diag'];
/* 'place': the placement test's verdict for a unit — the rating starts at that step if the unit has none yet;
   'hint': a hint was shown (recorded the moment it is shown, so the league knows of it whatever the answer says later);
   'giveup': "I can't solve this" on a daily problem — a miss that also lowers the daily difficulty */
export const RESULTS = ['right', 'wrong', 'solved', 'missed', 'skip', 'place', 'hint', 'giveup'];
export const CONTEXTS = ['daily'];
export const STUDY_LEVELS = ['L1', 'L2', 'L3', 'L4'];
export const MAX_HINTS = 5;
export const UNIT_RE = /^(?:[a-z]+\/[a-z_]+|[a-z]+\/\*|contest\/[a-z]+)$/;
const ITEM = /^[\w~.:-]{3,120}$/;
const MAX_BATCH = 50, MAX_STATE = 200000, RECENT_MAX = 60, RECENT_DAYS = 60;

/* rating scale: a problem at step s sits at 1000 + 100·s; a learner starts at step 3 (1300) */
export const START = 1300;
export const stepRating = step => 1000 + 100 * step;
export const ratingStep = rating => Math.max(1, Math.min(10, Math.round((rating - 1000) / 100)));
export function updateRating(rating, step, result) {
  if (result === 'skip' || result === 'place' || result === 'hint') return rating;
  /* graded answers count fully; marking yourself counts half */
  return updateRatingBy(rating, step, result === 'right' || result === 'solved' ? 1 : 0, result === 'right' || result === 'wrong' ? 32 : 16);
}
/* the same move for a result between 0 and 1 (a photo-graded written answer: the fraction of its marks) */
export function updateRatingBy(rating, step, won, k = 32) {
  const expected = 1 / (1 + 10 ** ((stepRating(step) - rating) / 400));
  return Math.round((rating + k * (Math.max(0, Math.min(1, won)) - expected)) * 10) / 10;
}

/* ── the daily problems' difficulty (practice-tools.js has the same numbers for the page; the tests check both).
   One rating per study level, on the same scale as the problems (step s = 1000 + 100 s). A new learner starts in the
   middle of the level's steps ("medium"). Elo against the problem's step: K = 48 for the first 10 rated answers, 20
   after; right or solved goes up, wrong, missed or "I can't solve this" goes down (the last at least K/2, so the next
   problems are easier); hints shrink a rise by a third each (three or more: no change) and never turn it into a fall.
   Kept inside the level's steps widened by one. A problem moves the rating once a day, and at most 60 a day. ── */
export const LEVEL_STEPS = Object.freeze({ L1: [2, 7], L2: [5, 7], L3: [6, 9], L4: [8, 9] });
export const DAILY_K_FIRST = 48, DAILY_K = 20, DAILY_FIRST_N = 10, DAILY_RATED_PER_DAY = 60;
const levelKey = level => (LEVEL_STEPS[level] ? level : 'L1');
export const dailyBounds = level => { const [lo, hi] = LEVEL_STEPS[levelKey(level)]; return [stepRating(Math.max(1, lo - 1)), stepRating(Math.min(10, hi + 1))]; };
export const dailyStart = level => { const [lo, hi] = LEVEL_STEPS[levelKey(level)]; return stepRating((lo + hi) / 2); };
export const dailyK = n => (n < DAILY_FIRST_N ? DAILY_K_FIRST : DAILY_K);
export const DAILY_RESULTS = ['right', 'solved', 'wrong', 'missed', 'giveup'];
export function dailyUpdate(rating, n, step, result, hints = 0, level = 'L1') {
  if (!DAILY_RESULTS.includes(result)) return rating;
  const won = result === 'right' || result === 'solved' ? 1 : 0, h = Math.max(0, Math.min(MAX_HINTS, Math.floor(Number(hints) || 0)));
  const k = dailyK(n), expected = 1 / (1 + 10 ** ((stepRating(Math.max(1, Math.min(10, Number(step) || 3))) - rating) / 400));
  let delta = k * (won - expected);
  if (won) delta *= Math.max(0, 1 - h / 3);
  if (result === 'giveup') delta = Math.min(delta, -k / 2);
  const [lo, hi] = dailyBounds(level);
  return Math.round(Math.max(lo, Math.min(hi, rating + delta)) * 10) / 10;
}

const ready = new WeakSet();
export async function ensurePracticeSchema(env) {
  if (ready.has(env.DB)) return;
  /* one statement at a time: an index is prepared only after its table exists */
  for (const sql of PRACTICE_SCHEMA) await env.DB.prepare(sql).run();
  const have = new Set(((await env.DB.prepare('PRAGMA table_info(practice_attempts)').all()).results || []).map(c => c.name));
  for (const [name, type] of ATTEMPT_COLUMNS) if (!have.has(name)) {
    try { await env.DB.prepare(`ALTER TABLE practice_attempts ADD COLUMN ${name} ${type}`).run(); }
    catch (e) { if (!/duplicate column/i.test(String(e?.message || e))) throw e; }
  }
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
  /* {L1: {rating, n, dir, updated_at}, …} for the levels this member has answered daily problems in */
  async function dailyOf(env, userId) {
    const rows = (await env.DB.prepare('SELECT level,rating,n,dir,updated_at FROM practice_daily WHERE user_id=?').bind(userId).all()).results || [];
    return Object.fromEntries(rows.map(r => [r.level, { rating: r.rating, n: r.n, dir: r.dir, updated_at: r.updated_at }]));
  }
  return async function practiceRoute(p, m, body, me, env) {
    if (!p.startsWith('/api/practice/')) return undefined;
    needUser(me);
    await ensurePracticeSchema(env);
    if (p === '/api/practice/state' && m === 'GET') {
      const row = await env.DB.prepare('SELECT state FROM practice_state WHERE user_id=?').bind(me.id).first();
      let state = {}; try { state = row ? JSON.parse(row.state) : {}; } catch (e) { state = {}; }
      return { state, skills: await skills(env, me.id), daily: await dailyOf(env, me.id) };
    }
    /* the latest answers, newest first: what the Olympiad home's weekly set reads for recent accuracy and recent misses
       (weekly-set.js). Read-only, the last 60 answers of the last 60 days, skips and placements left out */
    if (p === '/api/practice/recent' && m === 'GET') {
      /* a hint shown is not an answer; "I can't solve this" reads as a miss */
      const rows = (await env.DB.prepare("SELECT item_id,mode,unit,step,CASE result WHEN 'giveup' THEN 'missed' ELSE result END AS result,created_at AS at FROM practice_attempts WHERE user_id=? AND created_at>=? AND result NOT IN ('skip','place','hint') ORDER BY created_at DESC, id DESC LIMIT ?")
        .bind(me.id, now() - RECENT_DAYS * 86400, RECENT_MAX).all()).results;
      return { attempts: rows };
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
        /* optional: hints seen (0-5), and a daily problem's context and study level */
        if (a.hints != null && !(Number.isInteger(a.hints) && a.hints >= 0 && a.hints <= MAX_HINTS)) bad('bad_attempt');
        if (a.ctx != null && !CONTEXTS.includes(a.ctx)) bad('bad_attempt');
        if (a.level != null && !STUDY_LEVELS.includes(a.level)) bad('bad_attempt');
        return { item_id: a.item_id, mode: a.mode, unit: a.unit, step, result: a.result, at, hints: a.hints || 0, ctx: a.ctx || null, level: a.ctx ? a.level || 'L1' : null };
      });
      const current = new Map((await skills(env, me.id)).map(s => [s.unit, s]));
      /* what the server already has for these problems over the last day: daily answers that moved the rating (a problem
         moves it once a day; at most DAILY_RATED_PER_DAY a day) */
      const dayAgo = t - 86400, DB = env.DB;
      const ratedToday = (await DB.prepare(`SELECT item_id FROM practice_attempts WHERE user_id=? AND ctx='daily' AND created_at>=? AND result IN (${DAILY_RESULTS.map(() => '?').join(',')})`)
        .bind(me.id, dayAgo, ...DAILY_RESULTS).all()).results.map(r => r.item_id);
      const rated = new Set(ratedToday);
      let ratedN = ratedToday.length;
      const daily = await dailyOf(env, me.id), dailyMoved = new Set();
      const statements = [];
      for (const a of clean) {
        statements.push(DB.prepare('INSERT INTO practice_attempts(user_id,item_id,mode,unit,step,result,created_at,hints,ctx) VALUES(?,?,?,?,?,?,?,?,?)').bind(me.id, a.item_id, a.mode, a.unit, a.step, a.result, a.at, a.hints, a.ctx));
        if (a.ctx === 'daily' && DAILY_RESULTS.includes(a.result) && !rated.has(a.item_id) && ratedN < DAILY_RATED_PER_DAY) {
          rated.add(a.item_id); ratedN++;
          const d = daily[a.level] || { rating: dailyStart(a.level), n: 0, dir: 0, updated_at: a.at };
          const next = dailyUpdate(d.rating, d.n, a.step, a.result, a.hints, a.level);
          daily[a.level] = { rating: next, n: d.n + 1, dir: next > d.rating ? 1 : next < d.rating ? -1 : 0, updated_at: Math.max(d.updated_at || 0, a.at) };
          dailyMoved.add(a.level);
        }
        if (a.result === 'skip' || a.result === 'hint') continue;
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
      for (const level of dailyMoved) { const d = daily[level];
        statements.push(DB.prepare('INSERT INTO practice_daily(user_id,level,rating,n,dir,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(user_id,level) DO UPDATE SET rating=excluded.rating,n=excluded.n,dir=excluded.dir,updated_at=excluded.updated_at').bind(me.id, level, d.rating, d.n, d.dir, d.updated_at)); }
      await DB.batch(statements);
      /* hints count however the answer reports them: the hints recorded for the problem over the last day (this batch
         included) are the least that is taken off its league XP */
      const answered = [...new Set(clean.filter(a => a.result === 'right' || a.result === 'solved').map(a => a.item_id))];
      const seen = answered.length ? new Map((await DB.prepare(`SELECT item_id,COUNT(*) AS n FROM practice_attempts WHERE user_id=? AND result='hint' AND created_at>=? AND item_id IN (${answered.map(() => '?').join(',')}) GROUP BY item_id`)
        .bind(me.id, Math.min(dayAgo, ...clean.map(a => a.at)), ...answered).all()).results.map(r => [r.item_id, r.n])) : new Map();
      const scored = clean.map(a => ({ ...a, hints: Math.min(MAX_HINTS, Math.max(a.hints, seen.get(a.item_id) || 0)) }));
      /* weekly league XP from these recorded attempts (league.js): right or solved ones only, less for hints, capped per day */
      const league = await leagueFromAttempts(env, me.id, scored, t);
      return { recorded: clean.length, league_xp: league.xp, goal_bonus: league.bonus, ...(league.today ? { league_today: league.today } : {}), skills: [...current.values()].map(({ placed, ...s }) => s), daily };
    }
    throw new HttpError(404, 'not_found');
  };
}

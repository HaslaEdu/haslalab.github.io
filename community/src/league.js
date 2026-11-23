/* Weekly leagues. A week runs Monday 00:00 to Sunday 24:00 Korean time. A member joins the week's league with their
   first league XP of the week and is put in a group of up to 30 members of the same tier, in join order.

   League XP comes only from what the server itself recorded: a practice attempt marked right or solved
   (practice-progress.js) and a written answer the server graded (practice-grade.js). The page never sends a number of
   XP. The rule is the page's own: 10 + 2 x step (competition items 20 + 5 x step), and a graded answer gets that times
   1 for a pass, 0.5 for partial credit and 0.15 for a retry. Against abuse: one problem counts once a day (a better
   grading of it adds only the difference), and at most 200 problems count per member per day.

   When a week is over, the Worker's minute cron (index.js scheduled) settles it a few groups at a time: ranks 1-7 move
   up a tier, the last 5 move down (never below Bronze); in Master ranks 1-3 are reborn: rebirths + 1, back to Bronze.
   Every step is idempotent (results have a key per member and week, and a member's tier moves only once per week);
   league_weeks marks a week as done. The all-time ranking orders members by rebirths, then tier, then total league XP. */

export const LEAGUE_TIERS = Object.freeze(['bronze', 'silver', 'gold', 'platinum', 'emerald', 'sapphire', 'ruby', 'amethyst', 'diamond', 'master']);
export const MASTER = LEAGUE_TIERS.length - 1;
export const GROUP_SIZE = 30, PROMOTE = 7, DEMOTE = 5, REBIRTH = 3;
export const DAILY_COUNTED = 200, MAX_ITEM_XP = 80, GROUPS_PER_TICK = 6, HISTORY_WEEKS = 12, RANKING_PAGE = 100;
const KST = 9 * 3600, DAY = 86400;

export const LEAGUE_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS league_state (
     user_id INTEGER PRIMARY KEY,
     tier INTEGER NOT NULL DEFAULT 0,
     rebirths INTEGER NOT NULL DEFAULT 0,
     total_xp INTEGER NOT NULL DEFAULT 0,
     last_week TEXT,
     closed_week TEXT,
     updated_at INTEGER NOT NULL DEFAULT 0)`,
  `CREATE INDEX IF NOT EXISTS league_state_rank ON league_state(rebirths DESC, tier DESC, total_xp DESC)`,
  `CREATE TABLE IF NOT EXISTS league_xp (
     user_id INTEGER NOT NULL,
     week TEXT NOT NULL,
     xp INTEGER NOT NULL DEFAULT 0,
     tier INTEGER NOT NULL,
     group_no INTEGER NOT NULL,
     joined_at INTEGER NOT NULL,
     updated_at INTEGER NOT NULL,
     PRIMARY KEY (user_id, week))`,
  `CREATE INDEX IF NOT EXISTS league_xp_group ON league_xp(week, tier, group_no)`,
  `CREATE TABLE IF NOT EXISTS league_xp_items (
     user_id INTEGER NOT NULL,
     day TEXT NOT NULL,
     item_id TEXT NOT NULL,
     xp INTEGER NOT NULL,
     PRIMARY KEY (user_id, day, item_id))`,
  `CREATE TABLE IF NOT EXISTS league_results (
     user_id INTEGER NOT NULL,
     week TEXT NOT NULL,
     tier INTEGER NOT NULL,
     group_id TEXT NOT NULL,
     rank INTEGER NOT NULL,
     xp INTEGER NOT NULL,
     outcome TEXT NOT NULL,
     created_at INTEGER NOT NULL,
     PRIMARY KEY (user_id, week))`,
  `CREATE TABLE IF NOT EXISTS league_weeks (
     week TEXT PRIMARY KEY,
     closed_at INTEGER NOT NULL)`
];
const ready = new WeakSet();
export async function ensureLeagueSchema(env) {
  if (ready.has(env.DB)) return;
  for (const sql of LEAGUE_SCHEMA) await env.DB.prepare(sql).run();
  ready.add(env.DB);
}

/* ── the calendar, in Korean time: a week is named by its Monday (YYYY-MM-DD) ── */
const isoDay = d => new Date(d * DAY * 1000).toISOString().slice(0, 10);
const kstDay = t => Math.floor((t + KST) / DAY);
export const dayOf = t => isoDay(kstDay(t));
export function weekOf(t) { const d = kstDay(t); return isoDay(d - ((d + 3) % 7)); }   /* 1970-01-01 was a Thursday */
export const weekStarts = week => Date.parse(week + 'T00:00:00Z') / 1000 - KST;
export const weekEnds = week => weekStarts(week) + 7 * DAY;
export const nextWeek = week => isoDay(Date.parse(week + 'T00:00:00Z') / 1000 / DAY + 7);
export const daysLeft = t => Math.max(1, Math.ceil((weekEnds(weekOf(t)) - t) / DAY));

/* ── XP ── */
const stepOf = s => Math.max(1, Math.min(10, Math.round(Number(s) || 3)));
export const baseXp = (kind, step) => kind === 'contest' ? 20 + 5 * stepOf(step) : 10 + 2 * stepOf(step);
export const BAND_MULT = Object.freeze({ pass: 1, partial: 0.5, retry: 0.15 });
/* a recorded attempt: a right answer earns league XP, a problem the member marked solved half of it */
/* a self-marked "I solved it" (contest problems checked against the PDF) earns half: nothing checks it */
export const attemptXp = a => !a ? 0 : a.result === 'right' ? baseXp(a.mode, a.step) : a.result === 'solved' ? Math.round(baseXp(a.mode, a.step) / 2) : 0;
/* a graded written answer (practice_graded): base XP by step times the band */
export const gradedXp = (source, step, band) => source === 'archive' || !(band in BAND_MULT) ? 0 : Math.max(1, Math.round(baseXp(source, step) * BAND_MULT[band]));

/* the group a new member of the week joins: the last group of that tier while it has room, else a new one */
async function groupFor(DB, week, tier) {
  const last = await DB.prepare('SELECT group_no,COUNT(*) AS n FROM league_xp WHERE week=? AND tier=? GROUP BY group_no ORDER BY group_no DESC LIMIT 1').bind(week, tier).first();
  return !last ? 1 : last.n < GROUP_SIZE ? last.group_no : last.group_no + 1;
}
async function joinWeek(DB, userId, week, t) {
  const row = await DB.prepare('SELECT tier,group_no FROM league_xp WHERE user_id=? AND week=?').bind(userId, week).first();
  if (row) return row;
  let st = await DB.prepare('SELECT tier FROM league_state WHERE user_id=?').bind(userId).first();
  if (!st) { await DB.prepare('INSERT OR IGNORE INTO league_state(user_id,tier,rebirths,total_xp,updated_at) VALUES(?,0,0,0,?)').bind(userId, t).run(); st = { tier: 0 }; }
  const tier = Math.max(0, Math.min(MASTER, st.tier | 0)), group_no = await groupFor(DB, week, tier);
  await DB.prepare('INSERT OR IGNORE INTO league_xp(user_id,week,xp,tier,group_no,joined_at,updated_at) VALUES(?,?,0,?,?,?,?)').bind(userId, week, tier, group_no, t, t).run();
  return { tier, group_no };
}

/* events: [{item_id, xp}] worked out on the server from rows it has just recorded. Returns the XP added. */
export async function awardLeagueXp(env, userId, events, t) {
  const list = (events || []).filter(e => e && typeof e.item_id === 'string' && e.item_id && e.xp > 0);
  if (!list.length || !Number.isInteger(userId)) return 0;
  await ensureLeagueSchema(env);
  const DB = env.DB, day = dayOf(t), week = weekOf(t);
  const had = new Map((await DB.prepare('SELECT item_id,xp FROM league_xp_items WHERE user_id=? AND day=?').bind(userId, day).all()).results.map(r => [r.item_id, r.xp]));
  let gain = 0;
  const writes = [];
  for (const e of list) {
    const key = e.item_id.slice(0, 120), xp = Math.min(MAX_ITEM_XP, Math.floor(e.xp));
    if (had.has(key)) {
      const old = had.get(key);
      if (xp <= old) continue;                       /* the same problem again today: nothing more, unless graded better */
      gain += xp - old;
    } else {
      if (had.size >= DAILY_COUNTED) continue;      /* the day's 200 problems are counted */
      gain += xp;
    }
    had.set(key, xp);
    writes.push(DB.prepare('INSERT INTO league_xp_items(user_id,day,item_id,xp) VALUES(?,?,?,?) ON CONFLICT(user_id,day,item_id) DO UPDATE SET xp=MAX(xp,excluded.xp)').bind(userId, day, key, xp));
  }
  if (!gain) return 0;
  await joinWeek(DB, userId, week, t);
  writes.push(DB.prepare('UPDATE league_xp SET xp=xp+?,updated_at=? WHERE user_id=? AND week=?').bind(gain, t, userId, week),
    DB.prepare('UPDATE league_state SET total_xp=total_xp+?,last_week=?,updated_at=? WHERE user_id=?').bind(gain, week, t, userId));
  await DB.batch(writes);
  return gain;
}
/* the two places that record activity call these; a league failure never fails the practice request */
export const leagueFromAttempts = (env, userId, attempts, t) =>
  awardLeagueXp(env, userId, attempts.map(a => ({ item_id: a.item_id, xp: attemptXp(a) })), t).catch(e => { console.error('league', String(e?.message || e).slice(0, 200)); return 0; });
export const leagueFromGrading = (env, userId, item, band, t) =>
  awardLeagueXp(env, userId, [{ item_id: item.id, xp: gradedXp(item.source, item.step, band) }], t).catch(e => { console.error('league', String(e?.message || e).slice(0, 200)); return 0; });

/* ── the week's end: what each rank in a group does. xps are the group's XP, best first ── */
export function groupOutcomes(tier, xps) {
  const n = xps.filter(x => x > 0).length;
  return xps.map((xp, i) => {
    const rank = i + 1;
    if (!(xp > 0)) return { rank, outcome: 'stay', tier, reborn: false };
    if (tier >= MASTER) {
      if (rank <= REBIRTH) return { rank, outcome: 'reborn', tier: 0, reborn: true };
      if (rank > Math.max(REBIRTH, n - DEMOTE)) return { rank, outcome: 'down', tier: MASTER - 1, reborn: false };
      return { rank, outcome: 'stay', tier, reborn: false };
    }
    if (rank <= PROMOTE) return { rank, outcome: 'up', tier: tier + 1, reborn: false };
    if (tier > 0 && rank > Math.max(PROMOTE, n - DEMOTE)) return { rank, outcome: 'down', tier: tier - 1, reborn: false };
    return { rank, outcome: 'stay', tier, reborn: false };
  });
}
const ORDER = 'ORDER BY x.xp DESC, x.updated_at ASC, x.user_id ASC';
const groupId = (week, tier, no) => `${week}/${LEAGUE_TIERS[tier]}/${no}`;

async function settleGroup(DB, week, tier, group_no, t) {
  const members = (await DB.prepare(`SELECT x.user_id,x.xp FROM league_xp x WHERE x.week=? AND x.tier=? AND x.group_no=? ${ORDER}`).bind(week, tier, group_no).all()).results;
  const outcomes = groupOutcomes(tier, members.map(m => m.xp)), gid = groupId(week, tier, group_no), statements = [];
  members.forEach((m, i) => {
    const o = outcomes[i];
    statements.push(DB.prepare('INSERT OR IGNORE INTO league_results(user_id,week,tier,group_id,rank,xp,outcome,created_at) VALUES(?,?,?,?,?,?,?,?)').bind(m.user_id, week, tier, gid, o.rank, m.xp, o.outcome, t),
      /* a member's tier moves once per week, however often this runs */
      DB.prepare(`INSERT INTO league_state(user_id,tier,rebirths,total_xp,closed_week,updated_at) VALUES(?,?,?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET tier=excluded.tier,rebirths=league_state.rebirths+excluded.rebirths,closed_week=excluded.closed_week,updated_at=excluded.updated_at
        WHERE league_state.closed_week IS NULL OR league_state.closed_week<excluded.closed_week`).bind(m.user_id, o.tier, o.reborn ? 1 : 0, m.xp, week, t));
  });
  if (statements.length) await DB.batch(statements);
  /* a member who already played in the new week before this ran joined at the old tier: move them to the new one */
  const next = nextWeek(week);
  for (const [i, m] of members.entries()) {
    if (outcomes[i].tier === tier) continue;
    const row = await DB.prepare('SELECT tier FROM league_xp WHERE user_id=? AND week=?').bind(m.user_id, next).first();
    if (!row || row.tier === outcomes[i].tier) continue;
    const no = await groupFor(DB, next, outcomes[i].tier);
    await DB.prepare('UPDATE league_xp SET tier=?,group_no=? WHERE user_id=? AND week=?').bind(outcomes[i].tier, no, m.user_id, next).run();
  }
}

/* the minute cron's step: settles a few groups of the oldest unfinished week, then marks the week done */
const closedUpTo = new WeakMap();   /* per database: the current week once nothing older is left open */
export async function closeLeagueWeeks(env, { now: t, groups = GROUPS_PER_TICK } = {}) {
  const current = weekOf(t);
  if (closedUpTo.get(env.DB) === current) return { week: null };
  await ensureLeagueSchema(env);
  const DB = env.DB;
  const open = await DB.prepare('SELECT x.week FROM league_xp x WHERE x.week<? AND NOT EXISTS (SELECT 1 FROM league_weeks w WHERE w.week=x.week) ORDER BY x.week LIMIT 1').bind(current).first();
  if (!open) { closedUpTo.set(env.DB, current); return { week: null }; }
  const week = open.week;
  const pending = (await DB.prepare(`SELECT DISTINCT x.tier,x.group_no FROM league_xp x WHERE x.week=? AND NOT EXISTS
      (SELECT 1 FROM league_results r WHERE r.user_id=x.user_id AND r.week=x.week) ORDER BY x.tier,x.group_no LIMIT ?`).bind(week, groups).all()).results;
  for (const g of pending) await settleGroup(DB, week, g.tier, g.group_no, t);
  const left = await DB.prepare('SELECT 1 AS n FROM league_xp x WHERE x.week=? AND NOT EXISTS (SELECT 1 FROM league_results r WHERE r.user_id=x.user_id AND r.week=x.week) LIMIT 1').bind(week).first();
  if (left) return { week, settled: pending.length, closed: false };
  await DB.batch([DB.prepare('INSERT OR IGNORE INTO league_weeks(week,closed_at) VALUES(?,?)').bind(week, t),
    /* the per-day item counts are needed only for the day they count */
    DB.prepare('DELETE FROM league_xp_items WHERE day<?').bind(week)]);
  return { week, settled: pending.length, closed: true };
}

/* ── reading ── */
const flagOf = c => typeof c === 'string' && /^[A-Z]{2}$/.test(c) ? c : null;
async function hasLearnerTable(DB) {
  return !!await DB.prepare("SELECT 1 AS n FROM sqlite_master WHERE type='table' AND name='learner_profile'").first().catch(() => null);
}
export async function leagueMe(env, userId, t) {
  await ensureLeagueSchema(env);
  const DB = env.DB, week = weekOf(t);
  const st = await DB.prepare('SELECT tier,rebirths,total_xp FROM league_state WHERE user_id=?').bind(userId).first();
  const row = await DB.prepare('SELECT tier,group_no,xp FROM league_xp WHERE user_id=? AND week=?').bind(userId, week).first();
  const tier = row ? row.tier : st?.tier ?? 0, out = {
    week, ends_at: weekEnds(week), days_left: daysLeft(t), tier, tier_key: LEAGUE_TIERS[tier], rebirths: st?.rebirths ?? 0, total_xp: st?.total_xp ?? 0,
    joined: !!row, xp: row?.xp ?? 0, rank: null, group_id: null, standings: [],
    rules: { size: GROUP_SIZE, promote: PROMOTE, demote: DEMOTE, rebirth: REBIRTH, daily_counted: DAILY_COUNTED },
    zones: tier >= MASTER ? { up: 0, reborn: REBIRTH, down: DEMOTE } : { up: PROMOTE, reborn: 0, down: tier > 0 ? DEMOTE : 0 }
  };
  if (!row) return out;
  const country = await hasLearnerTable(DB);
  const members = (await DB.prepare(`SELECT x.user_id,x.xp,u.nickname,COALESCE(s.rebirths,0) AS rebirths${country ? ',lp.country' : ''} FROM league_xp x
      JOIN users u ON u.id=x.user_id LEFT JOIN league_state s ON s.user_id=x.user_id${country ? ' LEFT JOIN learner_profile lp ON lp.user_id=x.user_id' : ''}
      WHERE x.week=? AND x.tier=? AND x.group_no=? ${ORDER}`).bind(week, row.tier, row.group_no).all()).results;
  const outcomes = groupOutcomes(row.tier, members.map(m => m.xp));
  out.group_id = groupId(week, row.tier, row.group_no);
  out.standings = members.map((m, i) => ({ rank: i + 1, nickname: m.nickname, xp: m.xp, rebirths: m.rebirths, country: flagOf(m.country), me: m.user_id === userId, zone: outcomes[i].outcome }));
  out.rank = out.standings.find(s => s.me)?.rank ?? null;
  return out;
}
export async function leagueRanking(env, page, userId) {
  await ensureLeagueSchema(env);
  const DB = env.DB, country = await hasLearnerTable(DB), off = (page - 1) * RANKING_PAGE;
  const from = `FROM league_state s JOIN users u ON u.id=s.user_id AND u.deleted=0 WHERE s.total_xp>0`;
  const rows = (await DB.prepare(`SELECT s.user_id,s.rebirths,s.tier,s.total_xp,u.nickname${country ? ',lp.country' : ''} FROM league_state s JOIN users u ON u.id=s.user_id AND u.deleted=0
      ${country ? 'LEFT JOIN learner_profile lp ON lp.user_id=s.user_id' : ''} WHERE s.total_xp>0
      ORDER BY s.rebirths DESC, s.tier DESC, s.total_xp DESC, s.user_id ASC LIMIT ? OFFSET ?`).bind(RANKING_PAGE, off).all()).results;
  const total = (await DB.prepare(`SELECT COUNT(*) AS n ${from}`).first())?.n ?? 0;
  let mine = null;
  if (userId) {
    const s = await DB.prepare('SELECT rebirths,tier,total_xp FROM league_state WHERE user_id=? AND total_xp>0').bind(userId).first();
    if (s) mine = 1 + ((await DB.prepare(`SELECT COUNT(*) AS n ${from} AND (s.rebirths>? OR (s.rebirths=? AND (s.tier>? OR (s.tier=? AND (s.total_xp>? OR (s.total_xp=? AND s.user_id<?))))))`)
      .bind(s.rebirths, s.rebirths, s.tier, s.tier, s.total_xp, s.total_xp, userId).first())?.n ?? 0);
  }
  return { page, per_page: RANKING_PAGE, total, mine, rows: rows.map((r, i) => ({ rank: off + i + 1, nickname: r.nickname, rebirths: r.rebirths, tier: r.tier, tier_key: LEAGUE_TIERS[r.tier], total_xp: r.total_xp, country: flagOf(r.country), me: r.user_id === userId })) };
}
export async function leagueHistory(env, userId) {
  await ensureLeagueSchema(env);
  return { weeks: (await env.DB.prepare('SELECT week,tier,group_id,rank,xp,outcome FROM league_results WHERE user_id=? ORDER BY week DESC LIMIT ?').bind(userId, HISTORY_WEEKS).all()).results
    .map(r => ({ ...r, tier_key: LEAGUE_TIERS[r.tier] })) };
}
/* account deletion: the member's league rows go with the account */
export const leagueDeletion = (env, userId) => ['league_state', 'league_xp', 'league_xp_items', 'league_results']
  .map(table => env.DB.prepare(`DELETE FROM ${table} WHERE user_id=?`).bind(userId));

export function createLeagueRouter({ HttpError, needUser, now, bad }) {
  return async function leagueRoute(p, m, body, me, req, env, url) {
    if (!p.startsWith('/api/league/')) return undefined;
    if (m !== 'GET') throw new HttpError(405, 'method_not_allowed');
    if (p === '/api/league/me') return leagueMe(env, needUser(me).id, now());
    if (p === '/api/league/history') return leagueHistory(env, needUser(me).id);
    if (p === '/api/league/ranking') {
      const raw = (url || (req?.url ? new URL(req.url) : null))?.searchParams.get('page') || '1';
      const page = /^\d{1,4}$/.test(raw) && +raw >= 1 && +raw <= 1000 ? +raw : bad('bad_page');
      return leagueRanking(env, page, me?.id ?? null);
    }
    throw new HttpError(404, 'not_found');
  };
}

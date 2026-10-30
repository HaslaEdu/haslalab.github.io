// Public SELECTs shared by the primary backend and the global read lane.
// Callers choose the D1 session/consistency policy and authenticate any private overlay.
// Profiles, individual answers, votes, account state and financial data stay outside this module.
import { canonicalProblemPeriod, isMonthPeriod, isProblemPeriod, isoMonth } from './problem-period.js';
import { getMonthlyAnswerSheet } from '../../monthly-problems.mjs';
import { visibleMonthlySql } from './monthly-answers.js';
import { monthlyPublicPresentation } from './monthly-presentation.js';
export const PUBLIC_BOARDS = Object.freeze(['free', 'qna', 'sim', 'study']);
export const PUBLIC_TAGS = Object.freeze(['gen', 'q', 'info', 'review', 'bug', 'notice']);
export const PUBLIC_PAGE = 20, PUBLIC_BEST = 3;
export const TIER_AT = Object.freeze([1, 30, 60, 90, 120, 150, 200, 300, 400, 500, 650, 800, 950, 1100, 1250, 1400, 1600, 1750, 1900, 2000, 2100, 2200, 2300, 2400, 2500, 2600, 2700, 2800, 2850, 2900, 3000]);
const PROBLEM_RATING = [0, 1, 2, 3, 4, 5, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 35, 38, 41, 44, 47, 50, 53, 56, 59, 62, 65, 68];
const pickLang = language => language === 'en' ? 'en' : 'ko';
const currentTime = () => Math.floor(Date.now() / 1000);
export class PublicDataError extends Error {
  constructor(code) { super(code); this.status = 400; this.code = code; }
}
export const publicDataPath = path => /^\/api\/(?:boards|posts|monthly|weekly|rank)$/.test(path);
const ACTIVE_PERIOD_SQL = `SELECT p.week FROM problems p WHERE p.opens_at<=? AND p.closes_at>? AND ${visibleMonthlySql('p')}
  ORDER BY CASE WHEN length(p.week)=7 THEN 0 ELSE 1 END,p.opens_at DESC,p.closes_at DESC,p.week DESC LIMIT 1`;
export function arenaPeriod(url) {
  const requested = url.searchParams.get('month') || url.searchParams.get('week') || '';
  if (requested && !isProblemPeriod(requested)) throw new PublicDataError('bad_week');
  return canonicalProblemPeriod(requested);
}
export async function currentPeriod(db, time = currentTime()) {
  const active = await db.prepare(ACTIVE_PERIOD_SQL).bind(time, time).all();
  return active.results[0]?.week || isoMonth(time);
}

export function publicIsoWeek(time) {
  const d = new Date((time + 9 * 3600) * 1000), day = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - day + 3);
  const year = d.getUTCFullYear(), first = new Date(Date.UTC(year, 0, 4)), firstDay = (first.getUTCDay() + 6) % 7;
  first.setUTCDate(first.getUTCDate() - firstDay + 3);
  return `${year}-W${String(1 + Math.round((d - first) / 604800000)).padStart(2, '0')}`;
}
export const tierOf = rating => { let tier = 0; TIER_AT.forEach((minimum, index) => { if (rating >= minimum) tier = index + 1; }); return tier; };
export function rateUser(levels) {
  const hardest = levels.slice().sort((a, b) => b - a).slice(0, 100);
  return Math.round(hardest.reduce((sum, level) => sum + (PROBLEM_RATING[level] || 0), 0) + 175 * (1 - Math.pow(0.995, levels.length)));
}

export async function readPublicBoards(db, url, time = currentTime()) {
  const result = await db.prepare('SELECT board, COUNT(*) n, SUM(created_at > ?) today FROM posts WHERE lang=? GROUP BY board')
    .bind(time - 86400, pickLang(url.searchParams.get('lang'))).all();
  return { boards: result.results };
}

export async function readPublicPosts(db, url, time = currentTime()) {
  const sp = url.searchParams, board = sp.get('board') || '', tag = sp.get('tag') || '';
  const query = (sp.get('q') || '').trim().slice(0, 60), field = sp.get('field') || 'all';
  const sort = sp.get('sort') || 'new', best = sp.get('best') === '1';
  const page = Math.max(1, Math.min(500, parseInt(sp.get('page')) || 1));
  if (board && !PUBLIC_BOARDS.includes(board)) throw new PublicDataError('bad_board');
  const lang = pickLang(sp.get('lang')), where = ["p.tag<>'notice'", 'p.lang=?'], args = [lang];
  if (board) { where.push('p.board=?'); args.push(board); }
  if (tag && PUBLIC_TAGS.includes(tag)) { where.push('p.tag=?'); args.push(tag); }
  if (best) where.push(`(p.n_likes-p.n_dislikes)>=${PUBLIC_BEST}`);
  if (query) {
    const like = '%' + query.replace(/[\\%_]/g, '\\$&') + '%';
    if (field === 'title') { where.push("p.title LIKE ? ESCAPE '\\'"); args.push(like); }
    else if (field === 'author') { where.push("u.nickname LIKE ? ESCAPE '\\'"); args.push(like); }
    else { where.push("(p.title LIKE ? ESCAPE '\\' OR p.body LIKE ? ESCAPE '\\')"); args.push(like, like); }
  }
  const filter = 'WHERE ' + where.join(' AND ');
  const order = sort === 'top' ? '(p.n_likes-p.n_dislikes) DESC, p.id DESC'
    : sort === 'cmt' ? 'p.n_comments DESC, p.id DESC'
    : sort === 'hot' ? `((p.n_likes-p.n_dislikes)*2+p.n_comments+p.views*0.05+1)*1.0/((${time}-p.created_at)/3600.0+2) DESC, p.id DESC`
    : 'p.id DESC';
  const columns = 'p.id,p.board,p.tag,p.title,substr(p.body,1,160) AS snip,p.created_at,p.updated_at,p.views,p.n_comments,p.n_likes,p.n_dislikes,u.nickname,u.avatar AS av,u.deleted AS gone';
  const statements = [
    db.prepare(`SELECT COUNT(*) n FROM posts p JOIN users u ON u.id=p.user_id ${filter}`).bind(...args),
    db.prepare(`SELECT ${columns} FROM posts p JOIN users u ON u.id=p.user_id ${filter} ORDER BY ${order} LIMIT ? OFFSET ?`).bind(...args, PUBLIC_PAGE, (page - 1) * PUBLIC_PAGE),
  ];
  if (page === 1 && !query) statements.push(db.prepare(`SELECT ${columns} FROM posts p JOIN users u ON u.id=p.user_id
    WHERE p.tag='notice' AND p.lang=? ${board ? "AND (p.board=? OR p.board='free')" : ''} ORDER BY p.id DESC LIMIT 5`).bind(lang, ...(board ? [board] : [])));
  const [count, rows, notices] = await db.batch(statements);
  return { posts: rows.results, notices: notices?.results || [], total: count.results[0].n, page, per: PUBLIC_PAGE };
}

function rankingStatement(db, weekExpression = null, args = []) {
  return db.prepare(`SELECT x.user_id, x.problem_id, MAX(x.score) s, MIN(x.created_at) at, p.points, p.level, u.nickname, u.avatar AS av
    FROM submissions x JOIN problems p ON p.id=x.problem_id JOIN users u ON u.id=x.user_id
    WHERE x.status='graded' AND u.deleted=0 AND ${visibleMonthlySql('p')} ${weekExpression ? `AND x.in_week=1 AND p.week=${weekExpression}` : ''}
    GROUP BY x.user_id, x.problem_id`).bind(...args);
}
export function projectRankingRows(rows, weekFilter) {
  const byUser = new Map();
  for (const row of rows) {
    let user = byUser.get(row.user_id);
    if (!user) byUser.set(row.user_id, user = { nickname: row.nickname, av: row.av, total: 0, solved: 0, tried: 0, last: 0, levels: [] });
    user.total += row.s; user.tried++; user.last = Math.max(user.last, row.at);
    if (row.s >= row.points * 0.8) { user.solved++; user.levels.push(row.level); }
  }
  const ranked = [...byUser.values()].map(user => {
    const rating = rateUser(user.levels), { levels, ...rest } = user;
    return { ...rest, rating, lv: tierOf(rating) };
  });
  ranked.sort(weekFilter ? (a, b) => b.total - a.total || a.last - b.last
    : (a, b) => b.rating - a.rating || b.solved - a.solved || a.last - b.last);
  return ranked.slice(0, 200);
}
export async function readPublicRanking(db, weekFilter = null) {
  return projectRankingRows((await rankingStatement(db, weekFilter ? '?' : null, weekFilter ? [weekFilter] : []).all()).results, weekFilter);
}

function problemSummary(row, lang, time) {
  row = monthlyPublicPresentation(row);
  const result = { id: row.id, week: row.week, period: row.week, month: isMonthPeriod(row.week) ? row.week : null,
    no: row.no, kind: row.kind, subject: row.subject, level: row.level, points: row.points,
    title: lang === 'en' ? row.title_en : row.title_ko, unit: row.unit, source: row.source, opens_at: row.opens_at, closes_at: row.closes_at,
    open: time < row.closes_at, closed: time >= row.closes_at };
  const answerSheet = getMonthlyAnswerSheet(row);
  if (answerSheet) result.answerSheet = answerSheet;
  return result;
}
export async function readPublicWeekly(db, url, time = currentTime()) {
  const lang = pickLang(url.searchParams.get('lang')), week = arenaPeriod(url);
  const where = (week ? 'p.week=? AND p.opens_at<=?' : `p.week=(${ACTIVE_PERIOD_SQL}) AND p.opens_at<=?`) + ` AND ${visibleMonthlySql('p')}`;
  const args = week ? [week, time] : [time, time, time];
  const weekExpression = week ? '?' : `COALESCE((${ACTIVE_PERIOD_SQL}),?)`;
  const rankingArgs = week ? [week] : [time, time, isoMonth(time)];
  // Explicit columns prevent fetching answer keys, rubrics, worked solutions or private submissions.
  // All four public projections share one D1 round trip and one database snapshot.
  const [rows, weeks, stats, ranked] = await db.batch([
    db.prepare(`SELECT p.id,p.week,p.no,p.kind,p.subject,p.level,p.points,p.title_ko,p.title_en,p.unit,p.source,p.opens_at,p.closes_at FROM problems p WHERE ${where} ORDER BY p.no`).bind(...args),
    db.prepare(`SELECT p.week, MIN(p.opens_at) o, MAX(p.closes_at) c, COUNT(*) n FROM problems p WHERE p.opens_at<=? AND ${visibleMonthlySql('p')} GROUP BY p.week ORDER BY o DESC LIMIT 60`).bind(time),
    db.prepare(`SELECT s.problem_id, COUNT(DISTINCT s.user_id) users, COUNT(DISTINCT CASE WHEN s.score>=p.points THEN s.user_id END) solved
      FROM submissions s JOIN problems p ON p.id=s.problem_id WHERE s.problem_id IN (SELECT p.id FROM problems p WHERE ${where}) GROUP BY s.problem_id`).bind(...args),
    rankingStatement(db, weekExpression, rankingArgs),
  ]);
  const counts = new Map(stats.results.map(row => [row.problem_id, row]));
  const problems = rows.results.map(row => ({ ...problemSummary(row, lang, time), users: counts.get(row.id)?.users || 0, solvers: counts.get(row.id)?.solved || 0 }));
  const period = week || rows.results[0]?.week || isoMonth(time);
  return { week: period, period, month: isMonthPeriod(period) ? period : null, problems, weeks: weeks.results, months: weeks.results,
    top: projectRankingRows(ranked.results, true).slice(0, 8), now: time, user: null, api_version: 5 };
}
export const readPublicMonthly = readPublicWeekly;

export async function readPublicData(path, url, db, time = currentTime()) {
  if (path === '/api/boards') return readPublicBoards(db, url, time);
  if (path === '/api/posts') return readPublicPosts(db, url, time);
  if (path === '/api/monthly' || path === '/api/weekly') return readPublicWeekly(db, url, time);
  if (path === '/api/rank') {
    const scopeArg = url.searchParams.get('scope'), scope = ['month', 'week'].includes(scopeArg) ? scopeArg : 'all';
    const requested = arenaPeriod(url);
    let week = scope === 'all' ? null : requested, rows;
    if (scope !== 'all' && !week) {
      const [active, ranked] = await db.batch([
        db.prepare(ACTIVE_PERIOD_SQL).bind(time, time),
        rankingStatement(db, `COALESCE((${ACTIVE_PERIOD_SQL}),?)`, [time, time, isoMonth(time)]),
      ]);
      week = active.results[0]?.week || isoMonth(time);
      rows = projectRankingRows(ranked.results, true);
    } else rows = await readPublicRanking(db, week);
    return { scope, week, period: week, month: isMonthPeriod(week) ? week : null,
      rows: rows.slice(0, 100).map((row, index) => ({ ...row, rank: index + 1 })), mine: null, tierAt: TIER_AT, user: null, api_version: 5 };
  }
  return undefined;
}

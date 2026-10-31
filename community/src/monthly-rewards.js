import { isMonthPeriod } from './problem-period.js';
import { ensureMonthlyAnswerSchema, visibleMonthlySql } from './monthly-answers.js';
import { rateUser, tierOf } from './public-data.js';

export const MONTHLY_TOKEN_REWARDS = Object.freeze([
  Object.freeze({rank:1,tokens:9}), Object.freeze({rank:2,tokens:6}), Object.freeze({rank:3,tokens:3}),
]);
const FIRST_REWARDED_PERIOD = '2026-11';
const eligible = period => isMonthPeriod(period) && period >= FIRST_REWARDED_PERIOD;
const ready = new WeakMap();
const now = () => Math.floor(Date.now()/1000);
const missingTable = error => /no such table/i.test(String(error?.message || error));

export function ensureMonthlyRewardSchema(db,key = db) {
  let promise = ready.get(key);
  if (!promise) {
    promise = ensureMonthlyAnswerSchema(db,key).then(() => db.batch([
      db.prepare(`CREATE TABLE IF NOT EXISTS monthly_result_publications (
        period TEXT PRIMARY KEY, announcement_at INTEGER NOT NULL, published_at INTEGER,
        policy_version TEXT NOT NULL
      )`),
      db.prepare(`CREATE TABLE IF NOT EXISTS monthly_result_rows (
        period TEXT NOT NULL, rank INTEGER NOT NULL, user_id INTEGER NOT NULL,
        nickname TEXT NOT NULL, av TEXT, total REAL NOT NULL, solved INTEGER NOT NULL,
        tried INTEGER NOT NULL, last INTEGER NOT NULL, levels TEXT NOT NULL,
        token_reward INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(period,rank), UNIQUE(period,user_id)
      )`),
    ])).then(() => true);
    ready.set(key,promise);
    promise.catch(() => { if (ready.get(key) === promise) ready.delete(key); });
  }
  return promise;
}

// An accepted attempt is ranked only for its original submission window. A later
// practice attempt cannot enter the final result even if its client flag is wrong.
const onTime = 's.in_week=1 AND s.created_at>=p.opens_at AND s.created_at<p.closes_at';
const pendingSql = `SELECT COUNT(*) pending FROM submissions s JOIN problems p ON p.id=s.problem_id
  JOIN users u ON u.id=s.user_id WHERE p.week=? AND ${visibleMonthlySql('p')} AND u.deleted=0
  AND ${onTime} AND s.status IN ('pending','error')`;

// SQL computes the same per-problem MAX and earliest-attempt tie break as the live
// monthly ranking. User ID is a final stable tie break, never a public field.
const finalRowsSql = `WITH best AS (
  SELECT s.user_id,s.problem_id,MAX(s.score) best,MIN(s.created_at) at,p.points,p.level,u.nickname,u.avatar av
  FROM submissions s JOIN problems p ON p.id=s.problem_id JOIN users u ON u.id=s.user_id
  WHERE p.week=? AND ${visibleMonthlySql('p')} AND u.deleted=0 AND ${onTime}
    AND s.status='graded' AND s.score IS NOT NULL GROUP BY s.user_id,s.problem_id
), totals AS (
  SELECT user_id,nickname,av,SUM(best) total,SUM(best>=points*0.8) solved,COUNT(*) tried,MAX(at) last,
    json_group_array(level) FILTER(WHERE best>=points*0.8) levels FROM best GROUP BY user_id
), ranked AS (
  SELECT *,ROW_NUMBER() OVER(ORDER BY total DESC,last ASC,user_id ASC) rank FROM totals
)
INSERT INTO monthly_result_rows(period,rank,user_id,nickname,av,total,solved,tried,last,levels,token_reward)
SELECT ?,rank,user_id,nickname,av,total,solved,tried,last,levels,
  CASE rank WHEN 1 THEN 9 WHEN 2 THEN 6 WHEN 3 THEN 3 ELSE 0 END FROM ranked
WHERE EXISTS(SELECT 1 FROM monthly_result_publications WHERE period=? AND published_at IS NULL)
ON CONFLICT(period,rank) DO NOTHING`;

// This is the sole write entry point: call from the primary scheduled Worker,
// never a public GET or a read replica. D1 batch is one transaction, including
// result capture, ledger entries, balances and publication. Cron retries and
// concurrent invocations therefore cannot grant the same month's reward twice.
export async function settleMonthlyRewards(db,{timestamp = now(),key = db,period = null} = {}) {
  await ensureMonthlyRewardSchema(db,key);
  const filter = period ? ' AND p.week=?' : '';
  const periods = (await db.prepare(`SELECT p.week period,MAX(p.closes_at) announcement_at FROM problems p
    WHERE p.week>=? AND length(p.week)=7 AND ${visibleMonthlySql('p')}${filter}
    GROUP BY p.week HAVING MAX(p.closes_at)<=? ORDER BY p.week`)
    .bind(FIRST_REWARDED_PERIOD,...(period ? [period] : []),timestamp).all()).results.filter(row => eligible(row.period));
  const published = [], waiting = [];
  for (const row of periods) {
    const previous = await db.prepare('SELECT published_at FROM monthly_result_publications WHERE period=?').bind(row.period).first();
    if (previous?.published_at !== null && previous?.published_at !== undefined) continue;
    const note = 'monthly:'+row.period;
    const batch = await db.batch([
      db.prepare(`INSERT INTO monthly_result_publications(period,announcement_at,published_at,policy_version)
        SELECT ?,MAX(p.closes_at),NULL,'monthly-token-awards-v1' FROM problems p
        WHERE p.week=? AND ${visibleMonthlySql('p')} HAVING COUNT(*)>0 AND MAX(p.closes_at)<=? AND 0=(${pendingSql})
        ON CONFLICT(period) DO NOTHING`).bind(row.period,row.period,timestamp,row.period),
      db.prepare(finalRowsSql).bind(row.period,row.period,row.period),
      db.prepare(`INSERT INTO lab_ledger(user_id,delta,reason,note,created_at)
        SELECT r.user_id,r.token_reward,'monthly_reward',?,? FROM monthly_result_rows r
        JOIN monthly_result_publications p ON p.period=r.period WHERE r.period=? AND r.token_reward>0
        AND p.published_at IS NULL`).bind(note,timestamp,row.period),
      db.prepare(`UPDATE users SET exam_tokens=exam_tokens+(SELECT r.token_reward FROM monthly_result_rows r
        WHERE r.period=? AND r.user_id=users.id) WHERE id IN (SELECT r.user_id FROM monthly_result_rows r
        JOIN monthly_result_publications p ON p.period=r.period WHERE r.period=? AND r.token_reward>0 AND p.published_at IS NULL)`)
        .bind(row.period,row.period),
      db.prepare('UPDATE monthly_result_publications SET published_at=? WHERE period=? AND published_at IS NULL').bind(timestamp,row.period),
    ]);
    if (batch.at(-1).meta?.changes) published.push(row.period);
    else if (!(await db.prepare('SELECT published_at FROM monthly_result_publications WHERE period=?').bind(row.period).first())) waiting.push(row.period);
  }
  return {published,waiting};
}

// SELECT-only, including cold deployments where the primary cron has not yet
// created the additive tables. This is safe to use in the public read lane.
export async function monthlyRewardSummary(db,period,{timestamp = now(),announcementAt = undefined} = {}) {
  const base = {eligible:eligible(period),status:'not_eligible',announcement_at:null,published_at:null,
    rewards:MONTHLY_TOKEN_REWARDS,rows:null};
  if (!base.eligible) return base;
  const meta = announcementAt === undefined ? (await db.prepare(`SELECT MAX(p.closes_at) announcement_at FROM problems p WHERE p.week=? AND ${visibleMonthlySql('p')}`).bind(period).all()).results[0] : {announcement_at:announcementAt};
  base.announcement_at = meta?.announcement_at ?? null;
  base.status = base.announcement_at && timestamp < base.announcement_at ? 'scheduled' : 'awaiting_publication';
  let publication;
  try { publication = (await db.prepare('SELECT announcement_at,published_at FROM monthly_result_publications WHERE period=?').bind(period).all()).results[0]; }
  catch (error) { if (!missingTable(error)) throw error; return base; }
  if (publication?.published_at !== null && publication?.published_at !== undefined) {
    const result = await db.prepare(`SELECT r.rank,r.total,r.solved,r.tried,r.last,r.levels,r.token_reward,
      u.nickname,u.avatar av,u.deleted FROM monthly_result_rows r LEFT JOIN users u ON u.id=r.user_id
      WHERE r.period=? ORDER BY r.rank LIMIT 200`).bind(period).all();
    return {...base,status:'published',announcement_at:publication.announcement_at,published_at:publication.published_at,
      rows:result.results.map(({levels,deleted,nickname,...row}) => {
        const rating = rateUser(JSON.parse(levels));
        return {...row,nickname:deleted || !nickname ? '탈퇴한 사용자' : nickname,av:deleted ? null : row.av,
          rating,lv:tierOf(rating)};
      })};
  }
  if (base.announcement_at === null) return base;
  if (timestamp >= base.announcement_at && (await db.prepare(pendingSql).bind(period).all()).results[0]?.pending > 0) base.status = 'awaiting_grading';
  return base;
}

export async function readFinalMonthlyRanking(db,period,options) {
  const summary = await monthlyRewardSummary(db,period,options);
  return summary.status === 'published' ? summary.rows : null;
}

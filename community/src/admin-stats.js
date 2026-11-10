/* Site statistics for admins: how many people signed up, how many were graded, how much Hasla AI was asked.
   Counts only, never a name, username, e-mail or answer, so the page shows nothing a leaked screenshot could
   identify anyone by. The route sits behind the admin check in index.js; this module only reads.
   "People" leaves out admin accounts, so testing by the team does not inflate the numbers.
   Days are Korean days (UTC+9), the same calendar the monthly problems run on. */
const KST = "'+9 hours'";
const DAY = `date(%s,'unixepoch',${KST})`;
const day = col => DAY.replace("%s", col);
const NOT_ADMIN = "COALESCE((SELECT role FROM users z WHERE z.id=%s),'user')<>'admin'";
const people = col => NOT_ADMIN.replace("%s", col);

/* a table made lazily by another feature may not exist yet on a fresh database: that reads as no rows */
const rows = async (db, sql, ...args) => { try { return (await db.prepare(sql).bind(...args).all()).results || []; } catch (e) { if (/no such table/i.test(String(e?.message))) return []; throw e; } };
const one = async (db, sql, ...args) => (await rows(db, sql, ...args))[0] || {};

export async function adminStats(db, { days = 30, now = Math.floor(Date.now() / 1000) } = {}) {
  days = Math.max(7, Math.min(180, Math.floor(+days) || 30));
  const today = new Date((now + 9 * 3600) * 1000).toISOString().slice(0, 10);
  const since = now - days * 86400, d7 = now - 7 * 86400, d1 = now - 86400;
  const [users, methods, signupDays, lab, labPeople, labDays, labExams, monthly, monthlyDays, ai, aiDays, pay, suspended] = await Promise.all([
    one(db, `SELECT COUNT(*) created,
        SUM(deleted=0) active, SUM(deleted=1) deleted, SUM(deleted=2) suspended,
        SUM(deleted=0 AND role='admin') admins,
        SUM(deleted=0 AND role<>'admin') people,
        SUM(deleted=0 AND role<>'admin' AND username LIKE '~pending_%') pending_username,
        SUM(role<>'admin' AND ${day("created_at")}=?) new_today,
        SUM(role<>'admin' AND created_at>=?) new_7d,
        SUM(role<>'admin' AND created_at>=?) new_period
      FROM users`, today, d7, since),
    rows(db, `SELECT 'password' method, COUNT(*) n FROM users WHERE deleted=0 AND role<>'admin' AND pw IS NOT NULL
      UNION ALL SELECT i.provider, COUNT(DISTINCT i.user_id) FROM identities i JOIN users u ON u.id=i.user_id
        WHERE u.deleted=0 AND u.role<>'admin' GROUP BY i.provider`),
    rows(db, `SELECT ${day("created_at")} day, COUNT(*) n FROM users WHERE role<>'admin' AND created_at>=? GROUP BY day`, since),
    rows(db, `SELECT status, COUNT(*) n, SUM(${people("user_id")}) people FROM lab_sessions GROUP BY status`),
    one(db, `SELECT COUNT(DISTINCT user_id) graded_people, COUNT(*) graded,
        SUM(COALESCE(graded_at,created_at)>=?) graded_24h, SUM(COALESCE(graded_at,created_at)>=?) graded_7d
      FROM lab_sessions WHERE status='graded' AND ${people("user_id")}`, d1, d7),
    rows(db, `SELECT ${day("COALESCE(graded_at,created_at)")} day, COUNT(*) n FROM lab_sessions
      WHERE status='graded' AND ${people("user_id")} AND COALESCE(graded_at,created_at)>=? GROUP BY day`, since),
    rows(db, `SELECT exam_key, COUNT(*) n, COUNT(DISTINCT user_id) people FROM lab_sessions
      WHERE status='graded' AND ${people("user_id")} GROUP BY exam_key ORDER BY n DESC, exam_key LIMIT 12`),
    one(db, `SELECT COUNT(*) submitted, SUM(status='graded') graded, COUNT(DISTINCT CASE WHEN status='graded' THEN user_id END) graded_people,
        SUM(status IN ('pending','error','ai_suspected')) waiting
      FROM submissions WHERE ${people("user_id")}`),
    rows(db, `SELECT ${day("COALESCE(graded_at,created_at)")} day, COUNT(*) n FROM submissions
      WHERE status='graded' AND ${people("user_id")} AND COALESCE(graded_at,created_at)>=? GROUP BY day`, since),
    one(db, `SELECT COUNT(*) asked, SUM(user_id IS NULL) guests, SUM(user_id IS NOT NULL) members,
        COUNT(DISTINCT user_id) member_people, SUM(at>=?) asked_7d, SUM(blocked IS NOT NULL AND blocked<>'') blocked
      FROM ai_usage WHERE user_id IS NULL OR ${people("user_id")}`, d7),
    rows(db, `SELECT ${day("at")} day, COUNT(*) n FROM ai_usage WHERE at>=? AND (user_id IS NULL OR ${people("user_id")}) GROUP BY day`, since),
    rows(db, `SELECT status, currency, COUNT(*) n, SUM(amount) amount FROM pay_orders WHERE ${people("user_id")} GROUP BY status, currency`),
    one(db, `SELECT COUNT(*) n FROM account_suspensions WHERE lifted_at IS NULL`),
  ]);
  /* anyone graded at least once, in the exam mode or on a monthly problem */
  const anyGraded = await one(db, `SELECT COUNT(*) n FROM (
      SELECT user_id FROM lab_sessions WHERE status='graded' UNION SELECT user_id FROM submissions WHERE status='graded') g
    WHERE ${people("g.user_id")}`);
  const num = v => Number(v) || 0;
  const series = new Map();
  for (let i = days - 1; i >= 0; i--) { const d = new Date((now + 9 * 3600 - i * 86400) * 1000).toISOString().slice(0, 10); series.set(d, { day: d, signups: 0, lab: 0, monthly: 0, ai: 0 }); }
  for (const [list, key] of [[signupDays, "signups"], [labDays, "lab"], [monthlyDays, "monthly"], [aiDays, "ai"]])
    for (const r of list) if (series.has(r.day)) series.get(r.day)[key] = num(r.n);
  const statuses = Object.fromEntries(lab.map(r => [r.status, { all: num(r.n), people: num(r.people) }]));
  return {
    generated_at: now, today, days,
    users: { created: num(users.created), active: num(users.active), deleted: num(users.deleted), suspended: num(users.suspended),
      suspended_open: num(suspended.n), admins: num(users.admins), people: num(users.people), pending_username: num(users.pending_username),
      new_today: num(users.new_today), new_7d: num(users.new_7d), new_period: num(users.new_period),
      methods: Object.fromEntries(methods.filter(r => num(r.n)).map(r => [r.method, num(r.n)])) },
    graded: { people: num(anyGraded.n) },
    lab: { graded: num(labPeople.graded), graded_people: num(labPeople.graded_people), graded_24h: num(labPeople.graded_24h), graded_7d: num(labPeople.graded_7d),
      statuses, exams: labExams.map(r => ({ exam_key: r.exam_key, graded: num(r.n), people: num(r.people) })) },
    monthly: { submitted: num(monthly.submitted), graded: num(monthly.graded), graded_people: num(monthly.graded_people), waiting: num(monthly.waiting) },
    ai: { asked: num(ai.asked), guests: num(ai.guests), members: num(ai.members), member_people: num(ai.member_people), asked_7d: num(ai.asked_7d), blocked: num(ai.blocked) },
    pay: pay.map(r => ({ status: r.status, currency: r.currency, orders: num(r.n), amount: num(r.amount) })),
    series: [...series.values()],
  };
}

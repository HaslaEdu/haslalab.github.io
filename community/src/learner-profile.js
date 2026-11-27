/* The learner's country and daily goal: asked once at sign-up (or the first visit to Learn after it); the member can
   change them in Settings (index.html, #/community/account, "Learning") and the goal on the practice page. The page uses
   the goal as its daily target and the country for its default exams; the league ranking shows the country's flag.
   One small table, made at runtime one statement at a time; the users table is not altered. */

/* ISO 3166-1 alpha-2, every officially assigned code (the same list as learner-form.js in the site's root) */
export const COUNTRIES = Object.freeze(('AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ '
  + 'CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR '
  + 'GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP '
  + 'KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT '
  + 'MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW '
  + 'SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG '
  + 'UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW').split(' '));
const COUNTRY_SET = new Set(COUNTRIES);
/* any whole number of problems from 1 to 50; the page suggests 10 and offers 1, 5, 10, 20 and 30 as quick picks */
export const GOAL_MIN = 1, GOAL_MAX = 50, DEFAULT_GOAL = 10;
export const GOAL_PICKS = Object.freeze([1, 5, 10, 20, 30]);
export const isDailyGoal = g => Number.isInteger(g) && g >= GOAL_MIN && g <= GOAL_MAX;
export const LEARNER_SAVES_PER_DAY = 20;

export const LEARNER_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS learner_profile (
     user_id INTEGER PRIMARY KEY,
     country TEXT,
     daily_goal INTEGER,
     updated_at INTEGER)`
];
const ready = new WeakSet();
export async function ensureLearnerSchema(env) {
  if (ready.has(env.DB)) return;
  for (const sql of LEARNER_SCHEMA) await env.DB.prepare(sql).run();
  ready.add(env.DB);
}

export const isCountry = c => typeof c === 'string' && COUNTRY_SET.has(c);
/* the two fields as the page sends them; anything else is refused with the field's own error code */
export function cleanLearner(body, bad) {
  if (!body || typeof body !== 'object') bad('bad_learner');
  const country = typeof body.country === 'string' ? body.country.trim().toUpperCase() : '';
  if (!isCountry(country)) bad('bad_country');
  const goal = typeof body.daily_goal === 'number' || (typeof body.daily_goal === 'string' && /^\d{1,2}$/.test(body.daily_goal)) ? Number(body.daily_goal) : NaN;
  if (!isDailyGoal(goal)) bad('bad_daily_goal');
  return { country, daily_goal: goal };
}

export async function listLearnerCountries(env, {query = '', before = 0} = {}) {
  await ensureLearnerSchema(env);
  const needle = String(query).trim().slice(0,64).toLowerCase();
  const cursor = Number.isSafeInteger(before) && before > 0 ? before : 0;
  const matches = needle ? ' AND (instr(lower(u.username),?)>0 OR instr(lower(u.nickname),?)>0 OR CAST(u.id AS TEXT)=?)' : '';
  const rows = (await env.DB.prepare(`SELECT u.id,u.username,u.nickname,l.country
    FROM users u LEFT JOIN learner_profile l ON l.user_id=u.id
    WHERE u.deleted=0${cursor ? ' AND u.id<?' : ''}${matches}
    ORDER BY u.id DESC LIMIT 51`).bind(...(cursor ? [cursor] : []), ...(needle ? [needle,needle,needle] : [])).all()).results || [];
  const users = rows.slice(0,50).map(row => ({...row,country:isCountry(row.country) ? row.country : null}));
  return {users,next:rows.length>50 ? users.at(-1).id : null};
}

export async function readLearner(env, userId) {
  await ensureLearnerSchema(env);
  const row = await env.DB.prepare('SELECT country,daily_goal,updated_at FROM learner_profile WHERE user_id=?').bind(userId).first();
  return row ? { country: row.country, daily_goal: row.daily_goal, updated_at: row.updated_at } : { country: null, daily_goal: null, updated_at: null };
}

/* account deletion (index.js DELETE /api/me) adds this to its batch */
export const learnerDeletion = (env, userId) => env.DB.prepare('DELETE FROM learner_profile WHERE user_id=?').bind(userId);

export function createLearnerRouter({ HttpError, needUser, limit, now, bad }) {
  return async function learnerRoute(p, m, body, me, req, env) {
    if (p !== '/api/me/learner') return undefined;
    needUser(me);
    if (m === 'GET') return readLearner(env, me.id);
    if (m === 'PUT' || m === 'POST') {
      /* index.js parses POST and PATCH bodies only; a PUT is read here */
      let data = body;
      if (m === 'PUT' && (!data || !Object.keys(data).length) && req?.json) data = await req.json().catch(() => null);
      const clean = cleanLearner(data, bad);
      await limit(env, 'learner:' + me.id, LEARNER_SAVES_PER_DAY, 86400);
      await ensureLearnerSchema(env);
      const t = now();
      await env.DB.prepare('INSERT INTO learner_profile(user_id,country,daily_goal,updated_at) VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET country=excluded.country,daily_goal=excluded.daily_goal,updated_at=excluded.updated_at')
        .bind(me.id, clean.country, clean.daily_goal, t).run();
      return { ...clean, updated_at: t };
    }
    throw new HttpError(405, 'method_not_allowed');
  };
}

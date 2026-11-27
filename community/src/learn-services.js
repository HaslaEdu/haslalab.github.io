/* Learn section services on the member's account:
   - the AI tutor beside a practice problem (hint first, never the answer before the learner has tried), a few free
     questions a day per member and more with a plan;
   - the member's plan (GET /api/learn/plan): what the page shows — ads or not, tutor questions left today;
   - translation of problem text into the learner's language, cached for everyone, with LaTeX kept as it is.
   Plans live in `entitlements` (one row per grant: a payment, a school, an admin). Nothing here charges anyone; a
   payment provider's webhook or an admin adds the row. */
import { generate } from './ai-assistant.js';
import { legacyJoinGate } from './workshop-group-gate.js';

export const LEARN_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS entitlements (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     user_id INTEGER NOT NULL,
     kind TEXT NOT NULL,
     starts_at INTEGER NOT NULL,
     ends_at INTEGER,
     source TEXT NOT NULL,
     ref TEXT,
     created_at INTEGER NOT NULL)`,
  `CREATE INDEX IF NOT EXISTS entitlements_user ON entitlements(user_id, kind)`,
  `CREATE TABLE IF NOT EXISTS ai_usage_daily (
     user_id INTEGER NOT NULL,
     day TEXT NOT NULL,
     kind TEXT NOT NULL,
     n INTEGER NOT NULL DEFAULT 0,
     PRIMARY KEY (user_id, day, kind))`,
  `CREATE TABLE IF NOT EXISTS classes (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     teacher_id INTEGER NOT NULL,
     name TEXT NOT NULL,
     code TEXT NOT NULL UNIQUE,
     created_at INTEGER NOT NULL,
     closed_at INTEGER)`,
  `CREATE INDEX IF NOT EXISTS classes_teacher ON classes(teacher_id)`,
  `CREATE TABLE IF NOT EXISTS class_members (
     class_id INTEGER NOT NULL,
     user_id INTEGER NOT NULL,
     joined_at INTEGER NOT NULL,
     PRIMARY KEY (class_id, user_id))`,
  `CREATE INDEX IF NOT EXISTS class_members_user ON class_members(user_id)`,
  `CREATE TABLE IF NOT EXISTS class_assignments (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     class_id INTEGER NOT NULL,
     title TEXT NOT NULL,
     items TEXT NOT NULL,
     due_at INTEGER,
     created_at INTEGER NOT NULL)`,
  `CREATE INDEX IF NOT EXISTS class_assignments_class ON class_assignments(class_id)`,
  `CREATE TABLE IF NOT EXISTS content_translations (
     h TEXT NOT NULL,
     lang TEXT NOT NULL,
     text TEXT NOT NULL,
     created_at INTEGER NOT NULL,
     PRIMARY KEY (h, lang))`
];
/* the site's languages: Korean and English for now */
export const LANGS = ['ko', 'en'];
export const LANG_NAMES = {ko: 'Korean', en: 'English', es: 'Spanish', pt: 'Brazilian Portuguese', id: 'Indonesian', vi: 'Vietnamese',
  hi: 'Hindi', zh: 'Simplified Chinese', ja: 'Japanese'};
/* free tutor questions a day; a plan's ceiling only guards against a stolen session */
export const TUTOR_FREE = 5, TUTOR_PLUS = 100, TUTOR_SCHOOL = 20;
/* photo gradings of written answers a day (practice-grade.js): a few free, more with any plan */
export const GRADE_FREE = 10, GRADE_PLAN = 60;
const PLAN_KINDS = ['plus', 'teacher', 'school_seat'];
const MAX_TRANSLATE = 12, MAX_SOURCE = 6000;
/* new translations (model calls) a day: a member, a guest's address */
export const TRANSLATE_MEMBER = 1200, TRANSLATE_GUEST = 240;
/* problem variants for teachers (teach.html): a few runs a day free, more with a teacher or school plan; each run makes
   up to VARIANT_MAX problems */
export const VARIANT_FREE = 3, VARIANT_PLAN = 40, VARIANT_MAX = 5;
/* classes: free for every teacher up to FREE_CLASSES classes of FREE_SEATS students; a teacher or school plan lifts both */
export const FREE_CLASSES = 1, FREE_SEATS = 30, PLAN_CLASSES = 30, PLAN_SEATS = 200;
const ITEM_ID = /^[a-z0-9]+-[a-z0-9-]{1,40}$/, CODE_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
const newCode = () => [...crypto.getRandomValues(new Uint8Array(6))].map(b => CODE_CHARS[b % CODE_CHARS.length]).join('');

const ready = new WeakSet();
export async function ensureLearnSchema(env) {
  if (ready.has(env.DB)) return;
  /* one statement at a time: an index is prepared only after its table exists */
  for (const sql of LEARN_SCHEMA) await env.DB.prepare(sql).run();
  ready.add(env.DB);
}
/* the learner's day in UTC: one boundary for everyone, wherever they are */
export const utcDay = (sec = Date.now() / 1000) => new Date(sec * 1000).toISOString().slice(0, 10);

export async function planOf(env, userId, t) {
  const rows = (await env.DB.prepare(`SELECT kind FROM entitlements WHERE user_id=? AND starts_at<=? AND (ends_at IS NULL OR ends_at>?)`)
    .bind(userId, t, t).all()).results || [];
  const kinds = new Set(rows.map(r => r.kind).filter(k => PLAN_KINDS.includes(k)));
  const plan = kinds.has('plus') ? 'plus' : kinds.has('school_seat') ? 'school' : kinds.has('teacher') ? 'teacher' : 'free';
  return {plan, kinds: [...kinds], ads: plan === 'free', tutorLimit: plan === 'plus' ? TUTOR_PLUS : plan === 'free' ? TUTOR_FREE : TUTOR_SCHOOL};
}
async function usedToday(env, userId, kind, day) {
  const row = await env.DB.prepare('SELECT n FROM ai_usage_daily WHERE user_id=? AND day=? AND kind=?').bind(userId, day, kind).first();
  return row ? row.n : 0;
}
/* counts the question only if it is still under the day's limit, in one statement, so two tabs cannot both pass */
export async function takeOne(env, userId, kind, day, max) {
  const row = await env.DB.prepare(`INSERT INTO ai_usage_daily(user_id,day,kind,n) VALUES(?,?,?,1)
    ON CONFLICT(user_id,day,kind) DO UPDATE SET n=n+1 WHERE ai_usage_daily.n<? RETURNING n`).bind(userId, day, kind, max).first();
  return row ? row.n : null;
}
export async function giveBack(env, userId, kind, day) {
  await env.DB.prepare('UPDATE ai_usage_daily SET n=MAX(0,n-1) WHERE user_id=? AND day=? AND kind=?').bind(userId, day, kind).run();
}

const clip = (s, n) => String(s ?? '').slice(0, n);
export function tutorMessages({problem, choices, attempt, solved, hintsSeen, question, lang, history}) {
  const language = LANG_NAMES[lang] || 'English';
  const system = `You are HaslaLab's physics tutor beside one practice problem. Reply in ${language}, in at most 150 words, with math as $...$ (KaTeX).
Teach, do not just answer: find what the learner is missing, ask one guiding question or give one next step.
${solved ? 'The learner has already answered this problem, so you may walk through the full solution if they ask.' : 'The learner has NOT finished this problem: never state the final numerical answer or the correct choice, even if asked; give the next step instead.'}
Stay on this problem and on physics. If the problem statement itself looks wrong, say so plainly.`;
  const ctx = `Problem:\n${clip(problem, 4000)}${choices?.length ? '\nChoices:\n' + choices.map((c, i) => `(${String.fromCharCode(65 + i)}) ${clip(c, 300)}`).join('\n') : ''}`
    + `${attempt ? `\nLearner's attempt: ${clip(attempt, 300)}` : ''}\nHints already shown: ${Math.max(0, Math.min(5, hintsSeen | 0))}`;
  const past = (Array.isArray(history) ? history : []).slice(-6)
    .filter(m => (m?.role === 'user' || m?.role === 'assistant') && typeof m.content === 'string')
    .map(m => ({role: m.role, content: clip(m.content, 1500)}));
  return [{role: 'system', content: system}, {role: 'user', content: ctx}, {role: 'assistant', content: 'Understood. What would you like help with?'}, ...past,
    {role: 'user', content: clip(question, 1500)}];
}

export const TRANSLATE_SYSTEM = to => `Translate the user's physics text into ${LANG_NAMES[to]}. Output only the translation.
Keep every LaTeX span ($...$, $$...$$, \\(...\\), \\[...\\]) exactly as it is, character for character. Keep numbers, units, variable names, line breaks and blank lines.
Do not solve, explain, shorten or add anything.`;
async function hashOf(text) {
  const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(d)].slice(0, 16).map(b => b.toString(16).padStart(2, '0')).join('');
}
/* a translation must keep the math: the same $-spans in the same order, or it is not stored */
export function mathSpans(text) { return (String(text).match(/\$\$[\s\S]+?\$\$|\$[^$\n]+?\$/g) || []); }
export function keepsMath(src, out) {
  const a = mathSpans(src), b = mathSpans(out);
  return a.length === b.length && a.every((s, i) => s === b[i]);
}

/* A teacher's variant request: the model writes new problems from one source problem and states, for each, an
   arithmetic expression that computes the answer from the numbers in the problem (`calc`). The page evaluates `calc`
   with its own parser (math-input.js) and a second, independent solve (`check`) must agree before a variant is marked
   as checked. Nothing here is trusted as correct; the teacher sees which checks passed. */
export const VARIANT_MODES = ['numbers', 'context', 'new'], VARIANT_LEVELS = ['easier', 'same', 'harder'], VARIANT_FORMATS = ['free', 'mc'];
export function variantMessages({source, n, mode, level, format, lang}) {
  const language = LANG_NAMES[lang] || 'English';
  const how = {numbers: 'Keep the situation and the question; change only the given numbers (choose values that give a clean but not trivial answer).',
    context: 'Keep the physics and the solution method; change the situation, the objects and the numbers.',
    new: 'Test the same idea with a different kind of question (for example ask for a different quantity, or reverse the question).'}[mode];
  const lv = {easier: 'Make it a little easier than the source.', same: 'Keep the same difficulty.', harder: 'Make it a little harder: one more step, but the same topic.'}[level];
  const system = `You write physics problems for a teacher's test, in ${language}. Math in LaTeX as $...$; units upright with \\mathrm{}.
${how} ${lv}
Write ${n} problem(s). Each must be self-contained, solvable with the data given, and have one numerical answer (or one formula answer if the source asks for a formula).
Reply with JSON only, no prose and no code fence:
{"variants":[{"q":"problem text","answer":"the answer as a plain number or a formula in ASCII, e.g. 4.9 or sqrt(2*g*h)","unit":"SI unit of the answer, ASCII, or empty",
"calc":"an arithmetic expression with the problem's numbers that evaluates to the answer, ASCII: + - * / ^ sqrt sin cos tan exp ln pi (angles in radians), e.g. sqrt(2*9.8*1.5)",
"sol":"a short worked solution, 2-6 sentences, with LaTeX"${format === 'mc' ? `,
"choices":["4 or 5 choice texts, one of them the answer; build each wrong choice from a real mistake (sign, missing factor 2, wrong unit conversion, using the wrong formula)"],"correct":0,"why":["one short line per wrong choice: the mistake it comes from"]` : ''}}]}`;
  const src = `Source problem:\n${clip(source.q, 4000)}${source.choices?.length ? '\nChoices: ' + source.choices.map((c, i) => `(${i + 1}) ${clip(c, 300)}`).join(' ') : ''}`
    + `${source.answer ? '\nSource answer: ' + clip(source.answer, 300) : ''}${source.sol ? '\nSource solution: ' + clip(source.sol, 2000) : ''}`;
  return [{role: 'system', content: system}, {role: 'user', content: src}];
}
export function checkMessages(q, lang) {
  return [{role: 'system', content: `Solve the physics problem. Reply with JSON only: {"answer":"the final answer as a plain number (SI units) or an ASCII formula"}. ${lang === 'ko' ? 'The problem is in Korean.' : ''}`},
    {role: 'user', content: clip(q, 4000)}];
}
export function parseJson(text) {
  const s = String(text || '').replace(/^```(?:json)?\s*|\s*```$/g, '').trim();
  const a = s.indexOf('{'), b = s.lastIndexOf('}');
  if (a < 0 || b <= a) return null;
  try { return JSON.parse(s.slice(a, b + 1)); } catch { return null; }
}
const str = (v, n) => typeof v === 'string' ? v.slice(0, n) : '';
export function cleanVariant(v, format) {
  if (!v || typeof v !== 'object') return null;
  const out = {q: str(v.q, 4000).trim(), answer: str(v.answer, 200).trim(), unit: str(v.unit, 24).trim(), calc: str(v.calc, 400).trim(), sol: str(v.sol, 3000).trim()};
  if (!out.q || !out.answer) return null;
  if (format === 'mc') {
    const ch = Array.isArray(v.choices) ? v.choices.filter(c => typeof c === 'string' && c.trim()).slice(0, 5).map(c => c.slice(0, 400)) : [];
    const k = Number.isInteger(v.correct) && v.correct >= 0 && v.correct < ch.length ? v.correct : -1;
    if (ch.length < 3 || k < 0) return null;
    out.choices = ch; out.correct = k; out.why = Array.isArray(v.why) ? v.why.filter(w => typeof w === 'string').slice(0, 5).map(w => w.slice(0, 300)) : [];
  }
  return out;
}

export function createLearnRouter({HttpError, needUser, limit, now, bad, clientIp}) {
  return async function learnRoute(p, m, body, me, req, env) {
    if (!p.startsWith('/api/learn/')) return undefined;
    await ensureLearnSchema(env);
    const t = now();
    if (p === '/api/learn/plan' && m === 'GET') {
      if (!me) return {plan: 'guest', ads: true, tutorLimit: 0, tutorLeft: 0, gradeLeft: 0};
      const plan = await planOf(env, me.id, t);
      const vmax = plan.plan === 'free' ? VARIANT_FREE : VARIANT_PLAN;
      return {...plan, tutorLeft: Math.max(0, plan.tutorLimit - await usedToday(env, me.id, 'tutor', utcDay(t))),
        variantLeft: Math.max(0, vmax - await usedToday(env, me.id, 'variant', utcDay(t))),
        gradeLeft: Math.max(0, (plan.plan === 'free' ? GRADE_FREE : GRADE_PLAN) - await usedToday(env, me.id, 'grade', utcDay(t)))};
    }
    if (p === '/api/learn/tutor' && m === 'POST') {
      needUser(me);
      if (!env.AI) throw new HttpError(503, 'ai_unavailable');
      if (!body || typeof body.problem !== 'string' || !body.problem.trim() || typeof body.question !== 'string' || !body.question.trim()) bad('bad_tutor');
      await limit(env, 'tutor-flood:' + me.id, 10, 60);
      const plan = await planOf(env, me.id, t), day = utcDay(t);
      const n = await takeOne(env, me.id, 'tutor', day, plan.tutorLimit);
      if (n == null) throw new HttpError(429, 'tutor_limit');
      const lang = LANGS.includes(body.lang) ? body.lang : 'en';
      let answer = '';
      try {
        answer = await generate(env, 'CHAT', tutorMessages({...body, lang, choices: Array.isArray(body.choices) ? body.choices.slice(0, 6) : []}), 700);
      } catch (e) { await giveBack(env, me.id, 'tutor', day); throw new HttpError(503, 'ai_failed'); }
      if (!answer) { await giveBack(env, me.id, 'tutor', day); throw new HttpError(503, 'ai_failed'); }
      return {answer, tutorLeft: Math.max(0, plan.tutorLimit - n), plan: plan.plan};
    }
    if (p === '/api/learn/translate' && m === 'POST') {
      const to = LANGS.includes(body?.to) ? body.to : bad('bad_lang');
      const texts = Array.isArray(body?.texts) ? body.texts : bad('bad_texts');
      if (!texts.length || texts.length > MAX_TRANSLATE || texts.some(s => typeof s !== 'string' || s.length > MAX_SOURCE)) bad('bad_texts');
      const hashes = await Promise.all(texts.map(s => hashOf(to + '\n' + s)));
      const found = new Map();
      for (const h of [...new Set(hashes)]) {
        const row = await env.DB.prepare('SELECT text FROM content_translations WHERE h=? AND lang=?').bind(h, to).first();
        if (row) found.set(h, row.text);
      }
      const missing = texts.map((s, i) => ({s, h: hashes[i]})).filter(x => !found.has(x.h) && x.s.trim());
      if (missing.length) {
        if (!env.AI) throw new HttpError(503, 'ai_unavailable');
        /* cached text is free for everyone; each new translation (one model call) counts against the reader, so a
           request of 12 texts costs 12; past the day's limit the rest are shown in the original */
        for (const [k, x] of missing.entries()) {
          if (found.has(x.h)) continue;
          try { await limit(env, me ? 'tr:m:' + me.id : 'tr:g:' + clientIp(req), me ? TRANSLATE_MEMBER : TRANSLATE_GUEST, 86400); }
          catch (e) { if (k === 0 || e?.status !== 429) throw e; break; }
          let out = '';
          try { out = (await generate(env, 'CHAT', [{role: 'system', content: TRANSLATE_SYSTEM(to)}, {role: 'user', content: x.s}], 2000)).trim(); } catch (e) { out = ''; }
          if (!out || !keepsMath(x.s, out)) continue;   /* the original is shown instead */
          found.set(x.h, out);
          await env.DB.prepare('INSERT OR IGNORE INTO content_translations(h,lang,text,created_at) VALUES(?,?,?,?)').bind(x.h, to, out, t).run();
        }
      }
      return {to, texts: texts.map((s, i) => found.get(hashes[i]) ?? null)};
    }
    if (p === '/api/learn/variants' && m === 'POST') {
      needUser(me);
      if (!env.AI) throw new HttpError(503, 'ai_unavailable');
      const src = body?.source;
      if (!src || typeof src.q !== 'string' || !src.q.trim() || src.q.length > MAX_SOURCE) bad('bad_source');
      const n = Number.isInteger(body.n) && body.n >= 1 && body.n <= VARIANT_MAX ? body.n : bad('bad_n');
      const mode = VARIANT_MODES.includes(body.mode) ? body.mode : bad('bad_mode');
      const level = VARIANT_LEVELS.includes(body.level) ? body.level : 'same', format = VARIANT_FORMATS.includes(body.format) ? body.format : 'free';
      const lang = LANGS.includes(body.lang) ? body.lang : 'en';
      await limit(env, 'variant-flood:' + me.id, 4, 60);
      const plan = await planOf(env, me.id, t), day = utcDay(t), max = plan.plan === 'free' ? VARIANT_FREE : VARIANT_PLAN;
      const used = await takeOne(env, me.id, 'variant', day, max);
      if (used == null) throw new HttpError(429, 'variant_limit');
      const source = {q: src.q, answer: str(src.answer, 300), sol: str(src.sol, 2000),
        choices: Array.isArray(src.choices) ? src.choices.filter(c => typeof c === 'string').slice(0, 6) : []};
      let variants = [];
      try {
        const out = parseJson(await generate(env, 'SOLVER', variantMessages({source, n, mode, level, format, lang}), 12000, null, {reasoning: true}));
        variants = (Array.isArray(out?.variants) ? out.variants : []).map(v => cleanVariant(v, format)).filter(Boolean).slice(0, n);
      } catch (e) { variants = []; }
      if (!variants.length) { await giveBack(env, me.id, 'variant', day); throw new HttpError(503, 'ai_failed'); }
      /* a second solve that does not see the answer */
      for (const v of variants) {
        try { v.check = str(parseJson(await generate(env, 'SOLVER', checkMessages(v.q + (v.choices ? '\n' + v.choices.map((c, i) => `(${i + 1}) ${c}`).join(' ') : ''), lang), 8000, null, {reasoning: true}))?.answer, 200); }
        catch (e) { v.check = ''; }
      }
      return {variants, left: Math.max(0, max - used), plan: plan.plan};
    }
    if (p.startsWith('/api/learn/classes')) return classRoute(p, m, body, me, env, t);
    throw new HttpError(404, 'not_found');
  };
  async function classRoute(p, m, body, me, env, t) {
    needUser(me);
    const DB = env.DB, one = (sql, ...a) => DB.prepare(sql).bind(...a).first(), all = async (sql, ...a) => (await DB.prepare(sql).bind(...a).all()).results || [];
    if (p === '/api/learn/classes' && m === 'GET') {
      const teaching = await all(`SELECT c.id,c.name,c.code,c.created_at,(SELECT COUNT(*) FROM class_members x WHERE x.class_id=c.id) AS n
        FROM classes c WHERE c.teacher_id=? AND c.closed_at IS NULL ORDER BY c.id DESC`, me.id);
      const joined = await all(`SELECT c.id,c.name,u.nickname AS teacher FROM class_members x JOIN classes c ON c.id=x.class_id LEFT JOIN users u ON u.id=c.teacher_id
        WHERE x.user_id=? AND c.closed_at IS NULL ORDER BY x.joined_at DESC`, me.id);
      const ids = joined.map(c => c.id);
      const assignments = ids.length ? await all(`SELECT id,class_id,title,items,due_at,created_at FROM class_assignments WHERE class_id IN (${ids.map(() => '?').join(',')}) ORDER BY id DESC LIMIT 100`, ...ids) : [];
      const mine = new Map((await all(`SELECT item_id,MAX(CASE WHEN result IN ('right','solved') THEN 1 ELSE 0 END) AS ok FROM practice_attempts WHERE user_id=? AND result<>'skip' GROUP BY item_id`, me.id).catch(() => [])).map(r => [r.item_id, r.ok]));
      return {teaching, joined, assignments: assignments.map(a => { const items = JSON.parse(a.items); return {...a, items, done: items.filter(i => mine.get(i) === 1).length}; })};
    }
    if (p === '/api/learn/classes' && m === 'POST') {
      const name = typeof body?.name === 'string' && body.name.trim().length >= 1 && body.name.trim().length <= 60 ? body.name.trim() : bad('bad_name');
      await limit(env, 'class-new:' + me.id, 10, 86400);
      const plan = await planOf(env, me.id, t), max = plan.plan === 'free' ? FREE_CLASSES : PLAN_CLASSES;
      const have = await one('SELECT COUNT(*) AS n FROM classes WHERE teacher_id=? AND closed_at IS NULL', me.id);
      if (have.n >= max) throw new HttpError(403, 'class_limit');
      for (let k = 0; k < 5; k++) {
        const code = newCode();
        try {
          const r = await DB.prepare('INSERT INTO classes(teacher_id,name,code,created_at) VALUES(?,?,?,?)').bind(me.id, name, code, t).run();
          return {id: r.meta.last_row_id, name, code};
        } catch (e) { if (!/UNIQUE/i.test(String(e?.message))) throw e; }
      }
      throw new HttpError(503, 'try_again');
    }
    if (p === '/api/learn/classes/join' && m === 'POST') {
      const code = String(body?.code || '').trim().toUpperCase();
      if (!/^[A-Z0-9]{6}$/.test(code)) bad('bad_code');
      await limit(env, 'class-join:' + me.id, 20, 3600);
      const c = await one('SELECT id,teacher_id,name FROM classes WHERE code=? AND closed_at IS NULL', code);
      if (!c) throw new HttpError(404, 'class_not_found');
      if (c.teacher_id === me.id) bad('own_class');
      /* a removed member, a group that turned its class code off or asks for approval (workshop-group-gate.js) */
      const refused = await legacyJoinGate(env, c.id, me.id, t);
      if (refused) throw new HttpError(refused === 'class_not_found' ? 404 : 403, refused);
      const plan = await planOf(env, c.teacher_id, t), seats = plan.plan === 'free' ? FREE_SEATS : PLAN_SEATS;
      const n = await one('SELECT COUNT(*) AS n FROM class_members WHERE class_id=?', c.id);
      const already = await one('SELECT 1 AS y FROM class_members WHERE class_id=? AND user_id=?', c.id, me.id);
      if (!already && n.n >= seats) throw new HttpError(403, 'class_full');
      await DB.prepare('INSERT OR IGNORE INTO class_members(class_id,user_id,joined_at) VALUES(?,?,?)').bind(c.id, me.id, t).run();
      return {id: c.id, name: c.name};
    }
    const mm = /^\/api\/learn\/classes\/(\d+)(?:\/(leave|assignments|members\/(\d+)))?$/.exec(p);
    if (!mm) throw new HttpError(404, 'not_found');
    const c = await one('SELECT id,teacher_id,name,code FROM classes WHERE id=? AND closed_at IS NULL', +mm[1]);
    if (!c) throw new HttpError(404, 'class_not_found');
    const teacher = c.teacher_id === me.id;
    if (mm[2] === 'leave' && m === 'POST') { await DB.prepare('DELETE FROM class_members WHERE class_id=? AND user_id=?').bind(c.id, me.id).run(); return {ok: true}; }
    if (!teacher) throw new HttpError(403, 'not_teacher');
    if (!mm[2] && m === 'GET') {
      /* what the teacher sees: each student's units (rating, answers) and how far each assignment is done — only for
         students in this class, and only their Learn practice */
      const members = await all(`SELECT x.user_id AS id,u.nickname,x.joined_at FROM class_members x LEFT JOIN users u ON u.id=x.user_id WHERE x.class_id=? ORDER BY u.nickname`, c.id);
      const assignments = (await all('SELECT id,title,items,due_at,created_at FROM class_assignments WHERE class_id=? ORDER BY id DESC LIMIT 50', c.id)).map(a => ({...a, items: JSON.parse(a.items)}));
      const ids = members.map(x => x.id), q = ids.map(() => '?').join(',');
      const skills = ids.length ? await all(`SELECT user_id,unit,rating,n,right_n,last_at FROM practice_skills WHERE user_id IN (${q})`, ...ids).catch(() => []) : [];
      const wanted = [...new Set(assignments.flatMap(a => a.items))];
      const done = ids.length && wanted.length ? await all(`SELECT user_id,item_id FROM practice_attempts WHERE user_id IN (${q}) AND item_id IN (${wanted.map(() => '?').join(',')}) AND result IN ('right','solved') GROUP BY user_id,item_id`, ...ids, ...wanted).catch(() => []) : [];
      const doneBy = new Map();
      for (const r of done) (doneBy.get(r.user_id) || doneBy.set(r.user_id, new Set()).get(r.user_id)).add(r.item_id);
      return {id: c.id, name: c.name, code: c.code, members: members.map(x => {
        const ks = skills.filter(k => k.user_id === x.id), set = doneBy.get(x.id) || new Set();
        return {...x, units: ks.map(({user_id, ...k}) => k), answered: ks.reduce((a, k) => a + k.n, 0), lastAt: ks.reduce((a, k) => Math.max(a, k.last_at), 0),
          assignments: Object.fromEntries(assignments.map(a => [a.id, a.items.filter(i => set.has(i)).length]))};
      }), assignments};
    }
    if (!mm[2] && m === 'DELETE') { await DB.prepare('UPDATE classes SET closed_at=? WHERE id=?').bind(t, c.id).run(); return {ok: true}; }
    if (mm[2] === 'assignments' && m === 'POST') {
      const title = typeof body?.title === 'string' && body.title.trim() && body.title.trim().length <= 80 ? body.title.trim() : bad('bad_title');
      const items = Array.isArray(body?.items) ? [...new Set(body.items)] : bad('bad_items');
      if (!items.length || items.length > 40 || items.some(i => typeof i !== 'string' || !ITEM_ID.test(i))) bad('bad_items');
      const due = body.due_at == null ? null : Number.isInteger(body.due_at) && body.due_at > t && body.due_at < t + 400 * 86400 ? body.due_at : bad('bad_due');
      await limit(env, 'class-assign:' + me.id, 60, 86400);
      const r = await DB.prepare('INSERT INTO class_assignments(class_id,title,items,due_at,created_at) VALUES(?,?,?,?,?)').bind(c.id, title, JSON.stringify(items), due, t).run();
      return {id: r.meta.last_row_id};
    }
    if (mm[3] && m === 'DELETE') { await DB.prepare('DELETE FROM class_members WHERE class_id=? AND user_id=?').bind(c.id, +mm[3]).run(); return {ok: true}; }
    throw new HttpError(404, 'not_found');
  }
}

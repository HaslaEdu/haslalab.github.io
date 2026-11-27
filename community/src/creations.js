/* Creations: simulations, virtual experiments and computational-physics problems that members write and share, and
   that anyone can open, play and solve (create.html). Two kinds:
     sim   JavaScript drawn on a canvas with a few helpers (sliders, readouts, a frame loop), optionally with a question
           whose answer is a number or a formula (a virtual experiment: measure, then answer);
     code  a Python problem: a statement, starter code and a grader that runs the solver's code in their own browser.
   Everything here is public text; a creation's code runs only in a sandboxed frame or a Pyodide worker in the reader's
   browser, never on the server. Owners edit and hide their own; staff can hide any. */
export const CREATION_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS creations (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     user_id INTEGER NOT NULL,
     kind TEXT NOT NULL,
     title TEXT NOT NULL,
     summary TEXT NOT NULL DEFAULT '',
     body TEXT NOT NULL DEFAULT '',
     code TEXT NOT NULL DEFAULT '',
     starter TEXT NOT NULL DEFAULT '',
     grader TEXT NOT NULL DEFAULT '',
     answer TEXT,
     unit TEXT NOT NULL DEFAULT '',
     status TEXT NOT NULL DEFAULT 'public',
     forked_from INTEGER,
     plays INTEGER NOT NULL DEFAULT 0,
     likes INTEGER NOT NULL DEFAULT 0,
     solves INTEGER NOT NULL DEFAULT 0,
     created_at INTEGER NOT NULL,
     updated_at INTEGER NOT NULL)`,
  `CREATE INDEX IF NOT EXISTS creations_list ON creations(status, kind, created_at DESC)`,
  `CREATE INDEX IF NOT EXISTS creations_user ON creations(user_id)`,
  `CREATE TABLE IF NOT EXISTS creation_first_publication (
    creation_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, published_at INTEGER NOT NULL)`,
  `CREATE INDEX IF NOT EXISTS creation_publication_owner_time ON creation_first_publication(user_id,published_at)`,
  ...['INSERT', 'UPDATE'].flatMap(event => {
    const transition = event === 'INSERT' ? '' : " AND OLD.status<>'public'";
    const name = event.toLowerCase();
    return [
      `CREATE TRIGGER IF NOT EXISTS creation_public_cap_${name} BEFORE ${event} ON creations
        WHEN NEW.status='public'${transition}
        BEGIN
          SELECT RAISE(ABORT,'workshop_public_cap') WHERE
            (SELECT COUNT(*) FROM creations WHERE user_id=NEW.user_id AND status='public')>=10;
          SELECT RAISE(ABORT,'workshop_daily_share_limit') WHERE
            (SELECT COUNT(*) FROM creation_first_publication WHERE user_id=NEW.user_id
              AND published_at>=NEW.updated_at-((NEW.updated_at+32400)%86400))>=3
            AND NOT EXISTS(SELECT 1 FROM creation_first_publication WHERE creation_id=NEW.id);
        END`,
      `CREATE TRIGGER IF NOT EXISTS creation_public_log_${name} AFTER ${event} ON creations
        WHEN NEW.status='public'${transition}
        BEGIN
          INSERT OR IGNORE INTO creation_first_publication(creation_id,user_id,published_at)
            VALUES(NEW.id,NEW.user_id,NEW.updated_at);
        END`
    ];
  }),
  `CREATE TABLE IF NOT EXISTS creation_likes (
     creation_id INTEGER NOT NULL,
     user_id INTEGER NOT NULL,
     created_at INTEGER NOT NULL,
     PRIMARY KEY (creation_id, user_id))`,
  `CREATE TABLE IF NOT EXISTS creation_solves (
     creation_id INTEGER NOT NULL,
     user_id INTEGER NOT NULL,
     created_at INTEGER NOT NULL,
     PRIMARY KEY (creation_id, user_id))`
];
export const KINDS = ['sim', 'code'];
export const LIMITS = {title: 80, summary: 200, body: 8000, code: 60000, starter: 20000, grader: 30000, answer: 400, unit: 24};
const PER_PAGE = 24;
const ready = new WeakSet();
export async function ensureCreationSchema(env) {
  if (ready.has(env.DB)) return;
  for (const sql of CREATION_SCHEMA) await env.DB.prepare(sql).run();
  for (const col of ['source_file','source_digest']) {
    try { await env.DB.prepare(`ALTER TABLE creations ADD COLUMN ${col} TEXT`).run(); }
    catch (e) { if (!/duplicate column/i.test(String(e?.message || e))) throw e; }
    await env.DB.prepare(`CREATE UNIQUE INDEX IF NOT EXISTS creations_${col}_idx ON creations(user_id,${col}) WHERE ${col} IS NOT NULL`).run();
  }
  ready.add(env.DB);
}
export async function publicCreationWrite(statement, HttpError) {
  try { return await statement.run(); }
  catch (error) {
    for (const code of ['workshop_public_cap','workshop_daily_share_limit']) {
      if (String(error?.message || error).includes(code)) throw new HttpError(429, code);
    }
    throw error;
  }
}
const LIST_COLS = 'c.id,c.kind,c.title,c.summary,c.plays,c.likes,c.solves,c.forked_from,c.created_at,c.updated_at,c.user_id,u.nickname';

export function createCreationRouter({HttpError, needUser, limit, now, bad, clientIp, isStaff = me => me?.role === 'admin'}) {
  const field = (body, key, required) => {
    const v = body?.[key];
    if (v == null || v === '') { if (required) bad('bad_' + key); return ''; }
    if (typeof v !== 'string' || v.length > LIMITS[key]) bad('bad_' + key);
    return key === 'title' || key === 'summary' || key === 'unit' ? v.trim() : v;
  };
  /* a sim's question: its answer as the text a learner would type (a number or a formula), checked in the browser */
  function clean(body, partial = false) {
    const out = {};
    if (!partial || 'kind' in body) out.kind = KINDS.includes(body?.kind) ? body.kind : bad('bad_kind');
    if (!partial || 'title' in body) { out.title = field(body, 'title', true); if (!out.title) bad('bad_title'); }
    for (const k of ['summary', 'body', 'code', 'starter', 'grader', 'unit']) if (!partial || k in body) out[k] = field(body, k, false);
    if (!partial || 'answer' in body) out.answer = body?.answer == null || body.answer === '' ? null : field(body, 'answer', false);
    return out;
  }
  function complete(c) {
    if (c.kind === 'sim' && !c.code.trim()) bad('bad_code');
    if (c.kind === 'code' && (!c.grader.trim() || !/def\s+grade\s*\(/.test(c.grader))) bad('bad_grader');
    if (c.kind === 'code' && !c.body.trim()) bad('bad_body');
  }
  return async function creationRoute(p, m, body, me, req, env) {
    if (!p.startsWith('/api/creations')) return undefined;
    await ensureCreationSchema(env);
    const DB = env.DB, t = now();
    if (p === '/api/creations' && m === 'GET') {
      const url = new URL(req?.url || 'https://x/'), q = url.searchParams;
      const kind = KINDS.includes(q.get('kind')) ? q.get('kind') : null;
      const sort = q.get('sort') === 'popular' ? '(c.likes*3+c.solves*2+c.plays) DESC, c.id DESC' : 'c.id DESC';
      const page = Math.max(1, Math.min(200, parseInt(q.get('page')) || 1));
      const mine = q.get('mine') === '1' && me;
      /* figures and problem sets shared from the other makers (workshop-share.js) are kept here too; create.html lists only its own kinds */
      const where = (mine ? 'c.user_id=?' : "c.status='public'") + (kind ? ' AND c.kind=?' : " AND c.kind IN ('sim','code')");
      const args = [...(mine ? [me.id] : []), ...(kind ? [kind] : [])];
      const rows = (await DB.prepare(`SELECT ${LIST_COLS} FROM creations c LEFT JOIN users u ON u.id=c.user_id WHERE ${where} ORDER BY ${sort} LIMIT ? OFFSET ?`)
        .bind(...args, PER_PAGE + 1, (page - 1) * PER_PAGE).all()).results || [];
      return {items: rows.slice(0, PER_PAGE), more: rows.length > PER_PAGE, page};
    }
    if (p === '/api/creations' && m === 'POST') {
      needUser(me);
      await limit(env, 'creation-new:' + me.id, 20, 86400);
      const c = clean(body);complete(c);
      const from = Number.isInteger(body?.forked_from) ? body.forked_from : null;
      const r = await publicCreationWrite(DB.prepare(`INSERT INTO creations(user_id,kind,title,summary,body,code,starter,grader,answer,unit,forked_from,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)`).bind(me.id, c.kind, c.title, c.summary, c.body, c.code, c.starter, c.grader, c.answer, c.unit, from, t, t), HttpError);
      return {id: r.meta.last_row_id};
    }
    const mm = /^\/api\/creations\/(\d+)(?:\/(like|play|solve))?$/.exec(p);
    if (!mm) throw new HttpError(404, 'not_found');
    const id = +mm[1];
    const row = await DB.prepare(`SELECT c.*,u.nickname FROM creations c LEFT JOIN users u ON u.id=c.user_id WHERE c.id=?`).bind(id).first();
    const owner = row && me && row.user_id === me.id, staff = isStaff(me);
    if (!row || row.status !== 'public' && !owner && !staff) throw new HttpError(404, 'not_found');
    if (!mm[2] && m === 'GET') {
      const liked = me ? !!(await DB.prepare('SELECT 1 AS y FROM creation_likes WHERE creation_id=? AND user_id=?').bind(id, me.id).first()) : false;
      const solved = me ? !!(await DB.prepare('SELECT 1 AS y FROM creation_solves WHERE creation_id=? AND user_id=?').bind(id, me.id).first()) : false;
      const {source_file, source_digest, ...creation} = row;
      return {creation: {...creation, mine: !!owner}, liked, solved};
    }
    if (!mm[2] && m === 'PATCH') {
      needUser(me);
      if (!owner && !staff) throw new HttpError(403, 'not_owner');
      await limit(env, 'creation-edit:' + me.id, 120, 3600);
      const c = {...row, ...clean(body, true)};complete(c);
      /* a remix starts as the member's private draft (workshop-share.js); the editor's "save and publish" makes it public */
      await publicCreationWrite(DB.prepare(`UPDATE creations SET kind=?,title=?,summary=?,body=?,code=?,starter=?,grader=?,answer=?,unit=?,updated_at=?,status=CASE WHEN status='draft' AND user_id=? THEN 'public' ELSE status END WHERE id=?`)
        .bind(c.kind, c.title, c.summary, c.body, c.code, c.starter, c.grader, c.answer, c.unit, t, me.id, id), HttpError);
      return {ok: true};
    }
    if (!mm[2] && m === 'DELETE') {
      needUser(me);
      if (!owner && !staff) throw new HttpError(403, 'not_owner');
      await DB.prepare("UPDATE creations SET status='hidden',updated_at=? WHERE id=?").bind(t, id).run();
      return {ok: true};
    }
    if (mm[2] === 'play' && m === 'POST') {
      /* one play per visitor per creation a day */
      try { await limit(env, `creation-play:${id}:${me ? 'm' + me.id : clientIp(req)}`, 1, 86400); }
      catch (e) { if (e?.status === 429) return {ok: true, counted: false}; throw e; }
      await DB.prepare('UPDATE creations SET plays=plays+1 WHERE id=?').bind(id).run();
      return {ok: true, counted: true};
    }
    if (mm[2] === 'like' && m === 'POST') {
      needUser(me);
      await limit(env, 'creation-like:' + me.id, 300, 3600);
      const on = body?.on !== false;
      const r = on ? await DB.prepare('INSERT OR IGNORE INTO creation_likes(creation_id,user_id,created_at) VALUES(?,?,?)').bind(id, me.id, t).run()
        : await DB.prepare('DELETE FROM creation_likes WHERE creation_id=? AND user_id=?').bind(id, me.id).run();
      const n = (await DB.prepare('SELECT COUNT(*) AS n FROM creation_likes WHERE creation_id=?').bind(id).first()).n;
      await DB.prepare('UPDATE creations SET likes=? WHERE id=?').bind(n, id).run();
      return {liked: on, likes: n, changed: !!r.meta?.changes};
    }
    if (mm[2] === 'solve' && m === 'POST') {
      needUser(me);
      await limit(env, 'creation-solve:' + me.id, 300, 3600);
      await DB.prepare('INSERT OR IGNORE INTO creation_solves(creation_id,user_id,created_at) VALUES(?,?,?)').bind(id, me.id, t).run();
      const n = (await DB.prepare('SELECT COUNT(*) AS n FROM creation_solves WHERE creation_id=?').bind(id).first()).n;
      await DB.prepare('UPDATE creations SET solves=? WHERE id=?').bind(n, id).run();
      return {solves: n};
    }
    throw new HttpError(404, 'not_found');
  };
}

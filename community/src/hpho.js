/* HPhO (HaslaLab Physics Olympiad): an individual, twice-yearly practice olympiad run by HaslaEdu. Not an admissions
   credential. This module holds its rounds and registrations:
     GET    /api/hpho                         rounds (public) and, signed in, the caller's own entries
     POST   /api/hpho/rounds/:id/entry        register (candidate number issued here)
     DELETE /api/hpho/rounds/:id/entry        withdraw while registration is open
     POST   /api/hpho/rounds/:id              admin: create or edit a round
     GET    /api/hpho/rounds/:id/entries      admin: the round's entries
   The answer sheets carry the candidate number only; candidates are warned not to write their name or school, and
   anything identifying they write anyway is their own responsibility (no automatic disqualification). */

export const HPHO_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS hpho_rounds (id TEXT PRIMARY KEY, title_ko TEXT NOT NULL, title_en TEXT NOT NULL,
    reg_open INTEGER NOT NULL, reg_close INTEGER NOT NULL, start_at INTEGER NOT NULL, duration_min INTEGER NOT NULL,
    fee_usd REAL NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'draft', created_at INTEGER NOT NULL, updated_at INTEGER)`,
  `CREATE TABLE IF NOT EXISTS hpho_entries (round_id TEXT NOT NULL, user_id INTEGER NOT NULL, candidate_no TEXT NOT NULL,
    country TEXT NOT NULL, level TEXT NOT NULL, birth_year INTEGER NOT NULL, guardian_consent INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL, PRIMARY KEY (round_id, user_id))`,
  `CREATE UNIQUE INDEX IF NOT EXISTS hpho_entries_no ON hpho_entries(round_id, candidate_no)`,
];

export const HPHO_LEVELS = ['middle', 'high', 'university', 'other'];
const ROUND_ID = /^(20\d\d)-([12])$/;
const STATUSES = ['draft', 'open', 'closed', 'finished'];
const now = () => Math.floor(Date.now() / 1000);

const ready = new WeakMap();
export function ensureHpho(db) {
  if (!ready.has(db)) {
    const p = db.batch(HPHO_SCHEMA.map(sql => db.prepare(sql))).then(() => true);
    ready.set(db, p); p.catch(() => ready.delete(db));
  }
  return ready.get(db);
}

/* a round as anyone may see it; a draft is never shown */
export function publicRound(r) {
  return { id: r.id, title: { ko: r.title_ko, en: r.title_en }, reg_open: r.reg_open, reg_close: r.reg_close,
    start_at: r.start_at, duration_min: r.duration_min, fee_usd: r.fee_usd, status: r.status };
}
const registrable = (r, t = now()) => r && r.status === 'open' && t >= r.reg_open && t < r.reg_close;

/* "HP271-4821": the round's year and half, then four digits drawn at random (an entry count cannot be read off it) */
export function candidatePrefix(roundId) {
  const m = ROUND_ID.exec(roundId); return m ? `HP${m[1].slice(2)}${m[2]}-` : null;
}

export function checkEntry(body, { year = new Date().getUTCFullYear() } = {}) {
  const country = typeof body?.country === 'string' ? body.country.trim().toUpperCase() : '';
  if (!/^[A-Z]{2}$/.test(country)) return { error: 'bad_country' };
  const level = HPHO_LEVELS.includes(body?.level) ? body.level : null;
  if (!level) return { error: 'bad_level' };
  const birth = Number(body?.birth_year);
  if (!Number.isInteger(birth) || birth < year - 40 || birth > year - 8) return { error: 'bad_birth_year' };
  if (body?.pledge !== true) return { error: 'pledge_required' };            /* rules, honour code, no outside help */
  if (body?.proctoring !== true) return { error: 'proctoring_consent_required' }; /* desktop app, webcam and screen */
  if (body?.identity_notice !== true) return { error: 'identity_notice_required' }; /* candidate number only on sheets */
  const minor = year - birth < 19;                                            /* may still be 18 on the day: ask */
  if (minor && body?.guardian_consent !== true) return { error: 'guardian_consent_required' };
  return { country, level, birth_year: birth, guardian_consent: minor ? 1 : 0 };
}

export function checkRound(id, body) {
  if (!ROUND_ID.test(id)) return { error: 'bad_round' };
  const text = (v, n) => typeof v === 'string' && v.trim() && v.trim().length <= n ? v.trim() : null;
  const title_ko = text(body?.title_ko, 80), title_en = text(body?.title_en, 80);
  if (!title_ko || !title_en) return { error: 'bad_title' };
  const ints = ['reg_open', 'reg_close', 'start_at'].map(k => Number(body?.[k]));
  if (!ints.every(Number.isInteger)) return { error: 'bad_time' };
  const [reg_open, reg_close, start_at] = ints;
  if (!(reg_open < reg_close && reg_close <= start_at)) return { error: 'bad_time_order' };
  const duration_min = Number(body?.duration_min);
  if (!Number.isInteger(duration_min) || duration_min < 30 || duration_min > 600) return { error: 'bad_duration' };
  const fee_usd = Number(body?.fee_usd ?? 0);
  if (!Number.isFinite(fee_usd) || fee_usd < 0 || fee_usd > 5) return { error: 'bad_fee' };   /* the owner's cap: $5 */
  const status = STATUSES.includes(body?.status) ? body.status : 'draft';
  return { title_ko, title_en, reg_open, reg_close, start_at, duration_min, fee_usd: Math.round(fee_usd * 100) / 100, status };
}

export function createHphoRouter({ HttpError, needUser, limit, isAdmin, scope = env => env.DB }) {
  const fail = (status, code) => { throw new HttpError(status, code); };
  return async function hpho(p, m, body, me, env) {
    if (p !== '/api/hpho' && !p.startsWith('/api/hpho/')) return undefined;
    const db = scope(env); await ensureHpho(db);
    if (p === '/api/hpho' && m === 'GET') {
      const rounds = (await db.prepare(`SELECT * FROM hpho_rounds WHERE status!='draft' ORDER BY start_at DESC LIMIT 20`).all()).results || [];
      const entries = {};
      if (me) for (const e of (await db.prepare('SELECT round_id,candidate_no,country,level,birth_year,created_at FROM hpho_entries WHERE user_id=?').bind(me.id).all()).results || [])
        entries[e.round_id] = e;
      return { rounds: rounds.map(publicRound), entries, now: now() };
    }
    let r = /^\/api\/hpho\/rounds\/([^/]+)\/entry$/.exec(p);
    if (r) {
      needUser(me);
      const id = r[1], round = await db.prepare('SELECT * FROM hpho_rounds WHERE id=?').bind(id).first();
      if (!round || round.status === 'draft') fail(404, 'round_not_found');
      if (m === 'POST') {
        await limit(env, 'hpho:' + me.id, 10, 3600);
        if (!registrable(round)) fail(409, 'registration_closed');
        const ok = checkEntry(body); if (ok.error) fail(400, ok.error);
        const had = await db.prepare('SELECT candidate_no FROM hpho_entries WHERE round_id=? AND user_id=?').bind(id, me.id).first();
        if (had) {
          await db.prepare('UPDATE hpho_entries SET country=?,level=?,birth_year=?,guardian_consent=? WHERE round_id=? AND user_id=?')
            .bind(ok.country, ok.level, ok.birth_year, ok.guardian_consent, id, me.id).run();
          return { ok: true, candidate_no: had.candidate_no, updated: true };
        }
        const prefix = candidatePrefix(id);
        for (let i = 0; i < 8; i++) {
          const no = prefix + String(crypto.getRandomValues(new Uint32Array(1))[0] % 10000).padStart(4, '0');
          try {
            await db.prepare('INSERT INTO hpho_entries(round_id,user_id,candidate_no,country,level,birth_year,guardian_consent,created_at) VALUES(?,?,?,?,?,?,?,?)')
              .bind(id, me.id, no, ok.country, ok.level, ok.birth_year, ok.guardian_consent, now()).run();
            return { ok: true, candidate_no: no };
          } catch (e) { if (!/UNIQUE/i.test(String(e?.message || e))) throw e; }
        }
        fail(503, 'candidate_number_busy');
      }
      if (m === 'DELETE') {
        if (!registrable(round)) fail(409, 'registration_closed');
        await db.prepare('DELETE FROM hpho_entries WHERE round_id=? AND user_id=?').bind(id, me.id).run();
        return { ok: true };
      }
      fail(405, 'method_not_allowed');
    }
    if ((r = /^\/api\/hpho\/rounds\/([^/]+)$/.exec(p)) && m === 'POST') {
      needUser(me); if (!isAdmin(me)) fail(403, 'forbidden');
      const ok = checkRound(r[1], body); if (ok.error) fail(400, ok.error);
      await db.prepare(`INSERT INTO hpho_rounds(id,title_ko,title_en,reg_open,reg_close,start_at,duration_min,fee_usd,status,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title_ko=excluded.title_ko,title_en=excluded.title_en,
        reg_open=excluded.reg_open,reg_close=excluded.reg_close,start_at=excluded.start_at,duration_min=excluded.duration_min,
        fee_usd=excluded.fee_usd,status=excluded.status,updated_at=excluded.created_at`)
        .bind(r[1], ok.title_ko, ok.title_en, ok.reg_open, ok.reg_close, ok.start_at, ok.duration_min, ok.fee_usd, ok.status, now()).run();
      return { ok: true, id: r[1] };
    }
    if ((r = /^\/api\/hpho\/rounds\/([^/]+)\/entries$/.exec(p)) && m === 'GET') {
      needUser(me); if (!isAdmin(me)) fail(403, 'forbidden');
      const rows = (await db.prepare('SELECT candidate_no,country,level,birth_year,guardian_consent,created_at FROM hpho_entries WHERE round_id=? ORDER BY created_at').bind(r[1]).all()).results || [];
      return { count: rows.length, entries: rows };
    }
    fail(404, 'not_found');
  };
}

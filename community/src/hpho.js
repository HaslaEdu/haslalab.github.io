/* HPhO (HaslaLab Physics Olympiad): an individual, twice-yearly practice olympiad run by HaslaEdu. Not an admissions
   credential. This module holds its rounds and registrations:
     GET    /api/hpho                         rounds (public) and, signed in, the caller's own entries
     POST   /api/hpho/rounds/:id/entry        register (candidate number issued here)
     DELETE /api/hpho/rounds/:id/entry        withdraw while registration is open
     POST   /api/hpho/rounds/:id              admin: create or edit a round
     GET    /api/hpho/rounds/:id/entries      admin: the round's entries
   The answer sheets carry the candidate number only; candidates are warned not to write their name or school, and
   anything identifying they write anyway is their own responsibility (no automatic disqualification).
   Fee assistance: a candidate from a low- or lower-middle-income economy (AID_AUTO_COUNTRIES, the World Bank's
   classification; review it each year) pays nothing without asking; anyone else may apply with a reason and a short
   note, no documents, and an admin decides (POST /api/hpho/rounds/:id/aid). */

export const HPHO_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS hpho_rounds (id TEXT PRIMARY KEY, title_ko TEXT NOT NULL, title_en TEXT NOT NULL,
    reg_open INTEGER NOT NULL, reg_close INTEGER NOT NULL, start_at INTEGER NOT NULL, duration_min INTEGER NOT NULL,
    fee_usd REAL NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'draft', created_at INTEGER NOT NULL, updated_at INTEGER)`,
  `CREATE TABLE IF NOT EXISTS hpho_entries (round_id TEXT NOT NULL, user_id INTEGER NOT NULL, candidate_no TEXT NOT NULL,
    country TEXT NOT NULL, level TEXT NOT NULL, birth_year INTEGER NOT NULL, guardian_consent INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL, PRIMARY KEY (round_id, user_id))`,
  `CREATE UNIQUE INDEX IF NOT EXISTS hpho_entries_no ON hpho_entries(round_id, candidate_no)`,
];
/* columns added after the table first went live: each ALTER runs once, a "duplicate column" is the column already there */
const HPHO_COLUMNS = [`ALTER TABLE hpho_entries ADD COLUMN aid TEXT NOT NULL DEFAULT 'none'`, `ALTER TABLE hpho_entries ADD COLUMN aid_reason TEXT`,
  `ALTER TABLE hpho_entries ADD COLUMN aid_note TEXT`, `ALTER TABLE hpho_entries ADD COLUMN aid_at INTEGER`,
  /* optional, separate from the required proctoring consent: may the proctoring records help train HaslaEdu's AI proctor */
  `ALTER TABLE hpho_entries ADD COLUMN train_consent INTEGER NOT NULL DEFAULT 0`,
  /* IsPhO-style days: the theory and the experiment exam each start at their own time (start_at stays the theory start) */
  `ALTER TABLE hpho_rounds ADD COLUMN theory_at INTEGER`, `ALTER TABLE hpho_rounds ADD COLUMN experiment_at INTEGER`];

/* each exam (theory, experiment) lasts five hours; its room opens an hour before, and a candidate must be seated in the
   waiting room twenty minutes before the start (the owner's rules, 2026-11-09) */
export const TRACKS = ['theory', 'experiment'];
export const TRACK_MIN = 300;
export const OPEN_BEFORE = 3600;
export const SEAT_BEFORE = 1200;
/* a round's exams in order: a round from before the split has its one exam (start_at, duration_min) as the theory */
export function roundTracks(r) {
  const out = [];
  const add = (track, start, min) => { if (Number.isInteger(start)) out.push({ track, start_at: start, duration_min: min, opens: start - OPEN_BEFORE, seat_by: start - SEAT_BEFORE, ends: start + min * 60 }); };
  if (r.theory_at != null) { add('theory', r.theory_at, TRACK_MIN); add('experiment', r.experiment_at ?? null, TRACK_MIN); }
  else add('theory', r.start_at, r.duration_min);
  return out;
}
/* when the round's last exam ends */
export const roundEnds = r => Math.max(...roundTracks(r).map(x => x.ends), r.start_at + r.duration_min * 60);

/* the World Bank's low- and lower-middle-income economies (FY2026 list as HaslaEdu applies it; check it before each round) */
export const AID_AUTO_COUNTRIES = new Set(('AF BF BI CF TD CD ER ET GM GW KP LR MG MW ML MZ NE RW SL SO SS SD SY TG UG YE ' +
  'AO BD BJ BT BO KH CM CV KM CG CI DJ EG SZ GH GN HT HN IN KE KI KG LA LB LS MR FM MA MM NP NI NG PK PG PH WS ST SN SB LK TJ TZ TL TN UZ VU VN PS ZM ZW').split(' '));
/* on hold (the owner, 2026-11-08): no automatic waiver and no requests until HaslaEdu decides how to target it */
export const AID_ENABLED = false;
export const AID_REASONS = ['family_income', 'public_assistance', 'school_referral', 'other'];
export const AID_STATES = ['none', 'auto', 'pending', 'approved', 'declined'];

export const HPHO_LEVELS = ['middle', 'high', 'university', 'other'];
const ROUND_ID = /^(20\d\d)-([12])$/;
const STATUSES = ['draft', 'open', 'closed', 'finished'];
const now = () => Math.floor(Date.now() / 1000);

const ready = new WeakMap();
export function ensureHpho(db) {
  if (!ready.has(db)) {
    const p = db.batch(HPHO_SCHEMA.map(sql => db.prepare(sql))).then(async () => {
      for (const sql of HPHO_COLUMNS) try { await db.prepare(sql).run(); } catch (e) { if (!/duplicate column/i.test(String(e?.message || e))) throw e; }
      return true;
    });
    ready.set(db, p); p.catch(() => ready.delete(db));
  }
  return ready.get(db);
}

/* a round as anyone may see it; a draft is never shown, except to admins: for them a draft is a rehearsal round they can
   register for and sit at any time before it ends, to test the exam end to end */
export function publicRound(r) {
  return { id: r.id, title: { ko: r.title_ko, en: r.title_en }, reg_open: r.reg_open, reg_close: r.reg_close,
    start_at: r.start_at, duration_min: r.duration_min, fee_usd: r.fee_usd, status: r.status,
    tracks: roundTracks(r).map(({ track, start_at, duration_min }) => ({ track, start_at, duration_min })) };
}
const registrable = (r, t = now(), admin = false) => r && (r.status === 'open' && t >= r.reg_open && t < r.reg_close
  || admin && r.status === 'draft' && t < roundEnds(r));
export const visibleRound = (r, admin) => !!r && (r.status !== 'draft' || admin);

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
  if (!Number.isInteger(birth) || birth < year - 40) return { error: 'bad_birth_year' };
  /* 14 or older (the owner's rule, 2026-11-09): only the year is asked, so the year itself must allow it and the
     candidate confirms it for a birthday still to come this year */
  if (birth > year - 14) return { error: 'too_young' };
  if (body?.age14 !== true) return { error: 'age14_required' };
  if (body?.pledge !== true) return { error: 'pledge_required' };            /* rules, honour code, no outside help */
  if (body?.proctoring !== true) return { error: 'proctoring_consent_required' }; /* desktop app, webcam and screen */
  if (body?.identity_notice !== true) return { error: 'identity_notice_required' }; /* candidate number only on sheets */
  const minor = year - birth < 19;                                            /* may still be 18 on the day: ask */
  if (minor && body?.guardian_consent !== true) return { error: 'guardian_consent_required' };
  let aid = 'none', aid_reason = null, aid_note = null;
  if (!AID_ENABLED) { /* assistance on hold: every candidate owes the round's fee */ }
  else if (AID_AUTO_COUNTRIES.has(country)) aid = 'auto';
  else if (body?.aid_request === true) {
    aid_reason = AID_REASONS.includes(body.aid_reason) ? body.aid_reason : null;
    if (!aid_reason) return { error: 'bad_aid_reason' };
    aid_note = typeof body.aid_note === 'string' ? body.aid_note.trim().slice(0, 300) : '';
    if (aid_note.length < 10) return { error: 'aid_note_required' };
    aid = 'pending';
  }
  /* a minor may let the records train the AI proctor only with a guardian's consent to that too, asked separately */
  const train = body?.train_consent === true;
  if (train && minor && body?.train_guardian_consent !== true) return { error: 'train_guardian_consent_required' };
  return { country, level, birth_year: birth, guardian_consent: minor ? 1 : 0, aid, aid_reason, aid_note, train_consent: train ? 1 : 0 };
}
/* what a candidate owes: nothing under automatic or approved assistance, else the round's fee */
export const feeDue = (round, aid) => aid === 'auto' || aid === 'approved' ? 0 : round.fee_usd;

export function checkRound(id, body) {
  if (!ROUND_ID.test(id)) return { error: 'bad_round' };
  const text = (v, n) => typeof v === 'string' && v.trim() && v.trim().length <= n ? v.trim() : null;
  const title_ko = text(body?.title_ko, 80), title_en = text(body?.title_en, 80);
  if (!title_ko || !title_en) return { error: 'bad_title' };
  /* theory_at (and experiment_at) set the two exam days; a round given only start_at keeps one exam of duration_min */
  const theory_at = body?.theory_at == null ? null : Number(body.theory_at), experiment_at = body?.experiment_at == null ? null : Number(body.experiment_at);
  if (experiment_at != null && theory_at == null) return { error: 'bad_time' };
  const ints = ['reg_open', 'reg_close'].map(k => Number(body?.[k])).concat(theory_at ?? Number(body?.start_at));
  if (!ints.every(Number.isInteger) || [theory_at, experiment_at].some(v => v != null && !Number.isInteger(v))) return { error: 'bad_time' };
  const [reg_open, reg_close, start_at] = ints;
  if (!(reg_open < reg_close && reg_close <= start_at)) return { error: 'bad_time_order' };
  /* the experiment starts after the theory exam has ended (another day, or later the same day) */
  if (experiment_at != null && experiment_at < theory_at + TRACK_MIN * 60) return { error: 'bad_time_order' };
  const duration_min = theory_at != null ? TRACK_MIN : Number(body?.duration_min);
  if (!Number.isInteger(duration_min) || duration_min < 30 || duration_min > 600) return { error: 'bad_duration' };
  const fee_usd = Number(body?.fee_usd ?? 0);
  if (!Number.isFinite(fee_usd) || fee_usd < 0 || fee_usd > 5) return { error: 'bad_fee' };   /* the owner's cap: $5 */
  const status = STATUSES.includes(body?.status) ? body.status : 'draft';
  return { title_ko, title_en, reg_open, reg_close, start_at, duration_min, theory_at, experiment_at, fee_usd: Math.round(fee_usd * 100) / 100, status };
}

export function createHphoRouter({ HttpError, needUser, limit, isAdmin, scope = env => env.DB }) {
  const fail = (status, code) => { throw new HttpError(status, code); };
  return async function hpho(p, m, body, me, env) {
    if (p !== '/api/hpho' && !p.startsWith('/api/hpho/')) return undefined;
    const db = scope(env); await ensureHpho(db);
    if (p === '/api/hpho' && m === 'GET') {
      const rounds = (await db.prepare(`SELECT * FROM hpho_rounds WHERE status!='draft' OR ? ORDER BY start_at DESC LIMIT 20`).bind(isAdmin(me) ? 1 : 0).all()).results || [];
      const entries = {};
      if (me) for (const e of (await db.prepare('SELECT round_id,candidate_no,country,level,birth_year,train_consent,aid,aid_reason,aid_note,created_at FROM hpho_entries WHERE user_id=?').bind(me.id).all()).results || []) {
        const round = rounds.find(r => r.id === e.round_id);
        entries[e.round_id] = { ...e, fee_due: round ? feeDue(round, e.aid) : null };
      }
      return { rounds: rounds.map(publicRound), entries, now: now() };
    }
    let r = /^\/api\/hpho\/rounds\/([^/]+)\/entry$/.exec(p);
    if (r) {
      needUser(me);
      const id = r[1], round = await db.prepare('SELECT * FROM hpho_rounds WHERE id=?').bind(id).first(), admin = isAdmin(me);
      if (!visibleRound(round, admin)) fail(404, 'round_not_found');
      if (m === 'POST') {
        await limit(env, 'hpho:' + me.id, 10, 3600);
        if (!registrable(round, now(), admin)) fail(409, 'registration_closed');
        const ok = checkEntry(body); if (ok.error) fail(400, ok.error);
        const had = await db.prepare('SELECT candidate_no,aid,aid_reason FROM hpho_entries WHERE round_id=? AND user_id=?').bind(id, me.id).first();
        if (had) {
          /* an admin's decision on a request stands while the candidate keeps asking; a new request or a new country re-opens it */
          const aid = ok.aid === 'pending' && ['approved', 'declined'].includes(had.aid) && had.aid_reason === ok.aid_reason ? had.aid : ok.aid;
          await db.prepare('UPDATE hpho_entries SET country=?,level=?,birth_year=?,guardian_consent=?,train_consent=?,aid=?,aid_reason=?,aid_note=?,aid_at=CASE WHEN ?=aid THEN aid_at ELSE NULL END WHERE round_id=? AND user_id=?')
            .bind(ok.country, ok.level, ok.birth_year, ok.guardian_consent, ok.train_consent, aid, ok.aid_reason, ok.aid_note, aid, id, me.id).run();
          return { ok: true, candidate_no: had.candidate_no, updated: true, aid, fee_due: feeDue(round, aid) };
        }
        const prefix = candidatePrefix(id);
        for (let i = 0; i < 8; i++) {
          const no = prefix + String(crypto.getRandomValues(new Uint32Array(1))[0] % 10000).padStart(4, '0');
          try {
            await db.prepare('INSERT INTO hpho_entries(round_id,user_id,candidate_no,country,level,birth_year,guardian_consent,train_consent,aid,aid_reason,aid_note,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)')
              .bind(id, me.id, no, ok.country, ok.level, ok.birth_year, ok.guardian_consent, ok.train_consent, ok.aid, ok.aid_reason, ok.aid_note, now()).run();
            return { ok: true, candidate_no: no, aid: ok.aid, fee_due: feeDue(round, ok.aid) };
          } catch (e) { if (!/UNIQUE/i.test(String(e?.message || e))) throw e; }
        }
        fail(503, 'candidate_number_busy');
      }
      if (m === 'DELETE') {
        if (!registrable(round, now(), admin)) fail(409, 'registration_closed');
        await db.prepare('DELETE FROM hpho_entries WHERE round_id=? AND user_id=?').bind(id, me.id).run();
        return { ok: true };
      }
      fail(405, 'method_not_allowed');
    }
    if ((r = /^\/api\/hpho\/rounds\/([^/]+)$/.exec(p)) && m === 'POST') {
      needUser(me); if (!isAdmin(me)) fail(403, 'forbidden');
      const ok = checkRound(r[1], body); if (ok.error) fail(400, ok.error);
      await db.prepare(`INSERT INTO hpho_rounds(id,title_ko,title_en,reg_open,reg_close,start_at,duration_min,theory_at,experiment_at,fee_usd,status,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title_ko=excluded.title_ko,title_en=excluded.title_en,
        reg_open=excluded.reg_open,reg_close=excluded.reg_close,start_at=excluded.start_at,duration_min=excluded.duration_min,
        theory_at=excluded.theory_at,experiment_at=excluded.experiment_at,fee_usd=excluded.fee_usd,status=excluded.status,updated_at=excluded.created_at`)
        .bind(r[1], ok.title_ko, ok.title_en, ok.reg_open, ok.reg_close, ok.start_at, ok.duration_min, ok.theory_at, ok.experiment_at, ok.fee_usd, ok.status, now()).run();
      return { ok: true, id: r[1] };
    }
    if ((r = /^\/api\/hpho\/rounds\/([^/]+)\/entries$/.exec(p)) && m === 'GET') {
      needUser(me); if (!isAdmin(me)) fail(403, 'forbidden');
      const rows = (await db.prepare('SELECT candidate_no,country,level,birth_year,guardian_consent,train_consent,aid,aid_reason,aid_note,aid_at,created_at FROM hpho_entries WHERE round_id=? ORDER BY created_at').bind(r[1]).all()).results || [];
      const aid = Object.fromEntries(AID_STATES.map(k => [k, rows.filter(e => e.aid === k).length]));
      return { count: rows.length, aid, entries: rows };
    }
    if ((r = /^\/api\/hpho\/rounds\/([^/]+)\/aid$/.exec(p)) && m === 'POST') {
      needUser(me); if (!isAdmin(me)) fail(403, 'forbidden');
      const decision = ['approved', 'declined'].includes(body?.decision) ? body.decision : fail(400, 'bad_decision');
      const no = typeof body?.candidate_no === 'string' ? body.candidate_no : fail(400, 'bad_candidate');
      const res = await db.prepare(`UPDATE hpho_entries SET aid=?,aid_at=? WHERE round_id=? AND candidate_no=? AND aid IN ('pending','approved','declined')`)
        .bind(decision, now(), r[1], no).run();
      if (!res.meta?.changes) fail(404, 'no_aid_request');
      return { ok: true, candidate_no: no, aid: decision };
    }
    fail(404, 'not_found');
  };
}

/* HPhO exam sessions, kept apart from registration (hpho.js). The exam is sat in the HaslaEdu desktop app's exam window;
   the web exam page there starts the session, sends the window's proctoring events with its own heartbeat, and ends it.
     POST /api/hpho/rounds/:id/exam/start    a registered candidate, from the start time until the end
     POST /api/hpho/rounds/:id/exam/events   up to 100 events per call; every call is a heartbeat
     POST /api/hpho/rounds/:id/exam/end      the candidate finishes early (the clock ends it otherwise)
     POST /api/hpho/rounds/:id/exam/snap     a webcam or screen snapshot (multipart: image, source, reason), kept in R2
     GET  /api/hpho/rounds/:id/exam/state    the caller's own session
     GET  /api/hpho/rounds/:id/exam/log?candidate=HP271-0042   admin: one candidate's session and events
   Like MIPT's online rounds, answer photos are uploaded during an hour after the exam (UPLOAD_MIN), not during it.
   Events are what the client reports, so a gap in the heartbeat is itself recorded (the server sees it). */

export const UPLOAD_MIN = 60;
export const SNAP_MAX_BYTES = 250 * 1024;
export const SNAP_SOURCES = ['webcam', 'screen'];
/* the snapshot's object key: round, candidate number (never the account), source, time and reason */
export const snapKey = (round, candidate, source, t, reason) => `hpho/${round}/${candidate}/${t}-${source}-${reason}.jpg`;
const isJpeg = b => b.length > 3 && b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff;
export const HEARTBEAT_GAP = 45;           /* seconds without a call before the next call records a gap */
export const EXAM_EVENTS = ['heartbeat', 'window_ready', 'focus_lost', 'focus_back', 'display_change', 'screen_locked', 'screen_unlocked',
  'suspend', 'resume', 'shortcut_blocked', 'window_close_attempt', 'network_lost', 'network_back', 'page_hidden', 'page_visible',
  'camera_started', 'camera_stopped', 'face_missing', 'faces_multiple', 'phone_seen', 'voice', 'process_new', 'process_list', 'clip_saved', 'snapshot_saved'];
const now = () => Math.floor(Date.now() / 1000);

export const HPHO_EXAM_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS hpho_sessions (round_id TEXT NOT NULL, user_id INTEGER NOT NULL, candidate_no TEXT NOT NULL,
    started_at INTEGER NOT NULL, ends_at INTEGER NOT NULL, last_beat INTEGER NOT NULL, ended_at INTEGER, client TEXT,
    events INTEGER NOT NULL DEFAULT 0, gaps INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (round_id, user_id))`,
  `CREATE TABLE IF NOT EXISTS hpho_events (round_id TEXT NOT NULL, user_id INTEGER NOT NULL, seq INTEGER NOT NULL,
    client_at INTEGER, at INTEGER NOT NULL, kind TEXT NOT NULL, detail TEXT, PRIMARY KEY (round_id, user_id, seq))`,
];
const ready = new WeakMap();
export function ensureHphoExam(db) {
  if (!ready.has(db)) { const p = db.batch(HPHO_EXAM_SCHEMA.map(s => db.prepare(s))).then(() => true); ready.set(db, p); p.catch(() => ready.delete(db)); }
  return ready.get(db);
}

/* what the client may report about itself: an app name and version, nothing else */
export function checkClient(c) {
  const app = c?.app === 'haslaedu-desktop' ? c.app : null, version = typeof c?.version === 'string' && /^\d+\.\d+\.\d+$/.test(c.version) ? c.version : null;
  return app && version ? `${app}/${version}` : null;
}
export function checkEvents(list) {
  if (!Array.isArray(list) || list.length > 100) return { error: 'bad_events' };
  const out = [];
  for (const e of list) {
    const seq = Number(e?.seq), t = Number(e?.t);
    if (!Number.isInteger(seq) || seq < 0 || seq > 1e7 || !EXAM_EVENTS.includes(e?.kind)) return { error: 'bad_events' };
    const detail = e.detail == null ? null : String(e.detail).replace(/[\u0000-\u001f]/g, ' ').slice(0, 200);
    out.push({ seq, client_at: Number.isInteger(t) ? t : null, kind: e.kind, detail });
  }
  return { events: out };
}
export const examWindow = r => ({ opens: r.start_at, ends: r.start_at + r.duration_min * 60, upload_until: r.start_at + r.duration_min * 60 + UPLOAD_MIN * 60 });

export function createHphoExamRouter({ HttpError, needUser, limit, isAdmin, scope = env => env.DB }) {
  const fail = (status, code) => { throw new HttpError(status, code); };
  return async function exam(p, m, body, me, env, url, req) {
    const r = /^\/api\/hpho\/rounds\/([^/]+)\/exam\/(start|events|end|state|log|snap)$/.exec(p);
    if (!r) return undefined;
    const [, id, action] = r, db = scope(env);
    needUser(me); await ensureHphoExam(db);
    const round = await db.prepare('SELECT * FROM hpho_rounds WHERE id=?').bind(id).first();
    if (!round || round.status === 'draft' && !isAdmin(me)) fail(404, 'round_not_found');   /* a draft: an admins' rehearsal */
    const w = examWindow(round), t = now();
    if (action === 'log' && m === 'GET') {
      if (!isAdmin(me)) fail(403, 'forbidden');
      const no = url?.searchParams?.get('candidate') || '';
      const s = await db.prepare('SELECT * FROM hpho_sessions WHERE round_id=? AND candidate_no=?').bind(id, no).first();
      if (!s) fail(404, 'no_session');
      const events = (await db.prepare('SELECT seq,client_at,at,kind,detail FROM hpho_events WHERE round_id=? AND user_id=? ORDER BY seq').bind(id, s.user_id).all()).results || [];
      return { session: { candidate_no: s.candidate_no, started_at: s.started_at, ends_at: s.ends_at, ended_at: s.ended_at, client: s.client, events: s.events, gaps: s.gaps }, events };
    }
    const session = await db.prepare('SELECT * FROM hpho_sessions WHERE round_id=? AND user_id=?').bind(id, me.id).first();
    if (action === 'state' && m === 'GET') return { window: w, now: t, session: session && { started_at: session.started_at, ends_at: session.ends_at, ended_at: session.ended_at, candidate_no: session.candidate_no } };
    if (m !== 'POST') fail(405, 'method_not_allowed');
    if (action === 'start') {
      const entry = await db.prepare('SELECT candidate_no FROM hpho_entries WHERE round_id=? AND user_id=?').bind(id, me.id).first();
      if (!entry) fail(403, 'not_registered');
      if (t < w.opens) fail(409, 'not_started');
      if (t >= w.ends) fail(409, 'exam_over');
      const client = checkClient(body?.client); if (!client) fail(400, 'desktop_app_required');
      if (session) return { ok: true, resumed: true, candidate_no: session.candidate_no, ends_at: session.ends_at, now: t };
      await db.prepare('INSERT INTO hpho_sessions(round_id,user_id,candidate_no,started_at,ends_at,last_beat,client) VALUES(?,?,?,?,?,?,?)')
        .bind(id, me.id, entry.candidate_no, t, w.ends, t, client).run();
      return { ok: true, candidate_no: entry.candidate_no, ends_at: w.ends, now: t };
    }
    if (!session) fail(409, 'no_session');
    if (action === 'events') {
      await limit(env, 'hpho-ev:' + me.id, 120, 600);
      if (t > w.ends + 600) fail(409, 'exam_over');
      const ok = checkEvents(body?.events); if (ok.error) fail(400, ok.error);
      const stmts = [];
      /* a silence the client did not report (the app killed, the network cut) is recorded here, by the server */
      const gap = t - session.last_beat > HEARTBEAT_GAP && !session.ended_at && session.last_beat < w.ends;
      for (const e of ok.events)
        stmts.push(db.prepare('INSERT OR IGNORE INTO hpho_events(round_id,user_id,seq,client_at,at,kind,detail) VALUES(?,?,?,?,?,?,?)').bind(id, me.id, e.seq, e.client_at, t, e.kind, e.detail));
      stmts.push(db.prepare('UPDATE hpho_sessions SET last_beat=?,events=events+?,gaps=gaps+? WHERE round_id=? AND user_id=?').bind(t, ok.events.length, gap ? 1 : 0, id, me.id));
      if (gap) stmts.push(db.prepare(`INSERT OR IGNORE INTO hpho_events(round_id,user_id,seq,client_at,at,kind,detail) VALUES(?,?,?,NULL,?,'heartbeat',?)`)
        .bind(id, me.id, -t, t, `server: no contact for ${t - session.last_beat}s`));
      await db.batch(stmts);
      return { ok: true, now: t, ends_at: session.ends_at, gap };
    }
    if (action === 'snap') {
      await limit(env, 'hpho-snap:' + me.id, 90, 600);
      if (t > w.ends + 600 || session.ended_at) fail(409, 'exam_over');
      const store = env.HPHO_SNAPS || env.LAB_PAGES; if (!store) fail(503, 'storage_unavailable');
      let form; try { form = await req.formData(); } catch { fail(400, 'bad_snapshot'); }
      const file = form.get('image'), source = SNAP_SOURCES.includes(form.get('source')) ? form.get('source') : null;
      const reason = /^[a-z_]{3,24}$/.test(String(form.get('reason') || '')) ? String(form.get('reason')) : null;
      if (!file || typeof file.arrayBuffer !== 'function' || !source || !reason || !['random', ...EXAM_EVENTS].includes(reason)) fail(400, 'bad_snapshot');
      if (file.size > SNAP_MAX_BYTES) fail(413, 'snapshot_too_large');
      const bytes = new Uint8Array(await file.arrayBuffer()); if (!isJpeg(bytes)) fail(415, 'snapshot_not_jpeg');
      const key = snapKey(id, session.candidate_no, source, t, reason);
      await store.put(key, bytes, { httpMetadata: { contentType: 'image/jpeg' }, customMetadata: { round: id, candidate: session.candidate_no, source, reason } });
      await db.prepare('UPDATE hpho_sessions SET last_beat=? WHERE round_id=? AND user_id=?').bind(t, id, me.id).run();
      return { ok: true };
    }
    if (action === 'end') {
      if (!session.ended_at) await db.prepare('UPDATE hpho_sessions SET ended_at=? WHERE round_id=? AND user_id=?').bind(Math.min(t, session.ends_at), id, me.id).run();
      return { ok: true, upload_until: w.upload_until };
    }
    fail(404, 'not_found');
  };
}

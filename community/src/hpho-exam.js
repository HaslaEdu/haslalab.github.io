/* HPhO exam seats, kept apart from registration (hpho.js). A round has a theory and an experiment exam, each on its own
   day, IsPhO-style (hpho.js roundTracks): the exam room opens an hour before the start, a candidate must be seated in the
   waiting room twenty minutes before it, the exam lasts five hours, and when the clock ends it the page moves to the
   submission page, where the answer photos are uploaded while the proctoring keeps recording (writing on the answer
   sheets after the end is cheating). The exam is sat in the HaslaEdu desktop app's exam window.
   Every route is /api/hpho/rounds/:id/exam/:track/<action>, track theory or experiment (without it: theory, the paths
   the first exam page used):
     GET  state                 the caller's own seat and the track's times
     POST checkin {client,lang} take a seat in the waiting room (from an hour before until 20 min before the start;
                                a seated candidate may come back until the end)
     POST lang {lang}           the language of the paper, until the start
     POST start {client}        the exam begins (from the start time); calling it again resumes after a disconnect
     POST events                up to 100 proctoring events per call; every call is a heartbeat
     POST snap                  a webcam or screen snapshot (multipart: image, source, reason), kept in R2
     POST earcheck              the technical check's ear photos (multipart: first, second): worn in or on the ears?
     POST voicecheck            the technical check's spoken sentence (multipart: audio WAV, lang): was it said?
     POST roomscan              the room scan's stills (multipart: front, left, right, back, ceiling, desk, under):
                                another person, a phone, another screen, a headset, notes?
     POST clip                  a five-minute recording segment (multipart: clip WebM, source webcam|screen|room)
     GET  docs                  which documents exist (general guide, writing sheet, answer sheet, paper) per language
     GET  doc?kind=&lang=       one PDF: the sheets from the room's opening, the paper from the start to the end, to a
                                seated candidate who has started
     POST answer                one answer page (multipart: image, page), from the end until the upload closes
     POST submit                the answers are in: the seat is done and the exam window may close
     admin:
     POST upload                a document (multipart: file PDF, kind, lang) — the organisers upload these themselves
     GET  seats                 every seat of the track, with disconnects, gaps and unverified checks flagged for review
     GET  monitor               live proctoring: every seat's latest webcam and screen photo, heartbeat and recent alerts
     GET  log?candidate=        one candidate's seat, events, snapshot and answer keys
     GET  media?key=            one stored snapshot or answer page
     POST verdict               {candidate, verdict: clear|review|cheating, note}: a person's decision after review
   Events are what the client reports, so a gap in the heartbeat is itself recorded (the server sees it). */
import { ensureHpho, roundTracks, TRACKS } from './hpho.js';

export const UPLOAD_MIN = 60;
export const SNAP_MAX_BYTES = 250 * 1024;
export const ANSWER_MAX_BYTES = 4 * 1024 * 1024;
export const ANSWER_MAX_PAGES = 80;
export const DOC_MAX_BYTES = 40 * 1024 * 1024;
export const VOICE_MAX_BYTES = 1024 * 1024;
export const SNAP_SOURCES = ['webcam', 'screen'];
export const CLIP_SOURCES = ['webcam', 'screen', 'room'];
export const CLIP_MAX_BYTES = 24 * 1024 * 1024;
export const SCAN_VIEWS = ['front', 'left', 'right', 'back', 'ceiling', 'desk', 'under'];
export const DOC_KINDS = ['guide', 'writing', 'answer', 'paper'];      /* general guide, 답안지 (writing sheet), answer sheet, the paper */
export const DOC_LANGS = ['ko', 'en'];
export const VERDICTS = ['clear', 'review', 'cheating'];
/* a seat is flagged for a person to look at the recording once the candidate dropped out this often */
export const REVIEW_RECONNECTS = 3, REVIEW_GAPS = 3;
/* the snapshot's object key: round, candidate number (never the account), source, time and reason */
export const snapKey = (round, candidate, source, t, reason) => `hpho/${round}/${candidate}/${t}-${source}-${reason}.jpg`;
export const docKey = (round, track, kind, lang) => `hpho-docs/${round}/${track}/${kind}-${lang}.pdf`;
export const clipKey = (round, track, candidate, t, source) => `hpho-rec/${round}/${track}/${candidate}/${t}-${source}.webm`;
export const answerKey = (round, track, candidate, page, ext) => `hpho-answers/${round}/${track}/${candidate}/${String(page).padStart(3, '0')}.${ext}`;
const isJpeg = b => b.length > 3 && b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff;
const isPng = b => b.length > 7 && b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47;
const isPdf = b => b.length > 4 && String.fromCharCode(...b.subarray(0, 5)) === '%PDF-';
const isWebm = b => b.length > 4 && b[0] === 0x1a && b[1] === 0x45 && b[2] === 0xdf && b[3] === 0xa3;
const isWav = b => b.length > 44 && String.fromCharCode(...b.subarray(0, 4)) === 'RIFF' && String.fromCharCode(...b.subarray(8, 12)) === 'WAVE';
export const HEARTBEAT_GAP = 45;           /* seconds without a call before the next call records a gap */
export const EXAM_EVENTS = ['heartbeat', 'window_ready', 'focus_lost', 'focus_back', 'display_change', 'screen_locked', 'screen_unlocked',
  'suspend', 'resume', 'shortcut_blocked', 'window_close_attempt', 'network_lost', 'network_back', 'page_hidden', 'page_visible',
  'camera_started', 'camera_stopped', 'face_missing', 'faces_multiple', 'phone_seen', 'voice', 'process_new', 'process_list', 'clip_saved', 'snapshot_saved',
  'face_check', 'mic_check', 'ear_check', 'checkin', 'reconnect', 'time_over', 'after_time', 'answer_page', 'submitted', 'paper_lang',
  'system_sound', 'room_scan', 'recording_started', 'recording_failed', 'displays', 'seated'];
export const EARCHECK_EARLY = 3600;        /* the ear and voice checks open an hour before the start, with the technical check */
const EAR_VERDICTS = ['clear', 'device', 'unclear'];
const EAR_PROMPT = n => `These are ${n} webcam photos of an exam candidate, taken during the technical check before an online physics exam${n === 3 ? ': the first faces the camera, in the second the head is turned to show one ear, in the third the other ear' : ': in the first the head is turned to show one ear, in the second the other ear'}.
Decide whether the candidate wears anything in, on or over the ears or head that could carry sound: earbuds, in-ear earphones, headphones, an over-ear or on-ear headset (also the headband over the head), a hearing device, or a wire leading to an ear. A headset seen in any photo counts, even if an ear is hidden.
Earrings, ear piercings, hair clips and glasses are not devices. Use "unclear" for a photo in which neither the ear nor anything over it can be seen (hair, angle, blur, too dark) or there is no person.
Reply with JSON only: {"verdicts":[${Array.from({ length: n }, () => '"clear"|"device"|"unclear"').join(',')}],"note":"at most 15 words, in English"}`;
const ROOM_PROMPT = `These are webcam stills from the room scan before an online physics exam, taken in order: ${SCAN_VIEWS.join(', ')} (the front of the room, the left and right walls, behind the candidate, the ceiling, the desk top, under the desk).
Look for: another person (or part of one); a phone, smartwatch or tablet; a screen other than the one computer the candidate sits the exam on (a second monitor, a laptop, a TV showing text); earphones or a headset; books, notes or written papers (blank or printed exam answer sheets, a pen, a calculator and a drink are allowed).
Reply with JSON only: {"person":bool,"phone":bool,"screen":bool,"headset":bool,"notes":bool,"unclear":bool,"note":"at most 20 words, in English"} ("unclear": the stills are too dark or blurred to judge).`;
/* the sentence the candidate reads aloud in the microphone check, in the language of the page */
export const VOICE_SENTENCE = { ko: '저는 HPhO에 정직하게 응시하겠습니다.', en: 'I will sit HPhO honestly.' };
const voicePrompt = lang => `This is a microphone test recorded before an online exam. The candidate was asked to read this sentence aloud: "${VOICE_SENTENCE[lang]}".
Listen to the recording. "said" is true only if a human voice clearly reads that sentence, or very nearly that sentence (small slips are fine). It is false for silence, noise, music, tapping, a shout or a word that is not the sentence, humming, or a different sentence.
Reply with JSON only: {"said":true|false,"heard":"what you heard, at most 12 words"}`;
const b64 = bytes => { let s = ''; for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000)); return btoa(s); };
async function gemini(env, parts, maxOutputTokens = 200) {
  const model = env.HPHO_VISION_MODEL || env.GEMINI_MODEL || 'gemini-flash-lite-latest';
  const r = await fetch(`${env.GEMINI_BASE || 'https://generativelanguage.googleapis.com/v1beta/models'}/${model}:generateContent`, {
    method: 'POST', signal: AbortSignal.timeout(30000), headers: { 'Content-Type': 'application/json', 'x-goog-api-key': env.GEMINI_API_KEY },
    body: JSON.stringify({ contents: [{ role: 'user', parts }], generationConfig: { responseMimeType: 'application/json', temperature: 0, maxOutputTokens } }) });
  if (!r.ok) return null;
  const j = await r.json(), raw = (j.candidates?.[0]?.content?.parts || []).map(x => x.text || '').join('');
  return JSON.parse(String(raw).trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, ''));
}
/* the default ear model: Gemini, with the two photos inline. { unavailable: true } when it cannot answer, so the check never
   blocks a candidate because the model is down (the photos are kept and the result is recorded either way) */
export async function geminiEarVision(env, ...shots) {
  if (!env.GEMINI_API_KEY) return { unavailable: true };
  try { return earVerdict(await gemini(env, [...shots.map(b => ({ inline_data: { mime_type: 'image/jpeg', data: b64(b) } })), { text: EAR_PROMPT(shots.length) }]), shots.length); }
  catch { return { unavailable: true }; }
}
const clean = (v, n) => typeof v === 'string' ? v.replace(/[\u0000-\u001f]/g, ' ').slice(0, n) : '';
/* the model's answer, reduced to one verdict per photo and a short note; the old two-field form is still read */
export function earVerdict(v, n = 2) {
  const list = Array.isArray(v?.verdicts) ? v.verdicts : [v?.first, v?.second];
  if (!v || list.length !== n || !list.every(x => EAR_VERDICTS.includes(x))) return { unavailable: true };
  return { verdicts: list, note: clean(v.note, 120) };
}
/* the room scan's stills, judged together */
export async function geminiRoomScan(env, stills) {
  if (!env.GEMINI_API_KEY) return { unavailable: true };
  try { return roomVerdict(await gemini(env, [...stills.map(b => ({ inline_data: { mime_type: 'image/jpeg', data: b64(b) } })), { text: ROOM_PROMPT }])); }
  catch { return { unavailable: true }; }
}
export const ROOM_BLOCK = ['person', 'phone', 'screen', 'headset'];      /* these stop the candidate; notes go to review */
export function roomVerdict(v) {
  if (!v || ![...ROOM_BLOCK, 'notes', 'unclear'].every(k => typeof v[k] === 'boolean')) return { unavailable: true };
  return { found: [...ROOM_BLOCK, 'notes'].filter(k => v[k]), unclear: v.unclear, note: clean(v.note, 160) };
}
/* the default voice model: Gemini listens to the WAV and says whether the sentence was read. A level meter alone let a
   shout, a cough or a tap on the desk pass; this hears the words. Unavailable: the page asks again; a seat whose checks
   could not be verified is flagged for review (checkNote). */
export async function geminiVoiceCheck(env, wav, lang) {
  if (!env.GEMINI_API_KEY) return { unavailable: true };
  try { return voiceVerdict(await gemini(env, [{ inline_data: { mime_type: 'audio/wav', data: b64(wav) } }, { text: voicePrompt(lang) }])); }
  catch { return { unavailable: true }; }
}
export function voiceVerdict(v) {
  if (!v || typeof v.said !== 'boolean') return { unavailable: true };
  return { said: v.said, heard: clean(v.heard, 120) };
}
const now = () => Math.floor(Date.now() / 1000);

export const HPHO_EXAM_SCHEMA = [
  /* the first exam page's sessions (one per round); kept for its records, no longer written */
  `CREATE TABLE IF NOT EXISTS hpho_sessions (round_id TEXT NOT NULL, user_id INTEGER NOT NULL, candidate_no TEXT NOT NULL,
    started_at INTEGER NOT NULL, ends_at INTEGER NOT NULL, last_beat INTEGER NOT NULL, ended_at INTEGER, client TEXT,
    events INTEGER NOT NULL DEFAULT 0, gaps INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (round_id, user_id))`,
  `CREATE TABLE IF NOT EXISTS hpho_seats (round_id TEXT NOT NULL, user_id INTEGER NOT NULL, track TEXT NOT NULL, candidate_no TEXT NOT NULL,
    checked_in_at INTEGER NOT NULL, started_at INTEGER, ends_at INTEGER NOT NULL, last_beat INTEGER NOT NULL, submitted_at INTEGER,
    paper_lang TEXT NOT NULL DEFAULT 'ko', client TEXT, events INTEGER NOT NULL DEFAULT 0, gaps INTEGER NOT NULL DEFAULT 0,
    reconnects INTEGER NOT NULL DEFAULT 0, pages INTEGER NOT NULL DEFAULT 0, verdict TEXT, verdict_note TEXT, verdict_at INTEGER,
    check_note TEXT, last_webcam TEXT, last_screen TEXT, clips INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (round_id, user_id, track))`,
  `CREATE UNIQUE INDEX IF NOT EXISTS hpho_seats_no ON hpho_seats(round_id, track, candidate_no)`,
  `CREATE TABLE IF NOT EXISTS hpho_events (round_id TEXT NOT NULL, user_id INTEGER NOT NULL, seq INTEGER NOT NULL,
    client_at INTEGER, at INTEGER NOT NULL, kind TEXT NOT NULL, detail TEXT, PRIMARY KEY (round_id, user_id, seq))`,
];
const EXAM_COLUMNS = [`ALTER TABLE hpho_events ADD COLUMN track TEXT`];
const ready = new WeakMap();
export function ensureHphoExam(db) {
  if (!ready.has(db)) {
    const p = Promise.all([ensureHpho(db), db.batch(HPHO_EXAM_SCHEMA.map(s => db.prepare(s)))]).then(async () => {
      for (const sql of EXAM_COLUMNS) try { await db.prepare(sql).run(); } catch (e) { if (!/duplicate column/i.test(String(e?.message || e))) throw e; }
      return true;
    });
    ready.set(db, p); p.catch(() => ready.delete(db));
  }
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
    if (!Number.isInteger(seq) || seq < 0 || seq > 1e9 || !EXAM_EVENTS.includes(e?.kind)) return { error: 'bad_events' };
    const detail = e.detail == null ? null : String(e.detail).replace(/[\u0000-\u001f]/g, ' ').slice(0, 200);
    out.push({ seq, client_at: Number.isInteger(t) ? t : null, kind: e.kind, detail });
  }
  return { events: out };
}
/* one exam's times: the room opens, seating closes, the start, the end, and the end of the answer upload */
export function examWindow(round, track = 'theory') {
  const x = roundTracks(round).find(v => v.track === track);
  if (!x) return null;
  return { track, opens: x.opens, seat_by: x.seat_by, start_at: x.start_at, ends: x.ends, upload_until: x.ends + UPLOAD_MIN * 60, duration_min: x.duration_min };
}
/* a seat flagged for review: dropped out or went silent often enough that a person should look at the recording */
export const needsReview = s => (s.reconnects || 0) >= REVIEW_RECONNECTS || (s.gaps || 0) >= REVIEW_GAPS || !!s.check_note;
/* what the technical checks could not confirm, from the server's own records of them (the latest of each before t):
   an ear check, a voice check or a room scan that was not clear (the model was down, or it saw something) */
export function checkNote(events) {
  const last = k => events.filter(e => e.kind === k).sort((a, b) => b.at - a.at || a.seq - b.seq)[0];
  const out = [];
  for (const [kind, ok, name] of [['ear_check', /^clear/, 'ears'], ['mic_check', /^said/, 'voice'], ['room_scan', /^clear/, 'room']]) {
    const e = last(kind); if (!e) { out.push(`${name}: not done`); continue; }
    if (!ok.test(e.detail || '')) out.push(`${name}: ${String(e.detail || '').slice(0, 60)}`);
  }
  return out.join('; ') || null;
}
/* the seat's own ends_at is what the exam's end was at check-in; the page is told the round's current times (window) */
const seatView = s => s && { candidate_no: s.candidate_no, checked_in_at: s.checked_in_at, started_at: s.started_at, ends_at: s.ends_at,
  submitted_at: s.submitted_at, paper_lang: s.paper_lang, reconnects: s.reconnects, pages: s.pages };
const adminSeat = s => ({ ...seatView(s), client: s.client, events: s.events, gaps: s.gaps, last_beat: s.last_beat, clips: s.clips,
  check_note: s.check_note, verdict: s.verdict, verdict_note: s.verdict_note, verdict_at: s.verdict_at, review: needsReview(s) });
/* events a proctor watching live wants to see */
export const ALERTS = ['focus_lost', 'display_change', 'screen_locked', 'suspend', 'shortcut_blocked', 'window_close_attempt', 'network_lost', 'page_hidden',
  'camera_stopped', 'face_missing', 'faces_multiple', 'phone_seen', 'voice', 'system_sound', 'reconnect', 'recording_failed', 'after_time'];

export function createHphoExamRouter({ HttpError, needUser, limit, isAdmin, scope = env => env.DB, earVision = geminiEarVision, voiceCheck = geminiVoiceCheck, roomScan = geminiRoomScan }) {
  const fail = (status, code) => { throw new HttpError(status, code); };
  const form = async req => { try { return await req.formData(); } catch { fail(400, 'bad_upload'); } };
  const bytesOf = async (file, max, tooLarge = 'upload_too_large') => {
    if (!file || typeof file.arrayBuffer !== 'function') fail(400, 'bad_upload');
    if (file.size > max) fail(413, tooLarge);
    return new Uint8Array(await file.arrayBuffer());
  };
  return async function exam(p, m, body, me, env, url, req) {
    const r = /^\/api\/hpho\/rounds\/([^/]+)\/exam\/(?:(theory|experiment)\/)?(state|checkin|lang|start|events|snap|earcheck|voicecheck|roomscan|clip|docs|doc|answer|submit|upload|seats|monitor|log|media|verdict)$/.exec(p);
    if (!r) return undefined;
    const [, id, track = 'theory', action] = r, db = scope(env), admin = isAdmin(me);
    needUser(me); await ensureHphoExam(db);
    const round = await db.prepare('SELECT * FROM hpho_rounds WHERE id=?').bind(id).first();
    if (!round || round.status === 'draft' && !admin) fail(404, 'round_not_found');   /* a draft: an admins' rehearsal */
    const w = examWindow(round, track); if (!w) fail(404, 'no_such_exam');
    const t = now(), store = env.HPHO_SNAPS || env.LAB_PAGES;
    const q = k => url?.searchParams?.get(k) || '';

    /* ── the organisers ── */
    if (['upload', 'seats', 'monitor', 'log', 'media', 'verdict'].includes(action)) {
      if (!admin) fail(403, 'forbidden');
      if (action === 'upload' && m === 'POST') {
        if (!store) fail(503, 'storage_unavailable');
        const f = await form(req), kind = String(f.get('kind') || ''), lang = String(f.get('lang') || '');
        if (!DOC_KINDS.includes(kind) || !DOC_LANGS.includes(lang)) fail(400, 'bad_doc');
        const bytes = await bytesOf(f.get('file'), DOC_MAX_BYTES); if (!isPdf(bytes)) fail(415, 'doc_not_pdf');
        await store.put(docKey(id, track, kind, lang), bytes, { httpMetadata: { contentType: 'application/pdf' }, customMetadata: { round: id, track, kind, lang, at: String(t) } });
        return { ok: true, kind, lang, size: bytes.length };
      }
      if (action === 'seats' && m === 'GET') {
        const rows = (await db.prepare('SELECT * FROM hpho_seats WHERE round_id=? AND track=? ORDER BY candidate_no').bind(id, track).all()).results || [];
        return { window: w, now: t, seats: rows.map(adminSeat), review: rows.filter(needsReview).length };
      }
      if (action === 'monitor' && m === 'GET') {
        const rows = (await db.prepare('SELECT * FROM hpho_seats WHERE round_id=? AND track=? ORDER BY candidate_no').bind(id, track).all()).results || [];
        const alerts = (await db.prepare(`SELECT user_id,at,kind,detail FROM hpho_events WHERE round_id=? AND (track=? OR track IS NULL) AND at>=? AND kind IN (${ALERTS.map(() => '?').join(',')}) ORDER BY at DESC LIMIT 500`)
          .bind(id, track, t - 900, ...ALERTS).all()).results || [];
        return { window: w, now: t, seats: rows.map(s => ({ ...adminSeat(s), last_webcam: s.last_webcam, last_screen: s.last_screen, online: t - s.last_beat < 45 && !s.submitted_at,
          alerts: alerts.filter(a => a.user_id === s.user_id).slice(0, 6).map(({ at, kind, detail }) => ({ at, kind, detail })) })) };
      }
      if (action === 'log' && m === 'GET') {
        const s = await db.prepare('SELECT * FROM hpho_seats WHERE round_id=? AND track=? AND candidate_no=?').bind(id, track, q('candidate')).first();
        if (!s) fail(404, 'no_session');
        const events = (await db.prepare('SELECT seq,client_at,at,kind,detail FROM hpho_events WHERE round_id=? AND user_id=? AND (track=? OR track IS NULL) ORDER BY at,seq').bind(id, s.user_id, track).all()).results || [];
        const keys = async prefix => { if (!store?.list) return []; const out = []; let cursor;
          do { const l = await store.list({ prefix, cursor, limit: 1000 }); out.push(...l.objects.map(o => o.key)); cursor = l.truncated ? l.cursor : null; } while (cursor && out.length < 5000);
          return out; };
        /* the snapshots of this exam: taken from an hour before its start until its upload closed */
        const snaps = (await keys(`hpho/${id}/${s.candidate_no}/`)).filter(k => { const at = Number(/\/(\d+)-[a-z]+-[a-z_]+\.\w+$/.exec(k)?.[1]); return at >= w.opens && at <= w.upload_until + 600; });
        return { seat: adminSeat(s), window: w, events, snaps, answers: await keys(`hpho-answers/${id}/${track}/${s.candidate_no}/`),
          clips: await keys(`hpho-rec/${id}/${track}/${s.candidate_no}/`) };
      }
      if (action === 'media' && m === 'GET') {
        const key = q('key');
        if (!(key.startsWith(`hpho/${id}/`) || key.startsWith(`hpho-answers/${id}/`) || key.startsWith(`hpho-rec/${id}/`)) || key.includes('..') || !store) fail(404, 'not_found');
        const o = await store.get(key); if (!o) fail(404, 'not_found');
        return new Response(o.body, { headers: { 'Content-Type': o.httpMetadata?.contentType || 'image/jpeg', 'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff' } });
      }
      if (action === 'verdict' && m === 'POST') {
        const verdict = VERDICTS.includes(body?.verdict) ? body.verdict : fail(400, 'bad_verdict');
        const note = typeof body?.note === 'string' ? body.note.replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, 500) : '';
        const res = await db.prepare('UPDATE hpho_seats SET verdict=?,verdict_note=?,verdict_at=? WHERE round_id=? AND track=? AND candidate_no=?')
          .bind(verdict, note, t, id, track, String(body?.candidate || '')).run();
        if (!res.meta?.changes) fail(404, 'no_session');
        return { ok: true, verdict };
      }
      fail(405, 'method_not_allowed');
    }

    const entry = await db.prepare('SELECT candidate_no FROM hpho_entries WHERE round_id=? AND user_id=?').bind(id, me.id).first();
    const seat = await db.prepare('SELECT * FROM hpho_seats WHERE round_id=? AND user_id=? AND track=?').bind(id, me.id, track).first();
    const lastSeq = async () => (await db.prepare('SELECT MAX(seq) AS s FROM hpho_events WHERE round_id=? AND user_id=? AND seq>=0').bind(id, me.id).first())?.s || 0;
    const serverEvent = (kind, detail, mark = 0) => db.prepare(`INSERT OR IGNORE INTO hpho_events(round_id,user_id,seq,client_at,at,kind,detail,track) VALUES(?,?,?,NULL,?,?,?,?)`)
      .bind(id, me.id, -(mark + t), t, kind, String(detail || '').slice(0, 200), track);

    if (action === 'state' && m === 'GET') return { window: w, now: t, registered: !!entry, session: seatView(seat), seq: seat ? await lastSeq() : 0 };

    if (action === 'docs' && m === 'GET') {
      if (!entry && !admin) fail(403, 'not_registered');
      if (t < w.opens && !admin) return { docs: [], now: t };
      const docs = [];
      for (const kind of DOC_KINDS) for (const lang of DOC_LANGS) {
        const o = store ? await store.head(docKey(id, track, kind, lang)) : null;
        if (o) docs.push({ kind, lang, size: o.size });
      }
      return { docs, now: t };
    }
    if (action === 'doc' && m === 'GET') {
      const kind = q('kind'), lang = q('lang');
      if (!DOC_KINDS.includes(kind) || !DOC_LANGS.includes(lang)) fail(400, 'bad_doc');
      if (!admin) {
        if (!entry) fail(403, 'not_registered');
        if (t < w.opens) fail(409, 'not_open');
        /* the paper: only on the exam's own clock, to a candidate who is sitting it; once the time is over it is gone */
        if (kind === 'paper' && (!seat?.started_at || t < w.start_at || t >= w.ends)) fail(409, t >= w.ends ? 'exam_over' : 'not_started');
      }
      const o = store ? await store.get(docKey(id, track, kind, lang)) : null; if (!o) fail(404, 'no_doc');
      return new Response(o.body, { headers: { 'Content-Type': 'application/pdf', 'Cache-Control': 'private, no-store', 'Content-Disposition': 'inline', 'X-Content-Type-Options': 'nosniff' } });
    }
    if (m !== 'POST') fail(405, 'method_not_allowed');
    if (!entry) fail(403, 'not_registered');

    if (['earcheck', 'voicecheck', 'roomscan'].includes(action)) {
      if (t < w.start_at - EARCHECK_EARLY || t >= w.ends) fail(409, 'check_closed');
      await limit(env, `hpho-${action}:` + me.id, 8, 600);
      const f = await form(req);
      if (action === 'voicecheck') {
        const lang = DOC_LANGS.includes(f.get('lang')) ? f.get('lang') : 'ko';
        const wav = await bytesOf(f.get('audio'), VOICE_MAX_BYTES, 'audio_too_large'); if (!isWav(wav)) fail(415, 'audio_not_wav');
        if (store) await store.put(`hpho/${id}/${entry.candidate_no}/${t}-mic-voice_check.wav`, wav, { httpMetadata: { contentType: 'audio/wav' }, customMetadata: { round: id, candidate: entry.candidate_no, source: 'mic', reason: 'voice_check' } });
        const v = await voiceCheck(env, wav, lang);
        await serverEvent('mic_check', v.unavailable ? 'model unavailable' : `${v.said ? 'said' : 'not said'}${v.heard ? ' · heard: ' + v.heard : ''}`, 5e9).run();
        return v.unavailable ? { ok: true, unavailable: true } : { ok: true, said: v.said };
      }
      const still = async name => { const bytes = await bytesOf(f.get(name), SNAP_MAX_BYTES * 2, 'snapshot_too_large'); if (!isJpeg(bytes)) fail(415, 'snapshot_not_jpeg'); return bytes; };
      const keep = (bytes, name, reason) => store?.put(`hpho/${id}/${entry.candidate_no}/${t}-${reason === 'room_scan' ? 'roomscan' : 'earcheck'}-${name}.jpg`, bytes, { httpMetadata: { contentType: 'image/jpeg' }, customMetadata: { round: id, candidate: entry.candidate_no, source: 'webcam', reason } });
      if (action === 'roomscan') {
        const stills = [];
        for (const v of SCAN_VIEWS) { const b = await still(v); stills.push(b); await keep(b, v, 'room_scan'); }
        const v = await roomScan(env, stills);
        const blocked = v.unavailable ? [] : v.found.filter(k => ROOM_BLOCK.includes(k));
        await serverEvent('room_scan', v.unavailable ? 'model unavailable' : v.found.length || v.unclear ? `flag: ${[...v.found, ...(v.unclear ? ['unclear'] : [])].join(',')}${v.note ? ' · ' + v.note : ''}` : `clear${v.note ? ' · ' + v.note : ''}`, 3e9).run();
        return v.unavailable ? { ok: true, unavailable: true } : { ok: true, found: v.found, blocked, unclear: v.unclear };
      }
      const names = f.get('front') ? ['front', 'first', 'second'] : ['first', 'second'], shots = [];
      for (const n of names) { const b = await still(n); shots.push(b); await keep(b, n, 'ear_check'); }
      const v = await earVision(env, ...shots);
      const verdict = v.unavailable ? null : v.verdicts.includes('device') ? 'device' : v.verdicts.includes('unclear') ? 'unclear' : 'clear';
      /* recorded by the server (seq below every client seq and every server gap mark) */
      await serverEvent('ear_check', v.unavailable ? 'model unavailable' : `${verdict} (${v.verdicts.join(',')})${v.note ? ' · ' + v.note : ''}`, 4e9).run();
      return v.unavailable ? { ok: true, unavailable: true } : { ok: true, verdict, verdicts: v.verdicts };
    }

    /* the server's own records of the checks (negative seq) since the room opened */
    const noteNow = async () => checkNote((await db.prepare(`SELECT seq,at,kind,detail FROM hpho_events WHERE round_id=? AND user_id=? AND seq<0 AND at>=? AND kind IN ('ear_check','mic_check','room_scan')`)
      .bind(id, me.id, w.start_at - EARCHECK_EARLY).all()).results || []);
    if (action === 'checkin') {
      if (t < w.opens) fail(409, 'not_open');
      if (t >= w.ends) fail(409, 'exam_over');
      const client = checkClient(body?.client); if (!client) fail(400, 'desktop_app_required');
      const lang = DOC_LANGS.includes(body?.lang) ? body.lang : 'ko';
      if (seat) {
        /* back after leaving the room, or after a disconnect during the exam (counted: a person reviews frequent ones) */
        /* every return goes through the check again: the room scan of this return joins the seat's note */
        const note = await noteNow();
        await db.batch([db.prepare(`UPDATE hpho_seats SET reconnects=reconnects+?,client=?,check_note=? WHERE round_id=? AND user_id=? AND track=?`).bind(seat.started_at ? 1 : 0, client, note, id, me.id, track),
          ...(seat.started_at ? [serverEvent('reconnect', `checkin again · ${client}`, 8e9)] : [])]);
        const s = await db.prepare('SELECT * FROM hpho_seats WHERE round_id=? AND user_id=? AND track=?').bind(id, me.id, track).first();
        return { ok: true, resumed: true, session: seatView(s), window: w, now: t, seq: await lastSeq() };
      }
      /* seated twenty minutes before the start, or not at all (admins rehearsing a draft are let in late) */
      if (t >= w.seat_by && !(admin && round.status === 'draft')) fail(409, 'seating_closed');
      await db.batch([db.prepare('INSERT INTO hpho_seats(round_id,user_id,track,candidate_no,checked_in_at,ends_at,last_beat,paper_lang,client,check_note) VALUES(?,?,?,?,?,?,?,?,?,?)')
        .bind(id, me.id, track, entry.candidate_no, t, w.ends, t, lang, client, await noteNow()), serverEvent('checkin', client, 6e9)]);
      const s = await db.prepare('SELECT * FROM hpho_seats WHERE round_id=? AND user_id=? AND track=?').bind(id, me.id, track).first();
      return { ok: true, session: seatView(s), window: w, now: t, seq: await lastSeq() };
    }
    if (!seat) fail(409, 'not_seated');
    if (action === 'lang') {
      if (seat.started_at || t >= w.start_at) fail(409, 'exam_started');
      const lang = DOC_LANGS.includes(body?.lang) ? body.lang : fail(400, 'bad_lang');
      await db.prepare('UPDATE hpho_seats SET paper_lang=? WHERE round_id=? AND user_id=? AND track=?').bind(lang, id, me.id, track).run();
      return { ok: true, paper_lang: lang };
    }
    if (action === 'start') {
      if (t < w.start_at) fail(409, 'not_started');
      if (t >= w.ends) fail(409, 'exam_over');
      const client = checkClient(body?.client); if (!client) fail(400, 'desktop_app_required');
      if (seat.started_at) return { ok: true, resumed: true, candidate_no: seat.candidate_no, ends_at: w.ends, paper_lang: seat.paper_lang, now: t, seq: await lastSeq() };
      await db.prepare('UPDATE hpho_seats SET started_at=?,last_beat=?,client=? WHERE round_id=? AND user_id=? AND track=?').bind(t, t, client, id, me.id, track).run();
      return { ok: true, candidate_no: seat.candidate_no, ends_at: w.ends, paper_lang: seat.paper_lang, now: t, seq: await lastSeq() };
    }
    if (action === 'events') {
      await limit(env, 'hpho-ev:' + me.id, 120, 600);
      if (t > w.upload_until + 600) fail(409, 'exam_over');
      const ok = checkEvents(body?.events); if (ok.error) fail(400, ok.error);
      const stmts = [];
      /* a silence the client did not report (the app killed, the network cut) is recorded here, by the server */
      const gap = !!seat.started_at && t - seat.last_beat > HEARTBEAT_GAP && !seat.submitted_at && seat.last_beat < w.upload_until;
      for (const e of ok.events)
        stmts.push(db.prepare('INSERT OR IGNORE INTO hpho_events(round_id,user_id,seq,client_at,at,kind,detail,track) VALUES(?,?,?,?,?,?,?,?)').bind(id, me.id, e.seq, e.client_at, t, e.kind, e.detail, track));
      stmts.push(db.prepare('UPDATE hpho_seats SET last_beat=?,events=events+?,gaps=gaps+? WHERE round_id=? AND user_id=? AND track=?').bind(t, ok.events.length, gap ? 1 : 0, id, me.id, track));
      if (gap) stmts.push(serverEvent('heartbeat', `server: no contact for ${t - seat.last_beat}s`));
      await db.batch(stmts);
      return { ok: true, now: t, ends_at: w.ends, upload_until: w.upload_until, gap };
    }
    if (action === 'snap') {
      await limit(env, 'hpho-snap:' + me.id, 120, 600);
      if (t > w.upload_until + 600 || seat.submitted_at) fail(409, 'exam_over');
      if (!store) fail(503, 'storage_unavailable');
      const f = await form(req), source = SNAP_SOURCES.includes(f.get('source')) ? f.get('source') : null;
      const reason = /^[a-z_]{3,24}$/.test(String(f.get('reason') || '')) ? String(f.get('reason')) : null;
      if (!source || !reason || !['random', ...EXAM_EVENTS].includes(reason)) fail(400, 'bad_snapshot');
      const bytes = await bytesOf(f.get('image'), SNAP_MAX_BYTES, 'snapshot_too_large'); if (!isJpeg(bytes)) fail(415, 'snapshot_not_jpeg');
      const key = snapKey(id, seat.candidate_no, source, t, reason);
      await store.put(key, bytes, { httpMetadata: { contentType: 'image/jpeg' }, customMetadata: { round: id, track, candidate: seat.candidate_no, source, reason } });
      await db.prepare(`UPDATE hpho_seats SET last_beat=?,${source === 'screen' ? 'last_screen' : 'last_webcam'}=? WHERE round_id=? AND user_id=? AND track=?`).bind(t, key, id, me.id, track).run();
      return { ok: true };
    }
    if (action === 'clip') {
      /* the recording, in five-minute WebM segments: from the seat in the waiting room until the answers are submitted */
      await limit(env, 'hpho-clip:' + me.id, 40, 600);
      if (t > w.upload_until + 600 || seat.submitted_at && t > seat.submitted_at + 120) fail(409, 'exam_over');
      if (!store) fail(503, 'storage_unavailable');
      const f = await form(req), source = CLIP_SOURCES.includes(f.get('source')) ? f.get('source') : fail(400, 'bad_clip');
      const bytes = await bytesOf(f.get('clip'), CLIP_MAX_BYTES, 'clip_too_large'); if (!isWebm(bytes)) fail(415, 'clip_not_webm');
      await store.put(clipKey(id, track, seat.candidate_no, t, source), bytes, { httpMetadata: { contentType: 'video/webm' }, customMetadata: { round: id, track, candidate: seat.candidate_no, source } });
      await db.prepare('UPDATE hpho_seats SET clips=clips+1,last_beat=? WHERE round_id=? AND user_id=? AND track=?').bind(t, id, me.id, track).run();
      return { ok: true };
    }
    if (action === 'answer') {
      /* the answers go up after the time is over, never during the exam */
      if (t < w.ends) fail(409, 'not_over');
      if (t > w.upload_until || seat.submitted_at) fail(409, 'upload_closed');
      if (!store) fail(503, 'storage_unavailable');
      await limit(env, 'hpho-ans:' + me.id, 200, 3600);
      const f = await form(req), page = Number(f.get('page'));
      if (!Number.isInteger(page) || page < 1 || page > ANSWER_MAX_PAGES) fail(400, 'bad_page');
      const bytes = await bytesOf(f.get('image'), ANSWER_MAX_BYTES), ext = isJpeg(bytes) ? 'jpg' : isPng(bytes) ? 'png' : fail(415, 'answer_not_image');
      await store.put(answerKey(id, track, seat.candidate_no, page, ext), bytes, { httpMetadata: { contentType: ext === 'jpg' ? 'image/jpeg' : 'image/png' }, customMetadata: { round: id, track, candidate: seat.candidate_no, page: String(page) } });
      await db.prepare('UPDATE hpho_seats SET pages=MAX(pages,?),last_beat=? WHERE round_id=? AND user_id=? AND track=?').bind(page, t, id, me.id, track).run();
      return { ok: true, page };
    }
    if (action === 'submit') {
      if (t < w.ends) fail(409, 'not_over');
      if (!seat.submitted_at) await db.batch([db.prepare('UPDATE hpho_seats SET submitted_at=? WHERE round_id=? AND user_id=? AND track=?').bind(t, id, me.id, track), serverEvent('submitted', `${seat.pages} page(s)`, 7e9)]);
      return { ok: true, pages: seat.pages };
    }
    fail(404, 'not_found');
  };
}

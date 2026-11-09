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
     POST glasscheck            glasses that might be smart, held to the camera (multipart: front, inside): camera, speaker, light?
     POST roomscan              the room scan's stills (multipart: front, left, right, back, ceiling, desk, under):
                                another person, a phone, another screen, a headset, notes?
     POST keep                  at the end: is this seat flagged? only then the recordings come to the server
     POST phone                 pair the candidate's phone (the second camera, Monito-style): a one-time code for the QR
     GET  phone                 the phone's state: connected, the room scan view by view, its placement
   The phone, by the code in the QR (no sign-in on the phone), at /api/hpho/phone/:code/<action>:
     GET  state                 round, track, candidate number, what is left to do
     POST scan                  one view of the room scan (multipart: view, frames f0..f7 taken while the phone turns
                                slowly): the model looks for forbidden things in that view
     POST place                 a photo from where the phone will stand: are the candidate, hands, desk and screen seen?
     POST snap                  a proctoring photo from the phone (multipart: image, reason), every 15 s
     POST beat                  the phone is still there
     POST clip                  a five-minute recording segment (multipart: clip WebM, source webcam|screen|room),
                                accepted only from a flagged seat
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
     POST retain                keep or delete the recordings now (the cron does it an hour after the upload closes)
   What is stored: the recordings (webcam with microphone, screen with the computer's sound, the room scans) stay on the
   candidate's computer during the exam and come to the server only from a seat the detectors flagged (suspicion(),
   asked through keep at the end); the server refuses them from any other seat. The proctoring photos of a seat that
   was not flagged are deleted an hour after its upload closed (hphoRetainTick, every 15 minutes from the cron), except
   the webcam photos after the time was over (writing then is cheating). Answers, check photos and events stay.
   Events are what the client reports, so a gap in the heartbeat is itself recorded (the server sees it). */
import { ensureHpho, roundTracks, TRACKS } from './hpho.js';

export const UPLOAD_MIN = 60;
export const SNAP_MAX_BYTES = 250 * 1024;          /* a webcam still of the checks (640 px) */
/* proctoring photos: the webcam at 640 px, the screen at its own resolution (up to 1920 px) so its text stays readable */
export const SNAP_SOURCE_MAX = { webcam: 400 * 1024, screen: 1536 * 1024, phone: 600 * 1024 };
export const ANSWER_MAX_BYTES = 4 * 1024 * 1024;
export const ANSWER_MAX_PAGES = 80;
export const DOC_MAX_BYTES = 40 * 1024 * 1024;
export const VOICE_MAX_BYTES = 1024 * 1024;
export const SNAP_SOURCES = ['webcam', 'screen'];
export const CLIP_SOURCES = ['webcam', 'screen', 'room'];
/* the phone's room scan, as Monito and MIPT's online rounds do it, in four moves that do not overlap: one slow turn of
   the whole room at eye height, the desk top with the monitor's sides and back, under the desk, the ceiling */
export const PHONE_VIEWS = ['room', 'desk', 'under', 'ceiling'];
/* six frames a view, each at most 768 px (one image tile for the model: the least it is billed for), after the phone
   itself dropped blurred or dark ones: a view costs about 1,600 input tokens */
export const PHONE_FRAMES = 6, PHONE_ONLINE = 40;
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
const isWebp = b => b.length > 12 && String.fromCharCode(...b.subarray(0, 4)) === 'RIFF' && String.fromCharCode(...b.subarray(8, 12)) === 'WEBP';
const isPng = b => b.length > 7 && b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47;
const isPdf = b => b.length > 4 && String.fromCharCode(...b.subarray(0, 5)) === '%PDF-';
const isWebm = b => b.length > 4 && b[0] === 0x1a && b[1] === 0x45 && b[2] === 0xdf && b[3] === 0xa3;
const isWav = b => b.length > 44 && String.fromCharCode(...b.subarray(0, 4)) === 'RIFF' && String.fromCharCode(...b.subarray(8, 12)) === 'WAVE';
export const HEARTBEAT_GAP = 45;           /* seconds without a call before the next call records a gap */
export const EXAM_EVENTS = ['heartbeat', 'window_ready', 'focus_lost', 'focus_back', 'display_change', 'screen_locked', 'screen_unlocked',
  'suspend', 'resume', 'shortcut_blocked', 'window_close_attempt', 'network_lost', 'network_back', 'page_hidden', 'page_visible',
  'camera_started', 'camera_stopped', 'face_missing', 'faces_multiple', 'phone_seen', 'voice', 'process_new', 'process_list', 'clip_saved', 'snapshot_saved',
  'face_check', 'mic_check', 'ear_check', 'checkin', 'reconnect', 'time_over', 'after_time', 'answer_page', 'submitted', 'paper_lang',
  'system_sound', 'room_scan', 'recording_started', 'recording_failed', 'displays', 'seated', 'phone_lost', 'phone_back'];
export const EARCHECK_EARLY = 3600;        /* the ear and voice checks open an hour before the start, with the technical check */
const EAR_VERDICTS = ['clear', 'device', 'unclear'];
const EAR_PROMPT = n => `These are ${n} webcam photos of an exam candidate, taken during the technical check before an online physics exam${n === 3 ? ': the first faces the camera with both hands raised beside the face (wrists visible), in the second the head is turned to show one ear, in the third the other ear' : ': in the first the head is turned to show one ear, in the second the other ear'}.
Decide whether the candidate wears anything in, on or over the ears or head that could carry sound: earbuds, in-ear earphones, headphones, an over-ear or on-ear headset (also the headband over the head), a hearing device, or a wire leading to an ear. A headset seen in any photo counts, even if an ear is hidden.
Earrings, ear piercings, hair clips and glasses are not devices. Use "unclear" for a photo in which neither the ear nor anything over it can be seen (hair, angle, blur, too dark) or there is no person.
"wrists" is true only if both wrists can be clearly seen in the first photo (hands raised beside the face).
"ears_covered" is true if a hat, beanie, hood, headband or hair covers an ear in the ear photos (the ear itself must be seen).
Also: "cap" is true if the candidate wears a cap or a hat with a brim (a baseball cap, a bucket hat, a sun hat), which can hide the eyes; a beanie or a hat without a brim is fine. "watch" is true if a smartwatch, fitness band or any watch is on a visible wrist.
"glasses": "none" if no glasses; "regular" for thin ordinary glasses; "check" if they could be smart glasses and should be shown up close (thick frames or temples, a dot or lens at a corner of the frame, an LED, a bulge near the ear, a display in a lens).
Reply with JSON only, plain text in the note (no escape sequences): {"verdicts":[${Array.from({ length: n }, () => '"clear"|"device"|"unclear"').join(',')}],"ears_covered":bool,"wrists":bool,"cap":bool,"watch":bool,"glasses":"none"|"regular"|"check","note":"at most 15 words, in English"}`;
const GLASS_PROMPT = `These two close-up webcam photos show a candidate's glasses, taken off and held to the camera before an online exam: the first from the front (lenses and frame corners), the second the inside of the temples.
"smart" is true if they are or may be smart glasses: a camera lens or pinhole at a frame corner or the bridge, an LED, speaker grilles or touch pads on the temples, a charging contact, a display or projector in a lens, a brand such as Ray-Ban Meta, Xreal, Even Realities, Brilliant Labs. "clear_view" is false if the glasses are not seen well enough to judge.
Reply with JSON only: {"smart":bool,"clear_view":bool,"note":"at most 15 words, in English"}`;
export async function geminiGlassCheck(env, front, inside) {
  if (!env.GEMINI_API_KEY) return { unavailable: true };
  try { const v = await gemini(env, [{ inline_data: { mime_type: 'image/jpeg', data: b64(front) } }, { inline_data: { mime_type: 'image/jpeg', data: b64(inside) } }, { text: GLASS_PROMPT }]);
    return v && typeof v.smart === 'boolean' ? { smart: v.smart, clear: v.clear_view !== false, note: clean(v.note, 120) } : { unavailable: true }; }
  catch { return { unavailable: true }; }
}
const VIEW_NAMES = { room: 'the whole room, all the way round (a 360° turn at eye height)', desk: 'the whole desk top, including the sides and back of the monitor and around the keyboard',
  under: 'under the desk and the floor around the chair', ceiling: 'the ceiling' };
const VIEW_PROMPT = view => `These ${PHONE_FRAMES} or fewer frames come from a phone camera turned slowly during the room scan before an online physics exam. This part of the scan should show ${VIEW_NAMES[view]}.
Look carefully at every frame, including small objects, papers, other screens and reflections, for:
- another person or part of one; - a phone, smartwatch, tablet or e-reader (the phone that is filming is not visible to itself);
- a screen other than the one computer used for the exam (a second monitor, a laptop, a TV or projector showing anything);
- earphones, earbuds or a headset; - books, notes, sticky notes, written or printed papers, formula sheets, writing on the walls or desk (blank or printed answer sheets, a pen, a ruler, a calculator and a drink are allowed).
Also say whether the frames really show ${VIEW_NAMES[view]} ("covered": false if they show something else, are too dark, too blurred from turning too fast, or blocked).
Reply with JSON only: {"covered":bool,"person":bool,"phone":bool,"screen":bool,"headset":bool,"notes":bool,"note":"at most 20 words, in English"}`;
const PLACE_PROMPT = `This photo is from a phone placed as a second camera for an online physics exam. It should stand to the side of or behind the candidate, about 1 to 1.5 m away, so that one picture shows the candidate (head and body), both hands, the desk top and the computer screen.
Reply with JSON only: {"person":bool,"hands":bool,"desk":bool,"screen":bool,"note":"what to change, at most 15 words, in English"}`;
const ROOM_PROMPT = `These are webcam stills from the room scan before an online physics exam, taken in order: ${SCAN_VIEWS.join(', ')} (the front of the room, the left and right walls, behind the candidate, the ceiling, the desk top, under the desk).
Look for: another person (or part of one); a phone, smartwatch or tablet; a screen other than the one computer the candidate sits the exam on (a second monitor, a laptop, a TV showing text); earphones or a headset; books, notes or written papers (blank or printed exam answer sheets, a pen, a calculator and a drink are allowed).
Reply with JSON only: {"person":bool,"phone":bool,"screen":bool,"headset":bool,"notes":bool,"unclear":bool,"note":"at most 20 words, in English"} ("unclear": the stills are too dark or blurred to judge).`;
/* the sentence the candidate reads aloud in the microphone check, in the language of the page */
export const VOICE_SENTENCE = { ko: '저는 HPhO에 정직하게 응시하겠습니다.', en: 'I will sit HPhO honestly.' };
const voicePrompt = lang => `This is a microphone test recorded before an online exam. The candidate was asked to read this sentence aloud: "${VOICE_SENTENCE[lang]}".
Listen to the recording. "said" is true only if a human voice clearly reads that sentence, or very nearly that sentence (small slips are fine). It is false for silence, noise, music, tapping, a shout or a word that is not the sentence, humming, or a different sentence.
Reply with JSON only, writing what you heard as plain text (no escape sequences): {"said":true|false,"heard":"what you heard, at most 12 words"}`;
const b64 = bytes => { let s = ''; for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000)); return btoa(s); };
async function gemini(env, parts, maxOutputTokens = 200) {
  const model = env.HPHO_VISION_MODEL || env.GEMINI_MODEL || 'gemini-flash-lite-latest';
  const r = await fetch(`${env.GEMINI_BASE || 'https://generativelanguage.googleapis.com/v1beta/models'}/${model}:generateContent`, {
    method: 'POST', signal: AbortSignal.timeout(30000), headers: { 'Content-Type': 'application/json', 'x-goog-api-key': env.GEMINI_API_KEY },
    body: JSON.stringify({ contents: [{ role: 'user', parts }], generationConfig: { responseMimeType: 'application/json', temperature: 0, maxOutputTokens } }) });
  if (!r.ok) return null;
  const j = await r.json(), raw = (j.candidates?.[0]?.content?.parts || []).map(x => x.text || '').join('');
  return lenientJson(raw);
}
/* the model's reply as JSON. A free-text field (what was heard, a note) in Korean sometimes comes with a broken \u escape
   that JSON.parse refuses, which made a correct answer look like no answer: the escapes are repaired, and failing that
   the true/false fields and the verdict list are read from the text itself */
export function lenientJson(raw) {
  const text = String(raw || '').trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
  try { return JSON.parse(text); } catch {}
  try { return JSON.parse(text.replace(/\\u(?![0-9a-fA-F]{4})/g, '\\\\u')); } catch {}
  const out = {};
  for (const m of text.matchAll(/"(\w+)"\s*:\s*(true|false)/g)) out[m[1]] = m[2] === 'true';
  for (const m of text.matchAll(/"(\w+)"\s*:\s*"(clear|device|unclear|none|regular|smart)"/g)) out[m[1]] = m[2];
  const list = /"verdicts"\s*:\s*\[([^\]]*)\]/.exec(text); if (list) out.verdicts = [...list[1].matchAll(/"(\w+)"/g)].map(x => x[1]);
  return Object.keys(out).length ? out : null;
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
  return { verdicts: list, ears_covered: v.ears_covered === true, wrists: v.wrists !== false, cap: v.cap === true, watch: v.watch === true, glasses: ['regular', 'check', 'smart'].includes(v.glasses) ? v.glasses : 'none', note: clean(v.note, 120) };
}
/* the room scan's stills, judged together */
export async function geminiRoomScan(env, stills) {
  if (!env.GEMINI_API_KEY) return { unavailable: true };
  try { return roomVerdict(await gemini(env, [...stills.map(b => ({ inline_data: { mime_type: 'image/jpeg', data: b64(b) } })), { text: ROOM_PROMPT }])); }
  catch { return { unavailable: true }; }
}
export const ROOM_BLOCK = ['person', 'phone', 'screen', 'headset'];      /* these stop the candidate; notes go to review */
/* one view of the phone's scan */
export async function geminiPhoneView(env, view, frames) {
  if (!env.GEMINI_API_KEY) return { unavailable: true };
  try { return viewVerdict(await gemini(env, [...frames.map(b => ({ inline_data: { mime_type: isWebp(b) ? 'image/webp' : 'image/jpeg', data: b64(b) } })), { text: VIEW_PROMPT(view) }])); }
  catch { return { unavailable: true }; }
}
export function viewVerdict(v) {
  if (!v || ![...ROOM_BLOCK, 'notes', 'covered'].every(k => typeof v[k] === 'boolean')) return { unavailable: true };
  return { covered: v.covered, found: [...ROOM_BLOCK, 'notes'].filter(k => v[k]), note: clean(v.note, 160) };
}
export async function geminiPlacement(env, photo) {
  if (!env.GEMINI_API_KEY) return { unavailable: true };
  try { const v = await gemini(env, [{ inline_data: { mime_type: 'image/jpeg', data: b64(photo) } }, { text: PLACE_PROMPT }]);
    if (!v || !['person', 'hands', 'desk', 'screen'].every(k => typeof v[k] === 'boolean')) return { unavailable: true };
    return { ok: v.person && v.hands && v.desk && v.screen, missing: ['person', 'hands', 'desk', 'screen'].filter(k => !v[k]), note: clean(v.note, 120) }; }
  catch { return { unavailable: true }; }
}
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
    check_note TEXT, last_webcam TEXT, last_screen TEXT, clips INTEGER NOT NULL DEFAULT 0, kept TEXT, pruned_at INTEGER,
    PRIMARY KEY (round_id, user_id, track))`,
  `CREATE UNIQUE INDEX IF NOT EXISTS hpho_seats_no ON hpho_seats(round_id, track, candidate_no)`,
  /* the candidate's phone for one exam: the code's hash (the code itself is only in the QR), its scan and placement */
  `CREATE TABLE IF NOT EXISTS hpho_phones (round_id TEXT NOT NULL, user_id INTEGER NOT NULL, track TEXT NOT NULL, candidate_no TEXT NOT NULL,
    code_hash TEXT NOT NULL, created_at INTEGER NOT NULL, last_beat INTEGER, scan TEXT NOT NULL DEFAULT '{}', placed INTEGER NOT NULL DEFAULT 0,
    place_note TEXT, last_snap TEXT, device TEXT, PRIMARY KEY (round_id, user_id, track))`,
  `CREATE UNIQUE INDEX IF NOT EXISTS hpho_phones_code ON hpho_phones(code_hash)`,
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
const adminSeat = s => ({ ...seatView(s), client: s.client, events: s.events, gaps: s.gaps, last_beat: s.last_beat, clips: s.clips, kept: s.kept, pruned_at: s.pruned_at,
  check_note: s.check_note, verdict: s.verdict, verdict_note: s.verdict_note, verdict_at: s.verdict_at, review: needsReview(s) });
/* why a seat's recordings are kept for a person to review: what the on-device detectors (MediaPipe face and phone,
   voice and computer-sound levels), the desktop app (window, monitors, programs), the server (heartbeat gaps,
   reconnects) and the model checks (ears, voice, room) found. A strong sign once is enough; weak ones (a glance away,
   a short silence of the network) must repeat. A person's verdict of review or cheating always keeps them */
export const STRONG = ['faces_multiple', 'phone_seen', 'system_sound', 'camera_stopped', 'window_close_attempt', 'recording_failed'];
export const WEAK = ['focus_lost', 'face_missing', 'voice', 'page_hidden', 'network_lost', 'shortcut_blocked', 'screen_locked', 'suspend', 'phone_lost'];
export const WEAK_LIMIT = 3;
export function suspicion(seat, events) {
  const out = [], n = k => events.filter(e => e.kind === k).length;
  for (const k of STRONG) if (n(k)) out.push(`${k}×${n(k)}`);
  for (const k of WEAK) if (n(k) >= WEAK_LIMIT) out.push(`${k}×${n(k)}`);
  if (events.some(e => e.kind === 'display_change' && parseInt(e.detail, 10) > 1)) out.push('second_display');
  const risky = events.filter(e => e.kind === 'process_new' && /(^| )!/.test(e.detail || ''));
  if (risky.length) out.push('programs: ' + [...new Set(risky.flatMap(e => (e.detail.match(/!\S+/g) || [])))].join(' ').slice(0, 80));
  if ((seat.reconnects || 0) >= REVIEW_RECONNECTS) out.push(`reconnects×${seat.reconnects}`);
  if ((seat.gaps || 0) >= REVIEW_GAPS) out.push(`gaps×${seat.gaps}`);
  if (seat.check_note) out.push('checks: ' + seat.check_note.slice(0, 80));
  if (['review', 'cheating'].includes(seat.verdict)) out.push('verdict: ' + seat.verdict);
  return out;
}
export const RETAIN_AFTER = 3600;          /* the hour after the upload closes, in which an organiser may still flag a seat */
/* keep or delete one seat's recordings and proctoring photos; returns what was decided */
export async function retainSeat(db, store, round, seat, w, t) {
  const events = (await db.prepare('SELECT seq,at,kind,detail FROM hpho_events WHERE round_id=? AND user_id=? AND (track=? OR track IS NULL) AND at>=? AND at<=?')
    .bind(round, seat.user_id, seat.track, w.opens, w.upload_until + 600).all()).results || [];
  /* a seat already flagged at the end (keep) stays flagged; else the flags are counted now (a person's verdict included) */
  const why = seat.kept ? [seat.kept, ...(['review', 'cheating'].includes(seat.verdict) && !seat.kept.includes('verdict') ? ['verdict: ' + seat.verdict] : [])] : suspicion(seat, events);
  let deleted = 0;
  if (!why.length && store?.list) {
    const keys = [];
    const collect = async (prefix, keep = () => true) => { let cursor;
      do { const l = await store.list({ prefix, cursor, limit: 1000 }); keys.push(...l.objects.map(o => o.key).filter(keep)); cursor = l.truncated ? l.cursor : null; } while (cursor); };
    await collect(`hpho-rec/${round}/${seat.track}/${seat.candidate_no}/`);
    /* the proctoring photos of this exam's time; the ear and room check stills stay */
    await collect(`hpho/${round}/${seat.candidate_no}/`, k => { const m = /\/(\d+)-(webcam|screen)-([a-z_]+)\.jpg$/.exec(k); return !!m && +m[1] >= w.opens && +m[1] <= w.upload_until + 600 && !(m[2] === 'webcam' && m[3] === 'after_time'); });
    for (let i = 0; i < keys.length; i += 100) { const part = keys.slice(i, i + 100); await (store.delete ? store.delete(part) : Promise.all(part.map(k => store.del?.(k)))); deleted += part.length; }
  }
  const kept = why.length ? why.join('; ').slice(0, 500) : null;
  await db.prepare('UPDATE hpho_seats SET kept=?,pruned_at=?,last_webcam=CASE WHEN ? THEN last_webcam ELSE NULL END,last_screen=CASE WHEN ? THEN last_screen ELSE NULL END WHERE round_id=? AND user_id=? AND track=?')
    .bind(kept, t, why.length ? 1 : 0, why.length ? 1 : 0, round, seat.user_id, seat.track).run();
  return { candidate_no: seat.candidate_no, kept, deleted };
}
/* the cron's step: seats whose upload closed more than an hour ago and were not decided yet (a few at a time) */
export async function hphoRetainTick(env, { now: at = Date.now(), scope = e => e.DB, limit = 20 } = {}) {
  const db = scope(env), store = env.HPHO_SNAPS || env.LAB_PAGES, t = Math.floor(at / 1000);
  await ensureHphoExam(db);
  const seats = (await db.prepare('SELECT s.*, r.start_at AS r_start, r.duration_min AS r_dur, r.theory_at AS r_theory, r.experiment_at AS r_exp FROM hpho_seats s JOIN hpho_rounds r ON r.id=s.round_id WHERE s.pruned_at IS NULL ORDER BY s.checked_in_at LIMIT 500').all()).results || [];
  const out = [];
  for (const s of seats) {
    if (out.length >= limit) break;
    const w = examWindow({ start_at: s.r_start, duration_min: s.r_dur, theory_at: s.r_theory, experiment_at: s.r_exp }, s.track);
    if (!w || t < w.upload_until + RETAIN_AFTER) continue;
    out.push(await retainSeat(db, store, s.round_id, s, w, t));
  }
  return out;
}

/* events a proctor watching live wants to see */
export const ALERTS = ['focus_lost', 'display_change', 'screen_locked', 'suspend', 'shortcut_blocked', 'window_close_attempt', 'network_lost', 'page_hidden',
  'camera_stopped', 'face_missing', 'faces_multiple', 'phone_seen', 'voice', 'system_sound', 'reconnect', 'recording_failed', 'after_time', 'process_new', 'phone_lost'];

const sha256 = async s => [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s)))].map(b => b.toString(16).padStart(2, '0')).join('');
const phoneState = (ph, t) => ph && { paired: !!ph.last_beat, online: !!ph.last_beat && t - ph.last_beat < PHONE_ONLINE, placed: !!ph.placed, place_note: ph.place_note,
  scan: JSON.parse(ph.scan || '{}'), scanned: PHONE_VIEWS.every(v => ['clear', 'notes', 'unverified'].includes(JSON.parse(ph.scan || '{}')[v]?.status)) };
export function createHphoExamRouter({ HttpError, needUser, limit, isAdmin, scope = env => env.DB, earVision = geminiEarVision, voiceCheck = geminiVoiceCheck, glassCheck = geminiGlassCheck, roomScan = geminiRoomScan, phoneView = geminiPhoneView, placement = geminiPlacement }) {
  const fail = (status, code) => { throw new HttpError(status, code); };
  const form = async req => { try { return await req.formData(); } catch { fail(400, 'bad_upload'); } };
  const bytesOf = async (file, max, tooLarge = 'upload_too_large') => {
    if (!file || typeof file.arrayBuffer !== 'function') fail(400, 'bad_upload');
    if (file.size > max) fail(413, tooLarge);
    return new Uint8Array(await file.arrayBuffer());
  };
  /* the phone: its code is its only key; it works from the room's opening until the upload closes */
  async function phoneRoute(code, action, m, env, req, device) {
    const db = scope(env); await ensureHphoExam(db);
    const ph = /^[A-Za-z0-9_-]{20,64}$/.test(code) ? await db.prepare('SELECT * FROM hpho_phones WHERE code_hash=?').bind(await sha256(code)).first() : null;
    if (!ph) fail(404, 'phone_not_found');
    const round = await db.prepare('SELECT * FROM hpho_rounds WHERE id=?').bind(ph.round_id).first(), w = round && examWindow(round, ph.track), t = now();
    if (!w || t >= w.upload_until + 600) fail(409, 'exam_over');
    const store = env.HPHO_SNAPS || env.LAB_PAGES, where = [ph.round_id, ph.user_id, ph.track];
    /* one phone per seat: the first device to open the code keeps it; another one is refused while the first is
       connected (no one else's phone can take over a candidate's seat, and two candidates' scans never mix) */
    if (!/^[A-Za-z0-9_-]{16,64}$/.test(device || '')) fail(400, 'bad_device');
    if (ph.device && ph.device !== device && ph.last_beat && t - ph.last_beat < PHONE_ONLINE) fail(409, 'phone_in_use');
    if (ph.device !== device) { await db.prepare('UPDATE hpho_phones SET device=? WHERE round_id=? AND user_id=? AND track=?').bind(device, ...where).run(); ph.device = device; }
    const event = (kind, detail, mark) => db.prepare(`INSERT OR IGNORE INTO hpho_events(round_id,user_id,seq,client_at,at,kind,detail,track) VALUES(?,?,?,NULL,?,?,?,?)`).bind(ph.round_id, ph.user_id, -(mark + t), t, kind, String(detail || '').slice(0, 200), ph.track);
    const beat = () => db.prepare('UPDATE hpho_phones SET last_beat=? WHERE round_id=? AND user_id=? AND track=?').bind(t, ...where).run();
    if (action === 'state' && m === 'GET') { await beat(); return { round: ph.round_id, track: ph.track, candidate_no: ph.candidate_no, window: w, now: t, views: PHONE_VIEWS, ...phoneState({ ...ph, last_beat: t }, t) }; }
    if (m !== 'POST') fail(405, 'method_not_allowed');
    await limit(env, 'hpho-phone:' + ph.user_id, 400, 600);
    if (action === 'beat') { await beat(); return { ok: true, now: t }; }
    let f; try { f = await req.formData(); } catch { fail(400, 'bad_upload'); }
    const jpeg = async (name, max = SNAP_SOURCE_MAX.phone, webp = false) => { const file = f.get(name); if (!file || typeof file.arrayBuffer !== 'function') fail(400, 'bad_upload'); if (file.size > max) fail(413, 'snapshot_too_large');
      const b = new Uint8Array(await file.arrayBuffer()); if (!isJpeg(b) && !(webp && isWebp(b))) fail(415, 'snapshot_not_jpeg'); return b; };
    const put = (key, b, reason) => store?.put(key, b, { httpMetadata: { contentType: 'image/jpeg' }, customMetadata: { round: ph.round_id, track: ph.track, candidate: ph.candidate_no, source: 'phone', reason } });
    if (action === 'scan') {
      const view = PHONE_VIEWS.includes(f.get('view')) ? f.get('view') : fail(400, 'bad_view');
      /* the phone's frames: JPEG or WebP (smaller), already chosen and enhanced on the phone */
      const frames = []; for (let i = 0; i < PHONE_FRAMES; i++) if (f.get('f' + i)) frames.push(await jpeg('f' + i, SNAP_SOURCE_MAX.phone, true));
      if (frames.length < 3) fail(400, 'too_few_frames');
      for (const [i, b] of frames.entries()) await store?.put(`hpho/${ph.round_id}/${ph.candidate_no}/${t}-phone-scan_${view}_${i}.${isWebp(b) ? 'webp' : 'jpg'}`, b, { httpMetadata: { contentType: isWebp(b) ? 'image/webp' : 'image/jpeg' }, customMetadata: { round: ph.round_id, track: ph.track, candidate: ph.candidate_no, source: 'phone', reason: 'room_scan' } });
      const scan = JSON.parse(ph.scan || '{}'), tries = (scan[view]?.tries || 0) + 1;
      const v = await phoneView(env, view, frames);
      /* blocked: remove it and sweep again. Not covered (too fast, too dark): sweep again. No model: three tries, then unverified */
      const status = v.unavailable ? (tries >= 3 ? 'unverified' : 'unavailable') : !v.covered ? 'redo' : v.found.some(k => ROOM_BLOCK.includes(k)) ? 'blocked' : v.found.includes('notes') ? 'notes' : 'clear';
      scan[view] = { status, tries, found: v.found || [], at: t };
      const stmts = [db.prepare('UPDATE hpho_phones SET scan=?,last_beat=? WHERE round_id=? AND user_id=? AND track=?').bind(JSON.stringify(scan), t, ...where)];
      /* every view done: one room_scan record (the seat's checks read it) */
      if (PHONE_VIEWS.every(k => ['clear', 'notes', 'unverified'].includes(scan[k]?.status))) {
        const flags = PHONE_VIEWS.filter(k => scan[k].status !== 'clear').map(k => `${k}=${scan[k].status === 'notes' ? 'notes' : 'model unavailable'}`);
        stmts.push(event('room_scan', flags.length ? `flag: phone · ${flags.join(',')}` : 'clear (phone)', 3e9));
      }
      await db.batch(stmts);
      return { ok: true, view, status, found: v.found || [], note: v.note || '' };
    }
    if (action === 'place') {
      const b = await jpeg('image'); await put(`hpho/${ph.round_id}/${ph.candidate_no}/${t}-phone-placement.jpg`, b, 'placement');
      const v = await placement(env, b), tries = (ph.placed_tries || 0) + 1;
      const ok = v.unavailable ? null : v.ok;
      await db.prepare('UPDATE hpho_phones SET placed=?,place_note=?,last_beat=? WHERE round_id=? AND user_id=? AND track=?')
        .bind(ok ? 1 : 0, v.unavailable ? 'model unavailable' : ok ? null : (v.missing.join(',') + (v.note ? ' · ' + v.note : '')).slice(0, 200), t, ...where).run();
      return v.unavailable ? { ok: true, unavailable: true } : { ok: true, placed: ok, missing: v.missing };
    }
    if (action === 'snap') {
      const reason = /^[a-z_]{3,24}$/.test(String(f.get('reason') || '')) ? String(f.get('reason')) : 'random';
      const b = await jpeg('image'), key = `hpho/${ph.round_id}/${ph.candidate_no}/${t}-phone-${reason}.jpg`;
      await put(key, b, reason);
      await db.batch([db.prepare('UPDATE hpho_phones SET last_snap=?,last_beat=? WHERE round_id=? AND user_id=? AND track=?').bind(key, t, ...where)]);
      return { ok: true };
    }
    fail(404, 'not_found');
  }
  return async function exam(p, m, body, me, env, url, req) {
    const phone = /^\/api\/hpho\/phone\/([^/]+)\/(state|scan|place|snap|beat)$/.exec(p);
    if (phone) return phoneRoute(phone[1], phone[2], m, env, req, url?.searchParams?.get('d'));
    const r = /^\/api\/hpho\/rounds\/([^/]+)\/exam\/(?:(theory|experiment)\/)?(state|checkin|lang|start|events|snap|earcheck|voicecheck|glasscheck|roomscan|phone|keep|clip|docs|doc|answer|submit|upload|seats|monitor|log|media|verdict|retain)$/.exec(p);
    if (!r) return undefined;
    const [, id, track = 'theory', action] = r, db = scope(env), admin = isAdmin(me);
    needUser(me); await ensureHphoExam(db);
    const round = await db.prepare('SELECT * FROM hpho_rounds WHERE id=?').bind(id).first();
    if (!round || round.status === 'draft' && !admin) fail(404, 'round_not_found');   /* a draft: an admins' rehearsal */
    const w = examWindow(round, track); if (!w) fail(404, 'no_such_exam');
    const t = now(), store = env.HPHO_SNAPS || env.LAB_PAGES;
    const q = k => url?.searchParams?.get(k) || '';

    /* ── the organisers ── */
    if (['upload', 'seats', 'monitor', 'log', 'media', 'verdict', 'retain'].includes(action)) {
      if (action === 'retain' && m === 'POST') {
        /* now, for this exam's seats (after its upload closed): keep the flagged, delete the rest */
        if (t < w.upload_until) fail(409, 'not_over');
        const rows = (await db.prepare('SELECT * FROM hpho_seats WHERE round_id=? AND track=?').bind(id, track).all()).results || [];
        const out = []; for (const s of rows) out.push(await retainSeat(db, store, id, s, w, t));
        return { ok: true, seats: out };
      }
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
        const phones = new Map(((await db.prepare('SELECT user_id,last_beat,last_snap FROM hpho_phones WHERE round_id=? AND track=?').bind(id, track).all()).results || []).map(x => [x.user_id, x]));
        return { window: w, now: t, seats: rows.map(s => ({ ...adminSeat(s), last_webcam: s.last_webcam, last_screen: s.last_screen, online: t - s.last_beat < 45 && !s.submitted_at,
          last_phone: phones.get(s.user_id)?.last_snap || null, phone_online: !!phones.get(s.user_id)?.last_beat && t - phones.get(s.user_id).last_beat < PHONE_ONLINE,
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

    if (action === 'phone') {
      if (!entry) fail(403, 'not_registered');
      const ph = await db.prepare('SELECT * FROM hpho_phones WHERE round_id=? AND user_id=? AND track=?').bind(id, me.id, track).first();
      if (m === 'GET') return { now: t, phone: phoneState(ph, t), views: PHONE_VIEWS };
      if (m !== 'POST') fail(405, 'method_not_allowed');
      if (t < w.start_at - EARCHECK_EARLY || t >= w.upload_until) fail(409, 'check_closed');
      /* a new code (the QR shows it once); a phone already paired keeps its scan, a new code replaces the old one */
      const code = btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(24)))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
      /* rescan (a return after a disconnect): the room is shown again and the phone stood again */
      if (ph) await db.prepare(`UPDATE hpho_phones SET code_hash=?,device=NULL${body?.rescan ? ",scan='{}',placed=0,place_note=NULL" : ''} WHERE round_id=? AND user_id=? AND track=?`).bind(await sha256(code), id, me.id, track).run();
      else await db.prepare('INSERT INTO hpho_phones(round_id,user_id,track,candidate_no,code_hash,created_at) VALUES(?,?,?,?,?,?)').bind(id, me.id, track, entry.candidate_no, await sha256(code), t).run();
      return { ok: true, code };
    }
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

    if (['earcheck', 'voicecheck', 'glasscheck', 'roomscan'].includes(action)) {
      if (t < w.start_at - EARCHECK_EARLY || t >= w.ends) fail(409, 'check_closed');
      await limit(env, `hpho-${action}:` + me.id, 8, 600);
      const f = await form(req);
      if (action === 'voicecheck') {
        const lang = DOC_LANGS.includes(f.get('lang')) ? f.get('lang') : 'ko';
        const wav = await bytesOf(f.get('audio'), VOICE_MAX_BYTES, 'audio_too_large'); if (!isWav(wav)) fail(415, 'audio_not_wav');
        if (store) await store.put(`hpho/${id}/${entry.candidate_no}/${t}-mic-voice_check.wav`, wav, { httpMetadata: { contentType: 'audio/wav' }, customMetadata: { round: id, candidate: entry.candidate_no, source: 'mic', reason: 'voice_check' } });
        /* decided on the candidate's computer (Whisper in the page): no model call here; the recording and what was heard
           are kept, so a person can listen to it */
        if (f.get('local') === 'said') {
          await serverEvent('mic_check', `said (on device) · heard: ${clean(String(f.get('heard') || ''), 100)}`, 5e9).run();
          return { ok: true, said: true, local: true };
        }
        const v = await voiceCheck(env, wav, lang);
        await serverEvent('mic_check', v.unavailable ? 'model unavailable' : `${v.said ? 'said' : 'not said'}${v.heard ? ' · heard: ' + v.heard : ''}`, 5e9).run();
        return v.unavailable ? { ok: true, unavailable: true } : { ok: true, said: v.said };
      }
      const still = async name => { const bytes = await bytesOf(f.get(name), SNAP_MAX_BYTES * 2, 'snapshot_too_large'); if (!isJpeg(bytes)) fail(415, 'snapshot_not_jpeg'); return bytes; };
      const keep = (bytes, name, reason) => store?.put(`hpho/${id}/${entry.candidate_no}/${t}-${reason === 'room_scan' ? 'roomscan' : 'earcheck'}-${name}.jpg`, bytes, { httpMetadata: { contentType: 'image/jpeg' }, customMetadata: { round: id, candidate: entry.candidate_no, source: 'webcam', reason } });
      if (action === 'glasscheck') {
        const front = await still('front'), inside = await still('inside');
        await keep(front, 'glasses-front', 'ear_check'); await keep(inside, 'glasses-inside', 'ear_check');
        const v = await glassCheck(env, front, inside);
        await serverEvent('ear_check', v.unavailable ? 'glasses: model unavailable' : v.smart ? `glasses: smart${v.note ? ' · ' + v.note : ''}` : v.clear ? `clear (glasses shown, ordinary)${v.note ? ' · ' + v.note : ''}` : 'glasses: unclear', 4e9 + 1).run();
        return v.unavailable ? { ok: true, unavailable: true } : { ok: true, smart: v.smart, clear: v.clear };
      }
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
      /* glasses that might be smart are not a fail yet: the page asks to see them up close (glasscheck) */
      const verdict = v.unavailable ? null : v.verdicts.includes('device') ? 'device' : v.ears_covered ? 'covered' : v.watch ? 'watch' : v.cap ? 'cap' : shots.length === 3 && v.wrists === false ? 'wrists' : v.verdicts.includes('unclear') ? 'unclear' : ['check', 'smart'].includes(v.glasses) ? 'glasses_check' : 'clear';
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
      const bytes = await bytesOf(f.get('image'), SNAP_SOURCE_MAX[source], 'snapshot_too_large'); if (!isJpeg(bytes)) fail(415, 'snapshot_not_jpeg');
      const key = snapKey(id, seat.candidate_no, source, t, reason);
      await store.put(key, bytes, { httpMetadata: { contentType: 'image/jpeg' }, customMetadata: { round: id, track, candidate: seat.candidate_no, source, reason } });
      await db.prepare(`UPDATE hpho_seats SET last_beat=?,${source === 'screen' ? 'last_screen' : 'last_webcam'}=? WHERE round_id=? AND user_id=? AND track=?`).bind(t, key, id, me.id, track).run();
      return { ok: true };
    }
    if (action === 'keep') {
      /* asked once the time is over: the seat's flags so far decide whether its recordings come to the server. The
         candidate learns only yes or no, never why */
      if (t < w.ends) fail(409, 'not_over');
      const events = (await db.prepare('SELECT seq,at,kind,detail FROM hpho_events WHERE round_id=? AND user_id=? AND (track=? OR track IS NULL) AND at>=?').bind(id, me.id, track, w.opens).all()).results || [];
      const why = suspicion(seat, events), kept = why.length ? why.join('; ').slice(0, 500) : null;
      await db.prepare('UPDATE hpho_seats SET kept=COALESCE(?,kept) WHERE round_id=? AND user_id=? AND track=?').bind(kept, id, me.id, track).run();
      return { ok: true, keep: !!(kept || seat.kept) };
    }
    if (action === 'clip') {
      /* the recording, in five-minute WebM segments, from a flagged seat only, until half an hour after the upload closed */
      await limit(env, 'hpho-clip:' + me.id, 400, 3600);
      if (!seat.kept) fail(403, 'not_kept');
      if (t > w.upload_until + 1800) fail(409, 'exam_over');
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

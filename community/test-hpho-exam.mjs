import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createHphoRouter, roundTracks, checkRound, publicRound} from './src/hpho.js';
import {createHphoExamRouter, checkEvents, checkClient, earVerdict, voiceVerdict, roomVerdict, viewVerdict, lenientJson, checkNote, suspicion, hphoRetainTick, PHONE_VIEWS, examWindow, needsReview, UPLOAD_MIN, SCAN_VIEWS} from './src/hpho-exam.js';

class HttpError extends Error { constructor(status, code) { super(code); this.status = status; this.code = code; } }
function d1() {
  const sql = new DatabaseSync(':memory:');
  const make = (q, args = []) => ({ bind: (...v) => make(q, v), async first() { return sql.prepare(q).get(...args) || null; },
    async all() { return { results: sql.prepare(q).all(...args) }; }, async run() { const r = sql.prepare(q).run(...args); return { meta: { changes: r.changes } }; } });
  return { sql, DB: { prepare: q => make(q), async batch(list) { for (const s of list) await s.run(); return []; } } };
}
/* an R2 bucket in memory: put, get, head, list */
function r2() {
  const m = new Map();
  return { m, async delete(keys) { for (const k of [].concat(keys)) m.delete(k); }, async put(k, v, o) { m.set(k, { bytes: new Uint8Array(v), meta: o }); },
    async get(k) { const o = m.get(k); return o ? { body: o.bytes, size: o.bytes.length, httpMetadata: o.meta?.httpMetadata } : null; },
    async head(k) { const o = m.get(k); return o ? { size: o.bytes.length } : null; },
    async list({ prefix }) { return { objects: [...m.keys()].filter(k => k.startsWith(prefix)).map(key => ({ key })), truncated: false }; } };
}
const needUser = u => { if (!u) throw new HttpError(401, 'login_required'); return u; };
const deps = { HttpError, needUser, limit: async () => {}, isAdmin: u => u?.role === 'admin' };
const admin = { id: 1, role: 'admin' }, student = { id: 7 }, other = { id: 9 };
const client = { app: 'haslaedu-desktop', version: '0.5.5' };
const entry = { country: 'KR', level: 'high', birth_year: new Date().getUTCFullYear() - 20, age14: true, pledge: true, proctoring: true, identity_notice: true };
const code = async p => { try { await p; return null; } catch (e) { return e.code; } };
const JPEG = new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 1, 2, 3]), PDF = new TextEncoder().encode('%PDF-1.7 x');
function wav() { const b = new Uint8Array(64); b.set(new TextEncoder().encode('RIFF'), 0); b.set(new TextEncoder().encode('WAVE'), 8); return b; }

/* a round whose theory exam starts `theory` seconds from now and whose experiment starts a day later */
async function setup(theory, { voice = { said: true }, ear = { verdicts: ['clear', 'clear', 'clear'] }, room = { found: [], unclear: false }, view = () => ({ covered: true, found: [] }), place = { ok: true, missing: [] }, glass = { smart: false, clear: true } } = {}) {
  const { sql, DB } = d1(), store = r2(), env = { DB, HPHO_SNAPS: store }, t = Math.floor(Date.now() / 1000);
  const reg = createHphoRouter(deps), exam = createHphoExamRouter({ ...deps, voiceCheck: async () => voice, earVision: async () => ear, glassCheck: async () => glass, roomScan: async () => room, phoneView: async (_e, v) => view(v), placement: async () => place });
  await reg('/api/hpho/rounds/2027-1', 'POST', { title_ko: 'a', title_en: 'a', reg_open: t - 7200, reg_close: t + 3600, theory_at: t + 7200, experiment_at: t + 7200 + 86400, fee_usd: 0, status: 'open' }, admin, env);
  await reg('/api/hpho/rounds/2027-1/entry', 'POST', entry, student, env);
  sql.prepare('UPDATE hpho_rounds SET theory_at=?,start_at=?,experiment_at=?').run(t + theory, t + theory, t + theory + 86400);
  const call = (action, m, body, me, query = '', track = 'theory') => exam(`/api/hpho/rounds/2027-1/exam/${track}/${action}`, m, body, me, env, new URL('https://x/' + query));
  const form = (action, fields, me = student, track = 'theory') => { const f = new FormData(); for (const [k, v] of Object.entries(fields)) f.set(k, v instanceof Uint8Array ? new Blob([v]) : v);
    return exam(`/api/hpho/rounds/2027-1/exam/${track}/${action}`, 'POST', {}, me, env, new URL('https://x/'), new Request('https://x/', { method: 'POST', body: f })); };
  /* move the theory exam by s seconds (negative: it is now later in the day) */
  const shift = s => sql.prepare('UPDATE hpho_rounds SET theory_at=theory_at+?,start_at=start_at+?').run(s, s);
  const phone = (code, action, fields, d = 'phone-device-aaaaaaaa') => { const u = new URL('https://x/?d=' + d); if (!fields) return exam(`/api/hpho/phone/${code}/${action}`, 'GET', null, null, env, u);
    const fd = new FormData(); for (const [k, v] of Object.entries(fields)) fd.set(k, v instanceof Uint8Array ? new Blob([v]) : v);
    return exam(`/api/hpho/phone/${code}/${action}`, 'POST', {}, null, env, u, new Request('https://x/', { method: 'POST', body: fd })); };
  return { sql, store, call, form, shift, t, reg, env, phone };
}

test('a round has a theory and an experiment exam, five hours each', () => {
  const r = { start_at: 1000, duration_min: 300, theory_at: 1000, experiment_at: 1000 + 86400 };
  assert.deepEqual(roundTracks(r).map(x => [x.track, x.start_at, x.ends - x.start_at, x.start_at - x.opens, x.start_at - x.seat_by]),
    [['theory', 1000, 18000, 3600, 1200], ['experiment', 87400, 18000, 3600, 1200]]);
  assert.deepEqual(roundTracks({ start_at: 50, duration_min: 240 }).map(x => x.track), ['theory'], 'a round from before the split keeps one exam');
  assert.equal(publicRound({ ...r, id: 'x', title_ko: 'a', title_en: 'b' }).tracks.length, 2);
  const base = { title_ko: 'a', title_en: 'a', reg_open: 1, reg_close: 2 };
  assert.equal(checkRound('2027-1', { ...base, theory_at: 100, experiment_at: 200 }).error, 'bad_time_order', 'the experiment comes after the theory has ended');
  assert.equal(checkRound('2027-1', { ...base, theory_at: 100, experiment_at: 100 + 18000 }).duration_min, 300);
  assert.equal(examWindow({ start_at: 0, duration_min: 300, theory_at: 0 }, 'experiment'), null);
});

test('client and event checks', () => {
  assert.equal(checkClient(client), 'haslaedu-desktop/0.5.5');
  assert.equal(checkClient({ app: 'chrome', version: '1.0.0' }), null);
  assert.equal(checkEvents([{ seq: 1, t: 5, kind: 'focus_lost', detail: 'x\u0007y' }]).events[0].detail, 'x y');
  assert.equal(checkEvents([{ seq: 1, kind: 'rm -rf' }]).error, 'bad_events');
  assert.equal(checkEvents(Array.from({ length: 101 }, (_, i) => ({ seq: i, kind: 'heartbeat' }))).error, 'bad_events');
});

test('the room opens an hour before; seats close twenty minutes before the start', async () => {
  const early = await setup(3700);
  assert.equal(await code(early.call('checkin', 'POST', { client }, student)), 'not_open');
  const f = await setup(1800);
  assert.equal(await code(f.call('checkin', 'POST', { client }, other)), 'not_registered');
  assert.equal(await code(f.call('checkin', 'POST', {}, student)), 'desktop_app_required');
  const s = await f.call('checkin', 'POST', { client, lang: 'en' }, student);
  assert.match(s.session.candidate_no, /^HP271-\d{4}$/);
  assert.equal(s.session.paper_lang, 'en');
  const late = await setup(1100);
  assert.equal(await code(late.call('checkin', 'POST', { client }, student)), 'seating_closed', 'eighteen minutes before: too late');
  /* a seated candidate who left the room may come back after seating closed */
  f.shift(-1000);
  assert.equal((await f.call('checkin', 'POST', { client }, student)).resumed, true);
  /* the experiment has its own seat, on its own day */
  assert.equal(await code(f.call('checkin', 'POST', { client }, student, '', 'experiment')), 'not_open');
});

test('the paper language can be changed in the waiting room, not after the start', async () => {
  const f = await setup(1800);
  assert.equal(await code(f.call('lang', 'POST', { lang: 'en' }, student)), 'not_seated');
  await f.call('checkin', 'POST', { client }, student);
  assert.equal((await f.call('lang', 'POST', { lang: 'en' }, student)).paper_lang, 'en');
  f.shift(-1801);
  assert.equal(await code(f.call('lang', 'POST', { lang: 'ko' }, student)), 'exam_started');
});

test('the exam starts at the start time; a disconnect resumes and is counted', async () => {
  const f = await setup(1800);
  await f.call('checkin', 'POST', { client }, student);
  assert.equal(await code(f.call('start', 'POST', { client }, student)), 'not_started');
  f.shift(-1801);
  const s = await f.call('start', 'POST', { client }, student);
  assert.ok(s.ends_at - s.now <= 300 * 60);
  await f.call('events', 'POST', { events: [{ seq: 1, t: s.now, kind: 'window_ready' }, { seq: 2, t: s.now, kind: 'focus_lost' }] }, student);
  /* the app crashes and comes back three times: each return goes through the check-in and is recorded */
  for (let i = 0; i < 3; i++) {
    const back = await f.call('checkin', 'POST', { client }, student);
    assert.equal(back.seq, 2, 'the page continues the event numbering');
    assert.equal((await f.call('start', 'POST', { client }, student)).resumed, true);
  }
  const seats = await f.call('seats', 'GET', null, admin);
  assert.equal(seats.seats[0].reconnects, 3);
  assert.equal(seats.review, 1, 'frequent disconnects are flagged for a person to review');
  assert.equal(await code(f.call('seats', 'GET', null, student)), 'forbidden');
  const no = seats.seats[0].candidate_no;
  assert.equal((await f.call('verdict', 'POST', { candidate: no, verdict: 'cheating', note: 'left the camera for 10 min' }, admin)).verdict, 'cheating');
  const log = await f.call('log', 'GET', null, admin, '?candidate=' + no);
  assert.equal(log.seat.verdict, 'cheating');
  assert.ok(log.events.some(e => e.kind === 'reconnect'));
  assert.ok(log.events.some(e => e.kind === 'focus_lost'));
});

test('a silence the server sees is recorded as a gap', async () => {
  const f = await setup(1800);
  await f.call('checkin', 'POST', { client }, student);
  f.shift(-1801);
  await f.call('start', 'POST', { client }, student);
  f.sql.prepare('UPDATE hpho_seats SET last_beat=last_beat-120').run();
  assert.equal((await f.call('events', 'POST', { events: [] }, student)).gap, true);
  assert.equal(f.sql.prepare('SELECT gaps FROM hpho_seats').get().gaps, 1);
});

test('documents: the sheets from the opening, the paper only during the exam', async () => {
  const f = await setup(1800);
  assert.equal(await code(f.form('upload', { kind: 'paper', lang: 'ko', file: PDF }, student)), 'forbidden');
  assert.equal(await code(f.form('upload', { kind: 'paper', lang: 'ko', file: JPEG }, admin)), 'doc_not_pdf');
  for (const kind of ['guide', 'writing', 'answer', 'paper']) await f.form('upload', { kind, lang: 'ko', file: PDF }, admin);
  await f.form('upload', { kind: 'paper', lang: 'en', file: PDF }, admin);
  assert.equal((await f.call('docs', 'GET', null, student)).docs.length, 5);
  const guide = await f.call('doc', 'GET', null, student, '?kind=guide&lang=ko');
  assert.equal(guide.headers.get('Content-Type'), 'application/pdf');
  assert.equal(await code(f.call('doc', 'GET', null, student, '?kind=paper&lang=ko')), 'not_started', 'no paper in the waiting room');
  await f.call('checkin', 'POST', { client }, student);
  f.shift(-1801);
  assert.equal(await code(f.call('doc', 'GET', null, student, '?kind=paper&lang=ko')), 'not_started', 'not before the candidate has started');
  await f.call('start', 'POST', { client }, student);
  assert.equal((await f.call('doc', 'GET', null, student, '?kind=paper&lang=en')).status, 200);
  f.shift(-300 * 60);
  assert.equal(await code(f.call('doc', 'GET', null, student, '?kind=paper&lang=en')), 'exam_over', 'the paper is gone once the time is over');
});

test('answers go up after the end, during the upload hour; then the seat is submitted', async () => {
  const f = await setup(1800);
  await f.call('checkin', 'POST', { client }, student);
  f.shift(-1801); await f.call('start', 'POST', { client }, student);
  assert.equal(await code(f.form('answer', { page: '1', image: JPEG })), 'not_over', 'not during the exam');
  assert.equal(await code(f.call('submit', 'POST', {}, student)), 'not_over');
  f.shift(-300 * 60);
  /* the recording goes on after the time: writing on the sheets now is cheating */
  assert.equal((await f.form('snap', { image: JPEG, source: 'webcam', reason: 'after_time' })).ok, true);
  assert.equal((await f.form('answer', { page: '1', image: JPEG })).page, 1);
  assert.equal(await code(f.form('answer', { page: '2', image: PDF })), 'answer_not_image');
  await f.form('answer', { page: '2', image: JPEG });
  assert.equal((await f.call('submit', 'POST', {}, student)).pages, 2);
  assert.equal(await code(f.form('answer', { page: '3', image: JPEG })), 'upload_closed');
  assert.equal(await code(f.form('snap', { image: JPEG, source: 'webcam', reason: 'random' })), 'exam_over');
  const no = f.sql.prepare('SELECT candidate_no FROM hpho_seats').get().candidate_no;
  const log = await f.call('log', 'GET', null, admin, '?candidate=' + no);
  assert.equal(log.answers.length, 2);
  assert.equal(log.snaps.length, 1);
  assert.equal((await f.call('media', 'GET', null, admin, '?key=' + encodeURIComponent(log.answers[0]))).status, 200);
  assert.equal(await code(f.call('media', 'GET', null, admin, '?key=other/x.jpg')), 'not_found');
  assert.ok(UPLOAD_MIN >= 30);
});

test('voice check: the sentence must be heard, a noise does not pass', async () => {
  const no = await setup(1800, { voice: { said: false } });
  assert.equal((await no.form('voicecheck', { audio: wav(), lang: 'ko' })).said, false);
  assert.equal(await code(no.form('voicecheck', { audio: JPEG, lang: 'ko' })), 'audio_not_wav');
  const yes = await setup(1800);
  assert.equal((await yes.form('voicecheck', { audio: wav(), lang: 'ko' })).said, true);
  const down = await setup(1800, { voice: { unavailable: true } });
  assert.equal((await down.form('voicecheck', { audio: wav(), lang: 'en' })).unavailable, true);
  assert.equal(await code((await setup(3700)).form('voicecheck', { audio: wav(), lang: 'ko' })), 'check_closed');
  /* decided on the computer: kept and recorded, no model call (the model stub here would say not said) */
  const local = await no.form('voicecheck', { audio: wav(), lang: 'ko', local: 'said', heard: '저는 정직하게 응시하겠습니다' });
  assert.deepEqual([local.said, local.local], [true, true]);
  assert.deepEqual(voiceVerdict({ said: true, heard: 'x\u0000y' }), { said: true, heard: 'x y' });
  /* the model's reply with a broken escape in the Korean it heard (as Gemini sent it): still read as said */
  assert.equal(lenientJson('{"said": true, "heard": "\\uc800\\ub294 \\uaca\u071f\\uc2b5"}').said, true);
  assert.deepEqual(lenientJson('```json\n{"verdicts":["clear","device"],"cap":false,"glasses":"smart","note":"\\ub"}\n```'), { cap: false, glasses: 'smart', note: '\\ub', verdicts: ['clear', 'device'] });
  assert.equal(voiceVerdict({ said: 'yes' }).unavailable, true);
});

test('ear check: the front and both ears; a headset in any photo stops the candidate', async () => {
  const f = await setup(1800, { ear: { verdicts: ['device', 'clear', 'unclear'] } });
  assert.equal((await f.form('earcheck', { front: JPEG, first: JPEG, second: JPEG })).verdict, 'device');
  assert.equal(earVerdict({ verdicts: ['clear', 'maybe', 'clear'] }, 3).unavailable, true);
  assert.deepEqual(earVerdict({ verdicts: ['clear', 'unclear', 'clear'], note: 'a\nb' }, 3), { verdicts: ['clear', 'unclear', 'clear'], ears_covered: false, wrists: true, cap: false, watch: false, glasses: 'none', note: 'a b' });
  const glasses = await setup(1800, { ear: { verdicts: ['clear', 'clear', 'clear'], glasses: 'check' } });
  assert.equal((await glasses.form('earcheck', { front: JPEG, first: JPEG, second: JPEG })).verdict, 'glasses_check', 'thick glasses: shown up close next');
  const beanie = await setup(1800, { ear: { verdicts: ['clear', 'clear', 'clear'], ears_covered: true } });
  assert.equal((await beanie.form('earcheck', { front: JPEG, first: JPEG, second: JPEG })).verdict, 'covered', 'a beanie over the ears: lift it');
  const wrists = await setup(1800, { ear: { verdicts: ['clear', 'clear', 'clear'], wrists: false } });
  assert.equal((await wrists.form('earcheck', { front: JPEG, first: JPEG, second: JPEG })).verdict, 'wrists', 'hands not raised: no pass');
  const cap = await setup(1800, { ear: { verdicts: ['clear', 'clear', 'clear'], cap: true } });
  assert.equal((await cap.form('earcheck', { front: JPEG, first: JPEG, second: JPEG })).verdict, 'cap', 'a brimmed cap hides the eyes');
  assert.deepEqual(earVerdict({ first: 'clear', second: 'clear' }).verdicts, ['clear', 'clear'], 'the old two-photo form is still read');
  assert.equal(needsReview({ reconnects: 1, gaps: 3 }), true);
});

test('room scan: a person, a phone, another screen or a headset stops; notes go to review', async () => {
  const stills = Object.fromEntries(SCAN_VIEWS.map(v => [v, JPEG]));
  const f = await setup(1800, { room: { found: ['phone', 'notes'], unclear: false } });
  const r = await f.form('roomscan', stills);
  assert.deepEqual(r.blocked, ['phone']);
  assert.equal(await code(f.form('roomscan', { front: JPEG })), 'bad_upload', 'every view is needed');
  assert.deepEqual(roomVerdict({ person: false, phone: false, screen: true, headset: false, notes: true, unclear: false }).found, ['screen', 'notes']);
  assert.equal(roomVerdict({ person: 'no' }).unavailable, true);
});

test('checks the server could not confirm flag the seat for review', async () => {
  assert.equal(checkNote([{ kind: 'ear_check', at: 1, detail: 'clear (clear,clear,clear)' }, { kind: 'mic_check', at: 1, detail: 'said · heard: x' }, { kind: 'room_scan', at: 1, detail: 'clear' }]), null);
  assert.match(checkNote([{ kind: 'ear_check', at: 1, detail: 'model unavailable' }, { kind: 'mic_check', at: 2, detail: 'said' }]), /ears: model unavailable; room: not done/);
  const f = await setup(1800, { voice: { unavailable: true } });
  await f.form('earcheck', { front: JPEG, first: JPEG, second: JPEG });
  await f.form('voicecheck', { audio: wav(), lang: 'ko' });
  await f.form('roomscan', Object.fromEntries(SCAN_VIEWS.map(v => [v, JPEG])));
  await f.call('checkin', 'POST', { client }, student);
  const seat = (await f.call('seats', 'GET', null, admin)).seats[0];
  assert.match(seat.check_note, /^voice: model unavailable$/);
  assert.equal(seat.review, true);
});

test('recordings and the live monitor', async () => {
  const f = await setup(1800);
  const WEBM = new Uint8Array([0x1a, 0x45, 0xdf, 0xa3, 1, 2, 3]);
  assert.equal(await code(f.form('clip', { clip: WEBM, source: 'webcam' })), 'not_seated');
  await f.call('checkin', 'POST', { client }, student);
  assert.equal(await code(f.form('clip', { clip: WEBM, source: 'screen' })), 'not_kept', 'no recording on the server from a seat not flagged');
  assert.equal(await code(f.call('keep', 'POST', {}, student)), 'not_over');
  await f.form('snap', { image: JPEG, source: 'webcam', reason: 'random' });
  await f.call('events', 'POST', { events: [{ seq: 1, kind: 'system_sound', detail: '4s' }, { seq: 2, kind: 'heartbeat' }] }, student);
  const m = await f.call('monitor', 'GET', null, admin);
  assert.equal(m.seats[0].online, true);
  assert.match(m.seats[0].last_webcam, /-webcam-random\.jpg$/);
  assert.deepEqual(m.seats[0].alerts.map(a => a.kind), ['system_sound']);
  assert.equal(await code(f.call('monitor', 'GET', null, student)), 'forbidden');
  /* the time is over: the computer's sound flagged the seat, so its recordings come up */
  f.shift(-1801 - 300 * 60);
  assert.equal((await f.call('keep', 'POST', {}, student)).keep, true);
  assert.equal((await f.form('clip', { clip: WEBM, source: 'screen' })).ok, true);
  assert.equal(await code(f.form('clip', { clip: JPEG, source: 'screen' })), 'clip_not_webm');
  const no = m.seats[0].candidate_no, log = await f.call('log', 'GET', null, admin, '?candidate=' + no);
  assert.equal(log.clips.length, 1);
  assert.equal((await f.call('media', 'GET', null, admin, '?key=' + encodeURIComponent(log.clips[0]))).status, 200);
});

test('the old paths without a track are the theory exam; a draft is for admins only', async () => {
  const f = await setup(1800), exam = createHphoExamRouter(deps);
  const s = await exam('/api/hpho/rounds/2027-1/exam/state', 'GET', null, student, f.env, new URL('https://x/'));
  assert.equal(s.window.track, 'theory');
  f.sql.prepare("UPDATE hpho_rounds SET status='draft'").run();
  assert.equal(await code(exam('/api/hpho/rounds/2027-1/exam/state', 'GET', null, student, f.env, new URL('https://x/'))), 'round_not_found');
  assert.equal((await exam('/api/hpho/rounds/2027-1/exam/state', 'GET', null, admin, f.env, new URL('https://x/'))).window.track, 'theory');
});

test('only flagged seats keep their recordings and proctoring photos', async () => {
  assert.deepEqual(suspicion({}, [{ kind: 'focus_lost' }, { kind: 'focus_lost' }]), [], 'a glance away twice is not a flag');
  assert.deepEqual(suspicion({}, [{ kind: 'phone_seen' }]), ['phone_seen×1']);
  assert.match(suspicion({}, [{ kind: 'process_new', detail: 'notepad.exe !anydesk.exe' }]).join(), /programs: !anydesk\.exe/);
  assert.deepEqual(suspicion({ verdict: 'review' }, []), ['verdict: review']);
  const WEBM = new Uint8Array([0x1a, 0x45, 0xdf, 0xa3, 1]);
  const f = await setup(1800);
  const other2 = { id: 11 };
  await f.reg('/api/hpho/rounds/2027-1/entry', 'POST', entry, other2, f.env);
  for (const who of [student, other2]) {
    await f.call('checkin', 'POST', { client }, who);
    await f.form('snap', { image: JPEG, source: 'webcam', reason: 'random' }, who);
  }
  await f.call('events', 'POST', { events: [{ seq: 1, kind: 'faces_multiple' }] }, other2);
  f.sql.prepare('UPDATE hpho_seats SET check_note=NULL').run();      /* as if both had passed the ear, voice and room checks */
  f.shift(-1801 - 300 * 60);
  assert.equal((await f.call('keep', 'POST', {}, student)).keep, false, 'not flagged: the recordings stay on the computer and are deleted there');
  assert.equal((await f.call('keep', 'POST', {}, other2)).keep, true);
  await f.form('clip', { clip: WEBM, source: 'screen' }, other2);
  await f.form('snap', { image: JPEG, source: 'webcam', reason: 'after_time' }, student);
  const keys = () => [...f.store.m.keys()].filter(k => /^hpho(-rec)?\//.test(k));
  assert.equal(keys().length, 4);
  assert.equal(await code(f.call('retain', 'POST', {}, admin)), 'not_over');
  const later = Date.now() + (3600 + 3600 + 60) * 1000;            /* the upload closed more than an hour ago */
  assert.equal((await hphoRetainTick(f.env, { now: Date.now() })).length, 0, 'not before the hour after the upload');
  const done = await hphoRetainTick(f.env, { now: later });
  assert.equal(done.length, 2);
  const kept = done.find(d => d.kept), gone = done.find(d => !d.kept);
  assert.match(kept.kept, /faces_multiple/); assert.equal(gone.deleted, 1);
  assert.equal(keys().length, 3, 'the flagged seat keeps its recording and photo; the other only its webcam after the time');
  assert.ok(keys().filter(k => !k.includes(kept.candidate_no)).every(k => /-webcam-after_time\.jpg$/.test(k)));
  assert.equal((await hphoRetainTick(f.env, { now: later })).length, 0, 'decided once');
});

test('the phone: paired by a QR code, scans the room view by view, then stands where it sees the candidate', async () => {
  let notes = false;
  const f = await setup(1800, { view: v => v === 'desk' && !notes ? (notes = true, { covered: true, found: ['phone'] }) : v === 'under' ? { covered: true, found: ['notes'] } : { covered: true, found: [] } });
  assert.equal(await code(f.phone('x'.repeat(30), 'state')), 'phone_not_found');
  const { code: c } = await f.call('phone', 'POST', {}, student);
  assert.match(c, /^[A-Za-z0-9_-]{32}$/);
  const s = await f.phone(c, 'state');
  assert.equal(s.candidate_no.startsWith('HP271-'), true); assert.equal(s.scanned, false);
  assert.equal((await f.call('phone', 'GET', null, student)).phone.online, true);
  assert.equal(await code(f.phone(c, 'state', null, 'another-phone-bbbbbbbb')), 'phone_in_use', 'a second phone cannot take the seat');
  const frames = { f0: JPEG, f1: JPEG, f2: JPEG, f3: JPEG };
  assert.equal(await code(f.phone(c, 'scan', { view: 'room', f0: JPEG })), 'too_few_frames');
  assert.equal(await code(f.phone(c, 'scan', { view: 'front', ...{ f0: JPEG, f1: JPEG, f2: JPEG } })), 'bad_view');
  const WEBP = new Uint8Array([...new TextEncoder().encode('RIFF'), 0, 0, 0, 0, ...new TextEncoder().encode('WEBPVP8 ')]);
  assert.equal((await f.phone(c, 'scan', { view: 'ceiling', f0: WEBP, f1: WEBP, f2: JPEG })).status, 'clear', 'WebP frames from the phone are taken');
  assert.equal((await f.phone(c, 'scan', { view: 'desk', ...frames })).status, 'blocked', 'a phone on the desk: remove it and sweep again');
  for (const view of PHONE_VIEWS) await f.phone(c, 'scan', { view, ...frames });
  const after = (await f.call('phone', 'GET', null, student)).phone;
  assert.equal(after.scanned, true); assert.equal(after.scan.under.status, 'notes');
  assert.equal((await f.phone(c, 'place', { image: JPEG })).placed, true);
  assert.equal((await f.phone(c, 'snap', { image: JPEG, reason: 'random' })).ok, true);
  /* the scan's record feeds the seat's checks: notes under the desk go to review */
  await f.form('earcheck', { front: JPEG, first: JPEG, second: JPEG });
  await f.form('voicecheck', { audio: wav(), lang: 'ko' });
  await f.call('checkin', 'POST', { client }, student);
  const seat = (await f.call('seats', 'GET', null, admin)).seats[0];
  assert.match(seat.check_note, /room: flag: phone · under=notes/);
  const m = await f.call('monitor', 'GET', null, admin);
  assert.match(m.seats[0].last_phone, /-phone-random\.jpg$/); assert.equal(m.seats[0].phone_online, true);
  /* a new code replaces the old one */
  const again = await f.call('phone', 'POST', {}, student);
  assert.equal(await code(f.phone(c, 'state')), 'phone_not_found');
  assert.equal((await f.phone(again.code, 'state')).scanned, true, 'the scan stays with the seat');
  assert.deepEqual(viewVerdict({ covered: false, person: false, phone: false, screen: false, headset: false, notes: false }).covered, false);
});

test('glasses shown up close: smart ones stop the candidate', async () => {
  const f = await setup(1800, { glass: { smart: true, clear: true } });
  assert.equal((await f.form('glasscheck', { front: JPEG, inside: JPEG })).smart, true);
  const g = await setup(1800);
  assert.deepEqual(await g.form('glasscheck', { front: JPEG, inside: JPEG }), { ok: true, smart: false, clear: true });
});

test('away for ten seconds during the exam: the seat goes to a person for review', async () => {
  const f = await setup(1800);
  await f.call('checkin', 'POST', { client }, student);
  const { code: c } = await f.call('phone', 'POST', {}, student);
  await f.phone(c, 'snap', { image: JPEG, reason: 'absent' });
  assert.equal((await f.call('log', 'GET', null, admin, '?candidate=' + (await f.call('seats', 'GET', null, admin)).seats[0].candidate_no)).events.filter(e => e.kind === 'absent').length, 0, 'not in the waiting room');
  f.shift(-1860);                                                   /* the exam has started */
  await f.phone(c, 'snap', { image: JPEG, reason: 'absent' });
  const no = (await f.call('seats', 'GET', null, admin)).seats[0].candidate_no;
  const log = await f.call('log', 'GET', null, admin, '?candidate=' + no);
  assert.ok(log.events.some(e => e.kind === 'absent' && /phone/.test(e.detail)));
  const { suspicion } = await import('./src/hpho-exam.js');
  assert.deepEqual(suspicion({}, [{ kind: 'absent' }]), ['absent×1'], 'one absence is enough');
});

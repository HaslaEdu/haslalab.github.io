import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createHphoRouter} from './src/hpho.js';
import {createHphoExamRouter, checkEvents, checkClient, UPLOAD_MIN} from './src/hpho-exam.js';

class HttpError extends Error { constructor(status, code) { super(code); this.status = status; this.code = code; } }
function d1() {
  const sql = new DatabaseSync(':memory:');
  const make = (q, args = []) => ({ bind: (...v) => make(q, v), async first() { return sql.prepare(q).get(...args) || null; },
    async all() { return { results: sql.prepare(q).all(...args) }; }, async run() { const r = sql.prepare(q).run(...args); return { meta: { changes: r.changes } }; } });
  return { sql, DB: { prepare: q => make(q), async batch(list) { for (const s of list) await s.run(); return []; } } };
}
const needUser = u => { if (!u) throw new HttpError(401, 'login_required'); return u; };
const deps = { HttpError, needUser, limit: async () => {}, isAdmin: u => u?.role === 'admin' };
const admin = { id: 1, role: 'admin' }, student = { id: 7 }, other = { id: 9 };
const client = { app: 'haslaedu-desktop', version: '0.5.0' };
const entry = { country: 'KR', level: 'high', birth_year: new Date().getUTCFullYear() - 20, pledge: true, proctoring: true, identity_notice: true };
const code = async p => { try { await p; return null; } catch (e) { return e.code; } };

async function setup(startOffset) {
  const { sql, DB } = d1(), env = { DB }, t = Math.floor(Date.now() / 1000);
  const reg = createHphoRouter(deps), exam = createHphoExamRouter(deps);
  await reg('/api/hpho/rounds/2027-1', 'POST', { title_ko: 'a', title_en: 'a', reg_open: t - 7200, reg_close: t + 3600, start_at: t + 7200, duration_min: 240, fee_usd: 3.5, status: 'open' }, admin, env);
  await reg('/api/hpho/rounds/2027-1/entry', 'POST', entry, student, env);
  /* then move the start to where the test wants it */
  sql.prepare('UPDATE hpho_rounds SET start_at=?').run(t + startOffset);
  const call = (action, m, body, me, query = '') => exam(`/api/hpho/rounds/2027-1/exam/${action}`, m, body, me, env, new URL('https://x/' + query));
  const callRaw = (action, form, store) => exam(`/api/hpho/rounds/2027-1/exam/${action}`, 'POST', {}, student, { ...env, HPHO_SNAPS: store }, new URL('https://x/'), new Request('https://x/', { method: 'POST', body: form }));
  return { sql, call, callRaw, t };
}

test('client and event checks', () => {
  assert.equal(checkClient(client), 'haslaedu-desktop/0.5.0');
  assert.equal(checkClient({ app: 'chrome', version: '1.0.0' }), null);
  assert.equal(checkEvents([{ seq: 1, t: 5, kind: 'focus_lost', detail: 'x\u0007y' }]).events[0].detail, 'x y');
  assert.equal(checkEvents([{ seq: 1, kind: 'rm -rf' }]).error, 'bad_events');
  assert.equal(checkEvents(Array.from({ length: 101 }, (_, i) => ({ seq: i, kind: 'heartbeat' }))).error, 'bad_events');
});

test('a session opens only at the start time, for a registered candidate, from the desktop app', async () => {
  const early = await setup(600);
  assert.equal(await code(early.call('start', 'POST', { client }, student)), 'not_started');
  const f = await setup(-60);
  assert.equal(await code(f.call('start', 'POST', { client }, other)), 'not_registered');
  assert.equal(await code(f.call('start', 'POST', {}, student)), 'desktop_app_required');
  const s = await f.call('start', 'POST', { client }, student);
  assert.match(s.candidate_no, /^HP271-\d{4}$/);
  assert.equal((await f.call('start', 'POST', { client }, student)).resumed, true, 'reopening the app resumes');
  const over = await setup(-240 * 60 - 1);
  assert.equal(await code(over.call('start', 'POST', { client }, student)), 'exam_over');
});

test('events are stored once each, a silent stretch is recorded by the server, and only an admin reads the log', async () => {
  const f = await setup(-60);
  await f.call('start', 'POST', { client }, student);
  await f.call('events', 'POST', { events: [{ seq: 1, t: f.t, kind: 'window_ready' }, { seq: 2, t: f.t, kind: 'focus_lost', detail: 'alt-tab' }] }, student);
  await f.call('events', 'POST', { events: [{ seq: 2, t: f.t, kind: 'focus_lost' }] }, student);     /* a resend */
  f.sql.prepare('UPDATE hpho_sessions SET last_beat=last_beat-120').run();
  const r = await f.call('events', 'POST', { events: [{ seq: 3, kind: 'heartbeat' }] }, student);
  assert.equal(r.gap, true);
  assert.equal(await code(f.call('log', 'GET', null, student, '?candidate=x')), 'forbidden');
  const no = f.sql.prepare('SELECT candidate_no FROM hpho_sessions').get().candidate_no;
  const log = await f.call('log', 'GET', null, admin, '?candidate=' + no);
  assert.deepEqual(log.events.filter(e => e.seq >= 0).map(e => e.kind), ['window_ready', 'focus_lost', 'heartbeat']);
  assert.equal(log.session.gaps, 1);
  assert.ok(log.events.some(e => e.seq < 0 && /no contact/.test(e.detail)));
  const end = await f.call('end', 'POST', {}, student);
  assert.ok(end.upload_until - log.session.ends_at === UPLOAD_MIN * 60);
});

test('snapshots: JPEG only, small, from a live session, stored under the candidate number', async () => {
  const f = await setup(-60);
  const puts = [];
  const env2 = { put: (k, v, o) => puts.push([k, v.length, o]) };
  const snap = (bytes, source = 'webcam', reason = 'random') => {
    const form = new FormData(); form.set('image', new Blob([bytes], { type: 'image/jpeg' })); form.set('source', source); form.set('reason', reason);
    return f.callRaw('snap', form, env2);
  };
  await f.call('start', 'POST', { client }, student);
  const jpeg = new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 1, 2, 3]);
  assert.equal((await snap(jpeg)).ok, true);
  assert.match(puts[0][0], /^hpho\/2027-1\/HP271-\d{4}\/\d+-webcam-random\.jpg$/);
  assert.equal(await code(snap(new Uint8Array([0x89, 0x50, 0x4e, 0x47]))), 'snapshot_not_jpeg');
  assert.equal(await code(snap(jpeg, 'microphone')), 'bad_snapshot');
  assert.equal(await code(snap(jpeg, 'screen', 'not a reason')), 'bad_snapshot');
  assert.equal(await code(snap(new Uint8Array(260 * 1024).fill(0xff))), 'snapshot_too_large');
  await f.call('end', 'POST', {}, student);
  assert.equal(await code(snap(jpeg)), 'exam_over');
});

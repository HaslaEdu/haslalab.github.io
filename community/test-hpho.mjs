import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createHphoRouter, checkEntry, checkRound, candidatePrefix, AID_ENABLED} from './src/hpho.js';

class HttpError extends Error { constructor(status, code) { super(code); this.status = status; this.code = code; } }
function d1() {
  const sql = new DatabaseSync(':memory:');
  const make = (q, args = []) => { const st = { get: (...a) => sql.prepare(q).get(...a), all: (...a) => sql.prepare(q).all(...a), run: (...a) => sql.prepare(q).run(...a) }; return {
    bind: (...v) => make(q, v), async first() { return st.get(...args) || null; }, async all() { return { results: st.all(...args) }; },
    async run() { const r = st.run(...args); return { meta: { changes: r.changes } }; } }; };
  return { sql, DB: { prepare: q => make(q), async batch(list) { for (const s of list) await s.run(); return []; } } };
}
const needUser = u => { if (!u) throw new HttpError(401, 'login_required'); return u; };
const router = () => { const { sql, DB } = d1(); const env = { DB };
  const r = createHphoRouter({ HttpError, needUser, limit: async () => {}, isAdmin: u => u?.role === 'admin' });
  return { sql, call: (p, m, body, me) => r(p, m, body, me, env) }; };
const admin = { id: 1, role: 'admin' }, student = { id: 7 }, t = Math.floor(Date.now() / 1000);
const round = { title_ko: '제1회 HPhO', title_en: 'HPhO 2027-I', reg_open: t - 3600, reg_close: t + 86400, start_at: t + 2 * 86400, duration_min: 240, fee_usd: 3, status: 'open' };
const entry = { country: 'kr', level: 'high', birth_year: new Date().getUTCFullYear() - 17, pledge: true, proctoring: true, identity_notice: true, guardian_consent: true };
const code = async p => { try { await p; return null; } catch (e) { return e.code; } };

test('candidate numbers carry the round and four random digits', () => {
  assert.equal(candidatePrefix('2027-1'), 'HP271-');
  assert.equal(candidatePrefix('2027-3'), null);
});

test('a round keeps the owner\'s $5 cap and a sane timetable', () => {
  assert.equal(checkRound('2027-1', round).fee_usd, 3);
  assert.equal(checkRound('2027-1', { ...round, fee_usd: 5.01 }).error, 'bad_fee');
  assert.equal(checkRound('2027-1', { ...round, reg_close: round.start_at + 1 }).error, 'bad_time_order');
  assert.equal(checkRound('27-1', round).error, 'bad_round');
});

test('registration asks for the pledge, the proctoring consent, the identity notice and, for minors, a guardian', () => {
  assert.equal(checkEntry(entry).country, 'KR');
  for (const [k, err] of [['pledge', 'pledge_required'], ['proctoring', 'proctoring_consent_required'], ['identity_notice', 'identity_notice_required'], ['guardian_consent', 'guardian_consent_required']])
    assert.equal(checkEntry({ ...entry, [k]: false }).error, err);
  assert.equal(checkEntry({ ...entry, birth_year: new Date().getUTCFullYear() - 25, guardian_consent: false }).guardian_consent, 0);
  assert.equal(checkEntry({ ...entry, country: 'Korea' }).error, 'bad_country');
});

test('rounds, registration, withdrawal and the admin list', async () => {
  const f = router();
  assert.equal(await code(f.call('/api/hpho/rounds/2027-1', 'POST', round, student)), 'forbidden');
  await f.call('/api/hpho/rounds/2027-1', 'POST', round, admin);
  await f.call('/api/hpho/rounds/2026-2', 'POST', { ...round, title_ko: '초안', status: 'draft' }, admin);
  const pub = await f.call('/api/hpho', 'GET', null, null);
  assert.deepEqual(pub.rounds.map(r => r.id), ['2027-1'], 'a draft is never public');
  assert.equal(await code(f.call('/api/hpho/rounds/2027-1/entry', 'POST', entry, null)), 'login_required');
  const reg = await f.call('/api/hpho/rounds/2027-1/entry', 'POST', entry, student);
  assert.match(reg.candidate_no, /^HP271-\d{4}$/);
  const again = await f.call('/api/hpho/rounds/2027-1/entry', 'POST', { ...entry, level: 'middle' }, student);
  assert.equal(again.candidate_no, reg.candidate_no, 'editing keeps the number');
  assert.equal((await f.call('/api/hpho', 'GET', null, student)).entries['2027-1'].level, 'middle');
  assert.equal(await code(f.call('/api/hpho/rounds/2026-2/entry', 'POST', entry, student)), 'round_not_found');
  assert.equal(await code(f.call('/api/hpho/rounds/2027-1/entries', 'GET', null, student)), 'forbidden');
  assert.equal((await f.call('/api/hpho/rounds/2027-1/entries', 'GET', null, admin)).count, 1);
  await f.call('/api/hpho/rounds/2027-1/entry', 'DELETE', null, student);
  assert.equal((await f.call('/api/hpho/rounds/2027-1/entries', 'GET', null, admin)).count, 0);
  await f.call('/api/hpho/rounds/2027-1', 'POST', { ...round, reg_close: t - 1, reg_open: t - 7200 }, admin);
  assert.equal(await code(f.call('/api/hpho/rounds/2027-1/entry', 'POST', entry, student)), 'registration_closed');
});

test('while assistance is on hold every candidate owes the fee', () => {
  if (AID_ENABLED) return;
  assert.equal(checkEntry({ ...entry, country: 'NP' }).aid, 'none');
  assert.equal(checkEntry({ ...entry, aid_request: true, aid_reason: 'family_income', aid_note: '가계 형편이 어려워 참가비가 부담됩니다.' }).aid, 'none');
});

test('fee assistance: automatic for low- and lower-middle-income economies, otherwise a request an admin decides', { skip: !AID_ENABLED && 'assistance is on hold' }, async () => {
  assert.equal(checkEntry({ ...entry, country: 'NP' }).aid, 'auto');
  assert.equal(checkEntry(entry).aid, 'none');
  assert.equal(checkEntry({ ...entry, aid_request: true, aid_reason: 'nope', aid_note: '집안 형편이 어렵습니다.' }).error, 'bad_aid_reason');
  assert.equal(checkEntry({ ...entry, aid_request: true, aid_reason: 'family_income', aid_note: '짧음' }).error, 'aid_note_required');
  const f = router();
  await f.call('/api/hpho/rounds/2027-1', 'POST', round, admin);
  const auto = await f.call('/api/hpho/rounds/2027-1/entry', 'POST', { ...entry, country: 'VN' }, { id: 8 });
  assert.equal(auto.fee_due, 0);
  const req = await f.call('/api/hpho/rounds/2027-1/entry', 'POST', { ...entry, aid_request: true, aid_reason: 'family_income', aid_note: '가계 형편이 어려워 참가비가 부담됩니다.' }, student);
  assert.deepEqual([req.aid, req.fee_due], ['pending', 3]);
  assert.equal(await code(f.call('/api/hpho/rounds/2027-1/aid', 'POST', { candidate_no: req.candidate_no, decision: 'approved' }, student)), 'forbidden');
  await f.call('/api/hpho/rounds/2027-1/aid', 'POST', { candidate_no: req.candidate_no, decision: 'approved' }, admin);
  assert.equal((await f.call('/api/hpho', 'GET', null, student)).entries['2027-1'].fee_due, 0);
  const edit = await f.call('/api/hpho/rounds/2027-1/entry', 'POST', { ...entry, level: 'middle', aid_request: true, aid_reason: 'family_income', aid_note: '가계 형편이 어려워 참가비가 부담됩니다.' }, student);
  assert.equal(edit.aid, 'approved', 'editing other fields keeps the decision');
  assert.equal(await code(f.call('/api/hpho/rounds/2027-1/aid', 'POST', { candidate_no: auto.candidate_no, decision: 'declined' }, admin)), 'no_aid_request', 'automatic assistance is not up for decision');
  const list = await f.call('/api/hpho/rounds/2027-1/entries', 'GET', null, admin);
  assert.deepEqual([list.aid.auto, list.aid.approved], [1, 1]);
});

test('the assistance columns are added to a table created before them', async () => {
  const { sql, DB } = d1();
  sql.exec(`CREATE TABLE hpho_entries (round_id TEXT NOT NULL, user_id INTEGER NOT NULL, candidate_no TEXT NOT NULL, country TEXT NOT NULL, level TEXT NOT NULL, birth_year INTEGER NOT NULL, guardian_consent INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, PRIMARY KEY (round_id, user_id))`);
  const r = createHphoRouter({ HttpError, needUser, limit: async () => {}, isAdmin: u => u?.role === 'admin' });
  await r('/api/hpho', 'GET', null, null, { DB });
  assert.ok(sql.prepare('PRAGMA table_info(hpho_entries)').all().some(c => c.name === 'aid'));
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createHphoRouter, checkEntry, checkRound, candidatePrefix} from './src/hpho.js';

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

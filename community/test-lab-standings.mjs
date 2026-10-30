// Exercise the real private report routes against local SQLite. No AI, network or production data.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import worker from './src/index.js';

const sqlite = new DatabaseSync(':memory:');
for (const file of readdirSync(new URL('./migrations/', import.meta.url)).filter(n => /^\d{4}_.*\.sql$/.test(n)).sort())
  sqlite.exec(readFileSync(new URL('./migrations/' + file, import.meta.url), 'utf8'));
const DB = {
  prepare(query) {
    const st = sqlite.prepare(query), make = args => ({
      bind: (...bound) => make(bound),
      async first() { return st.get(...args) || null; },
      async all() { return { results: st.all(...args) }; },
      async run() { return this.executeSync(); },
      executeSync() {
        if (st.columns().length) return { results: st.all(...args) };
        const r = st.run(...args); return { success: true, meta: { changes: r.changes, last_row_id: Number(r.lastInsertRowid) } };
      },
    });
    return make([]);
  },
  async batch(statements) {
    sqlite.exec('BEGIN');
    try { const results = statements.map(s => s.executeSync()); sqlite.exec('COMMIT'); return results; }
    catch (error) { sqlite.exec('ROLLBACK'); throw error; }
  },
};
const timestamp = Math.floor(Date.now() / 1000), tokens = {}, env = { DB, LAB_KEEP_HOURS: 'off' };
for (let id = 1; id <= 20; id++) {
  sqlite.prepare("INSERT INTO users(id,username,nickname,pw,role,created_at) VALUES(?,?,?,'unused','user',?)")
    .run(id, 'sample' + id, 'Sample ' + id, timestamp);
  const token = ('sample_' + id).padEnd(48, 'x'); tokens[id] = token;
  const hash = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(token))).toString('base64url');
  sqlite.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)').run(hash, id, timestamp, timestamp + 3600);
}
globalThis.caches = { default: { async match() {}, async put() {} } };
const originalFetch = globalThis.fetch;
globalThis.fetch = () => { throw new Error('Unexpected external request'); };
test.after(() => { globalThis.fetch = originalFetch; sqlite.close(); });
test.beforeEach(() => { sqlite.exec('DELETE FROM lab_sessions'); });

function seed({ user = 1, comp = 'ipho', year = 2024, exam_key = comp + year, tasks = ['T1'], review = false,
  score = 5, points, maxima = Object.fromEntries(tasks.map(task => [task, 10])), criteria, detail, sources, status = 'graded', ...extra } = {}) {
  points ??= Object.values(maxima).reduce((sum, value) => sum + value, 0);
  let remaining = score;
  const per = Object.fromEntries(tasks.map(task => {
    const got = Math.min(remaining ?? 0, maxima[task]); remaining -= got;
    return [task, { status: 'graded', score: got, points: maxima[task], items: [{ id: criteria || 'A', points: maxima[task], got }] }];
  }));
  const src = sources || Object.fromEntries(tasks.map(task => [task, { kind: 'theory', sol: `IPhO_${year}_${task}S.pdf` }]));
  if (review) src._review = 1;
  const fields = { user_id: user, exam_key, comp, year, tasks: JSON.stringify(tasks), sources: JSON.stringify(src),
    started_at: timestamp - 100, ended_at: timestamp - 50, scan_until: timestamp - 10, upload_hash: crypto.randomUUID(),
    status, charged: 1, score, points, detail: detail === undefined ? JSON.stringify({ tasks: per }) : detail,
    created_at: timestamp - 100, graded_at: status === 'graded' ? timestamp : null, ...extra };
  const keys = Object.keys(fields), result = sqlite.prepare(`INSERT INTO lab_sessions(${keys.join(',')}) VALUES(${keys.map(() => '?').join(',')})`).run(...Object.values(fields));
  return Number(result.lastInsertRowid);
}
async function request(path, user = 1, body) {
  const response = await worker.fetch(new Request('https://worker.local/api' + path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { ...(user ? { Authorization: 'Bearer ' + tokens[user] } : {}), ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  }), env);
  return { status: response.status, data: await response.json(), headers: response.headers };
}
async function report(id, user = 1) {
  const r = await request('/lab/sessions/' + id, user); assert.equal(r.status, 200, JSON.stringify(r.data)); return r.data.session;
}

test('timed and review cohorts stay strictly separate; both reports disclose their sample', async () => {
  const timed = seed(), review = seed({ user: 2, review: true, score: 9 });
  seed({ user: 3, score: 8 }); seed({ user: 4, review: true, score: 1 });
  const a = await report(timed), b = await report(review, 2);
  assert.equal(a.sample_standing.cohort, 'timed'); assert.equal(a.sample_standing.n, 2); assert.equal(a.sample_standing.rank, 2);
  assert.equal(a.sample_standing.avg, 65); assert.deepEqual(a.standing, a.sample_standing);
  assert.equal(b.standing, null); assert.equal(b.sample_standing.cohort, 'review'); assert.equal(b.sample_standing.n, 2);
  assert.equal(b.sample_standing.rank, 1); assert.equal(b.sample_standing.avg, 50); assert.ok(b.sample_standing.cohort_label.ko);
});

test('each user contributes their first qualifying attempt; retries count the selected candidate exactly once', async () => {
  const first = seed({ score: 2 }); seed({ user: 2, score: 6 }); seed({ user: 2, score: 10 });
  const retry = seed({ score: 9 }); seed({ user: 3, score: 8, status: 'pending' }); seed({ user: 3, score: 4 });
  const initial = (await report(first)).sample_standing, later = (await report(retry)).sample_standing;
  assert.equal(initial.n, 3); assert.equal(initial.rank, 3); assert.equal(initial.first, true);
  assert.equal(later.n, 3); assert.equal(later.rank, 1); assert.equal(later.first, false); assert.equal(later.avg, 63.3);
  assert.equal(later.basis, 'each_user_first_graded');
});

test('ties share their rank and zero scores are valid observations', async () => {
  const id = seed({ score: 0 }); seed({ user: 2, score: 0 }); seed({ user: 3, score: 5 });
  const standing = (await report(id)).sample_standing;
  assert.equal(standing.n, 3); assert.equal(standing.rank, 2); assert.equal(standing.top_pct, 66.7);
  assert.equal(standing.percentile, 0); assert.equal(standing.mine, 0); assert.equal(standing.avg, 16.7);
});

test('singleton samples keep rank but do not fabricate percentile or top percentage', async () => {
  const sample = (await report(seed())).sample_standing;
  assert.equal(sample.n, 1); assert.equal(sample.rank, 1); assert.equal(sample.top_pct, null); assert.equal(sample.percentile, null);
});

test('historical floating-point residue cannot split a fractional shared rank', async () => {
  const id = seed({ score: 0.3 }); seed({ user: 2, score: 0.1 + 0.2 }); seed({ user: 3, score: 0.30001 });
  const standing = (await report(id)).sample_standing;
  assert.equal(standing.n, 3); assert.equal(standing.rank, 2); assert.equal(standing.top_pct, 66.7); assert.equal(standing.percentile, 0);
});

test('normalized task sets ignore JSON formatting and order while keeping partial sets apart', async () => {
  const id = seed({ tasks: ['T1','T2'], score: 12 });
  const reversed = seed({ user: 2, tasks: ['T2','T1'], score: 8, detail: JSON.stringify({ tasks: {
    T1: { status: 'graded', points: 10, score: 4, items: [{ id: 'A', points: 10 }] },
    T2: { status: 'graded', points: 10, score: 4, items: [{ id: 'A', points: 10 }] },
  } }) });
  sqlite.prepare('UPDATE lab_sessions SET tasks=? WHERE id=?').run('[ "T2", "T1" ]', reversed);
  seed({ user: 3, tasks: ['T1'], maxima: { T1: 20 }, score: 9 }); // Same total maximum, different/partial task set.
  const sample = (await report(id)).sample_standing;
  assert.equal(sample.n, 2); assert.equal(sample.avg, 50);
});

test('different competition, year, round, total maximum, task maximum and rubric never mix', async () => {
  const id = seed({ tasks: ['T1','T2'], maxima: { T1: 10, T2: 20 }, score: 15 });
  const base = { tasks: ['T1','T2'], maxima: { T1: 10, T2: 20 }, score: 20 };
  seed({ ...base, user: 2, comp: 'apho', exam_key: 'ipho2024' });
  seed({ ...base, user: 3, year: 2025, exam_key: 'ipho2024' });
  seed({ ...base, user: 4, exam_key: 'ipho2024:round2' });
  seed({ ...base, user: 5, maxima: { T1: 10, T2: 30 } });
  seed({ ...base, user: 6, maxima: { T1: 20, T2: 10 } });
  seed({ ...base, user: 7, criteria: 'B' });
  seed({ ...base, user: 8, sources: { T1: { kind: 'theory', sol: 'IPhO_2024_T1AS.pdf' }, T2: { kind: 'theory', sol: 'IPhO_2024_T2S.pdf' } } });
  seed({ ...base, user: 9 });
  const sample = (await report(id)).sample_standing;
  assert.equal(sample.n, 2); assert.equal(sample.rank, 2); assert.equal(sample.avg, 58.3);
});

test('complete saved rubrics keep empty zero answers comparable to full-mark answers', async () => {
  const id = seed({ score: 0, detail: JSON.stringify({ tasks: { T1: { status: 'empty', score: 0, points: 10, comparison_rubric: [['A',10]], pages: 0 } } }) });
  seed({ user: 2, score: 10 });
  const sample = (await report(id)).sample_standing;
  assert.equal(sample.n, 2); assert.equal(sample.mine, 0); assert.equal(sample.rank, 2);
});

test('qualitative, null, pending, malformed and contest results never enter numeric samples', async () => {
  const id = seed();
  const invalid = [
    { score: null }, { points: 0 }, { status: 'pending' }, { status: 'error' }, { score: -1 }, { score: 11 },
    { detail: JSON.stringify({ tasks: { T1: { status: 'graded', score: 5, points: 10, grading_mode: 'qualitative_review' } } }) },
    { detail: JSON.stringify({ tasks: { T1: { status: 'pending', score: 5, points: 10 } } }) },
    { exam_key: 'contest:ipho2024' },
  ];
  for (const [i, values] of invalid.entries()) {
    const other = seed({ user: i + 2, ...values });
    assert.equal((await report(other, i + 2)).sample_standing, null, JSON.stringify(values));
  }
  seed({ user: 12, detail: '{bad json' }); // Corrupt historical detail must not contaminate another report's cohort.
  assert.equal((await report(id)).sample_standing.n, 1);
});

test('historical numeric totals lacking a verifiable rubric show only their own observation', async () => {
  const id = seed({ detail: null }); seed({ user: 2, detail: null }); seed({ user: 3 });
  const sample = (await report(id)).sample_standing;
  assert.equal(sample.n, 1); assert.equal(sample.rank, 1); assert.equal(sample.top_pct, null);
});

test('selected bootstrap and direct GET expose identical private sample data without answers or identities', async () => {
  const id = seed({ review: true }); seed({ user: 2, review: true, score: 8 });
  const direct = await request('/lab/sessions/' + id), bootstrap = await request('/lab/bootstrap?include=sessions,health&id=' + id);
  assert.equal(bootstrap.status, 200); assert.deepEqual(bootstrap.data.session.sample_standing, direct.data.session.sample_standing);
  assert.equal(bootstrap.data.session.standing, null); assert.equal(direct.headers.get('Cache-Control'), 'no-store');
  assert.doesNotMatch(JSON.stringify(bootstrap.data.session.sample_standing), /user_id|Sample 2|upload_hash|sources|detail/);
  assert.equal((await request('/lab/sessions/' + id, 2)).status, 404);
  assert.equal((await request('/lab/bootstrap?id=' + id, 2)).status, 404);
  assert.equal((await request('/lab/sessions/' + id, null)).status, 401);
});

test('idempotent submission of an already graded review returns its sample without another charge', async () => {
  const id = seed({ review: true }); seed({ user: 2, review: true, score: 8 });
  const before = await report(id), credit = (await request('/lab/tokens')).data.tokens;
  const submitted = await request('/lab/sessions/' + id + '/submit', 1, { grade: true });
  assert.equal(submitted.status, 200); assert.equal(submitted.data.queued, false); assert.equal(submitted.data.session.status, 'graded');
  assert.deepEqual(submitted.data.session.sample_standing, before.sample_standing); assert.equal(submitted.data.session.standing, null);
  assert.equal(submitted.data.session.sample_standing.n, 2); assert.equal(submitted.data.tokens, credit);
  assert.equal(sqlite.prepare('SELECT COUNT(*) AS n FROM lab_ledger').get().n, 0);
});

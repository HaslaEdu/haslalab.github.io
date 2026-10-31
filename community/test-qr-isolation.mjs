// Real Worker + local SQLite. Never calls a provider, remote database or production URL.
import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import worker from './src/index.js';

const digest = async value => Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))).toString('base64url');
async function fixture(run) {
  const sql = new DatabaseSync(':memory:');
  for (const file of readdirSync(new URL('./migrations/', import.meta.url)).filter(file => /^\d{4}_.*\.sql$/.test(file)).sort()) sql.exec(readFileSync(new URL('./migrations/' + file, import.meta.url), 'utf8'));
  let beforeQrWrite, clock = 1793444400, externalCalls = 0;
  const queries = [], queued = [], tokens = {};
  const DB = { prepare(query) {
    const statement = sql.prepare(query), make = args => ({ query, bind: (...values) => make(values),
      async first() { queries.push(query); return statement.get(...args) || null; },
      async all() { queries.push(query); return { results: statement.all(...args) }; },
      async run() {
        if (/^UPDATE lab_sessions SET upload_hash=\? WHERE id=\?/.test(query) && beforeQrWrite) {
          const hook = beforeQrWrite; beforeQrWrite = null; await hook();
        }
        return this.executeSync();
      },
      executeSync() { queries.push(query); if (statement.columns().length) return { results: statement.all(...args) };
        const result = statement.run(...args); return { results: [], meta: { changes: result.changes, last_row_id: Number(result.lastInsertRowid) } }; },
    }); return make([]);
  }, async batch(statements) {
    sql.exec('BEGIN'); try { const results = statements.map(statement => statement.executeSync()); sql.exec('COMMIT'); return results; }
    catch (error) { sql.exec('ROLLBACK'); throw error; }
  } };
  for (const id of [1, 2, 3]) {
    tokens[id] = ('qr_local_account_' + id).padEnd(48, 'x');
    sql.prepare("INSERT INTO users(id,username,nickname,pw,role,created_at,exam_tokens,token_parts) VALUES(?,?,?,'unused','user',?,5,50)")
      .run(id, 'qr' + id, 'QR ' + id, clock);
    sql.prepare('INSERT INTO sessions VALUES(?,?,?,?)').run(await digest(tokens[id]), id, clock, clock + 86400);
  }
  const saved = { fetch: globalThis.fetch, caches: globalThis.caches, now: Date.now };
  globalThis.fetch = () => { externalCalls++; throw new Error('QR tests must never call external services'); };
  globalThis.caches = { default: { async match() {}, async put() {} } }; Date.now = () => clock * 1000;
  const env = { DB, GEMINI_API_KEY:'local-mock-only', LAB_KEEP_HOURS: 'off', LAB_JOBS: { async sendBatch(items) { queued.push(...items); } } };
  const api = async (path, { user = 1, body, method = body === undefined ? 'GET' : 'POST', headers = {} } = {}) => {
    const response = await worker.fetch(new Request('https://qr.local/api' + path, { method,
      headers: { 'Cache-Control': 'no-cache', ...(user ? { Authorization: 'Bearer ' + tokens[user] } : {}),
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...headers },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }) }), env);
    return { status: response.status, data: await response.json(), headers: response.headers };
  };
  const start = async user => api('/lab/start', { user, body: { provider:'gemini',comp: 'ipho', year: 2025, tasks: ['E1'] } });
  const phone = async (token, id) => api('/lab/up' + (id ? '/' + id : ''), { user: null, headers: { 'X-Lab-Token': token } });
  try { await run({ sql, api, start, phone, queries, queued, beforeQrWrite: hook => { beforeQrWrite = hook; }, time: value => { clock = value; } });
    assert.equal(externalCalls, 0);
  } finally { Object.assign(globalThis, { fetch: saved.fetch, caches: saved.caches }); Date.now = saved.now; sql.close(); }
}

test('different accounts starting the same exam concurrently have distinct QR grants, session ownership and hashes', async () => {
  await fixture(async ({ start, phone, api, sql }) => {
    const [a, b] = await Promise.all([start(1), start(2)]);
    assert.equal(a.status, 200); assert.equal(b.status, 200);
    const first = a.data, second = b.data;
    assert.notEqual(first.session.id, second.session.id); assert.notEqual(first.token, second.token);
    assert.equal((await phone(first.token)).data.id, first.session.id);
    assert.equal((await phone(second.token)).data.id, second.session.id);
    assert.equal((await phone(first.token, second.session.id)).status, 403);
    assert.equal((await phone(second.token, first.session.id)).status, 403);
    assert.equal((await api('/lab/sessions/' + first.session.id, { user: 2 })).status, 404);
    assert.equal((await api('/lab/sessions/' + first.session.id + '/qr', { user: 2, body: {} })).status, 404);
    assert.equal((await api('/lab/sessions/' + first.session.id, { user: null, headers: { 'X-Lab-Token': first.token } })).status, 401);
    const rows = sql.prepare('SELECT upload_hash FROM lab_sessions ORDER BY id').all();
    assert.ok(rows.every(row => row.upload_hash !== first.token && row.upload_hash !== second.token));
    assert.notEqual(rows[0].upload_hash, rows[1].upload_hash);
    const firstHash = sql.prepare('SELECT upload_hash FROM lab_sessions WHERE id=?').get(first.session.id).upload_hash;
    assert.throws(() => sql.prepare('UPDATE lab_sessions SET upload_hash=? WHERE id=?').run(firstHash, second.session.id), /UNIQUE/);
  });
});

test('parallel starts for one account resume one session and hand out the initial QR only to its creator', async () => {
  await fixture(async ({ start, sql }) => {
    const results = await Promise.all(Array.from({ length: 6 }, () => start(1)));
    assert.ok(results.every(result => result.status === 200));
    assert.equal(new Set(results.map(result => result.data.session.id)).size, 1);
    assert.equal(results.filter(result => result.data.token).length, 1);
    assert.equal(sql.prepare('SELECT COUNT(*) AS n FROM lab_sessions WHERE user_id=1').get().n, 1);
  });
});

test('monthly QR capabilities remain separate across simultaneous users and bind the complete ID-secret pair to one problem', async () => {
  await fixture(async ({ api, time }) => {
    time(Date.parse('2026-11-01T12:00:00+09:00') / 1000);
    const [a, b] = await Promise.all([1, 2].map(user => api('/monthly/problems/4/scan', { user, body: {provider:'gemini'} })));
    assert.equal(a.status, 200); assert.equal(b.status, 200);
    const first = a.data.scan, second = b.data.scan;
    assert.notEqual(first.id, second.id); assert.notEqual(first.token, second.token);
    const phone = token => api('/monthly/up', { user: null, headers: { 'X-Lab-Token': token } });
    assert.equal((await phone(first.token)).data.id, first.id); assert.equal((await phone(second.token)).data.id, second.id);
    const wrongPair = second.id + '.' + first.token.split('.')[1];
    assert.equal((await phone(wrongPair)).status, 403);
    assert.equal((await api('/monthly/problems/4/scan?scan_id=' + first.id, { user: 2 })).status, 404);
    assert.equal((await api('/monthly/problems/5/scan?scan_id=' + first.id)).status, 404);
    const anotherProblem = await api('/monthly/problems/5/scan', { body: {provider:'gemini'} });
    assert.equal(anotherProblem.status, 200); assert.notEqual(anotherProblem.data.scan.token, first.token);
    assert.equal((await phone(first.token)).data.problem_id, 4, 'opening another problem must not redirect an existing grant');
    assert.equal((await phone(anotherProblem.data.scan.token)).data.problem_id, 5);
    assert.equal((await phone(second.token)).data.id, second.id);
  });
});

test('QR rotation invalidates only that account’s old token and preserves other users’ phone grants', async () => {
  await fixture(async ({ start, api, phone }) => {
    const a = (await start(1)).data, b = (await start(2)).data;
    const changed = await api('/lab/sessions/' + a.session.id + '/qr', { body: {} });
    assert.equal(changed.status, 200); assert.notEqual(changed.data.token, a.token);
    assert.equal((await phone(a.token)).status, 403);
    assert.equal((await phone(changed.data.token)).data.id, a.session.id);
    assert.equal((await phone(b.token)).data.id, b.session.id);
    assert.equal((await phone(changed.data.token)).headers.get('Cache-Control'), 'no-store');
  });
});

test('a concurrent accepted end or grading transition cannot be overwritten by an older QR renewal', async () => {
  for (const grade of [false, true]) await fixture(async ({ start, api, phone, sql, beforeQrWrite }) => {
    const a = (await start(1)).data, id = a.session.id;
    assert.equal((await api('/lab/sessions/' + id + '/finish', { body: {} })).status, 200);
    let retired;
    beforeQrWrite(async () => {
      const ended = await api('/lab/sessions/' + id + '/submit', { body: { grade } });
      assert.equal(ended.status, 200); assert.equal(ended.data.session.status, grade ? 'grading' : 'ended');
      retired = sql.prepare('SELECT upload_hash FROM lab_sessions WHERE id=?').get(id).upload_hash;
      assert.ok(retired.startsWith('void:'));
    });
    const renewal = await api('/lab/sessions/' + id + '/qr', { body: {} });
    assert.equal(renewal.status, 409); assert.equal(renewal.data.error, 'closed'); assert.equal(renewal.data.token, undefined);
    assert.equal(sql.prepare('SELECT upload_hash FROM lab_sessions WHERE id=?').get(id).upload_hash, retired);
    assert.equal((await phone(a.token)).status, 410);
  });
});

test('expired scanning windows and already revoked grants cannot be renewed even if an old request saw an active row', async () => {
  await fixture(async ({ start, api, phone, sql, time }) => {
    const a = (await start(1)).data, id = a.session.id;
    const finished = await api('/lab/sessions/' + id + '/finish', { body: {} });
    time(finished.data.session.scan_until + 121);
    assert.equal((await api('/lab/sessions/' + id + '/qr', { body: {} })).status, 409);
    assert.equal((await phone(a.token)).status, 410);
    const b = (await start(2)).data;
    sql.prepare("UPDATE lab_sessions SET upload_hash='void:'||upload_hash WHERE id=?").run(b.session.id);
    const before = sql.prepare('SELECT upload_hash FROM lab_sessions WHERE id=?').get(b.session.id).upload_hash;
    assert.equal((await api('/lab/sessions/' + b.session.id + '/qr', { user: 2, body: {} })).status, 409);
    assert.equal(sql.prepare('SELECT upload_hash FROM lab_sessions WHERE id=?').get(b.session.id).upload_hash, before);
  });
});

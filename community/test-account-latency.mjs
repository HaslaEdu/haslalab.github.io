// Exercise the real Worker against local SQLite; no provider or production calls.
import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import worker from './src/index.js';
import { publicRead, invalidatePublicReads } from './src/public-read-cache.js';

const sql = new DatabaseSync(':memory:');
for (const name of readdirSync(new URL('./migrations/', import.meta.url)).filter(n => /^\d{4}_.*\.sql$/.test(n)).sort()) sql.exec(readFileSync(new URL('./migrations/' + name, import.meta.url), 'utf8'));
const metadata = () => ({ timings: { sql_duration_ms: 0.125 }, rows_read: 1, served_by_region: 'LOCAL', served_by_primary: true });
const DB = {
  prepare(query) {
    const st = sql.prepare(query), make = args => ({
      bind: (...a) => make(a),
      async first() { return st.get(...args) || null; },
      async all() { return { results: st.all(...args), meta: metadata() }; },
      async run() { return this.executeSync(); },
      executeSync() {
        if (st.columns().length) return { results: st.all(...args), meta: metadata() };
        const r = st.run(...args);
        return { results: [], meta: { ...metadata(), changes: r.changes, last_row_id: Number(r.lastInsertRowid) } };
      },
    });
    return make([]);
  },
  async batch(sts) {
    sql.exec('BEGIN');
    try { const result = sts.map(st => st.executeSync()); sql.exec('COMMIT'); return result; }
    catch (e) { sql.exec('ROLLBACK'); throw e; }
  },
};
const cache = new Map(), env = { DB, ALLOWED_ORIGINS: 'https://haslalab.org', LAB_KEEP_HOURS: 'off' };
globalThis.caches = { default: { async match(k) { return cache.get(k.url)?.clone(); }, async put(k, v) { cache.set(k.url, v.clone()); } } };
const t = Math.floor(Date.now() / 1000), tokens = {};
for (let id = 1; id <= 2; id++) {
  tokens[id] = ('local_account_' + id).padEnd(48, 'x');
  const hash = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(tokens[id]))).toString('base64url');
  sql.prepare("INSERT INTO users(id,username,nickname,pw,role,created_at,exam_tokens,exam_half,token_parts) VALUES(?,?,?,'test-private-hash','user',?,?,1,2)").run(id, 'account' + id, 'Account ' + id, t, id * 3);
  sql.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)').run(hash, id, t, t + 3600);
  sql.prepare('INSERT INTO identities(provider,sub,user_id,created_at) VALUES(?,?,?,?)').run('google', 'private-sub-' + id, id, t);
  sql.prepare("INSERT INTO lab_sessions(user_id,exam_key,comp,year,tasks,started_at,ended_at,scan_until,upload_hash,status,created_at) VALUES(?,'ipho2024','ipho',2024,'[\"E1\"]',?,?,?,?,'running',?)").run(id, t, t + 18000, t + 19800, 'private-upload-' + id, t);
}
sql.prepare("INSERT INTO problems(id,week,kind,title_ko,title_en,body_ko,body_en,answer,model_ko,opens_at,closes_at,created_at) VALUES(999,'2099-W01','short','공개 제목','Public title','private body','private body','{\"value\":2}','private model',?,?,?)").run(t - 60, t + 3600, t);
for (const [id, score] of [[1, 70], [2, 20]]) sql.prepare("INSERT INTO submissions(problem_id,user_id,answer,status,score,in_week,created_at) VALUES(999,?,?,'graded',?,1,?)").run(id, 'private-answer-' + id, score, t);
const originalFetch = globalThis.fetch;
globalThis.fetch = () => { throw new Error('unexpected external request'); };
test.after(() => { globalThis.fetch = originalFetch; sql.close(); });
async function api(path, { id = 1, method = 'GET', body, headers = {} } = {}) {
  const r = await worker.fetch(new Request('https://worker.local/api' + path, { method, headers: { ...(id ? { Authorization: 'Bearer ' + tokens[id] } : {}), ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...headers }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) }), env);
  return { status: r.status, data: await r.json(), headers: r.headers };
}
const trips = r => Number(/db;desc="(\d+) queries"/.exec(r.headers.get('Server-Timing'))[1]);

test('one overview isolates account sections and never caches private data', async () => {
  const a = await api('/me/overview?user_id=2');
  assert.equal(a.status, 200); assert.equal(a.data.user.nickname, 'Account 1');
  assert.equal(a.data.tokens, 3.5); assert.equal(a.data.parts, 2); assert.equal(a.data.has_password, true);
  assert.deepEqual(a.data.identities.map(x => x.provider), ['google']);
  assert.equal(a.data.stats.subs[0].score, 70); assert.equal(a.data.active.id, 1); assert.equal(a.data.health.v, 5);
  assert.doesNotMatch(JSON.stringify(a.data), /private-(?:sub|upload|answer)-|test-private-hash|tokenHash/);
  assert.equal(a.headers.get('Cache-Control'), 'no-store');
  const b = await api('/me/overview', { id: 2 });
  assert.equal(b.data.user.nickname, 'Account 2'); assert.equal(b.data.tokens, 6.5); assert.equal(b.data.active.id, 2);
  assert.equal(b.data.stats.subs[0].score, 20); assert.equal(trips(b), 2, 'warm account uses one auth lookup and one section batch');
  assert.ok([...cache.keys()].every(k => !/overview|tokens|identities|active/.test(k)));
});

test('private balance and role remain fresh even with a reusable public leaderboard', async () => {
  sql.prepare("UPDATE users SET exam_tokens=17,exam_half=0,role='admin' WHERE id=1").run();
  const r = await api('/me/overview');
  assert.equal(r.data.tokens, 17); assert.equal(r.data.user.role, 'admin'); assert.equal(trips(r), 2);
  const tokens = await api('/lab/tokens'); assert.equal(tokens.data.tokens, 17); assert.equal(trips(tokens), 2);
  const active = await api('/lab/active'); assert.equal(active.data.tokens, 17); assert.equal(trips(active), 2);
});

test('weekly public projection is reused without sharing individual scores or answer keys', async () => {
  const a = await api('/weekly?week=2099-W01&lang=ko');
  const b = await api('/weekly?week=2099-W01&lang=ko', { id: 2 });
  assert.equal(a.data.problems[0].best, 70); assert.equal(b.data.problems[0].best, 20);
  assert.equal(a.data.user.nickname, 'Account 1'); assert.equal(b.data.user.nickname, 'Account 2');
  assert.doesNotMatch(JSON.stringify(b.data), /private-(?:body|model|answer)|"answer"|"rubric"/);
  assert.equal(b.data.api_version, 5); assert.equal(trips(b), 2);
  const anonymous = await api('/weekly?week=2099-W01&lang=ko', { id: null });
  assert.equal(anonymous.data.user, null); assert.equal(anonymous.data.problems[0].best, undefined);
});

test('a submission invalidates derived scores and fresh requests bypass the public cache', async () => {
  await api('/rank?scope=all');
  const sent = await api('/problems/999/submit', { method: 'POST', body: { answer: '2' } });
  assert.equal(sent.status, 200); assert.equal(sent.data.score, 100);
  const r = await api('/weekly?week=2099-W01&lang=ko', { headers: { 'Cache-Control': 'no-cache' } });
  assert.equal(r.data.problems[0].best, 100); assert.equal(r.data.top[0].total, 100);
});

test('expired and revoked sessions cannot recover an account through overview or a warm cache', async () => {
  assert.equal((await api('/me/overview', { id: null })).status, 401);
  sql.prepare('UPDATE sessions SET expires_at=0 WHERE user_id=2').run();
  assert.equal((await api('/me/overview', { id: 2 })).status, 401);
  sql.prepare('DELETE FROM sessions WHERE user_id=1').run();
  assert.equal((await api('/me/overview')).status, 401);
});

test('SQL metadata separates execution time, rows and serving region from binding wait', async () => {
  const r = await api('/me');
  assert.match(r.headers.get('Server-Timing'), /sql;desc="1 statements";dur=0.125/);
  assert.match(r.headers.get('Server-Timing'), /d1_region;desc="LOCAL primary"/);
  assert.match(r.headers.get('Server-Timing'), /d1_read;desc="1 rows"/);
});

test('public cache coalesces reads, clones results, isolates databases and rejects invalidated in-flight writes', async () => {
  const a = { DB: {} }, b = { DB: {} }; let resolve, loads = 0;
  const load = () => { loads++; return new Promise(r => { resolve = r; }); };
  const first = publicRead(a, 'same', load), duplicate = publicRead(a, 'same', load);
  await Promise.resolve(); assert.equal(loads, 1); invalidatePublicReads(a); resolve({ rows: [1] });
  const x = await first; await duplicate; x.rows.push(2);
  assert.deepEqual(await publicRead(a, 'same', () => ({ rows: [3] })), { rows: [3] });
  assert.deepEqual(await publicRead(b, 'same', () => ({ rows: [4] })), { rows: [4] });
});

test('refreshing a nested public ranking does not prevent its weekly projection from being cached', async () => {
  const env = { DB: {} };
  await publicRead(env, 'weekly', async () => ({ top: await publicRead(env, 'rank', () => [10], { fresh: true }) }), { fresh: true });
  const r = await publicRead(env, 'weekly', () => { throw new Error('fresh outer projection was lost'); });
  assert.deepEqual(r, { top: [10] });
});

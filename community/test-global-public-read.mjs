// Real SQLite + simulated D1 sessions. No Cloudflare, provider, secret or production access.
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import test from 'node:test';
import gateway from './src/edge-gateway.js';
import backend from './src/index.js';
import { selectOnly } from './src/public-consistency.js';
import { DB_SCOPE, READ_METRICS, publicRead } from './src/public-read-cache.js';
import { createD1Metrics } from './src/d1-timing.js';

const fixtures = [], ORIGIN = 'https://haslalab.org';
const sensitiveSQL = /\b(?:pw|token_hash|exam_tokens|exam_half|token_parts|sessions|lab_sessions|lab_pages|lab_ledger|pay_orders|identities|answer|rubric|model_ko|model_en)\b/i;
async function fixture({ actualBackend = false, enabled = true, supported = true } = {}) {
  const sql = new DatabaseSync(':memory:'); fixtures.push(sql);
  for (const name of readdirSync(new URL('./migrations/', import.meta.url)).filter(n => /^\d{4}_.*\.sql$/.test(n)).sort()) sql.exec(readFileSync(new URL('./migrations/' + name, import.meta.url), 'utf8'));
  sql.exec('DELETE FROM submissions; DELETE FROM problems');
  const time = Math.floor(Date.now() / 1000), token = 'local_global_read_owner'.padEnd(48, 'x');
  sql.prepare("INSERT INTO users(id,username,nickname,pw,role,avatar,created_at,exam_tokens) VALUES(1,'PRIVATE_LOGIN','Public Owner','PRIVATE_HASH','user','publicAvatar',?,7)").run(time);
  const tokenHash = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(token))).toString('base64url');
  sql.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,1,?,?)').run(tokenHash, time, time + 3600);
  sql.prepare("INSERT INTO posts(id,user_id,board,tag,lang,title,body,created_at) VALUES(1,1,'free','gen','ko','Before mutation','Public body',?)").run(time);
  sql.prepare("INSERT INTO posts(id,user_id,board,tag,lang,title,body,created_at) VALUES(2,1,'free','notice','ko','Public notice','Public notice',?)").run(time);
  sql.prepare("INSERT INTO problems(id,week,no,kind,subject,points,level,title_ko,title_en,body_ko,body_en,answer,rubric,model_ko,model_en,opens_at,closes_at,created_at) VALUES(999,'2099-W01',1,'short','physics',100,10,'공개 제목','Public title','PRIVATE_BODY','PRIVATE_BODY','{\"value\":2}','[]','PRIVATE_MODEL','PRIVATE_MODEL',?,?,?)").run(time - 60, time + 3600, time);
  sql.prepare("INSERT INTO submissions(problem_id,user_id,answer,status,score,in_week,created_at) VALUES(999,1,'PRIVATE_SUBMISSION','graded',80,1,?)").run(time);
  const state = { version: 0, failEdge: false }, queries = [], edgeModes = [], primaryModes = [], services = [], tasks = [], bookmarks = new Set(['bookmark-A', 'bookmark-B']);
  function binding(lane, mode) {
    let executed = false, observedVersion = null;
    const metadata = (rows = 0, changes = 0, id = 0) => ({ changes, last_row_id: id, rows_read: rows,
      timings: { sql_duration_ms: 0.125 }, served_by_primary: lane !== 'replica', served_by_region: lane === 'replica' ? 'WNAM' : 'APAC', served_by_colo: lane === 'replica' ? 'LAX' : 'HKG' });
    return {
      prepare(query) {
        if (lane === 'replica') { assert.match(query, /^SELECT\b/i); assert.doesNotMatch(query, sensitiveSQL); }
        const statement = sql.prepare(query), make = args => ({
          bind: (...values) => make(values),
          executeSync() {
            if (lane === 'replica' && state.failEdge) throw new Error('fixture unavailable replica');
            executed = true; queries.push({ lane, mode, query, version: state.version });
            state.onQuery?.({ lane, mode, query, version: state.version });
            const mutation = !/^\s*SELECT\b/i.test(query);
            if (statement.columns().length) {
              const rows = statement.all(...args).map(row => ({ ...row }));
              if (mutation) state.version++;
              observedVersion = state.version;
              return { results: rows, meta: metadata(rows.length, mutation ? sql.prepare('SELECT changes() n').get().n : 0) };
            }
            const result = statement.run(...args); if (mutation) state.version++;
            observedVersion = state.version;
            return { results: [], meta: metadata(0, result.changes, Number(result.lastInsertRowid)) };
          },
          async all() {
            const result = this.executeSync();
            if (state.pauseRanking && /GROUP BY x\.user_id, x\.problem_id/.test(query)) await state.pauseRanking({ lane, mode, result });
            return result;
          },
          async first() { return this.executeSync().results[0] || null; },
          async run() { return this.executeSync(); },
        });
        return make([]);
      },
      async batch(statements) {
        sql.exec('BEGIN');
        try { const result = statements.map(statement => statement.executeSync()); sql.exec('COMMIT'); return result; }
        catch (error) { sql.exec('ROLLBACK'); throw error; }
      },
      getBookmark() {
        if (!executed) return null;
        const value = `bm-${lane}-v${observedVersion}`; bookmarks.add(value); return value;
      },
    };
  }
  const DB = binding('primary');
  DB.withSession = mode => { primaryModes.push(mode); assert.equal(mode, 'first-primary'); return binding('primary-session', mode); };
  const PUBLIC_DB = { withSession(mode) {
    edgeModes.push(mode);
    if (mode !== 'first-unconstrained' && !bookmarks.has(mode)) throw new Error('fixture revoked or invalid bookmark');
    return binding('replica', mode);
  } };
  const cache = new Map();
  globalThis.caches = { default: {
    async match(key) { return cache.get(key.url)?.clone(); },
    async put(key, response) { cache.set(key.url, response.clone()); },
  } };
  const backendEnv = { DB, ALLOWED_ORIGINS: ORIGIN, LAB_KEEP_HOURS: 'off' };
  const env = { ALLOWED_ORIGINS: ORIGIN, GLOBAL_PUBLIC_READS: enabled ? '1' : '0', ...(supported ? { PUBLIC_DB } : {}), COMMUNITY: {
    async fetch(request) {
      services.push(request);
      if (actualBackend) return backend.fetch(request, backendEnv, { waitUntil: promise => tasks.push(promise) });
      return Response.json({ from: 'primary', calls: services.length }, { headers: { 'Cache-Control': 'no-store', 'X-D1-Bookmark': 'bm-primary-fallback' } });
    },
  } };
  return { sql, state, queries, edgeModes, primaryModes, services, bookmarks, cache, env, DB, backendEnv, tasks,
    async request(path, { auth = false, method = 'GET', body, headers = {} } = {}) {
      const response = await gateway.fetch(new Request('https://global-edge.test/api' + path, { method,
        headers: { Origin: ORIGIN, ...(auth ? { Authorization: 'Bearer ' + token } : {}), ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...headers },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      }), env, { waitUntil: promise => tasks.push(promise) });
      return { response, status: response.status, headers: response.headers, data: await response.json() };
    },
    async flush() { while (tasks.length) await Promise.all(tasks.splice(0)); },
    change(query, ...args) { sql.prepare(query).run(...args); state.version++; },
  };
}
test.after(() => fixtures.forEach(sql => sql.close()));
const noPrivateData = data => assert.doesNotMatch(JSON.stringify(data), /PRIVATE_|tokenHash|token_hash|user_id|problem_id|"username"|"answer"|"rubric"|"solution"/);

test('the four exact public routes read local replicas with real public SQL and region metadata', async () => {
  const h = await fixture(), before = h.sql.prepare('SELECT COUNT(*) n FROM problems').get().n;
  for (const [path, auth] of [['/boards?case=local', true], ['/posts?case=local', true], ['/weekly?week=2099-W01&case=local', false], ['/rank?case=local', false]]) {
    const r = await h.request(path, { auth });
    assert.equal(r.status, 200); assert.equal(r.headers.get('X-Public-Read-Source'), 'replica');
    assert.match(r.headers.get('Server-Timing'), /d1_region;desc="WNAM replica"/);
    assert.match(r.headers.get('Server-Timing'), /d1_colo;desc="LAX"/);
    assert.ok(h.bookmarks.has(r.headers.get('X-D1-Bookmark'))); noPrivateData(r.data);
    assert.equal(r.headers.get('Access-Control-Allow-Origin'), ORIGIN);
    assert.match(r.headers.get('Access-Control-Expose-Headers'), /X-D1-Bookmark/);
    await h.flush();
  }
  assert.equal(h.services.length, 0); assert.deepEqual(h.edgeModes, Array(4).fill('first-unconstrained'));
  assert.ok(h.queries.every(row => row.lane === 'replica' && /^SELECT\b/.test(row.query)));
  assert.equal(h.sql.prepare('SELECT COUNT(*) n FROM problems').get().n, before, 'global weekly reads never publish seed data');
});

test('authenticated rankings, private pages, writes and fresh reads use the service binding without local D1', async () => {
  const h = await fixture();
  for (const [path, options] of [
    ['/weekly?case=auth', { auth: true }], ['/rank?case=auth', { auth: true }],
    ['/rank?case=cookie', { headers: { Cookie: 'account=x' } }], ['/weekly?case=scan', { headers: { 'X-Lab-Token': 'scan-code' } }],
    ['/me/overview', {}], ['/users/Public%20Owner', {}], ['/posts/1?view=1', {}], ['/lab/tokens', {}], ['/lab/sessions/1', {}], ['/pay/status?id=1', {}],
    ['/posts', { auth: true, method: 'POST', body: { title: 'Write' } }], ['/comments/1', { auth: true, method: 'PATCH', body: { body: 'Edit' } }],
    ['/lab/up/pages', { method: 'PUT', body: { scan: true } }], ['/posts/1', { auth: true, method: 'DELETE' }],
    ['/boards?case=fresh', { headers: { 'Cache-Control': 'no-cache' } }], ['/posts?case=fresh', { headers: { 'Cache-Control': 'max-age=0' } }], ['/rank?case=fresh', { headers: { 'Cache-Control': 'no-store' } }],
  ]) assert.equal((await h.request(path, options)).data.from, 'primary');
  assert.equal(h.services.length, 17); assert.equal(h.edgeModes.length, 0); assert.equal(h.queries.length, 0); await h.flush();
});

test('bookmarks constrain sessions, survive cache hits and isolate cached database versions', async () => {
  const h = await fixture();
  const a = await h.request('/posts?case=bookmarks&__hl_bm=bookmark-A'); await h.flush();
  h.change("UPDATE posts SET title='After mutation' WHERE id=1");
  const b = await h.request('/posts?__hl_bm=bookmark-B&case=bookmarks'); await h.flush();
  assert.equal(a.data.posts[0].title, 'Before mutation'); assert.equal(b.data.posts[0].title, 'After mutation');
  assert.deepEqual(h.edgeModes, ['bookmark-A', 'bookmark-B']);
  assert.notEqual(a.headers.get('X-D1-Bookmark'), b.headers.get('X-D1-Bookmark'));
  const cached = await h.request('/posts?__hl_bm=bookmark-A&case=bookmarks');
  assert.equal(cached.headers.get('X-Edge-Cache'), 'hit'); assert.equal(cached.data.posts[0].title, 'Before mutation');
  assert.equal(cached.headers.get('X-D1-Bookmark'), a.headers.get('X-D1-Bookmark'));
  assert.match(cached.headers.get('Server-Timing'), /db;desc="0 queries";dur=0/);
  assert.equal(h.edgeModes.length, 2); assert.equal(h.services.length, 0);
});

test('an actual primary post mutation returns a checkpoint that bypasses an older anonymous cache key', async () => {
  const h = await fixture({ actualBackend: true });
  const old = await h.request('/posts?case=mutation'); await h.flush(); assert.equal(old.data.total, 1);
  const sent = await h.request('/posts', { auth: true, method: 'POST', body: { board: 'free', title: 'Published post', body: 'Public new body' } });
  assert.equal(sent.status, 200);
  const bookmark = sent.headers.get('X-D1-Bookmark'); assert.ok(bookmark && h.bookmarks.has(bookmark));
  assert.deepEqual(h.primaryModes, ['first-primary']);
  const next = await h.request('/posts?' + new URLSearchParams({ case: 'mutation', __hl_bm: bookmark })); await h.flush();
  assert.equal(next.data.total, 2); assert.equal(next.data.posts[0].title, 'Published post');
  assert.equal(h.edgeModes.at(-1), bookmark); assert.equal(h.services.length, 1);
  assert.equal((await h.request('/posts?case=mutation')).data.total, 1, 'the old public key cannot satisfy the new checkpoint');
});

test('invalid, revoked and unavailable replica reads fall back to a fresh primary GET', async () => {
  const h = await fixture();
  for (const path of ['/posts?case=invalid&__hl_bm=%0A', '/posts?case=revoked&__hl_bm=revoked-bookmark']) {
    const r = await h.request(path); assert.equal(r.data.from, 'primary');
    assert.equal(r.headers.get('X-Public-Read-Source'), 'primary-fallback');
    assert.equal(h.services.at(-1).headers.get('Cache-Control'), 'no-cache'); await h.flush();
  }
  h.state.failEdge = true;
  const failed = await h.request('/boards?case=failed'); await h.flush();
  assert.equal(failed.data.from, 'primary'); assert.equal(failed.headers.get('X-Public-Read-Source'), 'primary-fallback');
  assert.equal(h.services.at(-1).headers.get('Cache-Control'), 'no-cache');
  assert.ok(h.services.every(request => request.method === 'GET'));
});

test('region capability checks issue SELECT 1 only and never reuse a cached response as routing evidence', async () => {
  const h = await fixture({ enabled: false });
  for (let i = 0; i < 2; i++) {
    const r = await h.request('/health?read_region_check=1');
    assert.deepEqual(r.data, { ok: true, supported: true, replica: true, primary: false, regions: ['WNAM'], colos: ['LAX'] });
    assert.equal(r.headers.get('Cache-Control'), 'no-store'); noPrivateData(r.data);
  }
  assert.equal(h.services.length, 0); assert.equal(h.queries.length, 2);
  assert.ok(h.queries.every(row => row.query === 'SELECT 1 AS ready'));
  assert.equal(h.cache.size, 0);
});

test('a disabled or unsupported rollout keeps public reads on the existing backend', async () => {
  const disabled = await fixture({ enabled: false });
  assert.equal((await disabled.request('/posts?case=disabled')).data.from, 'primary'); await disabled.flush();
  assert.equal(disabled.edgeModes.length, 0);
  const unsupported = await fixture({ supported: false });
  assert.equal((await unsupported.request('/posts?case=unsupported')).data.from, 'primary'); await unsupported.flush();
  const probe = await unsupported.request('/health?read_region_check=1');
  assert.deepEqual(probe.data, { ok: true, supported: false }); assert.equal(unsupported.queries.length, 0);
});

test('the SELECT-only boundary rejects writes, pragmas, writable CTEs and stacked SQL before execution', async () => {
  const h = await fixture(), guarded = selectOnly(h.DB);
  for (const query of ['UPDATE posts SET views=1', 'DELETE FROM users', 'INSERT INTO users(id) VALUES(9)', 'PRAGMA writable_schema=ON', 'WITH x AS (SELECT 1) DELETE FROM posts', 'SELECT 1; DELETE FROM posts', '/* hidden */ DELETE FROM posts']) {
    assert.throws(() => guarded.prepare(query), /SELECT only/);
  }
  assert.equal(h.queries.length, 0);
  assert.equal((await guarded.prepare('SELECT 1 AS ready').all()).results[0].ready, 1);
  assert.equal(h.sql.prepare('SELECT views FROM posts WHERE id=1').get().views, 0);
});

test('public mutations authenticate inside a first-primary session while balances and exam state retain the primary binding', async () => {
  const h = await fixture({ actualBackend: true });
  const sent = await h.request('/posts', { auth: true, method: 'POST', body: { board: 'free', title: 'Primary checkpoint', body: 'Public content' } });
  assert.equal(sent.status, 200); assert.ok(sent.headers.get('X-D1-Bookmark'));
  assert.ok(h.queries.some(row => /FROM sessions/.test(row.query) && row.lane === 'primary-session' && row.mode === 'first-primary'));
  assert.ok(h.queries.some(row => /INSERT INTO posts/.test(row.query) && row.lane === 'primary-session'));
  h.queries.length = 0; h.primaryModes.length = 0;
  const balance = await h.request('/lab/tokens', { auth: true }); assert.equal(balance.data.tokens, 7);
  const active = await h.request('/lab/active', { auth: true }); assert.equal(active.data.active, null);
  const me = await h.request('/me', { auth: true }); assert.equal(me.data.user.nickname, 'Public Owner');
  assert.equal(h.primaryModes.length, 0); assert.ok(h.queries.every(row => row.lane === 'primary'));
  assert.equal(h.edgeModes.length, 0);
});

test('weekly publication runs only through the primary cron and never through the global reader', async () => {
  const h = await fixture(), before = h.sql.prepare('SELECT COUNT(*) n FROM problems').get().n;
  await h.request('/weekly?week=2099-W01&case=cron'); await h.flush();
  assert.equal(h.sql.prepare('SELECT COUNT(*) n FROM problems').get().n, before);
  h.queries.length = 0;
  await backend.scheduled({ scheduledTime: 60000 }, h.backendEnv, { waitUntil: promise => h.tasks.push(promise) }); await h.flush();
  assert.ok(h.sql.prepare('SELECT COUNT(*) n FROM problems').get().n > before);
  assert.ok(h.queries.some(row => /INSERT INTO problems/.test(row.query)));
  assert.ok(h.queries.every(row => row.lane === 'primary'));
  assert.equal(h.primaryModes.length, 0);
});

test('pending public snapshot reuse records a hit on the joining request across separate request DB wrappers', async () => {
  const sharedDB = {}, firstMetrics = createD1Metrics(), secondMetrics = createD1Metrics();
  const firstEnv = { DB: {}, [DB_SCOPE]: sharedDB, [READ_METRICS]: firstMetrics };
  const secondEnv = { DB: {}, [DB_SCOPE]: sharedDB, [READ_METRICS]: secondMetrics };
  let release, started;
  const held = new Promise(resolve => { release = resolve; }), loading = new Promise(resolve => { started = resolve; });
  const first = publicRead(firstEnv, 'rank-snapshot', () => { started(); return held; });
  await loading;
  const second = publicRead(secondEnv, 'rank-snapshot', () => { throw Error('joining request must not load another snapshot'); });
  assert.equal(firstMetrics.misses, 1); assert.equal(firstMetrics.hits, 0);
  assert.equal(secondMetrics.hits, 1, 'reused in-flight data cannot certify the joining request\'s DB checkpoint');
  assert.equal(secondMetrics.misses, 0);
  release({ rows: [{ score: 80 }], version: 'B1' });
  const [a, b] = await Promise.all([first, second]);
  assert.deepEqual(a, b); a.rows[0].score = 100; assert.equal(b.rows[0].score, 80);
});

test('a later authenticated session joining an older rank query never certifies that snapshot with a newer bookmark', async () => {
  const h = await fixture({ actualBackend: true });
  let release, rankingStarted, newerAuth;
  const held = new Promise(resolve => { release = resolve; });
  const loading = new Promise(resolve => { rankingStarted = resolve; });
  const authenticated = new Promise(resolve => { newerAuth = resolve; });
  let paused = false;
  h.state.pauseRanking = async () => { if (!paused) { paused = true; rankingStarted(); await held; } };
  h.state.onQuery = ({ query }) => {
    if (/FROM sessions/.test(query) && h.queries.filter(row => /FROM sessions/.test(row.query)).length === 2) newerAuth();
  };
  const first = h.request('/rank?scope=all&case=checkpoint-join', { auth: true });
  await loading; // First session has already read score 80 at B1, but its shared query is still pending.
  h.change('UPDATE submissions SET score=100 WHERE problem_id=999');
  const second = h.request('/rank?scope=all&case=checkpoint-join', { auth: true });
  await authenticated;
  await new Promise(resolve => setImmediate(resolve)); // Allow the authenticated request to join the pending projection.
  release();
  const [older, joined] = await Promise.all([first, second]);
  assert.equal(older.status, 200); assert.equal(joined.status, 200);
  assert.equal(older.data.rows[0].total, 80); assert.equal(joined.data.rows[0].total, 80);
  const authVersions = h.queries.filter(row => /FROM sessions/.test(row.query)).map(row => row.version);
  assert.deepEqual(authVersions, [0, 1], 'the joining session really authenticated after a newer commit');
  assert.equal(older.headers.get('X-D1-Bookmark'), 'bm-primary-session-v0');
  assert.equal(joined.headers.has('X-D1-Bookmark'), false, 'B2 authentication cannot certify reused B1 ranking data');
  assert.match(joined.headers.get('Server-Timing'), /public_cache;desc="1 hits 0 misses"/);
  const fresh = await h.request('/rank?scope=all&case=checkpoint-join', { auth: true, headers: { 'Cache-Control': 'no-cache' } });
  assert.equal(fresh.data.rows[0].total, 100);
  assert.equal(fresh.headers.get('X-D1-Bookmark'), 'bm-primary-session-v1');
});

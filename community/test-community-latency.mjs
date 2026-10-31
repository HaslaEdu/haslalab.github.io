// Local Worker integration tests: real SQLite transactions, no external requests or production writes.
// Run: node --test test-community-latency.mjs
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import test from 'node:test';
import worker from './src/index.js';

const sql = new DatabaseSync(':memory:');
for (const name of readdirSync(new URL('./migrations/', import.meta.url)).filter(n => /^\d{4}_.*\.sql$/.test(n)).sort()) {
  sql.exec(readFileSync(new URL('./migrations/' + name, import.meta.url), 'utf8'));
}
sql.exec('PRAGMA foreign_keys=ON');
let calls = 0;
const meta = (changes = 0, id = 0) => ({ changes, last_row_id: id, duration: 0, timings: { sql_duration_ms: 0 }, served_by_region: 'LOCAL', served_by_primary: true });
const DB = {
  prepare(query) {
    const statement = sql.prepare(query);
    const make = args => ({
      bind: (...bound) => make(bound),
      async first() { calls++; return statement.get(...args) || null; },
      async all() { calls++; return { results: statement.all(...args), meta: meta() }; },
      async run() { calls++; return this.executeSync(); },
      executeSync() {
        if (statement.columns().length) return { results: statement.all(...args), meta: meta() };
        const result = statement.run(...args);
        return { results: [], meta: meta(result.changes, Number(result.lastInsertRowid)) };
      },
    });
    return make([]);
  },
  async batch(statements) {
    calls++;
    sql.exec('BEGIN');
    try {
      // A D1 batch is ordered and atomic; execute it without yielding between statements.
      const results = statements.map(statement => statement.executeSync());
      sql.exec('COMMIT');
      return results;
    } catch (error) { sql.exec('ROLLBACK'); throw error; }
  },
};
const cache = new Map();
globalThis.caches = { default: {
  async match(key) { return cache.get(key.url)?.clone(); },
  async put(key, response) { cache.set(key.url, response.clone()); },
} };
const env = { DB, ALLOWED_ORIGINS: 'https://haslalab.org', LAB_KEEP_HOURS: 'off' };
const time = Math.floor(Date.now() / 1000), tokens = {};
for (const [id, role, deleted] of [[1, 'user', 0], [2, 'user', 0], [3, 'admin', 0], [4, 'user', 1]]) {
  sql.prepare('INSERT INTO users(id,username,nickname,pw,role,created_at,avatar,deleted) VALUES(?,?,?,\'private_hash\',?,?,?,?)')
    .run(id, 'login' + id, 'Person ' + id, role, time, 'avatar' + id, deleted);
  tokens[id] = ('community_local_' + id).padEnd(48, 'x');
  const hash = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(tokens[id]))).toString('base64url');
  sql.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)').run(hash, id, time, time + 3600);
}
tokens[5] = 'community_local_expired'.padEnd(48, 'x');
tokens[6] = 'community_local_revoked'.padEnd(48, 'x');
const expiredHash = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(tokens[5]))).toString('base64url');
sql.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,2,?,?)').run(expiredHash, time - 7200, time - 3600);
sql.prepare("INSERT INTO identities(provider,sub,user_id,created_at) VALUES('github','fixture',2,?)").run(time);
for (const [id, owner] of [[101, 1], [102, 4]]) {
  sql.prepare("INSERT INTO posts(id,board,tag,lang,user_id,title,body,created_at) VALUES(?,'qna','gen','ko',?,'Fixture title','Fixture body',?)").run(id, owner, time);
}
for (const [id, owner, post, parent] of [[201, 1, 101, null], [202, 2, 101, 201], [203, 4, 101, null], [301, 1, 102, null]]) {
  sql.prepare('INSERT INTO comments(id,post_id,user_id,parent_id,body,created_at) VALUES(?,?,?,?,?,?)').run(id, post, owner, parent, 'Comment ' + id, time);
}
sql.exec('UPDATE posts SET n_comments=(SELECT COUNT(*) FROM comments WHERE post_id=posts.id)');
const originalFetch = globalThis.fetch;
globalThis.fetch = async () => { throw Error('Test must not contact external services'); };
test.after(() => { globalThis.fetch = originalFetch; sql.close(); });

async function api(path, { user = 2, method = 'GET', body } = {}) {
  const response = await worker.fetch(new Request('https://local.test/api' + path, {
    method, headers: { ...(user ? { Authorization: 'Bearer ' + tokens[user] } : {}), ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  }), env);
  return { status: response.status, headers: response.headers, data: await response.json() };
}
function resetVotes() {
  sql.exec('DELETE FROM likes WHERE post_id=101; DELETE FROM dislikes WHERE post_id=101; UPDATE posts SET n_likes=0,n_dislikes=0 WHERE id=101');
  sql.exec("DELETE FROM ratelimits WHERE k LIKE 'vote:%'");
}
function checkCounts() {
  const p = sql.prepare('SELECT n_likes,n_dislikes FROM posts WHERE id=101').get();
  assert.equal(p.n_likes, sql.prepare('SELECT COUNT(*) n FROM likes WHERE post_id=101').get().n);
  assert.equal(p.n_dislikes, sql.prepare('SELECT COUNT(*) n FROM dislikes WHERE post_id=101').get().n);
  assert.equal(sql.prepare('SELECT COUNT(*) n FROM likes l JOIN dislikes d USING(post_id,user_id)').get().n, 0);
  return p;
}

test('private detail returns validated permissions, reactions and exact view count in auth plus one batch', async () => {
  resetVotes();
  sql.prepare('INSERT INTO dislikes(post_id,user_id,created_at) VALUES(101,2,?)').run(time);
  sql.exec('UPDATE posts SET n_dislikes=1 WHERE id=101');
  const views = sql.prepare('SELECT views FROM posts WHERE id=101').get().views;
  calls = 0;
  const result = await api('/posts/101?view=1');
  assert.equal(calls, 2);
  assert.equal(result.status, 200);
  assert.equal(result.headers.get('Cache-Control'), 'no-store');
  assert.equal(result.data.api_version, 5);
  assert.equal(result.data.user.nickname, 'Person 2');
  assert.equal(result.data.post.views, views + 1);
  assert.equal(result.data.post.mine, false);
  assert.equal(result.data.my, -1);
  assert.equal(result.data.liked, false);
  assert.equal(result.data.comments.find(c => c.id === 202).mine, true);
  assert.equal(result.data.comments.find(c => c.id === 203).gone, 1);
  for (const item of [result.data.post, ...result.data.comments]) assert.equal('user_id' in item, false);
  assert.equal(JSON.stringify(result.data).includes('private_hash'), false);
  assert.equal((await api('/posts/101')).data.post.views, views + 1);
  calls = 0;
  const anonymous = await api('/posts/101', { user: null });
  assert.equal(calls, 1);
  assert.equal(anonymous.data.user, null);
  assert.equal(anonymous.data.my, 0);
  assert.ok(anonymous.data.comments.every(c => !c.mine));
  const admin = await api('/posts/101', { user: 3 });
  assert.equal(admin.data.post.mine, true);
  assert.ok(admin.data.comments.every(c => c.mine));
  assert.equal((await api('/posts/99999?view=1')).status, 404);
  assert.equal(cache.size, 0, 'personalized detail never enters shared cache');
});

test('identity settings use one batch after auth and disclose only the current account', async () => {
  calls = 0;
  const result = await api('/me/identities');
  assert.equal(result.status, 200);
  assert.equal(calls, 2);
  assert.deepEqual(result.data.identities, [{ provider: 'github', created_at: time }]);
  assert.equal(result.data.has_pw, true);
  assert.deepEqual((await api('/me/identities', { user: 1 })).data.identities, []);
  assert.equal((await api('/me/identities', { user: null })).status, 401);
});

test('votes toggle and switch atomically, keeping counters and missing-post behavior correct', async () => {
  resetVotes();
  calls = 0;
  let result = await api('/posts/101/vote', { method: 'POST', body: { v: 1 } });
  assert.equal(calls, 3, 'auth + atomic admission + atomic vote batch');
  assert.deepEqual(result.data, { my: 1, liked: true, n_likes: 1, n_dislikes: 0 });
  result = await api('/posts/101/vote', { method: 'POST', body: { v: -1 } });
  assert.deepEqual(result.data, { my: -1, liked: false, n_likes: 0, n_dislikes: 1 });
  result = await api('/posts/101/vote', { method: 'POST', body: { v: -1 } });
  assert.deepEqual(result.data, { my: 0, liked: false, n_likes: 0, n_dislikes: 0 });
  assert.equal((await api('/posts/101/like', { method: 'POST', body: {} })).data.my, 1);
  assert.equal((await api('/posts/101/like', { method: 'POST', body: {} })).data.my, 0);
  const before = checkCounts();
  assert.equal((await api('/posts/99999/vote', { method: 'POST', body: { v: 1 } })).status, 404);
  assert.equal(sql.prepare('SELECT COUNT(*) n FROM likes WHERE post_id=99999').get().n, 0);
  assert.equal((await api('/posts/101/vote', { user: null, method: 'POST', body: { v: 1 } })).status, 401);
  assert.equal((await api('/posts/101/vote', { user: 4, method: 'POST', body: { v: 1 } })).status, 401);
  for (const user of [5, 6]) {
    assert.equal((await api('/posts/101/vote', { user, method: 'POST', body: { v: 1 } })).status, 401);
    const detail = await api('/posts/101', { user });
    assert.equal(detail.data.user, null);
    assert.equal(detail.data.my, 0);
    assert.ok(detail.data.comments.every(c => !c.mine));
  }
  assert.deepEqual(checkCounts(), before);
});

test('simultaneous votes never lose counts or insert duplicate/opposite reactions', async () => {
  resetVotes();
  const results = await Promise.all(Array.from({ length: 12 }, () => api('/posts/101/vote', { method: 'POST', body: { v: 1 } })));
  assert.ok(results.every(r => r.status === 200));
  assert.ok(results.every(r => r.data.n_likes <= 1 && r.data.n_dislikes === 0));
  assert.equal(checkCounts().n_likes, 0, 'an even number of same-button toggles cancels');
  const independent = await Promise.all([1, 2, 3].map(user => api('/posts/101/vote', { user, method: 'POST', body: { v: 1 } })));
  assert.ok(independent.every(r => r.status === 200));
  assert.equal(checkCounts().n_likes, 3);
  const switches = await Promise.all(Array.from({ length: 15 }, (_, i) => api('/posts/101/vote', { method: 'POST', body: { v: i % 2 ? -1 : 1 } })));
  assert.ok(switches.every(r => r.status === 200));
  checkCounts();
});

test('comment append payload matches detail, normalizes reply threads and rejects foreign/missing parents atomically', async () => {
  const baseline = sql.prepare('SELECT n_comments FROM posts WHERE id=101').get().n_comments;
  calls = 0;
  const result = await api('/posts/101/comments', { method: 'POST', body: { body: '  Reply\r\ntext\u0000 ', parent_id: 202 } });
  assert.equal(result.status, 200);
  assert.equal(calls, 3, 'auth + admission + validation/insert/counter transaction');
  const c = result.data.comment;
  assert.equal(result.data.id, c.id);
  assert.deepEqual(Object.keys(c).sort(), ['av', 'body', 'created_at', 'gone', 'id', 'mine', 'nickname', 'parent_id', 'updated_at']);
  assert.equal(c.parent_id, 201);
  assert.equal(c.body, 'Reply\ntext');
  assert.equal(c.mine, true);
  assert.equal(c.gone, 0);
  assert.equal(c.nickname, 'Person 2');
  assert.equal(c.av, 'avatar2');
  assert.equal(c.updated_at, null);
  const detail = await api('/posts/101');
  assert.deepEqual(detail.data.comments.find(item => item.id === c.id), c);
  assert.equal(detail.data.post.n_comments, baseline + 1);
  for (const parent_id of [301, 99999, 'invalid']) {
    assert.equal((await api('/posts/101/comments', { method: 'POST', body: { body: 'Invalid reply', parent_id } })).status, 404);
  }
  assert.equal((await api('/posts/99999/comments', { method: 'POST', body: { body: 'Missing thread' } })).status, 404);
  assert.equal(sql.prepare('SELECT n_comments FROM posts WHERE id=101').get().n_comments, baseline + 1);
  assert.equal((await api('/posts/101/comments', { user: null, method: 'POST', body: { body: 'Anonymous' } })).status, 401);
  assert.equal((await api('/comments/' + c.id, { user: 1, method: 'DELETE' })).status, 403);
});

test('fixed-window admission enforces the limit under concurrency and resets only after expiry', async () => {
  sql.exec("DELETE FROM ratelimits WHERE k='post:1'");
  const results = await Promise.all(Array.from({ length: 25 }, (_, i) => api('/posts', { user: 1, method: 'POST', body: { board: 'free', title: 'Rate fixture ' + i, body: 'Body' } })));
  assert.equal(results.filter(r => r.status === 200).length, 5);
  assert.equal(results.filter(r => r.status === 429 && r.data.error === 'rate_limited').length, 20);
  assert.equal(sql.prepare("SELECT n FROM ratelimits WHERE k='post:1'").get().n, 5);
  sql.prepare("UPDATE ratelimits SET start=?,n=5 WHERE k='post:1'").run(time - 601);
  assert.equal((await api('/posts', { user: 1, method: 'POST', body: { board: 'free', title: 'After expiry', body: 'Body' } })).status, 200);
  assert.equal(sql.prepare("SELECT n FROM ratelimits WHERE k='post:1'").get().n, 1);
});

test('concurrent comment inserts keep exact counters and one-level reply structure', async () => {
  const before = sql.prepare('SELECT n_comments FROM posts WHERE id=101').get().n_comments;
  const replies = await Promise.all(Array.from({ length: 8 }, (_, i) => api('/posts/101/comments', { user: 3, method: 'POST', body: { body: 'Concurrent reply ' + i, parent_id: 202 } })));
  assert.ok(replies.every(r => r.status === 200 && r.data.comment.parent_id === 201));
  assert.equal(new Set(replies.map(r => r.data.id)).size, 8);
  const count = sql.prepare('SELECT COUNT(*) n FROM comments WHERE post_id=101').get().n;
  assert.equal(sql.prepare('SELECT n_comments FROM posts WHERE id=101').get().n_comments, before + 8);
  assert.equal(count, before + 8);
});

test('deleting a thread while a reply arrives leaves no orphan reply or stale count', async () => {
  const [removed, reply] = await Promise.all([
    api('/comments/201', { user: 1, method: 'DELETE' }),
    api('/posts/101/comments', { user: 3, method: 'POST', body: { body: 'Racing reply', parent_id: 202 } }),
  ]);
  assert.equal(removed.status, 200);
  assert.ok([200, 404].includes(reply.status));
  assert.equal(sql.prepare('SELECT COUNT(*) n FROM comments WHERE id=201 OR parent_id=201').get().n, 0);
  assert.equal(sql.prepare('SELECT n_comments FROM posts WHERE id=101').get().n_comments,
    sql.prepare('SELECT COUNT(*) n FROM comments WHERE post_id=101').get().n);
});

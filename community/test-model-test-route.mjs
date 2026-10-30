// The model playground is a private, bounded request path, not an exam submission.
import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import worker from './src/index.js';
import { createModelTestRouter } from './src/model-test-route.js';
import { ModelTestError } from './src/model-test.js';

class HttpError extends Error {
  constructor(status, code, extra) { super(code); Object.assign(this, { status, code, extra }); }
}
const endpoint = 'https://worker.local/api/admin/lab/model-test';
const admin = { id: 1, role: 'admin' }, student = { id: 2, role: 'user' };
const validBody = { pipeline: 'gemini-gemini', problem: 'What is 1 + 1?', rubric: 'Award 1 point for 2.', points: 1, images: [] };
const request = (body = validBody, options = {}) => new Request(endpoint, {
  method: 'POST', headers: { 'Content-Type': 'application/json', ...options.headers },
  body: typeof body === 'string' ? body : JSON.stringify(body), ...options,
});

function fixture({ user = admin, rateError, runError } = {}) {
  const calls = { config: 0, validate: 0, run: 0, limit: [] };
  const services = {
    config(env) { calls.config++; return { pipelines: [{ id: 'gemini-gemini', available: !!env.GEMINI_API_KEY }] }; },
    validate(body) {
      calls.validate++;
      if (!body || Array.isArray(body) || body.pipeline !== 'gemini-gemini') throw new HttpError(400, 'bad_pipeline');
      return body;
    },
    async run(env, body) { calls.run++; if (runError) throw runError; return { pipeline: body.pipeline, grading: { status: 'graded', score: 1, points: 1 } }; },
  };
  const handler = createModelTestRouter({ HttpError, currentUser: async () => user,
    needUser(value) { if (!value) throw new HttpError(401, 'login_required'); return value; },
    async limit(env, key, max, seconds) { calls.limit.push({ key, max, seconds }); if (rateError) throw rateError; },
  }, services);
  return { handler, calls };
}
const errorStatus = status => error => error?.status === status;

function unreadBody(method = 'POST') {
  const base = request('deliberately invalid JSON', { method }), touches = { count: 0 };
  const req = new Proxy(base, { get(target, key) {
    if (key === 'body' || key === 'json' || key === 'text' || key === 'arrayBuffer') {
      touches.count++; throw new Error('private body must not be read');
    }
    const value = Reflect.get(target, key, target);
    return typeof value === 'function' ? value.bind(target) : value;
  } });
  return { req, touches };
}

test('anonymous and ordinary accounts are denied before consuming an image body', async () => {
  for (const [user, status] of [[null, 401], [student, 403]]) {
    const { handler, calls } = fixture({ user }), { req, touches } = unreadBody();
    await assert.rejects(handler(req, {}), errorStatus(status));
    assert.equal(touches.count, 0);
    assert.equal(calls.config + calls.validate + calls.run + calls.limit.length, 0);
  }
});

test('admin config is a read-only capability query and never runs a provider', async () => {
  const { handler, calls } = fixture();
  assert.deepEqual(await handler(new Request(endpoint), { GEMINI_API_KEY: 'synthetic-test-key' }), {
    pipelines: [{ id: 'gemini-gemini', available: true }],
    limits: { testsPerHour: 30 },
  });
  assert.equal(calls.config, 1); assert.equal(calls.validate + calls.run + calls.limit.length, 0);
});

test('only JSON POST and GET are accepted', async () => {
  const { handler, calls } = fixture();
  await assert.rejects(handler(new Request(endpoint, { method: 'DELETE' }), {}), errorStatus(405));
  await assert.rejects(handler(request('{}', { headers: { 'Content-Type': 'text/plain' } }), {}), errorStatus(415));
  assert.equal(calls.run + calls.validate + calls.limit.length, 0);
});

test('malformed and non-object JSON cannot reach a provider', async () => {
  for (const body of ['{', '[]', 'null']) {
    const { handler, calls } = fixture();
    await assert.rejects(handler(request(body), {}), errorStatus(400));
    assert.equal(calls.run, 0);
  }
});

test('the 8 MiB admission limit rejects a declared oversized body before reading it', async () => {
  const { handler, calls } = fixture();
  await assert.rejects(handler(request('{}', { headers: { 'Content-Type': 'application/json', 'Content-Length': String(8 * 1024 * 1024 + 1) } }), {}), errorStatus(413));
  assert.equal(calls.run + calls.validate + calls.limit.length, 0);
});

test('stream counting rejects oversized chunked bodies even with a small declared length', async () => {
  let canceled = false;
  const chunk = new Uint8Array(1024 * 1024).fill(32);
  let sent = 0;
  const body = new ReadableStream({
    pull(controller) { if (sent++ < 100) controller.enqueue(chunk); else controller.close(); },
    cancel() { canceled = true; },
  });
  const req = new Request(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Content-Length': '2' }, body, duplex: 'half' });
  const { handler, calls } = fixture();
  await assert.rejects(handler(req, {}), errorStatus(413));
  assert.ok(canceled); assert.equal(calls.run + calls.validate + calls.limit.length, 0);
});

test('unknown pipelines are validated before a test can call a provider', async () => {
  const { handler, calls } = fixture();
  await assert.rejects(handler(request({ ...validBody, pipeline: 'client-arbitrary-provider' }), {}), errorStatus(400));
  assert.equal(calls.run, 0);
});

test('valid tests are bounded to thirty per account per hour and returned without persistence', async () => {
  const { handler, calls } = fixture();
  const output = await handler(request(), {});
  assert.equal(output.grading.score, 1); assert.equal(calls.run, 1); assert.equal(calls.validate, 1);
  assert.equal(calls.limit.length, 1); assert.equal(calls.limit[0].max, 30); assert.equal(calls.limit[0].seconds, 3600);
  assert.match(calls.limit[0].key, /1/);
});

test('rate-limited tests never call a provider', async () => {
  const { handler, calls } = fixture({ rateError: new HttpError(429, 'rate_limited') });
  await assert.rejects(handler(request(), {}), errorStatus(429));
  assert.equal(calls.run, 0);
});

test('provider failures retain only safe stage and model diagnostics', async () => {
  const failure = new ModelTestError(502, 'model_test_provider_failed', {
    stage: 'grading', provider: 'deepseek', model: 'deepseek-flash',
  });
  failure.raw = { api_key: 'synthetic-private-key', prompt: 'synthetic-private-prompt' };
  const { handler } = fixture({ runError: failure });
  await assert.rejects(handler(request(), {}), error => {
    assert.equal(error.status, 502); assert.equal(error.code, 'model_test_provider_failed');
    assert.deepEqual(error.extra, { stage: 'grading', provider: 'deepseek', model: 'deepseek-flash' });
    assert.ok(!JSON.stringify(error.extra).includes('synthetic-private'));
    return true;
  });
});

test('untrusted provider error metadata cannot become response fields', async () => {
  const failure = new ModelTestError(700, 'upstream raw response?api_key=synthetic-private-key', {
    stage: 'api_key=synthetic-private-key', provider: 'arbitrary-upstream', model: 'https://untrusted.invalid/key',
  });
  const { handler } = fixture({ runError: failure });
  await assert.rejects(handler(request(), {}), error => {
    assert.equal(error.status, 502); assert.equal(error.code, 'model_test_failed');
    assert.deepEqual(error.extra, {}); return true;
  });
});

test('a grading failure keeps the completed OCR result and only numeric usage', async () => {
  const failure = new ModelTestError(502, 'model_test_provider_failed', { stage: 'grading', provider: 'deepseek', model: 'deepseek-flash' });
  failure.ocr = { provider: 'gemini', model: 'gemini-flash-latest', text: 'student transcript', ms: 8, internal: 'synthetic-private' };
  failure.usage = { calls: 2, input_tokens: 14, output_tokens: 5, cached_tokens: 0, api_key: 'synthetic-private', stages: [] };
  failure.elapsed_ms = 21;
  const { handler } = fixture({ runError: failure });
  await assert.rejects(handler(request(), {}), error => {
    assert.deepEqual(error.extra.ocr, { provider: 'gemini', model: 'gemini-flash-latest', text: 'student transcript', ms: 8 });
    assert.deepEqual(error.extra.usage, { calls: 2, input_tokens: 14, output_tokens: 5, cached_tokens: 0 });
    assert.equal(error.extra.elapsed_ms, 21);
    assert.ok(!JSON.stringify(error.extra).includes('synthetic-private')); return true;
  });
});

test('partial failure retains detailed usage and recomputes trusted prices without leaking metadata', async () => {
  const failure = new ModelTestError(502, 'model_test_provider_failed', { stage: 'grading', provider: 'deepseek', model: 'deepseek-flash' });
  const stage = { stage: 'ocr', provider: 'deepseek', model: 'deepseek-flash', resolved_model: 'deepseek-v4.1-flash-1017',
    calls: 1, started_at: '2026-10-30T14:00:00.000Z', finished_at: '2026-10-30T14:00:00.200Z', ms: 200,
    input_tokens: 100, cached_tokens: 40, uncached_input_tokens: 60, output_tokens: 20, reasoning_tokens: 5,
    total_tokens: 120, output_tokens_per_second: 100, usage_known: true, ok: true,
    pricing: { source_url: 'javascript:synthetic-private', total_usd: 999 }, raw: 'synthetic-private' };
  failure.usage = { calls: 2, input_tokens: null, output_tokens: null, cached_tokens: null, incomplete: true,
    known_tokens: { input_tokens: 100, cached_tokens: 40, output_tokens: 20, raw: 'synthetic-private' },
    pricing: { total_usd: 999, source_urls: ['javascript:synthetic-private'] }, stages: [stage,
      { ...stage, stage: 'grading', ok: false, usage_known: false, input_tokens: null, cached_tokens: null,
        uncached_input_tokens: null, output_tokens: null, reasoning_tokens: null, total_tokens: null }] };
  const { handler } = fixture({ runError: failure });
  await assert.rejects(handler(request(), {}), error => {
    const usage = error.extra.usage;
    assert.equal(usage.input_tokens, null);
    assert.equal(usage.stages[0].resolved_model, stage.resolved_model);
    assert.equal(usage.stages[0].calls, 1);
    assert.equal(usage.stages[0].reasoning_tokens, 5);
    assert.equal(usage.stages[0].pricing.status, 'estimated');
    assert.ok(Math.abs(usage.stages[0].pricing.total_usd - 0.00002112) < 1e-12);
    assert.equal(usage.pricing.status, 'incomplete');
    assert.equal(usage.pricing.total_usd, null);
    assert.ok(Math.abs(usage.pricing.known_usd - 0.00002112) < 1e-12);
    assert.equal(usage.pricing.priced_calls, 1);
    assert.equal(usage.pricing.total_calls, 2);
    assert.ok(!JSON.stringify(usage).includes('synthetic-private'));
    return true;
  });
});

async function database() {
  const sql = new DatabaseSync(':memory:'), queries = [];
  sql.exec(`CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT,nickname TEXT,role TEXT,created_at INTEGER,avatar TEXT,deleted INTEGER DEFAULT 0);
    CREATE TABLE sessions(token_hash TEXT,user_id INTEGER,created_at INTEGER,expires_at INTEGER);
    CREATE TABLE ratelimits(k TEXT PRIMARY KEY,start INTEGER,n INTEGER);`);
  const tokens = {}, now = Math.floor(Date.now() / 1000);
  for (const user of [admin, student]) {
    const token = ('model_test_account_' + user.id).padEnd(48, 'x'); tokens[user.id] = token;
    const hash = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(token))).toString('base64url');
    sql.prepare('INSERT INTO users(id,username,nickname,role,created_at) VALUES(?,?,?,?,?)').run(user.id, 'model' + user.id, 'Model ' + user.id, user.role, now);
    sql.prepare('INSERT INTO sessions VALUES(?,?,?,?)').run(hash, user.id, now, now + 3600);
  }
  const DB = { prepare(query) {
    queries.push(query); const st = sql.prepare(query);
    const make = args => ({
      bind: (...values) => make(values),
      async all() { return { results: st.all(...args) }; },
      async first() { return st.get(...args) || null; },
      async run() { throw new Error('model tests must not mutate exam records'); },
    });
    return make([]);
  } };
  return { sql, queries, DB, tokens };
}

test('the real Worker gates this path before general body parsing and does not touch production tables', async () => {
  const db = await database(), env = { DB: db.DB, ALLOWED_ORIGINS: 'https://haslalab.org' };
  const originalFetch = globalThis.fetch; let calls = 0;
  globalThis.fetch = async () => { calls++; throw new Error('unexpected provider call'); };
  try {
    for (const [id, status] of [[null, 401], [2, 403]]) {
      const original = request('{', { headers: { 'Content-Type': 'application/json', Origin: 'https://haslalab.org', ...(id ? { Authorization: 'Bearer ' + db.tokens[id] } : {}) } });
      let consumed = 0;
      const req = new Proxy(original, { get(target, key) {
        if (['body', 'json', 'text', 'arrayBuffer'].includes(key)) { consumed++; throw new Error('authentication must precede body parsing'); }
        const value = Reflect.get(target, key, target); return typeof value === 'function' ? value.bind(target) : value;
      } });
      const response = await worker.fetch(req, env);
      assert.equal(response.status, status); assert.equal(consumed, 0);
      assert.equal(response.headers.get('Cache-Control'), 'no-store');
    }
    const config = await worker.fetch(new Request(endpoint, { headers: { Authorization: 'Bearer ' + db.tokens[1], Origin: 'https://haslalab.org' } }), env);
    assert.equal(config.status, 200); assert.equal(config.headers.get('Cache-Control'), 'no-store');
    const data = await config.json(); assert.equal(data.pipelines.length, 3); assert.ok(data.pipelines.every(p => !p.available));
    assert.equal(config.headers.get('Access-Control-Allow-Origin'), 'https://haslalab.org');
    env.GEMINI_API_KEY = 'synthetic-gemini-secret'; env.DEEPSEEK_API_KEY = 'synthetic-deepseek-secret';
    const configured = await worker.fetch(new Request(endpoint, { headers: { Authorization: 'Bearer ' + db.tokens[1] } }), env);
    const available = await configured.json();
    assert.ok(available.pipelines.every(p => p.available));
    assert.ok(!JSON.stringify(available).includes('synthetic-'));
    assert.ok(db.queries.every(query => /SELECT u\.id.*sessions s JOIN users/s.test(query)), db.queries.join('\n'));
    assert.equal(calls, 0);
  } finally { globalThis.fetch = originalFetch; db.sql.close(); }
});

test('a real authenticated mixed pipeline writes only its rate-limit admission, never a result or token', async () => {
  const db = await database(), env = { DB: db.DB, GEMINI_API_KEY: 'synthetic-gemini-secret', DEEPSEEK_API_KEY: 'synthetic-deepseek-secret' };
  const originalFetch = globalThis.fetch, providers = [];
  const transcript = { text: '2', legible: true, uncertainties: [] };
  const grade = { status: 'graded', score: 1, feedback: 'Correct.', evidence: [{ quote: '2', reason: 'Matches the expected answer.' }] };
  globalThis.fetch = async (url, options) => {
    providers.push({ url, request: JSON.parse(options.body) });
    return Response.json(providers.length === 1
      ? { candidates: [{ finishReason: 'STOP', content: { parts: [{ text: JSON.stringify(transcript) }] } }], usageMetadata: { promptTokenCount: 12, candidatesTokenCount: 6 } }
      : { choices: [{ finish_reason: 'stop', message: { content: JSON.stringify(grade) } }], usage: { prompt_tokens: 22, completion_tokens: 8 } });
  };
  try {
    const body = { ...validBody, pipeline: 'gemini-deepseek', images: [{ mime: 'image/png', data: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/FXChyoAAAAASUVORK5CYII=' }] };
    const response = await worker.fetch(request(body, { headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + db.tokens[1] } }), env);
    assert.equal(response.status, 200); assert.equal(response.headers.get('Cache-Control'), 'no-store');
    const result = await response.json();
    assert.equal(result.ocr.provider, 'gemini'); assert.equal(result.grading.provider, 'deepseek');
    assert.equal(result.grading.status, 'graded'); assert.equal(result.grading.score, 1);
    assert.equal(providers.length, 2); assert.match(providers[0].url, /^https:\/\/generativelanguage\.googleapis\.com\//);
    assert.equal(providers[1].url, 'https://api.deepseek.com/chat/completions');
    assert.ok(!JSON.stringify(providers[1].request).includes('image_url'));
    assert.ok(db.queries.every(query => /SELECT u\.id.*sessions s JOIN users/s.test(query) || /^INSERT INTO ratelimits/.test(query)), db.queries.join('\n'));
    assert.equal(db.sql.prepare('SELECT COUNT(*) n FROM ratelimits').get().n, 1);
  } finally { globalThis.fetch = originalFetch; db.sql.close(); }
});

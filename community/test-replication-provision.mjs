import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { provisionReplication, runReplicationProvision, REPLICATION_URL } from './provision-replication.mjs';

const reply = (mode, extra = {}) => Response.json({ success: true, result: { read_replication: mode === undefined ? undefined : { mode }, ...extra } });
const quiet = () => {};

test('already-enabled replication is verified with one GET and no PUT', async () => {
  const calls = [], logs = [];
  const result = await provisionReplication(async (...args) => { calls.push(args); return reply('auto', { name: 'PRIVATE_DATABASE_VALUE' }); }, value => logs.push(value), quiet);
  assert.deepEqual(result, { verified: true, mode: 'auto' });
  assert.deepEqual(calls, [['GET', undefined]]);
  assert.equal(logs.join('\n').includes('PRIVATE_DATABASE_VALUE'), false);
});

test('disabled or missing mode performs only PUT auto then an independent GET verification', async () => {
  for (const initial of ['disabled', undefined]) {
    const calls = [];
    const result = await provisionReplication(async (method, body) => {
      calls.push({ method, body });
      return calls.length === 1 ? reply(initial) : calls.length === 2 ? reply('disabled') : reply('auto');
    }, quiet, quiet);
    assert.deepEqual(result, { verified: true, mode: 'auto' });
    assert.deepEqual(calls, [{ method: 'GET', body: undefined }, { method: 'PUT', body: { read_replication: { mode: 'auto' } } }, { method: 'GET', body: undefined }]);
  }
});

test('401 or 403 at any stage is explicitly unverified and never broadens or replaces credentials', async () => {
  for (const status of [401, 403]) for (const failAt of [1, 2, 3]) {
    let calls = 0; const warnings = [], logs = [];
    const result = await provisionReplication(async () => {
      calls++;
      return calls === failAt ? Response.json({ errors: [{ message: 'SECRET_API_PAYLOAD' }] }, { status }) : reply(calls === 1 ? 'disabled' : 'auto');
    }, value => logs.push(value), value => warnings.push(value));
    assert.deepEqual(result, { verified: false, mode: 'unverified' }); assert.equal(calls, failAt);
    assert.equal(warnings.length, 1); assert.ok(warnings[0].includes('HTTP ' + status));
    assert.equal(logs.concat(warnings).join('\n').includes('SECRET_API_PAYLOAD'), false);
  }
});

test('401 during GET, PUT or verification stays unverified, stops immediately and never exposes secrets', async () => {
  for (const failAt of [1, 2, 3]) {
    const calls = [], logs = [], warnings = [], token = 'SECRET_EXISTING_DEPLOY_TOKEN';
    const result = await runReplicationProvision({ token, log: value => logs.push(value), warn: value => warnings.push(value),
      fetchImpl: async (url, options) => {
        calls.push({ url, options });
        return calls.length === failAt
          ? Response.json({ errors: [{ message: 'SECRET_AUTH_PAYLOAD' }] }, { status: 401 })
          : reply(calls.length === 1 ? 'disabled' : 'auto');
      } });
    assert.deepEqual(result, { verified: false, mode: 'unverified' });
    assert.deepEqual(calls.map(call => call.options.method), ['GET', 'PUT', 'GET'].slice(0, failAt));
    assert.ok(calls.every(call => call.url === REPLICATION_URL && call.options.headers.Authorization === 'Bearer ' + token));
    assert.equal(warnings.length, 1); assert.match(warnings[0], /::warning::.*unverified: HTTP 401/);
    assert.match(warnings[0], /No credential or permission changes were attempted/);
    assert.equal(logs.concat(warnings).join('\n').includes('SECRET_'), false);
  }
});

test('network, unexpected HTTP, malformed responses and failed verification fail closed without logging payloads', async () => {
  const scenarios = [
    () => { throw new Error('SECRET_NETWORK_PAYLOAD'); },
    () => new Response('SECRET_SERVER_PAYLOAD', { status: 500 }),
    ...[400, 402, 404, 429].map(status => () => new Response('SECRET_HTTP_PAYLOAD', { status })),
    () => new Response('SECRET_NOT_JSON'),
    () => Response.json({ success: false, errors: [{ message: 'SECRET_API_ERROR' }] }),
    () => Response.json({ success: true }),
    () => reply('SECRET_UNKNOWN_MODE'),
  ];
  for (const response of scenarios) {
    const logs = []; let calls = 0;
    await assert.rejects(provisionReplication(async () => { calls++; return response(); }, value => logs.push(value), value => logs.push(value)), error => !/SECRET_/.test(error.message));
    assert.equal(calls, 1); assert.equal(logs.join('\n').includes('SECRET_'), false);
  }
  let calls = 0;
  await assert.rejects(provisionReplication(async () => { calls++; return reply('disabled'); }, quiet, quiet), /verification failed/);
  assert.equal(calls, 3);
});

test('REST requests target only the existing database with the supplied token and prohibit redirects', async () => {
  const calls = [];
  const result = await runReplicationProvision({ token: 'local-test-credential', log: quiet, warn: quiet, fetchImpl: async (url, options) => {
    calls.push({ url, options });
    return reply(calls.length === 1 ? 'disabled' : 'auto');
  } });
  assert.equal(result.verified, true); assert.equal(calls.length, 3);
  for (const { url, options } of calls) {
    assert.equal(url, REPLICATION_URL);
    assert.equal(options.headers.Authorization, 'Bearer local-test-credential');
    assert.equal(options.redirect, 'error'); assert.ok(options.signal instanceof AbortSignal);
    assert.deepEqual(Object.keys(options.headers).sort(), options.method === 'PUT' ? ['Authorization', 'Content-Type'] : ['Authorization']);
  }
  assert.deepEqual(JSON.parse(calls[1].options.body), { read_replication: { mode: 'auto' } });
  await assert.rejects(runReplicationProvision({ token: '', fetchImpl: () => { throw Error('must not call'); } }), /existing deployment/);
});

test('workflow exposes verified mode as a step output without altering either Worker deployment command', () => {
  const source = readFileSync(new URL('./provision-replication.mjs', import.meta.url), 'utf8');
  const workflow = readFileSync(new URL('../.github/workflows/deploy-worker.yml', import.meta.url), 'utf8');
  assert.match(source, /read_replication=\$\{mode\}/);
  assert.match(workflow, /id: replication\s+run: node provision-replication\.mjs/);
  assert.match(workflow, /community\/provision-replication\.mjs/);
  assert.match(workflow, /- run: npx wrangler deploy\s+env:/);
  assert.match(workflow, /- run: npx wrangler deploy --config wrangler\.edge\.toml\s+env:/);
});

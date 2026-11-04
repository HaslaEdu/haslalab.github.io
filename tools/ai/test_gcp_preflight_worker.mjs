// Offline only. RSA keys are generated in memory; no real credentials/providers.
import test from 'node:test';
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { handle, SCOPES, expiryMillis } from './gcp_preflight_worker.mjs';

const NOW = Date.parse('2026-11-05T00:00:00Z');
const TOKEN_URL = 'https://oauth2.googleapis.com/token';
const GATE_TOKEN = 'a'.repeat(64), OAUTH_TOKEN = 'ya29.SYNTHETIC_PRIVATE_OAUTH_TOKEN';
const PRIVATE_ERROR = 'DO_NOT_RETURN_UPSTREAM_MESSAGE_OR_EMAIL';
const encoder = new TextEncoder();
let fixturePromise;
function fixture() {
  if (!fixturePromise) fixturePromise = (async () => {
    const pair = await webcrypto.subtle.generateKey({ name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048,
      publicExponent: Uint8Array.of(1, 0, 1), hash: 'SHA-256' }, true, ['sign', 'verify']);
    const der = await webcrypto.subtle.exportKey('pkcs8', pair.privateKey);
    const pem = '-----BEGIN PRIVATE KEY-----\n' + Buffer.from(der).toString('base64').match(/.{1,64}/g).join('\n') + '\n-----END PRIVATE KEY-----\n';
    const digest = Buffer.from(await webcrypto.subtle.digest('SHA-256', encoder.encode(GATE_TOKEN))).toString('hex');
    return { pair, env: { GCP_SA_KEY: JSON.stringify({ type: 'service_account', project_id: 'project-hasla',
      client_email: 'preflight-fixture@project-hasla.iam.gserviceaccount.com', private_key: pem, token_uri: TOKEN_URL }),
      GCP_PROJECT: 'project-hasla', GCP_TUNING_BUCKET: 'gs://hasla-training',
      GCP_PREFLIGHT_AUTH_SHA256: digest, GCP_PREFLIGHT_EXPIRES_AT: '2026-11-05T00:15:00Z' } };
  })();
  return fixturePromise;
}
const request = (path = '/preflight', method = 'GET', auth = true) => new Request('https://isolated.invalid' + path,
  { method, headers: auth ? { Authorization: 'Bearer ' + GATE_TOKEN } : {} });
const json = (value, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } });
function provider(options = {}) {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url: String(url), ...init });
    assert.equal(init.redirect, 'manual');
    assert.ok(init.signal instanceof AbortSignal);
    if (url === TOKEN_URL) return options.oauthResponse ? options.oauthResponse() : json({ access_token: OAUTH_TOKEN, token_type: 'Bearer' });
    assert.equal(init.headers.Authorization, 'Bearer ' + OAUTH_TOKEN);
    if (options.apiResponse) { const response = options.apiResponse(String(url), calls); if (response) return response; }
    if (String(url).endsWith(':testIamPermissions')) {
      assert.equal(init.method, 'POST');
      const permissions = JSON.parse(init.body).permissions;
      assert.deepEqual(permissions, ['aiplatform.customJobs.create', 'aiplatform.customJobs.get', 'aiplatform.customJobs.list', 'aiplatform.customJobs.cancel']);
      return json({ permissions: [...permissions, PRIVATE_ERROR] });
    }
    assert.equal(init.method, 'GET'); assert.equal(init.body, undefined);
    if (String(url).includes('/consumerQuotaMetrics')) return json({ metrics: [{
      metric: 'aiplatform.googleapis.com/custom_model_training_nvidia_a100_80gb_gpus',
      displayName: PRIVATE_ERROR, consumerQuotaLimits: [{ quotaBuckets: [
        { dimensions: { region: 'us-central1' }, effectiveLimit: '1' },
        { dimensions: { region: 'europe-west4' }, effectiveLimit: '999' },
      ] }],
    }] });
    if (String(url).includes('serviceusage.googleapis.com')) return json({ state: 'ENABLED', config: { secret: PRIVATE_ERROR } });
    if (String(url).includes('storage.googleapis.com')) return json({ location: 'US', secret: PRIVATE_ERROR });
    return json({ quotas: [
      { metric: 'GPUS_ALL_REGIONS', limit: 1, usage: 0 },
      { metric: 'NVIDIA_A100_80GB_GPUS', limit: 1, usage: 0 },
      { metric: 'SECRET_GPU_' + PRIVATE_ERROR, limit: 500, usage: 0 },
      { metric: '__proto__', limit: 999, usage: 0 },
      { metric: 'CPUS', limit: 100, usage: 0 },
    ], defaultServiceAccount: PRIVATE_ERROR, commonInstanceMetadata: { private_key: PRIVATE_ERROR } });
  };
  return { calls, fetchImpl };
}
async function run(envChanges = {}, options = {}, req = request()) {
  const f = await fixture(), mock = provider(options);
  const response = await handle(req, { ...f.env, ...envChanges }, { fetchImpl: mock.fetchImpl, cryptoImpl: webcrypto, now: NOW });
  return { response, body: await response.json(), calls: mock.calls, f };
}

test('authorized flow uses required Vertex scope with fixed read and IAM-test endpoints', async () => {
  const { response, body, calls, f } = await run();
  assert.equal(response.status, 200); assert.equal(response.headers.get('Cache-Control'), 'no-store');
  assert.equal(body.gpu_creation_attempted, false); assert.equal(body.write_api_calls, 0);
  assert.equal(calls.filter(c => c.method === 'POST').length, 2);
  assert.equal(calls.filter(c => c.method === 'GET').length, 13);
  assert.ok(calls.every(c => c.method === 'GET' || c.url === TOKEN_URL || c.url.endsWith(':testIamPermissions')));
  const assertion = new URLSearchParams(calls[0].body).get('assertion');
  const [header, claims, signature] = assertion.split('.');
  const payload = JSON.parse(Buffer.from(claims, 'base64url'));
  assert.equal(payload.scope, SCOPES.join(' '));
  assert.equal(payload.aud, TOKEN_URL); assert.equal(payload.iat, Math.floor(NOW / 1000));
  assert.ok(payload.exp <= payload.iat + 600);
  assert.equal(payload.scope.includes('https://www.googleapis.com/auth/cloud-platform '), false);
  assert.ok(await webcrypto.subtle.verify('RSASSA-PKCS1-v1_5', f.pair.publicKey, Buffer.from(signature, 'base64url'), encoder.encode(header + '.' + claims)));
  const output = JSON.stringify(body);
  assert.equal(output.includes(OAUTH_TOKEN), false); assert.equal(output.includes(PRIVATE_ERROR), false);
  assert.equal(output.includes('private_key'), false); assert.equal(output.includes('client_email'), false);
  assert.equal(output.includes('preflight-fixture'), false); assert.equal(output.includes('__proto__'), false);
  assert.equal(body.checks.find(c => c.target === 'vertex_custom_gpu_quotas').quotas.length, 1);
  assert.deepEqual(body.checks.find(c => c.target === 'vertex_custom_job_permissions').permissions,
    ['aiplatform.customJobs.create', 'aiplatform.customJobs.get', 'aiplatform.customJobs.list', 'aiplatform.customJobs.cancel']);
});

test('GPU quota case and default bucket are retained without assuming a regional allocation', async () => {
  const { body } = await run({}, { apiResponse(url) {
    if (url.includes('/consumerQuotaMetrics')) return json({ metrics: [{
      metric: 'aiplatform.googleapis.com/custom_model_training_nvidia_a100_80GB_gpus',
      consumerQuotaLimits: [{ quotaBuckets: [{ dimensions: {}, effectiveLimit: '0' },
        { dimensions: { region: 'us-central1' }, effectiveLimit: '1' }] }],
    }] });
  } });
  const rows = body.checks.find(c => c.target === 'vertex_custom_gpu_quotas').quotas;
  assert.deepEqual(rows, [{ gpu: 'nvidia_a100_80gb', region: 'global_default', limit: 0 },
    { gpu: 'nvidia_a100_80gb', region: 'us-central1', limit: 1 }]);
});

test('object permission check returns only three fixed permission names', async () => {
  const { body, calls } = await run({}, { apiResponse(url) {
    if (url.includes('/iam/testPermissions')) return json({ permissions: ['storage.objects.get', 'storage.objects.create', PRIVATE_ERROR] });
  } });
  assert.deepEqual(body.checks.find(c => c.target === 'gcs_object_permissions').permissions,
    ['storage.objects.get', 'storage.objects.create']);
  assert.equal(JSON.stringify(body).includes(PRIVATE_ERROR), false);
  assert.equal(calls.find(c => c.url.includes('/iam/testPermissions')).method, 'GET');
});

test('FULL proto3 quota bucket omitted int64 is zero while absent and invalid schemas stay unavailable', async () => {
  const { body } = await run({}, { apiResponse(url) {
    if (url.includes('/consumerQuotaMetrics')) return json({ metrics: [{
      metric: 'aiplatform.googleapis.com/custom_model_training_nvidia_a100_80gb_gpus',
      consumerQuotaLimits: [{ quotaBuckets: [{}, { dimensions: { region: 'us-central1' } },
        { dimensions: { region: 'us-east4' }, effectiveLimit: null }, null, []] }, {}],
    }, { metric: 'aiplatform.googleapis.com/custom_model_training_nvidia_h100_gpus' }] });
  } });
  const rows = body.checks.find(c => c.target === 'vertex_custom_gpu_quotas').quotas;
  assert.deepEqual(rows, [
    { gpu: 'nvidia_a100_80gb', region: 'global_default', limit: 0, limit_basis: 'proto3_default_zero' },
    { gpu: 'nvidia_a100_80gb', region: 'us-central1', limit: 0, limit_basis: 'proto3_default_zero' },
  ]);
});

test('guest, expired, wrong path/query, and write methods never read SA or call provider', async () => {
  const f = await fixture(); let reads = 0, calls = 0;
  const secretEnv = { ...f.env }; Object.defineProperty(secretEnv, 'GCP_SA_KEY', { get() { reads++; throw new Error('secret touched'); } });
  const expiredEnv = Object.create(secretEnv); expiredEnv.GCP_PREFLIGHT_EXPIRES_AT = '2026-11-04T23:59:59Z';
  for (const [req, env] of [
    [request('/preflight', 'GET', false), secretEnv], [request('/other'), secretEnv],
    [request('/preflight?url=https://example.invalid'), secretEnv], [request('/preflight', 'POST'), secretEnv],
    [request(), expiredEnv],
  ]) {
    const response = await handle(req, env, { cryptoImpl: webcrypto, now: NOW, fetchImpl: () => { calls++; throw new Error('network forbidden'); } });
    assert.ok(response.status >= 400);
  }
  assert.equal(reads, 0); assert.equal(calls, 0);
});

test('incorrect bearer, missing or excessive expiry fail closed before GCP config', async () => {
  for (const change of [ { GCP_PREFLIGHT_AUTH_SHA256: '0'.repeat(64) }, { GCP_PREFLIGHT_EXPIRES_AT: undefined },
    { GCP_PREFLIGHT_EXPIRES_AT: '2026-11-06T00:00:00Z' }, { GCP_PREFLIGHT_AUTH_SHA256: 'bad' } ]) {
    const { response, calls } = await run(change); assert.equal(response.status, 403); assert.equal(calls.length, 0);
  }
});

test('all unrelated inherited bindings remain unread', async () => {
  const f = await fixture(), mock = provider();
  const allowed = new Set(Object.keys(f.env));
  const env = new Proxy(f.env, { get(target, key) { assert.ok(allowed.has(key)); return target[key]; } });
  const response = await handle(request(), env, { fetchImpl: mock.fetchImpl, cryptoImpl: webcrypto, now: NOW });
  assert.equal(response.status, 200);
});

test('project, bucket, SA project, or token URI mismatch never reaches OAuth', async () => {
  const f = await fixture(), key = JSON.parse(f.env.GCP_SA_KEY);
  for (const changes of [{ GCP_PROJECT: 'other-project' }, { GCP_TUNING_BUCKET: 'gs://other-bucket' },
    { GCP_SA_KEY: JSON.stringify({ ...key, project_id: 'other-project' }) },
    { GCP_SA_KEY: JSON.stringify({ ...key, token_uri: 'https://example.invalid/token' }) }, { GCP_SA_KEY: '{bad' }]) {
    const { response, calls } = await run(changes); assert.equal(response.status, 503); assert.equal(calls.length, 0);
  }
});

test('default Compute service-account domain is accepted without disclosing its email', async () => {
  const f = await fixture(), key = JSON.parse(f.env.GCP_SA_KEY);
  const email = '123456789012-compute@developer.gserviceaccount.com';
  const result = await run({ GCP_SA_KEY: JSON.stringify({ ...key, client_email: email }) });
  assert.equal(result.response.status, 200); assert.equal(JSON.stringify(result.body).includes(email), false);
});

test('upstream OAuth errors return only enum and status without error text or key material', async () => {
  const { response, body, calls } = await run({}, { oauthResponse: () => json({ error: 'invalid_grant', error_description: PRIVATE_ERROR }, 400) });
  assert.equal(response.status, 502); assert.equal(body.oauth.reason, 'invalid_grant'); assert.equal(calls.length, 1);
  assert.equal(JSON.stringify(body).includes(PRIVATE_ERROR), false);
});

test('API errors retain fixed ErrorInfo reason and suppress all messages', async () => {
  const { body } = await run({}, { apiResponse: url => url.includes('compute.googleapis.com/compute/')
    ? json({ error: { status: 'PERMISSION_DENIED', message: PRIVATE_ERROR, details: [{ reason: 'ACCESS_TOKEN_SCOPE_INSUFFICIENT', metadata: { secret: PRIVATE_ERROR } }] } }, 403) : null });
  assert.equal(body.checks[0].reason, 'ACCESS_TOKEN_SCOPE_INSUFFICIENT');
  assert.equal(JSON.stringify(body).includes(PRIVATE_ERROR), false);
});

test('OAuth and API redirects are never followed', async () => {
  let result = await run({}, { oauthResponse: () => new Response(null, { status: 302, headers: { Location: 'https://example.invalid/leak' } }) });
  assert.equal(result.calls.length, 1); assert.equal(result.body.oauth.reason, 'redirect_rejected');
  result = await run({}, { apiResponse: () => new Response(null, { status: 302, headers: { Location: 'https://example.invalid/leak' } }) });
  assert.ok(result.body.checks.every(c => c.reason === 'redirect_rejected'));
  assert.ok(result.calls.every(c => !c.url.includes('example.invalid')));
});

test('quota pagination stays on fixed API and is capped without claiming complete inventory', async () => {
  let page = 0;
  const { body, calls } = await run({}, { apiResponse: url => url.includes('/consumerQuotaMetrics') ? json({ metrics: [], nextPageToken: 'opaque-' + (++page) }) : null });
  const quota = body.checks.find(c => c.target === 'vertex_custom_gpu_quotas');
  assert.equal(page, 5); assert.equal(quota.quota_inventory_complete, false);
  assert.equal(calls.filter(c => c.url.includes('/consumerQuotaMetrics')).length, 5);
});

test('oversized responses and transport errors return fixed failures', async () => {
  const { body } = await run({}, { apiResponse: url => url.includes('storage.googleapis.com')
    ? new Response('{}', { status: 200, headers: { 'Content-Length': '9000000' } }) : null });
  assert.equal(body.checks.find(c => c.target === 'gcs_bucket_metadata').reason, 'malformed_or_oversized_response');
  const f = await fixture();
  const response = await handle(request(), f.env, { cryptoImpl: webcrypto, now: NOW, fetchImpl: () => { throw new Error(PRIVATE_ERROR); } });
  const output = await response.text(); assert.equal(output.includes(PRIVATE_ERROR), false); assert.ok(output.includes('transport_unavailable'));
});

test('non-finite/boolean/unknown quotas are omitted and missing data is not a zero quota', async () => {
  const { body } = await run({}, { apiResponse: url => url.includes('compute.googleapis.com/compute/')
    ? json({ quotas: [{ metric: 'NVIDIA_A100_GPUS', limit: true, usage: 0 }, { metric: 'NVIDIA_H100_GPUS', limit: 'NaN', usage: 0 }], quotaStatusWarning: { code: PRIVATE_ERROR } }) : null });
  assert.deepEqual(body.checks[0].quotas, []); assert.equal(body.checks[0].quota_fields_available, false);
});

test('expiry uses canonical UTC timestamps only', () => {
  assert.equal(expiryMillis('2026-02-31T00:00:00Z'), null);
  assert.equal(expiryMillis('1760000000'), null);
  assert.equal(expiryMillis('2026-11-05T00:15:00Z'), NOW + 900000);
});

test('gate expiry during OAuth prevents all subsequent provider GETs', async () => {
  const f = await fixture(); let current = NOW, calls = 0;
  const response = await handle(request(), f.env, { cryptoImpl: webcrypto, now: NOW, currentTime: () => current,
    fetchImpl: async (url, options) => {
      calls++; assert.equal(url, TOKEN_URL); assert.equal(options.method, 'POST');
      current = NOW + 900000;
      return json({ access_token: OAUTH_TOKEN, token_type: 'Bearer' });
    } });
  const body = await response.json();
  assert.equal(calls, 1); assert.ok(body.checks.every(check => check.reason === 'transport_unavailable'));
});

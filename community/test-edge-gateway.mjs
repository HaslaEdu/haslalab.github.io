// Service-binding and Cache API stand-ins only: no network, database, keys or production requests.
import assert from 'node:assert/strict';
import test from 'node:test';
import gateway from './src/edge-gateway.js';

const ORIGIN = 'https://haslalab.org', OTHER = 'http://localhost:8765';
const defer = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; };
const tick = () => new Promise(resolve => setTimeout(resolve, 0));
function harness(handler = () => Response.json({ ok: true })) {
  const stored = new Map(), calls = [], tasks = [];
  const cache = {
    async match(key) { return stored.get(key.url)?.clone(); },
    async put(key, response) { stored.set(key.url, response.clone()); },
  };
  globalThis.caches = { default: cache };
  const env = { ALLOWED_ORIGINS: ORIGIN + ',' + OTHER, COMMUNITY: { async fetch(request) { calls.push(request); return handler(request, calls.length); } } };
  return { cache, stored, calls, tasks,
    request(path, options = {}) { return gateway.fetch(new Request('https://haslalab-community-edge.haslalab.workers.dev' + path, options), env, { waitUntil: promise => tasks.push(promise) }); },
    async flush() { while (tasks.length) await Promise.all(tasks.splice(0)); },
  };
}

test('preflight stays local and CORS is recalculated for every origin', async () => {
  const h = harness();
  let response = await h.request('/api/me', { method: 'OPTIONS', headers: { Origin: ORIGIN } });
  assert.equal(response.status, 204);
  assert.equal(response.headers.get('Access-Control-Allow-Origin'), ORIGIN);
  assert.match(response.headers.get('Access-Control-Allow-Headers'), /Authorization/);
  assert.match(response.headers.get('Access-Control-Allow-Headers'), /X-Monthly-Scan/);
  assert.equal(response.headers.get('Access-Control-Max-Age'), '86400');
  assert.equal(response.headers.get('Cache-Control'), 'no-store');
  response = await h.request('/api/me', { method: 'OPTIONS', headers: { Origin: 'https://untrusted.test' } });
  assert.equal(response.headers.has('Access-Control-Allow-Origin'), false);
  assert.equal(h.calls.length, 0);
});

test('invariant public GET cache crosses auth while canonical queries and caller CORS stay correct', async () => {
  const h = harness(() => Response.json({ posts: [{ id: 1 }] }, { headers: {
    'Cache-Control': 'no-store', 'Vary': 'Origin', 'Access-Control-Allow-Origin': ORIGIN,
    'Server-Timing': 'db;desc="1 queries";dur=10, total;dur=12', 'X-Edge-Cache': 'hit',
  } }));
  const first = await h.request('/api/posts?lang=ko&board=free&case=public', { headers: { Authorization: 'Bearer first', Origin: ORIGIN } });
  assert.equal(first.headers.get('X-Edge-Cache'), 'miss');
  assert.equal(first.headers.get('X-Origin-Edge-Cache'), 'hit');
  assert.match(first.headers.get('Server-Timing'), /db;desc="1 queries";dur=10/);
  assert.match(first.headers.get('Server-Timing'), /gateway;desc="miss GET \/api\/posts 200"/);
  assert.equal(first.headers.get('Cache-Control'), 'no-store');
  await first.text(); await h.flush();
  const hit = await h.request('/api/posts?case=public&board=free&lang=ko', { headers: { Authorization: 'Bearer second', Origin: OTHER } });
  assert.equal(h.calls.length, 1);
  assert.equal(hit.headers.get('X-Edge-Cache'), 'hit');
  assert.equal(hit.headers.get('Access-Control-Allow-Origin'), OTHER);
  assert.match(hit.headers.get('Server-Timing'), /db;desc="0 queries";dur=0/);
  assert.deepEqual(await hit.json(), { posts: [{ id: 1 }] });
  const denied = await h.request('/api/posts?lang=ko&case=public&board=free', { headers: { Origin: 'https://untrusted.test' } });
  assert.equal(denied.headers.has('Access-Control-Allow-Origin'), false);
  assert.equal([...h.stored.values()][0].headers.get('Cache-Control'), 'public, max-age=15');
});

test('private paths, authenticated rankings, writes and unsafe upstream responses never enter shared cache', async () => {
  const paths = ['/api/me', '/api/me/overview', '/api/users/Person', '/api/posts/7?view=1', '/api/lab/tokens', '/api/lab/sessions/7', '/api/pay/status?id=7', '/api/monthly/scan', '/api/monthly/problems/4/scan/00000000-0000-0000-0000-000000000000'];
  const h = harness(() => Response.json({ private: true }, { headers: { 'Cache-Control': 'public, max-age=999', 'Access-Control-Allow-Origin': ORIGIN } }));
  for (const path of paths) for (let i = 0; i < 2; i++) {
    const response = await h.request(path, { headers: { Authorization: 'Bearer account' } });
    assert.equal(response.headers.get('Cache-Control'), 'no-store'); await response.text();
  }
  assert.equal(h.calls.length, paths.length * 2);
  for (const headers of [{ Authorization: 'Bearer account' }, { Cookie: 'session=account' }, { 'X-Lab-Token': 'scan' }, { 'X-Monthly-Scan': 'monthly-scan' }]) {
    await (await h.request('/api/rank?case=private', { headers })).text();
    await (await h.request('/api/weekly?case=private', { headers })).text();
  }
  await (await h.request('/api/posts', { method: 'POST', body: '{}' })).text();
  await h.flush(); assert.equal(h.stored.size, 0);
  for (const [index, response] of [
    new Response('error', { status: 503, headers: { 'Content-Type': 'application/json' } }),
    new Response('html', { headers: { 'Content-Type': 'text/html' } }),
    Response.json({ ok: true }, { headers: { 'Set-Cookie': 'private=1' } }),
    Response.json({ ok: true }, { headers: { 'Cache-Control': 'private, no-store' } }),
    Response.json({ ok: true }, { headers: { Vary: 'Authorization' } }),
  ].entries()) {
    const unsafe = harness(() => response.clone());
    await (await unsafe.request('/api/health?unsafe=' + index)).text(); await unsafe.flush();
    assert.equal(unsafe.stored.size, 0);
  }
});

test('request body, auth, scan code, client IP, URL and manual OAuth redirects survive service binding forwarding', async () => {
  const binary = new Uint8Array([0, 255, 13, 10, 128]);
  const h = harness(async request => {
    const url = new URL(request.url);
    assert.equal(url.origin, 'https://haslalab-community.haslalab.workers.dev');
    assert.equal(request.redirect, 'manual');
    if (request.method === 'PUT') {
      assert.equal(url.pathname + url.search, '/api/lab/up/pages?task=Q5&kind=answer');
      assert.deepEqual(new Uint8Array(await request.arrayBuffer()), binary);
      for (const [name, value] of Object.entries({ Authorization: 'Bearer owner', 'X-Lab-Token': 'scan-code', 'CF-Connecting-IP': '203.0.113.12', Origin: ORIGIN })) assert.equal(request.headers.get(name), value);
      assert.equal(request.headers.has('X-Hasla-IP-Check'), false);
      return Response.json({ uploaded: true });
    }
    const location = new URL('https://provider.test/authorize');
    location.searchParams.set('redirect_uri', url.origin + '/api/oauth/google/callback');
    return new Response(null, { status: 302, headers: { Location: location, 'Cache-Control': 'no-store' } });
  });
  const upload = await h.request('/api/lab/up/pages?task=Q5&kind=answer', { method: 'PUT', body: binary, headers: { Authorization: 'Bearer owner', 'X-Lab-Token': 'scan-code', 'CF-Connecting-IP': '203.0.113.12', Origin: ORIGIN, 'X-Hasla-IP-Check': 'caller-controlled' } });
  assert.equal(upload.status, 200);
  const redirect = await h.request('/api/oauth/google/start?return_to=https%3A%2F%2Fhaslalab.org%2F');
  assert.equal(redirect.status, 302);
  assert.equal(new URL(redirect.headers.get('Location')).searchParams.get('redirect_uri'), 'https://haslalab-community.haslalab.workers.dev/api/oauth/google/callback');
  assert.equal(h.stored.size, 0);
});

test('monthly scan capabilities forward in their private header without entering shared caches or diagnostics', async () => {
  const token='local-monthly-capability'.padEnd(43,'x');
  const h=harness(request=>{
    assert.equal(request.headers.get('X-Monthly-Scan'),token);
    assert.equal(request.headers.has('Authorization'),false);
    assert.equal(request.url.includes(token),false);
    return Response.json({ok:true});
  });
  for(const path of ['/api/monthly/scan','/api/monthly'])for(let i=0;i<2;i++){
    const r=await h.request(path,{headers:{'X-Monthly-Scan':token}});
    assert.equal(r.headers.get('Cache-Control'),'no-store');assert.equal(r.headers.get('X-Edge-Cache'),'bypass');
    assert.equal(r.headers.get('Server-Timing').includes(token),false);await r.text();
  }
  await h.flush();assert.equal(h.calls.length,4);assert.equal(h.stored.size,0);
});

test('public misses coalesce across accounts and cache writes never block responses', async () => {
  const upstream = defer(), put = defer();
  const h = harness(() => upstream.promise);
  const originalPut = h.cache.put;
  h.cache.put = async (...args) => { await put.promise; return originalPut(...args); };
  const requests = Array.from({ length: 6 }, (_, i) => h.request('/api/boards?case=coalesce', { headers: { Authorization: 'Bearer ' + i, Origin: i % 2 ? ORIGIN : OTHER } }));
  await tick(); assert.equal(h.calls.length, 1);
  upstream.resolve(Response.json({ boards: [] }));
  const responses = await Promise.race([Promise.all(requests), new Promise(resolve => setTimeout(() => resolve(null), 100))]);
  assert.ok(responses, 'background put must not delay the API result');
  assert.equal(responses.filter(r => r.headers.get('X-Edge-Cache') === 'coalesced').length, 5);
  for (const [i, response] of responses.entries()) { assert.equal(response.headers.get('Access-Control-Allow-Origin'), i % 2 ? ORIGIN : OTHER); await response.text(); }
  assert.equal(h.stored.size, 0);
  put.resolve(); await h.flush(); assert.equal(h.stored.size, 1);
});

test('refresh bypasses both caches, supersedes old reads and cannot be overwritten by an older background put', async () => {
  const blockedPut = defer();
  const h = harness(request => {
    if (h.calls.length === 2) assert.equal(request.headers.get('Cache-Control'), 'no-cache');
    return Response.json({ version: h.calls.length });
  });
  const originalPut = h.cache.put; let puts = 0;
  h.cache.put = async (...args) => { if (++puts === 1) await blockedPut.promise; return originalPut(...args); };
  assert.equal((await (await h.request('/api/posts?case=refresh')).json()).version, 1);
  await tick();
  const fresh = await h.request('/api/posts?case=refresh', { headers: { 'Cache-Control': 'no-cache' } });
  assert.equal(fresh.headers.get('X-Edge-Cache'), 'refresh'); assert.equal((await fresh.json()).version, 2);
  for (let i = 0; i < 8; i++) await (await h.request('/api/posts?case=refresh', { headers: { 'Cache-Control': 'no-cache' } })).text();
  assert.equal(puts, 1, 'a blocked put retains only the latest replacement');
  blockedPut.resolve(); await h.flush();
  assert.equal(puts, 2);
  assert.equal((await (await h.request('/api/posts?case=refresh')).json()).version, 10);
  assert.equal(h.calls.length, 10);
  const delayed = defer(), late = harness((_request, count) => count === 1 ? delayed.promise : Response.json({ version: 2 }));
  const old = late.request('/api/posts?case=late'); await tick();
  assert.equal((await (await late.request('/api/posts?case=late', { headers: { 'Cache-Control': 'no-store' } })).json()).version, 2);
  delayed.resolve(Response.json({ version: 1 })); await (await old).text(); await late.flush();
  assert.equal((await (await late.request('/api/posts?case=late')).json()).version, 2);
});

test('settings and keyed avatars retain only their safe browser cache policies; diagnostic is never cached', async () => {
  const h = harness(async request => {
    const url = new URL(request.url);
    if (url.pathname === '/api/avatar/missingkey') return new Response(null, { status: 404, headers: { 'Cache-Control': 'public, max-age=300' } });
    if (url.pathname.startsWith('/api/avatar/')) return new Response(new Uint8Array([1, 2]), { headers: { 'Content-Type': 'image/webp', 'Cache-Control': 'public, max-age=31536000, immutable', 'Content-Security-Policy': "default-src 'none'", 'X-Content-Type-Options': 'nosniff' } });
    if (url.searchParams.get('transport_check') === '1') {
      assert.equal(request.headers.get('Cache-Control'), 'no-cache');
      if (!request.headers.get('CF-Connecting-IP')) {
        assert.equal(request.headers.get('X-Hasla-IP-Check'), 'missing');
        return Response.json({ ok: true }, { headers: { 'X-Hasla-IP-Preserved': '0' } });
      }
      const expected = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode('203.0.113.45'))).toString('base64url');
      assert.equal(request.headers.get('X-Hasla-IP-Check'), expected);
      return Response.json({ ok: true }, { headers: { 'X-Hasla-IP-Preserved': '1' } });
    }
    return Response.json({ ok: true });
  });
  const health = await h.request('/api/health?case=settings'); await health.text(); await h.flush();
  assert.equal(health.headers.get('Cache-Control'), 'public, max-age=300');
  assert.equal([...h.stored.values()][0].headers.get('Cache-Control'), 'public, max-age=300');
  const avatar = await h.request('/api/avatar/abcdefgh');
  assert.equal(avatar.headers.get('Cache-Control'), 'public, max-age=31536000, immutable');
  assert.equal(avatar.headers.get('Content-Security-Policy'), "default-src 'none'");
  assert.equal(avatar.headers.get('X-Content-Type-Options'), 'nosniff'); await avatar.text();
  assert.equal((await h.request('/api/avatar/missingkey')).headers.get('Cache-Control'), 'public, max-age=300');
  const diagnostic = await h.request('/api/health?transport_check=1', { headers: { 'CF-Connecting-IP': '203.0.113.45', 'X-Hasla-IP-Check': 'forged' } });
  assert.equal(diagnostic.headers.get('Cache-Control'), 'no-store');
  assert.equal(diagnostic.headers.get('X-Hasla-IP-Preserved'), '1');
  assert.equal(diagnostic.headers.has('X-Hasla-IP-Check'), false); await diagnostic.text(); await h.flush();
  const missingIP = await h.request('/api/health?transport_check=1');
  assert.equal(missingIP.headers.get('X-Hasla-IP-Preserved'), '0'); await missingIP.text(); await h.flush();
  assert.equal(h.stored.size, 1);
});

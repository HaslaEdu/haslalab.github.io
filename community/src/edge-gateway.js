// Public SELECTs and cache hits stay near the visitor. The placed Worker owns private checks, writes and secrets.
import { readAtEdge } from './public-reader.js';
const BACKEND_ORIGIN = 'https://haslalab-community.haslalab.workers.dev';
const PUBLIC_GET = /^\/api\/(?:health|boards|posts|lab\/stats|pay\/config|lab\/contest\/catalog)$/;
const ANONYMOUS_GET = /^\/api\/(?:monthly|weekly|rank)$/;
const SETTINGS = /^\/api\/(?:health|pay\/config|lab\/contest\/catalog)$/;
const AVATAR = /^\/api\/avatar\/[A-Za-z0-9_-]{8,32}$/;
const MAX_PENDING = 128, PENDING_MS = 5000;
const pending = new Map(), writes = new Map();
const refreshRequested = request => /\b(?:no-cache|no-store|max-age\s*=\s*0)\b/i.test(request.headers.get('Cache-Control') || '');

function corsHeaders(request, env, headers) {
  for (const key of [...headers.keys()]) if (key.startsWith('access-control-')) headers.delete(key);
  const origin = request.headers.get('Origin') || '';
  const allowed = (env.ALLOWED_ORIGINS || '').split(',').map(s => s.trim()).filter(Boolean);
  if (allowed.includes(origin)) headers.set('Access-Control-Allow-Origin', origin);
  headers.set('Access-Control-Allow-Methods', 'GET,POST,PUT,PATCH,DELETE,OPTIONS');
  headers.set('Access-Control-Allow-Headers', 'Authorization,Content-Type,X-Lab-Token,Cache-Control');
  headers.set('Access-Control-Max-Age', '86400');
  headers.set('Access-Control-Expose-Headers', 'X-D1-Bookmark,X-Public-Read-Source');
  const vary = (headers.get('Vary') || '').split(',').map(v => v.trim()).filter(Boolean);
  if (!vary.some(v => v.toLowerCase() === 'origin')) vary.push('Origin');
  headers.set('Vary', vary.join(', '));
}

function publicPolicy(request, url) {
  if (request.method !== 'GET' || url.href.length > 4096 || url.searchParams.has('view')) return null;
  const anonymous = !request.headers.get('Authorization') && !request.headers.get('Cookie') && !request.headers.get('X-Lab-Token');
  if (!PUBLIC_GET.test(url.pathname) && !(anonymous && ANONYMOUS_GET.test(url.pathname))) return null;
  const key = new URL(url.pathname + url.search, 'https://haslalab-community-edge.haslalab.workers.dev');
  key.searchParams.sort(); // Stable for duplicate keys: preserve the backend's first-value semantics.
  return { key: new Request(key), ttl: SETTINGS.test(url.pathname) ? 300 : 15 };
}

function cacheable(response) {
  return response.status === 200 && /^application\/(?:json|[\w.+-]+\+json)(?:\s*;|$)/i.test(response.headers.get('Content-Type') || '')
    && !response.headers.has('Set-Cookie') && !/\bprivate\b/i.test(response.headers.get('Cache-Control') || '')
    && !(response.headers.get('Vary') || '').split(',').some(v => v.trim() && v.trim().toLowerCase() !== 'origin');
}

function browserCache(response, request, url, diagnostic) {
  if (request.method !== 'GET' || diagnostic) return 'no-store';
  if (SETTINGS.test(url.pathname) && cacheable(response)) return 'public, max-age=300';
  if (AVATAR.test(url.pathname) && !response.headers.has('Set-Cookie')) {
    const value = response.headers.get('Cache-Control') || '';
    if (response.status === 200 && /^image\//i.test(response.headers.get('Content-Type') || '') && /^public,\s*max-age=31536000,\s*immutable$/i.test(value)) return value;
    if (response.status === 404 && /^public,\s*max-age=300$/i.test(value)) return value;
  }
  return 'no-store';
}

function finish(response, request, env, started, state, { hit = false, diagnostic = false } = {}) {
  const headers = new Headers(response.headers), url = new URL(request.url), elapsed = Date.now() - started;
  const originalCache = headers.get('X-Edge-Cache');
  if (originalCache && !hit) headers.set('X-Origin-Edge-Cache', originalCache);
  headers.set('X-Edge-Cache', state);
  headers.set('Cache-Control', browserCache(response, request, url, diagnostic));
  corsHeaders(request, env, headers);
  const route = url.pathname.replace(/["\\\x00-\x20\x7f-\uffff]/g, '').slice(0, 240);
  const timing = hit ? `db;desc="0 queries";dur=0, total;dur=${elapsed}` : headers.get('Server-Timing');
  headers.set('Server-Timing', `${timing ? timing + ', ' : ''}gateway;desc="${state} ${request.method} ${route} ${response.status}";dur=${elapsed}`);
  headers.set('Timing-Allow-Origin', '*');
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

function forwardRequest(request, url) {
  const backend = new URL(url.pathname + url.search, BACKEND_ORIGIN);
  const forwarded = new Request(backend, request);
  const headers = new Headers(forwarded.headers);
  // A caller cannot provide an internal diagnostic. CF-Connecting-IP itself is passed unchanged.
  headers.delete('X-Hasla-IP-Check');
  return new Request(forwarded, { headers, redirect: 'manual' });
}

async function ipDiagnostic(request, forwarded) {
  const originalIP = request.headers.get('CF-Connecting-IP');
  if (!originalIP) { forwarded.headers.set('X-Hasla-IP-Check', 'missing'); forwarded.headers.set('Cache-Control', 'no-cache'); return; }
  const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(originalIP));
  let bytes = '';
  for (const byte of new Uint8Array(hash)) bytes += String.fromCharCode(byte);
  forwarded.headers.set('X-Hasla-IP-Check', btoa(bytes).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''));
  forwarded.headers.set('Cache-Control', 'no-cache');
}

function background(ctx, promise) {
  const safe = promise.catch(() => {}); // A cache failure must not turn a successful API response into an error.
  if (ctx?.waitUntil) ctx.waitUntil(safe);
}

function queueWrite(key, entry, stored, policy, ctx) {
  let writer = writes.get(key);
  const desired = { entry, stored };
  if (writer) {
    // A slow Cache API write retains one newest replacement, never an unbounded promise chain.
    if (writer.desired?.stored.body) writer.desired.stored.body.cancel().catch(() => {});
    writer.desired = desired;
    background(ctx, writer.done);
    return;
  }
  writer = { desired, done: null };
  writes.set(key, writer);
  writer.done = Promise.resolve().then(async () => {
    try {
      while (writer.desired) {
        const next = writer.desired; writer.desired = null;
        try {
          if (!next.entry.obsolete && pending.get(key) === next.entry) await caches.default.put(policy.key, next.stored);
        } catch { /* A failed cache put must not block a newer refresh. */ }
        finally { if (pending.get(key) === next.entry) pending.delete(key); }
      }
    } finally { if (writes.get(key) === writer) writes.delete(key); }
  });
  background(ctx, writer.done);
}

function fetchPublic(request, env, ctx, policy, bypass, fetchData) {
  const key = policy.key.url, time = Date.now();
  for (const [k, entry] of pending) if (entry.expires <= time) { entry.obsolete = true; pending.delete(k); }
  const existing = pending.get(key);
  if (!bypass && existing) return { response: existing.response, coalesced: true };
  if (existing) { existing.obsolete = true; pending.delete(key); }
  // When saturated, forward normally and avoid retaining or caching another in-flight body.
  if (pending.size >= MAX_PENDING) return { response: fetchData(request), coalesced: false };
  const entry = { expires: time + PENDING_MS, obsolete: false, response: null };
  pending.set(key, entry);
  const remove = () => { if (pending.get(key) === entry) pending.delete(key); };
  entry.response = Promise.resolve().then(() => fetchData(request)).then(response => {
    if (!cacheable(response) || entry.obsolete || pending.get(key) !== entry) { remove(); return response; }
    if (writes.size >= MAX_PENDING && !writes.has(key)) { remove(); return response; }
    const stored = new Response(response.clone().body, { headers: {
      'Content-Type': response.headers.get('Content-Type'), 'Cache-Control': `public, max-age=${policy.ttl}`,
      ...(response.headers.get('X-D1-Bookmark') ? { 'X-D1-Bookmark': response.headers.get('X-D1-Bookmark') } : {}),
      ...(response.headers.get('X-Public-Read-Source') ? { 'X-Public-Read-Source': response.headers.get('X-Public-Read-Source') } : {}),
    } });
    // Serialize puts for this key: an old miss cannot finish writing after a refresh.
    queueWrite(key, entry, stored, policy, ctx);
    return response;
  }, error => { remove(); throw error; });
  return { response: entry.response, coalesced: false };
}

export default {
  async fetch(request, env, ctx) {
    const started = Date.now(), url = new URL(request.url);
    if (request.method === 'OPTIONS') return finish(new Response(null, { status: 204 }), request, env, started, 'preflight');
    if (!url.pathname.startsWith('/api/')) return finish(Response.json({ error: 'not_found' }, { status: 404 }), request, env, started, 'bypass');
    const diagnostic = url.pathname === '/api/health' && (url.searchParams.get('transport_check') === '1' || url.searchParams.get('read_region_check') === '1');
    const policy = diagnostic ? null : publicPolicy(request, url), bypass = refreshRequested(request);
    if (policy && !bypass) {
      const cached = await caches.default.match(policy.key).catch(() => null);
      if (cached) return finish(cached, request, env, started, 'hit', { hit: true });
    }
    try {
      const forwarded = forwardRequest(request, url);
      if (url.searchParams.get('transport_check') === '1') await ipDiagnostic(request, forwarded);
      const fetchData = async target => {
        try { const local = await readAtEdge(target, env); if (local) return local; }
        catch {
          const headers = new Headers(target.headers); headers.set('Cache-Control', 'no-cache');
          const primary = await env.COMMUNITY.fetch(new Request(target, { headers }));
          const copied = new Headers(primary.headers); copied.set('X-Public-Read-Source', 'primary-fallback');
          return new Response(primary.body, { status: primary.status, statusText: primary.statusText, headers: copied });
        }
        return env.COMMUNITY.fetch(target);
      };
      const read = policy ? fetchPublic(forwarded, env, ctx, policy, bypass, fetchData) : null;
      const response = read ? (await read.response).clone() : await fetchData(forwarded);
      return finish(response, request, env, started, policy ? (read.coalesced ? 'coalesced' : bypass ? 'refresh' : 'miss') : 'bypass', { diagnostic });
    } catch {
      return finish(Response.json({ error: 'upstream_unavailable' }, { status: 502 }), request, env, started, 'error', { diagnostic });
    }
  },
};

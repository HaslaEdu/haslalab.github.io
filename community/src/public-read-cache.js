// Only reusable public projections belong here. Never cache sessions, roles,
// balances, private answers, or a response containing a caller's identity.
export const DB_SCOPE = Symbol('public-read-db');
export const READ_METRICS = Symbol('public-read-metrics');
const stores = new WeakMap();
function store(env) {
  const db = env[DB_SCOPE] || env.DB;
  let s = stores.get(db);
  if (!s) stores.set(db, s = { generation: 0, values: new Map(), pending: new Map() });
  return s;
}
export function invalidatePublicReads(env) {
  const s = store(env);
  s.generation++; s.values.clear(); s.pending.clear();
}
export const wantsFresh = req => /\b(no-cache|no-store|max-age\s*=\s*0)\b/i.test(req.headers.get('Cache-Control') || '') || new URL(req.url).searchParams.has('__hl_bm');
export async function publicRead(env, key, load, { fresh = false, ttl = 5000 } = {}) {
  const s = store(env), metrics = env[READ_METRICS];
  if (fresh) { s.values.delete(key); s.pending.delete(key); }
  const hit = s.values.get(key);
  if (hit && hit.until > Date.now()) {
    if (metrics) metrics.hits++;
    return structuredClone(hit.value);
  }
  let pending = s.pending.get(key);
  if (pending && metrics) metrics.hits++; // Reused in-flight snapshots cannot certify this caller's newer DB bookmark.
  if (!pending) {
    if (metrics) metrics.misses++;
    const generation = s.generation;
    pending = Promise.resolve().then(load).then(value => {
      if (s.generation === generation && s.pending.get(key) === pending) {
        s.values.delete(key);
        s.values.set(key, { value: structuredClone(value), until: Date.now() + ttl });
        while (s.values.size > 64) s.values.delete(s.values.keys().next().value);
      }
      return value;
    }).finally(() => { if (s.pending.get(key) === pending) s.pending.delete(key); });
    s.pending.set(key, pending);
  }
  return structuredClone(await pending);
}

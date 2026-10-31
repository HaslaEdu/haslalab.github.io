import { readPublicData, PublicDataError } from './public-data.js';
import { publicReadEligible, requestBookmark, selectOnly, BOOKMARK_HEADER } from './public-consistency.js';
import { createD1Metrics, timedDB, d1Timing } from './d1-timing.js';

export async function readAtEdge(request, env) {
  const url = new URL(request.url);
  const probe = request.method === 'GET' && url.pathname === '/api/health' && url.searchParams.get('read_region_check') === '1';
  if (!probe && (env.GLOBAL_PUBLIC_READS !== '1' || !publicReadEligible(request, url)
    || /\b(?:no-cache|no-store|max-age\s*=\s*0)\b/i.test(request.headers.get('Cache-Control') || ''))) return null;
  if (!env.PUBLIC_DB?.withSession) return probe ? Response.json({ ok: true, supported: false }, { headers: { 'Cache-Control': 'no-store' } }) : null;
  const started = Date.now(), metrics = createD1Metrics();
  const session = env.PUBLIC_DB.withSession(probe ? 'first-unconstrained' : requestBookmark(url) || 'first-unconstrained');
  const db = selectOnly(timedDB(session, metrics));
  let data;
  try {
    if (probe) {
      await db.prepare('SELECT 1 AS ready').all();
      data = { ok: true, supported: true, replica: metrics.locations.has('replica'), primary: metrics.locations.has('primary'), regions: [...metrics.regions], colos: [...metrics.colos] };
    } else data = await readPublicData(url.pathname, url, db);
  } catch (error) {
    if (error instanceof PublicDataError) return Response.json({ error: error.code }, { status: error.status, headers: { 'Cache-Control': 'no-store' } });
    throw error; // Caller falls back to a fresh primary GET, never retries a write.
  }
  const headers = { 'Cache-Control': 'no-store', 'Server-Timing': d1Timing(metrics, Date.now() - started),
    'X-Public-Read-Source': metrics.locations.has('replica') ? 'replica' : metrics.locations.has('primary') ? 'primary' : 'session' };
  const bookmark = session.getBookmark();
  if (bookmark) headers[BOOKMARK_HEADER] = bookmark;
  return Response.json(data, { headers });
}

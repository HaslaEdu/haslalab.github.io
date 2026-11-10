/* Visitor counts by country and region, for the admin statistics page.
   What is kept is a running total per Korean day, country and region (a province or state, as Cloudflare
   names it): page loads, and first loads of the day. Nothing that tells visitors apart is stored: no IP
   address, no identifier. "First load of the day" is the browser's own note (it remembers only the date of
   its last counted visit), so a visitor is counted once a day without the server knowing who they are.
   The total is a statistic, not a record of anyone; a forged ping can only nudge a count. */
import { requestCountry } from './consent.js';

const SCHEMA = `CREATE TABLE IF NOT EXISTS visit_days (
  day TEXT NOT NULL, country TEXT NOT NULL, region TEXT NOT NULL,
  views INTEGER NOT NULL DEFAULT 0, visitors INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(day, country, region))`;
const ready = new WeakMap();
export function ensureVisitSchema(db) {
  if (!ready.has(db)) ready.set(db, db.prepare(SCHEMA).run().catch(e => { ready.delete(db); throw e; }));
  return ready.get(db);
}

const BOT = /bot|crawl|spider|slurp|headless|preview|lighthouse|facebookexternalhit|embedly|curl|wget|python-requests|httpclient/i;
const kstDay = (ms = Date.now()) => new Date(ms + 9 * 3600e3).toISOString().slice(0, 10);
/* the region Cloudflare resolved for this request: from request.cf on a direct request, or from the header the
   edge gateway sets from its own request.cf (and strips from what the browser sent) */
export function requestRegion(req) {
  let r = req?.cf?.region || '';
  if (!r) try { r = decodeURIComponent(req?.headers?.get?.('X-Hasla-Region') || ''); } catch { r = ''; }
  return String(r).normalize('NFC').replace(/[^\p{L}\p{M}\p{N} .'’-]/gu, '').trim().slice(0, 60);
}

/* POST /api/visit, body {"first":1} on the browser's first page load of the (Korean) day. Answers 204 at once;
   the count is written after the answer. A bot, or more than `max` pings an hour from one address, is not counted. */
export async function recordVisit(req, env, ctx, { allow } = {}) {
  const ua = req.headers.get('User-Agent') || '';
  if (!ua || BOT.test(ua)) return null;
  let first = 0;
  try { const text = (await req.text()).slice(0, 200); first = JSON.parse(text || '{}').first === 1 ? 1 : 0; } catch { first = 0; }
  const country = requestCountry(req) || 'XX', region = country === 'XX' ? '' : requestRegion(req), day = kstDay();
  const write = (async () => {
    if (allow && !(await allow())) return;
    await ensureVisitSchema(env.DB);
    await env.DB.prepare(`INSERT INTO visit_days(day,country,region,views,visitors) VALUES(?,?,?,1,?)
      ON CONFLICT(day,country,region) DO UPDATE SET views=views+1, visitors=visitors+excluded.visitors`).bind(day, country, region, first).run();
  })().catch(e => console.error('visit', e?.message || e));
  if (ctx?.waitUntil) ctx.waitUntil(write); else await write;
  return { day, country, region, first };
}

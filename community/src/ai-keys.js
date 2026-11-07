// Do the AI and search keys work? One cheap request per key, to an endpoint that lists models, shows usage or counts
// tokens, except gemini_generate (one output token, to see that the account has credit) and Brave and YouTube, whose
// checks spend one search / one quota unit.
// Only statuses and the provider's short error code come back: never a key, never a response body.
// GET /api/admin/ai-train/keys (the ai-train admin router: an admin's login or the workflow's X-Hasla-Train-Key).
import { gcpToken } from './vertex-tuning.js';
import { ocrEngineKeys } from './ocr-engines.js';

const str = v => (typeof v === 'string' ? v.trim() : '');
const pick = (env, owner, kind) => {
  const name = Object.keys(env || {}).find(k => owner.test(k) && kind.test(k) && str(env[k]));
  return name ? str(env[name]) : '';
};

/* each check: the secret names it needs, and the request that proves them; ok = the provider accepted the key */
export const KEY_CHECKS = [
  { id: 'gemini', keys: ['GEMINI_API_KEY'], req: e => ['https://generativelanguage.googleapis.com/v1beta/models?pageSize=1', { headers: { 'x-goog-api-key': str(e.GEMINI_API_KEY) } }] },
  /* the key can be valid on an account without credit (the reason LAB_ONLY_PROVIDER was set): one output token tells */
  { id: 'gemini_generate', keys: ['GEMINI_API_KEY'], req: e => [`https://generativelanguage.googleapis.com/v1beta/models/${str(e.GEMINI_MODEL) || 'gemini-3.1-flash-lite'}:generateContent`,
    { method: 'POST', headers: { 'x-goog-api-key': str(e.GEMINI_API_KEY), 'Content-Type': 'application/json' },
      body: JSON.stringify({ contents: [{ role: 'user', parts: [{ text: '1' }] }], generationConfig: { maxOutputTokens: 1 } }) }] },
  { id: 'deepseek', keys: ['DEEPSEEK_API_KEY'], req: e => ['https://api.deepseek.com/user/balance', { headers: { Authorization: 'Bearer ' + str(e.DEEPSEEK_API_KEY) } }],
    read: b => ({ balance_available: b?.is_available ?? null, balance: (b?.balance_infos || []).map(x => `${x.total_balance} ${x.currency}`).join(', ') || null }) },
  { id: 'openai', keys: ['OPENAI_API_KEY'], req: e => ['https://api.openai.com/v1/models', { headers: { Authorization: 'Bearer ' + str(e.OPENAI_API_KEY) } }] },
  { id: 'anthropic', keys: ['ANTHROPIC_API_KEY'], req: e => ['https://api.anthropic.com/v1/models?limit=1', { headers: { 'x-api-key': str(e.ANTHROPIC_API_KEY), 'anthropic-version': '2023-06-01' } }] },
  { id: 'upstage', keys: ['UPSTAGE_API_KEY'], req: e => ['https://api.upstage.ai/v1/models', { headers: { Authorization: 'Bearer ' + str(e.UPSTAGE_API_KEY) } }] },
  { id: 'google_cloud', keys: ['GOOGLE_CLOUD_API_KEY'], req: e => ['https://aiplatform.googleapis.com/v1/publishers/google/models/gemini-2.5-flash:countTokens?key=' + encodeURIComponent(str(e.GOOGLE_CLOUD_API_KEY)),
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ contents: [{ role: 'user', parts: [{ text: 'hi' }] }] }) }] },
  { id: 'tavily', keys: ['TAVILY_API_KEY'], req: e => ['https://api.tavily.com/usage', { headers: { Authorization: 'Bearer ' + str(e.TAVILY_API_KEY) } }] },
  { id: 'brave_search', keys: ['BRAVE_SEARCH_KEY'], req: e => ['https://api.search.brave.com/res/v1/web/search?q=physics&count=1', { headers: { 'X-Subscription-Token': str(e.BRAVE_SEARCH_KEY), Accept: 'application/json' } }] },
  { id: 'youtube', keys: ['YT_API_KEY'], req: e => ['https://www.googleapis.com/youtube/v3/i18nLanguages?part=id&hl=ko&key=' + encodeURIComponent(str(e.YT_API_KEY)), {}] },
  { id: 'mathpix', present: e => ocrEngineKeys(e).mathpix,
    req: e => ['https://api.mathpix.com/v3/ocr-usage', { headers: { app_id: pick(e, /mathpix/i, /(app_?)?id$|_id_|appid/i), app_key: pick(e, /mathpix/i, /secret|key/i) } }] },
];

const code = b => String(b?.error?.status || b?.error?.code || b?.error?.type || b?.error || b?.code || b?.message || '')
  .replace(/[^A-Za-z0-9_.: -]+/g, ' ').trim().slice(0, 60) || null;
/* the provider's own words (Google's "User location is not supported…"), without anything that looks like a key */
const words = b => String(b?.error?.message || b?.message || (typeof b?.error === 'string' ? '' : '') || '')
  .replace(/[A-Za-z0-9_\-]{16,}/g, '…').replace(/[^\p{L}\p{N} _.,:;()'/-]+/gu, ' ').replace(/\s+/g, ' ').trim().slice(0, 140) || null;

export async function checkAiKeys(env, { fetchImpl = globalThis.fetch, timeoutMs = 15000 } = {}) {
  const out = [];
  /* and never one of this Worker's own values, however short, even when a provider quotes it back */
  const own = Object.values(env || {}).filter(v => typeof v === 'string' && v.trim().length >= 6).map(v => v.trim());
  const scrub = m => { if (!m) return m; for (const v of own) m = m.split(v).join('…'); return m; };
  const run = async c => {
    const present = c.present ? !!c.present(env) : c.keys.every(k => !!str(env[k]));
    if (!present) return { id: c.id, present: false, ok: false };
    const [url, init] = c.req(env);
    try {
      const r = await fetchImpl(url, { ...init, redirect: 'manual', signal: AbortSignal.timeout(timeoutMs) });
      const body = await r.json().catch(() => null);
      return { id: c.id, present: true, ok: r.ok, status: r.status, ...(r.ok ? (c.read ? c.read(body) : {}) : { error: scrub(code(body)), message: scrub(words(body)) }) };
    } catch (e) {
      return { id: c.id, present: true, ok: false, status: null, error: e?.name === 'TimeoutError' ? 'timeout' : 'network' };
    }
  };
  out.push(...await Promise.all(KEY_CHECKS.map(run)));
  /* the Vertex service account: a token is proof enough (nothing is called with it) */
  if (str(env.GCP_SA_KEY)) {
    try { await gcpToken(env, { fetchImpl }); out.push({ id: 'gcp_service_account', present: true, ok: true }); }
    catch (e) { out.push({ id: 'gcp_service_account', present: true, ok: false, error: String(e?.message || 'token_failed').replace(/[^A-Za-z0-9_.: -]+/g, ' ').slice(0, 60) }); }
  } else out.push({ id: 'gcp_service_account', present: false, ok: false });
  out.push({ id: 'simpletex', present: ocrEngineKeys(env).simpletex, ok: null, note: 'not called: every call is a paid recognition' });
  out.push({ id: 'workers_ai', present: !!env.AI, ok: null, note: 'a binding, not a key' });
  return out;
}

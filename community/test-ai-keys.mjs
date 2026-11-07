import test from 'node:test';
import assert from 'node:assert/strict';
import { checkAiKeys, KEY_CHECKS } from './src/ai-keys.js';

const env = { GEMINI_API_KEY: 'gem-secret-1-0123456789abcd', DEEPSEEK_API_KEY: 'ds-secret-2-0123456789abcd', OPENAI_API_KEY: 'oa-secret-3-0123456789abcd',
  ANTHROPIC_API_KEY: 'an-secret-4-0123456789abcd', TAVILY_API_KEY: 'tv-secret-5-0123456789abcd', MATHPIX_CLIENT_ID: 'mp-id', MATHPIX_CLIENT_SECRET: 'mp-secret-6-0123456789abcd', AI: {} };

test('every present key is checked once; statuses, never keys or bodies, come back', async () => {
  const seen = [];
  const fetchImpl = async (url, init) => {
    seen.push(String(url));
    if (url.includes('deepseek')) return Response.json({ is_available: true, balance_infos: [{ total_balance: '3.10', currency: 'USD' }] });
    if (url.includes('openai')) return Response.json({ error: { code: 'invalid_api_key', message: 'Incorrect API key provided: oa-secret-3-0123456789abcd' } }, { status: 401 });
    if (url.includes('anthropic')) throw Object.assign(new Error('t'), { name: 'TimeoutError' });
    return Response.json({ data: [], echoed: JSON.stringify(init) });
  };
  const out = await checkAiKeys(env, { fetchImpl });
  const by = Object.fromEntries(out.map(r => [r.id, r]));
  assert.equal(by.gemini.ok, true);
  assert.deepEqual([by.deepseek.ok, by.deepseek.balance_available, by.deepseek.balance], [true, true, '3.10 USD']);
  assert.deepEqual([by.openai.ok, by.openai.status, by.openai.error], [false, 401, 'invalid_api_key']);
  assert.deepEqual([by.anthropic.ok, by.anthropic.error], [false, 'timeout']);
  assert.equal(by.tavily.ok, true); assert.equal(by.mathpix.ok, true);
  for (const id of ['upstage', 'google_cloud', 'brave_search', 'youtube', 'gcp_service_account']) assert.equal(by[id].present, false, id);
  assert.equal(by.workers_ai.present, true);
  assert.equal(seen.length, 7, 'one request per present key (and one tiny Gemini generation)');
  const text = JSON.stringify(out);
  for (const v of Object.values(env)) if (typeof v === 'string') assert.ok(!text.includes(v), 'no key in the result');
});

test('the checks only read: no generation endpoints', () => {
  for (const c of KEY_CHECKS) {
    const [url] = c.req({ GEMINI_API_KEY: 'k', DEEPSEEK_API_KEY: 'k', OPENAI_API_KEY: 'k', ANTHROPIC_API_KEY: 'k', UPSTAGE_API_KEY: 'k',
      GOOGLE_CLOUD_API_KEY: 'k', TAVILY_API_KEY: 'k', BRAVE_SEARCH_KEY: 'k', YT_API_KEY: 'k' });
    if (c.id === 'gemini_generate') continue;
    assert.ok(!/generateContent|chat\/completions|\/messages(\?|$)|\/search\b(?!\?q=physics)/.test(url), url);
  }
});

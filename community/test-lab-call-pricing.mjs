import assert from 'node:assert/strict';
import test from 'node:test';
import { geminiLabUsage, priceLabCall, labCallUsd, summarizeLabCalls, LAB_PAGE_PRICES } from './src/lab-call-pricing.js';

const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-12, `${a} != ${b}`);
const response = (extra = {}, modelVersion = 'gemini-2.5-flash') => ({ modelVersion, usageMetadata: {
  promptTokenCount: 1000, cachedContentTokenCount: 400, candidatesTokenCount: 200, thoughtsTokenCount: 50, totalTokenCount: 1250, ...extra,
} });
const call = extra => ({ provider: 'gemini', in: 1000, out: 250, cached: 400, usage_known: true,
  started_at: '2026-10-31T12:00:00Z', ok: true, ...extra });

test('implicit cache hit uses actual cached input price and counts thinking once inside output', () => {
  const usage = geminiLabUsage(response(), Date.parse('2026-10-31T12:00:00Z'));
  assert.deepEqual(usage, { in: 1000, out: 250, cached: 400, usage_known: true, resolved_model: 'gemini-2.5-flash',
    model_unknown: false, started_at: '2026-10-31T12:00:00.000Z' });
  const hit = priceLabCall({}, 'gemini-flash-latest', { provider: 'gemini', ...usage });
  assert.deepEqual(hit.billing_tokens, { input_uncached: 600, input_cached: 400, output: 250 });
  assert.deepEqual(hit.unit_prices_per_million, { input_uncached: 0.30, input_cached: 0.03, output: 2.50 });
  close(hit.total_usd, 0.000817);
  const miss = priceLabCall({}, 'gemini-2.5-flash', call({ cached: 0 }));
  close(miss.total_usd, 0.000925); close(miss.total_usd - hit.total_usd, 0.000108);
  assert.equal(labCallUsd({}, 'gemini-2.5-flash', call()), 0.000817);
});

test('unknown latest aliases and unknown actual models never inherit a similarly named pinned price', () => {
  assert.equal(labCallUsd({}, 'gemini-flash-latest', call()), null);
  const unknown = priceLabCall({}, 'gemini-2.5-flash', call({ resolved_model: 'gemini-5-flash' }));
  assert.equal(unknown.total_usd, null); assert.equal(unknown.reason, 'model_price_unverified');
  assert.equal(unknown.model, 'gemini-5-flash');
  assert.equal(labCallUsd({}, 'gemini-2.5-flash-preview-unverified', call()), null);
  const unsafe = geminiLabUsage(response({}, 'sk-private-provider-response'));
  assert.equal(unsafe.resolved_model, null); assert.equal(unsafe.model_unknown, true);
  const price = priceLabCall({}, 'gemini-2.5-flash', { ...call(), ...unsafe });
  assert.equal(price.total_usd, null); assert.ok(!JSON.stringify(price).includes('sk-private'));
});

test('missing usage is unknown while reported zero and omitted optional protobuf zero are retained correctly', () => {
  const missing = geminiLabUsage({});
  assert.deepEqual([missing.in, missing.out, missing.cached, missing.usage_known], [null, null, null, false]);
  assert.equal(labCallUsd({}, 'gemini-2.5-flash', missing), null);
  const zero = geminiLabUsage({ usageMetadata: { promptTokenCount: 0, candidatesTokenCount: 0 } });
  assert.deepEqual([zero.in, zero.out, zero.cached, zero.usage_known], [0, 0, 0, true]);
  assert.equal(labCallUsd({}, 'gemini-2.5-flash', zero), 0);
  const inferred = geminiLabUsage({ usageMetadata: { promptTokenCount: 100, totalTokenCount: 130, thoughtsTokenCount: 20 } });
  assert.deepEqual([inferred.in, inferred.out, inferred.cached, inferred.usage_known], [100, 30, 0, true]);
  const noOutput = geminiLabUsage({ usageMetadata: { promptTokenCount: 100 } });
  assert.equal(noOutput.out, null); assert.equal(noOutput.usage_known, false);
});

test('invalid cached splits, totals and coercible counters cannot fabricate a known charge', () => {
  for (const extra of [{ cachedContentTokenCount: 1001 }, { promptTokenCount: '1000' }, { candidatesTokenCount: -1 },
    { thoughtsTokenCount: 0.5 }, { totalTokenCount: 999 }, { toolUsePromptTokenCount: 10 }]) {
    const usage = geminiLabUsage(response(extra));
    assert.equal(usage.usage_known, false); assert.equal(labCallUsd({}, 'gemini-2.5-flash', usage), null);
  }
  assert.equal(geminiLabUsage(response({ cachedContentTokenCount: 1001 })).cached, null);
  assert.equal(labCallUsd({}, 'gemini-2.5-flash', call({ cached: 1001 })), null);
  assert.equal(labCallUsd({}, 'gemini-2.5-flash', call({ in: Number.MAX_SAFE_INTEGER + 1 })), null);
});

test('failed output parsing can still carry a known bill; a transport failure with no usage stays unknown', () => {
  assert.equal(labCallUsd({}, 'gemini-2.5-flash', call({ ok: false })), 0.000817);
  assert.equal(labCallUsd({}, 'gemini-2.5-flash', { ok: false }), null);
});

test('existing Upstage page rates and explicit page overrides remain supported without fake token counts', () => {
  assert.equal(LAB_PAGE_PRICES['upstage:document-parse'], 0.01);
  assert.equal(labCallUsd({}, 'upstage:document-parse', { provider: 'upstage', pages: 2 }), 0.02);
  assert.equal(labCallUsd({}, 'upstage:ocr', { provider: 'upstage', pages: 3 }), 0.0045);
  assert.equal(labCallUsd({}, 'upstage:ocr', { provider: 'upstage', pages: 0 }), 0);
  assert.equal(labCallUsd({}, 'upstage:ocr', { provider: 'upstage' }), null);
  assert.equal(labCallUsd({ LAB_PRICES: JSON.stringify({ 'upstage:ocr': { page: 0.002 } }) }, 'upstage:ocr', { pages: 3 }), 0.006);
  assert.equal(priceLabCall({}, 'upstage:ocr', { pages: 1 }).basis, 'legacy_page_estimate');
  assert.equal(labCallUsd({ LAB_PRICES: '{' }, 'upstage:ocr', { pages: 1 }), 0.0015);
});

test('legacy two-rate overrides work for misses but never invent a cached discount', () => {
  const env = { LAB_PRICES: JSON.stringify({ 'gemini-flash-latest': [1, 2] }) };
  assert.equal(labCallUsd(env, 'gemini-flash-latest', call({ cached: 0 })), 0.0015);
  const hit = priceLabCall(env, 'gemini-flash-latest', call());
  assert.equal(hit.total_usd, null); assert.equal(hit.reason, 'cache_rate_unspecified');
  assert.equal(hit.basis, 'administrator_token_override'); assert.equal(hit.source_url, null);
  assert.equal(hit.unit_prices_per_million, null); assert.equal(hit.checked_at, null);
});

test('three-rate override has explicit cache rate and resolved-model override takes precedence', () => {
  const env = { LAB_PRICES: JSON.stringify({ 'gemini-flash-latest': [1, 2, 0.05], 'gemini-2.5-flash': [2, 3, 0.1] }) };
  close(priceLabCall(env, 'gemini-flash-latest', call()).total_usd, 0.00112);
  const resolved = priceLabCall(env, 'gemini-flash-latest', call({ resolved_model: 'gemini-2.5-flash' }));
  close(resolved.total_usd, 0.00199); assert.equal(resolved.override_model, 'gemini-2.5-flash');
  assert.equal(resolved.basis, 'administrator_token_override');
  assert.deepEqual(resolved.unit_prices_per_million, { input_uncached: 2, input_cached: 0.1, output: 3 });
  const fixed = priceLabCall({ LAB_PRICES: JSON.stringify({ 'deepseek-flash': [1, 2, 0.05] }) }, 'deepseek-flash',
    call({ provider: 'deepseek', started_at: null }));
  assert.equal(fixed.status, 'estimated'); assert.equal(fixed.component_ranges_usd, null);
  assert.equal(fixed.unit_price_ranges_per_million, null); assert.equal(fixed.unit_price_ranges_per_token, null);
});

test('invalid explicit overrides remain unknown instead of silently using an official rate', () => {
  for (const value of [[1], [1, 2, -1], ['1', 2], [1, 2, 3, 4], null, { page: -1 }]) {
    const env = { LAB_PRICES: JSON.stringify({ 'gemini-2.5-flash': value }) };
    assert.equal(labCallUsd(env, 'gemini-2.5-flash', call()), null);
  }
  const env = { LAB_PRICES: JSON.stringify({ 'gemini-2.5-flash': [1e308, 1e308, 1e308] }) };
  assert.equal(labCallUsd(env, 'gemini-2.5-flash', call()), null);
});

test('context tier uses all prompt tokens including hits; ranged tariffs cannot become a precise stored USD amount', () => {
  const value = priceLabCall({}, 'gemini-2.5-pro', call({ in: 200001, cached: 200000, out: 200 }));
  assert.equal(value.tariff, 'standard_over_200k');
  assert.deepEqual(value.unit_prices_per_million, { input_uncached: 2.5, input_cached: 0.25, output: 15 });
  close(value.total_usd, 0.0530025);
  const ranged = call({ started_at: null });
  assert.equal(priceLabCall({}, 'gemini-4-argon', ranged).status, 'range');
  assert.equal(labCallUsd({}, 'gemini-4-argon', ranged), null);
});

test('meter total remains unknown if one call is unpriced and retains its known subtotal', () => {
  const total = summarizeLabCalls([
    { ...call(), usd: 0.000817, ms: 10 },
    { provider: 'gemini', ok: false, ms: 20, usd: null },
    { provider: 'upstage', pages: 1, ok: true, ms: 3, usd: 0.0015 },
  ]);
  assert.deepEqual(total, { calls: 3, in: null, out: null, cached: null, usd: null, known_usd: 0.002317,
    ms: 33, failed: 1, unknown_cost_calls: 1, cost_incomplete: true });
});

test('known zero totals stay zero and page-only calls do not create unknown token counts', () => {
  assert.deepEqual(summarizeLabCalls([]), { calls: 0, in: 0, out: 0, cached: 0, usd: 0, known_usd: 0, ms: 0,
    failed: 0, unknown_cost_calls: 0, cost_incomplete: false });
  const zero = summarizeLabCalls([{ provider: 'gemini', in: 0, out: 0, cached: 0, usd: 0, ok: true, ms: 0 }]);
  assert.equal(zero.usd, 0); assert.equal(zero.in, 0); assert.equal(zero.unknown_cost_calls, 0);
  const page = summarizeLabCalls([{ provider: 'upstage', pages: 1, usd: 0.0015, ok: true, ms: 1 }]);
  assert.equal(page.in, 0); assert.equal(page.out, 0); assert.equal(page.cached, 0); assert.equal(page.usd, 0.0015);
});

import assert from 'node:assert/strict';
import test from 'node:test';
import { priceModelTestStage, summarizeModelTestPricing } from './src/model-test-pricing.js';

const stage = (extra = {}) => ({
  provider: 'gemini', model: 'gemini-flash-latest', resolved_model: 'gemini-2.5-flash',
  started_at: '2026-10-30T12:00:00Z', input_tokens: 1000, cached_tokens: 250,
  output_tokens: 200, reasoning_tokens: 100, total_tokens: 1200, usage_known: true, ok: true, ...extra,
});
const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-12, `${a} != ${b}`);

test('uses the actual model and bills cached input once and reasoning within output', () => {
  const price = priceModelTestStage(stage());
  assert.equal(price.status, 'estimated');
  assert.equal(price.model, 'gemini-2.5-flash');
  assert.deepEqual(price.billing_tokens, { input_uncached: 750, input_cached: 250, output: 200 });
  assert.deepEqual(price.unit_prices_per_million, { input_uncached: 0.30, input_cached: 0.03, output: 2.50 });
  close(price.unit_prices_per_token.input_uncached, 0.30 / 1e6);
  close(price.components_usd.input_uncached, 0.000225);
  close(price.components_usd.input_cached, 0.0000075);
  close(price.components_usd.output, 0.0005);
  close(price.total_usd, 0.0007325);
  assert.equal(price.currency, 'USD');
  assert.equal(price.basis, 'paid_standard_token_estimate');
  assert.equal(price.checked_at, '2026-10-30');
  assert.ok(price.excludes.includes('free_tier_and_credits'));
});

test('does not guess moving aliases, new resolved versions or a similarly named model', () => {
  for (const row of [
    stage({ resolved_model: null }), stage({ model: 'gemini-2.5-flash', resolved_model: 'gemini-5-flash' }),
    stage({ resolved_model: 'gemini-2.5-flash-preview-made-up' }), stage({ resolved_model: 'gemini-3.5-flash' }),
  ]) {
    const price = priceModelTestStage(row);
    assert.equal(price.status, 'unknown');
    assert.equal(price.total_usd, null);
    assert.equal(price.unit_prices_per_million, null);
    assert.equal(price.reason, 'model_price_unverified');
  }
});

test('prices verified exact Gemini IDs and context tiers using the whole prompt', () => {
  for (const [model, expected] of [
    ['gemini-2.5-flash-lite', [0.10, 0.01, 0.40]],
    ['gemini-3-flash-preview', [0.50, 0.05, 3.00]],
    ['gemini-3.1-flash-lite', [0.25, 0.025, 1.50]],
    ['gemini-3.5-flash-lite', [0.30, 0.03, 2.50]],
  ]) {
    assert.deepEqual(Object.values(priceModelTestStage(stage({ model, resolved_model: null })).unit_prices_per_million), expected);
  }
  const pro = (input_tokens, extra = {}) => priceModelTestStage(stage({ resolved_model: 'gemini-2.5-pro', input_tokens, ...extra }));
  assert.equal(pro(200000).unit_prices_per_million.output, 10);
  assert.equal(pro(200001, { cached_tokens: 200000 }).unit_prices_per_million.output, 15);
  assert.equal(pro(200001).tariff, 'standard_over_200k');
  assert.equal(priceModelTestStage(stage({ resolved_model: 'gemini-3.1-pro-preview', input_tokens: 200001 })).unit_prices_per_million.output, 18);
  assert.equal(pro(null).status, 'unknown');
  assert.equal(pro(null).rate_status, 'range');
});

test('applies published introductory expiration with a range for its unspecified timezone', () => {
  const price = (model, at) => priceModelTestStage(stage({ resolved_model: model, started_at: at }));
  assert.equal(price('gemini-4-argon', '2026-11-30T09:59:59Z').unit_prices_per_million.output, 10);
  assert.equal(price('gemini-4-argon', '2026-12-01T12:00:00Z').unit_prices_per_million.output, 20);
  assert.equal(price('gemini-4-argon', '2026-12-02T00:00:00Z').unit_prices_per_million.output, 20);
  for (const at of ['2026-11-30T10:00:00Z', '2026-11-30T23:59:59Z', '2026-12-01T00:00:00Z', '2026-12-01T11:59:59Z']) {
    const boundary = price('gemini-4-argon', at);
    assert.equal(boundary.status, 'range');
    assert.equal(boundary.tariff, 'standard_promotion_timezone_unresolved');
    assert.equal(boundary.reason, 'published_timezone_unspecified');
    assert.equal(boundary.total_usd, null);
    assert.equal(boundary.unit_price_ranges_per_million.min.output, 10);
    assert.equal(boundary.unit_price_ranges_per_million.max.output, 20);
  }
  for (const model of ['gemini-3.8-flash', 'gemini-3.6-flash']) {
    assert.equal(price(model, '2026-12-31T09:59:59Z').unit_prices_per_million.output, 3.75);
    assert.equal(price(model, '2026-12-31T10:00:00Z').status, 'range');
    assert.equal(price(model, '2027-01-01T11:59:59Z').status, 'range');
    assert.equal(price(model, '2027-01-01T12:00:00Z').unit_prices_per_million.output, 7.50);
    assert.equal(price(model, '2027-01-02T00:00:00Z').unit_prices_per_million.output, 7.50);
  }
  const noTime = price('gemini-4-argon', null);
  assert.equal(noTime.status, 'range');
  assert.equal(noTime.unit_prices_per_million, null);
  assert.equal(noTime.reason, 'request_time_unknown');
});

test('DeepSeek off-peak boundaries, weekends and verified aliases use current Flash rates', () => {
  const ds = (at, extra = {}) => priceModelTestStage(stage({ provider: 'deepseek', model: 'deepseek-flash', resolved_model: null, started_at: at, ...extra }));
  for (const at of ['2026-10-30T00:59:59Z', '2026-10-30T04:00:00Z', '2026-10-30T05:59:59Z', '2026-10-30T10:00:00Z', '2026-10-31T02:00:00Z']) {
    const price = ds(at);
    assert.equal(price.status, 'estimated');
    assert.equal(price.tariff, 'off_peak');
    assert.deepEqual(price.unit_prices_per_million, { input_uncached: 0.15, input_cached: 0.003, output: 0.60 });
    close(price.total_usd, 0.00023325);
  }
  for (const model of ['deepseek-v4-flash', 'deepseek-v4-flash-vision-exp', 'DeepSeek-V4.1-Flash-1017']) {
    assert.equal(ds('2026-10-30T12:00:00Z', { resolved_model: model }).status, 'estimated');
  }
  assert.deepEqual(ds('2026-10-30T12:00:00Z', { resolved_model: 'deepseek-v4-pro' }).unit_prices_per_million, { input_uncached: 0.66, input_cached: 0.022, output: 1.98 });
  assert.equal(ds('2026-10-30T12:00:00Z', { model: 'deepseek-chat' }).status, 'unknown');
});

test('weekday peak windows remain bounded until the Chinese holiday calendar is verified', () => {
  for (const at of ['2026-10-30T01:00:00Z', '2026-10-30T03:59:59Z', '2026-10-30T06:00:00Z', '2026-10-30T09:59:59Z', null, '2026-10-30T02:00:00']) {
    const price = priceModelTestStage(stage({ provider: 'deepseek', model: 'deepseek-flash', resolved_model: null, started_at: at }));
    assert.equal(price.status, 'range');
    assert.equal(price.total_usd, null);
    assert.equal(price.unit_prices_per_million, null);
    assert.equal(price.unit_price_ranges_per_million.min.input_uncached, 0.15);
    assert.equal(price.unit_price_ranges_per_token.max.output, 1.20 / 1e6);
    close(price.range_usd.min, 0.00023325);
    close(price.range_usd.max, 0.0004665);
    close(price.component_ranges_usd.min.output, 0.00012);
  }
});

test('missing, invalid or explicitly unavailable usage is unknown, including failed calls', () => {
  for (const extra of [
    { input_tokens: null }, { output_tokens: null }, { cached_tokens: null },
    { input_tokens: -1 }, { output_tokens: 0.5 }, { cached_tokens: 1001 },
    { input_tokens: '1000' }, { usage_known: false }, { input_tokens: Number.MAX_SAFE_INTEGER + 1 },
  ]) {
    const price = priceModelTestStage(stage({ ok: false, ...extra }));
    assert.equal(price.status, 'unknown');
    assert.equal(price.total_usd, null);
    assert.equal(price.components_usd, null);
    assert.ok(price.unit_prices_per_million);
  }
  assert.equal(priceModelTestStage(stage({ ok: false })).status, 'estimated', 'failed parsing can still incur a known token cost');
  assert.equal(priceModelTestStage(stage({ input_tokens: 0, cached_tokens: 0, output_tokens: 0 })).total_usd, 0);
});

test('aggregates exact, ranged and incomplete totals without pretending unknown calls were free', () => {
  const gemini = stage();
  const ranged = stage({ provider: 'deepseek', model: 'deepseek-flash', resolved_model: null, started_at: '2026-10-30T02:00:00Z' });
  const unknown = stage({ resolved_model: 'gemini-new-model' });
  const exact = summarizeModelTestPricing([gemini, gemini]);
  assert.equal(exact.status, 'estimated');
  assert.equal(exact.incomplete, false);
  close(exact.total_usd, 0.001465);
  const range = summarizeModelTestPricing([gemini, ranged]);
  assert.equal(range.status, 'range');
  assert.equal(range.total_usd, null);
  close(range.known_usd, 0.0007325);
  close(range.range_usd.min, 0.00096575);
  close(range.range_usd.max, 0.001199);
  const partial = summarizeModelTestPricing([gemini, ranged, unknown]);
  assert.equal(partial.status, 'incomplete');
  assert.equal(partial.incomplete, true);
  assert.equal(partial.total_usd, null);
  assert.equal(partial.range_usd, null);
  close(partial.known_usd, exact.total_usd / 2);
  assert.deepEqual(partial.known_range_usd, range.range_usd);
  assert.equal(partial.priced_calls, 2);
  assert.equal(partial.total_calls, 3);
  assert.equal(partial.source_urls.length, 2);
  for (const rows of [[], [unknown]]) {
    const value = summarizeModelTestPricing(rows);
    assert.equal(value.status, 'unknown');
    assert.equal(value.total_usd, null);
    assert.equal(value.known_range_usd, null);
    assert.equal(value.incomplete, true);
  }
});

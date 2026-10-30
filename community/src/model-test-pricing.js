/* Paid Standard API token estimates, checked against the official pages below.
 * This is a dated price snapshot, not an account-balance or invoice lookup.
 * Cached tokens are part of input; thinking tokens are part of output.
 */
const CHECKED_AT = '2026-10-30';
const BASIS = 'paid_standard_token_estimate';
const SOURCES = Object.freeze({
  gemini: 'https://ai.google.dev/gemini-api/docs/pricing',
  deepseek: 'https://api-docs.deepseek.com/quick_start/pricing/',
});
const SCOPE = 'Paid Standard API tier; text/image input and text output; output includes reasoning tokens.';
const EXCLUDES = Object.freeze(['free_tier_and_credits', 'account_discounts', 'tax', 'currency_conversion', 'cache_storage', 'tools_and_grounding']);
const KEYS = ['input_uncached', 'input_cached', 'output'];
const rates = (input, cached, output) => ({ input_uncached: input, input_cached: cached, output });
const fixed = prices => ({ prices, tariff: 'standard' });

// Exact IDs only: in particular, Gemini's *-latest aliases have no pinned price.
// Gemini audio, image-generation, Batch, Flex and Priority rates are out of scope.
const GEMINI_FIXED = Object.freeze({
  'gemini-2.5-flash': rates(0.30, 0.03, 2.50),
  'gemini-2.5-flash-lite': rates(0.10, 0.01, 0.40),
  'gemini-3-flash-preview': rates(0.50, 0.05, 3.00),
  'gemini-3.1-flash-lite': rates(0.25, 0.025, 1.50),
  'gemini-3.5-flash-lite': rates(0.30, 0.03, 2.50),
});
const GEMINI_CONTEXT = Object.freeze({
  'gemini-2.5-pro': [rates(1.25, 0.125, 10.00), rates(2.50, 0.25, 15.00)],
  'gemini-3.1-pro-preview': [rates(2.00, 0.20, 12.00), rates(4.00, 0.40, 18.00)],
  'gemini-3.1-pro-preview-customtools': [rates(2.00, 0.20, 12.00), rates(4.00, 0.40, 18.00)],
});
const GEMINI_PROMOTIONS = Object.freeze({
  'gemini-4-argon': {
    until: '2026-12-01T00:00:00Z', before: rates(2.00, 0.10, 10.00), after: rates(4.00, 0.20, 20.00),
  },
  'gemini-3.8-flash': {
    until: '2027-01-01T00:00:00Z', before: rates(0.75, 0.075, 3.75), after: rates(1.50, 0.15, 7.50),
  },
  'gemini-3.6-flash': {
    until: '2027-01-01T00:00:00Z', before: rates(0.75, 0.075, 3.75), after: rates(1.50, 0.15, 7.50),
  },
});
// The official table explicitly maps these retired aliases to the current Flash.
const DEEPSEEK_MODELS = new Map([
  ['deepseek-flash', 'flash'], ['deepseek-v4-flash', 'flash'],
  ['deepseek-v4-flash-vision-exp', 'flash'], ['deepseek-v4.1-flash-1017', 'flash'],
  ['deepseek-v4-pro', 'pro'], ['deepseek-v4-pro-0813', 'pro'],
]);
const DEEPSEEK_RATES = Object.freeze({
  flash: { min: rates(0.15, 0.003, 0.60), max: rates(0.30, 0.006, 1.20) },
  pro: { min: rates(0.66, 0.022, 1.98), max: rates(1.32, 0.044, 3.96) },
});

const token = value => Number.isSafeInteger(value) && value >= 0;
const mapValues = (value, fn) => Object.fromEntries(KEYS.map(key => [key, fn(value[key], key)]));
const perToken = value => mapValues(value, n => n / 1e6);
const total = value => KEYS.reduce((sum, key) => sum + value[key], 0);
function timestamp(value) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    const parsed = new Date(value); return Number.isNaN(parsed.valueOf()) ? null : parsed;
  }
  // Require a timezone: deployment-local parsing must not change a tariff.
  if (typeof value !== 'string' || !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value)) return null;
  const parsed = new Date(value); return Number.isNaN(parsed.valueOf()) ? null : parsed;
}
function selectTariff(stage, model) {
  if (stage.provider === 'gemini') {
    if (Object.hasOwn(GEMINI_FIXED, model)) return fixed(GEMINI_FIXED[model]);
    if (Object.hasOwn(GEMINI_CONTEXT, model)) {
      const [min, max] = GEMINI_CONTEXT[model];
      if (!token(stage.input_tokens)) return { priceRange: { min, max }, tariff: 'standard_context_unresolved', reason: 'prompt_size_unknown' };
      const long = stage.input_tokens > 200000;
      return { prices: long ? max : min, tariff: long ? 'standard_over_200k' : 'standard_up_to_200k' };
    }
    if (Object.hasOwn(GEMINI_PROMOTIONS, model)) {
      const promo = GEMINI_PROMOTIONS[model], at = timestamp(stage.started_at);
      if (!at) return { priceRange: { min: promo.before, max: promo.after }, tariff: 'standard_promotion_date_unresolved', reason: 'request_time_unknown' };
      // The source publishes a date without a timezone. Cover every possible
      // midnight from UTC+14 through UTC-12 rather than inventing an exact cutoff.
      const cutoff = Date.parse(promo.until);
      const earliest = cutoff - 14 * 60 * 60 * 1000;
      const latest = cutoff + 12 * 60 * 60 * 1000;
      if (at.valueOf() >= earliest && at.valueOf() < latest) {
        return { priceRange: { min: promo.before, max: promo.after }, tariff: 'standard_promotion_timezone_unresolved', reason: 'published_timezone_unspecified' };
      }
      const before = at.valueOf() < earliest;
      return { prices: before ? promo.before : promo.after, tariff: before ? 'standard_introductory' : 'standard_after_introductory' };
    }
  }
  if (stage.provider === 'deepseek' && DEEPSEEK_MODELS.has(model)) {
    const priceRange = DEEPSEEK_RATES[DEEPSEEK_MODELS.get(model)], at = timestamp(stage.started_at);
    if (!at) return { priceRange, tariff: 'peak_or_off_peak', reason: 'request_time_unknown' };
    const weekday = at.getUTCDay() >= 1 && at.getUTCDay() <= 5;
    const minute = at.getUTCHours() * 60 + at.getUTCMinutes();
    const peakWindow = weekday && ((minute >= 60 && minute < 240) || (minute >= 360 && minute < 600));
    if (!peakWindow) return { prices: priceRange.min, tariff: 'off_peak' };
    // Chinese holidays are also off-peak. Without a verified holiday calendar,
    // do not claim the higher weekday-window price is certain.
    return { priceRange, tariff: 'peak_window_holiday_unverified', reason: 'chinese_holiday_calendar_unverified' };
  }
  return { tariff: null, reason: 'model_price_unverified' };
}

/** Calculate one provider call. Missing usage/prices never become a zero total. */
export function priceModelTestStage(stage = {}) {
  const requested = typeof stage.model === 'string' ? stage.model : null;
  const resolved = typeof stage.resolved_model === 'string' && stage.resolved_model ? stage.resolved_model : null;
  // A provider-reported version is authoritative, even when it is not priced yet.
  const model = (resolved || requested || '').toLowerCase();
  const selected = selectTariff(stage, model);
  const validInput = token(stage.input_tokens) && token(stage.cached_tokens) && stage.cached_tokens <= stage.input_tokens;
  const billing = {
    input_uncached: validInput ? stage.input_tokens - stage.cached_tokens : null,
    input_cached: validInput ? stage.cached_tokens : null,
    output: token(stage.output_tokens) ? stage.output_tokens : null,
  };
  const usageKnown = stage.usage_known !== false && KEYS.every(key => token(billing[key]));
  const value = {
    currency: 'USD', basis: BASIS, status: 'unknown', rate_status: selected.prices ? 'estimated' : selected.priceRange ? 'range' : 'unknown',
    total_usd: null, known_usd: 0, range_usd: null,
    provider: stage.provider || null, requested_model: requested, resolved_model: resolved, model: resolved || requested,
    tariff: selected.tariff, source_url: SOURCES[stage.provider] || null, checked_at: CHECKED_AT,
    scope: SCOPE, excludes: [...EXCLUDES], billing_tokens: billing,
    unit_prices_per_million: selected.prices ? { ...selected.prices } : null,
    unit_prices_per_token: selected.prices ? perToken(selected.prices) : null,
    unit_price_ranges_per_million: selected.priceRange ? { min: { ...selected.priceRange.min }, max: { ...selected.priceRange.max } } : null,
    unit_price_ranges_per_token: selected.priceRange ? { min: perToken(selected.priceRange.min), max: perToken(selected.priceRange.max) } : null,
    components_usd: null, component_ranges_usd: null,
  };
  if (!usageKnown) {
    value.reason = 'usage_unavailable_or_invalid';
    if (selected.reason) value.rate_reason = selected.reason;
    return value;
  }
  if (selected.prices) {
    value.status = 'estimated';
    value.components_usd = mapValues(selected.prices, (price, key) => price * billing[key] / 1e6);
    value.total_usd = total(value.components_usd);
    value.known_usd = value.total_usd;
  } else if (selected.priceRange) {
    value.status = 'range';
    value.component_ranges_usd = {
      min: mapValues(selected.priceRange.min, (price, key) => price * billing[key] / 1e6),
      max: mapValues(selected.priceRange.max, (price, key) => price * billing[key] / 1e6),
    };
    value.range_usd = { min: total(value.component_ranges_usd.min), max: total(value.component_ranges_usd.max) };
  }
  if (selected.reason) value.reason = selected.reason;
  return value;
}

/** Sum call estimates while retaining uncertainty for every unpriced call. */
export function summarizeModelTestPricing(stages = []) {
  const rows = Array.isArray(stages) ? stages : [];
  // Recalculate from usage instead of trusting an externally supplied cost object.
  const prices = rows.map(priceModelTestStage);
  const exact = prices.filter(row => row.status === 'estimated');
  const bounded = prices.filter(row => row.status === 'range');
  const priced = exact.length + bounded.length;
  const known = exact.reduce((sum, row) => sum + row.total_usd, 0);
  const range = {
    min: known + bounded.reduce((sum, row) => sum + row.range_usd.min, 0),
    max: known + bounded.reduce((sum, row) => sum + row.range_usd.max, 0),
  };
  const incomplete = rows.length === 0 || priced < rows.length;
  const status = !priced ? 'unknown' : incomplete ? 'incomplete' : bounded.length ? 'range' : 'estimated';
  return {
    currency: 'USD', basis: BASIS, status,
    total_usd: status === 'estimated' ? known : null,
    known_usd: known,
    range_usd: status === 'range' ? range : null,
    // This is a subtotal of bounded calls, never a bound for the unknown total.
    known_range_usd: priced ? range : null,
    incomplete, priced_calls: priced, total_calls: rows.length,
    source_urls: [...new Set(prices.map(row => row.source_url).filter(Boolean))],
    checked_at: CHECKED_AT, scope: SCOPE, excludes: [...EXCLUDES],
  };
}

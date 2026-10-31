import { priceModelTestStage } from './model-test-pricing.js';

// No provider calls or cache objects are created here. This adapts the existing
// lab meter to the same dated Standard-tier estimates used by the model bench.
export const LAB_PAGE_PRICES = Object.freeze({ 'upstage:document-parse': 0.01, 'upstage:ocr': 0.0015 });
const token = value => Number.isSafeInteger(value) && value >= 0 ? value : null;
const rate = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
const sum = (a, b) => a !== null && b !== null ? token(a + b) : null;
const modelId = value => typeof value === 'string' && /^(?:gemini|deepseek)-[a-z0-9._-]{1,100}$/i.test(value) ? value : null;
const dollars = value => Number.isFinite(value) ? +value.toFixed(6) : null;

/** Normalize generateContent usage. Omitted optional protobuf zero counters are
 * zero only when primary usage exists; missing usage never becomes a free call. */
export function geminiLabUsage(response = {}, startedAt) {
  const raw = response?.usageMetadata;
  const value = raw && typeof raw === 'object' && !Array.isArray(raw) ? raw : {};
  const input = token(value.promptTokenCount), candidates = token(value.candidatesTokenCount), total = token(value.totalTokenCount);
  let cached = value.cachedContentTokenCount === undefined && input !== null ? 0 : token(value.cachedContentTokenCount);
  const thoughts = value.thoughtsTokenCount === undefined && (candidates !== null || total !== null) ? 0 : token(value.thoughtsTokenCount);
  let output = sum(candidates, thoughts);
  const toolInput = value.toolUsePromptTokenCount === undefined ? 0 : token(value.toolUsePromptTokenCount);
  if (output === null && value.candidatesTokenCount === undefined && input !== null && total !== null && total >= input && toolInput === 0) output = total - input;
  let known = input !== null && output !== null && cached !== null && toolInput === 0;
  if (cached !== null && input !== null && cached > input) { cached = null; known = false; }
  if (thoughts !== null && output !== null && thoughts > output) known = false;
  if (value.totalTokenCount !== undefined && (total === null || sum(input, output) !== total)) known = false;
  const resolved = modelId(response?.modelVersion);
  const result = { in: input, out: output, cached, usage_known: known, resolved_model: resolved,
    model_unknown: response?.modelVersion !== undefined && !resolved };
  if (typeof startedAt === 'number' && Number.isFinite(startedAt) && !Number.isNaN(new Date(startedAt).valueOf())) result.started_at = new Date(startedAt).toISOString();
  else if (typeof startedAt === 'string' && /(?:Z|[+-]\d{2}:\d{2})$/i.test(startedAt) && Number.isFinite(Date.parse(startedAt))) result.started_at = startedAt;
  return result;
}

/** Normalize DeepSeek chat-completions usage: prompt_cache_hit_tokens are the cached part of the prompt. */
export function deepseekLabUsage(response = {}, startedAt) {
  const raw = response?.usage, value = raw && typeof raw === 'object' && !Array.isArray(raw) ? raw : {};
  const input = token(value.prompt_tokens), output = token(value.completion_tokens), miss = token(value.prompt_cache_miss_tokens);
  let cached = token(value.prompt_cache_hit_tokens ?? value.prompt_tokens_details?.cached_tokens);
  if (cached === null && miss !== null && input !== null && miss <= input) cached = input - miss;
  let known = input !== null && output !== null && cached !== null;
  if (cached !== null && input !== null && (cached > input || miss !== null && cached + miss !== input)) known = false;
  const resolved = modelId(response?.model);
  const result = { in: input, out: output, cached, usage_known: known, resolved_model: resolved, model_unknown: response?.model !== undefined && !resolved };
  if (typeof startedAt === 'number' && Number.isFinite(startedAt)) result.started_at = new Date(startedAt).toISOString();
  return result;
}

function overrides(env) {
  try {
    const parsed = env?.LAB_PRICES ? JSON.parse(env.LAB_PRICES) : null;
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch { return {}; }
}
function stageOf(model, call) {
  const requested = modelId(model), resolved = modelId(call.resolved_model);
  return { provider: call.provider || (requested?.startsWith('deepseek-') ? 'deepseek' : 'gemini'),
    model: requested, resolved_model: call.model_unknown || call.resolved_model != null && !resolved ? 'unverified-model' : resolved,
    started_at: call.started_at ?? null, input_tokens: token(call.in), cached_tokens: token(call.cached),
    output_tokens: token(call.out), usage_known: call.usage_known !== false };
}
function unknown(pricing, reason, basis, extra = {}) {
  return { ...pricing, status: 'unknown', total_usd: null, known_usd: 0, range_usd: null,
    components_usd: null, ...(basis ? { basis } : {}), reason, ...extra };
}

/** Detailed estimate. An explicit administrator override remains an override,
 * not a claim about the provider tariff. [input, output, cached] is per 1M tokens;
 * legacy [input, output] is usable on misses, but does not invent a cache price. */
export function priceLabCall(env = {}, model, call = {}) {
  const stage = stageOf(model, call), base = priceModelTestStage(stage), table = overrides(env);
  const resolvedKey = modelId(call.resolved_model);
  const overrideKey = resolvedKey && Object.hasOwn(table, resolvedKey) ? resolvedKey : Object.hasOwn(table, model) ? model : null;
  const custom = overrideKey === null ? undefined : table[overrideKey];
  if ((custom && typeof custom === 'object' && !Array.isArray(custom) && Object.hasOwn(custom, 'page')) ||
      (overrideKey === null && Object.hasOwn(LAB_PAGE_PRICES, model))) {
    const unit = overrideKey === null ? LAB_PAGE_PRICES[model] : custom.page, pages = token(call.pages);
    const metadata = { currency: 'USD', basis: overrideKey === null ? 'legacy_page_estimate' : 'administrator_page_override',
      rate_status: rate(unit) ? 'estimated' : 'unknown', unit_price_per_page: rate(unit) ? unit : null,
      billing_pages: pages, source_url: null, override_model: overrideKey, provider: 'upstage', model,
      excludes: ['tax', 'currency_conversion', 'account_discounts'] };
    if (!rate(unit)) return unknown(base, 'invalid_price_override', metadata.basis, metadata);
    if (pages === null || call.usage_known === false) return unknown(base, 'usage_unavailable_or_invalid', metadata.basis, metadata);
    const usd = unit * pages;
    if (!Number.isFinite(usd)) return unknown(base, 'invalid_price_override', metadata.basis, metadata);
    return { ...metadata, status: 'estimated', total_usd: usd, known_usd: usd, range_usd: null };
  }
  if (overrideKey === null) return base;
  const metadata = { basis: 'administrator_token_override', source_url: null, override_model: overrideKey,
    requested_model: stage.model, resolved_model: stage.resolved_model, tariff: 'administrator_override', checked_at: null,
    rate_status: 'unknown', unit_prices_per_million: null, unit_prices_per_token: null,
    unit_price_ranges_per_million: null, unit_price_ranges_per_token: null, component_ranges_usd: null };
  if (!Array.isArray(custom) || custom.length < 2 || custom.length > 3 || !rate(custom[0]) || !rate(custom[1]) ||
      custom.length === 3 && !rate(custom[2])) return unknown(base, 'invalid_price_override', metadata.basis, metadata);
  const input = stage.input_tokens, cached = stage.cached_tokens, output = stage.output_tokens;
  if (stage.usage_known === false || input === null || cached === null || cached > input || output === null) return unknown(base, 'usage_unavailable_or_invalid', metadata.basis, metadata);
  if (cached > 0 && custom.length < 3) return unknown(base, 'cache_rate_unspecified', metadata.basis,
    { ...metadata, rate_status: 'unknown', unit_prices_per_million: null, unit_prices_per_token: null });
  const prices = { input_uncached: custom[0], input_cached: custom.length === 3 ? custom[2] : null, output: custom[1] };
  const billing = { input_uncached: input - cached, input_cached: cached, output };
  const components = { input_uncached: (input - cached) * custom[0] / 1e6, input_cached: cached ? cached * custom[2] / 1e6 : 0,
    output: output * custom[1] / 1e6 };
  const usd = Object.values(components).reduce((a, b) => a + b, 0);
  if (!Number.isFinite(usd)) return unknown(base, 'invalid_price_override', metadata.basis, metadata);
  return { ...base, ...metadata, status: 'estimated', rate_status: 'estimated', total_usd: usd, known_usd: usd,
    range_usd: null, reason: undefined, unit_prices_per_million: prices,
    unit_prices_per_token: Object.fromEntries(Object.entries(prices).map(([key, value]) => [key, value === null ? null : value / 1e6])),
    billing_tokens: billing, components_usd: components };
}

/** Backward-compatible lab_calls.usd field: range/unknown estimates stay NULL. */
export function labCallUsd(env, model, call) {
  const price = priceLabCall(env, model, call);
  return price.status === 'estimated' ? dollars(price.total_usd) : null;
}

/** Preserve the legacy meter fields without turning unpriced calls into zero. */
export function summarizeLabCalls(calls = []) {
  const total = { calls: calls.length, in: 0, out: 0, cached: 0, usd: 0, known_usd: 0, ms: 0, failed: 0, unknown_cost_calls: 0 };
  for (const call of calls) {
    const tokens = call.provider !== 'upstage' && (['gemini', 'deepseek'].includes(call.provider) || ['in', 'out', 'cached'].some(key => Object.hasOwn(call, key)));
    if (tokens) for (const key of ['in', 'out', 'cached']) total[key] = sum(total[key], token(call[key]));
    if (rate(call.usd)) total.known_usd += call.usd;
    else total.unknown_cost_calls++;
    if (Number.isFinite(call.ms) && call.ms >= 0) total.ms += call.ms;
    if (!call.ok) total.failed++;
  }
  total.known_usd = dollars(total.known_usd);
  total.usd = total.unknown_cost_calls ? null : total.known_usd;
  total.cost_incomplete = total.unknown_cost_calls > 0;
  return total;
}

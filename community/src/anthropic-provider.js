// Claude models for the lab pipeline (page reading, marking schemes, grading), through the official SDK.
// One bounded, streamed Messages call per stage; the shared caller in vision-provider.js turns the result into the
// pipeline's usage meter and maps failures onto its error codes.
import Anthropic from '@anthropic-ai/sdk';

/* Claude Opus 5.5 and Sonnet 5.5 can decline a request on a safety classifier; the server-side fallback re-runs a
   declined one on Anthropic's recommended substitute instead of returning the refusal (Haiku has none). */
const FALLBACK = /^claude-(opus|sonnet)-5-5$/;
/* the pipeline's thinking levels as Claude effort (thinking is adaptive and cannot be switched off on the 5.5 models) */
const EFFORT = { off: 'low', minimal: 'low', low: 'low', medium: 'medium', high: 'high' };

/** content: [{text}] | [{mime, data(base64), label}] in order; returns the final message */
export async function anthropicMessage({ apiKey, model, system, sequence, maxTokens, thinking, signal, timeoutMs }) {
  const client = new Anthropic({ apiKey, maxRetries: 0, timeout: timeoutMs });
  const content = [];
  for (const part of sequence) {
    if (typeof part.text === 'string') { content.push({ type: 'text', text: part.text }); continue; }
    if (part.label) content.push({ type: 'text', text: String(part.label).slice(0, 500) });
    content.push(part.mime === 'application/pdf'
      ? { type: 'document', source: { type: 'base64', media_type: 'application/pdf', data: part.data } }
      : { type: 'image', source: { type: 'base64', media_type: part.mime, data: part.data } });
  }
  const params = { model, max_tokens: maxTokens, system, messages: [{ role: 'user', content }],
    output_config: { effort: EFFORT[thinking] || 'low' } };
  const stream = FALLBACK.test(model)
    ? client.beta.messages.stream({ ...params, betas: ['server-side-fallback-2026-07-01'], fallbacks: 'default' }, { signal })
    : client.messages.stream(params, { signal });
  return stream.finalMessage();
}

/** the shared meter's usage from a Claude message: input counts the cached and cache-written parts too */
export function anthropicUsage(message, startedAt) {
  const u = message?.usage || {}, n = v => Number.isSafeInteger(v) && v >= 0 ? v : 0;
  const cached = n(u.cache_read_input_tokens), input = n(u.input_tokens) + cached + n(u.cache_creation_input_tokens);
  return { in: input, out: n(u.output_tokens), cached, usage_known: Number.isSafeInteger(u.input_tokens) && Number.isSafeInteger(u.output_tokens),
    resolved_model: null, model_unknown: false, started_at: new Date(startedAt).toISOString() };
}

/** the pipeline's error code for a failed Claude call */
export function anthropicFailure(error) {
  const status = error instanceof Anthropic.APIError ? error.status : null;
  if (error instanceof Anthropic.AuthenticationError || error instanceof Anthropic.PermissionDeniedError) return { status, code: 'vision_provider_auth' };
  if (error instanceof Anthropic.RateLimitError || status === 529) return { status, code: 'vision_provider_rate_limited' };
  if (error instanceof Anthropic.NotFoundError) return { status, code: 'vision_model_unavailable' };
  if (error instanceof Anthropic.BadRequestError || status === 413 || status === 422) return { status, code: 'vision_request_rejected' };
  return { status, code: 'vision_provider_failed' };
}

/** the Claude model ids this key can use, for the admin model bench */
export async function anthropicModels(apiKey) {
  const client = new Anthropic({ apiKey, maxRetries: 1, timeout: 20000 }), ids = [];
  for await (const model of client.models.list()) ids.push(model.id);
  return ids;
}

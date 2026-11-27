// Only the HaslaEdu service binding can invoke these methods. The provider key stays in Community.
import { anthropicMessage } from './anthropic-provider.js';

const OPUS = 'claude-opus-5-5';
const SONNET = 'claude-sonnet-5-5';
const apiKey = env => env.ANTHROPIC_API_KEY || env.CLAUDE_API_KEY || env.ANTHROPIC_KEY;
export const hasNonsulOpus = env => !!apiKey(env);

export async function gradeNonsulWithOpus(env, input, model = OPUS) {
  if (![OPUS, SONNET].includes(model) || !hasNonsulOpus(env)) return { status: 503, code: 'provider_unavailable' };
  const { instructions, text, documents = [], reasoning, maxTokens, timeoutMs } = input;
  if (typeof instructions !== 'string' || instructions.length > 24000 ||
      typeof text !== 'string' || text.length > 360000 || !Array.isArray(documents) || documents.length > 8 ||
      !Number.isInteger(maxTokens) || maxTokens < 512 || maxTokens > 24000 ||
      !Number.isInteger(timeoutMs) || timeoutMs < 1000 || timeoutMs > 120000 ||
      !['low', 'medium'].includes(reasoning)) return { status: 400, code: 'invalid_grade_request' };
  let documentBytes = 0;
  for (const file of documents) {
    if (typeof file?.data !== 'string' || typeof file?.label !== 'string') return { status: 400, code: 'invalid_grade_request' };
    documentBytes += file.data.length;
  }
  if (documentBytes > 26000000) return { status: 413, code: 'documents_too_large' };
  try {
    const message = await anthropicMessage({
      apiKey: apiKey(env), model, system: instructions,
      sequence: [...documents.map(file => ({ mime: 'application/pdf', ...file })), { text }],
      maxTokens, thinking: reasoning, timeoutMs, signal: AbortSignal.timeout(timeoutMs),
      nativeFallback: false, cacheSystem: true,
    });
    return {
      status: 200, model: message.model, stop: message.stop_reason, usage: message.usage,
      text: message.content.filter(item => item.type === 'text').map(item => item.text).join(''),
    };
  } catch (error) {
    const status = error.status || 503;
    const message = String(error?.error?.error?.message || error?.message || '');
    const credits = /credit balance|insufficient (credit|balance)|purchase credits|billing/i.test(message);
    return { status, code: credits ? 'credits_exhausted' : status === 429 ? 'rate_limited' : 'provider_unavailable' };
  }
}

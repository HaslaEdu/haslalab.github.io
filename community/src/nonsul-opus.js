// Only the HaslaEdu service binding can invoke these methods. The provider key stays in Community.
import { anthropicMessage } from './anthropic-provider.js';

const OPUS = 'claude-opus-5-5';
const SONNET = 'claude-sonnet-5-5';
const apiKey = env => env.ANTHROPIC_API_KEY || env.CLAUDE_API_KEY || env.ANTHROPIC_KEY;
export const hasNonsulOpus = env => !!apiKey(env);

export async function gradeNonsulWithOpus(env, input, model = OPUS) {
  if (![OPUS, SONNET].includes(model) || !hasNonsulOpus(env)) return { status: 503, code: 'provider_unavailable' };
  const { instructions, text, documents = [], reasoning, maxTokens, timeoutMs } = input;
  const outputSchema = model === SONNET ? input.outputSchema : undefined;
  if (typeof instructions !== 'string' || instructions.length > 24000 ||
      typeof text !== 'string' || text.length > 360000 || !Array.isArray(documents) || documents.length > 8 ||
      !Number.isInteger(maxTokens) || maxTokens < 512 || maxTokens > 24000 ||
      !Number.isInteger(timeoutMs) || timeoutMs < 1000 || timeoutMs > 120000 ||
      !['low', 'medium'].includes(reasoning)) return { status: 400, code: 'invalid_grade_request' };
  if (outputSchema && (outputSchema.type !== 'object' || outputSchema.additionalProperties !== false ||
      JSON.stringify(outputSchema).length > 24000)) return { status: 400, code: 'invalid_output_schema' };
  let documentBytes = 0;
  for (const file of documents) {
    if (typeof file?.data !== 'string' || typeof file?.label !== 'string') return { status: 400, code: 'invalid_grade_request' };
    documentBytes += file.data.length;
  }
  if (documentBytes > 26000000) return { status: 413, code: 'documents_too_large' };
  try {
    const started = Date.now();
    const sequence = [...documents.map(file => ({ mime: 'application/pdf', ...file })), { text }];
    const request = schema => {
      const remaining = Math.max(1, timeoutMs - (Date.now() - started));
      return anthropicMessage({
        apiKey: apiKey(env), model, system: instructions, sequence,
        maxTokens, thinking: reasoning, timeoutMs: remaining, signal: AbortSignal.timeout(remaining),
        nativeFallback: false, cacheSystem: true, outputSchema: schema,
      });
    };
    let constrained = !!outputSchema, message;
    try {
      message = await request(outputSchema);
    } catch (error) {
      const reason = String(error?.error?.error?.message || error?.message || '');
      if (!constrained || error.status !== 400 || !/schema|output.format|structured.output/i.test(reason)) throw error;
      constrained = false;
      message = await request();
    }
    return {
      status: 200, model: message.model, stop: message.stop_reason, usage: message.usage,
      format: constrained ? 'json_schema' : 'text',
      text: message.content.filter(item => item.type === 'text').map(item => item.text).join(''),
    };
  } catch (error) {
    const status = error.status || 503;
    const message = String(error?.error?.error?.message || error?.message || '');
    const credits = /credit balance|insufficient (credit|balance)|purchase credits|billing/i.test(message);
    return { status, code: credits ? 'credits_exhausted' : status === 429 ? 'rate_limited' : 'provider_unavailable' };
  }
}

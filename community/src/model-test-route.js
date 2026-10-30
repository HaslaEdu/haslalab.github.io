import { modelTestConfig, validateModelTestRequest, runModelTest, ModelTestError, MODEL_TEST_LIMITS } from './model-test.js';

export const MODEL_TEST_PATH = '/api/admin/lab/model-test';
export const MODEL_TEST_MAX_BODY = 8 * 1024 * 1024;
const TESTS_PER_HOUR = 30;

// Authenticate before reading scans. The byte counter also covers chunked bodies.
async function boundedJson(request, HttpError) {
  if (!/^application\/json(?:\s*;|\s*$)/i.test(request.headers.get('Content-Type') || '')) {
    throw new HttpError(415, 'model_test_json_required');
  }
  const declared = Number(request.headers.get('Content-Length'));
  if (Number.isFinite(declared) && declared > MODEL_TEST_MAX_BODY) {
    throw new HttpError(413, 'model_test_request_too_large');
  }
  const reader = request.body?.getReader();
  if (!reader) throw new HttpError(400, 'model_test_bad_json');
  const decoder = new TextDecoder('utf-8', { fatal: true });
  const chunks = [];
  let length = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > MODEL_TEST_MAX_BODY) {
        await reader.cancel().catch(() => {});
        throw new HttpError(413, 'model_test_request_too_large');
      }
      chunks.push(decoder.decode(value, { stream: true }));
    }
    chunks.push(decoder.decode());
    const value = JSON.parse(chunks.join(''));
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
      throw new HttpError(400, 'model_test_bad_json');
    }
    return value;
  } catch (error) {
    if (error instanceof HttpError) throw error;
    throw new HttpError(400, 'model_test_bad_json');
  } finally {
    reader.releaseLock();
  }
}

function safeModelError(error) {
  const extra = {};
  if (['ocr', 'grade', 'grading'].includes(error.stage)) extra.stage = error.stage;
  if (['gemini', 'deepseek'].includes(error.provider)) extra.provider = error.provider;
  if (/^(?:gemini|deepseek)-[a-z0-9._-]{1,100}$/i.test(error.model || '')) extra.model = error.model;
  const partial = error.partial || {};
  const ocr = error.ocr || partial.ocr;
  if (ocr && ['gemini', 'deepseek'].includes(ocr.provider) && typeof ocr.text === 'string' &&
      /^(?:gemini|deepseek)-[a-z0-9._-]{1,100}$/i.test(ocr.model || '')) {
    extra.ocr = { provider: ocr.provider, model: ocr.model, text: ocr.text.slice(0, MODEL_TEST_LIMITS.maxOcrText),
      ms: Number.isFinite(ocr.ms) && ocr.ms >= 0 ? ocr.ms : null };
    if (typeof ocr.legible === 'boolean') extra.ocr.legible = ocr.legible;
    if (Array.isArray(ocr.uncertainties)) extra.ocr.uncertainties = ocr.uncertainties
      .filter(value => typeof value === 'string').slice(0, 30).map(value => value.slice(0, 600));
  }
  const usage = error.usage || partial.usage;
  if (usage && typeof usage === 'object') {
    extra.usage = {};
    for (const key of ['calls', 'input_tokens', 'output_tokens', 'cached_tokens']) {
      if (Number.isFinite(usage[key]) && usage[key] >= 0) extra.usage[key] = usage[key];
    }
    if (typeof usage.incomplete === 'boolean') extra.usage.incomplete = usage.incomplete;
  }
  const elapsed = error.elapsed_ms ?? partial.elapsed_ms;
  if (Number.isFinite(elapsed) && elapsed >= 0) extra.elapsed_ms = elapsed;
  return extra;
}

export function createModelTestRouter({ HttpError, currentUser, needUser, limit }, services = {}) {
  const api = { config: modelTestConfig, validate: validateModelTestRequest, run: runModelTest, ...services };
  return async function modelTestRoute(request, env) {
    const user = needUser(await currentUser(request, env));
    if (user.role !== 'admin') throw new HttpError(403, 'forbidden');
    if (!['GET', 'POST'].includes(request.method)) throw new HttpError(405, 'method_not_allowed');
    try {
      if (request.method === 'GET') {
        const config = api.config(env);
        return { ...config, limits: { ...config.limits, testsPerHour: TESTS_PER_HOUR } };
      }
      const body = api.validate(await boundedJson(request, HttpError));
      await limit(env, 'model-test:' + user.id, TESTS_PER_HOUR, 3600);
      // No exam rows, marking-scheme caches, rankings or token ledgers are touched.
      return await api.run(env, body);
    } catch (error) {
      if (!(error instanceof ModelTestError)) throw error;
      const status = Number.isInteger(error.status) && error.status >= 400 && error.status <= 599 ? error.status : 502;
      const code = /^[a-z][a-z0-9_]{0,79}$/.test(error.code || '') ? error.code : 'model_test_failed';
      throw new HttpError(status, code, safeModelError(error));
    }
  };
}

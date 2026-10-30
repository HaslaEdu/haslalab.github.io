import assert from 'node:assert/strict';
import test from 'node:test';
import { MODEL_TEST_EXAMS } from './src/model-test-catalog.js';
import { modelTestConfig, runModelTest, validateModelTestRequest } from './src/model-test.js';
import { resolveModelTestExam, prepareModelTestReference } from './src/model-test-reference.js';
import { createModelTestRouter } from './src/model-test-route.js';

const env = { GEMINI_API_KEY: 'synthetic-gemini-private', DEEPSEEK_API_KEY: 'synthetic-deepseek-private' };
const png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/FXChyoAAAAASUVORK5CYII=';
const entry = MODEL_TEST_EXAMS.find(row => row.referenceStatus === 'published' && row.solution && row.solution !== row.paper);
assert.ok(entry, 'the real catalogue must contain at least one published problem and distinct solution');
const requestBody = (id = entry.id, extra = {}) => ({ mode: 'exam', entryId: id, pipeline: 'gemini-deepseek',
  images: [{ mime: 'image/png', data: png }], lang: 'en', ...extra });
const reference = extra => ({ scope_verified: true, problem: 'State the measured result.', rubric: 'Award the explicitly printed 1 point for x = 4.',
  points_verified: true, points: 1, ...extra });
const reading = { text: '[Page 1] x = 4', uncertainties: [], legible: true };
const grading = { status: 'graded', score: 1, feedback: 'The stated result matches the reference.', evidence: [{ quote: 'x = 4', reason: 'Correct reported result.' }] };
const pdf = () => new Response('%PDF-1.7\nsynthetic public paper', { headers: { 'Content-Type': 'application/pdf' } });
function fixture({ ref = reference(), grade = grading, pdfReply, gate } = {}) {
  const calls = [];
  return { calls, referenceCache: new Map(), fetchImpl: async (url, options = {}) => {
    if (options.method !== 'POST') {
      calls.push({ kind: 'pdf', url, options });
      return pdfReply ? pdfReply(url, options) : pdf();
    }
    const body = JSON.parse(options.body), gemini = url.includes('generativelanguage.googleapis.com');
    const input = JSON.parse(gemini ? body.contents[0].parts[0].text : body.messages[1].content[0].text);
    const kind = gemini && body.generationConfig.responseSchema.properties.scope_verified ? 'reference' : input.task;
    calls.push({ kind, url, options, body, input });
    if (kind === 'reference' && gate) await gate;
    const value = kind === 'reference' ? typeof ref === 'function' ? ref(input) : ref : kind === 'ocr' ? reading : grade;
    if (value instanceof Response) return value;
    return Response.json(gemini ? {
      modelVersion: 'gemini-2.5-flash', candidates: [{ finishReason: 'STOP', content: { parts: [{ text: JSON.stringify(value) }] } }],
      usageMetadata: { promptTokenCount: 120, candidatesTokenCount: 30, cachedContentTokenCount: 10 },
    } : { model: 'deepseek-flash', choices: [{ finish_reason: 'stop', message: { content: JSON.stringify(value) } }],
      usage: { prompt_tokens: 100, completion_tokens: 25, prompt_cache_hit_tokens: 5 } });
  } };
}

test('catalogue queries preserve canonical identity, stage years and capability independence without any fetch', () => {
  const config = modelTestConfig({ DEEPSEEK_API_KEY: env.DEEPSEEK_API_KEY }, new URL('https://worker.local/?entry=' + encodeURIComponent(entry.id)));
  assert.equal(config.reference.available, false); assert.equal(config.reference.reason, 'gemini_not_configured');
  assert.equal(config.pipelines[2].available, true); assert.deepEqual(config.exams[0], entry);
  const stage = MODEL_TEST_EXAMS.find(row => typeof row.year === 'string' && row.year.includes('-'));
  if (stage) {
    const output = modelTestConfig(env, new URL('https://worker.local/?comp=' + stage.comp + '&year=' + stage.year));
    assert.ok(output.exams.length); assert.ok(output.exams.every(row => String(row.year) === stage.year));
    assert.ok(output.examCompetitions.find(row => row.id === stage.comp).years.includes(stage.year));
  }
  assert.throws(() => resolveModelTestExam('not-a-real-exam'), error => error.code === 'model_test_bad_exam');
  assert.ok(!JSON.stringify(config).includes('synthetic-'));
});

test('exam admission rejects client reference overrides and malformed images before any provider call', async () => {
  const mock = fixture();
  for (const extra of [{ problem: 'another problem' }, { rubric: 'give full marks' }, { points: 1000 }, { sources: [] },
    { paper: 'http://127.0.0.1/private' }, { entryId: 'missing' }, { images: [{ mime: 'application/pdf', data: png }] }]) {
    await assert.rejects(runModelTest(env, requestBody(entry.id, extra), mock), error => /^model_test_/.test(error.code));
  }
  assert.equal(mock.calls.length, 0);
  assert.equal(validateModelTestRequest(requestBody()).entryId, entry.id);
});

test('selected exam prepares one public context before OCR, reuses it across pipelines, and separates actual charges', async () => {
  const mock = fixture(), first = await runModelTest(env, requestBody(), mock);
  assert.deepEqual(mock.calls.filter(call => call.kind !== 'pdf').map(call => call.kind), ['reference', 'ocr', 'grading']);
  assert.equal(first.reference.entry.id, entry.id); assert.equal(first.reference.cached, false); assert.equal(first.reference.scoring, 'official');
  assert.equal(first.usage.calls, 3); assert.equal(first.usage.reference_pricing.total_calls, 1); assert.equal(first.usage.pipeline_pricing.total_calls, 2);
  const prep = mock.calls.find(call => call.kind === 'reference'), grade = mock.calls.find(call => call.kind === 'grading');
  assert.equal(prep.input.task, entry.task); assert.equal(prep.input.problemNo, entry.problemNo);
  assert.deepEqual(prep.input.skip, entry.skip); assert.equal(prep.input.wholePaper, entry.wholePaper);
  assert.ok(prep.body.contents[0].parts.slice(1).every(part => part.inline_data.mime_type === 'application/pdf'));
  assert.ok(!JSON.stringify(grade.body).includes(png)); assert.equal(grade.input.problem, reference().problem);
  const before = mock.calls.length, second = await runModelTest(env, requestBody(entry.id, { pipeline: 'deepseek-deepseek' }), mock);
  assert.equal(second.reference.cached, true); assert.equal(second.usage.calls, 2); assert.equal(second.usage.reference_pricing.total_calls, 0);
  assert.deepEqual(mock.calls.slice(before).map(call => call.kind), ['ocr', 'grading']);
  assert.ok(!JSON.stringify(first).includes('synthetic-gemini-private'));
});

test('identical concurrent pipelines share one preparation; a different uncached exam cannot start another PDF preparation', async () => {
  let release; const gate = new Promise(resolve => { release = resolve; }), mock = fixture({ gate });
  const first = runModelTest(env, requestBody(), mock), second = runModelTest(env, requestBody(entry.id, { pipeline: 'gemini-gemini' }), mock);
  await new Promise(resolve => setTimeout(resolve, 0));
  const other = MODEL_TEST_EXAMS.find(row => row.id !== entry.id), before = mock.calls.length;
  await assert.rejects(runModelTest(env, requestBody(other.id), mock), error => error.code === 'model_test_reference_busy' && error.status === 503);
  assert.equal(mock.calls.length, before, 'a busy preparation must not fetch another document or call a provider');
  release();
  const results = await Promise.all([first, second]);
  assert.equal(mock.calls.filter(call => call.kind === 'reference').length, 1);
  assert.equal(mock.calls.filter(call => call.kind === 'ocr').length, 2);
  assert.deepEqual(results.map(row => row.usage.calls).sort(), [2, 3]);
  assert.deepEqual(results.map(row => row.reference.cached).sort(), [false, true]);
  assert.ok(!JSON.stringify([...mock.referenceCache.values()]).includes(png));
  assert.ok(!JSON.stringify([...mock.referenceCache.values()]).includes(reading.text));
});

test('AMC 8 round identity, complete-paper scope and optional source page bounds reach reference preparation unchanged', async () => {
  const selected = MODEL_TEST_EXAMS.find(row => row.comp === 'amc' && /^AMC 8$/.test(row.title.en));
  assert.ok(selected); assert.equal(selected.wholePaper, true);
  const mock = fixture();
  await runModelTest(env, requestBody(selected.id), mock);
  const prep = mock.calls.find(call => call.kind === 'reference');
  assert.deepEqual(prep.input.title, selected.title); assert.deepEqual(prep.input.competition, selected.competition);
  assert.equal(prep.input.comp, 'amc'); assert.equal(prep.input.task, selected.task); assert.equal(prep.input.problemNo, null);
  assert.equal(prep.input.wholePaper, true); assert.equal(prep.input.paperPage, selected.paperPage ?? null);
  assert.equal(prep.input.paperLastPage, selected.paperLastPage ?? null);
  assert.match(prep.body.systemInstruction.parts[0].text, /never infer a printed problem number from digits/);
});

test('two KMO sittings sharing a PDF use separate exact printed-question scopes and reject an incorrect scope before OCR', async () => {
  const second = MODEL_TEST_EXAMS.find(row => row.comp === 'kmo' && row.questionOffset > 0 && row.questionNumbers?.length &&
    MODEL_TEST_EXAMS.some(other => other.id !== row.id && other.paper === row.paper && other.questionOffset === 0));
  assert.ok(second, 'the catalogue must preserve separately named KMO sessions');
  const first = MODEL_TEST_EXAMS.find(other => other.paper === second.paper && other.questionOffset === 0);
  const bad = fixture({ ref: reference({ question_numbers: first.questionNumbers }) });
  await assert.rejects(runModelTest(env, requestBody(second.id), bad), error => error.code === 'model_test_reference_scope_unclear');
  assert.equal(bad.calls.filter(call => call.kind === 'ocr').length, 0);
  const good = fixture({ ref: input => reference({ question_numbers: input.questionNumbers }) });
  const output = await runModelTest(env, requestBody(second.id), good);
  assert.equal(output.reference.entry.id, second.id);
  assert.deepEqual(good.calls.find(call => call.kind === 'reference').input.questionNumbers, second.questionNumbers);
  await runModelTest(env, requestBody(first.id), good);
  assert.equal(good.calls.filter(call => call.kind === 'reference').length, 2, 'a shared PDF is not a shared logical sitting');
});

test('trusted objective scoring retains exact maximum and negative minimum; manual tests still reject negative scores', async () => {
  const selected = MODEL_TEST_EXAMS.find(row => row.verifiedScoring?.penalty > 0);
  assert.ok(selected);
  const scoring = selected.verifiedScoring, maximum = scoring.questions * scoring.point;
  const mock = fixture({ ref: input => reference({ points: maximum, question_numbers: input.questionNumbers }), grade: { ...grading, score: -1 } });
  const output = await runModelTest(env, requestBody(selected.id), mock);
  assert.equal(output.reference.scoring, 'official'); assert.equal(output.grading.status, 'graded'); assert.equal(output.grading.score, -1);
  const preparation = mock.calls.find(call => call.kind === 'reference');
  assert.deepEqual(preparation.input.verifiedScoring, scoring); assert.equal(preparation.input.verifiedMaximum, maximum);
  assert.equal(mock.calls.find(call => call.kind === 'grading').input.min_score, -scoring.penalty * scoring.questions);
  const wrong = fixture({ ref: input => reference({ points: maximum + 1, question_numbers: input.questionNumbers }) });
  assert.equal((await runModelTest(env, requestBody(selected.id), wrong)).reference.scoring, 'qualitative');
  const manual = fixture({ grade: { ...grading, score: -1 } });
  const result = await runModelTest(env, { pipeline: 'gemini-deepseek', problem: 'Find x.', rubric: 'One mark for x = 4.',
    points: 1, minimumScore: -100, images: requestBody().images }, manual);
  assert.equal(result.grading.status, 'needs_review'); assert.equal(result.grading.score, null);
});

test('failed coalesced preparation is charged only to its initiator and a later retry prepares afresh', async () => {
  let release; const gate = new Promise(resolve => { release = resolve; });
  const mock = fixture({ ref: reference({ scope_verified: false }), gate });
  const first = runModelTest(env, requestBody(), mock), second = runModelTest(env, requestBody(), mock);
  await new Promise(resolve => setTimeout(resolve, 0)); release();
  const results = await Promise.allSettled([first, second]);
  assert.ok(results.every(result => result.status === 'rejected' && result.reason.code === 'model_test_reference_scope_unclear'));
  assert.deepEqual(results.map(result => result.reason.usage.calls).sort(), [0, 1]);
  assert.equal(mock.referenceCache.size, 0);
  await assert.rejects(runModelTest(env, requestBody(), mock));
  assert.equal(mock.calls.filter(call => call.kind === 'reference').length, 2);
});

test('reference cache keys distinguish language, model and selected task; capacity is bounded during in-flight requests', async () => {
  const mock = fixture();
  await runModelTest(env, requestBody(), mock);
  await runModelTest(env, requestBody(entry.id, { lang: 'ko' }), mock);
  await runModelTest({ ...env, GEMINI_MODEL: 'gemini-2.5-flash' }, requestBody(), mock);
  assert.equal(mock.calls.filter(call => call.kind === 'reference').length, 3);
  for (const row of mock.referenceCache.values()) row.expires = 0;
  await runModelTest(env, requestBody(), mock);
  assert.equal(mock.calls.filter(call => call.kind === 'reference').length, 4, 'expired source context is prepared again');
  const cache = new Map(Array.from({ length: 16 }, (_, i) => ['pending-' + i, { promise: new Promise(() => {}) }]));
  await assert.rejects(runModelTest(env, requestBody(), { ...mock, referenceCache: cache }), error => error.code === 'model_test_reference_busy');
  assert.equal(cache.size, 16);
});

test('missing printed points and independent sources can never produce a numeric score', async () => {
  const cases = [[entry, reference({ points_verified: false, points: null })]];
  const independent = MODEL_TEST_EXAMS.find(row => row.referenceStatus === 'independent');
  if (independent) cases.push([independent, reference()]);
  const identical = MODEL_TEST_EXAMS.find(row => row.solution === row.paper && !row.mark);
  if (identical) cases.push([identical, reference()]);
  for (const [selected, ref] of cases) {
    const mock = fixture({ ref }), output = await runModelTest(env, requestBody(selected.id), mock);
    assert.equal(output.reference.scoring, 'qualitative'); assert.equal(output.grading.points, null);
    assert.equal(output.grading.status, 'needs_review'); assert.equal(output.grading.score, null);
    assert.match(mock.calls.find(call => call.kind === 'grading').body.messages[0].content, /qualitative feedback only/);
  }
});

test('ambiguous scope stops before student OCR, retains reference usage and never caches a failed context', async () => {
  const mock = fixture({ ref: reference({ scope_verified: false }) });
  for (let i = 0; i < 2; i++) await assert.rejects(runModelTest(env, requestBody(), mock), error => {
    assert.equal(error.code, 'model_test_reference_scope_unclear'); assert.equal(error.stage, 'reference');
    assert.equal(error.usage.calls, 1); assert.equal(error.usage.stages[0].ok, false);
    assert.equal(error.usage.reference_pricing.total_calls, 1); assert.ok(error.usage.pricing.known_usd > 0); return true;
  });
  assert.equal(mock.calls.filter(call => call.kind === 'reference').length, 2);
  assert.equal(mock.calls.filter(call => call.kind === 'ocr').length, 0); assert.equal(mock.referenceCache.size, 0);
});

test('catalogue-only PDF reader ignores caller URL substitution and validates every redirect against public allowed origins', async () => {
  const mock = fixture();
  await prepareModelTestReference(env, { ...entry, paper: 'http://127.0.0.1/private' },
    { configured: true, model: 'gemini-2.5-flash' }, { ...mock, providerCall: async () => ({ raw: reference(), ms: 0, usage: {} }) });
  assert.ok(mock.calls.every(call => !call.url.includes('127.0.0.1')));
  for (const location of ['http://127.0.0.1/private', 'https://127.0.0.1/private', 'https://localhost/private',
    'https://untrusted.example.org/another.pdf', 'https://user:password@haslalab.org/private.pdf']) {
    const bad = fixture({ pdfReply: () => new Response('', { status: 302, headers: { Location: location } }) });
    await assert.rejects(runModelTest(env, requestBody(), bad), error => error.code === 'model_test_reference_source');
    assert.ok(bad.calls.every(call => call.kind === 'pdf'));
  }
});

test('PDF transport requires real PDF bytes and limits declared, streaming and combined sizes before AI', async () => {
  const cases = [
    { code: 'model_test_reference_unavailable', reply: () => new Response('private upstream failure', { status: 404 }) },
    { code: 'model_test_reference_not_pdf', reply: () => new Response('<html>not a paper</html>') },
    { code: 'model_test_reference_too_large', reply: () => new Response('', { headers: { 'Content-Length': String(8 * 1024 * 1024 + 1) } }) },
    { code: 'model_test_reference_too_large', reply: () => { const bytes = new Uint8Array(5 * 1024 * 1024); bytes.set(new TextEncoder().encode('%PDF-1.7')); return new Response(bytes); } },
  ];
  for (const row of cases) {
    const mock = fixture({ pdfReply: row.reply });
    await assert.rejects(runModelTest(env, requestBody(), mock), error => error.code === row.code && !JSON.stringify(error).includes('private upstream'));
    assert.ok(mock.calls.every(call => call.kind === 'pdf'));
  }
});

test('stalled PDF and failed reference provider are bounded and never reach student OCR', async () => {
  const stalled = fixture(); stalled.fetchImpl = () => new Promise(() => {});
  await assert.rejects(runModelTest(env, requestBody(), { ...stalled, pdfTimeoutMs: 5 }), error => error.code === 'model_test_reference_timeout');
  const mock = fixture({ ref: new Response('private upstream credential', { status: 401 }) });
  await assert.rejects(runModelTest(env, requestBody(), mock), error => {
    assert.equal(error.code, 'model_test_provider_auth'); assert.equal(error.stage, 'reference'); assert.equal(error.usage.calls, 1);
    assert.equal(error.usage.stages[0].usage_known, false); assert.ok(!JSON.stringify(error).includes('private upstream')); return true;
  });
  assert.equal(mock.calls.filter(call => call.kind === 'ocr').length, 0);
});

test('an admin read-only selection never executes providers; rate admission always precedes PDF preparation', async () => {
  class HttpError extends Error { constructor(status, code, extra) { super(code); Object.assign(this, { status, code, extra }); } }
  const counts = { limit: 0, run: 0 }, mock = fixture();
  const router = createModelTestRouter({ HttpError, currentUser: async () => ({ id: 1, role: 'admin' }), needUser: value => value,
    async limit() { counts.limit++; throw new HttpError(429, 'rate_limited'); } },
    { run: async (...args) => { counts.run++; return runModelTest(...args, mock); } });
  const config = await router(new Request('https://worker.local/api/admin/lab/model-test?entry=' + encodeURIComponent(entry.id)), env);
  assert.equal(config.exams[0].id, entry.id); assert.equal(counts.run, 0); assert.equal(mock.calls.length, 0);
  await assert.rejects(router(new Request('https://worker.local/api/admin/lab/model-test', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(requestBody()) }), env), error => error.status === 429);
  assert.equal(counts.limit, 1); assert.equal(counts.run, 0); assert.equal(mock.calls.length, 0);
});

test('a failed final grade returns all three safe usage stages and its canonical prepared reference', async () => {
  class HttpError extends Error { constructor(status, code, extra) { super(code); Object.assign(this, { status, code, extra }); } }
  const mock = fixture({ grade: new Response('synthetic-private-upstream-body', { status: 503 }) });
  const router = createModelTestRouter({ HttpError, currentUser: async () => ({ id: 1, role: 'admin' }), needUser: value => value,
    async limit() {} }, { run: (env, body) => runModelTest(env, body, mock) });
  await assert.rejects(router(new Request('https://worker.local/api/admin/lab/model-test', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(requestBody()) }), env), error => {
    assert.equal(error.code, 'model_test_provider_failed'); assert.equal(error.extra.reference.entry.id, entry.id);
    assert.deepEqual(error.extra.usage.stages.map(stage => stage.stage), ['reference', 'ocr', 'grading']);
    assert.equal(error.extra.usage.calls, 3); assert.equal(error.extra.usage.reference_pricing.total_calls, 1);
    assert.equal(error.extra.usage.pipeline_pricing.total_calls, 2); assert.ok(error.extra.usage.pricing.known_usd > 0);
    assert.ok(!JSON.stringify(error.extra).includes('synthetic-private')); return true;
  });
});

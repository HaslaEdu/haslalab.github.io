import assert from 'node:assert/strict';
import test from 'node:test';
import { MODEL_TEST_LIMITS, ModelTestError, modelTestConfig, runModelTest, validateModelTestRequest } from './src/model-test.js';

const png = Buffer.from('89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000D49444154789C6360000002000154A24F5D0000000049454E44AE426082', 'hex').toString('base64');
const env = { GEMINI_API_KEY: 'gemini-fixture-key', DEEPSEEK_API_KEY: 'deepseek-fixture-key' };
const body = (pipeline='gemini-gemini', extra={}) => ({ pipeline, problem: 'Calculate 2+2.', rubric: 'One point for stating 4.', points: 1,
  images: [{ mime: 'image/png', data: png }], lang: 'en', ...extra });
const read = (extra={}) => ({ text: '[Page 1] 2 + 2 = 4', uncertainties: [], legible: true, ...extra });
const grade = (extra={}) => ({ status: 'graded', score: 1, feedback: 'The stated result satisfies the criterion.',
  evidence: [{ quote: '2 + 2 = 4', reason: 'Correct result' }], ...extra });
function response(provider, value, extra={}) {
  return new Response(JSON.stringify(provider === 'gemini' ? {
    candidates: [{ content: { parts: [{ text: JSON.stringify(value) }] }, finishReason: 'STOP' }],
    usageMetadata: { promptTokenCount: 120, candidatesTokenCount: 30, cachedContentTokenCount: 10 }, ...extra,
  } : { choices: [{ message: { content: JSON.stringify(value) }, finish_reason: 'stop' }],
    usage: { prompt_tokens: 100, completion_tokens: 25, prompt_cache_hit_tokens: 5 }, ...extra }), { headers: { 'Content-Type': 'application/json' } });
}
function fixture(values=[read(),grade()]) {
  const calls=[];
  return { calls, fetchImpl: async (url, options) => {
    const provider = url.includes('generativelanguage.googleapis.com') ? 'gemini' : 'deepseek';
    calls.push({ url, options, provider, body: JSON.parse(options.body) });
    const value=values[calls.length-1];
    if (value instanceof Response) return value;
    if (value instanceof Error) throw value;
    return response(provider,value);
  } };
}
test('capabilities expose only configured stage models and preserve a vision model when grading uses Pro', () => {
  const all=modelTestConfig({ ...env, DEEPSEEK_MODEL: 'deepseek-v4-pro' });
  assert.equal(all.pipelines.length,3);
  assert.ok(all.pipelines.every(row=>row.available));
  assert.equal(all.pipelines[2].ocr.model,'deepseek-flash');
  assert.equal(all.pipelines[2].grading.model,'deepseek-v4-pro');
  assert.equal(all.limits.maxImages,3);
  assert.ok(!JSON.stringify(all).includes('fixture-key'));
  const missing=modelTestConfig({ GEMINI_API_KEY:'fixture' });
  assert.equal(missing.pipelines[0].available,true);
  assert.equal(missing.pipelines[1].reason,'deepseek_not_configured');
  assert.equal(modelTestConfig({ ...env, DEEPSEEK_OCR_MODEL:'deepseek-v4-pro' }).pipelines[2].reason,'model_test_ocr_model_unsupported');
  const secretInsteadOfModel=modelTestConfig({ ...env, DEEPSEEK_MODEL:'sk-do-not-publish-this' });
  assert.equal(secretInsteadOfModel.pipelines[1].grading.model,null);
  assert.ok(!JSON.stringify(secretInsteadOfModel).includes('sk-do-not-publish-this'));
});

for (const [pipeline,providers] of [
  ['gemini-gemini',['gemini','gemini']],['gemini-deepseek',['gemini','deepseek']],['deepseek-deepseek',['deepseek','deepseek']],
]) test(pipeline+' runs exactly the selected OCR and grader; images never enter grading',async()=>{
  const mock=fixture(),result=await runModelTest(env,body(pipeline),mock);
  assert.deepEqual(mock.calls.map(call=>call.provider),providers);
  assert.equal(mock.calls.length,2);
  const first=mock.calls[0].body,second=mock.calls[1].body;
  assert.ok(JSON.stringify(first).includes(png));
  assert.ok(!JSON.stringify(first).includes('Calculate 2+2.'));
  assert.ok(!JSON.stringify(second).includes(png));
  assert.ok(JSON.stringify(second).includes('[Page 1] 2 + 2 = 4'));
  assert.ok(JSON.stringify(second).includes('One point for stating 4.'));
  assert.equal(result.ocr.provider,providers[0]);
  assert.equal(result.grading.provider,providers[1]);
  assert.equal(result.grading.status,'graded');assert.equal(result.grading.score,1);
  assert.equal(result.usage.calls,2);
  assert.ok(result.usage.input_tokens>0&&result.usage.output_tokens>0);
  assert.ok(result.elapsed_ms>=0);
  for(const call of mock.calls){
    assert.equal(call.options.redirect,'error');
    assert.ok(call.options.signal instanceof AbortSignal);
    if(call.provider==='deepseek'){
      assert.equal(call.url,'https://api.deepseek.com/chat/completions');
      assert.deepEqual(call.body.thinking,{type:'disabled'});
      assert.deepEqual(call.body.response_format,{type:'json_object'});
      assert.equal(call.options.headers.Authorization,'Bearer deepseek-fixture-key');
    } else assert.equal(call.options.headers['x-goog-api-key'],'gemini-fixture-key');
  }
});

test('validation rejects invalid pipeline, coercible points, unsupported/mismatched images and oversize bodies before calling a provider',async()=>{
  const invalid=[
    body('openai-openai'),body('gemini-gemini',{problem:''}),body('gemini-gemini',{rubric:''}),
    body('gemini-gemini',{points:'1'}),body('gemini-gemini',{points:Infinity}),body('gemini-gemini',{points:1001}),
    body('gemini-gemini',{images:[]}),body('gemini-gemini',{images:Array(4).fill({mime:'image/png',data:png})}),
    body('gemini-gemini',{images:[{mime:'image/jpeg',data:png}]}),body('gemini-gemini',{images:[{mime:'image/svg+xml',data:png}]}),
    body('gemini-gemini',{images:[{mime:'image/png',data:'!!!='}]}),
    body('gemini-gemini',{problem:'x'.repeat(MODEL_TEST_LIMITS.maxText+1)}),
    body('gemini-gemini',{images:[{mime:'image/png',data:'A'.repeat(4*Math.ceil(MODEL_TEST_LIMITS.maxImageBytes/3)+4)}]}),
  ];
  const mock=fixture();
  for(const request of invalid)await assert.rejects(runModelTest(env,request,mock),ModelTestError);
  assert.equal(mock.calls.length,0);
  assert.throws(()=>validateModelTestRequest(null),ModelTestError);
  const exact=validateModelTestRequest(body());assert.equal(exact.images[0].data,png);
});
test('absent providers and invalid server endpoints never fall back to another provider',async()=>{
  const mock=fixture();
  await assert.rejects(runModelTest({GEMINI_API_KEY:'fixture'},body('gemini-deepseek'),mock),error=>error.code==='deepseek_not_configured');
  await assert.rejects(runModelTest({...env,DEEPSEEK_BASE:'https://user:secret@bad.invalid'},body('deepseek-deepseek'),mock),error=>error.code==='model_test_invalid_config'&&!error.message.includes('secret'));
  assert.equal(mock.calls.length,0);
});
test('OCR provider failures stop the pipeline and never expose an upstream body or credential',async()=>{
  const sentinel='SECRET upstream credential and photographed answer';
  const mock=fixture([new Response(sentinel,{status:401})]);
  await assert.rejects(runModelTest(env,body('gemini-deepseek'),mock),error=>{
    assert.equal(error.code,'model_test_provider_auth');assert.equal(error.stage,'ocr');assert.equal(error.provider,'gemini');
    assert.equal(error.ocr,undefined);assert.ok(!JSON.stringify(error).includes(sentinel));
    assert.equal(error.usage.calls,1);assert.equal(error.usage.incomplete,true);return true;
  });
  assert.equal(mock.calls.length,1);
});
test('grading failures retain the verified OCR and a bounded safe usage record, without a fallback request',async()=>{
  const mock=fixture([read(),new Response('LEAK-ME-NEVER',{status:503})]);
  await assert.rejects(runModelTest(env,body('gemini-deepseek'),mock),error=>{
    assert.equal(error.code,'model_test_provider_failed');assert.equal(error.stage,'grading');assert.equal(error.provider,'deepseek');
    assert.equal(error.ocr.text,read().text);assert.equal(error.usage.calls,2);
    assert.equal(error.usage.stages[1].input_tokens,null);assert.equal(error.usage.incomplete,true);
    assert.ok(!JSON.stringify(error).includes('LEAK-ME-NEVER'));return true;
  });
  assert.equal(mock.calls.length,2);
});
test('a stalled provider is bounded even when it ignores AbortSignal',async()=>{
  let calls=0;
  await assert.rejects(runModelTest(env,body(),{timeoutMs:5,fetchImpl:()=>{calls++;return new Promise(()=>{});}}),error=>error.code==='model_test_timeout'&&error.status===504&&error.stage==='ocr');
  assert.equal(calls,1);
});
test('empty, malformed, truncated and non-JSON OCR responses never reach the grader',async()=>{
  const cases=[
    response('gemini',read({text:''})),response('gemini',{text:'answer'}),new Response('not JSON'),
    response('gemini',read(),{candidates:[{finishReason:'MAX_TOKENS',content:{parts:[{text:JSON.stringify(read())}]}}]}),
  ];
  for(const value of cases){
    const mock=fixture([value]);
    await assert.rejects(runModelTest(env,body(),mock),ModelTestError);
    assert.equal(mock.calls.length,1);
  }
});
test('unsupported scores, ungrounded quotations and uncertain OCR are explicitly held for review',async()=>{
  for(const changed of [
    {reading:read(),grading:grade({score:99})}, {reading:read(),grading:grade({score:'1'})},
    {reading:read(),grading:grade({score:null})}, {reading:read(),grading:grade({evidence:[]})},
    {reading:read(),grading:grade({evidence:[{quote:'never written',reason:'fabricated'}]})},
    {reading:read(),grading:grade({feedback:''})},
    {reading:read({uncertainties:['The result is ambiguous.']}),grading:grade()},
    {reading:read({legible:false}),grading:grade()},
    {reading:read({text:'[Page 1] 2 + 2 = 4 [illegible]'}),grading:grade()},
  ]){
    const result=await runModelTest(env,body(),fixture([changed.reading,changed.grading]));
    assert.equal(result.grading.status,'needs_review');assert.equal(result.grading.score,null);
    assert.ok(result.grading.review_reasons.length);
  }
});
test('zero is accepted only when the grader explicitly supplies a valid zero and grounded evidence',async()=>{
  const result=await runModelTest(env,body(),fixture([read(),grade({score:0})]));
  assert.equal(result.grading.status,'graded');assert.equal(result.grading.score,0);
});
test('Unicode/whitespace normalization validates quotations without changing the saved OCR',async()=>{
  const result=await runModelTest(env,body(),fixture([read({text:'[Page 1] Ａ = ４\nunits'}),grade({evidence:[{quote:'A = 4 units',reason:'same visible text'}]})]));
  assert.equal(result.ocr.text,'[Page 1] Ａ = ４\nunits');
  assert.equal(result.grading.status,'graded');
});
test('provider response bytes are bounded even when Content-Length is absent',async()=>{
  let cancelled=false;
  const stream=new ReadableStream({
    pull(controller){controller.enqueue(new Uint8Array(600000));},
    cancel(){cancelled=true;},
  });
  const mock=fixture([new Response(stream)]);
  await assert.rejects(runModelTest(env,body(),mock),error=>error.code==='model_test_invalid_response');
  assert.equal(mock.calls.length,1);assert.equal(cancelled,true);
});

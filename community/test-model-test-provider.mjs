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
    modelVersion: 'gemini-2.5-flash',
    candidates: [{ content: { parts: [{ text: JSON.stringify(value) }] }, finishReason: 'STOP' }],
    usageMetadata: { promptTokenCount: 120, candidatesTokenCount: 30, cachedContentTokenCount: 10 }, ...extra,
  } : { model: 'deepseek-flash', choices: [{ message: { content: JSON.stringify(value) }, finish_reason: 'stop' }],
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
]) test(pipeline+' runs exactly the selected OCR and grader; original images also reach grading',async()=>{
  const mock=fixture(),result=await runModelTest(env,body(pipeline),mock);
  assert.deepEqual(mock.calls.map(call=>call.provider),providers);
  assert.equal(mock.calls.length,2);
  const first=mock.calls[0].body,second=mock.calls[1].body;
  assert.ok(JSON.stringify(first).includes(png));
  assert.ok(!JSON.stringify(first).includes('Calculate 2+2.'));
  assert.ok(JSON.stringify(second).includes(png));
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

test('Gemini and DeepSeek keep the shared exam and policy before language and private OCR tails',async()=>{
  for(const pipeline of ['gemini-gemini','deepseek-deepseek']) {
    const runs=[];
    for(const [lang,marker] of [['en','PRIVATE_STUDENT_A'],['ko','PRIVATE_STUDENT_B']]) {
      const mock=fixture([read({text:'[Page 1] 2 + 2 = 4\n'+marker}),grade()]);
      assert.equal((await runModelTest(env,body(pipeline,{lang}),mock)).grading.status,'graded');
      const request=mock.calls[1].body, gemini=mock.calls[1].provider==='gemini';
      const policy=gemini?request.systemInstruction.parts[0].text:request.messages[0].content;
      const serialized=gemini?request.contents[0].parts[0].text:request.messages[1].content[0].text;
      const input=JSON.parse(serialized), boundary=serialized.indexOf('"language":');
      assert.deepEqual(Object.keys(input),['task','problem','rubric','points','min_score','language','page_count','visuals','transcript','uncertainties','legible']);
      assert.ok(boundary>serialized.indexOf('"rubric":')); assert.ok(boundary<serialized.indexOf('"transcript":'));
      assert.ok(policy.includes('Every evidence.quote for text evidence must be copied exactly')); assert.ok(!policy.includes(marker));
      assert.ok(serialized.includes(marker)); assert.ok(!serialized.slice(0,boundary).includes(marker));
      assert.ok(!Object.hasOwn(request,'cachedContent')); assert.ok(!JSON.stringify(request).includes('"cache_control"'));
      assert.ok(mock.calls.every(call=>call.url.endsWith(':generateContent')||call.url.endsWith('/chat/completions')));
      runs.push({policy,prefix:serialized.slice(0,boundary),request});
    }
    assert.equal(runs[0].policy,runs[1].policy); assert.equal(runs[0].prefix,runs[1].prefix);
    assert.ok(!JSON.stringify(runs[0].request).includes('PRIVATE_STUDENT_B')); assert.ok(!JSON.stringify(runs[1].request).includes('PRIVATE_STUDENT_A'));
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

for(const pipeline of ['gemini-gemini','gemini-deepseek','deepseek-deepseek'])test(pipeline+' grades image-only directional diagrams using bounded original-page evidence',async()=>{
  const visual={page:1,kind:'diagram',box:[.1,.2,.8,.9],description:'A vector arrow points upward beside the labelled axis.'};
  const evidence={source:'image',page:1,box:[.1,.2,.8,.9],description:visual.description,quote:'',reason:'The actual diagram meets the directional criterion.'};
  const mock=fixture([read({text:'',visuals:[visual]}),grade({evidence:[evidence]})]);
  const result=await runModelTest(env,body(pipeline),mock);
  assert.equal(result.ocr.text,'');assert.deepEqual(result.ocr.visuals,[visual]);assert.equal(result.grading.status,'graded');assert.equal(result.grading.score,1);
  assert.equal(result.grading.evidence[0].source,'image');assert.ok(JSON.stringify(mock.calls[1].body).includes(png));assert.equal(mock.calls.length,2);
});

test('nonexistent visual pages and degenerate image evidence cannot manufacture a numerical grade',async()=>{
  const visual={page:2,kind:'graph',box:[.1,.1,.9,.9],description:'A graph on an absent second page.'};
  const invalidOcr=fixture([read({text:'',visuals:[visual]})]);
  await assert.rejects(runModelTest(env,body(),invalidOcr),error=>error.code==='model_test_invalid_response'&&error.stage==='ocr'&&error.usage.calls===1);
  assert.equal(invalidOcr.calls.length,1);
  for(const evidence of [{source:'image',page:2,box:[.1,.1,.9,.9],description:'A copied reference figure, not a submitted page.',reason:'Wrong page',quote:''},
    {source:'image',page:1,box:[0,0,0,0],description:'An empty region is not image evidence.',reason:'Empty region',quote:''}]){
    const result=await runModelTest(env,body(),fixture([read(),grade({evidence:[evidence]})]));
    assert.equal(result.grading.status,'needs_review');assert.equal(result.grading.score,null);assert.ok(result.grading.review_reasons.includes('ungrounded_evidence'));
  }
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

test('usage separates requested and resolved models, counts thinking once, splits cache, and records bounded wall time',async()=>{
  const mock=fixture([
    response('gemini',read(),{usageMetadata:{promptTokenCount:120,cachedContentTokenCount:10,candidatesTokenCount:30,thoughtsTokenCount:7,totalTokenCount:157}}),
    response('deepseek',grade(),{usage:{prompt_tokens:100,prompt_cache_hit_tokens:5,prompt_cache_miss_tokens:95,completion_tokens:25,
      completion_tokens_details:{reasoning_tokens:9},total_tokens:125}}),
  ]);
  const result=await runModelTest(env,body('gemini-deepseek'),mock),[ocr,grading]=result.usage.stages;
  assert.equal(ocr.model,'gemini-flash-latest');assert.equal(ocr.resolved_model,'gemini-2.5-flash');
  assert.equal(grading.model,'deepseek-flash');assert.equal(grading.resolved_model,'deepseek-flash');
  assert.deepEqual([ocr.input_tokens,ocr.cached_tokens,ocr.uncached_input_tokens,ocr.output_tokens,ocr.reasoning_tokens,ocr.total_tokens],[120,10,110,37,7,157]);
  assert.deepEqual([grading.input_tokens,grading.cached_tokens,grading.uncached_input_tokens,grading.output_tokens,grading.reasoning_tokens,grading.total_tokens],[100,5,95,25,9,125]);
  assert.deepEqual([result.usage.input_tokens,result.usage.cached_tokens,result.usage.uncached_input_tokens,
    result.usage.output_tokens,result.usage.reasoning_tokens,result.usage.total_tokens],[220,15,205,62,16,282]);
  for(const stage of result.usage.stages){
    assert.equal(stage.calls,1);assert.equal(stage.usage_known,true);assert.equal(stage.ok,true);
    assert.equal(new Date(stage.started_at).toISOString(),stage.started_at);
    assert.equal(new Date(stage.finished_at).toISOString(),stage.finished_at);
    assert.equal(Date.parse(stage.finished_at)-Date.parse(stage.started_at),stage.ms);
    assert.equal(stage.output_tokens_per_second,stage.ms>0?stage.output_tokens*1000/stage.ms:null);
    assert.ok(stage.pricing);assert.ok(stage.pricing.unit_prices_per_token||stage.pricing.unit_price_ranges_per_token);
  }
  assert.ok(result.usage.pricing);assert.equal(result.usage.incomplete,undefined);
});

test('absent usage metadata is unknown, while explicitly reported zero tokens remain known zero',async()=>{
  const unknown=await runModelTest(env,body('gemini-deepseek'),fixture([
    response('gemini',read(),{usageMetadata:undefined}),response('deepseek',grade(),{usage:undefined}),
  ]));
  for(const stage of unknown.usage.stages){
    assert.equal(stage.usage_known,false);assert.equal(stage.pricing.total_usd,null);assert.equal(stage.pricing.status,'unknown');
    for(const field of ['input_tokens','cached_tokens','uncached_input_tokens','output_tokens','reasoning_tokens','total_tokens'])assert.equal(stage[field],null);
  }
  assert.equal(unknown.usage.input_tokens,null);assert.equal(unknown.usage.known_tokens.input_tokens,null);assert.equal(unknown.usage.incomplete,true);
  assert.equal(unknown.usage.pricing.total_usd,null);
  const zero=await runModelTest(env,body('deepseek-deepseek'),fixture([
    response('deepseek',read(),{usage:{prompt_tokens:0,completion_tokens:0,prompt_cache_hit_tokens:0,prompt_cache_miss_tokens:0,total_tokens:0,completion_tokens_details:{reasoning_tokens:0}}}),
    response('deepseek',grade(),{usage:{prompt_tokens:0,completion_tokens:0,prompt_cache_hit_tokens:0,prompt_cache_miss_tokens:0,total_tokens:0,completion_tokens_details:{reasoning_tokens:0}}}),
  ]));
  assert.equal(zero.usage.input_tokens,0);assert.equal(zero.usage.output_tokens,0);assert.equal(zero.usage.reasoning_tokens,0);
  assert.equal(zero.usage.incomplete,undefined);assert.ok(zero.usage.stages.every(stage=>stage.usage_known));
  assert.equal(zero.usage.pricing.total_usd,0);
});

test('partial token metadata preserves reported counts and never invents cache or reasoning amounts',async()=>{
  const result=await runModelTest(env,body('gemini-deepseek'),fixture([
    response('gemini',read(),{usageMetadata:{promptTokenCount:120,candidatesTokenCount:30,totalTokenCount:150}}),
    response('deepseek',grade(),{usage:{prompt_tokens:100,completion_tokens:25,total_tokens:125}}),
  ]));
  const [ocr,grading]=result.usage.stages;
  assert.equal(ocr.cached_tokens,0);assert.equal(ocr.reasoning_tokens,0);assert.equal(ocr.usage_known,true);
  assert.equal(grading.input_tokens,100);assert.equal(grading.output_tokens,25);assert.equal(grading.total_tokens,125);
  assert.equal(grading.cached_tokens,null);assert.equal(grading.uncached_input_tokens,null);assert.equal(grading.reasoning_tokens,null);
  assert.equal(grading.usage_known,false);assert.equal(grading.pricing.total_usd,null);
  assert.equal(result.usage.input_tokens,220);assert.equal(result.usage.cached_tokens,null);assert.equal(result.usage.known_tokens.cached_tokens,0);
  assert.equal(result.usage.reasoning_tokens,null);assert.equal(result.usage.incomplete,true);assert.equal(result.usage.pricing.total_usd,null);
});

test('HTTP 200 model-output parse failures retain usage, resolved model, elapsed time and estimated billing',async()=>{
  const invalidOcr=response('gemini',read(),{candidates:[{finishReason:'STOP',content:{parts:[{text:'not JSON'}]}}]});
  await assert.rejects(runModelTest(env,body(),fixture([invalidOcr])),error=>{
    assert.equal(error.code,'model_test_invalid_response');assert.equal(error.ocr,undefined);assert.equal(error.usage.calls,1);
    const stage=error.usage.stages[0];assert.equal(stage.ok,false);assert.equal(stage.usage_known,true);
    assert.equal(stage.resolved_model,'gemini-2.5-flash');assert.equal(stage.input_tokens,120);assert.equal(stage.output_tokens,30);
    assert.equal(stage.pricing.status,'estimated');assert.ok(stage.pricing.total_usd>0);assert.equal(error.usage.incomplete,true);return true;
  });
  const invalidGrade=response('deepseek',grade(),{choices:[{finish_reason:'length',message:{content:'{"score":'}}]});
  await assert.rejects(runModelTest(env,body('gemini-deepseek'),fixture([read(),invalidGrade])),error=>{
    assert.equal(error.stage,'grading');assert.equal(error.ocr.text,read().text);assert.equal(error.usage.calls,2);
    assert.equal(error.usage.input_tokens,220);assert.equal(error.usage.stages[1].ok,false);assert.equal(error.usage.stages[1].usage_known,true);
    assert.equal(error.usage.stages[1].output_tokens,25);assert.ok(error.usage.stages[1].pricing.total_usd!==null||error.usage.stages[1].pricing.range_usd);return true;
  });
});

test('semantic OCR schema failures retain known usage and mark the attempted stage as failed',async()=>{
  await assert.rejects(runModelTest(env,body(),fixture([response('gemini',{text:'answer'})])),error=>{
    assert.equal(error.usage.calls,1);assert.equal(error.usage.stages[0].ok,false);assert.equal(error.usage.stages[0].usage_known,true);
    assert.equal(error.usage.input_tokens,120);assert.ok(error.usage.pricing.total_usd>0);return true;
  });
});

test('network failures retain earlier known partial usage but never publish unknown usage as a zero total',async()=>{
  await assert.rejects(runModelTest(env,body('gemini-deepseek'),fixture([read(),new Error('SECRET network request')])),error=>{
    const failed=error.usage.stages[1];assert.equal(failed.usage_known,false);assert.equal(failed.ok,false);assert.equal(failed.resolved_model,null);
    assert.equal(failed.total_tokens,null);assert.equal(error.usage.input_tokens,null);assert.equal(error.usage.output_tokens,null);
    assert.equal(error.usage.known_tokens.input_tokens,120);assert.equal(error.usage.known_tokens.output_tokens,30);
    assert.equal(error.usage.pricing.total_usd,null);assert.ok(error.usage.pricing.known_usd>0);
    assert.ok(!JSON.stringify(error).includes('SECRET'));return true;
  });
});

test('invalid token splits and unsafe resolved-model strings cannot fabricate known billing',async()=>{
  const result=await runModelTest(env,body('deepseek-deepseek'),fixture([
    response('deepseek',read(),{model:'sk-secret-do-not-publish',usage:{prompt_tokens:100,completion_tokens:25,prompt_cache_hit_tokens:101}}),
    response('deepseek',grade(),{model:'deepseek-unknown-unpriced',usage:{prompt_tokens:100,completion_tokens:25,prompt_cache_hit_tokens:5,
      prompt_cache_miss_tokens:95,total_tokens:125,completion_tokens_details:{reasoning_tokens:26}}}),
  ]));
  const [ocr,grading]=result.usage.stages;assert.equal(ocr.resolved_model,null);assert.equal(ocr.cached_tokens,null);assert.equal(ocr.usage_known,false);
  assert.equal(grading.reasoning_tokens,null);assert.equal(grading.usage_known,false);assert.equal(grading.pricing.total_usd,null);
  assert.ok(!JSON.stringify(result).includes('sk-secret'));assert.equal(result.usage.pricing.total_usd,null);
});

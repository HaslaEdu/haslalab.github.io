import test from 'node:test';
import assert from 'node:assert/strict';
import { visionJSON, visionTranscript, visionCapabilities, VISION_MODELS, VISION_IMAGE_LIMIT, listProviderModels } from './src/vision-provider.js';
const env={GEMINI_API_KEY:'fixture-g',DEEPSEEK_API_KEY:'fixture-d'};
const image={mime:'image/png',data:'iVBORw0KGgo=',label:'student page 1'};
const response=(provider,raw={ok:true},extra={})=>Response.json(provider==='gemini'?{
 modelVersion:VISION_MODELS.gemini,candidates:[{finishReason:'STOP',content:{parts:[{text:JSON.stringify(raw)}]}}],
 usageMetadata:{promptTokenCount:100,cachedContentTokenCount:40,candidatesTokenCount:20,totalTokenCount:120},...extra
}:{
 model:VISION_MODELS.deepseek,choices:[{finish_reason:'stop',message:{content:JSON.stringify(raw)}}],
 usage:{prompt_tokens:100,prompt_cache_hit_tokens:40,prompt_cache_miss_tokens:60,completion_tokens:20,total_tokens:120},...extra
});
for(const provider of ['deepseek','gemini'])test(provider+': exact selected model, image bytes, original detail and cached meter',async()=>{
 let calls=0;
 const result=await visionJSON({...env,GEMINI_MODEL:'unwanted',DEEPSEEK_MODEL:'unwanted'},{
  provider,policy:'fixed competition rubric',images:[image],input:{answer:'arrow to the left'},schema:{type:'object'},
  fetchImpl:async(url,request)=>{
   calls++;assert.equal(request.redirect,'manual');const body=JSON.parse(request.body);
   if(provider==='gemini'){
    assert.match(url,/gemini-3\.5-flash-lite:generateContent$/);assert.equal(request.headers['x-goog-api-key'],'fixture-g');
    assert.deepEqual(body.contents[0].parts[2].inline_data,{mime_type:image.mime,data:image.data});
    assert.match(body.systemInstruction.parts[0].text,/arrows/);
   }else{
    assert.match(url,/api\.deepseek\.com\/chat\/completions$/);assert.equal(body.model,'deepseek-flash');assert.equal(request.headers.Authorization,'Bearer fixture-d');
    assert.deepEqual(body.messages[1].content[2].image_url,{url:'data:image/png;base64,'+image.data,detail:'high'});
   }return response(provider);
  }
 });
 assert.equal(calls,1);assert.deepEqual(result.raw,{ok:true});assert.equal(result.usage.cached_tokens,40);
 assert.equal(result.usage.uncached_input_tokens,60);assert.equal(result.usage.output_tokens,20);assert.equal(result.provider,provider);
});
test('ordered reference prefix, official image, student suffix and student image retain association',async()=>{
 await visionJSON(env,{provider:'deepseek',parts:[{text:'official reference prefix'},{...image,label:'official graph'},{text:'student suffix'},{...image,label:'student graph'}],
 fetchImpl:async(_url,request)=>{
  assert.deepEqual(JSON.parse(request.body).messages[1].content.filter(p=>p.type==='text').map(p=>p.text),['official reference prefix','official graph','student suffix','student graph']);
  return response('deepseek');
 }});
});
test('missing/unavailable choice, invalid/PDF image and oversize never call a provider',async()=>{
 let calls=0;const options={fetchImpl:async()=>{calls++;throw Error('unexpected');}};
 for(const [settings,provider,images,code]of [
  [env,undefined,[image],'bad_provider'],[{},'deepseek',[image],'provider_unavailable'],
  [env,'deepseek',[{mime:'application/pdf',data:'JVBERi0='}],'vision_bad_image'],
  [env,'gemini',[{...image,data:'https://private.example/file'}],'vision_bad_image'],
  [env,'gemini',[{...image,data:Buffer.alloc(VISION_IMAGE_LIMIT+1).toString('base64')}],'vision_images_too_large']
 ])await assert.rejects(visionJSON(settings,{...options,provider,images}),e=>e.code===code);
 assert.equal(calls,0);assert.equal(visionCapabilities({}).providers.every(p=>p.available===false),true);
});
test('provider failure has no fallback and never leaks provider body or credentials',async()=>{
 const calls=[];
 await assert.rejects(visionJSON(env,{provider:'deepseek',images:[image],fetchImpl:async(url)=>{
  calls.push(url);return new Response('sensitive fixture-d payload',{status:401});
 }}),e=>e.code==='vision_provider_auth'&&!JSON.stringify(e).includes('fixture-d')&&!e.message.includes('sensitive'));
 assert.equal(calls.length,1);assert.match(calls[0],/deepseek/);
});
test('invalid paid response keeps known usage and impossible cached totals remain unknown',async()=>{
 await assert.rejects(visionJSON(env,{provider:'gemini',fetchImpl:async()=>response('gemini',[],{})}),e=>e.code==='vision_invalid_response'&&e.usage.input_tokens===100&&e.usage.ok===false);
 const result=await visionJSON(env,{provider:'deepseek',fetchImpl:async()=>response('deepseek',{ok:true},{usage:{prompt_tokens:3,prompt_cache_hit_tokens:5,completion_tokens:2}})});
 assert.equal(result.usage.cached_tokens,null);assert.equal(result.usage.uncached_input_tokens,null);assert.equal(result.usage.usage_known,false);
});
test('timeout and caller cancellation complete even when fetch ignores its signal',async()=>{
 await assert.rejects(visionJSON(env,{provider:'gemini',timeoutMs:5,fetchImpl:()=>new Promise(()=>{})}),e=>e.code==='vision_provider_timeout');
 const controller=new AbortController();
 const pending=visionJSON(env,{provider:'deepseek',signal:controller.signal,fetchImpl:()=>new Promise(()=>{})});
 controller.abort();await assert.rejects(pending,e=>e.code==='vision_provider_timeout');
});
test('graph-only OCR works while invented page/bounding-box records are rejected',async()=>{
 const raw={text:'',legible:true,uncertainties:[],visuals:[{page:1,kind:'direction',description:'blue arrow from left to right',box:[.1,.1,.9,.9]}]};
 const result=await visionTranscript(env,'gemini',[image],{fetchImpl:async()=>response('gemini',raw)});
 assert.equal(result.text,'');assert.equal(result.visuals[0].kind,'direction');
 for(const visual of [{...raw.visuals[0],page:2},{...raw.visuals[0],box:[0,0,2,2]}])
  await assert.rejects(visionTranscript(env,'gemini',[image],{fetchImpl:async()=>response('gemini',{...raw,visuals:[visual]})}),e=>e.code==='vision_response_schema');
});

test('HTTP causes remain distinguishable without exposing upstream error text',async()=>{
 for(const [status,code]of [[400,'vision_request_rejected'],[401,'vision_provider_auth'],[402,'vision_provider_credits'],[403,'vision_provider_auth'],[404,'vision_model_unavailable'],[413,'vision_request_rejected'],[422,'vision_request_rejected'],[429,'vision_provider_rate_limited'],[503,'vision_provider_failed']]){
  await assert.rejects(visionJSON(env,{provider:'deepseek',fetchImpl:async()=>Response.json({error:{code:'invalid_request_error',message:'private fixture-d user data'}},{status})}),error=>{
   assert.equal(error.code,code);assert.equal(error.provider_status,status);assert.equal(error.provider_code,'invalid_request_error');assert.ok(error.ms>=0);
   assert.ok(!JSON.stringify(error).includes('private fixture-d'));assert.equal(error.provider_message,'private fixture-d user data','kept apart for the admin bench only');return true;
  });
 }
 await assert.rejects(visionJSON(env,{provider:'deepseek',fetchImpl:async()=>Response.json({error:{code:'sk-private-token',message:'sensitive'}},{status:400})}),error=>error.provider_code===undefined&&!JSON.stringify(error).includes('sk-private'));
});
test('blank JSON-mode output and truncated/blocked responses retain paid usage and distinct causes',async()=>{
 for(const [content,finish,code]of [['   ','stop','vision_response_empty'],['{"text":"cut','length','vision_response_truncated'],['','content_filter','vision_response_blocked']]){
  await assert.rejects(visionJSON(env,{provider:'deepseek',fetchImpl:async()=>response('deepseek',{}, {choices:[{finish_reason:finish,message:{content}}]})}),error=>error.code===code&&error.usage.input_tokens===100&&error.usage.ok===false&&error.provider_status===200);
 }
 await assert.rejects(visionJSON(env,{provider:'gemini',fetchImpl:async()=>response('gemini',{}, {candidates:[{finishReason:'MAX_TOKENS',content:{parts:[{text:'{'}]}}]})}),error=>error.code==='vision_response_truncated'&&error.usage.input_tokens===100);
});
test('DeepSeek OCR receives an explicit JSON example with required fields and no student content in the prefix',async()=>{
 await visionTranscript(env,'deepseek',[image],{fetchImpl:async(_url,request)=>{
  const body=JSON.parse(request.body),system=body.messages[0].content;
  assert.match(system,/JSON structure example/);assert.match(system,/"text":""/);assert.match(system,/"visuals":\[\]/);assert.ok(!system.includes(image.data));
  return response('deepseek',{text:'visible handwritten answer',legible:true,uncertainties:[],visuals:[]});
 }});
});
test('gemini: thinking is asked at its lowest level, and a request refused for it is sent once more without it',async()=>{
 const bodies=[];
 const result=await visionJSON(env,{provider:'gemini',policy:'p',images:[image],input:'x',schema:{type:'object'},
  fetchImpl:async(_url,request)=>{const body=JSON.parse(request.body);bodies.push(body);
   if(body.generationConfig.thinkingConfig)return new Response(JSON.stringify({error:{code:400,status:'INVALID_ARGUMENT'}}),{status:400});
   return response('gemini');}});
 assert.equal(bodies.length,2);assert.deepEqual(bodies[0].generationConfig.thinkingConfig,{thinkingLevel:'minimal'});
 assert.equal(bodies[1].generationConfig.thinkingConfig,undefined);assert.deepEqual(result.raw,{ok:true});
 const off=[];await visionJSON({...env,GEMINI_THINKING_LEVEL:'off'},{provider:'gemini',policy:'p',images:[image],input:'x',schema:{type:'object'},
  fetchImpl:async(_url,request)=>{off.push(JSON.parse(request.body));return response('gemini');}});
 assert.equal(off.length,1);assert.equal(off[0].generationConfig.thinkingConfig,undefined);
});

test('a bench model replaces the default only when it is that provider\'s own id; the listing names what each key serves',async()=>{
 const urls=[],models=[];const fetchImpl=async(url,request)=>{urls.push(url);models.push(JSON.parse(request.body).model);return response(url.includes('deepseek')?'deepseek':'gemini');};
 for(const model of ['gemini-3.6-flash','deepseek-v4-pro','../evil','gemini-x/../../y'])
  await visionJSON(env,{provider:'gemini',policy:'p',images:[image],input:'x',schema:{type:'object'},model,fetchImpl});
 await visionJSON(env,{provider:'deepseek',policy:'p',images:[image],input:'x',schema:{type:'object'},model:'deepseek-v4-pro',fetchImpl});
 assert.match(urls[0],/\/models\/gemini-3\.6-flash:generateContent$/);
 for(const url of urls.slice(1,4))assert.match(url,/\/models\/gemini-3\.5-flash-lite:generateContent$/);
 assert.equal(models[4],'deepseek-v4-pro');
 const listed=await listProviderModels(env,'gemini',async url=>{assert.match(url,/\/v1beta\/models\?pageSize=1000$/);return Response.json({models:[
  {name:'models/gemini-3.6-flash',supportedGenerationMethods:['generateContent']},{name:'models/text-embedding-004',supportedGenerationMethods:['embedContent']}]});});
 assert.deepEqual(listed,['gemini-3.6-flash']);
 assert.deepEqual(await listProviderModels(env,'deepseek',async url=>{assert.equal(url,'https://api.deepseek.com/models');return Response.json({data:[{id:'deepseek-flash'},{id:'deepseek-v4-pro'}]});}),['deepseek-flash','deepseek-v4-pro']);
});

test('Claude reads through the SDK: images as image blocks, PDFs as documents, the server-side fallback on 5.5 models, a 429 as rate-limited', async () => {
  const { visionJSON } = await import('./src/vision-provider.js');
  const sse = text => ['message_start', { type: 'message_start', message: { id: 'm', type: 'message', role: 'assistant', model: 'claude-sonnet-5-5', content: [], stop_reason: null, usage: { input_tokens: 120, output_tokens: 1, cache_read_input_tokens: 30 } } },
    'content_block_start', { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } },
    'content_block_delta', { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text } },
    'content_block_stop', { type: 'content_block_stop', index: 0 },
    'message_delta', { type: 'message_delta', delta: { stop_reason: 'end_turn' }, usage: { output_tokens: 9 } },
    'message_stop', { type: 'message_stop' }].reduce((out, v, i, a) => i % 2 ? out : out + `event: ${v}\ndata: ${JSON.stringify(a[i + 1])}\n\n`, '');
  const seen = [], original = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    seen.push({ url: String(url), headers: new Headers(init.headers), body: JSON.parse(init.body) });
    if (seen.length === 2) return new Response(JSON.stringify({ type: 'error', error: { type: 'rate_limit_error', message: 'slow down' } }), { status: 429, headers: { 'content-type': 'application/json' } });
    return new Response(sse('{"text":"x = 2 m","items":[]}'), { headers: { 'content-type': 'text/event-stream' } });
  };
  try {
    const env = { ANTHROPIC_API_KEY: 'test-key' }, jpeg = Buffer.from([255, 216, 255, 224, 0, 16]).toString('base64'), pdf = Buffer.from('%PDF-1.4 x').toString('base64');
    const out = await visionJSON(env, { provider: 'anthropic', model: 'claude-sonnet-5-5', thinking: 'low', schema: { type: 'object', properties: { text: { type: 'string' } } },
      parts: [{ text: '[TASK: read page]' }, { inline_data: { mime_type: 'image/jpeg', data: jpeg }, label: 'page 1' }, { inline_data: { mime_type: 'application/pdf', data: pdf }, label: 'solution' }] });
    assert.equal(out.raw.text, 'x = 2 m'); assert.equal(out.usage.input_tokens, 150); assert.equal(out.usage.cached_tokens, 30); assert.equal(out.usage.output_tokens, 9);
    const req = seen[0];
    assert.match(req.url, /api\.anthropic\.com\/v1\/messages/); assert.equal(req.body.model, 'claude-sonnet-5-5'); assert.equal(req.body.fallbacks, 'default');
    assert.match(req.headers.get('anthropic-beta') || '', /server-side-fallback-2026-07-01/); assert.equal(req.body.output_config.effort, 'low');
    const content = req.body.messages[0].content;
    assert.deepEqual(content.map(b => b.type), ['text', 'text', 'image', 'text', 'document']); assert.equal(content[2].source.media_type, 'image/jpeg');
    assert.deepEqual(content[4].cache_control, { type: 'ephemeral' }, 'the papers are the cached prefix'); assert.equal(content[2].cache_control, undefined);
    assert.match(req.body.system, /Return exactly one JSON object/); assert.equal(req.body.temperature, undefined, 'no sampling parameters on 5.5 models');
    await assert.rejects(visionJSON(env, { provider: 'anthropic', model: 'claude-haiku-5-5', parts: [{ text: 'x' }] }), e => e.code === 'vision_provider_rate_limited' && e.provider_status === 429);
    assert.equal(seen[1].body.fallbacks, undefined, 'Haiku has no server-side fallback');
  } finally { globalThis.fetch = original; }
});

test('OpenAI models are called on chat completions with images, PDFs as files and their reasoning effort', async () => {
  const { visionJSON } = await import('./src/vision-provider.js');
  let sent;
  const fetchImpl = async (url, init) => { sent = { url: String(url), headers: init.headers, body: JSON.parse(init.body) };
    return Response.json({ model: 'gpt-5-mini', choices: [{ finish_reason: 'stop', message: { content: '{"ok":true}' } }], usage: { prompt_tokens: 50, completion_tokens: 7, prompt_tokens_details: { cached_tokens: 10 } } }); };
  const out = await visionJSON({ OPENAI_API_KEY: 'k' }, { provider: 'openai', model: 'gpt-5-mini', thinking: 'low', fetchImpl, schema: { type: 'object' },
    parts: [{ text: 'grade' }, { inline_data: { mime_type: 'image/png', data: 'iVBORw0KGgo=' } }, { inline_data: { mime_type: 'application/pdf', data: 'JVBERi0=' } }] });
  assert.equal(out.raw.ok, true); assert.match(sent.url, /api\.openai\.com\/v1\/chat\/completions$/); assert.equal(sent.headers.Authorization, 'Bearer k');
  assert.equal(sent.body.reasoning_effort, 'low'); assert.equal(sent.body.response_format.type, 'json_object'); assert.ok(sent.body.max_completion_tokens > 0);
  const user = sent.body.messages[1].content;
  assert.ok(user.some(p => p.type === 'image_url' && p.image_url.url.startsWith('data:image/png;base64,'))); assert.ok(user.some(p => p.type === 'file' && p.file.file_data.startsWith('data:application/pdf;base64,')));
  assert.equal(out.usage.cached_tokens, 10);
});

test('a candidate still chooses only Gemini or DeepSeek; the new providers are for the pipeline\'s stages', async () => {
  const { visionProvider, requireVisionProvider, visionCapabilities, providerKeys } = await import('./src/vision-provider.js');
  assert.throws(() => visionProvider('anthropic'), e => e.code === 'bad_provider'); assert.throws(() => visionProvider('openai'), e => e.code === 'bad_provider');
  assert.equal(requireVisionProvider({ CLAUDE_API_KEY: 'x' }, 'anthropic'), 'anthropic', 'an alternative key name is accepted');
  assert.deepEqual(visionCapabilities({}).providers.map(p => p.id), ['gemini', 'deepseek']);
  assert.deepEqual(providerKeys({ OPENAI_API_KEY: 'a', MY_CLAUDE: 'secret-value' }), { gemini: false, deepseek: false, openai: true, anthropic: false, names: ['MY_CLAUDE', 'OPENAI_API_KEY'] });
  assert.throws(() => requireVisionProvider({ ANTHROPIC_API_KEY: '  \n' }, 'anthropic'), e => e.code === 'provider_unavailable', 'a blank key is no key');
});

import test from 'node:test';
import assert from 'node:assert/strict';
import { visionJSON, visionTranscript, visionCapabilities, VISION_MODELS, VISION_IMAGE_LIMIT } from './src/vision-provider.js';
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
   assert.ok(!JSON.stringify(error).includes('private fixture-d'));return true;
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

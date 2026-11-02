// Real workerd Request/fetch semantics. All upstream HTTP is a loopback mock;
// this suite uses no Cloudflare account, production binding or billed provider.
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url);
const {unstable_dev}=require(process.env.HASLA_WRANGLER_PATH||'wrangler');
test('actual workerd calls both visual adapters and refuses to follow credential-bearing redirects', {timeout:60000},async()=>{
 const calls=[];
 const upstream=http.createServer(async(request,response)=>{
  const chunks=[];for await(const chunk of request)chunks.push(chunk);
  calls.push({url:request.url,authorization:request.headers.authorization});
  if(request.url.startsWith('/redirect/')){response.writeHead(302,{Location:base+'/credential-destination'});return response.end();}
  const gemini=request.url.includes(':generateContent');
  if(gemini)assert.equal(request.headers['x-goog-api-key'],'runtime-g');
  else assert.equal(request.headers.authorization,'Bearer runtime-d');
  response.setHeader('Content-Type','application/json');
  const content=JSON.stringify({text:'local runtime fixture'});
  response.end(JSON.stringify(gemini?{modelVersion:'gemini-3.5-flash-lite',candidates:[{finishReason:'STOP',content:{parts:[{text:content}]}}],usageMetadata:{promptTokenCount:10,candidatesTokenCount:5,totalTokenCount:15}}:
   {model:'deepseek-flash',choices:[{finish_reason:'stop',message:{content}}],usage:{prompt_tokens:10,completion_tokens:5,prompt_cache_hit_tokens:0,prompt_cache_miss_tokens:10}}));
 });
 await new Promise(resolve=>upstream.listen(0,'127.0.0.1',resolve));
 const base='http://127.0.0.1:'+upstream.address().port;let worker;
 try{
  worker=await unstable_dev(fileURLToPath(new URL('./fixtures/vision-runtime-worker.mjs',import.meta.url)),{
   config:fileURLToPath(new URL('./fixtures/wrangler-vision-runtime.toml',import.meta.url)),
   local:true,ip:'127.0.0.1',port:0,persist:false,logLevel:'error',
   vars:{GEMINI_API_KEY:'runtime-g',DEEPSEEK_API_KEY:'runtime-d',GEMINI_BASE:base,DEEPSEEK_BASE:base,FIXTURE_BASE:base},
   experimental:{disableExperimentalWarning:true,disableDevRegistry:true},
  });
  const old=await worker.fetch('/old-option');assert.deepEqual(await old.json(),{rejected:true,type:'TypeError'});
  assert.equal(calls.length,0,'unsupported redirect:error fails before any HTTP request in workerd');
  for(const path of ['/','/developer'])for(const provider of ['deepseek','gemini']){
   const response=await worker.fetch(path+'?provider='+provider),result=await response.json();assert.equal(response.status,200,JSON.stringify({path,provider,result,calls:calls.length}));
   assert.deepEqual(result,{text:'local runtime fixture',provider});
  }
  assert.equal(calls.length,4);
  for(const path of ['/','/developer']){
   const response=await worker.fetch(path+'?provider=deepseek&redirect=1');assert.equal(response.status,502);
   const result=await response.json();assert.ok(['vision_provider_failed','model_test_provider_failed'].includes(result.error));
  }
  assert.equal(calls.length,6);assert.ok(!calls.some(call=>call.url.includes('credential-destination')));
 }finally{await worker?.stop();await new Promise(resolve=>upstream.close(resolve));}
});

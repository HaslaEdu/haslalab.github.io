import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import {createProblemBankOcrRouter,PROBLEM_BANK_OCR_PATH,geminiProblemText} from './src/problem-bank-ocr.js';
import {upstageParse} from './src/upstage-ocr.js';
import community from './src/index.js';
import bank from '../problem-bank/worker.mjs';

if(!globalThis.crypto)globalThis.crypto=webcrypto;
const TOKEN='a'.repeat(32),SID='src_'+'b'.repeat(64),KEY='synthetic-test-provider-key';
const PNG=Uint8Array.from(Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aXioAAAAASUVORK5CYII=','base64'));
const URL_BASE='https://community.test'+PROBLEM_BANK_OCR_PATH;
const ADMIN={id:1,role:'admin',username:'admin',nickname:'Admin'},USER={id:2,role:'user',username:'member',nickname:'Member'};
const TEXT='Find the kinetic energy $E=\\frac12mv^2$ of the particle.';
class HttpError extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
const needUser=user=>{if(!user)throw new HttpError(401,'login_required');return user;};
function photo({bytes=PNG,type='image/png',extra=[],duplicate=false}={}){
  const form=new FormData();form.append('image',new Blob([bytes],{type}),'photo.png');if(duplicate)form.append('image',new Blob([bytes],{type}),'second.png');for(const [key,value]of extra)form.append(key,value);return form;
}
const request=(body=photo(),extra={})=>new Request(URL_BASE+'?mode=math',{method:'POST',body,...extra});
function fixture({user=ADMIN,configured=true,parse}={}){
  const calls={parse:0,auth:0},env={...(configured?{GEMINI_API_KEY:KEY}:{})};
  const router=createProblemBankOcrRouter({HttpError,currentUser:async()=>{calls.auth++;return user;},needUser,parse:parse??(async()=>{calls.parse++;return{markdown:TEXT};})});
  return {router,env,calls,call:req=>router(req,env)};
}
const rejects=(promise,status,code)=>assert.rejects(promise,error=>error.status===status&&error.code===code);

test('dedicated archive OCR denies guests and members before reading bytes or invoking a provider',async()=>{
  for(const [user,status,code]of [[null,401,'login_required'],[USER,403,'admin_required']]){
    const f=fixture({user});let reads=0;
    const req={method:'POST',url:URL_BASE,headers:new Headers({'Content-Type':'application/json'}),body:{getReader(){reads++;assert.fail('unauthorized body must not be read');}}};
    await rejects(f.call(req),status,code);assert.equal(reads,0);assert.equal(f.calls.parse,0);assert.equal(f.calls.auth,1);
  }
});

test('archive OCR rejects unsupported methods and missing keys without invoking a provider',async()=>{
  const f=fixture();await rejects(f.call(new Request(URL_BASE)),405,'method_not_allowed');assert.equal(f.calls.auth,0);assert.equal(f.calls.parse,0);
  const off=fixture({configured:false});await rejects(off.call(request()),503,'ocr_unavailable');assert.equal(off.calls.parse,0);
});

test('only one original raster image is accepted, without monthly IDs, model selection or source data',async()=>{
  const f=fixture();
  for(const extra of [[['problem_id','8']],[['provider','deepseek']],[['model','other']],[['source',SID]],[['solution','hidden answer']]])await rejects(f.call(request(photo({extra}))),400,'invalid_scan');
  await rejects(f.call(request(photo({duplicate:true}))),400,'invalid_scan');
  await rejects(f.call(request(new FormData())),400,'invalid_scan');
  await rejects(f.call(request(photo({bytes:new Uint8Array()}))),400,'invalid_scan');
  await rejects(f.call(request(photo({type:'image/svg+xml'}))),415,'unsupported_scan_type');
  await rejects(f.call(request(photo({bytes:new TextEncoder().encode('not a PNG')}))),400,'invalid_scan');
  await rejects(f.call(request(photo({type:'image/jpeg'}))),400,'invalid_scan');
  await rejects(f.call(new Request(URL_BASE+'?mode=math&provider=upstage',{method:'POST',body:photo()})),400,'invalid_scan');
  await rejects(f.call(new Request(URL_BASE+'?mode=math&mode=math',{method:'POST',body:photo()})),400,'invalid_scan');
  assert.equal(f.calls.parse,0);
});

test('oversized image data and oversized declared uploads fail before paid parsing',async()=>{
  const f=fixture(),large=new Uint8Array(8*1024*1024+1);large.set(PNG.subarray(0,8));
  await rejects(f.call(request(photo({bytes:large}))),413,'image_too_big');
  await rejects(f.call(request(photo(),{headers:{'Content-Length':String(9*1024*1024)}})),413,'image_too_big');
  assert.equal(f.calls.parse,0);
});

const geminiReply=text=>Response.json({candidates:[{content:{parts:[{text:JSON.stringify({text})}]},finishReason:'STOP'}],usageMetadata:{promptTokenCount:300,candidatesTokenCount:40,totalTokenCount:340}});
async function withFetch(impl,run){const original=globalThis.fetch;globalThis.fetch=impl;try{return await run();}finally{globalThis.fetch=original;}}
test('valid admin photos are transcribed once by Gemini 3.1 Flash-Lite, keeping LaTeX, with no key or prompt in the result',async()=>{
  let paidCalls=0;
  const out=await withFetch(async(url,init)=>{paidCalls++;assert.match(String(url),/gemini-3\.1-flash-lite:generateContent/);const body=JSON.parse(init.body);assert.ok(JSON.stringify(body).includes(Buffer.from(PNG).toString('base64')));return geminiReply(TEXT);},
    ()=>fixture({parse:geminiProblemText}).call(request()));
  assert.equal(paidCalls,1);assert.equal(out.text,TEXT);assert.equal(out.confidence,null);assert.equal(out.engine,'gemini-3.1-flash-lite');assert.equal(out.format,'markdown-latex');assert.doesNotMatch(JSON.stringify(out),/synthetic-test-provider-key|Transcribe|solution|grade|photo_id/);
  const other=await withFetch(async url=>{assert.match(String(url),/gemini-9-test:generateContent/);return geminiReply(TEXT);},()=>geminiProblemText({GEMINI_API_KEY:KEY,BANK_OCR_MODEL:'gemini-9-test'},PNG,'image/png'));
  assert.equal(other.markdown,TEXT);assert.equal(other.model,'gemini-9-test');
});

test('archive-only parsing sanitizes provider failures and private diagnostics',async()=>{
  for(const [status,expectedStatus,code]of [[429,429,'ocr_rate_limited'],[500,502,'ocr_failed'],[401,502,'ocr_failed']]){
    await withFetch(async()=>new Response('PRIVATE provider diagnostic '+KEY,{status}),async()=>{
      await assert.rejects(fixture({parse:geminiProblemText}).call(request()),error=>error.status===expectedStatus&&error.code===code&&!String(error.message).includes(KEY));
    });
  }
  for(const name of ['AbortError','TimeoutError']){const f=fixture({parse:async()=>{const e=new Error('PRIVATE timeout');e.name=name;throw e;}});await rejects(f.call(request()),504,'ocr_timeout');}
});

test('existing non-archive Upstage calls retain their three-attempt default',async()=>{
  const original=globalThis.setTimeout;let calls=0;globalThis.setTimeout=callback=>{queueMicrotask(callback);return 0;};
  try{const result=await upstageParse({UPSTAGE_API_KEY:KEY},PNG,'image/png',{fetchImpl:async()=>{calls++;return calls<3?new Response('temporary',{status:503}):Response.json({content:{markdown:TEXT},usage:{pages:1}});}});assert.equal(calls,3);assert.equal(result.markdown,TEXT);}
  finally{globalThis.setTimeout=original;}
});

test('the shared Upstage helper keeps the filename extension consistent with accepted image MIME types',async()=>{
  for(const [mime,name]of [['image/png','page.png'],['image/jpeg','page.jpg'],['image/webp','page.webp']])await upstageParse({UPSTAGE_API_KEY:KEY},PNG,mime,{maxAttempts:1,fetchImpl:async(url,init)=>{assert.equal(init.body.get('document').name,name);assert.equal(init.body.get('document').type,mime);return Response.json({content:{markdown:TEXT},usage:{pages:1}});}});
});

test('empty, overlong or corrupt transcripts fail without truncating problem conditions',async()=>{
  for(const markdown of ['',null,'abc','x'.repeat(12001),'valid\0invalid']){const f=fixture({parse:async()=>({markdown})});await rejects(f.call(request()),422,'ocr_text_unusable');}
});

function liveFixture(user=ADMIN,{configured=true}={}){
  const sql=[];const db={prepare(query){sql.push(query);return{bind(){return{async first(){assert.match(query,/FROM sessions s JOIN users u/);return user?{...user}:null;},async all(){assert.match(query,/FROM sessions s JOIN users u/);return{results:user?[{...user}]:[]};}};}};}};
  return {env:{DB:db,...(configured?{GEMINI_API_KEY:KEY}:{}),ALLOWED_ORIGINS:'https://haslalab.org'},sql};
}

test('actual community dispatch authenticates the dedicated path before generic body parsing',async()=>{
  for(const [user,status]of [[null,401],[USER,403]]){
    const f=liveFixture(user),req=new Request(URL_BASE,{method:'POST',headers:{Authorization:'Bearer '+TOKEN,'Content-Type':'application/json'},body:'{"provider":"deepseek","problem_id":8}'}),response=await community.fetch(req,f.env,{});
    assert.equal(response.status,status);assert.equal(req.bodyUsed,false);assert.equal(f.sql.length,1);assert.doesNotMatch(await response.text(),/provider_required|problem_id|monthly/);
  }
});

test('actual community route reports a missing Gemini key and never creates a monthly submission or calls a provider',async()=>{
  const original=globalThis.fetch;let calls=0;globalThis.fetch=async()=>{calls++;assert.fail('provider must not be called without its key');};
  try{const f=liveFixture(ADMIN,{configured:false}),response=await community.fetch(request(photo(),{headers:{Authorization:'Bearer '+TOKEN}}),f.env,{});assert.equal(response.status,503);assert.deepEqual(await response.json(),{error:'ocr_unavailable'});assert.equal(calls,0);assert.equal(f.sql.length,1);}
  finally{globalThis.fetch=original;}
});

test('real bank adapter, actual community dispatch and the Gemini transcriber share the image-only contract',async()=>{
  const original=globalThis.fetch,timeout=AbortSignal.timeout;let providerCalls=0;const deadlines=[],upstream=[];
  AbortSignal.timeout=ms=>{deadlines.push(ms);return timeout(ms);};
  globalThis.fetch=async(url,init)=>{providerCalls++;assert.match(String(url),/gemini-3\.1-flash-lite:generateContent/);return geminiReply(TEXT);};
  try{
    const f=liveFixture(),bankQueries=[],db={prepare(sql){bankQueries.push(sql);return{bind(){return{async all(){return{results:sql.includes('sqlite_master')?['bank_question_facets','bank_question_catalogue','bank_source_presentations'].map(name=>({name})):[]};}};}};}};
    const env={BANK_OCR_ENABLED:'1',BANK_SEARCH:db,BANK_REGISTRY:db,COMMUNITY:{async fetch(req){const url=new URL(req.url);upstream.push(url.pathname);if(url.pathname==='/api/me')return Response.json({user:ADMIN});assert.equal(url.pathname,PROBLEM_BANK_OCR_PATH);assert.equal(url.search,'?mode=math');return community.fetch(req,f.env,{});}}};
    const body=photo();body.set('kind','book');body.set('collection','physics');body.set('source',SID);body.set('lang','ko');
    const req=new Request('https://bank.test/api/problem-bank/identify?kind=book&collection=physics',{method:'POST',headers:{Authorization:'Bearer '+TOKEN},body}),response=await bank.fetch(req,env),out=await response.json();
    assert.equal(response.status,200,JSON.stringify(out));assert.equal(providerCalls,1);assert.deepEqual(upstream,['/api/me',PROBLEM_BANK_OCR_PATH]);assert.equal(out.recognized_text,TEXT);assert.equal(out.ocr_used,true);assert.equal(out.automatic_match_confirmed,false);assert.deepEqual(out.searched_languages,['ko','en']);assert.deepEqual(out.items,[]);
    assert.equal(f.sql.length,1);assert.ok(f.sql.every(query=>/FROM sessions s JOIN users u/.test(query)));assert.ok(bankQueries.every(query=>!/^\s*(?:INSERT|UPDATE|DELETE|CREATE|DROP)/.test(query)));assert.ok(deadlines.includes(80000));assert.match(response.headers.get('Cache-Control'),/private.*no-store/);assert.doesNotMatch(JSON.stringify(out),/provider_required|problem_id|photo_id|synthetic-test-provider-key/);
  }finally{globalThis.fetch=original;AbortSignal.timeout=timeout;}
});

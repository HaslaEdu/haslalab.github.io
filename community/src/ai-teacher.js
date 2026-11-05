// Standalone nonproduction teacher handler. Intentionally not wired into index.js.
// Official schemas checked 2026-11-05:
// https://developers.openai.com/api/docs/models/gpt-6.1-terra
// https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses
// https://api-docs.deepseek.com/api/create-chat-completion/
// Keys are used only from existing Worker bindings; no secret values are returned.

export const TEACHER_MODELS=Object.freeze({deepseek:'deepseek-v4-pro',openai:'gpt-6.1-terra'});
// Operational spend/memory ceilings only: no desired teacher-answer length.
export const TEACHER_LIMITS=Object.freeze({outputTokens:32768,requestBytes:1024,providerRequestBytes:12288,responseBytes:524288,timeoutMs:120000});
const URLS=Object.freeze({deepseek:'https://api.deepseek.com/chat/completions',openai:'https://api.openai.com/v1/responses'});
const KEY_NAMES=Object.freeze({deepseek:'DEEPSEEK_API_KEY',openai:'OPENAI_API_KEY'});
const TASKS=Object.freeze({heat_exchange_review:{kind:'heat',N:2,review:true},heat_exchange_n2:{kind:'heat',N:2,review:false},heat_exchange_n10000:{kind:'heat',N:10000,review:false},
  math_integral:{kind:'integral'},physics_mechanics:{kind:'mechanics'}});
const encoder=new TextEncoder(),replays=new Map();
const exact=(value,keys)=>value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join('|')===[...keys].sort().join('|');
const integer=value=>Number.isSafeInteger(value)&&value>=0&&value<=1000000;
const english=value=>typeof value==='string'&&value.trim()&&value.length<=64000&&
  ![...value].some(char=>/\p{Letter}/u.test(char)&&!/[\p{Script=Latin}\p{Script=Greek}\p{Math}]/u.test(char))&&
  !/<\|[^\n]*?\|>|<\/?think>|```/i.test(value);
class TeacherError extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
function check(value,status,code){if(!value)throw new TeacherError(status,code);}
function json(value,status=200){return new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});}
export async function teacherDigest(value){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',typeof value==='string'?encoder.encode(value):value))].map(v=>v.toString(16).padStart(2,'0')).join('');}
export function teacherCanonical(value){const sorted=v=>Array.isArray(v)?v.map(sorted):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(key=>[key,sorted(v[key])])):v;return JSON.stringify(sorted(value));}
function equalDigest(a,b){if(!/^[a-f0-9]{64}$/.test(a||'')||!/^[a-f0-9]{64}$/.test(b||''))return false;let mismatch=0;for(let i=0;i<64;i++)mismatch|=a.charCodeAt(i)^b.charCodeAt(i);return mismatch===0;}
async function boundedText(response,maximum){
  const length=response.headers.get('Content-Length');
  check(length===null||/^\d+$/.test(length)&&Number(length)<=maximum,502,'teacher_response_too_large');
  check(response.body,502,'teacher_invalid_response');
  const reader=response.body.getReader(),chunks=[];let size=0;
  try{for(;;){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;
      if(size>maximum){try{await reader.cancel();}catch{}throw new TeacherError(502,'teacher_response_too_large');}chunks.push(value);}}
  finally{reader.releaseLock();}
  const bytes=new Uint8Array(size);let offset=0;for(const value of chunks){bytes.set(value,offset);offset+=value.byteLength;}
  try{return new TextDecoder('utf-8',{fatal:true}).decode(bytes);}catch{throw new TeacherError(502,'teacher_invalid_response');}
}
const schemaObject=properties=>({type:'object',properties,required:Object.keys(properties),additionalProperties:false});
export function teacherOutputSchema(task){
  check(Object.hasOwn(TASKS,task),400,'teacher_task_not_allowed');
  const base={version:{type:'integer',const:1},task:{type:'string',const:task},
    core:schemaObject({version:{type:'integer',const:1},domain:{type:'string',const:'haslalab'},task:{type:'string',const:'solve'},status:{type:'string',const:'ok'},
      blocks:{type:'array',minItems:3,maxItems:12,items:schemaObject({id:{type:'string'},kind:{type:'string',enum:['reasoning','result','criticism']},text:{type:'string'}})},
      assessment:{type:'null'},checks:{type:'array',items:{type:'string'},maxItems:0}}),
    assumptions:{type:'array',minItems:1,maxItems:12,items:{type:'string'}},
    verdict:{type:'string',enum:['valid_with_stated_assumptions','needs_correction']},
    corrections:{type:'array',maxItems:8,items:{type:'string'}}};
  if(TASKS[task].kind==='heat')Object.assign(base,{recurrence_latex:{type:'string'},residual_latex:{type:'string'},
    numeric:schemaObject({N:{type:'integer',const:TASKS[task].N},mean_hot_celsius:{type:'number'},mean_cold_celsius:{type:'number'},finite_exact:{type:'boolean',const:false}})});
  else Object.assign(base,{derivation_latex:{type:'string'},numeric:TASKS[task].kind==='integral'?
    schemaObject({value:{type:'number'},units:{type:'string',const:'dimensionless'}}):
    schemaObject({final_velocity_m_s:{type:'number'},displacement_m:{type:'number'},units:{type:'string',const:'SI'}})});
  return schemaObject(base);
}
function policy(task){
  return 'You are an independent physics teacher. Return only one JSON object matching this schema: '+JSON.stringify(teacherOutputSchema(task))+'. '+
    'Write all generated prose in English. Give a complete public worked proof with checkable equations, not private internal reasoning or thinking-channel text. Use the detail needed for correctness; no desired answer length is specified. '+
    'Each core block starts with @COND, @DERIVE or @ANS; include all three tags. Put every mathematical expression inside LaTeX $...$ delimiters. '+
    'Use reasoning, result or criticism block kinds. Separate physical assumptions, the allowed construction, exact finite statements and asymptotic statements. '+
    (TASKS[task].kind==='heat'?'If independently valid, normalize recurrence_latex to $x_{i,j}=(x_{i-1,j}+x_{i,j-1})/2$ and residual_latex to $r_N=\\binom{2N}{N}/4^N$; otherwise report needs_correction. Explain boundaries and verify these formulas in the public core. ':'State the governing mathematics, exact result and units in the public core and derivation_latex. ')+
    'Use kelvin in entropy logarithms. Do not fabricate sources, official rubrics, experimental results, or code/tool execution. '+
    'The client will independently verify the mathematics; producing JSON is not proof of correctness.';
}
function problem(task){
  if(TASKS[task].kind==='integral')return 'Evaluate the real definite integral of x squared from x=0 to x=2. The variable and integral are dimensionless. Provide a complete checkable public worked proof, an exact symbolic answer in the core, and the numerical value with units=dimensionless. Do not claim to have used a tool.';
  if(TASKS[task].kind==='mechanics')return 'A particle moves in one dimension with constant acceleration a=3 metres per second squared. At t=0 its position is x0=0 metres and its velocity is v0=2 metres per second. Find its velocity and displacement at t=4 seconds. State the governing equations, derive the results and check units. Use SI units and explain the constant-acceleration assumption. Do not claim to have used a tool.';
  const {N,review}=TASKS[task];
  return 'Water initially at 100 degrees Celsius and milk initially at 0 degrees Celsius have equal constant total heat capacities C. '+
    'Assume no phase changes, negligible vessel heat capacity, an insulated exterior, no external work, and no water-milk mass mixing. '+
    'Split each fluid into N equal-heat-capacity portions C/N. For each water portion H_i in increasing i, bring it to full equilibrium '+
    'successively with milk portions M_1 through M_N, preserving the current temperatures of previously used milk portions. '+
    'Keep all portions separate and insulated between contacts; recombine only within each fluid after all N squared contacts. '+
    (review?'Review this construction independently. Derive or correct its recurrence and closed form, assess whether temperature exchange is approached and whether this violates the second law. ':'Derive a concise public solution for this construction. ')+
    'Give the final mean water and milk temperatures for N='+N+' as numeric JSON values, the recurrence and residual factor in LaTeX, '+
    'and distinguish exact finite attainment from a limiting approach. Do not assume the final means must be equal just because undivided bodies equilibrate.';
}
export function validateTeacherOutput(value,task){
  const heat=TASKS[task]?.kind==='heat';
  check(Object.hasOwn(TASKS,task)&&exact(value,['version','task','core','assumptions','numeric','verdict','corrections',...(heat?['recurrence_latex','residual_latex']:['derivation_latex'])])&&value.version===1&&value.task===task,502,'teacher_invalid_final_schema');
  const core=value.core;
  check(exact(core,['version','domain','task','status','blocks','assessment','checks'])&&core.version===1&&core.domain==='haslalab'&&core.task==='solve'&&core.status==='ok'&&core.assessment===null&&Array.isArray(core.checks)&&!core.checks.length,502,'teacher_invalid_final_schema');
  check(Array.isArray(core.blocks)&&core.blocks.length>=3&&core.blocks.length<=12,502,'teacher_invalid_final_schema');
  const ids=new Set(),tags=new Set();
  for(const block of core.blocks){check(exact(block,['id','kind','text'])&&/^[A-Za-z0-9_-]{1,100}$/.test(block.id)&&!ids.has(block.id)&&['reasoning','result','criticism'].includes(block.kind)&&english(block.text),502,'teacher_invalid_public_core');
    ids.add(block.id);const tag=block.text.match(/^@(COND|DERIVE|ANS) /)?.[1];check(tag,502,'teacher_invalid_public_core');tags.add(tag);
    const plain=block.text.replace(/\$\$[\s\S]*?\$\$|\$[^$\n]+\$/g,'');
    check(!/[$\\=<>±≈≤≥∫∑√^]/.test(plain),502,'teacher_invalid_math_format');}
  check(tags.size===3,502,'teacher_invalid_public_core');
  check(Array.isArray(value.assumptions)&&value.assumptions.length>=1&&value.assumptions.length<=12&&value.assumptions.every(english)&&
    (heat?english(value.recurrence_latex)&&english(value.residual_latex):english(value.derivation_latex))&&Array.isArray(value.corrections)&&value.corrections.length<=8&&value.corrections.every(english),502,'teacher_invalid_final_schema');
  const number=v=>typeof v==='number'&&Number.isFinite(v)&&Math.abs(v)<=1000000;
  const numericOk=heat?exact(value.numeric,['N','mean_hot_celsius','mean_cold_celsius','finite_exact'])&&value.numeric.N===TASKS[task].N&&value.numeric.finite_exact===false&&[value.numeric.mean_hot_celsius,value.numeric.mean_cold_celsius].every(number):
    TASKS[task].kind==='integral'?exact(value.numeric,['value','units'])&&number(value.numeric.value)&&value.numeric.units==='dimensionless':
    exact(value.numeric,['final_velocity_m_s','displacement_m','units'])&&[value.numeric.final_velocity_m_s,value.numeric.displacement_m].every(number)&&value.numeric.units==='SI';
  check(numericOk&&['valid_with_stated_assumptions','needs_correction'].includes(value.verdict)&&JSON.stringify(value).length<=192000,502,'teacher_invalid_final_schema');
  // Structural/English validation only. The caller must verify temperatures and proof.
  return value;
}
function usageOf(provider,data){
  const usage=data?.usage||{},openai=provider==='openai';
  const input=openai?usage.input_tokens:usage.prompt_tokens,output=openai?usage.output_tokens:usage.completion_tokens;
  const cached=openai?usage.input_tokens_details?.cached_tokens:(usage.prompt_cache_hit_tokens??usage.prompt_tokens_details?.cached_tokens);
  const reasoning=openai?usage.output_tokens_details?.reasoning_tokens:usage.completion_tokens_details?.reasoning_tokens;
  return {known:integer(input)&&integer(output)&&output<=TEACHER_LIMITS.outputTokens,input_tokens:integer(input)?input:null,output_tokens:integer(output)?output:null,
    cached_input_tokens:integer(cached)&&integer(input)&&cached<=input?cached:null,
    reasoning_tokens:integer(reasoning)&&integer(output)&&reasoning<=output?reasoning:null,
    reported_total_tokens:integer(usage.total_tokens)?usage.total_tokens:null};
}
function providerCode(status){return status===401||status===403?'teacher_provider_auth':status===429?'teacher_provider_rate_limited':status===404?'teacher_model_unavailable':
  status>=300&&status<400?'teacher_redirect_rejected':[400,413,422].includes(status)?'teacher_request_rejected':'teacher_provider_failed';}
function safeId(value,secrets){return typeof value==='string'&&/^[A-Za-z0-9_.:-]{1,160}$/.test(value)&&!secrets.some(key=>value.includes(key))?value:null;}
async function callProvider(provider,task,env,options){
  const model=TEACHER_MODELS[provider],key=env[KEY_NAMES[provider]],secrets=Object.values(KEY_NAMES).map(name=>env[name]).filter(value=>typeof value==='string'&&value.length>=8);
  const result={provider,model,requested_model:model,reported_model:null,status:'failed',attempted:false,fixture:options.fixture,
    http_status:null,response_id:null,usage:null,finish_status:null,request_bytes:null,request_sha256:null,output_sha256:null,code:null};
  if(typeof key!=='string'||key.length<8||key.length>512){return {...result,status:'not_configured',code:'teacher_provider_unavailable'};}
  const controller=new AbortController(),timeoutMs=options.timeoutMs??TEACHER_LIMITS.timeoutMs;
  let timer;const started=options.clock();
  const execute=async()=>{
    const body=provider==='openai'?{model,store:false,stream:false,service_tier:'default',max_output_tokens:TEACHER_LIMITS.outputTokens,reasoning:{effort:'medium'},
      input:[{role:'developer',content:[{type:'input_text',text:policy(task)}]},{role:'user',content:[{type:'input_text',text:problem(task)}]}],
      text:{format:{type:'json_schema',name:'hasla_teacher_public_proof',strict:true,schema:teacherOutputSchema(task)}}}:
      {model,stream:false,max_tokens:TEACHER_LIMITS.outputTokens,thinking:{type:'disabled'},temperature:0,
       messages:[{role:'system',content:policy(task)},{role:'user',content:problem(task)}],response_format:{type:'json_object'}};
    const serialized=JSON.stringify(body);result.request_bytes=encoder.encode(serialized).byteLength;
    check(result.request_bytes<=TEACHER_LIMITS.providerRequestBytes,502,'teacher_request_size_limit');
    result.request_sha256=await teacherDigest(serialized);result.attempted=true;
    const response=await options.fetchImpl(URLS[provider],{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+key},body:serialized,redirect:'manual',signal:controller.signal});
    result.http_status=response.status;
    if(!response.ok){try{await response.body?.cancel();}catch{}throw new TeacherError(502,providerCode(response.status));}
    let data;try{data=JSON.parse(await boundedText(response,TEACHER_LIMITS.responseBytes));}catch(error){if(error instanceof TeacherError)throw error;throw new TeacherError(502,'teacher_invalid_response');}
    result.usage=usageOf(provider,data);
    check(result.usage.known,502,'teacher_usage_missing_or_invalid');
    check(typeof data.model==='string'&&(data.model===model||data.model.startsWith(model+'-'))&&/^[a-z0-9.-]{1,100}$/.test(data.model),502,'teacher_model_mismatch');
    result.reported_model=data.model;result.response_id=safeId(data.id,secrets);
    let final;
    if(provider==='openai'){
      check(data.status==='completed'&&Array.isArray(data.output),502,'teacher_incomplete_response');
      result.finish_status='completed';
      const messages=data.output.filter(item=>item?.type==='message'&&item.role==='assistant');
      check(messages.length>0&&!messages.some(item=>(item.content||[]).some(part=>part?.type==='refusal')),502,'teacher_missing_final');
      final=messages.flatMap(item=>item.content||[]).filter(part=>part?.type==='output_text'&&typeof part.text==='string').map(part=>part.text).join('');
    }else{
      const choice=data.choices?.[0];
      check(data.choices?.length===1&&choice.finish_reason==='stop'&&choice.message?.role==='assistant',502,'teacher_incomplete_response');
      result.finish_status='stop';
      final=choice.message.content; // reasoning_content is never read, saved or returned.
    }
    check(typeof final==='string'&&final.trim()&&final.length<=192000&&!secrets.some(secret=>final.includes(secret)),502,'teacher_invalid_final');
    let output;try{output=JSON.parse(final);}catch{throw new TeacherError(502,'teacher_invalid_final_json');}
    result.output=validateTeacherOutput(output,task);result.output_sha256=await teacherDigest(teacherCanonical(result.output));
    result.output_hash_format='canonical_json_utf8_sorted_keys_v1';result.status='ok';result.code=null;
  };
  try{await Promise.race([execute(),new Promise((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(new TeacherError(504,'teacher_timeout'));},timeoutMs);})]);}
  catch(error){result.code=error instanceof TeacherError?error.code:'teacher_transport_failed';delete result.output;result.status='failed';}
  finally{clearTimeout(timer);}
  return {...result,elapsed_ms:Math.max(0,options.clock()-started)};
}
function expiryMillis(value){if(typeof value==='number'&&Number.isFinite(value))return value<1e12?value*1000:value;if(typeof value!=='string')return NaN;
  return /^\d{10,13}$/.test(value)?expiryMillis(Number(value)):Date.parse(value);}

export async function handleTeacherRequest(request,env,expectedTokenDigest,options={}){
  try{
    check(new URL(request.url).pathname==='/__hasla_teacher',404,'teacher_not_found');
    check(request.method==='POST',405,'teacher_method_not_allowed');
    const clock=options.clock??Date.now,now=clock(),expiry=expiryMillis(env.HASLA_TEACHER_EXPIRES_AT);
    check(Number.isFinite(now)&&Number.isFinite(expiry)&&now<expiry&&expiry<=now+15*60*1000,403,'teacher_window_invalid');
    const token=request.headers.get('Authorization')?.match(/^Bearer ([A-Za-z0-9_-]{32,128})$/)?.[1];
    check(token&&equalDigest(await teacherDigest(token),expectedTokenDigest),401,'teacher_unauthorized');
    check(request.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase()==='application/json',400,'teacher_json_required');
    const raw=await boundedText(request,TEACHER_LIMITS.requestBytes);
    check(equalDigest(await teacherDigest(raw),env.HASLA_TEACHER_REQUEST_SHA256),403,'teacher_request_binding_failed');
    let body;try{body=JSON.parse(raw);}catch{throw new TeacherError(400,'teacher_invalid_request');}
    check(exact(body,['task','nonce'])&&Object.hasOwn(TASKS,body.task)&&/^[a-f0-9]{32,64}$/.test(body.nonce),400,'teacher_task_not_allowed');
    const timeoutMs=options.timeoutMs??TEACHER_LIMITS.timeoutMs;
    check(Number.isInteger(timeoutMs)&&timeoutMs>=1&&timeoutMs<=180000,500,'teacher_timeout_config_invalid');
    const fixture=Object.hasOwn(options,'fetchImpl');
    const replayKey=expectedTokenDigest+':'+env.HASLA_TEACHER_REQUEST_SHA256+':'+body.nonce+':'+fixture;
    // This collapses concurrent/repeated calls in one isolate. The short-lived
    // controller sends exactly one request and never retries; this is not a
    // claim of global exactly-once execution across separate Worker isolates.
    if(!replays.has(replayKey)){
      if(replays.size>=8)replays.delete(replays.keys().next().value);
      const promise=Promise.all(['deepseek','openai'].map(provider=>callProvider(provider,body.task,env,
        {fetchImpl:options.fetchImpl??globalThis.fetch,clock,timeoutMs,fixture}))).then(async results=>{
          const successes=results.filter(item=>item.status==='ok').length;
          return {version:1,task:body.task,nonce:body.nonce,fixture,question:problem(body.task),question_sha256:await teacherDigest(problem(body.task)),
            status:successes===2?'complete':successes===1?'partial':'failed',
            both_providers_used:successes===2,results,mathematics_verified:false,admitted_to_training:false};});
      replays.set(replayKey,promise);
    }
    const result=await replays.get(replayKey);
    return json(result,result.status==='complete'?200:result.status==='partial'?207:502);
  }catch(error){return json({error:error instanceof TeacherError?error.code:'teacher_request_failed'},error instanceof TeacherError?error.status:500);}
}

export default {fetch(request,env){return handleTeacherRequest(request,env,env.HASLA_TEACHER_AUTH_SHA256);}};

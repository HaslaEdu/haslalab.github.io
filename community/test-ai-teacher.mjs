import assert from 'node:assert/strict';
import {test} from 'node:test';
import {handleTeacherRequest,teacherDigest,teacherCanonical,teacherOutputSchema,TEACHER_LIMITS} from './src/ai-teacher.js';

let serial=0;
const token='fixture_teacher_auth_token_abcdefghijklmnopqrstuvwxyz';
function output(task='heat_exchange_review'){
  if(task==='math_integral'||task==='physics_mechanics')return {version:1,task,core:{version:1,domain:'haslalab',task:'solve',status:'ok',assessment:null,checks:[],blocks:[
    {id:'conditions',kind:'reasoning',text:task==='math_integral'?'@COND Integrate the stated real polynomial over the closed interval.':'@COND One-dimensional motion has constant acceleration and the stated SI initial conditions.'},
    {id:'derivation',kind:'reasoning',text:task==='math_integral'?'@DERIVE An antiderivative is $F(x)=x^3/3$, so evaluate $F(2)-F(0)$.':'@DERIVE Integrate acceleration to obtain $v=v_0+at$ and $x-x_0=v_0t+at^2/2$.'},
    {id:'answer',kind:'result',text:task==='math_integral'?'@ANS The dimensionless integral is $8/3$.':'@ANS The final velocity is $14\,\\mathrm{m/s}$ and displacement $32\,\\mathrm m$.'}]},
    assumptions:[task==='math_integral'?'Ordinary real integration.':'Constant acceleration in an inertial frame.'],derivation_latex:task==='math_integral'?'$[x^3/3]_0^2=8/3$':'$v=2+3(4)=14;\\quad x=2(4)+3(4)^2/2=32$',
    numeric:task==='math_integral'?{value:8/3,units:'dimensionless'}:{final_velocity_m_s:14,displacement_m:32,units:'SI'},verdict:'valid_with_stated_assumptions',corrections:[]};
  const N=task==='heat_exchange_n10000'?10000:2;
  return {version:1,task,core:{version:1,domain:'haslalab',task:'solve',status:'ok',assessment:null,checks:[],blocks:[
    {id:'conditions',kind:'reasoning',text:'@COND Equal constant heat capacities $C$; insulated fluids remain physically separate, with no phase changes or external work.'},
    {id:'derivation',kind:'reasoning',text:'@DERIVE Equilibrate equal-capacity portions in the specified order. Use $x_{ij}=(x_{i-1,j}+x_{i,j-1})/2$.'},
    {id:'answer',kind:'result',text:'@ANS The means are $100r_N$ and $100(1-r_N)$ degrees Celsius; finite error is positive and approaches zero in the limit.'}]},
    assumptions:['Equal constant total heat capacities','Insulated surroundings','No phase changes','No cross-fluid mass mixing','No external work'],
    recurrence_latex:'$x_{ij}=(x_{i-1,j}+x_{i,j-1})/2$',residual_latex:'$r_N=\\binom{2N}{N}/4^N$',
    numeric:{N,mean_hot_celsius:N===2?37.5:0.564182531222042,mean_cold_celsius:N===2?62.5:99.43581746877796,finite_exact:false},
    verdict:'valid_with_stated_assumptions',corrections:[]};
}
async function fixture({task='heat_exchange_review',extra={},envChanges={}}={}){
  const raw=JSON.stringify({task,nonce:(++serial).toString(16).padStart(32,'0'),...extra});
  const digest=await teacherDigest(token),env={OPENAI_API_KEY:'fixture_openai_secret_key',DEEPSEEK_API_KEY:'fixture_deepseek_secret_key',
    HASLA_TEACHER_AUTH_SHA256:digest,HASLA_TEACHER_EXPIRES_AT:String(Math.floor(Date.now()/1000)+300),HASLA_TEACHER_REQUEST_SHA256:await teacherDigest(raw),...envChanges};
  const request=()=>new Request('https://preview.invalid/__hasla_teacher',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:raw});
  return {raw,digest,env,request};
}
function response(provider,value=output()){
  return new Response(JSON.stringify(provider==='openai'?{id:'resp_fixture',model:'gpt-6.1-terra',status:'completed',usage:{input_tokens:900,output_tokens:500,total_tokens:1400,input_tokens_details:{cached_tokens:0},output_tokens_details:{reasoning_tokens:50}},
    output:[{type:'reasoning',summary:[{text:'PRIVATE_REASONING_MUST_NEVER_LEAVE'}]},{type:'message',role:'assistant',content:[{type:'output_text',text:JSON.stringify(value)}]}]}:
    {id:'deepseek_fixture',model:'deepseek-v4-pro',usage:{prompt_tokens:800,completion_tokens:450,total_tokens:1250,prompt_cache_hit_tokens:0},
      choices:[{finish_reason:'stop',message:{role:'assistant',content:JSON.stringify(value),reasoning_content:'PRIVATE_REASONING_MUST_NEVER_LEAVE'}}]}),{headers:{'Content-Type':'application/json'}});
}
test('one bounded fixed-model request per provider; only public final JSON and safe usage leave',async()=>{
  const f=await fixture(),calls=[];
  const result=await handleTeacherRequest(f.request(),f.env,f.digest,{fetchImpl:async(url,init)=>{
    calls.push({url,init,body:JSON.parse(init.body)});return response(url.includes('openai')?'openai':'deepseek');}});
  assert.equal(result.status,200);const value=await result.json();assert.equal(value.both_providers_used,true);assert.equal(calls.length,2);
  assert.deepEqual(new Set(calls.map(call=>call.url)),new Set(['https://api.openai.com/v1/responses','https://api.deepseek.com/chat/completions']));
  for(const call of calls){assert.equal(call.init.redirect,'manual');assert.ok(call.init.signal);assert.equal(call.body.max_output_tokens??call.body.max_tokens,32768);}
  assert.equal(calls.find(call=>call.url.includes('openai')).body.store,false);
  assert.equal(calls.find(call=>call.url.includes('openai')).body.service_tier,'default');
  assert.equal(calls.find(call=>call.url.includes('deepseek')).body.thinking.type,'disabled');
  assert.equal(value.results.every(item=>item.usage.known&&item.status==='ok'),true);
  assert.equal(value.fixture,true);assert.ok(value.results.every(item=>item.fixture));
  assert.ok(value.question.includes('N=2'));assert.equal(value.question_sha256,await teacherDigest(value.question));
  for(const item of value.results){assert.equal(item.output_sha256,await teacherDigest(teacherCanonical(item.output)));
    assert.match(item.request_sha256,/^[a-f0-9]{64}$/);assert.ok(item.request_bytes<=12288);assert.equal(item.model,item.requested_model);}
  assert.equal(value.results.find(item=>item.provider==='openai').finish_status,'completed');
  assert.equal(value.results.find(item=>item.provider==='deepseek').finish_status,'stop');
  const rendered=JSON.stringify(value);assert.ok(!rendered.includes('PRIVATE_REASONING'));assert.ok(!rendered.includes('fixture_openai_secret_key'));assert.ok(!rendered.includes('fixture_deepseek_secret_key'));
  assert.equal(value.mathematics_verified,false);assert.equal(value.admitted_to_training,false);
});
test('fixed tasks include numeric cases and schema forbids arbitrary fields',async()=>{
  for(const task of ['heat_exchange_n2','heat_exchange_n10000']){
    const f=await fixture({task}),r=await handleTeacherRequest(f.request(),f.env,f.digest,{fetchImpl:async url=>response(url.includes('openai')?'openai':'deepseek',output(task))});
    assert.equal(r.status,200);assert.equal((await r.json()).results[0].output.numeric.N,task==='heat_exchange_n2'?2:10000);
  }
  const f=await fixture({extra:{messages:[{role:'user',content:'arbitrary proxy prompt'}]}});
  const r=await handleTeacherRequest(f.request(),f.env,f.digest,{fetchImpl:async()=>{throw new Error('must not call');}});assert.equal(r.status,400);
  assert.equal(teacherOutputSchema('heat_exchange_review').additionalProperties,false);
});
test('math and mechanics use identical questions for both teachers without a target answer length',async()=>{
  for(const task of ['math_integral','physics_mechanics']){
    const f=await fixture({task}),calls=[];const r=await handleTeacherRequest(f.request(),f.env,f.digest,{fetchImpl:async(url,init)=>{
      const body=JSON.parse(init.body);calls.push(body);return response(url.includes('openai')?'openai':'deepseek',output(task));}});
    assert.equal(r.status,200);const result=await r.json();assert.equal(result.both_providers_used,true);assert.equal(calls.length,2);
    const openai=calls.find(value=>value.model==='gpt-6.1-terra'),deepseek=calls.find(value=>value.model==='deepseek-v4-pro');
    assert.equal(openai.input[1].content[0].text,deepseek.messages[1].content);assert.equal(result.question,deepseek.messages[1].content);
    assert.ok(deepseek.messages[0].content.includes('no desired answer length is specified'));
    assert.deepEqual(result.results[0].output.numeric,task==='math_integral'?{value:8/3,units:'dimensionless'}:{final_velocity_m_s:14,displacement_m:32,units:'SI'});
  }
});
test('auth, request digest and expiry fail before any provider call',async()=>{
  for(const kind of ['auth','request','expired','future']){
    const f=await fixture();if(kind==='request')f.env.HASLA_TEACHER_REQUEST_SHA256='0'.repeat(64);
    if(kind==='expired')f.env.HASLA_TEACHER_EXPIRES_AT=String(Math.floor(Date.now()/1000)-1);
    if(kind==='future')f.env.HASLA_TEACHER_EXPIRES_AT=String(Math.floor(Date.now()/1000)+3600);
    let calls=0;const r=await handleTeacherRequest(f.request(),f.env,kind==='auth'?'0'.repeat(64):f.digest,{fetchImpl:async()=>{calls++;throw new Error('forbidden');}});
    assert.ok(r.status>=400);assert.equal(calls,0);
  }
});
test('one failed provider never claims both succeeded or exposes raw upstream errors',async()=>{
  const f=await fixture(),r=await handleTeacherRequest(f.request(),f.env,f.digest,{fetchImpl:async url=>url.includes('deepseek')?
    new Response('raw error: fixture_deepseek_secret_key PRIVATE_REASONING',{status:401}):response('openai')});
  assert.equal(r.status,207);const result=await r.json();assert.equal(result.both_providers_used,false);assert.equal(result.status,'partial');
  assert.equal(result.results[0].code,'teacher_provider_auth');assert.equal(result.results[1].status,'ok');
  assert.ok(!JSON.stringify(result).includes('raw error'));assert.ok(!JSON.stringify(result).includes('fixture_deepseek_secret_key'));
});
test('non-English, invalid JSON and reasoning-only responses are not accepted',async()=>{
  for(const kind of ['language','json','reasoning']){
    const f=await fixture();const r=await handleTeacherRequest(f.request(),f.env,f.digest,{fetchImpl:async url=>{
      if(url.includes('openai'))return response('openai');const bad=output();
      if(kind==='language')bad.core.blocks[0].text+=' 한국어';
      if(kind==='json')return new Response(JSON.stringify({model:'deepseek-v4-pro',usage:{prompt_tokens:1,completion_tokens:2},choices:[{finish_reason:'stop',message:{role:'assistant',content:'not JSON'}}]}));
      if(kind==='reasoning')return new Response(JSON.stringify({model:'deepseek-v4-pro',usage:{prompt_tokens:1,completion_tokens:2},choices:[{finish_reason:'stop',message:{role:'assistant',content:'',reasoning_content:'PRIVATE'}}]}));
      return response('deepseek',bad);}});
    const result=await r.json();assert.equal(result.both_providers_used,false);assert.equal(result.results[0].status,'failed');assert.ok(!JSON.stringify(result).includes('PRIVATE'));
  }
});
test('redirects and oversized bodies fail closed with no fallback models or retry',async()=>{
  for(const kind of ['redirect','oversize']){
    const f=await fixture();let calls=0;const r=await handleTeacherRequest(f.request(),f.env,f.digest,{fetchImpl:async url=>{
      calls++;if(url.includes('openai'))return response('openai');return kind==='redirect'?new Response('secret',{status:302,headers:{Location:'https://evil.invalid'}}):new Response('x'.repeat(TEACHER_LIMITS.responseBytes+1));}});
    const result=await r.json();assert.equal(calls,2);assert.equal(result.both_providers_used,false);assert.equal(result.results[0].code,kind==='redirect'?'teacher_redirect_rejected':'teacher_response_too_large');
  }
});
test('timeouts are bounded even if a mock ignores AbortSignal',async()=>{
  const f=await fixture();let calls=0;const r=await handleTeacherRequest(f.request(),f.env,f.digest,{timeoutMs:10,fetchImpl:async()=>{calls++;return await new Promise(()=>{});}});
  assert.equal(calls,2);assert.equal(r.status,502);assert.ok((await r.json()).results.every(item=>item.code==='teacher_timeout'));
});
test('a repeated exact nonce is collapsed in one isolate without extra calls',async()=>{
  const f=await fixture();let calls=0;const options={fetchImpl:async url=>{calls++;return response(url.includes('openai')?'openai':'deepseek');}};
  const first=await handleTeacherRequest(f.request(),f.env,f.digest,options),second=await handleTeacherRequest(f.request(),f.env,f.digest,options);
  assert.deepEqual(await first.json(),await second.json());assert.equal(calls,2);
});
test('keys in an unexpected final output are rejected and not reflected',async()=>{
  const f=await fixture(),bad=output();bad.corrections=['fixture_deepseek_secret_key'];
  const r=await handleTeacherRequest(f.request(),f.env,f.digest,{fetchImpl:async url=>response(url.includes('openai')?'openai':'deepseek',bad)});
  const value=await r.json();assert.equal(value.both_providers_used,false);assert.ok(!JSON.stringify(value).includes('fixture_deepseek_secret_key'));
});

// Offline only: generated RSA, synthetic quota resources, no credentials or provider calls.
import test from 'node:test';
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { handle,PROJECT_NUMBER,SERVICES,METRIC,PREFERENCE_ID,JUSTIFICATION } from './gcp_training_prerequisites_worker.mjs';

const NOW=Date.parse('2026-11-05T00:00:00Z'),BEARER='p'.repeat(64),OAUTH='ya29.SYNTHETIC_TOKEN';
const PRIVATE='PRIVATE_UPSTREAM_TEXT',EMAIL='offline-fixture@example.invalid';
const USAGE='https://serviceusage.googleapis.com/v1/projects/'+PROJECT_NUMBER;
const PARENT='projects/'+PROJECT_NUMBER+'/locations/global';
const BASE='https://cloudquotas.googleapis.com/v1/'+PARENT;
const QUOTA_ID='OpaqueA10080QuotaId';
const PREF_NAME=PARENT+'/quotaPreferences/'+PREFERENCE_ID;
const json=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
let fixturePromise;
async function fixture(){if(!fixturePromise)fixturePromise=(async()=>{
  const pair=await webcrypto.subtle.generateKey({name:'RSASSA-PKCS1-v1_5',modulusLength:2048,publicExponent:Uint8Array.of(1,0,1),hash:'SHA-256'},true,['sign','verify']);
  const der=await webcrypto.subtle.exportKey('pkcs8',pair.privateKey);
  const pem='-----BEGIN PRIVATE KEY-----\n'+Buffer.from(der).toString('base64').match(/.{1,64}/g).join('\n')+'\n-----END PRIVATE KEY-----\n';
  return {GCP_PROJECT:'project-hasla',GCP_TUNING_BUCKET:'hasla-training',GCP_SA_KEY:JSON.stringify({type:'service_account',project_id:'project-hasla',
    client_email:'offline-fixture@project-hasla.iam.gserviceaccount.com',private_key:pem,token_uri:'https://oauth2.googleapis.com/token'}),
    GCP_PREREQ_AUTH_SHA256:Buffer.from(await webcrypto.subtle.digest('SHA-256',new TextEncoder().encode(BEARER))).toString('hex'),
    GCP_PREREQ_EXPIRES_AT:'2026-11-05T00:45:00Z',GCP_PREREQ_CONTACT_EMAIL:EMAIL};
})();return fixturePromise;}
const request=(path='/status',method='GET',body,auth=true)=>new Request('https://isolated.invalid'+path,{method,
  headers:auth?{Authorization:'Bearer '+BEARER}:{},...(body===undefined?{}:{body})});
const info=(changes={})=>({name:PARENT+'/services/aiplatform.googleapis.com/quotaInfos/'+QUOTA_ID,service:'aiplatform.googleapis.com',
  metric:METRIC,quotaId:QUOTA_ID,dimensions:['region'],dimensionsInfos:[{dimensions:{region:'us-central1'},details:{value:'0'}}],...changes});
const preference=(changes={})=>({name:PREF_NAME,service:'aiplatform.googleapis.com',quotaId:QUOTA_ID,dimensions:{region:'us-central1'},
  quotaConfig:{preferredValue:'1'},reconciling:true,...changes});
function provider(options={}){
  const calls=[];let stored=options.existing;
  const fetchImpl=async(url,init={})=>{
    url=String(url);calls.push({url,...init});const u=new URL(url);
    assert.equal(init.redirect,'manual');assert.ok(init.signal instanceof AbortSignal);
    if(url==='https://oauth2.googleapis.com/token')return options.oauth?options.oauth():json({access_token:OAUTH,token_type:'Bearer'});
    assert.equal(init.headers.Authorization,'Bearer '+OAUTH);
    if(url===USAGE+'/services:batchEnable'){
      assert.equal(init.method,'POST');assert.deepEqual(JSON.parse(init.body),{serviceIds:SERVICES});
      if(options.lostEnable)throw new Error(PRIVATE);
      return options.enable?options.enable():json({name:'operations/acf.p2-315617551669-offline',done:false,metadata:{secret:PRIVATE}});
    }
    if(SERVICES.some(service=>url===USAGE+'/services/'+service+'?fields=name,state')){
      assert.equal(init.method,'GET');assert.equal(init.body,undefined);
      return options.service?options.service(url):json({name:'projects/'+PROJECT_NUMBER+'/services/'+u.pathname.split('/').at(-1),state:'ENABLED',config:{secret:PRIVATE}});
    }
    if(u.pathname==='/v1/'+PARENT+'/services/aiplatform.googleapis.com/quotaInfos'){
      assert.equal(init.method,'GET');assert.equal(init.body,undefined);assert.equal(u.searchParams.get('pageSize'),'100');
      assert.ok(u.searchParams.get('fields').includes('quotaInfos(name,quotaId,metric,service,dimensions,'));
      return options.quotas?options.quotas(u):json({quotaInfos:[info(),info({metric:'aiplatform.googleapis.com/prediction_nvidia_a100_80gb_gpus',quotaId:PRIVATE})]});
    }
    if(url===BASE+'/quotaPreferences/'+PREFERENCE_ID){
      assert.equal(init.method,'GET');return options.preferenceRead?options.preferenceRead():stored?json(stored):json({error:{message:PRIVATE}},404);
    }
    if(u.pathname==='/v1/'+PARENT+'/quotaPreferences'){
      assert.equal(init.method,'POST');assert.deepEqual([...u.searchParams.keys()],['quotaPreferenceId']);assert.equal(u.searchParams.get('quotaPreferenceId'),PREFERENCE_ID);
      const body=JSON.parse(init.body);assert.deepEqual(Object.keys(body).sort(),['service','quotaId','dimensions','quotaConfig','justification','contactEmail'].sort());
      assert.equal(body.contactEmail,EMAIL);stored=preference();
      if(options.lostCreate)throw new Error(PRIVATE);
      return options.create?options.create(body):json(stored);
    }
    throw new Error('Unexpected offline endpoint '+url);
  };
  return {calls,fetchImpl,options};
}
async function harness(options={},changes={}){
  const env={...await fixture(),...changes},mock=provider(options);
  const call=async(path='/status',method='GET',body)=>{
    const response=await handle(typeof path==='string'?request(path,method,body):path,env,{fetchImpl:mock.fetchImpl,cryptoImpl:webcrypto,now:NOW});
    const data=await response.json(),raw=JSON.stringify(data);
    assert.equal(raw.includes(PRIVATE),false);assert.equal(raw.includes(EMAIL),false);assert.equal(raw.includes(OAUTH),false);
    assert.equal(raw.includes('private_key'),false);assert.equal(raw.includes('client_email'),false);
    assert.equal(data.gpu_creation_attempted,false);assert.equal(response.headers.get('Cache-Control'),'no-store');
    return {response,data};
  };return {...mock,env,call};
}
const writes=h=>h.calls.filter(call=>call.method==='POST'&&call.url!=='https://oauth2.googleapis.com/token');

test('enable route performs one fixed batch mutation and never polls, applies quota or creates GPU',async()=>{
  const h=await harness(),result=await h.call('/enable-apis','POST','{}');assert.equal(result.response.status,200);
  assert.equal(result.data.status,'enable_request_submitted');assert.equal(result.data.operation_done,false);assert.equal(result.data.write_api_calls,1);
  assert.equal(result.data.automatic_retry,false);assert.equal(writes(h).length,1);assert.equal(h.calls.length,2);
  assert.equal(writes(h)[0].url,USAGE+'/services:batchEnable');
});

test('status contains only fixed service states and exact-case-insensitive training A10080 quotas',async()=>{
  const h=await harness({quotas:()=>json({quotaInfos:[info({metric:METRIC.replace('80gb','80GB')}),
    info({service:'compute.googleapis.com'}),info({metric:METRIC+'_extra'}),info({metric:'aiplatform.googleapis.com/prediction_nvidia_a100_80gb_gpus'})]})});
  const result=await h.call();assert.equal(result.response.status,200);assert.equal(writes(h).length,0);assert.equal(result.data.write_api_calls,0);
  assert.deepEqual(result.data.quota.quotas,[{quota_id:QUOTA_ID,region:'us-central1',limit:0}]);assert.equal(result.data.quota.complete,true);
  assert.deepEqual(result.data.services.map(item=>item.state),['ENABLED','ENABLED']);assert.equal(h.calls.length,4);
});

test('quota request discovers opaque ID, checks fixed preference404 and creates desired1 with env-only contact',async()=>{
  const h=await harness(),result=await h.call('/request-quota','POST');assert.equal(result.response.status,200);
  assert.equal(result.data.status,'quota_preference_submitted');assert.equal(result.data.preferred_value,1);assert.equal(result.data.contact_included,true);
  assert.equal(result.data.contact_verified,false);assert.equal(result.data.reconciling,true);assert.equal(writes(h).length,1);
  const body=JSON.parse(writes(h)[0].body);assert.deepEqual(body.dimensions,{region:'us-central1'});assert.deepEqual(body.quotaConfig,{preferredValue:'1'});
  assert.equal(body.service,'aiplatform.googleapis.com');assert.equal(body.quotaId,QUOTA_ID);assert.equal(body.justification,JUSTIFICATION);
  assert.equal(writes(h)[0].url,BASE+'/quotaPreferences?quotaPreferenceId='+PREFERENCE_ID);
});

test('existing matching preference is reported with contact unverified and no retry/update',async()=>{
  const h=await harness({existing:preference()}),result=await h.call('/request-quota','POST','{}');
  assert.equal(result.data.status,'existing_matching_preference_contact_unverifiable');assert.equal(result.data.contact_verified,false);
  assert.equal(result.data.write_api_calls,0);assert.equal(writes(h).length,0);
});

test('existing wrong service, quota, dimensions, value or owner blocks all mutation',async()=>{
  for(const change of [{service:'compute.googleapis.com'},{quotaId:'other'},{name:'projects/999/locations/global/quotaPreferences/'+PREFERENCE_ID},
    {dimensions:{region:'us-east4'}},{dimensions:{region:'us-central1',gpu:'other'}},{quotaConfig:{preferredValue:'2'}}]){
    const h=await harness({existing:preference(change)}),result=await h.call('/request-quota','POST');
    assert.equal(result.data.reason,'existing_preference_mismatch');assert.equal(writes(h).length,0);
  }
});

test('403 on discovery or preference read stops with safe permission reason and no mutation',async()=>{
  for(const options of [{quotas:()=>json({error:{message:PRIVATE}},403)},{preferenceRead:()=>json({error:{message:PRIVATE}},403)}]){
    const h=await harness(options),result=await h.call('/request-quota','POST');assert.equal(result.response.status,403);
    assert.equal(result.data.reason,'PERMISSION_DENIED');assert.equal(writes(h).length,0);
  }
});

test('missing, ambiguous, wrong owner or nonmatching metric never supplies a guessed quota ID',async()=>{
  for(const entries of [[],[info({metric:METRIC+'_wrong'})],[info({name:'projects/999/locations/global/services/aiplatform.googleapis.com/quotaInfos/'+QUOTA_ID})],
    [info(),info({quotaId:'OtherId',name:PARENT+'/services/aiplatform.googleapis.com/quotaInfos/OtherId'})]]){
    const h=await harness({quotas:()=>json({quotaInfos:entries})}),result=await h.call('/request-quota','POST');
    assert.equal(result.data.reason,'quota_identity_unconfirmed');assert.equal(writes(h).length,0);
  }
});

test('already sufficient and unlimited quotas cause no preference read or mutation',async()=>{
  for(const value of ['1','2','-1']){
    const h=await harness({quotas:()=>json({quotaInfos:[info({dimensionsInfos:[{dimensions:{region:'us-central1'},details:{value}}]})]})});
    assert.equal((await h.call('/request-quota','POST')).data.status,'quota_already_sufficient');assert.equal(writes(h).length,0);
    assert.equal(h.calls.some(call=>call.url.includes('/quotaPreferences')),false);
  }
});

test('dimension schema and unknown regional limit fail closed; proto3 empty details is verified zero',async()=>{
  for(const entry of [info({dimensions:['region','user']}),info({dimensionsInfos:[{dimensions:{region:'us-central1'}}]}),
    info({dimensionsInfos:[{dimensions:{region:'us-east4'},details:{value:'0'}}]})]){
    const h=await harness({quotas:()=>json({quotaInfos:[entry]})}),result=await h.call('/request-quota','POST');
    assert.ok(result.response.status>=400);assert.equal(writes(h).length,0);
  }
  const h=await harness({quotas:()=>json({quotaInfos:[info({dimensionsInfos:[{dimensions:{region:'us-central1'},details:{}}]})]})});
  assert.equal((await h.call('/request-quota','POST')).data.status,'quota_preference_submitted');
});

test('invalid specific limit or oversized location list never falls back to a default zero',async()=>{
  for(const specific of [{dimensions:{region:'us-central1'},details:{value:PRIVATE}},
    {dimensions:{region:'us-central1'},details:{value:'0'},applicableLocations:Array(101).fill('us-central1')}]){
    const h=await harness({quotas:()=>json({quotaInfos:[info({dimensionsInfos:[{dimensions:{},details:{value:'0'}},specific]})]})});
    const result=await h.call('/request-quota','POST');assert.equal(result.data.reason,'quota_schema_invalid');assert.equal(writes(h).length,0);
  }
});

test('applicableLocations and default regional quota values remain numeric with explicit precedence',async()=>{
  const h=await harness({quotas:()=>json({quotaInfos:[info({dimensionsInfos:[{dimensions:{},details:{value:'0'},applicableLocations:['global']},
    {dimensions:{region:'us-central1'},details:{value:'1'}}]})]})});
  const status=await h.call();assert.deepEqual(status.data.quota.quotas,[{quota_id:QUOTA_ID,region:'global_default',limit:0},{quota_id:QUOTA_ID,region:'us-central1',limit:1}]);
  assert.equal((await h.call('/request-quota','POST')).data.status,'quota_already_sufficient');assert.equal(writes(h).length,0);
});

test('pagination is bounded at5, fixed-host and incomplete discovery prevents application',async()=>{
  let page=0;const h=await harness({quotas:()=>json({quotaInfos:[],nextPageToken:'opaque?url=https://attacker.invalid/'+(++page)})});
  const result=await h.call('/request-quota','POST');assert.equal(result.data.reason,'pagination_limit');assert.equal(writes(h).length,0);
  const lists=h.calls.filter(call=>call.url.includes('/quotaInfos?'));assert.equal(lists.length,5);
  assert.ok(lists.every(call=>new URL(call.url).origin==='https://cloudquotas.googleapis.com'));
  assert.equal(lists.some(call=>new URL(call.url).searchParams.has('url')),false);
});

test('repeated page tokens, excessive schemas and excessive output fail closed within bounds',async()=>{
  for(const options of [{quotas:()=>json({quotaInfos:[],nextPageToken:'same'})},{quotas:()=>json({quotaInfos:'invalid'})},
    {quotas:()=>json({quotaInfos:[info({dimensionsInfos:Array.from({length:200},()=>({dimensions:{region:'us-central1'},details:{value:'0'}}))})]})}]){
    const h=await harness(options),result=await h.call('/status');assert.equal(result.data.quota.complete,false);
    assert.ok(result.data.quota.quotas.length<=128);assert.ok(h.calls.length<=8);assert.equal(writes(h).length,0);
  }
});

test('projected quota list supports responses above256KiB and rejects above2MiB without mutation',async()=>{
  const h=await harness({quotas:()=>json({quotaInfos:[info()],unused:'x'.repeat(300000)})});
  assert.equal((await h.call('/status')).data.quota.complete,true);
  const oversized=await harness({quotas:()=>json({quotaInfos:[info()],unused:'x'.repeat(2*1024*1024)})});
  const result=await oversized.call('/request-quota','POST');assert.equal(result.data.reason,'malformed_or_oversized_response');assert.equal(writes(oversized).length,0);
});

test('lost quota creation response has exactly one attempt and later explicit request only observes existing fixedID',async()=>{
  const h=await harness({lostCreate:true}),first=await h.call('/request-quota','POST');
  assert.equal(first.data.status,'quota_request_outcome_unknown');assert.equal(first.data.write_api_calls,1);assert.equal(first.data.automatic_retry,false);
  assert.equal(writes(h).length,1);const second=await h.call('/request-quota','POST');
  assert.equal(second.data.status,'existing_matching_preference_contact_unverifiable');assert.equal(writes(h).length,1);
});

test('enable403, lost response and operation failure never retry or expose raw errors',async()=>{
  for(const [options,expected]of [[{enable:()=>json({error:{message:PRIVATE}},403)},'enable_request_rejected'],
    [{lostEnable:true},'enable_outcome_unknown'],[{enable:()=>json({name:'operations/x',done:true,error:{code:7,message:PRIVATE}})},'enable_operation_failed'],
    [{enable:()=>json({name:'operations/x',done:true,error:{code:'constructor',message:PRIVATE}})},'enable_operation_failed']]){
    const h=await harness(options),result=await h.call('/enable-apis','POST');assert.equal(result.data.status,expected);assert.equal(writes(h).length,1);
    assert.equal(result.data.automatic_retry,false);assert.equal(typeof result.data.reason,'string');
  }
});

test('quota403, server error and malformed success report one attempt without automatic retry',async()=>{
  for(const create of [()=>json({error:{message:PRIVATE}},403),()=>json({error:{message:PRIVATE}},503),()=>json({message:PRIVATE})]){
    const h=await harness({create}),result=await h.call('/request-quota','POST');assert.ok(result.response.status>=400);assert.equal(writes(h).length,1);
    assert.equal(result.data.automatic_retry,false);assert.equal(result.data.write_api_calls,1);
  }
});

test('guest, expiry, wrong method, arbitrary API route or query never reads SA/contact or calls upstream',async()=>{
  const env={...await fixture()};let reads=0,calls=0;
  for(const name of ['GCP_SA_KEY','GCP_PREREQ_CONTACT_EMAIL'])Object.defineProperty(env,name,{get(){reads++;throw new Error('must not read');}});
  for(const req of [request('/status','GET',undefined,false),request('/enable-apis','GET'),request('/enable-apis?project=other','POST'),
    request('/request-quota?quota=other','POST'),request('/grant-iam','POST'),request('/start','POST')]){
    assert.ok((await handle(req,env,{cryptoImpl:webcrypto,now:NOW,fetchImpl:()=>{calls++;}})).status>=400);
  }
  for(const expiry of ['2026-11-04T23:59:59Z','2026-11-05T02:00:00Z']){
    const expired=Object.create(env);expired.GCP_PREREQ_EXPIRES_AT=expiry;
    assert.equal((await handle(request('/request-quota','POST'),expired,{cryptoImpl:webcrypto,now:NOW,fetchImpl:()=>{calls++;}})).status,403);
  }
  assert.equal(reads,0);assert.equal(calls,0);
});

test('nonempty/oversized bodies are rejected before SA, contact or OAuth',async()=>{
  const env={...await fixture()};let reads=0,calls=0;Object.defineProperty(env,'GCP_SA_KEY',{get(){reads++;throw new Error('secret read');}});
  for(const body of [' ',JSON.stringify({serviceIds:['other']}),'x'.repeat(1000)]){
    const result=await handle(request('/enable-apis','POST',body),env,{cryptoImpl:webcrypto,now:NOW,fetchImpl:()=>{calls++;}});
    assert.equal((await result.json()).reason,'body_rejected');
  }assert.equal(reads,0);assert.equal(calls,0);
});

test('contact is required only for quota route, validated privately and never taken from request',async()=>{
  for(const email of [undefined,'invalid','a@example.invalid\nInjected: secret','x'.repeat(65)+'@example.invalid','bad..user@example.invalid','.user@example.invalid','user.@example.invalid']){
    const h=await harness({}, {GCP_PREREQ_CONTACT_EMAIL:email}),result=await h.call('/request-quota','POST');
    assert.equal(result.data.reason,'contact_email_invalid');assert.equal(h.calls.length,0);
  }
  const h=await harness();Object.defineProperty(h.env,'GCP_PREREQ_CONTACT_EMAIL',{get(){throw new Error('email must remain unread');}});
  assert.equal((await h.call('/status')).response.status,200);assert.equal((await h.call('/enable-apis','POST')).response.status,200);
});

test('project/bucket/key mismatches and OAuth errors cannot reach prerequisite writes',async()=>{
  for(const changes of [{GCP_PROJECT:'other'},{GCP_TUNING_BUCKET:'other'},{GCP_SA_KEY:'invalid'}]){
    const h=await harness({},changes),result=await h.call('/enable-apis','POST');assert.equal(result.data.reason,'configuration_invalid');assert.equal(h.calls.length,0);
  }
  const h=await harness({oauth:()=>json({error:'invalid_grant',error_description:PRIVATE},400)}),result=await h.call('/enable-apis','POST');
  assert.equal(result.data.reason,'invalid_grant');assert.equal(writes(h).length,0);assert.equal(h.calls.length,1);
});

test('unknown service state, redirects and upstream identity mismatch return safe enums only',async()=>{
  const h=await harness({service:url=>json({name:'projects/'+PROJECT_NUMBER+'/services/'+new URL(url).pathname.split('/').at(-1),state:PRIVATE}),
    quotas:()=>new Response(PRIVATE,{status:302,headers:{Location:'https://attacker.invalid'}})});
  const result=await h.call();assert.ok(result.data.services.every(item=>item.state==='STATE_UNSPECIFIED'));
  assert.equal(result.data.quota.reason,'redirect_rejected');assert.equal(result.data.quota.complete,false);assert.equal(writes(h).length,0);
});

test('unrelated inherited bindings are never accessed',async()=>{
  const h=await harness(),keys=new Set(Object.keys(h.env));const env=new Proxy(h.env,{get(target,key){assert.ok(keys.has(key));return target[key];}});
  assert.equal((await handle(request(),env,{cryptoImpl:webcrypto,now:NOW,fetchImpl:h.fetchImpl})).status,200);
});

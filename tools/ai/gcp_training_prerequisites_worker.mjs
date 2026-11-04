// Expiring, fixed GCP prerequisite actions. No GPU, IAM, billing, data, or generic proxy.
// https://docs.cloud.google.com/service-usage/docs/reference/rest/v1/services/batchEnable
// https://docs.cloud.google.com/docs/quotas/reference/rest/v1/projects.locations.quotaPreferences/create
import { PROJECT, authenticate, gcpConfiguration, gcpTokenFor, gcpRequestJson } from './gcp_preflight_worker.mjs';

export const PROJECT_NUMBER='315617551669';
export const SERVICES=Object.freeze(['cloudquotas.googleapis.com','cloudresourcemanager.googleapis.com']);
export const METRIC='aiplatform.googleapis.com/custom_model_training_nvidia_a100_80gb_gpus';
export const PREFERENCE_ID='hasla-gemma-a10080-us-central1-20261105';
export const JUSTIFICATION='One A10080 GPU for a single Gemma BF16LoRA style pilot; max1800sec, combined100000KRWcap; QwQseparateprovider';
const NEEDED_PERMISSIONS=Object.freeze(['serviceusage.services.enable','cloudquotas.quotas.get','cloudquotas.quotas.update','storage.buckets.get']);
const SERVICE='aiplatform.googleapis.com',REGION='us-central1',MAX_PAGES=5;
const USAGE='https://serviceusage.googleapis.com/v1/projects/'+PROJECT_NUMBER;
const QUOTA_PARENT='projects/'+PROJECT_NUMBER+'/locations/global';
const QUOTA='https://cloudquotas.googleapis.com/v1/'+QUOTA_PARENT;
const INFO_PARENT=QUOTA_PARENT+'/services/'+SERVICE+'/quotaInfos/';
const PREFERENCE=QUOTA_PARENT+'/quotaPreferences/'+PREFERENCE_ID;
const QUOTA_FIELDS='quotaInfos(name,quotaId,metric,service,dimensions,dimensionsInfos(dimensions,details(value),applicableLocations)),nextPageToken';
const reply=(body,status=200)=>new Response(JSON.stringify({project:PROJECT,gpu_creation_attempted:false,...body}),{status,
  headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
function fail(reason){const error=new Error(reason);error.safeReason=reason;throw error;}
function require(value,reason){if(!value)fail(reason);}
function isMap(value){return value&&typeof value==='object'&&!Array.isArray(value);}
function numeric(value){if(typeof value==='string'&&/^-?[0-9]{1,16}$/.test(value))value=Number(value);
  return Number.isSafeInteger(value)&&value>=-1?value:null;}
function quotaValue(details){return isMap(details)?Object.hasOwn(details,'value')?numeric(details.value):0:null;}
function validQuota(item){return isMap(item)&&item.service===SERVICE&&typeof item.metric==='string'&&item.metric.toLowerCase()===METRIC
  &&typeof item.quotaId==='string'&&/^[A-Za-z0-9_.-]{1,200}$/.test(item.quotaId)&&item.name===INFO_PARENT+item.quotaId;}
function validDimensions(item){const infos=item.dimensionsInfos??[];
  return Array.isArray(infos)&&infos.length<=500&&infos.every(info=>{
    if(!isMap(info)||!isMap(info.dimensions??{})||quotaValue(info.details)===null)return false;
    const dims=info.dimensions??{},keys=Object.keys(dims),locations=info.applicableLocations??[];
    return keys.length<=1&&keys.every(key=>key==='region')
      &&(keys.length===0||typeof dims.region==='string'&&/^[a-z]+-[a-z]+[0-9]{1,2}$/.test(dims.region))
      &&Array.isArray(locations)&&locations.length<=100&&locations.every(region=>typeof region==='string'&&(region==='global'||/^[a-z]+-[a-z]+[0-9]{1,2}$/.test(region)));
  });}
function regionalRows(item){const rows=[];
  for(const info of Array.isArray(item.dimensionsInfos)?item.dimensionsInfos.slice(0,500):[]){
    if(rows.length>128)return rows;
    if(!isMap(info)||!isMap(info.dimensions??{}))continue;const dims=info.dimensions??{},keys=Object.keys(dims),limit=quotaValue(info.details);
    if(limit===null||keys.some(key=>key!=='region'))continue;
    if(keys.length===1&&typeof dims.region==='string'&&/^[a-z]+-[a-z]+[0-9]{1,2}$/.test(dims.region))rows.push({quota_id:item.quotaId,region:dims.region,limit});
    else if(keys.length===0){const locations=Array.isArray(info.applicableLocations)?info.applicableLocations:[];
      for(const region of locations.slice(0,100))if(typeof region==='string'&&/^[a-z]+-[a-z]+[0-9]{1,2}$/.test(region))rows.push({quota_id:item.quotaId,region,limit});
      if(locations.length===0||locations.includes('global'))rows.push({quota_id:item.quotaId,region:'global_default',limit});
    }
  }return rows;
}
async function emptyBody(request){if(!request.body)return;const reader=request.body.getReader();let length=0,raw='';
  try{for(;;){const part=await reader.read();if(part.done)break;length+=part.value.byteLength;
    if(length>2){await reader.cancel();fail('body_rejected');}raw+=new TextDecoder('utf-8',{fatal:true}).decode(part.value);}}
  catch(error){if(error.safeReason)throw error;fail('body_rejected');}finally{reader.releaseLock();}
  require(length===0||raw==='{}','body_rejected');}
function contactEmail(env){const value=env.GCP_PREREQ_CONTACT_EMAIL;
  require(typeof value==='string'&&value.length<=254&&/^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$/.test(value)
    &&!value.startsWith('.')&&!value.includes('..')&&!value.includes('.@'),'contact_email_invalid');return value;}
function matchingPreference(item,quotaId){return isMap(item)&&item.name===PREFERENCE&&item.service===SERVICE&&item.quotaId===quotaId
  &&isMap(item.dimensions)&&Object.keys(item.dimensions).length===1&&item.dimensions.region===REGION&&item.quotaConfig?.preferredValue==='1';}
function preferenceSummary(item,quotaId){return {quota_id:quotaId,region:REGION,preferred_value:1,reconciling:item.reconciling===true,
  granted_value:numeric(item.quotaConfig?.grantedValue),contact_verified:false};}
function operationReason(error){return new Map([[1,'CANCELLED'],[3,'INVALID_ARGUMENT'],[5,'NOT_FOUND'],[7,'PERMISSION_DENIED'],[8,'RESOURCE_EXHAUSTED'],
  [9,'FAILED_PRECONDITION'],[13,'INTERNAL'],[14,'UNAVAILABLE'],[16,'UNAUTHENTICATED']]).get(error?.code)||'operation_failed';}

class Client{
  constructor(fetchImpl,token){this.fetchImpl=fetchImpl;this.token=token;}
  async json(method,url,body,limit=65536){return gcpRequestJson(this.fetchImpl,url,{method,headers:{Authorization:'Bearer '+this.token,
    ...(body===undefined?{}:{'Content-Type':'application/json'})},...(body===undefined?{}:{body:JSON.stringify(body)})},limit);}
  async serviceState(service){const result=await this.json('GET',USAGE+'/services/'+service+'?fields=name,state');
    if(!result.ok)return {service,http_status:result.http_status,state:'UNKNOWN',reason:result.reason};
    if(result.data?.name!=='projects/'+PROJECT_NUMBER+'/services/'+service)return {service,http_status:result.http_status,state:'UNKNOWN',reason:'service_identity_mismatch'};
    return {service,http_status:result.http_status,state:['ENABLED','DISABLED','STATE_UNSPECIFIED'].includes(result.data.state)?result.data.state:'STATE_UNSPECIFIED'};}
  async quotas(){const infos=[],rows=[],tokens=new Set();let token;
    for(let page=0;page<MAX_PAGES;page++){
      const params=new URLSearchParams({pageSize:'100',fields:QUOTA_FIELDS});if(token)params.set('pageToken',token);
      const result=await this.json('GET',QUOTA+'/services/'+SERVICE+'/quotaInfos?'+params,undefined,2*1024*1024);
      if(!result.ok)return {ok:false,http_status:result.http_status,reason:result.reason,complete:false,rows,infos};
      if(!isMap(result.data)||!Array.isArray(result.data.quotaInfos??[])||(result.data.quotaInfos??[]).length>100)
        return {ok:false,http_status:result.http_status,reason:'quota_schema_invalid',complete:false,rows,infos};
      for(const item of result.data.quotaInfos??[])if(validQuota(item)){
        if(!validDimensions(item))return {ok:false,http_status:result.http_status,reason:'quota_schema_invalid',complete:false,rows,infos};
        infos.push(item);rows.push(...regionalRows(item));
        if(infos.length>16||rows.length>128)return {ok:false,http_status:result.http_status,reason:'quota_result_limit',complete:false,rows:rows.slice(0,128),infos};}
      const next=result.data.nextPageToken;
      if(next===undefined||next==='')return {ok:true,http_status:result.http_status,complete:true,rows,infos};
      if(typeof next!=='string'||next.length>2048||tokens.has(next))return {ok:false,http_status:result.http_status,reason:'pagination_invalid',complete:false,rows,infos};
      tokens.add(next);token=next;
    }return {ok:true,http_status:200,complete:false,reason:'pagination_limit',rows,infos};
  }
}

export async function handle(request,env,options={}){
  const cryptoImpl=options.cryptoImpl||globalThis.crypto,fetchImpl=options.fetchImpl||globalThis.fetch,now=options.now??Date.now();
  let writeAttempts=0;
  try{
    const url=new URL(request.url),route=url.pathname;
    if(url.search||url.hash||!(request.method==='GET'&&['/status','/principal'].includes(route)||request.method==='POST'&&['/enable-apis','/request-quota'].includes(route)))return reply({reason:'route_rejected',write_api_calls:0},404);
    const gate=await authenticate(request,{GCP_PREFLIGHT_AUTH_SHA256:env.GCP_PREREQ_AUTH_SHA256,GCP_PREFLIGHT_EXPIRES_AT:env.GCP_PREREQ_EXPIRES_AT},cryptoImpl,now);
    if(!gate.ok)return reply({reason:gate.reason,write_api_calls:0},403);
    if(request.method==='POST')await emptyBody(request);
    const email=route==='/request-quota'?contactEmail(env):null;
    const config=gcpConfiguration(env);require(config.ok,'configuration_invalid');
    if(route==='/principal')return reply({iam_member:'serviceAccount:'+config.key.client_email,project_number:PROJECT_NUMBER,
      needed_permissions:NEEDED_PERMISSIONS,write_api_calls:0});
    const gatedFetch=(address,init)=>{if((options.now??Date.now())>=gate.expires)fail('gate_expired');return fetchImpl(address,init);};
    const auth=await gcpTokenFor(config.key,gate.expires,{fetchImpl:gatedFetch,cryptoImpl,now});
    if(!auth.ok)return reply({reason:auth.reason,http_status:auth.http_status,write_api_calls:0},502);
    const client=new Client(gatedFetch,auth.token);
    if(route==='/status'){
      const [services,quota]=await Promise.all([Promise.all(SERVICES.map(service=>client.serviceState(service))),client.quotas()]);
      return reply({status:'prerequisites_observed',services,quota:{http_status:quota.http_status,complete:quota.complete,
        ...(quota.reason?{reason:quota.reason}:{}),quotas:quota.rows},write_api_calls:0});
    }
    if(route==='/enable-apis'){
      writeAttempts++;const result=await client.json('POST',USAGE+'/services:batchEnable',{serviceIds:SERVICES});
      if(!result.ok)return reply({status:result.http_status===null||result.http_status>=500?'enable_outcome_unknown':'enable_request_rejected',reason:result.reason,
        http_status:result.http_status,write_api_calls:writeAttempts,automatic_retry:false},result.http_status===403?403:502);
      if(result.data?.error)return reply({status:'enable_operation_failed',reason:operationReason(result.data.error),http_status:result.http_status,
        write_api_calls:writeAttempts,automatic_retry:false},502);
      const valid=isMap(result.data)&&typeof result.data.name==='string'&&/^operations\/[A-Za-z0-9_.-]{1,240}$/.test(result.data.name);
      return reply({status:valid?'enable_request_submitted':'enable_outcome_unknown',operation_done:valid&&result.data.done===true,
        http_status:result.http_status,write_api_calls:writeAttempts,automatic_retry:false},valid?200:502);
    }
    // Discover the opaque quota ID from this authenticated, complete exact-metric list.
    const observed=await client.quotas();
    if(!observed.ok||!observed.complete)return reply({status:'quota_discovery_unavailable',reason:observed.reason||'quota_discovery_incomplete',
      http_status:observed.http_status,write_api_calls:0,automatic_retry:false},observed.http_status===403?403:502);
    const ids=[...new Set(observed.infos.map(item=>item.quotaId))];require(ids.length===1,'quota_identity_unconfirmed');
    const quotaId=ids[0],info=observed.infos.find(item=>item.quotaId===quotaId);
    require(Array.isArray(info.dimensions)&&info.dimensions.length===1&&info.dimensions[0]==='region','quota_dimensions_unconfirmed');
    const specific=observed.rows.filter(item=>item.region===REGION),defaults=observed.rows.filter(item=>item.region==='global_default');
    const effective=specific.length?specific:defaults;require(effective.length===1,'regional_quota_unavailable');
    if(effective[0].limit===-1||effective[0].limit>=1)return reply({status:'quota_already_sufficient',quota_id:quotaId,region:REGION,write_api_calls:0});
    require(effective[0].limit===0,'regional_quota_unavailable');
    const existing=await client.json('GET',QUOTA+'/quotaPreferences/'+PREFERENCE_ID);
    if(existing.ok){require(matchingPreference(existing.data,quotaId),'existing_preference_mismatch');
      return reply({status:'existing_matching_preference_contact_unverifiable',...preferenceSummary(existing.data,quotaId),write_api_calls:0,automatic_retry:false});}
    if(existing.http_status!==404)return reply({status:'preference_read_unavailable',reason:existing.reason,http_status:existing.http_status,write_api_calls:0},existing.http_status===403?403:502);
    const body={service:SERVICE,quotaId,dimensions:{region:REGION},quotaConfig:{preferredValue:'1'},justification:JUSTIFICATION,contactEmail:email};
    writeAttempts++;const created=await client.json('POST',QUOTA+'/quotaPreferences?'+new URLSearchParams({quotaPreferenceId:PREFERENCE_ID}),body);
    if(!created.ok)return reply({status:created.http_status===null||created.http_status>=500?'quota_request_outcome_unknown':'quota_request_rejected',
      reason:created.reason,http_status:created.http_status,write_api_calls:writeAttempts,automatic_retry:false},created.http_status===403?403:502);
    if(!matchingPreference(created.data,quotaId))return reply({status:'quota_request_outcome_unknown',reason:'preference_response_unconfirmed',
      write_api_calls:writeAttempts,automatic_retry:false},502);
    return reply({status:'quota_preference_submitted',...preferenceSummary(created.data,quotaId),contact_included:true,write_api_calls:writeAttempts,automatic_retry:false});
  }catch(error){return reply({reason:typeof error?.safeReason==='string'?error.safeReason:'prerequisites_failed',write_api_calls:writeAttempts,automatic_retry:false},409);}
}

export default{fetch(request,env){return handle(request,env);}};

// Isolated expiring controller. No production module, DB, R2, or arbitrary proxy.
import { PROJECT, BUCKET, authenticate, gcpConfiguration, gcpTokenFor, gcpRequestJson } from './gcp_preflight_worker.mjs';

export const REGION = 'us-central1';
export const IMAGE = 'runpod/pytorch@sha256:0a360022e8de4375af99430f84e8b38951acc397252163a37ceac7204d01be35';
export const CODE_FILES = Object.freeze(['gcp_gemma_worker.py','train_lora.py','role_config.py','private_pod_train.py',
  'private_verify_adapter.py','private_dual_run.py','private_corpus_run.py','training_budget.py']);
const PACKAGES = ['torch','unsloth','unsloth_zoo','transformers','trl','datasets','peft'];
export const INPUTS = Object.freeze({
  train: { name:'train.chat.jsonl', bytes:320061, records:60, sha256:'933daff03738b4daeaa0ca17bf45aa24cfb39736940f9126e27da57a088f7b5c' },
  validation: { name:'validation.chat.jsonl', bytes:55453, records:11, sha256:'e3052b3d8cfdd04c03c8de250649b89a1d4d3104477782c5227799c1dce0160f' },
});
const PROBE = new TextEncoder().encode('hasla-private-gemma-probe-000000'); // exactly 32 nonsensitive bytes
const JOB_STATES = new Set(['JOB_STATE_QUEUED','JOB_STATE_PENDING','JOB_STATE_RUNNING','JOB_STATE_SUCCEEDED',
  'JOB_STATE_FAILED','JOB_STATE_CANCELLING','JOB_STATE_CANCELLED','JOB_STATE_PAUSED','JOB_STATE_EXPIRED']);
const TERMINAL = new Set(['JOB_STATE_SUCCEEDED','JOB_STATE_FAILED','JOB_STATE_CANCELLED','JOB_STATE_EXPIRED']);
const ENCODER = new TextEncoder();
const SHA = /^[a-f0-9]{64}$/;
const GEN = /^[1-9][0-9]{0,24}$/;
const response = (value,status=200) => new Response(JSON.stringify(value),{ status,
  headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'} });
const canonical = value => JSON.stringify(value && typeof value === 'object'
  ? Array.isArray(value) ? value.map(v=>JSON.parse(canonical(v))) : Object.fromEntries(Object.keys(value).sort().map(k=>[k,JSON.parse(canonical(value[k]))])) : value);
const digest = async (raw,cryptoImpl) => Array.from(new Uint8Array(await cryptoImpl.subtle.digest('SHA-256',raw)),v=>v.toString(16).padStart(2,'0')).join('');
function fail(reason) { const error=new Error(reason);error.safeReason=reason;throw error; }
function require(value,reason) { if (!value) fail(reason); }
function exactKeys(value,keys) { return value && typeof value==='object' && !Array.isArray(value) && Object.keys(value).sort().join('|')===[...keys].sort().join('|'); }

export function controlManifest(raw) {
  require(typeof raw==='string' && raw.length>0 && raw.length<=32768,'manifest_invalid');
  let m;try { m=JSON.parse(raw); } catch { fail('manifest_invalid'); }
  require(exactKeys(m,['version','kind','run_id','project_id','project_number','service_account_email','bucket','dataset_version','code_commit','code_sha256','dependency_versions','budget']),'manifest_invalid');
  require(m.version===1 && m.kind==='gcp_gemma_control_v1' && /^[a-z0-9][a-z0-9-]{0,62}$/.test(m.run_id)
    && m.project_id===PROJECT && m.bucket===BUCKET && m.dataset_version==='gemma-chat-v5-approved-20261105'
    && typeof m.project_number==='string' && /^[1-9][0-9]{0,19}$/.test(m.project_number)
    && m.service_account_email===`service-${m.project_number}@gcp-sa-aiplatform-cc.iam.gserviceaccount.com`
    && /^[a-f0-9]{40}$/.test(m.code_commit),'manifest_invalid');
  require(exactKeys(m.code_sha256,CODE_FILES) && Object.values(m.code_sha256).every(s=>typeof s==='string' && SHA.test(s)),'code_manifest_invalid');
  require(exactKeys(m.dependency_versions,PACKAGES) && Object.values(m.dependency_versions).every(s=>typeof s==='string' && /^[A-Za-z0-9_.+!-]{1,120}$/.test(s)),'dependency_manifest_invalid');
  const b=m.budget;
  require(exactKeys(b,['authorized_budget_krw','prior_closed_upper_krw','other_reserved_upper_krw','job_reserved_upper_krw','reserve_krw'])
    && Object.values(b).every(v=>Number.isSafeInteger(v) && v>=0) && b.authorized_budget_krw===100000
    && b.job_reserved_upper_krw===15000 && b.reserve_krw===5000
    && b.prior_closed_upper_krw+b.other_reserved_upper_krw+b.job_reserved_upper_krw+b.reserve_krw<=100000,'budget_invalid');
  return m;
}

async function readBytes(body,limit) {
  if (!body) return new Uint8Array();
  const reader=body.getReader(),chunks=[];let length=0;
  try { for (;;) { const part=await reader.read();if(part.done)break;length+=part.value.byteLength;
    if(length>limit){await reader.cancel();fail('body_size_rejected');}chunks.push(part.value); } }
  finally { reader.releaseLock(); }
  const raw=new Uint8Array(length);let offset=0;for(const chunk of chunks){raw.set(chunk,offset);offset+=chunk.length;}return raw;
}
async function emptyBody(request) { const raw=await readBytes(request.body,2);require(raw.length===0 || new TextDecoder().decode(raw)==='{}','body_rejected'); }

export function runtimeManifest(m,inputs,probe) {
  return {version:1,kind:'gcp_gemma_training_v1',run_id:m.run_id,project_id:PROJECT,project_number:m.project_number,
    service_account_email:m.service_account_email,bucket:BUCKET,prefix:'hasla-ai/gemma/'+m.run_id,
    machine_type:'a2-ultragpu-1g',runtime_seconds:1200,upload_grace_seconds:180,dataset_version:m.dataset_version,
    code_sha256:m.code_sha256,dependency_versions:m.dependency_versions,inputs,privacy_probe:probe,budget:m.budget};
}

// Public pinned source only. No provider/HF keys are forwarded to the VM.
const BOOTSTRAP = String.raw`
import hashlib,importlib.metadata,json,os,pathlib,subprocess,sys,time,urllib.request
m=json.loads(os.environ['HASLA_GCP_GEMMA_MANIFEST']);commit=os.environ['HASLA_GCP_CODE_COMMIT']
root=pathlib.Path('/tmp/hasla-gemma');root.mkdir(exist_ok=True);os.chdir(root)
deadline=time.monotonic()+500
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**kw):return None
opener=urllib.request.build_opener(NoRedirect)
for name,expected in m['code_sha256'].items():
 url='https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io/'+commit+'/tools/ai/'+name
 with opener.open(url,timeout=20) as r:raw=r.read(1048577)
 if len(raw)>1048576 or hashlib.sha256(raw).hexdigest()!=expected:raise SystemExit(2)
 (root/name).write_bytes(raw)
if importlib.metadata.version('torch')!=m['dependency_versions']['torch']:raise SystemExit(3)
(root/'constraints.txt').write_text('torch=='+m['dependency_versions']['torch']+'\n')
packages=[k+'=='+v for k,v in m['dependency_versions'].items() if k!='torch']
env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','SECRET','PASSWORD','KEY')) and not k.startswith('HASLA_')}
remaining=int(deadline-time.monotonic())
if remaining<30:raise SystemExit(4)
with open('/tmp/hasla-gemma-setup.log','wb') as log:
 subprocess.run([sys.executable,'-m','pip','install','--quiet','--no-cache-dir','--constraint',str(root/'constraints.txt'),*packages],env=env,stdout=log,stderr=log,timeout=remaining,check=True)
os.execv(sys.executable,[sys.executable,str(root/'gcp_gemma_worker.py')])
`;

export function jobBody(m,runtime,manifestHash) {
  return {displayName:'hasla-gemma-'+m.run_id,labels:{hasla_run_id:m.run_id,hasla_manifest:manifestHash.slice(0,40)},
    jobSpec:{scheduling:{timeout:'1800s',disableRetries:true,restartJobOnWorkerRestart:false,strategy:'STANDARD'},
      workerPoolSpecs:[{replicaCount:'1',machineSpec:{machineType:'a2-ultragpu-1g',acceleratorType:'NVIDIA_A100_80GB',acceleratorCount:1},
        diskSpec:{bootDiskType:'pd-ssd',bootDiskSizeGb:200},containerSpec:{imageUri:IMAGE,command:['python','-c',BOOTSTRAP],
          env:[{name:'HASLA_GCP_GEMMA_MANIFEST',value:canonical(runtime)},{name:'HASLA_GCP_CODE_COMMIT',value:m.code_commit}]}}]}};
}

function ownJob(job,m,hash) {
  return job && typeof job.name==='string'
    && new RegExp(`^projects/${m.project_number}/locations/${REGION}/customJobs/[0-9]+$`).test(job.name)
    && job.displayName==='hasla-gemma-'+m.run_id && job.labels?.hasla_run_id===m.run_id
    && job.labels?.hasla_manifest===hash.slice(0,40);
}
function safeJob(job) { return {name:job.name,state:JOB_STATES.has(job.state)?job.state:'JOB_STATE_UNSPECIFIED',
  terminal:TERMINAL.has(job.state),cpu_weights_verified:false}; }

class Controller {
  constructor(m,hash,token,fetchImpl,cryptoImpl){Object.assign(this,{m,hash,token,fetchImpl,cryptoImpl});this.prefix='hasla-ai/gemma/'+m.run_id;}
  object(name){return this.prefix+'/'+name;}
  metaUrl(name){return 'https://storage.googleapis.com/storage/v1/b/'+BUCKET+'/o/'+encodeURIComponent(this.object(name));}
  async json(method,url,body){return gcpRequestJson(this.fetchImpl,url,{method,headers:{Authorization:'Bearer '+this.token,
    ...(body!==undefined?{'Content-Type':'application/json'}:{})},...(body!==undefined?{body:canonical(body)}:{})},65536);}
  async metadata(name){const r=await this.json('GET',this.metaUrl(name)+'?fields=bucket,name,size,generation,md5Hash');
    if(!r.ok)return r;const v=r.data;require(v?.bucket===BUCKET && v.name===this.object(name) && typeof v.generation==='string' && GEN.test(v.generation)
      && typeof v.size==='string' && /^[0-9]{1,20}$/.test(v.size),'object_metadata_invalid');return {ok:true,data:v};}
  async requireBucketPrivacy(){const r=await this.json('GET','https://storage.googleapis.com/storage/v1/b/'+BUCKET+'?fields=name,iamConfiguration');
    require(r.ok && r.data?.name===BUCKET && r.data.iamConfiguration?.publicAccessPrevention==='enforced'
      && r.data.iamConfiguration?.uniformBucketLevelAccess?.enabled===true,'bucket_privacy_unverified');}
  async media(name,generation,limit){let r;
    try{r=await this.fetchImpl(this.metaUrl(name)+'?alt=media&generation='+generation,{method:'GET',headers:{Authorization:'Bearer '+this.token},redirect:'manual',signal:AbortSignal.timeout(15000)});}
    catch{fail('object_transfer_failed');}require(r.status===200,'object_transfer_failed');return readBytes(r.body,limit);}
  async anonymous(name,generation){let r;
    try{r=await this.fetchImpl('https://storage.googleapis.com/'+BUCKET+'/'+this.object(name).split('/').map(encodeURIComponent).join('/')+'?generation='+generation,
      {method:'GET',credentials:'omit',redirect:'manual',signal:AbortSignal.timeout(10000)});}catch{return false;}
    const privateObject=r.status===403;await r.body?.cancel().catch(()=>{});return privateObject;}
  async put(name,raw,type='application/json'){const url='https://storage.googleapis.com/upload/storage/v1/b/'+BUCKET+'/o?'+new URLSearchParams({uploadType:'media',name:this.object(name),ifGenerationMatch:'0'});
    return gcpRequestJson(this.fetchImpl,url,{method:'POST',headers:{Authorization:'Bearer '+this.token,'Content-Type':type},body:raw},65536);}
  async record(name,value){const raw=ENCODER.encode(canonical(value));const r=await this.put(name,raw);
    if(!r.ok && r.http_status!==412)fail('private_receipt_write_unconfirmed');
    const found=await this.metadata(name);require(found.ok,'private_receipt_write_unconfirmed');
    const actual=await this.media(name,found.data.generation,8192);require(await digest(actual,this.cryptoImpl)===await digest(raw,this.cryptoImpl),'private_receipt_mismatch');
    require(await this.anonymous(name,found.data.generation),'private_receipt_not_private');return found.data.generation;}
  async getRecord(name){const meta=await this.metadata(name);if(!meta.ok){if(meta.http_status===404)return null;fail('private_receipt_read_failed');}
    require(await this.anonymous(name,meta.data.generation),'private_receipt_not_private');const raw=await this.media(name,meta.data.generation,8192);
    try{return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw));}catch{fail('private_receipt_invalid');}}
  async verify(name,expected){if(Object.values(INPUTS).some(item=>item.name===name))await this.requireBucketPrivacy();
    const found=await this.metadata(name);require(found.ok,'object_missing');const meta=found.data;
    require(meta.size===String(expected.bytes),'object_size_mismatch');const raw=await this.media(name,meta.generation,expected.bytes);
    require(raw.length===expected.bytes && await digest(raw,this.cryptoImpl)===expected.sha256,'object_hash_mismatch');
    require(await this.anonymous(name,meta.generation),'object_not_private');return {name,generation:meta.generation,...expected};}
  async probe(create=false){require(PROBE.length===32,'probe_invalid');const probeSha=await digest(PROBE,this.cryptoImpl);
    if(create){const result=await this.put('privacy-probe.bin',PROBE,'application/octet-stream');require(result.ok||result.http_status===412,'probe_create_failed');}
    const p=await this.verify('privacy-probe.bin',{bytes:32,sha256:probeSha});
    if(create)await this.record('privacy-proof.json',{version:1,run_id:this.m.run_id,manifest_sha256:this.hash,probe:p,anonymous_status:403});
    const proof=await this.getRecord('privacy-proof.json');require(proof?.manifest_sha256===this.hash && canonical(proof.probe)===canonical(p)
      && proof.anonymous_status===403,'privacy_probe_unverified');return p;}
  async inputs(){const result={};for(const [split,item]of Object.entries(INPUTS)){const v=await this.verify(item.name,item);result[split]=v;}return result;}
  async findJob(){const receipt=await this.getRecord('job-receipt.json');
    if(receipt){require(receipt.manifest_sha256===this.hash && typeof receipt.name==='string'
      && new RegExp(`^projects/${this.m.project_number}/locations/${REGION}/customJobs/[0-9]+$`).test(receipt.name),'job_receipt_invalid');
      const r=await this.json('GET','https://'+REGION+'-aiplatform.googleapis.com/v1/'+receipt.name);require(r.ok,'job_status_unavailable');
      require(ownJob(r.data,this.m,this.hash),'job_identity_mismatch');return r.data;}
    const lease=await this.getRecord('start-intent.json');if(!lease)return null;
    require(lease.manifest_sha256===this.hash && lease.run_id===this.m.run_id,'start_intent_mismatch');
    const filter='labels.hasla_run_id="'+this.m.run_id+'"';
    const r=await this.json('GET','https://'+REGION+'-aiplatform.googleapis.com/v1/projects/'+PROJECT+'/locations/'+REGION+'/customJobs?'+new URLSearchParams({pageSize:'20',filter}));
    require(r.ok && Array.isArray(r.data.customJobs||[]) && !r.data.nextPageToken,'job_discovery_unavailable');
    const matches=(r.data.customJobs||[]).filter(job=>ownJob(job,this.m,this.hash));require(matches.length<=1,'multiple_own_jobs');return matches[0]||null;}
  async workerSummary(name){const meta=await this.metadata(name);if(!meta.ok)return null;require(await this.anonymous(name,meta.data.generation),'worker_report_not_private');
    const raw=await this.media(name,meta.data.generation,65536);let value;try{value=JSON.parse(new TextDecoder().decode(raw));}catch{return null;}
    const safe={};for(const item of [value,value.numeric_progress,value.training_report])if(item&&typeof item==='object')
      for(const k of ['steps_completed','max_steps','train_loss','eval_loss','elapsed_seconds'])if(typeof item[k]==='number'&&Number.isFinite(item[k])&&Math.abs(item[k])<=1e9)safe[k]=item[k];
    if(['starting','stored','partial','training','training_ended','uploaded','failed','blocked','completed','preflight_ready'].includes(value.status))safe.status=value.status;
    if(['training','training_ended','adapter_validation','uploading_adapter'].includes(value.phase))safe.phase=value.phase;
    if(typeof value.weights_updated==='boolean')safe.weights_updated=value.weights_updated;return safe;}
}

export async function handle(request,env,options={}) {
  const cryptoImpl=options.cryptoImpl||globalThis.crypto,fetchImpl=options.fetchImpl||globalThis.fetch,now=options.now??Date.now();
  let gpuCreationAttempted=false;
  try{const u=new URL(request.url);const input=/^\/inputs\/(train|validation)$/.exec(u.pathname);
    const allowed=u.pathname==='/status'&&request.method==='GET'||['/probe','/start','/cancel'].includes(u.pathname)&&request.method==='POST'||input&&request.method==='PUT';
    if(!allowed||u.search||u.hash)return response({reason:'route_rejected'},404);
    const gate=await authenticate(request,{GCP_PREFLIGHT_AUTH_SHA256:env.GCP_GEMMA_AUTH_SHA256,GCP_PREFLIGHT_EXPIRES_AT:env.GCP_GEMMA_EXPIRES_AT},cryptoImpl,now);
    if(!gate.ok)return response({reason:gate.reason},403);
    const m=controlManifest(env.GCP_GEMMA_MANIFEST),config=gcpConfiguration(env);require(config.ok,'configuration_invalid');
    const hash=await digest(ENCODER.encode(canonical(m)),cryptoImpl);
    const gatedFetch=(url,init)=>{if((options.now??Date.now())>=gate.expires)fail('gate_expired');return fetchImpl(url,init);};
    const auth=await gcpTokenFor(config.key,gate.expires,{fetchImpl:gatedFetch,cryptoImpl,now});require(auth.ok,'oauth_unavailable');
    const c=new Controller(m,hash,auth.token,gatedFetch,cryptoImpl);
    if(input){await c.requireBucketPrivacy();await c.probe(false);const split=input[1],spec=INPUTS[split];
      const raw=await readBytes(request.body,spec.bytes);require(raw.length===spec.bytes&&await digest(raw,cryptoImpl)===spec.sha256,'input_payload_mismatch');
      let lines;try{lines=new TextDecoder('utf-8',{fatal:true}).decode(raw).split(/\r?\n/).filter(s=>s.trim());for(const line of lines)JSON.parse(line);}catch{fail('input_payload_mismatch');}
      require(lines.length===spec.records,'input_count_mismatch');await c.requireBucketPrivacy();
      const r=await c.put(spec.name,raw,'application/jsonl');require(r.ok||r.http_status===412,'input_upload_unconfirmed');
      const verified=await c.verify(spec.name,spec);return response({status:'input_private_verified',split,generation:verified.generation,bytes:spec.bytes,records:spec.records,sha256:spec.sha256});}
    if(u.pathname==='/probe'){await emptyBody(request);const probe=await c.probe(true);return response({status:'private_probe_verified',generation:probe.generation,bytes:32,anonymous_status:403,gpu_creation_attempted:false});}
    if(u.pathname==='/status'){const lease=await c.getRecord('start-intent.json'),job=await c.findJob();return response({status:job?'job_observed':lease?'creation_outcome_unknown':'not_started',
      job:job?safeJob(job):null,start_intent_present:!!lease,reservation_retained:!!lease,progress:await c.workerSummary('progress.json'),result:await c.workerSummary('result.json')});}
    await emptyBody(request);
    if(u.pathname==='/cancel'){const job=await c.findJob();require(job,'own_job_unconfirmed');if(TERMINAL.has(job.state))return response({status:'already_terminal',job:safeJob(job)});
      const r=await c.json('POST','https://'+REGION+'-aiplatform.googleapis.com/v1/'+job.name+':cancel',{});
      return response({status:r.ok?'cancellation_requested':'cancellation_unconfirmed',job:safeJob(job),reservation_retained:true},r.ok?200:502);}
    await c.requireBucketPrivacy();const probe=await c.probe(false),inputs=await c.inputs(),runtime=runtimeManifest(m,inputs,probe);
    await c.record('runtime-manifest.json',runtime);
    const intent={version:1,run_id:m.run_id,manifest_sha256:hash,job_reserved_upper_krw:15000};
    const lease=await c.put('start-intent.json',ENCODER.encode(canonical(intent)));
    if(!lease.ok)return response({status:'start_blocked',reason:lease.http_status===412?'start_already_attempted':'start_intent_unconfirmed',reservation_retained:true,gpu_creation_attempted:false},409);
    const leaseMeta=await c.metadata('start-intent.json');require(leaseMeta.ok,'start_intent_unconfirmed');
    const leaseRaw=await c.media('start-intent.json',leaseMeta.data.generation,8192);
    require(await digest(leaseRaw,cryptoImpl)===await digest(ENCODER.encode(canonical(intent)),cryptoImpl),'start_intent_mismatch');
    require(await c.anonymous('start-intent.json',leaseMeta.data.generation),'start_intent_not_private');
    await c.requireBucketPrivacy();
    gpuCreationAttempted=true;
    const created=await c.json('POST','https://'+REGION+'-aiplatform.googleapis.com/v1/projects/'+PROJECT+'/locations/'+REGION+'/customJobs',jobBody(m,runtime,hash));
    if(!created.ok||!ownJob(created.data,m,hash))return response({status:'creation_outcome_unknown',reservation_retained:true,gpu_creation_attempted:true},502);
    await c.record('job-receipt.json',{version:1,run_id:m.run_id,manifest_sha256:hash,name:created.data.name});
    return response({status:'job_created',job:safeJob(created.data),reservation_retained:true,job_reserved_upper_krw:15000});
  // A failed observation cannot prove that an earlier reservation/job is absent.
  }catch(error){return response({reason:typeof error?.safeReason==='string'?error.safeReason:'controller_failed',gpu_creation_attempted:gpuCreationAttempted,
    reservation_retained:true,reservation_release_authorized:false},409);}
}

export default {fetch(request,env){return handle(request,env);}};

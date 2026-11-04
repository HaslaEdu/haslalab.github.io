// Offline state-machine tests. Only generated RSA and synthetic JSONL are used.
import test from 'node:test';
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { handle, controlManifest, jobBody, runtimeManifest, INPUTS, IMAGE, CODE_FILES } from './gcp_gemma_control_worker.mjs';

const NOW=Date.parse('2026-11-05T00:00:00Z'),TOKEN='c'.repeat(64),OAUTH='ya29.OFFLINE_ONLY';
const SECRET='NEVER_RETURN_UPSTREAM_SECRET';
const enc=new TextEncoder();
const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
const clone=value=>JSON.parse(JSON.stringify(value));
const realSHA=async raw=>Buffer.from(await webcrypto.subtle.digest('SHA-256',raw)).toString('hex');
function synthetic(spec){
  const lines=Array.from({length:spec.records},()=>JSON.stringify({messages:[{role:'user',content:'synthetic'},{role:'assistant',content:'fixture'}]}));
  const length=enc.encode(lines.join('\n')+'\n').length;
  const first=JSON.parse(lines[0]);first.messages[0].content+='x'.repeat(spec.bytes-length);
  lines[0]=JSON.stringify(first);const raw=enc.encode(lines.join('\n')+'\n');assert.equal(raw.length,spec.bytes);return raw;
}
const raws=Object.fromEntries(Object.entries(INPUTS).map(([key,spec])=>[key,synthetic(spec)]));
// A test-only digest adapter gives synthetic fixtures the frozen dataset identities.
// Production always uses WebCrypto directly; no env/request bypass exists.
let fixturePromise;
async function fixture(){
  if(!fixturePromise)fixturePromise=(async()=>{
    const pair=await webcrypto.subtle.generateKey({name:'RSASSA-PKCS1-v1_5',modulusLength:2048,publicExponent:Uint8Array.of(1,0,1),hash:'SHA-256'},true,['sign','verify']);
    const der=await webcrypto.subtle.exportKey('pkcs8',pair.privateKey);
    const pem='-----BEGIN PRIVATE KEY-----\n'+Buffer.from(der).toString('base64').match(/.{1,64}/g).join('\n')+'\n-----END PRIVATE KEY-----\n';
    const substitutions=new Map();for(const [key,raw]of Object.entries(raws))substitutions.set(await realSHA(raw),INPUTS[key].sha256);
    const subtle=new Proxy(webcrypto.subtle,{get(target,key){if(key==='digest')return async(algorithm,data)=>{
      const actual=await target.digest(algorithm,data),sha=Buffer.from(actual).toString('hex');
      return substitutions.has(sha)?Uint8Array.from(Buffer.from(substitutions.get(sha),'hex')).buffer:actual;
    };const method=Reflect.get(target,key);return typeof method==='function'?method.bind(target):method;}});
    const manifest={version:1,kind:'gcp_gemma_control_v1',run_id:'offline-fixture',project_id:'project-hasla',project_number:'123456789012',
      service_account_email:'service-123456789012@gcp-sa-aiplatform-cc.iam.gserviceaccount.com',bucket:'hasla-training',
      dataset_version:'gemma-chat-v5-approved-20261105',code_commit:'1'.repeat(40),code_sha256:Object.fromEntries(CODE_FILES.map(name=>[name,'2'.repeat(64)])),
      dependency_versions:{torch:'2.8.0+cu128',unsloth:'2026.11.1',unsloth_zoo:'2026.11.1',transformers:'4.57.1',trl:'0.23.1',datasets:'4.3.0',peft:'0.17.1'},
      budget:{authorized_budget_krw:100000,prior_closed_upper_krw:20000,other_reserved_upper_krw:10000,job_reserved_upper_krw:15000,reserve_krw:5000}};
    return {manifest,cryptoImpl:{subtle},env:{GCP_SA_KEY:JSON.stringify({type:'service_account',project_id:'project-hasla',
      client_email:'fixture@project-hasla.iam.gserviceaccount.com',private_key:pem,token_uri:'https://oauth2.googleapis.com/token'}),
      GCP_PROJECT:'project-hasla',GCP_TUNING_BUCKET:'hasla-training',GCP_GEMMA_AUTH_SHA256:await realSHA(enc.encode(TOKEN)),
      GCP_GEMMA_EXPIRES_AT:'2026-11-05T00:45:00Z',GCP_GEMMA_MANIFEST:JSON.stringify(manifest)}};
  })();return fixturePromise;
}
function provider(options={}){
  const calls=[],objects=new Map(),jobs=[];let generation=100,bucketReads=0;
  const prefix='hasla-ai/gemma/offline-fixture/';
  const store=(name,raw)=>{const item={name:prefix+name,raw:Buffer.from(raw),generation:String(++generation)};objects.set(item.name,item);return item;};
  const metadata=item=>({bucket:'hasla-training',name:item.name,size:String(item.raw.length),generation:item.generation,md5Hash:'OFFLINE_MD5'});
  const fetchImpl=async(url,init={})=>{
    url=String(url);calls.push({url,...init});const u=new URL(url);
    assert.equal(init.redirect,'manual');assert.ok(init.signal instanceof AbortSignal);
    if(url==='https://oauth2.googleapis.com/token')return json({access_token:OAUTH,token_type:'Bearer'});
    const anonymous=u.hostname==='storage.googleapis.com'&&u.pathname.startsWith('/hasla-training/');
    if(anonymous){assert.equal(init.headers?.Authorization,undefined);assert.equal(init.credentials,'omit');
      const name=decodeURIComponent(u.pathname.slice('/hasla-training/'.length));
      return new Response(SECRET,{status:options.publicObject?.(name)?200:403});}
    assert.equal(init.headers.Authorization,'Bearer '+OAUTH);
    if(u.pathname==='/storage/v1/b/hasla-training'){
      bucketReads++;
      if(options.bucketFailAfter&&bucketReads>options.bucketFailAfter)return json({error:{message:SECRET}},403);
      if(options.bucketStatus)return json({error:{message:SECRET}},options.bucketStatus);
      return json({name:'hasla-training',iamConfiguration:{publicAccessPrevention:options.pap??'enforced',uniformBucketLevelAccess:{enabled:options.ubla??true}}});
    }
    if(u.pathname==='/upload/storage/v1/b/hasla-training/o'){
      assert.equal(init.method,'POST');assert.equal(u.searchParams.get('ifGenerationMatch'),'0');
      const name=u.searchParams.get('name');assert.ok(name.startsWith(prefix));
      if(objects.has(name))return json({error:{message:SECRET}},412);
      if(options.failReceipt&&name.endsWith('/job-receipt.json'))return json({error:{message:SECRET}},503);
      const item=store(name.slice(prefix.length),typeof init.body==='string'?enc.encode(init.body):init.body);
      if(options.unknownLease&&name.endsWith('/start-intent.json'))throw new Error(SECRET);
      return json(options.invalidUploadResponse?{message:SECRET}:metadata(item));
    }
    if(u.pathname.startsWith('/storage/v1/b/hasla-training/o/')){
      const name=decodeURIComponent(u.pathname.slice('/storage/v1/b/hasla-training/o/'.length)),item=objects.get(name);
      if(options.failMetadataFor?.(name))return json({error:{message:SECRET}},403);
      if(!item)return json({error:{message:SECRET}},404);
      if(u.searchParams.get('generation')&&u.searchParams.get('generation')!==item.generation)return json({},404);
      return u.searchParams.get('alt')==='media'?new Response(item.raw):json(metadata(item));
    }
    if(u.hostname==='us-central1-aiplatform.googleapis.com'){
      if(u.pathname==='/v1/projects/project-hasla/locations/us-central1/customJobs'){
        if(init.method==='GET')return json({customJobs:options.foreignJobs??jobs});
        assert.equal(init.method,'POST');const body=JSON.parse(init.body);
        const job={...body,name:'projects/123456789012/locations/us-central1/customJobs/'+(456+jobs.length),state:'JOB_STATE_RUNNING'};
        jobs.push(job);if(options.unknownCreate)throw new Error(SECRET);return json(job);
      }
      const job=jobs.find(item=>'/v1/'+item.name===u.pathname.replace(/:cancel$/,''));
      if(!job)return json({error:{message:SECRET}},404);
      if(u.pathname.endsWith(':cancel')){assert.equal(init.method,'POST');job.state='JOB_STATE_CANCELLING';return json({});}
      assert.equal(init.method,'GET');return json(job);
    }
    throw new Error('Unexpected offline URL '+url);
  };
  return {fetchImpl,calls,objects,jobs,store,options};
}
const req=(path,method='GET',body,authorized=true)=>new Request('https://isolated.invalid'+path,{method,
  headers:authorized?{Authorization:'Bearer '+TOKEN}:{},...(body!==undefined?{body}: {})});
async function harness(options={},envChanges={}){
  const f=await fixture(),mock=provider(options),env={...f.env,...envChanges};
  const call=async(path,method='GET',body)=>{
    const response=await handle(typeof path==='string'?req(path,method,body):path,env,{fetchImpl:mock.fetchImpl,cryptoImpl:f.cryptoImpl,now:NOW});
    const data=await response.json();assert.equal(JSON.stringify(data).includes(SECRET),false);assert.equal(JSON.stringify(data).includes(OAUTH),false);
    assert.equal(response.headers.get('Cache-Control'),'no-store');return {response,data};
  };
  const ready=async()=>{assert.equal((await call('/probe','POST')).response.status,200);
    for(const split of ['train','validation'])assert.equal((await call('/inputs/'+split,'PUT',raws[split])).response.status,200);};
  return {...mock,f,env,call,ready};
}
const createCalls=h=>h.calls.filter(c=>c.method==='POST'&&c.url==='https://us-central1-aiplatform.googleapis.com/v1/projects/project-hasla/locations/us-central1/customJobs');
const uploadCalls=h=>h.calls.filter(c=>c.url.startsWith('https://storage.googleapis.com/upload/'));

test('fixed model/GPU/runtime/bootstrap contract has no request overrides or service-account override',async()=>{
  const f=await fixture(),m=controlManifest(f.env.GCP_GEMMA_MANIFEST),runtime=runtimeManifest(m,{},{}),body=jobBody(m,runtime,'3'.repeat(64));
  assert.equal(runtime.runtime_seconds,1200);assert.equal(runtime.upload_grace_seconds,180);
  assert.deepEqual(body.jobSpec.scheduling,{timeout:'1800s',disableRetries:true,restartJobOnWorkerRestart:false,strategy:'STANDARD'});
  assert.equal(Object.hasOwn(body.jobSpec,'serviceAccount'),false);assert.equal(body.jobSpec.workerPoolSpecs.length,1);
  const pool=body.jobSpec.workerPoolSpecs[0];assert.equal(pool.replicaCount,'1');
  assert.deepEqual(pool.machineSpec,{machineType:'a2-ultragpu-1g',acceleratorType:'NVIDIA_A100_80GB',acceleratorCount:1});
  assert.equal(pool.containerSpec.imageUri,IMAGE);assert.deepEqual(pool.containerSpec.env.map(e=>e.name),['HASLA_GCP_GEMMA_MANIFEST','HASLA_GCP_CODE_COMMIT']);
  const bootstrap=pool.containerSpec.command[2];
  assert.ok(bootstrap.includes("'https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io/'"));
  assert.ok(bootstrap.includes('hashlib.sha256(raw).hexdigest()!=expected'));
  assert.ok(bootstrap.includes("'torch=='+m['dependency_versions']['torch']+'\\n'"));
  const compiled=spawnSync('python',['-c','import ast,sys; ast.parse(sys.stdin.read())'],{input:bootstrap,encoding:'utf8'});
  assert.equal(compiled.status,0,compiled.stderr);
});

test('complete private flow proves 32B probe, exact two inputs and one GPU creation',async()=>{
  const h=await harness();await h.ready();
  const probe=h.objects.get('hasla-ai/gemma/offline-fixture/privacy-probe.bin');assert.equal(probe.raw.length,32);
  const result=await h.call('/start','POST');assert.equal(result.response.status,200);assert.equal(result.data.status,'job_created');
  assert.equal(createCalls(h).length,1);assert.equal(result.data.reservation_retained,true);
  const runtime=JSON.parse(h.objects.get('hasla-ai/gemma/offline-fixture/runtime-manifest.json').raw);
  assert.equal(runtime.inputs.train.records,60);assert.equal(runtime.inputs.validation.records,11);
  assert.equal(runtime.inputs.train.sha256,INPUTS.train.sha256);assert.equal(runtime.privacy_probe.bytes,32);
  assert.equal(Object.hasOwn(runtime.inputs,'test'),false);assert.equal(runtime.service_account_email,h.f.manifest.service_account_email);
  const status=await h.call('/status');assert.equal(status.data.job.state,'JOB_STATE_RUNNING');
  const cancel=await h.call('/cancel','POST');assert.equal(cancel.data.status,'cancellation_requested');
  assert.equal(h.calls.filter(c=>c.url.endsWith(':cancel')).length,1);
});

test('missing or weak bucket privacy blocks source body read even if anonymous access is 403',async()=>{
  for(const options of [{bucketStatus:403},{pap:'inherited'},{pap:'unspecified'},{ubla:false}]){
    const h=await harness(options);assert.equal((await h.call('/probe','POST')).response.status,200);
    let reads=0;const poisoned={url:'https://isolated.invalid/inputs/train',method:'PUT',headers:new Headers({Authorization:'Bearer '+TOKEN}),get body(){reads++;throw new Error('body must stay unread');}};
    const result=await h.call(poisoned);assert.equal(result.data.reason,'bucket_privacy_unverified');assert.equal(reads,0);
    assert.equal(uploadCalls(h).filter(c=>new URL(c.url).searchParams.get('name').endsWith('train.chat.jsonl')).length,0);
    const start=await h.call('/start','POST');assert.equal(start.data.reason,'bucket_privacy_unverified');assert.equal(createCalls(h).length,0);
  }
});

test('allAuthenticatedUsers can pass anonymous403 but cannot pass missing PAP gate',async()=>{
  const h=await harness({pap:'inherited'});await h.call('/probe','POST');
  const result=await h.call('/inputs/train','PUT',raws.train);assert.equal(result.data.reason,'bucket_privacy_unverified');
  assert.equal(uploadCalls(h).length,2);assert.equal(createCalls(h).length,0);
});

test('privacy is rechecked immediately before source upload and creation',async()=>{
  const upload=await harness({bucketFailAfter:1});await upload.call('/probe','POST');
  assert.equal((await upload.call('/inputs/train','PUT',raws.train)).data.reason,'bucket_privacy_unverified');
  assert.equal(uploadCalls(upload).some(c=>new URL(c.url).searchParams.get('name').endsWith('train.chat.jsonl')),false);
  const start=await harness();await start.ready();
  const reads=start.calls.filter(c=>new URL(c.url).pathname==='/storage/v1/b/hasla-training').length;
  start.options.bucketFailAfter=reads+3; // initial start check and both input checks pass; final check fails.
  const result=await start.call('/start','POST');assert.equal(result.data.reason,'bucket_privacy_unverified');
  assert.equal(result.data.reservation_retained,true);assert.equal(result.data.gpu_creation_attempted,false);assert.equal(createCalls(start).length,0);
});

test('no probe or public probe blocks input body consumption and upload',async()=>{
  for(const options of [{},{publicObject:name=>name.endsWith('privacy-probe.bin')}]){
    const h=await harness(options);if(options.publicObject)assert.equal((await h.call('/probe','POST')).response.status,409);
    let reads=0;const request={url:'https://isolated.invalid/inputs/train',method:'PUT',headers:new Headers({Authorization:'Bearer '+TOKEN}),get body(){reads++;throw new Error('unread');}};
    assert.equal((await h.call(request)).response.status,409);assert.equal(reads,0);
    assert.equal(uploadCalls(h).some(c=>new URL(c.url).searchParams.get('name').endsWith('train.chat.jsonl')),false);
  }
});

test('guest, expired and wrong route/query never read SA or call upstream',async()=>{
  const f=await fixture();let reads=0,calls=0;const env={...f.env};
  Object.defineProperty(env,'GCP_SA_KEY',{get(){reads++;throw new Error('must not read');}});
  for(const request of [req('/status','GET',undefined,false),req('/arbitrary'),req('/start?gpu=L4','POST'),req('/inputs/test','PUT'),req('/status','POST')]){
    assert.ok((await handle(request,env,{cryptoImpl:webcrypto,now:NOW,fetchImpl:()=>{calls++;}})).status>=400);
  }
  for(const expiry of ['2026-11-04T23:59:59Z','2026-11-05T02:00:00Z']){
    const expiredEnv=Object.create(env);expiredEnv.GCP_GEMMA_EXPIRES_AT=expiry;
    assert.equal((await handle(req('/status'),expiredEnv,{cryptoImpl:webcrypto,now:NOW,fetchImpl:()=>{calls++;}})).status,403);
  }
  assert.equal(reads,0);assert.equal(calls,0);
});

test('manifest rejects budget, code, dependency, project and arbitrary override fields before OAuth',async()=>{
  const f=await fixture();
  for(const change of [m=>{m.project_id='other';},m=>{m.project_number='1'.repeat(21);},m=>{m.code_sha256.extra='3'.repeat(64);},
    m=>{delete m.code_sha256[CODE_FILES[0]];},m=>{m.code_commit='main';},m=>{m.dependency_versions.torch='2.8.0 --bad';},
    m=>{m.budget.prior_closed_upper_krw=90000;},m=>{m.budget.job_reserved_upper_krw=14999;},m=>{m.budget.reserve_krw=5001;},m=>{m.gpu='L4';}]){
    const m=clone(f.manifest);change(m);const h=await harness({}, {GCP_GEMMA_MANIFEST:JSON.stringify(m)});
    assert.equal((await h.call('/status')).response.status,409);assert.equal(h.calls.length,0);
  }
});

test('unrelated inherited bindings are not accessed',async()=>{
  const h=await harness();const allowed=new Set(Object.keys(h.env));
  const env=new Proxy(h.env,{get(target,key){assert.ok(allowed.has(key),'unexpected binding access');return target[key];}});
  const result=await handle(req('/status'),env,{fetchImpl:h.fetchImpl,cryptoImpl:h.f.cryptoImpl,now:NOW});assert.equal(result.status,200);
});

test('wrong bytes/hash/count never upload and production crypto rejects synthetic fixture',async()=>{
  const h=await harness();await h.call('/probe','POST');
  const before=uploadCalls(h).length;
  assert.equal((await h.call('/inputs/train','PUT',new Uint8Array(5))).data.reason,'input_payload_mismatch');
  const changed=raws.train.slice();changed[50]^=1;assert.equal((await h.call('/inputs/train','PUT',changed)).data.reason,'input_payload_mismatch');
  const actual=await handle(req('/inputs/train','PUT',raws.train),h.env,{fetchImpl:h.fetchImpl,cryptoImpl:webcrypto,now:NOW});
  assert.equal((await actual.json()).reason,'input_payload_mismatch');assert.equal(uploadCalls(h).length,before);
  const wrongCount=synthetic({...INPUTS.train,records:59});
  const hashOfWrongCount=await realSHA(wrongCount),subtle=new Proxy(h.f.cryptoImpl.subtle,{get(target,key){
    if(key==='digest')return async(algorithm,data)=>await realSHA(data)===hashOfWrongCount
      ?Uint8Array.from(Buffer.from(INPUTS.train.sha256,'hex')).buffer:target.digest(algorithm,data);
    return Reflect.get(target,key);
  }});
  const countResult=await handle(req('/inputs/train','PUT',wrongCount),h.env,{fetchImpl:h.fetchImpl,cryptoImpl:{subtle},now:NOW});
  assert.equal((await countResult.json()).reason,'input_count_mismatch');assert.equal(uploadCalls(h).length,before);
});

test('duplicate start atomically blocks a second creation',async()=>{
  const h=await harness();await h.ready();assert.equal((await h.call('/start','POST')).data.status,'job_created');
  const again=await h.call('/start','POST');assert.equal(again.data.reason,'start_already_attempted');assert.equal(again.data.reservation_retained,true);
  assert.equal(createCalls(h).length,1);
});

test('lost creation response is never retried and status discovers only own job',async()=>{
  const h=await harness({unknownCreate:true});await h.ready();const first=await h.call('/start','POST');
  assert.equal(first.data.status,'creation_outcome_unknown');assert.equal(first.data.gpu_creation_attempted,true);assert.equal(first.data.reservation_retained,true);
  assert.equal((await h.call('/start','POST')).data.reason,'start_already_attempted');assert.equal(createCalls(h).length,1);
  const status=await h.call('/status');assert.equal(status.data.status,'job_observed');assert.equal(status.data.job.name,h.jobs[0].name);
});

test('lost lease response retains hold without any creation POST',async()=>{
  const h=await harness({unknownLease:true});await h.ready();const first=await h.call('/start','POST');
  assert.equal(first.data.reason,'start_intent_unconfirmed');assert.equal(first.data.reservation_retained,true);assert.equal(first.data.gpu_creation_attempted,false);
  assert.equal((await h.call('/start','POST')).data.reason,'start_already_attempted');assert.equal(createCalls(h).length,0);
});

test('receipt failure after creation truthfully reports possible GPU and retains reservation',async()=>{
  const h=await harness({failReceipt:true});await h.ready();const result=await h.call('/start','POST');
  assert.equal(result.data.reason,'private_receipt_write_unconfirmed');assert.equal(result.data.gpu_creation_attempted,true);
  assert.equal(result.data.reservation_retained,true);assert.equal(result.data.reservation_release_authorized,false);assert.equal(createCalls(h).length,1);
});

test('failed status or cancel observation retains any previous reservation conservatively',async()=>{
  const h=await harness();await h.ready();await h.call('/start','POST');
  h.options.failMetadataFor=name=>name.endsWith('/start-intent.json');
  const status=await h.call('/status');assert.equal(status.data.reservation_retained,true);assert.equal(status.data.reservation_release_authorized,false);
  h.options.failMetadataFor=name=>name.endsWith('/job-receipt.json');
  const cancel=await h.call('/cancel','POST');assert.equal(cancel.data.reservation_retained,true);assert.equal(cancel.data.reservation_release_authorized,false);
  assert.equal(h.calls.some(c=>c.url.endsWith(':cancel')),false);assert.equal(createCalls(h).length,1);
});

test('start lease is read back and verified instead of trusting upload response',async()=>{
  const h=await harness({invalidUploadResponse:true});await h.ready();const result=await h.call('/start','POST');
  assert.equal(result.data.status,'job_created');assert.equal(createCalls(h).length,1);
  const reads=h.calls.filter(c=>c.method==='GET'&&c.url.includes('start-intent.json'));
  assert.ok(reads.some(c=>c.url.includes('alt=media')));
});

test('nonempty control bodies and foreign jobs cannot drive creation/cancel',async()=>{
  const h=await harness();await h.ready();
  const result=await h.call('/start','POST',JSON.stringify({gpu:'L4',url:'https://attacker.invalid'}));assert.ok(result.response.status>=400);assert.equal(createCalls(h).length,0);
  const cancel=await h.call('/cancel','POST',JSON.stringify({name:'projects/999/locations/us-central1/customJobs/1'}));assert.ok(cancel.response.status>=400);
  assert.equal(h.calls.some(c=>c.url.endsWith(':cancel')),false);
});

test('unknown create discovery ignores foreign identity and never cancels it',async()=>{
  const h=await harness({unknownCreate:true});await h.ready();await h.call('/start','POST');
  h.options.foreignJobs=[{...h.jobs[0],name:'projects/999/locations/us-central1/customJobs/1'}];
  const status=await h.call('/status');assert.equal(status.data.status,'creation_outcome_unknown');
  assert.equal((await h.call('/cancel','POST')).data.reason,'own_job_unconfirmed');assert.equal(h.calls.some(c=>c.url.endsWith(':cancel')),false);
});

test('worker summaries expose only known enums, finite numeric metrics and booleans',async()=>{
  const h=await harness();h.store('progress.json',enc.encode(JSON.stringify({status:'training',phase:'training',steps_completed:8,train_loss:1.2,
    weights_updated:true,private_key:SECRET,messages:SECRET,eval_loss:'secret',elapsed_seconds:Infinity})));
  const result=await h.call('/status');assert.deepEqual(result.data.progress,{steps_completed:8,train_loss:1.2,status:'training',phase:'training',weights_updated:true});
  h.store('result.json',enc.encode(JSON.stringify({status:'stored',max_steps:8,weights_updated:true,
    training_report:{steps_completed:8,train_loss:1.1,eval_loss:1.3,messages:SECRET},numeric_progress:{elapsed_seconds:100,private_key:SECRET}})));
  const stored=await h.call('/status');assert.deepEqual(stored.data.result,{max_steps:8,elapsed_seconds:100,steps_completed:8,train_loss:1.1,eval_loss:1.3,status:'stored',weights_updated:true});
});

test('HTTP implementation contains no generic URL, arbitrary job, direct data or provider token response route',()=>{
  const source=readFileSync(new URL('./gcp_gemma_control_worker.mjs',import.meta.url),'utf8');
  assert.equal(source.includes('request.json('),false);assert.equal(source.includes('request.text('),false);
  assert.equal(source.includes('env.DB'),false);assert.equal(source.includes('env.R2'),false);
  assert.ok(source.includes("ifGenerationMatch:'0'"));assert.ok(source.includes("publicAccessPrevention==='enforced'"));
});

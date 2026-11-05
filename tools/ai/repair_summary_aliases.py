"""Fixed, reversible JSON-string indexes over three actual private summaries."""
import base64,gzip,hashlib,json,os,re,signal,urllib.request
from pathlib import Path
import private_qwq_gpu_run as parent
import private_qwq_gpu_eval as worker

RUN='41964609630';HEAD='a00c8f99da516361a5210fab328efe5fe911bfce'
ENTITY=parent.ENTITY;PROJECT=parent.resume.PROJECT
BOOT='private_qwq_gpu_bootstrap_result_json';PROGRESS='private_qwq_gpu_progress';RESULT='private_qwq_gpu_result_json'
NAMES=('hasla-qwq-publication-smoke-41964079194','hasla-qwq-bootstrap-'+RUN,'hasla-qwq-gpu-comparison-'+RUN)
SMOKE_SHA='16e38db2224b8d32714b750c6eab516c74e7fd04ab2547a4662da27fbd967cfd'
PINS={'private_qwq_gpu_run.py': 'e8d7be733c4b7a8b65f635f77e1e535f202e7665ba3a2f0d1c374b2bb9342de2', 'private_qwq_gpu_eval.py': '34c09c2a2db22f9b4c525030736e61039b6c2d72ddcc2d55d9bb888e635de0af', 'private_qwq_comparison.py': '280bfeef08d8bd9d26feddc784cf4724687373ae4c186302bc0d171b103298db', 'private_resume_adapter.py': 'e52f9e5c31d938c98b7f3215761e3a3ccee616c645b74bd4cfa899cb34b551af', 'private_verify_adapter.py': 'e349889bbbd25fc5aa80ff32f43c2a3911a3f21ca0fd6f8b530d9b82142063a9', 'role_config.py': 'fde4850efcb0002d3458772956fcf61398c705814e1d6534981404ae495eac03', 'private_corpus_run.py': '8fdbdfa9748f0d2c526cb4212b9b033878ec2847625adefc27091d66f0319888', 'private_pod_train.py': '52e40d98d532b2e4bf0ab686f65ad72ad5286f866b2146cc2cff10c65efaaef5', 'training_budget.py': '6727d8089e55289b89c6e750820ed3275b76fa5a991b324c089251c58d17c46f', 'private_dedicated_run.py': 'a62082d48d415197701397aea9d494793c18345919ab1649d1566a370a514963', 'private_dual_run.py': 'ec3c8e586ebc8f252ee1cdfbc0d4e619f60d1f6209bc07f2172d84cbfe70f49b', 'private_qwq_bootstrap_diagnostic.py': '5acb7414242003f0be5c8e1c396ecd761367e4a92d4c18000090507cdc742d3d'}
def require(ok):
    if not ok:raise ValueError('fixed_alias_repair_rejected')
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def sha(v):return hashlib.sha256(v).hexdigest()
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args):return None

class API:
    def __init__(self,env):
        self.key=env['WANDB_API_KEY'];self.opener=urllib.request.build_opener(NoRedirect())
    def call(self,query,variables):
        auth=base64.b64encode(('api:'+self.key).encode()).decode()
        request=urllib.request.Request('https://api.wandb.ai/graphql',data=canon({'query':query,'variables':variables}).encode(),
            headers={'Authorization':'Basic '+auth,'Content-Type':'application/json'})
        with self.opener.open(request,timeout=10) as response:
            raw=response.read(524289);require(response.status==200 and len(raw)<=524288)
        value=json.loads(raw);require(type(value) is dict and not value.get('errors') and type(value.get('data')) is dict)
        return value['data']
    def read(self,name):
        require(name in NAMES)
        value=self.call('query($e:String!,$p:String!,$r:String!){project(name:$p,entityName:$e){name access run(name:$r){id name state summaryMetrics}}}',{'e':ENTITY,'p':PROJECT,'r':name})
        project=value.get('project');require(type(project) is dict and project.get('name')==PROJECT and project.get('access')=='PRIVATE')
        run=project.get('run');require(type(run) is dict and run.get('name')==name and type(run.get('id')) is str and 0<len(run['id'])<=256)
        summary=run.get('summaryMetrics');summary=json.loads(summary) if type(summary) is str else summary
        require(type(summary) is dict and len(canon(summary).encode())<=196608)
        return {'id':run['id'],'name':name,'state':run.get('state'),'summary':summary}
    def write(self,row,summary):
        require(row['name'] in NAMES and type(summary) is dict)
        value=self.call('mutation UpsertBucket($id:String,$summaryMetrics:JSONString){upsertBucket(input:{id:$id,summaryMetrics:$summaryMetrics}){bucket{id}}}',{'id':row['id'],'summaryMetrics':canon(summary)})
        require((value.get('upsertBucket') or {}).get('bucket',{}).get('id')==row['id'])

def reconstruct(summary,prefix):
    flat={k[len(prefix)+1:]:v for k,v in summary.items() if k.startswith(prefix+'.')}
    require(flat and len(flat)<=128)
    root={}
    for path,value in flat.items():
        parts=path.split('.');require(all(re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,79}',p) for p in parts) and len(parts)<=5)
        node=root
        for part in parts[:-1]:
            if part not in node:node[part]={}
            require(type(node[part]) is dict);node=node[part]
        require(parts[-1] not in node);node[parts[-1]]=value
    return root

def aliases(row):
    s=row['summary'];name=row['name'];out={}
    allowed=(BOOT,) if name!=NAMES[2] else (PROGRESS,RESULT)
    prefixes=allowed if name!=NAMES[2] else ((RESULT,) if any(k.startswith(RESULT+'.') for k in s) else (PROGRESS,))
    require(all(not k.startswith('private_qwq') or any(k==p or k.startswith(p+'.') for p in allowed) for k in s))
    for prefix in prefixes:
        if not any(k.startswith(prefix+'.') for k in s):continue
        value=reconstruct(s,prefix)
        if name==NAMES[0]:
            require(row['state']=='finished' and sha(canon(value).encode())==SMOKE_SHA)
        elif prefix==BOOT:
            require(row['state']=='finished');parent.safe_bootstrap_result({BOOT:value},RUN,HEAD)
            require(value['status']=='passed')
        elif prefix==PROGRESS:
            require(set(value)=={'phase','case_id','mode','completed_attempts','paired_completed_cases','evaluation_only','weights_updated'})
            parent.safe_progress({PROGRESS:value})
        else:worker.validate_result(value,RUN)
        encoded=canon(value)
        require(prefix not in s or type(s[prefix]) is str and s[prefix]==encoded)
        out[prefix]=encoded
    require(out);return out

def emit_backup(row,public,emit):
    from nacl.public import PublicKey,SealedBox
    key=base64.b64decode(public,validate=True);require(len(key)==32 and base64.b64encode(key).decode()==public)
    raw=canon({'kind':'private_summary_alias_backup','target_run_id':RUN,'row':row}).encode()
    packed=gzip.compress(raw,mtime=0);cipher=SealedBox(PublicKey(key)).encrypt(packed);encoded=base64.b64encode(cipher).decode();parts=(len(encoded)+31999)//32000
    for i in range(parts):emit({'event':'private_qwq_gpu_observation','artifact_export_fragment':{'part':i,'parts':parts,'cipher_sha256':sha(cipher),'base64':encoded[i*32000:(i+1)*32000]}})
    emit({'event':'private_qwq_gpu_observation','artifact_export':{'kind':'private_summary_alias_backup','run_id':RUN,'name':row['name'],'algorithm':'libsodium_sealed_box_curve25519xsalsa20poly1305','compression':'gzip','public_key_sha256':sha(key),'raw_sha256':sha(raw),'raw_bytes':len(raw),'gzip_bytes':len(packed),'cipher_sha256':sha(cipher),'cipher_bytes':len(cipher),'base64_characters':len(encoded),'parts':parts}})

def verify_after(before,after,added):
    require(after['id']==before['id'] and after['name']==before['name'])
    require(all(k in after['summary'] and canon(after['summary'][k])==canon(v) for k,v in before['summary'].items()))
    require(all(after['summary'].get(k)==v for k,v in added.items()))
    # Reconstructing the aliases must still validate against the original flat facts.
    aliases(after)

def repair(api,public,emit):
    mode=None;receipts=[]
    for index,name in enumerate(NAMES):
        before=api.read(name);fresh=api.read(name)
        require(canon(before)==canon(fresh));added=aliases(fresh)
        if index!=0 and all(fresh['summary'].get(k)==v for k,v in added.items()):continue
        emit_backup(fresh,public,emit)
        if index==0:
            # The finished synthetic run establishes backend merge behavior first.
            api.write(fresh,added);after=api.read(name)
            mode='merge' if all(k in after['summary'] and canon(after['summary'][k])==canon(v) for k,v in fresh['summary'].items()) else 'whole_snapshot'
            if mode=='whole_snapshot':
                api.write(fresh,{**fresh['summary'],**added});after=api.read(name)
            verify_after(fresh,after,added)
        else:
            require(mode in ('merge','whole_snapshot'))
            api.write(fresh,added if mode=='merge' else {**fresh['summary'],**added})
            after=api.read(name);verify_after(fresh,after,added)
        receipt={'name':name,'aliases':sorted(added),'before_sha256':sha(canon(fresh['summary']).encode()),
                 'after_sha256':sha(canon(after['summary']).encode()),'readback_verified':True,
                 'server_write_mode':mode,'atomic_compare_and_swap':False,'original_flat_fields_preserved':True}
        receipts.append(receipt);emit({'event':'private_qwq_gpu_observation','summary_alias_repair':receipt})
    return receipts

def main():
    require(os.environ.get('WANDB_ENTITY')==ENTITY and os.environ.get('WANDB_API_KEY') and os.environ.get('HASLA_SUMMARY_ALIAS_REPAIR')==RUN)
    require(not any('RUNPOD' in k.upper() and ('KEY' in k.upper() or 'TOKEN' in k.upper()) for k in os.environ))
    for name,pin in PINS.items():require(sha(Path(__file__).with_name(name).read_bytes())==pin)
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError()));signal.alarm(120)
    try:repair(API(os.environ),os.environ['HASLA_EVAL_EXPORT_PUBLIC_KEY'],lambda event:print(canon(event),flush=True));return 0
    finally:signal.alarm(0)
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:print('{"event":"private_qwq_gpu_observation_failed","failure_code":"fixed_alias_repair_failed","automatic_retry_authorized":false}');raise SystemExit(1)

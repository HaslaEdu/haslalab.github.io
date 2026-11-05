"""Seal three fixed PRIVATE W&B GraphQL summaries. No SDK/model/provider calls."""
import base64,gzip,hashlib,json,os,signal,urllib.request
ENTITY='mimgyuson-haslaedu';PROJECT='hasla-ai-private-training';RUN='41964609630'
NAMES=('hasla-qwq-bootstrap-41964609630','hasla-qwq-gpu-comparison-41964609630','hasla-qwq-publication-smoke-41964079194')
def require(ok):
    if not ok: raise ValueError('fixed_private_summary_invalid')
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args):return None
def query(env,opener=None):
    text='query($e:String!,$p:String!,$r0:String!,$r1:String!,$r2:String!){project(name:$p,entityName:$e){name access a:run(name:$r0){name state summaryMetrics} b:run(name:$r1){name state summaryMetrics} c:run(name:$r2){name state summaryMetrics}}}'
    variables={'e':ENTITY,'p':PROJECT,**{'r'+str(i):name for i,name in enumerate(NAMES)}}
    auth=base64.b64encode(('api:'+env['WANDB_API_KEY']).encode()).decode()
    request=urllib.request.Request('https://api.wandb.ai/graphql',data=canonical({'query':text,'variables':variables}),headers={'Authorization':'Basic '+auth,'Content-Type':'application/json'})
    with (opener or urllib.request.build_opener(NoRedirect())).open(request,timeout=25) as response:
        raw=response.read(524289);require(response.status==200 and len(raw)<=524288)
    value=json.loads(raw);require(type(value) is dict and not value.get('errors'))
    project=(value.get('data') or {}).get('project');require(type(project) is dict and project.get('name')==PROJECT and project.get('access')=='PRIVATE')
    return project
def project_payload(project):
    require(type(project) is dict and project.get('name')==PROJECT and project.get('access')=='PRIVATE')
    rows=[]
    for alias,name in zip(('a','b','c'),NAMES):
        require(alias in project);row=project[alias]
        if row is None:rows.append({'requested_name':name,'present':False});continue
        require(type(row) is dict and set(row)=={'name','state','summaryMetrics'} and row['name']==name)
        require(row['state'] is None or type(row['state']) is str and len(row['state'].encode())<=100)
        summary=row['summaryMetrics'];require(type(summary) in (str,dict,list,type(None)))
        raw=summary.encode() if type(summary) is str else canonical(summary);require(len(raw)<=65536)
        rows.append({'requested_name':name,'present':True,'name':row['name'],'state':row['state'],'summaryMetrics':summary,'summary_bytes':len(raw),'summary_sha256':sha(raw)})
    return {'version':1,'kind':'private_qwq_fixed_summary_discovery','target_run_id':RUN,'private_project_verified':True,'model_calls':0,'provider_calls':0,'runs':rows}
def recipient(text):
    from nacl.public import PublicKey,SealedBox
    public=base64.b64decode(text,validate=True);require(type(text) is str and len(public)==32 and base64.b64encode(public).decode()==text)
    box=SealedBox(PublicKey(public));box.encrypt(b'recipient-validation');return public,box
def seal(payload,text):
    public,box=recipient(text);raw=canonical(payload);require(len(raw)<=262144)
    packed=gzip.compress(raw,mtime=0);cipher=box.encrypt(packed);encoded=base64.b64encode(cipher).decode();parts=(len(encoded)+31999)//32000
    meta={'version':1,'algorithm':'libsodium_sealed_box_curve25519xsalsa20poly1305','compression':'gzip','run_id':RUN,'public_key_sha256':sha(public),'raw_sha256':sha(raw),'raw_bytes':len(raw),'gzip_bytes':len(packed),'cipher_bytes':len(cipher),'cipher_sha256':sha(cipher),'base64_characters':len(encoded),'parts':parts}
    events=[{'event':'private_qwq_gpu_observation','artifact_export_fragment':{'part':i,'parts':parts,'cipher_sha256':sha(cipher),'base64':encoded[i*32000:(i+1)*32000]}} for i in range(parts)]
    events.append({'event':'private_qwq_gpu_observation','artifact_export':meta});require(all(len(canonical(e))<49152 for e in events));return events
def main():
    try:
        signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError()));signal.alarm(60)
        require(os.environ.get('WANDB_ENTITY')==ENTITY and os.environ.get('WANDB_API_KEY') and os.environ.get('WANDB_BASE_URL','https://api.wandb.ai').rstrip('/')=='https://api.wandb.ai')
        require(not any('RUNPOD' in k.upper() and ('KEY' in k.upper() or 'TOKEN' in k.upper()) for k in os.environ))
        public=os.environ.get('HASLA_EVAL_EXPORT_PUBLIC_KEY','');recipient(public)
        events=seal(project_payload(query(os.environ)),public)
        for event in events:print(canonical(event).decode(),flush=True)
        return 0
    except Exception:print('{"event":"private_qwq_gpu_observation_failed","failure_code":"fixed_summary_read_failed"}');return 1
    finally:signal.alarm(0)
if __name__=='__main__':raise SystemExit(main())

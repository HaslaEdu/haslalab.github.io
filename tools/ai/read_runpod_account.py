"""One fixed read-only RunPod account snapshot; sealed output, no GPU actions.

Uses the already exercised balance query and REST v2 inventory/catalog routes.
The existing sealed observation transport carries a distinct account payload.
"""
import base64,gzip,hashlib,json,os,re,signal,urllib.request
from datetime import datetime,timezone
from decimal import Decimal

REST='https://api.runpod.io/v2';GRAPHQL='https://api.runpod.io/graphql'
BALANCE_QUERY='query { myself { clientBalance underBalance } }'
CATALOG='/catalog/gpus?include=AVAILABILITY&product=POD&count=1&cloud=SECURE&minCudaVersion=12.8'
GEMMA_GPUS=('NVIDIA A100-PCIE-40GB','NVIDIA L40S','NVIDIA L40','NVIDIA A40')
OBSERVED_GPU_IDS=GEMMA_GPUS+('NVIDIA A100 80GB PCIe','NVIDIA A100-SXM4-80GB','NVIDIA H100 80GB HBM3','NVIDIA H100 PCIe','NVIDIA H100 NVL','NVIDIA H200','NVIDIA H200 NVL')
class ProbeError(ValueError):pass
def require(ok):
    if not ok:raise ProbeError('fixed_readonly_account_probe_rejected')
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args):return None
def number(value,minimum=0,maximum=1000000):
    if type(value) not in (int,float,str):return None
    try:v=Decimal(str(value))
    except Exception:return None
    return str(v) if v.is_finite() and minimum<=v<=maximum else None
def integer(value,maximum=1000):
    return value if type(value) is int and 0<=value<=maximum else None
def label(value,limit=160):
    return value if type(value) is str and len(value)<=limit and re.fullmatch(r'[A-Za-z0-9_. /()-]+',value) else None

class API:
    def __init__(self,key):self.key=key;self.opener=urllib.request.build_opener(NoRedirect())
    def call(self,method,url,body=None):
        require((method,url,body)==('POST',GRAPHQL,{'query':BALANCE_QUERY}) or method=='GET' and body is None and url in (REST+'/pods',REST+CATALOG))
        request=urllib.request.Request(url,data=None if body is None else canon(body),method=method,
            headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'})
        with self.opener.open(request,timeout=20) as response:
            raw=response.read(2*1024**2+1);require(response.status==200 and len(raw)<=2*1024**2)
        value=json.loads(raw);require(type(value) is dict);return value

def collect(api,launch,commit):
    statuses={};funding=pods=offers=None
    try:
        value=api.call('POST',GRAPHQL,{'query':BALANCE_QUERY})
        require(not value.get('errors'));user=(value.get('data') or {}).get('myself');require(type(user) is dict)
        balance=number(user.get('clientBalance'),-1000000);under=user.get('underBalance');require(balance is not None and type(under) is bool)
        available=max(Decimal(0),Decimal(balance)) if not under else Decimal(0)
        funding={'balance_usd':balance,'under_balance':under,'user_runpod_limit_usd':'60',
                 'maximum_future_plan_funding_usd':str(min(Decimal(60),available)),
                 'future_training_reservation_verified':False}
        statuses['balance']='observed'
    except Exception:statuses['balance']='unavailable'
    try:
        value=api.call('GET',REST+'/pods');rows=value.get('pods');require(type(rows) is list and len(rows)<=500)
        safe=[];identities=set()
        for row in rows:
            require(type(row) is dict and type(row.get('id')) is str and re.fullmatch('[A-Za-z0-9_-]{1,100}',row['id']) and row['id'] not in identities)
            identities.add(row['id']);gpu=row.get('gpu') if type(row.get('gpu')) is dict else {}
            state=row.get('status',row.get('desiredStatus'))
            safe.append({'id':row['id'],'name':label(row.get('name')),'status':state if state in ('RUNNING','STOPPED','EXITED','TERMINATED','CREATED','PENDING','STARTING') else 'unknown',
                'gpu_id':label(gpu.get('id')),'gpu_count':integer(gpu.get('count'),128),
                'hourly_usd':number(row.get('cost',row.get('costPerHr'))),
                'container_disk_gb':integer(row.get('disk',row.get('containerDiskInGb')),100000)})
        complete=set(value)=={'pods'}
        pods={'rows':safe,'observed_count':len(safe),'complete':complete,'absence_or_zero_charge_proven':False,
              'preexisting_pods_must_be_preserved':True}
        statuses['pods']='observed'
    except Exception:statuses['pods']='unavailable'
    try:
        value=api.call('GET',REST+CATALOG);rows=value.get('gpus');require(type(rows) is list and len(rows)<=500)
        safe=[];seen=set()
        for row in rows:
            require(type(row) is dict)
            if row.get('id') not in OBSERVED_GPU_IDS:continue
            require(row['id'] not in seen);seen.add(row['id'])
            stock=row.get('availability');price=(row.get('price') or {}).get('secure')
            safe.append({'gpu_id':row['id'],'secure_hourly_usd':number(price),'availability':stock if stock in ('NONE','LOW','MEDIUM','HIGH') else 'unknown',
                'gemma_profile_allowed':row['id'] in GEMMA_GPUS})
        offers={'cloud':'SECURE','gpu_count':1,'cuda_minimum':'12.8','rows':safe,'quote_does_not_guarantee_placement':True}
        statuses['offers']='observed'
    except Exception:statuses['offers']='unavailable'
    return {'version':1,'kind':'private_runpod_funding_inventory_v1','observed_at_utc':datetime.now(timezone.utc).isoformat(),
        'launch_id':launch,'probe_code_commit':commit,'endpoint_statuses':statuses,'funding':funding,'pods':pods,'offers':offers,
        'intended_gemma_profile':'gemma-26b-qlora-v1','model_calls':0,'gpu_creation_performed':False,
        'provider_resource_write_calls':0,'billing_or_secret_mutations':False,'google_api_calls':0}

def recipient(value):
    from nacl.public import PublicKey,SealedBox
    raw=base64.b64decode(value,validate=True);require(type(value) is str and len(raw)==32 and base64.b64encode(raw).decode()==value)
    box=SealedBox(PublicKey(raw));box.encrypt(b'recipient-validation');return raw,box
def seal(payload,public):
    key,box=recipient(public);raw=canon(payload);require(len(raw)<=524288)
    packed=gzip.compress(raw,mtime=0);cipher=box.encrypt(packed);encoded=base64.b64encode(cipher).decode();parts=(len(encoded)+31999)//32000
    events=[{'event':'private_qwq_gpu_observation','artifact_export_fragment':{'part':i,'parts':parts,'cipher_sha256':sha(cipher),'base64':encoded[i*32000:(i+1)*32000]}} for i in range(parts)]
    events.append({'event':'private_qwq_gpu_observation','artifact_export':{'kind':'private_runpod_funding_inventory_v1','run_id':os.environ.get('GITHUB_RUN_ID'),
        'launch_id':payload['launch_id'],'algorithm':'libsodium_sealed_box_curve25519xsalsa20poly1305','compression':'gzip',
        'public_key_sha256':sha(key),'raw_sha256':sha(raw),'raw_bytes':len(raw),'gzip_bytes':len(packed),'cipher_sha256':sha(cipher),'cipher_bytes':len(cipher),'base64_characters':len(encoded),'parts':parts}})
    require(all(len(canon(e))<49152 for e in events));return events
def main():
    launch=os.environ.get('HASLA_RUNPOD_READONLY_LAUNCH_ID','');commit=os.environ.get('GITHUB_SHA','')
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('GITHUB_REPOSITORY','').lower()=='haslaedu/haslalab.github.io'
        and re.fullmatch('[0-9a-f]{32}',launch) and re.fullmatch('[0-9a-f]{40}',commit) and os.environ.get('RUNPOD_API_KEY'))
    require(not any(os.environ.get(k) for k in ('WANDB_API_KEY','HF_TOKEN','GEMINI_API_KEY','OPENAI_API_KEY','DEEPSEEK_API_KEY')))
    public=os.environ.get('HASLA_EVAL_EXPORT_PUBLIC_KEY','');recipient(public)
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError()));signal.alarm(90)
    try:
        payload=collect(API(os.environ['RUNPOD_API_KEY']),launch,commit)
        for event in seal(payload,public):print(canon(event).decode(),flush=True)
        return 0
    finally:signal.alarm(0)
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:print('{"event":"private_qwq_gpu_observation_failed","failure_code":"fixed_runpod_readonly_probe_failed"}');raise SystemExit(1)

"""Fixed Pod bootstrap diagnostics, sanitized and sealed; GET/read-only only."""
import base64, gzip, hashlib, importlib, json, os, re, sys, time
from pathlib import Path
POD='zbhwdm2mm7h1m7'
RUN='41953551011'
COMMIT='2844cdbef7f99ba5e2e61c02b15c4e42d630cbae'
OBSERVER_SHA='8cb60526523a5baeebdb10040dc6692c4c8184d58b0c60dd297b9a39502deca5'
def require(value):
    if not value: raise ValueError('private_debug_export_rejected')
def canon(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def sanitize(text,env):
    text=str(text)[:8192]
    if re.search(r'(?i)docker\s+run|dockerargs|dockerentrypoint|--gpus|--entrypoint|--env\b|\s-e\s',text):return '[DOCKER_ARGUMENTS_REDACTED]'
    text=re.sub(r'-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----','[PRIVATE_KEY_REDACTED]',text,flags=re.S)
    secrets=sorted({v for k,v in env.items() if isinstance(v,str) and len(v)>=6 and
                    any(x in k.upper() for x in ('KEY','TOKEN','SECRET','PASSWORD'))},key=len,reverse=True)
    for value in secrets: text=text.replace(value,'[REDACTED]')
    text=re.sub(r'https?://[^\s<>]+','[URL]',text)
    text=re.sub(r'''(?i)\b(?:bearer\s+\S+|(?:[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*)['"]?\s*[:=]\s*['"]?[^\s,;]+)''',
                '[REDACTED]',text)
    return re.sub(r'\b(?:rp_|rpa_|wandb_)[A-Za-z0-9_-]{8,}','[REDACTED]',text)
def model_started(summary):
    return not isinstance(summary,dict) or any(summary.get(k) is not None for k in
        ('private_qwq_gpu_progress','private_qwq_gpu_result_json'))
def read_logs(diag,env,source,get,clock=time.monotonic):
    response=None; rows=[]; deadline=clock()+6; private_block=False
    try:
        with diag.worker.hard_wall(6),diag.resume._quiet():
            response=get(diag.parent.cloud.REST+'/pods/'+POD+'/logs',params={'source':source,'tail':60},
                stream=True,allow_redirects=False,timeout=(3,3),headers={'Authorization':'Bearer '+env['RUNPOD_API_KEY']})
            if response.status_code!=200:return {'state':'unavailable','rows':[]}
            for raw in diag.bounded_lines(response,deadline,clock):
                if len(rows)>=32:break
                if not raw.startswith(b'data:'):continue
                try:value=json.loads(raw[5:])
                except Exception:continue
                if isinstance(value,dict) and value.get('source')==source and isinstance(value.get('line'),str):
                    text=value['line']
                    if re.search(r'-----BEGIN .*PRIVATE KEY-----',text):private_block=True
                    if private_block:
                        if re.search(r'-----END .*PRIVATE KEY-----',text):private_block=False
                        continue
                    rows.append(sanitize(text,env))
        return {'state':'observed','rows':rows}
    except Exception:return {'state':'partial' if rows else 'unavailable','rows':rows}
    finally:
        if response is not None:response.close()
def collect(diag,env,services,get):
    pod=services.pod(POD,20)
    require(isinstance(pod,dict) and pod.get('id')==POD and pod.get('name')==diag.POD_NAME)
    safe=diag.pod_projection(pod)
    safe['lastStatusChange']=sanitize(pod.get('lastStatusChange',''),env)[:4096]
    safe['runtime_present']=isinstance(pod.get('runtime'),dict)
    try:services.private(); before=services.summary(RUN,10)
    except Exception:before=None
    logs={'system':read_logs(diag,env,'system',get)}
    skip=model_started(before)
    if not skip:
        logs['container']=read_logs(diag,env,'container',get)
        try:after=services.summary(RUN,10)
        except Exception:after=None
        skip=model_started(after) or any(re.search(r'(?i)<think>|</think>|\bevaluating\b|\bgenerating\b',line)
                                         for line in logs['container']['rows'])
    if skip:logs['container']={'state':'skipped_model_or_summary_unknown','rows':[]}
    return {'version':1,'kind':'private_qwq_bootstrap_diagnostic','run_id':RUN,'code_commit':COMMIT,
            'pod':safe,'logs':logs,'env_included':False,'docker_args_included':False,'model_calls':0}
def sealed_events(value,public):
    from nacl.public import PublicKey,SealedBox
    key=base64.b64decode(public,validate=True)
    require(len(key)==32 and base64.b64encode(key).decode()==public)
    raw=canon(value);require(len(raw)<=600000)
    zipped=gzip.compress(raw,mtime=0);cipher=SealedBox(PublicKey(key)).encrypt(zipped)
    encoded=base64.b64encode(cipher).decode();parts=(len(encoded)+31999)//32000
    events=[{'event':'private_qwq_gpu_observation','private_debug_fragment':{'part':i,'parts':parts,
        'cipher_sha256':sha(cipher),'base64':encoded[i*32000:(i+1)*32000]}} for i in range(parts)]
    events.append({'event':'private_qwq_gpu_observation','private_debug_export':{'version':1,'run_id':RUN,
        'code_commit':COMMIT,'pod_id':POD,'algorithm':'libsodium_sealed_box_curve25519xsalsa20poly1305',
        'compression':'gzip','public_key_sha256':sha(key),'raw_sha256':sha(raw),'raw_bytes':len(raw),
        'gzip_bytes':len(zipped),'cipher_sha256':sha(cipher),'cipher_bytes':len(cipher),
        'base64_characters':len(encoded),'parts':parts}})
    require(all(len(canon(e))<48*1024 for e in events));return events
def main():
    try:
        root=Path(sys.argv[1]).resolve();require(len(sys.argv)==2)
        require(sha((root/'private_qwq_gpu_observe.py').read_bytes())==OBSERVER_SHA)
        sys.path.insert(0,str(root));diag=importlib.import_module('private_qwq_gpu_observe')
        require(diag.TARGET==RUN and diag.TARGET_COMMIT==COMMIT)
        for name,pin in diag.HELPER_PINS.items():require(sha((root/name).read_bytes())==pin)
        public=os.environ['HASLA_DEBUG_EXPORT_PUBLIC_KEY']
        sealed_events({'recipient_probe':True},public)
        services=diag.parent.Services(os.environ)
        value=collect(diag,os.environ,services,diag.parent.cloud.requests.get)
        for event in sealed_events(value,public):print(canon(event).decode(),flush=True)
        return 0
    except Exception:
        print('{"event":"private_qwq_gpu_observation","private_debug_export_failed":true}');return 1
if __name__=='__main__':raise SystemExit(main())

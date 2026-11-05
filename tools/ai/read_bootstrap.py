"""Fixed V4 PRIVATE W&B discovery; sealed evidence only, no provider/model calls."""
import base64, contextlib, gzip, hashlib, json, os, re, signal, tempfile, urllib.request
from pathlib import Path
RUN='41961432873'; COMMIT='f335ea007ce81720dd90a903586292f0a0b7da0c'; NONCE='65686709803606c09f7ad17c01de16fa'
ENTITY='mimgyuson-haslaedu'; PROJECT='hasla-ai-private-training'; NAME='hasla-qwq-bootstrap-'+RUN
REFERENCE=ENTITY+'/'+PROJECT+'/'+NAME+':v0'
TERMINAL_PROOF_SHA='c2bde2b98d299b63237c7b07c2b2cba46e9417b861ab9d03514f28bf2bbd9d3e'
def require(ok):
    if not ok: raise ValueError('fixed_private_evidence_invalid')
def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def sanitize(text,env):
    for key in env:
        if env[key] and (len(env[key])>=4 or re.search('KEY|TOKEN|SECRET|PASSWORD|AUTH|COOKIE',key,re.I)): text=text.replace(env[key],'[REDACTED]')
    text=re.sub(r'-----BEGIN [^-]+-----[\s\S]*?-----END [^-]+-----','[REDACTED_PEM]',text)
    text=re.sub(r'https?://[^\s\"\'<>]+','[REDACTED_URL]',text)
    text=re.sub(r'(?im)^.*(?:dockerargs|docker_args|os\.environ|HASLA_QWQ_GPU_EVAL_JOB|WANDB_API_KEY|^\s*[A-Z_][A-Z0-9_]*\s*=).*$','[REDACTED_ENV_LINE]',text)
    text=re.sub(r'(?i)(bearer\s+)[^\s\"\']+|\b(?:hf_|sk-|rpa_)[A-Za-z0-9_-]+','[REDACTED_SECRET]',text)
    text=re.sub(r'(?i)((?:api[_-]?key|token|secret|password|authorization|cookie)[\"\']?\s*[:=]\s*)([\"\']).*?\2',r'\1[REDACTED]',text)
    return text.encode('utf8','replace')[-65536:].decode('utf8','ignore')
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args): return None
def private_query(env):
    query='query($e:String!,$p:String!,$r:String!){project(name:$p,entityName:$e){name access run(name:$r){name state summaryMetrics}}}'
    auth=base64.b64encode(('api:'+env['WANDB_API_KEY']).encode()).decode()
    request=urllib.request.Request('https://api.wandb.ai/graphql',data=canonical({'query':query,'variables':{'e':ENTITY,'p':PROJECT,'r':NAME}}),headers={'Authorization':'Basic '+auth,'Content-Type':'application/json'})
    with urllib.request.build_opener(NoRedirect()).open(request,timeout=20) as response:
        require(response.status==200); raw=response.read(65537); require(len(raw)<=65536)
    value=json.loads(raw); require(type(value) is dict and not value.get('errors'))
    project=(value.get('data') or {}).get('project'); require(type(project) is dict and project.get('name')==PROJECT and project.get('access')=='PRIVATE')
    return project.get('run')
def artifact_files(api,root):
    try: artifact=api.artifact(REFERENCE,type='bootstrap-diagnostic')
    except Exception: return {'state':'absent_or_unavailable','files':[]}
    require(artifact.qualified_name==REFERENCE and artifact.type=='bootstrap-diagnostic' and artifact.state=='COMMITTED' and not getattr(artifact,'is_link',False))
    meta=artifact.metadata; require(type(meta) is dict and set(meta)=={'private','run_id','code_commit','model_calls','files'} and meta['private'] is True and meta['run_id']==RUN and meta['code_commit']==COMMIT and type(meta['model_calls']) is int and meta['model_calls']==0)
    rows=meta['files']; require(type(rows) is list and len(rows)==2 and [r.get('name') for r in rows if type(r) is dict]==['diagnostics.json','traceback.txt'])
    entries=artifact.manifest.entries; require(type(entries) is dict and set(entries)=={'diagnostics.json','traceback.txt'})
    creator=artifact.logged_by(); require(creator is not None and creator.id==NAME and creator.entity==ENTITY and creator.project==PROJECT)
    files=[]; manifest_diagnostics=[]
    for row in rows:
        require(set(row)=={'name','bytes','sha256'} and type(row['bytes']) is int and 0<=row['bytes']<=32768 and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}',row['sha256']))
        entry=entries[row['name']]; require(entry.path==row['name'] and entry.size==row['bytes'] and not getattr(entry,'ref',None))
        fresh=artifact.get_entry(row['name']); require(fresh.path==row['name'] and fresh.size==row['bytes'] and not getattr(fresh,'ref',None))
        path=Path(fresh.download(root=str(root),skip_cache=True)); require(path.absolute()==(root/row['name']).absolute() and not path.is_symlink() and path.is_file() and path.resolve()==(root/row['name']).resolve() and path.stat().st_size==row['bytes'])
        raw=path.read_bytes(); require(sha(raw)==row['sha256'])
        md5=base64.b64encode(hashlib.md5(raw).digest()).decode()
        digest=getattr(entry,'digest',None); fresh_digest=getattr(fresh,'digest',None)
        require(all(d is None or type(d) is str and re.fullmatch('[A-Za-z0-9+/=:_-]{1,160}',d) for d in (digest,fresh_digest)))
        manifest_diagnostics.append({'path':str(entry.path),'size':entry.size,'digest':digest,'ref_present':bool(getattr(entry,'ref',None)),'fresh_entry_digest':fresh_digest,'computed_md5_base64':md5,'computed_sha256':sha(raw),'manifest_digest_matches_md5':digest==md5,'fresh_digest_matches_md5':fresh_digest==md5})
        if row['name']=='diagnostics.json':
            body=json.loads(raw); require(type(body) is dict and body.get('run_id')==RUN and body.get('code_commit')==COMMIT and body.get('kind')=='private_qwq_bootstrap_diagnostic' and body.get('model_calls')==0)
        else: require(len(raw)<=12288); raw.decode('utf8')
        files.append({**row,'base64':base64.b64encode(raw).decode()})
    require({p.name for p in root.iterdir()}=={'diagnostics.json','traceback.txt'})
    return {'state':'committed_verified','reference':REFERENCE,'metadata':meta,'files':files,'manifest_diagnostics':manifest_diagnostics,'parent_receipt_fabricated':False}
def discover(api,query,env):
    row=query(env)
    result={'version':1,'kind':'private_qwq_bootstrap_discovery','run_id':RUN,'code_commit':COMMIT,'launch_id':NONCE,'terminal_proof_sha256':TERMINAL_PROOF_SHA,'private_project_verified':True,'parent_bootstrap_receipt_present':False,'run_state':'absent','artifact':{'state':'not_queried','files':[]},'output_log':None,'model_calls':0,'provider_calls':0}
    if row is None: return result
    require(type(row) is dict and row.get('name')==NAME)
    result['run_state']=row.get('state') if row.get('state') in ('running','finished','failed','crashed','killed','pending') else 'other'
    summary=row.get('summaryMetrics') or {}; summary=json.loads(summary) if type(summary) is str else summary
    require(type(summary) is dict); candidate=summary.get('private_qwq_gpu_bootstrap_result_json')
    result['summary_observation']={'diagnostic_summary_present':candidate is not None,'summary_sha256':sha(canonical(summary))}
    with tempfile.TemporaryDirectory(prefix='bootstrap-read-') as directory:
        root=Path(directory)
        try: result['artifact']=artifact_files(api,root)
        except Exception: result['artifact']={'state':'rejected_or_unavailable','files':[]}
    if result['artifact']['state']!='committed_verified':
        try:
            run=api.run(ENTITY+'/'+PROJECT+'/'+NAME); require(run.id==NAME and run.entity==ENTITY and run.project==PROJECT)
            files=list(run.files(names=['output.log'],per_page=2)); require(len(files)<=1)
            if files:
                file=files[0]; require(file.name=='output.log' and type(file.size) is int and 0<=file.size<=65536)
                with tempfile.TemporaryDirectory(prefix='bootstrap-output-') as directory:
                    file.download(root=directory,replace=False,exist_ok=False); path=Path(directory)/'output.log'
                    require(path.is_file() and not path.is_symlink() and path.stat().st_size<=65536)
                    result['output_log']={'name':'output.log','sanitized_text':sanitize(path.read_bytes().decode('utf8','replace'),env)}
        except Exception: result['output_log_state']='absent_or_unavailable'
    query(env)  # Recheck PRIVATE before allowing any sealed publication.
    return result
def sealed_events(value,text):
    from nacl.public import PublicKey,SealedBox
    public=base64.b64decode(text,validate=True); require(len(public)==32 and base64.b64encode(public).decode()==text)
    raw=canonical(value); require(len(raw)<=196608); packed=gzip.compress(raw,mtime=0); cipher=SealedBox(PublicKey(public)).encrypt(packed); encoded=base64.b64encode(cipher).decode(); parts=(len(encoded)+31999)//32000
    meta={'version':1,'algorithm':'libsodium_sealed_box_curve25519xsalsa20poly1305','compression':'gzip','run_id':RUN,'code_commit':COMMIT,'public_key_sha256':sha(public),'raw_sha256':sha(raw),'raw_bytes':len(raw),'gzip_bytes':len(packed),'cipher_bytes':len(cipher),'cipher_sha256':sha(cipher),'base64_characters':len(encoded),'parts':parts}
    events=[{'event':'private_qwq_gpu_observation','artifact_export_fragment':{'part':i,'parts':parts,'cipher_sha256':sha(cipher),'base64':encoded[i*32000:(i+1)*32000]}} for i in range(parts)]; events.append({'event':'private_qwq_gpu_observation','artifact_export':meta}); return events
def main():
    try:
        signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError())); signal.alarm(170)
        require(os.environ.get('WANDB_ENTITY')==ENTITY and os.environ.get('WANDB_API_KEY') and os.environ.get('WANDB_BASE_URL','https://api.wandb.ai').rstrip('/')=='https://api.wandb.ai')
        require(not any(('RUNPOD' in k.upper() and ('KEY' in k.upper() or 'TOKEN' in k.upper())) for k in os.environ))
        public=os.environ.get('HASLA_EVAL_EXPORT_PUBLIC_KEY',''); sealed_events({'recipient_check':True},public)
        with open(os.devnull,'w') as quiet,contextlib.redirect_stdout(quiet),contextlib.redirect_stderr(quiet):
            import wandb
            value=discover(wandb.Api(api_key=os.environ['WANDB_API_KEY'],timeout=20),private_query,os.environ)
            events=sealed_events(value,public)
        for event in events: print(canonical(event).decode(),flush=True)
        return 0
    except Exception: print('{"event":"private_qwq_gpu_observation_failed","failure_code":"fixed_bootstrap_read_failed"}'); return 1
    finally: signal.alarm(0)
if __name__=='__main__': raise SystemExit(main())

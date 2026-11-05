"""Inline-only private bootstrap diagnostics; no model or provider operations."""


def bootstrap_diagnostic_source():
    return r'''
import base64, contextlib, hashlib, json, os, re, signal, subprocess, sys, tempfile, traceback
from pathlib import Path

CORE = ('torch','transformers','unsloth','unsloth_zoo','peft','bitsandbytes','trl')
ERRORS = {'AssertionError','ImportError','ModuleNotFoundError','RuntimeError','ValueError','TypeError','AttributeError','OSError','TimeoutExpired','TimeoutError','ValidationError','UsageError','CommError','AuthenticationError','HTTPError','SSLError','ConnectionError','VerificationError','ResumeError'}
ENTITY, PROJECT = 'mimgyuson-haslaedu', 'hasla-ai-private-training'
VERSION = r'[A-Za-z0-9.+_-]{1,100}'
PHASE = 'job_validation'
HF_CREDENTIALS = {'HF_TOKEN','HF_API_TOKEN','HUGGING_FACE_HUB_TOKEN','HUGGINGFACE_TOKEN','HUGGINGFACEHUB_API_TOKEN','HUGGINGFACE_API_KEY','HF_API_KEY','HF_HUB_TOKEN'}

def sanitize_environment(env):
    names = [key for key in env if key.upper() in HF_CREDENTIALS or ('RUNPOD' in key.upper() and any(word in key.upper() for word in ('KEY','TOKEN')))]
    for key in names: del env[key]
    return len(names)

def require(ok):
    if not ok: raise ValueError('bootstrap_diagnostic_invalid')

def sanitize(text, env):
    for value in sorted({v for k,v in env.items() if isinstance(v,str) and v and (len(v)>=4 or re.search(r'KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTH|COOKIE',k,re.I))},key=len,reverse=True):
        text = text.replace(value, '[REDACTED]')
    text = re.sub(r'-----BEGIN [^-]+-----[\s\S]*?-----END [^-]+-----','[REDACTED_PEM]',text)
    text = re.sub(r'https?://[^\s\"\'<>]+','[REDACTED_URL]',text)
    text = re.sub(r'(?i)(bearer\s+)[^\s\"\']+|\b(?:hf_|sk-|rpa_)[A-Za-z0-9_-]+','[REDACTED_SECRET]',text)
    text = re.sub(r'(?im)^.*(?:dockerargs|docker_args|os\.environ|HASLA_QWQ_GPU_EVAL_JOB).*$','[REDACTED_ENV_LINE]',text)
    text = re.sub(r'(?i)((?:api[_-]?key|token|secret|password|credential|authorization|cookie)[\"\']?\s*[:=]\s*)([\"\']).*?\2',r'\1[REDACTED]',text)
    text = re.sub(r'(?i)((?:api[_-]?key|token|secret|password|credential|authorization|cookie)\s*[:=]\s*)[^\s,;]+',r'\1[REDACTED]',text)
    return text.encode('utf8','replace')[-4096:].decode('utf8','ignore')

def probe(stage, root, runner=subprocess.run):
    output, log = root/(stage+'.json'), root/(stage+'.log')
    common = 'import json,sys; from pathlib import Path; from importlib.metadata import version; names='+repr(CORE)+'; out=Path(sys.argv[1]); '
    if stage == 'core_compare':
        code = common+"before=json.loads(Path('/workspace/qwq-eval-core.json').read_text()); after={n:version(n) for n in names}; out.write_text(json.dumps({'before':before,'after':after})); assert before==after"
    elif stage == 'module_import':
        code = 'import unsloth, bitsandbytes, peft, torch, wandb; '+common+"out.write_text(json.dumps({'versions':{n:version(n) for n in names},'wandb':version('wandb')})); assert version('wandb')=='0.31.0'"
    else:
        require(stage == 'GPU_check')
        code = "import torch; "+common+"available=torch.cuda.is_available(); count=torch.cuda.device_count(); name=torch.cuda.get_device_name(0) if available and count else None; value={'available':available,'count':count,'name':name if name in (None,'NVIDIA A40') else 'other','compiled_cuda':torch.version.cuda}; out.write_text(json.dumps(value)); assert available and count==1 and name=='NVIDIA A40'"
    code += '; import os; os._exit(0)'
    with log.open('wb') as handle:
        try:
            result = runner([sys.executable,'-c',code,str(output)],stdout=handle,stderr=subprocess.STDOUT,timeout=30,check=False)
            exit_code = result.returncode if type(result.returncode) is int and 0<=result.returncode<=255 else 255
            kind = None
        except Exception as error:
            exit_code, kind = 255, type(error).__name__ if type(error).__name__ in ERRORS else 'OtherError'
    with log.open('rb') as handle: handle.seek(max(0,log.stat().st_size-8192)); raw=handle.read(8192)
    text = sanitize(raw.decode('utf8','replace'),os.environ)
    if exit_code and kind is None:
        matches = re.findall(r'(?m)^([A-Za-z][A-Za-z0-9]*Error|TimeoutExpired):',text)
        kind = matches[-1] if matches and matches[-1] in ERRORS else 'OtherError'
    data = json.loads(output.read_bytes()) if output.is_file() and output.stat().st_size<=8192 else None
    if data is not None:
        if stage in ('core_compare','module_import'):
            require(type(data) is dict and set(data)==({'before','after'} if stage=='core_compare' else {'versions','wandb'}))
            maps = (data['before'],data['after']) if stage=='core_compare' else (data['versions'],)
            require(all(type(m) is dict and set(m)==set(CORE) and all(type(v) is str and re.fullmatch(VERSION,v) for v in m.values()) for m in maps))
            if stage=='module_import': require(data['wandb']=='0.31.0')
        else:
            require(type(data) is dict and set(data)=={'available','count','name','compiled_cuda'} and type(data['available']) is bool and type(data['count']) is int and 0<=data['count']<=16 and data['name'] in (None,'NVIDIA A40','other') and (data['compiled_cuda'] is None or type(data['compiled_cuda']) is str and re.fullmatch(VERSION,data['compiled_cuda'])))
    return {'stage':stage,'status':'passed' if exit_code==0 and data is not None else 'failed','exit_code':exit_code,'exception_type':kind,'observations':data}, text

def diagnose(root, runner=subprocess.run):
    stages, logs = [], []
    for stage in ('core_compare','module_import','GPU_check'):
        try: row, text = probe(stage,root,runner)
        except Exception as error:
            kind = type(error).__name__ if type(error).__name__ in ERRORS else 'OtherError'
            row, text = {'stage':stage,'status':'failed','exit_code':255,'exception_type':kind,'observations':None}, sanitize(traceback.format_exc(),os.environ)
        stages.append(row)
        if text: logs.append('['+stage+']\n'+text)
    return stages, '\n'.join(logs).encode('utf8','replace')[-12288:].decode('utf8','ignore')

def publish(job, root, clients):
    global PHASE
    PHASE = 'clients'
    api, privacy, sdk = clients(os.environ)
    def private(): require(privacy(ENTITY)=={'entity':ENTITY,'project':PROJECT,'access':'PRIVATE'})
    PHASE = 'project_privacy'
    private()
    name = 'hasla-qwq-bootstrap-'+job['run_id']
    PHASE = 'sdk_init'
    run = sdk.init(entity=ENTITY,project=PROJECT,id=name,name=name,resume='never',job_type='bootstrap-diagnostic',settings=sdk.Settings(init_timeout=20,console='off',disable_code=True,disable_git=True))
    try:
        PHASE = 'local_probes'
        stages, trace = diagnose(root)
        value = {'version':1,'kind':'private_qwq_bootstrap_diagnostic','run_id':job['run_id'],'code_commit':job['code_commit'],'model_calls':0,'optimizer_steps':0,'stages':stages,'passed':len(stages)==3 and all(r['status']=='passed' for r in stages)}
        (root/'diagnostics.json').write_text(json.dumps(value,sort_keys=True,allow_nan=False),encoding='utf8'); (root/'traceback.txt').write_text(trace,encoding='utf8')
        files = [{'name':n,'bytes':(root/n).stat().st_size,'sha256':hashlib.sha256((root/n).read_bytes()).hexdigest()} for n in ('diagnostics.json','traceback.txt')]
        PHASE = 'artifact_create'
        private()
        artifact = sdk.Artifact(name,type='bootstrap-diagnostic',metadata={'private':True,'run_id':job['run_id'],'code_commit':job['code_commit'],'model_calls':0,'files':files})
        for row in files: artifact.add_file(str(root/row['name']),name=row['name'])
        PHASE = 'artifact_wait'
        saved = run.log_artifact(artifact).wait(timeout=30)
        PHASE = 'artifact_verify'
        require(saved.state=='COMMITTED' and saved.type=='bootstrap-diagnostic' and saved.metadata==artifact.metadata and re.fullmatch(re.escape(ENTITY+'/'+PROJECT+'/'+name)+r':v[0-9]+',saved.qualified_name) and set(saved.manifest.entries)=={r['name'] for r in files})
        for row in files:
            entry = saved.manifest.entries[row['name']]
            require(entry.size==row['bytes'] and not getattr(entry,'ref',None) and entry.digest==base64.b64encode(hashlib.md5((root/row['name']).read_bytes()).digest()).decode())
        private()
        result = {'version':1,'run_id':job['run_id'],'code_commit':job['code_commit'],'status':'passed' if value['passed'] else 'failed','stages':[{'stage':r['stage'],'status':r['status'],'exit_code':r['exit_code'],'exception_type':r['exception_type']} for r in stages],'artifact':saved.qualified_name,'files':files,'model_calls':0}
        PHASE = 'summary'
        run.summary.update({'private_qwq_gpu_bootstrap_result_json':json.dumps(result,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)})
        return 0 if value['passed'] else 1
    finally:
        primary_failure = sys.exc_info()[0] is not None
        try: run.finish()
        except Exception:
            if not primary_failure:
                PHASE = 'finish'
                raise

def main():
    global PHASE
    sanitize_environment(os.environ)
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('bootstrap_deadline'))); signal.alarm(180)
    try:
        job = json.loads(os.environ['HASLA_QWQ_GPU_EVAL_JOB'])
        require(type(job) is dict and re.fullmatch(r'[1-9][0-9]{5,19}',job.get('run_id','')) and re.fullmatch(r'[0-9a-f]{40}',job.get('code_commit','')))
        from private_qwq_gpu_eval import private_clients
        with tempfile.TemporaryDirectory(prefix='qwq-bootstrap-') as directory, open(os.devnull,'w') as quiet, contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
            return publish(job,Path(directory),private_clients)
    except Exception as error:
        kind = type(error).__name__ if type(error).__name__ in ERRORS else 'OtherError'
        print(json.dumps({'event':'private_qwq_gpu_bootstrap_diagnostic','status':'failed','phase':PHASE,'exception_type':kind,'exit_code':1},sort_keys=True))
        return 1
    finally: signal.alarm(0)

if __name__=='__main__': raise SystemExit(main())
'''.lstrip()

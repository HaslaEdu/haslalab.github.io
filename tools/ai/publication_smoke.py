"""FREE CPU-only synthetic W&B publication smoke; no models/providers/data."""
import base64,contextlib,hashlib,importlib.metadata,json,os,re,signal,sys,tempfile,time,urllib.request
from pathlib import Path
ENTITY='mimgyuson-haslaedu';PROJECT='hasla-ai-private-training';PUBLIC=sys.stdout;STAGE='starting';FAILED_STAGE=None;START=time.monotonic()
ERRORS={'AssertionError','ImportError','ModuleNotFoundError','RuntimeError','ValueError','TypeError','AttributeError','OSError','TimeoutError','WaitTimeoutError','CommError','UsageError','ValidationError'}
class SmokeError(ValueError): pass
def require(ok,code):
    if not ok: raise SmokeError(code)
def mark(stage):
    global STAGE
    STAGE=stage; print(json.dumps({'event':'private_qwq_publication_smoke','stage':stage,'status':'reached','elapsed_seconds':round(min(1000000,max(0,time.monotonic()-START)),3)},sort_keys=True),file=PUBLIC,flush=True)
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args): return None
def private(env):
    auth=base64.b64encode(('api:'+env['WANDB_API_KEY']).encode()).decode()
    request=urllib.request.Request('https://api.wandb.ai/graphql',data=json.dumps({'query':'query($e:String!,$p:String!){project(name:$p,entityName:$e){name access}}','variables':{'e':ENTITY,'p':PROJECT}}).encode(),headers={'Authorization':'Basic '+auth,'Content-Type':'application/json'})
    with urllib.request.build_opener(NoRedirect()).open(request,timeout=20) as response:
        raw=response.read(65537);require(response.status==200 and len(raw)<=65536,'private_response_invalid')
    value=json.loads(raw);require(type(value) is dict and not value.get('errors'),'private_query_failed')
    project=(value.get('data') or {}).get('project');require(type(project) is dict and project.get('name')==PROJECT and project.get('access')=='PRIVATE','private_project_required')
    return {'entity':ENTITY,'project':PROJECT,'access':'PRIVATE'}
def execute(sdk,run_id,commit,root,privacy):
    global FAILED_STAGE
    failed=False
    name='hasla-qwq-publication-smoke-'+run_id
    def check(): require(privacy()=={'entity':ENTITY,'project':PROJECT,'access':'PRIVATE'},'private_project_required')
    mark('private_before_init');check();mark('sdk_init')
    run=sdk.init(entity=ENTITY,project=PROJECT,id=name,name=name,resume='never',job_type='publication-smoke',settings=sdk.Settings(init_timeout=20,console='off',disable_code=True,disable_git=True))
    try:
        mark('synthetic_files')
        value={'version':1,'kind':'publication_smoke','run_id':run_id,'code_commit':commit,'model_calls':0,'optimizer_steps':0,'synthetic_only':True}
        (root/'diagnostics.json').write_text(json.dumps(value,sort_keys=True),encoding='utf8');(root/'traceback.txt').write_text('SYNTHETIC PUBLICATION SMOKE ONLY\n',encoding='utf8')
        files=[{'name':n,'bytes':(root/n).stat().st_size,'sha256':hashlib.sha256((root/n).read_bytes()).hexdigest()} for n in ('diagnostics.json','traceback.txt')]
        mark('private_before_artifact');check();mark('artifact_create')
        artifact=sdk.Artifact(name,type='bootstrap-diagnostic',metadata={'private':True,'run_id':run_id,'code_commit':commit,'model_calls':0,'files':files})
        for row in files: artifact.add_file(str(root/row['name']),name=row['name'])
        mark('artifact_log');pending=run.log_artifact(artifact);mark('artifact_wait');saved=pending.wait(timeout=30)
        mark('validate_state');require(saved.state=='COMMITTED','artifact_state_invalid')
        mark('validate_type');require(saved.type=='bootstrap-diagnostic','artifact_type_invalid')
        mark('validate_metadata');require(saved.metadata==artifact.metadata,'artifact_metadata_invalid')
        mark('validate_name');require(re.fullmatch(re.escape(ENTITY+'/'+PROJECT+'/'+name)+r':v[0-9]+',saved.qualified_name),'artifact_name_invalid')
        mark('validate_entries');require(set(saved.manifest.entries)=={r['name'] for r in files},'artifact_entries_invalid')
        for row in files:
            entry=saved.manifest.entries[row['name']]
            mark('validate_size_'+row['name'].split('.')[0]);require(entry.size==row['bytes'],'artifact_size_invalid')
            mark('validate_ref_'+row['name'].split('.')[0]);require(not getattr(entry,'ref',None),'artifact_ref_invalid')
            mark('validate_digest_'+row['name'].split('.')[0]);require(entry.digest==base64.b64encode(hashlib.md5((root/row['name']).read_bytes()).digest()).decode(),'artifact_digest_invalid')
        mark('private_before_summary');check();mark('summary_update')
        result={'version':1,'kind':'publication_smoke','run_id':run_id,'code_commit':commit,'status':'passed','stages':[{'stage':s,'status':'passed','exit_code':0,'exception_type':None} for s in ('core_compare','module_import','GPU_check')],'artifact':saved.qualified_name,'files':files,'model_calls':0,'synthetic_only':True}
        run.summary.update({'private_qwq_gpu_bootstrap_result_json':result})
        mark('summary_returned');return result
    except BaseException:
        failed=True;FAILED_STAGE=STAGE;raise
    finally:
        try: mark('run_finish');run.finish();mark('finish_returned')
        except Exception:
            if not failed: raise
            mark('finish_failed_after_primary_error')
def main():
    try:
        signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError()));signal.alarm(180)
        run_id=os.environ.get('GITHUB_RUN_ID','');commit=os.environ.get('GITHUB_SHA','')
        require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and re.fullmatch('[1-9][0-9]{5,19}',run_id) and re.fullmatch('[0-9a-f]{40}',commit),'ephemeral_cpu_runner_required')
        require(os.environ.get('WANDB_ENTITY')==ENTITY and os.environ.get('WANDB_API_KEY') and os.environ.get('WANDB_BASE_URL','https://api.wandb.ai').rstrip('/')=='https://api.wandb.ai','wandb_credentials_invalid')
        require(not any('RUNPOD' in k.upper() and ('KEY' in k.upper() or 'TOKEN' in k.upper()) for k in os.environ),'provider_credential_forbidden')
        with tempfile.TemporaryDirectory(prefix='qwq-publication-smoke-') as directory,open(os.devnull,'w') as quiet,contextlib.redirect_stdout(quiet),contextlib.redirect_stderr(quiet):
            mark('sdk_import');require(importlib.metadata.version('wandb')=='0.31.0','sdk_version_invalid');import wandb
            mark('private_clients');private(os.environ);mark('sdk_api');wandb.Api(api_key=os.environ['WANDB_API_KEY'],timeout=60)
            execute(wandb,run_id,commit,Path(directory),lambda:private(os.environ))
        mark('completed');return 0
    except Exception as error:
        kind=type(error).__name__ if type(error).__name__ in ERRORS else 'OtherError'
        code=str(error) if type(error) is SmokeError else 'sdk_operation_failed'
        print(json.dumps({'event':'private_qwq_publication_smoke','status':'failed','stage':FAILED_STAGE or STAGE,'exception_type':kind,'failure_code':code,'elapsed_seconds':round(min(1000000,max(0,time.monotonic()-START)),3)},sort_keys=True),file=PUBLIC,flush=True);return 1
    finally: signal.alarm(0)
if __name__=='__main__':raise SystemExit(main())

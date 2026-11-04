"""One bounded private Gemma job using Vertex managed metadata ADC only.

Packages/models must already be accessible in the pinned runtime. No install,
resource creation/deletion, service-account key, provider API key, deployment or
model promotion exists here. --preflight reads inputs without a GPU or upload.
"""
import argparse
import base64
import hashlib
import importlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote,urlencode

KIND='gcp_gemma_training_v1'
BUCKET='hasla-training'
PROJECT='project-hasla'
MACHINE='a2-ultragpu-1g'
META='http://metadata.google.internal/computeMetadata/v1/'
STORAGE='https://storage.googleapis.com'
CODE_FILES=('gcp_gemma_worker.py','train_lora.py','role_config.py','private_pod_train.py',
            'private_verify_adapter.py','private_dual_run.py','private_corpus_run.py','training_budget.py')
DEPENDENCIES=('torch','unsloth','unsloth_zoo','transformers','trl','datasets','peft')
MAX_INPUT=16*1024**2
MAX_JSON=1024**2
SHA=re.compile(r'[a-f0-9]{64}\Z')
ERRORS=frozenset(('manifest_invalid','unexpected_credential','private_workspace_required','code_pin_mismatch',
    'dependency_profile_mismatch','metadata_unavailable','runtime_identity_mismatch','metadata_token_invalid',
    'bucket_metadata_unavailable','bucket_privacy_unverified','source_metadata_invalid','source_transfer_failed',
    'source_integrity_failed','source_records_invalid','gpu_contract_failed','insufficient_training_time',
    'training_process_failed','training_timeout','training_report_invalid','weights_unverified','upload_failed',
    'upload_integrity_failed','deadline_reached','cancelled','worker_failed'))


class WorkerError(ValueError):
    def __init__(self,code):
        self.code=code if code in ERRORS else 'worker_failed';super().__init__(self.code)


def require(value,code):
    if not value:raise WorkerError(code)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf8')


def sha_file(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def strict_json(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            require(key not in result,'manifest_invalid');result[key]=value
        return result
    def invalid(_value):raise WorkerError('manifest_invalid')
    try:return json.loads(raw,object_pairs_hook=unique,parse_constant=invalid)
    except WorkerError:raise
    except Exception:raise WorkerError('manifest_invalid') from None


def credentials(env):
    explicit={'GOOGLE_APPLICATION_CREDENTIALS','GOOGLE_AUTH_ACCESS_TOKEN','CLOUDSDK_AUTH_ACCESS_TOKEN',
        'GCP_SA_KEY','GITHUB_TOKEN','GH_TOKEN','GH_ENTERPRISE_TOKEN','GITHUB_ENTERPRISE_TOKEN',
        'RUNPOD_TOKEN','WANDB_TOKEN','HF_TOKEN','HUGGING_FACE_HUB_TOKEN','HUGGINGFACE_HUB_TOKEN','HUGGINGFACEHUB_API_TOKEN'}
    require(not any(value and (key in explicit or re.search(r'(?:API_KEY|ACCESS_TOKEN|PRIVATE_KEY|SECRET|PASSWORD)$',key)
                or key.startswith(('WANDB_API','RUNPOD_API','HF_API','HUGGINGFACE_API')))
                for key,value in env.items()),'unexpected_credential')


def manifest_from_env(env):
    raw=env.get('HASLA_GCP_GEMMA_MANIFEST','')
    require(isinstance(raw,str) and 0<len(raw.encode())<=65536,'manifest_invalid');value=strict_json(raw)
    fields={'version','kind','run_id','project_id','project_number','service_account_email','bucket','prefix',
        'machine_type','runtime_seconds','upload_grace_seconds','dataset_version','code_sha256','dependency_versions','inputs',
        'budget','privacy_probe'}
    require(isinstance(value,dict) and set(value)==fields and type(value['version']) is int and value['version']==1
            and value['kind']==KIND,'manifest_invalid')
    run=value['run_id'];number=value['project_number']
    require(isinstance(run,str) and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}',run)
        and isinstance(number,str) and re.fullmatch(r'[1-9][0-9]{0,19}',number),'manifest_invalid')
    require(value['project_id']==PROJECT and value['bucket']==BUCKET and value['machine_type']==MACHINE
        and value['prefix']=='hasla-ai/gemma/'+run
        and value['service_account_email']=='service-'+number+'@gcp-sa-aiplatform-cc.iam.gserviceaccount.com','manifest_invalid')
    require(type(value['runtime_seconds']) is int and 600<=value['runtime_seconds']<=1800
        and type(value['upload_grace_seconds']) is int and value['upload_grace_seconds']==180,'manifest_invalid')
    require(isinstance(value['dataset_version'],str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',value['dataset_version']),
        'manifest_invalid')
    budget=value['budget']
    require(isinstance(budget,dict) and set(budget)=={'authorized_budget_krw','prior_closed_upper_krw',
        'other_reserved_upper_krw','job_reserved_upper_krw','reserve_krw'}
        and all(type(amount) is int and amount>=0 for amount in budget.values())
        and budget['authorized_budget_krw']==100000 and budget['job_reserved_upper_krw']==15000
        and budget['reserve_krw']==5000
        and sum(budget[key] for key in ('prior_closed_upper_krw','other_reserved_upper_krw','job_reserved_upper_krw','reserve_krw'))<=100000,
        'manifest_invalid')
    probe=value['privacy_probe']
    require(isinstance(probe,dict) and set(probe)=={'name','generation','bytes','sha256'}
        and probe['name']=='privacy-probe.bin' and type(probe['bytes']) is int and probe['bytes']==32
        and isinstance(probe['generation'],str) and re.fullmatch(r'[1-9][0-9]{0,24}',probe['generation'])
        and isinstance(probe['sha256'],str) and SHA.fullmatch(probe['sha256']),'manifest_invalid')
    pins=value['code_sha256'];versions=value['dependency_versions']
    require(isinstance(pins,dict) and set(pins)==set(CODE_FILES)
        and all(isinstance(v,str) and SHA.fullmatch(v) for v in pins.values()),'manifest_invalid')
    require(isinstance(versions,dict) and set(versions)==set(DEPENDENCIES)
        and all(isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9_.+!-]{1,120}',v) for v in versions.values()),'manifest_invalid')
    require(isinstance(value['inputs'],dict) and set(value['inputs'])=={'train','validation'},'manifest_invalid')
    for split,item in value['inputs'].items():
        require(isinstance(item,dict) and set(item)=={'name','generation','bytes','sha256','records'}
            and item['name']==split+'.chat.jsonl' and isinstance(item['generation'],str)
            and re.fullmatch(r'[1-9][0-9]{0,24}',item['generation'])
            and type(item['bytes']) is int and 0<item['bytes']<=MAX_INPUT
            and isinstance(item['sha256'],str) and SHA.fullmatch(item['sha256'])
            and type(item['records']) is int and 1<=item['records']<=4096,'manifest_invalid')
    return value


def code_modules(manifest,root=None):
    root=Path(__file__).resolve().parent if root is None else Path(root).resolve()
    for name,digest in manifest['code_sha256'].items():
        path=root/name
        require(path.is_file() and not path.is_symlink() and path.resolve().parent==root
                and sha_file(path)==digest,'code_pin_mismatch')
    result={}
    for name in ('role_config','private_pod_train','private_verify_adapter','private_dual_run','train_lora'):
        module=importlib.import_module(name)
        require(Path(module.__file__).resolve()==root/(name+'.py'),'code_pin_mismatch');result[name]=module
    return result


class Http:
    def __init__(self):
        import requests
        self.session=requests.Session();self.session.trust_env=False
    def request(self,method,url,*,anonymous=False,**options):
        if anonymous:
            # Separate client: no ADC header, prior cookies, .netrc or proxies.
            import requests
            with requests.Session() as session:
                session.trust_env=False
                return session.request(method,url,allow_redirects=False,**options)
        return self.session.request(method,url,allow_redirects=False,**options)


class Storage:
    def __init__(self,manifest,env,http,deadline,clock=time.monotonic):
        self.manifest=manifest;self.env=env;self.http=http;self.deadline=deadline;self.clock=clock
        self._token=None;self._expiry=0;self.private_verified=False
    def remaining(self):
        remaining=self.deadline-self.clock();require(remaining>0,'deadline_reached');return remaining
    def metadata(self,path,json_response=False):
        response=self.http.request('GET',META+path,headers={'Metadata-Flavor':'Google'},timeout=min(10,self.remaining()))
        try:
            headers={k.lower():v for k,v in response.headers.items()}
            require(response.status_code==200 and headers.get('metadata-flavor')=='Google'
                    and len(response.content)<=65536,'metadata_unavailable')
            return strict_json(response.content) if json_response else response.content.decode('utf8').strip()
        finally:response.close()
    def identity(self,*,preflight=False):
        # Vertex executes inside Google-managed tenant projects. Ownership is
        # CLOUD_ML_PROJECT_ID (number), coupled to the exact managed run-as SA.
        require(self.env.get('CLOUD_ML_PROJECT_ID')==self.manifest['project_number'],'runtime_identity_mismatch')
        email=self.metadata('instance/service-accounts/default/email')
        require(email==self.manifest['service_account_email'],'runtime_identity_mismatch')
        tenant=self.metadata('project/project-id')
        require(re.fullmatch(r'[a-z][a-z0-9-]{3,62}',tenant),'runtime_identity_mismatch')
        if not preflight:
            machine=self.metadata('instance/machine-type')
            require(machine.rsplit('/',1)[-1]==MACHINE,'runtime_identity_mismatch')
        return {'owner_project_id':self.manifest['project_id'],'owner_project_number':self.manifest['project_number'],
            'run_as_service_account':email,'tenant_project_id_sha256':hashlib.sha256(tenant.encode()).hexdigest()}
    def token(self):
        if self._token is None or self._expiry-self.clock()<60:
            require(self.metadata('instance/service-accounts/default/email')==self.manifest['service_account_email'],
                'runtime_identity_mismatch')
            value=self.metadata('instance/service-accounts/default/token',True)
            require(isinstance(value,dict) and value.get('token_type')=='Bearer'
                and isinstance(value.get('access_token'),str) and re.fullmatch(r'[A-Za-z0-9._~+/=-]{1,8192}',value['access_token'])
                and type(value.get('expires_in')) is int and 60<=value['expires_in']<=7200,'metadata_token_invalid')
            self._token=value['access_token'];self._expiry=self.clock()+value['expires_in']
        return self._token
    def request(self,method,url,*,data=None,content_type=None,limit=MAX_JSON):
        headers={'Authorization':'Bearer '+self.token(),'Accept-Encoding':'identity'}
        if content_type:headers['Content-Type']=content_type
        response=self.http.request(method,url,headers=headers,data=data,timeout=min(120,self.remaining()))
        try:
            require(response.status_code in (200,201),'upload_failed' if method=='POST' else 'source_transfer_failed')
            require(len(response.content)<=limit,'source_transfer_failed')
            return response.content
        finally:response.close()
    def assert_bucket_private(self):
        """Require live PAP enforcement and UBLA; object denial is insufficient.

        Anonymous 403 cannot exclude access granted to allAuthenticatedUsers.
        Inability to read the bucket policy configuration therefore fails closed.
        """
        self.private_verified=False
        try:
            raw=self.request('GET',STORAGE+'/storage/v1/b/'+BUCKET+'?fields=iamConfiguration')
        except WorkerError as error:
            if error.code=='source_transfer_failed':raise WorkerError('bucket_metadata_unavailable') from None
            raise
        try:value=strict_json(raw)
        except WorkerError:raise WorkerError('bucket_privacy_unverified') from None
        iam=value.get('iamConfiguration') if isinstance(value,dict) else None
        require(isinstance(iam,dict) and iam.get('publicAccessPrevention')=='enforced'
            and isinstance(iam.get('uniformBucketLevelAccess'),dict)
            and iam['uniformBucketLevelAccess'].get('enabled') is True,'bucket_privacy_unverified')
    def assert_private(self):
        """Strong live bucket gate followed by additional exact object proof.

        Parent uploads only a nonsensitive random probe before any private input.
        Exact probe bytes/generation and anonymous denial are rechecked here;
        every actual input/output is also anonymously checked at its generation.
        """
        self.assert_bucket_private()
        probe=self.manifest['privacy_probe'];name=self.object_name(probe['name'])
        url=STORAGE+'/storage/v1/b/'+BUCKET+'/o/'+quote(name,safe='')
        meta=strict_json(self.request('GET',url+'?generation='+probe['generation']))
        require(isinstance(meta,dict) and meta.get('bucket')==BUCKET and meta.get('name')==name
            and meta.get('generation')==probe['generation'] and meta.get('size')=='32','bucket_privacy_unverified')
        raw=self.request('GET',url+'?alt=media&generation='+probe['generation'],limit=32)
        require(len(raw)==32 and hashlib.sha256(raw).hexdigest()==probe['sha256'],'bucket_privacy_unverified')
        self.anonymous_private(name,probe['generation'])
        self.private_verified=True
    def anonymous_private(self,name,generation):
        require(name.startswith(self.manifest['prefix']+'/') and re.fullmatch(r'[1-9][0-9]{0,24}',generation),
            'bucket_privacy_unverified')
        url=STORAGE+'/storage/v1/b/'+BUCKET+'/o/'+quote(name,safe='')+'?alt=media&generation='+generation
        response=self.http.request('GET',url,headers={'Accept-Encoding':'identity'},anonymous=True,
            stream=True,timeout=min(20,self.remaining()))
        try:
            if response.status_code!=403:
                self.private_verified=False;raise WorkerError('bucket_privacy_unverified')
        finally:response.close()
    def object_name(self,name):
        allowed={'privacy-probe.bin','train.chat.jsonl','validation.chat.jsonl','progress.json','result.json','adapter_config.json','adapter_model.safetensors'}
        require(name in allowed,'manifest_invalid');return self.manifest['prefix']+'/'+name
    def download(self,split,root):
        self.assert_private()
        item=self.manifest['inputs'][split];name=self.object_name(item['name'])
        url=STORAGE+'/storage/v1/b/'+BUCKET+'/o/'+quote(name,safe='')
        value=strict_json(self.request('GET',url+'?generation='+item['generation']))
        require(isinstance(value,dict) and value.get('bucket')==BUCKET and value.get('name')==name
            and value.get('generation')==item['generation'] and value.get('size')==str(item['bytes']),
            'source_metadata_invalid')
        self.assert_bucket_private()
        raw=self.request('GET',url+'?alt=media&generation='+item['generation'],limit=item['bytes'])
        require(len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256'],'source_integrity_failed')
        self.anonymous_private(name,item['generation'])
        path=Path(root)/item['name'];require(not path.exists() and not path.is_symlink(),'private_workspace_required')
        path.write_bytes(raw);return raw,path
    def upload(self,name,path):
        require(name in ('progress.json','result.json','adapter_config.json','adapter_model.safetensors'),'manifest_invalid')
        self.assert_private();path=Path(path);require(path.is_file() and not path.is_symlink(),'upload_integrity_failed')
        size=path.stat().st_size;digest=sha_file(path)
        with path.open('rb') as stream:md5=base64.b64encode(hashlib.file_digest(stream,'md5').digest()).decode()
        object_name=self.object_name(name)
        url=STORAGE+'/upload/storage/v1/b/'+BUCKET+'/o?'+urlencode({'uploadType':'media','name':object_name,'ifGenerationMatch':'0'})
        with path.open('rb') as stream:
            value=strict_json(self.request('POST',url,data=stream,
                content_type='application/json' if name.endswith('.json') else 'application/octet-stream'))
        require(isinstance(value,dict) and value.get('bucket')==BUCKET and value.get('name')==object_name
            and value.get('size')==str(size) and value.get('md5Hash')==md5
            and isinstance(value.get('generation'),str) and re.fullmatch(r'[1-9][0-9]{0,24}',value['generation'])
            and path.stat().st_size==size and sha_file(path)==digest,'upload_integrity_failed')
        self.anonymous_private(object_name,value['generation'])
        return {'name':name,'bytes':size,'sha256':digest,'generation':value['generation']}


def check_gpu(run=subprocess.run):
    result=run(['nvidia-smi','--query-gpu=name,memory.total','--format=csv,noheader,nounits'],
        check=False,capture_output=True,text=True,timeout=15)
    lines=result.stdout.strip().splitlines() if result.returncode==0 else []
    require(len(lines)==1,'gpu_contract_failed');parts=[part.strip() for part in lines[0].split(',')]
    require(len(parts)==2 and parts[0] in ('NVIDIA A100 80GB PCIe','NVIDIA A100-SXM4-80GB')
        and re.fullmatch(r'[0-9]+',parts[1]) and 79000<=int(parts[1])<=85000,'gpu_contract_failed')
    return {'gpu_count':1,'gpu_name':parts[0],'gpu_memory_mib':int(parts[1])}


def trainer_environment(env):
    allowed=('PATH','LD_LIBRARY_PATH','LIBRARY_PATH','CUDA_HOME','CUDA_PATH','CUDA_VISIBLE_DEVICES','HOME','TMPDIR',
        'HF_HOME','HF_HUB_CACHE','HUGGINGFACE_HUB_CACHE','TORCH_HOME','TORCHINDUCTOR_CACHE_DIR','TRITON_CACHE_DIR')
    child={key:env[key] for key in allowed if key in env}
    child.update(WANDB_MODE='disabled',WANDB_DISABLED='true',WANDB_CONSOLE='off',WANDB_SILENT='true',
        WANDB_DISABLE_CODE='true',HF_HUB_DISABLE_TELEMETRY='1',HF_HUB_DISABLE_IMPLICIT_TOKEN='1',TOKENIZERS_PARALLELISM='false')
    return child


def run_trainer(command,*,cwd,env,stderr,timeout,clock=time.monotonic):
    process=subprocess.Popen(command,cwd=str(cwd),env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
        stderr=stderr,start_new_session=os.name=='posix')
    deadline=clock()+timeout
    try:
        while True:
            remaining=deadline-clock();require(remaining>0,'training_timeout')
            try:return process.wait(timeout=min(30,remaining))
            except subprocess.TimeoutExpired:pass
    finally:
        if process.poll() is None:
            if os.name=='posix':os.killpg(process.pid,signal.SIGTERM)
            else:process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name=='posix':os.killpg(process.pid,signal.SIGKILL)
                else:process.kill()
                process.wait(timeout=5)


def execute(env=None,*,http=None,workspace=None,preflight=False,clock=time.monotonic,
            trainer=run_trainer,gpu_check=check_gpu,version=importlib.metadata.version):
    env=dict(os.environ if env is None else env);credentials(env);manifest=manifest_from_env(env)
    modules=code_modules(manifest);pod=modules['private_pod_train'];verify=modules['private_verify_adapter']
    for package,expected in manifest['dependency_versions'].items():
        try:actual=version(package)
        except Exception:raise WorkerError('dependency_profile_mismatch') from None
        require(actual==expected,'dependency_profile_mismatch')
    parent=Path(tempfile.gettempdir() if workspace is None else workspace).absolute()
    require(not any(path.is_symlink() for path in (parent,*parent.parents))
        and not any('onedrive' in part.casefold() for part in parent.parts)
        and not any((path/'.git').exists() for path in (parent,*parent.parents)),'private_workspace_required')
    parent.mkdir(parents=True,exist_ok=True);deadline=clock()+manifest['runtime_seconds']
    client=Storage(manifest,env,Http() if http is None else http,deadline,clock)
    committed=None
    temporary=tempfile.TemporaryDirectory(prefix='hasla-gcp-gemma-',dir=parent)
    try:
        folder=temporary.name
        root=Path(folder);identity=client.identity(preflight=preflight);client.assert_private()
        training_raw,training_path=client.download('train',root);validation_raw,validation_path=client.download('validation',root)
        try:
            training=pod.rows_from_payload(training_raw,'train','chat');validation=pod.rows_from_payload(validation_raw,'validation','chat')
            require(len(training)==manifest['inputs']['train']['records'] and len(validation)==manifest['inputs']['validation']['records'],
                'source_records_invalid')
            pod.validate_row_roles(training+validation,'chat','chat');pod.verify_partitions(training,validation)
            modules['private_dual_run'].validate_source_lineage(training+validation,'chat')
            modules['train_lora'].load(training_path,data_format='chat',validation_path=validation_path,role='chat')
            config=pod.data_bounded_settings(modules['role_config'].get_role_config('chat'),len(training))
        except WorkerError:raise
        except Exception:raise WorkerError('source_records_invalid') from None
        require(config['default_rank']==8 and config['precision']=='bf16' and config['max_length']==1024
            and config['load_in_4bit'] is False and config['max_steps']==math.ceil(len(training)/8),'manifest_invalid')
        base={'kind':KIND,'run_id':manifest['run_id'],'dataset_version':manifest['dataset_version'],
            'role':'chat','base_model':config['base_model'],'rank':8,'precision':'bf16','training_method':'lora',
            'max_length':1024,'max_steps':config['max_steps'],'test_records_used':0,'quality_verified':False,
            'source_inputs':manifest['inputs'],'code_sha256':manifest['code_sha256'],
            'dependency_versions':manifest['dependency_versions'],'identity':identity,'promoted':False,'deployed':False,
            'budget':manifest['budget'],'privacy_probe':manifest['privacy_probe'],
            'privacy_verification':'live_pap_enforced_ubla_and_exact_generation_anonymous_deny_v2',
            'source_lineage_checked':True,'full_source_provenance_retained_in_pinned_input_objects':True}
        if preflight:return {**base,'status':'preflight_ready','weights_updated':False,'gpu_used':False,'objects_uploaded':0}
        gpu=gpu_check();base.update(gpu);client.assert_private()
        progress_path=root/'progress.json';progress_path.write_bytes(canonical({**base,'status':'starting','weights_updated':False}))
        client.upload('progress.json',progress_path)
        adapter=root/'adapter';numeric=root/'numeric-progress.json'
        client.assert_private()
        allowance=client.remaining()-manifest['upload_grace_seconds'];require(allowance>=180,'insufficient_training_time')
        command=pod.training_command(Path(__file__).resolve().parent/'train_lora.py',training_path,adapter,
            validation=validation_path,config=config,data_format='chat')
        command+=['--progress-json',str(numeric),'--train-wall-seconds',str(max(30,int(allowance)-120))]
        try:
            with tempfile.TemporaryFile(dir=root) as stderr:
                code=trainer(command,cwd=root,env=trainer_environment(env),stderr=stderr,timeout=allowance)
                require(code==0,'training_process_failed')
            for split,path in (('train',training_path),('validation',validation_path)):
                require(sha_file(path)==manifest['inputs'][split]['sha256'],'source_integrity_failed')
            try:
                report=pod.training_report(adapter,config,'chat',manifest['inputs']['train']['sha256'],manifest['inputs']['validation']['sha256'])
                files,inventory_sha=pod.adapter_inventory(adapter,config)
            except Exception:raise WorkerError('training_report_invalid') from None
            try:
                zero=verify.config_check(adapter/'adapter_config.json','chat',8)
                counts=verify.inspect_safetensors(adapter/'adapter_model.safetensors',8,verify.LIMITS['chat'])
                require(zero is True and counts['pair_shapes_supported'] is True and counts['b_all_finite'] is True
                    and counts['standard_b_nonzero_elements']>0,'weights_unverified')
            except WorkerError:raise
            except Exception:raise WorkerError('weights_unverified') from None
            uploads=[client.upload(item['name'],adapter/item['name']) for item in files]
            result={**base,'status':'stored' if report['scheduled_steps_completed'] else 'partial','weights_updated':True,
                'training_report':report,'tensor_evidence':counts,'zero_initializer':True,'adapter_inventory_sha256':inventory_sha,
                'adapter_files':uploads,'optimizer_state_restored':False,'initial_adapter':None,
                'numeric_progress':pod.read_numeric_progress(numeric),'private':True,'input_file_hashes_rechecked_after_training':True}
            path=root/'result.json';path.write_bytes(canonical(result));receipt=client.upload('result.json',path)
            committed={**result,'result_object':receipt}
        except Exception as error:
            failure={**base,'status':'failed','weights_updated':False,
                'code':error.code if isinstance(error,WorkerError) else 'worker_failed','private':True}
            if client.private_verified:
                try:
                    path=root/'result.json';path.write_bytes(canonical(failure));client.upload('result.json',path)
                except Exception:pass
            raise
    finally:
        try:temporary.cleanup()
        except Exception:
            if committed is None:raise
    return committed


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--preflight',action='store_true');args=parser.parse_args(argv)
    try:
        value=execute(preflight=args.preflight)
        event={'event':'gcp_gemma_worker','status':value['status'],'run_id':value['run_id'],
            'weights_updated':value['weights_updated'],'quality_verified':False,'test_records_used':0,
            'steps_completed':value.get('training_report',{}).get('steps_completed',0),'promoted':False,'deployed':False}
    except Exception as error:
        event={'event':'gcp_gemma_worker','status':'blocked' if isinstance(error,WorkerError) and error.code in
            ('bucket_metadata_unavailable','bucket_privacy_unverified','runtime_identity_mismatch','dependency_profile_mismatch') else 'failed',
            'code':error.code if isinstance(error,WorkerError) else 'worker_failed','weights_updated':False,'promoted':False,'deployed':False}
    print(json.dumps(event,ensure_ascii=True,separators=(',',':')),flush=True)
    return 0 if event['status'] in ('stored','partial','preflight_ready') else 1


if __name__=='__main__':
    def stop(_signum,_frame):raise WorkerError('cancelled')
    signal.signal(signal.SIGTERM,stop)
    raise SystemExit(main())

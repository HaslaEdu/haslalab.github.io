"""One reviewed PRIVATE 12-page OCR calibration on a bounded inexpensive GPU.

No training GPU policy is changed. --preflight is read-only (manifest only,
zero PDF download/model import/Pod creation); --cleanup uses only the RunPod
key and this exact run's prefix/receipt. Unknown creation is never free/deleted.
"""
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import signal
import sys
import tempfile
import time

import private_corpus_run as cloud
import private_stage_corpus as privacy
import private_ocr_gpu_run as common
import private_ocr_batch_worker as batch
from training_budget import BudgetLedger, BudgetPolicy, PodQuote, reserve_run, settle_run, validate_observed_pod

PREFIX='hasla-private-ocr-batch-'
KIND='private_ocr_calibration_run_v1'
SETUP_KIND='private_ocr_batch_setup_v1'
PROJECT=cloud.PROJECT
CALIBRATION_COUNT=12
CLEANUP_SECONDS=120
GPU_IDS=('NVIDIA L40S','NVIDIA RTX A6000','NVIDIA A40','NVIDIA L40','NVIDIA GeForce RTX 4090','NVIDIA RTX A5000')
MAX_GPU_USD=Decimal('1.25')
SETUP_ERRORS=frozenset(('setup_failed','setup_timeout','setup_deadline','cpu_paddle_installed','job_pin_mismatch',
    'base_torch_missing','base_torch_invalid','dependency_version_mismatch','worker_process_failed','private_project_unverified'))
PHASES=frozenset(('bootstrap','setup','worker'))
SUBJECTS=frozenset(('environment','cpu_paddle_check','base_torch_check','gpu_engine_install','doc_parser_install','pinned_version_check','private_worker'))
ERRORS=frozenset(('configuration_invalid','manifest_invalid','job_pin_mismatch','budget_unavailable','active_reservation_unverified',
    'old_ocr_pod_present','unexpected_active_pod','private_project_unverified','funding_unavailable','funding_below_bound',
    'gpu_unavailable','public_code_mismatch','image_unverified','source_unverified','run_already_exists','creation_failed',
    'pod_validation_failed','pod_stopped','deadline_reached','cleanup_unconfirmed','cancelled','probe_failed'))


class RunError(ValueError):
    def __init__(self,code):
        self.code=code if code in ERRORS else 'probe_failed';super().__init__(self.code)


def require(value,code):
    if not value:raise RunError(code)


def number(value):
    try:return common.number(value)
    except Exception:raise RunError('manifest_invalid') from None


def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def run_id(env):
    value=env.get('HASLA_OCR_BATCH_RUN_ID',env.get('GITHUB_RUN_ID',''))
    require(isinstance(value,str) and re.fullmatch(r'[0-9]{1,32}',value),'configuration_invalid');return value


def load_manifest(env):
    raw=env.get('HASLA_OCR_BATCH_MANIFEST','')
    require(isinstance(raw,str) and 0<len(raw.encode())<=16384,'manifest_invalid')
    try:value=privacy.strict_json(raw)
    except Exception:raise RunError('manifest_invalid') from None
    fields={'version','kind','budget_krw','authorized_budget_krw','prior_closed_krw','active_reservation_holds_krw',
        'other_reservation_holds_krw','known_training_run_ids','active_training_runs','total_runtime_seconds',
        'gpu_usd_per_hour_upper','gpu_ids','image_digest','run_script_sha256','worker_script_sha256','job_sha256','job'}
    require(isinstance(value,dict) and set(value)==fields and type(value['version']) is int and value['version']==1 and value['kind']==KIND,'manifest_invalid')
    for key in ('run_script_sha256','worker_script_sha256','job_sha256'):
        require(re.fullmatch(r'[a-f0-9]{64}',str(value[key])),'manifest_invalid')
    require(hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==value['run_script_sha256'],'public_code_mismatch')
    require(re.fullmatch(r'[a-f0-9]{40}',env.get('GITHUB_SHA','')),'configuration_invalid')
    require(re.fullmatch(r'sha256:[a-f0-9]{64}',str(value['image_digest'])),'manifest_invalid')
    require(number(value['authorized_budget_krw'])<=100000 and number(value['budget_krw'])<=number(value['authorized_budget_krw']),'manifest_invalid')
    for key in ('prior_closed_krw','active_reservation_holds_krw','other_reservation_holds_krw'):number(value[key])
    rate=number(value['gpu_usd_per_hour_upper']);require(0<rate<=MAX_GPU_USD,'manifest_invalid')
    ids=value['gpu_ids'];require(isinstance(ids,list) and ids and len(set(ids))==len(ids) and all(g in GPU_IDS for g in ids),'manifest_invalid')
    known=value['known_training_run_ids'];require(isinstance(known,list) and 0<len(known)<=32 and len(set(known))==len(known)
        and all(isinstance(x,str) and re.fullmatch(r'[0-9]{1,32}',x) for x in known),'manifest_invalid')
    active=value['active_training_runs'];seen=set();require(isinstance(active,list) and len(active)<=32,'manifest_invalid')
    for item in active:
        require(isinstance(item,dict) and set(item)=={'run_id','roles'} and item['run_id'] in known and item['run_id'] not in seen,'manifest_invalid')
        seen.add(item['run_id']);roles=item['roles']
        require(isinstance(roles,list) and roles and len(set(roles))==len(roles) and set(roles)<={'chat','solver'},'manifest_invalid')
    try:job=batch.validate_job(value['job'])
    except Exception:raise RunError('manifest_invalid') from None
    require(hashlib.sha256(canonical(job)).hexdigest()==value['job_sha256'],'job_pin_mismatch')
    require(job['mode']=='calibration' and job['bulk_authorized'] is False and isinstance(job['page_keys'],list)
            and len(job['page_keys'])==CALIBRATION_COUNT,'manifest_invalid')
    total=value['total_runtime_seconds']
    require(type(total) is int and job['runtime_seconds']+600+CLEANUP_SECONDS<=total<=3600,'manifest_invalid')
    return value


def budget(manifest,name,now):
    try:
        policy=BudgetPolicy(fx_krw_per_usd_upper=2000,budget_krw=manifest['budget_krw'],authorized_budget_krw=manifest['authorized_budget_krw'],
            reserve_krw=5000,tax_multiplier='1.15')
        training_quote=PodQuote(gpu_usd_per_hour_upper=4,container_disk_gb=200,volume_disk_gb=0)
        minimum=sum(((training_quote.hourly_usd_upper*policy.fx_krw_per_usd_upper*policy.tax_multiplier*Decimal(common.ROLE_CAPS[role]+120)/3600)
                      .to_integral_value(rounding=ROUND_CEILING) for row in manifest['active_training_runs'] for role in row['roles']),Decimal(0))
        require(number(manifest['active_reservation_holds_krw'])>=minimum,'active_reservation_unverified')
        prior=sum((number(manifest[key]) for key in ('prior_closed_krw','active_reservation_holds_krw','other_reservation_holds_krw')),Decimal(0))
        quote=PodQuote(gpu_usd_per_hour_upper=manifest['gpu_usd_per_hour_upper'],container_disk_gb=200,volume_disk_gb=0,gpu_count=1)
        ledger=BudgetLedger(policy,prior_spend_krw=prior)
        work=manifest['total_runtime_seconds']-CLEANUP_SECONDS
        ledger=reserve_run(ledger,name,'fast',quote,now,work,work,cleanup_grace_seconds=CLEANUP_SECONDS,minimum_run_seconds=work)
        require(ledger.runs[-1].plan.run_seconds==work,'budget_unavailable')
        return ledger,quote
    except RunError:raise
    except Exception:raise RunError('budget_unavailable') from None


def check_inventory(manifest,pods,name):
    require(isinstance(pods,list),'active_reservation_unverified')
    if any(str(p.get('name','')).startswith((common.PREFIX,PREFIX)) for p in pods):raise RunError('old_ocr_pod_present')
    # Existing model reservations use a $4/h ceiling too. A reported adjusted
    # rate must not silently invalidate those holds while OCR is being rented.
    for pod in pods:
        require(isinstance(pod,dict),'active_reservation_unverified')
        if str(pod.get('desiredStatus',pod.get('status',''))).upper()=='TERMINATED':continue
        if pod.get('adjustedCostPerHr') is not None:
            try:rate=number(pod['adjustedCostPerHr'])
            except Exception:raise RunError('active_reservation_unverified') from None
            require(0<rate<=4,'active_reservation_unverified')
    try:common.check_inventory(manifest,pods,name)
    except Exception as error:raise RunError(getattr(error,'code','active_reservation_unverified')) from None


def funding_check(manifest,quote,*,query=None):
    try:
        if query is None:
            from private_pod_status import _funding_query
            value=_funding_query('query FundingSufficiency { myself { clientBalance underBalance } }',cloud.E)
        else:value=query('query FundingSufficiency { myself { clientBalance underBalance } }')
        user=value.get('myself') if isinstance(value,dict) else None
        require(isinstance(user,dict) and type(user.get('underBalance')) is bool,'funding_unavailable')
        balance=number(user.get('clientBalance'))
        training_quote=PodQuote(gpu_usd_per_hour_upper=4,container_disk_gb=200,volume_disk_gb=0)
        training_seconds=sum(common.ROLE_CAPS[role]+120 for row in manifest['active_training_runs'] for role in row['roles'])
        bound=training_quote.hourly_usd_upper*Decimal(training_seconds)/3600+quote.hourly_usd_upper*Decimal(manifest['total_runtime_seconds'])/3600
        # Retain unposted earlier OCR reservations until root settles them.
        bound+=number(manifest['other_reservation_holds_krw'])/Decimal(2300)
        return {'funding_check':'available','sufficient_for_all_reserved_upper':balance>=bound and user['underBalance'] is False}
    except Exception:return {'funding_check':'unavailable','sufficient_for_all_reserved_upper':None}


def choose_gpu(manifest):
    catalog=cloud.runpod('GET','/catalog/gpus?include=AVAILABILITY&product=POD&count=1&cloud=SECURE&minCudaVersion=12.8')
    for wanted in manifest['gpu_ids']:
        for row in catalog.get('gpus',[]):
            try:price=number((row.get('price') or {}).get('secure'))
            except Exception:continue
            if row.get('id')==wanted and str(row.get('availability')).upper() in ('LOW','MEDIUM','HIGH') and 0<price<=number(manifest['gpu_usd_per_hour_upper']):return wanted
    raise RunError('gpu_unavailable')


def verify_assets(manifest,commit):
    response=cloud.requests.get('https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io/'+commit+'/tools/ai/private_ocr_batch_worker.py',
        timeout=20,allow_redirects=False)
    try:require(response.status_code==200 and len(response.content)<=256*1024 and hashlib.sha256(response.content).hexdigest()==manifest['worker_script_sha256'],'public_code_mismatch')
    finally:response.close()
    response=cloud.requests.get('https://auth.docker.io/token',params={'service':'registry.docker.io','scope':'repository:runpod/pytorch:pull'},timeout=20)
    try:require(response.status_code==200,'image_unverified');token=response.json().get('token');require(isinstance(token,str) and 0<len(token)<=16384,'image_unverified')
    finally:response.close()
    response=cloud.requests.head('https://registry-1.docker.io/v2/runpod/pytorch/manifests/'+common.IMAGE_TAG,timeout=20,allow_redirects=False,
        headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json'})
    try:require(response.status_code==200 and response.headers.get('Docker-Content-Digest')==manifest['image_digest'],'image_unverified')
    finally:response.close()


def verify_source(job,env):
    try:
        source_env={key:env[key] for key in ('WANDB_API_KEY','WANDB_ENTITY','WANDB_PROJECT','WANDB_BASE_URL') if key in env}
        with tempfile.TemporaryDirectory(prefix='hasla-ocr-calibration-preflight-') as temporary:
            _,_,pending,_=batch.open_source(job['source_artifact'],source_env,temporary,expected_hash=job['source_manifest_sha256'],
                expected_sources=job['expected_source_count'],expected_pending=job['expected_pending_pages'])
            require(all((key['source_index'],key['page_number']) in pending for key in job['page_keys']),'source_unverified')
    except Exception:raise RunError('source_unverified') from None


BOOTSTRAP=r'''
import contextlib,hashlib,importlib.metadata,json,math,os,subprocess,sys,threading,time
from pathlib import Path
import private_ocr_batch_worker as b
env=os.environ
job=b.validate_job(b.json_read(env['HASLA_OCR_BATCH_JOB']))
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def bounded_worker_job(job,deadline,now):
 effective=min(job['runtime_seconds'],math.floor(deadline-now-30))
 if effective<min(600,job['runtime_seconds']):raise RuntimeError('setup_deadline')
 return {**job,'runtime_seconds':effective}
def torch_constraint(version):
 if not isinstance(version,str) or not __import__('re').fullmatch(r'[0-9][A-Za-z0-9.+_-]{1,80}',version):raise RuntimeError('base_torch_invalid')
 return 'torch=='+version+'\n'
if hashlib.sha256(canonical(job)).hexdigest()!=env['HASLA_OCR_BATCH_JOB_SHA256']:raise SystemExit(2)
entity=b.artifact_entity(job['source_artifact'])
deadline=float(env['HASLA_OCR_BATCH_WORK_DEADLINE_EPOCH'])
run=None;stop=threading.Event();thread=None;lock=threading.Lock();phase='bootstrap';subject='environment';value=None;began=time.monotonic();sequence=0
with b.quiet():
 try:
  b.assert_private(env,entity)
  import wandb
  settings=wandb.Settings(console='off',disable_code=True,save_code=False,disable_git=True,disable_job_creation=True,x_disable_meta=True,x_disable_stats=True,init_timeout=60,finish_timeout=30,base_url='https://api.wandb.ai')
  b.assert_private(env,entity)
  run=wandb.init(entity=entity,project=b.PROJECT,id=env['RUN']+'-setup',name=env['RUN']+'-setup',resume='never',job_type='private-ocr-bootstrap',
   config={'kind':'private_ocr_batch_setup_v1'},settings=settings,dir='/workspace/ocr-calibration')
  def beat():
   global sequence
   try:
    b.assert_private(env,entity)
    with lock:
     if stop.is_set():return
     sequence+=1
     progress={'kind':'private_ocr_batch_setup_v1','status':'running','phase':phase,'subject':subject,
       'heartbeat_sequence':sequence,'driver_elapsed_seconds':round(time.monotonic()-began,3),'worker_sha256':env['HASLA_OCR_BATCH_WORKER_SHA256']}
     run.summary['private_ocr_setup_progress_json']=json.dumps(progress,ensure_ascii=True)
     run.log({'private_ocr_setup_alive':1,'private_ocr_setup_phase':phase,'private_ocr_setup_sequence':sequence},commit=True)
   except Exception:pass
  def heartbeat():
   while not stop.wait(20):beat()
  beat()
  thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
  subject='cpu_paddle_check'
  try:importlib.metadata.version('paddlepaddle')
  except importlib.metadata.PackageNotFoundError:pass
  else:raise RuntimeError('cpu_paddle_installed')
  phase='setup';subject='base_torch_check';beat()
  try:base_torch=importlib.metadata.version('torch')
  except importlib.metadata.PackageNotFoundError:raise RuntimeError('base_torch_missing')
  constraint='/workspace/ocr-calibration/base-constraints.txt'
  with open(constraint,'x',encoding='utf-8') as handle:handle.write(torch_constraint(base_torch))
  package_env={key:val for key,val in env.items() if not __import__('re').search(r'KEY|TOKEN|SECRET|PASSWORD',key,__import__('re').I) and not key.startswith('HASLA_')}
  commands=([sys.executable,'-m','pip','install','--quiet','paddlepaddle-gpu==3.2.1','-i','https://www.paddlepaddle.org.cn/packages/stable/cu126/'],
   [sys.executable,'-m','pip','install','--quiet','paddleocr[doc-parser]==3.6.0','paddlex==3.6.0','PyMuPDF==1.28.2'])
  for index,command in enumerate(commands):
   subject='gpu_engine_install' if index==0 else 'doc_parser_install';beat()
   remaining=deadline-time.time()-660
   if remaining<=0:raise RuntimeError('setup_deadline')
   done=subprocess.run(command+['--constraint',constraint],env=package_env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False,timeout=remaining)
   if done.returncode:raise RuntimeError('setup_failed')
  subject='pinned_version_check';beat()
  if any(importlib.metadata.version(package)!=version for package,version in b.PACKAGES.items()):raise RuntimeError('dependency_version_mismatch')
  try:importlib.metadata.version('paddlepaddle')
  except importlib.metadata.PackageNotFoundError:pass
  else:raise RuntimeError('cpu_paddle_installed')
  phase='worker';subject='private_worker';beat();job=bounded_worker_job(job,deadline,time.time());effective=job['runtime_seconds']
  value={'kind':'private_ocr_batch_setup_v1','status':'ready','phase':phase,'effective_worker_seconds':effective,'worker_sha256':env['HASLA_OCR_BATCH_WORKER_SHA256']}
  b.assert_private(env,entity);run.summary['private_ocr_setup_result_json']=json.dumps(value,ensure_ascii=True)
  child={key:val for key,val in env.items() if not __import__('re').search(r'KEY|TOKEN|SECRET|PASSWORD',key,__import__('re').I) or key=='WANDB_API_KEY'}
  child['HASLA_OCR_BATCH_JOB']=json.dumps(job,ensure_ascii=True,separators=(',',':'))
  done=subprocess.run([sys.executable,'/workspace/ocr-calibration/private_ocr_batch_worker.py'],env=child,
    stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=max(1,deadline-time.time()-10),check=False)
  if done.returncode:raise RuntimeError('worker_process_failed')
  value={**value,'status':'finished'}
 except Exception as error:
  code='setup_timeout' if isinstance(error,subprocess.TimeoutExpired) else str(error) if str(error) in ('setup_failed','setup_deadline','cpu_paddle_installed','base_torch_missing','base_torch_invalid','worker_process_failed','dependency_version_mismatch') else 'setup_failed'
  value={'kind':'private_ocr_batch_setup_v1','status':'failed','phase':phase,'subject':subject,'code':code,
   'driver_elapsed_seconds':round(time.monotonic()-began,3),'heartbeat_sequence':sequence,'worker_sha256':env['HASLA_OCR_BATCH_WORKER_SHA256']}
 finally:
  stop.set()
  if thread is not None:thread.join(timeout=1)
  if run is not None:
   try:b.assert_private(env,entity);run.summary['private_ocr_setup_result_json']=json.dumps(value,ensure_ascii=True)
   except Exception:pass
   with lock:
    with contextlib.suppress(Exception):run.finish(exit_code=0 if value and value.get('status')=='finished' else 1)
raise SystemExit(0 if value and value.get('status')=='finished' else 1)
'''


def command_and_env(manifest,env,entity,name,work_deadline_epoch):
    pod_env={'WANDB_API_KEY':env['WANDB_API_KEY'],'WANDB_ENTITY':entity,'WANDB_PROJECT':PROJECT,'RUN':name,
        'HASLA_OCR_BATCH_JOB':json.dumps(manifest['job'],ensure_ascii=True,separators=(',',':')),
        'HASLA_OCR_BATCH_JOB_SHA256':manifest['job_sha256'],'HASLA_OCR_BATCH_WORKER_SHA256':manifest['worker_script_sha256'],
        'HASLA_OCR_BATCH_WORK_DEADLINE_EPOCH':str(work_deadline_epoch),'WANDB_SILENT':'true','WANDB_CONSOLE':'off','WANDB_DISABLE_CODE':'true'}
    url='https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io/'+env['GITHUB_SHA']+'/tools/ai/private_ocr_batch_worker.py'
    setup='set -eu; mkdir -p /workspace/ocr-calibration; cd /workspace/ocr-calibration; '
    setup+='curl --connect-timeout 10 --max-time 30 -fsSL '+shlex.quote(url)+' -o private_ocr_batch_worker.py; '
    setup+='printf \'%s  %s\\n\' '+shlex.quote(manifest['worker_script_sha256'])+' private_ocr_batch_worker.py | sha256sum -c - >/dev/null; '
    setup+='python -m venv --system-site-packages venv; env -u WANDB_API_KEY venv/bin/python -m pip install --quiet wandb >/workspace/ocr-calibration/bootstrap.log 2>&1; '
    setup+='exec venv/bin/python -c '+shlex.quote(BOOTSTRAP)+' >/workspace/ocr-calibration/driver.log 2>&1'
    work=manifest['total_runtime_seconds']-CLEANUP_SECONDS
    command='exec timeout --signal=TERM --kill-after=10s '+str(work-10)+'s bash -lc '+shlex.quote(setup)
    return command,pod_env


def clean_result(value,manifest,entity,name):
    require(isinstance(value,dict) and value.get('kind')==batch.KIND and value.get('terminal') is True
            and value.get('status') in ('calibration_complete','partial','failed'),'configuration_invalid')
    result={'kind':batch.KIND,'terminal':True,'status':value['status']}
    for flag,expected in (('machine_ocr',True),('training_eligible',False),('human_reviewed',False),('scientifically_verified',False)):
        require(value.get(flag) is expected,'configuration_invalid');result[flag]=expected
    for key in ('selected_pages','processed_pages','extracted_pages','pending_attempted_pages','unprocessed_selected_pages',
                'source_pdfs_byte_verified','source_aliases_inventory_checked','next_cursor','total_source_pending_pages'):
        if key in value:
            require(type(value[key]) is int and 0<=value[key]<=1000000,'configuration_invalid');result[key]=value[key]
    if 'selected_pages' in result:require(result['selected_pages']==CALIBRATION_COUNT,'configuration_invalid')
    if 'processed_pages' in result:require(result['processed_pages']<=CALIBRATION_COUNT,'configuration_invalid')
    if all(key in result for key in ('processed_pages','extracted_pages','pending_attempted_pages')):
        require(result['extracted_pages']+result['pending_attempted_pages']==result['processed_pages'],'configuration_invalid')
    if all(key in result for key in ('processed_pages','unprocessed_selected_pages')):
        require(result['unprocessed_selected_pages']==CALIBRATION_COUNT-result['processed_pages'],'configuration_invalid')
    if 'next_cursor' in result and 'processed_pages' in result:
        require(result['next_cursor']==result['processed_pages'],'configuration_invalid')
    if 'worker_seconds' in value:
        seconds=value['worker_seconds']
        require(type(seconds) in (int,float) and math.isfinite(seconds) and 0<=seconds<=manifest['total_runtime_seconds'],'configuration_invalid')
        result['worker_seconds']=seconds
    if value['status']=='calibration_complete':
        require(value.get('selected_pages')==CALIBRATION_COUNT and value.get('processed_pages')==CALIBRATION_COUNT
                and value.get('pending_attempted_pages')==0 and value.get('extracted_pages')==CALIBRATION_COUNT
                and value.get('original_selected_pdf_bytes_unchanged') is True
                and value.get('source_aliases_inventory_checked')==manifest['job']['expected_source_count']
                and value.get('total_source_pending_pages')==manifest['job']['expected_pending_pages']
                and value.get('source_pdfs_byte_verified')==len({k['source_index'] for k in manifest['job']['page_keys']})
                and value.get('selection_sha256')==hashlib.sha256(canonical(manifest['job']['page_keys'])).hexdigest(),'configuration_invalid')
        result['original_selected_pdf_bytes_unchanged']=True
    if 'selection_sha256' in value:
        require(value['selection_sha256']==hashlib.sha256(canonical(manifest['job']['page_keys'])).hexdigest(),'configuration_invalid')
        result['selection_sha256']=value['selection_sha256']
    if 'code' in value:require(value['code'] in batch.ERRORS,'configuration_invalid');result['code']=value['code']
    pointers=value.get('checkpoints',[]);require(isinstance(pointers,list) and len(pointers)<=CALIBRATION_COUNT,'configuration_invalid')
    clean=[];previous_cursor=0
    for pointer in pointers:
        require(isinstance(pointer,dict) and set(pointer)=={'artifact','manifest_sha256','next_cursor'}
                and re.fullmatch(re.escape(entity+'/'+PROJECT+'/'+name+'-checkpoint-')+r'[0-9]{6}:v[0-9]+',str(pointer['artifact']))
                and re.fullmatch(r'[a-f0-9]{64}',str(pointer['manifest_sha256']))
                and type(pointer['next_cursor']) is int and previous_cursor<pointer['next_cursor']<=CALIBRATION_COUNT,'configuration_invalid')
        clean.append(dict(pointer))
        previous_cursor=pointer['next_cursor']
    if value['status']=='calibration_complete':
        require(clean and previous_cursor==CALIBRATION_COUNT,'configuration_invalid')
    result['checkpoints']=clean
    return result


def read_result(entity,name,manifest,timeout=10):
    # Native W&B run state is not termination evidence, including transient
    # failed/crashed/finished states. Only explicit pinned terminal data counts.
    try:
        row=common.summary_run(entity,name,max(0.1,timeout/2))
        summary=json.loads(row.get('summaryMetrics') or '{}') if row and isinstance(row.get('summaryMetrics','{}'),str) else (row or {}).get('summaryMetrics',{})
        value=summary.get('private_ocr_batch_result_json')
        for _ in range(2):
            if not isinstance(value,str):break
            value=json.loads(value)
        if isinstance(value,dict) and summary.get('private_ocr_batch_worker_sha256')==manifest['worker_script_sha256']:
            return clean_result(value,manifest,entity,name)
    except Exception:pass
    try:
        row=common.summary_run(entity,name+'-setup',max(0.1,timeout/2))
        summary=json.loads(row.get('summaryMetrics') or '{}') if row and isinstance(row.get('summaryMetrics','{}'),str) else (row or {}).get('summaryMetrics',{})
        value=summary.get('private_ocr_setup_result_json')
        if isinstance(value,str):value=json.loads(value)
        if (isinstance(value,dict) and value.get('kind')==SETUP_KIND and value.get('status')=='failed'
                and value.get('worker_sha256')==manifest['worker_script_sha256'] and value.get('code') in SETUP_ERRORS):
            result={'kind':SETUP_KIND,'status':'failed','terminal':True,'code':value['code']}
            if value.get('phase') in PHASES:result['phase']=value['phase']
            if value.get('subject') in SUBJECTS:result['subject']=value['subject']
            return result
    except Exception:pass
    return None


def read_phase(entity,name,manifest,timeout=10):
    try:
        row=common.summary_run(entity,name+'-setup',timeout)
        summary=row.get('summaryMetrics') or '{}' if row else '{}'
        if isinstance(summary,str):summary=json.loads(summary)
        value=summary.get('private_ocr_setup_progress_json')
        if isinstance(value,str):value=json.loads(value)
        require(isinstance(value,dict) and value.get('kind')==SETUP_KIND and value.get('status')=='running'
            and value.get('worker_sha256')==manifest['worker_script_sha256'] and value.get('phase') in PHASES
            and value.get('subject') in SUBJECTS,'configuration_invalid')
        elapsed=value.get('driver_elapsed_seconds');sequence=value.get('heartbeat_sequence')
        require(type(elapsed) in (int,float) and 0<=elapsed<=3600 and type(sequence) is int and 0<sequence<=1000,'configuration_invalid')
        return {'phase':value['phase'],'subject':value['subject'],'status':'heartbeat_observed',
                'driver_elapsed_seconds':elapsed,'heartbeat_sequence':sequence}
    except Exception:return None


def state_path(env):
    path=common.state_path({**env,'GITHUB_RUN_ID':run_id(env),'HASLA_OCR_GPU_RUN_ID':run_id(env)})
    return path.with_name('hasla-ocr-batch-'+run_id(env)+'.private.json')


def bounded_cleanup(name,pod,deadline,*,clock=time.monotonic,sleep=time.sleep):
    matches=[pod] if pod and pod.get('name')==name and isinstance(pod.get('id'),str) else []
    if not matches:
        for attempt in range(4):
            remaining=deadline-clock()
            if remaining<=0:break
            try:
                rows=cloud.runpod('GET','/pods',request_timeout=min(5,remaining))
                matches=[p for p in rows if p.get('name')==name and isinstance(p.get('id'),str)
                    and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',p['id'])]
            except Exception:matches=[]
            if matches:break
            if attempt<3:sleep(min(2,max(0,deadline-clock())))
    if not matches:return {'deletion_confirmed':False,'matched_pods':0,'creation_outcome':'unresolved'}
    outcomes=[]
    for item in matches:
        try:outcomes.append(common.delete_exact(item,name,deadline,clock))
        except Exception:outcomes.append(False)
    return {'deletion_confirmed':all(outcomes),'matched_pods':len(matches),'creation_outcome':'discovered'}


def execute(env=None,*,preflight=False,clock=time.monotonic,wall_clock=time.time,sleep=time.sleep):
    env=os.environ if env is None else env;cloud.E=env;name=PREFIX+run_id(env)
    require(bool(env.get('RUNPOD_API_KEY')) and bool(env.get('WANDB_API_KEY')),'configuration_invalid')
    manifest=load_manifest(env);ledger,quote=budget(manifest,name,clock());path=state_path(env)
    previous=json.loads(path.read_text()) if path.exists() else None
    require(not previous or previous.get('create_attempted') is not True,'old_ocr_pod_present')
    state={'name':name,'create_attempted':False,'deletion_confirmed':False};common.save_state(path,state)
    with privacy.quiet_output():
        entity=privacy.existing_private_project(cloud.wandb_query)
        require(batch.artifact_entity(manifest['job']['source_artifact'])==entity,'private_project_unverified')
        require(common.summary_run(entity,name) is None and common.summary_run(entity,name+'-setup') is None,'run_already_exists')
        check_inventory(manifest,cloud.runpod('GET','/pods'),name)
        funded=funding_check(manifest,quote)
        if funded['sufficient_for_all_reserved_upper'] is not True:
            return {'event':KIND,'status':'blocked','code':'funding_below_bound' if funded['funding_check']=='available' else 'funding_unavailable',
                    'gpu_creation_attempted':False,**funded}
        gpu=choose_gpu(manifest);verify_assets(manifest,env['GITHUB_SHA']);verify_source(manifest['job'],env)
    plan=ledger.runs[-1].plan
    guard={key:str(number(manifest[key])) for key in ('prior_closed_krw','active_reservation_holds_krw','other_reservation_holds_krw')}
    guard.update(guard_prior_upper_krw=str(ledger.prior_spend_krw),probe_reserved_upper_krw=str(plan.reserved_krw),
        budget_krw=str(ledger.policy.budget_krw),total_runtime_seconds=manifest['total_runtime_seconds'],gpu_hourly_ceiling=str(quote.gpu_usd_per_hour_upper),
        calibration_pages=len(manifest['job']['page_keys']),source_count=manifest['job']['expected_source_count'],
        source_manifest_sha256=manifest['job']['source_manifest_sha256'],job_sha256=manifest['job_sha256'],
        manifest_sha256=hashlib.sha256(canonical(manifest)).hexdigest())
    if preflight:return {'event':KIND,'status':'preflight_ready','gpu_creation_attempted':False,'pdfs_downloaded':0,'gpu':gpu,**guard}
    pod=None;value=None;outcome=None;attempted=False;code=None;last_phase={'phase':'bootstrap','status':'unreported','code':'awaiting_bootstrap_heartbeat'}
    try:
        with privacy.quiet_output():
            check_inventory(manifest,cloud.runpod('GET','/pods'),name)
            require(funding_check(manifest,quote)['sufficient_for_all_reserved_upper'] is True,'funding_below_bound')
            privacy.assert_private(cloud.wandb_query,entity)
            ledger,quote=budget(manifest,name,clock());plan=ledger.runs[-1].plan
            command,pod_env=command_and_env(manifest,env,entity,name,wall_clock()+plan.run_seconds)
            state.update(create_attempted=True,reserved_upper_krw=str(plan.reserved_krw));common.save_state(path,state);attempted=True
            pod=cloud.runpod('POST','/pods',json={'name':name,'cloud':'SECURE','gpu':{'id':gpu,'count':1,'minCudaVersion':'12.8'},
                'disk':200,'image':'runpod/pytorch@'+manifest['image_digest'],'entrypoint':['/bin/bash','-lc'],'cmd':[command],
                'ports':[],'env':pod_env,'startSsh':False,'startJupyter':False})
            require(isinstance(pod,dict) and isinstance(pod.get('id'),str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',pod['id']),'creation_failed')
            state['pod_id']=pod['id'];common.save_state(path,state)
            pod=cloud.runpod('GET','/pods/'+pod['id'],request_timeout=10)
            require(pod.get('name')==name and (pod.get('gpu') or {}).get('id')==gpu,'pod_validation_failed');validate_observed_pod(plan,pod)
        while clock()<float(plan.deadline_monotonic):
            remaining=float(plan.deadline_monotonic)-clock()
            with privacy.quiet_output():
                value=read_result(entity,name,manifest,timeout=min(10,remaining))
                if value is not None:
                    last_phase={'phase':value.get('phase','worker'),'status':'explicit_terminal_result','code':value.get('code','completed')}
                    break
                remaining=float(plan.deadline_monotonic)-clock()
                if remaining<=0:break
                observed=read_phase(entity,name,manifest,timeout=min(5,remaining))
                if observed:last_phase=observed
                remaining=float(plan.deadline_monotonic)-clock()
                if remaining<=0:break
                info=cloud.runpod('GET','/pods/'+pod['id'],request_timeout=min(5,remaining));validate_observed_pod(plan,info)
                require(info.get('name')==name and (info.get('gpu') or {}).get('id')==gpu,'pod_validation_failed')
                require(info.get('desiredStatus') not in ('EXITED','ERROR','TERMINATED','STOPPED'),'pod_stopped')
            sleep(min(10,max(0,float(plan.deadline_monotonic)-clock())))
        require(value is not None,'deadline_reached')
    except Exception as error:code=error.code if isinstance(error,RunError) else 'probe_failed'
    finally:
        if attempted:
            with privacy.quiet_output():outcome=bounded_cleanup(name,pod,float(plan.billing_deadline_monotonic),clock=clock,sleep=sleep)
            state.update(outcome);common.save_state(path,state)
            if outcome['deletion_confirmed']:ledger=settle_run(ledger,name,clock(),deletion_confirmed=True)
            else:code='cleanup_unconfirmed'
    status='succeeded' if not code and value and value.get('status')=='calibration_complete' else 'partial' if not code and value and value.get('status')=='partial' else 'failed'
    event={'event':KIND,'status':status,'gpu_creation_attempted':attempted,**guard}
    if code:event['code']=code
    if outcome:event.update(outcome)
    if value:event['result']=value
    event['last_observed_phase']=last_phase
    charge=ledger.runs[-1].charged_krw
    event.update(incremental_ocr_cost_upper_krw=str(charge) if charge is not None else None,
        reservation_retained=attempted and charge is None,prior_guard_is_not_new_spend=True)
    if attempted:event['observed_pod_lifecycle_seconds']=round(max(0,clock()-float(plan.started_monotonic)),3)
    return event


def cleanup_only(env=None,*,clock=time.monotonic,sleep=time.sleep):
    env=os.environ if env is None else env;cloud.E=env;require(bool(env.get('RUNPOD_API_KEY')),'configuration_invalid')
    name=PREFIX+run_id(env);path=state_path(env);state=json.loads(path.read_text()) if path.exists() else None
    with privacy.quiet_output():matches=common.exact_matches(name)
    if not matches:
        if state and state.get('name')==name and state.get('create_attempted') is False:
            return {'event':'private_ocr_batch_cleanup','status':'not_created','deletion_confirmed':None,'matched_pods':0}
        if state and state.get('name')==name and state.get('deletion_confirmed') is True:
            return {'event':'private_ocr_batch_cleanup','status':'already_confirmed','deletion_confirmed':True,'matched_pods':0}
        if state and state.get('name')==name and state.get('create_attempted') is True and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',str(state.get('pod_id',''))):
            matches=[{'name':name,'id':state['pod_id']}]
        else:return {'event':'private_ocr_batch_cleanup','status':'unresolved','deletion_confirmed':False,'matched_pods':0}
    with privacy.quiet_output():
        deadline=clock()+CLEANUP_SECONDS;ok=all([common.delete_exact(p,name,deadline,clock) for p in matches])
    if ok:common.save_state(path,{'name':name,'create_attempted':True,'deletion_confirmed':True})
    return {'event':'private_ocr_batch_cleanup','status':'deleted' if ok else 'unresolved','deletion_confirmed':ok,'matched_pods':len(matches)}


def main(argv=None):
    argv=sys.argv[1:] if argv is None else argv
    try:
        require(set(argv)<={'--preflight','--cleanup'} and not ('--preflight' in argv and '--cleanup' in argv),'configuration_invalid')
        event=cleanup_only() if '--cleanup' in argv else execute(preflight='--preflight' in argv)
    except Exception as error:event={'event':KIND,'status':'failed','code':error.code if isinstance(error,RunError) else 'probe_failed'}
    print(json.dumps(event,ensure_ascii=True,separators=(',',':')),flush=True)
    return 0 if event['status'] in ('succeeded','preflight_ready','not_created','already_confirmed','deleted') else 1


if __name__=='__main__':
    def terminate(_signum,_frame):raise RunError('cancelled')
    signal.signal(signal.SIGTERM,terminate)
    raise SystemExit(main())

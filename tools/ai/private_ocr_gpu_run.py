"""Dedicated, bounded public-page GPU OCR calibration; no private OCR/training.

--preflight performs read-only checks and creates no GPU. --cleanup requires
only a RunPod API key and exact numeric run ID. A lost creation response with
no discovered Pod remains unresolved, never a confirmed deletion/free run.
"""
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
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
import private_ocr_gpu_worker as worker
from training_budget import BudgetLedger, BudgetPolicy, PodQuote, reserve_run, settle_run, validate_observed_pod

PREFIX=worker.PREFIX
PROJECT=worker.PROJECT
GPU_IDS=cloud.GPU_IDS[:4]
IMAGE_REPOSITORY='runpod/pytorch'
IMAGE_TAG='1.0.2-cu1281-torch280-ubuntu2404'
ROLE_CAPS={'chat':1800,'solver':14400}
RUNTIME=1800
ERRORS=frozenset(('configuration_invalid','manifest_invalid','budget_unavailable','private_project_unverified',
    'public_code_mismatch','image_unverified','funding_unavailable','funding_below_bound','active_reservation_unverified',
    'unexpected_active_pod','previous_probe_present','gpu_unavailable','calibration_run_already_exists','creation_failed',
    'pod_validation_failed','pod_stopped','result_invalid','deadline_reached','cleanup_unconfirmed','cancelled','probe_failed'))


class ProbeRunError(ValueError):
    def __init__(self,code):
        self.code=code if code in ERRORS else 'probe_failed'
        super().__init__(self.code)


def require(condition,code):
    if not condition:raise ProbeRunError(code)


def number(value):
    require(type(value) in (int,float,str,Decimal),'manifest_invalid')
    try:value=Decimal(str(value))
    except Exception:raise ProbeRunError('manifest_invalid') from None
    require(value.is_finite() and value>=0,'manifest_invalid')
    return value


def run_id(env):
    value=env.get('HASLA_OCR_GPU_RUN_ID',env.get('GITHUB_RUN_ID',''))
    require(isinstance(value,str) and re.fullmatch(r'[0-9]{1,32}',value),'configuration_invalid')
    return value


def load_manifest(env):
    raw=env.get('HASLA_OCR_GPU_MANIFEST','')
    require(isinstance(raw,str) and 0<len(raw.encode())<=16384,'manifest_invalid')
    try:value=privacy.strict_json(raw)
    except Exception:raise ProbeRunError('manifest_invalid') from None
    fields={'version','kind','budget_krw','authorized_budget_krw','prior_closed_krw','active_reservation_holds_krw',
        'known_training_run_ids','active_training_runs','runtime_seconds','gpu_ids','image_digest',
        'run_script_sha256','worker_script_sha256','helper_script_sha256'}
    require(isinstance(value,dict) and set(value)==fields and type(value['version']) is int and value['version']==1
            and value['kind']==worker.KIND and type(value['runtime_seconds']) is int and value['runtime_seconds']==RUNTIME,'manifest_invalid')
    require(number(value['authorized_budget_krw'])<=100000 and number(value['budget_krw'])<=number(value['authorized_budget_krw']),'manifest_invalid')
    for key in ('prior_closed_krw','active_reservation_holds_krw'):number(value[key])
    require(re.fullmatch(r'sha256:[a-f0-9]{64}',str(value['image_digest'])),'manifest_invalid')
    for key in ('run_script_sha256','worker_script_sha256','helper_script_sha256'):
        require(re.fullmatch(r'[a-f0-9]{64}',str(value[key])),'manifest_invalid')
    require(hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==value['run_script_sha256'],'public_code_mismatch')
    require(re.fullmatch(r'[a-f0-9]{40}',env.get('GITHUB_SHA','')),'configuration_invalid')
    ids=value['gpu_ids']
    require(isinstance(ids,list) and 0<len(ids)<=len(GPU_IDS) and len(set(ids))==len(ids) and all(gpu in GPU_IDS for gpu in ids),'manifest_invalid')
    known=value['known_training_run_ids']
    require(isinstance(known,list) and 0<len(known)<=32 and len(set(known))==len(known)
            and all(isinstance(x,str) and re.fullmatch(r'[0-9]{1,32}',x) for x in known),'manifest_invalid')
    active=value['active_training_runs'];seen=set()
    require(isinstance(active,list) and len(active)<=32,'manifest_invalid')
    for item in active:
        require(isinstance(item,dict) and set(item)=={'run_id','roles'} and item['run_id'] in known
                and item['run_id'] not in seen,'manifest_invalid')
        seen.add(item['run_id']);roles=item['roles']
        require(isinstance(roles,list) and 0<len(roles)<=2 and len(set(roles))==len(roles) and set(roles)<=set(ROLE_CAPS),'manifest_invalid')
    return value


def budget(manifest,name,now):
    try:
        policy=BudgetPolicy(fx_krw_per_usd_upper=2000,budget_krw=manifest['budget_krw'],authorized_budget_krw=manifest['authorized_budget_krw'],
            reserve_krw=5000,tax_multiplier='1.15')
        quote=PodQuote(gpu_usd_per_hour_upper=4,container_disk_gb=200,volume_disk_gb=0,gpu_count=1)
        prior=number(manifest['prior_closed_krw']);holds=number(manifest['active_reservation_holds_krw'])
        minimum=sum(((quote.hourly_usd_upper*policy.fx_krw_per_usd_upper*policy.tax_multiplier*Decimal(ROLE_CAPS[role]+120)/3600)
                     .to_integral_value(rounding=ROUND_CEILING) for run in manifest['active_training_runs'] for role in run['roles']),Decimal(0))
        require(holds>=minimum,'active_reservation_unverified')
        ledger=BudgetLedger(policy,prior_spend_krw=prior+holds)
        ledger=reserve_run(ledger,name,'fast',quote,now,RUNTIME,RUNTIME,cleanup_grace_seconds=120,minimum_run_seconds=RUNTIME)
        require(ledger.runs[-1].plan.run_seconds==RUNTIME,'budget_unavailable')
        return ledger,quote
    except ProbeRunError:raise
    except Exception:raise ProbeRunError('budget_unavailable') from None


def check_inventory(manifest,pods,name):
    require(isinstance(pods,list),'active_reservation_unverified')
    declared={cloud.PREFIX+run['run_id']+'-'+role:role for run in manifest['active_training_runs'] for role in run['roles']}
    known={cloud.PREFIX+x+suffix for x in manifest['known_training_run_ids'] for suffix in ('','-chat','-solver')}
    observed=set()
    for pod in pods:
        require(isinstance(pod,dict) and isinstance(pod.get('name'),str),'active_reservation_unverified')
        pod_name=pod['name']
        if pod_name.startswith(PREFIX):raise ProbeRunError('previous_probe_present')
        if str(pod.get('desiredStatus',pod.get('status',''))).upper()=='TERMINATED':continue
        require(pod_name in declared,'unexpected_active_pod')
        require(pod_name not in observed,'active_reservation_unverified');observed.add(pod_name)
        gpu=pod.get('gpu') or {}
        require(type(gpu.get('count')) is int and gpu['count']==1 and gpu.get('id') in GPU_IDS
                and 0<number(pod.get('costPerHr',pod.get('cost')))<=4
                and number(pod.get('containerDiskInGb',pod.get('disk')))<=200
                and number(pod.get('volumeInGb'))==0 and not pod.get('networkVolume') and not pod.get('networkVolumeId'), 'active_reservation_unverified')
    if number(manifest['active_reservation_holds_krw'])==0:
        require(not manifest['active_training_runs'] and not observed and not any(p.get('name') in known for p in pods),'active_reservation_unverified')


def funding_check(manifest,quote,*,query=None):
    try:
        if query is None:
            from private_pod_status import _funding_query
            data=_funding_query('query FundingSufficiency { myself { clientBalance underBalance } }',cloud.E)
        else:data=query('query FundingSufficiency { myself { clientBalance underBalance } }')
        user=data.get('myself') if isinstance(data,dict) else None
        require(isinstance(user,dict) and type(user.get('underBalance')) is bool,'funding_unavailable')
        balance=number(user.get('clientBalance'))
        seconds=RUNTIME+120+sum(ROLE_CAPS[role]+120 for run in manifest['active_training_runs'] for role in run['roles'])
        covered=balance>=quote.hourly_usd_upper*Decimal(seconds)/3600 and user['underBalance'] is False
        return {'funding_check':'available','sufficient_for_full_active_and_probe_upper':covered}
    except Exception:
        return {'funding_check':'unavailable','sufficient_for_full_active_and_probe_upper':None}


def verify_public_assets(manifest,commit):
    for field,filename in (('worker_script_sha256','private_ocr_gpu_worker.py'),('helper_script_sha256','private_ocr_probe.py')):
        response=cloud.requests.get('https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io/'+commit+'/tools/ai/'+filename,
                                    timeout=20,allow_redirects=False)
        try:
            require(response.status_code==200 and len(response.content)<=256*1024
                    and hashlib.sha256(response.content).hexdigest()==manifest[field],'public_code_mismatch')
        finally:response.close()
    token_response=cloud.requests.get('https://auth.docker.io/token',params={'service':'registry.docker.io','scope':'repository:'+IMAGE_REPOSITORY+':pull'},timeout=20)
    try:
        require(token_response.status_code==200,'image_unverified');token=token_response.json().get('token')
        require(isinstance(token,str) and 0<len(token)<=16384,'image_unverified')
    finally:token_response.close()
    response=cloud.requests.head('https://registry-1.docker.io/v2/'+IMAGE_REPOSITORY+'/manifests/'+IMAGE_TAG,
        headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json'},
        timeout=20,allow_redirects=False)
    try:require(response.status_code==200 and response.headers.get('Docker-Content-Digest')==manifest['image_digest'],'image_unverified')
    finally:response.close()


def selected_gpu(manifest):
    catalog=cloud.runpod('GET','/catalog/gpus?include=AVAILABILITY&product=POD&count=1&cloud=SECURE&minCudaVersion=12.8')
    for desired in manifest['gpu_ids']:
        for row in catalog.get('gpus',[]):
            try:price=number((row.get('price') or {}).get('secure'))
            except Exception:continue
            if row.get('id')==desired and str(row.get('availability')).upper() in ('LOW','MEDIUM','HIGH') and 0<price<=4:return desired
    raise ProbeRunError('gpu_unavailable')


def summary_run(entity,name,timeout=10):
    data=cloud.wandb_query('query($e:String!,$p:String!,$r:String!){project(name:$p,entityName:$e){run(name:$r){state summaryMetrics}}}',
        {'e':entity,'p':PROJECT,'r':name},timeout=timeout)
    return (data.get('project') or {}).get('run')


def read_result(entity,name,manifest,timeout=10):
    try:
        row=summary_run(entity,name,timeout)
        if not row:return None
        summary=row.get('summaryMetrics') or '{}'
        if isinstance(summary,str):summary=json.loads(summary)
        value=summary.get('private_ocr_gpu_result_json')
        if value is None:value=summary.get('private_ocr_gpu_result')
        for _ in range(2):
            if not isinstance(value,str):break
            value=json.loads(value)
        if isinstance(value,dict):
            if (summary.get('private_ocr_gpu_worker_sha256')!=manifest['worker_script_sha256']
                    or summary.get('private_ocr_gpu_helper_sha256')!=manifest['helper_script_sha256']):return None
            return worker.clean_result(value)
    except Exception:return None
    # W&B's native run state can be stale or falsely terminal. It is not proof
    # that the actual GPU process exited. Only a validated explicit result,
    # observed Pod exit, or the original hard deadline terminates this probe.
    return None


def command_and_env(manifest,env,entity,name):
    pod_env={'WANDB_API_KEY':env['WANDB_API_KEY'],'WANDB_ENTITY':entity,'WANDB_PROJECT':PROJECT,'RUN':name,
        'REPO_SHA':env['GITHUB_SHA'],'HASLA_OCR_GPU_WORKER_SHA256':manifest['worker_script_sha256'],
        'HASLA_OCR_GPU_HELPER_SHA256':manifest['helper_script_sha256'],'WANDB_CONSOLE':'off','WANDB_SILENT':'true','WANDB_DISABLE_CODE':'true'}
    base='https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io/'+env['GITHUB_SHA']+'/tools/ai/'
    setup='set -eu; mkdir -p /workspace/ocr-probe; cd /workspace/ocr-probe; python -m venv venv; '
    setup+='venv/bin/python -m pip install --quiet wandb >/workspace/ocr-probe/bootstrap.log 2>&1; '
    for filename,field in (('private_ocr_gpu_worker.py','worker_script_sha256'),('private_ocr_probe.py','helper_script_sha256')):
        setup+='curl --connect-timeout 10 --max-time 30 -fsSL '+shlex.quote(base+filename)+' -o '+shlex.quote(filename)+'; '
        setup+='printf \'%s  %s\\n\' '+shlex.quote(manifest[field])+' '+shlex.quote(filename)+' | sha256sum -c - >/dev/null; '
    setup+='exec venv/bin/python private_ocr_gpu_worker.py >/workspace/ocr-probe/worker.log 2>&1'
    command='exec timeout --signal=TERM --kill-after=20s 1680s bash -lc '+shlex.quote(setup)
    return command,pod_env


def state_path(env):
    directory=Path(env.get('RUNNER_TEMP',tempfile.gettempdir())).resolve()
    require(not any(p.lower().startswith('onedrive') for p in directory.parts)
            and not any((p/'.git').exists() for p in (directory,*directory.parents)),'configuration_invalid')
    directory.mkdir(parents=True,exist_ok=True)
    return directory/('hasla-ocr-gpu-'+run_id(env)+'.private.json')


def save_state(path,value):
    temporary=path.with_suffix('.updated.json')
    temporary.write_text(json.dumps(value,ensure_ascii=True),encoding='utf-8')
    with __import__('contextlib').suppress(OSError):temporary.chmod(0o600)
    temporary.replace(path)


def exact_matches(name):
    rows=cloud.runpod('GET','/pods',request_timeout=10)
    require(isinstance(rows,list),'cleanup_unconfirmed')
    matches=[p for p in rows if p.get('name')==name]
    require(all(isinstance(p.get('id'),str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',p['id']) for p in matches),'cleanup_unconfirmed')
    return matches


def delete_exact(pod,name,deadline,clock=time.monotonic):
    require(pod.get('name')==name,'cleanup_unconfirmed')
    # Check provider identity before DELETE, including receipt-based recovery.
    try:
        remaining=deadline-clock()
        if remaining<=0:return False
        check=cloud.requests.get(cloud.REST+'/pods/'+pod['id'],headers={'Authorization':'Bearer '+cloud.E['RUNPOD_API_KEY']},timeout=min(5,remaining))
        try:
            if check.status_code==404:return True
            if check.status_code!=200 or check.json().get('name')!=name:return False
        finally:check.close()
    except Exception:return False
    for _ in range(3):
        remaining=deadline-clock()
        if remaining<=0:return False
        try:
            response=cloud.requests.delete(cloud.REST+'/pods/'+pod['id'],headers={'Authorization':'Bearer '+cloud.E['RUNPOD_API_KEY']},timeout=min(5,remaining))
            status=response.status_code;response.close()
            if status not in (200,204,404):continue
            remaining=deadline-clock()
            if remaining<=0:return False
            check=cloud.requests.get(cloud.REST+'/pods/'+pod['id'],headers={'Authorization':'Bearer '+cloud.E['RUNPOD_API_KEY']},timeout=min(5,remaining))
            try:
                if check.status_code==404:return True
                if check.status_code==200:
                    data=check.json()
                    if data.get('name')==name and data.get('status')=='TERMINATED':return True
            finally:check.close()
        except Exception:pass
    return False


def cleanup_attempt(name,pod=None,*,clock=time.monotonic,sleep=time.sleep):
    deadline=clock()+120
    matches=[pod] if pod and pod.get('id') and pod.get('name')==name else []
    if not matches:
        for attempt in range(4):
            try:matches=exact_matches(name)
            except Exception:matches=[]
            if matches:break
            if attempt<3:sleep(2)
    if not matches:return {'deletion_confirmed':False,'matched_pods':0,'creation_outcome':'unresolved'}
    outcomes=[]
    for item in matches:
        try:outcomes.append(delete_exact(item,name,deadline,clock))
        except Exception:outcomes.append(False)
    confirmed=all(outcomes)
    return {'deletion_confirmed':confirmed,'matched_pods':len(matches),'creation_outcome':'discovered'}


def execute(env=None,*,preflight=False,clock=time.monotonic,sleep=time.sleep):
    env=os.environ if env is None else env;cloud.E=env
    name=PREFIX+run_id(env)
    require(bool(env.get('RUNPOD_API_KEY')) and bool(env.get('WANDB_API_KEY')),'configuration_invalid')
    manifest=load_manifest(env);ledger,quote=budget(manifest,name,clock())
    path=state_path(env)
    previous=json.loads(path.read_text()) if path.exists() else None
    require(not previous or previous.get('create_attempted') is not True,'previous_probe_present')
    state={'name':name,'create_attempted':False,'deletion_confirmed':False}
    save_state(path,state)
    with privacy.quiet_output():
        entity=privacy.existing_private_project(cloud.wandb_query)
        require(summary_run(entity,name) is None,'calibration_run_already_exists')
        check_inventory(manifest,cloud.runpod('GET','/pods'),name)
        funding=funding_check(manifest,quote)
        if funding['sufficient_for_full_active_and_probe_upper'] is not True:
            return {'event':'public_gpu_ocr_probe','status':'blocked','code':'funding_below_bound' if funding['funding_check']=='available' else 'funding_unavailable',
                    'gpu_creation_attempted':False,**funding}
        gpu=selected_gpu(manifest);verify_public_assets(manifest,env['GITHUB_SHA'])
    plan=ledger.runs[-1].plan
    guard={'prior_closed_krw':str(number(manifest['prior_closed_krw'])),'active_reservation_holds_krw':str(number(manifest['active_reservation_holds_krw'])),
        'guard_prior_upper_krw':str(ledger.prior_spend_krw),'probe_reserved_upper_krw':str(plan.reserved_krw),
        'budget_krw':str(ledger.policy.budget_krw),'runtime_seconds':RUNTIME}
    if preflight:return {'event':'public_gpu_ocr_probe','status':'preflight_ready','gpu_creation_attempted':False,'funding_sufficient':True,'gpu':gpu,**guard}
    pod=None;value=None;error_code=None;attempted=False;outcome=None
    try:
        # Recheck account/project state immediately before spending.
        with privacy.quiet_output():
            check_inventory(manifest,cloud.runpod('GET','/pods'),name)
            funding=funding_check(manifest,quote)
            require(funding['sufficient_for_full_active_and_probe_upper'] is True,'funding_below_bound')
            privacy.assert_private(cloud.wandb_query,entity)
            command,pod_env=command_and_env(manifest,env,entity,name)
            ledger,quote=budget(manifest,name,clock());plan=ledger.runs[-1].plan
            state['create_attempted']=True;state['reserved_upper_krw']=str(plan.reserved_krw);save_state(path,state);attempted=True
            pod=cloud.runpod('POST','/pods',json={'name':name,'cloud':'SECURE','gpu':{'id':gpu,'count':1,'minCudaVersion':'12.8'},
                'disk':200,'image':IMAGE_REPOSITORY+'@'+manifest['image_digest'],'entrypoint':['/bin/bash','-lc'],'cmd':[command],
                'ports':[],'env':pod_env,'startSsh':False,'startJupyter':False})
            require(isinstance(pod,dict) and isinstance(pod.get('id'),str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',pod['id']),'creation_failed')
            state['pod_id']=pod['id'];save_state(path,state)
            pod=cloud.runpod('GET','/pods/'+pod['id'],request_timeout=10)
            require(pod.get('name')==name,'pod_validation_failed')
            validate_observed_pod(plan,pod)
            require((pod.get('gpu') or {}).get('id')==gpu,'pod_validation_failed')
        while clock()<float(plan.deadline_monotonic):
            remaining=float(plan.deadline_monotonic)-clock()
            with privacy.quiet_output():
                value=read_result(entity,name,manifest,timeout=min(10,remaining))
                if value is not None:break
                info=cloud.runpod('GET','/pods/'+pod['id'],request_timeout=min(10,remaining))
                validate_observed_pod(plan,info)
                require(info.get('name')==name and (info.get('gpu') or {}).get('id')==gpu,'pod_validation_failed')
                require(info.get('desiredStatus') not in ('EXITED','ERROR','TERMINATED','STOPPED'),'pod_stopped')
            sleep(min(10,max(0,float(plan.deadline_monotonic)-clock())))
        require(value is not None,'deadline_reached')
    except Exception as error:
        error_code=error.code if isinstance(error,ProbeRunError) else 'probe_failed'
    finally:
        if attempted:
            with privacy.quiet_output():outcome=cleanup_attempt(name,pod,clock=clock,sleep=sleep)
            state.update(outcome);save_state(path,state)
            if outcome['deletion_confirmed']:
                ledger=settle_run(ledger,name,clock(),deletion_confirmed=True)
            else:error_code='cleanup_unconfirmed'
    event={'event':'public_gpu_ocr_probe','status':'succeeded' if not error_code and value and value['status']=='succeeded' else 'failed',
        'gpu_creation_attempted':attempted,**guard}
    if error_code:event['code']=error_code
    if outcome:event.update(outcome)
    if value:event['result']=worker.clean_result(value)
    charge=ledger.runs[-1].charged_krw
    event['incremental_probe_cost_upper_krw']=str(charge) if charge is not None else None
    event['probe_reservation_retained']=charge is None and attempted
    event['prior_guard_is_not_new_spend']=True
    if attempted:event['observed_pod_lifecycle_seconds']=round(max(0,clock()-float(plan.started_monotonic)),3)
    return event


def cleanup_only(env=None,*,clock=time.monotonic,sleep=time.sleep):
    env=os.environ if env is None else env;cloud.E=env
    require(bool(env.get('RUNPOD_API_KEY')),'configuration_invalid')
    name=PREFIX+run_id(env);path=state_path(env)
    state=json.loads(path.read_text()) if path.exists() else None
    with privacy.quiet_output():matches=exact_matches(name)
    if not matches:
        if state and state.get('name')==name and state.get('create_attempted') is False:
            return {'event':'public_gpu_ocr_cleanup','status':'not_created','deletion_confirmed':None,'matched_pods':0}
        if state and state.get('name')==name and state.get('deletion_confirmed') is True:
            return {'event':'public_gpu_ocr_cleanup','status':'already_confirmed','deletion_confirmed':True,'matched_pods':0}
        if (state and state.get('name')==name and state.get('create_attempted') is True
                and isinstance(state.get('pod_id'),str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',state['pod_id'])):
            matches=[{'id':state['pod_id'],'name':name}]
        else:
            return {'event':'public_gpu_ocr_cleanup','status':'unresolved','deletion_confirmed':False,'matched_pods':0}
    with privacy.quiet_output():
        deadline=clock()+120;ok=all([delete_exact(p,name,deadline,clock) for p in matches])
    if ok:save_state(path,{'name':name,'create_attempted':True,'deletion_confirmed':True})
    return {'event':'public_gpu_ocr_cleanup','status':'deleted' if ok else 'unresolved','deletion_confirmed':ok,'matched_pods':len(matches)}


def main(argv=None):
    argv=sys.argv[1:] if argv is None else argv
    try:
        require(set(argv)<= {'--preflight','--cleanup'} and not ('--preflight' in argv and '--cleanup' in argv),'configuration_invalid')
        event=cleanup_only() if '--cleanup' in argv else execute(preflight='--preflight' in argv)
    except Exception as error:
        event={'event':'public_gpu_ocr_probe','status':'failed','code':error.code if isinstance(error,ProbeRunError) else 'probe_failed'}
    print(json.dumps(event,ensure_ascii=True,separators=(',',':')),flush=True)
    return 0 if event.get('status') in ('succeeded','preflight_ready','not_created','already_confirmed','deleted') else 1


if __name__=='__main__':
    def terminate(_signum,_frame):raise ProbeRunError('cancelled')
    signal.signal(signal.SIGTERM,terminate)
    raise SystemExit(main())

"""Read-only provider inventory observations for one exact OCR attempt.

Two absence observations do not establish creation rejection, deletion, or zero
billing. This module has no create/delete/cleanup endpoint or model imports.
"""
import argparse
from datetime import datetime,timezone
import json
import math
import os
import re
import time

PREFIXES={'private-batch':'hasla-private-ocr-batch-','public-probe':'hasla-private-ocr-probe-'}


class ObservationError(ValueError):pass


def require(value,code):
    if not value:raise ObservationError(code)


def inventory(env,*,get=None):
    require(bool(env.get('RUNPOD_API_KEY')),'provider_credential_missing')
    require(not any(value and (key.startswith(('WANDB_','HF_','HUGGING')) or key in ('OPENAI_API_KEY','GOOGLE_CLOUD_API_KEY','GCP_SA_KEY'))
        for key,value in env.items()),'unexpected_credential')
    if get is None:
        import requests
        get=requests.get
    response=get('https://api.runpod.io/v2/pods',
        headers={'Authorization':'Bearer '+env['RUNPOD_API_KEY'],'User-Agent':'HaslaExactOCRReconciliation/1.0'},
        timeout=20,allow_redirects=False)
    try:
        require(response.status_code==200 and len(response.content)<=8*1024**2,'inventory_unavailable')
        value=response.json()
    finally:response.close()
    page_fields={'total','totalCount','nextCursor','nextPage','next','hasMore','hasNextPage'}
    require(isinstance(value,dict) and set(value)<={'pods','pagination'}|page_fields
            and isinstance(value.get('pods'),list) and len(value['pods'])<=10000,'inventory_invalid')
    require('pagination' not in value or isinstance(value['pagination'],dict) and set(value['pagination'])<=page_fields,
            'inventory_incomplete')
    for metadata in (value,value.get('pagination',{})):
        require(isinstance(metadata,dict),'inventory_incomplete')
        require(not any(metadata.get(key) for key in ('nextCursor','nextPage','next','hasMore','hasNextPage')),'inventory_incomplete')
        for key in ('total','totalCount'):
            if key in metadata:
                require(type(metadata[key]) is int and metadata[key]==len(value['pods']),'inventory_incomplete')
    require(all(isinstance(row,dict) and isinstance(row.get('name'),str) and isinstance(row.get('id'),str)
                for row in value['pods']),'inventory_invalid')
    return value['pods']


def observed_pod(row):
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,128}',row['id']),'target_identity_invalid')
    result={'id':row['id'],'name':row['name']}
    gpu=row.get('gpu') or {}
    if isinstance(gpu,dict):result['gpu']={key:gpu.get(key) for key in ('id','count')}
    for key in ('status','desiredStatus'):
        if isinstance(row.get(key),str):result[key]=row[key][:40]
    for key in ('cost','costPerHr','adjustedCostPerHr'):
        if key in row:
            try:value=float(row[key])
            except (ValueError,TypeError):continue
            if math.isfinite(value) and value>=0:result[key]=value
    runtime=row.get('runtime') or {}
    seconds=runtime.get('uptimeInSeconds') if isinstance(runtime,dict) else None
    if type(seconds) in (int,float) and math.isfinite(seconds) and seconds>=0:result['uptime_seconds']=seconds
    return result


def observe(run_id,scope,env=None,*,get=None,clock=time.monotonic,sleep=time.sleep):
    require(isinstance(run_id,str) and re.fullmatch(r'[0-9]{1,32}',run_id) and scope in PREFIXES,'arguments_invalid')
    env=os.environ if env is None else env;name=PREFIXES[scope]+run_id;observations=[];first_finished=None
    for index in range(2):
        if index:
            delay=max(0,15-(clock()-first_finished))
            if delay:sleep(delay)
            require(clock()-first_finished>=15,'observation_spacing_invalid')
        began=clock();rows=inventory(env,get=get)
        matches=[observed_pod(row) for row in rows if row['name']==name]
        first_finished=clock() if not index else first_finished
        observations.append({'checked_at':datetime.now(timezone.utc).isoformat(),'matched_pods':len(matches),
            'pods':matches,'request_seconds':round(max(0,clock()-began),3)})
    return {'event':'private_ocr_provider_observation','run_id':run_id,'scope':scope,'observations':observations,
        'absence_observed_twice':all(row['matched_pods']==0 for row in observations),
        'get_only':True,'creation_attempted':False,'deletion_attempted':False,
        'does_not_prove_creation_rejection_or_zero_billing':True,'reservation_release_authorized':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    parser.add_argument('--scope',choices=tuple(PREFIXES),required=True);args=parser.parse_args()
    try:event=observe(args.run_id,args.scope)
    except Exception as error:
        event={'event':'private_ocr_provider_observation','status':'unavailable',
            'code':str(error) if isinstance(error,ObservationError) else 'provider_read_failed',
            'creation_attempted':False,'deletion_attempted':False,'reservation_release_authorized':False}
    print(json.dumps(event,ensure_ascii=True,separators=(',',':')),flush=True)
    return 1 if event.get('status')=='unavailable' else 0


if __name__=='__main__':raise SystemExit(main())

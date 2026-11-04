"""Bounded PRIVATE pending-page machine OCR; never approved training data.

--inspect-source is CPU-only: it downloads only the small manifest after the
PRIVATE/immutable-artifact/file-inventory gates. No Paddle/PyMuPDF import occurs.
Actual OCR is separately configured by an explicit page allowlist. Source PDFs
are read-only; model text and structured blocks only enter PRIVATE checkpoints.
"""
import argparse
import base64
from collections import Counter
from collections.abc import Mapping
import contextlib
import gzip
import hashlib
import importlib.metadata
import io
import json
import math
import multiprocessing
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import threading
import time
import urllib.request

PROJECT='hasla-ai-private-training'
SOURCE_TYPE='ocr-source'
OUTPUT_TYPE='ocr-checkpoint'
KIND='private_pending_page_ocr_v1'
EXPECTED_SOURCES=858
EXPECTED_PENDING=8084
CALIBRATION_PAGES=12
MAX_PDF_BYTES=256*1024**2
MAX_TOTAL_PDF_BYTES=3*1024**3
MAX_MANIFEST_BYTES=8*1024**2
MAX_PAGE_BYTES=4*1024**2
MAX_SHARD_PAGES=25
MAX_SHARD_BYTES=64*1024**2
MAX_TOTAL_OCR_BYTES=512*1024**2
MAX_PIXELS=20000000
MAX_DIMENSION=10000
MAX_PNG_BYTES=32*1024**2
DPI=300
RENDER_VERSION='1.28.2'
PACKAGES={'paddlepaddle-gpu':'3.2.1','paddleocr':'3.6.0','paddlex':'3.6.0','PyMuPDF':RENDER_VERSION}
TRIAGE=frozenset(('encoding_recovery_ocr_candidate','image_present_ocr_candidate',
                 'empty_native_requires_visual_triage','sparse_native_requires_visual_triage'))
ERRORS=frozenset(('configuration_invalid','credential_scope_invalid','private_project_unverified','artifact_invalid',
    'manifest_invalid','manifest_hash_mismatch','inventory_invalid','source_hash_mismatch','source_size_limit','path_invalid',
    'page_not_pending','duplicate_page','render_pixel_limit','render_failed','render_size_limit','uniform_white_render',
    'dependency_invalid','gpu_unavailable','model_initialization_failed','page_ocr_failed','output_invalid','output_size_limit',
    'page_timeout','engine_failed','deadline_reached','checkpoint_failed','resume_invalid','disk_space_low','worker_failed'))


class BatchError(ValueError):
    def __init__(self,code):
        self.code=code if code in ERRORS else 'worker_failed'
        super().__init__(self.code)


def require(value,code):
    if not value:raise BatchError(code)


def integer(value,minimum,maximum,code='manifest_invalid'):
    require(type(value) is int and minimum<=value<=maximum,code)
    return value


def sha_file(path):
    with Path(path).open('rb') as handle:return hashlib.file_digest(handle,'sha256').hexdigest()


def sha(value):return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def json_read(raw):
    def pairs(values):
        result={}
        for key,value in values:
            require(key not in result,'manifest_invalid');result[key]=value
        return result
    try:return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(BatchError('manifest_invalid')))
    except BatchError:raise
    except Exception:raise BatchError('manifest_invalid') from None


@contextlib.contextmanager
def quiet():
    saved=[]
    with open(os.devnull,'w') as sink,contextlib.redirect_stdout(sink),contextlib.redirect_stderr(sink):
        try:
            for fd in (1,2):saved.append((fd,os.dup(fd)));os.dup2(sink.fileno(),fd)
            yield
        finally:
            for fd,previous in reversed(saved):os.dup2(previous,fd);os.close(previous)


def checked_hash(value,code='manifest_invalid'):
    require(isinstance(value,str) and re.fullmatch(r'[a-f0-9]{64}',value),code)
    return value


def alias(index):return 'source_'+str(index).zfill(4)+'.pdf'


def ranges(value,maximum):
    require(isinstance(value,list) and 0<len(value)<=maximum,'manifest_invalid')
    output=set();previous=0
    for item in value:
        require(isinstance(item,list) and len(item)==2,'manifest_invalid')
        start=integer(item[0],1,maximum);end=integer(item[1],start,maximum)
        require(start>previous,'manifest_invalid');previous=end;output.update(range(start,end+1))
    return output


def private_directory(path):
    path=Path(path)
    for current in (path,*path.parents):
        require(not current.is_symlink(),'path_invalid')
        if current.exists():require(not getattr(current.lstat(),'st_file_attributes',0)&0x400,'path_invalid')
    path=path.resolve()
    require(not any(part.lower().startswith('onedrive') for part in path.parts)
            and not any((parent/'.git').exists() for parent in (path,*path.parents)),'path_invalid')
    return path


def regular_file(path,root):
    root=private_directory(root);path=Path(path)
    require(path.parent.resolve()==root and not path.is_symlink(),'path_invalid')
    info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400,'path_invalid')
    return info


def artifact_entity(reference):
    require(isinstance(reference,str),'artifact_invalid')
    match=re.fullmatch(r'([A-Za-z0-9][A-Za-z0-9_.-]{0,127})/'+PROJECT+r'/([A-Za-z0-9][A-Za-z0-9_.-]{0,127}):v[0-9]+',reference)
    require(match is not None,'artifact_invalid')
    return match[1]


def credentials(env,entity):
    require(bool(env.get('WANDB_API_KEY')) and env.get('WANDB_ENTITY',entity)==entity
            and env.get('WANDB_PROJECT',PROJECT)==PROJECT
            and env.get('WANDB_BASE_URL','https://api.wandb.ai').rstrip('/')=='https://api.wandb.ai','credential_scope_invalid')
    forbidden=('RUNPOD_API_KEY','RUNPOD_API_TOKEN','HF_TOKEN','HF_API_TOKEN','HUGGINGFACE_TOKEN','HUGGING_FACE_HUB_TOKEN','OPENAI_API_KEY')
    require(not any(env.get(key) for key in forbidden),'credential_scope_invalid')


def assert_private(env,entity,opener=urllib.request.urlopen):
    credentials(env,entity)
    request=urllib.request.Request('https://api.wandb.ai/graphql',data=canonical({'query':
        'query($e:String!,$p:String!){project(name:$p,entityName:$e){name access}}','variables':{'e':entity,'p':PROJECT}}),
        headers={'Content-Type':'application/json','Authorization':'Basic '+base64.b64encode(('api:'+env['WANDB_API_KEY']).encode()).decode()})
    try:
        with opener(request,timeout=15) as response:raw=response.read(128*1024+1)
        require(len(raw)<=128*1024,'private_project_unverified');value=json_read(raw)
        project=(value.get('data') or {}).get('project')
        require(not value.get('errors') and isinstance(project,dict) and project.get('name')==PROJECT
                and project.get('access')=='PRIVATE','private_project_unverified')
    except Exception:raise BatchError('private_project_unverified') from None


def validate_manifest(manifest):
    require(isinstance(manifest,dict) and set(manifest)=={'version','kind','bundle_id','dataset_version','part_plain_bytes',
        'total_pdf_bytes','source_inventory_sha256','page_jobs_sha256','sources','parts'},'manifest_invalid')
    require(type(manifest['version']) is int and manifest['version']==1 and manifest['kind']==SOURCE_TYPE
            and re.fullmatch(r'[a-f0-9]{32}',str(manifest['bundle_id']))
            and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',str(manifest['dataset_version']))
            and type(manifest['part_plain_bytes']) is int and manifest['part_plain_bytes']==16*1024**2,'manifest_invalid')
    checked_hash(manifest['source_inventory_sha256']);checked_hash(manifest['page_jobs_sha256'])
    sources=manifest['sources'];require(isinstance(sources,list) and len(sources)==EXPECTED_SOURCES,'manifest_invalid')
    source_ids=set();source_hashes=set();pending=set();total=0;all_pages=0
    for index,source in enumerate(sources):
        require(isinstance(source,dict) and set(source)=={'index','alias','source_id','source_family','pdf_bytes','pdf_sha256',
            'page_count','pending_page_ranges','triage_page_ranges','drive_file_id'},'manifest_invalid')
        require(type(source['index']) is int and source['index']==index and source['alias']==alias(index)
                and re.fullmatch(r'[A-Za-z0-9_:\-]{1,180}',str(source['source_id']))
                and source['source_family'] in ('textbook','competition_document'),'manifest_invalid')
        require(source['source_id'] not in source_ids and source['pdf_sha256'] not in source_hashes,'manifest_invalid')
        source_ids.add(source['source_id']);source_hashes.add(checked_hash(source['pdf_sha256']))
        total+=integer(source['pdf_bytes'],5,MAX_PDF_BYTES);all_pages+=integer(source['page_count'],1,100000)
        require(total<=MAX_TOTAL_PDF_BYTES and all_pages<=1000000,'manifest_invalid')
        selected=ranges(source['pending_page_ranges'],source['page_count'])
        classified=set();triage=source['triage_page_ranges']
        require(isinstance(triage,dict) and bool(triage) and set(triage)<=TRIAGE,'manifest_invalid')
        for intervals in triage.values():
            values=ranges(intervals,source['page_count']);require(not classified&values,'manifest_invalid');classified.update(values)
        require(selected==classified,'manifest_invalid')
        drive=source['drive_file_id'];require(drive is None or isinstance(drive,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',drive),'manifest_invalid')
        pending.update((index,page) for page in selected)
    require(type(manifest['total_pdf_bytes']) is int and total==manifest['total_pdf_bytes'] and len(pending)==EXPECTED_PENDING,'manifest_invalid')
    # Transport framing is retained as provenance, never interpreted as paths.
    parts=manifest['parts'];require(isinstance(parts,list) and 0<len(parts)<=12000,'manifest_invalid')
    source_index=0;offset=0
    for index,part in enumerate(parts,1):
        require(isinstance(part,dict) and set(part)=={'index','source_index','offset','plain_bytes','plain_sha256','cipher_bytes','cipher_sha256'},'manifest_invalid')
        if offset==sources[source_index]['pdf_bytes']:source_index+=1;offset=0
        require(source_index<len(sources),'manifest_invalid')
        length=min(16*1024**2,sources[source_index]['pdf_bytes']-offset)
        require(type(part['index']) is int and part['index']==index and type(part['source_index']) is int and part['source_index']==source_index
                and type(part['offset']) is int and part['offset']==offset and type(part['plain_bytes']) is int and part['plain_bytes']==length
                and type(part['cipher_bytes']) is int and part['cipher_bytes']==length+40,'manifest_invalid')
        checked_hash(part['plain_sha256']);checked_hash(part['cipher_sha256']);offset+=length
    require(source_index==len(sources)-1 and offset==sources[-1]['pdf_bytes'],'manifest_invalid')
    return pending


def artifact_inventory(artifact,reference):
    require(artifact.qualified_name==reference and artifact.type==SOURCE_TYPE and artifact.state=='COMMITTED','artifact_invalid')
    metadata=artifact.metadata
    require(isinstance(metadata,dict) and metadata.get('private') is True and metadata.get('kind')==SOURCE_TYPE
            and metadata.get('source_count')==EXPECTED_SOURCES and metadata.get('pending_pages')==EXPECTED_PENDING,'artifact_invalid')
    entries=artifact.manifest.entries
    require(isinstance(entries,Mapping) and set(entries)=={'manifest.json'}|{alias(index) for index in range(EXPECTED_SOURCES)},'inventory_invalid')
    total=0
    for name,entry in entries.items():
        require(getattr(entry,'ref',None) is None,'inventory_invalid')
        size=getattr(entry,'size',None)
        integer(size,1,MAX_MANIFEST_BYTES if name=='manifest.json' else MAX_PDF_BYTES,'inventory_invalid')
        if name!='manifest.json':total+=size
    require(total==metadata.get('total_pdf_bytes') and total<=MAX_TOTAL_PDF_BYTES,'inventory_invalid')
    return entries


def downloaded_file(artifact,name,directory,maximum):
    directory=private_directory(directory)
    require(directory.is_dir() and not (directory/name).exists(),'path_invalid')
    returned=artifact.get_path(name).download(root=str(directory))
    path=Path(returned)
    require(path.resolve()==directory/name,'path_invalid');info=regular_file(path,directory)
    integer(info.st_size,1,maximum,'source_size_limit')
    return path


def open_source(reference,env,directory,*,expected_hash=None,sdk=None,privacy=assert_private):
    entity=artifact_entity(reference);credentials(env,entity);privacy(env,entity)
    directory=private_directory(directory)
    require(directory.is_dir() and not any(directory.iterdir()),'path_invalid')
    if sdk is None:import wandb as sdk
    with quiet():
        api=sdk.Api(api_key=env['WANDB_API_KEY'],timeout=30)
        artifact=api.artifact(reference,type=SOURCE_TYPE)
        entries=artifact_inventory(artifact,reference)
        manifest_path=downloaded_file(artifact,'manifest.json',directory,MAX_MANIFEST_BYTES)
    raw=manifest_path.read_bytes();actual_hash=sha(raw)
    if expected_hash is not None:require(actual_hash==checked_hash(expected_hash),'manifest_hash_mismatch')
    manifest=json_read(raw);pending=validate_manifest(manifest)
    require(all(entries[source['alias']].size==source['pdf_bytes'] for source in manifest['sources']),'inventory_invalid')
    privacy(env,entity)
    return artifact,manifest,pending,actual_hash


def inspect_source(env=None,*,sdk=None,privacy=assert_private):
    env=os.environ if env is None else env
    reference=env.get('HASLA_OCR_SOURCE_ARTIFACT','');entity=artifact_entity(reference)
    parent=private_directory(Path(tempfile.gettempdir()))
    with quiet(),tempfile.TemporaryDirectory(prefix='hasla-private-ocr-inspect-',dir=parent) as temporary:
        _,manifest,pending,manifest_hash=open_source(reference,env,temporary,sdk=sdk,privacy=privacy)
    return {'event':'private_ocr_source_inspection','status':'inspected','private_project_checked':True,
            'manifest_sha256':manifest_hash,'source_count':len(manifest['sources']),'pending_pages':len(pending),
            'total_pdf_bytes':manifest['total_pdf_bytes'],'pdfs_downloaded':0,
            'inspection_scope':'manifest_and_artifact_inventory_only','gpu_initialized':False}


def main(argv=None):
    argv=sys.argv[1:] if argv is None else argv
    try:
        require(set(argv)<={'--inspect-source'} and len(argv)<=1,'configuration_invalid')
        if '--inspect-source' in argv:
            event=inspect_source()
        else:
            event=run_batch()
        code=0 if event.get('status') in ('inspected','calibration_complete','selection_complete','all_pending_pages_complete') else 1
    except Exception as error:
        event={'event':'private_pending_page_ocr','status':'failed','code':error.code if isinstance(error,BatchError) else 'worker_failed'}
        code=1
    # Result references and page records remain in the PRIVATE run/checkpoints.
    public={key:value for key,value in event.items() if key not in ('checkpoints','source_artifact','run')}
    print(json.dumps(public,ensure_ascii=True,separators=(',',':')),flush=True)
    return code


if __name__=='__main__':
    raise SystemExit(main())

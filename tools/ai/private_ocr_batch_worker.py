"""Bounded PRIVATE pending-page machine OCR; never approved training data.

--inspect-source is CPU-only: it downloads only the small manifest after the
PRIVATE/immutable-artifact/file-inventory gates. No Paddle/PyMuPDF import occurs.
Actual OCR is separately configured by an explicit page allowlist. Source PDFs
are read-only; model text and structured blocks only enter PRIVATE checkpoints.
"""
import base64
from collections.abc import Mapping
import contextlib
import gzip
import hashlib
import importlib.metadata
import json
import math
import multiprocessing
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
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
    'page_timeout','engine_failed','deadline_reached','checkpoint_failed','resume_invalid','disk_space_low','worker_failed',
    'no_machine_text','worker_timeout'))


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
    key=env.get('WANDB_API_KEY')
    require(isinstance(key,str) and 0<len(key)<=1024 and key.isascii() and not any(c.isspace() for c in key)
            and env.get('WANDB_ENTITY',entity)==entity
            and env.get('WANDB_PROJECT',PROJECT)==PROJECT
            and env.get('WANDB_BASE_URL','https://api.wandb.ai').rstrip('/')=='https://api.wandb.ai','credential_scope_invalid')
    forbidden={'HF_TOKEN','HF_API_TOKEN','HF_API_KEY','HUGGINGFACE_TOKEN','HUGGING_FACE_HUB_TOKEN',
               'HUGGINGFACE_HUB_TOKEN','HUGGINGFACEHUB_API_TOKEN','HUGGINGFACE_API_KEY','OPENAI_API_KEY'}
    require(not any(value and (name.upper() in forbidden or 'RUNPOD' in name.upper()
            and any(marker in name.upper() for marker in ('KEY','TOKEN'))) for name,value in env.items()),'credential_scope_invalid')


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


def validate_manifest(manifest,expected_sources=None,expected_pending=None):
    expected_sources=EXPECTED_SOURCES if expected_sources is None else integer(expected_sources,1,10000)
    expected_pending=EXPECTED_PENDING if expected_pending is None else integer(expected_pending,1,1000000)
    require(isinstance(manifest,dict) and set(manifest)=={'version','kind','bundle_id','dataset_version','part_plain_bytes',
        'total_pdf_bytes','source_inventory_sha256','page_jobs_sha256','sources','parts'},'manifest_invalid')
    require(type(manifest['version']) is int and manifest['version']==1 and manifest['kind']==SOURCE_TYPE
            and re.fullmatch(r'[a-f0-9]{32}',str(manifest['bundle_id']))
            and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',str(manifest['dataset_version']))
            and type(manifest['part_plain_bytes']) is int and manifest['part_plain_bytes']==16*1024**2,'manifest_invalid')
    checked_hash(manifest['source_inventory_sha256']);checked_hash(manifest['page_jobs_sha256'])
    sources=manifest['sources'];require(isinstance(sources,list) and len(sources)==expected_sources,'manifest_invalid')
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
    require(type(manifest['total_pdf_bytes']) is int and total==manifest['total_pdf_bytes'] and len(pending)==expected_pending,'manifest_invalid')
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


def artifact_inventory(artifact,reference,expected_sources=None,expected_pending=None):
    expected_sources=EXPECTED_SOURCES if expected_sources is None else integer(expected_sources,1,10000)
    expected_pending=EXPECTED_PENDING if expected_pending is None else integer(expected_pending,1,1000000)
    require(artifact.qualified_name==reference and artifact.type==SOURCE_TYPE and artifact.state=='COMMITTED'
            and getattr(artifact,'is_link',False) is False,'artifact_invalid')
    metadata=artifact.metadata
    require(isinstance(metadata,dict) and metadata.get('private') is True and metadata.get('kind')==SOURCE_TYPE
            and metadata.get('source_count')==expected_sources and metadata.get('pending_pages')==expected_pending,'artifact_invalid')
    entries=artifact.manifest.entries
    require(isinstance(entries,Mapping) and set(entries)=={'manifest.json'}|{alias(index) for index in range(expected_sources)},'inventory_invalid')
    total=0
    for name,entry in entries.items():
        require(str(getattr(entry,'path',''))==name and getattr(entry,'ref',None) is None,'inventory_invalid')
        size=getattr(entry,'size',None)
        integer(size,1,MAX_MANIFEST_BYTES if name=='manifest.json' else MAX_PDF_BYTES,'inventory_invalid')
        if name!='manifest.json':total+=size
    require(total==metadata.get('total_pdf_bytes') and total<=MAX_TOTAL_PDF_BYTES,'inventory_invalid')
    return entries


def downloaded_file(artifact,name,directory,maximum):
    directory=private_directory(directory)
    require(directory.is_dir() and not (directory/name).exists(),'path_invalid')
    entry=artifact.get_entry(name)
    require(str(getattr(entry,'path',''))==name and getattr(entry,'ref',None) is None,'inventory_invalid')
    expected=integer(getattr(entry,'size',None),1,maximum,'source_size_limit')
    returned=entry.download(root=str(directory),skip_cache=True)
    path=Path(returned)
    require(path.resolve()==directory/name,'path_invalid');info=regular_file(path,directory)
    require(info.st_size==expected,'source_size_limit')
    return path


def open_source(reference,env,directory,*,expected_hash=None,sdk=None,privacy=assert_private,expected_sources=None,expected_pending=None):
    entity=artifact_entity(reference);credentials(env,entity);privacy(env,entity)
    directory=private_directory(directory)
    require(directory.is_dir() and not any(directory.iterdir()),'path_invalid')
    if sdk is None:import wandb as sdk
    with quiet():
        api=sdk.Api(api_key=env['WANDB_API_KEY'],overrides={'base_url':'https://api.wandb.ai'},timeout=30)
        artifact=api.artifact(reference,type=SOURCE_TYPE)
        entries=artifact_inventory(artifact,reference,expected_sources,expected_pending)
        manifest_path=downloaded_file(artifact,'manifest.json',directory,MAX_MANIFEST_BYTES)
    raw=manifest_path.read_bytes();actual_hash=sha(raw)
    if expected_hash is not None:require(actual_hash==checked_hash(expected_hash),'manifest_hash_mismatch')
    manifest=json_read(raw);pending=validate_manifest(manifest,expected_sources,expected_pending)
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


def validate_job(value):
    fields={'version','mode','source_artifact','source_manifest_sha256','expected_source_count','expected_pending_pages',
            'page_keys','runtime_seconds','per_page_seconds','checkpoint_pages','bulk_authorized','calibration_checkpoint'}
    require(isinstance(value,dict) and fields<=set(value)<=fields|{'learning_exclusions'}
            and type(value['version']) is int and value['version']==1,'configuration_invalid')
    require(value['mode'] in ('calibration','bulk'),'configuration_invalid');entity=artifact_entity(value['source_artifact'])
    checked_hash(value['source_manifest_sha256'],'configuration_invalid')
    integer(value['expected_source_count'],1,10000,'configuration_invalid')
    integer(value['expected_pending_pages'],1,1000000,'configuration_invalid')
    integer(value['runtime_seconds'],240,1800 if value['mode']=='calibration' else 18000,'configuration_invalid')
    integer(value['per_page_seconds'],1,600,'configuration_invalid');integer(value['checkpoint_pages'],1,MAX_SHARD_PAGES,'configuration_invalid')
    keys=value['page_keys']
    whole_pending=value['mode']=='bulk' and keys=='all_pending'
    require(whole_pending or isinstance(keys,list) and 0<len(keys)<=(CALIBRATION_PAGES if value['mode']=='calibration' else value['expected_pending_pages']),'configuration_invalid')
    seen=set()
    for key in ([] if whole_pending else keys):
        require(isinstance(key,dict) and set(key)=={'source_index','page_number'},'configuration_invalid')
        item=(integer(key['source_index'],0,value['expected_source_count']-1,'configuration_invalid'),integer(key['page_number'],1,100000,'configuration_invalid'))
        require(item not in seen,'duplicate_page');seen.add(item)
    if value['mode']=='calibration':
        require(value['bulk_authorized'] is False and value['calibration_checkpoint'] is None,'configuration_invalid')
    else:
        proof=value['calibration_checkpoint']
        require(value['bulk_authorized'] is True and isinstance(proof,dict) and set(proof)=={'artifact','manifest_sha256'}
                and artifact_entity(proof['artifact'])==entity,'configuration_invalid')
        checked_hash(proof['manifest_sha256'],'configuration_invalid')
    exclusions=value.get('learning_exclusions',[])
    require(isinstance(exclusions,list) and len(exclusions)<=value['expected_pending_pages'],'configuration_invalid')
    exclusion_keys=set()
    for item in exclusions:
        require(isinstance(item,dict) and set(item)=={'source_index','page_number','reason'},'configuration_invalid')
        key=(integer(item['source_index'],0,value['expected_source_count']-1,'configuration_invalid'),integer(item['page_number'],1,100000,'configuration_invalid'))
        require(key not in exclusion_keys and (whole_pending or key in seen) and item['reason'] in
                ('cover_page','bibliography','table_of_contents','non_problem_front_matter','user_excluded'),'configuration_invalid')
        exclusion_keys.add(key)
    return value


def choose_calibration_pages(manifest,limit=CALIBRATION_PAGES,*,expected_sources=None,expected_pending=None):
    """Metadata-only proposal; callers pin the resulting explicit allowlist."""
    validate_manifest(manifest,expected_sources,expected_pending);buckets={}
    for source in manifest['sources']:
        for triage,intervals in source['triage_page_ranges'].items():
            candidates=[]
            for first,last in intervals:
                candidates.extend([(first+last)//2,first,last])
            buckets.setdefault((source['source_family'],triage),[]).extend((source['index'],page) for page in dict.fromkeys(candidates))
    selected=[];seen=set();used_sources=set()
    for prefer_new in (True,False):
        while len(selected)<limit:
            added=False
            for category in sorted(buckets):
                candidate=next((item for item in buckets[category] if item not in seen and (not prefer_new or item[0] not in used_sources)),None)
                if candidate is None:continue
                seen.add(candidate);used_sources.add(candidate[0]);selected.append({'source_index':candidate[0],'page_number':candidate[1]});added=True
                if len(selected)==limit:break
            if not added:break
    return selected


def verify_pdf(path,source,directory):
    info=regular_file(path,directory)
    require(info.st_size==source['pdf_bytes'] and info.st_size<=MAX_PDF_BYTES,'source_size_limit')
    with Path(path).open('rb') as handle:require(handle.read(5)==b'%PDF-','source_hash_mismatch')
    require(sha_file(path)==source['pdf_sha256'],'source_hash_mismatch')


def rendering_size(width_points,height_points):
    require(type(width_points) in (int,float) and type(height_points) in (int,float)
            and math.isfinite(width_points) and math.isfinite(height_points) and width_points>0 and height_points>0,'render_failed')
    width=math.ceil(width_points*DPI/72);height=math.ceil(height_points*DPI/72)
    require(width<=MAX_DIMENSION and height<=MAX_DIMENSION and width*height<=MAX_PIXELS,'render_pixel_limit')
    return width,height


def render_page(pdf_path,page_number,source,scratch,fitz=None):
    if fitz is None:import pymupdf as fitz
    path=Path(scratch)/'render.png'
    require(not path.exists(),'path_invalid')
    with fitz.open(str(pdf_path)) as document:
        require(not document.is_encrypted and document.page_count==source['page_count'],'source_hash_mismatch')
        page=document.load_page(page_number-1)
        predicted=rendering_size(float(page.rect.width),float(page.rect.height))
        # No crop, rotation rewrite, grayscale, thresholding or lossy compression.
        pixels=page.get_pixmap(dpi=DPI,colorspace=fitz.csRGB,alpha=False,annots=True)
        require(pixels.width<=MAX_DIMENSION and pixels.height<=MAX_DIMENSION and pixels.width*pixels.height<=MAX_PIXELS
                and pixels.n==3,'render_pixel_limit')
        samples=pixels.samples
        info={'dpi':DPI,'colorspace':'RGB','alpha':False,'annotations':True,'format':'PNG',
              'width':pixels.width,'height':pixels.height,'pymupdf_version':RENDER_VERSION,
              'uniform_white_candidate':samples.count(255)==len(samples)}
        if info['uniform_white_candidate']:return None,info
        png=pixels.tobytes('png');require(0<len(png)<=MAX_PNG_BYTES,'render_size_limit')
        with path.open('xb') as handle:require(handle.write(png)==len(png),'render_failed')
        info['png_sha256']=sha(png)
        return path,info


def page_blocks(page):
    require(isinstance(page,Mapping),'output_invalid')
    settings=page.get('model_settings')
    require(isinstance(settings,Mapping) and settings.get('use_layout_detection') is True
            and page.get('layout_det_res') is not None,'output_invalid')
    values=page.get('parsing_res_list');require(isinstance(values,(list,tuple)) and len(values)<=2048,'output_invalid')
    blocks=[];byte_count=0
    for order,block in enumerate(values):
        if isinstance(block,Mapping):label,text,bbox=block.get('block_label'),block.get('block_content'),block.get('block_bbox')
        else:label,text,bbox=getattr(block,'label',None),getattr(block,'content',None),getattr(block,'bbox',None)
        require(isinstance(label,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}',label) and isinstance(text,str),'output_invalid')
        byte_count+=len(text.encode('utf-8'));require(byte_count<=MAX_PAGE_BYTES,'output_size_limit')
        if hasattr(bbox,'tolist'):bbox=bbox.tolist()
        require(isinstance(bbox,(list,tuple)) and len(bbox)==4,'output_invalid')
        coordinates=[]
        for coordinate in bbox:
            require(type(coordinate) in (int,float) and math.isfinite(coordinate) and abs(coordinate)<=MAX_DIMENSION*2,'output_invalid')
            coordinates.append(coordinate)
        blocks.append({'reading_order_index':order,'label':label,'text':text,'bbox_pixels':coordinates})
    text='\n\n'.join(block['text'] for block in blocks)
    require(len(text.encode('utf-8'))<=MAX_PAGE_BYTES,'output_size_limit')
    return text,blocks


def engine_main(connection,input_directory,scratch_directory):
    """Isolated model process. Never receives a provider/model/SDK credential."""
    for key in tuple(os.environ):
        if re.search(r'KEY|TOKEN|SECRET|PASSWORD',key,re.I):os.environ.pop(key,None)
    os.environ.update(WANDB_MODE='disabled',DO_NOT_TRACK='1',HF_HUB_DISABLE_TELEMETRY='1')
    with quiet():
        try:
            for package,expected in PACKAGES.items():require(importlib.metadata.version(package)==expected,'dependency_invalid')
            try:importlib.metadata.version('paddlepaddle')
            except importlib.metadata.PackageNotFoundError:pass
            else:raise BatchError('dependency_invalid')
            import paddle
            require(paddle.is_compiled_with_cuda() is True and paddle.device.cuda.device_count()>=1,'gpu_unavailable')
            paddle.set_device('gpu:0');require(paddle.get_device()=='gpu:0','gpu_unavailable')
            from paddleocr import PaddleOCRVL
            pipeline=PaddleOCRVL(device='gpu:0',pipeline_version='v1.6',vl_rec_backend='native',use_layout_detection=True,
                layout_detection_model_name='PP-DocLayoutV3',vl_rec_model_name='PaddleOCR-VL-1.6-0.9B',
                use_doc_orientation_classify=False,use_doc_unwarping=False)
            connection.send({'kind':'ready'})
        except Exception as error:
            connection.send({'kind':'error','code':error.code if isinstance(error,BatchError) else 'model_initialization_failed'});return
        while True:
            try:message=connection.recv()
            except EOFError:return
            if message is None:return
            started=time.monotonic();render=None
            try:
                source,page_number=message['source'],message['page_number']
                index=integer(source['index'],0,9999,'configuration_invalid')
                require(source['alias']==alias(index) and page_number in ranges(source['pending_page_ranges'],source['page_count']),'page_not_pending')
                path=Path(input_directory)/alias(index)
                image,render=render_page(path,page_number,source,scratch_directory)
                if image is None:raise BatchError('uniform_white_render')
                pages=list(pipeline.predict(input=str(image)));require(len(pages)==1,'output_invalid')
                text,blocks=page_blocks(pages[0])
                require(bool(text.strip()),'no_machine_text')
                connection.send({'status':'machine_ocr_extracted','text':text,'blocks':blocks,'render':render,'seconds':round(time.monotonic()-started,3)})
            except Exception as error:
                connection.send({'status':'pending','code':error.code if isinstance(error,BatchError) else 'page_ocr_failed',
                                 'render':render,'seconds':round(time.monotonic()-started,3)})
            finally:
                image_path=Path(scratch_directory)/'render.png'
                if image_path.exists() and not image_path.is_symlink():image_path.unlink()


class ProcessEngine:
    def __init__(self,input_directory,scratch_directory,deadline,clock=time.monotonic):
        self.input_directory=input_directory;self.scratch_directory=scratch_directory;self.deadline=deadline;self.clock=clock
        self.process=None;self.connection=None;self.restarts=0

    def start(self):
        require(self.restarts<3 and self.deadline-self.clock()>30,'deadline_reached');self.restarts+=1
        context=multiprocessing.get_context('spawn');parent,child=context.Pipe()
        # Allow the official pipeline to create its own worker processes. The
        # outer supervisor owns and kills the complete Linux process group.
        self.process=context.Process(target=engine_main,args=(child,str(self.input_directory),str(self.scratch_directory)))
        self.process.start();child.close();self.connection=parent
        if not parent.poll(min(600,max(0,self.deadline-self.clock()))):self.close();raise BatchError('model_initialization_failed')
        try:message=parent.recv()
        except Exception:self.close();raise BatchError('model_initialization_failed') from None
        if message.get('kind')!='ready':self.close();raise BatchError('model_initialization_failed')

    def page(self,source,page_number,seconds):
        if self.process is None or not self.process.is_alive():self.start()
        self.connection.send({'source':source,'page_number':page_number})
        timeout=min(seconds,max(0,self.deadline-self.clock()))
        if timeout<=0 or not self.connection.poll(timeout):
            self.close();return {'status':'pending','code':'page_timeout','render':None,'seconds':timeout}
        try:return self.connection.recv()
        except Exception:
            self.close();return {'status':'pending','code':'engine_failed','render':None,'seconds':0}

    def close(self):
        if self.process is not None:
            if self.process.is_alive():self.process.terminate()
            self.process.join(timeout=5)
            if self.process.is_alive():self.process.kill();self.process.join(timeout=5)
            self.process=None
        if self.connection is not None:self.connection.close();self.connection=None


def page_record(job,manifest,key,response):
    source=manifest['sources'][key['source_index']]
    require(isinstance(response,dict) and response.get('status') in ('machine_ocr_extracted','pending'),'output_invalid')
    status=response['status'];seconds=response.get('seconds',0)
    require(type(seconds) in (int,float) and math.isfinite(seconds) and 0<=seconds<=18000,'output_invalid')
    metadata={'target_role':'solver','content_type':'machine_ocr_document_page','extraction':'machine_ocr',
        'machine_ocr':True,'human_reviewed':False,'scientifically_verified':False,'training_eligible':False,
        'review_status':'machine_ocr_pending_review','source_artifact':job['source_artifact'],
        'source_manifest_sha256':job['source_manifest_sha256'],'source_bundle_id':manifest['bundle_id'],
        'page_key':{'source_index':key['source_index'],'page_number':key['page_number']},
        'haslalab_provenance':{'source_id':source['source_id'],'local_source_sha256':source['pdf_sha256'],
            'source_family':source['source_family'],'original_locator':'page:'+str(key['page_number']),'extraction':'machine_ocr'},
        'source_alias':source['alias'],'drive_file_id':source['drive_file_id'],
        'pipeline':'PaddleOCR-VL-1.6-full-native-gpu0','packages':dict(PACKAGES),'render':response.get('render'),
        'page_processing_seconds':seconds,'text_is_model_output_not_ground_truth':True}
    exclusions=[item['reason'] for item in job.get('learning_exclusions',[]) if item['source_index']==key['source_index'] and item['page_number']==key['page_number']]
    metadata.update(learning_excluded=bool(exclusions),learning_exclusion_reasons=exclusions)
    if status=='machine_ocr_extracted':
        text=response.get('text');blocks=response.get('blocks')
        require(isinstance(text,str) and isinstance(blocks,list) and len(blocks)<=2048,'output_invalid')
        require(len(text.encode('utf-8'))<=MAX_PAGE_BYTES and all(isinstance(b,dict) and b.get('reading_order_index')==i
            and isinstance(b.get('text'),str) for i,b in enumerate(blocks)),'output_invalid')
        require(text=='\n\n'.join(b['text'] for b in blocks),'output_invalid')
        flags=[]
        if len(text.strip())<80:flags.append('sparse_machine_text')
        if text.count('\ufffd')/max(1,len(text))>0.02:flags.append('replacement_characters')
        if not text.strip():flags.append('no_machine_text')
        metadata['quality_flags']=flags;metadata['text_sha256']=sha(text.encode('utf-8'))
        row={'status':status,'text':text,'blocks':blocks,'metadata':metadata}
    else:
        code=response.get('code');require(code in ERRORS,'output_invalid')
        row={'status':'pending','error_code':code,'text':None,'blocks':[],'metadata':metadata}
    require(len(canonical(row))<=16*1024**2,'output_size_limit')
    return row


def scope_status(job,cursor,extracted,failed,total_pending):
    if cursor<len(job['page_keys']) or failed:return 'partial'
    if job['mode']=='calibration':return 'calibration_complete'
    if extracted==total_pending and len(job['page_keys'])==total_pending:return 'all_pending_pages_complete'
    return 'selection_complete'


def process_pages(job,manifest,pending,engine,prepare_pdf,checkpoint,deadline,*,clock=time.monotonic):
    keys=job['page_keys'];require(all((key['source_index'],key['page_number']) in pending for key in keys),'page_not_pending')
    require(len({(k['source_index'],k['page_number']) for k in keys})==len(keys),'duplicate_page')
    records=[];record_bytes=0;total_bytes=0;cursor=0;extracted=0;failed=0;checkpoints=[];last_checkpoint=clock()
    def flush(terminal=False):
        nonlocal records,record_bytes,last_checkpoint
        if not records:return
        counters={'processed_pages':cursor,'extracted_pages':extracted,'pending_attempted_pages':failed,
                  'selected_pages':len(keys),'total_source_pending_pages':len(pending)}
        state=scope_status(job,cursor,extracted,failed,len(pending)) if terminal else 'running'
        checkpoints.append(checkpoint(records,cursor,counters,state,checkpoints[-1] if checkpoints else None))
        records=[];record_bytes=0;last_checkpoint=clock()
    try:
        for key in keys:
            if clock()>=deadline:break
            source=manifest['sources'][key['source_index']]
            try:
                prepare_pdf(source)
                remaining=deadline-clock()
                if remaining<=0:break
                response=engine.page(source,key['page_number'],min(job['per_page_seconds'],remaining))
                row=page_record(job,manifest,key,response)
            except Exception as error:
                code=error.code if isinstance(error,BatchError) else 'engine_failed'
                if code=='deadline_reached':break
                row=page_record(job,manifest,key,{'status':'pending','code':code,'render':None,'seconds':0})
            size=len(canonical(row))+1
            if records and (len(records)>=job['checkpoint_pages'] or record_bytes+size>MAX_SHARD_BYTES):flush()
            if total_bytes+size>MAX_TOTAL_OCR_BYTES:break
            records.append(row);record_bytes+=size;total_bytes+=size;cursor+=1
            if row['status']=='machine_ocr_extracted':extracted+=1
            else:failed+=1
            if len(records)>=job['checkpoint_pages'] or clock()-last_checkpoint>=60:flush()
        flush(terminal=True)
        return {'kind':KIND,'status':scope_status(job,cursor,extracted,failed,len(pending)),
            'terminal':True,'mode':job['mode'],'selected_pages':len(keys),'processed_pages':cursor,
            'extracted_pages':extracted,'pending_attempted_pages':failed,'unprocessed_selected_pages':len(keys)-cursor,
            'total_source_pending_pages':len(pending),'all_source_pending_pages_extracted':extracted==len(pending) and not failed,
            'checkpoints':checkpoints,'machine_ocr':True,'human_reviewed':False,'scientifically_verified':False,
            'training_eligible':False,'next_cursor':cursor,'selection_sha256':sha(canonical(keys))}
    finally:engine.close()


def checkpoint_writer(job,manifest,run,sdk,env,entity,directory,deadline,*,privacy=assert_private,clock=time.monotonic):
    sequence=0
    def checkpoint(records,cursor,counters,state,previous):
        nonlocal sequence
        require(0<len(records)<=MAX_SHARD_PAGES and clock()<deadline,'checkpoint_failed')
        folder=Path(directory)/('checkpoint_'+str(sequence).zfill(6));folder.mkdir()
        raw=b''.join(canonical(row)+b'\n' for row in records);require(len(raw)<=MAX_SHARD_BYTES,'output_size_limit')
        require(shutil.disk_usage(folder).free>=2*len(raw)+64*1024**2,'disk_space_low')
        shard=folder/'pages.jsonl.gz'
        with shard.open('xb') as underlying:
            with gzip.GzipFile(filename='',fileobj=underlying,mode='wb',mtime=0) as compressed:compressed.write(raw)
        require(shard.stat().st_size<=MAX_SHARD_BYTES+65536,'output_size_limit')
        checkpoint_manifest={'kind':KIND,'mode':job['mode'],'scope_status':state,'source_artifact':job['source_artifact'],
            'source_manifest_sha256':job['source_manifest_sha256'],'source_bundle_id':manifest['bundle_id'],
            'selection_sha256':sha(canonical(job['page_keys'])),'next_cursor':cursor,'first_cursor':cursor-len(records),
            'counters':counters,'previous_checkpoint':previous,'machine_ocr':True,'human_reviewed':False,
            'scientifically_verified':False,'training_eligible':False,'packages':dict(PACKAGES),
            'render_policy':{'dpi':DPI,'colorspace':'RGB','alpha':False,'annotations':True,'format':'PNG','max_pixels':MAX_PIXELS},
            'worker_sha256':env['HASLA_OCR_BATCH_WORKER_SHA256'],
            'shard':{'name':'pages.jsonl.gz','records':len(records),'raw_bytes':len(raw),'gzip_bytes':shard.stat().st_size,
                     'gzip_sha256':sha_file(shard),'raw_sha256':sha(raw)}}
        checkpoint_path=folder/'checkpoint.json'
        with checkpoint_path.open('xb') as handle:handle.write(canonical(checkpoint_manifest))
        privacy(env,entity)
        name=env['RUN']+'-checkpoint-'+str(sequence).zfill(6)
        artifact=sdk.Artifact(name,type=OUTPUT_TYPE,metadata={'private':True,'kind':KIND,'mode':job['mode'],
            'processed_pages':cursor,'source_manifest_sha256':job['source_manifest_sha256'],'machine_ocr':True,'training_eligible':False})
        artifact.add_file(str(shard),name='pages.jsonl.gz');artifact.add_file(str(checkpoint_path),name='checkpoint.json')
        privacy(env,entity);run.log_artifact(artifact)
        require(deadline-clock()>0,'deadline_reached');artifact.wait(timeout=min(120,deadline-clock()))
        reference=artifact.qualified_name
        require(artifact_entity(reference)==entity and reference.rsplit('/',1)[-1].startswith(name+':v'),'checkpoint_failed')
        require(artifact.state=='COMMITTED','checkpoint_failed');privacy(env,entity)
        result={'artifact':reference,'manifest_sha256':sha_file(checkpoint_path),'next_cursor':cursor}
        sequence+=1
        # The immutable checkpoint is already committed. A failed heartbeat or
        # local transient-file cleanup must not erase its returned receipt.
        with contextlib.suppress(Exception):
            run.summary['private_ocr_batch_progress_json']=json.dumps({'kind':KIND,'terminal':False,**counters,'latest_checkpoint':result},ensure_ascii=True)
        with contextlib.suppress(Exception):
            run.log({'private_ocr_pages_processed':cursor,'private_ocr_pages_extracted':counters['extracted_pages']},commit=True)
        # SDK upload has committed; remove only these owned transient shard files.
        for path in (shard,checkpoint_path):
            with contextlib.suppress(OSError):path.unlink()
        with contextlib.suppress(OSError):folder.rmdir()
        return result
    return checkpoint


def calibration_proof(job,sdk,env,entity,directory,*,privacy=assert_private):
    if job['mode']!='bulk':return
    proof=job['calibration_checkpoint'];privacy(env,entity)
    artifact=sdk.Api(api_key=env['WANDB_API_KEY'],overrides={'base_url':'https://api.wandb.ai'},timeout=30).artifact(proof['artifact'],type=OUTPUT_TYPE)
    require(artifact.qualified_name==proof['artifact'] and artifact.type==OUTPUT_TYPE and artifact.state=='COMMITTED'
            and getattr(artifact,'is_link',False) is False and artifact.metadata.get('private') is True,'artifact_invalid')
    entries=artifact.manifest.entries
    require(set(entries)=={'checkpoint.json','pages.jsonl.gz'} and all(getattr(e,'ref',None) is None
            and str(getattr(e,'path',''))==name for name,e in entries.items())
            and 0<entries['checkpoint.json'].size<=MAX_MANIFEST_BYTES,'artifact_invalid')
    path=downloaded_file(artifact,'checkpoint.json',directory,MAX_MANIFEST_BYTES)
    require(sha_file(path)==proof['manifest_sha256'],'manifest_hash_mismatch');value=json_read(path.read_bytes())
    require(value.get('kind')==KIND and value.get('mode')=='calibration' and value.get('source_manifest_sha256')==job['source_manifest_sha256']
            and value.get('machine_ocr') is True and value.get('training_eligible') is False and value.get('packages')==PACKAGES
            and value.get('source_artifact')==job['source_artifact'] and value.get('human_reviewed') is False
            and value.get('scientifically_verified') is False and value.get('counters',{}).get('selected_pages')==CALIBRATION_PAGES
            and value.get('counters',{}).get('processed_pages')==CALIBRATION_PAGES
            and value.get('counters',{}).get('extracted_pages',0)>0,'configuration_invalid')


def run_batch(env=None,*,sdk=None,privacy=assert_private,engine_factory=ProcessEngine,clock=time.monotonic):
    env=os.environ if env is None else env;started=clock()
    raw=env.get('HASLA_OCR_BATCH_JOB','');require(isinstance(raw,str) and 0<len(raw.encode())<=1024**2,'configuration_invalid')
    job=validate_job(json_read(raw));entity=artifact_entity(job['source_artifact']);credentials(env,entity)
    require(isinstance(env.get('RUN'),str) and re.fullmatch(r'hasla-private-ocr-batch-[0-9]{1,32}',env['RUN']),'configuration_invalid')
    checked_hash(env.get('HASLA_OCR_BATCH_WORKER_SHA256'),'configuration_invalid')
    require(sha_file(__file__)==env['HASLA_OCR_BATCH_WORKER_SHA256'],'configuration_invalid')
    deadline=started+job['runtime_seconds'];work_deadline=deadline-180
    run=None;result=None;stop=threading.Event();thread=None;log_lock=threading.Lock();committed=[];last_counts={}
    with quiet():
        privacy(env,entity)
        if sdk is None:import wandb as sdk
        parent=private_directory(Path(tempfile.gettempdir()))
        with tempfile.TemporaryDirectory(prefix='hasla-private-ocr-batch-',dir=parent) as temporary:
            directory=Path(temporary);inputs=directory/'inputs';inputs.mkdir();scratch=directory/'render';scratch.mkdir()
            outputs=directory/'outputs';outputs.mkdir();proof_dir=directory/'calibration';proof_dir.mkdir()
            try:
                artifact,manifest,pending,_=open_source(job['source_artifact'],env,inputs,expected_hash=job['source_manifest_sha256'],sdk=sdk,privacy=privacy,
                    expected_sources=job['expected_source_count'],expected_pending=job['expected_pending_pages'])
                if job['page_keys']=='all_pending':
                    job={**job,'page_keys':[{'source_index':index,'page_number':page} for index,page in sorted(pending)]}
                require(all((k['source_index'],k['page_number']) in pending for k in job['page_keys']),'page_not_pending')
                selected={(k['source_index'],k['page_number']) for k in job['page_keys']}
                require(all((k['source_index'],k['page_number']) in selected for k in job.get('learning_exclusions',[])),'page_not_pending')
                calibration_proof(job,sdk,env,entity,proof_dir,privacy=privacy)
                require(clock()<work_deadline,'deadline_reached')
                settings=sdk.Settings(console='off',disable_code=True,save_code=False,disable_git=True,disable_job_creation=True,
                    x_disable_meta=True,x_disable_stats=True,init_timeout=60,finish_timeout=30,base_url='https://api.wandb.ai')
                privacy(env,entity)
                run=sdk.init(entity=entity,project=PROJECT,id=env['RUN'],name=env['RUN'],resume='never',job_type='private-pending-page-ocr',
                    config={'kind':KIND,'mode':job['mode'],'selected_pages':len(job['page_keys']),'training_eligible':False},settings=settings,dir=str(directory))
                def heartbeat():
                    while not stop.wait(20):
                        try:
                            privacy(env,entity)
                            with log_lock:
                                if stop.is_set():return
                                run.log({'private_ocr_alive':1,'private_ocr_elapsed_seconds':round(clock()-started,3)},commit=True)
                        except Exception:pass
                thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
                verified={}
                def prepare_pdf(source):
                    if source['index'] in verified:return verified[source['index']]
                    privacy(env,entity)
                    require(clock()<work_deadline,'deadline_reached')
                    require(shutil.disk_usage(inputs).free>=2*source['pdf_bytes']+128*1024**2,'disk_space_low')
                    path=downloaded_file(artifact,source['alias'],inputs,MAX_PDF_BYTES);verify_pdf(path,source,inputs)
                    verified[source['index']]=path;return path
                writer=checkpoint_writer(job,manifest,run,sdk,env,entity,outputs,deadline,privacy=privacy,clock=clock)
                def checkpoint(records,cursor,counters,state,previous):
                    pointer=writer(records,cursor,counters,state,previous)
                    committed.append(pointer);last_counts.update(counters)
                    receipt(env,{'kind':KIND,'status':'running','terminal':False,'checkpoints':list(committed),**counters})
                    return pointer
                engine=engine_factory(inputs,scratch,work_deadline,clock)
                result=process_pages(job,manifest,pending,engine,prepare_pdf,checkpoint,work_deadline,clock=clock)
                for index,path in verified.items():verify_pdf(path,manifest['sources'][index],inputs)
                result.update(source_pdfs_byte_verified=len(verified),source_aliases_inventory_checked=len(manifest['sources']),
                              original_selected_pdf_bytes_unchanged=True,worker_seconds=round(clock()-started,3))
            except Exception as error:
                result={'kind':KIND,'status':'partial' if committed else 'failed','terminal':True,
                        'code':error.code if isinstance(error,BatchError) else 'worker_failed','checkpoints':list(committed),**last_counts,
                        'machine_ocr':True,'human_reviewed':False,'scientifically_verified':False,'training_eligible':False}
            finally:
                stop.set()
                if thread is not None:thread.join(timeout=1)
                if run is not None:
                    try:
                        privacy(env,entity)
                        run.summary['private_ocr_batch_worker_sha256']=env['HASLA_OCR_BATCH_WORKER_SHA256']
                        run.summary['private_ocr_batch_result_json']=json.dumps(result,ensure_ascii=True,separators=(',',':'))
                    except Exception:pass
                    with log_lock:
                        with contextlib.suppress(Exception):run.finish(exit_code=0 if result and result.get('status') in ('calibration_complete','selection_complete','all_pending_pages_complete') else 1)
                if result is not None:receipt(env,result)
    return result


def receipt(env,value):
    raw=env.get('HASLA_OCR_BATCH_RESULT_PATH')
    if not raw:return
    path=Path(raw);parent=private_directory(path.parent)
    require(parent.name.startswith('hasla-private-ocr-supervisor-') and path.name=='result.json','path_invalid')
    temporary=parent/'result.updated.json'
    require(not temporary.exists() and not path.is_symlink(),'path_invalid')
    with temporary.open('xb') as stream:stream.write(canonical(value))
    temporary.replace(path)


def supervisor_environment(env,result_path):
    allowed=('PATH','HOME','LD_LIBRARY_PATH','CUDA_HOME','CUDA_PATH','CUDA_VISIBLE_DEVICES','NVIDIA_VISIBLE_DEVICES',
        'NVIDIA_DRIVER_CAPABILITIES','LANG','LC_ALL','TMPDIR','VIRTUAL_ENV','HF_HOME','PADDLE_PDX_CACHE_HOME',
        'WANDB_API_KEY','WANDB_ENTITY','WANDB_PROJECT','RUN','HASLA_OCR_BATCH_JOB','HASLA_OCR_BATCH_WORKER_SHA256')
    result={key:env[key] for key in allowed if key in env}
    result.update(HASLA_OCR_BATCH_RESULT_PATH=str(result_path),WANDB_SILENT='true',WANDB_CONSOLE='off',
                  HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',PYTHONIOENCODING='utf-8')
    return result


def kill_owned_process(process):
    if process.poll() is not None:return
    # This group was created by this supervisor, never a supplied/external PID.
    with contextlib.suppress(ProcessLookupError):os.killpg(process.pid,signal.SIGTERM)
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):os.killpg(process.pid,signal.SIGKILL)
        process.wait(timeout=5)


def supervise(env=None,*,popen=subprocess.Popen,killer=kill_owned_process):
    env=os.environ if env is None else env
    require(sys.platform.startswith('linux'),'configuration_invalid')
    job=validate_job(json_read(env.get('HASLA_OCR_BATCH_JOB','')))
    credentials(env,artifact_entity(job['source_artifact']))
    parent=private_directory(Path(tempfile.gettempdir()))
    with tempfile.TemporaryDirectory(prefix='hasla-private-ocr-supervisor-',dir=parent) as temporary:
        path=Path(temporary)/'result.json';process=None;timed_out=False
        try:
            process=popen([sys.executable,str(Path(__file__).resolve()),'--_worker'],start_new_session=True,
                stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=supervisor_environment(env,path))
            try:process.wait(timeout=job['runtime_seconds']-15)
            except subprocess.TimeoutExpired:timed_out=True;killer(process)
            if path.is_file() and not path.is_symlink() and path.stat().st_size<=2*1024**2:
                value=json_read(path.read_bytes())
                require(value.get('kind')==KIND,'output_invalid')
                if timed_out or value.get('terminal') is not True:
                    value.update(status='partial',terminal=True,code='worker_timeout' if timed_out else 'worker_failed')
                return value
            return {'kind':KIND,'status':'failed','terminal':True,'code':'worker_timeout' if timed_out else 'worker_failed',
                    'machine_ocr':True,'training_eligible':False,'human_reviewed':False,'scientifically_verified':False}
        finally:
            if process is not None and process.poll() is None:killer(process)


def main(argv=None):
    argv=sys.argv[1:] if argv is None else argv
    try:
        require(set(argv)<={'--inspect-source','--_worker'} and len(argv)<=1,'configuration_invalid')
        if '--inspect-source' in argv:
            event=inspect_source()
        elif '--_worker' in argv:
            event=run_batch()
        else:event=supervise()
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

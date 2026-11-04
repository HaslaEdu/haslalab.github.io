"""One public-page PaddleOCR-VL-1.6 GPU calibration, never model training.

Only fixed aggregate results enter an existing PRIVATE W&B project. No private
document, adapter, arbitrary URL/model, HF credential or RunPod API key is used.
The outer Pod launcher pins this file and private_ocr_probe.py by raw-byte SHA.
"""
import argparse
import base64
import contextlib
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

PROJECT = 'hasla-ai-private-training'
PREFIX = 'hasla-private-ocr-probe-'
KIND = 'public_gpu_ocr_calibration_v1'
DEMO_URL = 'https://paddle-model-ecology.bj.bcebos.com/paddlex/imgs/demo_image/paddleocr_vl_demo.png'
PACKAGES = {'paddlepaddle-gpu':'3.2.1', 'paddleocr':'3.6.0', 'paddlex':'3.6.0'}
STAGES = frozenset(('configuration','privacy','setup','dependencies','initialization','prediction','result_validation','publication','complete'))
ERRORS = frozenset(('configuration_invalid','public_code_mismatch','private_project_unverified','setup_failed','setup_timeout',
    'dependency_missing','dependency_version_mismatch','cpu_paddle_installed','gpu_unavailable','initialization_failed',
    'prediction_failed','layout_stage_missing','unsupported_result','no_result','no_text','inference_timeout',
    'inference_process_failed','invalid_result','deadline_reached','publication_failed','worker_failed','terminal_without_result'))
TIMINGS = ('setup_seconds','initialization_seconds','prediction_seconds','total_seconds')
BLOCK_TYPES = frozenset(('text','formula','table','other'))
HEARTBEAT_SECONDS = 20


class ProbeError(ValueError):
    def __init__(self, code):
        self.code = code if code in ERRORS else 'worker_failed'
        super().__init__(self.code)


def require(condition, code):
    if not condition:
        raise ProbeError(code)


def result(status, stage, error_code=None):
    require(status in ('succeeded','failed') and stage in STAGES, 'invalid_result')
    value = {'kind':KIND, 'status':status, 'stage':stage, 'public_sample_only':True, 'private_inputs_read':0,
             'private_document_uploads':0, 'pages_requested':1, 'device':'gpu:0', 'pipeline_version':'v1.6',
             'full_layout_and_vlm_pipeline':True, 'layout_model':'PP-DocLayoutV3',
             'recognition_model':'PaddleOCR-VL-1.6-0.9B', 'pinned_packages':dict(PACKAGES),
             'timing_scope':'worker_start_through_inference_before_result_publication'}
    if error_code is not None:
        require(error_code in ERRORS, 'invalid_result'); value['error_code']=error_code
    return value


def clean_result(value):
    require(isinstance(value,dict), 'invalid_result')
    status, stage, code = value.get('status'),value.get('stage'),value.get('error_code')
    require(status in ('succeeded','failed') and stage in STAGES, 'invalid_result')
    require((status=='failed' and code in ERRORS) or (status=='succeeded' and code is None and stage=='complete'), 'invalid_result')
    clean=result(status,stage,code)
    require(all(value.get(key)==expected for key,expected in clean.items()), 'invalid_result')
    if status=='failed':
        return clean
    for key in ('pages','blocks','characters'):
        number=value.get(key)
        require(type(number) is int and 1<=number<=10000000 and (key!='pages' or number==1),'invalid_result')
        clean[key]=number
    for key in TIMINGS:
        number=value.get(key)
        require(type(number) in (int,float) and math.isfinite(number) and 0<=number<=1800,'invalid_result')
        clean[key]=number
    require(clean['total_seconds']+0.01>=sum(clean[key] for key in TIMINGS[:-1]),'invalid_result')
    types=value.get('block_types')
    require(isinstance(types,dict) and set(types)<=BLOCK_TYPES and all(type(n) is int and 0<=n<=10000000 for n in types.values())
            and sum(types.values())==clean['blocks'] and value.get('layout_stage_present') is True
            and value.get('gpu_backend_verified') is True,'invalid_result')
    clean.update(block_types=dict(types),layout_stage_present=True,gpu_backend_verified=True)
    return clean


@contextlib.contextmanager
def quiet():
    saved=[]
    with open(os.devnull,'w') as sink:
        with contextlib.redirect_stdout(sink),contextlib.redirect_stderr(sink):
            try:
                for number in (1,2):
                    saved.append((number,os.dup(number)));os.dup2(sink.fileno(),number)
                yield
            finally:
                for number,previous in reversed(saved):
                    os.dup2(previous,number);os.close(previous)


def load_helper(path, expected):
    require(isinstance(expected,str) and re.fullmatch(r'[a-f0-9]{64}',expected),'configuration_invalid')
    path=Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size<=256*1024,'public_code_mismatch')
    require(hashlib.sha256(path.read_bytes()).hexdigest()==expected,'public_code_mismatch')
    spec=importlib.util.spec_from_file_location('hasla_pinned_public_ocr_helper',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    require(module.DEMO_URL==DEMO_URL,'public_code_mismatch')
    return module


def dependencies(version=importlib.metadata.version, paddle=None):
    try:
        version('paddlepaddle')
    except importlib.metadata.PackageNotFoundError:
        pass
    else:
        raise ProbeError('cpu_paddle_installed')
    for package,expected in PACKAGES.items():
        try:
            actual=version(package)
        except importlib.metadata.PackageNotFoundError:
            raise ProbeError('dependency_missing') from None
        require(actual==expected,'dependency_version_mismatch')
    if paddle is None:
        import paddle
    require(paddle.is_compiled_with_cuda() is True and paddle.device.cuda.device_count()>=1,'gpu_unavailable')
    paddle.set_device('gpu:0')
    require(paddle.get_device()=='gpu:0','gpu_unavailable')


def infer_once(helper, *, dependency_check=dependencies, factory=None, clock=time.monotonic):
    started,stage=clock(),'dependencies'
    try:
        dependency_check()
        if factory is None:
            from paddleocr import PaddleOCRVL
            factory=PaddleOCRVL
        stage='initialization';before=clock()
        pipeline=factory(device='gpu:0',pipeline_version='v1.6',vl_rec_backend='native',
            layout_detection_model_name='PP-DocLayoutV3',vl_rec_model_name='PaddleOCR-VL-1.6-0.9B',
            use_layout_detection=True,use_doc_orientation_classify=False,use_doc_unwarping=False)
        initialized=clock();stage='prediction'
        pages=list(pipeline.predict(input=DEMO_URL));predicted=clock();stage='result_validation'
        require(len(pages)==1,'no_result')
        try:
            counts=helper.summarize_page(pages[0])
        except Exception as error:
            code=getattr(error,'code',None)
            raise ProbeError(code if code in ('layout_stage_missing','unsupported_result') else 'invalid_result') from None
        require(counts['blocks']>0 and counts['characters']>0,'no_text')
        value=result('succeeded','complete')
        value.update(counts,setup_seconds=0,initialization_seconds=round(initialized-before,3),
                     prediction_seconds=round(predicted-initialized,3),total_seconds=round(clock()-started,3),gpu_backend_verified=True)
        return clean_result(value)
    except ProbeError as error:
        return result('failed',stage,error.code)
    except Exception:
        code='initialization_failed' if stage=='initialization' else 'prediction_failed' if stage=='prediction' else 'worker_failed'
        return result('failed',stage,code)


def private_project(env, opener=urllib.request.urlopen):
    entity=env.get('WANDB_ENTITY','')
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,128}',entity) and env.get('WANDB_PROJECT')==PROJECT
            and isinstance(env.get('WANDB_API_KEY'),str) and bool(env['WANDB_API_KEY']),'configuration_invalid')
    document='query($e:String!,$p:String!){project(name:$p,entityName:$e){name access}}'
    request=urllib.request.Request('https://api.wandb.ai/graphql',data=json.dumps({'query':document,'variables':{'e':entity,'p':PROJECT}}).encode(),
        headers={'Content-Type':'application/json','Authorization':'Basic '+base64.b64encode(('api:'+env['WANDB_API_KEY']).encode()).decode()})
    try:
        with opener(request,timeout=15) as response:
            raw=response.read(128*1024+1)
        require(len(raw)<=128*1024,'private_project_unverified')
        data=json.loads(raw)
        project=(data.get('data') or {}).get('project')
        require(not data.get('errors') and isinstance(project,dict) and project.get('name')==PROJECT
                and project.get('access')=='PRIVATE','private_project_unverified')
    except ProbeError:
        raise
    except Exception:
        raise ProbeError('private_project_unverified') from None
    return entity


def validate_env(env):
    run=env.get('RUN','')
    require(isinstance(run,str) and re.fullmatch(re.escape(PREFIX)+r'[0-9]{1,32}',run),'configuration_invalid')
    forbidden=('RUNPOD_API_KEY','RUNPOD_API_TOKEN','HF_TOKEN','HF_API_TOKEN','HUGGINGFACE_TOKEN','HUGGING_FACE_HUB_TOKEN','OPENAI_API_KEY')
    require(not any(env.get(key) for key in forbidden),'configuration_invalid')
    for key in ('HASLA_OCR_GPU_WORKER_SHA256','HASLA_OCR_GPU_HELPER_SHA256'):
        require(isinstance(env.get(key),str) and re.fullmatch(r'[a-f0-9]{64}',env[key]),'configuration_invalid')
    require(hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==env['HASLA_OCR_GPU_WORKER_SHA256'],'public_code_mismatch')
    return run


def infer_environment(env):
    allowed=('PATH','HOME','LD_LIBRARY_PATH','CUDA_HOME','CUDA_PATH','CUDA_VISIBLE_DEVICES','NVIDIA_VISIBLE_DEVICES',
             'LANG','LC_ALL','TMPDIR','VIRTUAL_ENV','HF_HOME','PADDLE_PDX_CACHE_HOME')
    safe={key:env[key] for key in allowed if key in env}
    safe.update(HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',WANDB_MODE='disabled',PYTHONIOENCODING='utf-8')
    safe['HASLA_OCR_GPU_HELPER_SHA256']=env['HASLA_OCR_GPU_HELPER_SHA256']
    return safe


def publish_result(run,value,env):
    run.summary['private_ocr_gpu_kind']=KIND
    run.summary['private_ocr_gpu_worker_sha256']=env['HASLA_OCR_GPU_WORKER_SHA256']
    run.summary['private_ocr_gpu_helper_sha256']=env['HASLA_OCR_GPU_HELPER_SHA256']
    run.summary['private_ocr_gpu_result']=value
    # Scalar is written last, after the code pins that the parent verifies.
    run.summary['private_ocr_gpu_result_json']=json.dumps(value,ensure_ascii=True,separators=(',',':'))


def run_worker(env=None, *, sdk=None, private_check=private_project, runner=subprocess.run, clock=time.monotonic):
    env=os.environ if env is None else env
    started,stage,run,verified=clock(),'configuration',None,False
    heartbeat_stop=threading.Event();heartbeat_thread=None;log_lock=threading.Lock()
    with quiet():
        try:
            name=validate_env(env)
            helper_path=Path(__file__).with_name('private_ocr_probe.py')
            load_helper(helper_path,env['HASLA_OCR_GPU_HELPER_SHA256'])
            stage='privacy';entity=private_check(env);verified=True
            if sdk is None:
                os.environ['WANDB_SILENT']='true';os.environ['WANDB_CONSOLE']='off'
                import wandb as sdk
            with tempfile.TemporaryDirectory(prefix='hasla-public-gpu-ocr-') as temporary:
                settings=sdk.Settings(console='off',disable_code=True,save_code=False,disable_git=True,
                    disable_job_creation=True,x_disable_meta=True,x_disable_stats=True,init_timeout=60)
                private_check(env)
                run=sdk.init(entity=entity,project=PROJECT,id=name,name=name,resume='never',job_type='public-gpu-ocr-calibration',
                    config={'kind':KIND,'public_sample_only':True},settings=settings,dir=temporary)
                stage='setup'
                def heartbeat():
                    try:
                        private_check(env)
                        with log_lock:
                            elapsed=clock()-started
                            if heartbeat_stop.is_set() or not 0<=elapsed<=1680:return
                            run.log({'public_gpu_ocr_alive':1,'public_gpu_ocr_elapsed_seconds':round(elapsed,3),
                                     'public_gpu_ocr_stage':stage if stage in STAGES else 'setup'},commit=True)
                    except Exception:
                        # Telemetry failure is not proof that inference failed.
                        pass
                heartbeat()
                def keep_alive():
                    while not heartbeat_stop.wait(HEARTBEAT_SECONDS):heartbeat()
                heartbeat_thread=threading.Thread(target=keep_alive,daemon=True)
                heartbeat_thread.start()
                commands=((sys.executable,'-m','pip','install','--quiet','paddlepaddle-gpu==3.2.1','-i','https://www.paddlepaddle.org.cn/packages/stable/cu126/'),
                          (sys.executable,'-m','pip','install','--quiet','paddleocr[doc-parser]==3.6.0','paddlex==3.6.0'))
                for command in commands:
                    remaining=1500-(clock()-started)
                    require(remaining>120,'deadline_reached')
                    try:
                        done=runner(list(command),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL,
                                    check=False,timeout=min(900,remaining-120),env=infer_environment(env))
                    except subprocess.TimeoutExpired:
                        raise ProbeError('setup_timeout') from None
                    require(done.returncode==0,'setup_failed')
                setup=clock()-started;stage='prediction'
                output=Path(temporary)/'aggregate.json'
                remaining=1620-(clock()-started)
                require(remaining>60,'deadline_reached')
                try:
                    done=runner([sys.executable,str(Path(__file__).resolve()),'--infer','--result',str(output)],
                        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL,check=False,
                        timeout=min(remaining-60,1500),env=infer_environment(env))
                except subprocess.TimeoutExpired:
                    raise ProbeError('inference_timeout') from None
                require(output.is_file() and output.stat().st_size<=16384,'inference_process_failed')
                value=clean_result(json.loads(output.read_text(encoding='utf-8')))
                require(done.returncode==(0 if value['status']=='succeeded' else 1),'invalid_result')
                if value['status']=='succeeded':
                    value.update(setup_seconds=round(setup,3),total_seconds=round(clock()-started,3))
                    value=clean_result(value)
                stage='publication';private_check(env)
                publish_result(run,value,env)
                return value
        except Exception as error:
            code=error.code if isinstance(error,ProbeError) else 'worker_failed'
            value=result('failed',stage,code)
            if verified and run is not None:
                try:
                    private_check(env)
                    publish_result(run,value,env)
                except Exception:
                    pass
            return value
        finally:
            heartbeat_stop.set()
            if heartbeat_thread is not None:heartbeat_thread.join(timeout=1)
            if run is not None:
                with log_lock:
                    with contextlib.suppress(Exception):
                        run.finish(exit_code=0 if 'value' in locals() and value.get('status')=='succeeded' else 1)


def main(argv=None):
    parser=argparse.ArgumentParser(exit_on_error=False)
    parser.add_argument('--infer',action='store_true');parser.add_argument('--result',type=Path)
    try:
        args,unknown=parser.parse_known_args(argv)
        require(not unknown and (args.infer==bool(args.result)),'configuration_invalid')
        if args.infer:
            with quiet():
                helper=load_helper(Path(__file__).with_name('private_ocr_probe.py'),os.environ.get('HASLA_OCR_GPU_HELPER_SHA256'))
                value=infer_once(helper)
                with args.result.open('x',encoding='utf-8') as stream:
                    stream.write(json.dumps(value,ensure_ascii=True,separators=(',',':')))
        else:
            value=run_worker()
    except Exception:
        value=result('failed','configuration','configuration_invalid')
    # No arbitrary exception/provider output, recognized text or adapter claim.
    if not (argv and '--infer' in argv) and '--infer' not in sys.argv:
        print(json.dumps(value,ensure_ascii=True,separators=(',',':')),flush=True)
    return 0 if value['status']=='succeeded' else 1


if __name__=='__main__':
    raise SystemExit(main())

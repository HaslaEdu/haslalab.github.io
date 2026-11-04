"""Prepare and stage a token-checked PRIVATE native delta on CPU only."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urljoin, urlsplit

import private_contest_delta as delta
import private_fetch_contest_sources as fetch
import private_stage_corpus as privacy
import private_corpus_run as cloud

TOKENIZER_COMMIT='976055f8c83f394f35dbd3ab09a285a984907bd0'
TOKENIZER_FILES={
    'tokenizer.json':(7032399,'19564a48c4f71a2a1b937cce34c737a1e662b171c5f5d7edf641a15cd896f07d'),
    'tokenizer_config.json':(8291,'ab43f460108ca40fbb09fa537696baf862b6a9b46a2c6688b9de711293e3ddc4')}


class PreparationError(ValueError):pass


class PipelineFailure(PreparationError):
    def __init__(self,phase,error):
        from private_text_pack import PackError
        known=isinstance(error,(PreparationError,delta.DeltaError,fetch.FetchError,PackError))
        code=str(error) if known and re.fullmatch(r'[a-z_]{1,80}',str(error)) else 'private_native_preparation_failed'
        super().__init__(code)
        self.phase=phase
        self.error_class=type(error).__name__


def require(value,code):
    if not value:raise PreparationError(code)


def load_manifest(env):
    raw=env.get('HASLA_CONTEST_DELTA_MANIFEST','')
    require(isinstance(raw,str) and 0<len(raw.encode())<=16384,'manifest_invalid')
    value=privacy.strict_json(raw)
    fields={'version','source_artifact','inventory_sha256','packed_artifact','packed_files','dataset_version','authorization_note'}
    require(isinstance(value,dict) and set(value)==fields and type(value['version']) is int and value['version']==1,'manifest_invalid')
    entity,_=delta.reference_parts(value['source_artifact'],env)
    require(re.fullmatch(re.escape(entity+'/'+fetch.PROJECT+'/')+r'[A-Za-z0-9_.-]+:v[0-9]+',value['packed_artifact']),
            'manifest_invalid')
    delta.checked_sha(value['inventory_sha256'])
    require(isinstance(value['dataset_version'],str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',value['dataset_version']),
            'manifest_invalid')
    require(isinstance(value['authorization_note'],str) and 1<=len(value['authorization_note'])<=2000,'manifest_invalid')
    require(isinstance(value['packed_files'],dict) and set(value['packed_files'])=={'train','validation'},'manifest_invalid')
    for item in value['packed_files'].values():
        require(isinstance(item,dict) and set(item)=={'bytes','sha256','records'}
                and type(item['bytes']) is int and 0<item['bytes']<=256*1024**2
                and type(item['records']) is int and 0<item['records']<=1000000,'manifest_invalid')
        delta.checked_sha(item['sha256'])
    return value,entity


def download_packed(manifest,env,entity,root,sdk):
    """Read only two fixed entries after every SDK path/ref/size gate."""
    root=Path(root);require(not root.exists(),'workspace_collision');root.mkdir()
    deadline=time.monotonic()+900
    fetch.assert_private(entity,env,deadline)
    api=sdk.Api(api_key=env['WANDB_API_KEY'],overrides={'base_url':fetch.WANDB_API},timeout=30)
    reference=manifest['packed_artifact'];artifact=api.artifact(reference,type='dataset')
    require(artifact.qualified_name==reference and artifact.type=='dataset' and artifact.state=='COMMITTED'
            and not getattr(artifact,'is_link',False),'packed_artifact_invalid')
    entries=artifact.manifest.entries
    require(isinstance(entries,dict) and set(entries)=={'train.text.jsonl','validation.text.jsonl'},'packed_artifact_invalid')
    files={}
    for split,item in manifest['packed_files'].items():
        name=split+'.text.jsonl';entry=entries[name]
        for candidate in (entry,artifact.get_entry(name)):
            require(getattr(candidate,'path',None)==name and getattr(candidate,'ref',None) is None
                    and getattr(candidate,'size',None)==item['bytes'],'packed_entry_invalid')
        bound=artifact.get_entry(name)
        require(getattr(bound,'path',None)==name and getattr(bound,'ref',None) is None
                and getattr(bound,'size',None)==item['bytes'],'packed_entry_invalid')
        fetch.assert_private(entity,env,deadline)
        result=Path(bound.download(root=str(root),skip_cache=True))
        require(result.absolute()==(root/name).absolute(),'packed_download_invalid')
        path=delta.checked_file(root,name,256*1024**2,item['sha256'],item['bytes'])
        with path.open('rb') as stream:
            require(sum(bool(line.strip()) for line in stream)==item['records'],'packed_count_mismatch')
        files[split]={'bytes':item['bytes'],'sha256':item['sha256']}
    require(set(p.name for p in root.iterdir())==set(entries),'packed_download_invalid')
    minimal={'private':True,'target_role':'solver','format':'text','files':files}
    pin=root/'manifest.json';pin.write_bytes(delta.canonical(minimal))
    fetch.assert_private(entity,env,deadline)
    return delta.sha_file(pin)


def download_tokenizer(root,*,get=None):
    root=Path(root);require(not root.exists(),'workspace_collision');root.mkdir()
    get=cloud.requests.get if get is None else get
    for name,(size,expected) in TOKENIZER_FILES.items():
        url='https://huggingface.co/Qwen/QwQ-32B/resolve/'+TOKENIZER_COMMIT+'/'+name
        for hop in range(4):
            parsed=urlsplit(url)
            require(parsed.scheme=='https' and parsed.hostname=='huggingface.co' and parsed.port in (None,443)
                    and not parsed.username and not parsed.password,'tokenizer_redirect_rejected')
            response=get(url,allow_redirects=False,stream=True,timeout=(10,30),
                headers={'Accept-Encoding':'identity','User-Agent':'HaslaPrivateNativePreparation/1.0'})
            try:
                if response.status_code in (301,302,303,307,308):
                    require(hop<3 and bool(response.headers.get('Location')),'tokenizer_redirect_rejected')
                    url=urljoin(url,response.headers['Location']);continue
                require(response.status_code==200,'tokenizer_transfer_failed')
                require(str(response.headers.get('Content-Encoding','identity')).lower() in ('','identity'),
                        'tokenizer_transfer_failed')
                received=0;digest=hashlib.sha256();target=root/name
                with target.open('xb') as stream:
                    for chunk in response.iter_content(chunk_size=65536):
                        if not chunk:continue
                        require(isinstance(chunk,bytes),'tokenizer_transfer_failed')
                        received+=len(chunk);require(received<=size,'tokenizer_transfer_failed')
                        digest.update(chunk);stream.write(chunk)
                require(received==size and digest.hexdigest()==expected,'tokenizer_hash_mismatch')
                break
            finally:response.close()
        else:raise PreparationError('tokenizer_redirect_rejected')
    return root


def stage_packed(manifest,packed,output,env,entity,sdk,run_id):
    files={}
    for split in ('train','validation'):
        item=packed['files'][split];path=Path(output)/(split+'.text.jsonl')
        require(type(item['records']) is int and item['records']>0,'empty_native_delta')
        delta.checked_file(output,path.name,256*1024**2,item['sha256'],item['bytes'])
        files[split]={'records':item['records'],'raw_bytes':item['bytes'],'raw_sha256':item['sha256']}
    name='hasla-private-stage-'+run_id+'-solver'
    metadata={'private':True,'role':'solver','format':'text','dataset_version':manifest['dataset_version'],
        'source_artifact':manifest['source_artifact'],'inventory_sha256':manifest['inventory_sha256'],
        'token_length_measured':True,'max_tokens_including_eos':1024,**files}
    deadline=time.monotonic()+600;fetch.assert_private(entity,env,deadline)
    settings=sdk.Settings(console='off',disable_code=True,save_code=False,disable_git=True,disable_job_creation=True,
        x_disable_meta=True,x_disable_stats=True,finish_timeout=30)
    run=sdk.init(entity=entity,project=fetch.PROJECT,id=name,name=name,resume='never',job_type='private-native-delta-staging',
        config={'role':'solver','private':True},settings=settings,dir=str(Path(output).parent))
    reference=None
    try:
        artifact=sdk.Artifact(name+'-data',type='dataset',metadata=metadata)
        for split in ('train','validation'):
            path=Path(output)/(split+'.text.jsonl');artifact.add_file(str(path),name=path.name,policy='immutable',skip_cache=True)
        fetch.assert_private(entity,env,deadline);run.log_artifact(artifact);artifact.wait(timeout=480)
        reference=artifact.qualified_name
        require(isinstance(reference,str) and re.fullmatch(re.escape(entity+'/'+fetch.PROJECT+'/'+name+'-data:')+r'v[0-9]+',reference)
                and artifact.state=='COMMITTED','staged_artifact_invalid')
        fetch.assert_private(entity,env,deadline)
    finally:
        # A committed data receipt survives unrelated finish telemetry failure.
        try:run.finish()
        except Exception:
            if reference is None:raise
    return {'event':'private_contest_delta_staged','status':'staged','private':True,'input_artifact':reference,
        'dataset_version':manifest['dataset_version'],'role':'solver','format':'text',**files,
        'token_length_measured':True,'max_tokens_including_eos':1024,'training_performed':False,
        'source_inventory_complete':packed.get('source_inventory_complete',False)}


def execute(env=None):
    env=os.environ if env is None else env
    fetch.credentials(env);require(not any(env.get(k) for k in delta.EXTRA_CREDENTIALS),'wandb_only_credentials_required')
    manifest,entity=load_manifest(env)
    run_id=env.get('GITHUB_RUN_ID','');require(re.fullmatch(r'[0-9]{1,32}',run_id),'run_id_invalid')
    parent=delta.private_path(env.get('WANDB_DIR',''));parent.mkdir(parents=True,exist_ok=True)
    cloud.E=env
    with privacy.quiet_output(),tempfile.TemporaryDirectory(prefix='native-delta-',dir=parent) as temporary:
        phase='private_project'
        try:
            base=Path(temporary);deadline=time.monotonic()+2400
            fetch.assert_private(entity,env,deadline)
            import wandb as sdk
            source=base/'source';source.mkdir()
            phase='source_native_download'
            delta.download_sources(manifest['source_artifact'],manifest['inventory_sha256'],env,source)
            phase='previous_packed_download'
            packed_pin=download_packed(manifest,env,entity,base/'previous',sdk)
            native=base/'native';phase='native_conversion'
            delta.convert_local(source,manifest['inventory_sha256'],base/'previous',packed_pin,native,
                manifest['dataset_version']+'-native',manifest['authorization_note'],artifact_reference=manifest['source_artifact'])
            phase='public_tokenizer_download';download_tokenizer(base/'tokenizer')
            import private_text_pack as packing
            output=base/'packed';phase='exact_token_packing'
            packed=packing.prepare(native,delta.sha_file(native/'manifest.json'),base/'tokenizer',
                TOKENIZER_FILES['tokenizer.json'][1],TOKENIZER_FILES['tokenizer_config.json'][1],output,manifest['dataset_version'])
            require(packed.get('training_ready') is True and packed.get('token_length_measured') is True,'token_gate_unverified')
            phase='private_dataset_staging'
            event=stage_packed(manifest,packed,output,env,entity,sdk,run_id)
        except Exception as error:
            raise PipelineFailure(phase,error) from None
    return event


def main():
    try:event=execute()
    except Exception as error:
        safe=str(error) if isinstance(error,(PreparationError,delta.DeltaError,fetch.FetchError)) else 'private_native_preparation_failed'
        event={'event':'private_contest_delta_failed','code':safe,'training_performed':False}
        if isinstance(error,PipelineFailure):event.update(phase=error.phase,error_class=error.error_class)
    print(json.dumps(event,ensure_ascii=True,separators=(',',':')),flush=True)
    return 0 if event.get('status')=='staged' else 1


if __name__=='__main__':raise SystemExit(main())

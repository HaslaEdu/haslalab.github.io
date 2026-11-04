"""Tiny synthetic offline PDFs only. No real sources, sockets, SDK or APIs."""
import base64
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import runpy
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

try:
    from nacl.secret import SecretBox
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / '.private-problem-bank-runtime/hasla-ai-corpus/secure-upload-runtime'))
    from nacl.secret import SecretBox

import private_stage_ocr_sources as stage

PRIVATE = b'SYNTHETIC_PRIVATE_OCR_BYTES_NO_REAL_DOCUMENT'


class TransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.control = runpy.run_path(str(Path(__file__).resolve().parents[3] / 'operations/hasla-ai-stage-ocr-control.py'), run_name='ocr_control_offline')

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='hasla-ocr-stage-unit-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.addCleanup(patch.stopall)
        # Only tiny fixture files are written on the low-space workstation.
        patch.object(stage,'DISK_HEADROOM',0).start()
        for name in ('get','post','put','delete','request'):
            patch.object(stage.core.requests,name,side_effect=AssertionError('network forbidden')).start()
        self.source = self.root / 'inventory-v1'; self.source.mkdir()
        self.payloads, sources = [], []
        for index in range(2):
            raw = b'%PDF-1.7\n' + PRIVATE + bytes([65+index]) * (80+index)
            path = self.source / ('private-original-' + str(index) + '.pdf'); path.write_bytes(raw)
            self.payloads.append(raw)
            sources.append({'source_id':'fixture:' + str(index), 'source_family':'textbook' if index == 0 else 'competition_document',
                'local_pdf_path':str(path), 'local_pdf_sha256':stage.digest(raw), 'source_page_count':3,
                'pending_page_ranges':[[1,2]], 'triage_page_ranges':{'image_present_ocr_candidate':[[1,1]],
                    'empty_native_requires_visual_triage':[[2,2]]}, 'drive_file_id':'synthetic-drive' if index == 0 else None})
        self.inventory = self.source / 'manifest.json'
        self.document = {'schema':'haslalab-pending-ocr-triage-v1','metadata_only':True,'pdfs_opened':0,
                         'sources':sources,'jobs':{'sha256':'b'*64}}
        self.inventory.write_text(json.dumps(self.document),encoding='utf-8')
        self.output = self.root / 'encrypted'

    def prepare(self):
        # Policy size is reduced only in this in-process synthetic fixture.
        patch.object(stage,'PART_BYTES',64).start()
        result = stage.prepare_bundle(self.inventory,self.output,allowed_roots=(self.root,),
            disk_usage=lambda _:SimpleNamespace(free=10**10))
        descriptor = stage.strict_json((self.output / 'transfer.private.json').read_bytes())
        return result, descriptor

    def getter(self, descriptor, replacements=None, observed=None):
        replacements = {} if replacements is None else replacements
        def get(url,**options):
            self.assertEqual(options['headers'],{'Authorization':'Bearer '+descriptor['bearer']})
            self.assertFalse(options['allow_redirects'])
            self.assertTrue(options['stream'])
            self.assertTrue(url.startswith(descriptor['url']+'/part_'))
            name = url.rsplit('/',1)[-1]
            raw = replacements.get(name,(self.output/name).read_bytes())
            response = SimpleNamespace(status_code=200,headers={'Content-Length':str(len(raw))},closed=False)
            response.iter_content=lambda chunk_size:(raw[i:i+17] for i in range(0,len(raw),17))
            response.close=lambda:setattr(response,'closed',True)
            if observed is not None:observed.append(response)
            return response
        return get

    def open_manifest(self, descriptor):
        box = SecretBox(base64.b64decode(descriptor['key_b64']))
        return stage.strict_json(box.decrypt((self.output/'part_000000.bin').read_bytes()))

    def test_streamed_roundtrip_fixed_aliases_and_nonce_uniqueness(self):
        event,descriptor=self.prepare()
        self.assertEqual(event['originals_modified'],0)
        nonces=set()
        for part in self.output.glob('part_*.bin'):
            raw=part.read_bytes();self.assertNotIn(PRIVATE,raw);nonces.add(raw[:24])
        self.assertEqual(len(nonces),descriptor['part_count'])
        self.assertLess(len(json.dumps(descriptor).encode()),stage.DESCRIPTOR_LIMIT)
        manifest=self.open_manifest(descriptor)
        encoded=json.dumps(manifest)
        self.assertNotIn(str(self.source),encoded)
        self.assertNotIn('private-original',encoded)
        target=self.root/'received';target.mkdir()
        got,totals=stage.reconstruct_sources(descriptor,target,get=self.getter(descriptor))
        self.assertEqual(got,manifest)
        self.assertEqual(totals['source_count'],2)
        self.assertEqual(totals['pending_pages'],4)
        self.assertEqual({p.name for p in target.iterdir()},{'source_0000.pdf','source_0001.pdf','manifest.json'})
        for index,raw in enumerate(self.payloads):self.assertEqual((target/stage.alias(index)).read_bytes(),raw)

    def test_insufficient_disk_and_invalid_sources_do_not_create_bundle(self):
        with self.assertRaisesRegex(stage.StageError,'free_disk'):
            stage.prepare_bundle(self.inventory,self.output,allowed_roots=(self.root,),disk_usage=lambda _:SimpleNamespace(free=1))
        self.assertFalse(self.output.exists())
        for changes in [{'local_pdf_sha256':'0'*64},{'pending_page_ranges':[[0,1]]},{'source_page_count':True},
                        {'source_id':'../escape'},{'triage_page_ranges':{'unknown':[[1,2]]}}]:
            document=copy.deepcopy(self.document);document['sources'][0].update(changes)
            self.inventory.write_text(json.dumps(document),encoding='utf-8')
            with self.subTest(keys=list(changes)),self.assertRaises(stage.StageError):
                stage.prepare_bundle(self.inventory,self.output,allowed_roots=(self.root,),disk_usage=lambda _:SimpleNamespace(free=10**10))
            self.assertFalse(self.output.exists())

    def test_source_scope_symlinks_duplicate_hashes_and_pdf_magic_rejected(self):
        with self.assertRaisesRegex(stage.StageError,'outside_private_roots'):
            stage.prepare_bundle(self.inventory,self.output,allowed_roots=(self.root/'elsewhere',),disk_usage=lambda _:SimpleNamespace(free=10**10))
        document=copy.deepcopy(self.document);document['sources'][1]['local_pdf_path']=document['sources'][0]['local_pdf_path']
        document['sources'][1]['local_pdf_sha256']=document['sources'][0]['local_pdf_sha256']
        self.inventory.write_text(json.dumps(document),encoding='utf-8')
        with self.assertRaisesRegex(stage.StageError,'duplicate_source'):
            stage.prepare_bundle(self.inventory,self.output,allowed_roots=(self.root,),disk_usage=lambda _:SimpleNamespace(free=10**10))
        document=copy.deepcopy(self.document);path=Path(document['sources'][0]['local_pdf_path']);raw=b'NO PDF'+PRIVATE
        path.write_bytes(raw);document['sources'][0]['local_pdf_sha256']=stage.digest(raw)
        self.inventory.write_text(json.dumps(document),encoding='utf-8')
        with self.assertRaisesRegex(stage.StageError,'pdf_magic'):
            stage.prepare_bundle(self.inventory,self.output,allowed_roots=(self.root,),disk_usage=lambda _:SimpleNamespace(free=10**10))
        self.assertFalse(self.output.exists());self.assertEqual(path.read_bytes(),raw)

    def test_reparse_source_is_rejected_before_opening_content(self):
        source_path=Path(self.document['sources'][0]['local_pdf_path'])
        actual=Path.lstat
        def lstat(path,*args,**kwargs):
            info=actual(path,*args,**kwargs)
            if path==source_path:
                return SimpleNamespace(st_mode=info.st_mode,st_file_attributes=0x400)
            return info
        with patch.object(Path,'lstat',lstat),self.assertRaisesRegex(stage.StageError,'regular_file'):
            stage.preparation_plan(self.inventory,self.output,allowed_roots=(self.root,))
        self.assertFalse(self.output.exists())

    def test_no_overwrite_and_repository_output_rejected(self):
        self.output.mkdir();(self.output/'keep').write_bytes(PRIVATE)
        with self.assertRaisesRegex(stage.StageError,'overwrite'):
            stage.prepare_bundle(self.inventory,self.output,allowed_roots=(self.root,),disk_usage=lambda _:SimpleNamespace(free=10**10))
        self.assertEqual((self.output/'keep').read_bytes(),PRIVATE)
        git=self.root/'repo';git.mkdir();(git/'.git').mkdir()
        with self.assertRaisesRegex(stage.StageError,'private_directory'):
            stage.preparation_plan(self.inventory,git/'output',allowed_roots=(self.root,))

    def test_per_file_and_total_limits_without_large_allocations(self):
        with patch.object(stage,'FILE_LIMIT',10),self.assertRaisesRegex(stage.StageError,'source_size_limit'):
            stage.preparation_plan(self.inventory,self.output,allowed_roots=(self.root,))
        with patch.object(stage,'TOTAL_LIMIT',200),self.assertRaisesRegex(stage.StageError,'total_size_limit'):
            stage.preparation_plan(self.inventory,self.output,allowed_roots=(self.root,))

    def test_manifest_rejects_paths_order_offsets_missing_parts_and_page_overlap(self):
        _,descriptor=self.prepare();manifest=self.open_manifest(descriptor)
        mutations=[]
        for field,value in [('alias','../source.pdf'),('index',True),('pdf_bytes',stage.FILE_LIMIT+1),
                            ('pending_page_ranges',[[1,2],[2,3]])]:
            changed=copy.deepcopy(manifest);changed['sources'][0][field]=value;mutations.append(changed)
        for field,value in [('offset',1),('index',2),('source_index',1),('plain_bytes',65),('cipher_bytes',1)]:
            changed=copy.deepcopy(manifest);changed['parts'][0][field]=value;mutations.append(changed)
        changed=copy.deepcopy(manifest);changed['parts'].pop();mutations.append(changed)
        changed=copy.deepcopy(manifest);changed['sources'][0]['local_pdf_path']=str(self.source);mutations.append(changed)
        for changed in mutations:
            with self.subTest(fields=set(changed)),self.assertRaises(stage.StageError):stage.manifest_check(changed,descriptor)

    def test_descriptor_target_key_size_and_bundle_validation(self):
        _,descriptor=self.prepare()
        for changes in [{'url':'https://evil.invalid/ocr/'+descriptor['bundle_id']},
                {'url':descriptor['url']+'?secret=x'},{'url':descriptor['url'].replace('https://','http://')},
                {'key_b64':'invalid'},{'version':True},{'part_count':True},{'total_pdf_bytes':stage.TOTAL_LIMIT+1},
                {'source_count':0},{'part0_cipher_bytes':stage.MANIFEST_LIMIT+41},{'extra':'private'}]:
            with self.subTest(fields=list(changes)),self.assertRaises(stage.StageError):stage.descriptor_check({**descriptor,**changes})

    def test_swapped_cipher_bad_key_and_nonce_reuse_fail_authentication(self):
        _,descriptor=self.prepare()
        first=(self.output/'part_000001.bin').read_bytes()
        target=self.root/'received';target.mkdir()
        with self.assertRaises(stage.StageError):
            stage.reconstruct_sources(descriptor,target,get=self.getter(descriptor,{'part_000002.bin':first}))
        other=self.root/'wrong-key';other.mkdir()
        bad={**descriptor,'key_b64':base64.b64encode(b'x'*32).decode()}
        with self.assertRaisesRegex(stage.StageError,'decryption'):
            stage.reconstruct_sources(bad,other,get=self.getter(bad))
        # A manifest-valid ciphertext with a reused nonce is still forbidden.
        manifest=self.open_manifest(descriptor);box=SecretBox(base64.b64decode(descriptor['key_b64']))
        original=(self.output/'part_000001.bin').read_bytes();plain=box.decrypt(original)
        part0nonce=(self.output/'part_000000.bin').read_bytes()[:24]
        reused=bytes(box.encrypt(plain,part0nonce));manifest['parts'][0]['cipher_sha256']=stage.digest(reused)
        raw=json.dumps(manifest,separators=(',',':')).encode();part0=bytes(box.encrypt(raw,part0nonce))
        bad={**descriptor,'part0_cipher_bytes':len(part0),'part0_cipher_sha256':stage.digest(part0)}
        third=self.root/'nonce-reuse';third.mkdir()
        with self.assertRaisesRegex(stage.StageError,'nonce_reuse'):
            stage.reconstruct_sources(bad,third,get=self.getter(bad,{'part_000000.bin':part0,'part_000001.bin':reused}))

    def test_full_pdf_hash_mismatch_even_when_authenticated_parts_match(self):
        _,descriptor=self.prepare();manifest=self.open_manifest(descriptor)
        manifest['sources'][0]['pdf_sha256']='0'*64
        box=SecretBox(base64.b64decode(descriptor['key_b64']));cipher=bytes(box.encrypt(json.dumps(manifest).encode()))
        changed={**descriptor,'part0_cipher_bytes':len(cipher),'part0_cipher_sha256':stage.digest(cipher)}
        target=self.root/'received';target.mkdir()
        with self.assertRaisesRegex(stage.StageError,'pdf_hash'):
            stage.reconstruct_sources(changed,target,get=self.getter(changed,{'part_000000.bin':cipher}))

    def test_fetch_redirect_length_overflow_encoding_and_deadline_fail_closed(self):
        _,descriptor=self.prepare();part=self.open_manifest(descriptor)['parts'][0]
        for status,headers,payload in [(302,{'Content-Length':'104'},b''),
                (200,{'Content-Length':'999'},b''),(200,{'Content-Length':'104','Content-Encoding':'gzip'},b''),
                (200,{'Content-Length':'104'},b'x'*105)]:
            response=SimpleNamespace(status_code=status,headers=headers,closed=False)
            response.iter_content=lambda chunk_size:[payload]
            response.close=lambda:setattr(response,'closed',True)
            with self.subTest(status=status,headers=headers),self.assertRaises(stage.StageError):
                stage.fetch_part(descriptor,1,part['cipher_bytes'],part['cipher_sha256'],get=lambda *_,**__:response)
            self.assertTrue(response.closed)
        ticks=iter([0,601])
        with self.assertRaisesRegex(stage.StageError,'deadline'):
            stage.fetch_part(descriptor,1,part['cipher_bytes'],part['cipher_sha256'],get=self.getter(descriptor),clock=lambda:next(ticks,601))

    def sdk(self):
        observed=SimpleNamespace(files=[],uploaded=False,finished=False,initialized=False)
        class Artifact:
            def __init__(self,name,type,metadata):
                assert type=='ocr-source';self.qualified_name='fixture/'+stage.PROJECT+'/'+name+':v0'
            def add_file(self,path,name):observed.files.append((name,Path(path).read_bytes()))
            def wait(self,timeout):pass
        class Run:
            def log_artifact(self,artifact):observed.uploaded=True
            def finish(self):observed.finished=True
        def init(**kwargs):
            observed.initialized=True;print('SYNTHETIC_SDK_SECRET');return Run()
        return SimpleNamespace(Settings=lambda **_:None,Artifact=Artifact,init=init),observed

    def query(self,document,variables=None):
        self.assertNotIn('mutation',document.lower())
        return {'viewer':{'entity':'fixture'}} if variables is None else {'project':{'name':stage.PROJECT,'access':'PRIVATE'}}

    def test_private_gate_and_all_pdfs_verified_before_artifact_or_run(self):
        _,descriptor=self.prepare();sdk,observed=self.sdk()
        env={'WANDB_API_KEY':'SYNTHETIC_KEY','GITHUB_RUN_ID':'123','HASLA_OCR_STAGE_INPUT':json.dumps(descriptor),
             'HASLA_OCR_STAGE_BUNDLE_ID':descriptor['bundle_id']}
        output=io.StringIO()
        with contextlib.redirect_stdout(output):event=stage.stage(env,query=self.query,get=self.getter(descriptor),sdk=sdk)
        self.assertEqual(output.getvalue(),'');self.assertTrue(observed.uploaded and observed.finished)
        self.assertEqual([name for name,_ in observed.files],['source_0000.pdf','source_0001.pdf','manifest.json'])
        for secret in ('SYNTHETIC_KEY','SYNTHETIC_SDK_SECRET',descriptor['url'],descriptor['bearer'],descriptor['key_b64'],str(self.source)):
            self.assertNotIn(secret,json.dumps(event))
        sdk,observed=self.sdk()
        def public(document,variables=None):
            return {'viewer':{'entity':'fixture'}} if variables is None else {'project':{'name':stage.PROJECT,'access':'PUBLIC'}}
        with self.assertRaisesRegex(stage.StageError,'private_project'):
            stage.stage(env,query=public,get=lambda *_,**__:self.fail('fetch before privacy check'),sdk=sdk)
        self.assertFalse(observed.initialized or observed.uploaded)
        with self.assertRaises(stage.StageError):
            stage.stage(env,query=self.query,get=self.getter(descriptor,{'part_000002.bin':b'corrupt'}),sdk=sdk)
        self.assertFalse(observed.initialized or observed.uploaded)

    def test_model_credentials_and_main_exception_never_publish_raw_errors(self):
        for name in ('HF_TOKEN','RUNPOD_API_KEY','OPENAI_API_KEY'):
            with self.assertRaisesRegex(stage.StageError,'unexpected_model'):
                stage.stage({name:'secret'})
        output=io.StringIO()
        with patch.object(stage,'stage',side_effect=RuntimeError(str(self.source))),contextlib.redirect_stdout(output):
            self.assertEqual(stage.main(),1)
        self.assertNotIn(str(self.source),output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['code'],'private_ocr_staging_failed')
        output=io.StringIO()
        with patch.object(stage,'stage',side_effect=stage.StageError('synthetic_secret')),contextlib.redirect_stdout(output):
            stage.main()
        self.assertNotIn('synthetic_secret',output.getvalue())

    def test_missing_or_wrong_expected_bundle_prevents_all_network(self):
        _,descriptor=self.prepare()
        for expected in ('','0'*32):
            env={'WANDB_API_KEY':'synthetic','GITHUB_RUN_ID':'123','HASLA_OCR_STAGE_INPUT':json.dumps(descriptor),
                 'HASLA_OCR_STAGE_BUNDLE_ID':expected}
            with self.assertRaisesRegex(stage.StageError,'expected_bundle'):
                stage.stage(env,query=lambda *_,**__:self.fail('network before bundle check'))

    def test_partial_write_cleanup_removes_only_own_new_files(self):
        actual_open=Path.open
        for failure_name in ('part_000001.bin','transfer.private.json'):
            def failing_open(path,mode='r',*args,**kwargs):
                handle=actual_open(path,mode,*args,**kwargs)
                if path.parent==self.output and path.name==failure_name and mode in ('xb','x'):
                    class Writer:
                        def __enter__(self):return self
                        def __exit__(self,*_):handle.close()
                        def write(self,value):
                            handle.write(value[:3]);raise OSError('synthetic_secret')
                    return Writer()
                return handle
            with self.subTest(filename=failure_name),patch.object(Path,'open',failing_open),self.assertRaises(OSError):
                stage.prepare_bundle(self.inventory,self.output,allowed_roots=(self.root,),disk_usage=lambda _:SimpleNamespace(free=10**10))
            self.assertFalse(self.output.exists())
            self.assertEqual(Path(self.document['sources'][0]['local_pdf_path']).read_bytes(),self.payloads[0])

    def test_competing_metadata_file_is_not_deleted_by_failed_prepare(self):
        actual=stage.write_private
        def competing(path,value,**options):
            if Path(path).name=='transfer.private.json':
                Path(path).write_bytes(PRIVATE)
            return actual(path,value,**options)
        with patch.object(stage,'write_private',competing),self.assertRaises(FileExistsError):
            stage.prepare_bundle(self.inventory,self.output,allowed_roots=(self.root,),disk_usage=lambda _:SimpleNamespace(free=10**10))
        self.assertEqual((self.output/'transfer.private.json').read_bytes(),PRIVATE)
        self.assertEqual({path.name for path in self.output.iterdir()},{'transfer.private.json'})

    def test_privacy_change_before_upload_finishes_run_and_cleans_plaintext(self):
        _,descriptor=self.prepare();sdk,observed=self.sdk();private_calls=[];directories=[]
        def query(document,variables=None):
            if variables is None:return {'viewer':{'entity':'fixture'}}
            private_calls.append(True)
            return {'project':{'name':stage.PROJECT,'access':'PUBLIC' if len(private_calls)==4 else 'PRIVATE'}}
        original=stage.reconstruct_sources
        def reconstruct(descriptor,directory,**options):
            directories.append(Path(directory));return original(descriptor,directory,**options)
        env={'WANDB_API_KEY':'synthetic','GITHUB_RUN_ID':'123','HASLA_OCR_STAGE_INPUT':json.dumps(descriptor),
             'HASLA_OCR_STAGE_BUNDLE_ID':descriptor['bundle_id']}
        with patch.object(stage,'reconstruct_sources',reconstruct),self.assertRaisesRegex(stage.StageError,'private_project'):
            stage.stage(env,query=query,get=self.getter(descriptor),sdk=sdk)
        self.assertTrue(observed.initialized and observed.finished)
        self.assertFalse(observed.uploaded)
        self.assertTrue(directories and all(not path.exists() for path in directories))

    def test_cipher_handler_serves_only_indexed_encrypted_parts(self):
        _,descriptor=self.prepare();directory,descriptor,index=self.control['load_bundle'](self.output)
        Handler=self.control['handler_for'](directory,descriptor,index)
        handler=Handler.__new__(Handler);handler.connection=SimpleNamespace(settimeout=lambda _:None)
        handler.path=descriptor['url'].split('.com',1)[1]+'/part_000000.bin'
        handler.headers={'Authorization':'Bearer '+descriptor['bearer']}
        handler.wfile=io.BytesIO();statuses=[]
        handler.send_response=lambda code:statuses.append(code)
        handler.send_header=lambda *args:None;handler.end_headers=lambda:None
        handler.send_error=lambda code:statuses.append(code)
        handler.do_GET()
        self.assertEqual(statuses,[200]);self.assertEqual(handler.wfile.getvalue(),(self.output/'part_000000.bin').read_bytes())
        for route,extra in [('/transfer.private.json',{}),(handler.path,{'Range':'bytes=0-1'}),
                            ('/ocr/'+descriptor['bundle_id']+'/source_0000.pdf',{})]:
            handler.path=route;handler.headers={'Authorization':'Bearer '+descriptor['bearer'],**extra};handler.wfile=io.BytesIO()
            handler.do_GET();self.assertEqual(statuses[-1],404);self.assertEqual(handler.wfile.getvalue(),b'')

    def test_exact_auth_routes_never_serve_plaintext_or_other_bundles(self):
        _,descriptor=self.prepare();authorize=self.control['authorized_part']
        prefix='/ocr/'+descriptor['bundle_id']
        self.assertEqual(authorize(prefix+'/part_000000.bin','Bearer '+descriptor['bearer'],descriptor),0)
        for path,auth in [(prefix+'/../transfer.private.json','Bearer '+descriptor['bearer']),
                (prefix+'/part_000000.bin?x=1','Bearer '+descriptor['bearer']),
                ('/ocr/'+'0'*32+'/part_000000.bin','Bearer '+descriptor['bearer']),
                (prefix+'/part_999999.bin','Bearer '+descriptor['bearer']),
                (prefix+'/part_000000.bin','wrong'),(prefix+'/part_000000.bin','한글')]:
            self.assertIsNone(authorize(path,auth,descriptor))

    def test_ocr_rotation_allows_other_gpu_runs_but_blocks_exact_consumer(self):
        def api(method,path,body=None):
            if '/jobs?' in path:return {'jobs':[{'name':'private-dual-pilot','status':'in_progress'}]}
            return {'workflow_runs':[{'id':1,'display_title':'gpu=true ocr-stage=false'}]}
        self.control['no_active_ocr_consumer'](api)
        def active(method,path,body=None):
            if '/jobs?' in path:return {'jobs':[{'name':'stage-ocr-sources','status':'in_progress'}]}
            return {'workflow_runs':[{'id':2,'display_title':'ocr-stage=true'}]}
        with self.assertRaisesRegex(stage.StageError,'consumer_active'):self.control['no_active_ocr_consumer'](active)

    def test_publish_only_one_sealed_secret_and_dispatch_fixed_cpu_flags(self):
        _,descriptor=self.prepare();self.control['load_bundle'](self.output)
        (self.output/'ready.json').write_text(json.dumps({'ready':True,'expires_at':10**12}))
        from nacl.public import PrivateKey,SealedBox
        key=PrivateKey.generate();calls=[]
        def api(method,path,body=None):
            calls.append((method,path,body))
            if '/runs?' in path:return {'workflow_runs':[]}
            if path.endswith('/public-key'):return {'key':base64.b64encode(bytes(key.public_key)).decode(),'key_id':'fixture'}
            if method=='PUT':
                self.assertEqual(path,'/actions/secrets/HASLA_OCR_STAGE_INPUT')
                self.assertEqual(json.loads(SealedBox(key).decrypt(base64.b64decode(body['encrypted_value']))),descriptor)
        lock=self.root/'lock'
        event=self.control['publish'](self.output,api=api,lock_path=lock)
        self.assertEqual(event['secret_count'],1)
        event=self.control['dispatch'](self.output,api=api,lock_path=lock)
        self.assertFalse(event['gpu_creation_enabled'])
        body=[body for method,path,body in calls if method=='POST'][0]
        self.assertEqual(body['inputs']['ocr_stage_only'],'true')
        self.assertEqual(body['inputs']['preflight_only'],'true')
        self.assertEqual(body['inputs']['stage_only'],'false')
        self.assertEqual(body['inputs']['ocr_stage_bundle_id'],descriptor['bundle_id'])
        with self.assertRaisesRegex(stage.StageError,'ocr_dispatch_pending'):self.control['dispatch'](self.output,api=api,lock_path=lock)
        self.assertFalse(lock.exists())
        # Pending intent blocks rotation even before Actions lists the run.
        with self.assertRaisesRegex(stage.StageError,'ocr_dispatch_pending'):
            self.control['publish'](self.output,api=api,lock_path=lock)
        registry=self.control['read_registry'](lock)
        self.assertEqual(registry['state'],'dispatch_pending')

    def test_completion_ack_requires_finished_ocr_job_and_current_dispatch(self):
        _,descriptor=self.prepare();lock=self.root/'lock'
        import time
        from datetime import datetime,timezone
        epoch=time.time()
        registry={'state':'dispatch_pending','bundle_id':descriptor['bundle_id'],
                  'descriptor_sha256':self.control['descriptor_sha'](descriptor),'dispatch_epoch':epoch}
        self.control['write_registry'](lock,registry)
        def api(method,path,body=None):
            if '/jobs?' in path:return {'jobs':[{'name':'stage-ocr-sources','status':'completed','conclusion':'success'}]}
            return {'status':'completed','head_branch':self.control['BRANCH'],
                    'display_title':'ocr-stage=true, bundle='+descriptor['bundle_id'],
                    'created_at':datetime.fromtimestamp(epoch+1,timezone.utc).isoformat()}
        event=self.control['acknowledge'](self.output,987,api=api,lock_path=lock)
        self.assertTrue(event['secret_rotation_unblocked'])
        self.assertEqual(self.control['read_registry'](lock)['state'],'acknowledged')
        self.control['write_registry'](lock,registry)
        def active(method,path,body=None):
            if '/jobs?' in path:return {'jobs':[{'name':'stage-ocr-sources','status':'in_progress'}]}
            return api(method,path,body)
        with self.assertRaisesRegex(stage.StageError,'completion_unverified'):
            self.control['acknowledge'](self.output,987,api=active,lock_path=lock)

    def test_failed_secret_put_keeps_rotation_intent_and_prevents_dispatch(self):
        _,descriptor=self.prepare();lock=self.root/'lock'
        (self.output/'ready.json').write_text(json.dumps({'ready':True,'expires_at':10**12}))
        from nacl.public import PrivateKey
        key=PrivateKey.generate()
        def api(method,path,body=None):
            if '/runs?' in path:return {'workflow_runs':[]}
            if path.endswith('/public-key'):return {'key':base64.b64encode(bytes(key.public_key)).decode(),'key_id':'fixture'}
            if method=='PUT':raise RuntimeError('synthetic ambiguous network failure')
            self.fail('unexpected dispatch')
        with self.assertRaises(RuntimeError):self.control['publish'](self.output,api=api,lock_path=lock)
        self.assertEqual(self.control['read_registry'](lock)['state'],'rotation_pending')
        (self.output/'published.json').write_text('{}')
        with self.assertRaisesRegex(stage.StageError,'ocr_dispatch_pending'):
            self.control['dispatch'](self.output,api=api,lock_path=lock)


if __name__=='__main__':
    unittest.main()

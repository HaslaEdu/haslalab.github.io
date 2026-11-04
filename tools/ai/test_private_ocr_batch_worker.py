"""Small offline fixtures; no real PDFs, renders, model dependencies or APIs."""
import contextlib
import hashlib
import gzip
import io
import json
from pathlib import Path
import tempfile
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import private_ocr_batch_worker as batch

PRIVATE='SYNTHETIC_PRIVATE_OCR_TEXT no real source'
REFERENCE='fixture/'+batch.PROJECT+'/fixture-sources:v0'


def fixture():
    sources=[];parts=[];payloads={}
    for index in range(2):
        pdf=b'%PDF-1.7\nSYNTHETIC '+bytes([65+index])*40
        digest=hashlib.sha256(pdf).hexdigest();name=batch.alias(index);payloads[name]=pdf
        sources.append({'index':index,'alias':name,'source_id':'fixture:'+str(index),'source_family':'textbook' if not index else 'competition_document',
                        'pdf_bytes':len(pdf),'pdf_sha256':digest,'page_count':3,'pending_page_ranges':[[1,2]],
                        'triage_page_ranges':{'image_present_ocr_candidate':[[1,1]],'encoding_recovery_ocr_candidate':[[2,2]]},'drive_file_id':None})
        parts.append({'index':index+1,'source_index':index,'offset':0,'plain_bytes':len(pdf),'plain_sha256':digest,
                      'cipher_bytes':len(pdf)+40,'cipher_sha256':'c'*64})
    manifest={'version':1,'kind':'ocr-source','bundle_id':'b'*32,'dataset_version':'fixture-v1','part_plain_bytes':16*1024**2,
              'total_pdf_bytes':sum(len(value) for value in payloads.values()),'source_inventory_sha256':'a'*64,'page_jobs_sha256':'d'*64,
              'sources':sources,'parts':parts}
    raw=batch.canonical(manifest);payloads['manifest.json']=raw
    return manifest,payloads


class InputTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        patch.object(batch,'EXPECTED_SOURCES',2).start();patch.object(batch,'EXPECTED_PENDING',4).start()
        # Fixtures write only KB, so logical headroom tests do not depend on
        # concurrent unrelated workspace activity on the low-space C: drive.
        patch.object(batch.shutil,'disk_usage',return_value=SimpleNamespace(free=10**10)).start()
        patch.object(batch.urllib.request,'urlopen',side_effect=AssertionError('network forbidden')).start()
        temporary=tempfile.TemporaryDirectory(prefix='hasla-batch-unit-');self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
        self.manifest,self.payloads=fixture();self.downloads=[];self.privacy_checks=[]
        self.env={'WANDB_API_KEY':'SYNTHETIC_KEY','WANDB_ENTITY':'fixture','WANDB_PROJECT':batch.PROJECT,'HASLA_OCR_SOURCE_ARTIFACT':REFERENCE}
        self.entries={name:SimpleNamespace(path=name,size=len(raw),ref=None) for name,raw in self.payloads.items()}
        test=self
        class Artifact:
            qualified_name=REFERENCE;type=batch.SOURCE_TYPE;state='COMMITTED'
            metadata={'private':True,'kind':'ocr-source','source_count':2,'pending_pages':4,'total_pdf_bytes':test.manifest['total_pdf_bytes']}
            manifest=SimpleNamespace(entries=test.entries)
            def get_entry(self,name):
                def download(root,skip_cache):
                    test.assertTrue(skip_cache)
                    test.downloads.append(name);path=Path(root)/name;path.write_bytes(test.payloads[name]);return str(path)
                return SimpleNamespace(path=name,size=len(test.payloads[name]),ref=None,download=download)
        self.artifact=Artifact()
        self.sdk=SimpleNamespace(Api=lambda **_:SimpleNamespace(artifact=lambda *_,**__:self.artifact))

    def privacy(self,env,entity):
        self.assertEqual(entity,'fixture');self.privacy_checks.append(True)

    def directory(self,name='input'):
        path=self.root/name;path.mkdir();return path

    def test_inspect_downloads_only_manifest_and_imports_no_model_or_renderer(self):
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            event=batch.inspect_source(self.env,sdk=self.sdk,privacy=self.privacy)
        self.assertEqual(output.getvalue(),'');self.assertEqual(self.downloads,['manifest.json'])
        self.assertEqual(event['manifest_sha256'],hashlib.sha256(self.payloads['manifest.json']).hexdigest())
        self.assertEqual(event['source_count'],2);self.assertEqual(event['pending_pages'],4);self.assertEqual(event['pdfs_downloaded'],0)
        self.assertFalse(event['gpu_initialized']);self.assertGreaterEqual(len(self.privacy_checks),2)
        for secret in ('SYNTHETIC_KEY',REFERENCE,PRIVATE,'fixture:0'):
            self.assertNotIn(secret,json.dumps(event))

    def test_nonprivate_or_wrong_artifact_identity_blocks_manifest_download(self):
        for changes in ({'state':'PENDING'},{'qualified_name':REFERENCE.replace(':v0',':latest')},{'type':'dataset'},
                        {'metadata':{**self.artifact.metadata,'private':False}}):
            original={key:getattr(self.artifact,key) for key in changes}
            for key,value in changes.items():setattr(self.artifact,key,value)
            with self.subTest(fields=list(changes)),self.assertRaises(batch.BatchError):
                batch.open_source(REFERENCE,self.env,self.directory(str(len(self.downloads))+str(list(changes))),sdk=self.sdk,privacy=self.privacy)
            self.assertEqual(self.downloads,[])
            for key,value in original.items():setattr(self.artifact,key,value)

    def test_linked_source_artifact_is_rejected_before_any_manifest_download(self):
        self.artifact.is_link=True
        with self.assertRaisesRegex(batch.BatchError,'artifact_invalid'):
            batch.open_source(REFERENCE,self.env,self.directory(),sdk=self.sdk,privacy=self.privacy)
        self.assertEqual(self.downloads,[])

    def test_entry_path_must_equal_fixed_alias_before_sdk_download(self):
        self.entries['source_0000.pdf'].path='../foreign.pdf'
        with self.assertRaisesRegex(batch.BatchError,'inventory_invalid'):
            batch.open_source(REFERENCE,self.env,self.directory(),sdk=self.sdk,privacy=self.privacy)
        self.assertEqual(self.downloads,[])

    def test_external_refs_and_extra_artifact_paths_are_rejected_before_download(self):
        self.entries['source_0000.pdf'].ref='https://invalid.example/private'
        with self.assertRaises(batch.BatchError):batch.open_source(REFERENCE,self.env,self.directory(),sdk=self.sdk,privacy=self.privacy)
        self.entries['source_0000.pdf'].ref=None;self.entries['../secret']=SimpleNamespace(size=1,ref=None)
        with self.assertRaises(batch.BatchError):batch.open_source(REFERENCE,self.env,self.directory('other'),sdk=self.sdk,privacy=self.privacy)
        self.assertEqual(self.downloads,[])

    def test_expected_manifest_sha_and_source_page_ranges_fail_closed(self):
        with self.assertRaisesRegex(batch.BatchError,'manifest_hash'):
            batch.open_source(REFERENCE,self.env,self.directory(),expected_hash='0'*64,sdk=self.sdk,privacy=self.privacy)
        manifest=json.loads(json.dumps(self.manifest));manifest['sources'][0]['pending_page_ranges']=[[0,2]]
        with self.assertRaises(batch.BatchError):batch.validate_manifest(manifest)
        manifest=json.loads(json.dumps(self.manifest));manifest['sources'][0]['alias']='../private.pdf'
        with self.assertRaises(batch.BatchError):batch.validate_manifest(manifest)

    def test_immutable_reference_and_credential_scope_required(self):
        for reference in (REFERENCE.replace(':v0',':latest'),'https://invalid.example/input','other/public/data:v0'):
            with self.assertRaises(batch.BatchError):batch.artifact_entity(reference)
        for field in ('HF_TOKEN','HF_API_KEY','HUGGINGFACE_HUB_TOKEN','HUGGINGFACEHUB_API_TOKEN',
                      'RUNPOD_API_KEY','RUNPOD_API_TOKEN','OPENAI_API_KEY'):
            with self.assertRaises(batch.BatchError):batch.credentials({**self.env,field:'secret'},'fixture')

    def job(self,keys=None):
        return {'version':1,'mode':'calibration','source_artifact':REFERENCE,'source_manifest_sha256':hashlib.sha256(self.payloads['manifest.json']).hexdigest(),
                'expected_source_count':2,'expected_pending_pages':4,'page_keys':keys or [{'source_index':0,'page_number':1},{'source_index':1,'page_number':1}],
                'runtime_seconds':240,'per_page_seconds':20,'checkpoint_pages':2,'bulk_authorized':False,'calibration_checkpoint':None}

    def reply(self,text=PRIVATE):
        return {'status':'machine_ocr_extracted','text':text,'blocks':[{'reading_order_index':0,'label':'text','text':text,'bbox_pixels':[0,0,10,20]}],
                'render':{'dpi':300,'colorspace':'RGB','alpha':False,'annotations':True,'format':'PNG','width':10,'height':20,
                          'pymupdf_version':batch.RENDER_VERSION,'png_sha256':'f'*64},'seconds':1}

    def test_job_requires_explicit_pending_allowlist_and_bulk_calibration_proof(self):
        batch.validate_job(self.job())
        for changes in ({'page_keys':[{'source_index':0,'page_number':1}]*2},{'bulk_authorized':True},
                        {'runtime_seconds':1801},{'checkpoint_pages':26},{'mode':'bulk'}):
            with self.subTest(keys=list(changes)),self.assertRaises(batch.BatchError):batch.validate_job({**self.job(),**changes})
        job=self.job([{'source_index':0,'page_number':3}]);engine=SimpleNamespace(close=lambda:None)
        with self.assertRaisesRegex(batch.BatchError,'page_not_pending'):
            batch.process_pages(job,self.manifest,batch.validate_manifest(self.manifest),engine,lambda _:None,lambda *_:None,999)

    def test_metadata_only_calibration_proposal_is_unique_and_pending(self):
        keys=batch.choose_calibration_pages(self.manifest,4)
        self.assertEqual(len(keys),4);self.assertEqual(len({(k['source_index'],k['page_number']) for k in keys}),4)
        self.assertTrue(all((k['source_index'],k['page_number']) in batch.validate_manifest(self.manifest) for k in keys))

    def test_machine_ocr_record_preserves_text_and_rejects_training_ground_truth_labels(self):
        text='V ≠ v; x² ≠ x2. 한글 $E=mc^2$.'
        record=batch.page_record(self.job(),self.manifest,{'source_index':0,'page_number':1},self.reply(text))
        self.assertEqual(record['text'],text);meta=record['metadata']
        self.assertEqual(meta['haslalab_provenance']['extraction'],'machine_ocr')
        self.assertFalse(meta['training_eligible'] or meta['human_reviewed'] or meta['scientifically_verified'])
        self.assertTrue(meta['text_is_model_output_not_ground_truth'])
        self.assertNotIn('messages',record)

    def test_structured_blocks_preserve_pipeline_reading_order_and_formula(self):
        page={'model_settings':{'use_layout_detection':True},'layout_det_res':{},'parsing_res_list':[
            {'block_label':'display_formula','block_content':'x² + y² = 1','block_bbox':[100,200,300,400]},
            SimpleNamespace(label='text',content='Follow after the formula.',bbox=[0,0,10,10])]}
        text,blocks=batch.page_blocks(page)
        self.assertEqual(text,'x² + y² = 1\n\nFollow after the formula.')
        self.assertEqual([b['reading_order_index'] for b in blocks],[0,1])
        self.assertEqual(blocks[0]['bbox_pixels'],[100,200,300,400])

    def fake_fitz(self,oversize=False,white=False):
        observed=[]
        class Page:
            rect=SimpleNamespace(width=100000 if oversize else 2.4,height=100000 if oversize else 4.8)
            def get_pixmap(self,**options):
                observed.append(options)
                return SimpleNamespace(width=10,height=20,n=3,samples=b'\xff'*600 if white else b'\x00\x01\x02'*200,
                                       tobytes=lambda kind:b'PNG_SYNTHETIC')
        class Doc:
            is_encrypted=False;page_count=3
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def load_page(self,index):
                assert index==0
                return Page()
        return SimpleNamespace(open=lambda _:Doc(),csRGB='RGB_CONSTANT'),observed

    def test_render_is_full_color_lossless_without_rotation_or_crop_edits(self):
        fitz,observed=self.fake_fitz();scratch=self.directory('render')
        path,info=batch.render_page('synthetic.pdf',1,self.manifest['sources'][0],scratch,fitz=fitz)
        self.assertEqual(observed,[{'dpi':300,'colorspace':'RGB_CONSTANT','alpha':False,'annots':True}])
        self.assertEqual(path.read_bytes(),b'PNG_SYNTHETIC');self.assertEqual(info['colorspace'],'RGB')

    def test_render_pixel_limit_is_checked_before_allocation_and_white_is_pending(self):
        fitz,observed=self.fake_fitz(oversize=True)
        with self.assertRaisesRegex(batch.BatchError,'render_pixel_limit'):
            batch.render_page('synthetic.pdf',1,self.manifest['sources'][0],self.directory(),fitz=fitz)
        self.assertEqual(observed,[])
        fitz,_=self.fake_fitz(white=True);scratch=self.directory('white')
        path,info=batch.render_page('synthetic.pdf',1,self.manifest['sources'][0],scratch,fitz=fitz)
        self.assertIsNone(path);self.assertTrue(info['uniform_white_candidate']);self.assertEqual(list(scratch.iterdir()),[])

    def test_page_failure_isolated_checkpoint_at_most_requested_pages_and_partial(self):
        job=self.job([{'source_index':i,'page_number':p} for i in range(2) for p in (1,2)])
        seen=[];saved=[];owner=self
        class Engine:
            closed=False
            def page(self,source,page,seconds):
                seen.append((source['index'],page))
                return {'status':'pending','code':'page_ocr_failed','seconds':1} if len(seen)==1 else owner.reply()
            def close(self):self.closed=True
        engine=Engine()
        def checkpoint(records,cursor,counters,state,previous):
            saved.append(records);return {'artifact':'fixture/'+batch.PROJECT+'/checkpoint-'+str(cursor)+':v0','manifest_sha256':'a'*64,'next_cursor':cursor}
        result=batch.process_pages(job,self.manifest,batch.validate_manifest(self.manifest),engine,lambda _:None,checkpoint,999999999)
        self.assertEqual(len(seen),4);self.assertTrue(engine.closed);self.assertTrue(all(len(rows)<=2 for rows in saved))
        self.assertEqual(result['status'],'partial');self.assertEqual(result['extracted_pages'],3);self.assertEqual(result['pending_attempted_pages'],1)
        self.assertFalse(result['all_source_pending_pages_extracted'])

    def test_calibration_completion_is_not_bulk_or_all_pending_completion(self):
        saved=[];owner=self
        engine=SimpleNamespace(page=lambda *_:owner.reply(),close=lambda:None)
        result=batch.process_pages(self.job(),self.manifest,batch.validate_manifest(self.manifest),engine,lambda _:None,
            lambda rows,cursor,*_:{'artifact':'fixture/'+batch.PROJECT+'/checkpoint:v0','manifest_sha256':'a'*64,'next_cursor':cursor},999999999)
        self.assertEqual(result['status'],'calibration_complete');self.assertFalse(result['all_source_pending_pages_extracted'])

    def test_deadline_stops_new_pages_and_preserves_partial_checkpoint(self):
        now=[0];owner=self;saved=[]
        def page(*_):now[0]+=5;return owner.reply()
        engine=SimpleNamespace(page=page,close=lambda:None)
        result=batch.process_pages(self.job(),self.manifest,batch.validate_manifest(self.manifest),engine,lambda _:None,
            lambda rows,cursor,*_:saved.append(rows) or {'artifact':'fixture/'+batch.PROJECT+'/checkpoint:v0','manifest_sha256':'a'*64,'next_cursor':cursor},
            2,clock=lambda:now[0])
        self.assertEqual(result['status'],'partial');self.assertEqual(result['processed_pages'],1);self.assertEqual(len(saved),1)

    def test_hard_supervisor_kills_only_its_spawned_group_and_keeps_checkpoint_receipt(self):
        job=self.job();env={**self.env,'HASLA_OCR_BATCH_JOB':json.dumps(job)};killed=[];observed=[]
        class Process:
            pid=12345;done=False
            def poll(self):return 1 if self.done else None
            def wait(self,timeout):raise subprocess.TimeoutExpired('synthetic-worker',timeout)
        def popen(command,**options):
            observed.append(options);path=Path(options['env']['HASLA_OCR_BATCH_RESULT_PATH'])
            path.write_bytes(batch.canonical({'kind':batch.KIND,'status':'running','terminal':False,'processed_pages':2,'checkpoints':[]}))
            return Process()
        def killer(process):killed.append(process.pid);process.done=True
        with patch.object(batch.sys,'platform','linux'):
            result=batch.supervise(env,popen=popen,killer=killer)
        self.assertEqual(killed,[12345]);self.assertEqual(result['status'],'partial');self.assertEqual(result['code'],'worker_timeout')
        self.assertEqual(result['processed_pages'],2);self.assertTrue(observed[0]['start_new_session'])
        self.assertEqual(observed[0]['stdout'],subprocess.DEVNULL)

    def output_sdk(self,fail_second=False):
        owner=self;observed=SimpleNamespace(files=[],uploads=0,finished=False,summary={},engines=[])
        class Artifact:
            def __init__(self,name,type,metadata):
                owner.assertEqual(type,batch.OUTPUT_TYPE);owner.assertTrue(metadata['private'])
                self.qualified_name='fixture/'+batch.PROJECT+'/'+name+':v0';self.state='PENDING';self.files={}
            def add_file(self,path,name):self.files[name]=Path(path).read_bytes()
            def wait(self,timeout):self.state='COMMITTED'
        class Run:
            summary=observed.summary
            def log_artifact(self,artifact):
                observed.uploads+=1
                if fail_second and observed.uploads==2:raise batch.BatchError('checkpoint_failed')
                observed.files.append(artifact.files)
            def log(self,*args,**kwargs):pass
            def finish(self,exit_code):observed.finished=True
        def init(**options):
            print(PRIVATE);owner.assertEqual(options['resume'],'never');return Run()
        sdk=SimpleNamespace(Api=self.sdk.Api,Settings=lambda **options:options,Artifact=Artifact,init=init)
        class Engine:
            def __init__(self,*args):self.closed=False;observed.engines.append(self)
            def page(self,*args):return owner.reply(PRIVATE+'\u0085\u2028\u2029 x² ≠ x2')
            def close(self):self.closed=True
        return sdk,Engine,observed

    def test_private_end_to_end_outputs_checkpoint_rows_only_and_preserves_source_bytes(self):
        sdk,engine,observed=self.output_sdk();job=self.job()
        env={**self.env,'RUN':'hasla-private-ocr-batch-123','HASLA_OCR_BATCH_JOB':json.dumps(job),
             'HASLA_OCR_BATCH_WORKER_SHA256':hashlib.sha256(Path(batch.__file__).read_bytes()).hexdigest()}
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            result=batch.run_batch(env,sdk=sdk,privacy=self.privacy,engine_factory=engine)
        self.assertEqual(output.getvalue(),'');self.assertEqual(result['status'],'calibration_complete')
        self.assertEqual(result['source_pdfs_byte_verified'],2);self.assertEqual(result['source_aliases_inventory_checked'],2)
        self.assertTrue(result['original_selected_pdf_bytes_unchanged']);self.assertTrue(observed.finished)
        self.assertTrue(all(e.closed for e in observed.engines));self.assertEqual(len(observed.files),1)
        files=observed.files[0];self.assertEqual(set(files),{'pages.jsonl.gz','checkpoint.json'})
        raw=gzip.decompress(files['pages.jsonl.gz']);rows=[json.loads(line) for line in raw.split(b'\n') if line]
        self.assertEqual(len(rows),2);self.assertIn('\u0085\u2028\u2029',rows[0]['text'])
        self.assertFalse(rows[0]['metadata']['training_eligible']);self.assertNotIn(PRIVATE,json.dumps(observed.summary))
        checkpoint=json.loads(files['checkpoint.json']);self.assertEqual(checkpoint['shard']['raw_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(self.downloads,['manifest.json','source_0000.pdf','source_0001.pdf'])

    def test_later_upload_failure_reports_committed_partial_not_all_pages(self):
        sdk,engine,observed=self.output_sdk(fail_second=True);job={**self.job(),'checkpoint_pages':1}
        env={**self.env,'RUN':'hasla-private-ocr-batch-123','HASLA_OCR_BATCH_JOB':json.dumps(job),
             'HASLA_OCR_BATCH_WORKER_SHA256':hashlib.sha256(Path(batch.__file__).read_bytes()).hexdigest()}
        result=batch.run_batch(env,sdk=sdk,privacy=self.privacy,engine_factory=engine)
        self.assertEqual(result['status'],'partial');self.assertEqual(result['processed_pages'],1)
        self.assertEqual(len(result['checkpoints']),1);self.assertEqual(result['code'],'checkpoint_failed')
        self.assertTrue(observed.finished);self.assertTrue(all(e.closed for e in observed.engines))

    def test_committed_checkpoint_is_not_lost_when_progress_telemetry_fails(self):
        sdk,engine,observed=self.output_sdk();original=sdk.init
        def init(**options):
            run=original(**options)
            def log(*args,**kwargs):
                if observed.uploads:raise RuntimeError(PRIVATE)
            run.log=log;return run
        sdk.init=init
        env={**self.env,'RUN':'hasla-private-ocr-batch-123','HASLA_OCR_BATCH_JOB':json.dumps(self.job()),
             'HASLA_OCR_BATCH_WORKER_SHA256':hashlib.sha256(Path(batch.__file__).read_bytes()).hexdigest()}
        result=batch.run_batch(env,sdk=sdk,privacy=self.privacy,engine_factory=engine)
        self.assertEqual(observed.uploads,1);self.assertEqual(result['status'],'calibration_complete')
        self.assertEqual(len(result['checkpoints']),1);self.assertEqual(result['processed_pages'],2)

    def test_existing_native_only_qwq_gate_rejects_machine_ocr_record(self):
        from private_dual_run import validate_source_lineage
        row=batch.page_record(self.job(),self.manifest,{'source_index':0,'page_number':1},self.reply())
        with self.assertRaises(ValueError):validate_source_lineage([row],'solver')

    def test_bulk_all_pending_is_small_explicit_plan_and_requires_prior_calibration(self):
        proof={'artifact':'fixture/'+batch.PROJECT+'/calibration:v0','manifest_sha256':'a'*64}
        value={**self.job(),'mode':'bulk','page_keys':'all_pending','bulk_authorized':True,'calibration_checkpoint':proof}
        batch.validate_job(value)
        with self.assertRaises(batch.BatchError):batch.validate_job({**value,'bulk_authorized':False})

    def test_explicit_cover_exclusion_survives_ocr_and_generic_manifest_counts(self):
        job={**self.job(),'learning_exclusions':[{'source_index':0,'page_number':1,'reason':'cover_page'}]}
        batch.validate_job(job)
        row=batch.page_record(job,self.manifest,{'source_index':0,'page_number':1},self.reply())
        self.assertTrue(row['metadata']['learning_excluded']);self.assertEqual(row['metadata']['learning_exclusion_reasons'],['cover_page'])
        self.assertFalse(row['metadata']['training_eligible'])
        with patch.object(batch,'EXPECTED_SOURCES',999),patch.object(batch,'EXPECTED_PENDING',9999):
            batch.validate_job(job)
            _,manifest,pending,_=batch.open_source(REFERENCE,self.env,self.directory(),sdk=self.sdk,privacy=self.privacy,
                expected_hash=job['source_manifest_sha256'],expected_sources=2,expected_pending=4)
        self.assertEqual(len(manifest['sources']),2);self.assertEqual(len(pending),4)

    def test_checkpoint_cadence_never_exceeds_twenty_five_pages(self):
        job={**self.job(),'mode':'bulk','page_keys':[{'source_index':0,'page_number':p} for p in range(1,27)],'checkpoint_pages':25}
        pending={(0,p) for p in range(1,27)};sizes=[];owner=self
        engine=SimpleNamespace(page=lambda *_:owner.reply(),close=lambda:None)
        def checkpoint(rows,cursor,*args):
            sizes.append(len(rows));return {'artifact':'fixture/'+batch.PROJECT+'/checkpoint-'+str(cursor)+':v0','manifest_sha256':'a'*64,'next_cursor':cursor}
        result=batch.process_pages(job,self.manifest,pending,engine,lambda _:None,checkpoint,999999999)
        self.assertEqual(sizes,[25,1]);self.assertEqual(result['processed_pages'],26)

    def test_privacy_loss_before_checkpoint_upload_never_logs_payload(self):
        sdk,engine,observed=self.output_sdk();env={**self.env,'RUN':'hasla-private-ocr-batch-123','HASLA_OCR_BATCH_WORKER_SHA256':'a'*64}
        folder=self.directory('checkpoint-output');calls=[]
        def private(env,entity):
            calls.append(True)
            if len(calls)==2:raise batch.BatchError('private_project_unverified')
        run=SimpleNamespace(summary={},log_artifact=lambda _:self.fail('upload after privacy loss'),log=lambda *_,**__:None)
        writer=batch.checkpoint_writer(self.job(),self.manifest,run,sdk,env,'fixture',folder,999999999,privacy=private)
        row=batch.page_record(self.job(),self.manifest,{'source_index':0,'page_number':1},self.reply())
        with self.assertRaisesRegex(batch.BatchError,'private_project'):
            writer([row],1,{'processed_pages':1,'extracted_pages':1},'running',None)
        self.assertEqual(observed.uploads,0)


if __name__=='__main__':unittest.main()

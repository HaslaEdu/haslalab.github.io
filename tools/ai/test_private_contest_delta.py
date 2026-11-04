"""Offline synthetic fixtures; no paid API, W&B access, GPU or private source bodies."""
from collections import Counter
from contextlib import redirect_stdout
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import private_contest_delta as delta
import private_dual_run as dual
import private_pod_train as pod
import train_lora

PRIVATE = 'SYNTHETIC_PRIVATE_TEXT_MUST_NOT_APPEAR_IN_STDOUT '
REFERENCE = 'fixture-entity/hasla-ai-private-training/hasla-contest-sources-partial-123:v0'


def sha(data): return hashlib.sha256(data).hexdigest()


def source_for(split, offset=0):
    for i in range(offset,100000):
        source=sha(('fixture-source-'+str(i)).encode())
        if delta.source_split(source)==split: return source
    raise AssertionError('fixture source unavailable')


def page_for(source, *, ordinal=1, text=None, status='text_ready', extra=None):
    text=text if text is not None else PRIVATE*5
    value={'source_sha256':source,'source_bytes':100,'pdf_page':ordinal,'width':595.,'height':842.,'rotation':0,
        'native_char_count':len(text),'native_text':text,'text_geometry':{'blocks':[]},
        'native_image_object_count':0,'native_status':status,'quality_gate':delta.quality(text,min_chars=80),
        'independent_scientific_review':False,'problem_segmentation':'pending'}
    if extra: value.update(extra)
    return value


def make_inventory(root, sources):
    root.mkdir()
    (root/'native').mkdir()
    receipts=[]
    for i,(source,pages) in enumerate(sources):
        alias=f'source_{i:06d}.pdf'
        native='native/'+alias[:-4]+'.jsonl.gz'
        compressed=gzip.compress(b''.join(delta.canonical(p) for p in pages),mtime=0)
        (root/native).write_bytes(compressed)
        receipts.append({'alias':alias,'filename':f'fixture-{i}.pdf',
            'archive_url':f'https://{delta.fetch.ARCHIVE_HOST}/pdf/fixture-{i}.pdf',
            'declared_bytes':100,'declared_sha256':None,'status':'verified_native_extracted',
            'scientific_accuracy_verified':False,'problem_segmentation':'pending','sha256':source,'bytes':100,
            'integrity_basis':'catalogued_archive_download_local_sha256','native_alias':native,
            'native_sha256':sha(compressed),'native_bytes':len(compressed),'pages':len(pages),
            'native_characters':sum(len(p['native_text']) for p in pages),
            'quality_counts':dict(Counter(p['native_status'] for p in pages))})
    value={'schema_version':1,'kind':'private_contest_source_receipts','private':True,
        'source_catalog_sha256':'a'*64,'plan_sha256':'b'*64,'complete':False,'stop_code':'transfer_deadline',
        'complete_means':'all_plan_names_processed_not_all_valid','planned_source_names':len(receipts)+2,
        'processed_source_names':len(receipts),'remaining_source_names':2,'not_all_names_are_unique_pdfs':True,
        'status_counts':dict(Counter(r['status'] for r in receipts)),'downloaded_body_bytes':100*len(receipts),
        'native_compressed_bytes':sum(r['native_bytes'] for r in receipts),'sources':receipts,
        'ocr_performed':False,'training_or_deployment_performed':False}
    (root/'inventory.json').write_bytes(delta.canonical(value))
    return value,delta.sha_file(root/'inventory.json')


def meta_for(source,split):
    return {'target_role':'solver','split':split,'group_id':'fixture:'+source,'scan_suspect':False,
        'content_type':'competition_problem','haslalab_provenance':{'source_id':'fixture:'+source,
        'source_family':'competition_document','local_source_sha256':source,'extraction':'native','original_locator':'page:1'}}


def make_packed(root, train_source=None, validation_source=None, *, segment=None):
    root.mkdir()
    files={}
    for split,source in (('train',train_source or sha(b'old-train')),('validation',validation_source or sha(b'old-validation'))):
        meta=meta_for(source,split)
        if split=='train' and segment:
            meta['packing']={'segments':[{'metadata':segment,'original_text_sha256':sha(b'old-segment')} ]}
        raw=delta.canonical({'text':'Existing synthetic packed '+split,'metadata':meta})
        (root/(split+'.text.jsonl')).write_bytes(raw)
        files[split]={'bytes':len(raw),'sha256':sha(raw),'records':1,'path':'NEVER_FOLLOW_THIS_PATH'}
    (root/'manifest.json').write_bytes(delta.canonical({'target_role':'solver','format':'text','files':files}))
    return delta.sha_file(root/'manifest.json')


class FakeArtifact:
    def __init__(self,input_root,report):
        self.qualified_name=REFERENCE;self.type=delta.fetch.PARTIAL_TYPE;self.state='COMMITTED';self.is_link=False
        self.metadata={'private':True,'complete':False,'plan_sha256':report['plan_sha256'],
                       'source_catalog_sha256':report['source_catalog_sha256']}
        self.bodies={'inventory.json':(input_root/'inventory.json').read_bytes()}
        for r in report['sources']:
            if r['status']=='verified_native_extracted':
                self.bodies[r['native_alias']]=(input_root/r['native_alias']).read_bytes()
                self.bodies['pdf/'+r['alias']]=b'P'*r['bytes']
        self.manifest=SimpleNamespace(entries={n:SimpleNamespace(size=len(b),ref=None) for n,b in self.bodies.items()})
        self.downloaded=[]
    def get_entry(self,name):
        def download(*,root,skip_cache):
            self.downloaded.append(name)
            path=Path(root)/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(self.bodies[name]);return str(path)
        return SimpleNamespace(download=download,path=name,ref=None,size=len(self.bodies[name]))


class ContestDeltaTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.input=self.root/'input';self.packed=self.root/'packed';self.output=self.root/'out'
        self.a=source_for('train');self.b=source_for('validation')
        self.report,self.pin=make_inventory(self.input,[(self.a,[page_for(self.a,text=PRIVATE*5+' A')]),
            (self.b,[page_for(self.b,text=PRIVATE*5+' B')])])
        self.packed_pin=make_packed(self.packed)
        self.env={'WANDB_API_KEY':'synthetic-key','WANDB_ENTITY':'fixture-entity'}
        self.addCleanup(patch.stopall)
        import requests
        patch.object(requests.sessions.Session,'request',side_effect=AssertionError('network forbidden')).start()
        patch('socket.create_connection',side_effect=AssertionError('network forbidden')).start()
    def rewrite(self):
        self.report['processed_source_names']=len(self.report['sources'])
        self.report['remaining_source_names']=self.report['planned_source_names']-len(self.report['sources'])
        self.report['status_counts']=dict(Counter(r['status'] for r in self.report['sources']))
        self.report['native_compressed_bytes']=sum(r.get('native_bytes',0) for r in self.report['sources'] if r['status']=='verified_native_extracted')
        (self.input/'inventory.json').write_bytes(delta.canonical(self.report));self.pin=delta.sha_file(self.input/'inventory.json')
    def replace_page(self,index,page):
        r=self.report['sources'][index];raw=gzip.compress(delta.canonical(page),mtime=0)
        (self.input/r['native_alias']).write_bytes(raw)
        r.update(native_bytes=len(raw),native_sha256=sha(raw),pages=1,native_characters=len(page['native_text']),quality_counts={page['native_status']:1})
        self.rewrite()
    def run_conversion(self,**kwargs):
        args=dict(input_dir=self.input,inventory_sha=self.pin,packed_dir=self.packed,packed_manifest_sha=self.packed_pin,
            output_dir=self.output,dataset_version='fixture-delta-v1',authorization_note='Synthetic fixture authorization')
        args.update(kwargs);return delta.convert_local(**args)
    def read_output(self,split):
        return [json.loads(t) for t in (self.output/(split+'.text.jsonl')).read_text(encoding='utf-8').splitlines()]
    def remote(self,artifact=None,**kwargs):
        artifact=artifact or FakeArtifact(self.input,self.report)
        api=SimpleNamespace(artifact=Mock(return_value=artifact));sdk=SimpleNamespace(Api=Mock(return_value=api))
        privacy=Mock();destination=self.root/('remote-'+str(len(list(self.root.glob('remote-*')))));destination.mkdir()
        result=delta.download_sources(REFERENCE,self.pin,self.env,destination,privacy=privacy,sdk_loader=lambda:sdk,**kwargs)
        return result,artifact,sdk,privacy,destination

    def test_only_native_text_delta_passes_existing_qwq_gates(self):
        result=self.run_conversion()
        self.assertEqual({s:result['files'][s]['records'] for s in ('train','validation')},{'train':1,'validation':1})
        for split in ('train','validation'):
            values=self.read_output(split)
            dual.validate_source_lineage(values,'solver');pod.validate_row_roles(values,'solver','text')
            pod.rows_from_payload((self.output/(split+'.text.jsonl')).read_bytes(),split,'text')
            self.assertFalse(values[0]['metadata']['scientifically_verified'])
            self.assertFalse(values[0]['metadata']['human_reviewed'])
        train,held=train_lora.load(self.output/'train.text.jsonl',data_format='text',validation_path=self.output/'validation.text.jsonl',role='solver')
        pod.verify_partitions(train,held)
        self.assertFalse(result['training_ready']);self.assertTrue(result['requires_token_length_validation_before_training'])

    def test_old_source_seen_only_in_hidden_packed_segment_is_skipped(self):
        for p in self.packed.iterdir():p.unlink()
        self.packed.rmdir()
        self.packed_pin=make_packed(self.packed,segment=meta_for(self.b,'train'))
        (self.input/self.report['sources'][1]['native_alias']).unlink()
        result=self.run_conversion()
        self.assertEqual(result['totals']['existing_source_sha_skipped'],1)
        self.assertEqual(result['files']['validation']['records'],0)

    def test_existing_source_sha_cannot_cross_packed_splits(self):
        for p in self.packed.iterdir():p.unlink()
        self.packed.rmdir();self.packed_pin=make_packed(self.packed,segment=meta_for(sha(b'old-validation'),'train'))
        with self.assertRaisesRegex(delta.DeltaError,'existing_source_split_conflict'):self.run_conversion()
        self.assertFalse(self.output.exists())

    def test_packed_paths_not_followed_and_missing_hash_fails(self):
        delta.load_existing(self.packed,self.packed_pin)
        m=json.loads((self.packed/'manifest.json').read_text());del m['files']['train']['sha256']
        (self.packed/'manifest.json').write_bytes(delta.canonical(m))
        with self.assertRaisesRegex(delta.DeltaError,'invalid_sha256'):
            self.run_conversion(packed_manifest_sha=delta.sha_file(self.packed/'manifest.json'))

    def test_inventory_native_and_existing_checksum_mismatch_stop(self):
        for kwargs in ({'inventory_sha':'f'*64},{'packed_manifest_sha':'f'*64}):
            with self.subTest(kwargs=kwargs),self.assertRaisesRegex(delta.DeltaError,'sha256_mismatch'):self.run_conversion(**kwargs)
        (self.input/self.report['sources'][0]['native_alias']).write_bytes(b'wrong')
        with self.assertRaises(delta.DeltaError):self.run_conversion()
        self.assertFalse(self.output.exists())

    def test_scan_sparse_original_quality_and_ocr_never_become_approved(self):
        cases=[page_for(self.a,status='scan_suspect',text='short'),page_for(self.a,status='sparse_or_damaged'),
            page_for(self.a,extra={'ocr_performed':True}),page_for(self.a,extra={'machine_ocr':True}),
            page_for(self.a,extra={'metadata':{'extraction_method':'machine_ocr'}}),
            page_for(self.a,extra={'scan_suspect':True}),
            page_for(self.a,extra={'metadata':{'scan_suspect':True}}),
            page_for(self.a,extra={'extraction_method':'OCR'}),
            page_for(self.a,extra={'extraction':'canonical_body'}),
            page_for(self.a,extra={'quality_gate':{'status':'pending_extraction','issues':['held']}}),
            page_for(self.a,text='\ue000'*200)]
        for i,page in enumerate(cases):
            self.replace_page(0,page)
            result=self.run_conversion(output_dir=self.root/('reject-'+str(i)))
            self.assertEqual(result['totals']['pages_rejected'],1)
            self.assertEqual(result['files']['train']['records'],0)

    def test_duplicate_failed_and_missing_receipts_are_not_exported(self):
        for i,status in enumerate(('duplicate_existing_sha256','failed','archive_not_found'),2):
            r=copy.deepcopy(self.report['sources'][0]);r.update(alias=f'source_{i:06d}.pdf',filename=f'other-{i}.pdf',
                archive_url=f'https://{delta.fetch.ARCHIVE_HOST}/pdf/other-{i}.pdf',status=status)
            if status=='failed':r['failure_code']='native_parse_failed'
            self.report['sources'].append(r)
        self.report['planned_source_names']=7;self.rewrite()
        result=self.run_conversion();self.assertEqual(result['totals']['nonverified_source_receipts_skipped'],3)

    def test_decompression_page_and_total_caps_leave_no_output(self):
        with patch.object(delta,'MAX_NATIVE_RAW',50),self.assertRaisesRegex(delta.DeltaError,'native_decompression_limit'):
            self.run_conversion()
        with patch.object(delta,'MAX_PAGE_BYTES',20),self.assertRaisesRegex(delta.DeltaError,'native_decompression_limit'):
            self.run_conversion()
        with patch.object(delta,'MAX_TOTAL_RAW',50),self.assertRaisesRegex(delta.DeltaError,'native_decompression_limit'):
            self.run_conversion()
        self.assertFalse(self.output.exists())

    def test_page_count_and_source_mismatches_abort_atomic_export(self):
        self.replace_page(0,page_for(self.a,extra={'source_sha256':'f'*64}))
        with self.assertRaisesRegex(delta.DeltaError,'native_page_schema_rejected'):self.run_conversion()
        self.assertFalse(self.output.exists())
        self.replace_page(0,page_for(self.a));r=self.report['sources'][0];r['pages']=2;r['quality_counts']={'text_ready':2};self.rewrite()
        with self.assertRaisesRegex(delta.DeltaError,'native_page_count_mismatch'):self.run_conversion()
        self.assertFalse(self.output.exists())

    def test_gzip_truncation_is_sanitized_and_not_partial_success(self):
        r=self.report['sources'][0];path=self.input/r['native_alias'];raw=path.read_bytes()[:-5];path.write_bytes(raw)
        r.update(native_sha256=sha(raw),native_bytes=len(raw));self.rewrite()
        with self.assertRaisesRegex(delta.DeltaError,'native_gzip_rejected'):self.run_conversion()
        self.assertFalse(self.output.exists())

    def test_exact_duplicate_chunks_do_not_cross_delta_splits(self):
        self.replace_page(0,page_for(self.a));self.replace_page(1,page_for(self.b))
        result=self.run_conversion()
        self.assertEqual(sum(result['files'][s]['records'] for s in ('train','validation')),1)
        self.assertEqual(result['totals']['exact_duplicate_chunks_skipped'],1)

    def test_source_split_and_output_are_deterministic(self):
        self.run_conversion();other=self.root/'other-output';delta_result=self.run_conversion(output_dir=other)
        for split in ('train','validation'):
            self.assertEqual((self.output/(split+'.text.jsonl')).read_bytes(),(other/(split+'.text.jsonl')).read_bytes())
        self.assertEqual(delta_result['split_seed'],delta.SEED)

    def test_read_only_inspect_prints_inventory_sha_and_no_native_text(self):
        with redirect_stdout(io.StringIO()) as out:delta.main(['--input-dir',str(self.input),'--inspect'])
        result=json.loads(out.getvalue());self.assertEqual(result['inventory_sha256'],self.pin)
        self.assertNotIn(PRIVATE,out.getvalue());self.assertFalse(self.output.exists())

    def test_conversion_cli_stdout_is_counts_and_hashes_only(self):
        with redirect_stdout(io.StringIO()) as out:delta.main(['--input-dir',str(self.input),'--inventory-sha256',self.pin,
            '--packed-dir',str(self.packed),'--packed-manifest-sha256',self.packed_pin,'--output-dir',str(self.output),
            '--dataset-version','fixture-cli','--authorization-note',PRIVATE])
        self.assertNotIn(PRIVATE,out.getvalue());self.assertNotIn('native_text',out.getvalue())
        self.assertFalse(json.loads(out.getvalue())['training_or_upload_performed'])

    def test_remote_inspect_downloads_inventory_only_and_rechecks_private(self):
        (report,pin),artifact,sdk,privacy,_=self.remote(inspect=True)
        self.assertEqual(pin,self.pin);self.assertEqual(artifact.downloaded,['inventory.json'])
        self.assertEqual(privacy.call_count,2);sdk.Api.assert_called_once()

    def test_remote_downloads_only_registered_native_never_pdf(self):
        _,artifact,_,_,destination=self.remote()
        self.assertEqual(len(artifact.downloaded),3)
        self.assertFalse(any(n.startswith('pdf/') for n in artifact.downloaded))
        self.assertFalse((destination/'pdf').exists())

    def test_remote_private_failure_precedes_sdk_or_any_download(self):
        sdk=Mock();privacy=Mock(side_effect=delta.fetch.FetchError('private_project_not_verified'))
        with self.assertRaisesRegex(delta.DeltaError,'private_project_not_verified'):
            delta.download_sources(REFERENCE,self.pin,self.env,self.root/'safe',privacy=privacy,sdk_loader=sdk)
        sdk.assert_not_called()

    def test_alias_wrong_entity_project_and_extra_credentials_rejected(self):
        for ref in (REFERENCE.replace(':v0',':latest'),REFERENCE.replace('hasla-ai-private-training','public-project'),
                    REFERENCE.replace('fixture-entity','another-entity')):
            with self.subTest(ref=ref),self.assertRaises(delta.DeltaError):delta.reference_parts(ref,self.env)
        for key in ('HF_TOKEN','RUNPOD_API_KEY','OPENAI_API_KEY'):
            with self.subTest(key=key),self.assertRaises(delta.DeltaError):
                delta.download_sources(REFERENCE,self.pin,{**self.env,key:'NEVER_PRINT'},self.root/'safe',sdk_loader=Mock())

    def test_remote_reference_traversal_link_and_sizes_rejected(self):
        mutations=[lambda a:setattr(a,'is_link',True),
            lambda a:setattr(a.manifest.entries['inventory.json'],'ref','https://example.invalid/private'),
            lambda a:setattr(a.manifest.entries['inventory.json'],'ref',''),
            lambda a:setattr(a.manifest.entries['inventory.json'],'path','../escape'),
            lambda a:a.manifest.entries.update({'../escape':SimpleNamespace(size=1,ref=None)}),
            lambda a:setattr(a.manifest.entries['inventory.json'],'size',delta.MAX_INVENTORY+1)]
        for mutation in mutations:
            artifact=FakeArtifact(self.input,self.report);mutation(artifact)
            with self.assertRaises(delta.DeltaError):self.remote(artifact=artifact,inspect=True)
            self.assertEqual(artifact.downloaded,[])

    def test_unregistered_native_file_or_modified_inventory_rejected(self):
        artifact=FakeArtifact(self.input,self.report)
        artifact.manifest.entries['native/source_999999.jsonl.gz']=SimpleNamespace(size=1,ref=None)
        with self.assertRaisesRegex(delta.DeltaError,'artifact_inventory_files_mismatch'):self.remote(artifact=artifact)
        artifact=FakeArtifact(self.input,self.report);artifact.bodies['inventory.json']=b'X'*len(artifact.bodies['inventory.json'])
        with self.assertRaisesRegex(delta.DeltaError,'input_sha256_mismatch'):self.remote(artifact=artifact,inspect=True)

    def test_bound_entry_identity_is_checked_before_download(self):
        for field,value in (('path','../escape'),('ref','https://example.invalid/private'),
                            ('ref',''),('size',1),('size',True)):
            artifact=FakeArtifact(self.input,self.report)
            original=artifact.get_entry
            def get_entry(name):
                bound=original(name);setattr(bound,field,value);return bound
            artifact.get_entry=get_entry
            with self.subTest(field=field,value=value),self.assertRaisesRegex(delta.DeltaError,'bound_artifact_entry_rejected'):
                self.remote(artifact=artifact,inspect=True)
            self.assertEqual(artifact.downloaded,[])

    def test_private_paths_and_existing_output_are_rejected(self):
        with self.assertRaises(delta.DeltaError):delta.private_path(self.root/'OneDrive'/'data')
        self.output.mkdir()
        with self.assertRaisesRegex(delta.DeltaError,'output_collision_or_overlap'):self.run_conversion()
        self.assertEqual(list(self.output.iterdir()),[])


if __name__=='__main__':unittest.main()

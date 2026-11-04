"""Small offline fixtures; no real PDFs, renders, model dependencies or APIs."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import private_inspect_ocr_source as batch

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
        patch.object(batch.urllib.request,'urlopen',side_effect=AssertionError('network forbidden')).start()
        temporary=tempfile.TemporaryDirectory(prefix='hasla-batch-unit-');self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
        self.manifest,self.payloads=fixture();self.downloads=[];self.privacy_checks=[]
        self.env={'WANDB_API_KEY':'SYNTHETIC_KEY','WANDB_ENTITY':'fixture','WANDB_PROJECT':batch.PROJECT,'HASLA_OCR_SOURCE_ARTIFACT':REFERENCE}
        self.entries={name:SimpleNamespace(size=len(raw),ref=None) for name,raw in self.payloads.items()}
        test=self
        class Artifact:
            qualified_name=REFERENCE;type=batch.SOURCE_TYPE;state='COMMITTED'
            metadata={'private':True,'kind':'ocr-source','source_count':2,'pending_pages':4,'total_pdf_bytes':test.manifest['total_pdf_bytes']}
            manifest=SimpleNamespace(entries=test.entries)
            def get_path(self,name):
                def download(root):
                    test.downloads.append(name);path=Path(root)/name;path.write_bytes(test.payloads[name]);return str(path)
                return SimpleNamespace(download=download)
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
        for field in ('HF_TOKEN','RUNPOD_API_KEY','OPENAI_API_KEY'):
            with self.assertRaises(batch.BatchError):batch.credentials({**self.env,field:'secret'},'fixture')


if __name__=='__main__':unittest.main()

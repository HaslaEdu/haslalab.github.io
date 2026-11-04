import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import private_contest_delta_run as run


class Entry:
    def __init__(self,name,raw):self.path=name;self.ref=None;self.size=len(raw);self.raw=raw;self.downloads=0
    def download(self,root,skip_cache):
        self.downloads+=1;path=Path(root)/self.path;path.write_bytes(self.raw);return str(path)


class DeltaPreparationTests(unittest.TestCase):
    def packed(self):
        entries={name:Entry(name,b'{"id":"fixture"}\n') for name in ('train.text.jsonl','validation.text.jsonl')}
        ref='entity/hasla-ai-private-training/fixture:v0'
        artifact=types.SimpleNamespace(qualified_name=ref,type='dataset',state='COMMITTED',is_link=False,
            manifest=types.SimpleNamespace(entries=entries),get_entry=lambda name:entries[name])
        sdk=types.SimpleNamespace(Api=lambda **kw:types.SimpleNamespace(artifact=lambda *a,**kw:artifact))
        manifest={'packed_artifact':ref,'packed_files':{s:{'bytes':len(e.raw),'sha256':hashlib.sha256(e.raw).hexdigest(),'records':1}
            for s,e in zip(('train','validation'),entries.values())}}
        return manifest,entries,artifact,sdk

    def test_fixed_two_file_inventory_and_actual_sha(self):
        manifest,entries,artifact,sdk=self.packed()
        with tempfile.TemporaryDirectory() as folder,patch.object(run.fetch,'assert_private'):
            root=Path(folder)/'packed'
            digest=run.download_packed(manifest,{'WANDB_API_KEY':'fixture'},'entity',root,sdk)
            self.assertEqual(digest,run.delta.sha_file(root/'manifest.json'))
            self.assertEqual(set(p.name for p in root.iterdir()),{'train.text.jsonl','validation.text.jsonl','manifest.json'})
        self.assertEqual(sum(e.downloads for e in entries.values()),2)

    def test_bound_sdk_path_rejected_before_download(self):
        manifest,entries,artifact,sdk=self.packed();bad=Entry('../escape',b'bad')
        artifact.get_entry=lambda name:bad
        with tempfile.TemporaryDirectory() as folder,patch.object(run.fetch,'assert_private'):
            with self.assertRaisesRegex(run.PreparationError,'packed_entry_invalid'):
                run.download_packed(manifest,{'WANDB_API_KEY':'fixture'},'entity',Path(folder)/'packed',sdk)
        self.assertEqual(bad.downloads,0)

    def test_bound_external_ref_rejected_before_download(self):
        manifest,entries,artifact,sdk=self.packed();entries['train.text.jsonl'].ref='https://example.invalid/x'
        with tempfile.TemporaryDirectory() as folder,patch.object(run.fetch,'assert_private'):
            with self.assertRaisesRegex(run.PreparationError,'packed_entry_invalid'):
                run.download_packed(manifest,{'WANDB_API_KEY':'fixture'},'entity',Path(folder)/'packed',sdk)
        self.assertEqual(sum(e.downloads for e in entries.values()),0)

    def test_payload_sha_mismatch_cannot_become_previous_corpus(self):
        manifest,entries,artifact,sdk=self.packed();manifest['packed_files']['train']['sha256']='0'*64
        with tempfile.TemporaryDirectory() as folder,patch.object(run.fetch,'assert_private'):
            with self.assertRaises(run.delta.DeltaError):
                run.download_packed(manifest,{'WANDB_API_KEY':'fixture'},'entity',Path(folder)/'packed',sdk)

    def tokenizer(self,redirect=False):
        raw=b'fixture'
        calls=[]
        def get(url,**kwargs):
            calls.append(url)
            return types.SimpleNamespace(status_code=302 if redirect else 200,
                headers={'Location':'https://example.invalid/tokenizer.json'} if redirect else {},
                iter_content=lambda **kw:iter([raw]),close=lambda:None)
        files={name:(len(raw),hashlib.sha256(raw).hexdigest()) for name in run.TOKENIZER_FILES}
        return files,get,calls

    def test_public_tokenizer_pinned_bytes_without_auth(self):
        files,get,calls=self.tokenizer()
        with tempfile.TemporaryDirectory() as folder,patch.object(run,'TOKENIZER_FILES',files):
            result=run.download_tokenizer(Path(folder)/'tokenizer',get=get)
            self.assertEqual(len(list(result.iterdir())),2)
        self.assertTrue(all(run.TOKENIZER_COMMIT in url for url in calls))

    def test_tokenizer_cross_host_redirect_never_followed(self):
        files,get,calls=self.tokenizer(True)
        with tempfile.TemporaryDirectory() as folder,patch.object(run,'TOKENIZER_FILES',files):
            with self.assertRaisesRegex(run.PreparationError,'tokenizer_redirect_rejected'):
                run.download_tokenizer(Path(folder)/'tokenizer',get=get)
        self.assertEqual(len(calls),1)

    def test_committed_dataset_receipt_survives_finish_telemetry_failure(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(run.fetch,'assert_private'):
            root=Path(folder);files={}
            for split in ('train','validation'):
                path=root/(split+'.text.jsonl');path.write_bytes(b'{"fixture":true}\n')
                files[split]={'records':1,'bytes':path.stat().st_size,'sha256':run.delta.sha_file(path)}
            artifact=types.SimpleNamespace(qualified_name='entity/hasla-ai-private-training/hasla-private-stage-123-solver-data:v0',
                state='COMMITTED',add_file=lambda *a,**kw:None,wait=lambda **kw:None)
            def fail():raise RuntimeError('private telemetry')
            sdk=types.SimpleNamespace(Settings=lambda **kw:None,Artifact=lambda *a,**kw:artifact,
                init=lambda **kw:types.SimpleNamespace(log_artifact=lambda a:None,finish=fail))
            manifest={'source_artifact':'entity/hasla-ai-private-training/hasla-contest-sources-partial-1:v0',
                'inventory_sha256':'a'*64,'dataset_version':'fixture'}
            event=run.stage_packed(manifest,{'files':files},root,{},'entity',sdk,'123')
            self.assertEqual(event['status'],'staged');self.assertFalse(event['training_performed'])


if __name__=='__main__':unittest.main()

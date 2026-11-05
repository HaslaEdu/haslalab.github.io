import base64
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import subprocess
import unittest
from unittest.mock import patch

from private_qwq_bootstrap_diagnostic import bootstrap_diagnostic_source


def namespace():
    source = bootstrap_diagnostic_source()
    values = {'__name__': 'inline_test'}
    exec(compile(source, '<inline-bootstrap>', 'exec'), values)
    return values


class Tests(unittest.TestCase):
    def test_completed_import_with_shutdown_hook_is_not_misclassified_as_timeout(self):
        n=namespace()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);modules=root/'modules';modules.mkdir()
            for name in (*n['CORE'],'wandb'):
                version='0.31.0' if name=='wandb' else '1.0'
                package=modules/name;package.mkdir()
                body='import atexit,time; atexit.register(lambda:time.sleep(3))' if name=='unsloth' else ''
                (package/'__init__.py').write_text(body)
                dist=modules/(name+'-'+version+'.dist-info');dist.mkdir()
                (dist/'METADATA').write_text('Metadata-Version: 2.1\nName: '+name+'\nVersion: '+version+'\n')
            env={'PYTHONPATH':str(modules)}
            if os.name=='nt':env['SystemRoot']=os.environ['SystemRoot']
            def actual(command,**kwargs):
                self.assertTrue(command[2].endswith('; import os; os._exit(0)'))
                return subprocess.run(command,**{**kwargs,'timeout':1,'env':env})
            row,_=n['probe']('module_import',root,actual)
            self.assertEqual(row['status'],'passed');self.assertEqual(row['exit_code'],0)
            self.assertEqual(row['observations']['wandb'],'0.31.0')
            def prior(command,**kwargs):
                command=[*command];command[2]=command[2].removesuffix('; import os; os._exit(0)')
                return subprocess.run(command,**{**kwargs,'timeout':1,'env':env})
            row,_=n['probe']('module_import',root,prior)
            self.assertEqual(row['status'],'failed');self.assertEqual(row['exception_type'],'TimeoutExpired')
            self.assertEqual(row['observations']['wandb'],'0.31.0')

    def test_inline_is_self_contained_and_redacts_bounded_private_trace(self):
        n = namespace()
        text = 'PRIVATE_VALUE\nTOKEN="new secret text"\nhttps://example.com/private\nBearer ABC\n'
        text += '-----BEGIN PRIVATE KEY-----\nPEM_CONTENT\n-----END PRIVATE KEY-----\n'
        text += 'dockerArgs=[hidden]\n'+('x'*5000)+' PRIVATE_VALUE'
        result = n['sanitize'](text, {'WANDB_API_KEY':'PRIVATE_VALUE'})
        self.assertLessEqual(len(result), 4096)
        self.assertNotIn('PRIVATE_VALUE', result)
        short = n['sanitize'](text[:300], {'WANDB_API_KEY':'PRIVATE_VALUE'})
        for secret in ('new secret text','example.com','ABC','PEM_CONTENT','dockerArgs'):
            self.assertNotIn(secret, short)

    def test_probes_are_fresh_unsloth_first_and_gpu_still_runs_after_import_failure(self):
        n = namespace(); calls = []
        def run(command, **kwargs):
            code, output = command[2], Path(command[3]); calls.append(code)
            self.assertEqual(command[:2], [n['sys'].executable,'-c'])
            self.assertEqual(kwargs['timeout'], 30)
            if len(calls)==1:
                versions = dict.fromkeys(n['CORE'],'1.0'); data={'before':versions,'after':versions}
            elif len(calls)==2:
                self.assertTrue(code.startswith('import unsloth, bitsandbytes, peft, torch, wandb;'))
                kwargs['stdout'].write(b'RuntimeError: PRIVATE_VALUE\n')
                return SimpleNamespace(returncode=1)
            else:
                self.assertTrue(code.startswith('import torch;'))
                data={'available':False,'count':0,'name':None,'compiled_cuda':'12.8'}
            output.write_text(json.dumps(data)); return SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{'WANDB_API_KEY':'PRIVATE_VALUE'}):
            stages, trace = n['diagnose'](Path(directory),run)
        self.assertEqual([r['stage'] for r in stages],['core_compare','module_import','GPU_check'])
        self.assertEqual(stages[1]['exception_type'],'RuntimeError')
        self.assertFalse(stages[2]['observations']['available'])
        self.assertNotIn('PRIVATE_VALUE',trace); self.assertEqual(len(calls),3)

    def test_gpu_probe_is_torch_only_and_validates_observation_shape(self):
        n=namespace()
        def run(command,**kwargs):
            self.assertTrue(command[2].startswith('import torch;'))
            self.assertNotIn('unsloth,',command[2])
            Path(command[3]).write_text(json.dumps({'available':True,'count':1,'name':'NVIDIA A40','compiled_cuda':'12.8'}))
            return SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as directory:
            row,_=n['probe']('GPU_check',Path(directory),run)
            self.assertEqual(row['status'],'passed')
            def wrong(command,**kwargs):
                Path(command[3]).write_text('{"raw_env":"PRIVATE"}'); return SimpleNamespace(returncode=0)
            with self.assertRaises(ValueError): n['probe']('GPU_check',Path(directory),wrong)

    def test_private_committed_exact_two_files_and_safe_summary(self):
        for tampered in (False,True):
            with self.subTest(tampered=tampered), tempfile.TemporaryDirectory() as directory:
                n=namespace(); actions=[]; summary={}; artifacts=[]
                class Artifact:
                    def __init__(self,name,type,metadata):
                        self.name,self.type,self.metadata=name,type,metadata; self.paths={}; artifacts.append(self)
                    def add_file(self,path,name): self.paths[name]=Path(path)
                def upload(artifact):
                    actions.append('upload')
                    entries={name:SimpleNamespace(size=p.stat().st_size,ref=None,digest=base64.b64encode(hashlib.md5(p.read_bytes()).digest()).decode()) for name,p in artifact.paths.items()}
                    if tampered: entries['traceback.txt'].digest='wrong'
                    saved=SimpleNamespace(state='COMMITTED',type='bootstrap-diagnostic',metadata=artifact.metadata,
                        qualified_name=n['ENTITY']+'/'+n['PROJECT']+'/'+artifact.name+':v0',manifest=SimpleNamespace(entries=entries))
                    return SimpleNamespace(wait=lambda timeout:saved)
                run=SimpleNamespace(log_artifact=upload,summary=summary,finish=lambda:actions.append('finish'))
                def init(**kwargs):
                    actions.append('init'); self.assertEqual(kwargs['id'],'hasla-qwq-bootstrap-41956885560'); return run
                sdk=SimpleNamespace(init=init,Settings=lambda **k:k,Artifact=Artifact)
                def privacy(entity):
                    self.assertEqual(entity,n['ENTITY']); actions.append('privacy')
                    return {'entity':entity,'project':n['PROJECT'],'access':'PRIVATE'}
                n['diagnose']=lambda root: ([{'stage':'core_compare','status':'failed','exit_code':1,'exception_type':'RuntimeError','observations':None}],'sanitized_private_trace')
                job={'run_id':'41956885560','code_commit':'a'*40}
                if tampered:
                    with self.assertRaises(ValueError): n['publish'](job,Path(directory),lambda env:(None,privacy,sdk))
                    self.assertFalse(summary)
                else:
                    self.assertEqual(n['publish'](job,Path(directory),lambda env:(None,privacy,sdk)),1)
                    self.assertIs(type(summary['private_qwq_gpu_bootstrap_result_json']),str)
                    value=json.loads(summary['private_qwq_gpu_bootstrap_result_json'])
                    self.assertEqual(set(artifacts[0].paths),{'diagnostics.json','traceback.txt'})
                    self.assertEqual(actions[:2],['privacy','init']); self.assertEqual(actions[-1],'finish')
                    self.assertNotIn('sanitized_private_trace',json.dumps(value)); self.assertEqual(value['status'],'failed')

    def test_privacy_failure_before_initialization_and_public_error_is_fixed(self):
        n=namespace(); called=[]
        n['diagnose']=lambda root:([], '')
        def clients(env):
            called.append('clients'); raise RuntimeError('PRIVATE_RAW_KEY_ERROR')
        fake=SimpleNamespace(private_clients=clients)
        env={'HASLA_QWQ_GPU_EVAL_JOB':json.dumps({'run_id':'41956885560','code_commit':'a'*40})}
        output=io.StringIO()
        with patch.dict(os.environ,env),patch.dict(n['sys'].modules,{'private_qwq_gpu_eval':fake}),patch.object(n['signal'],'signal'),patch.object(n['signal'],'alarm',create=True),patch.object(n['signal'],'SIGALRM',14,create=True),redirect_stdout(output):
            self.assertEqual(n['main'](),1)
        event=json.loads(output.getvalue())
        self.assertEqual(event,{'event':'private_qwq_gpu_bootstrap_diagnostic','status':'failed','phase':'clients','exception_type':'RuntimeError','exit_code':1})
        self.assertEqual(called,['clients']); self.assertNotIn('PRIVATE_RAW_KEY_ERROR',output.getvalue())
        for privacy in (False,None,{'entity':n['ENTITY'],'project':n['PROJECT'],'access':'PUBLIC'}):
            with self.subTest(privacy=privacy),tempfile.TemporaryDirectory() as directory:
                sdk=SimpleNamespace(init=lambda **_: self.fail('SDK init before PRIVATE proof'))
                with self.assertRaises(ValueError):
                    n['publish']({'run_id':'41956885560','code_commit':'a'*40},Path(directory),lambda env:(None,lambda _:privacy,sdk))

    def test_client_failure_is_labeled_without_starting_later_probes(self):
        n=namespace();order=[]
        n['diagnose']=lambda root:(order.append('local_probes') or [], 'local_synthetic_trace')
        with tempfile.TemporaryDirectory() as directory:
            def clients(env):
                order.append('clients')
                self.assertFalse((Path(directory)/'diagnostics.json').exists())
                raise RuntimeError('PRIVATE_RAW')
            with self.assertRaises(RuntimeError):n['publish']({'run_id':'41956885560','code_commit':'a'*40},Path(directory),clients)
        self.assertEqual(order,['clients']);self.assertEqual(n['PHASE'],'clients')

    def test_injected_provider_hf_names_removed_before_sdk_and_all_fresh_probes(self):
        n=namespace(); sdk_calls=[]; probe_calls=[]
        forbidden=set(n['HF_CREDENTIALS'])|{'RUNPOD_API_KEY','runpod_scoped_TOKEN','PREFIX_RUNPOD_key'}
        env={key:'DUMMY_PRIVATE_VALUE' for key in forbidden}
        env.update({'WANDB_API_KEY':'KEPT_WANDB_VALUE','HF_HOME':'/public/cache','RUNPOD_POD_ID':'pod-context',
                    'HASLA_QWQ_GPU_EVAL_JOB':json.dumps({'run_id':'41956885560','code_commit':'a'*40})})
        def clean(current):
            self.assertTrue(forbidden.isdisjoint(current)); self.assertEqual(current['WANDB_API_KEY'],'KEPT_WANDB_VALUE')
            self.assertEqual(current['HF_HOME'],'/public/cache'); self.assertEqual(current['RUNPOD_POD_ID'],'pod-context')
        def clients(current): clean(current); sdk_calls.append(True)
        def runner(command,**kwargs):
            clean(os.environ); probe_calls.append(command)
            self.assertNotIn('env',kwargs)  # subprocess inherits the sanitized CURRENT environment.
            stage=Path(command[3]).stem; versions=dict.fromkeys(n['CORE'],'1.0')
            data={'before':versions,'after':versions} if stage=='core_compare' else {'versions':versions,'wandb':'0.31.0'} if stage=='module_import' else {'available':True,'count':1,'name':'NVIDIA A40','compiled_cuda':'12.8'}
            Path(command[3]).write_text(json.dumps(data)); return SimpleNamespace(returncode=0)
        def publish(job,root,client):
            client(os.environ); stages,_=n['diagnose'](root,runner)
            self.assertEqual(len(stages),3); self.assertTrue(all(row['status']=='passed' for row in stages)); return 0
        n['publish']=publish; fake=SimpleNamespace(private_clients=clients); output=io.StringIO()
        with patch.dict(os.environ,env,clear=True),patch.dict(n['sys'].modules,{'private_qwq_gpu_eval':fake}),patch.object(n['signal'],'signal'),patch.object(n['signal'],'alarm',create=True),patch.object(n['signal'],'SIGALRM',14,create=True),redirect_stdout(output):
            self.assertEqual(n['main'](),0); clean(os.environ)
        self.assertEqual(len(sdk_calls),1); self.assertEqual(len(probe_calls),3); self.assertEqual(output.getvalue(),'')
        class NamesOnly(dict):
            def __getitem__(self,key): raise AssertionError('credential value read')
        names=NamesOnly({'RUNPOD_API_KEY':object(),'WANDB_API_KEY':object()})
        self.assertEqual(n['sanitize_environment'](names),1); self.assertEqual(set(names),{'WANDB_API_KEY'})


if __name__=='__main__': unittest.main()

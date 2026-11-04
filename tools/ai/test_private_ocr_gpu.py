"""Offline public-page GPU probe fixtures. No SDK/API/model/GPU execution."""
import contextlib
from decimal import Decimal
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import private_ocr_gpu_run as parent
import private_ocr_gpu_worker as worker
import private_ocr_probe as helper

SENSITIVE='SYNTHETIC_PRIVATE_DATA credential_placeholder https://invalid.example/?token=synthetic'
REAL_FUNDING=parent.funding_check
REAL_ASSETS=parent.verify_public_assets
REAL_RESULT=parent.read_result
REAL_DELETE=parent.delete_exact


def successful():
    value=worker.result('succeeded','complete')
    value.update(pages=1,blocks=2,characters=200,block_types={'text':1,'formula':1},layout_stage_present=True,
                 gpu_backend_verified=True,setup_seconds=2,initialization_seconds=1,prediction_seconds=2,total_seconds=5)
    return value


class Clock:
    def __init__(self):self.value=100.0
    def __call__(self):return self.value
    def sleep(self,seconds):self.value+=seconds


class ParentTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        temporary=tempfile.TemporaryDirectory(prefix='hasla-ocr-gpu-unit-');self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.clock=Clock();self.calls=[];self.pods={};self.deleted=[]
        for name in ('request','get','post','head','delete'):
            patch.object(parent.cloud.requests,name,side_effect=AssertionError('network forbidden')).start()
        self.manifest={'version':1,'kind':worker.KIND,'budget_krw':100000,'authorized_budget_krw':100000,
            'prior_closed_krw':10344,'active_reservation_holds_krw':0,'known_training_run_ids':['41826983533'],
            'active_training_runs':[],'runtime_seconds':1800,'gpu_ids':[parent.GPU_IDS[2]],'image_digest':'sha256:'+'d'*64,
            'run_script_sha256':hashlib.sha256(Path(parent.__file__).read_bytes()).hexdigest(),
            'worker_script_sha256':hashlib.sha256(Path(worker.__file__).read_bytes()).hexdigest(),
            'helper_script_sha256':hashlib.sha256(Path(helper.__file__).read_bytes()).hexdigest()}
        self.env={'RUNPOD_API_KEY':'SYNTHETIC_RUNPOD','WANDB_API_KEY':'SYNTHETIC_WANDB','GITHUB_RUN_ID':'123456',
                  'GITHUB_SHA':'a'*40,'RUNNER_TEMP':str(self.root),'HASLA_OCR_GPU_MANIFEST':json.dumps(self.manifest)}
        patch.object(parent.privacy,'existing_private_project',return_value='fixture').start()
        patch.object(parent.privacy,'assert_private',return_value=None).start()
        patch.object(parent,'summary_run',return_value=None).start()
        patch.object(parent,'funding_check',return_value={'funding_check':'available','sufficient_for_full_active_and_probe_upper':True}).start()
        patch.object(parent,'verify_public_assets',return_value=None).start()
        patch.object(parent,'read_result',return_value=successful()).start()
        patch.object(parent.cloud,'runpod',side_effect=self.api).start()
        patch.object(parent,'delete_exact',side_effect=self.delete).start()

    def api(self,method,path,**options):
        self.calls.append((method,path,options))
        if method=='GET' and path.startswith('/catalog/'):
            return {'gpus':[{'id':parent.GPU_IDS[2],'price':{'secure':3},'availability':'HIGH'}]}
        if method=='GET' and path=='/pods':return list(self.pods.values())
        if method=='POST' and path=='/pods':
            body=options['json'];pod={'id':'fixture-pod','name':body['name'],'costPerHr':3,'containerDiskInGb':200,
                                    'volumeInGb':0,'gpu':body['gpu'],'desiredStatus':'RUNNING'}
            self.pods[pod['id']]=pod;return pod
        if method=='GET' and path.startswith('/pods/'):return self.pods[path.rsplit('/',1)[-1]]
        self.fail('unexpected API route')

    def delete(self,pod,name,deadline,clock):
        self.assertEqual(pod['name'],name);self.deleted.append(pod['id']);self.pods.pop(pod['id'],None);return True

    def execute(self,**options):return parent.execute(self.env,clock=self.clock,sleep=self.clock.sleep,**options)

    def test_current_closed_budget_is_generic_and_only_incremental_is_charged(self):
        event=self.execute()
        self.assertEqual(event['status'],'succeeded');self.assertTrue(event['deletion_confirmed'])
        self.assertEqual(event['prior_closed_krw'],'10344');self.assertEqual(event['active_reservation_holds_krw'],'0')
        self.assertEqual(event['guard_prior_upper_krw'],'10344');self.assertEqual(event['probe_reserved_upper_krw'],'4944')
        self.assertTrue(event['prior_guard_is_not_new_spend']);self.assertEqual(event['incremental_probe_cost_upper_krw'],'0')
        self.assertNotIn('weights_updated',json.dumps(event));self.assertEqual(self.deleted,['fixture-pod'])

    def test_preflight_never_creates_and_cleanup_needs_only_runpod_key(self):
        event=self.execute(preflight=True)
        self.assertEqual(event['status'],'preflight_ready');self.assertFalse(event['gpu_creation_attempted'])
        self.assertFalse(any(method=='POST' for method,_,_ in self.calls))
        cleanup=parent.cleanup_only({key:self.env[key] for key in ('RUNPOD_API_KEY','GITHUB_RUN_ID','RUNNER_TEMP')},clock=self.clock,sleep=self.clock.sleep)
        self.assertEqual(cleanup['status'],'not_created');self.assertIsNone(cleanup['deletion_confirmed'])

    def test_funding_below_full_bound_blocks_before_paid_post(self):
        parent.funding_check.return_value={'funding_check':'available','sufficient_for_full_active_and_probe_upper':False}
        event=self.execute();self.assertEqual(event['status'],'blocked');self.assertFalse(event['gpu_creation_attempted'])
        self.assertFalse(any(method=='POST' for method,_,_ in self.calls))

    def test_zero_holds_require_all_training_pods_absent(self):
        self.pods['old']={'id':'old','name':parent.cloud.PREFIX+'41826983533-solver','desiredStatus':'RUNNING'}
        with self.assertRaises(parent.ProbeRunError):self.execute(preflight=True)
        self.assertEqual(self.deleted,[]);self.assertFalse(any(method=='POST' for method,_,_ in self.calls))

    def test_active_holds_minimum_and_full_funding_boundary_without_balance_output(self):
        self.manifest.update(prior_closed_krw=7653,active_reservation_holds_krw=42327,
                             active_training_runs=[{'run_id':'41826983533','roles':['solver']}])
        ledger,quote=parent.budget(self.manifest,parent.PREFIX+'123',0)
        self.assertEqual(ledger.prior_spend_krw,Decimal(49980));self.assertEqual(ledger.runs[-1].plan.reserved_krw,Decimal(4944))
        required=quote.hourly_usd_upper*Decimal(1800+120+14400+120)/3600
        event=REAL_FUNDING(self.manifest,quote,query=lambda _:{'myself':{'clientBalance':str(required),'underBalance':False}})
        self.assertTrue(event['sufficient_for_full_active_and_probe_upper'])
        self.assertNotIn(str(required),json.dumps(event));self.assertNotIn('clientBalance',json.dumps(event))
        event=REAL_FUNDING(self.manifest,quote,query=lambda _:{'myself':{'clientBalance':str(required-Decimal('0.00001')),'underBalance':False}})
        self.assertFalse(event['sufficient_for_full_active_and_probe_upper'])
        self.manifest['active_reservation_holds_krw']=0
        with self.assertRaisesRegex(parent.ProbeRunError,'active_reservation'):parent.budget(self.manifest,'fixture',0)

    def test_invalid_balance_never_creates_false_sufficiency(self):
        _,quote=parent.budget(self.manifest,'fixture',0)
        for value in (True,None,'NaN','Infinity','-1',SENSITIVE):
            event=REAL_FUNDING(self.manifest,quote,query=lambda _,v=value:{'myself':{'clientBalance':v,'underBalance':False}})
            self.assertIsNone(event['sufficient_for_full_active_and_probe_upper']);self.assertNotIn(SENSITIVE,json.dumps(event))

    def test_unknown_creation_absence_never_counts_as_deleted_or_settled(self):
        original=self.api
        def api(method,path,**options):
            if method=='POST':self.calls.append((method,path,options));raise RuntimeError(SENSITIVE)
            return original(method,path,**options)
        parent.cloud.runpod.side_effect=api
        event=self.execute();self.assertFalse(event['deletion_confirmed']);self.assertTrue(event['probe_reservation_retained'])
        self.assertIsNone(event['incremental_probe_cost_upper_krw']);self.assertEqual(event['creation_outcome'],'unresolved')
        self.assertNotIn(SENSITIVE,json.dumps(event));self.assertEqual(sum(method=='POST' for method,_,_ in self.calls),1)
        event=parent.cleanup_only({key:self.env[key] for key in ('RUNPOD_API_KEY','GITHUB_RUN_ID','RUNNER_TEMP')},clock=self.clock,sleep=self.clock.sleep)
        self.assertFalse(event['deletion_confirmed']);self.assertEqual(event['status'],'unresolved')

    def test_lost_create_response_reconciles_only_exact_name_and_deletes_it(self):
        original=self.api
        def api(method,path,**options):
            response=original(method,path,**options)
            if method=='POST':raise RuntimeError(SENSITIVE)
            return response
        parent.cloud.runpod.side_effect=api
        event=self.execute();self.assertTrue(event['deletion_confirmed']);self.assertEqual(self.deleted,['fixture-pod'])
        self.assertFalse(event['probe_reservation_retained'])

    def test_failed_or_missing_child_result_always_deletes(self):
        parent.read_result.return_value=worker.result('failed','setup','setup_failed')
        event=self.execute();self.assertEqual(event['status'],'failed');self.assertTrue(event['deletion_confirmed'])
        self.assertEqual(event['result']['error_code'],'setup_failed')

    def test_deadline_is_bounded_and_cleanup_always_runs(self):
        parent.read_result.return_value=None
        event=self.execute();self.assertEqual(event['code'],'deadline_reached');self.assertTrue(event['deletion_confirmed'])
        self.assertLessEqual(self.clock.value,1900);self.assertEqual(self.deleted,['fixture-pod'])

    def test_post_creation_price_violation_deletes_immediately(self):
        original=self.api
        def api(method,path,**options):
            response=original(method,path,**options)
            if method=='POST':response['costPerHr']=99
            return response
        parent.cloud.runpod.side_effect=api
        event=self.execute();self.assertEqual(event['status'],'failed');self.assertTrue(event['deletion_confirmed'])

    def test_pod_env_and_command_never_contain_runpod_or_hf_credentials(self):
        command,env=parent.command_and_env(self.manifest,{**self.env,'HF_TOKEN':SENSITIVE},'fixture',parent.PREFIX+'123')
        self.assertEqual(set(env)&{'RUNPOD_API_KEY','HF_TOKEN'},set())
        self.assertEqual(env['WANDB_API_KEY'],self.env['WANDB_API_KEY'])
        for secret in (SENSITIVE,self.env['RUNPOD_API_KEY'],self.env['WANDB_API_KEY']):self.assertNotIn(secret,command)
        self.assertIn('timeout --signal=TERM --kill-after=20s 1680s',command);self.assertIn('sha256sum -c',command)
        event=self.execute();body=[x[2]['json'] for x in self.calls if x[0]=='POST'][0]
        self.assertEqual(body['disk'],200);self.assertEqual(body['gpu']['count'],1)
        self.assertEqual(body['image'],'runpod/pytorch@'+self.manifest['image_digest']);self.assertFalse(body['startSsh'])

    def test_cleanup_never_deletes_training_or_other_names(self):
        self.pods={'foreign':{'id':'foreign','name':parent.cloud.PREFIX+'123456-solver'}}
        event=parent.cleanup_only(self.env,clock=self.clock,sleep=self.clock.sleep)
        self.assertFalse(event['deletion_confirmed']);self.assertEqual(self.deleted,[])

    def test_delete_checks_provider_identity_before_any_mutation(self):
        parent.cloud.E=self.env;name=parent.PREFIX+'123456';closed=[]
        def response(status,data=None):
            return SimpleNamespace(status_code=status,json=lambda:data,close=lambda:closed.append(True))
        parent.cloud.requests.get.side_effect=lambda *_,**__:response(200,{'name':parent.cloud.PREFIX+'123456-solver'})
        self.assertFalse(REAL_DELETE({'id':'foreign','name':name},name,self.clock()+120,self.clock))
        parent.cloud.requests.delete.assert_not_called()
        parent.cloud.requests.get.side_effect=[response(200,{'name':name}),response(404)]
        parent.cloud.requests.delete.side_effect=lambda *_,**__:response(204)
        self.assertTrue(REAL_DELETE({'id':'fixture','name':name},name,self.clock()+120,self.clock))
        self.assertEqual(parent.cloud.requests.delete.call_count,1);self.assertTrue(closed)

    def test_unconfirmed_cleanup_retains_the_full_probe_reservation(self):
        parent.delete_exact.side_effect=lambda *_,**__:False
        event=self.execute()
        self.assertFalse(event['deletion_confirmed']);self.assertTrue(event['probe_reservation_retained'])
        self.assertIsNone(event['incremental_probe_cost_upper_krw']);self.assertEqual(event['code'],'cleanup_unconfirmed')

    def test_public_code_and_registry_digest_are_verified_without_redirects(self):
        calls=[]
        def response(status,content=b'',data=None,headers=None):
            return SimpleNamespace(status_code=status,content=content,json=lambda:data,headers=headers or {},close=lambda:None)
        def get(url,**options):
            calls.append((url,options))
            if 'private_ocr_gpu_worker.py' in url:return response(200,Path(worker.__file__).read_bytes())
            if 'private_ocr_probe.py' in url:return response(200,Path(helper.__file__).read_bytes())
            return response(200,data={'token':'SYNTHETIC_PUBLIC_REGISTRY_TOKEN'})
        parent.cloud.requests.get.side_effect=get
        parent.cloud.requests.head.side_effect=lambda *_,**__:response(200,headers={'Docker-Content-Digest':self.manifest['image_digest']})
        REAL_ASSETS(self.manifest,'a'*40)
        self.assertFalse(calls[0][1]['allow_redirects']);self.assertFalse(parent.cloud.requests.head.call_args.kwargs['allow_redirects'])
        parent.cloud.requests.head.side_effect=lambda *_,**__:response(200,headers={'Docker-Content-Digest':'sha256:'+'0'*64})
        with self.assertRaisesRegex(parent.ProbeRunError,'image_unverified'):REAL_ASSETS(self.manifest,'a'*40)

    def test_result_scalar_requires_matching_code_pins_and_ignores_native_terminal_state(self):
        summary={'private_ocr_gpu_result_json':json.dumps(successful()),
                 'private_ocr_gpu_worker_sha256':self.manifest['worker_script_sha256'],
                 'private_ocr_gpu_helper_sha256':self.manifest['helper_script_sha256']}
        parent.summary_run.return_value={'state':'finished','summaryMetrics':json.dumps(summary)}
        self.assertEqual(REAL_RESULT('fixture','run',self.manifest)['status'],'succeeded')
        summary['private_ocr_gpu_worker_sha256']='0'*64
        parent.summary_run.return_value={'state':'finished','summaryMetrics':json.dumps(summary)}
        self.assertIsNone(REAL_RESULT('fixture','run',self.manifest))
        for state in ('crashed','failed','finished','killed'):
            parent.summary_run.return_value={'state':state,'summaryMetrics':'{}'}
            self.assertIsNone(REAL_RESULT('fixture','run',self.manifest))
        parent.summary_run.side_effect=RuntimeError(SENSITIVE)
        self.assertIsNone(REAL_RESULT('fixture','run',self.manifest))

    def test_false_native_crash_while_gpu_runs_waits_for_explicit_result(self):
        calls=[]
        def read(entity,name,manifest,timeout=10):
            calls.append(True)
            if len(calls)<3:
                parent.summary_run.return_value={'state':'crashed','summaryMetrics':'{}'}
            else:
                summary={'private_ocr_gpu_result_json':json.dumps(successful()),
                         'private_ocr_gpu_worker_sha256':self.manifest['worker_script_sha256'],
                         'private_ocr_gpu_helper_sha256':self.manifest['helper_script_sha256']}
                parent.summary_run.return_value={'state':'finished','summaryMetrics':json.dumps(summary)}
            return REAL_RESULT(entity,name,manifest,timeout)
        parent.read_result.side_effect=read
        event=self.execute()
        self.assertEqual(event['status'],'succeeded');self.assertEqual(len(calls),3)
        self.assertEqual(self.clock.value,120);self.assertEqual(self.deleted,['fixture-pod'])

    def test_manifest_rejects_unpinned_or_over_budget_configuration(self):
        for key,value in [('runtime_seconds',3600),('gpu_ids',[parent.cloud.GPU_IDS[-1]]),('image_digest','latest'),
                          ('known_training_run_ids',[]),('version',True),('worker_script_sha256','bad')]:
            manifest={**self.manifest,key:value};env={**self.env,'HASLA_OCR_GPU_MANIFEST':json.dumps(manifest)}
            with self.subTest(key=key),self.assertRaises(parent.ProbeRunError):parent.load_manifest(env)
        with self.assertRaises(parent.ProbeRunError):parent.budget({**self.manifest,'prior_closed_krw':99000},'fixture',0)

    def test_main_never_logs_arbitrary_exception_or_claims_training(self):
        stream=io.StringIO()
        with patch.object(parent,'execute',side_effect=RuntimeError(SENSITIVE)),contextlib.redirect_stdout(stream):
            self.assertEqual(parent.main([]),1)
        self.assertNotIn(SENSITIVE,stream.getvalue());self.assertNotIn('weights_updated',stream.getvalue())


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        patch.object(worker.urllib.request,'urlopen',side_effect=AssertionError('network forbidden')).start()
        self.clock=Clock();self.observed=SimpleNamespace(summary={},finished=False,initialized=False,heartbeats=[],alive=threading.Event())
        self.env={'RUN':worker.PREFIX+'123','WANDB_API_KEY':'SYNTHETIC_WANDB','WANDB_ENTITY':'fixture','WANDB_PROJECT':worker.PROJECT,
                  'HASLA_OCR_GPU_WORKER_SHA256':hashlib.sha256(Path(worker.__file__).read_bytes()).hexdigest(),
                  'HASLA_OCR_GPU_HELPER_SHA256':hashlib.sha256(Path(helper.__file__).read_bytes()).hexdigest()}

    def sdk(self):
        observed=self.observed
        class Run:
            summary=observed.summary
            def log(self,metrics,commit):
                assert commit is True
                assert not observed.finished
                observed.heartbeats.append(metrics)
                if len(observed.heartbeats)>=2:observed.alive.set()
            def finish(self,exit_code):observed.finished=True;observed.exit_code=exit_code
        def init(**options):
            self.assertEqual(options['resume'],'never');self.assertEqual(options['project'],worker.PROJECT)
            observed.initialized=True;print(SENSITIVE);return Run()
        return SimpleNamespace(Settings=lambda **options:options,init=init)

    def runner(self,command,**options):
        self.assertEqual(options['stdout'],worker.subprocess.DEVNULL);self.assertEqual(options['stderr'],worker.subprocess.DEVNULL)
        self.assertNotIn('WANDB_API_KEY',options['env']);self.assertNotIn('RUNPOD_API_KEY',options['env'])
        if '--infer' in command:
            Path(command[-1]).write_text(json.dumps(successful()),encoding='utf-8');self.clock.sleep(3)
        else:self.clock.sleep(1)
        return SimpleNamespace(returncode=0)

    def test_worker_success_publishes_only_private_fixed_scalar_and_code_pins(self):
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream):
            value=worker.run_worker(self.env,sdk=self.sdk(),private_check=lambda _: 'fixture',runner=self.runner,clock=self.clock)
        self.assertEqual(stream.getvalue(),'');self.assertEqual(value['status'],'succeeded');self.assertTrue(self.observed.finished)
        saved=json.loads(self.observed.summary['private_ocr_gpu_result_json'])
        self.assertEqual(saved['kind'],worker.KIND);self.assertEqual(saved['pages'],1)
        self.assertEqual(self.observed.summary['private_ocr_gpu_worker_sha256'],self.env['HASLA_OCR_GPU_WORKER_SHA256'])
        self.assertTrue(self.observed.heartbeats)
        self.assertTrue(all(set(x)=={'public_gpu_ocr_alive','public_gpu_ocr_elapsed_seconds','public_gpu_ocr_stage'} for x in self.observed.heartbeats))
        self.assertNotIn(SENSITIVE,json.dumps(self.observed.summary));self.assertNotIn('weights_updated',json.dumps(saved))

    def test_unverified_project_prevents_sdk_and_dependency_install(self):
        def private(_):raise worker.ProbeError('private_project_unverified')
        value=worker.run_worker(self.env,sdk=self.sdk(),private_check=private,runner=lambda *_,**__:self.fail('setup before privacy'))
        self.assertEqual(value['status'],'failed');self.assertFalse(self.observed.initialized);self.assertEqual(self.observed.summary,{})

    def test_setup_failure_publishes_fixed_failure_without_raw_logs(self):
        def runner(*args,**options):print(SENSITIVE);return SimpleNamespace(returncode=1)
        value=worker.run_worker(self.env,sdk=self.sdk(),private_check=lambda _: 'fixture',runner=runner)
        self.assertEqual(value['error_code'],'setup_failed');self.assertTrue(self.observed.finished)
        self.assertNotIn(SENSITIVE,json.dumps(self.observed.summary))

    def test_committed_heartbeat_continues_while_setup_child_is_running(self):
        waited=[]
        def runner(command,**options):
            if not waited:
                waited.append(True)
                self.assertTrue(self.observed.alive.wait(timeout=1))
                self.assertFalse(self.observed.finished)
            return self.runner(command,**options)
        with patch.object(worker,'HEARTBEAT_SECONDS',0.005):
            value=worker.run_worker(self.env,sdk=self.sdk(),private_check=lambda _:'fixture',runner=runner,clock=self.clock)
        self.assertEqual(value['status'],'succeeded');self.assertGreaterEqual(len(self.observed.heartbeats),2)
        self.assertTrue(self.observed.finished)

    def test_privacy_change_before_publication_does_not_publish_result(self):
        checks=[]
        def private(_):
            checks.append(True)
            if len(checks)>=3:raise worker.ProbeError('private_project_unverified')
            return 'fixture'
        value=worker.run_worker(self.env,sdk=self.sdk(),private_check=private,runner=self.runner,clock=self.clock)
        self.assertEqual(value['status'],'failed');self.assertEqual(self.observed.summary,{})
        self.assertTrue(self.observed.finished)

    def test_child_credentials_or_code_mismatch_are_rejected_before_sdk(self):
        for changes in ({'HF_TOKEN':'private'},{'RUNPOD_API_KEY':'private'},{'HASLA_OCR_GPU_WORKER_SHA256':'0'*64}):
            value=worker.run_worker({**self.env,**changes},sdk=self.sdk(),private_check=lambda _:self.fail('network before config'))
            self.assertEqual(value['status'],'failed');self.assertFalse(self.observed.initialized)

    def test_public_full_pipeline_gpu_zero_only_and_no_recognized_text_in_result(self):
        seen={}
        page={'model_settings':{'use_layout_detection':True},'layout_det_res':{},
              'parsing_res_list':[{'block_label':'text','block_content':SENSITIVE}]}
        def factory(**options):
            seen.update(options)
            def predict(**arguments):self.assertEqual(arguments,{'input':worker.DEMO_URL});return [page]
            return SimpleNamespace(predict=predict)
        value=worker.infer_once(helper,dependency_check=lambda:None,factory=factory)
        self.assertEqual(value['status'],'succeeded');self.assertEqual(seen['device'],'gpu:0')
        self.assertTrue(seen['use_layout_detection']);self.assertEqual(seen['vl_rec_backend'],'native')
        self.assertNotIn(SENSITIVE,json.dumps(value))

    def test_dependency_versions_gpu_evidence_and_cpu_fallback_rejected(self):
        def version(package):
            if package=='paddlepaddle':raise importlib.metadata.PackageNotFoundError(package)
            return worker.PACKAGES[package]
        paddle=SimpleNamespace(is_compiled_with_cuda=lambda:True,device=SimpleNamespace(cuda=SimpleNamespace(device_count=lambda:1)),
                               set_device=lambda _:None,get_device=lambda:'gpu:0')
        worker.dependencies(version,paddle)
        paddle.get_device=lambda:'cpu'
        with self.assertRaisesRegex(worker.ProbeError,'gpu_unavailable'):worker.dependencies(version,paddle)
        with self.assertRaisesRegex(worker.ProbeError,'cpu_paddle_installed'):worker.dependencies(lambda _:'3.2.1',paddle)

    def test_invalid_and_secret_result_fields_are_never_forwarded(self):
        clean=worker.clean_result({**successful(),'raw_text':SENSITIVE,'adapter':SENSITIVE,'weights_updated':True})
        self.assertNotIn(SENSITIVE,json.dumps(clean));self.assertNotIn('weights_updated',clean)
        for changes in ({'pages':2},{'device':'cpu'},{'prediction_seconds':float('nan')},{'gpu_backend_verified':False},
                        {'private_inputs_read':1},{'block_types':{SENSITIVE:2}}):
            with self.subTest(fields=list(changes)),self.assertRaises(worker.ProbeError):worker.clean_result({**successful(),**changes})


if __name__=='__main__':unittest.main()

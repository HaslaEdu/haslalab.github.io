"""Offline money/deadline/privacy/cleanup fixtures; no real API/GPU/install."""
import ast
import base64
from decimal import Decimal
import hashlib
import io
import contextlib
import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import zlib
from unittest.mock import patch

import private_ocr_batch_run as parent

REAL_FUNDING=parent.funding_check
REAL_READ=parent.read_result
REAL_VERIFY_SOURCE=parent.verify_source
PRIVATE='SYNTHETIC_PRIVATE_SECRET https://invalid.example/?key=synthetic'


class Clock:
    def __init__(self):self.t=0.0
    def __call__(self):return self.t
    def sleep(self,seconds):self.t+=seconds


class ParentTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        temporary=tempfile.TemporaryDirectory(prefix='hasla-batch-parent-unit-');self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.clock=Clock();self.calls=[];self.pods={};self.deleted=[]
        patch.object(parent,'CALIBRATION_COUNT',2).start()
        for name in ('get','post','head','delete','request'):
            patch.object(parent.cloud.requests,name,side_effect=AssertionError('network forbidden')).start()
        self.job={'version':1,'mode':'calibration','source_artifact':'fixture/'+parent.PROJECT+'/sources:v0','source_manifest_sha256':'b'*64,
            'expected_source_count':2,'expected_pending_pages':4,'page_keys':[{'source_index':0,'page_number':1},{'source_index':1,'page_number':1}],
            'runtime_seconds':1800,'per_page_seconds':120,'checkpoint_pages':2,'bulk_authorized':False,'calibration_checkpoint':None,
            'learning_exclusions':[{'source_index':1,'page_number':1,'reason':'cover_page'}]}
        self.manifest={'version':1,'kind':parent.KIND,'budget_krw':100000,'authorized_budget_krw':100000,'prior_closed_krw':10344,
            'active_reservation_holds_krw':0,'other_reservation_holds_krw':4944,'known_training_run_ids':['41826983533'],
            'active_training_runs':[],'total_runtime_seconds':3600,'gpu_usd_per_hour_upper':'1.25','gpu_ids':['NVIDIA L40S','NVIDIA RTX A6000'],
            'image_digest':'sha256:'+'d'*64,'run_script_sha256':hashlib.sha256(Path(parent.__file__).read_bytes()).hexdigest(),
            'worker_script_sha256':hashlib.sha256(Path(parent.batch.__file__).read_bytes()).hexdigest(),
            'job':self.job,'job_sha256':hashlib.sha256(parent.canonical(self.job)).hexdigest()}
        self.env={'RUNPOD_API_KEY':'SYNTHETIC_PROVIDER_KEY','WANDB_API_KEY':'SYNTHETIC_WANDB_KEY','GITHUB_SHA':'a'*40,
            'GITHUB_RUN_ID':'123456','RUNNER_TEMP':str(self.root),'HASLA_OCR_BATCH_MANIFEST':json.dumps(self.manifest)}
        patch.object(parent.privacy,'existing_private_project',return_value='fixture').start()
        patch.object(parent.privacy,'assert_private',return_value=None).start()
        patch.object(parent.common,'summary_run',return_value=None).start()
        patch.object(parent,'funding_check',return_value={'funding_check':'available','sufficient_for_all_reserved_upper':True}).start()
        patch.object(parent,'verify_assets',return_value=None).start();patch.object(parent,'verify_source',return_value=None).start()
        patch.object(parent.cloud,'runpod',side_effect=self.api).start()
        patch.object(parent.common,'delete_exact',side_effect=self.delete).start()
        patch.object(parent,'read_result',return_value=self.result()).start()

    def result(self,status='calibration_complete'):
        name=parent.PREFIX+'123456'
        return {'kind':parent.batch.KIND,'status':status,'terminal':True,'mode':'calibration','machine_ocr':True,
            'human_reviewed':False,'scientifically_verified':False,'training_eligible':False,'selected_pages':2,'processed_pages':2,
            'extracted_pages':2,'pending_attempted_pages':0,'unprocessed_selected_pages':0,'source_pdfs_byte_verified':2,
            'source_aliases_inventory_checked':2,'next_cursor':2,'total_source_pending_pages':4,
            'original_selected_pdf_bytes_unchanged':True,'selection_sha256':hashlib.sha256(parent.canonical(self.job['page_keys'])).hexdigest(),
            'checkpoints':[{'artifact':'fixture/'+parent.PROJECT+'/'+name+'-checkpoint-000000:v0','manifest_sha256':'c'*64,'next_cursor':2}]}

    def api(self,method,path,**options):
        self.calls.append((method,path,options))
        if method=='GET' and path.startswith('/catalog/'):
            return {'gpus':[{'id':'NVIDIA L40S','price':{'secure':1.09},'availability':'HIGH'}]}
        if method=='GET' and path=='/pods':return list(self.pods.values())
        if method=='POST' and path=='/pods':
            body=options['json'];pod={'id':'ocr-fixture','name':body['name'],'gpu':body['gpu'],'costPerHr':1.09,
                'containerDiskInGb':200,'volumeInGb':0,'desiredStatus':'RUNNING'}
            self.pods[pod['id']]=pod;return pod
        if method=='GET' and path.startswith('/pods/'):return self.pods[path.rsplit('/',1)[-1]]
        self.fail('unexpected API route')

    def delete(self,pod,name,deadline,clock):
        self.assertEqual(pod['name'],name);self.deleted.append(pod['id']);self.pods.pop(pod['id'],None);return True

    def execute(self,**options):return parent.execute(self.env,clock=self.clock,wall_clock=lambda:1000000,sleep=self.clock.sleep,**options)

    def test_inexpensive_policy_leaves_training_gpu_allowlist_unchanged(self):
        original=tuple(parent.cloud.GPU_IDS);event=self.execute()
        self.assertEqual(event['status'],'succeeded');self.assertTrue(event['deletion_confirmed'])
        body=[o['json'] for method,_,o in self.calls if method=='POST'][0]
        self.assertEqual(body['gpu']['id'],'NVIDIA L40S');self.assertEqual(body['gpu']['count'],1)
        self.assertEqual(body['disk'],200);self.assertEqual(tuple(parent.cloud.GPU_IDS),original)
        self.assertNotIn('NVIDIA L40S',original)

    def test_total_cost_cap_includes_cleanup_and_only_incremental_is_new_spend(self):
        ledger,quote=parent.budget(self.manifest,'fixture',0);plan=ledger.runs[-1].plan
        self.assertEqual(plan.run_seconds,3480);self.assertEqual(plan.cleanup_grace_seconds,120)
        self.assertEqual(plan.reserved_krw,Decimal(2944));self.assertEqual(plan.billing_deadline_monotonic,Decimal(3600))
        event=self.execute();self.assertEqual(event['guard_prior_upper_krw'],'15288')
        self.assertEqual(event['other_reservation_holds_krw'],'4944');self.assertEqual(event['incremental_ocr_cost_upper_krw'],'0')
        self.assertTrue(event['prior_guard_is_not_new_spend'])

    def test_generic_prior_and_active_main_holds_cannot_be_understated(self):
        value={**self.manifest,'active_training_runs':[{'run_id':'41826983533','roles':['solver']}],'active_reservation_holds_krw':37383}
        ledger,_=parent.budget(value,'fixture',0);self.assertEqual(ledger.prior_spend_krw,Decimal(52671))
        with self.assertRaisesRegex(parent.RunError,'active_reservation'):
            parent.budget({**value,'active_reservation_holds_krw':0},'fixture',0)
        with self.assertRaises(parent.RunError):parent.budget({**value,'prior_closed_krw':99000},'fixture',0)

    def test_funding_compares_full_main_cap_new_hour_and_unsettled_other_hold_privately(self):
        value={**self.manifest,'active_training_runs':[{'run_id':'41826983533','roles':['solver']}],'active_reservation_holds_krw':37383}
        _,quote=parent.budget(value,'fixture',0)
        training=parent.PodQuote(gpu_usd_per_hour_upper=4,container_disk_gb=200,volume_disk_gb=0)
        required=training.hourly_usd_upper*Decimal(14520)/3600+quote.hourly_usd_upper+Decimal(4944)/2300
        for balance,expected in [(required,True),(required-Decimal('0.0001'),False)]:
            event=REAL_FUNDING(value,quote,query=lambda _:{'myself':{'clientBalance':str(balance),'underBalance':False}})
            self.assertEqual(event['sufficient_for_all_reserved_upper'],expected)
            self.assertNotIn(str(required),json.dumps(event));self.assertNotIn('clientBalance',json.dumps(event))

    def test_preflight_creates_nothing_and_source_check_is_manifest_only(self):
        event=self.execute(preflight=True);self.assertEqual(event['status'],'preflight_ready')
        self.assertEqual(event['pdfs_downloaded'],0);self.assertFalse(any(method=='POST' for method,_,_ in self.calls))
        parent.verify_source.assert_called_once_with(self.job,self.env)
        with patch.object(parent.batch,'open_source',return_value=(None,None,{(0,1),(1,1)},'b'*64)) as opened:
            REAL_VERIFY_SOURCE(self.job,self.env)
        self.assertEqual(opened.call_args.kwargs['expected_hash'],self.job['source_manifest_sha256'])

    def test_preflight_full_manifest_hash_changes_when_accounting_changes_with_same_job(self):
        first=self.execute(preflight=True)
        self.assertEqual(first['manifest_sha256'],hashlib.sha256(parent.canonical(self.manifest)).hexdigest())
        updated={**self.manifest,'prior_closed_krw':self.manifest['prior_closed_krw']+1}
        self.env['HASLA_OCR_BATCH_MANIFEST']=json.dumps(updated)
        second=self.execute(preflight=True)
        self.assertEqual(first['job_sha256'],second['job_sha256'])
        self.assertNotEqual(first['manifest_sha256'],second['manifest_sha256'])
        self.assertFalse(any(method=='POST' for method,_,_ in self.calls))

    def test_compact_bootstrap_is_byte_identical_and_reduces_command_size(self):
        tree=ast.parse(parent.bootstrap_loader())
        encoded=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Constant)
                     and isinstance(n.value,str) and len(n.value)>100)
        self.assertEqual(zlib.decompress(base64.b64decode(encoded)),parent.BOOTSTRAP.encode())
        command,_=parent.command_and_env(self.manifest,self.env,'fixture',parent.PREFIX+'123456',1003480)
        self.assertLess(len(command.encode()),5000)

    def test_creation_http_diagnostic_never_contains_upstream_payload_and_hold_remains(self):
        def failure(method,path,**options):
            if method=='POST':
                parent.cloud.safe_event('runpod_api_error',method='POST',http_status=400,category='gpu_capacity',provider_detail=PRIVATE)
                raise RuntimeError('RunPod POST status 400')
            return self.api(method,path,**options)
        parent.cloud.runpod.side_effect=failure
        event=self.execute()
        self.assertEqual(event['creation_diagnostic'],{'http_status':400,'category':'gpu_capacity'})
        self.assertTrue(event['reservation_retained']);self.assertIsNone(event['incremental_ocr_cost_upper_krw'])
        self.assertNotIn(PRIVATE,json.dumps(event))

    def test_manifest_preflight_passes_only_wandb_credentials_to_strict_source_reader(self):
        observed=[]
        def opened(reference,env,*args,**kwargs):
            parent.batch.credentials(env,'fixture');observed.append(env)
            return None,None,{(0,1),(1,1)},'b'*64
        with patch.object(parent.batch,'open_source',side_effect=opened):
            REAL_VERIFY_SOURCE(self.job,{**self.env,'HF_API_KEY':'SYNTHETIC_MODEL_KEY'})
        self.assertEqual(set(observed[0]),{'WANDB_API_KEY'})

    def test_active_training_adjusted_rate_cannot_exceed_its_existing_hold_ceiling(self):
        manifest={**self.manifest,'active_training_runs':[{'run_id':'41826983533','roles':['solver']}],
                  'active_reservation_holds_krw':37383}
        pod={'id':'main-training','name':parent.cloud.PREFIX+'41826983533-solver','desiredStatus':'RUNNING',
             'gpu':{'id':parent.cloud.GPU_IDS[0],'count':1},'costPerHr':'3.99','adjustedCostPerHr':'8',
             'containerDiskInGb':200,'volumeInGb':0}
        with self.assertRaisesRegex(parent.RunError,'active_reservation_unverified'):
            parent.check_inventory(manifest,[pod],parent.PREFIX+'123456')

    def test_old_public_probe_or_batch_blocks_creation_and_is_not_deleted(self):
        for name in (parent.common.PREFIX+'999',parent.PREFIX+'999'):
            self.pods={'other':{'id':'other','name':name}}
            with self.subTest(name=name),self.assertRaisesRegex(parent.RunError,'old_ocr_pod'):
                self.execute(preflight=True)
            self.assertEqual(self.deleted,[])
        self.assertFalse(any(method=='POST' for method,_,_ in self.calls))

    def test_setup_clips_only_worker_runtime_to_actual_remaining_budget(self):
        tree=ast.parse(parent.BOOTSTRAP);function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='bounded_worker_job')
        scope={'math':math};exec(compile(ast.Module(body=[function],type_ignores=[]),'bootstrap-policy','exec'),scope)
        clipped=scope['bounded_worker_job'](self.job,3480,1800)
        self.assertEqual(clipped['runtime_seconds'],1650)
        self.assertEqual({k:v for k,v in clipped.items() if k!='runtime_seconds'},{k:v for k,v in self.job.items() if k!='runtime_seconds'})
        self.assertEqual(self.job['runtime_seconds'],1800)
        with self.assertRaisesRegex(RuntimeError,'setup_deadline'):scope['bounded_worker_job'](self.job,3480,3000)

    def test_child_environment_has_no_provider_or_model_keys_and_bootstrap_is_hard_bounded(self):
        command,env=parent.command_and_env(self.manifest,{**self.env,'HF_TOKEN':PRIVATE},'fixture',parent.PREFIX+'123456',1003480)
        self.assertFalse(set(env)&{'RUNPOD_API_KEY','HF_TOKEN','GITHUB_TOKEN'})
        self.assertEqual(env['WANDB_API_KEY'],self.env['WANDB_API_KEY']);self.assertEqual(env['HASLA_OCR_BATCH_JOB_SHA256'],self.manifest['job_sha256'])
        for secret in (PRIVATE,self.env['WANDB_API_KEY'],self.env['RUNPOD_API_KEY']):self.assertNotIn(secret,command)
        self.assertIn('--system-site-packages',command);self.assertIn('3470s bash',command)
        self.assertIn('cpu_paddle_installed',parent.BOOTSTRAP);self.assertIn('commit=True',parent.BOOTSTRAP)

    def test_manifest_rejects_unreviewed_job_or_runtime_price_override(self):
        for changes in ({'gpu_usd_per_hour_upper':2},{'total_runtime_seconds':3601},{'total_runtime_seconds':2000},
                        {'gpu_ids':['NVIDIA H100 80GB HBM3']},{'job_sha256':'0'*64}):
            env={**self.env,'HASLA_OCR_BATCH_MANIFEST':json.dumps({**self.manifest,**changes})}
            with self.subTest(fields=list(changes)),self.assertRaises(parent.RunError):parent.load_manifest(env)
        changed={**self.job,'page_keys':list(reversed(self.job['page_keys']))}
        with self.assertRaisesRegex(parent.RunError,'job_pin'):
            parent.load_manifest({**self.env,'HASLA_OCR_BATCH_MANIFEST':json.dumps({**self.manifest,'job':changed})})

    def test_unknown_create_absence_does_not_release_reservation_or_claim_deletion(self):
        original=self.api
        def api(method,path,**options):
            if method=='POST':self.calls.append((method,path,options));raise RuntimeError(PRIVATE)
            return original(method,path,**options)
        parent.cloud.runpod.side_effect=api
        event=self.execute();self.assertFalse(event['deletion_confirmed']);self.assertTrue(event['reservation_retained'])
        self.assertIsNone(event['incremental_ocr_cost_upper_krw']);self.assertEqual(sum(m=='POST' for m,_,_ in self.calls),1)

    def test_native_failed_state_without_pinned_result_is_not_termination_proof(self):
        for state in ('failed','crashed','killed','finished'):
            parent.common.summary_run.return_value={'state':state,'summaryMetrics':'{}'}
            self.assertIsNone(REAL_READ('fixture',parent.PREFIX+'123456',self.manifest))

    def test_explicit_setup_failure_is_pinned_and_parent_deletes_promptly(self):
        value={'kind':parent.SETUP_KIND,'status':'failed','phase':'setup','subject':'gpu_engine_install','code':'setup_failed','worker_sha256':self.manifest['worker_script_sha256']}
        def summary(entity,name,timeout=10):
            if not any(method=='POST' for method,_,_ in self.calls):return None
            return {'state':'failed','summaryMetrics':json.dumps({'private_ocr_setup_result_json':json.dumps(value)})} if name.endswith('-setup') else None
        parent.common.summary_run.side_effect=summary
        parent.read_result.side_effect=lambda *args,**kw:REAL_READ(*args,**kw)
        event=self.execute();self.assertEqual(event['status'],'failed');self.assertTrue(event['deletion_confirmed'])
        self.assertEqual(event['result']['code'],'setup_failed');self.assertEqual(self.clock.t,0)
        self.assertEqual(event['last_observed_phase']['phase'],'setup')

    def test_price_violation_and_actual_pod_exit_both_cleanup(self):
        original=self.api
        def api(method,path,**options):
            result=original(method,path,**options)
            if method=='POST':result['costPerHr']=3
            return result
        parent.cloud.runpod.side_effect=api
        event=self.execute();self.assertTrue(event['deletion_confirmed']);self.assertEqual(event['status'],'failed')

    def test_actual_pod_exit_without_terminal_summary_cleans_up_promptly(self):
        parent.read_result.return_value=None
        original=self.api
        def api(method,path,**options):
            value=original(method,path,**options)
            if method=='GET' and path.startswith('/pods/'):value['desiredStatus']='EXITED'
            return value
        parent.cloud.runpod.side_effect=api
        event=self.execute();self.assertEqual(event['code'],'pod_stopped')
        self.assertTrue(event['deletion_confirmed']);self.assertEqual(self.clock.t,0)

    def test_deadline_includes_setup_model_and_upload_before_cleanup_margin(self):
        parent.read_result.return_value=None
        event=self.execute();self.assertEqual(event['code'],'deadline_reached');self.assertTrue(event['deletion_confirmed'])
        self.assertEqual(self.clock.t,3480);self.assertEqual(event['total_runtime_seconds'],3600)

    def test_no_foreign_training_pod_deletes_and_cleanup_requires_only_provider_key(self):
        self.pods={'training':{'id':'training','name':parent.cloud.PREFIX+'123456-solver'}}
        event=parent.cleanup_only({key:self.env[key] for key in ('RUNPOD_API_KEY','GITHUB_RUN_ID','RUNNER_TEMP')},clock=self.clock,sleep=self.clock.sleep)
        self.assertFalse(event['deletion_confirmed']);self.assertEqual(self.deleted,[])

    def test_result_sanitizer_never_forwards_ocr_text_or_unknown_checkpoint_refs(self):
        value=parent.clean_result({**self.result(),'text':PRIVATE,'blocks':[PRIVATE],'weights_updated':True},self.manifest,'fixture',parent.PREFIX+'123456')
        self.assertNotIn(PRIVATE,json.dumps(value));self.assertNotIn('weights_updated',value)
        bad={**self.result(),'checkpoints':[{'artifact':'https://invalid.example/ocr','manifest_sha256':'c'*64,'next_cursor':2}]}
        with self.assertRaises(parent.RunError):parent.clean_result(bad,self.manifest,'fixture',parent.PREFIX+'123456')

    def test_complete_result_requires_stored_checkpoint_and_consistent_counts(self):
        for changes in ({'checkpoints':[]},{'processed_pages':3},{'pending_attempted_pages':1},
                        {'unprocessed_selected_pages':1},{'worker_seconds':float('nan')}):
            with self.subTest(fields=list(changes)),self.assertRaises(parent.RunError):
                parent.clean_result({**self.result(),**changes},self.manifest,'fixture',parent.PREFIX+'123456')
        value=parent.clean_result({**self.result(),'worker_seconds':81.25},self.manifest,'fixture',parent.PREFIX+'123456')
        self.assertEqual(value['worker_seconds'],81.25)

    def test_nonprivate_project_and_unverified_source_prevent_paid_calls(self):
        parent.privacy.existing_private_project.side_effect=RuntimeError(PRIVATE)
        with self.assertRaises(RuntimeError):self.execute(preflight=True)
        self.assertFalse(any(m=='POST' for m,_,_ in self.calls))
        parent.privacy.existing_private_project.side_effect=None
        parent.verify_source.side_effect=parent.RunError('source_unverified')
        with self.assertRaises(parent.RunError):self.execute(preflight=True)
        self.assertFalse(any(m=='POST' for m,_,_ in self.calls))

    def test_main_errors_are_fixed_and_never_ocr_or_key_output(self):
        output=io.StringIO()
        with patch.object(parent,'execute',side_effect=RuntimeError(PRIVATE)),contextlib.redirect_stdout(output):self.assertEqual(parent.main([]),1)
        self.assertNotIn(PRIVATE,output.getvalue());self.assertNotIn('weights_updated',output.getvalue())

    def test_funding_below_bound_is_free_blocked_without_create(self):
        parent.funding_check.return_value={'funding_check':'available','sufficient_for_all_reserved_upper':False}
        event=self.execute();self.assertEqual(event['status'],'blocked');self.assertFalse(event['gpu_creation_attempted'])
        self.assertFalse(any(m=='POST' for m,_,_ in self.calls));self.assertEqual(self.deleted,[])

    def test_phase_heartbeat_reports_only_fixed_safe_fields_and_never_ends_run(self):
        value={'kind':parent.SETUP_KIND,'status':'running','phase':'setup','subject':'doc_parser_install',
            'heartbeat_sequence':5,'driver_elapsed_seconds':81.25,'worker_sha256':self.manifest['worker_script_sha256'],'raw_text':PRIVATE}
        parent.common.summary_run.return_value={'state':'crashed','summaryMetrics':json.dumps({'private_ocr_setup_progress_json':json.dumps(value)})}
        phase=parent.read_phase('fixture',parent.PREFIX+'123456',self.manifest)
        self.assertEqual(phase['phase'],'setup');self.assertEqual(phase['heartbeat_sequence'],5);self.assertNotIn(PRIVATE,json.dumps(phase))
        self.assertIsNone(REAL_READ('fixture',parent.PREFIX+'123456',self.manifest))
        value['subject']=PRIVATE
        parent.common.summary_run.return_value={'summaryMetrics':json.dumps({'private_ocr_setup_progress_json':json.dumps(value)})}
        self.assertIsNone(parent.read_phase('fixture','run',self.manifest))

    def test_deadline_with_no_bootstrap_report_does_not_invent_failure_phase(self):
        parent.read_result.return_value=None
        event=self.execute();self.assertEqual(event['last_observed_phase'],{'phase':'bootstrap','status':'unreported','code':'awaiting_bootstrap_heartbeat'})
        self.assertEqual(event['observed_pod_lifecycle_seconds'],3480)

    def test_cleanup_uses_original_global_billing_deadline_not_a_new_grace(self):
        observed=[]
        parent.common.delete_exact.side_effect=lambda pod,name,deadline,clock:observed.append(deadline) or self.delete(pod,name,deadline,clock)
        parent.read_result.return_value=None
        event=self.execute();self.assertTrue(event['deletion_confirmed']);self.assertEqual(observed,[3600])

    def test_base_torch_constraint_preserves_installed_cuda_build_and_rejects_injection(self):
        tree=ast.parse(parent.BOOTSTRAP);function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='torch_constraint')
        scope={};exec(compile(ast.Module(body=[function],type_ignores=[]),'bootstrap-torch-policy','exec'),scope)
        self.assertEqual(scope['torch_constraint']('2.8.0+cu128'),'torch==2.8.0+cu128\n')
        for value in ('2.8.0\nmalicious','https://invalid.example/wheel',PRIVATE):
            with self.assertRaisesRegex(RuntimeError,'base_torch_invalid'):scope['torch_constraint'](value)


if __name__=='__main__':unittest.main()

from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import tempfile
import subprocess
import unittest

import private_qwq_gpu_run as parent


class Clock:
    def __init__(self):
        self.now = 100
    def __call__(self):
        return self.now
    def sleep(self, seconds):
        self.now += seconds


class FakeServices:
    def __init__(self):
        self.calls = []
        self.pod_value = None
        self.bad_resource = {}
        self.lose_create = False
        self.unknown_create = False
        self.no_result = False
        self.delete_ok = True
        self.price = Decimal('0.59')
        self.existing = [{'id': 'keep-user-pod', 'name': 'unrelated-user-pod'}]
        self.source_error = False
        self.funding_error = False
        self.no_progress = False
        self.bootstrap_value = None
    def pods(self):
        self.calls.append('pods')
        return deepcopy(self.existing)
    def source(self):
        self.calls.append('source')
        if self.source_error:
            raise parent.EvaluationError('source_fixture_blocked')
    def private(self):
        self.calls.append('private')
    def quote(self):
        self.calls.append('quote')
        return self.price
    def funding(self, ledger):
        self.calls.append('funding')
        assert ledger.reserved_krw == 1175
        if self.funding_error:
            raise parent.EvaluationError('funding_fixture_blocked')
    def create(self, name, env, command):
        self.calls.append(('create', deepcopy(env), command))
        self.pod_value = {'id': 'new-eval-pod', 'name': name, 'gpu': {'id': 'NVIDIA A40', 'count': 1},
            'containerDiskInGb': 200, 'volumeInGb': 0, 'costPerHr': '0.59', 'desiredStatus': 'RUNNING',
            **self.bad_resource}
        if self.lose_create:
            raise RuntimeError('UPSTREAM_SECRET_MUST_NOT_LEAVE')
        return deepcopy(self.pod_value)
    def reconcile(self, name):
        self.calls.append('reconcile')
        return [] if self.unknown_create else [deepcopy(self.pod_value)]
    def delete(self, identity):
        self.calls.append(('delete', identity))
        return self.delete_ok
    def pod(self, identity, timeout):
        self.calls.append('pod')
        return deepcopy(self.pod_value)
    def bootstrap_summary(self, run_id, timeout):
        self.calls.append('bootstrap_summary')
        return {'private_qwq_gpu_bootstrap_result_json': diagnostic_fixture(run_id)}
    def bootstrap(self, identity, timeout):
        self.calls.append(('bootstrap', identity))
        return self.bootstrap_value
    def summary(self, run_id, timeout):
        self.calls.append('summary')
        result = {'private_qwq_gpu_progress': {'phase': 'evaluating', 'case_id': 'momentum_energy',
            'mode': 'base', 'completed_attempts': 0, 'paired_completed_cases': 0,
            'evaluation_only': True, 'weights_updated': False, 'arbitrary_raw_text': 'DO_NOT_LOG'}}
        if self.no_progress:
            result = {}
        if not self.no_result:
            result['private_qwq_gpu_result_json'] = {'status': 'uploaded', 'execution_status': 'completed',
                                                   'run_id': run_id}
        return result


def diagnostic_fixture(run_id='123'):
    return {'version':1,'run_id':run_id,'code_commit':'a'*40,'status':'passed',
        'stages':[{'stage':s,'status':'passed','exit_code':0,'exception_type':None}
                  for s in ('core_compare','module_import','GPU_check')],
        'artifact':parent.ENTITY+'/'+parent.resume.PROJECT+'/hasla-qwq-bootstrap-'+run_id+':v0',
        'files':[{'name':n,'bytes':10,'sha256':'0'*64} for n in ('diagnostics.json','traceback.txt')],
        'model_calls':0}


class ParentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / 'state.json'
        plan = parent.evaluation_plan()
        root = Path(parent.__file__).parent
        self.manifest = {**parent.FIXED, 'code_commit': 'a' * 40, 'launch_id': 'b' * 32,
            'script_sha256': {n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in parent.REQUIRED_SCRIPTS},
            'source_adapter': deepcopy(parent.SOURCE_ADAPTER),
            'case_set_sha256': plan['comparison']['case_set_sha256'],
            'comparison_plan_sha256': hashlib.sha256(parent.canonical(plan)).hexdigest()}
        self.env = {'HASLA_QWQ_GPU_EVAL_MANIFEST': parent.canonical(self.manifest).decode(),
            'GITHUB_RUN_ID': '123', 'GITHUB_SHA': 'a' * 40, 'HASLA_QWQ_GPU_EVAL_LAUNCH_ID': 'b' * 32,
            'RUNPOD_API_KEY': 'PROVIDER_SECRET', 'WANDB_API_KEY': 'PRIVATE_STORAGE_SECRET',
            'WANDB_ENTITY': parent.ENTITY, 'HASLA_PREFLIGHT_ONLY': 'true'}
        self.services, self.clock, self.events = FakeServices(), Clock(), []
    def tearDown(self):
        self.tmp.cleanup()
    def execute(self, **kwargs):
        return parent.run(self.env, self.services, clock=self.clock, sleep=self.clock.sleep,
            wall_clock=lambda: 2000000000, state_path=self.state,
            emit=lambda event, **data: self.events.append({'event': event, **data}),
            result_validator=lambda value, _: value, **kwargs)
    def paid(self):
        self.env['HASLA_PREFLIGHT_ONLY'] = 'false'

    def test_fixed_plan_and_reservation_within_both_authorizations(self):
        checked = parent.validate_manifest(self.manifest)
        self.assertEqual(parent.comparison_plan_sha256(), 'b22d2a1430b009930331d16933b76db30c2807a09cbea77d359bc6a9c27c8c24')
        ledger = parent.budget_plan(checked, 'fixture', 0)
        self.assertEqual(ledger.reserved_krw, 1175)
        self.assertEqual(ledger.available_krw, 20487)
        self.assertLessEqual(ledger.reserved_krw, 1203)
        self.assertEqual(checked['previous_eval_upper_krw'] + ledger.reserved_krw, 2972)
        self.assertEqual(ledger.policy.fx_krw_per_usd_upper, 2000)

    def test_policy_changes_unknown_fields_source_and_plan_tampering_fail_closed(self):
        for key, value in [('gpu_id', 'NVIDIA L40S'), ('gpu_count', 2), ('runtime_seconds', 2801),
            ('child_runtime_seconds', 3000), ('gpu_usd_per_hour_upper', '0.61'),
            ('prior_upper_krw', 73337), ('reserved_upper_krw', 2922), ('optimizer_steps', 1),
            ('authorized_total', 100001), ('version', True), ('additional_limit_krw', 1204),
            ('comparison_plan_sha256', '0' * 64), ('source_adapter', {})]:
            with self.subTest(key=key), self.assertRaises(Exception):
                parent.validate_manifest({**self.manifest, key: value})
        with self.assertRaises(parent.EvaluationError):
            parent.validate_manifest({**self.manifest, 'raw_corpus': 'must-not-accept'})

    def test_preflight_checks_source_capacity_funding_without_creation_or_download(self):
        self.assertEqual(self.execute(), {'status': 'preflight_ready'})
        self.assertEqual(self.services.calls, ['pods', 'source', 'quote', 'funding'])
        self.assertFalse(self.state.exists())
        event = self.events[0]
        self.assertEqual(event['event'], 'private_qwq_gpu_preflight')
        self.assertEqual(event['remaining_budget_krw'], 20487)
        self.assertEqual(event['source_adapter_files'], parent.SOURCE_ADAPTER['files'])
        self.assertFalse(event['gpu_creation_performed'])

    def test_bad_source_or_funding_creates_nothing(self):
        for field in ('source_error', 'funding_error'):
            self.services = FakeServices()
            setattr(self.services, field, True)
            with self.subTest(field=field), self.assertRaises(parent.EvaluationError):
                self.execute()
            self.assertFalse(any(isinstance(x, tuple) and x[0]=='create' for x in self.services.calls))
            self.assertFalse(self.state.exists())

    def test_inventory_blocks_existing_task_but_preserves_unrelated_ids(self):
        self.assertEqual(parent.inventory(self.services.existing), {'keep-user-pod'})
        for rows in ([{'id': 'x', 'name': 'hasla-private-books-prior-solver'}],
                     [{'id': 'x', 'name': 'hasla-private-qwq-eval-prior'}],
                     [{'id': 'x', 'name': 'a'}, {'id': 'x', 'name': 'b'}], None):
            with self.subTest(rows=rows), self.assertRaises(parent.EvaluationError):
                parent.inventory(rows)

    def test_quote_over_ceiling_rejected_before_creation(self):
        self.services.price = Decimal('0.60001')
        with self.assertRaisesRegex(parent.EvaluationError, 'capacity_quote_invalid'):
            self.execute()
        self.assertNotIn('funding', self.services.calls)

    def test_paid_one_gpu_child_no_provider_key_absolute_deadline_and_scoped_cleanup(self):
        self.paid()
        self.execute()
        creates = [x for x in self.services.calls if isinstance(x, tuple) and x[0]=='create']
        self.assertEqual(len(creates), 1)
        child = creates[0][1]
        self.assertNotIn('RUNPOD_API_KEY', child)
        self.assertNotIn('PROVIDER_SECRET', json.dumps(child))
        self.assertNotIn('HF_TOKEN', child)
        job = json.loads(child['HASLA_QWQ_GPU_EVAL_JOB'])
        self.assertEqual(job['deadline_unix'], 2000002500)
        self.assertEqual(job['runtime_seconds'], 2400)
        self.assertEqual(set(job['script_sha256']), set(parent.CHILD_SCRIPTS))
        self.assertEqual(job['optimizer_steps'], 0)
        self.assertEqual(child['UNSLOTH_SKIP_NOTEBOOK_SYNC'], '1')
        self.assertEqual([x for x in self.services.calls if isinstance(x, tuple) and x[0]=='delete'],
                         [('delete', 'new-eval-pod')])
        self.assertTrue(json.loads(self.state.read_bytes())['closed'])
        self.assertNotIn('DO_NOT_LOG', json.dumps(self.events))

    def test_observed_wrong_gpu_price_disk_or_count_is_deleted_not_used(self):
        self.paid()
        for bad in ({'costPerHr': '0.60001'}, {'gpu': {'id':'NVIDIA L40S','count':1}},
                    {'gpu': {'id':'NVIDIA A40','count':2}}, {'containerDiskInGb': 201},
                    {'volumeInGb': 1}, {'networkVolume': True}):
            self.services = FakeServices(); self.services.bad_resource = bad
            self.state.unlink(missing_ok=True)
            with self.subTest(bad=bad), self.assertRaises(Exception):
                self.execute()
            self.assertNotIn('summary', self.services.calls)
            self.assertIn(('delete', 'new-eval-pod'), self.services.calls)

    def test_preexisting_id_returned_by_provider_is_never_deleted(self):
        self.paid(); self.services.bad_resource = {'id':'keep-user-pod'}
        with self.assertRaises(parent.EvaluationError):self.execute()
        self.assertFalse(any(isinstance(x, tuple) and x[0]=='delete' for x in self.services.calls))

    def test_lost_create_response_reconciles_once_without_recreation(self):
        self.paid(); self.services.lose_create = True
        self.execute()
        self.assertEqual(sum(isinstance(x, tuple) and x[0]=='create' for x in self.services.calls), 1)
        self.assertIn('reconcile', self.services.calls)
        self.assertIn(('delete', 'new-eval-pod'), self.services.calls)

    def test_unknown_create_retains_reservation_and_does_not_claim_absence(self):
        self.paid(); self.services.lose_create = True; self.services.unknown_create = True
        with self.assertRaisesRegex(parent.EvaluationError, 'cleanup_unconfirmed'):self.execute()
        self.assertEqual(sum(isinstance(x, tuple) and x[0]=='create' for x in self.services.calls), 1)
        cleanup = [x for x in self.events if x['event']=='private_qwq_gpu_cleanup'][-1]
        self.assertFalse(cleanup['deletion_confirmed']); self.assertTrue(cleanup['reservation_retained'])
        self.assertFalse(json.loads(self.state.read_bytes())['closed'])

    def test_deadline_stops_lost_child_and_confirms_cleanup_before_cost(self):
        self.paid(); self.services.no_result = True
        with self.assertRaisesRegex(parent.EvaluationError, 'parent_deadline'):self.execute()
        self.assertEqual(self.clock.now, 2780)
        self.assertIn(('delete', 'new-eval-pod'), self.services.calls)
        cost = [x for x in self.events if x['event']=='private_qwq_gpu_cost'][-1]
        self.assertLessEqual(cost['run_upper_krw'], 1175)
        self.assertTrue(cost['deletion_confirmed'])

    def test_unconfirmed_delete_has_no_settlement_event(self):
        self.paid(); self.services.delete_ok = False
        with self.assertRaisesRegex(parent.EvaluationError, 'cleanup_unconfirmed'):self.execute()
        self.assertFalse(any(x['event']=='private_qwq_gpu_cost' for x in self.events))

    def test_cleanup_is_idempotent_and_no_state_means_no_provider_call(self):
        self.assertTrue(parent.cleanup(self.env, self.services, state_path=self.state, emit=lambda *a,**k:None))
        self.assertEqual(self.services.calls, [])
        self.paid(); self.execute(); self.services.calls.clear()
        self.assertTrue(parent.cleanup(self.env, self.services, state_path=self.state, emit=lambda *a,**k:None))
        self.assertEqual(self.services.calls, [])

    def test_progress_is_fixed_projection_and_rejects_training_or_unknown_case(self):
        good = self.services.summary('123', 1)
        self.assertNotIn('DO_NOT_LOG', json.dumps(parent.safe_progress(good)))
        for key,value in [('weights_updated',True),('evaluation_only',False),('case_id','private-original-text')]:
            bad=deepcopy(good);bad['private_qwq_gpu_progress'][key]=value
            with self.assertRaises(parent.EvaluationError):parent.safe_progress(bad)

    def test_bootstrap_preserves_image_core_and_reports_only_fixed_stages(self):
        command=parent.pod_command(self.manifest)
        self.assertIn('/opt/unsloth-venv/bin/python -m pip install -q wandb==0.31.0',command)
        self.assertNotIn('--upgrade',command)
        self.assertNotIn('pip install -q unsloth',command)
        self.assertIn('import unsloth, bitsandbytes, peft, torch, wandb',command)
        self.assertIn('core_compare',command)
        self.assertIn('GPU_check',command)
        self.assertIn('torch.cuda.device_count()',command)
        self.assertIn('2500s',command)
        self.assertIn('sleep 120',command)
        self.assertIn('private_qwq_gpu_bootstrap',command)
        self.assertIn('qwq-eval-core.json',command)
        self.assertIn('unsloth_zoo',command)
        self.assertLess(command.index('pip install'),command.index('-B private_qwq_gpu_eval.py'))
        self.assertLess(command.index('def diagnose'),command.index('-B private_qwq_gpu_eval.py'))
        self.assertLess(command.index('compgen -e'),command.index('pip install'))

    def test_injected_pod_credentials_removed_from_parent_shell_and_child_process(self):
        bash=Path(r'C:\Program Files\Git\bin\bash.exe') if os.name=='nt' else Path('/bin/bash')
        if not bash.is_file():self.skipTest('Bash not installed')
        script=parent.pod_credential_cleanup()+''';
        [[ ! -v RUNPOD_API_KEY && ! -v injectedRunpodToken && ! -v HF_TOKEN && ! -v HF_HUB_TOKEN && -v WANDB_API_KEY && -v RUNPOD_POD_ID ]] || exit 7;
        export -p | grep -q 'WANDB_API_KEY' || exit 8;
        /bin/bash -c '[[ ! -v RUNPOD_API_KEY && ! -v HF_TOKEN && -v WANDB_API_KEY && -v RUNPOD_POD_ID ]]' '''
        env={'WANDB_API_KEY':'synthetic-storage','RUNPOD_API_KEY':'synthetic-provider',
             'injectedRunpodToken':'synthetic-provider','HF_TOKEN':'synthetic-hf','HF_HUB_TOKEN':'synthetic-hf',
             'RUNPOD_POD_ID':'synthetic-pod'}
        if os.name=='nt':env['SystemRoot']=os.environ['SystemRoot']
        result=subprocess.run([str(bash),'-c',script],env=env,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0)
        self.assertEqual(result.stdout,b'');self.assertEqual(result.stderr,b'')

    def test_only_the_four_approved_optional_packages_are_removed_before_sdk(self):
        inner=shlex.split(parent.pod_command(self.manifest))[-1]
        uninstall=[c.strip() for c in inner.split(';') if '-m pip uninstall' in c]
        self.assertEqual(len(uninstall),1)
        args=shlex.split(uninstall[0].split(' >',1)[0])
        self.assertEqual(args,[parent.PYTHON,'-m','pip','uninstall','-y','vllm','torchcodec','mistral-common','decord'])
        self.assertNotIn('torch',args);self.assertNotIn('transformers',args)
        self.assertLess(inner.index('pip uninstall'),inner.index('pip install'))
        self.assertLess(inner.index('qwq-eval-core.json'),inner.index('pip uninstall'))

    def test_complete_inline_bootstrap_and_outer_wrapper_have_valid_bash_syntax(self):
        bash=Path(r'C:\Program Files\Git\bin\bash.exe') if os.name=='nt' else Path('/bin/bash')
        if not bash.is_file():self.skipTest('Bash not installed')
        command=parent.pod_command(self.manifest)
        for name,script in [('outer',command),('inner',shlex.split(command)[-1])]:
            path=Path(self.tmp.name)/(name+'.sh');path.write_text(script,encoding='utf8',newline='\n')
            checked=subprocess.run([str(bash),'-n',path.as_posix()],capture_output=True,timeout=10)
            self.assertEqual(checked.returncode,0);self.assertEqual(checked.stderr,b'')

    def test_bootstrap_markers_reject_raw_extra_keys_and_bad_codes(self):
        good={'event':'private_qwq_gpu_bootstrap','stage':'failed','exit_code':7}
        self.assertEqual(parent.bootstrap_marker(json.dumps(good)),{'stage':'failed','exit_code':7})
        for bad in ['private secret', '{}', json.dumps({**good,'raw':'secret'}),
                    json.dumps({**good,'exit_code':True}),json.dumps({**good,'exit_code':256}),
                    json.dumps({**good,'stage':'private-secret'}),json.dumps({**good,'stage':[]})]:
            self.assertIsNone(parent.bootstrap_marker(bad))

    def test_bootstrap_get_exact_owned_pod_is_bounded_and_never_returns_raw_lines(self):
        from contextlib import nullcontext
        from unittest.mock import patch
        import private_qwq_gpu_eval as worker
        class Response:
            status_code=200
            closed=False
            def close(self):self.closed=True
            def iter_content(self,chunk_size):
                self.chunk_size=chunk_size
                for line in ['PRIVATE_SECRET raw stderr', json.dumps({'event':'private_qwq_gpu_bootstrap','stage':'sdk'}),
                             json.dumps({'event':'private_qwq_gpu_bootstrap','stage':'failed','exit_code':9})]:
                    yield b'data:'+json.dumps({'source':'container','line':line}).encode()+b'\n'
        response=Response();calls=[]
        def get(url,**kwargs):calls.append((url,kwargs));return response
        with patch.object(parent.cloud.requests,'get',side_effect=get),patch.object(worker,'hard_wall',lambda s:nullcontext()):
            result=parent.Services(self.env).bootstrap('new-eval-pod',6)
        self.assertEqual(result,{'stage':'failed','exit_code':9})
        self.assertTrue(response.closed);self.assertEqual(response.chunk_size,1024)
        self.assertEqual(calls[0][0],parent.cloud.REST+'/pods/new-eval-pod/logs')
        self.assertFalse(calls[0][1]['allow_redirects'])
        self.assertEqual(calls[0][1]['params'],{'source':'container','tail':60})
        self.assertNotIn('PRIVATE_SECRET',json.dumps(result))

    def test_bootstrap_oversized_single_stream_chunk_cannot_smuggle_marker(self):
        from contextlib import nullcontext
        from unittest.mock import patch
        import private_qwq_gpu_eval as worker
        class Response:
            status_code=200
            def close(self):pass
            def iter_content(self,chunk_size):
                yield b'x'*65537+b'\ndata:'+json.dumps({'source':'container','line':json.dumps({'event':'private_qwq_gpu_bootstrap','stage':'sdk'})}).encode()+b'\n'
        with patch.object(parent.cloud.requests,'get',return_value=Response()),patch.object(worker,'hard_wall',lambda s:nullcontext()):
            self.assertIsNone(parent.Services(self.env).bootstrap('new-eval-pod',6))

    def test_startup_unknown_is_bounded_to_1500_and_deleted(self):
        self.paid();self.services.no_result=True;self.services.no_progress=True
        with self.assertRaisesRegex(parent.EvaluationError,'startup_unobserved'):self.execute()
        self.assertEqual(self.clock.now,100+1500)
        self.assertIn(('delete','new-eval-pod'),self.services.calls)
        self.assertTrue(any(e['event']=='private_qwq_gpu_cost' for e in self.events))

    def test_bootstrap_failure_cleans_up_early_and_drops_arbitrary_strings(self):
        self.paid();self.services.no_result=True;self.services.no_progress=True
        self.services.bootstrap_value={'stage':'failed','exit_code':7}
        with self.assertRaisesRegex(parent.EvaluationError,'bootstrap_failed'):self.execute()
        self.assertEqual(self.clock.now,100)
        self.assertIn(('delete','new-eval-pod'),self.services.calls)
        self.assertEqual(next(e for e in self.events if e['event']=='private_qwq_gpu_bootstrap'),
                         {'event':'private_qwq_gpu_bootstrap','run_id':'123','stage':'failed','exit_code':7})

    def test_create_preserves_official_entrypoint_exact_cmd_and_environment(self):
        from unittest.mock import patch
        captured=[]
        with patch.object(parent.cloud,'runpod',side_effect=lambda *args,**kwargs:captured.append((args,kwargs))):
            parent.Services(self.env).create('exact',{'UNSLOTH_SKIP_NOTEBOOK_SYNC':'1'},'safe command')
        args,kw=captured[0]
        self.assertEqual(args,('POST','/pods'))
        body=kw['json']
        self.assertNotIn('entrypoint',body)
        self.assertEqual(body['image'],parent.IMAGE)
        self.assertEqual(body['cmd'],['/bin/bash','-lc','safe command'])
        self.assertEqual(body['gpu'],{'id':'NVIDIA A40','count':1,'minCudaVersion':'12.8'})
        self.assertEqual(body['env'],{'UNSLOTH_SKIP_NOTEBOOK_SYNC':'1'})
        self.assertFalse(body['startSsh']);self.assertEqual(body['ports'],[])

    def test_private_bootstrap_safe_projection_and_identity_fail_closed(self):
        good=diagnostic_fixture()
        self.assertEqual(parent.safe_bootstrap_result({'private_qwq_gpu_bootstrap_result_json':good},'123','a'*40),good)
        for key,value in [('run_id','124'),('code_commit','f'*40),('model_calls',1),('artifact','public/unsafe:v0'),('raw','SECRET')]:
            with self.subTest(key=key),self.assertRaises(parent.EvaluationError):
                parent.safe_bootstrap_result({'private_qwq_gpu_bootstrap_result_json':{**good,key:value}},'123','a'*40)
        bad=deepcopy(good);bad['stages'][1]['observations']={'raw':'SECRET'}
        with self.assertRaises(parent.EvaluationError):parent.safe_bootstrap_result({'private_qwq_gpu_bootstrap_result_json':bad},'123','a'*40)

    def test_fixed_diagnostic_failure_is_relayed_but_raw_stdout_is_never_exposed(self):
        inner=shlex.split(parent.pod_command(self.manifest))[-1]
        lexer=shlex.shlex(inner,posix=True,punctuation_chars=True);lexer.whitespace_split=True
        tokens=list(lexer)
        relay=next(tokens[i+2] for i in range(len(tokens)-2)
                   if tokens[i:i+2]==[parent.PYTHON,'-c'] and 'data.splitlines()' in tokens[i+2])
        path=Path(self.tmp.name)/'private.log'
        event={'event':'private_qwq_gpu_bootstrap_diagnostic','status':'failed','phase':'sdk_init','exception_type':'UsageError','exit_code':1}
        path.write_text('PRIVATE_RAW_KEY\n'+json.dumps({**event,'raw':'PRIVATE_RAW_KEY'})+'\n'+json.dumps(event)+'\n')
        relay=relay.replace("'/workspace/qwq-eval-dependencies.log'",repr(str(path)))
        import sys
        result=subprocess.run([sys.executable,'-c',relay],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0)
        self.assertEqual(json.loads(result.stdout),event)
        self.assertNotIn('PRIVATE_RAW',result.stdout)
        marker=parent.diagnostic_failure_marker(result.stdout.strip())
        self.assertEqual(marker,{'stage':'diagnostic_failed','phase':'sdk_init','exception_type':'UsageError','exit_code':1})
        self.assertEqual(parent.bootstrap_marker(json.dumps({'event':'private_qwq_gpu_bootstrap',**marker})),marker)

    def test_failed_marker_rechecks_lagging_summary_once_before_cleanup(self):
        self.paid();self.services.no_result=True;self.services.no_progress=True
        self.services.bootstrap_value={'stage':'diagnostic_failed','phase':'summary','exception_type':'UsageError','exit_code':1}
        calls=[]
        def summary(*args):
            calls.append(True)
            return {} if len(calls)==1 else {'private_qwq_gpu_bootstrap_result_json':diagnostic_fixture()}
        self.services.bootstrap_summary=summary
        with self.assertRaisesRegex(parent.EvaluationError,'bootstrap_failed'):self.execute()
        self.assertEqual(len(calls),2)
        self.assertTrue(any(e['event']=='private_qwq_gpu_bootstrap_diagnostic' for e in self.events))
        self.assertIn(('delete','new-eval-pod'),self.services.calls)

    def test_private_bootstrap_failure_retains_safe_artifact_evidence_then_deletes(self):
        self.paid();self.services.no_result=True
        bad=diagnostic_fixture();bad['status']='failed';bad['stages'][1].update(status='failed',exit_code=1,exception_type='ImportError')
        self.services.bootstrap_summary=lambda *args:{'private_qwq_gpu_bootstrap_result_json':bad}
        with self.assertRaisesRegex(parent.EvaluationError,'bootstrap_diagnostic_failed'):self.execute()
        event=next(e for e in self.events if e['event']=='private_qwq_gpu_bootstrap_diagnostic')
        self.assertEqual(event['artifact'],bad['artifact']);self.assertNotIn('observations',json.dumps(event))
        self.assertIn(('delete','new-eval-pod'),self.services.calls)

    def test_uploaded_evaluation_without_committed_private_bootstrap_receipt_is_rejected(self):
        self.paid();self.services.bootstrap_summary=lambda *args:{}
        with self.assertRaisesRegex(parent.EvaluationError,'bootstrap_receipt_unavailable'):self.execute()
        self.assertIn(('delete','new-eval-pod'),self.services.calls)

    def test_script_checksum_failure_blocks_services_and_no_state_written(self):
        data=json.loads(self.env['HASLA_QWQ_GPU_EVAL_MANIFEST']);data['script_sha256']['role_config.py']='0'*64
        self.env['HASLA_QWQ_GPU_EVAL_MANIFEST']=parent.canonical(data).decode()
        with self.assertRaisesRegex(parent.EvaluationError,'public_script_hash_mismatch'):self.execute()
        self.assertEqual(self.services.calls,[]);self.assertFalse(self.state.exists())


class WorkflowTests(unittest.TestCase):
    def test_gpu_flag_is_exclusive_and_no_model_or_provider_keys_reach_child(self):
        text=(Path(__file__).resolve().parents[2]/'.github/workflows/train-ai.yml').read_text()
        jobs=[p for p in re.split(r'(?m)^  (?=[a-z][a-z0-9-]+:\s*$)',text.split('jobs:\n',1)[1]) if p.strip()]
        gpu=next(p for p in jobs if p.startswith('compare-qwq-gpu:'))
        self.assertIn('timeout-minutes: 70',gpu)
        self.assertIn('group: hasla-private-qwq-gpu-evaluation',gpu)
        self.assertNotIn('HF_TOKEN',gpu)
        self.assertNotIn('upload-artifact',gpu)
        self.assertIn('!inputs.compare_qwq_cpu',gpu)
        for job in jobs:
            if job!=gpu:self.assertIn('!inputs.compare_qwq_gpu',next(l for l in job.splitlines() if l.startswith('    if:')))


if __name__=='__main__':unittest.main()

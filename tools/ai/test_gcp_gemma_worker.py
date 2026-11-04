"""CPU fakes only: no real HTTP, package install, models, Torch or GPU work."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from urllib.parse import unquote,urlsplit,parse_qs
from unittest.mock import patch

import gcp_gemma_worker as worker


def response(status,raw=b'',headers=None):
    return SimpleNamespace(status_code=status,content=raw,headers=headers or {},close=lambda:None)


def payload(split,count):
    rows=[]
    for index in range(count):
        label=split+'-'+str(index);digest=hashlib.sha256(label.encode()).hexdigest()
        rows.append({'id':label,'messages':[{'role':'user','content':'Question '+label},
            {'role':'assistant','content':'Answer '+label}],
            'metadata':{'split':split,'target_role':'chat','group_id':label,'derivation':'paraphrase_observed_exchange',
                'reconstructed':True,'old_synthetic_seed':False,'observed_reply_link':'observed_direct_reply',
                'reviewer':'independent-fixture','review_status':'approved','collected_at':'2026-11-05T00:00:00Z',
                'source_url':'https://orbi.kr/'+str((100000 if split=='train' else 200000)+index),
                'question_sha256':digest,'answer_sha256':hashlib.sha256(('answer-'+label).encode()).hexdigest(),
                'author_filter':{'policy_version':'exclude-bugiu-v1','post_author_checked':True,
                    'selected_reply_authors_checked':True,'reply_branch_checked':True,'excluded_author_present':False}}})
    return b'\n'.join(worker.canonical(row) for row in rows)+b'\n'


class FakeHttp:
    def __init__(self,manifest,inputs):
        self.manifest=manifest;self.calls=[];self.public=set();self.bad_checksum=False
        self.broad_authenticated_readers=False
        self.bucket_status=200
        self.bucket_policy={'publicAccessPrevention':'enforced','uniformBucketLevelAccess':{'enabled':True}}
        self.objects={manifest['prefix']+'/privacy-probe.bin':(b'x'*32,'10')}
        self.objects.update({manifest['prefix']+'/'+split+'.chat.jsonl':(raw,str(20+index))
            for index,(split,raw) in enumerate(inputs.items())})
    def request(self,method,url,**options):
        self.calls.append((method,url,options))
        if url.startswith(worker.META):
            assert method=='GET' and options['headers']=={'Metadata-Flavor':'Google'}
            path=url[len(worker.META):]
            values={'instance/service-accounts/default/email':self.manifest['service_account_email'].encode(),
                'project/project-id':b'google-managed-tenant-project',
                'instance/machine-type':('projects/tenant/zones/test/machineTypes/'+worker.MACHINE).encode(),
                'instance/service-accounts/default/token':worker.canonical({'access_token':'adc-fixture-token',
                    'token_type':'Bearer','expires_in':3600})}
            return response(200,values[path],{'Metadata-Flavor':'Google'})
        assert url.startswith(worker.STORAGE)
        parsed=urlsplit(url);query=parse_qs(parsed.query)
        if parsed.path=='/storage/v1/b/'+worker.BUCKET:
            assert method=='GET' and query=={'fields':['iamConfiguration']}
            assert options['headers']['Authorization']=='Bearer adc-fixture-token'
            return response(self.bucket_status,worker.canonical({'iamConfiguration':self.bucket_policy}))
        if method=='POST':
            assert query['ifGenerationMatch']==['0'] and query['uploadType']==['media']
            assert options['headers']['Authorization']=='Bearer adc-fixture-token'
            name=query['name'][0]
            if name in self.objects:return response(412)
            raw=options['data'].read();generation=str(100+len(self.objects));self.objects[name]=(raw,generation)
            value=self.metadata(name)
            if self.bad_checksum:value['md5Hash']='bad'
            return response(200,worker.canonical(value))
        assert method=='GET'
        name=unquote(parsed.path.split('/o/',1)[1]);current=self.objects.get(name)
        if not current or query.get('generation')!=[current[1]]:return response(404)
        if options.get('outside_authenticated'):
            assert options['headers']['Authorization']=='Bearer unrelated-google-identity'
            return response(200 if self.broad_authenticated_readers else 403)
        if options.get('anonymous'):
            assert 'Authorization' not in options['headers'] and options.get('stream') is True
            return response(200 if name in self.public else 403)
        assert options['headers']['Authorization']=='Bearer adc-fixture-token'
        return response(200,current[0] if query.get('alt')==['media'] else worker.canonical(self.metadata(name)))
    def metadata(self,name):
        raw,generation=self.objects[name]
        return {'name':name,'bucket':worker.BUCKET,'size':str(len(raw)),'generation':generation,
            'md5Hash':base64.b64encode(hashlib.md5(raw).digest()).decode()}


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.inputs={'train':payload('train',60),'validation':payload('validation',11)}
        root=Path(worker.__file__).parent
        self.manifest={'version':1,'kind':worker.KIND,'run_id':'gemma-fixture','project_id':worker.PROJECT,
            'project_number':'1234567890','service_account_email':'service-1234567890@gcp-sa-aiplatform-cc.iam.gserviceaccount.com',
            'bucket':worker.BUCKET,'prefix':'hasla-ai/gemma/gemma-fixture','machine_type':worker.MACHINE,
            'runtime_seconds':1800,'upload_grace_seconds':180,'dataset_version':'gemma-chat-v5-fixture',
            'code_sha256':{name:worker.sha_file(root/name) for name in worker.CODE_FILES},
            'dependency_versions':{name:'fixture' for name in worker.DEPENDENCIES},
            'privacy_probe':{'name':'privacy-probe.bin','generation':'10','bytes':32,'sha256':hashlib.sha256(b'x'*32).hexdigest()},
            'budget':{'authorized_budget_krw':100000,'prior_closed_upper_krw':20000,'other_reserved_upper_krw':30000,
                'job_reserved_upper_krw':15000,'reserve_krw':5000},
            'inputs':{split:{'name':split+'.chat.jsonl','generation':str(20+index),'bytes':len(raw),
                'sha256':hashlib.sha256(raw).hexdigest(),'records':60 if split=='train' else 11}
                for index,(split,raw) in enumerate(self.inputs.items())}}
        self.trainer_calls=[];self.zero=False;self.nonfinite=False;self.partial=False
        self.http=FakeHttp(self.manifest,self.inputs)
    def env(self):
        return {'HASLA_GCP_GEMMA_MANIFEST':json.dumps(self.manifest),'CLOUD_ML_PROJECT_ID':'1234567890','PATH':'fixture'}
    def trainer(self,command,**options):
        self.trainer_calls.append((command,options));root=Path(options['cwd']);adapter=root/'adapter';adapter.mkdir()
        config={'peft_type':'LORA','r':8,'base_model_name_or_path':'google/gemma-4-26B-A4B-it','init_lora_weights':True}
        (adapter/'adapter_config.json').write_bytes(worker.canonical(config))
        a='base_model.model.layers.0.q_proj.lora_A.weight';b=a.replace('_A','_B')
        header={a:{'dtype':'BF16','shape':[8,4],'data_offsets':[0,64]},
                b:{'dtype':'BF16','shape':[4,8],'data_offsets':[64,128]}}
        raw=worker.canonical(header);value=0x7f80 if self.nonfinite else 0 if self.zero else 0x3f80
        model=struct.pack('<Q',len(raw))+raw+b'\0'*64+struct.pack('<H',value)+b'\0'*62
        (adapter/'adapter_model.safetensors').write_bytes(model)
        maximum=int(command[command.index('--max-steps')+1]);steps=1 if self.partial else maximum
        report={'role':'chat','base_model':config['base_model_name_or_path'],'format':'chat','precision':'bf16',
            'training_method':'lora','rank':8,'max_length':1024,'max_steps':maximum,'steps_completed':steps,
            'training_sha256':worker.sha_file(root/'train.chat.jsonl'),
            'validation_sha256':worker.sha_file(root/'validation.chat.jsonl'),'weights_updated':True,
            'train_loss':1.0,'eval_loss':1.2,'initial_adapter_model_sha256':None,'optimizer_state_restored':False}
        (adapter/'hasla_training_manifest.json').write_bytes(worker.canonical(report))
        return 0
    def execute(self,**kwargs):
        return worker.execute(self.env(),http=self.http,workspace=self.directory.name,trainer=self.trainer,
            gpu_check=lambda:{'gpu_count':1,'gpu_name':'NVIDIA A100-SXM4-80GB','gpu_memory_mib':81175},
            version=lambda name:'fixture',**kwargs)

    def test_real_validators_and_cpu_tensor_scanner_before_private_stage(self):
        result=self.execute();self.assertEqual(result['status'],'stored');self.assertTrue(result['weights_updated'])
        self.assertEqual(result['max_steps'],8);self.assertEqual(result['training_report']['steps_completed'],8)
        self.assertEqual(result['tensor_evidence']['standard_b_nonzero_elements'],1)
        self.assertFalse(result['quality_verified']);self.assertEqual(result['test_records_used'],0)
        names={name.rsplit('/',1)[-1] for name in self.http.objects}
        self.assertEqual(names,{'privacy-probe.bin','train.chat.jsonl','validation.chat.jsonl',
            'progress.json','result.json','adapter_config.json','adapter_model.safetensors'})
        command,options=self.trainer_calls[0]
        self.assertIn('--epochs',command);self.assertNotIn('--resume-adapter',command)
        self.assertLessEqual(options['timeout'],1620)
        self.assertNotIn('HASLA_GCP_GEMMA_MANIFEST',options['env']);self.assertNotIn('CLOUD_ML_PROJECT_ID',options['env'])
        self.assertTrue(all(method in ('GET','POST') for method,_,_ in self.http.calls))

    def test_preflight_uses_no_gpu_trainer_or_upload_and_allows_tenant_project(self):
        result=self.execute(preflight=True);self.assertEqual(result['status'],'preflight_ready')
        self.assertFalse(result['gpu_used']);self.assertEqual(self.trainer_calls,[])
        self.assertFalse(any(method=='POST' for method,_,_ in self.http.calls))

    def test_zero_and_nonfinite_weights_never_publish_adapter(self):
        for mode in ('zero','nonfinite'):
            with self.subTest(mode=mode):
                self.http=FakeHttp(self.manifest,self.inputs);self.zero=mode=='zero';self.nonfinite=mode=='nonfinite'
                with self.assertRaisesRegex(worker.WorkerError,'weights_unverified'):self.execute()
                self.assertNotIn(self.manifest['prefix']+'/adapter_model.safetensors',self.http.objects)

    def test_clean_partial_weights_are_stored_without_claiming_full_schedule(self):
        self.partial=True;result=self.execute();self.assertEqual(result['status'],'partial')
        self.assertFalse(result['training_report']['scheduled_steps_completed']);self.assertTrue(result['weights_updated'])

    def test_public_probe_blocks_before_private_input_download_or_training(self):
        self.http.public.add(self.manifest['prefix']+'/privacy-probe.bin')
        with self.assertRaisesRegex(worker.WorkerError,'bucket_privacy_unverified'):self.execute()
        self.assertEqual(self.trainer_calls,[])
        self.assertFalse(any('train.chat.jsonl' in unquote(url) for _,url,_ in self.http.calls))

    def test_bucket_metadata_permission_denial_is_not_replaced_by_private_probe(self):
        self.http.bucket_status=403
        with self.assertRaisesRegex(worker.WorkerError,'bucket_metadata_unavailable'):self.execute()
        self.assertEqual(self.trainer_calls,[])
        self.assertFalse(any('/o/' in url or method=='POST' for method,url,_ in self.http.calls))

    def test_broad_authenticated_principals_cannot_pass_anonymous_denial_only(self):
        # allAuthenticatedUsers can read despite every anonymous request yielding
        # 403. PAP enforcement is the required live server-side denial of both
        # broad principal classes; a private probe cannot substitute for it.
        self.http.broad_authenticated_readers=True
        self.http.bucket_policy['publicAccessPrevention']='inherited'
        probe=self.manifest['prefix']+'/privacy-probe.bin'
        url=worker.STORAGE+'/storage/v1/b/'+worker.BUCKET+'/o/'+worker.quote(probe,safe='')+'?alt=media&generation=10'
        outsider=self.http.request('GET',url,headers={'Authorization':'Bearer unrelated-google-identity'},outside_authenticated=True)
        anonymous=self.http.request('GET',url,headers={'Accept-Encoding':'identity'},anonymous=True,stream=True)
        self.assertEqual(outsider.status_code,200);self.assertEqual(anonymous.status_code,403)
        self.http.calls.clear()
        with self.assertRaisesRegex(worker.WorkerError,'bucket_privacy_unverified'):self.execute()
        self.assertEqual(self.trainer_calls,[])
        self.assertFalse(any('/o/' in url or method=='POST' for method,url,_ in self.http.calls))

    def test_legacy_acl_bucket_is_rejected_even_with_pap_and_private_probe(self):
        self.http.bucket_policy['uniformBucketLevelAccess']['enabled']=False
        with self.assertRaisesRegex(worker.WorkerError,'bucket_privacy_unverified'):self.execute()
        self.assertEqual(self.trainer_calls,[])
        self.assertFalse(any('/o/' in url or method=='POST' for method,url,_ in self.http.calls))

    def test_live_policy_is_rechecked_before_private_media_and_training(self):
        for boundary in ('source_metadata','progress_upload'):
            with self.subTest(boundary=boundary):
                self.http=FakeHttp(self.manifest,self.inputs);actual=self.http.request
                def change_policy(method,url,**options):
                    reply=actual(method,url,**options)
                    source_meta=(method=='GET' and 'train.chat.jsonl' in unquote(url)
                        and 'alt=media' not in url)
                    progress=(method=='POST' and 'progress.json' in unquote(url))
                    if (boundary=='source_metadata' and source_meta) or (boundary=='progress_upload' and progress):
                        self.http.bucket_policy['publicAccessPrevention']='inherited'
                    return reply
                self.http.request=change_policy
                with self.assertRaisesRegex(worker.WorkerError,'bucket_privacy_unverified'):self.execute()
                self.assertEqual(self.trainer_calls,[])
                if boundary=='source_metadata':
                    self.assertFalse(any('train.chat.jsonl' in unquote(url) and 'alt=media' in url
                        for _,url,_ in self.http.calls))

    def test_public_input_blocks_training_even_when_probe_is_private(self):
        self.http.public.add(self.manifest['prefix']+'/train.chat.jsonl')
        with self.assertRaisesRegex(worker.WorkerError,'bucket_privacy_unverified'):self.execute()
        self.assertEqual(self.trainer_calls,[])

    def test_input_hash_mismatch_is_rejected_before_trainer(self):
        self.manifest['inputs']['train']['sha256']='0'*64
        with self.assertRaisesRegex(worker.WorkerError,'source_integrity_failed'):self.execute()
        self.assertEqual(self.trainer_calls,[])

    def test_existing_generation_cannot_be_overwritten_or_retrained(self):
        self.http.objects[self.manifest['prefix']+'/progress.json']=(b'previous','99')
        with self.assertRaisesRegex(worker.WorkerError,'upload_failed'):self.execute()
        self.assertEqual(self.trainer_calls,[])

    def test_server_upload_checksum_mismatch_cannot_claim_success(self):
        self.http.bad_checksum=True
        with self.assertRaisesRegex(worker.WorkerError,'upload_integrity_failed'):self.execute()
        self.assertEqual(self.trainer_calls,[])

    def test_manifest_budget_prefix_and_generation_are_strict(self):
        for change in ('budget','prefix','generation','version'):
            value=copy.deepcopy(self.manifest)
            if change=='budget':value['budget']['other_reserved_upper_krw']=99999
            if change=='prefix':value['prefix']='hasla-ai/gemma/other'
            if change=='generation':value['inputs']['train']['generation']='latest'
            if change=='version':value['version']=True
            with self.subTest(change=change),self.assertRaises(worker.WorkerError):
                worker.manifest_from_env({'HASLA_GCP_GEMMA_MANIFEST':json.dumps(value)})

    def test_provider_keys_and_sa_json_are_rejected_before_http(self):
        for name in ('GOOGLE_APPLICATION_CREDENTIALS','GCP_SA_KEY','HF_TOKEN','WANDB_API_KEY','RUNPOD_API_KEY',
                     'GITHUB_TOKEN','GH_TOKEN','GH_ENTERPRISE_TOKEN','GITHUB_ENTERPRISE_TOKEN','RUNPOD_TOKEN','WANDB_TOKEN'):
            env={**self.env(),name:'synthetic-secret'}
            with self.subTest(name=name),self.assertRaisesRegex(worker.WorkerError,'unexpected_credential'):
                worker.execute(env,http=self.http)
        self.assertEqual(self.http.calls,[])

    def test_temporary_cleanup_failure_preserves_committed_private_receipt(self):
        actual=tempfile.TemporaryDirectory
        class CleanupFailure:
            def __init__(self,*args,**kwargs):
                self.directory=actual(*args,**kwargs);self.name=self.directory.name
            def cleanup(self):
                self.directory.cleanup();raise OSError('synthetic cleanup failure')
        with patch.object(worker.tempfile,'TemporaryDirectory',CleanupFailure):
            result=self.execute()
        self.assertEqual(result['status'],'stored')
        self.assertEqual(result['result_object']['name'],'result.json')
        self.assertIn(self.manifest['prefix']+'/result.json',self.http.objects)

    def test_public_uploaded_model_prevents_success_and_failure_receipt_upload(self):
        self.http.public.add(self.manifest['prefix']+'/adapter_model.safetensors')
        with self.assertRaisesRegex(worker.WorkerError,'bucket_privacy_unverified'):self.execute()
        self.assertEqual(len(self.trainer_calls),1)
        self.assertNotIn(self.manifest['prefix']+'/result.json',self.http.objects)

    def test_dependency_and_code_pins_fail_before_any_http(self):
        with self.assertRaisesRegex(worker.WorkerError,'dependency_profile_mismatch'):
            worker.execute(self.env(),http=self.http,version=lambda name:'wrong')
        self.manifest['code_sha256']['train_lora.py']='0'*64
        with self.assertRaisesRegex(worker.WorkerError,'code_pin_mismatch'):self.execute()
        self.assertEqual(self.http.calls,[])

    def test_wrong_managed_owner_project_number_fails_before_gcs(self):
        env={**self.env(),'CLOUD_ML_PROJECT_ID':'999'}
        with self.assertRaisesRegex(worker.WorkerError,'runtime_identity_mismatch'):
            worker.execute(env,http=self.http,version=lambda name:'fixture')
        self.assertEqual(self.http.calls,[])

    def test_a100_gpu_count_and_memory_metadata_are_checked(self):
        good=lambda *a,**kw:SimpleNamespace(returncode=0,stdout='NVIDIA A100-SXM4-80GB, 81175\n')
        self.assertEqual(worker.check_gpu(good)['gpu_count'],1)
        for text in ('NVIDIA A100-SXM4-40GB, 40536','NVIDIA A100-SXM4-80GB, 81175\nNVIDIA A100-SXM4-80GB, 81175'):
            with self.assertRaisesRegex(worker.WorkerError,'gpu_contract_failed'):
                worker.check_gpu(lambda *a,**kw:SimpleNamespace(returncode=0,stdout=text))


if __name__=='__main__':unittest.main()

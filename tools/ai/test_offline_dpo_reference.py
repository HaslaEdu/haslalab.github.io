import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import private_pod_train as pod
import private_verify_adapter as verifier
from test_private_verify_adapter import adapter,Entry,Fixture

def receipt():
    return {'version':1,'method':'post_sft_frozen_reference_offline_dpo_v1','data_sha256':'a'*64,'pairs':2,'epochs':3,'beta':0.1,'learning_rate':5e-7,
      'optimizer_steps_completed':6,'expected_optimizer_steps':6,'reference_kind':'same_active_post_sft_adapter_cached_sum_logps',
      'reference_cached_before_optimizer':True,'reference_adapter_parameter_sha256':'b'*64,'reference_after_cache_parameter_sha256':'b'*64,
      'final_adapter_parameter_sha256':'c'*64,'trainable_lora_tensors':2,'reference_files':[
          {'name':'adapter_config.json','bytes':10,'sha256':'d'*64},{'name':'adapter_model.safetensors','bytes':100,'sha256':'e'*64}],
      'reference_logps_sha256':'f'*64,'loss_last':0.68,'loss_mean':0.69,'gradient_norm_min':0.01,'gradient_norm_max':0.1,
      'dropout_disabled_during_reference_and_policy':True,'weights_updated':True,'model_generation_calls':0,'performance_evaluations':0,
      'quality_verified':False,'production_promoted':False,'review_sha256':'1'*64,'helper_sha256':'2'*64,'relative_weight_change_verified':True,
      'final_adapter_model_sha256':'3'*64,'b_changed_tensors':1,'b_changed_elements':2}

class ReferenceTests(unittest.TestCase):
    def test_failure_checkpoint_is_private_incomplete_and_preserves_two_files(self):
        created=[];logged=[]
        private={'entity':'fixture-entity','project':'hasla-ai-private-training'}
        class Artifact:
            def __init__(self,name,type,metadata):
                self.qualified_name=f"fixture-entity/hasla-ai-private-training/{name}:v0";self.metadata=metadata;self.files=[];created.append(self)
            def add_file(self,path,name):self.files.append(name)
            def wait(self,timeout):self.timeout=timeout
        env={'RUN':'hasla-private-books-123-solver','ARTIFACT':'hasla-private-books-123-solver-lora','HASLA_DATA_SHA256':'a'*64}
        config={'public_rationale_required':True,'role':'solver','base_model':'Qwen/QwQ-32B','offline_dpo_sha256':'b'*64}
        with tempfile.TemporaryDirectory() as temp,patch.object(pod,'assert_private_project',return_value=private):
            root=Path(temp);ref=root/'adapter-post-sft-reference';ref.mkdir()
            (ref/'adapter_config.json').write_bytes(b'{}');(ref/'adapter_model.safetensors').write_bytes(b'synthetic-unverified-weight')
            result=pod.preserve_failure_checkpoint(env,root,private,SimpleNamespace(log_artifact=logged.append),SimpleNamespace(Artifact=Artifact),config)
            self.assertFalse(result['training_complete']);self.assertTrue(result['tensor_verification_pending'])
            self.assertEqual(created[0].timeout,120);self.assertTrue(created[0].metadata['private'])
            self.assertEqual(created[0].files,list(verifier.FILES));self.assertEqual(len(logged),1)
            created.clear()
            with patch.object(pod,'assert_private_project',side_effect=ValueError('privacy-unknown')):
                with self.assertRaises(ValueError):pod.preserve_failure_checkpoint(env,root,private,SimpleNamespace(log_artifact=logged.append),SimpleNamespace(Artifact=Artifact),config)
            self.assertEqual(created,[])

    def test_receipt_requires_real_unchanged_reference_full_updates_and_no_evaluation(self):
        for validate in (pod.validated_offline_dpo_receipt,verifier.validated_offline_dpo_receipt):
            value=receipt();self.assertEqual(validate(value),value)
            for key,replacement in [('reference_after_cache_parameter_sha256','9'*64),('optimizer_steps_completed',0),
                ('model_generation_calls',1),('reference_kind','adapter_disabled_base'),('gradient_norm_min',0.0),('relative_weight_change_verified',False)]:
                bad=copy.deepcopy(value);bad[key]=replacement
                with self.assertRaises(ValueError):validate(bad)

    def test_actual_private_reference_download_and_independent_numeric_delta(self):
        fixture=Fixture('solver',model=adapter(rank=16,bits=[0x40000000]+[0]*15));result=fixture.results['solver']
        reference=f'fixture-entity/{verifier.PROJECT}/hasla-private-books-123-solver-lora-post-sft-reference:v0'
        config=json.dumps({'peft_type':'LORA','r':16,'base_model_name_or_path':'Qwen/QwQ-32B'}).encode()
        blobs={'adapter_config.json':config,'adapter_model.safetensors':adapter(rank=16,bits=[0x3f800000]+[0]*15)}
        inventory=[{'name':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in blobs.items()]
        entries={name:Entry(name,data,fixture.downloads) for name,data in blobs.items()}
        def get_entry(name):entries[name].parent_bound=True;return entries[name]
        artifact=SimpleNamespace(qualified_name=reference,type='lora-reference',state='COMMITTED',is_link=False,
          metadata={'private':True,'phase':'post_source_sft_before_offline_dpo','run':'hasla-private-books-123-solver','files':inventory},
          manifest=SimpleNamespace(entries=entries),get_entry=get_entry)
        fixture.artifacts[reference]=artifact
        value=receipt();value.update(reference_files=inventory,final_adapter_model_sha256=result['adapter_files'][1]['sha256'])
        result.update(offline_dpo_training=value,post_sft_reference_artifact=reference)
        with tempfile.TemporaryDirectory() as temp,patch.object(verifier,'validated_offline_dpo_receipt',lambda value:value):
            root=Path(temp)/'solver';root.mkdir();(root/'adapter_model.safetensors').write_bytes(fixture.artifacts[result['artifact']].manifest.entries['adapter_model.safetensors'].data)
            output=verifier.verify_post_sft_reference(fixture,fixture,'fixture-entity','123','solver',result,root)
            self.assertTrue(output['dpo_relative_weight_change_verified']);self.assertEqual(output['dpo_b_changed_tensors'],1)
        self.assertEqual(set(fixture.downloads),set(verifier.FILES))

    def test_reference_namespace_rejected_without_download(self):
        value={'offline_dpo_training':receipt(),'post_sft_reference_artifact':'other/project/wrong:v0'}
        with patch.object(verifier,'validated_offline_dpo_receipt',lambda value:value):
            with self.assertRaises(verifier.VerificationError):
                verifier.verify_post_sft_reference(None,None,'fixture-entity','123','solver',value,Path('unused'))

if __name__=='__main__':unittest.main()

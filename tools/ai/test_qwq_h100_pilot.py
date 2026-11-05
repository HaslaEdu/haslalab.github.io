import copy,json,unittest
from decimal import Decimal
from unittest.mock import patch
import private_dual_run as inputs
import private_dedicated_run as parent
import private_dual_pod as child
import private_pod_train as pod
import private_verify_adapter as verifier
from role_config import validate_role_format

def manifest():
    return {'budget_krw':100000,'authorized_budget_krw':100000,'prior_upper_krw':0,'selected_roles':['solver'],
      'runpod_usd_policy':{'total_limit':'60','prior_spent_or_reserved':'0.1147826087'},
      'train_script_sha256':'a'*64,'role_config_sha256':'b'*64,'pod_script_sha256':'c'*64,'public_rationale_script_sha256':'d'*64,'offline_dpo_script_sha256':'a'*64,
      'roles':{'solver':{'format':'chat','sft_epochs':3,'assistant_only_loss':'required','runtime_seconds':12000,
          'offline_dpo':{'parts':1,'encoded_sha256':'b'*64,'raw_sha256':'c'*64,'raw_bytes':100,'records':2,'review_sha256':'d'*64},'gpu_ids':['NVIDIA H100 80GB HBM3'],'gpu_usd_per_hour_upper':'4','train':{'raw_sha256':'e'*64},'validation':{'raw_sha256':'f'*64}}}}

def labels():
    return {'version':3,'assistant_only_loss':True,'assistant_loss_status':'official_qwq_public_rationale_responses_only_verified',
      'selected_template_sha256':'16488ad69d85833e5f66c50174f39834b688343337e9337f018deaa21b354117',
      'processor_class':'Tokenizer','tokenizer_class':'Tokenizer','mask_probe_dimensions':2,'mask_probe_batch_size':1,
      'mask_probe_token_count':2000,'mask_probe_assistant_tokens':800,'mask_method':'official_qwq_public_rationale_responses_only',
      'mask_helper_sha256':'a'*64,'public_rationale_helper_sha256':'b'*64,'records_verified':33,
      'trainer_assistant_only_loss':False,'trainer_completion_only_loss':False}

def report():
    fixed={'gpu_count':1,'gpu_name':'NVIDIA H100 80GB HBM3','physical_vram_bytes':80*1024**3,'cpu_or_disk_offload_used':False,
      'dense_quantization_verified':True,'dense_layers':64,'quantized_linear_tensors':448,'base_parameters_frozen':True,
      'first_optimizer_step_completed':True,'first_step_peak_allocated_bytes':30*1024**3,'first_step_peak_reserved_bytes':40*1024**3}
    return {'role':'solver','training_records':29,'validation_records':4,'steps_completed':12,
      'initial_adapter_model_sha256':'5b4c2e755930a30298927cdf905fd158c4745473eea7c41f87630183729d0112',
      'label_diagnostics':labels(),'qwq_sft_provenance':{'version':1,
        'foundation_revision':'976055f8c83f394f35dbd3ab09a285a984907bd0','public_rationale_helper_sha256':'b'*64,
        'model_evaluations_performed':0,'quality_evaluation_deferred':True,'epochs_requested':3,'epochs_completed':3.0,
        'trainer_max_steps':-1,'training_records':29,'validation_records':4,'data_derived_optimizer_steps_upper':12,'runtime':fixed}}

class H100PilotTests(unittest.TestCase):
    def test_only_prepaid_pool_limits_no_obsolete_eight_dollar_or_fifty_minute_gate(self):
        value=manifest();ledger,quote,seconds,gpus=inputs.resource_settings(value,'solver')
        self.assertEqual(seconds,12000);self.assertEqual(gpus,['NVIDIA H100 80GB HBM3'])
        self.assertGreater(quote.hourly_usd_upper*Decimal(seconds*2)/3600*ledger.policy.tax_multiplier,8)
        self.assertIsNone(parent.sibling_allowance({'HASLA_TRAINING_ROLE':'both'},value))
        for mutate in ('wallet','gpu','epochs','loss'):
            bad=copy.deepcopy(value)
            if mutate=='wallet':bad['runpod_usd_policy']['prior_spent_or_reserved']='40'
            if mutate=='gpu':bad['roles']['solver']['gpu_ids']=['NVIDIA A40']
            if mutate=='epochs':bad['roles']['solver']['sft_epochs']=2
            if mutate=='loss':bad['roles']['solver']['assistant_only_loss']='auto'
            with self.assertRaises(ValueError):inputs.resource_settings(bad,'solver')

    def test_three_natural_epochs_and_data_derived_upper_bound_without_step_target(self):
        config=pod.data_bounded_settings(validate_role_format('solver','chat'),29,epochs=3)
        config.update(public_rationale_required=True,offline_dpo_path='private-dpo.jsonl',offline_dpo_sha256='a'*64,offline_dpo_review_sha256='b'*64)
        self.assertEqual(config['max_steps'],-1);self.assertEqual(config['data_derived_optimizer_steps_upper'],12)
        command=pod.training_command('script','train','out','held',config,'chat')
        for flag,value in [('--epochs','3'),('--max-steps','-1'),('--assistant-only-loss','required'),('--max-len','4096')]:
            self.assertEqual(command[command.index(flag)+1],value)

    def test_epoch_and_selective_loss_job_require_one_pinned_source_helper(self):
        value=manifest();env={'GITHUB_SHA':'a'*40,'HF_TOKEN':'synthetic','WANDB_API_KEY':'synthetic','HASLA_SOLVER_DPO_00':'synthetic'}
        observed=parent.pod_environment(env,value,'synthetic','solver','synthetic-solver','synthetic/hasla-ai-private-training/input:v0',12000)
        job=json.loads(observed['HASLA_ROLE_JOBS'])[0]
        self.assertEqual(job['sft_epochs'],3);self.assertEqual(job['runtime_seconds'],11400)
        self.assertEqual(observed['HASLA_PUBLIC_RATIONALE_SCRIPT_SHA256'],'d'*64)
        self.assertNotIn('HASLA_MATCHED_EVAL_SCRIPT_SHA256',observed)
        child.role_jobs(observed)
        observed.pop('HASLA_PUBLIC_RATIONALE_SCRIPT_SHA256')
        with self.assertRaises(ValueError):child.role_jobs(observed)

    def test_version_three_label_boundary_proof_and_source_rationale_pin_are_strict(self):
        value=labels()
        for validate in (pod.validated_label_diagnostics,verifier.validated_label_diagnostics):
            self.assertEqual(validate(value,'chat'),value)
            for key,replacement in [('public_rationale_helper_sha256','bad'),('version',2),('trainer_completion_only_loss',True),('selected_template_sha256','c'*64)]:
                bad=copy.deepcopy(value);bad[key]=replacement
                with self.assertRaises(ValueError):validate(bad,'chat')

    def test_continued_source_checkpoint_optimizer_proof_and_no_model_evaluation(self):
        value=report()
        for validate in (pod.validated_qwq_sft_receipts,verifier.validated_qwq_sft_receipts):
            self.assertEqual(validate(value,'solver')['qwq_sft_provenance'],value['qwq_sft_provenance'])
            for mutation in ('reset','evaluation','steps','offload','missing','partial'):
                bad=copy.deepcopy(value)
                if mutation=='reset':bad['initial_adapter_model_sha256']='c'*64
                if mutation=='evaluation':bad['qwq_matched_evaluation']={}
                if mutation=='steps':bad['steps_completed']=13
                if mutation=='offload':bad['qwq_sft_provenance']['runtime']['cpu_or_disk_offload_used']=True
                if mutation=='missing':bad.pop('qwq_sft_provenance')
                if mutation=='partial':bad['qwq_sft_provenance']['epochs_completed']=2.5
                with self.assertRaises(ValueError):validate(bad,'solver')

if __name__=='__main__':unittest.main()

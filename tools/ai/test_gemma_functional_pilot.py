import copy
import hashlib
import json
import unittest
import contextlib
from unittest.mock import patch
from types import SimpleNamespace

import train_lora as trainer
import private_dual_run as inputs
import private_dedicated_run as parent
import private_dual_pod as child
import private_pod_train as pod
import private_verify_adapter as verifier


class Tokenizer:
    chat_template = 'synthetic-reviewed-template'
    def apply_chat_template(self, messages, add_generation_prompt=False, **kwargs):
        text = '<bos><|turn>user\n' + messages[-1 if add_generation_prompt else -2]['content'] + '<turn|>\n' + trainer.GEMMA_RESPONSE_PREFIX
        return text if add_generation_prompt else text + messages[-1]['content'] + '<turn|>\n'
    def encode(self, text, **kwargs):return list(text.encode())


def helper(_, tokenizer, instruction_part, response_part, force_match, return_function):
    assert instruction_part == '<|turn>user\n' and response_part == trainer.GEMMA_RESPONSE_PREFIX
    assert force_match is True and return_function is True
    def mask(batch):
        labels=[]
        for ids in batch['input_ids']:
            raw=bytes(ids);boundary=raw.index(response_part.encode())+len(response_part.encode())
            labels.append([-100]*boundary+ids[boundary:])
        return {'labels':labels}
    return mask


def row():return {'messages':[{'role':'user','content':'Synthetic task.'},{'role':'assistant','content':'create'}]}
def manifest():
    return {'budget_krw':100000,'authorized_budget_krw':100000,'prior_upper_krw':0,'selected_roles':['chat'],
      'runpod_usd_policy':{'total_limit':'60','cycle_limit':'3','prior_spent_or_reserved':'0'},
      'train_script_sha256':'c'*64,'role_config_sha256':'d'*64,'pod_script_sha256':'e'*64,
      'roles':{'chat':{'format':'chat','training_profile':'gemma-26b-qlora-v1','assistant_only_loss':'required',
          'runtime_seconds':3600,'gpu_ids':['NVIDIA A40'],'gpu_usd_per_hour_upper':'0.7',
          'train':{'raw_sha256':'a'*64},'validation':{'raw_sha256':'b'*64}}}}


def diagnostics():
    return {'version':2,'assistant_only_loss':True,'assistant_loss_status':'official_gemma_responses_only_verified',
      'selected_template_sha256':trainer.GEMMA_FORMATTER_TEMPLATE_SHA256,'processor_class':'SyntheticTokenizer',
      'tokenizer_class':'SyntheticTokenizer','mask_probe_dimensions':2,'mask_probe_batch_size':1,
      'mask_probe_token_count':30,'mask_probe_assistant_tokens':3,'mask_method':'official_gemma_responses_only',
      'mask_helper_sha256':'d'*64,'records_verified':38,'trainer_assistant_only_loss':False,'trainer_completion_only_loss':False}


class FunctionalPilotTests(unittest.TestCase):
    def test_generation_is_greedy_bounded_and_restores_parameter_modes(self):
        class Tensor:
            def __init__(self,value):self.value=value
            def tolist(self):return self.value
        class Parameter:
            def __init__(self,flag):self.requires_grad=flag
            def requires_grad_(self,flag):self.requires_grad=flag
        class Model:
            training=True
            def __init__(self):self.params=[Parameter(True),Parameter(False)];self.fail=False
            def parameters(self):return iter(self.params)
            def eval(self):self.training=False
            def train(self,flag):self.training=flag
            def generate(self,**kwargs):
                self.assertions=(kwargs['max_new_tokens']==16 and kwargs['do_sample'] is False)
                self.params[0].requires_grad=False
                if self.fail:raise RuntimeError('synthetic')
                return Tensor([kwargs['input_ids'].tolist()[0]+list(b'chat')])
        model=Model();torch=SimpleNamespace(long='long',tensor=lambda value,**k:Tensor(value),ones_like=lambda value:value,no_grad=contextlib.nullcontext)
        tokenizer=SimpleNamespace(decode=lambda ids,**kwargs:bytes(ids).decode())
        rows=[{'id':str(i),'metadata':{'curriculum_mode':'intent_classifier'},'messages':[{'role':'assistant','content':'chat'}]} for i in range(8)]
        prepared=[{'input_ids':[1,2,3],'labels':[-100,-100,3]} for _ in rows]
        result=trainer.evaluate_gemma_routing(model,tokenizer,torch,rows,prepared)
        self.assertEqual(result['correct'],8);self.assertTrue(model.assertions)
        self.assertTrue(model.training);self.assertEqual([p.requires_grad for p in model.params],[True,False])
        model.fail=True
        with self.assertRaises(RuntimeError):trainer.evaluate_gemma_routing(model,tokenizer,torch,rows,prepared)
        self.assertTrue(model.training);self.assertEqual([p.requires_grad for p in model.params],[True,False])

    def test_native_text_labels_and_template_are_preserved(self):
        tok=Tokenizer();raw=copy.deepcopy(row())
        with patch.object(trainer,'GEMMA_FORMATTER_TEMPLATE_SHA256',hashlib.sha256(tok.chat_template.encode()).hexdigest()):
            actual=trainer.gemma_response_only_rows(tok,[raw],helper,1024)[0]
        self.assertEqual(raw,row());self.assertEqual(tok.chat_template,Tokenizer.chat_template)
        boundary=next(i for i,v in enumerate(actual['labels']) if v!=-100)
        self.assertTrue(all(v==-100 for v in actual['labels'][:boundary]))
        self.assertEqual(actual['labels'][boundary:],actual['input_ids'][boundary:])

    def test_wrong_mask_or_truncation_or_control_tokens_rejected(self):
        tok=Tokenizer()
        with patch.object(trainer,'GEMMA_FORMATTER_TEMPLATE_SHA256',hashlib.sha256(tok.chat_template.encode()).hexdigest()):
            with self.assertRaises(ValueError):trainer.gemma_response_only_rows(tok,[row()],helper,2)
            with self.assertRaises(ValueError):trainer.gemma_response_only_rows(tok,[row()],lambda *a,**k:lambda b:{'labels':b['input_ids']},1024)
            bad=row();bad['messages'][-1]['content']='<turn|> leaked'
            with self.assertRaises(ValueError):trainer.gemma_response_only_rows(tok,[bad],helper,1024)

    def test_actual_collator_padding_and_labels_are_checked(self):
        value={'input_ids':[1,2,3],'attention_mask':[1,1,1],'labels':[-100,-100,3]}
        good=lambda rows:{'input_ids':[[1,2,3,0]],'labels':[[-100,-100,3,-100]]}
        trainer.verify_response_only_collation(good,[value])
        for labels in [[1,2,3,-100],[-100,-100,3,0]]:
            with self.assertRaises(ValueError):trainer.verify_response_only_collation(lambda rows:{'input_ids':[[1,2,3,0]],'labels':[labels]},[value])

    def test_usd_cap_and_default_queue_allow_one_gemma_pod(self):
        value=manifest();ledger,quote,seconds,gpus=inputs.resource_settings(value,'chat')
        self.assertEqual(seconds,3600);self.assertEqual(gpus,['NVIDIA A40'])
        self.assertIsNone(parent.sibling_allowance({'HASLA_TRAINING_ROLE':'both'},value))
        self.assertLess(quote.hourly_usd_upper*2*ledger.policy.tax_multiplier,3)
        for change in ('prior','quote','loss','sibling','roles'):
            bad=copy.deepcopy(value)
            if change=='prior':bad['runpod_usd_policy']['prior_spent_or_reserved']='59'
            if change=='quote':bad['roles']['chat']['gpu_usd_per_hour_upper']='0.71'
            if change=='loss':bad['roles']['chat'].pop('assistant_only_loss')
            if change=='sibling':bad['sibling_allowance']={}
            if change=='roles':bad['selected_roles']=['solver']
            with self.assertRaises(ValueError):inputs.resource_settings(bad,'chat')

    def test_required_loss_reaches_job_and_trainer_command(self):
        env={'GITHUB_SHA':'a'*40,'HF_TOKEN':'synthetic','WANDB_API_KEY':'synthetic'}
        result=parent.pod_environment(env,manifest(),'synthetic','chat','synthetic-chat','synthetic/hasla-ai-private-training/input:v0',3600)
        job=json.loads(result['HASLA_ROLE_JOBS'])[0]
        self.assertEqual(job['assistant_only_loss'],'required')
        child.role_jobs(result)
        config={'role':'chat','training_profile':'gemma-26b-qlora-v1','default_rank':8,'max_steps':4,'max_length':1024,'assistant_only_loss_required':True}
        command=pod.training_command('script','train','out','validation',config,'chat')
        self.assertEqual(command[command.index('--assistant-only-loss')+1],'required')
        self.assertEqual(command[command.index('--epochs')+1],'1')
        bad=copy.deepcopy(job);bad['assistant_only_loss']='auto'
        with self.assertRaises(ValueError):child.role_jobs({'HASLA_ROLE_JOBS':json.dumps([bad])})

    def test_version_two_label_proof_is_strict_in_worker_and_verifier(self):
        value=diagnostics()
        for validate in (pod.validated_label_diagnostics,verifier.validated_label_diagnostics):
            self.assertEqual(validate(value,'chat'),value)
            for key,replacement in [('version',1),('assistant_only_loss',False),('records_verified',0),('trainer_completion_only_loss',True),('selected_template_sha256','0'*64)]:
                bad=copy.deepcopy(value);bad[key]=replacement
                with self.assertRaises(ValueError):validate(bad,'chat')
        for validate in (pod.validated_gemma_receipts,verifier.validated_gemma_receipts):
            with self.assertRaises(ValueError):
                validate({'label_diagnostics':value},'chat','gemma-26b-qlora-v1',30,8,'a'*64)

    def test_exact_cohort_has_no_arbitrary_authored_bypass(self):
        value={'id':'synthetic-reviewed','review_status':'approved','messages':row()['messages'],
          'metadata':{'dataset_version':'synthetic-cohort','review_status':'approved','review_receipt_sha256':'f'*64,
            'provenance_type':'authored_runtime_routing_diagnostic_v1','split':'validation'}}
        trusted={'dataset_version':'synthetic-cohort','review_receipt_sha256':'f'*64,
          'row_sha256':{value['id']:inputs._authored_chat_sha(value)},'splits':{value['id']:'validation'}}
        with patch.object(inputs,'_FUNCTIONAL_CHAT_COHORT',trusted):
            inputs.validate_functional_chat(value)
            bad=copy.deepcopy(value);bad['messages'][-1]['content']='changed'
            with self.assertRaises(ValueError):inputs.validate_functional_chat(bad)

    def test_functional_metric_counts_and_case_identity_are_recomputed(self):
        cases=[{'id_sha256':f'{i:064x}','target':'chat','prediction':'chat','generated_tokens':2,'correct':True} for i in range(8)]
        value={'version':1,'method':'native_gemma_greedy_routing_v1','validation_sha256':'a'*64,
          'validation_records':8,'max_new_tokens':16,'before':{'correct':8,'valid_labels':8,'cases':cases},'after':{'correct':8,'valid_labels':8,'cases':copy.deepcopy(cases)}}
        for validate in (pod.validated_functional_evaluation,verifier.validated_functional_evaluation):
            self.assertEqual(validate(value,'a'*64,8),value)
            for mutate in ('count','raw','identity'):
                bad=copy.deepcopy(value)
                if mutate=='count':bad['after']['correct']=0
                if mutate=='raw':bad['after']['cases'][0]['prediction']='unbounded raw answer'
                if mutate=='identity':bad['after']['cases'][0]['id_sha256']='f'*64
                with self.assertRaises(ValueError):validate(bad,'a'*64,8)


if __name__=='__main__':unittest.main()

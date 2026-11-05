"""Offline preference updates from reviewed public teacher proofs; no generation."""
import hashlib,json,math,re
from pathlib import Path

TEMPLATE_SHA256='16488ad69d85833e5f66c50174f39834b688343337e9337f018deaa21b354117'
RESPONSE_PREFIX='<|im_start|>assistant\n<think>\n'
PROVIDERS={'deepseek':'deepseek-v4-pro','openai':'gpt-6.1-terra','gemini':'gemini-3.8-flash'}

def require(ok,code):
    if not ok:raise ValueError(code)

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def sha(value):return hashlib.sha256(value).hexdigest()
def file_sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def digest(value):return isinstance(value,str) and re.fullmatch('[a-f0-9]{64}',value) is not None

def validate_rows(rows):
    require(type(rows) is list and len(rows)>0,'nonempty_reviewed_preferences_required')
    seen=set()
    for row in rows:
        require(type(row) is dict and set(row)=={'id','prompt_messages','chosen','rejected','metadata'},'invalid_preference_row')
        meta=row['metadata'];prompt=row['prompt_messages']
        require(isinstance(row['id'],str) and row['id'] and row['id'] not in seen,'duplicate_preference_identity');seen.add(row['id'])
        require(type(prompt) is list and len(prompt)==2 and all(type(m) is dict and set(m)=={'role','content'}
          and m['role']==role and isinstance(m['content'],str) and m['content'].strip() for m,role in zip(prompt,('system','user'))),'complete_same_problem_prompt_required')
        require(type(meta) is dict and meta.get('fixture') is False and meta.get('teacher_generated') is True
          and meta.get('both_correct_complete') is True and meta.get('all_providers_requested')==list(PROVIDERS)
          and all(digest(meta.get(k)) for k in ('question_sha256','record_sha256','handler_sha256','independent_review_sha256','root_approval_sha256'))
          and sha(prompt[-1]['content'].encode())==meta['question_sha256']
          and meta.get('group_id')=='teacher-problem:'+meta['question_sha256'] and isinstance(meta.get('tokenizer'),dict)
          and meta['tokenizer'].get('model')=='Qwen/QwQ-32B'
          and meta['tokenizer'].get('tokenizer_config_sha256')=='ab43f460108ca40fbb09fa537696baf862b6a9b46a2c6688b9de711293e3ddc4'
          and meta['tokenizer'].get('tokenizer_sha256')=='19564a48c4f71a2a1b937cce34c737a1e662b171c5f5d7edf641a15cd896f07d'
          and meta['tokenizer'].get('truncation') is False,
          'independently_reviewed_real_teacher_preferences_required')
        require(type(meta.get('chosen_public_tokens')) is int and type(meta.get('rejected_public_tokens')) is int
          and 0<meta['chosen_public_tokens']<meta['rejected_public_tokens'],'actual_shorter_complete_public_proof_required')
        providers=[]
        for mode in ('chosen','rejected'):
            choice=row[mode];require(type(choice) is dict and set(choice)=={'core','public_rationale','teacher_provenance'},'invalid_public_teacher_choice')
            core=choice['core'];rationale=choice['public_rationale'];provenance=choice['teacher_provenance']
            require(type(core) is dict and type(core.get('blocks')) is list and core['blocks']
              and all(type(b) is dict and isinstance(b.get('text'),str) and b['text'].strip() for b in core['blocks'])
              and isinstance(rationale,str) and rationale=='\n\n'.join(b['text'] for b in core['blocks']), 'unchanged_public_core_and_derivation_required')
            require(type(provenance) is dict and provenance.get('provider') in PROVIDERS
              and provenance.get('requested_model')==PROVIDERS[provenance['provider']]
              and isinstance(provenance.get('reported_model'),str) and (provenance['reported_model']==PROVIDERS[provenance['provider']]
                or provenance['reported_model'].startswith(PROVIDERS[provenance['provider']]+'-'))
              and isinstance(provenance.get('response_id'),str) and provenance['response_id']
              and digest(provenance.get('request_sha256')) and digest(provenance.get('output_sha256'))
              and isinstance(provenance.get('usage'),dict),'actual_teacher_provenance_required')
            providers.append(provenance['provider'])
            text=canonical(core).decode()+rationale+''.join(m['content'] for m in prompt)
            require(not any(token in text for token in ('<think>','</think>','<|','|>')),'source_contains_reasoning_or_chat_control_tokens')
        require(providers[0]!=providers[1],'independent_teacher_choices_required')
    return rows

def read_rows(path,expected_sha):
    path=Path(path);require(digest(expected_sha) and not path.is_symlink() and path.is_file()
      and 0<path.stat().st_size<=16*1024**2 and file_sha(path)==expected_sha,'preference_file_pin_mismatch')
    return validate_rows([json.loads(line) for line in path.read_text(encoding='utf8').splitlines() if line.strip()])

def prepare_pairs(processor,rows,official_mask_helper,max_length=16384):
    validate_rows(rows);tokenizer=getattr(processor,'tokenizer',processor)
    template=getattr(processor,'chat_template',None)
    require(isinstance(template,str) and sha(template.encode())==TEMPLATE_SHA256,'official_qwq_template_required')
    masker=official_mask_helper(None,tokenizer=processor,instruction_part='<|im_start|>user\n',response_part=RESPONSE_PREFIX,force_match=True,return_function=True)
    require(callable(masker),'official_selective_loss_helper_required')
    prepared=[]
    for row in rows:
        prompt=processor.apply_chat_template(row['prompt_messages'],tokenize=False,add_generation_prompt=True)
        require(isinstance(prompt,str) and prompt.endswith(RESPONSE_PREFIX),'official_qwq_native_prefix_required')
        prefix=tokenizer.encode(prompt,add_special_tokens=False);item={'id_sha256':sha(row['id'].encode()),'question_sha256':row['metadata']['question_sha256']}
        for mode in ('chosen','rejected'):
            choice=row[mode];content='<think>\n'+choice['public_rationale']+'\n</think>\n'+canonical(choice['core']).decode()
            public_count=len(tokenizer.encode(choice['public_rationale'],add_special_tokens=False))
            require(public_count==row['metadata'][mode+'_public_tokens'],'actual_public_proof_token_count_mismatch')
            full=processor.apply_chat_template(row['prompt_messages']+[{'role':'assistant','content':content}],tokenize=False,add_generation_prompt=False)
            ids=tokenizer.encode(full,add_special_tokens=False)
            require(isinstance(full,str) and full.startswith(prompt) and isinstance(ids,list) and ids[:len(prefix)]==prefix
              and 0<len(prefix)<len(ids)<=max_length,'native_preference_prefix_or_context_invalid')
            eos=tokenizer.eos_token_id;require(type(eos) is int and ids[len(prefix):].count(eos)==1,'single_complete_assistant_eos_required')
            end=ids.index(eos,len(prefix))+1
            require(end==len(ids) or tokenizer.decode(ids[end:]).isspace(),'text_after_assistant_eos')
            expected=[-100]*len(prefix)+ids[len(prefix):end]+[-100]*(len(ids)-end)
            require(masker({'input_ids':[ids]}).get('labels')==[expected],'official_preference_mask_mismatch')
            item[mode]={'input_ids':ids,'attention_mask':[1]*len(ids),'labels':expected,'selected_tokens':end-len(prefix)}
        prepared.append(item)
    require(processor.chat_template==template,'preference_preparation_changed_template')
    return prepared

def sequence_logp(model,torch_module,row):
    # CausalLM.loss is the mean over nonignored shifted labels. Batch size is
    # exactly one, so multiplying by that count recovers SUM log probability.
    count=sum(v!=-100 for v in row['labels'][1:])
    require(count==row['selected_tokens'] and count>0,'causal_response_count_mismatch')
    device=next(model.parameters()).device
    ids=torch_module.tensor([row['input_ids']],dtype=torch_module.long,device=device)
    labels=torch_module.tensor([row['labels']],dtype=torch_module.long,device=device)
    output=model(input_ids=ids,attention_mask=torch_module.ones_like(ids),labels=labels,use_cache=False,return_dict=True)
    loss=output.loss
    require(loss.numel()==1 and bool(torch_module.isfinite(loss.detach()).all().item()),'nonfinite_preference_logp')
    return -loss.float()*count

def parameter_digest(model,torch_module):
    digest=hashlib.sha256();count=0
    for name,p in sorted(model.named_parameters(),key=lambda x:x[0]):
        if not p.requires_grad:continue
        require(re.search(r'(^|\.)lora_[AB](?=\.|$)',name) is not None,'only_lora_parameters_may_update')
        require(bool(torch_module.isfinite(p.detach()).all().item()),'nonfinite_trainable_parameter')
        digest.update(name.encode());digest.update(str(tuple(p.shape)).encode())
        digest.update(p.detach().cpu().contiguous().view(torch_module.uint8).numpy().tobytes());count+=1
    require(count>0,'no_trainable_lora_parameters');return digest.hexdigest(),count

def train_offline_dpo(model,processor,torch_module,prepared,reference_dir,source_sha):
    require(prepared and digest(source_sha),'real_preference_source_required')
    reference_dir=Path(reference_dir);require(not reference_dir.exists(),'reference_checkpoint_must_be_new')
    model.save_pretrained(str(reference_dir))
    reference_files=[{'name':n,'bytes':(reference_dir/n).stat().st_size,'sha256':file_sha(reference_dir/n)} for n in ('adapter_config.json','adapter_model.safetensors')]
    parameters=list(model.parameters());flags=[p.requires_grad for p in parameters];was_training=model.training
    dropouts=[(m,m.p) for m in model.modules() if isinstance(m,torch_module.nn.Dropout)]
    reference=[]
    losses=[];gradient_norms=[];steps=0
    try:
        for module,_ in dropouts:module.p=0.0
        before,count=parameter_digest(model,torch_module)
        model.eval()
        # No DPO optimizer exists until every reference likelihood is cached
        # on the SAME active, post-SFT adapter. Never disable its adapter.
        with torch_module.no_grad():
            for pair in prepared:
                values={mode:float(sequence_logp(model,torch_module,pair[mode]).detach().double().item()) for mode in ('chosen','rejected')}
                require(all(math.isfinite(v) for v in values.values()),'reference_logp_nonfinite');reference.append(values)
        after_cache,_=parameter_digest(model,torch_module)
        require(after_cache==before,'reference_caching_changed_adapter')
        active=[p for p in parameters if p.requires_grad]
        optimizer=torch_module.optim.AdamW(active,lr=5e-7,weight_decay=0.0)
        model.train()
        for _epoch in range(3):
            for pair,ref in zip(prepared,reference):
                optimizer.zero_grad(set_to_none=True)
                chosen=sequence_logp(model,torch_module,pair['chosen'])
                rejected=sequence_logp(model,torch_module,pair['rejected'])
                margin=(chosen-rejected)-(ref['chosen']-ref['rejected'])
                loss=-torch_module.nn.functional.logsigmoid(0.1*margin)
                require(bool(torch_module.isfinite(loss.detach()).all().item()),'dpo_loss_nonfinite')
                loss.backward()
                norm=torch_module.nn.utils.clip_grad_norm_(active,1.0,error_if_nonfinite=True)
                value=float(norm.detach().double().item());require(math.isfinite(value) and value>0,'dpo_has_no_finite_nonzero_gradient')
                optimizer.step();steps+=1;losses.append(float(loss.detach().double().item()));gradient_norms.append(value)
        after,_=parameter_digest(model,torch_module);require(after!=before,'offline_dpo_adapter_unchanged')
    finally:
        for module,probability in dropouts:module.p=probability
        for p,flag in zip(parameters,flags):p.requires_grad_(flag)
        model.train(was_training)
        require(all(p.requires_grad is flag for p,flag in zip(parameters,flags))
          and all(m.p==probability for m,probability in dropouts) and model.training is was_training,'training_modes_or_flags_not_restored')
    return {'version':1,'method':'post_sft_frozen_reference_offline_dpo_v1','data_sha256':source_sha,'pairs':len(prepared),
      'epochs':3,'beta':0.1,'learning_rate':5e-7,'optimizer_steps_completed':steps,'expected_optimizer_steps':3*len(prepared),
      'reference_kind':'same_active_post_sft_adapter_cached_sum_logps','reference_cached_before_optimizer':True,
      'reference_adapter_parameter_sha256':before,'reference_after_cache_parameter_sha256':after_cache,
      'final_adapter_parameter_sha256':after,'trainable_lora_tensors':count,'reference_files':reference_files,
      'reference_logps_sha256':sha(canonical(reference)),'loss_last':losses[-1],'loss_mean':sum(losses)/len(losses),
      'gradient_norm_min':min(gradient_norms),'gradient_norm_max':max(gradient_norms),
      'dropout_disabled_during_reference_and_policy':True,'weights_updated':True,'model_generation_calls':0,
      'performance_evaluations':0,'quality_verified':False,'production_promoted':False}

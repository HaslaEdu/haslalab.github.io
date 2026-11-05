"""Trusted rendering of attributed PUBLIC worked solutions, not private thoughts.

The caller must bind the reviewed cohort manifest. This helper checks internal
source linkage and loss boundaries; it does not certify arbitrary mathematics.
No model/provider/network imports. The official QwQ template remains unchanged.
"""
import hashlib,json,re,unicodedata

TEMPLATE_SHA256='16488ad69d85833e5f66c50174f39834b688343337e9337f018deaa21b354117'
RESPONSE_PREFIX='<|im_start|>assistant\n<think>\n'
CONTROL=re.compile(r'<\|[^\n]*?\|>|</?think>',re.I)
SHA=re.compile(r'[0-9a-f]{64}\Z')
HEAT_SOURCE_SHA256='c272fa5e1034402550fc2d64ab6090e0bedc32c29d4f5f4d68a70575b45118e1'
HEAT_REVIEW_SHA256='db18b18efef1828ad5091c579bb3b733538817493b190ddb015ab6ac3b2b6f06'

def require(value,code):
    if not value:raise ValueError(code)
def digest(text):return hashlib.sha256(text.encode('utf8')).hexdigest()
def strict_object(raw):
    def pairs(items):
        value={}
        for key,item in items:
            require(key not in value,'duplicate_final_json_key');value[key]=item
        return value
    def invalid(_):raise ValueError('nonfinite_final_json')
    try:return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)
    except ValueError:raise
    except Exception:raise ValueError('invalid_final_json') from None

def public_rationale_text(row):
    require(type(row) is dict,'public_rationale_row_invalid')
    meta=row.get('metadata');require(type(meta) is dict
      and meta.get('source_authorship') in ('source_transcription','authored_public_worked_example'),'public_rationale_attribution_required')
    require(meta.get('teacher_generated',False) is False and meta.get('contains_hidden_chain_of_thought',False) is False,'private_or_teacher_reasoning_forbidden')
    authored=meta['source_authorship']=='authored_public_worked_example'
    rationale=meta.get('public_rationale')
    require(type(rationale) is dict and set(rationale)=={'version','kind','language','text','sha256','source_evidence'}
      and type(rationale['version']) is int and rationale['version']==1
      and rationale['kind']=='source_public_worked_derivation' and rationale['language']=='en','public_rationale_schema_invalid')
    text=rationale['text'];require(type(text) is str and text.strip() and len(text)<=64000 and not CONTROL.search(text),'public_rationale_text_invalid')
    require(all(not c.isalpha() or any(s in unicodedata.name(c,'') for s in ('LATIN','GREEK','MATHEMATICAL')) for c in text),'public_rationale_english_required')
    evidence=rationale['source_evidence'];require(type(evidence) is dict,'public_rationale_evidence_invalid')
    if authored:
        require(set(evidence)=={'provenance_type','source_sha256','source_path','text_sha256','review_receipt_sha256'}
          and evidence['provenance_type']=='authored_physics_curriculum_v1' and evidence['source_sha256']==HEAT_SOURCE_SHA256
          and evidence['review_receipt_sha256']==meta.get('review_receipt_sha256')==HEAT_REVIEW_SHA256
          and type(evidence['source_path']) is str and evidence['source_path'].replace('\\','/')=='C:/Users/andre/CodexWork/HaslaLab/operations/hasla-heat-exchange-20261105/reviewed_examples.json'
          and meta.get('authored') is True and meta.get('input_language')=='en' and meta.get('target_language')=='en'
          and meta.get('teacher_generated') is False and meta.get('contains_hidden_chain_of_thought') is False,'authored_public_rationale_provenance_invalid')
    else:
        require(meta.get('language')=='en' and set(evidence)=={'locator','solution_id','source_id','source_sha256','text_sha256'}
          and type(evidence['source_sha256']) is str and SHA.fullmatch(evidence['source_sha256'])
          and type(evidence['locator']) is str and 0<len(evidence['locator'])<=500 and not any(ord(c)<32 for c in evidence['locator'])
          and type(evidence['source_id']) is str and re.fullmatch(r'src_[0-9a-f]{64}',evidence['source_id'])
          and type(evidence['solution_id']) is str and re.fullmatch(r'sol_[0-9a-f]{64}',evidence['solution_id']),'public_rationale_evidence_invalid')
        require(evidence==meta.get('source_evidence',{}).get('solution') and evidence['solution_id']==meta.get('solution_id')
          and evidence['source_id'] in row.get('source_ids',[]),'public_rationale_source_link_mismatch')
    require(type(rationale['sha256']) is str and SHA.fullmatch(rationale['sha256'])
      and digest(text)==rationale['sha256']==evidence['text_sha256'],'public_rationale_hash_mismatch')
    messages=row.get('messages');require(type(messages) is list and [m.get('role') for m in messages] in
      (['user','assistant'],['system','user','assistant']),'public_rationale_turn_invalid')
    require(all(type(m.get('content')) is str and not CONTROL.search(m['content']) for m in messages),'public_source_control_tokens_forbidden')
    final=strict_object(messages[-1]['content'])
    require(type(final) is dict and set(final)=={'version','domain','task','status','blocks','assessment','checks'}
      and type(final['version']) is int and final['version']==1 and final['domain']=='haslalab' and final['task'] in (('solve','concept') if authored else ('solve','explain'))
      and final['status']=='ok' and final['assessment'] is None and final['checks']==[],'public_final_core_invalid')
    blocks=final['blocks'];require(type(blocks) is list and 1<=len(blocks)<=50 and all(type(b) is dict and set(b)=={'id','kind','text'}
      and type(b['id']) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,100}',b['id']) and b['kind'] in ('reasoning','result','criticism')
      and type(b['text']) is str for b in blocks) and len({b['id'] for b in blocks})==len(blocks),'public_final_blocks_invalid')
    if authored:require('\n\n'.join(b['text'] for b in blocks)==text,'authored_public_rationale_not_exact_final')
    else:require(len(blocks)==1 and blocks[0]['id']=='source-reference' and blocks[0]['kind']=='reasoning'
      and blocks[0]['text']==text,'public_rationale_not_exact_source_reference')
    return text

def prepare_response_only_rows(processor,rows,official_mask_helper,max_length):
    template=getattr(processor,'chat_template',None)
    require(type(template) is str and digest(template)==TEMPLATE_SHA256,'official_qwq_template_required')
    require(type(rows) is list and rows,'nonempty_public_rationale_rows_required')
    require(callable(official_mask_helper) and type(max_length) is int and 1<=max_length<=16384,'public_rationale_mask_configuration_invalid')
    masker=official_mask_helper(None,tokenizer=processor,instruction_part='<|im_start|>user\n',response_part=RESPONSE_PREFIX,
      force_match=True,return_function=True)
    require(callable(masker),'official_response_masker_unavailable')
    tokenizer=getattr(processor,'tokenizer',processor);prepared=[]
    for row in rows:
        text=public_rationale_text(row);messages=row['messages'];copied=[dict(m) for m in messages]
        copied[-1]['content']='<think>\n'+text+'\n</think>\n'+messages[-1]['content']
        prompt=processor.apply_chat_template(messages[:-1],tokenize=False,add_generation_prompt=True)
        full=processor.apply_chat_template(copied,tokenize=False,add_generation_prompt=False)
        require(type(prompt) is str and type(full) is str and prompt.endswith(RESPONSE_PREFIX) and full.startswith(prompt),'public_rationale_prompt_prefix_invalid')
        require(full[len(prompt):].startswith(text+'\n</think>\n'+messages[-1]['content']),'public_rationale_rendered_content_changed')
        ids=tokenizer.encode(full,add_special_tokens=False);prefix=tokenizer.encode(prompt,add_special_tokens=False)
        require(type(ids) is list and type(prefix) is list and prefix and len(prefix)<len(ids)<=max_length and ids[:len(prefix)]==prefix
          and all(type(v) is int and v>=0 for v in ids),'public_rationale_no_truncation_or_prefix_failed')
        eos_id=getattr(tokenizer,'eos_token_id',None)
        require(type(eos_id) is int and eos_id in ids[len(prefix):],'public_rationale_eos_missing')
        end=ids.index(eos_id,len(prefix))+1
        require(end==len(ids) or tokenizer.decode(ids[end:]).isspace(),'public_rationale_nonwhitespace_after_eos')
        expected=[-100]*len(prefix)+ids[len(prefix):end]+[-100]*(len(ids)-end)
        labels=masker({'input_ids':[ids]}).get('labels')
        require(type(labels) is list and labels==[expected],'public_rationale_complete_loss_boundary_failed')
        prepared.append({'input_ids':ids,'attention_mask':[1]*len(ids),'labels':expected})
    require(getattr(processor,'chat_template',None)==template,'official_qwq_template_changed')
    return prepared

public_rationale_rows=prepare_response_only_rows

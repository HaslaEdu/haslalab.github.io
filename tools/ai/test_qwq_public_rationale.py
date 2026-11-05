"""Synthetic contracts only. Real tokenizer/collator audit is a separate receipt."""
import copy,hashlib,json,re,unittest
from unittest.mock import patch
import qwq_public_rationale as m
EOS='<|im_end|>'
def row():
 text='A public source worked derivation yields $x=1$.';digest=m.digest(text)
 evidence={'locator':'solutions/p1','solution_id':'sol_'+'a'*64,'source_id':'src_'+'b'*64,'source_sha256':'c'*64,'text_sha256':digest}
 core={'version':1,'domain':'haslalab','task':'solve','status':'ok','assessment':None,'checks':[],
  'blocks':[{'id':'source-reference','kind':'reasoning','text':text}]}
 return {'messages':[{'role':'user','content':'Solve the published case.'},{'role':'assistant','content':json.dumps(core)}],
  'source_ids':[evidence['source_id']],'metadata':{'language':'en','source_authorship':'source_transcription','solution_id':evidence['solution_id'],
  'source_evidence':{'solution':evidence},'public_rationale':{'version':1,'kind':'source_public_worked_derivation','language':'en','text':text,'sha256':digest,'source_evidence':evidence}}}
class Processor:
 chat_template='synthetic-only-template';eos_token_id=999999
 def encode(self,text,add_special_tokens=False):
  return [i for piece in re.split('('+re.escape(EOS)+')',text) if piece for i in ([self.eos_token_id] if piece==EOS else [ord(c) for c in piece])]
 def decode(self,ids):return ''.join(EOS if x==self.eos_token_id else chr(x) for x in ids)
 def apply_chat_template(self,msgs,tokenize=False,add_generation_prompt=False):
  prefix='<|im_start|>user\n'+msgs[0]['content']+EOS+'\n'
  return prefix+m.RESPONSE_PREFIX if add_generation_prompt else prefix+'<|im_start|>assistant\n'+msgs[-1]['content']+EOS+'\n'
def helper(_,tokenizer,instruction_part,response_part,force_match,return_function):
 assert force_match and return_function and instruction_part=='<|im_start|>user\n' and response_part==m.RESPONSE_PREFIX
 def mask(batch):
  ids=batch['input_ids'][0];text=tokenizer.decode(ids);n=len(tokenizer.encode(text[:text.index(response_part)+len(response_part)]));end=ids.index(tokenizer.eos_token_id,n)+1
  return {'labels':[[-100]*n+ids[n:end]+[-100]*(len(ids)-end)]}
 return mask
class Tests(unittest.TestCase):
 def test_nonempty_attributed_rationale_closer_final_and_eos_are_learned(self):
  r=row();original=copy.deepcopy(r);p=Processor()
  with patch.object(m,'TEMPLATE_SHA256',m.digest(p.chat_template)):out=m.prepare_response_only_rows(p,[r],helper,4096)[0]
  n=out['labels'].index(next(x for x in out['labels'] if x!=-100));learned=p.decode([x for x in out['labels'] if x!=-100])
  self.assertTrue(learned.startswith(r['metadata']['public_rationale']['text']+'\n</think>\n'))
  self.assertIn(r['messages'][-1]['content'],learned);self.assertTrue(learned.endswith(EOS));self.assertEqual(out['labels'][-1],-100)
  self.assertTrue(all(x==-100 for x in out['labels'][:n]));self.assertEqual(r,original);self.assertEqual(p.chat_template,'synthetic-only-template')
 def test_source_evidence_hash_authorship_and_final_binding_fail_closed(self):
  mutations=[lambda r:r['metadata']['public_rationale'].update(text='changed'),lambda r:r['metadata']['public_rationale']['source_evidence'].update(source_id='src_'+'d'*64),
   lambda r:r['metadata'].update(source_authorship='teacher_private_reasoning'),lambda r:r['metadata'].update(teacher_generated=True),
   lambda r:r['messages'][-1].update(content=r['messages'][-1]['content'].replace('source-reference','other'))]
  for fn in mutations:
   r=row();fn(r)
   with self.subTest(fn=fn),self.assertRaises(ValueError):m.public_rationale_text(r)
 def test_control_tokens_or_korean_cannot_be_smuggled_as_public_rationale(self):
  for bad in ('<think>private</think>','<|im_end|>','한국어'):
   r=row();r['metadata']['public_rationale']['text']=bad;r['metadata']['public_rationale']['sha256']=m.digest(bad);r['metadata']['public_rationale']['source_evidence']['text_sha256']=m.digest(bad)
   with self.assertRaises(ValueError):m.public_rationale_text(r)
 def test_no_truncation_missing_eos_and_dropped_labels_are_rejected(self):
  p=Processor()
  with patch.object(m,'TEMPLATE_SHA256',m.digest(p.chat_template)):
   with self.assertRaises(ValueError):m.prepare_response_only_rows(p,[row()],helper,10)
   with self.assertRaises(ValueError):m.prepare_response_only_rows(p,[],helper,4096)
   with self.assertRaises(ValueError):m.prepare_response_only_rows(p,[row()],lambda *a,**k:lambda batch:{'labels':[[-100]*len(batch['input_ids'][0])]},4096)
   p.eos_token_id=None
   with self.assertRaises((ValueError,TypeError)):m.prepare_response_only_rows(p,[row()],helper,4096)
 def test_official_template_is_required(self):
  with self.assertRaises(ValueError):m.prepare_response_only_rows(Processor(),[row()],helper,4096)
 def test_authored_heat_is_distinct_not_falsely_transcribed_or_teacher_generated(self):
  r=row();meta=r['metadata'];text=meta['public_rationale']['text'];meta.update(source_authorship='authored_public_worked_example',authored=True,input_language='en',target_language='en',teacher_generated=False,contains_hidden_chain_of_thought=False,review_receipt_sha256=m.HEAT_REVIEW_SHA256)
  meta['public_rationale']['source_evidence']={'provenance_type':'authored_physics_curriculum_v1','source_sha256':m.HEAT_SOURCE_SHA256,'source_path':'C:/Users/andre/CodexWork/HaslaLab/operations/hasla-heat-exchange-20261105/reviewed_examples.json','text_sha256':m.digest(text),'review_receipt_sha256':m.HEAT_REVIEW_SHA256}
  self.assertEqual(m.public_rationale_text(r),text)
  meta['input_language']='ko'
  with self.assertRaises(ValueError):m.public_rationale_text(r)
if __name__=='__main__':unittest.main()

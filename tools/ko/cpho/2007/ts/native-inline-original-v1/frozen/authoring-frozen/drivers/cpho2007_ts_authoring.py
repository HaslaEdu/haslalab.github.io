from pathlib import Path
import json,hashlib,shutil,re
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS')
class Page:
 def __init__(self,n):
  self.n=n;self.source=json.loads((B/f'authoring/page{n:02}-original-source-slots.json').read_text('utf8'));self.slots={s['id']:s for s in self.source['slots']};self.values={};self.notes=[]
 def put(self,row,part,ko,en,reason=None):
  key=f'{self.n}-{row}-{part}';assert key in self.slots and key not in self.values,key
  s=self.slots[key]
  if s.get('retain_native'):assert not re.search('[가-힣A-Za-z]',ko+en),('Semantic translation cannot be hidden in a retained native punctuation-only slot',key,ko,en)
  if not s.get('retain_native')and (not ko.strip()or not en.strip()):assert reason,(key,ko,en)
  self.values[key]=dict(ko=ko,en=en,source=s['source'],retain_native=s.get('retain_native',False),source_point=s['size'],original_baseline=s['origin'][1],reason=reason)
 def save(self,note):
  for key,s in self.slots.items():
   if s.get('retain_native')and key not in self.values:self.values[key]=dict(ko='',en='',source=s['source'],retain_native=True,source_point=s['size'],original_baseline=s['origin'][1],reason='Exact original punctuation remains native; no new glyph is inserted.')
  assert set(self.values)==set(self.slots),sorted(set(self.slots)-set(self.values))
  result=dict(source_page=self.n,source_sha256='2e30b56ab9274363686cbf5bc1ef7532dcf579e0703de2c01098b003ab70cdd9',status='EXPLICIT_BILINGUAL_PROSE_AUTHORING_NOT_YET_A_DELIVERABLE',source_visual_review_note=note,prose=self.values)
  path=B/f'authoring/page{self.n:02}-bilingual-prose.json';content=json.dumps(result,ensure_ascii=False,indent=2)+'\n';tsv=B/f'authoring/page{self.n:02}.tsv';tsv_text='\n'.join(key+'\t'+self.values[key]['ko']+'\t'+self.values[key]['en']for key in self.slots)+'\n'
  for prior,new in[(path,content),(tsv,tsv_text)]:
   if prior.exists()and prior.read_text('utf8')!=new:
    history=B/'authoring/history'/hashlib.sha256(prior.read_bytes()).hexdigest()[:16];history.mkdir(parents=True,exist_ok=True);shutil.copy2(prior,history/prior.name)
   prior.write_text(new,'utf8')
  print('EXPLICIT_CPHO2007_BILINGUAL_PROSE_PAGE',self.n,len(self.slots),hashlib.sha256(path.read_bytes()).hexdigest(),flush=True);return path

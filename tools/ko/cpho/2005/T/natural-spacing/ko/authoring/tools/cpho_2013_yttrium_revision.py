"""Narrow source-confirmed material-name correction, using the frozen T builder.
All other natural proofs remain byte-identical. No frozen source file is edited.
"""
from pathlib import Path
import json,time,shutil
import cpho_early_natural as a
from pdf_memory_gate import page_worker
ROOT=a.BASE/'revision-yttrium-body'
SAVED_INSTALL=a.install
EDITS={}
def install():
 SAVED_INSTALL()
 import cpho_natural_prose_edits as prose
 for language,entry in EDITS.items():
  table=prose.EDITS if language=='ko'else prose.EN_EDITS
  table.setdefault((2013,2),{})['2-19-0']=(entry['before'],entry['after'])
 a.core.OUT=ROOT

def build():
 ROOT.mkdir(exist_ok=True)
 for lang,old,new in [('ko','이리듐','이트륨'),('en','Ir-vanadate','yttrium vanadate')]:
  p=next(p for p in a.placements(2013,lang,2)if p['id']=='2-19-0')
  if p['text'].count(old)!=1:raise ValueError('Expected material-name mistranslation must occur once in the source journal')
  EDITS[lang]=dict(before=p['text'],after=p['text'].replace(old,new),old_term=old,correct_term=new)
 a.install=install
 for lang in('ko','en'):
  folder=ROOT/f'2013/{lang}';folder.mkdir(parents=True,exist_ok=True)
  for n in(1,3):
   for suffix in('.pdf','.png','.qa.json','.plan.json','.audit.json','.prose-native-text-overlap.json'):
    source=a.BASE/f'output/2013/{lang}/page{n:02}{suffix}'
    if source.exists():shutil.copy2(source,folder/source.name)
  with page_worker():a.build(2013,lang,2)
  time.sleep(.6)
 data=dict(source=str(a.original(2013)),source_sha256=a.core.sha(a.original(2013)),
  source_literal='钒酸钇自倍频',source_confirmed_material='yttrium vanadate',evidence=str(a.BASE.parent/'source-label-check/2013-laser-label.png'),
  revision='Body page2 prose slot2-19-0 in both languages. Figure page3 was already corrected. The frozen 43-module builder is unchanged; only this explicit translation-table override is applied.',
  original_size_baseline_design_retained=True,native_physical_math_reentered=False,edits=EDITS,
  unchanged_pages=[dict(language=l,page=n,sha256=a.core.sha(ROOT/f'2013/{l}/page{n:02}.pdf'))for l in('ko','en')for n in(1,3)])
 (ROOT/'material-terminology.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf8')
 return ROOT
if __name__=='__main__':print(build())

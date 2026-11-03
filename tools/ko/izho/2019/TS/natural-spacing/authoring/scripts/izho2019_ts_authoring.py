from pathlib import Path
import sys,json
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions');sys.path.insert(0,str(B/'engine'))
import source_slot_authoring as author
author.B=B
def begin(n):
 p=author.PagePlan(2019,n);p.fragments=[];p.add('0,0,0','국제 자우티코프 올림피아드/이론시험','International Zhautykov Olympiad/Theoretical Competition');p.add('0,0,0','쪽 ','Page ');p.protect_range('0,0,0',0,1,'Original header Roman V as printed in the official2019 source. Preserve exact source9.96pt Arial-BoldMT CID/GID/point/Y/paint; do not invent XV.');return p
def around(p,at,parts,literals):
 text=p.runs[at]['text'];assert len(parts)==len(literals)+1;cursor=0
 for target,literal in zip(parts,literals):
  start=text.index(literal,cursor)
  if cursor<start:p.prose_range(at,cursor,start,target)
  else:assert not target,(at,target,literal)
  p.protect_range(at,start,start+len(literal),'Original encoded mathematical reference, score, numeral, unit, enum or source punctuation; retain exact original font/GID/point/paint/physicalY.');cursor=start+len(literal)
 if cursor<len(text):p.prose_range(at,cursor,len(text),parts[-1])
 else:assert not parts[-1]
def score(p,at):
 text=p.runs[at]['text'];start=text.index('points');end=start+len('points')
 if start:p.protect_range(at,0,start,'Original source bracket/score/separator; original encoded font/GID/point/Y.')
 p.prose_range(at,start,end,'점')
 if end<len(text):p.protect_range(at,end,len(text),'Original source closing score bracket and separator.')
def finish(p,centered,note):
 selected={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
 for at in p.runs:
  coords=tuple(map(int,at.split(',')))
  if coords not in selected and coords not in fragments:p.protect(at,'Full original source page visually read. Complete original native math/function/unit/Greek/variable/script/score/counter/enumerator/source punctuation or diagram label; retain source encoded fonts/GIDs/fractional Tf/Tm/points/paint/Y and original Form/clip/rule/graphic programs. No mathematical retyping or rasterization.')
 path=p.save();q=json.loads(path.read_text('utf8'));q['centered']=centered;q['native_prose_tokens']+=['V','tg','ln','RMS','const'];q['source_visual_review_note']=note;q['staging_only_prose_baseline']=True;path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('PRIVATE_C19_FULL_SOURCE_PROSE_PLAN',p.page,len(q['slots']),flush=True);return path

from pathlib import Path
import sys,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');sys.path.insert(0,'D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions/engine')
import source_slot_authoring as author
author.B=B
def begin(n):
 p=author.PagePlan(2016,n);p.fragments=[]
 p.add('0,0,0','국제 자우티코프 올림피아드/이론시험 해설','International Zhautykov Olympiad/Theoretical Competition/Solutions')
 p.add('0,0,0','쪽 ','Page ');p.protect_fragment('0,0,0','XII','Original twelfth-edition Roman numeral, exact encoded9.96pt Arial bold font/GID/point/Y.');return p
def around(p,at,parts,literals):
 text=p.runs[at]['text'];assert len(parts)==len(literals)+1;cursor=0
 for target,literal in zip(parts,literals):
  start=text.index(literal,cursor)
  if cursor<start:p.prose_range(at,cursor,start,target)
  else:assert not target,(at,target,literal)
  p.protect_range(at,start,start+len(literal),'Original encoded mathematical reference, numeral, score, variable, unit or punctuation; exact source font/GID/point/paint/baseline retained.');cursor=start+len(literal)
 if cursor<len(text):p.prose_range(at,cursor,len(text),parts[-1])
 else:assert not parts[-1]
def score(p,at,following=''):
 text=p.runs[at]['text'];assert '['in text and 'points]'in text
 start=text.index('points');end=start+len('points')
 if start:p.protect_range(at,0,start,'Original bracket, exact source score and separator; keep native bold font/GID/point/Y.')
 p.prose_range(at,start,end,'점')
 tail=text[end:];close=tail.index(']')+1
 p.protect_range(at,end,end+close,'Original closing score bracket in the native source bold face.')
 remainder=text[end+close:]
 if remainder.strip():
  assert remainder.strip()=='T'and following; p.prose_range(at,end+close,len(text),following)
 else:
  assert not following
  if remainder:p.prose_range(at,end+close,len(text),' ')
def finish(p,centered,note):
 selected={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
 for at in p.runs:
  coords=tuple(map(int,at.split(',')))
  if coords not in selected and coords not in fragments:p.protect(at,'Full source page visually read: original native equation/function/unit/variable/Greek symbol/script/score/enumerator/source punctuation or diagram label. Preserve encoded font programs/GIDs, fractional points, paint, original Y and complete graphical primitives; no mathematical retyping or diagram replacement.')
 path=p.save();q=json.loads(path.read_text('utf8'));q['centered']=centered;q['native_prose_tokens']+=['XII','tg','ln'];q['source_visual_review_note']=note;q['staging_only_prose_baseline']=True
 path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('PRIVATE_IZHO2016_SOURCE_PROSE_PLAN',p.page,len(q['slots']),flush=True);return path

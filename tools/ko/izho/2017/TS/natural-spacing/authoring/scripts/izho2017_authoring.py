from pathlib import Path
import sys,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2017-complete-solutions')
sys.path.insert(0,'D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions/engine')
import source_slot_authoring as author
author.B=B
def begin(n):
 p=author.PagePlan(2017,n);p.fragments=[]
 p.add('0,0,0','국제 자우티코프 올림피아드/이론시험 해설','International Zhautykov Olympiad/Theoretical Competition/Solutions')
 p.add('0,0,0','쪽 ','Page ')
 p.protect_fragment('0,0,0','XIII','Original thirteenth-edition Roman numeral, actual Arial bold10.08pt native CID retained.')
 return p
def around(p,at,parts,literals):
 source=p.runs[at]['text'];assert len(parts)==len(literals)+1;cursor=0
 for target,literal in zip(parts,literals):
  start=source.index(literal,cursor)
  if start>cursor:p.prose_range(at,cursor,start,target)
  else:assert not target
  p.protect_range(at,start,start+len(literal),'Actual original numeral, reference, variable or punctuation retained with original font/CID/GID/point/Y.');cursor=start+len(literal)
 if cursor<len(source):p.prose_range(at,cursor,len(source),parts[-1])
 else:assert not parts[-1]
def finish(p,centered,note):
 selected={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
 for at in p.runs:
  coords=tuple(map(int,at.split(',')))
  if coords not in selected and coords not in fragments:p.protect(at,'Complete original page read visually. Native formula, mathematical descriptor/subscript, function, numeral, score or punctuation; retain every physical original glyph, script, complete Form, fraction rule, figure and exact source point.')
 path=p.save();q=json.loads(path.read_text('utf8'));q['centered']=centered;q['source_visual_review_note']=note;path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('PRIVATE_IZHO2017_PROSE_PLAN',p.page,len(q['slots']),flush=True)

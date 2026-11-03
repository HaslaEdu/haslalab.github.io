from pathlib import Path
import sys,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2013-complete-solutions');sys.path.insert(0,'D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions/engine')
import source_slot_authoring as author
author.B=B
def begin(n):
 p=author.PagePlan(2013,n);p.fragments=[]
 p.add('0,0,0','국제 자우티코프 올림피아드/이론시험 해설','International Zhautykov Olympiad/Theoretical Competition/Solutions')
 p.add('0,0,0','쪽 ','Page ');p.protect_fragment('0,0,0','IX','Original Roman ninth-edition label in actual9.96pt Arial-Bold.');return p
def around(p,at,parts,literals):
 text=p.runs[at]['text'];assert len(parts)==len(literals)+1;cursor=0
 for target,literal in zip(parts,literals):
  start=text.index(literal,cursor)
  if cursor<start:p.prose_range(at,cursor,start,target)
  else:assert not target
  p.protect_range(at,start,start+len(literal),'Complete original mathematical symbol/reference/score/unit/source punctuation, retained as exact encoded source glyphs with their original fonts/GIDs/points/baselines.');cursor=start+len(literal)
 if cursor<len(text):p.prose_range(at,cursor,len(text),parts[-1])
 else:assert not parts[-1]
def finish(p,centered,note):
 selected={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
 for at in p.runs:
  coords=tuple(map(int,at.split(',')))
  if coords not in selected and coords not in fragments:p.protect(at,'Human-read complete source page: actual native variable/Greek/function/unit/math index/score/enumerator/punctuation run. Preserve all encoded glyphs, original fractional script points, source mathematical bitmaps and vector paths; no formula retyping.')
 path=p.save();q=json.loads(path.read_text('utf8'));q['centered']=centered;q['source_visual_review_note']=note;q['staging_only_prose_baseline']=True
 path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('PRIVATE_IZHO2013_EXPLICIT_PROSE_PLAN',p.page,len(q['slots']),flush=True);return path

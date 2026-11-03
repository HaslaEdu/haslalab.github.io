from pathlib import Path
import sys,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2015-complete-solutions');sys.path.insert(0,'D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions/engine')
import source_slot_authoring as author
author.B=B
def begin(n):
 p=author.PagePlan(2015,n);p.fragments=[]
 p.add('0,0,0','국제 자우티코프 올림피아드','International Zhautykov Olympiad')
 p.add('0,0,0','/이론시험 해설','/Theoretical Competition/Solutions')
 p.add('0,0,0','쪽 ','Page ');p.protect_fragment('0,0,0','XI','Original eleventh-edition Roman numeral in native10.08pt Arial bold.');p.protect_fragment('0,0,0','2015','Original source year in native10.08pt Arial bold.');return p
def around(p,at,parts,literals):
 text=p.runs[at]['text'];assert len(parts)==len(literals)+1;cursor=0
 for target,literal in zip(parts,literals):
  start=text.index(literal,cursor)
  if cursor<start:p.prose_range(at,cursor,start,target)
  else:assert not target
  p.protect_range(at,start,start+len(literal),'Original source mathematical symbol/reference/numeral/unit/punctuation retained as exact encoded source font/GID/point/baseline.');cursor=start+len(literal)
 if cursor<len(text):p.prose_range(at,cursor,len(text),parts[-1])
 else:assert not parts[-1]
def finish(p,centered,note):
 selected={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
 for at in p.runs:
  coords=tuple(map(int,at.split(',')))
  if coords not in selected and coords not in fragments:p.protect(at,'Full original source page visually read: original mathematical notation, diagram label, reference, score, punctuation or index. Preserve actual encoded font/GID/fractional point/paint/Y, original bitmap and every vector rule. No mathematical regeneration.')
 path=p.save();q=json.loads(path.read_text('utf8'));q['centered']=centered;q['source_visual_review_note']=note
 for slot in q['slots']:
  at=','.join(map(str,slot['at']))
  if p.runs[at]['font']=='Cambria Math'and slot['source_text'].strip()=='and':
   assert p.page==9 and slot['at']==[54,1,1]and slot.get('range')and slot['text']==' 및 '
   q['reviewed_math_font_prose_words'].append(dict(at=slot['at'],substring=slot['source_text'],source_substring=None,range=slot['range'],translated_text=slot['text'],reviewed=True,reason='Full original page9 read: only the literal English conjunction and and surrounding prose spaces between the original closing parenthesis and p-dot are prose. Preserve both adjacent original mathematical clusters, exact native source CIDs/points/Y and all original accents.'))
 path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('PRIVATE_IZHO2015_EXPLICIT_PROSE_PLAN',p.page,len(q['slots']),flush=True);return path

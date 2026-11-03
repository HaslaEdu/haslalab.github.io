from pathlib import Path
import json
import source_slot_authoring as author
B=Path(__file__).resolve().parents[1];author.B=B
REASON='Full original source page visually read. Original mathematical notation, native reference/index/score/unit retains exact encoded font/GID/fractional point/paint/Y and complete source program. No mathematical retyping, scaling or rasterization.'
def begin(n):
 p=author.PagePlan(2018,n);p.fragments=[];p.header();p.protect_fragment('0,0,0','XIV',REASON);return p
def around(p,at,parts,literals):
 source=p.runs[at]['text'];assert len(parts)==len(literals)+1;cursor=0
 for target,literal in zip(parts,literals):
  start=source.index(literal,cursor)
  if cursor<start:p.prose_range(at,cursor,start,target)
  else:assert not target
  p.protect_range(at,start,start+len(literal),REASON);cursor=start+len(literal)
 if cursor<len(source):p.prose_range(at,cursor,len(source),parts[-1])
 else:assert not parts[-1]
def title(p,at,identifier,points):around(p,at,['문제 ','','점',''],[identifier+' (',points,')'])
def formula(p,at):
 text=p.runs[at]['text'];assert text.startswith('Formula ');p.add(at,'식 ','Formula ');p.protect_fragment(at,text[len('Formula '):].strip(),REASON)
def point_labels(p):
 import re
 for at,r in p.runs.items():
  if re.fullmatch(r'\s*\[[\d,. ]+points\]\s*',r['text']):
   text=r['text'];start=text.index('points');around(p,at,['','점',''],[text[:start],text[start+6:]])
def part(p,at,number,heading,points):around(p,at,['제','부. '+heading+' (','점',''],[number,points,')'])
def finish(p,centered,note):
 selected={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
 for at in p.runs:
  coords=tuple(map(int,at.split(',')))
  if coords not in selected and coords not in fragments:p.protect(at,REASON)
 path=p.save();d=json.loads(path.read_text('utf8'));d['small_glyph_heights']=False;d['centered']=centered;d['native_prose_tokens']=['XIV','sin','cos','max','min','log','exp','const','sm','см','mA','Cl','μCl'];d['source_visual_review_note']=note;path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');print('EXPLICIT_SOURCE2018_TS_KOREAN_PLAN',p.page,len(p.slots),flush=True);return path

"""Consolidate complete early Word equation objects, including Roman fractions.

No mathematical text is regenerated. Connected original glyph rectangles become
one lossless crop, so HTML cannot turn a numerator and denominator into a list.
"""
import copy,re
import pymupdf as fitz
from izho_early_extract import math_candidate,is_seed

def candidate(s):
 t=s['text'].strip()
 if t in {'Mg','Mu','gR','Bax','eBu','eBU','gHV','gdx','nMm','rh','neu','rdr','aBL','dt','dE','tg','ctg','arctg'}:return True
 return math_candidate(s)

def consolidate(page,e,folder=None):
 used={int(i) for i in re.findall(r'\[\[(\d+)\]\]',e['source']+' '+e['ko'])}
 if not used:return e,None
 bi=int(re.match(r'\d+-(\d+)',e['id'])[1]);b=page.get_text('dict')['blocks'][bi]
 if b['type']!=0:return e,None
 spans=[s for l in b['lines'] for s in l['spans'] if s['text'].strip()];rects=[fitz.Rect(s['bbox']) for s in spans]
 def connected(i,j):
  a,c=rects[i],rects[j]
  if max(a.x0-c.x1,c.x0-a.x1,0)>8 or max(a.y0-c.y1,c.y0-a.y1,0)>4.5:return False
  return not any(not candidate(s) and not is_seed(s) for s in spans[min(i,j)+1:max(i,j)])
 selected={i for i,s in enumerate(spans) if is_seed(s)}
 changed=True
 while changed:
  changed=False
  for i,s in enumerate(spans):
   if i not in selected and candidate(s) and any(connected(i,j) for j in selected):selected.add(i);changed=True
 groups=[]
 for i in sorted(selected):
  hits=[g for g in groups if any(connected(i,j) for j in g)];g={i}
  for h in hits:g|=h;groups.remove(h)
  groups.append(g)
 comps=[]
 for g in groups:
  r=fitz.Rect(rects[min(g)])
  for i in g:r|=rects[i]
  comps.append({'rect':r,'spans':g,'old':[]})
 for mi in sorted(used):
  r=fitz.Rect(e['math'][mi]['rect'])
  scores=[(r&c['rect']).get_area() for c in comps]
  if scores and max(scores)>r.get_area()*.1:c=comps[scores.index(max(scores))]
  else:c={'rect':r,'spans':set(),'old':[]};comps.append(c)
  c['old'].append(mi)
 comps=[c for c in comps if c['old']];comps.sort(key=lambda c:min(c['old']))
 q=copy.deepcopy(e);maths=[];changes=[]
 for ni,c in enumerate(comps):
  old=c['old'];r=c['rect']+(-.3,-.3,.3,.3);tag=f'§M{ni}§'
  for field in ['source','ko']:
   text=q[field];matches=[m for m in re.finditer(r'\[\[(\d+)\]\]',text) if int(m[1]) in old]
   if not matches:continue
   first,last=matches[0],matches[-1];middle=text[first.start():last.end()]
   if re.search(r'[가-힣]',middle):
    raise ValueError(f"Korean prose separates one original equation: {e['id']}: {middle}")
   before,after=text[:first.start()],text[last.end():]
   # Some Word fractions emit the Roman numerator before the first italic
   # variable. Those numerals now live inside the complete original crop.
   original_before=e['source'].split(f'[[{old[0]}]]',1)[0]
   prefix=re.search(r'(?<!\S)(\d+(?:\s+\d+)*)\s*$',original_before)
   seed_indices=[i for i in c['spans'] if is_seed(spans[i])]
   head=' '.join(spans[i]['text'].strip() for i in sorted(c['spans']) if seed_indices and i<min(seed_indices) and re.fullmatch(r'[0-9\s]+',spans[i]['text'].strip()))
   if prefix and prefix[1] in head and before.rstrip().endswith(prefix[1]):before=before.rstrip()[:-len(prefix[1])].rstrip()+' '
   original_after=e['source'].rsplit(f'[[{old[-1]}]]',1)[-1]
   suffix=re.match(r'\s*(\d+(?:\s+\d+)*)',original_after)
   if suffix and seed_indices:
    tail=' '.join(spans[i]['text'].strip() for i in sorted(c['spans']) if i>max(seed_indices) and re.fullmatch(r'[0-9\s]+',spans[i]['text'].strip()))
    if suffix[1] in tail and after.lstrip().startswith(suffix[1]):after=after.lstrip()[len(suffix[1]):]
   literal=re.match(r'\s*([A-Za-z]{1,5})(?=\s|[.,;:]|$)',original_after)
   if literal and seed_indices and candidate({'text':literal[1]}):
    tail=[spans[i]['text'].strip() for i in c['spans'] if i>max(seed_indices)]
    if literal[1] in tail and after.lstrip().startswith(literal[1]):after=after.lstrip()[len(literal[1]):]
   q[field]=before+tag+after
  name=f"{e['id']}-eq{ni}.png"
  if folder is not None:page.get_pixmap(matrix=fitz.Matrix(4,4),clip=r,alpha=False).save(folder/name)
  maths.append({'file':name,'width':r.width,'height':r.height,'rect':list(r),'text':' '.join(spans[i]['text'] for i in sorted(c['spans'])) or 'original equation crop'})
  changes.append({'new':ni,'old':old,'rect':list(r),'text':maths[-1]['text']})
 for ni in range(len(comps)):
  for field in ['source','ko']:q[field]=q[field].replace(f'§M{ni}§',f'[[{ni}]]')
 q['math']=maths;q['equation_consolidation']='izho_early_math.py: complete source glyph components'
 return q,{'id':e['id'],'changes':changes,'ko_before':e['ko'],'ko_after':q['ko']}

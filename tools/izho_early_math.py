"""Consolidate complete early Word equation objects, including Roman fractions.

No mathematical text is regenerated. Connected original glyph rectangles become
one lossless crop, so HTML cannot turn a numerator and denominator into a list.
"""
import copy,re,hashlib
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image,ImageFilter,ImageChops
import pymupdf as fitz
from izho_early_extract import math_candidate,is_seed

_clean_pages={}
_original_math_regions={}
_math_vector_paths={}
_svg_pages=set()
_svg_glyphs={}
_cache_version=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
CYRILLIC_UNITS={'Па','кПа','МПа','Кл','Дж','кДж','Вт','Гц','кг','см','мм','км','моль','эВ','мэВ','МэВ','ГэВ','ТэВ'}

def register_math_regions(document,entries,prefer_svg=False):
 for e in entries:
  key=(document.name,e['page'])
  _original_math_regions.setdefault(key,[]).extend(fitz.Rect(m['rect']) for m in e.get('math',[]))
  if prefer_svg:_svg_pages.add(key)

def math_pixmap(page,rect):
 """Render original math without prose from the neighbouring Word line.

 Word's tall equation boxes may include descenders from the preceding prose.
 Remove prose characters from a temporary PDF using tiny hit points that do
 not intersect a mathematical glyph, leaving the original math font intact.
 """
 key=(page.parent.name,page.number)
 if key in _svg_pages:return svg_math_pixmap(page,rect)
 if key not in _clean_pages:
  cache=Path(__file__).resolve().parents[1]/'tmp/izho-early/math-cache'
  signature=hashlib.sha256((_cache_version+repr(key)+repr(page.get_text('words'))+repr(_original_math_regions.get(key,[]))).encode('utf8')+page.read_contents()).hexdigest()
  cached=cache/(signature+'.pdf')
  if cached.exists():
   _clean_pages[key]=fitz.open(cached)
   return _clean_pages[key][0].get_pixmap(matrix=fitz.Matrix(4,4),clip=rect,alpha=False)
  blocks=page.get_text('rawdict')['blocks'];protected=[];prose=[]
  for block in blocks:
   if block['type']!=0:continue
   spans=[{**s,'text':''.join(c['c'] for c in s['chars'])} for line in block['lines'] for s in line['spans']]
   selected={i for i,s in enumerate(spans) if is_seed(s)}
   def near(i,j):
    a,b=spans[i]['bbox'],spans[j]['bbox']
    return max(a[0]-b[2],b[0]-a[2],0)<=8 and max(a[1]-b[3],b[1]-a[3],0)<=4.5 and not any(not candidate(s) and not is_seed(s) for s in spans[min(i,j)+1:max(i,j)])
   changed=True
   while changed:
    changed=False
    for i,s in enumerate(spans):
     if i not in selected and candidate(s) and any(near(i,j) for j in selected):selected.add(i);changed=True
   has_prose=any(re.search(r'[A-Za-zА-Яа-яЁё]{2,}',s['text']) and not candidate(s) for s in spans)
   for i,s in enumerate(spans):
    text=s['text'];r=fitz.Rect(s['bbox'])
    article=(text.strip()=='a' and 'Italic' not in s.get('font','') and 'Math' not in s.get('font','')
      and i+1<len(spans) and re.match(r'tube\b',spans[i+1]['text'].lstrip(),re.I))
    math_regions=_original_math_regions.get(key,[])+[v for kind,v in math_vectors(page) if kind=='radical']
    inside_original_math=any((r&old).get_area()>r.get_area()*.7 for old in math_regions)
    heading_number=has_prose and r.x0<130 and re.fullmatch(r'\s*\d+\.\s*',text)
    label_number=heading_number or (has_prose and i not in selected and not inside_original_math and re.fullmatch(r'\s*\d+(?:\.\d+)?[.)]?\s*',text))
    if (text.strip() in CYRILLIC_UNITS or candidate(s) or is_seed(s)) and not label_number and not article:
     protected.extend(fitz.Rect(c['bbox']) for c in s['chars'] if c['c'].strip())
    elif article or label_number or re.search(r'[A-Za-zА-Яа-яЁё]{2,}',text):prose.extend(c for c in s['chars'] if c['c'].strip())
  document=fitz.open();document.insert_pdf(page.parent,from_page=page.number,to_page=page.number);clean=document[0]
  protected_bounds=[tuple(p) for p in protected]
  def overlaps_math(r):
   a,b,c,d=r
   return any(a<p[2] and c>p[0] and b<p[3] and d>p[1] for p in protected_bounds)
  hits=[]
  for char in prose:
   r=fitz.Rect(char['bbox']);points=[(r.x0+r.width*.5,r.y0+r.height*f) for f in [.18,.35,.6,.83]]
   for x,y in points:
    hit=fitz.Rect(x-.05,y-.05,x+.05,y+.05)
    if not overlaps_math(hit):hits.append(hit);break
  # A narrow strip removes a complete prose line. Merge safe adjacent hit
  # points so a Word page needs dozens rather than thousands of annotations.
  strips=[]
  for hit in sorted(hits,key=lambda r:(round(r.y0,1),r.x0)):
   if strips and abs(strips[-1].y0-hit.y0)<.3 and hit.x0-strips[-1].x1<18:
    union=strips[-1]|hit
    if not overlaps_math(union):strips[-1]=union;continue
   strips.append(hit)
  for hit in strips:clean.add_redact_annot(hit,fill=None)
  clean.apply_redactions(images=0,graphics=0,text=0)
  cache.mkdir(parents=True,exist_ok=True);temporary=cached.with_suffix('.tmp.pdf')
  document.save(temporary,garbage=4,deflate=True);temporary.replace(cached)
  _clean_pages[key]=document
 return _clean_pages[key][0].get_pixmap(matrix=fitz.Matrix(4,4),clip=rect,alpha=False)

def svg_math_pixmap(page,rect):
 """Erase exact prose outlines, never a math font's oversized PDF bbox.

 The 2012 solution gives ordinary prose the CambriaMath font as well. Classify
 words with our equation vocabulary rather than treating the font as proof of
 mathematical content. Source vectors (fraction bars and radicals) remain native.
 """
 key=(page.parent.name,page.number)
 if key not in _svg_glyphs:
  prose_origins=set();math_origins=set()
  regions=_original_math_regions.get(key,[])+[r for kind,r in math_vectors(page) if kind=='radical']
  for block in page.get_text('rawdict')['blocks']:
   if block['type']!=0:continue
   spans=[{**s,'text':''.join(c['c'] for c in s['chars'])} for line in block['lines'] for s in line['spans']]
   for s in spans:
    text=s['text'].strip();r=fitz.Rect(s['bbox'])
    original=any((r&old).get_area()>r.get_area()*.7 for old in regions)
    mathematical=text in CYRILLIC_UNITS or candidate(s) or is_seed(s) or (original and re.fullmatch(r'[\d\s.,()+−=–-]+',text))
    destination=math_origins if mathematical else prose_origins if re.search(r'[A-Za-zА-Яа-яЁё]{2,}',text) else None
    if destination is not None:destination.update((round(c['origin'][0],2),round(c['origin'][1],2)) for c in s['chars'] if c['c'].strip())
  svg=ET.fromstring(page.get_svg_image(text_as_path=True));ns='{http://www.w3.org/2000/svg}';uses=[]
  for use in svg.iter(ns+'use'):
   matrix=re.search(r'matrix\(([^)]+)\)',use.get('transform',''))
   if not matrix:continue
   values=[float(v) for v in re.split(r'[,\s]+',matrix[1].strip())]
   if len(values)==6:
    origin=(round(values[4],2),round(values[5],2))
    uses.append((origin,origin in prose_origins,origin in math_origins,copy.deepcopy(use)))
  _svg_glyphs[key]=(svg.tag,svg.attrib,svg.findall(ns+'defs'),uses)
 pix=page.get_pixmap(matrix=fitz.Matrix(4,4),clip=rect,alpha=False)
 bitmap=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
 tag,attributes,definitions,uses=_svg_glyphs[key]
 attributes=dict(attributes,width=str(pix.width/4),height=str(pix.height/4),viewBox=f'{pix.x/4} {pix.y/4} {pix.width/4} {pix.height/4}')
 erase=ET.Element(tag,attributes);keep=ET.Element(tag,attributes)
 for defs in definitions:erase.append(copy.deepcopy(defs));keep.append(copy.deepcopy(defs))
 for point,prose,math,use in uses:
  if not (rect.x0-72<point[0]<rect.x1+72 and rect.y0-72<point[1]<rect.y1+72):continue
  inside=rect.x0-4<=point[0]<=rect.x1+1 and rect.y0-2<=point[1]<=rect.y1+2
  if math and inside:keep.append(copy.deepcopy(use))
  elif prose or not inside:erase.append(copy.deepcopy(use))
 def mask(root):
  ET.register_namespace('','http://www.w3.org/2000/svg')
  ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
  doc=fitz.open(stream=ET.tostring(root),filetype='svg')
  rendered=doc[0].get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csGRAY,alpha=False)
  result=Image.frombytes('L',(rendered.width,rendered.height),rendered.samples).point(lambda v:255 if v<248 else 0)
  doc.close();return result
 # Protect the exact mathematical outline as well as its antialiased edge.
 # Dilation removes the prose fringe without nibbling a nearby denominator.
 erase_mask=mask(erase).filter(ImageFilter.MaxFilter(3))
 keep_mask=mask(keep).filter(ImageFilter.MaxFilter(3))
 bitmap.paste('white',mask=ImageChops.subtract(erase_mask,keep_mask))
 return bitmap

def math_vectors(page):
 key=(page.parent.name,page.number)
 if key not in _math_vector_paths:
  result=[]
  for drawing in page.get_drawings():
   r=drawing['rect']
   if not (2<r.width<150 and r.height<35):continue
   color=drawing.get('fill') or drawing.get('color')
   if color is None or min(color)>.4:continue
   if r.height<1.4:result.append(('fraction_bar',r));continue
   lines=[item for item in drawing['items'] if item[0]=='l']
   # Word draws a square root as a filled hook and overbar, outside all
   # text-glyph bounds. An arrow's lower point is on the right, unlike this hook.
   top_bar=any(abs(a.y-b.y)<.8 and abs(a.x-b.x)>r.width*.6 and min(a.y,b.y)<r.y0+1.5 for _,a,b in lines)
   lower_left=any(p.x<r.x0+r.width*.25 and p.y>r.y1-1 for line in lines for p in line[1:])
   if len(lines)>=5 and top_bar and lower_left:result.append(('radical',r))
  _math_vector_paths[key]=result
 return _math_vector_paths[key]

def candidate(s):
 t=s['text'].strip()
 if re.fullmatch(r'[A-Za-z]{2}',t) and 'Italic' in s.get('font',''):return True
 if t=='at' and ('Italic' in s.get('font','') or 'CambriaMath' in s.get('font','')):return True
 if t=='kPa':return True
 if t in {'Af','Bg','Ch'}:return True
 if t.lower() in {'ext','cond','opt','surf','sur','tot','rot','rad','crtitcal'}:return True
 if t.lower() in {'arcsin','arccos','arctan','arccot','sinh','cosh','tanh','coth','sec','csc','sgn','det','re','im'}:return True
 if t in {'Mg','Mu','gR','Bax','eBu','eBU','gHV','gdx','nMm','rh','neu','rdr','aBL','dt','dE','tg','ctg','arctg','Idl','IdlR','dB','dI','rdz','jhdr','hvr','jdr','qS','qSh'}:return True
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
  # Consolidation may add a fraction or index, but must never narrow an
  # already captured equation (Word sometimes emits its numerals out of order).
  c['rect']|=r
  c['old'].append(mi)
 comps=[c for c in comps if c['old']]
 for kind,vector in math_vectors(page):
  if kind=='radical':
   hits=[c for c in comps if max(c['rect'].x0-vector.x1,vector.x0-c['rect'].x1,0)<4.5 and max(c['rect'].y0-vector.y1,vector.y0-c['rect'].y1,0)<3]
  else:
   hits=[c for c in comps if min(c['rect'].x1,vector.x1)-max(c['rect'].x0,vector.x0)>1 and max(c['rect'].y0-vector.y1,vector.y0-c['rect'].y1,0)<8]
   if len(hits)<2 or not any(c['rect'].y0<vector.y0 for c in hits) or not any(c['rect'].y1>vector.y1 for c in hits):continue
  if not hits:continue
  merged={'rect':fitz.Rect(vector),'spans':set(),'old':[],'vectors':[{'kind':kind,'rect':list(vector)}]}
  for c in hits:
   merged['rect']|=c['rect'];merged['spans']|=c['spans'];merged['old']+=c['old'];merged['vectors']+=c.get('vectors',[]);comps.remove(c)
  if kind=='radical':
   for i,s in enumerate(spans):
    if candidate(s) and (rects[i]&vector).get_area()>rects[i].get_area()*.6:
     merged['spans'].add(i);merged['rect']|=rects[i]
  merged['old']=sorted(set(merged['old']));comps.append(merged)
 comps.sort(key=lambda c:min(c['old']))
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
   word_prefix=re.search(r'(?<!\S)([A-Za-z]{2,12})\s*$',original_before)
   if word_prefix and candidate({'text':word_prefix[1]}) and word_prefix[1] in [spans[i]['text'].strip() for i in c['spans']] and before.rstrip().endswith(word_prefix[1]):before=before.rstrip()[:-len(word_prefix[1])].rstrip()+' '
   original_after=e['source'].rsplit(f'[[{old[-1]}]]',1)[-1]
   suffix=re.match(r'\s*(\d+(?:\s+\d+)*)',original_after)
   if suffix and seed_indices:
    tail=' '.join(spans[i]['text'].strip() for i in sorted(c['spans']) if i>max(seed_indices) and re.fullmatch(r'[0-9\s]+',spans[i]['text'].strip()))
    if suffix[1] in tail and after.lstrip().startswith(suffix[1]):after=after.lstrip()[len(suffix[1]):]
   literal=re.match(r'\s*([A-Za-z]{1,12})(?=\s|[.,;:]|$)',original_after)
   if literal and seed_indices and candidate({'text':literal[1]}):
    component_text=[spans[i]['text'].strip() for i in c['spans']]
    if literal[1] in component_text and after.lstrip().startswith(literal[1]):after=after.lstrip()[len(literal[1]):]
   q[field]=before+tag+after
  name=f"{e['id']}-eq{ni}.png"
  if folder is not None:math_pixmap(page,r).save(folder/name)
  original_rects=[e['math'][mi]['rect'] for mi in old]
  assert all(r.contains(fitz.Rect(old_rect)) for old_rect in original_rects),(e['id'],old)
  maths.append({'file':name,'width':r.width,'height':r.height,'rect':list(r),'text':' '.join(spans[i]['text'] for i in sorted(c['spans'])) or 'original equation crop',
    'original_rects':original_rects,'original_texts':[e['math'][mi].get('text','') for mi in old],'source_vectors':c.get('vectors',[])})
  changes.append({'new':ni,'old':old,'rect':list(r),'original_rects':original_rects,'text':maths[-1]['text']})
 for ni in range(len(comps)):
  for field in ['source','ko']:q[field]=q[field].replace(f'§M{ni}§',f'[[{ni}]]')
 q['math']=maths;q['equation_consolidation']='izho_early_math.py: complete source glyph components'
 return q,{'id':e['id'],'changes':changes,'ko_before':e['ko'],'ko_after':q['ko']}

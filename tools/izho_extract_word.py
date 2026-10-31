"""Extract Word / MathType inline equations as complete image groups, including digits and units."""
import argparse,json,re,hashlib
from pathlib import Path
import pymupdf as fitz

FUNCTIONS={'arcsin','arccos','arctan','asin','acos','atan','sinh','cosh','tanh','coth','abs','sign','floor','ceil'}
UNIT={'K','К','Cl','C','Hz','kg','mm','cm','km','m','s','h','k','F/m','H/m','J/K','km/s','m/s','km/h','rad/s','H','F','V','J','W','Pa','A','mA','Ω','sin','cos','tan','ln','log','exp','max','min'}
UNIT |= FUNCTIONS | {'mol','mole','year','years'}
UNIT |= {'mu','eEx','eBu','eB','eBx','mE','mru','dp','er','rdr','eE','Rdl','NI','dj','eBrdr','eBr','eV','mV','eb','vt','eu','NIR','Edr','dr','dt','dl','nl','const'}
UNIT |= {'mgR','pV','RT','gR','Rd','Qdq','mgd','mg','nRT','KR','cn','xdx','Vdt','GM','FR','mVR','rdrd','cR'}
UNIT |= {'sly','sgy','kx','ky','my','mx','gs','Vg','pS','gH','Hl','CU','Nk','ne','kc','ak','edq','AB','CD','AF'}
UNIT |= {'dk','LI','mr','NW','sl','ABCD','ABEF','dx','dq','dy','dz','du','da','dv'}
UNIT |= {'dn','th'}  # Derivative numerator and threshold subscript in laser equations.
UNIT |= {'Па','Кл','Дж','Вт','Гц','кг','см','мм','км'}
MATH_FONTS=set()
def configure_math_fonts(doc):
 MATH_FONTS.clear()
 for p in doc:
  for b in p.get_text('dict')['blocks']:
   if b['type']!=0:continue
   for line in b['lines']:
    for s in line['spans']:
     if re.search('[\U0001d400-\U0001d7ff]',s['text']):MATH_FONTS.add(s['font'].replace(' ',''))
def mathword(w):return w in UNIT or w.lower() in {x.lower() for x in UNIT} or bool(re.fullmatch(r'[A-Za-z]*d[A-Z][A-Za-z]*',w))
def candidate(s):
 t=s['text'].strip();font=s['font'].replace(' ','')
 if not t:return False
 if font in MATH_FONTS or font.startswith(('CM','CambriaMath','Symbol','LMMath','MTExtra')):return True
 if 'Italic' in font and not re.search('[A-Za-z]{2,}',t):return True
 if t in UNIT or re.fullmatch(r'[A-Za-z]*d[A-Z][A-Za-z]*',t):return True
 words=re.findall('[A-Za-zА-Яа-я]{2,}',t)
 return bool(re.search(r'\d|[=+−×÷∞∑∫√<>≤≥≈≠]',t)) and all(w in UNIT for w in words)

def extract(source,folder,pages):
 folder.mkdir(parents=True,exist_ok=True)
 manifest=folder/'translation.json'
 if manifest.exists() and any(e.get('ko','').strip() for e in json.loads(manifest.read_text('utf8'))['entries']):
  raise ValueError('Refusing to overwrite a translated/reviewed manifest: '+str(manifest))
 doc=fitz.open(source);doc.select(pages)
 configure_math_fonts(doc)
 small=any(s['bbox'][3]-s['bbox'][1]>2.5*s['size'] for p in doc for b in p.get_text('dict')['blocks'] if b['type']==0 for l in b['lines'] for s in l['spans'])
 fitz.TOOLS.set_small_glyph_heights(small);entries=[]
 for pi,page in enumerate(doc):
  for bi,b in enumerate(page.get_text('dict')['blocks']):
   if b['type']!=0:continue
   spans=[s for l in b['lines'] for s in l['spans']];text=' '.join(s['text'] for s in spans)
   words=re.findall('[A-Za-z]{3,}',text)
   if not words or all(mathword(w) or w.lower() in {'out','amu','mev','ghz','kev'} for w in words):continue
   groups=[]
   for i,s in enumerate(spans):
    if not candidate(s):continue
    r=fitz.Rect(s['bbox']);ids=[i]
    while True:
     j=next((j for j,(q,is_) in enumerate(groups) if abs(s['origin'][1]-sum(spans[n]['origin'][1] for n in is_)/len(is_))<=min([s['size']]+[spans[n]['size'] for n in is_])*.45 and ((min(r.y1,q.y1)>max(r.y0,q.y0) and max(r.x0,q.x0)-min(r.x1,q.x1)<4)
        or (min(r.x1,q.x1)>max(r.x0,q.x0) and max(r.y0,q.y0)-min(r.y1,q.y1)<4))),None)
     if j is None:break
     q,others=groups.pop(j);r|=q;ids+=others
    groups.append((r,ids))
   key=f'{pi+1}-{bi}';maths=[];byspan={}
   for r,ids in sorted(groups,key=lambda x:min(x[1])):
    r+=(-.3,-.3,.3,.3);mi=len(maths);name=f'{key}-m{mi}.png';page.get_pixmap(matrix=fitz.Matrix(4,4),clip=r,alpha=False).save(folder/name)
    maths.append({'file':name,'width':r.width,'height':r.height,'rect':list(r),'text':' '.join(spans[i]['text'] for i in sorted(ids))})
    for i in ids:byspan[i]=mi
   chunks=[];seen=set()
   for i,s in enumerate(spans):
    if i in byspan:
     mi=byspan[i]
     if mi not in seen:chunks.append(f'[[{mi}]]');seen.add(mi)
    else:chunks.append(s['text'])
   entries.append({'id':key,'page':pi,'rect':b['bbox'],'size':max(s['size'] for s in spans),'source':re.sub(r'\s+',' ',' '.join(chunks)).strip(),'math':maths,'ko':''})
 # MathType often emits numerator, denominator and equals-sign parts in separate PDF lines.
 # Consecutive tokens with no intervening prose belong to one expression: crop their union.
 for entry in entries:
  old=entry['math'];maths=[];chunks=[];end=0
  for match in re.finditer(r'\[\[\d+\]\](?:\s+\[\[\d+\]\])*',entry['source']):
   ids=list(map(int,re.findall(r'\d+',match.group())));groups=[]
   for oi in ids:
    q=fitz.Rect(old[oi]['rect'])
    if groups:
     r,part=groups[-1]
     near=(min(r.y1,q.y1)>max(r.y0,q.y0) and max(r.x0,q.x0)-min(r.x1,q.x1)<12) or (max(r.x0,q.x0)-min(r.x1,q.x1)<4 and max(r.y0,q.y0)-min(r.y1,q.y1)<5)
    else:near=False
    if near:groups[-1]=(r|q,part+[oi])
    else:groups.append((q,[oi]))
   tokens=[]
   for r,part in groups:
    mi=len(maths);name=f"{entry['id']}-m{mi}.png";doc[entry['page']].get_pixmap(matrix=fitz.Matrix(4,4),clip=r,alpha=False).save(folder/name)
    maths.append({'file':name,'width':r.width,'height':r.height,'rect':list(r),'text':' '.join(old[n]['text'] for n in part)});tokens.append(f'[[{mi}]]')
   chunks += [entry['source'][end:match.start()],' '.join(tokens)];end=match.end()
  chunks.append(entry['source'][end:]);entry['source']=''.join(chunks);entry['math']=maths
 out={'source':'tmp/source-audit/'+source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_pages':pages,'small_glyph_heights':small,'word_equations':True,'entries':entries,'provenance':{'source_name':source.name}}
 (folder/'translation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf8');print('Extracted',len(entries),'regions')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('folder',type=Path);p.add_argument('--pages',required=True);a=p.parse_args();lo,hi=map(int,a.pages.split('-'));extract(a.source,a.folder,list(range(lo-1,hi)))

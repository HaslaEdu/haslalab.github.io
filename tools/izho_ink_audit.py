"""Compare rendered Hangul glyph ink with the masked source and final equation/image ink.

This is a second check after bbox auditing and full-page visual review. Intersections
are connected at 400% scale; components over 15 dark pixels require visual review.
"""
import argparse,hashlib,json,re,io,pymupdf as f,numpy as np
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];FONT=ROOT/'tools/ko/fonts/NotoSansKR-Regular.ttf'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('year',type=int);parser.add_argument('kind',choices=['T','TS']);args=parser.parse_args();year=args.year;kind=args.kind
data=json.loads((ROOT/f'tools/ko/izho/{year}/{kind}/translation.json').read_text('utf8'))
f.TOOLS.set_small_glyph_heights(bool(data.get('small_glyph_heights')))
src=f.open(ROOT/data['source'])
if data.get('source_pages') is not None:src.select(data['source_pages'])
out=f.open(ROOT/f'pdfx/izho/IZhO_{year}_{kind}_KO.pdf')
report=[]
for pi,page in enumerate(out):
 pix=src[pi].get_pixmap(matrix=f.Matrix(4,4),alpha=False);base=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);draw=ImageDraw.Draw(base)
 # Reproduce the actual background masks, then union the final image ink below.
 for e in data['entries']:
  if e['page']==pi and not e.get('passthrough'):
   draw.rectangle(tuple(v*4 for v in e.get('redact_rect',e['rect'])),fill='white')
 for key in ['erase_rects','preserve_rects']:
  for e in data.get(key,[]):
   if e['page']==pi and not f.Rect(e['rect']).is_empty:draw.rectangle(tuple(v*4 for v in e['rect']),fill='white')
 mathink=np.asarray(base.convert('L'))<80
 mathink[:240,:]=False
 kd=f.open();kp=kd.new_page(width=page.rect.width,height=page.rect.height);kp.insert_font(fontname='ko',fontfile=str(FONT))
 for b in page.get_text('rawdict')['blocks']:
  if b['type']!=0:continue
  for l in b['lines']:
   for s in l['spans']:
    for c in s['chars']:
     if re.search('[가-힣]',c['c']):kp.insert_text(c['origin'],c['c'],fontsize=s['size'],fontname='ko')
 kpix=kp.get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csGRAY,alpha=False);kink=np.frombuffer(kpix.samples,dtype=np.uint8).reshape(kpix.height,kpix.width)<80
 # Original and inserted formula/figure images are audited at their final coordinates.
 for b in page.get_text('dict')['blocks']:
  if b['type']!=1:continue
  r=f.Rect(b['bbox']);x0,y0,x1,y1=[round(v*4) for v in r]
  if x1<=x0 or y1<=y0:continue
  im=Image.open(io.BytesIO(b['image'])).convert('RGBA')
  if b.get('mask'):im.putalpha(Image.open(io.BytesIO(b['mask'])).convert('L').resize(im.size, Image.Resampling.LANCZOS))
  bg=Image.new('RGBA',im.size,'white');bg.alpha_composite(im);im=bg.convert('L').resize((x1-x0,y1-y0))
  if 0<=x0<x1<=pix.width and 0<=y0<y1<=pix.height:mathink[y0:y1,x0:x1] |= np.asarray(im)<80
 overlap=mathink&kink
 count=int(overlap.sum());pts=np.argwhere(overlap)
 groups=[];pending=set(map(tuple,pts))
 while pending:
  group=[pending.pop()];stack=group[:]
  while stack:
   yy,xx=stack.pop()
   for dy in [-1,0,1]:
    for dx in [-1,0,1]:
     q=(yy+dy,xx+dx)
     if q in pending:pending.remove(q);stack.append(q);group.append(q)
  if len(group)>15:groups.append({'pixels':len(group),'rect':[min(q[1] for q in group)/4,min(q[0] for q in group)/4,max(q[1] for q in group)/4,max(q[0] for q in group)/4]})
 report.append({'page':pi+1,'clusters':groups,'overlap_pixels':count,'bounds':([float(pts[:,1].min()/4),float(pts[:,0].min()/4),float(pts[:,1].max()/4),float(pts[:,0].max()/4)] if count else None)})
 if count:
  color=np.asarray(base).copy();color[overlap]=[255,0,0];Image.fromarray(color).save(ROOT/f'tmp/izho-qa/ink_{year}_{kind}_p{pi+1}.png')
 print(report[-1],flush=True)
result={'file':f'IZhO_{year}_{kind}_KO.pdf','sha256':hashlib.sha256((ROOT/f'pdfx/izho/IZhO_{year}_{kind}_KO.pdf').read_bytes()).hexdigest(),'scale':4,'dark_threshold':80,'component_threshold':15,'flagged_components':sum(len(p['clusters']) for p in report),'pages':report}
(ROOT/f'tmp/izho-qa/{year}_{kind}_ink.json').write_text(json.dumps(result,indent=2),'utf8')
raise SystemExit(bool(result['flagged_components']))

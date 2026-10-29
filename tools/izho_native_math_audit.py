"""Compare retained native equation ink to the original page at exact coordinates."""
import argparse,json,re,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import pymupdf as f
from izho_translate import ROOT,resolve_source
from izho_extract_word import mathword
def components(mask):
 pending=set(map(tuple,np.argwhere(mask)));groups=[]
 while pending:
  group=[pending.pop()];stack=group[:]
  while stack:
   yy,xx=stack.pop()
   for dy in [-1,0,1]:
    for dx in [-1,0,1]:
     q=(yy+dy,xx+dx)
     if q in pending:pending.remove(q);stack.append(q);group.append(q)
  if len(group)>15:groups.append({'pixels':len(group),'rect':[int(min(q[1] for q in group))/4,int(min(q[0] for q in group))/4,int(max(q[1] for q in group))/4,int(max(q[0] for q in group))/4]})
 return groups

def run(year,kind):
 folder=ROOT/'tools/ko/izho'/str(year)/kind;data=json.loads((folder/'translation.json').read_text('utf8'));f.TOOLS.set_small_glyph_heights(bool(data.get('small_glyph_heights')))
 src=f.open(resolve_source(data));
 if data.get('source_pages') is not None:src.select(data['source_pages'])
 target=ROOT/'pdfx/izho'/f'IZhO_{year}_{kind}_KO.pdf';out=f.open(target);pages=[]
 for pi,(a,b) in enumerate(zip(src,out)):
  pa=a.get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csGRAY);pb=b.get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csGRAY)
  aa=np.frombuffer(pa.samples,np.uint8).reshape(pa.height,pa.width);bb=np.frombuffer(pb.samples,np.uint8).reshape(pb.height,pb.width)
  mask=Image.new('1',(pa.width,pa.height));draw=ImageDraw.Draw(mask)
  rects=[]
  for block in a.get_text('dict')['blocks']:
   if block['type']!=0:continue
   spans=[s for l in block['lines'] for s in l['spans']];text=' '.join(s['text'] for s in spans);words=re.findall('[A-Za-z]{2,}',text)
   if re.search('[А-Яа-яЁё]{2,}',text) or any(not mathword(w) for w in words):continue
   if not any(s['font'].replace(' ','').startswith(('CM','CambriaMath','Symbol','MTExtra')) for s in spans):continue
   r=f.Rect(block['bbox']);rects.append(list(r));draw.rectangle(tuple(v*4 for v in r),fill=1)
  for e in data['entries']:
   if e['page']!=pi or e.get('passthrough'):continue
   r=f.Rect(e.get('redact_rect',e['rect']));draw.rectangle(tuple(v*4 for v in r),fill=0)
  # Native equation bands explicitly restored after the prose masks remain expected.
  for keep in data.get('native_math_qa_rects',[]):
   if keep['page']==pi:draw.rectangle(tuple(v*4 for v in keep['rect']),fill=1)
  # A two-pixel tolerance admits raster resampling on restored transparent crops.
  from PIL import ImageFilter
  live=np.array(Image.fromarray((bb<100).astype('uint8')*255).filter(ImageFilter.MaxFilter(3)))>0
  missing=(aa<80)&np.array(mask,dtype=bool)&(~live)
  groups=components(missing);flagged=[g for g in groups if g['pixels']>15]
  row={'page':pi+1,'equation_blocks':len(rects),'missing_pixels':int(missing.sum()),'clusters':flagged};pages.append(row);print(row,flush=True)
 report={'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'scale':4,'flagged_components':sum(len(p['clusters']) for p in pages),'pages':pages}
 (ROOT/'tmp/izho-qa'/f'{year}_{kind}_native-math.json').write_text(json.dumps(report,indent=2),'utf8')
 return report['flagged_components']
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('year',type=int);p.add_argument('kind');a=p.parse_args();raise SystemExit(bool(run(a.year,a.kind)))

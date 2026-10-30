"""Find rendered Hangul ink hidden by a later white image, clip, or overlay."""
import argparse,json,hashlib,re
from pathlib import Path
import numpy as np,pymupdf as f
from PIL import Image,ImageFilter
from izho_native_math_audit import components
from izho_translate import ROOT,FONT
p=argparse.ArgumentParser(description=__doc__);p.add_argument('year',type=int);p.add_argument('kind',choices=['T','TS']);a=p.parse_args();path=ROOT/f'pdfx/izho/IZhO_{a.year}_{a.kind}_KO.pdf';d=f.open(path);rows=[]
for pi,page in enumerate(d):
 m=f.open();q=m.new_page(width=page.rect.width,height=page.rect.height);q.insert_font(fontname='ko',fontfile=str(FONT));chars=0
 for b in page.get_text('rawdict')['blocks']:
  if b['type']!=0:continue
  for l in b['lines']:
   for s in l['spans']:
    for c in s['chars']:
     if re.search('[가-힣]',c['c']):q.insert_text(c['origin'],c['c'],fontsize=s['size'],fontname='ko');chars+=1
 x=q.get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csGRAY);y=page.get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csGRAY);expected=np.frombuffer(x.samples,np.uint8).reshape(x.height,x.width)<80;actual=np.frombuffer(y.samples,np.uint8).reshape(y.height,y.width)<100;near=np.asarray(Image.fromarray(actual.astype(np.uint8)*255).filter(ImageFilter.MaxFilter(5)))>0;missing=expected&~near;groups=components(missing);row={'page':pi+1,'hangul_characters':chars,'missing_pixels':int(missing.sum()),'clusters':groups};rows.append(row);print(row,flush=True)
r={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'scale':4,'pixel_tolerance':2,'flagged_components':sum(len(r['clusters'])for r in rows),'pages':rows};(ROOT/f'tmp/izho-qa/{a.year}_{a.kind}_text-visibility.json').write_text(json.dumps(r,indent=2),'utf8');raise SystemExit(bool(r['flagged_components']))

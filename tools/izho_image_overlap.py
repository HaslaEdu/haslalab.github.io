"""Find opaque inline-math image backgrounds that hide ink in another inline image."""
import argparse,json,hashlib,io
from pathlib import Path
from PIL import Image
import numpy as np
import pymupdf as f
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('year',type=int);p.add_argument('kind',choices=['T','TS']);a=p.parse_args()
folder=R/f'tools/ko/izho/{a.year}/{a.kind}';data=json.loads((folder/'translation.json').read_text('utf8'));keys={};ratios={}
def key(im):return (im.width,im.height,hashlib.md5(im.convert('RGB').tobytes()).hexdigest())
for e in data['entries']:
 if e.get('passthrough'):continue
 for mi,m in enumerate(e.get('math',[])):
  if mi not in e.get('preserved_math',[]):
   im=Image.open(folder/m['file']);keys.setdefault(key(im),[]).append(m['file']);ratios[key(im)]=int(m['width'])/int(m['height'])
D=f.open(R/f'pdfx/izho/IZhO_{a.year}_{a.kind}_KO.pdf');report=[]
for pi,page in enumerate(D):
 imgs=[];clipped=[]
 for b in page.get_text('dict')['blocks']:
  if b['type']!=1:continue
  im=Image.open(io.BytesIO(b['image'])).convert('RGB');k=key(im)
  if k not in keys:continue
  r=f.Rect(b['bbox']);w,h=round(r.width*4),round(r.height*4)
  if w<=0 or h<=0:continue
  error=abs((r.width/r.height)/ratios[k]-1)
  if error>.025:
   tr=b['transform'];xx=tr[4]+(np.arange(im.width)+.5)/im.width*tr[0];yy=tr[5]+(np.arange(im.height)+.5)/im.height*tr[3]
   outside=(xx[None,:]<r.x0)|(xx[None,:]>r.x1)|(yy[:,None]<r.y0)|(yy[:,None]>r.y1)
   lost=int(((np.asarray(im).min(axis=2)<100)&outside).sum())
   if lost>15:clipped.append({'images':keys[k],'rect':list(r),'aspect_ratio_error':error,'clipped_dark_pixels':lost})
  im=im.resize((w,h));imgs.append((r,np.asarray(im).min(axis=2)<100,keys[k]))
 hits=[]
 for i,(r,ink,names) in enumerate(imgs):
  for q,over,names2 in imgs[i+1:]:
   x=r&q
   if x.width<.3 or x.height<.3:continue
   rx,ry=[round((x.x0-r.x0)*4),round((x.y0-r.y0)*4)];qx,qy=[round((x.x0-q.x0)*4),round((x.y0-q.y0)*4)];w,h=round(x.width*4),round(x.height*4)
   h=min(h,ink.shape[0]-ry,over.shape[0]-qy);w=min(w,ink.shape[1]-rx,over.shape[1]-qx)
   if w<=0 or h<=0:continue
   hidden=ink[ry:ry+h,rx:rx+w]&~over[qy:qy+h,qx:qx+w];n=int(hidden.sum())
   if n>15:hits.append({'earlier':names,'later':names2,'rect':list(x),'occluded_dark_pixels':n})
 report.append({'page':pi+1,'inline_images':len(imgs),'occlusions':hits,'clipped_images':clipped});print(report[-1],flush=True)
path=R/f'tmp/izho-qa/{a.year}_{a.kind}_inline-image-occlusion.json';path.write_text(json.dumps(report,indent=2),'utf8')
raise SystemExit(any(x['occlusions'] or x['clipped_images'] for x in report))

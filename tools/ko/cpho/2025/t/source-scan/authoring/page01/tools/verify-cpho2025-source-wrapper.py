from pathlib import Path
import json,hashlib,sys,time
sys.path.insert(0,'D:/CodexBuilds/Hasla-publish-20261031/tools')
from pdf_memory_gate import page_worker
import pymupdf as fitz,numpy as np
from PIL import Image,ImageDraw
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025');p=B/'source-clip-normalization.json';q=json.loads(p.read_text('utf8'));rows=[]
for n in range(1,7):
 with page_worker():
  with fitz.open(q['source'])as old,fitz.open(q['normalized_source'])as new:
   a=old[n-1].get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False);b=new[n-1].get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False)
   assert(a.width,a.height)==(b.width,b.height)
   before=np.frombuffer(a.samples,np.uint8).reshape(-1,3);after=np.frombuffer(b.samples,np.uint8).reshape(-1,3);changed=int(np.any(before!=after,axis=1).sum());assert changed==0,(n,changed)
   rows.append(dict(page=n,scale=4,changed_pixels=changed,original_rgb_sha256=hashlib.sha256(a.samples).hexdigest(),normalized_rgb_sha256=hashlib.sha256(b.samples).hexdigest()))
   if n==1:
    rect=fitz.Rect(60,132,535,178);pix=old[0].get_pixmap(matrix=fitz.Matrix(3,3),clip=rect,colorspace=fitz.csRGB,alpha=False);im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);draw=ImageDraw.Draw(im)
    for x in range(60,536,10):
     xp=round((x-rect.x0)*3);draw.line((xp,0,xp,im.height),fill=(170,190,220),width=1);draw.text((xp+1,0),str(x),fill=(80,80,160))
    for y in range(140,178,10):
     yp=round((y-rect.y0)*3);draw.line((0,yp,im.width,yp),fill=(170,190,220),width=1);draw.text((0,yp+1),str(y),fill=(80,80,160))
    im.save(B/'p1-hint-coordinate-review.png')
 print(json.dumps(rows[-1]),flush=True);time.sleep(.6)
q['render_validation']=rows;q['status']='SOURCE_WRAPPER_PIXEL_IDENTICAL';p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')

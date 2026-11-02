from pathlib import Path
import json
import pymupdf as fitz
import cv2,numpy as np
from PIL import Image
D=Path('D:/CodexBuilds/Hasla-original-style-20261031');scale=2420/595
image=np.asarray(Image.open(D/'cpho2025/source-original-p1.png').convert('L'));x0,y0,x1,y1=[round(v*scale)for v in[62,193,231.7,209]];source=(image[y0:y1,x0:x1]<160).astype(np.float32);text='用在决定分子排布中扮演着重要角色'
fonts=[('SimSun','C:/Windows/Fonts/simsun.ttc'),('KaiTi',str(D/'official-hans-fonts/faces/simkai.ttf')),('FangSong',str(D/'official-hans-fonts/faces/simfang.ttf'))];rows=[]
for name,file in fonts:
 doc=fitz.open();page=doc.new_page(width=200,height=35);page.insert_font(fontname='CompareFace',fontfile=file)
 for size in np.arange(9.8,11.001,.02):
  xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,b'');page.set_contents(xref);page.insert_text((3,23),text,fontname='CompareFace',fontsize=float(size))
  pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY,alpha=False);a=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width);mask=(a<128).astype(np.uint8)
  for spread_x,spread_y in[(0,0),(1,0),(0,1),(1,1)]:
   m=cv2.dilate(mask,np.ones((2*spread_y+1,2*spread_x+1),np.uint8));ys,xs=np.nonzero(m);template=m[ys.min():ys.max()+1,xs.min():xs.max()+1].astype(np.float32)
   if template.shape[0]>source.shape[0]or template.shape[1]>source.shape[1]:continue
   score=cv2.matchTemplate(source,template,cv2.TM_CCORR);_,intersection,_,location=cv2.minMaxLoc(score);union=float(source.sum()+template.sum()-intersection);iou=intersection/union
   rows.append(dict(font=name,size_pt=round(float(size),3),spread_x=spread_x,spread_y=spread_y,intersection=round(intersection),union=round(union),iou=iou,location=location,template_pixels=[template.shape[1],template.shape[0]]))
 doc.close()
rows.sort(key=lambda r:-r['iou']);out=dict(source_sha256='b7c3ff8e024d4805306b7cd7e11bb22dd487ff1ee1aa6a504f096a1676296957',scope='Read-only scanned CJK typeface/physical point-size calibration on a manually verified contiguous16-character original prose run; no translated PDF generated and no equations recognized or retyped',source_crop_pixel=[x0,y0,x1,y1],text=text,source_foreground_pixels=int(source.sum()),top20=rows[:20],best_by_font={n:next(r for r in rows if r['font']==n)for n,_ in fonts})
(D/'cpho2025/body-font-calibration.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf8');print(json.dumps(out['best_by_font'],ensure_ascii=False))

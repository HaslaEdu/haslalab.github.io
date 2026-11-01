from pathlib import Path
import json
import pymupdf as f,cv2,numpy as np
from PIL import Image
P=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025/p6-authoring');im=np.asarray(Image.open(P/'source-p6-4x.png').convert('L'));results=[]
for name,text,rect in [('first','第',[264,773,275,787]),('middle','页',[284,773,296,787]),('last','页',[325,772,337,786])]:
 x0,y0,x1,y1=[round(v*4)for v in rect];mask=(im[y0:y1,x0:x1]<160).astype(np.float32);rows=[]
 with f.open()as d:
  p=d.new_page(width=60,height=30);p.insert_font(fontname='Face',fontfile='C:/Windows/Fonts/simsun.ttc')
  for size in np.arange(8.1,8.801,.02):
   for stroke in [0,.2,.35,.5,.6]:
    xref=d.get_new_xref();d.update_object(xref,'<<>>');d.update_stream(xref,b'');p.set_contents(xref);p.insert_text((4,22),text,fontname='Face',fontsize=float(size),render_mode=2,border_width=stroke)
    pic=p.get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csGRAY,alpha=False);a=np.frombuffer(pic.samples,np.uint8).reshape(pic.height,pic.width);ink=(a<160).astype(np.uint8);ys,xs=np.nonzero(ink);tpl=ink[ys.min():ys.max()+1,xs.min():xs.max()+1].astype(np.float32)
    if tpl.shape[0]>mask.shape[0]or tpl.shape[1]>mask.shape[1]:continue
    _,inter,_,loc=cv2.minMaxLoc(cv2.matchTemplate(mask,tpl,cv2.TM_CCORR));score=float(inter/(mask.sum()+tpl.sum()-inter));origin=[(x0+loc[0]+16-int(xs.min()))/4,(y0+loc[1]+88-int(ys.min()))/4]
    rows.append(dict(point_size=round(float(size),2),stroke=stroke,iou=score,origin=origin))
 rows.sort(key=lambda x:-x['iou']);results.append(dict(field=name,source_CJK=text,source_rect=rect,font='SimSun',best=rows[0],top10=rows[:10]))
 print(name,rows[0],flush=True)
(P/'page06-footer-source-calibration.json').write_text(json.dumps(dict(source_sha256='c9562e8f6053b454391083289b179f28ed29f7d9024723a34a2a8b0e663bd306',page=6,scope='Only source Chinese glyph face/physical point/baseline measurement, before any translation fitting',measurements=results),indent=2),'utf8')

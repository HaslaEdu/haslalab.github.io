from pathlib import Path
import sys,json,hashlib
import cv2,numpy as np,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from cpho_2005_ts_compose import font_path
cv2.setNumThreads(1)
fields=[('heading','参考解答',[95,60,154,77],12.125,'SimHei'),('left-top','表示平板',[115,95,205,114],12.3,'SimSun'),('left-bottom','等于光在空气',[65,276,218,294],12.425,'SimSun'),('right-top','化简后得',[440,102,514,119],12.475,'SimSun'),('right-middle','单色光',[435,231,666,252],12.175,'SimSun')]
result=[]
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf') as doc:
 for name,text,rect,size,face in fields:
  p=doc[3].get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(rect),colorspace=f.csGRAY,alpha=False)
  source=(np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width)<160).astype(np.float32);candidates=[]
  with f.open()as d:
   pg=d.new_page(width=220,height=40);pg.insert_font(fontname='CalibratedOriginalFace',fontfile=str(font_path('en',face)))
   for stroke in np.arange(0,1.401,.025):
    xref=d.get_new_xref();d.update_object(xref,'<<>>');d.update_stream(xref,b'');pg.set_contents(xref)
    pg.insert_text((4,27),text,fontname='CalibratedOriginalFace',fontsize=size,render_mode=2 if stroke else 0,border_width=float(stroke/size))
    pix=pg.get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csGRAY,alpha=False)
    ar=(np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)<128).astype(np.float32);yy,xx=np.nonzero(ar);template=ar[yy.min():yy.max()+1,xx.min():xx.max()+1]
    _,inter,_,loc=cv2.minMaxLoc(cv2.matchTemplate(source,template,cv2.TM_CCORR));patch=source[loc[1]:loc[1]+template.shape[0],loc[0]:loc[0]+template.shape[1]]
    iou=float(inter/(patch.sum()+template.sum()-inter));candidates.append(dict(stroke_points=round(float(stroke),3),iou=iou))
  candidates.sort(key=lambda v:-v['iou']);result.append(dict(field=name,source_text=text,source_rect=rect,source_point_size=size,source_face=face,best=candidates[0],top5=candidates[:5]));print(name,candidates[:3],flush=True)
(B/'page04-source-stroke-calibration.json').write_text(json.dumps(dict(source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',scope='Original Chinese glyph ink only at previously measured fixed source points; no translated text involved.',fields=result),ensure_ascii=False,indent=2)+'\n','utf8')

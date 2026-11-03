from pathlib import Path
import sys,json
import cv2,numpy as np,pymupdf as f
sys.path.insert(0,'D:/CodexBuilds/Hasla-publish-20261031/tools')
from pdf_memory_gate import page_worker
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS');fonts=[('SimSun','C:/Windows/Fonts/simsun.ttc'),('SimHei','D:/CodexBuilds/Hasla-original-style-20261031/official-hans-fonts/faces/simhei.ttf'),('KaiTi','D:/CodexBuilds/Hasla-original-style-20261031/official-hans-fonts/faces/simkai.ttf')]
fields=[('heading','参考解答',[95,60,154,77],12,15),('left-top','表示平板',[115,95,205,114],11.5,14),('left-bottom','等于光在空气',[65,276,218,294],11.5,14),('right-top','化简后得',[440,102,514,119],11.5,14),('right-middle','单色光',[435,231,666,252],11.5,14)]
results=[]
with page_worker(),f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as original:
 for name,text,rect,start,end in fields:
  pic=original[3].get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(rect),colorspace=f.csGRAY,alpha=False);source=(np.frombuffer(pic.samples,np.uint8).reshape(pic.height,pic.width)<160).astype(np.float32);candidates=[]
  for face,file in fonts:
   with f.open()as d:
    p=d.new_page(width=220,height=40);p.insert_font(fontname='Face',fontfile=file)
    for size in np.arange(start,end+.001,.025):
     xref=d.get_new_xref();d.update_object(xref,'<<>>');d.update_stream(xref,b'');p.set_contents(xref);p.insert_text((4,27),text,fontname='Face',fontsize=float(size))
     pix=p.get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csGRAY,alpha=False);a=(np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)<128).astype(np.uint8)
     for sx,sy in [(0,0),(1,0),(0,1),(1,1),(2,1),(1,2)]:
      ink=cv2.dilate(a,np.ones((2*sy+1,2*sx+1),np.uint8));yy,xx=np.nonzero(ink);template=ink[yy.min():yy.max()+1,xx.min():xx.max()+1].astype(np.float32)
      if template.shape[0]>source.shape[0]or template.shape[1]>source.shape[1]:continue
      _,inter,_,loc=cv2.minMaxLoc(cv2.matchTemplate(source,template,cv2.TM_CCORR));patch=source[loc[1]:loc[1]+template.shape[0],loc[0]:loc[0]+template.shape[1]];score=float(inter/(patch.sum()+template.sum()-inter));origin=[pic.x/4+(loc[0]+16-int(xx.min()))/4,pic.y/4+(loc[1]+108-int(yy.min()))/4]
      candidates.append(dict(face=face,point_size=round(float(size),3),spread=[sx,sy],iou=score,source_origin=origin))
  candidates.sort(key=lambda x:-x['iou']);result=dict(field=name,source_text=text,source_rect=rect,best=candidates[0],best_by_face={face:next(r for r in candidates if r['face']==face)for face,_ in fonts},top20=candidates[:20]);results.append(result);print(json.dumps(result['best']),flush=True)
(B/'page04-source-font-calibration.json').write_text(json.dumps(dict(source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',page=4,scope='Original actual Chinese shapes only, no translated text or box fitting',fields=results),ensure_ascii=False,indent=2),'utf8')

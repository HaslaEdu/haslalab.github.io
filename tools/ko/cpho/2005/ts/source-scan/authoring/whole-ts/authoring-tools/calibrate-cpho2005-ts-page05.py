from pathlib import Path
import sys,json
import cv2,numpy as np,pymupdf as f
sys.path.insert(0,'D:/CodexBuilds/Hasla-publish-20261031/tools')
from pdf_memory_gate import page_worker
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
fonts=[('SimSun','C:/Windows/Fonts/simsun.ttc'),('SimHei','D:/CodexBuilds/Hasla-original-style-20261031/official-hans-fonts/faces/simhei.ttf')]
fields=[('angle-top','故存在某一入射角',[149,61,254,81]),('left-narrow','水平向右',[114,150,168,168]),('left-wide','作为一个系统',[62,247,139,265]),('right-top','振幅为',[438,97,478,115]),('right-middle','因此系统',[438,229,491,247]),('right-bottom','此时弹簧',[490,479,556,499])]
results=[];cv2.setNumThreads(1)
with page_worker(),f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as original:
 for name,text,rect in fields:
  pic=original[4].get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(rect),colorspace=f.csGRAY,alpha=False);source=(np.frombuffer(pic.samples,np.uint8).reshape(pic.height,pic.width)<160).astype(np.float32);candidates=[]
  for face,file in fonts:
   with f.open()as d:
    page=d.new_page(width=180,height=40);page.insert_font(fontname='MeasuredSource',fontfile=file)
    for size in np.arange(11.5,13.501,.025):
     xref=d.get_new_xref();d.update_object(xref,'<<>>');d.update_stream(xref,b'');page.set_contents(xref);page.insert_text((4,27),text,fontname='MeasuredSource',fontsize=float(size))
     pix=page.get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csGRAY,alpha=False);a=(np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)<128).astype(np.uint8)
     for sx,sy in [(0,0),(1,0),(0,1),(1,1),(2,1),(1,2)]:
      grown=cv2.dilate(a,np.ones((2*sy+1,2*sx+1),np.uint8))
      for angle in [-1,-.5,0,.5,1]if name=='angle-top'else[0]:
       ink=grown if not angle else cv2.warpAffine(grown,cv2.getRotationMatrix2D((16,108),angle,1),grown.shape[::-1],flags=cv2.INTER_NEAREST,borderValue=0)
       yy,xx=np.nonzero(ink);template=ink[yy.min():yy.max()+1,xx.min():xx.max()+1].astype(np.float32)
       if template.shape[0]>source.shape[0]or template.shape[1]>source.shape[1]:continue
       _,inter,_,loc=cv2.minMaxLoc(cv2.matchTemplate(source,template,cv2.TM_CCORR));patch=source[loc[1]:loc[1]+template.shape[0],loc[0]:loc[0]+template.shape[1]];score=float(inter/(patch.sum()+template.sum()-inter));origin=[pic.x/4+(loc[0]+16-int(xx.min()))/4,pic.y/4+(loc[1]+108-int(yy.min()))/4]
       candidates.append(dict(face=face,point_size=round(float(size),3),spread=[sx,sy],iou=score,source_origin=origin,baseline_angle_degrees=-angle))
  candidates.sort(key=lambda r:-r['iou']);result=dict(field=name,source_text=text,source_rect=rect,best=candidates[0],best_by_face={face:next(r for r in candidates if r['face']==face)for face,_ in fonts},top20=candidates[:20]);results.append(result);print(name,json.dumps(result['best']),flush=True)
(B/'page05-source-font-calibration.json').write_text(json.dumps(dict(source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',page=5,scope='Original actual Chinese glyphs only; physical font point and baseline estimates, no translated text or fit-to-box.',fields=results),ensure_ascii=False,indent=2)+'\n','utf8')

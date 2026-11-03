"""Resolve two visibly distinct source-prose typefaces using source pixels only."""
from pathlib import Path
import json,cv2,numpy as np,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS');fontroot=B.parents[1]/'official-hans-fonts/faces'
fonts=[('SimSun','C:/Windows/Fonts/simsun.ttc'),('SimHei',str(fontroot/'simhei.ttf')),('KaiTi',str(fontroot/'simkai.ttf')),('FangSong',str(fontroot/'simfang.ttf'))]
fields=[('particle-first','带电粒子',[98.5,129,153,148]),('axial-second','上运动',[59,202,103,222]),('individual-second','处有极大',[155,333,216,355])]
results=[];cv2.setNumThreads(1)
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as original:
 for name,text,rect in fields:
  pic=original[11].get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(rect),colorspace=f.csGRAY,alpha=False);source=(np.frombuffer(pic.samples,np.uint8).reshape(pic.height,pic.width)<160).astype(np.float32);candidates=[]
  for face,file in fonts:
   with f.open()as d:
    page=d.new_page(width=180,height=40);page.insert_font(fontname='MeasuredSource',fontfile=file)
    for size in np.arange(11,13.751,.025):
     xref=d.get_new_xref();d.update_object(xref,'<<>>');d.update_stream(xref,b'');page.set_contents(xref);page.insert_text((4,27),text,fontname='MeasuredSource',fontsize=float(size))
     pix=page.get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csGRAY,alpha=False);a=(np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)<128).astype(np.uint8)
     for sx,sy in[(0,0),(1,0),(0,1),(1,1),(2,1),(1,2)]:
      grown=cv2.dilate(a,np.ones((2*sy+1,2*sx+1),np.uint8))
      for angle in[-1,-.5,0,.5,1]:
       ink=grown if not angle else cv2.warpAffine(grown,cv2.getRotationMatrix2D((16,108),angle,1),grown.shape[::-1],flags=cv2.INTER_NEAREST,borderValue=0)
       yy,xx=np.nonzero(ink);template=ink[yy.min():yy.max()+1,xx.min():xx.max()+1].astype(np.float32)
       if template.shape[0]>source.shape[0]or template.shape[1]>source.shape[1]:continue
       _,inter,_,loc=cv2.minMaxLoc(cv2.matchTemplate(source,template,cv2.TM_CCORR));patch=source[loc[1]:loc[1]+template.shape[0],loc[0]:loc[0]+template.shape[1]];score=float(inter/(patch.sum()+template.sum()-inter));origin=[pic.x/4+(loc[0]+16-int(xx.min()))/4,pic.y/4+(loc[1]+108-int(yy.min()))/4]
       candidates.append(dict(face=face,point_size=round(float(size),3),spread=[sx,sy],iou=score,source_origin=origin,baseline_angle_degrees=-angle))
   print(name,face,'best',max(r['iou']for r in candidates if r['face']==face),flush=True)
  candidates.sort(key=lambda r:-r['iou']);result=dict(field=name,source_text=text,source_rect=rect,best=candidates[0],best_by_face={face:next(r for r in candidates if r['face']==face)for face,_ in fonts},top20=candidates[:20]);results.append(result);print(name,'BEST',json.dumps(result['best']),flush=True)
(B/'page12-distinct-typeface-calibration.json').write_text(json.dumps(dict(source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',page=12,scope='Known original source CJK shapes only. Compare real SimSun/SimHei/KaiTi/FangSong outlines at source physical sizes and scan angles; never translated text fitting.',fields=results),ensure_ascii=False,indent=2)+'\n','utf8')

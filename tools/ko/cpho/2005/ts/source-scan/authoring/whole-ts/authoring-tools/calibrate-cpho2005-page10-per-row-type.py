"""Measure every original prose row's physical SimSun size before translation."""
from pathlib import Path
import json,numpy as np,cv2,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
prior=json.loads((B/'page10-row-baseline-proposals.json').read_text('utf8'));rows=prior['rows'];results=[];cv2.setNumThreads(1)
cachepath=B/'page10-per-row-source-type-proposals.json'
cache=json.loads(cachepath.read_text('utf8'))if cachepath.exists()else{}
cached={r['id']:r for r in cache.get('rows',[])}
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as original,f.open()as probe:
 page=probe.new_page(width=180,height=40);page.insert_font(fontname='OriginalSimSun',fontfile='C:/Windows/Fonts/simsun.ttc')
 for row in rows:
  old=cached.get(row['id'])
  if old and old['source_measurement_window']==row['source_measurement_window'] and old['source_text']==row['source_text'] and old.get('source_size_range',[11.5,14.751,.025])==row.get('source_size_range',[11.5,14.751,.025]):
   results.append(old);print('Retained unchanged source measurement',row['id'],flush=True);continue
  rect=row['source_measurement_window'];text=row['source_text'];pix=original[9].get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(rect),colorspace=f.csGRAY,alpha=False);source=(np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)<160).astype(np.float32);candidates=[]
  for size in np.arange(7.5 if row['id']=='caption'else 11.5,14.751,.025):
   xref=probe.get_new_xref();probe.update_object(xref,'<<>>');probe.update_stream(xref,b'');page.set_contents(xref);page.insert_text((4,27),text,fontname='OriginalSimSun',fontsize=float(size))
   p=page.get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csGRAY,alpha=False);a=(np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width)<128).astype(np.uint8)
   for sx,sy in[(1,1),(2,1),(1,2)]:
    grown=cv2.dilate(a,np.ones((2*sy+1,2*sx+1),np.uint8))
    for angle in[-1,-.5,0,.5,1]:
     ink=grown if not angle else cv2.warpAffine(grown,cv2.getRotationMatrix2D((16,108),angle,1),grown.shape[::-1],flags=cv2.INTER_NEAREST,borderValue=0)
     yy,xx=np.nonzero(ink);template=ink[yy.min():yy.max()+1,xx.min():xx.max()+1].astype(np.float32)
     if template.shape[0]>source.shape[0]or template.shape[1]>source.shape[1]:continue
     _,inter,_,loc=cv2.minMaxLoc(cv2.matchTemplate(source,template,cv2.TM_CCORR));patch=source[loc[1]:loc[1]+template.shape[0],loc[0]:loc[0]+template.shape[1]];score=float(inter/(patch.sum()+template.sum()-inter));origin=[pix.x/4+(loc[0]+16-int(xx.min()))/4,pix.y/4+(loc[1]+108-int(yy.min()))/4]
     candidates.append(dict(face='SimSun',source_point_size=round(float(size),3),source_origin=origin,source_baseline=origin[1],source_baseline_angle_degrees=-angle,spread=[sx,sy],iou=score))
  candidates.sort(key=lambda r:-r['iou']);assert candidates,row['id']
  result=dict(id=row['id'],source_region=row['source_region'],source_text=text,source_measurement_window=rect,source_size_range=row.get('source_size_range',[11.5,14.751,.025]),best=candidates[0],top10=candidates[:10],reviewed=False,no_translated_text_used=True);results.append(result)
  print(row['id'],candidates[0]['source_point_size'],candidates[0]['source_baseline'],round(candidates[0]['iou'],3),flush=True)
  (B/'page10-per-row-source-type-proposals.json').write_text(json.dumps(dict(source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',page=10,complete=len(results)==len(rows),scope='Original source known CJK samples only. SimSun family independently compared against SimHei/KaiTi/FangSong for visually atypical rows. Source pointsize/baseline estimates, not translated-width or font fitting. Every row retains its measured point, including larger source prose. No erase ROI is produced.',rows=results),ensure_ascii=False,indent=2)+'\n','utf8')
assert len(results)==len(rows)
cachepath.write_text(json.dumps(dict(source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',page=10,complete=True,scope='Original source CJK-only physical type measurement. Cached measurements are retained only for identical explicit source samples and windows; no target font fitting.',rows=results),ensure_ascii=False,indent=2)+'\n','utf8')

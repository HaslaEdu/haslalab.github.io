"""Independent source-only proposals for earlier low-confidence font samples.

This never edits an authored layout or a reviewed PDF. Expanded measurement
windows contain the same explicitly read CJK words, never target translations.
"""
from pathlib import Path
import json,cv2,numpy as np,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS');results=[];cv2.setNumThreads(1)
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as source,f.open()as probe:
 page=probe.new_page(width=180,height=40);page.insert_font(fontname='OriginalSimSun',fontfile='C:/Windows/Fonts/simsun.ttc')
 for number in [5,7,8,10]:
  prior=json.loads((B/f'page{number:02}-per-row-source-type-proposals.json').read_text('utf8'));layout=json.loads((B/f'authoring/page{number:02}-layout.json').read_text('utf8'));authored={r['id']:r for r in layout['rows']}
  for row in prior['rows']:
   if row['best']['iou']>=.7:continue
   assert authored[row['id']]['source_prose_face']=='SimSun'
   oldrect=row['source_measurement_window'];rect=[oldrect[0]-2,oldrect[1]-2,oldrect[2]+2,oldrect[3]+2];text=row['source_text'];p=source[number-1].get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(rect),colorspace=f.csGRAY,alpha=False);original=(np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width)<160).astype(np.float32);candidates=[]
   for size in np.arange(7.5 if row['id']=='caption'else 11,14.751,.025):
    xref=probe.get_new_xref();probe.update_object(xref,'<<>>');probe.update_stream(xref,b'');page.set_contents(xref);page.insert_text((4,27),text,fontname='OriginalSimSun',fontsize=float(size));q=page.get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csGRAY,alpha=False);a=(np.frombuffer(q.samples,np.uint8).reshape(q.height,q.width)<128).astype(np.uint8)
    for sx,sy in [(1,1),(2,1),(1,2)]:
     grown=cv2.dilate(a,np.ones((2*sy+1,2*sx+1),np.uint8))
     for angle in [-1,-.5,0,.5,1]:
      ink=grown if not angle else cv2.warpAffine(grown,cv2.getRotationMatrix2D((16,108),angle,1),grown.shape[::-1],flags=cv2.INTER_NEAREST,borderValue=0);yy,xx=np.nonzero(ink);template=ink[yy.min():yy.max()+1,xx.min():xx.max()+1].astype(np.float32)
      if template.shape[0]>original.shape[0]or template.shape[1]>original.shape[1]:continue
      _,inter,_,loc=cv2.minMaxLoc(cv2.matchTemplate(original,template,cv2.TM_CCORR));patch=original[loc[1]:loc[1]+template.shape[0],loc[0]:loc[0]+template.shape[1]];score=float(inter/(patch.sum()+template.sum()-inter));origin=[p.x/4+(loc[0]+16-int(xx.min()))/4,p.y/4+(loc[1]+108-int(yy.min()))/4];candidates.append(dict(face='SimSun',source_point_size=round(float(size),3),source_origin=origin,source_baseline=origin[1],source_baseline_angle_degrees=-angle,spread=[sx,sy],iou=score))
   candidates.sort(key=lambda r:-r['iou']);assert candidates
   result=dict(page=number,id=row['id'],source_text=text,old_source_window=oldrect,expanded_source_window=rect,old= row['best'],new=candidates[0],top10=candidates[:10],reviewed=False,no_layout_or_PDF_modified=True,source_region=row['source_region']);results.append(result)
   print(number,row['id'],'old',row['best']['source_point_size'],row['best']['source_baseline'],round(row['best']['iou'],3),'expanded',candidates[0]['source_point_size'],candidates[0]['source_baseline'],round(candidates[0]['iou'],3),flush=True)
   (B/'expanded-weak-source-window-proposals.json').write_text(json.dumps(dict(source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',proposals_only=True,authored_layouts_and_reviewed_outputs_unchanged=True,rows=results),ensure_ascii=False,indent=2)+'\n','utf8')

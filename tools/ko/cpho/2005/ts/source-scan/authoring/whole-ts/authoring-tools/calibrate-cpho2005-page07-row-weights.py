"""Original CJK print weight and independent Korean primary stem matching."""
from pathlib import Path
import json,sys
import cv2,numpy as np,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from cpho_2005_ts_compose import new_font,font_path,write_words
from cpho_2013_ts_korean_stems import stems
rows=json.loads((B/'page07-per-row-source-type-proposals.json').read_text('utf8'))['rows'];results=[];cv2.setNumThreads(1)
TEXT='판의 두께와 빛의 속력을';raw,metric,fontqa=new_font(font_path('ko'),TEXT)
cachepath=B/'page07-row-weight-calibration.json'
cached=json.loads(cachepath.read_text('utf8'))if cachepath.exists()else{}
assert not cached or cached['source_sha256']=='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f'
byid={r['id']:r for r in cached.get('rows',[])}
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as source,f.open()as english,f.open()as korean:
 ep=english.new_page(width=180,height=40);ep.insert_font(fontname='SourceSimSun',fontfile=str(font_path('en')))
 kp=korean.new_page(width=180,height=28);kp.insert_font(fontname='SourceRoleBatang',fontbuffer=raw)
 for row in rows:
  prior=byid.get(row['id'])
  if prior and row['id']!='section-four'and prior['source_point_size']==row['best']['source_point_size']and prior['source_measurement_window']==row['source_measurement_window']and prior['source_role_font']['source_sha256']==fontqa['source_sha256']:
   results.append(prior);print('unchanged fixed-source measurement retained',row['id'],flush=True);continue
  size=row['best']['source_point_size'];rect=row['source_measurement_window'];text=row['source_text'];angle=-row['best']['source_baseline_angle_degrees'];candidates=[]
  pic=source[6].get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(rect),colorspace=f.csGRAY,alpha=False);original=(np.frombuffer(pic.samples,np.uint8).reshape(pic.height,pic.width)<160).astype(np.float32)
  for stroke in np.arange(0,1.401,.025):
   xref=english.get_new_xref();english.update_object(xref,'<<>>');english.update_stream(xref,b'');ep.set_contents(xref);ep.insert_text((4,27),text,fontname='SourceSimSun',fontsize=size,render_mode=2 if stroke else 0,border_width=float(stroke/size))
   p=ep.get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csGRAY,alpha=False);a=(np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width)<160).astype(np.uint8)
   ink=a if not angle else cv2.warpAffine(a,cv2.getRotationMatrix2D((16,108),angle,1),a.shape[::-1],flags=cv2.INTER_NEAREST,borderValue=0);yy,xx=np.nonzero(ink);template=ink[yy.min():yy.max()+1,xx.min():xx.max()+1].astype(np.float32)
   if template.shape[0]>original.shape[0]or template.shape[1]>original.shape[1]:continue
   _,inter,_,loc=cv2.minMaxLoc(cv2.matchTemplate(original,template,cv2.TM_CCORR));patch=original[loc[1]:loc[1]+template.shape[0],loc[0]:loc[0]+template.shape[1]];score=float(inter/(patch.sum()+template.sum()-inter));candidates.append(dict(stroke_points=round(float(stroke),3),iou=score))
  candidates.sort(key=lambda r:-r['iou']);assert candidates,row['id']
  reference_override=None
  p=source[6].get_pixmap(matrix=f.Matrix(8,8),clip=f.Rect(rect),colorspace=f.csGRAY,alpha=False);gray=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width)
  try:source_stems=stems(gray,size)
  except ValueError:
   if row['id']!='section-four':raise
   # 三 has horizontal strokes only. Use the same-page, same-family nearby
   # original prose as an explicitly declared weight reference, not an
   # invented vertical-stem measurement of that ordinal.
   reference=next(r for r in rows if r['id']=='compression-first');reference_rect=reference['source_measurement_window'];reference_size=reference['best']['source_point_size']
   p=source[6].get_pixmap(matrix=f.Matrix(8,8),clip=f.Rect(reference_rect),colorspace=f.csGRAY,alpha=False);gray=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width);source_stems=stems(gray,reference_size)
   reference_override=dict(id=reference['id'],source_rect=reference_rect,source_point_size=reference_size,reason='Original Chinese ordinal 三 has no primary vertical stem; match the neighbouring original SimSun body weight. The ordinal font point stays independently fixed.')
  ko=[]
  for stroke in np.arange(0,1.001,.025):
   xref=korean.get_new_xref();korean.update_object(xref,'<<>>');korean.update_stream(xref,b'');kp.set_contents(xref);write_words(kp,2,20,TEXT,metric,size,'SourceRoleBatang',2 if stroke else 0,float(stroke))
   p=kp.get_pixmap(matrix=f.Matrix(8,8),colorspace=f.csGRAY,alpha=False);gray=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width);m=stems(gray,size)
   error=sum(abs(m[d]['median_pt']-source_stems[d]['median_pt'])for d in ['vertical','horizontal']);contrast=abs(m['vertical']['median_pt']/m['horizontal']['median_pt']-source_stems['vertical']['median_pt']/source_stems['horizontal']['median_pt'])
   ko.append(dict(stroke_points=round(float(stroke),3),stem_median_error_pt=error,stem_contrast_error=contrast,metrics=m))
  ko.sort(key=lambda r:(r['stem_median_error_pt'],r['stem_contrast_error'],r['stroke_points']))
  results.append(dict(id=row['id'],source_point_size=size,source_measurement_window=rect,English_source_SimSun_stroke=candidates[0],English_top5=candidates[:5],Korean_source_role_Batang_stroke=ko[0],Korean_top5=ko[:5],source_primary_stems=source_stems,primary_stem_reference_override=reference_override,source_role_font=fontqa))
  print(row['id'],'fixed_pt',size,'EN',candidates[0]['stroke_points'],'KO',ko[0]['stroke_points'],flush=True)
  (B/'page07-row-weight-calibration.json').write_text(json.dumps(dict(source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',page=7,complete=len(results)==len(rows),scope='Original actual Chinese glyph stroke comparison at independently fixed source font pointsize/scan angle. Korean Batang matched by independent vertical/horizontal primary stem medians and contrast, not whole ink density. No translated text fitting; source mathematical images untouched.',rows=results),ensure_ascii=False,indent=2)+'\n','utf8')
assert len(results)==len(rows)
cachepath.write_text(json.dumps(dict(source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',page=7,complete=True,scope='Source Chinese print-weight and independent Korean primary stem measurements at fixed source point sizes. Cached records require identical source point/window and role font SHA.',rows=results),ensure_ascii=False,indent=2)+'\n','utf8')

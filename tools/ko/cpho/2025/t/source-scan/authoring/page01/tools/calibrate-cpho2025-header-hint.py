from pathlib import Path
import json
import pymupdf as fitz,cv2,numpy as np
from PIL import Image
D=Path('D:/CodexBuilds/Hasla-original-style-20261031');B=D/'cpho2025';scale=2420/595;image=np.asarray(Image.open(B/'source-original-p1.png').convert('L'));offset_y=842-840.8678-.5661157
fonts=[('SimSun','C:/Windows/Fonts/simsun.ttc'),('SimHei',str(D/'official-hans-fonts/faces/simhei.ttf')),('KaiTi',str(D/'official-hans-fonts/faces/simkai.ttf')),('FangSong',str(D/'official-hans-fonts/faces/simfang.ttf'))]
fields=[('hint','对于多元函数',[113,141,177.5,158],9.9,10.6),('title','届全国中学生物理竞赛决赛理论考试试题',[194,88,442.5,105],13.3,14.0),('date_year','年',[256.5,108,269,121.5],9.9,10.6)]
result={}
for field,text,rect,start,end in fields:
 x0,y0,x1,y1=[round(v*scale)for v in rect];source=(image[y0:y1,x0:x1]<160).astype(np.float32);rows=[]
 for name,file in fonts:
  doc=fitz.open();page=doc.new_page(width=300,height=40);page.insert_font(fontname='CompareFace',fontfile=file)
  for size in np.arange(start,end+.001,.02):
   xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,b'');page.set_contents(xref);page.insert_text((3,26),text,fontname='CompareFace',fontsize=float(size))
   pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY,alpha=False);a=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width);mask=(a<128).astype(np.uint8)
   for spread_x,spread_y in[(0,0),(1,0),(0,1),(1,1)]:
    m=cv2.dilate(mask,np.ones((2*spread_y+1,2*spread_x+1),np.uint8));ys,xs=np.nonzero(m);rawbox=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)];template=m[rawbox[1]:rawbox[3],rawbox[0]:rawbox[2]].astype(np.float32)
    if template.shape[0]>source.shape[0]or template.shape[1]>source.shape[1]:continue
    corr=cv2.matchTemplate(source,template,cv2.TM_CCORR);_,intersection,_,location=cv2.minMaxLoc(corr);union=float(source.sum()+template.sum()-intersection)
    origin=[(x0+location[0]+3*scale-rawbox[0])/scale,offset_y+(y0+location[1]+26*scale-rawbox[1])/scale]
    rows.append(dict(font=name,size_pt=round(float(size),3),spread_x=spread_x,spread_y=spread_y,iou=intersection/union,source_font_origin_point=origin,template_pixels=[template.shape[1],template.shape[0]],raw_template_bbox=rawbox,match_location=location))
  doc.close()
 rows.sort(key=lambda r:-r['iou']);q=dict(field=field,source_sha256='b7c3ff8e024d4805306b7cd7e11bb22dd487ff1ee1aa6a504f096a1676296957',source_native_image_offset_y_pt=offset_y,source_crop_pixels=[x0,y0,x1,y1],manually_verified_CJK_text=text,scope='Typeface/physical point-size and baseline calibration only; original math retained as original bitmap programs at1x',top20=rows[:20],best_by_font={n:next(r for r in rows if r['font']==n)for n,_ in fonts})
 (B/f'{field}-font-calibration.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),'utf8');result[field]=q['best_by_font'];print(json.dumps({field:q['best_by_font']},ensure_ascii=False),flush=True)

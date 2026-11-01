from pathlib import Path
import json
import pymupdf as fitz,cv2,numpy as np
from PIL import Image
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025');scale=2420/595;offset_y=842-840.8678-.5661157;image=np.asarray(Image.open(B/'source-original-p1.png').convert('L'));x0,y0,x1,y1=[round(v*scale)for v in[62,193,231.7,209]];source=(image[y0:y1,x0:x1]<160).astype(np.float32);text='用在决定分子排布中扮演着重要角色';rows=[];size=10.24
doc=fitz.open();page=doc.new_page(width=200,height=40);page.insert_font(fontname='Face',fontfile='C:/Windows/Fonts/simsun.ttc')
for line_width in [0,*np.arange(.1,.701,.025)]:
 xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,b'');page.set_contents(xref);page.insert_text((3,26),text,fontname='Face',fontsize=size,render_mode=2 if line_width else 0,border_width=float(line_width)/size,color=(0,0,0))
 pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY,alpha=False);a=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width);m=(a<128).astype(np.float32);ys,xs=np.nonzero(m);box=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)];t=m[box[1]:box[3],box[0]:box[2]]
 _,intersection,_,loc=cv2.minMaxLoc(cv2.matchTemplate(source,t,cv2.TM_CCORR));union=float(source.sum()+t.sum()-intersection);origin=[(x0+loc[0]+3*scale-box[0])/scale,offset_y+(y0+loc[1]+26*scale-box[1])/scale]
 rows.append(dict(source_fixed_point_size=size,pdf_line_width_pt=round(float(line_width),3),render_mode=2 if line_width else 0,iou=intersection/union,source_original_font_origin_point=origin))
doc.close();rows.sort(key=lambda r:-r['iou']);q=dict(source_sha256='b7c3ff8e024d4805306b7cd7e11bb22dd487ff1ee1aa6a504f096a1676296957',scope='Actual PDF Tr0/Tr2 raster versus original scan; point size and advance fixed. Only source SimSun weight calibrated; Hangul needs separate real-stem comparison.',source_font='SimSun',source_crop_pixels=[x0,y0,x1,y1],rows=rows)
(B/'body-actual-stroke-calibration.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),'utf8');print(json.dumps(rows[:5],ensure_ascii=False))

from pathlib import Path
import json,hashlib
import pymupdf as fitz,numpy as np,cv2
from PIL import Image
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2020-complete-solutions');C=B/'figure-language';out=C/'source-label-measurements';out.mkdir(parents=True,exist_ok=True);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=B/'2020/inspection/page01-source-figures-2x.png';original=np.asarray(Image.open(source).convert('L'));_,cc,stats,_=cv2.connectedComponentsWithStats((original<160).astype('uint8'),8)
fields=[dict(id='sun-left',text='Sun',ko='태양',rect=[46,205,90,229],align='center'),dict(id='earth-left',text='Earth',ko='지구',rect=[286,176,344,201],align='center'),dict(id='fig1',text='Fig.',ko='그림',rect=[285,244,324,273],align='right'),dict(id='earth-right',text='Earth',ko='지구',rect=[718,170,770,191],align='center'),dict(id='to-sun',text='to the Sun',ko='태양 방향',rect=[448,267,551,287],align='left'),dict(id='fig2',text='Fig.',ko='그림',rect=[898,260,933,285],align='right')]
for field in fields:
 r=field['rect'];mask=(original[r[1]:r[3],r[0]:r[2]]<160).astype('float32');components=[]
 for i in sorted(set(map(int,np.unique(cc[r[1]:r[3],r[0]:r[2]])))-{0}):
  x,y,w,h,n=map(int,stats[i]);assert x>=r[0]and y>=r[1]and x+w<=r[2]and y+h<=r[3],(field['id'],i,[x,y,w,h]);components.append(dict(id=i,rect=[x,y,x+w,y+h],pixels=n))
 results=[]
 for face,file in [('Arial','arial.ttf'),('Calibri','calibri.ttf'),('Verdana','verdana.ttf'),('Tahoma','tahoma.ttf'),('TimesNewRoman','times.ttf')]:
  font=Path('C:/Windows/Fonts')/file
  if not font.exists():continue
  with fitz.open()as doc:
   page=doc.new_page(width=105,height=40);page.insert_font(fontname='SourceMeasure',fontfile=str(font))
   for size in np.arange(8.,14.001,.025):
    xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,b'');page.set_contents(xref);page.insert_text((2,28),field['text'],fontname='SourceMeasure',fontsize=float(size))
    pix=page.get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csGRAY);a=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width);m0=(a<128).astype('uint8')
    for spread in [0,1]:
     m=cv2.dilate(m0,np.ones((1+spread*2,1+spread*2),np.uint8));yy,xx=np.nonzero(m)
     if not len(xx):continue
     box=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)];t=m[box[1]:box[3],box[0]:box[2]].astype('float32')
     if t.shape[0]>mask.shape[0]or t.shape[1]>mask.shape[1]:continue
     _,inter,_,loc=cv2.minMaxLoc(cv2.matchTemplate(mask,t,cv2.TM_CCORR));union=float(mask.sum()+t.sum()-inter)
     results.append(dict(face=face,font_file=str(font),font_sha256=sha(font),size=round(float(size),3),pixel_spread=spread,iou=inter/union,origin=[(126+r[0]+loc[0]+4-box[0])/2,(708+r[1]+loc[1]+56-box[1])/2],location=loc,template_bbox=box))
 results.sort(key=lambda x:-x['iou']);assert results
 q=dict(source=str(B/'2020/source/IZhO_2020_TS.pdf'),source_sha256=sha(B/'2020/source/IZhO_2020_TS.pdf'),page=1,source_word=field['text'],source_page_crop=str(source),source_page_crop_sha256=sha(source),rect=r,scale=2.,source_crop_device_origin=[126,708],source_only=True,source_text_only_no_translated_box_fit=True,metadata_available=False,complete_isolated_source_word_components=components,method='Fit only unchanged original English raster glyphs against unscaled original font candidates; no Korean target string or target-box width participates.',top20=results[:20],best_by_face={face:next(v for v in results if v['face']==face)for face in {v['face']for v in results}})
 (out/(field['id']+'.json')).write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print(field['id'],[(v['face'],v['size'],round(v['iou'],5))for v in results[:3]],flush=True)
(C/'figure-fields.json').write_text(json.dumps(fields,ensure_ascii=False,indent=2)+'\n','utf8')

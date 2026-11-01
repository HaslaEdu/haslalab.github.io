from pathlib import Path
import sys,json,hashlib
import pymupdf as fitz,numpy as np,cv2
from PIL import Image
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
image=B/'2010/inspection/source-p04-figure.png';rect=[5,436,50,457];scale=2.
original=np.asarray(Image.open(image).convert('L'));source=(original[rect[1]:rect[3],rect[0]:rect[2]]<160).astype('float32')
_,cc,stats,_=cv2.connectedComponentsWithStats((original<160).astype('uint8'),8)
ids=set(map(int,np.unique(cc[rect[1]:rect[3],rect[0]:rect[2]])))-{0}
components=[]
for ident in ids:
 x,y,w,h,n=map(int,stats[ident]);assert x>=rect[0]and y>=rect[1]and x+w<=rect[2]and y+h<=rect[3];components.append(dict(id=ident,rect=[x,y,x+w,y+h],pixels=n))
results=[]
for name,file in [('TimesNewRoman-Bold','timesbd.ttf'),('TimesNewRoman','times.ttf'),('Arial-Bold','arialbd.ttf'),('Cambria-Bold','cambriab.ttf')]:
 font=Path('C:/Windows/Fonts')/file
 if not font.is_file():continue
 with fitz.open()as doc:
  page=doc.new_page(width=90,height=35);page.insert_font(fontname='SourceMeasure',fontfile=str(font))
  for size in np.arange(8.,14.001,.025):
   xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,b'');page.set_contents(xref)
   page.insert_text((2,25),'Рис.',fontname='SourceMeasure',fontsize=float(size))
   pix=page.get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csGRAY);grey=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width);mask=(grey<128).astype('uint8')
   for spread in [0,1]:
    m=cv2.dilate(mask,np.ones((1+2*spread,1+2*spread),np.uint8));yy,xx=np.nonzero(m)
    if not len(xx):continue
    box=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1];template=m[box[1]:box[3],box[0]:box[2]].astype('float32')
    if template.shape[0]>source.shape[0]or template.shape[1]>source.shape[1]:continue
    _,inter,_,loc=cv2.minMaxLoc(cv2.matchTemplate(source,template,cv2.TM_CCORR));union=float(source.sum()+template.sum()-inter)
    origin=[(611+rect[0]+loc[0]+4-box[0])/2,(382+rect[1]+loc[1]+50-box[1])/2]
    results.append(dict(face=name,font_file=str(font),font_sha256=sha(font),size=round(float(size),3),pixel_spread=spread,iou=inter/union,origin=origin,location=loc,template_bbox=box))
results.sort(key=lambda r:-r['iou']);assert results
out=B/'2010/source-caption-measurement.json';q=dict(source=str(B/'2010/source/IZhO_2010_TS_RU.pdf'),source_sha256=sha(B/'2010/source/IZhO_2010_TS_RU.pdf'),page=4,source_word='Рис.',source_page_crop=str(image),source_page_crop_sha256=sha(image),rect=rect,scale=2.,source_crop_device_origin=[611,382],source_only=True,source_text_only_no_translated_box_fit=True,metadata_available=False,complete_isolated_source_word_components=components,method='Compare unchanged source Russian caption with unscaled candidate original-font raster points; no translated word or target-box fit participates.',top20=results[:20],best_by_face={name:next(r for r in results if r['face']==name)for name in set(r['face']for r in results)});out.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(q['top20'][:3],ensure_ascii=False))

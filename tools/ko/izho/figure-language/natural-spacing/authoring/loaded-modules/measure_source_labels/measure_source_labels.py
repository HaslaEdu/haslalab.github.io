"""Source-only Latin bitmap label font/point/baseline measurement."""
from pathlib import Path
import sys,json,hashlib,time
import pymupdf as fitz,numpy as np,cv2
from PIL import Image
sys.path.insert(0,'D:/CodexBuilds/Hasla-publish-20261031/tools')
from pdf_memory_gate import page_worker
B=Path(__file__).resolve().parents[1]
FIELDS=[
 dict(id='light-source',page=2,image=3,text='light source',ko='광원',rect=[194,20,296,43],role='serif',align='center'),
 dict(id='plate',page=2,image=3,text='plate',ko='평판',rect=[262,122,315,150],role='serif',align='left'),
 dict(id='floor',page=2,image=3,text='floor',ko='바닥',rect=[285,249,334,278],role='serif',align='center'),
 dict(id='fig1',page=2,image=3,text='Fig.',ko='그림',rect=[282,363,322,392],role='serif',align='right'),
 dict(id='fig2',page=2,image=4,text='Fig.',ko='그림',rect=[440,399,484,431],role='serif',align='right'),
 dict(id='coil',page=3,image=1,text='Coil',ko='코일',rect=[149,8,198,35],role='sans-bold-italic',align='center'),
 dict(id='galvanometer',page=3,image=1,text='Galvanometer',ko='검류계',rect=[220,202,375,227],role='sans-bold-italic',align='center'),
]
FONTS={'serif':[('TimesNewRoman',Path('C:/Windows/Fonts/times.ttf')),('Cambria',Path('C:/Windows/Fonts/cambria.ttc'))],
 'sans-bold-italic':[(name,Path('C:/Windows/Fonts')/file)for name,file in [('Arial-BoldItalic','arialbi.ttf'),('Verdana-BoldItalic','verdanaz.ttf'),('Calibri-BoldItalic','calibriz.ttf'),('Arial-Bold','arialbd.ttf')]]}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def measure(field):
 inv=json.loads((B/'source-inventory.json').read_text('utf8'))
 meta=next(r for r in inv if r['year']==2010 and r['page']==field['page']and r['image_index']==field['image'])
 path=Path(meta['path']);original=np.asarray(Image.open(path).convert('L'));x0,y0,x1,y1=field['rect']
 source=(original[y0:y1,x0:x1]<160).astype('float32');results=[]
 # Inspection crops are original page renders at2x; their top-left origin is
 # the floor of the source clip's device coordinate, not its bitmap CTM width.
 scale=2.;origin_px=[int(np.floor(v*scale))for v in meta['image']['bbox'][:2]]
 for name,path_font in FONTS[field['role']]:
  if not path_font.is_file():continue
  with fitz.open()as doc:
   page=doc.new_page(width=150,height=35);page.insert_font(fontname='SourceMeasure',fontfile=str(path_font))
   for size in np.arange(7.,14.001,.05):
    xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,b'');page.set_contents(xref)
    page.insert_text((2,25),field['text'],fontname='SourceMeasure',fontsize=float(size))
    pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY)
    grey=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width);mask=(grey<128).astype('uint8')
    for spread in [0,1]:
     m=cv2.dilate(mask,np.ones((1+2*spread,1+2*spread),np.uint8));yy,xx=np.nonzero(m)
     if not len(xx):continue
     box=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1];template=m[box[1]:box[3],box[0]:box[2]].astype('float32')
     if template.shape[0]>source.shape[0]or template.shape[1]>source.shape[1]:continue
     _,inter,_,location=cv2.minMaxLoc(cv2.matchTemplate(source,template,cv2.TM_CCORR));union=float(source.sum()+template.sum()-inter)
     origin=[(origin_px[0]+x0+location[0]+2*scale-box[0])/scale,(origin_px[1]+y0+location[1]+25*scale-box[1])/scale]
     results.append(dict(face=name,font_file=str(path_font),font_sha256=sha(path_font),size=round(float(size),3),pixel_spread=spread,iou=inter/union,origin=origin,location=location,template_bbox=box))
 results.sort(key=lambda r:-r['iou']);assert results
 return dict(field=field,source_page_crop=meta,source_page_crop_sha256=sha(path),scale=scale,source_crop_device_origin=origin_px,metadata_available=False,source_text_only_no_translated_box_fit=True,method='Source English word raster at unscaled candidate font points; choose by dark-ink IoU. Target Korean wording never participates.',top20=results[:20],best_by_face={name:next(r for r in results if r['face']==name)for name,_ in FONTS[field['role']]if any(r['face']==name for r in results)})
if __name__=='__main__':
 out=B/'source-label-measurements';out.mkdir(exist_ok=True)
 for field in FIELDS:
  if len(sys.argv)>1 and field['id']not in sys.argv[1:]:continue
  with page_worker():q=measure(field)
  (out/(field['id']+'.json')).write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print(field['id'],q['top20'][0],flush=True);time.sleep(.6)

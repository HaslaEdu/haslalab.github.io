from pathlib import Path
import json,hashlib
import pymupdf as f,numpy as np,cv2
from PIL import Image
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original');O=B/'2018/inspection';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
a=np.asarray(Image.open(O/'page06-refraction-labels-original.png').convert('L'))
scale=542/177.4499969482422
fields=[dict(source_label='Bottom',text='바닥',rect=[53,324,157,349]),dict(source_label='Detector',text='검출기',rect=[362,342,483,369])]
for field in fields:
 r=field['rect'];mask=(a[r[1]:r[3],r[0]:r[2]]<160).astype('float32');results=[]
 for face,file in [('Arial-Bold','arialbd.ttf'),('Arial','arial.ttf'),('Tahoma-Bold','tahomabd.ttf'),('Times-Bold','timesbd.ttf'),('Arial-Black','ariblk.ttf'),('Calibri-Bold','calibrib.ttf'),('Verdana-Bold','verdanab.ttf'),('SegoeUI-Bold','segoeuib.ttf')]:
  path=Path('C:/Windows/Fonts')/file
  if not path.exists():continue
  with f.open()as d:
   p=d.new_page(width=100,height=35);p.insert_font(fontname='Measure',fontfile=str(path))
   for size in np.arange(8.,11.001,.025):
    x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,b'');p.set_contents(x)
    p.insert_text((2,25),field['source_label'],fontname='Measure',fontsize=float(size))
    pix=p.get_pixmap(matrix=f.Matrix(scale,scale),colorspace=f.csGRAY);m=(np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)<160).astype('uint8');yy,xx=np.nonzero(m)
    box=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)];t=m[box[1]:box[3],box[0]:box[2]].astype('float32')
    if t.shape[0]>mask.shape[0]or t.shape[1]>mask.shape[1]:continue
    _,inter,_,loc=cv2.minMaxLoc(cv2.matchTemplate(mask,t,cv2.TM_CCORR));union=float(mask.sum()+t.sum()-inter)
    baseline=155.+(r[1]+loc[1]+25*scale-box[1])/scale
    results.append(dict(face=face,font_file=str(path),font_sha256=sha(path),size=round(float(size),3),iou=inter/union,baseline=baseline,template_bbox=box,location=loc))
 results.sort(key=lambda x:-x['iou']);q=dict(field,source_sha256=sha(B/'2018/source/IZhO_2018_T.pdf'),image_sha256=sha(O/'page06-refraction-labels-original.png'),source_only=True,target_translation_used_for_fitting=False,method='Fit original unchanged English bitmap words to actual unscaled source-font candidates at the original image pixel-per-point ratio; Korean text is not used for measurement.',scale=scale,top20=results[:20],best_by_face={face:next(v for v in results if v['face']==face)for face in {v['face']for v in results}})
 (O/f"page06-label-{field['source_label'].lower()}-measurement.json").write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print(field['source_label'],[(x['face'],x['size'],round(x['iou'],5),round(x['baseline'],5))for x in results[:4]],flush=True)

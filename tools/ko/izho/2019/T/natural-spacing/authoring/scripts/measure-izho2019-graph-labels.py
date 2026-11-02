from pathlib import Path
import json,hashlib,os
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
import pymupdf as f,numpy as np,cv2
from PIL import Image
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2019-theory-original');O=B/'2019/inspection';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=B/'2019/source/IZhO_2019_T.pdf';image=O/'page02-raw-graph.png';a=np.asarray(Image.open(image).convert('L'))
with f.open(source)as doc:box=f.Rect(doc[1].get_image_info()[0]['bbox'])
scale=a.shape[1]/box.width
fields=[dict(id='title',source_label='Body temperature as a function of time',text='시간에 따른 물체의 온도',rect=[285,25,861,70],rotation=0),dict(id='time',source_label='Time, min',text='시간, 분',rect=[500,589,660,634],rotation=0),dict(id='temperature',source_label='Temperature, degree Celcius',text='온도, 섭씨',rect=[15,128,57,508],rotation=90)]
fonts=[('Arial-Bold','arialbd.ttf'),('Arial','arial.ttf'),('Tahoma-Bold','tahomabd.ttf'),('Calibri-Bold','calibrib.ttf'),('Verdana-Bold','verdanab.ttf'),('SegoeUI-Bold','segoeuib.ttf')]
for field in fields:
 r=field['rect'];crop=a[r[1]:r[3],r[0]:r[2]]
 if field['rotation']:crop=np.rot90(crop,k=3)
 mask=(crop<160).astype('float32');results=[]
 for face,file in fonts:
  path=Path('C:/Windows/Fonts')/file
  if not path.exists():continue
  with f.open()as d:
   p=d.new_page(width=420,height=40);p.insert_font(fontname='Measure',fontfile=str(path))
   for size in np.arange(10.,18.001,.025):
    x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,b'');p.set_contents(x)
    p.insert_text((2,30),field['source_label'],fontname='Measure',fontsize=float(size))
    pix=p.get_pixmap(matrix=f.Matrix(scale,scale),colorspace=f.csGRAY);m=(np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)<160).astype('uint8');yy,xx=np.nonzero(m)
    bb=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)];t=m[bb[1]:bb[3],bb[0]:bb[2]].astype('float32')
    if t.shape[0]>mask.shape[0]or t.shape[1]>mask.shape[1]:continue
    _,inter,_,loc=cv2.minMaxLoc(cv2.matchTemplate(mask,t,cv2.TM_CCORR));union=float(mask.sum()+t.sum()-inter)
    # Crop rotated clockwise is the source writing frame for vertical text.
    base_px=loc[1]+30*scale-bb[1]
    baseline=(box.y0+(r[1]+base_px)/scale)if not field['rotation']else(box.x0+(r[0]+base_px)/scale)
    results.append(dict(face=face,font_file=str(path),font_sha256=sha(path),size=round(float(size),3),iou=inter/union,baseline_coordinate_pt=baseline,baseline_coordinate_axis='x'if field['rotation']else'y',template_bbox=bb,location=loc))
 results.sort(key=lambda x:-x['iou']);assert results
 q=dict(field,source_sha256=sha(source),image_sha256=sha(image),source_only=True,target_translation_used_for_fitting=False,method='Original English raster vs unchanged candidate font outlines at the original pixel-to-point ratio; vertical crop rotated only for source measurement. Target translation never participates.',scale=scale,image_bbox=list(box),top20=results[:20],best_by_face={face:next(v for v in results if v['face']==face)for face in {v['face']for v in results}})
 (O/f"page02-label-{field['id']}-measurement.json").write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print(field['id'],[(v['face'],v['size'],round(v['iou'],5),round(v['baseline_coordinate_pt'],5))for v in results[:4]],flush=True)

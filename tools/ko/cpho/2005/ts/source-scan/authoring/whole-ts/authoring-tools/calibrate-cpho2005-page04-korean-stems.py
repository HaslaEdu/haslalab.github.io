from pathlib import Path
import sys,json,hashlib
import cv2,numpy as np,pymupdf as f
from PIL import Image,ImageDraw
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from cpho_2005_ts_compose import font_path,new_font,write_words
from cpho_2013_ts_korean_stems import stems
cv2.setNumThreads(1)
fields=[('heading','참고 해설',[98.3,60.1,149.9,76.5],12.125,'SimHei'),('left-top','판의 두께와 빛의 속력을',[128,98,180,114],12.3,'SimSun'),('left-bottom','판의 두께와 빛의 속력을',[66,276,143,294],12.425,'SimSun'),('right-top','판의 두께와 빛의 속력을',[441,102,492,119],12.475,'SimSun'),('right-middle','판의 두께와 빛의 속력을',[500.8,233,538.5,250],12.175,'SimSun')]
results=[];samples=[]
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as doc:
 for name,text,rect,size,face in fields:
  p=doc[3].get_pixmap(matrix=f.Matrix(8,8),clip=f.Rect(rect),colorspace=f.csGRAY,alpha=False)
  source=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width).copy();source_metrics=stems(source,size)
  raw,metric,fontqa=new_font(font_path('ko',face),text);candidates=[];pictures={}
  with f.open()as d:
   page=d.new_page(width=165,height=26);page.insert_font(fontname='KoreanSourceRole',fontbuffer=raw)
   for stroke in np.arange(0,.801,.025):
    xref=d.get_new_xref();d.update_object(xref,'<<>>');d.update_stream(xref,b'');page.set_contents(xref)
    write_words(page,2,18,text,metric,size,'KoreanSourceRole',2 if stroke else 0,float(stroke))
    pic=page.get_pixmap(matrix=f.Matrix(8,8),colorspace=f.csGRAY,alpha=False)
    gray=np.frombuffer(pic.samples,np.uint8).reshape(pic.height,pic.width).copy();measure=stems(gray,size)
    error=sum(abs(measure[a]['median_pt']-source_metrics[a]['median_pt'])for a in ['vertical','horizontal'])
    contrast=abs(measure['vertical']['median_pt']/measure['horizontal']['median_pt']-source_metrics['vertical']['median_pt']/source_metrics['horizontal']['median_pt'])
    candidates.append(dict(stroke_points=round(float(stroke),3),error_pt=error,contrast_error=contrast,metrics=measure));pictures[round(float(stroke),3)]=gray
  candidates.sort(key=lambda r:(r['error_pt'],r['contrast_error'],r['stroke_points']))
  best=candidates[0];results.append(dict(field=name,source_rect=rect,source_point_size=size,source_metrics=source_metrics,font=fontqa,best=best,results=candidates))
  samples.extend([(name+' original printed CJK',source),(name+f' Korean {size:g}pt calibrated stroke {best["stroke_points"]:g}pt',pictures[best['stroke_points']])])
  print(name,'source V/H',*[source_metrics[a]['median_pt']for a in ['vertical','horizontal']],'best',best['stroke_points'],'Korean V/H',*[best['metrics'][a]['median_pt']for a in ['vertical','horizontal']],flush=True)
width=max(a.shape[1]for _,a in samples);height=sum(a.shape[0]+22 for _,a in samples);image=Image.new('RGB',(width,height),'white');draw=ImageDraw.Draw(image);y=0
for label,gray in samples:draw.text((2,y+2),label,fill='black');image.paste(Image.fromarray(gray),(0,y+21));y+=gray.shape[0]+22
image.save(B/'source-renders/page04-source-vs-korean-stems.png')
(B/'page04-korean-stem-calibration.json').write_text(json.dumps(dict(source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',scope='Source physical vertical and horizontal primary stem medians and contrast at fixed independently measured source point sizes. Select least-stroke candidate if medians/contrast tie; no width fitting or whole-ink-density matching.',fields=results),ensure_ascii=False,indent=2)+'\n','utf8')

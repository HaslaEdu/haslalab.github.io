from pathlib import Path
import json,sys,os
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
import pymupdf as f
with page_worker():
 with f.open(B/'2018/source/IZhO_2018_TS.pdf')as d:
  p=d[9];info=p.get_image_info(xrefs=True);actual=info[2];assert actual['width']==743 and actual['height']==464
  f.Pixmap(d,actual['xref']).save(B/'2018/inspection/page10-original-star-bitmap.png')
  for v in info:v['digest']=v['digest'].hex()
  (B/'2018/inspection/page10-original-star-bitmap-info.json').write_text(json.dumps(dict(images=info,get_images_full=p.get_images(full=True)),indent=2),'utf8')
print('ORIGINAL_STELLAR_DIAGRAM_EXTRACTED_READ_ONLY',flush=True)

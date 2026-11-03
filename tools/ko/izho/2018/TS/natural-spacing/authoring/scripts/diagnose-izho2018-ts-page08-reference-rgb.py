from pathlib import Path
import sys,os,json,hashlib
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
import pymupdf as f,numpy as np
O=B/'natural/2018-page08-original-native-word-program';ref=O/'exact-original-native-CIDs-clips-rules-paint-only.pdf';proof=B/'natural/2018/TS/page08.pdf';R=f.Rect(130,472,302,499);rows=[]
with page_worker():
 for scale in[4,8,12]:
  arrays=[]
  for name,path in[('reference',ref),('proof',proof)]:
   with f.open(path)as doc:p=doc[0].get_pixmap(matrix=f.Matrix(scale,scale),clip=R,colorspace=f.csRGB,alpha=False);arrays.append(np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy());p.save(O/f'diagnostic-RGB-{name}-{scale}.png')
  a,b=arrays;yy,xx=np.nonzero((a.min(2)<255)&np.any(a!=b,2));items=[dict(point=[130+int(x)/scale,472+int(y)/scale],reference=a[y,x].tolist(),actual=b[y,x].tolist())for y,x in zip(yy,xx)];rows.append(dict(scale=scale,changed=len(items),pixels=items))
  print(scale,items,flush=True)
 (O/'diagnostic-reference-RGB-context-differences.json').write_text(json.dumps(rows,indent=2)+'\n','utf8')

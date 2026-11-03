from pathlib import Path
import sys,json,os,hashlib
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
import pymupdf as f,numpy as np
source=B/'2018/source/IZhO_2018_TS.pdf';rows=[]
for n in range(1,16):
 with page_worker():
  with f.open(source)as doc:
   spaces=[dict(font=t['font'],point=t['size'],GID=gid,origin=list(origin),bbox=list(box))for t in doc[n-1].get_texttrace()for cp,gid,origin,box in t['chars']if chr(cp).isspace()and 'Math'in t['font']and gid not in[0,3]];rows.append(dict(page=n,nonstandard_math_whitespace_glyphs=spaces))
   if n==15:
    measures=[]
    for scale in[4,8,12]:
     r=f.Rect(117.85,106.2,322.67,107.0);p=doc[14].get_pixmap(matrix=f.Matrix(scale,scale),clip=r,colorspace=f.csRGB,alpha=False);a=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3);measures.append(dict(scale=scale,rect=list(r),nonwhite_pixels=int(np.any(a!=255,2).sum())))
    (B/'2018/inspection/page15-original-adjacent-Form-layout-padding.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_page=15,measures=measures),indent=2)+'\n','utf8')
out=B/'2018/inspection/all15-original-native-math-painted-space-inventory.json';out.write_text(json.dumps(rows,indent=2)+'\n','utf8');print('SOURCE_NATIVE_NONSTANDARD_SPACE_INVENTORY',[(r['page'],len(r['nonstandard_math_whitespace_glyphs']))for r in rows],flush=True);print('SOURCE_ADJACENT_FORM_BOUNDARY_PIXEL_DIAGNOSTIC',measures,flush=True)

from pathlib import Path
import sys,json,pymupdf as f,os
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups
for n in map(int,sys.argv[1:]):
 out=B/f'2018/inspection/page{n:02}-original-native-inline-inventory.json'
 if out.exists():continue
 with page_worker():
  inv=inspect_inline_groups(B/'2018/source/IZhO_2018_TS.pdf',n);out.write_text(json.dumps(inv,ensure_ascii=False)+'\n','utf8')
  with f.open(B/'2018/source/IZhO_2018_TS.pdf')as doc:figs=[i['bbox']for i in doc[n-1].get_image_info()if f.Rect(i['bbox']).width>30 and f.Rect(i['bbox']).height>25]
 print('SOURCE2018_NATIVE_PROGRAM_INVENTORY',n,'Forms',len(inv['forms']),'vectors',len(inv['vector_paths']),'figures',figs,flush=True)

from pathlib import Path
import json,sys,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2015-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups
source=B/'2015/source/IZhO_2015_TS.pdf'
for n in map(int,sys.argv[1:]):
 with page_worker():
  inv=inspect_inline_groups(source,n);out=B/f'2015/inspection/page{n:02}-original-native-inline-inventory.json';out.write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n','utf8')
  print('SOURCE2015_NATIVE_STRUCTURES',n,'forms',len(inv['forms']),'clips',len(inv['clip_groups']),'vectors',len(inv['vector_paths']),flush=True)

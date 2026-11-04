from pathlib import Path
import sys,hashlib,json
B=Path(__file__).resolve().parents[1];E=B/'engine';E.mkdir(exist_ok=True);A=B/'authoring';A.mkdir(exist_ok=True)
R=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2004-original-style-bilingual/engine')
names=['pdf_native_inline_reposition.py','pdf_original_text_ops.py','pdf_original_style_audit.py','pdf_original_raster_math.py','pdf_scanned_translation_ink_qa.py','pdf_new_prose_outlines.py']
records=[]
for name in names:
 p=R/name;q=E/name
 if not q.exists():q.write_bytes(p.read_bytes())
 records.append(dict(name=name,read_only_parent=str(p),sha256=hashlib.sha256(q.read_bytes()).hexdigest()))
assert records[0]['sha256']=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
(E/'private-native-engine-provenance.json').write_text(json.dumps(records,indent=2)+'\n','utf8')
sys.path[:0]=[str(E),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups,_traces
import pymupdf as f
S=B/'source/CPhO_2008_original_combined_ZH.pdf'
for n in range(1,22):
 out=B/f'inspection/page{n:02}-original-native-programs.json'
 if out.exists():continue
 with page_worker():
  inv=inspect_inline_groups(S,n,include_text_shows=True)
  with f.open(S)as d:inv['actual_original_glyphs']=_traces(d[n-1])
  out.write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n','utf8');print('ORIGINAL_NATIVE_PROGRAMS',n,'forms',len(inv['forms']),'paths',len(inv['vector_paths']),'glyphs',len(inv['actual_original_glyphs']),flush=True)

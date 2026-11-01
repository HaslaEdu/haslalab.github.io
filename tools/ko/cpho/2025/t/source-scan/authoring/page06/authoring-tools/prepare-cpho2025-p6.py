from pathlib import Path
import os,sys,json,shutil
os.environ['PYTHONDONTWRITEBYTECODE']='1'
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025')
P=B/'p6-authoring';(P/'tools').mkdir(parents=True,exist_ok=True);(P/'plans').mkdir(exist_ok=True)
for name in ['compose_pages.py','qa_pages.py']:
 shutil.copy2(B/'p2-6-authoring/tools'/name,P/'tools'/name)
sys.path.insert(0,'D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools')
sys.path.insert(0,'C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab/tools')
import pymupdf as fitz
from pdf_memory_gate import page_worker
with page_worker(),fitz.open(B/'CPhO_2025_T_original-explicit-page-clip.pdf') as doc:
 doc[5].get_pixmap(matrix=fitz.Matrix(2,2),alpha=False).save(P/'source-p6.png')
h=json.loads((B/'page6-ocr-hints.json').read_text('utf8'))
print(json.dumps([dict(id=x['id'],text=x['text'],polygon=x['polygon'])for x in h['rows']],ensure_ascii=False,indent=2))

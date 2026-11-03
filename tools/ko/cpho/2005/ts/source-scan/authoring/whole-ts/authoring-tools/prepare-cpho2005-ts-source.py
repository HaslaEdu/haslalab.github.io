from pathlib import Path
import json,shutil,hashlib,sys
D=Path('D:/CodexBuilds/Hasla-original-style-20261031');B=D/'cpho2005/TS';C=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab');PUB=Path('D:/CodexBuilds/Hasla-publish-20261031');B.mkdir(parents=True,exist_ok=True)
for sub in ['inputs','row-hints','tools','authoring','source-renders']:(B/sub).mkdir(exist_ok=True)
source=D/'cpho-early-natural/final-v1/source-originals/CPhO_2005_Chinese_original.pdf';assert hashlib.sha256(source.read_bytes()).hexdigest()=='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f'
shutil.copy2(source,B/'inputs'/source.name);slots=json.loads((PUB/'tools/ko/cpho/2005/original/native-slots.json').read_text('utf8'));shutil.copy2(PUB/'tools/ko/cpho/2005/original/native-slots.json',B/'inputs/native-slots.json')
readable=[]
for page in range(4,17):
 p=C/f'tools/ko/cpho/2005/original/ocr-page{page:02}-draft.json';q=json.loads(p.read_text('utf8'));assert q['source_sha256']==slots['source_sha256'];shutil.copy2(p,B/f'row-hints/ocr-page{page:02}-draft.json')
 readable.append('PAGE '+str(page))
 for i,line in enumerate(q['lines']):
  x0=min(p[0]for p in line['polygon'])/q['scale'];x1=max(p[0]for p in line['polygon'])/q['scale'];y0=min(p[1]for p in line['polygon'])/q['scale'];y1=max(p[1]for p in line['polygon'])/q['scale']
  readable.append(f'{page}-{i}\t{[x0,y0,x1,y1]}\t{line["text"]}')
(B/'row-hints/source-language-location-hints.txt').write_text('\n'.join(readable)+'\n','utf8')
print(json.dumps([dict(page=p['source_page'],native_slots=[{k:s[k]for k in ['id','source','source_font','size','origin']}for s in p['slots']],images=p['images'])for p in slots['pages']if p['source_page']==4],ensure_ascii=False,indent=2))
sys.path[:0]=[str(PUB/'tools'),str(D/'cpho2013/TS/tools')]
import pymupdf as f
from pdf_memory_gate import page_worker
with page_worker(),f.open(source)as pdf:pdf[3].get_pixmap(matrix=f.Matrix(2,2),alpha=False).save(B/'source-renders/page04.png')

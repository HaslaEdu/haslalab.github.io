from pathlib import Path
import sys,json,hashlib,shutil,time
BASE=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS')
ROOT=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab')
sys.path[:0]=[str(BASE/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
import cpho_2013_ts_compose as compose
compose.ROOT=ROOT;compose.BASE=BASE;compose.SOURCE=ROOT/'tmp/original-style-sources/CPhO_2013_Chinese_original.pdf'
import cpho_2013_original_extract as original_source
original_source.ROOT=ROOT;original_source.SOURCE=compose.SOURCE
import cpho_2013_ts_qa as qa
import cpho_2013_ts_generic_qa_adapter as generic
from pdf_memory_gate import page_worker
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
backup=BASE/'root-paint-order-completion/preserved-drafts';backup.mkdir(parents=True,exist_ok=True)
jobs=[(4,'en'),(5,'ko'),(5,'en'),(6,'en')];saved=[]
if(backup/'inventory.json').exists():
    saved=json.loads((backup/'inventory.json').read_text('utf8'))
    for row in saved:assert sha(row['preserved'])==row['sha256'],'Preserved pre-root draft changed'
else:
    for number,lang in jobs:
        dest=backup/lang;dest.mkdir(exist_ok=True)
        for p in(BASE/'proofs'/lang).glob(f'page{number:02}*'):
            q=dest/p.name;shutil.copy2(p,q);saved.append(dict(path=str(p),preserved=str(q),sha256=sha(q)))
    (backup/'inventory.json').write_text(json.dumps(saved,indent=2)+'\n','utf8')
for number,lang in jobs:
    with page_worker():
        compose.build(number,lang);a=qa.audit(number,lang);b=generic.audit(number,lang)
        assert a['passed']and b['passed'],(number,lang)
    print(json.dumps(dict(source_page=number,language=lang,complete=True)),flush=True);time.sleep(.6)

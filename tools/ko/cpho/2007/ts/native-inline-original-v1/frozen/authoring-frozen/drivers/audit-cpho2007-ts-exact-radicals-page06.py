from pathlib import Path
import sys,hashlib,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS');sys.path.insert(0,str(B/'engine'));lang=sys.argv[1];assert lang in['ko','en']
path=B/f'natural/2007/{lang}/page06.audit.json'
if path.exists():
 h=B/'evidence/qa-history'/hashlib.sha256(path.read_bytes()).hexdigest()[:16];h.mkdir(parents=True,exist_ok=True)
 if not(h/path.name).exists():shutil.copy2(path,h/path.name)
from pdf_memory_gate import page_worker
from cpho2007_ts_runtime import audit_natural
with page_worker():audit_natural(6,lang)

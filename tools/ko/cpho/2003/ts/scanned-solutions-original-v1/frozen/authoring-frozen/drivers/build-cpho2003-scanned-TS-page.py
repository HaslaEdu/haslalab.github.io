"""Build one new, never overwritten, source-native C03 TS proof under global gate."""
from pathlib import Path
import sys,json,hashlib
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native')
T=B/'TS';sys.path[:0]=[str(T/'engine'),str(B/'engine'),'D:/CodexBuilds']
from pdf_memory_gate import page_worker
from cpho_2003_ts_compose import build
number=int(sys.argv[1]);lang=sys.argv[2]
assert number in range(4,11)and lang in ['ko','en']
with page_worker():out=build(number,lang)
rows=[]
for name,module in sorted(sys.modules.items()):
 p=getattr(module,'__file__',None)
 if p and Path(p).is_file()and any(Path(p).resolve().is_relative_to(root.resolve())for root in [T/'engine',B/'engine']):
  p=Path(p);rows.append(dict(module=name,path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
out.with_suffix('.build-loaded-modules.json').write_text(json.dumps(rows,indent=2)+'\n','utf8')

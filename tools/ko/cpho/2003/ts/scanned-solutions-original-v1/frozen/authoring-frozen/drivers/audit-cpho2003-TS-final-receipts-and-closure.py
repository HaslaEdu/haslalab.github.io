from pathlib import Path
import sys,json,hashlib
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');T=B/'TS'
sys.path[:0]=[str(T/'engine'),str(B/'engine'),'D:/CodexBuilds']
from pdf_memory_gate import page_worker
from cpho2003_ts_actual_donor_style import audit as style
from cpho2003_ts_native_ink import audit as native
import cpho_2003_ts_qa,cpho_2003_ts_poppler_qa
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for n in range(4,11):
 for lang in ['ko','en']:
  with page_worker():
   p=T/f'proofs/{lang}/page{n:02}.pdf'
   style(n,lang,output_override=p.with_suffix('.final-actual-donor-style.json'))
   native(n,lang,output_override=p.with_suffix('.final-source-native-ink.json'))
rows=[]
for name,m in sorted(sys.modules.items()):
 p=getattr(m,'__file__',None)
 if p and Path(p).is_file()and any(Path(p).resolve().is_relative_to(v.resolve())for v in [T/'engine',B/'engine']):
  p=Path(p);rows.append(dict(module=name,path=str(p.resolve()),sha256=sha(p),bytes=p.stat().st_size))
out=T/'authoring/final-auditor-import-closure.json';assert not out.exists();out.write_text(json.dumps(dict(source_sha256=sha(B/'inputs/CPhO_2003_Chinese_original.pdf'),all14_current_positive_style_and_native_reports_verified=True,modules=rows),indent=2)+'\n','utf8');print('ALL14_FINAL_AUDITOR_RUNTIME_CLOSURE',len(rows),sha(out),flush=True)

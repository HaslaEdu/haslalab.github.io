from pathlib import Path
import sys,json,time,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS');ROOT=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
import cpho_2013_ts_compose as compose
compose.BASE=B;compose.ROOT=ROOT;compose.SOURCE=ROOT/'tmp/original-style-sources/CPhO_2013_Chinese_original.pdf'
import cpho_2013_original_extract as original
original.ROOT=ROOT;original.SOURCE=compose.SOURCE
import cpho_2013_ts_qa as qa
import cpho_2013_ts_generic_qa_adapter as generic
from pdf_memory_gate import page_worker
import pymupdf as fitz,numpy as np
results=[]
for n in[12,13]:
 for lang in['ko','en']:
  try:
   with page_worker():
    target=compose.build(n,lang);a=qa.audit(n,lang);b=generic.audit(n,lang)
    plan=json.loads((B/f'authoring/page{n}-layout.json').read_text('utf8'));background=[]
    with fitz.open(compose.SOURCE)as source,fitz.open(target)as final:
     for record in plan.get('source_background_restore_atoms',[]):
      rect=fitz.Rect(record['rect']);x=source[n-1].get_pixmap(matrix=fitz.Matrix(4,4),clip=rect,alpha=False);y=final[0].get_pixmap(matrix=fitz.Matrix(4,4),clip=rect,alpha=False)
      changed=int(np.any(np.frombuffer(x.samples,np.uint8).reshape(-1,3)!=np.frombuffer(y.samples,np.uint8).reshape(-1,3),axis=1).sum());background.append(dict(rect=record['rect'],original_source_RGB_changed_pixels=changed,source_sha256=record['source_sha256'],final_sha256=hashlib.sha256(target.read_bytes()).hexdigest()));assert changed==0
    passed=a['passed']and b['passed'];report=dict(page=n,language=lang,passed=passed,original_background_RGB_replay=background)
    target.with_suffix('.background-replay-qa.json').write_text(json.dumps(report,indent=2)+'\n','utf8')
    results.append(report);print(json.dumps(report),flush=True)
  except Exception as error:
   results.append(dict(page=n,language=lang,passed=False,error=repr(error)));print(json.dumps(results[-1]),flush=True)
  time.sleep(.6)
(B/'root-paint-order-completion/final-page-results.json').write_text(json.dumps(results,indent=2)+'\n','utf8')
raise SystemExit(any(not r['passed']for r in results))

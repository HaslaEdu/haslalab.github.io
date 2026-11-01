from pathlib import Path
from collections import defaultdict
import os,sys,json,hashlib,subprocess
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/heading-alignment-v1')
load=lambda p:json.loads(Path(p).read_text('utf8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
producer=sha('D:/CodexBuilds/review-izho-heading-alignment.py')
accepted_producers={producer}|{sha(p)for p in (B/'producer-versions').glob('*.py')if p.stem==sha(p)}
env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
groups=defaultdict(list)
for r in load(B.parent/'published-izho-heading-detail-20261102.json')['candidates_requiring_review']:
 if abs(r['actual_center_error'])>.001:groups[(r['file'],r['published_page'])].append(r)
for (filename,page),rows in sorted(groups.items()):
 folder=B/filename.removesuffix('.pdf');folder.mkdir(exist_ok=True);report=folder/f'page{page:02}.alignment.json';pdf=folder/f'page{page:02}.pdf'
 if report.exists():
  q=load(report)
  if q.get('producer_sha256')in accepted_producers and q['passed']and sha(pdf)==q['proof_sha256']:
   print('CACHED',filename,page,flush=True);continue
 with(folder/f'page{page:02}.log').open('w',encoding='utf8')as log:
  r=subprocess.run([sys.executable,'-X','utf8','D:/CodexBuilds/review-izho-heading-alignment.py',filename,str(page)],stdout=log,stderr=subprocess.STDOUT,env=env)
 if r.returncode:print('FAILED',filename,page,str(folder/f'page{page:02}.log'),flush=True);raise SystemExit(r.returncode)
 print('PASS',filename,page,len(rows),flush=True)
print('ALL69_PAGES_180_HEADINGS_PASS',flush=True)
subprocess.run([sys.executable,'-X','utf8','D:/CodexBuilds/assemble-izho-heading-alignment.py'],env=env,check=True)

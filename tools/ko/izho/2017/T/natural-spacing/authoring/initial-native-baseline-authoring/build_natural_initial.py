from pathlib import Path
import subprocess,sys,time,json,os
B=Path(__file__).resolve().parent;year=int(sys.argv[1]);start=int(sys.argv[2])if len(sys.argv)>2 else 1;end=int(sys.argv[3])if len(sys.argv)>3 else {2012:6,2017:7}[year];status=[]
for i in range(start,end+1):
 code="""import sys,time
from pathlib import Path
B=Path(%r);sys.path[:0]=[str(B/'engine'),str(Path.cwd()/'tools'),str(B.parent/'izho-natural-spacing')]
from izho_natural_spacing_rebuild import page_build
from pdf_memory_gate import page_worker
from izho_natural_spacing_qa import audit
from modern_new_prose_collision_audit import audit_plan
plan=B/'natural/%d/T/plans'/('page%%02d.json'%%%d)
page_build(plan);time.sleep(.6)
with page_worker():a=audit(%d,'T',%d)
time.sleep(.6)
with page_worker():c=audit_plan(plan)
assert a['passed']and c['passed']
print('NATURAL_PAGE_COMPLETE',%d,flush=True)
"""%(str(B),year,i,year,i,i)
 log=B/f'natural/{year}/T/page{i:02}.build-audit.log'
 with log.open('w',encoding='utf8')as output:r=subprocess.run([sys.executable,'-u','-c',code],stdout=output,stderr=subprocess.STDOUT,env=dict(os.environ))
 status.append(dict(page=i,returncode=r.returncode));(B/f'natural/{year}/T/build-status.json').write_text(json.dumps(status,indent=2),encoding='utf8');print(year,i,r.returncode,flush=True)
 time.sleep(.6)

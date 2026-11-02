from pathlib import Path
import sys,time
B=Path(__file__).resolve().parent;sys.path[:0]=[str(B/'engine'),str(Path.cwd()/'tools'),str(B.parent/'izho-natural-spacing')]
from pdf_memory_gate import page_worker
from izho_natural_spacing_rebuild import page_build
from izho_natural_spacing_qa import audit
from modern_new_prose_collision_audit import audit_plan
y=int(sys.argv[1]);p=int(sys.argv[2]);plan=B/f'natural/{y}/T/plans/page{p:02}.json'
if '--build'in sys.argv:page_build(plan);time.sleep(.6)
with page_worker():a=audit(y,'T',p)
time.sleep(.6)
with page_worker():c=audit_plan(plan)
assert a['passed']and c['passed'];print('AUDIT_COMPLETE',y,p,flush=True)

from pathlib import Path
import sys,subprocess,os
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions')
n=int(sys.argv[1]);plan=B/f'natural/2010/TS/plans/page{n:02}.json'
env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
prefix=f"import sys;from pathlib import Path;sys.path[:0]=[{str(B/'engine')!r},'D:/CodexBuilds/Hasla-publish-20261031/tools'];from pdf_memory_gate import page_worker;"
jobs=[
 prefix+f"from izho_natural_spacing_rebuild import page_build;page_build(Path({str(plan)!r}))",
 prefix+f"from izho_natural_spacing_qa import audit\nwith page_worker():q=audit(2010,'TS',{n})\nassert q['passed']",
 prefix+f"from modern_new_prose_collision_audit import audit_plan\nwith page_worker():q=audit_plan(Path({str(plan)!r}))\nassert q['passed']",
]
for code in jobs:subprocess.run([sys.executable,'-u','-c',code],env=env,check=True)
if n==9:
 code=prefix+f"from reviewed_native_math_images import audit;q=audit(Path({str(plan)!r}));assert q['passed']"
 subprocess.run([sys.executable,'-u','-c',code],env=env,check=True)
code=prefix+f"from heading_source_alignment_audit import audit;q=audit(Path({str(plan)!r}));assert q['passed']"
subprocess.run([sys.executable,'-u','-c',code],env=env,check=True)
print('COMPLETE_SOURCE_NATIVE_TS_PAGE PASS',n,flush=True)

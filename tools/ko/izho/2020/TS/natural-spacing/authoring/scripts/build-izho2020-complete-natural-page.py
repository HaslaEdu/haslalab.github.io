from pathlib import Path
import sys,subprocess,os,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2020-complete-solutions');n=int(sys.argv[1]);plan=B/f'natural/2020/TS/plans/page{n:02}.json'
env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
prefix=f"import sys;from pathlib import Path;sys.path[:0]=[{str(B/'engine')!r},'D:/CodexBuilds/Hasla-publish-20261031/tools'];from pdf_memory_gate import page_worker;"
jobs=[prefix+f"from izho_natural_spacing_rebuild import page_build;page_build(Path({str(plan)!r}))",prefix+f"from izho_natural_spacing_qa import audit\nwith page_worker():q=audit(2020,'TS',{n})\nassert q['passed']",prefix+f"from modern_new_prose_collision_audit import audit_plan\nwith page_worker():q=audit_plan(Path({str(plan)!r}))\nassert q['passed']"]
for code in jobs:subprocess.run([sys.executable,'-u','-c',code],env=env,check=True)
code=prefix+f"from heading_source_alignment_audit import audit;q=audit(Path({str(plan)!r}));assert q['passed']"
subprocess.run([sys.executable,'-u','-c',code],env=env,check=True)
print('COMPLETE_SOURCE_NATIVE_2020_TS_PAGE PASS',n,flush=True)

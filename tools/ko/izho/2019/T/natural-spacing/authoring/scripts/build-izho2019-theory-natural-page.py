from pathlib import Path
import subprocess,sys,os
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2019-theory-original');n=int(sys.argv[1]);plan=B/f'natural/2019/T/plans/page{n:02}.json';env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1');prefix=f"import sys;from pathlib import Path;sys.path[:0]=[{str(B/'engine')!r},'D:/CodexBuilds/Hasla-publish-20261031/tools'];from pdf_memory_gate import page_worker;"
jobs=[prefix+f"from izho_natural_spacing_rebuild import page_build;page_build(Path({str(plan)!r}))",prefix+f"from izho_natural_spacing_qa import audit\nwith page_worker():q=audit(2019,'T',{n})\nassert q['passed']",prefix+f"from modern_new_prose_collision_audit import audit_plan\nwith page_worker():q=audit_plan(Path({str(plan)!r}))\nassert q['passed']",prefix+f"from heading_source_alignment_audit import audit;q=audit(Path({str(plan)!r}));assert q['passed']"]
audit_only='--audit-only'in sys.argv[2:];log=B/f'natural/2019/T/page{n:02}-build.log'
with log.open('a'if audit_only else'w',encoding='utf8')as out:
 for i,code in enumerate(jobs[1:]if audit_only else jobs,2 if audit_only else 1):
  r=subprocess.run([sys.executable,'-u','-c',code],env=env,stdout=out,stderr=subprocess.STDOUT)
  if r.returncode:print('NATIVE_2019_PAGE_FAILED',n,'stage',i,'log',log,flush=True);raise SystemExit(r.returncode)
  print('NATIVE_2019_PAGE_STAGE_PASS',n,i,flush=True)
print('NATIVE_2019_PAGE_ALL_CHECKS_PASS',n,flush=True)

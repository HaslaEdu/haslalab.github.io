from pathlib import Path
import subprocess,sys,os,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original');n=int(sys.argv[1]);plan=B/f'natural/2018/T/plans/page{n:02}.json'
env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
prefix=f"import sys;from pathlib import Path;sys.path[:0]=[{str(B/'engine')!r},'D:/CodexBuilds/Hasla-publish-20261031/tools'];from pdf_memory_gate import page_worker;"
jobs=[prefix+f"from izho_natural_spacing_rebuild import page_build;page_build(Path({str(plan)!r}))",prefix+f"from izho_natural_spacing_qa import audit\nwith page_worker():q=audit(2018,'T',{n})\nassert q['passed']",prefix+f"from modern_new_prose_collision_audit import audit_plan\nwith page_worker():q=audit_plan(Path({str(plan)!r}))\nassert q['passed']",prefix+f"from heading_source_alignment_audit import audit;q=audit(Path({str(plan)!r}));assert q['passed']"]
log=B/f'natural/2018/T/page{n:02}-build.log'
audit_only='--audit-only'in sys.argv[2:]
build_only='--build-only'in sys.argv[2:]
with log.open('a'if audit_only else'w',encoding='utf8')as out:
 for i,code in enumerate(jobs[:1]if build_only else jobs[1:]if audit_only else jobs,2 if audit_only else 1):
  p=subprocess.run([sys.executable,'-u','-c',code],env=env,stdout=out,stderr=subprocess.STDOUT)
  if p.returncode:
   print('NATIVE_NATURAL_2018_T_PAGE_FAILED',n,'stage',i,'log',log,flush=True);raise SystemExit(p.returncode)
  print('NATIVE_NATURAL_2018_T_PAGE_STAGE_PASS',n,i,flush=True)
print('2018_T_PRIVATE_BUILD_COMPLETE_AUDITS_PENDING'if build_only else'2018_T_PAGE_ALL_SOURCE_AND_FONT_COLLISION_HEADING_CHECKS_PASS',n,flush=True)

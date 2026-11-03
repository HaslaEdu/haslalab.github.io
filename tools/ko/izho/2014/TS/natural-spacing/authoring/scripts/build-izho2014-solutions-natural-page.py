from pathlib import Path
import sys,subprocess,os,contextlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2014-complete-solutions');n=int(sys.argv[1]);plan=B/f'natural/2014/TS/plans/page{n:02}.json';env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1');prefix=f"import sys;from pathlib import Path;sys.path[:0]=[{str(B/'engine')!r},'D:/CodexBuilds/Hasla-publish-20261031/tools'];from pdf_memory_gate import page_worker;"
jobs=[prefix+f"from izho_natural_spacing_rebuild import page_build;page_build(Path({str(plan)!r}))",prefix+f"from izho_natural_spacing_qa import audit\nwith page_worker():q=audit(2014,'TS',{n})\nassert q['passed']",prefix+f"from modern_new_prose_collision_audit import audit_plan\nwith page_worker():q=audit_plan(Path({str(plan)!r}))\nassert q['passed']",prefix+f"from heading_source_alignment_audit import audit;q=audit(Path({str(plan)!r}));assert q['passed']",prefix+f"from izho_2014_equation_counters import audit;q=audit(Path({str(plan)!r}));assert q['passed']",prefix+f"from final_translation_font_audit import audit;q=audit(Path({str(plan)!r}));assert q['passed']"]
log=B/f'natural/2014/TS/page{n:02}-build.log';prior=log.parent/f'page{n:02}.pdf'
if prior.exists():raise ValueError('Preserve and review existing2014 proof before choosing any rebuild')
existing=[p for p in log.parent.glob(f'page{n:02}*')if p.is_file()]
if existing:
 import hashlib,shutil
 version=hashlib.sha256(''.join(p.name+hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(existing)).encode()).hexdigest()[:16];history=log.parent/'history'/('failed-'+version);history.mkdir(parents=True,exist_ok=True)
 for p in existing:
  target=history/p.name
  if target.exists():assert target.read_bytes()==p.read_bytes()
  else:shutil.copy2(p,target)
with log.open('w',encoding='utf8')as out:
 for i,code in enumerate(jobs,1):
  r=subprocess.run([sys.executable,'-u','-X','utf8','-c',code],env=env,stdout=out,stderr=subprocess.STDOUT)
  if r.returncode:print('NATIVE_2014_TS_PAGE_FAILED',n,'stage',i,'log',log,flush=True);raise SystemExit(r.returncode)
  print('NATIVE_2014_TS_PAGE_STAGE_PASS',n,i,flush=True)
print('NATIVE_2014_TS_PAGE_ALL_INITIAL_CHECKS_PASS',n,flush=True)

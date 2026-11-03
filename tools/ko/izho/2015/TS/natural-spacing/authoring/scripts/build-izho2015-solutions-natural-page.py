from pathlib import Path
import sys,subprocess,os,json,hashlib,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2015-complete-solutions');n=int(sys.argv[1]);F=B/'natural/2015/TS';plan=F/f'plans/page{n:02}.json';env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1');prefix=f"import sys;from pathlib import Path;sys.path[:0]=[{str(B/'engine')!r},'D:/CodexBuilds/Hasla-publish-20261031/tools'];from pdf_memory_gate import page_worker;"
jobs=[prefix+f"from izho_natural_spacing_rebuild import page_build;page_build(Path({str(plan)!r}))",prefix+f"from izho_natural_spacing_qa import audit\nwith page_worker():q=audit(2015,'TS',{n})\nassert q['passed']",prefix+f"from modern_new_prose_collision_audit import audit_plan\nwith page_worker():q=audit_plan(Path({str(plan)!r}))\nassert q['passed']",prefix+f"from heading_source_alignment_audit import audit\nwith page_worker():q=audit(Path({str(plan)!r}))\nassert q['passed']",prefix+f"from izho_2015_equation_counters import audit\nwith page_worker():q=audit(Path({str(plan)!r}))\nassert q['passed']",prefix+f"from final_translation_font_audit import audit\nwith page_worker():q=audit(Path({str(plan)!r}))\nassert q['passed']",prefix+f"from izho_2015_independent_original_math_geometry import audit\nwith page_worker():q=audit(Path({str(plan)!r}))\nassert q['passed'],q['errors']"]
F.mkdir(parents=True,exist_ok=True);log=F/f'page{n:02}-build.log';prior=F/f'page{n:02}.pdf'
if prior.exists():raise ValueError('Archive and review existing source2015 proof before rebuilding')
with log.open('w',encoding='utf8')as out:
 for i,code in enumerate(jobs,1):
  r=subprocess.run([sys.executable,'-u','-X','utf8','-c',code],env=env,stdout=out,stderr=subprocess.STDOUT)
  if r.returncode:print('NATIVE_2015_TS_PAGE_FAILED',n,'stage',i,'log',log,flush=True);raise SystemExit(r.returncode)
  print('NATIVE_2015_TS_PAGE_STAGE_PASS',n,i,flush=True)
print('NATIVE_2015_TS_PAGE_ALL_SEVEN_CHECKS_PASS',n,flush=True)

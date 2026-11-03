from pathlib import Path
import sys,subprocess,os,hashlib
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2017-complete-solutions');F=B/'natural/2017/TS';n=int(sys.argv[1]);plan=F/f'plans/page{n:02}.json';proof=F/f'page{n:02}.pdf';pin=hashlib.sha256(proof.read_bytes()).hexdigest()
env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
prefix=f"import sys;from pathlib import Path;sys.path[:0]=[{str(B/'engine')!r},'D:/CodexBuilds/Hasla-publish-20261031/tools'];from pdf_memory_gate import page_worker;"
jobs=[prefix+f"from izho_natural_spacing_qa import audit\nwith page_worker():q=audit(2017,'TS',{n})\nassert q['passed']"]
for module in ['modern_new_prose_collision_audit','heading_source_alignment_audit','izho_2017_equation_counters','final_translation_font_audit','izho_2017_independent_original_math_geometry']:
 method='audit_plan'if module=='modern_new_prose_collision_audit'else'audit'
 jobs.append(prefix+f"from {module} import {method}\nwith page_worker():q={method}(Path({str(plan)!r}))\nassert q['passed']")
with (F/f'page{n:02}-read-only-recheck.log').open('w',encoding='utf8')as out:
 for i,code in enumerate(jobs,1):
  r=subprocess.run([sys.executable,'-u','-X','utf8','-c',code],env=env,stdout=out,stderr=subprocess.STDOUT)
  assert hashlib.sha256(proof.read_bytes()).hexdigest()==pin
  if r.returncode: print('READ_ONLY_RECHECK_FAILED',n,i,flush=True);raise SystemExit(r.returncode)
  print('READ_ONLY_RECHECK_PASS',n,i,flush=True)
print('ALL6_READ_ONLY_2017_RECHECKS_PASS',n,pin,flush=True)

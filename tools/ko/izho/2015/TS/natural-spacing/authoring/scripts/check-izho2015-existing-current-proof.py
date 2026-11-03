from pathlib import Path
import sys,subprocess,os
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2015-complete-solutions');env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
for n in map(int,sys.argv[1:]):
 p=B/f'natural/2015/TS/plans/page{n:02}.json';prefix=f"import sys;from pathlib import Path;sys.path[:0]=[{str(B/'engine')!r},'D:/CodexBuilds/Hasla-publish-20261031/tools'];from pdf_memory_gate import page_worker;";jobs=[f"from izho_natural_spacing_qa import audit\nwith page_worker():q=audit(2015,'TS',{n})\nassert q['passed']"]+[f"from {module} import {func}\nwith page_worker():q={func}(Path({str(p)!r}))\nassert q['passed']"for module,func in [('modern_new_prose_collision_audit','audit_plan'),('heading_source_alignment_audit','audit'),('izho_2015_equation_counters','audit'),('final_translation_font_audit','audit'),('izho_2015_independent_original_math_geometry','audit')]]
 with(B/f'natural/2015/TS/page{n:02}-current-check.log').open('w',encoding='utf8')as log:
  for i,code in enumerate(jobs,2):
   r=subprocess.run([sys.executable,'-u','-X','utf8','-c',prefix+code],env=env,stdout=log,stderr=subprocess.STDOUT)
   if r.returncode:print('CURRENT2015_PROOF_FAILED',n,i,flush=True);raise SystemExit(r.returncode)
   print('CURRENT2015_PROOF_STAGE_PASS',n,i,flush=True)

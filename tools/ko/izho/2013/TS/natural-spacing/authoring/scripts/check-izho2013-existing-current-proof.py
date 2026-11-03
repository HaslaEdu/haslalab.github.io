from pathlib import Path
import sys,subprocess,os,hashlib,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2013-complete-solutions');n=int(sys.argv[1]);plan=B/f'natural/2013/TS/plans/page{n:02}.json';F=plan.parent.parent
env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pdf=F/f'page{n:02}.pdf';before=sha(pdf)
prior=F/f'page{n:02}.audit.json'
if prior.exists():
 history=F/'history'/('audit-before-original-prose-reference-'+sha(prior)[:16]);history.mkdir(parents=True,exist_ok=True);shutil.copy2(prior,history/prior.name)
prefix=f"import sys;from pathlib import Path;sys.path[:0]=[{str(B/'engine')!r},'D:/CodexBuilds/Hasla-publish-20261031/tools'];from pdf_memory_gate import page_worker;"
jobs=[prefix+f"from izho_natural_spacing_qa import audit\nwith page_worker():q=audit(2013,'TS',{n})\nassert q['passed']",prefix+f"from modern_new_prose_collision_audit import audit_plan\nwith page_worker():q=audit_plan(Path({str(plan)!r}))\nassert q['passed']",prefix+f"from heading_source_alignment_audit import audit;q=audit(Path({str(plan)!r}));assert q['passed']",prefix+f"from izho_2013_equation_counters import audit;q=audit(Path({str(plan)!r}));assert q['passed']",prefix+f"from final_translation_font_audit import audit;q=audit(Path({str(plan)!r}));assert q['passed']"]
with(F/f'page{n:02}-current-recheck.log').open('w',encoding='utf8')as log:
 for i,code in enumerate(jobs,2):
  subprocess.run([sys.executable,'-u','-X','utf8','-c',code],env=env,stdout=log,stderr=subprocess.STDOUT,check=True);assert sha(pdf)==before;print('CURRENT_2013_PROOF_RECHECK_PASS',n,i,flush=True)
subprocess.run([sys.executable,'-u','-X','utf8','D:/CodexBuilds/check-and-preview-izho2013-extra-prose.py',str(n)],env=env,check=True);assert sha(pdf)==before
print('CURRENT_2013_ORIGINAL_PROSE_OVERLAP_PROOF_ALL_CHECKS_PASS',n,before,flush=True)

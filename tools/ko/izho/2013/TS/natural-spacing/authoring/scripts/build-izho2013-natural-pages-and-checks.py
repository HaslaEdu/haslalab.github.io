from pathlib import Path
import sys,subprocess,os,json,time
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2013-complete-solutions');env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1');progress=B/'natural/2013-private-page-progress.json';selected=list(map(int,sys.argv[1:]))
for n in selected:
 failed=None
 for name in['build-izho2013-solutions-natural-page.py','check-and-preview-izho2013-extra-prose.py']:
  result=subprocess.run([sys.executable,'-u','-X','utf8','D:/CodexBuilds/'+name,str(n)],env=env,cwd=Path.cwd())
  if result.returncode:failed=name;break
 rows={r['page']:r for r in json.loads(progress.read_text('utf8'))}if progress.exists()else{};rows[n]=dict(page=n,automated_checks_passed=failed is None,failed_stage=failed,visual_review_still_required=True);progress.write_text(json.dumps([rows[k]for k in sorted(rows)],indent=2)+'\n','utf8');print('IZHO2013_PRIVATE_PAGE_PROGRESS',n,'PASS'if failed is None else'NEEDS_REFINEMENT',failed or'',flush=True);time.sleep(8)
print('SELECTED_2013_SOURCE_PAGES_INITIAL_FINAL_CHECKS_FINISHED',selected,flush=True)

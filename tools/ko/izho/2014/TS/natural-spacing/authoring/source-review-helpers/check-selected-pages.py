from pathlib import Path
import json,subprocess,sys,os,hashlib
R=Path('D:/CodexBuilds');B=R/'Hasla-original-style-20261031/izho2014-complete-solutions';F=B/'natural/2014/TS';progress=B/'natural/2014-child-reviewed-progress.json';env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
for n in map(int,sys.argv[1:]):
 failure=None
 for name in['build-izho2014-solutions-natural-page.py','check-and-preview-izho2014-extra-prose.py']:
  r=subprocess.run([sys.executable,'-u','-X','utf8',str(R/name),str(n)],env=env)
  if r.returncode:failure=name;break
 rows={r['page']:r for r in json.loads(progress.read_text('utf8'))}if progress.exists()else{};pdf=F/f'page{n:02}.pdf';rows[n]=dict(page=n,all_automated_checks_passed=failure is None,failed_step=failure,pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest()if pdf.exists()else None,visual_review_still_required=True)
 progress.write_text(json.dumps([rows[k]for k in sorted(rows)],indent=2)+'\n','utf8');print('PRIVATE2014_CHILD_REVIEWED_PAGE_CHECKS',n,'PASS'if failure is None else'NEEDS_REFINEMENT',failure or'',flush=True)

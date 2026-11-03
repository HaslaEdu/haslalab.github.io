from pathlib import Path
import subprocess,sys,os,time,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions');env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf8',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1');progress=B/'natural/2012-private-page-progress.json';rows={r['page']:r for r in json.loads(progress.read_text('utf8'))}if progress.exists()else{}
audit_only='--audit-only'in sys.argv
selected=list(map(int,[a for a in sys.argv[1:]if a!='--audit-only']))
for n in selected:
 steps=['build-izho2012-solutions-natural-page.py','audit-izho2012-final-fonts-and-headings.py','render-izho2012-reviewed-previews.py'];failed=None
 for name in steps:
  extra=['--audit-only']if audit_only and name=='build-izho2012-solutions-natural-page.py'else[]
  r=subprocess.run([sys.executable,'-X','utf8','D:/CodexBuilds/'+name,str(n),*extra],env=env,cwd=Path.cwd())
  if r.returncode:failed=name;break
 if progress.exists():rows.update({r['page']:r for r in json.loads(progress.read_text('utf8'))})
 rows[n]=dict(page=n,automated_checks_passed=failed is None,failed_stage=failed,visual_review_still_required=True)
 progress.write_text(json.dumps([rows[k]for k in sorted(rows)],indent=2)+'\n','utf8')
 print('IZHO2012_PRIVATE_PAGE_PROGRESS',n,'PASS'if failed is None else'NEEDS_REFINEMENT',failed or'',flush=True)
 time.sleep(8)
print('SELECTED_2012_PAGES_FINISHED',json.dumps([rows[n]for n in selected]),flush=True)
if any(not rows[n]['automated_checks_passed']for n in selected):raise SystemExit(1)

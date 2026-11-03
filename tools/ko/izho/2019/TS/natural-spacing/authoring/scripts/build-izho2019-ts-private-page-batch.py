from pathlib import Path
import sys,subprocess,os,json,time,hashlib,datetime
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions');env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1');progress=B/'natural/2019-private-page-progress.json';selected=list(map(int,sys.argv[1:]));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for n in selected:
 failed=None
 for script in['build-izho2019-ts-natural-page.py','check-and-preview-izho2019-ts-extra-prose.py','audit-izho2019-ts-actual-expression-geometry.py']:
  result=subprocess.run([sys.executable,'-u','-X','utf8','D:/CodexBuilds/'+script,str(n)],env=env,cwd=Path.cwd())
  if result.returncode:failed=script;break
 rows={r['page']:r for r in json.loads(progress.read_text('utf8'))}if progress.exists()else{};proof=B/f'natural/2019/TS/page{n:02}.pdf';rows[n]=dict(page=n,automated_checks_passed=failed is None,failed_stage=failed,proof_sha256=sha(proof)if proof.exists()else None,visual_review_still_required=True,updated_utc=datetime.datetime.now(datetime.UTC).isoformat());progress.write_text(json.dumps([rows[k]for k in sorted(rows)],indent=2)+'\n','utf8');print('IZHO2019_PRIVATE_PAGE_PROGRESS',n,'PASS'if failed is None else'NEEDS_SOURCE_REFINEMENT',failed or'',flush=True);time.sleep(5)
print('SELECTED2019_INITIAL_PRIVATE_CHECKS_FINISHED',selected,flush=True)

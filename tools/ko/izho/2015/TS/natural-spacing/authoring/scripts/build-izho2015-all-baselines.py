from pathlib import Path
import subprocess,sys,os,time,json
R=Path('D:/CodexBuilds');B=R/'Hasla-original-style-20261031/izho2015-complete-solutions';env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1');progress=[]
for n in range(1,12):
 result=subprocess.run([sys.executable,'-u','-X','utf8',str(R/'build-izho2015-solutions-baseline-page.py'),str(n)],env=env,cwd=Path.cwd());progress.append(dict(page=n,baseline_checks_passed=result.returncode==0));(B/'2015-private-baseline-progress.json').write_text(json.dumps(progress,indent=2)+'\n','utf8');print('IZHO2015_BASELINE_PROGRESS',n,result.returncode,flush=True);time.sleep(2)
assert all(r['baseline_checks_passed']for r in progress),progress

from pathlib import Path
import subprocess,sys,json,os
r=Path('D:/CodexBuilds');b=r/'Hasla-original-style-20261031/izho2017-complete-solutions';env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf8',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1');rows=[]
for n in range(1,15):
 res=subprocess.run([sys.executable,'-X','utf8','-u',str(r/'build-izho2017-solutions-baseline-page.py'),str(n)],env=env);rows.append(dict(page=n,passed=res.returncode==0));(b/'2017-baseline-progress.json').write_text(json.dumps(rows,indent=2)+'\n','utf8');assert res.returncode==0,('Baseline failed',n)
print('ALL14_2017_INITIAL_SOURCE_LAYOUT_BASELINES_PASS',flush=True)

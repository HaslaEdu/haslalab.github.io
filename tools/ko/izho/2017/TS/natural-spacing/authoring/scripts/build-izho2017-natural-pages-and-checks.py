from pathlib import Path
import sys,subprocess,os,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2017-complete-solutions');env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1');progress=[]
for n in map(int,sys.argv[1:]):
 r=subprocess.run([sys.executable,'-u','-X','utf8','D:/CodexBuilds/build-izho2017-solutions-natural-page.py',str(n)],env=env);progress.append(dict(page=n,passed=r.returncode==0));(B/'2017-private-natural-progress.json').write_text(json.dumps(progress,indent=2)+'\n','utf8')
assert all(p['passed']for p in progress)

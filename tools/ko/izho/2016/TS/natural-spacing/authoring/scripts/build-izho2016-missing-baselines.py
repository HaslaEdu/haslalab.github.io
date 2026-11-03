from pathlib import Path
import subprocess,sys,os
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf8',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
for n in map(int,sys.argv[1:]):
 subprocess.run([sys.executable,'-u','-X','utf8','D:/CodexBuilds/build-izho2016-solutions-baseline-page.py',str(n)],check=True,cwd=Path.cwd(),env=env)
 print('COMPLETE_PRIVATE_IZHO2016_NATIVE_BASELINE_SOURCE_PAGE',n,flush=True)

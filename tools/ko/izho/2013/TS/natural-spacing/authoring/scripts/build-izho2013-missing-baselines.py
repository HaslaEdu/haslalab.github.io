from pathlib import Path
import subprocess,sys,os,time
root=Path.cwd();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf8',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
for n in map(int,sys.argv[1:]):
 subprocess.run([sys.executable,'-X','utf8','D:/CodexBuilds/build-izho2013-solutions-baseline-page.py',str(n)],check=True,cwd=root,env=env)
 print('COMPLETE_PRIVATE_IZHO2013_NATIVE_BASELINE_SOURCE_PAGE',n,flush=True);time.sleep(8)

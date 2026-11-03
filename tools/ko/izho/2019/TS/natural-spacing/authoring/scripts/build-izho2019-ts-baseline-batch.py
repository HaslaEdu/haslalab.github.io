from pathlib import Path
import subprocess,sys,os
B=Path("C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions")
env=dict(os.environ,PYTHONIOENCODING="utf8",PYTHONDONTWRITEBYTECODE="1",OPENBLAS_NUM_THREADS="1",OMP_NUM_THREADS="1",MKL_NUM_THREADS="1")
(B/"2019/native-baseline").mkdir(exist_ok=True)
for n in map(int,sys.argv[1:]):
 r=subprocess.run([sys.executable,"-u","-X","utf8","D:/CodexBuilds/build-izho2019-ts-baseline-page.py",str(n)],env=env)
 if r.returncode:raise SystemExit(r.returncode)

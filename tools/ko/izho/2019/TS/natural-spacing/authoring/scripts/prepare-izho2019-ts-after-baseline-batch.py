from pathlib import Path
import sys,subprocess,time,os
B=Path("C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions")
env=dict(os.environ,PYTHONIOENCODING="utf8",PYTHONDONTWRITEBYTECODE="1",OPENBLAS_NUM_THREADS="1",OMP_NUM_THREADS="1",MKL_NUM_THREADS="1")
while not all((B/f"2019/native-baseline/page{n:02}.qa.json").exists()for n in range(1,13)):time.sleep(10)
r=subprocess.run([sys.executable,"-u","-X","utf8","D:/CodexBuilds/prepare-izho2019-ts-natural.py",*map(str,range(1,13))],env=env)
raise SystemExit(r.returncode)

from pathlib import Path
import json,os,subprocess,sys
import icho2019_write_guard as guard
BASE=Path(__file__).resolve().parent;GATE=Path('D:/CodexBuilds/Hasla-publish-20261031/tools/pdf_memory_gate.py')
env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
only='--profile-only'in sys.argv
for n in map(int,[v for v in sys.argv[1:]if v!='--profile-only']):
    run=subprocess.run([sys.executable,'-X','utf8',str(GATE),'--',sys.executable,'-X','utf8',str(BASE/'profile_source_page.py'),str(n)]+(['--profile-only']if only else[]),cwd=BASE,env=env)
    if run.returncode:raise SystemExit(run.returncode)
guard.assert_protected_2024()

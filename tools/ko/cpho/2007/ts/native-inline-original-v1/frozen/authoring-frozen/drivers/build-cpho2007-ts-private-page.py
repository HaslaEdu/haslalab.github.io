from pathlib import Path
import sys,subprocess,os
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS');n=int(sys.argv[1]);lang=sys.argv[2];env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf8',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1');folder=B/f'evidence/{lang}';folder.mkdir(parents=True,exist_ok=True)
for stage,fn in[(1,'build_initial'),(2,'build_natural'),(3,'audit_natural')]:
 code=f"import sys;sys.path.insert(0,{str(B/'engine')!r});from pdf_memory_gate import page_worker;from cpho2007_ts_runtime import {fn}\nwith page_worker():{fn}({n},{lang!r})"
 log=folder/f'page{n:02}-stage{stage}.log'
 with log.open('w',encoding='utf8')as out:result=subprocess.run([sys.executable,'-u','-X','utf8','-c',code],env=env,stdout=out,stderr=subprocess.STDOUT)
 print('CPHO2007_TS_PRIVATE_PAGE_STAGE',n,lang,stage,'PASS'if result.returncode==0 else'NEEDS_REFINEMENT',log,flush=True)
 if result.returncode:raise SystemExit(result.returncode)
print('CPHO2007_TS_ALL_INITIAL_NATIVE_PROOF_CHECKS_PASS',n,lang,flush=True)

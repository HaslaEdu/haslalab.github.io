from pathlib import Path
import subprocess,sys,os,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
env=os.environ.copy();env.update(PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=';'.join([str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']))
for page in list(map(int,sys.argv[1:]))or[4,5]:
 for lang in ['ko','en']:
  for name,suffix in [('cpho_2005_ts_qa.py','.source-qa.json'),('cpho_2005_ts_poppler_qa.py','.poppler-qa.json')]:
   proc=subprocess.run([sys.executable,str(B/'tools'/name),str(page),lang],env=env)
   if proc.returncode:raise SystemExit(proc.returncode)
   report=json.loads((B/f'proofs/{lang}/page{page:02}{suffix}').read_text('utf8'))
   if not report['passed']:raise SystemExit(f'FAILED {page} {lang} {name}')
print('BOTH_PAGES_BOTH_LANGUAGES_BOTH_RENDERERS_PASS',flush=True)

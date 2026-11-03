from pathlib import Path
import subprocess,sys,json,os
R=Path('D:/CodexBuilds');B=R/'Hasla-original-style-20261031/cpho2007/TS';result=[]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf8',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
sys.path.insert(0,str(B/'engine'))
from cpho2007_ts_runtime import source_page
from cpho2007_ts_initial_native_baseline import translated_text
def current_language(n,lang):
 path=B/f'native-baseline/{lang}/page{n:02}-source-indexed.build.json'
 if not path.exists():return False
 actual={r['id']:r['text']for r in json.loads(path.read_text('utf8'))['fit_report']}
 auth=json.loads((B/f'authoring/page{n:02}-bilingual-prose.json').read_text('utf8'))['prose'];slots=source_page(n)['slots']
 expected={s['id']:translated_text(s,auth[s['id']][lang])for s in slots}
 return actual==expected
for n in range(int(sys.argv[1]),int(sys.argv[2])+1):
 for lang in ['ko','en']:
  baseline=B/f'native-baseline/{lang}/page{n:02}-source-indexed.pdf'
  if baseline.exists():
   audit=B/f'natural/2007/{lang}/page{n:02}.audit.json'
   if audit.exists()and json.loads(audit.read_text('utf8')).get('passed')and current_language(n,lang):print('EXISTING_PASSED_CURRENT_PROSE',n,lang,flush=True);continue
   subprocess.run([sys.executable,str(R/'preserve-cpho2007-ts-page.py'),str(n),lang],env=env,check=True)
  p=subprocess.run([sys.executable,str(R/'build-cpho2007-ts-private-page.py'),str(n),lang],env=env)
  result.append(dict(page=n,language=lang,exit_code=p.returncode));print('BATCH_PAGE_RESULT',n,lang,p.returncode,flush=True)
path=B/f'evidence/batch-pages{sys.argv[1]}-{sys.argv[2]}.json';path.write_text(json.dumps(result,indent=2)+'\n','utf8')

from pathlib import Path
import sys,json,hashlib,subprocess,os
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS');sys.path.insert(0,str(B/'engine'))
from pdf_memory_gate import page_worker
from cpho2007_ts_runtime import source_page
from cpho2007_ts_initial_native_baseline import translated_text
POP=Path('C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe');assert POP.exists();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();records=[]
for n in range(int(sys.argv[1]),int(sys.argv[2])+1):
 for lang in['ko','en']:
  proof=B/f'natural/2007/{lang}/page{n:02}.pdf';audit=proof.with_suffix('.audit.json')
  if not audit.exists()or not json.loads(audit.read_text('utf8')).get('passed'):continue
  if n!=20:
   journal=json.loads((B/f'native-baseline/{lang}/page{n:02}-source-indexed.build.json').read_text('utf8'));auth=json.loads((B/f'authoring/page{n:02}-bilingual-prose.json').read_text('utf8'))['prose'];expected={s['id']:translated_text(s,auth[s['id']][lang])for s in source_page(n)['slots']}
   if {r['id']:r['text']for r in journal['fit_report']}!=expected:print('SKIP_STALE_AUTHORING',n,lang,flush=True);continue
  digest=sha(proof);folder=B/f'proof-renders-144/{lang}';folder.mkdir(parents=True,exist_ok=True);stem=folder/f'page{n:02}-{digest[:16]}';png=stem.with_suffix('.png')
  if not png.exists():
   with page_worker():subprocess.run([str(POP),'-f','1','-l','1','-r','144','-png','-singlefile',str(proof),str(stem)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  records.append(dict(source_page=n,language=lang,proof=str(proof),proof_sha256=digest,png=str(png),png_sha256=sha(png),dpi=144,visual_review_pending=True));print('FRESH_POPPLER_144_PROOF_READY',n,lang,png,flush=True)
path=B/f'evidence/poppler144-pages{sys.argv[1]}-{sys.argv[2]}.json';path.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n','utf8')

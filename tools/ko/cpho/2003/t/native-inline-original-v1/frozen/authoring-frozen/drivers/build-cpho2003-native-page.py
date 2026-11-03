from pathlib import Path
import sys,json,hashlib,subprocess,os
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');sys.path.insert(0,str(B/'engine'))
from pdf_memory_gate import page_worker
import cpho2003_native_runtime as r
lang=sys.argv[1];n=int(sys.argv[2]);assert lang in ['ko','en']and n in [1,2,3]
with page_worker():
 initial=r.baseline_path(n,lang)
 if initial.exists():
  import cpho2003_initial_native_baseline as m
  journal=json.loads(initial.with_suffix('.build.json').read_text('utf8'));rows={s['id']:s for s in r.source_page(n)['slots']}
  texts={line.split('\t')[0]:line.split('\t')[1 if lang=='ko'else 2]for line in (B/f'authoring/native/page{n:02}.tsv').read_text('utf8').splitlines()}
  assert all(v['text']==m.translated_text(rows[v['id']],texts[v['id']])for v in journal['fit_report'])
  assert journal['source_sha256']==r.SOURCE_SHA and journal['output_sha256']==r.sha(initial)
 else:initial=r.build_initial(n,lang)
 out=r.build_natural(n,lang);qa=r.audit_natural(n,lang)
 pop=Path('C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe');folder=B/f'proof-renders-144/{lang}';folder.mkdir(parents=True,exist_ok=True);stem=folder/f'page{n:02}-{r.sha(out)[:16]}';assert not stem.with_suffix('.png').exists()
 subprocess.run([str(pop),'-f','1','-l','1','-r','144','-png','-singlefile',str(out),str(stem)],check=True,capture_output=True)
 print('CPHO2003_NATIVE_PAGE_STRICT_QA_PASS',lang,n,r.sha(out),flush=True)

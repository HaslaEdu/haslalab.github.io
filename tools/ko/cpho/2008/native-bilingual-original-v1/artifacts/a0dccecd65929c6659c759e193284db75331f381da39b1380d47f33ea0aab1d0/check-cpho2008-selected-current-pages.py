"""Current-SHA checks; reuse only an actual unchanged passing report."""
from pathlib import Path
import sys,json,hashlib,subprocess
B=Path(__file__).resolve().parents[1];sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups
from cpho2008_independent_native_qa import audit as native
from cpho2008_original_CID_states import audit as states
from cpho2008_new_prose_qa import audit as prose
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_text('utf8'));S=B/'source/CPhO_2008_original_combined_ZH.pdf'
POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
def current(p,pin):
 if not p.exists():return False
 r=read(p);return r.get('passed')is True and r.get('proof_sha256')==pin
failures=[]
for value in sys.argv[1:]:
 n,lang=value.split(':');n=int(n);pdf=B/f'proofs/{lang}/page{n:02}.pdf';pin=sha(pdf)
 with page_worker():
  if not current(pdf.with_suffix('.independent-native-audit.json'),pin):native(n,lang)
  p=pdf.with_suffix('.original-encoded-CID-states.json')
  if not current(p,pin):
   c=read(pdf.with_suffix('.composition.json'));r=states(S,n,pdf,read(B/f'inspection/page{n:02}-original-native-programs.json'),inspect_inline_groups(pdf,1,include_text_shows=True),c['erased_original_language_glyphs']);p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n','utf8');print('CURRENT_SOURCE_CID_STATE',n,lang,r['passed'],r['actual_original_encoded_CIDs_checked'],flush=True)
  if not current(pdf.with_suffix('.new-prose-style-spacing-visibility.json'),pin):prose(n,lang)
  out=B/f'inspection/page{n:02}-{lang}-current144';rpath=out.with_suffix('.json')
  if not out.with_suffix('.png').exists()or not rpath.exists()or read(rpath).get('proof_sha256')!=pin:
   r=subprocess.run([POP,'-f','1','-l','1','-singlefile','-r','144','-png',str(pdf),str(out)],capture_output=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW);rpath.write_text(json.dumps(dict(renderer='independent external Poppler144dpi',proof_sha256=pin,png_sha256=sha(out.with_suffix('.png')),proof_full_page_visual_review_pending=True,stderr=r.stderr.decode('utf8','replace')),indent=2)+'\n','utf8')
  assert sha(pdf)==pin
  page_pass=all(current(pdf.with_suffix('.'+kind+'.json'),pin)for kind in ['independent-native-audit','original-encoded-CID-states','new-prose-style-spacing-visibility'])
  if not page_pass:failures.append([n,lang,pin])
  print('CURRENT_CHECKS_AND144_PREVIEW_PASS'if page_pass else'CURRENT_CHECKS_DIAGNOSTIC_FAILURE',n,lang,pin,flush=True)
if failures:raise SystemExit('CURRENT_SHA_PAGE_AUDITS_FAILED '+json.dumps(failures))

from pathlib import Path
import sys,subprocess,os,json,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');F=B/'natural/2016/TS';sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for n in map(int,sys.argv[1:]):
 pdf=F/f'page{n:02}.pdf';out=F/f'page{n:02}-preview';before=sha(pdf)
 with page_worker():r=subprocess.run([POP,'-f','1','-l','1','-singlefile','-r','144','-png',str(pdf),str(out)],check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt'else 0)
 assert sha(pdf)==before
 q=dict(pdf_sha256=before,png_sha256=sha(out.with_suffix('.png')),source_page=n,renderer='independent external Poppler144dpi',renderer_stderr=r.stderr.decode('utf8','replace'))
 out.with_suffix('.json').write_text(json.dumps(q,indent=2)+'\n','utf8');print('INDEPENDENT_POPPLER_CURRENT_PROOF_PREVIEW_READY',n,before,flush=True)

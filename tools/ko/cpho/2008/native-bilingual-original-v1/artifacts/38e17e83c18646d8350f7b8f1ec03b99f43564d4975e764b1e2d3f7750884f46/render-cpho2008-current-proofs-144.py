from pathlib import Path
import sys,subprocess,hashlib,json
B=Path(__file__).resolve().parents[1];sys.path.insert(0,'D:/CodexBuilds/Hasla-publish-20261031/tools');from pdf_memory_gate import page_worker
POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
n=int(sys.argv[1]);langs=sys.argv[2:]or['ko','en']
for lang in langs:
 p=B/f'proofs/{lang}/page{n:02}.pdf';assert p.exists();out=B/f'inspection/page{n:02}-{lang}-current144'
 with page_worker():r=subprocess.run([POP,'-f','1','-l','1','-singlefile','-r','144','-png',str(p),str(out)],capture_output=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
 q=dict(renderer='independent external Poppler144dpi',proof_sha256=sha(p),png_sha256=sha(out.with_suffix('.png')),proof_full_page_visual_review_pending=True,stderr=r.stderr.decode('utf8','replace'))
 out.with_suffix('.json').write_text(json.dumps(q,indent=2)+'\n','utf8');print('EXTERNAL_FULL_PAGE144',n,lang,q['proof_sha256'],flush=True)

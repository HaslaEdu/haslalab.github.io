from pathlib import Path
import sys,subprocess,hashlib,json
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2019-theory-original/natural/2019/T');tool='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
for n in map(int,sys.argv[1:]):
 p=B/f'page{n:02}.pdf';prefix=B/f'page{n:02}-preview';r=subprocess.run([tool,'-f','1','-singlefile','-r','144','-png',str(p),str(prefix)],check=True,capture_output=True);q=dict(pdf_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),png_sha256=hashlib.sha256(prefix.with_suffix('.png').read_bytes()).hexdigest(),renderer='external Poppler144dpi fresh process',returncode=r.returncode);(B/f'page{n:02}-preview.json').write_text(json.dumps(q,indent=2)+'\n','utf8');print('FRESH2019_POPPLER_PREVIEW',n,q['pdf_sha256'],flush=True)

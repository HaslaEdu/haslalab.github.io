from pathlib import Path
import sys,subprocess,hashlib,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original/natural/2018/T')
tool='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
for n in map(int,sys.argv[1:]):
 p=B/f'page{n:02}.pdf';prefix=B/f'page{n:02}-preview'
 result=subprocess.run([tool,'-f','1','-singlefile','-r','144','-png',str(p),str(prefix)],check=True,capture_output=True)
 q=dict(pdf_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),png_sha256=hashlib.sha256(prefix.with_suffix('.png').read_bytes()).hexdigest(),renderer='external Poppler144dpi fresh process',returncode=result.returncode)
 (B/f'page{n:02}-preview.json').write_text(json.dumps(q,indent=2)+'\n','utf8');print('FRESH_POPPLER_PREVIEW',n,q['pdf_sha256'],flush=True)

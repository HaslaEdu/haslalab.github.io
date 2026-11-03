from pathlib import Path
import sys,json,subprocess,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path.insert(0,'D:/CodexBuilds/Hasla-publish-20261031/tools')
from pdf_memory_gate import page_worker
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
exe='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
for number in [4,5,6]:
 for lang in ['ko','en']:
  p=B/f'proofs/{lang}/page{number:02}.pdf';digest=sha(p)
  q=json.loads(p.with_suffix('.source-qa.json').read_text('utf8'));pop=json.loads(p.with_suffix('.poppler-qa.json').read_text('utf8'))
  assert q['passed']and pop['passed']and q['final_sha256']==pop['proof_sha256']==digest
  with page_worker():subprocess.run([exe,'-f','1','-singlefile','-r','144','-png',str(p),str(p.parent/f'page{number:02}-preview')],check=True,capture_output=True)
  assert sha(p)==digest
  print('FRESH_ORIGINAL_QUALITY_REVIEW_PREVIEW',number,lang,digest,flush=True)

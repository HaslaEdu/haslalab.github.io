from pathlib import Path
import sys,json,hashlib
B=Path(__file__).resolve().parents[1];sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from cpho2008_kept_ink_collision import audit
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
values=sys.argv[1:]or[f'{n}:{lang}'for n in range(1,22)for lang in ('ko','en')]
failed=[]
for value in values:
    n,lang=value.split(':');n=int(n);pdf=B/f'proofs/{lang}/page{n:02}.pdf';r=pdf.with_suffix('.kept-ink-collision.json')
    if r.exists():
        old=json.loads(r.read_text('utf8'))
        if old.get('passed')and old.get('proof_sha256')==sha(pdf):continue
    with page_worker():result=audit(n,lang)
    if not result['passed']:failed.append(value)
if failed:raise SystemExit('C08_KEPT_INK_FAILURES '+','.join(failed))

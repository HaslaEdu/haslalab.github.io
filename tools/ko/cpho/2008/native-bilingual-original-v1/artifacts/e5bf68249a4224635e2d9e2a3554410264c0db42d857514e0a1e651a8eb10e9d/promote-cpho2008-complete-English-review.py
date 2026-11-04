"""Archive actual previous English proofs before installing reviewed prose only."""
from pathlib import Path
import sys,json,hashlib,subprocess
B=Path(__file__).resolve().parents[1];sys.path.insert(0,str(B/'engine'))
from cpho2008_atomic_authoring import atomic_text
F=B/'authoring/English-complete-sentence-review';review=json.loads((F/'explicit-source-complete-English-review.json').read_text('utf8'));assert review['all_candidates_fit']
pages=sorted({r['source_page']for r in review['changes']});records=[]
for n in pages:
    live=B/f'authoring/page{n:02}-native-language.json';candidate=F/f'page{n:02}-native-language-candidate.json';old=json.loads(live.read_text('utf8'));new=json.loads(candidate.read_text('utf8'));assert len(old['rows'])==len(new['rows'])
    for a,z in zip(old['rows'],new['rows']):
        assert {k:v for k,v in a.items()if k!='en'}=={k:v for k,v in z.items()if k!='en'},(n,a['id'],'Only English prose may change')
    if old==new:continue
    pdf=B/f'proofs/en/page{n:02}.pdf';pin=hashlib.sha256(pdf.read_bytes()).hexdigest()
    subprocess.run([sys.executable,str(B/'scripts/archive-cpho2008-native-review.py'),str(n),'Continuous source-prose review: replace compressed English notes with accurate complete grammatical clauses at the original point; original Korean/math/source design unchanged','en'],check=True)
    atomic_text(live,candidate.read_text('utf8'));records.append(dict(source_page=n,old_actual_English_proof_sha256=pin,new_source_plan_sha256=hashlib.sha256(live.read_bytes()).hexdigest(),all_original_native_fonts_math_points_Y_images_and_Korean_unchanged=True))
out=F/'actual-old-English-proofs-archived-before-natural-revision.json'
if out.exists():
    old=out.read_bytes();h=F/'previous-reviewed-prose';h.mkdir(exist_ok=True);p=h/(hashlib.sha256(old).hexdigest()+'.json')
    if not p.exists():atomic_text(p,old.decode('utf8'))
atomic_text(out,json.dumps(dict(original_source_sha256=review['source_sha256'],pages=records),indent=2)+'\n')
print('C08_ENGLISH_COMPLETE_PROSE_PROMOTED',len(records))

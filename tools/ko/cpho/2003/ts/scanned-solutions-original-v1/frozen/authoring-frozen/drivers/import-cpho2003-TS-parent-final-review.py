from pathlib import Path
import json,hashlib,shutil
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');T=B/'TS';M=T/'master-v3';F=M/'authoring-frozen'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=T/'root-M3-approved-full14-original-design-and-semantic-review.json';q=json.loads(p.read_text('utf8'));assert q['source_sha256']==sha(B/'inputs/CPhO_2003_Chinese_original.pdf');assert q['approved_current_pages']==14 and q['pending_only_EN_source_pages']==[] and q['all7_original_full_pages_read']and q['all_other_prose_approved']
assert len(q['pages'])==14
for r in q['pages']:
 n=r['source_page'];lang=r['language'];assert r['approved']and r['parent_full_original_and_current_visual_and_paragraph_read']and r['issue']is None
 assert r['proof_sha256']==sha(F/f'proofs/{lang}/page{n:02}.pdf')
 assert r['full_preview_sha256']==sha(F/f'proofs/{lang}/page{n:02}-poppler/final.png')
 assert r['original_full_preview_sha256']==sha(F/f'source-renders/page{n:02}.png')
out=F/'evidence/root-final-full-visual-semantic-review.json';assert not out.exists();shutil.copy2(p,out);shutil.copy2(Path(__file__),F/'drivers'/Path(__file__).name);assert sha(out)==sha(p)
print('PARENT_APPROVED_ALL14_CURRENT_EXACT_PROOFS_AND_FULL_PREVIEWS',sha(out),flush=True)

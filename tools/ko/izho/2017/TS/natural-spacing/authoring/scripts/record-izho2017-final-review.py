from pathlib import Path
import hashlib,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-initial-theory');f=B/'natural/2017/T';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
pages=[]
for n in range(1,8):
 proof=f/f'page{n:02}.pdf';a=json.loads(proof.with_suffix('.audit.json').read_text('utf8'));c=json.loads(proof.with_suffix('.prose-collision.json').read_text('utf8'));assert a['passed']and c['passed']and a['output_sha256']==c['final_sha256']==sha(proof)
 pages.append(dict(page=n,proof_sha256=sha(proof),reviewed=True,review='Exact final full page manually inspected at774x1095 after all current physical-ink and independent prose-collision checks. Natural quarter-em prose spacing, original source font roles/point sizes, source title centers, every original mathematical expression and complete native figures retained. Page3 four bold native labels translated at original size/centers. Page4 full native height fraction packs horizontally beside its clause; v_infinity=100km/s and impact-parameter10^8 are separate source conditions. Page5 corrected staging clause, full Eq3 and following prose kept separate. Page6 both source caption centers restored.',review_image=str(f/f'final-page-review/page{n:02}.png'),review_image_sha256=sha(f/f'final-page-review/page{n:02}.png')))
(f/'visual-review.json').write_text(json.dumps(dict(pages=pages),ensure_ascii=False,indent=2)+'\n','utf8');print('VISUAL_REVIEW_COMPLETE',len(pages))

"""Freeze the root's visual review and the two corrected source clause joins."""
from pathlib import Path
import json,hashlib
B=Path(__file__).resolve().parents[1]
C=Path('C:/Users/andre/CodexWork/HaslaLab/translation-proof-work')
P=C/'proofs/icho/2024-final';E=B/'historical/icho/composer-2024'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as s:
  while chunk:=s.read(1048576):h.update(chunk)
 return h.hexdigest()
read=lambda p:json.loads(Path(p).read_text('utf8'))
ready=read(E/'READY.json');inventory=read(E/'final-inventory.json')
assert sha(E/'READY.json')=='305896bd3fc880f3d2783c3771bf2a847f2fa6389ffff2df9e9c383cc990a517'
assert sha(E/'final-inventory.json')==ready['inventory_sha256']=='a480ec90b1333740b3da743444c99ece663827559616cb9759b0d96d0d9db72e'
assert ready['status']=='READY'and inventory['passed']and inventory['technical_passed']
assert inventory['errors']==inventory['unreviewed']==[]
old=read(C/'staged/icho/review-2024/inventory-verified.json')['entries']
rows=[];changed=[];changed_qa=[]
for entry in inventory['entries']:
 i=entry['page'];p=P/f'page{i:02}.pdf';q=p.with_suffix('.layout.json');review=P/f'visual-review-page{i:02}.json';r=read(review)['pages'][0]
 assert sha(p)==entry['pdf_sha256']==r['proof_sha256']
 assert sha(q)==entry['layout_sha256']==r['layout_sha256']
 assert r['reviewed']and r['composer_sha256']==ready['composer_sha256']
 image=Path(r['render_image']);assert image.is_file()
 assert sha(image)==r['render_image_sha256']
 metadata=read(image.with_suffix('.render.json'));assert metadata['image_sha256']==sha(image)
 image_row=next(row for row in metadata['pages']if row['page']==i)
 assert image_row['proof_sha256']==sha(p)and image_row['layout_sha256']==sha(q)
 before=next(row for row in old if row['page']==i)
 if before['proof_sha256']!=sha(p):changed.append(i)
 if before['layout_sha256']!=sha(q):changed_qa.append(i)
 rows.append(dict(page=i,proof_sha256=sha(p),layout_sha256=sha(q),effective_plan_sha256=entry['effective_plan_sha256'],review_sha256=sha(review),review_image=str(image),review_image_sha256=sha(image),reviewed=True))
assert changed==changed_qa==[39,50]
assert rows[38]['proof_sha256']=='5787ddf9344913a614944cfd3b6b9b9f4e06ca766483eaaebcdb2e03de1aed59'
assert rows[49]['proof_sha256']=='32cd3074a3541537e913e5dec5f55fece6ede82bf353e2b94be425086c62cf34'
expanded=[1,2,3,4,5,6,7,8,13,14,15,16,17,18,19,20,21,22,27,28,31,32,33,34,37,38,39,40,41,42,43,44,45,46,49,50,51,52,55,56,57,58]
report=dict(status='PASS',source_sha256=ready['source_sha256'],pages=rows,
 root_layout_review_pages=list(range(1,63)),root_enlarged_review_pages=expanded,
 method='Root read fresh six-page layout contacts for every page and the enlarged final PNGs listed here. The translating agent read all62 full pages. Root then independently re-read the corrected39/50 full panels; all current image/proof/layout hashes are verified. Other60 PDF/layout/effective plans remain byte-identical.',
 changed_proof_pages=changed,changed_layout_pages=changed_qa,other60_proofs_unchanged=True,
 corrections=dict(page39='B를 얻는 단계에서 아세톤의 역할, DCC가 F를 페니실린 VK로 전환하는 단계에서 하는 역할: both instructions end with 답안지에 표시하라.',page50='C를 D로 전환하는 단계는 DMDO와의 원하지 않는 반응을 막기 위해 필요하다.'),
 program_sha256=sha(Path(__file__)))
out=B/'staged/icho/review-2024/root-independent-final-review.json';out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
print(json.dumps(dict(status='PASS',pages=len(rows),changed_proof_pages=changed,all_current_review_image_hashes_verified=True,path=str(out),sha256=sha(out))))

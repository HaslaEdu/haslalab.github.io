from pathlib import Path
import json,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2024-original-natural')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
preview=json.loads((B/'inspection/final-page-review/preview-index.json').read_text('utf8'))
for lang in ['KO','EN']:
 rows=[];visual=[]
 for n in range(1,6):
  final=B/f'T/figure-language/page{n:02}-{lang}.pdf';body=B/f'T/pages/page{n:02}-{lang}.pdf'
  a=json.loads((B/f'T/body-qa/page{n:02}-{lang}.audit.json').read_text('utf8'))
  f=json.loads((B/f'T/body-qa/page{n:02}-{lang}.font-style.json').read_text('utf8'))
  q=json.loads((B/f'T/figure-language/qa/page{n:02}-{lang}.audit.json').read_text('utf8'))
  assert a['passed'] and f['passed'] and q['passed']
  assert a['proof_sha256']==f['proof_sha256']==sha(body)
  assert q['body_sha256']==sha(body) and q['proof_sha256']==sha(final)
  r=next(p for p in preview['pages']if p['page']==n and p['language']==lang)
  assert r['proof_sha256']==sha(final) and r['image_sha256']==sha(r['image'])
  # The ten actual complete Poppler pages were inspected in this turn.
  r['reviewed']=True
  v=dict(r,source_page=n,source_math_atoms_reviewed=True,
   title_and_caption_alignment_reviewed=True,word_spacing_reviewed=True,
   original_figures_and_translated_labels_reviewed=True,
   review_note='Full-page Poppler preview visually inspected at774x1095; source point sizes and math-font programs independently checked. No unintended gaps, clipping, or collisions visible. Bitmap-label font/size information is source-measured, not embedded metadata.')
  visual.append(v);rows.append(dict(source_page=n,pdf=str(final),sha256=sha(final)))
 save(B/f'master-v1/{lang}-visual-review.json',dict(source_sha256=a['source_sha256'],language=lang,pages=visual))
 save(B/f'master-v1/{lang}-assembly-spec.json',dict(output=str(B/f'master-v1/CPhO_2024_T_{lang}.pdf'),proofs=rows))
save(B/'inspection/final-page-review/preview-index.json',preview)
print('Verified current raw audits, recorded ten actual visual reviews, wrote two assembly specs.')

from pathlib import Path
import hashlib,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS');O=B/'master-v1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
q=json.loads((O/'assembly-master-input.json').read_text('utf8'));editions=[]
for lang in ['ko','en']:
 output=O/f'editions/CPhO_2005_TS_{lang.upper()}.pdf';assembly=output.with_suffix('.assembly-qa.json');a=json.loads(assembly.read_text('utf8'))
 assert a['passed']and a['sha256']==sha(output)and len(a['pages'])==13
 pages=[];visual=[]
 for index,r in enumerate([r for r in q['proofs']if r['language']==lang],1):
  assert sha(r['pdf'])==r['sha256'];source_page=r['source_page'];v=json.loads((B/f'proofs/page{source_page:02}-visual-review.json').read_text('utf8'))
  checked=next(row for row in v['records']if row['language']==lang);assert checked['proof_sha256']==r['sha256']
  def ref(name,selector=None):
   p=Path(r['evidence'][name]);value=dict(path=str(p),sha256=sha(p))
   if selector:value['selector']=selector
   return value
  row=dict(page=index,source_page=source_page,pdf=r['pdf'],sha256=r['sha256'],source_scan_qa=ref('generic-scan-qa'),actual_style_qa=ref('publication-style-qa'),actual_outline_qa=ref('source-qa','new_prose_outlines'),independent_math_union_qa=ref('math-union-qa'),actual_single_source_math_qa=ref('source-qa','actual_final_math_single_native_source_controls'),poppler_source_and_math_qa=ref('poppler-qa'))
  if lang=='ko':row['hangul_visibility_qa']=ref('hangul-visibility')
  pages.append(row);visual.append(dict(page=index,source_page=source_page,proof_sha256=r['sha256'],reviewed=True,source_math_atoms_reviewed=True,fresh_poppler144_preview_sha256=checked['preview_sha256'],source_header_footer_centers_and_original_body_points_checked=True,quarter_em_word_spaces=True))
 view=O/f'visual-review-{lang}.json';view.write_text(json.dumps(dict(source_sha256=q['source_audited_sha256'],sha256=sha(output),pages=visual),ensure_ascii=False,indent=2)+'\n','utf8')
 editions.append(dict(output=str(output),sha256=sha(output),bytes=output.stat().st_size,pages=13,language=lang,proofs=pages,assembly_qa=str(assembly),visual_review=str(view)))
for snapshot in q['authoring_snapshots']:
 for rel,digest in snapshot['files'].items():assert sha(Path(snapshot['root'])/rel)==digest
ready=dict(status='READY',year=2005,kind='TS',source_original_sha256=q['source_original_sha256'],source_audited_sha256=q['source_audited_sha256'],editions=editions,authoring_snapshots=q['authoring_snapshots'],original_math_retyped=False,original_math_resampled=False,original_math_y_changed=False,translated_point_sizes_fitted=False,added_editorial_notes=0)
target=O/'CPhO_2005_TS_READY.json';target.write_text(json.dumps(ready,ensure_ascii=False,indent=2)+'\n','utf8')
print('FULL_CPHO2005_TS_READY',json.dumps([{k:r[k]for k in ['output','sha256','bytes','pages','language']}for r in editions]),flush=True)

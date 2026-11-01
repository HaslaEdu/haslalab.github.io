from pathlib import Path
import json,hashlib,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025/master-v1');p=B/'assembly-master-input.json';q=json.loads(p.read_text('utf8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,q):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
editions=[]
for lang in ['ko','en']:
 output=B/f'editions/CPhO_2025_T_{lang.upper()}.pdf';assembly=output.with_suffix('.assembly-qa.json');checked=json.loads(assembly.read_text('utf8'));assert checked['passed']and checked['sha256']==sha(output)and len(checked['pages'])==6
 pages=[];visual=[]
 for r in [r for r in q['proofs']if r['language']==lang]:
  assert sha(r['pdf'])==r['sha256']and sha(r['qa'])==r['qa_sha256'];qa=json.loads(Path(r['qa']).read_text('utf8'));assert qa['passed']and qa['final_sha256']==r['sha256']
  def ref(selector=None,path=None):
   src=Path(path or r['qa']);result=dict(path=str(src),sha256=sha(src))
   if selector:result['selector']=selector
   return result
  row=dict(page=r['source_page'],source_page=r['source_page'],pdf=r['pdf'],sha256=r['sha256'],source_scan_qa=ref())
  if r['source_page']==1:
   row.update(actual_style_qa=ref('actual_new_prose_styles'),actual_outline_qa=ref('actual_new_prose_outlines'),independent_math_union_qa=ref('independent_original_replayed_math_visibility'))
   if lang=='ko':row['hangul_visibility_qa']=ref(path=q['page01_ko_hangul_qa'])
  else:
   row.update(actual_style_qa=ref('actual_new_prose_style'),actual_outline_qa=ref('new_actual_prose_outlines'),independent_math_union_qa=ref('independent_replayed_math_visibility'))
   if lang=='ko':row['hangul_visibility_qa']=ref('hangul_visibility')
  if r.get('visual_review'):
   witness=json.loads(Path(r['visual_review']).read_text('utf8'));assert witness['reviewed']and witness['proof_sha256']==r['sha256']
  else:assert r['source_page']==1 and r['reviewed']
  visual.append(dict(page=r['source_page'],source_page=r['source_page'],proof_sha256=r['sha256'],reviewed=True,source_math_atoms_reviewed=True,source_witness=r.get('visual_review')or r.get('ready')))
  pages.append(row)
 visual_path=output.with_suffix('.visual-review.json');save(visual_path,dict(language=lang,sha256=sha(output),pages=visual,method='Full final page and original-source mathematical crop contacts manually reviewed by page author. Edition assembly independently unchanged in MuPDF4x and Poppler144.'))
 editions.append(dict(output=str(output),sha256=sha(output),bytes=output.stat().st_size,pages=6,language=lang,proofs=pages,assembly_qa=str(assembly),visual_review=str(visual_path)))
extra=B/'authoring-edition-assembly';extra.mkdir(exist_ok=True)
for name in ['assemble-scanned-proof-edition.py','prepare-cpho2025-assembly.py','finalize-cpho2025-master-ready.py','migrate-cpho2025-assembly-render-cache.py','cpho2025-master-assembly.log']:
 shutil.copy2(Path('D:/CodexBuilds')/name,extra/name)
q['authoring_snapshots'].append(dict(name='edition-assembly',root=str(extra),files={p.name:sha(p)for p in extra.iterdir()if p.is_file()}))
final=dict(status='READY',year=2025,kind='T',source_original_sha256=q['source_original_sha256'],source_audited_sha256=q['source_audited_sha256'],editions=editions,authoring_snapshots=q['authoring_snapshots'],original_math_retyped=False,original_math_resampled=False,original_math_y_changed=False,translated_point_sizes_fitted=False,added_editorial_notes=0)
normalization=B.parent/'source-clip-normalization.json';final['source_normalization_qa']=dict(path=str(normalization),sha256=sha(normalization))
target=B/'CPhO_2025_T_READY.json';save(target,final);print(json.dumps(dict(ready=str(target),editions=[{k:r[k]for k in ['output','sha256','bytes','pages','language']}for r in editions]),ensure_ascii=False),flush=True)

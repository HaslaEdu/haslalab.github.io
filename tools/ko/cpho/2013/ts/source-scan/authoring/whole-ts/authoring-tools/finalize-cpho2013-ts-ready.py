from pathlib import Path
import json,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/master-v1');q=json.loads((B/'assembly-master-input.json').read_text('utf8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,q):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
editions=[]
for lang in ['ko','en']:
 out=B/f'editions/CPhO_2013_TS_{lang.upper()}.pdf';assembly=out.with_suffix('.assembly-qa.json');a=json.loads(assembly.read_text('utf8'))
 assert a['passed']and a['sha256']==sha(out)and len(a['pages'])==11
 reviewed=json.loads((B/f'visual-review-{lang}.json').read_text('utf8'));assert len(reviewed['pages'])==11
 pages=[]
 for index,r in enumerate([r for r in q['proofs']if r['language']==lang],1):
  assert sha(r['pdf'])==r['sha256'];ev=r['evidence']
  def ref(key,selector=None):
   p=Path(ev[key]);value=dict(path=str(p),sha256=sha(p))
   if selector:value['selector']=selector
   return value
  row=dict(page=index,source_page=r['source_page'],pdf=r['pdf'],sha256=r['sha256'],source_scan_qa=ref('generic_qa'),actual_style_qa=ref('source_qa','actual_new_prose_style_audit'),actual_outline_qa=ref('source_qa','new_actual_outline_audit'),independent_math_union_qa=ref('math_union'))
  if lang=='ko':row['hangul_visibility_qa']=ref('source_qa','independent_hangul_visibility')
  pages.append(row);v=reviewed['pages'][index-1];assert v['reviewed']and v['source_math_atoms_reviewed']and v['proof_sha256']==r['sha256']and v['page']==index and v['source_page']==r['source_page']
 reviewed['sha256']=sha(out);save(B/f'visual-review-{lang}.json',reviewed)
 editions.append(dict(output=str(out),sha256=sha(out),bytes=out.stat().st_size,pages=11,language=lang,proofs=pages,assembly_qa=str(assembly),visual_review=str(B/f'visual-review-{lang}.json')))
for s in q['authoring_snapshots']:
 for rel,digest in s['files'].items():assert sha(Path(s['root'])/rel)==digest
final=dict(status='READY',year=2013,kind='TS',source_original_sha256=q['source_original_sha256'],source_audited_sha256=q['source_audited_sha256'],editions=editions,authoring_snapshots=q['authoring_snapshots'],original_math_retyped=False,original_math_resampled=False,original_math_y_changed=False,translated_point_sizes_fitted=False,added_editorial_notes=0)
save(B/'CPhO_2013_TS_READY.json',final);print('FINAL_READY',json.dumps([{k:r[k]for k in ['output','sha256','bytes','pages','language']}for r in editions]),flush=True)

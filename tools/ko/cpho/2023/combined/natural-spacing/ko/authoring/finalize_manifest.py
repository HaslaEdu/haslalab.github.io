"""Attach the narrow revision evidence; PDF bytes remain unchanged."""
from pathlib import Path
import json,hashlib,shutil
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 path=HERE/'editions/CPhO_2023_Combined_KO.ready.json';q=json.loads(path.read_text('utf8'));proof=HERE/'pages/CPhO_2023_p11_KO_natural.pdf';audit=proof.with_suffix('.independent.json')
 for row in q['independent_original_input_moved_math_audits']:
  if row['page']==11:row.update(path=str(audit),sha256=sha(audit))
 old=Path(q['visual_review']);visual=json.loads(old.read_text('utf8'))
 for row in visual['pages']:
  if row['page']==11:row.update(proof_sha256=sha(proof),reviewed=True,review='Projected original CID spacing repair; expanded clause and full-page comparison. Same native font/GID/size/paint/y; no change outside the affected line.')
 target=HERE/'visual-ko.json';target.write_text(json.dumps(visual,ensure_ascii=False,indent=2),'utf8');q['visual_review']=str(target)
 q['assembly_verification']='All 36 combined pages have the expected exact 4x RGB SHA in fresh MuPDF processes and zero changed pixels in separate Poppler 144dpi runs. Other35 original proof files and the complete36p EN edition retain their original bytes.'
 snapshot=Path(q['authoring_snapshotroot'])
 repo=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab')
 for relative in ('tools/ko/cpho/2023/natural-inline-groups.json','tools/ko/cpho/2023/original-labels/source-survey.json','tools/ko/cpho/2023/original-labels/label-plan.json','tmp/original-style-repair/2023/slots.json','tmp/original-style-repair/2023/CPhO_2023_p11_KO_proof.qa.json'):
  dest=snapshot/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(repo/relative,dest);q['authoring_snapshot_sha256'][relative]=sha(dest)
 for name in ('audit-inventory.json','audit-page11.json','engine-manifest.json'):
  dest=snapshot/name;shutil.copy2(HERE/name,dest);q['authoring_snapshot_sha256'][name]=sha(dest)
 shutil.copy2(Path(__file__),snapshot/'finalize_manifest.py');q['authoring_snapshot_sha256']['finalize_manifest.py']=sha(snapshot/'finalize_manifest.py')
 q['private_authored_space_revision']['metadata_finalizer_sha256']=sha(__file__)
 path.write_text(json.dumps(q,ensure_ascii=False,indent=2),'utf8')
 for relative,digest in q['authoring_snapshot_sha256'].items():assert sha(snapshot/relative)==digest,(relative,digest)
 assert sha(q['output'])==q['sha256']
 print(json.dumps(dict(manifest=str(path),manifest_sha256=sha(path),output=q['output'],sha256=q['sha256'],bytes=q['bytes'],snapshot=str(snapshot),authoring_files=len(q['authoring_snapshot_sha256'])),ensure_ascii=False,indent=2),flush=True)
 return q
if __name__=='__main__':run()

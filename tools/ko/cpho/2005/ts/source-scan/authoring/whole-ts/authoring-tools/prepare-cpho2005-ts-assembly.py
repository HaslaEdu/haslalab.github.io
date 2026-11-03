"""Freeze only complete, reviewed bilingual source4–16 proofs and evidence."""
from pathlib import Path
import json,hashlib,shutil,ast
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
R=Path('D:/CodexBuilds');OUT=B/'master-v1'
PIN=R/'Hasla-publish-20261031/tools';SHARED=B.parents[1]/'cpho2013/TS/tools'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):
 p.parent.mkdir(parents=True,exist_ok=True);raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8')
 if p.exists():assert p.read_bytes()==raw,('Frozen manifest already differs',str(p))
 else:p.write_bytes(raw)
def cp(p,q):
 p=Path(p);q.parent.mkdir(parents=True,exist_ok=True)
 if q.exists():assert sha(p)==sha(q),('Frozen source already differs',str(q))
 else:shutil.copy2(p,q)
 assert sha(p)==sha(q)
assert sha(B/'inputs/CPhO_2005_Chinese_original.pdf')=='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f'
assert sha(PIN/'pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
proofs=[]
for number in range(4,17):
 visual=json.loads((B/f'proofs/page{number:02}-visual-review.json').read_text('utf8'))
 assert visual['all_two_renderer_source_nonlanguage_ink_and_math_RGB_changes_zero']and visual['real_native_math_omission_negative_rejected']
 for lang in ['ko','en']:
  source=B/f'proofs/{lang}/page{number:02}.pdf';digest=sha(source)
  review=next(r for r in visual['records']if r['language']==lang)
  assert review['proof_sha256']==digest and review['fresh_Poppler144_full_page_visually_reviewed']
  assert review['preview_sha256']==sha(source.parent/f'page{number:02}-preview.png'),('Reviewed preview differs',number,lang)
  expected=['source-qa','generic-scan-qa','poppler-qa','math-union-qa','actual-CID-widths','publication-style-qa']+(['hangul-visibility']if lang=='ko'else[])
  evidence={}
  for name in expected:
   p=source.with_suffix('.'+name+'.json');v=json.loads(p.read_text('utf8'))
   assert v.get('passed',v.get('flagged_components')==0),(number,lang,name)
   if name=='source-qa':assert v['final_sha256']==digest and v['actual_final_math_single_native_source_controls']['RGB_errors']==0
   if name=='poppler-qa':assert v['proof_sha256']==digest and v['actual_math_RGB_errors']==0
   if name=='hangul-visibility':assert v['sha256']==digest and v['flagged_components']==0
   q=OUT/f'evidence/{lang}/page{number:02}-{name}.json';cp(p,q);evidence[name]=str(q)
  assert review['source_qa_sha256']==sha(source.with_suffix('.source-qa.json'))
  assert review['poppler_qa_sha256']==sha(source.with_suffix('.poppler-qa.json'))
  destination=OUT/f'proofs/{lang}/page{number:02}.pdf';cp(source,destination)
  cp(source.with_suffix('.composition.json'),OUT/f'evidence/{lang}/page{number:02}-composition.json')
  proofs.append(dict(source_page=number,language=lang,pdf=str(destination),sha256=digest,evidence=evidence))
snap=OUT/'authoring-whole-ts'
for name in ['authoring','inputs','row-hints','source-renders']:
 for p in(B/name).rglob('*'):
  if p.is_file()and p.suffix in ['.json','.png']:cp(p,snap/name/p.relative_to(B/name))
for p in B.glob('*.json'):cp(p,snap/'source-type-and-weight'/p.name)
for p in(B/'proofs').glob('*.json'):cp(p,snap/'visual-and-negative-evidence'/p.name)
for lang in ['ko','en']:
 for p in(B/f'proofs/{lang}').glob('page*-preview.png'):cp(p,snap/f'final-page-previews/{lang}'/p.name)
 for p in(B/f'proofs/{lang}').glob('page*.composition.json'):cp(p,snap/f'final-composition/{lang}'/p.name)
for p in(B/'tools').glob('*.py'):cp(p,snap/'page-tools'/p.name)
for p in R.glob('*cpho2005*.py'):cp(p,snap/'authoring-tools'/p.name)
cp(R/'assemble-scanned-proof-edition.py',snap/'authoring-tools/assemble-scanned-proof-edition.py')
font_provenance=B.parents[1]/'official-hans-fonts/fonts-provenance.json'
if font_provenance.exists():cp(font_provenance,snap/'font-provenance'/font_provenance.name)
# Resolve exactly the local Python dependency graph; never copy donor fonts,
# private textbooks, the private problem bank, or unrelated project inputs.
roots=[B/'tools',PIN,SHARED,R];todo=['cpho_2005_ts_compose','cpho_2005_ts_qa','cpho_2005_ts_poppler_qa','pdf_hangul_visibility','pdf_memory_gate'];seen=set()
while todo:
 name=todo.pop();p=next((root/(name+'.py')for root in roots if(root/(name+'.py')).is_file()),None)
 if p is None or p in seen:continue
 seen.add(p);cp(p,snap/'resolved-engine'/p.name)
 for node in ast.walk(ast.parse(p.read_text('utf8'))):
  if isinstance(node,ast.Import):todo.extend(a.name.split('.')[0]for a in node.names)
  elif isinstance(node,ast.ImportFrom)and node.module:todo.append(node.module.split('.')[0])
snapshot=dict(name='whole-ts',root=str(snap),files={p.relative_to(snap).as_posix():sha(p)for p in sorted(snap.rglob('*'))if p.is_file()})
master=dict(year=2005,kind='TS',source_original_sha256=sha(B/'inputs/CPhO_2005_Chinese_original.pdf'),source_audited_sha256=sha(B/'inputs/CPhO_2005_Chinese_original.pdf'),proofs=sorted(proofs,key=lambda r:(r['language'],r['source_page'])),authoring_snapshots=[snapshot])
save(OUT/'assembly-master-input.json',master)
for lang in ['ko','en']:
 save(OUT/f'assembly-{lang}-input.json',dict(output=str(OUT/f'editions/CPhO_2005_TS_{lang.upper()}.pdf'),proofs=[r for r in master['proofs']if r['language']==lang]))
print('FROZEN_COMPLETE_BILINGUAL_TS',len(proofs),'PROOFS',len(snapshot['files']),'AUTHORING_FILES',flush=True)

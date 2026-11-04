from pathlib import Path
import sys,json,hashlib
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');T=B/'TS'
sys.path[:0]=[str(T/'engine'),str(B/'engine'),'D:/CodexBuilds']
from pdf_memory_gate import page_worker
from cpho2003_ts_actual_donor_style import audit as style
from cpho2003_ts_native_ink import audit as native
import cpho_2003_ts_qa,cpho_2003_ts_poppler_qa
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for n in [8,10]:
 p=T/f'proofs/en/page{n:02}.pdf'
 with page_worker():
  style(n,'en',output_override=p.with_suffix('.final-actual-donor-style.json'))
  native(n,'en',output_override=p.with_suffix('.original-source-native-ink-v2.json'))
  native(n,'en',output_override=p.with_suffix('.final-source-native-ink.json'))
modules=[]
for name,m in sorted(sys.modules.items()):
 p=getattr(m,'__file__',None)
 if p and Path(p).is_file()and any(Path(p).resolve().is_relative_to(v.resolve())for v in [T/'engine',B/'engine']):
  p=Path(p);modules.append(dict(module=name,path=str(p.resolve()),sha256=sha(p),bytes=p.stat().st_size))
plans=[];reports=[]
for n in range(4,11):
 for lang in ['ko','en']:
  p=T/f'proofs/{lang}/page{n:02}.pdf';layout=T/f'authoring/proof-inputs/{lang}/page{n:02}-layout.json';comp=json.loads(p.with_suffix('.composition.json').read_text('utf8'));sty=json.loads(p.with_suffix('.final-actual-donor-style.json').read_text('utf8'));assert sha(layout)==comp['layout_sha256']==sty['layout_sha256']
  for suffix,key in [('.source-qa.json','final_sha256'),('.poppler-qa.json','proof_sha256'),('.final-actual-donor-style.json','proof_sha256'),('.final-source-native-ink.json','output_sha256')]:
   q=json.loads(p.with_suffix(suffix).read_text('utf8'));assert q['passed']and q[key]==sha(p)
  plans.append(dict(language=lang,source_page=n,proof_sha256=sha(p),layout_path=layout.relative_to(T/'authoring').as_posix(),layout_sha256=sha(layout),actual_build_layout_sha256=comp['layout_sha256'],actual_style_layout_sha256=sty['layout_sha256']))
  reports.append(dict(language=lang,source_page=n,proof_sha256=sha(p),source_QA_sha256=sha(p.with_suffix('.source-qa.json')),Poppler_QA_sha256=sha(p.with_suffix('.poppler-qa.json')),actual_style_sha256=sha(p.with_suffix('.final-actual-donor-style.json')),native_ink_sha256=sha(p.with_suffix('.final-source-native-ink.json'))))
for name,q in [('proof-inputs-map.json',dict(source_sha256=sha(B/'inputs/CPhO_2003_Chinese_original.pdf'),exact_actual_build_and_style_layouts_per_proof=True,approved_other12_proof_bytes_unchanged=True,layouts=plans)),('final-auditor-import-closure.json',dict(source_sha256=sha(B/'inputs/CPhO_2003_Chinese_original.pdf'),all14_current_positive_style_and_native_reports_verified=True,only_two_English_successors_reaudited_others_retain_exact_previously_audited_proof_and_report_bytes=True,actual_two_English_auditor_import_closure=modules,modules=modules,proofs=reports))]:
 p=T/'authoring'/name;assert not p.exists();p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
print('ALL14_CURRENT_RECEIPTS_BOUND_TO_EXACT_ACTUAL_PROOF_SPECIFIC_INPUT_PLANS',flush=True)

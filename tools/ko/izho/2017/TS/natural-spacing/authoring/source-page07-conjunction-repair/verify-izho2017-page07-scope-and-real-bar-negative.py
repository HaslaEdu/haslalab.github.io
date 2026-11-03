from pathlib import Path
import sys,json,hashlib,pymupdf as f,pikepdf,numpy as np
from PIL import Image
B=Path(__file__).resolve().parents[1];E=B/'engine';F=B/'natural/2017/TS';O=B/'page07-conjunction-repair';sys.path[:0]=[str(E),'D:/CodexBuilds/Hasla-publish-20261031/tools'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups,_traces,_font_programs
from izho_2017_independent_original_math_geometry import audit
from izho_2017_page07_original_conjunction_order import audit as order_audit
P=F/'plans/page07.json';p=json.loads(P.read_text('utf8'));proof=F/'page07.pdf';before=sha(proof);assert before=='685e9c601a8e1350244b39dc775a94e57a6b366c484ef6e092e0b95094033db4';pins=json.loads((O/'other13-approved-proof-pins.json').read_text('utf8'));assert all(sha(F/f'page{int(n):02}.pdf')==digest for n,digest in pins.items())
oldpng=F/'history/rejected-07-62f558aa0d342c1c/page07-preview.png';newpng=F/'page07-preview.png'
with page_worker():
 a=np.asarray(Image.open(oldpng).convert('RGB'));b=np.asarray(Image.open(newpng).convert('RGB'));assert a.shape==b.shape;changed=np.any(a!=b,axis=2);allowed=np.zeros(changed.shape,bool)
 for x0,y0,x1,y1 in[(111,150,459,174.1),(111,409,459,440.2)]:allowed[int(y0*2):int(np.ceil(y1*2)),int(x0*2):int(np.ceil(x1*2))]=True
 outside=int((changed&~allowed).sum());assert outside==0,outside;scope=dict(prior_rejected_proof_sha256='949b9ec26d254bf4fec971f6a9de8e419c6ab746a6d08d19092fe1dc621f2521',current_proof_sha256=before,renderer='independent external Poppler144dpi',three_source_problem_rows_only=True,changed_pixels_outside_three_problem_rows=outside,all_other_page_pixels_including_caption51_4_lower92CIDdisplay_and_scores_unchanged=True,other13_approved_proof_hashes_unchanged=True,passed=True);(O/'actual-source-row-scope-zero-outside.json').write_text(json.dumps(scope,indent=2)+'\n','utf8')
 positive=audit(P,report_override=O/'independent-original-math-positive.json');assert positive['passed'];assert order_audit(P)['passed'];inv=inspect_inline_groups(str(proof),1);program=p['reviewed_source2017_complete_original_expression_program_isolation']['programs'][1];forms=[v for v in inv['forms']if v['original_raw_sha256']==program['Form_raw_sha256']];assert len(forms)==1;chosen=forms[0];paths=[v for v in chosen['own_vector_paths']if f.Rect(v['rect']).height<2 and f.Rect(v['rect']).width>3];assert len(paths)==2;bar=paths[0];bad=O/'page07-only-one-original-equation10-fraction-rule-shifted-1pt.pdf'
 with pikepdf.open(proof)as doc:
  node=doc.pages[0]
  for index in chosen['path']:
   inst=list(pikepdf.parse_content_stream(node))[index];assert str(inst.operator)=='Do';node=node.Resources.XObject[inst.operands[0]]
  ops=list(pikepdf.parse_content_stream(node));start=min(bar['operator_indices']);end=max(bar['operator_indices'])+1;ops[start:end]=[pikepdf.ContentStreamInstruction([],pikepdf.Operator('q')),pikepdf.ContentStreamInstruction([1,0,0,1,1,0],pikepdf.Operator('cm'))]+ops[start:end]+[pikepdf.ContentStreamInstruction([],pikepdf.Operator('Q'))];node.write(pikepdf.unparse_content_stream(ops));doc.save(bad,compress_streams=False)
 with pikepdf.open(proof)as a,pikepdf.open(bad)as b:assert _font_programs(a.pages[0])==_font_programs(b.pages[0])
 with f.open(proof)as a,f.open(bad)as b:assert _traces(a[0])==_traces(b[0]),'Only one original fraction path changes; all native CID/font/GID/point/paint/X/Y must remain exact'
 error=None;negative=None
 try:negative=audit(P,final_override=bad,report_override=O/'one-native-fraction-rule-only-negative-audit.json')
 except (AssertionError,ValueError)as caught:error=type(caught).__name__+': '+str(caught)
 assert error is not None or not negative['passed'];assert sha(proof)==before;assert all(sha(F/f'page{int(n):02}.pdf')==digest for n,digest in pins.items());report=dict(original_source_sha256=p['original_english_source_sha256'],positive_proof_sha256=before,positive_proof_unmodified=True,actual_single_fraction_rule_only_bad_PDF_sha256=sha(bad),source_original_fraction_rule_before_mutation=bar,all_native_CID_font_GID_point_paint_X_Y_identical=True,all_original_font_programs_unchanged=True,strict_original_program_geometry_rejected_bad_PDF=True,failure=error,negative_audit=negative,other13_approved_proofs_unmodified=True,passed=True);(O/'one-native-fraction-rule-only-negative-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');print('C17_P7_ONLY_THREE_PROBLEM_ROWS_CHANGED_ALL_OTHER_PIXELS_AND13PROOFS_EXACT_REAL_BAR_ONLY_BAD_PDF_REJECTED',before,flush=True)

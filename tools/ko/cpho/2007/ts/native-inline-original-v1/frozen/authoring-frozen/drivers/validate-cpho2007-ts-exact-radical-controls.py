from pathlib import Path
import sys,json,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS');sys.path.insert(0,str(B/'engine'))
from pdf_memory_gate import page_worker
from cpho2007_complete_vector_motion import audit
import pymupdf as f,pikepdf
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();proof=B/'natural/2007/ko/page06.pdf';source=B/'natural/2007/ko/page06-immutable-input.pdf';positive=json.loads(proof.with_suffix('.audit.json').read_text('utf8'));assert positive['passed']and positive['output_sha256']==sha(proof)
qa=json.loads(proof.with_suffix('.qa.json').read_text('utf8'));out=B/'evidence/negative-controls-v2';records=[]
with page_worker():
 bad=out/'page06-KO-rejected-original-radical-stroke-color.pdf';assert not bad.exists()
 with pikepdf.open(proof)as pdf:
  ops=list(pikepdf.parse_content_stream(pdf.pages[0]));index=positive['native_graphics_motion_audit']['selected_native_math_groups'][0]['target_operator_indices'][0];assert str(ops[index].operator)=='m'
  ops.insert(index,pikepdf.ContentStreamInstruction([1,0,0],pikepdf.Operator('RG')));pdf.pages[0].Contents=pdf.make_stream(pikepdf.unparse_content_stream(ops));pdf.save(bad,compress_streams=False)
 try:audit(source,bad,qa['native_shifts'])
 except AssertionError as e:
  message=str(e);assert'Original radical stroke style changed'in message
 else:raise AssertionError('A changed original radical color was not rejected')
 records.append(dict(control='Actually recolor one original native radical stroke while preserving its original path operands and geometry.',fixture=str(bad),fixture_sha256=sha(bad),rejected=True,reason=message))
 bad=out/'page06-KO-rejected-unselected-graphic-dot.pdf';assert not bad.exists()
 with f.open(proof)as doc:doc[0].draw_line(f.Point(8,8),f.Point(10,8),color=(0,0,0),width=.5);doc.save(bad,garbage=0,deflate=False)
 _,q=audit(source,bad,qa['native_shifts']);assert q['changed_nonselected_native_graphical_pixels']>0
 records.append(dict(control='Actually add an unrelated graphic in the top margin, beyond every selected native radical path.',fixture=str(bad),fixture_sha256=sha(bad),rejected=True,nonselected_graphics_changed_pixels=q['changed_nonselected_native_graphical_pixels'],report=q))
path=out/'page06-exact-radical-negative-control-manifest.json';assert not path.exists();path.write_text(json.dumps(dict(reference_positive_proof=str(proof),reference_positive_sha256=sha(proof),all_rejected=all(r['rejected']for r in records),controls=records),ensure_ascii=False,indent=2)+'\n','utf8');print('EXACT_ORIGINAL_RADICAL_NEGATIVE_CONTROLS',len(records),True,sha(path),flush=True)

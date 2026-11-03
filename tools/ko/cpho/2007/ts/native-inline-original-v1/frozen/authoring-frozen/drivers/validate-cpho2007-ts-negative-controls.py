from pathlib import Path
import sys,json,hashlib,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS');sys.path.insert(0,str(B/'engine'))
from pdf_memory_gate import page_worker
import pymupdf as f
from cpho2007_ts_runtime import configure,baseline_path
from pdf_native_inline_reposition import reposition_inline
from pdf_moved_native_ink import audit_moved_native_ink
from pdf_new_prose_native_text_overlap import audit as prose_collision
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();out=B/'evidence/negative-controls-v2';out.mkdir(parents=True,exist_ok=True);records=[]
proof=B/'natural/2007/en/page10.pdf';audit=json.loads(proof.with_suffix('.audit.json').read_text('utf8'));assert audit['passed']and audit['output_sha256']==sha(proof)
configure(10,'en')
from cpho_natural_spacing_qa import original_native_glyphs
native=original_native_glyphs(2007,'en',10);composition=json.loads(proof.with_suffix('.qa.json').read_text('utf8'))
target=next(g for g in native if g['c']=='E'and'Times New Roman Italic'in g['font']and 285<g['origin'][1]<310)
with page_worker():
 missing=out/'page10-EN-rejected-erased-original-electric-field-E.pdf'
 if missing.exists():q=json.loads(missing.with_suffix('.rejection.json').read_text('utf8'));assert not q['passed']
 else:
  raw,_=reposition_inline(proof,1,erased_glyphs=[target]);missing.write_bytes(raw)
  q=audit_moved_native_ink(baseline_path(10,'en'),10,missing,shifts=composition['native_shifts'],erased_glyphs=composition['erased_hangul_glyphs'],protected_glyphs=native)
  assert not q['passed'];missing.with_suffix('.rejection.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
 records.append(dict(control='Actually erase one original native E in display equation(1), without retyping any mathematics.',fixture=str(missing),fixture_sha256=sha(missing),must_reject=True,rejected=not q['passed'],native_physical_glyph=target,report=str(missing.with_suffix('.rejection.json'))))
 overlap=out/'page10-EN-rejected-new-prose-over-original-electric-field-E.pdf';assert not overlap.exists()
 with f.open(proof)as doc:
  face=next(font[4]for font in doc[0].get_fonts()if font[3].startswith('SimSun')and font[4].startswith('Translation'))
  doc[0].insert_text(tuple(target['origin']),'MMMM',fontname=face,fontsize=target['size'],color=(0,0,0));doc.save(overlap,garbage=0,deflate=False)
 q=prose_collision(overlap,native_glyphs=native,shifts=composition['native_shifts']);assert not q['passed']and q['dark_prose_pixels_over_native_text']>0
 overlap.with_suffix('.rejection.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
 records.append(dict(control='Actually paint additional embedded SimSun prose through retained original native E; native CID/font/point/Y remain present.',fixture=str(overlap),fixture_sha256=sha(overlap),must_reject=True,rejected=not q['passed'],collision_pixels=q['dark_prose_pixels_over_native_text'],report=str(overlap.with_suffix('.rejection.json'))))
prior=B/'natural/2007/ko/page05.audit.json';old=json.loads(prior.read_text('utf8'));assert not old['passed']and not old['original_native_expression_relative_geometry']['passed']
snapshot=out/'real-rejected-page05-KO-original-comma-geometry.audit.json';assert not snapshot.exists();shutil.copy2(prior,snapshot)
records.append(dict(control='Real rejected proof: native A moved but its original fullwidth comma remained at the old source x. The complete-expression relative-geometry audit must reject it.',rejected=True,proof_sha256=old['output_sha256'],report=str(snapshot),report_sha256=sha(snapshot)))
path=out/'negative-control-manifest.json';assert not path.exists();path.write_text(json.dumps(dict(reference_positive_proof=str(proof),reference_positive_sha256=sha(proof),all_rejected=all(r['rejected']for r in records),controls=records),ensure_ascii=False,indent=2)+'\n','utf8');print('CPHO2007_TS_NEGATIVE_CONTROLS',len(records),all(r['rejected']for r in records),sha(path),flush=True)

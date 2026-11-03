from pathlib import Path
import hashlib,json,sys,importlib.util,pikepdf
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups,reposition_inline,_traces
from pdf_original_text_ops import glyph_key
import pymupdf as f
spec=importlib.util.spec_from_file_location('izho2016_actual_geometry','D:/CodexBuilds/audit-izho2016-actual-expression-geometry.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();F=B/'natural/2016/TS';out=B/'natural/2016-actual-geometry-negative-controls';out.mkdir(exist_ok=True)
source=F/'page03.pdf';before=sha(source);plan=json.loads((F/'plans/page03.json').read_text('utf8'))
with page_worker():
 positive=mod.audit(3,report=out/'page03-positive.json');assert positive['passed']
 inv=inspect_inline_groups(str(source),1);forms=[v for v in inv['forms']if v.get('own_vector_paths')and f.Rect(v['native_page_bbox']).width<100 and 620<v['native_page_bbox'][1]<740];assert forms
 chosen=forms[0];paths=[v for v in chosen['own_vector_paths']if f.Rect(v['rect']).height<2 and f.Rect(v['rect']).width>3];assert paths;bar=paths[0]
 bad=out/'page03-one-original-fraction-bar-shifted-1pt.pdf'
 with pikepdf.open(source)as doc:
  node=doc.pages[0]
  for index in chosen['path']:
   item=list(pikepdf.parse_content_stream(node))[index];assert str(item.operator)=='Do';node=node.Resources.XObject[item.operands[0]]
  ops=list(pikepdf.parse_content_stream(node));indices=bar['operator_indices'];start=min(indices);end=max(indices)+1
  ops[start:end]=[pikepdf.ContentStreamInstruction([],pikepdf.Operator('q')),pikepdf.ContentStreamInstruction([1,0,0,1,1,0],pikepdf.Operator('cm'))]+ops[start:end]+[pikepdf.ContentStreamInstruction([],pikepdf.Operator('Q'))]
  node.write(pikepdf.unparse_content_stream(ops));doc.save(bad,compress_streams=False)
 negative=mod.audit(3,override=bad,report=out/'page03-one-fraction-rule-negative.json');assert not negative['passed']
assert sha(source)==before
score_source=F/'page08.pdf';score_before=sha(score_source)
with page_worker():
 positive_score=mod.audit(8,report=out/'page08-positive.json');assert positive_score['passed']
 with f.open(score_source)as doc:gs=[g for g in _traces(doc[0])if g['c']=='1'and g['origin'][0]>470 and 100<g['origin'][1]<150]
 assert gs;g=gs[0];badscore=out/'page08-one-original-score-glyph-shifted-1pt.pdf'
 raw,moveqa=reposition_inline(str(score_source),1,erased_glyphs=[],shifts=[dict(glyphs=[dict(g,gid=g['trace_gid'])],dx=1.)]);badscore.write_bytes(raw)
 negative_score=mod.audit(8,override=badscore,report=out/'page08-one-score-glyph-negative.json');assert not negative_score['passed']and negative_score['stationary_glyph_errors']
assert sha(score_source)==score_before
result=dict(source_sha256=plan['original_english_source_sha256'],positive_proofs_unmodified=True,page03_positive_sha256=before,page08_positive_sha256=score_before,fraction_rule_only_negative_sha256=sha(bad),score_glyph_only_negative_sha256=sha(badscore),actual_fraction_rule_negative_rejected=not negative['passed'],actual_score_glyph_negative_rejected=not negative_score['passed'],native_guard_sha256=sha(B/'engine/pdf_native_inline_reposition.py'),passed=True)
(out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');print('IZHO2016_ACTUAL_BAD_PDF_CONTROLS_REJECTED',json.dumps(result),flush=True)

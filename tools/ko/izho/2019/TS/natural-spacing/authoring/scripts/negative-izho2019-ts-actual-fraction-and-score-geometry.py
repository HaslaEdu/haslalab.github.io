from pathlib import Path
import sys,json,hashlib,importlib.util,pikepdf,pymupdf as f
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions');E=B/'engine';F=B/'natural/2019/TS';sys.path[:0]=[str(E),'D:/CodexBuilds/Hasla-publish-20261031/tools'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups,reposition_inline,_traces,_font_programs
spec=importlib.util.spec_from_file_location('izho2019_actual_original_geometry','D:/CodexBuilds/audit-izho2019-ts-actual-expression-geometry.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
out=B/'natural/2019-actual-geometry-negative-controls';out.mkdir(exist_ok=True);source=F/'page08.pdf';before=sha(source);assert before=='fa1b9b18f0e4cac5e0c71c4e9b1bdd77b92c44f58ab5828b123fac96f27e35ab';plan=json.loads((F/'plans/page08.json').read_text('utf8'));binding=next(v for v in plan['reviewed_complete_original_mathematical_form_bindings']if abs(v['original_form_bbox'][0]-113.11)<.001 and abs(v['original_form_bbox'][1]-642.6599146605563)<.001)
with page_worker():
 positive=mod.audit(8,report=out/'page08-positive.json');assert positive['passed'];inv=inspect_inline_groups(str(source),1);forms=[v for v in inv['forms']if v['original_raw_sha256']==binding['original_form_program_sha256']];assert len(forms)==1;chosen=forms[0];paths=[v for v in chosen['own_vector_paths']if f.Rect(v['rect']).height<2 and f.Rect(v['rect']).width>3];assert len(paths)==1;bar=paths[0];bad=out/'page08-only-original-N-over-Sl-fraction-rule-shifted-1pt.pdf'
 with pikepdf.open(source)as doc:
  node=doc.pages[0]
  for index in chosen['path']:
   inst=list(pikepdf.parse_content_stream(node))[index];assert str(inst.operator)=='Do';node=node.Resources.XObject[inst.operands[0]]
  ops=list(pikepdf.parse_content_stream(node));start=min(bar['operator_indices']);end=max(bar['operator_indices'])+1;ops[start:end]=[pikepdf.ContentStreamInstruction([],pikepdf.Operator('q')),pikepdf.ContentStreamInstruction([1,0,0,1,1,0],pikepdf.Operator('cm'))]+ops[start:end]+[pikepdf.ContentStreamInstruction([],pikepdf.Operator('Q'))];node.write(pikepdf.unparse_content_stream(ops));doc.save(bad,compress_streams=False)
 with pikepdf.open(source)as a,pikepdf.open(bad)as b:assert _font_programs(a.pages[0])==_font_programs(b.pages[0])
 with f.open(source)as a,f.open(bad)as b:assert _traces(a[0])==_traces(b[0]),'A fraction-rule-only mutation must preserve every native CID/point/position/paint'
 negative=mod.audit(8,override=bad,report=out/'page08-original-fraction-rule-only-negative.json');assert not negative['passed'];assert sha(source)==before
 score=F/'page12.pdf';score_before=sha(score);assert score_before=='4356408a4daa9735383c2097a0afe625eb6ca0b0453922fdf59a2a1da5571a27';positive_score=mod.audit(12,report=out/'page12-positive.json');assert positive_score['passed']
 with f.open(score)as doc:gs=[g for g in _traces(doc[0])if g['c']=='3'and g['font']=='TimesNewRomanPSMT'and g['origin'][0]>470 and 80<g['origin'][1]<100];assert len(gs)==1;g=gs[0]
 badscore=out/'page12-only-original-score-digit3-shifted-1pt.pdf';raw,qa=reposition_inline(str(score),1,erased_glyphs=[],shifts=[dict(glyphs=[dict(g,gid=g['trace_gid'])],dx=1.)]);badscore.write_bytes(raw)
 with pikepdf.open(score)as a,pikepdf.open(badscore)as b:assert _font_programs(a.pages[0])==_font_programs(b.pages[0])
 negative_score=mod.audit(12,override=badscore,report=out/'page12-original-score-only-negative.json');assert not negative_score['passed']and negative_score['stationary_glyph_errors'];assert sha(score)==score_before
 result=dict(original_source_sha256=plan['original_english_source_sha256'],page08_positive_sha256=before,page12_positive_sha256=score_before,positive_proofs_unmodified=True,only_original_fraction_rule_bad_PDF_sha256=sha(bad),only_original_score_glyph_bad_PDF_sha256=sha(badscore),fraction_rule_only_control_preserves_every_native_CID_font_point_position_paint=True,actual_fraction_rule_only_negative_rejected=True,actual_score_glyph_only_negative_rejected=True,original_font_programs_unchanged=True,native_guard_sha256=sha(E/'pdf_native_inline_reposition.py'),passed=True);(out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');print('SOURCE2019_ACTUAL_ORIGINAL_FRACTION_RULE_ONLY_AND_SCORE_ONLY_BAD_PDFS_REJECTED',json.dumps(result),flush=True)

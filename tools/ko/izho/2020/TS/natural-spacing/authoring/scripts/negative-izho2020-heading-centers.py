from pathlib import Path
import sys,json,hashlib
import pymupdf as fitz
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2020-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from heading_source_alignment_audit import audit
from pdf_native_inline_reposition import reposition_inline,_traces
f=B/'natural/2020/TS';plan=f/'plans/page05.json';source=f/'page05.pdf';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();before=sha(source)
assert audit(plan)['passed']
with fitz.open(source)as doc:heading=[g for g in _traces(doc[0])if g['c'].strip()and abs(g['origin'][1]-629.88)<.01]
assert len(heading)>5;raw,q=reposition_inline(source,1,shifts=[dict(glyphs=heading,dx=-8.)]);assert q['passed']and q['font_programs_unchanged']and q['original_image_streams_unchanged']and not q['native_glyph_mismatches']
folder=B/'2020/heading-alignment-negative';folder.mkdir(exist_ok=True);target=folder/'page05-heading-left8pt.pdf';report=folder/'page05-heading-left8pt.audit.json';target.write_bytes(raw)
r=audit(plan,target,report);bad=[x for x in r['rows']if not x['passed']];assert not r['passed']and len(bad)==1 and abs(bad[0]['center_error_pt']+8.)<.001 and sha(source)==before
summary=dict(passed=True,canonical_proof_sha256=before,publication_pdf_unmodified=True,all_original_font_glyph_point_and_baseline_metadata_retained=True,original_encoded_images_and_diagram_geometry_retained=True,actual_heading_shift_pt=-8.,independent_source_center_rejected=True,raw_negative_audit=str(report),native_move_qa=q)
(folder/'regression.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n','utf8');print('REAL_MISALIGNED_HEADING_NEGATIVE_REJECTED',bad[0]['center_error_pt'])
p=f/'plans/page06.json';assert audit(p)['passed'];d=json.loads(p.read_text('utf8'));d['centered_lines']=[v for v in d['centered_lines']if abs(v['baseline']-370.8)>.02];clone=folder/'page06-one-subtitle-intent-omitted.json';clone.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
qa=audit(clone,f/'page06.pdf',folder/'page06-one-subtitle-intent-omitted.audit.json');missing=[v for v in qa['original_bold_prose_heading_coverage']['rows']if not v['passed']];assert not qa['passed']and len(missing)==1 and missing[0]['source_at']==[20,0]and all(v['passed']for v in qa['rows'])
(folder/'coverage-regression.json').write_text(json.dumps(dict(passed=True,canonical_proof_sha256=sha(f/'page06.pdf'),publication_pdf_unmodified=True,only_one_subtitle_alignment_intent_omitted=True,all_remaining_actual_centers_correct=True,original_source_heading_inventory_rejected_missing_intent=True,missing_source_at=[20,0],raw_negative_audit=str(folder/'page06-one-subtitle-intent-omitted.audit.json')),ensure_ascii=False,indent=2)+'\n','utf8');print('MISSING_SUBTITLE_CENTER_CHECK_REJECTED')

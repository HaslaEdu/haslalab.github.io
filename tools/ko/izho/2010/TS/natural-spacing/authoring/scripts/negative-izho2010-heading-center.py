from pathlib import Path
import sys,json,hashlib
import pymupdf as fitz
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from heading_source_alignment_audit import audit
from pdf_native_inline_reposition import reposition_inline,_traces
plan=B/'natural/2010/TS/plans/page04.json';source=plan.parents[1]/'page04.pdf';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();before=sha(source)
with fitz.open(source)as doc:heading=[g for g in _traces(doc[0])if g['c'].strip()and abs(g['origin'][1]-662.8800048828125)<.01]
assert len(heading)>5;raw,q=reposition_inline(source,1,erased_glyphs=[],shifts=[dict(glyphs=heading,dx=-8.)]);assert q['passed']and q['font_programs_unchanged']and q['original_image_streams_unchanged']and not q['native_glyph_mismatches']
folder=B/'2010/heading-alignment-negative';folder.mkdir(exist_ok=True);target=folder/'page04-heading-left8pt.pdf';report=folder/'page04-heading-left8pt.audit.json';target.write_bytes(raw)
r=audit(plan,target,report);bad=[r for r in r['rows']if not r['passed']];assert not r['passed']and len(bad)==1 and abs(bad[0]['center_error_pt']+8.)<.001 and sha(source)==before
summary=dict(passed=True,canonical_proof_sha256=before,publication_pdf_unmodified=True,all_original_font_glyph_point_and_baseline_metadata_retained=True,original_encoded_images_and_diagram_geometry_retained=True,actual_heading_shift_pt=-8.,independent_source_center_rejected=True,raw_negative_audit=str(report),native_move_qa=q)
(folder/'regression.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n','utf8');print('REAL_MISALIGNED_HEADING_NEGATIVE_REJECTED',bad[0]['center_error_pt'])

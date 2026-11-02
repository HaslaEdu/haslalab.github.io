from pathlib import Path
import sys,json,hashlib,importlib.util
import pymupdf as fitz
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/heading-alignment-v1')
spec=importlib.util.spec_from_file_location('heading','D:/CodexBuilds/review-izho-heading-alignment.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
from pdf_native_inline_reposition import reposition_inline,_traces
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
canonical=B/'IZhO_2012_T_KO/page02.pdf';before=sha(canonical)
row=next(r for r in h.load(B.parent/'published-izho-heading-detail-20261102.json')['headings']if r['file']=='IZhO_2012_T_KO.pdf'and r['published_page']==2 and r['source_at']==[6,0])
with fitz.open(canonical)as doc:gs=h.selected_heading(doc[0],row)
center=h.original_center(row);assert abs(h.nonspace_center(gs)-center)<=.001
raw,move=reposition_inline(canonical,1,shifts=[dict(glyphs=gs,dx=-8)],text_shift_mode='ctm')
assert move['passed']and move['font_programs_unchanged']and move['original_image_streams_unchanged']and move['native_vector_path_bytes_preserved']and not move['native_glyph_mismatches']
out=B/'analysis-only-negative';out.mkdir(exist_ok=True);(out/'page02-heading-left8pt.pdf').write_bytes(raw)
with fitz.open(stream=raw,filetype='pdf')as doc:actual=h.selected_heading(doc[0],row)
error=h.nonspace_center(actual)-h.original_center(row);assert abs(error+8)<=.001 and sha(canonical)==before
q=dict(passed=True,publication_pdf_unmodified=True,independent_original_source_center_rejected=True,native_metadata_and_other_graphics_retained=True,canonical_proof_sha256=before,source_original_sha256=sha(row['source_path']),source_original_page=row['source_page'],source_at=row['source_at'],actual_heading_shift_pt=-8,rejected_center_error_pt=error,native_move_qa=move)
h.save(B/'heading-negative-control.json',q);print('ACTUAL_8PT_NEGATIVE_REJECTED',error,flush=True)

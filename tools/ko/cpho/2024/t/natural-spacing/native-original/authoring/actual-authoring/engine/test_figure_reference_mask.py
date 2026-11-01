"""A real unrelated final-PDF drawing must fail the independent label mask."""
import json
import pymupdf as fitz
from cpho2024_natural import BASE,sha
from cpho2024_figure_label_qa import audit
from pdf_memory_gate import page_worker
source=BASE/'T/figure-language/page01-KO.pdf';digest=sha(source)
out=BASE/'T/final-label-mask-regression';out.mkdir(exist_ok=True)
negative=out/'analysis-new-unrelated-stroke.pdf'
with fitz.open(source)as doc:
 doc[0].draw_rect(fitz.Rect(30,30,31,31),color=None,fill=(0,0,0),width=0,overlay=True)
 doc.save(negative,garbage=0,deflate=False)
with page_worker():
 try:audit(1,'KO',analysis_target=negative,analysis_report=out/'negative.audit.json')
 except ValueError:pass
 else:raise AssertionError('An unrelated new drawing escaped the independent final-label mask')
q=json.loads((out/'negative.audit.json').read_text('utf8'))
assert not q['passed']and q['qa_mode']=='analysis-only-negative-clone'
assert q['original_body_glyph_metadata_unchanged']and q['all_original_font_programs_unchanged']and q['all_original_image_palette_ICC_mask_graphs_unchanged']
assert q['pixel_audit']['added_ink_outside_independent_actual_font_reference']>0
assert q['pixel_audit']['changed_pixels_outside_source_words_new_labels_and_reviewed_symbol_motion']>0
assert sha(source)==digest
report=dict(passed=True,publication_pdf_unmodified=True,source_canonical_proof_sha256=digest,negative_preserves_all_original_glyphs_fonts_images_and_ctms=True,negative_unrelated_actual_new_drawing_rejected=True,negative_added_ink_outside_reference=q['pixel_audit']['added_ink_outside_independent_actual_font_reference'],negative_changed_pixels_outside_reviewed_language=q['pixel_audit']['changed_pixels_outside_source_words_new_labels_and_reviewed_symbol_motion'])
(out/'regression.json').write_text(json.dumps(report,indent=2)+'\n','utf8');print('FINAL_LABEL_MASK_REAL_PDF_NEGATIVE PASS',flush=True)

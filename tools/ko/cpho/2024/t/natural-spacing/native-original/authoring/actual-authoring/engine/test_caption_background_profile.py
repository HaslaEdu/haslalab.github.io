"""Real PDF negative: a new black stroke at a caption edge must be rejected."""
from pathlib import Path
import json,pymupdf as fitz
from cpho2024_natural import BASE,sha
from cpho2024_body_qa import audit
from pdf_memory_gate import page_worker
source=BASE/'T/pages/page03-KO.pdf';before=sha(source);out=BASE/'T/source-caption-background-regression';out.mkdir(exist_ok=True)
with page_worker():
 positive=audit(3,'KO');assert positive['passed']and positive['source_caption_background_profile']['passed']
 # This exact source-caption sample was a pale original bitmap-edge pixel.
 # A real non-text paint, preserving all existing text/CIDs/fonts, must never
 # be classified as that original blank background.
 dest=out/'analysis-new-black-stroke.pdf'
 with fitz.open(source)as doc:
  doc[0].draw_rect(fitz.Rect(414.5,291.75,414.75,292),color=None,fill=(0,0,0),width=0,overlay=True);doc.save(dest,garbage=0,deflate=False)
 report=out/'negative.audit.json'
 try:audit(3,'KO',analysis_target=dest,analysis_report=report)
 except ValueError:pass
 else:raise AssertionError('A real new native drawing stroke was silently accepted')
 negative=json.loads(report.read_text('utf8'));assert not negative['passed']and negative['qa_mode']=='analysis-only-negative-clone'
 assert negative['original_native_ink']['passed']and negative['original_fonts_retained']and negative['original_images_retained']
 assert negative['verified_new_prose_over_native_geometry_pixels']>0
 assert negative['original_graphics_motion']['changed_nonselected_native_graphical_pixels']>0
 assert sha(source)==before
 evidence=dict(passed=True,source_canonical_proof_sha256=before,publication_pdf_unmodified=True,positive_original_pale_background_samples=positive['source_caption_background_profile']['proved_original_pale_caption_background_samples'],negative_preserves_all_original_font_programs_and_native_CID_geometry=True,negative_real_new_graphic_stroke_rejected=True,negative_actual_drawing_overlap_samples=negative['verified_new_prose_over_native_geometry_pixels'],negative_nonselected_graphic_changes=negative['original_graphics_motion']['changed_nonselected_native_graphical_pixels'])
 (out/'regression.json').write_text(json.dumps(evidence,indent=2)+'\n','utf8');print('CAPTION_BACKGROUND_REAL_PDF_REGRESSION PASS',flush=True)

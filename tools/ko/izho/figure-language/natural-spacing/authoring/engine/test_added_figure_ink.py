"""Real unrelated drawings must fail both bitmap and native figure overlays."""
import json
import pymupdf as fitz
from audit_figure_labels import audit,B,sha
from pdf_memory_gate import page_worker
out=B/'negative-controls';out.mkdir(exist_ok=True);rows=[]
for year,page in [(2010,2),(2011,3)]:
 source=B/f'{year}/T/page{page:02}.pdf';before=sha(source);negative=out/f'{year}-unrelated-stroke.pdf';report=out/f'{year}-negative.audit.json'
 with fitz.open(source)as doc:
  doc[0].draw_rect(fitz.Rect(30,30,31,31),color=None,fill=(0,0,0),width=0,overlay=True);doc.save(negative,garbage=0,deflate=False)
 with page_worker():
  try:audit(year,page,analysis_target=negative,analysis_report=report)
  except ValueError:pass
  else:raise AssertionError('An unrelated actual drawing was accepted')
 q=json.loads(report.read_text('utf8'));assert not q['passed']and q['qa_mode']=='analysis-only-negative-clone'
 assert q['original_body_glyph_font_GID_point_paint_and_y_preserved']and q['all_original_font_programs_retained']and q['all_original_image_palette_ICC_mask_graphs_and_CTMs_retained']and q['original_native_ink']['passed']
 assert q['pixel_audit']['added_ink_outside_independent_actual_font_reference']>0 and q['pixel_audit']['final_changed_outside_reviewed_words_caption_digits_and_reference']>0 and sha(source)==before
 rows.append(dict(year=year,page=page,canonical_proof_sha256=before,all_original_glyphs_fonts_images_and_caption_positions_retained=True,negative_added_ink_outside_reference=q['pixel_audit']['added_ink_outside_independent_actual_font_reference'],real_extra_drawing_rejected=True,publication_pdf_unmodified=True,passed=True))
(out/'regression.json').write_text(json.dumps(dict(rows=rows,passed=True),indent=2)+'\n','utf8');print('REAL_FIGURE_OVERLAY_NEGATIVES PASS',flush=True)

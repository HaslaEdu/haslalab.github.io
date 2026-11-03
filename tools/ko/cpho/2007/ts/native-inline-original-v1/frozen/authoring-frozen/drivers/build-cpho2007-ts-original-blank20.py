from pathlib import Path
import sys,json,hashlib,subprocess,os
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS');sys.path.insert(0,str(B/'engine'))
from cpho2007_ts_authoring import Page
from pdf_memory_gate import page_worker
import pikepdf,pymupdf as f
from pdf_original_text_ops import glyph_key
from pdf_native_inline_reposition import _traces
from cpho_natural_full_qa import native_font_programs
from izho_natural_spacing_qa import semantic
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=Page(20);assert not p.slots;p.save('Full original source page20 viewed at144dpi: blank final sheet with only the native folio20. No prose exists to translate. Retain the exact native page and folio, font programs, dimensions, original paths/images and all source graphical objects. Both languages therefore share the source page unchanged.')
source=B/'inputs/CPhO_2007_Chinese_original.pdf';source_sha=sha(source);assert source_sha=='2e30b56ab9274363686cbf5bc1ef7532dcf579e0703de2c01098b003ab70cdd9'
with page_worker():
 for lang in ['ko','en']:
  target=B/f'natural/2007/{lang}/page20.pdf';target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists()
  with pikepdf.open(source)as src,pikepdf.Pdf.new()as dst:dst.pages.append(src.pages[19]);dst.save(target,compress_streams=False)
  with f.open(source)as src,f.open(target)as dst:
   before=_traces(src[19]);after=_traces(dst[0]);assert before==after
   a=src[19].get_pixmap(matrix=f.Matrix(4,4),alpha=False);b=dst[0].get_pixmap(matrix=f.Matrix(4,4),alpha=False);assert a.samples==b.samples
   dims=list(src[19].rect);assert src[19].rect==dst[0].rect
  assert native_font_programs(source,20)==native_font_programs(target,1)
  with pikepdf.open(source)as src,pikepdf.open(target)as dst:
   content=lambda p:b'\n'.join(s.read_bytes()for s in(p.Contents if isinstance(p.Contents,pikepdf.Array)else[p.Contents]))
   assert content(src.pages[19])==content(dst.pages[0]);content_sha=hashlib.sha256(content(dst.pages[0])).hexdigest()
  target.with_suffix('.audit.json').write_text(json.dumps(dict(passed=True,source_page=20,language=lang,source_sha256=source_sha,output_sha256=sha(target),source_blank_page_preserved=True,source_folio20_glyphs=before,native_font_programs_unchanged=True,decoded_content_streams_sha256=content_sha,unchanged_decoded_native_content=True,fresh_MuPDF_4x_RGB_pixels_equal=True,dimensions=dims,visual_review_required=True),ensure_ascii=False,indent=2)+'\n','utf8')
  print('EXACT_ORIGINAL_BLANK_FINAL_PAGE',lang,sha(target),flush=True)

"""Additional independent original-math union, actual CID and Hangul checks."""
from pathlib import Path
from io import BytesIO
import sys,json,hashlib,argparse
import pikepdf,pymupdf as fitz,numpy as np
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from pdf_memory_gate import page_worker
from pdf_scanned_translation_ink_qa import render,summary
from pdf_hangul_visibility import audit as hangul_visibility
from pdf_original_text_ops import widths
from izho_new_prose_outline_qa import trace_font_resources
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
def union(control,final,prose,output):
 with pikepdf.open(control)as pdf:
  page=pdf.pages[0]
  if '/OriginalRasterReset'not in page.Resources.ExtGState:raise ValueError('Expected exact original replay resource missing')
  page.Resources.ExtGState.OriginalRasterReset.BM=pikepdf.Name.Multiply
  last=list(page.Contents)[-1].read_bytes()
  if not last.startswith(b'Q\nq\n/OriginalRasterReset gs'):raise ValueError('Unexpected math replay stream')
  page.Contents=pdf.make_stream(b'q\n'+last);pdf.save(output,compress_streams=False)
 expected=render(output);actual=render(final);new=render(prose)
 missing=(expected<160)&(actual>240);overlap=(expected<180)&(new<180)
 return dict(reference=str(output),reference_sha256=sha(output),method='Independent original-image replay ink union. Only the QA reference reset blend mode is Multiply, so opaque white scan padding cannot hide earlier source math. Actual final PDF unchanged.',original_math_ink_expected_pixels=int((expected<160).sum()),missing_original_replayed_math_ink=summary(missing,4),new_prose_overlap_independent_math_union=summary(overlap,4),passed=not missing.any()and not overlap.any())
def actual_widths(path):
 checked=0;bad=[];cache={}
 with pikepdf.open(path)as pdf,fitz.open(path)as doc:
  glyphs,_=trace_font_resources(pdf,doc[0])
  for glyph in glyphs:
   name=glyph['font_alias']
   if not name.startswith(('/TSHeader','/TSScanBody'))or glyph['c'].isspace():continue
   font=pdf.pages[0].Resources.Font[name]
   if str(font.get('/Subtype'))!='/Type0'or str(font.get('/Encoding'))!='/Identity-H':raise ValueError('Unexpected authored prose encoding')
   if str(font.DescendantFonts[0].get('/CIDToGIDMap','/Identity'))!='/Identity':raise ValueError('Unexpected CID/GID mapping')
   if name not in cache:cache[name]=widths(font)
   mapping,default=cache[name];value=mapping.get(glyph['gid'],default);checked+=1
   if value is None or value<=0:bad.append(dict(character=glyph['c'],gid=glyph['gid'],font=name,actual_CID_width=value))
 return dict(actual_used_new_prose_CID_widths_checked=checked,nonpositive_actual_CID_widths=bad,passed=checked>0 and not bad)
def check(number,lang):
 path=B/f'proofs/{lang}/page{number:02}.pdf'
 source=path.with_suffix('.source-qa.json');record=json.loads(source.read_text('utf8'))
 poppler=path.with_suffix('.poppler-qa.json');pop=json.loads(poppler.read_text('utf8'))
 assert record['passed']and pop['passed']and record['final_sha256']==pop['proof_sha256']==sha(path)
 with page_worker():
  math=union(path.with_suffix('.math-control.pdf'),path,path.with_suffix('.prose-only.pdf'),path.with_suffix('.independent-math-union.pdf'))
  math.update(source_sha256=record['source_sha256'],source_page=number,proof_sha256=sha(path),language=lang)
  save(path.with_suffix('.math-union-qa.json'),math);assert math['passed'],math
  widths_qa=actual_widths(path);save(path.with_suffix('.actual-CID-widths.json'),widths_qa);assert widths_qa['passed']
  if lang=='ko':
   visibility=hangul_visibility(path);save(path.with_suffix('.hangul-visibility.json'),visibility);assert visibility['flagged_components']==0
  # Lossless schema adapter of the independently checked actual PDF font
  # program, point, baseline, GID paint-count and calibrated stroke audit.
  style=record['actual_prose_font_point_baseline_and_paint'];assert style['passed']and style['glyph_paints_checked']>0 and not style['errors']
  adapted=dict(source_report=str(source),source_report_sha256=sha(source),selector='actual_prose_font_point_baseline_and_paint',proof_sha256=sha(path),actual_new_prose_glyph_paints_checked=style['glyph_paints_checked'],style_font_size_baseline_or_stroke_failures=style['errors'],actual_CID_widths=widths_qa,passed=style['passed']and widths_qa['passed'])
  save(path.with_suffix('.publication-style-qa.json'),adapted)
 print('FINAL_PUBLICATION_CHECKS',number,lang,'PASS',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('pages',nargs='+',type=int);args=p.parse_args()
 for number in args.pages:
  for lang in ['ko','en']:check(number,lang)

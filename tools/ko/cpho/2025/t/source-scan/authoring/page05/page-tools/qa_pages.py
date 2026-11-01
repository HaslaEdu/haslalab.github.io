"""Independent final pixel/program/prose/math-style QA for reviewed 2025 pages."""
from pathlib import Path
import sys,json,hashlib,argparse,re
import numpy as np,pymupdf as fitz,pikepdf
from compose_pages import BASE,B,ROOT,SOURCE,sha
from pdf_scanned_translation_ink_qa import audit_scan_page,render,summary
from pdf_memory_gate import page_worker

def math_visibility(control,final,prose,output):
 # The ordinary original recipe is untouched. This REFERENCE ONLY changes the
 # newly added reset's blend mode to Multiply, isolates the replay stream, and
 # thus unions all independent original glyph ink without opaque JPEG padding
 # hiding an earlier formula. Exact image/clip/CTM/scale bytes remain unchanged.
 with pikepdf.open(control)as pdf:
  page=pdf.pages[0]
  if '/OriginalRasterReset'not in page.Resources.ExtGState:raise ValueError('Expected exact original replay resource missing')
  page.Resources.ExtGState.OriginalRasterReset.BM=pikepdf.Name.Multiply
  last=list(page.Contents)[-1].read_bytes()
  if not last.startswith(b'Q\nq\n/OriginalRasterReset gs'):raise ValueError('Unexpected math replay stream, cannot isolate reference')
  page.Contents=pdf.make_stream(b'q\n'+last)
  pdf.save(output,compress_streams=False)
 expected=render(output);actual=render(final);new=render(prose)
 missing=(expected<160)&(actual>240);overlap=(expected<180)&(new<180)
 return dict(reference=str(output),reference_sha256=sha(output),method='Independent original-image clip replay union: only QA-reference reset BM Multiply avoids opaque white padding hiding earlier exact source mathematical ink. Actual final PDF unchanged.',
  original_math_ink_expected_pixels=int((expected<160).sum()),missing_original_replayed_math_ink=summary(missing,4),new_prose_overlap_independent_math_union=summary(overlap,4),passed=not missing.any()and not overlap.any())

def actual_style(target,meta):
 from io import BytesIO
 from collections import Counter
 from fontTools.ttLib import TTFont
 from izho_new_prose_outline_qa import trace_font_resources
 import compose_pages as comp
 raw=Path(meta['font']['subset']).read_bytes();metric=fitz.Font(fontbuffer=raw)
 from pdf_original_text_ops import widths
 with pikepdf.open(target)as pdf:declared,default=widths(pdf.pages[0].Resources.Font['/ScanBody'])
 quantization=[]
 with TTFont(BytesIO(raw))as font:
  cmap=font.getBestCmap();expected=[];invalid=[];upm=font['head'].unitsPerEm
  for part in meta['prose_placements']:
   x,y=part['point'];size=part['size']
   for match in re.finditer(r' +|[^ ]+',part['text']):
    word=match.group()
    if word.isspace():x+=len(word)*size/4;continue
    word_x=x
    for c in word:
     name=cmap.get(ord(c));gid=-1 if name is None else font.getGlyphID(name);actual_width=declared.get(gid,default)
     if name is None or font['hmtx'][name][0]<=0 or actual_width is None or actual_width<=0:invalid.append(dict(character=c,row=part['row']))
     source_width=font['hmtx'][name][0]*1000/upm
     difference=source_width-actual_width
     if difference<-.001 or difference>1.001:invalid.append(dict(character=c,row=part['row'],reason='Declared font CID width not source-hmtx integer quantization',source_width=source_width,actual_width=actual_width))
     if abs(difference)>.001:quantization.append(dict(character=c,gid=gid,source_hmtx_width_1000=source_width,actual_pdf_CID_width=actual_width))
     expected.append(dict(c=c,gid=gid,x=word_x,y=y,size=size,stroke=part['stroke'],row=part['row']))
     word_x+=actual_width*size/1000
    x+=metric.text_length(word,fontsize=size)
 with pikepdf.open(target)as pdf,fitz.open(target)as doc:
  actual,_=trace_font_resources(pdf,doc[0]);actual=[g for g in actual if g['font_alias']=='/ScanBody'and not g['c'].isspace()];traces=doc[0].get_texttrace();errors=[];remaining=list(actual)
  for e in expected:
   matches=[(i,g)for i,g in enumerate(remaining)if g['c']==e['c']and g['gid']==e['gid']and abs(g['size']-e['size'])<.001 and abs(g['origin'][0]-e['x'])<=.001 and abs(g['origin'][1]-e['y'])<=.001]
   if len(matches)!=1:errors.append(dict(reason='Expected actual original-point-size/prose GID/origin not unique',expected=e,matches=len(matches)));continue
   i,g=matches[0];remaining.pop(i)
   if g['font_program_sha256']!=meta['font']['subset_sha256']or g['render_type']!=2:errors.append(dict(reason='Actual new font program or Tr2 paint differs',glyph=g,expected=e))
   stroke=[t for t in traces if t['type']==1 and abs(t['size']-e['size'])<.001 and any(cp==ord(e['c'])and gid==e['gid']and abs(p[0]-e['x'])<=.001 and abs(p[1]-e['y'])<=.001 for cp,gid,p,bbox in t['chars'])]
   if not stroke or any(abs(t['linewidth']-e['stroke'])>1e-5 for t in stroke):errors.append(dict(reason='Actual source-calibrated stroke differs',expected=e,actual=[t['linewidth']for t in stroke]))
 return dict(actual_new_glyphs_checked=len(expected),actual_CID_advances_checked=True,source_hmtx_to_integer_PDF_width_quantization=quantization,word_origins_verified_from_authored_positions_and_actual_CID_widths=True,source_font_program_expected=meta['font']['subset_sha256'],invalid_actual_character_advances=invalid,unmatched_actual_glyphs=remaining,style_size_baseline_gid_or_stroke_errors=errors,passed=not invalid and not remaining and not errors)

def audit(number,lang):
 out=BASE/'proofs'/lang;target=out/f'page{number:02d}.pdf';meta=json.loads(target.with_suffix('.composition.json').read_text('utf8'));plan=json.loads(Path(meta['plan']).read_text('utf8'))
 if meta['proof_sha256']!=sha(target)or meta['plan_sha256']!=sha(meta['plan']):raise ValueError('Proof or reviewed plan changed')
 records=meta['math_replay']['atoms']
 result=audit_scan_page(SOURCE,number,target,meta['math_control'],meta['prose_reference'],language_erase_rects=[rect for r in plan['rows']for rect in r['erase_rects']],
  new_prose_rects=[[r['left']-1,r['baseline']-r['point_size']*1.3,r['right']+1,r['baseline']+r['point_size']*.4]for r in meta['placements']],
  original_inline_math_rects=[a['rect']for r in plan['rows']for a in r['atoms']],moved_inline_math_rects=[a['destination_rect']for a in records],
  protected_source_rects=plan['protected_source_display_and_figure_rects'],replayed_math_records=records,reviewed_blank_records=plan.get('reviewed_blank_background_rects',[]))
 result['actual_new_prose_style']=actual_style(target,meta)
 result['independent_replayed_math_visibility']=math_visibility(meta['math_control'],target,meta['prose_reference'],target.with_suffix('.math-union-reference.pdf'))
 import pdf_new_prose_outlines as outlines
 original=outlines.PREFIXES
 try:outlines.PREFIXES=('/ScanBody',);result['new_actual_prose_outlines']=outlines.audit(target)
 finally:outlines.PREFIXES=original
 if lang=='ko':
  from pdf_hangul_visibility import audit as visibility
  result['hangul_visibility']=visibility(target)
 result['passed']=result['passed']and result['actual_new_prose_style']['passed']and result['independent_replayed_math_visibility']['passed']and result['new_actual_prose_outlines']['passed']and not result.get('hangul_visibility',{}).get('flagged_components')
 target.with_suffix('.qa.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
 print('QA',number,lang,result['passed'],result['outside_declared_language_and_math_motion'],result['independent_replayed_math_visibility'],flush=True);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('page',type=int);p.add_argument('language',choices=['ko','en']);a=p.parse_args()
 with page_worker():audit(a.page,a.language)

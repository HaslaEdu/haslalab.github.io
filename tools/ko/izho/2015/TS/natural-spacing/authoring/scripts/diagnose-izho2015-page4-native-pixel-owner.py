from pathlib import Path
import sys,json,pikepdf,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2015-complete-solutions');F=B/'natural/2015/TS';O=B/'natural/2015-page04-exact-native-pixel-owner';O.mkdir(exist_ok=True);sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import _traces
from pdf_moved_native_ink import source_outline_reference
with page_worker():
 crop=O/'original-input-same-integer-crop.pdf'
 with pikepdf.open(F/'page04.old-source.pdf')as doc:
  h=float(doc.pages[0].MediaBox[3]);doc.pages[0].CropBox=pikepdf.Array([340,h-780,390,h-748]);doc.save(crop,compress_streams=False)
 with f.open(crop)as doc:
  page=doc[0];candidates=[g for g in _traces(page)if g['c'].strip()and g['trace_gid']>=0 and -30<g['origin'][0]<80 and -25<g['origin'][1]<60 and'Noto'not in g['font']];owners=[]
  for g in candidates:
   mask,qa=source_outline_reference(page,[g],scale=4)
   if mask is not None and mask[62,115]:owners.append(g);print('ORIGINAL_NATIVE_OUTLINE_OWNS_RAW_PIXEL',g,flush=True)
  (O/'outline-owners.json').write_text(json.dumps(dict(source_crop=str(crop),same_integer_crop=[340,748,390,780],original_pixel=[368.75,763.5],cropped_pixel=[115,62],source_native_candidates=len(candidates),owners=owners),ensure_ascii=False,indent=2)+'\n','utf8')

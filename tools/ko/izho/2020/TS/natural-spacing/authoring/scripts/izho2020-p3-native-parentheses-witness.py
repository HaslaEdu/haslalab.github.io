from pathlib import Path
import sys,json,hashlib
import pikepdf,pymupdf as fitz
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2020-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_native_inline_reposition import _traces
from pdf_native_glyph_raster_witness import audit,replay
from pdf_moved_native_ink import audit_moved_native_ink
from pdf_memory_gate import page_worker
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
f=B/'natural/2020/TS';source=f/'page03.old-source.pdf';target=f/'page03.pdf';out=f/'page03-parentheses-native-reference';out.mkdir(exist_ok=True);rows=[]
with page_worker():
 for index,(x,xx,y)in enumerate([(121.68,93.12,503.64),(127.68,99.12,743.64)],1):
  with fitz.open(source)as a,fitz.open(target)as b:
   g=next(g for g in _traces(a[0])if g['c']==')'and abs(g['origin'][0]-x)<.001 and abs(g['origin'][1]-y)<.001)
   actual=next(g for g in _traces(b[0])if g['c']==')'and abs(g['origin'][0]-xx)<.001 and abs(g['origin'][1]-y)<.001)
  dx=actual['origin'][0]-g['origin'][0];cid=audit(source,1,target,g,dx=dx,scale=4)
  raw,details=replay(source,1,g,dx=dx);(out/f'original-cid-{index}.pdf').write_bytes(raw)
  for src,dst in [(source,out/f'source-crop-{index}.pdf'),(target,out/f'final-crop-{index}.pdf')]:
   with pikepdf.open(src)as doc:
    h=float(doc.pages[0].MediaBox[3]);doc.pages[0].CropBox=pikepdf.Array([80,h-(int(y)+10),145,h-(int(y)-15)]);doc.save(dst,compress_streams=False)
  with fitz.open(out/f'source-crop-{index}.pdf')as doc:cropped=next(r for r in _traces(doc[0])if r['c']==')'and abs(r['origin'][0]-(x-80))<.001)
  scales={str(s):audit_moved_native_ink(out/f'source-crop-{index}.pdf',1,out/f'final-crop-{index}.pdf',shifts=[dict(glyphs=[cropped],dx=dx)],protected_glyphs=[cropped],scale=s)for s in [8,12]}
  rows.append(dict(source_glyph=g,actual_target_glyph=actual,requested_dx=dx,native_CID_reference=cid,svg_reference_scales=scales,passed=cid['passed']and all(v['passed']for v in scales.values())))
q=dict(kind='multiple-original-native-CID-references-v1',proof_sha256=sha(target),proof_unmodified=True,original_language_source_sha256=sha(B/'2020/source/IZhO_2020_TS.pdf'),source_page=3,rows=rows,passed=all(r['passed']for r in rows),scope='Two exact original TNR12pt right parentheses in table labels (2) and (14). Exact original encoded-CID/font/paint/y replay at4x, independent SVG8x/12x zero missing ink. All other protected glyphs retain ordinary zero-loss SVG checks; delivered PDF unchanged.')
(out/'witness.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('TWO_NATIVE_PARENTHESES',q['passed'],[r['native_CID_reference']['native_reference_dark_pixels']for r in rows]);assert q['passed']

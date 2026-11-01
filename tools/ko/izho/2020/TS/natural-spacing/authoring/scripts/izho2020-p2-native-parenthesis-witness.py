from pathlib import Path
import sys,json,hashlib
import pikepdf,pymupdf as fitz
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2020-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_native_inline_reposition import _traces
from pdf_native_glyph_raster_witness import audit,replay
from pdf_moved_native_ink import audit_moved_native_ink
from pdf_memory_gate import page_worker
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
f=B/'natural/2020/TS';source=f/'page02.old-source.pdf';target=f/'page02.pdf';out=f/'parenthesis-native-reference';out.mkdir(exist_ok=True)
with fitz.open(source)as a,fitz.open(target)as b:
 g=next(g for g in _traces(a[0])if g['c']==')'and abs(g['origin'][0]-121.68)<.001 and abs(g['origin'][1]-431.88)<.001)
 actual=next(g for g in _traces(b[0])if g['c']==')'and abs(g['origin'][0]-93.12)<.001 and abs(g['origin'][1]-431.88)<.001)
dx=actual['origin'][0]-g['origin'][0]
with page_worker():
 cid=audit(source,1,target,g,dx=dx,scale=4)
 raw,details=replay(source,1,g,dx=dx);(out/'original-cid-only.pdf').write_bytes(raw)
 for src,dst in [(source,out/'source-crop.pdf'),(target,out/'final-crop.pdf')]:
  with pikepdf.open(src)as doc:
   h=float(doc.pages[0].MediaBox[3]);doc.pages[0].CropBox=pikepdf.Array([80,h-440,140,h-420]);doc.save(dst,compress_streams=False)
 with fitz.open(out/'source-crop.pdf')as doc:cropped=next(r for r in _traces(doc[0])if r['c']==')'and abs(r['origin'][0]-41.68)<.001 and abs(r['origin'][1]-11.88)<.001)
 scales={str(s):audit_moved_native_ink(out/'source-crop.pdf',1,out/'final-crop.pdf',shifts=[dict(glyphs=[cropped],dx=dx)],protected_glyphs=[cropped],scale=s)for s in [8,12]}
q=dict(proof_sha256=sha(target),proof_unmodified=True,source_glyph=g,actual_target_glyph=actual,requested_dx=dx,native_CID_reference=cid,svg_reference_scales=scales,passed=cid['passed']and all(v['passed']for v in scales.values()),scope='One original TimesNewRomanPSMT12pt right parenthesis in table label (7). All source CIDs/fonts/paint/y retained. The one4x unhinted SVG edge sample is independently checked against the exact original encoded CID at its actual requested x;8x/12x SVG references also required zero missing ink.')
(out/'witness.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(q,ensure_ascii=False));assert q['passed']

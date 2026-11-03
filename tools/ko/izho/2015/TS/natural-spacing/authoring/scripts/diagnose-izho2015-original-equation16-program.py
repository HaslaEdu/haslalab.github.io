"""Exact original encoded complete display equation; no proof edits or thresholds."""
from pathlib import Path
import sys,json,hashlib,math,subprocess,pikepdf,pymupdf as f,numpy as np
from PIL import Image
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2015-complete-solutions');F=B/'natural/2015/TS';O=B/'natural/2015-page04-original-equation16-program';O.mkdir(exist_ok=True);sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import _traces,reposition_inline,inspect_inline_groups
from pdf_moved_native_ink import audit_moved_native_ink
from pdf_original_text_ops import glyph_key
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();source=B/'2015/source/IZhO_2015_TS.pdf';old=F/'page04.old-source.pdf';proof=F/'page04.pdf';pin=sha(proof);R=[130,750,515,790];POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
def rgb(path,scale,renderer,out):
 if renderer=='MuPDF':
  with f.open(path)as doc:p=doc[0].get_pixmap(matrix=f.Matrix(scale,scale),clip=f.Rect(R),colorspace=f.csRGB,alpha=False);return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()
 x,y,w,h=map(lambda v:int(v*scale),[R[0],R[1],R[2]-R[0],R[3]-R[1]])
 subprocess.run([POP,'-f','1','-singlefile','-r',str(scale*72),'-x',str(x),'-y',str(y),'-W',str(w),'-H',str(h),'-png',str(path),str(out)],capture_output=True,check=True)
 with Image.open(out.with_suffix('.png'))as im:return np.asarray(im.convert('RGB')).copy()
with page_worker():
 assert sha(source)=='c1bc32cc38c3f3b65121439f41feee3a8bcb48dcce1a41e14b16ba177eccbcde'
 with f.open(source)as doc:
  all_rows=_traces(doc[3]);gs=[g for g in all_rows if g['c'].strip()and f.Rect(R).contains(f.Point(g['origin']))];assert all(g['font']in['Cambria Math','Times New Roman']for g in gs);assert len(gs)>30
  keys={glyph_key(g)for g in gs};erase=[g for g in all_rows if g['c'].strip()and glyph_key(g)not in keys]
 inv=inspect_inline_groups(source,4);assert not inv['forms']
 raw,guard=reposition_inline(source,4,erased_glyphs=erase);ref=O/'exact-original-equation16-CIDs-clips-rules-paint-only.pdf';ref.write_bytes(raw)
 with f.open(ref)as doc:actual=[g for g in _traces(doc[0])if g['c'].strip()];assert {glyph_key(g)for g in actual}==keys
 measures=[]
 for scale in[4,8,12]:
  for renderer in['MuPDF','Poppler']:
   a=rgb(ref,scale,renderer,O/f'original-reference-{renderer}-{scale}');b=rgb(proof,scale,renderer,O/f'actual-proof-{renderer}-{scale}');assert a.shape==b.shape
   ink=a.min(axis=2)<255;dark=a.min(axis=2)<32;r=dict(renderer=renderer,scale=scale,reference_original_program_nonwhite_pixels=int(ink.sum()),reference_original_program_deep_dark_pixels=int(dark.sum()),missing_original_native_program_pixels=int((dark&(b.min(axis=2)>=220)).sum()),actual_reference_nonwhite_RGB_errors=int((ink&np.any(a!=b,axis=2)).sum()));r['passed']=r['reference_original_program_deep_dark_pixels']>0 and r['missing_original_native_program_pixels']==0 and r['actual_reference_nonwhite_RGB_errors']==0;measures.append(r);print('EXACT_ORIGINAL_EQUATION16_NATIVE_PROGRAM',r,flush=True)
 for inp,out in[(old,O/'original-input-same-integer-crop.pdf'),(proof,O/'actual-proof-same-integer-crop.pdf')]:
  with pikepdf.open(inp)as doc:h=float(doc.pages[0].MediaBox[3]);doc.pages[0].CropBox=pikepdf.Array([R[0],h-R[3],R[2],h-R[1]]);doc.save(out,compress_streams=False)
 with f.open(O/'original-input-same-integer-crop.pdf')as doc:cropped=[g for g in _traces(doc[0])if g['c'].strip()and -1<g['origin'][0]<R[2]-R[0]+1 and -1<g['origin'][1]<R[3]-R[1]+1];assert len(cropped)==len(gs)
 svg={str(s):audit_moved_native_ink(O/'original-input-same-integer-crop.pdf',1,O/'actual-proof-same-integer-crop.pdf',protected_glyphs=cropped,scale=s)for s in[4,8,12]}
 q=dict(kind='source2015-complete-original-equation16-native-program-v1',original_source_sha256=sha(source),source_page=4,original_input_page_sha256=sha(old),proof_sha256=pin,proof=str(proof),proof_unmodified=True,delivered_pdf_modified=False,mathematics_retyped=False,source_font_programs_substituted=False,complete_original_display_expression_glyphs=gs,source_native_reference_guard=guard,source_reference_sha256=sha(ref),source_reference_file=str(ref),source_math_expression_point_sizes=sorted({g['size']for g in gs}),same_integer_page_crop=R,native_original_program_reference_measurements=measures,svg_reference_scales=svg,passed=all(m['passed']for m in measures)and all(svg[s]['passed']and svg[s]['newly_missing_native_ink_pixels']==0 for s in['8','12']))
 assert sha(proof)==pin;(O/'witness.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('COMPLETE_LITERAL_SOURCE_EQ16_PROGRAM_WITNESS',q['passed'],len(gs),sha(O/'witness.json'),flush=True)

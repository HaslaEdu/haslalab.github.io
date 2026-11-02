"""Independent original encoded CID controls; delivered PDFs are never edited."""
from pathlib import Path
import sys,json,hashlib,math,subprocess,gc
import pymupdf as f,pikepdf,numpy as np
from PIL import Image
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_native_inline_reposition import _traces,reposition_inline
from pdf_native_glyph_promote import promote_native_glyphs
from pdf_moved_native_ink import audit_moved_native_ink
from pdf_original_text_ops import glyph_key
from pdf_memory_gate import page_worker
POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def crop_rgb(path,rect,scale,renderer,output):
 if renderer=='MuPDF':
  with f.open(path)as d:
   p=d[0].get_pixmap(matrix=f.Matrix(scale,scale),clip=f.Rect(rect),colorspace=f.csRGB,alpha=False)
   return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()
 x0,y0=math.floor(rect[0]*scale),math.floor(rect[1]*scale);x1,y1=math.ceil(rect[2]*scale),math.ceil(rect[3]*scale)
 subprocess.run([POP,'-f','1','-singlefile','-r',str(scale*72),'-x',str(x0),'-y',str(y0),'-W',str(x1-x0),'-H',str(y1-y0),'-png',str(path),str(output)],check=True,capture_output=True)
 return np.asarray(Image.open(output.with_suffix('.png')).convert('RGB')).copy()
for number in map(int,sys.argv[1:]):
 with page_worker():
  folder=B/f'natural/2018/T';old=folder/f'page{number:02}.old-source.pdf';target=folder/f'page{number:02}.pdf';out=folder/f'page{number:02}-native-digit-phase';out.mkdir(exist_ok=True)
  character,y=('5',631.63)if number==3 else('3',124.37)
  with f.open(old)as a,f.open(target)as b:
   def chosen(p):return sorted([g for g in _traces(p)if g['c']==character and g['font']=='Cambria Math'and abs(g['size']-12)<.001 and abs(g['origin'][1]-y)<.005],key=lambda g:g['origin'][0])
   original=chosen(a[0]);actual=chosen(b[0])
  assert len(original)==len(actual)==(1 if number==3 else 3)
  shifts=[];checks=[]
  for source,dest in zip(original,actual):
   assert all(source[k]==dest[k]for k in ['c','font','size','trace_gid','render_mode','color','opacity'])and abs(source['origin'][1]-dest['origin'][1])<.001
   dx=dest['origin'][0]-source['origin'][0];shifts.append(dict(glyphs=[source],dx=dx));checks.append(dict(source=source,actual_destination=dest,requested_dx=dx))
  moved,moveqa=reposition_inline(old,1,shifts=shifts,allow_white_background_panels=True)
  promoted,promoteqa=promote_native_glyphs(moved,1,actual)
  wanted={glyph_key(g)for g in actual}
  with f.open(stream=promoted,filetype='pdf')as d:unwanted=[g for g in _traces(d[0])if g['c'].strip()and glyph_key(g)not in wanted]
  reference,eraseqa=reposition_inline(promoted,1,erased_glyphs=unwanted)
  ref=out/'original-native-CID-only.pdf';ref.write_bytes(reference)
  measurements=[]
  for scale in [4,8,12]:
   for renderer in ['MuPDF','Poppler']:
    for index,g in enumerate(actual):
     r=list(f.Rect(g['bbox'])+(-.5,-.5,.5,.5))
     a=crop_rgb(ref,r,scale,renderer,out/f'ref-{renderer}-{scale}-{index}');b=crop_rgb(target,r,scale,renderer,out/f'final-{renderer}-{scale}-{index}')
     assert a.shape==b.shape,(a.shape,b.shape)
     ink=a.min(axis=2)<255;dark=a.min(axis=2)<32
     record=dict(renderer=renderer,scale=scale,index=index,reference_nonwhite_pixels=int(ink.sum()),reference_deep_dark_pixels=int(dark.sum()),missing_original_CID_pixels=int((dark&(b.min(axis=2)>=220)).sum()),actual_reference_nonwhite_RGB_errors=int((ink&np.any(a!=b,axis=2)).sum()))
     measurements.append(record);print(number,record,flush=True)
  high=[]
  for index,(source,dest)in enumerate(zip(original,actual)):
   rect=[min(source['origin'][0],dest['origin'][0])-8,y-17,max(source['origin'][0],dest['origin'][0])+15,y+9]
   oc=out/f'old-crop-{index}.pdf';fc=out/f'final-crop-{index}.pdf'
   for inp,output in [(old,oc),(target,fc)]:
    with pikepdf.open(inp)as d:
     height=float(d.pages[0].MediaBox[3]);d.pages[0].CropBox=pikepdf.Array([rect[0],height-rect[3],rect[2],height-rect[1]]);d.save(output,compress_streams=False)
   with f.open(oc)as d:
    glyph=next(g for g in _traces(d[0])if g['c']==source['c']and g['trace_gid']==source['trace_gid']and abs(g['origin'][0]-(source['origin'][0]-rect[0]))<.01 and abs(g['origin'][1]-(y-rect[1]))<.01)
   for scale in [8,12]:
    q=audit_moved_native_ink(oc,1,fc,shifts=[dict(glyphs=[glyph],dx=dest['origin'][0]-source['origin'][0])],protected_glyphs=[glyph],scale=scale)
    high.append(dict(index=index,scale=scale,svg_missing=q['newly_missing_native_ink_pixels'],passed=q['passed']));print('HIGH_RES_SVG',number,high[-1],flush=True)
  report=dict(kind='original-native-Cambria-digit-phase-diagnostic-v1',original_language_source_sha256='0782ab2ced4c911ce92b550aa2fd86cb7f6c9a6e24d7a60f64b13275df1e38ba',source_page=number,source_base_page_sha256=sha(old),proof_sha256=sha(target),proof_unmodified=True,delivered_pdf_modified=False,mathematics_retyped=False,checks=checks,source_move_qa=moveqa,original_CID_promotion=promoteqa,other_text_erasure=eraseqa,reference_sha256=sha(ref),native_CID_reference_measurements=measurements,high_resolution_unhinted_SVG=high,passed=all(q['missing_original_CID_pixels']==0 and q['actual_reference_nonwhite_RGB_errors']==0 and q['reference_deep_dark_pixels']>0 for q in measurements)and moveqa['passed']and promoteqa['passed']and eraseqa['passed'])
  (out/'witness.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');print('DIAGNOSTIC_COMPLETE',number,report['passed'],flush=True)
  gc.collect()

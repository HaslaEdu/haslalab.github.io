"""Complete original21-CID MathType Form witness; no proof edits or threshold changes."""
from pathlib import Path
import sys,json,hashlib,subprocess,os,pikepdf,pymupdf as f,numpy as np
from PIL import Image
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions');F=B/'natural/2018/TS';O=B/'natural/2018-page02-original-formula6-program';O.mkdir(exist_ok=True);sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import _traces,reposition_inline,inspect_inline_groups
from pdf_moved_native_ink import audit_moved_native_ink
from pdf_original_text_ops import glyph_key
from izho_2018_independent_original_math_geometry import infer
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();source=B/'2018/source/IZhO_2018_TS.pdf';old=F/'page02.old-source.pdf';proof=F/'page02.pdf';pin=sha(proof);R=[149,411,325,448];POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
def rgb(path,scale,renderer,out):
 if renderer=='MuPDF':
  with f.open(path)as doc:p=doc[0].get_pixmap(matrix=f.Matrix(scale,scale),clip=f.Rect(R),colorspace=f.csRGB,alpha=False);return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()
 x,y,w,h=[int(v*scale)for v in[R[0],R[1],R[2]-R[0],R[3]-R[1]]]
 subprocess.run([POP,'-f','1','-singlefile','-r',str(scale*72),'-x',str(x),'-y',str(y),'-W',str(w),'-H',str(h),'-png',str(path),str(out)],capture_output=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt'else 0)
 with Image.open(out.with_suffix('.png'))as im:return np.asarray(im.convert('RGB')).copy()
with page_worker():
 assert sha(source)=='f338dd0093628b658df3f02ca40a34b97e6ecd8fa431cf8517f08aa4eb14ff49'
 inv=json.loads((B/'2018/inspection/page02-original-native-inline-inventory.json').read_text('utf8'));form=next(v for v in inv['forms']if v['path']==[2062]);assert form['original_raw_sha256']=='666a17a58619bd070f911acee1ef41eb56e506fe081cd31e05fb3dd0c6a39df5'
 with f.open(source)as doc,f.open(proof)as dst:
  original=_traces(doc[1]);wanted={glyph_key(g)for g in form['glyphs']if g['c'].strip()};gs=[g for g in original if glyph_key(g)in wanted];assert len(gs)==21;dx=infer(gs,_traces(dst[0]));erase=[g for g in original if g['c'].strip()and glyph_key(g)not in wanted]
 # Isolate the literal original invoked Form. Preserve every original outer
 # graphics-state/clip operator and all original font/resource bytes; suppress
 # only unrelated top-level text/Do/path paints. One ROOT translation moves
 # the complete original Form plus its entire original ancestor context.
 ref=O/'exact-original-formula6-CIDs-Form-clips-rules-paint-only.pdf'
 with pikepdf.open(source)as src,pikepdf.Pdf.new()as single:
  single.pages.append(src.pages[1]);page=single.pages[0];ops=pikepdf.parse_content_stream(page);selected=[];suppressed=[]
  for i,op in enumerate(ops):
   name=str(op.operator)
   if name=='Do'and i!=2062:suppressed.append([i,name]);continue
   if name in ['Tj','TJ',"'",'"']:suppressed.append([i,name]);continue
   if name in ['S','s','f','F','f*','B','B*','b','b*']:
    suppressed.append([i,name]);selected.append(pikepdf.ContentStreamInstruction([],pikepdf.Operator('n')));continue
   selected.append(op)
  page.Contents=single.make_stream(('q\n1 0 0 1 '+format(dx,'.12f')+' 0 cm\n').encode()+pikepdf.unparse_content_stream(selected)+b'\nQ\n');single.save(ref,compress_streams=False)
 guard=dict(method='Literal original source Form invocation and exact source ancestor state/clips retained; unrelated top-level paint suppressed, one root horizontal dx only',literal_original_Form_raw_sha256=form['original_raw_sha256'],source_operator_path=[2062],source_top_level_paints_suppressed=suppressed,complete_original_expression_CIDs_and_internal_programs_unchanged=True)
 with f.open(ref)as doc:actual=[g for g in _traces(doc[0])if g['c'].strip()];assert len(actual)==21;assert abs(infer(gs,actual)-dx)<.001
 measures=[]
 for scale in[4,8,12]:
  for renderer in['MuPDF','Poppler']:
   a=rgb(ref,scale,renderer,O/f'original-reference-{renderer}-{scale}');b=rgb(proof,scale,renderer,O/f'actual-proof-{renderer}-{scale}');assert a.shape==b.shape
   ink=a.min(2)<255;dark=a.min(2)<32;r=dict(renderer=renderer,scale=scale,reference_original_program_nonwhite_pixels=int(ink.sum()),reference_original_program_deep_dark_pixels=int(dark.sum()),missing_original_native_program_pixels=int((dark&(b.min(2)>=220)).sum()),actual_reference_nonwhite_RGB_errors=int((ink&np.any(a!=b,2)).sum()));r['passed']=r['reference_original_program_deep_dark_pixels']>0 and r['missing_original_native_program_pixels']==0 and r['actual_reference_nonwhite_RGB_errors']==0;measures.append(r);print('EXACT_ORIGINAL2018_FORMULA6_PROGRAM',r,flush=True)
 for inp,out in[(ref,O/'original-reference-same-integer-crop.pdf'),(proof,O/'actual-proof-same-integer-crop.pdf')]:
  with pikepdf.open(inp)as doc:h=float(doc.pages[0].MediaBox[3]);doc.pages[0].CropBox=pikepdf.Array([R[0],h-R[3],R[2],h-R[1]]);doc.save(out,compress_streams=False)
 with f.open(O/'original-reference-same-integer-crop.pdf')as doc:cropped=[g for g in _traces(doc[0])if g['c'].strip()];assert len(cropped)==21
 svg={str(s):audit_moved_native_ink(O/'original-reference-same-integer-crop.pdf',1,O/'actual-proof-same-integer-crop.pdf',protected_glyphs=cropped,scale=s)for s in[4,8,12]}
 q=dict(kind='source2018-page02-complete-original-formula6-native-Form-program-v1',original_source_sha256=sha(source),source_page=2,original_input_page_sha256=sha(old),proof_sha256=pin,proof=str(proof),proof_unmodified=True,mathematics_retyped=False,source_font_programs_substituted=False,original_form=form,complete_original_expression_glyphs=gs,independently_inferred_whole_original_expression_dx=dx,source_native_reference_guard=guard,source_reference_sha256=sha(ref),source_reference_file=str(ref),source_math_expression_point_sizes=sorted({g['size']for g in gs}),same_integer_page_crop=R,native_original_program_reference_measurements=measures,svg_reference_scales=svg,passed=all(m['passed']for m in measures)and all(svg[str(s)]['passed']and svg[str(s)]['newly_missing_native_ink_pixels']==0 for s in[4,8,12]))
 assert sha(proof)==pin;(O/'witness.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('COMPLETE_LITERAL_ORIGINAL2018_FORMULA6_WITNESS',q['passed'],len(gs),sha(O/'witness.json'),flush=True)

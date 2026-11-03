"""Source-bound complete original native Word math controls for pages5/8."""
from pathlib import Path
import sys,json,hashlib,subprocess,os,pikepdf,pymupdf as f,numpy as np
from PIL import Image
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions');F=B/'natural/2018/TS';sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import _traces,reposition_inline,inspect_inline_groups
from pdf_moved_native_ink import audit_moved_native_ink
from pdf_original_text_ops import glyph_key
from izho_2018_independent_original_math_geometry import infer
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();source=B/'2018/source/IZhO_2018_TS.pdf';POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
def entry(inv,g):
 found=[(show,part)for show in inv['top_level_text_shows']for part in show['parts']if any(glyph_key(h)==glyph_key(g)and h['trace_gid']==g['trace_gid']for h in part['glyphs'])];assert len(found)==1,(g,len(found));show,part=found[0];assert len(part['glyphs'])==1;s=show['state']
 return dict(operator=show['operator'],operator_index=show['operator_index'],encoded_CID_hex=part['raw_hex'],code=part['code'],font_resource=s['active'],Tf=s['tf'],Tm=show['text_matrix'],CTM=s['ctm'],Tc=s['tc'],Tw=s['tw'],Th=s['th'],Ts=s['ts'],Tr=s['tr'])
def rgb(path,scale,renderer,R,out):
 if renderer=='MuPDF':
  with f.open(path)as doc:p=doc[0].get_pixmap(matrix=f.Matrix(scale,scale),clip=f.Rect(R),colorspace=f.csRGB,alpha=False);return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()
 x,y,w,h=[int(v*scale)for v in[R[0],R[1],R[2]-R[0],R[3]-R[1]]];subprocess.run([POP,'-f','1','-singlefile','-r',str(scale*72),'-x',str(x),'-y',str(y),'-W',str(w),'-H',str(h),'-png',str(path),str(out)],capture_output=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt'else 0)
 with Image.open(out.with_suffix('.png'))as im:return np.asarray(im.convert('RGB')).copy()
for n in list(map(int,sys.argv[1:]))or[5,8]:
 assert n in[5,8];O=B/f'natural/2018-page{n:02}-original-native-word-program';O.mkdir(exist_ok=True);proof=F/f'page{n:02}.pdf';old=F/f'page{n:02}.old-source.pdf';pin=sha(proof);plan=json.loads((F/f'plans/page{n:02}.json').read_text('utf8'));R=[109,666,178,683]if n==5 else[130,474,302,499]
 if n==8 and (O/'witness.json').exists()and not(O/'rejected-witness-including-previous-row-descender-fragments.json').exists():(O/'rejected-witness-including-previous-row-descender-fragments.json').write_bytes((O/'witness.json').read_bytes())
 with page_worker():
  assert sha(source)=='f338dd0093628b658df3f02ca40a34b97e6ecd8fa431cf8517f08aa4eb14ff49'
  inv=json.loads((B/f'2018/inspection/page{n:02}-original-native-inline-inventory.json').read_text('utf8'))
  with f.open(source)as src,f.open(old)as initial,f.open(proof)as dst:
   original=[g for g in _traces(src[n-1])if g['c'].strip()];baseline=_traces(initial[0]);actual=_traces(dst[0]);vectors=[]
   if n==5:gs=[g for g in original if 173<g['origin'][0]<239 and abs(g['origin'][1]-677.3799438476562)<.001];assert len(gs)==7
   else:
    profile=next(r for r in plan['reviewed_independent_original_expression_geometry_profiles']if abs(r['logical_prose_baseline']-487.6299743652344)<.001);gs=profile['original_glyphs'];assert len(gs)==32
    baseline_inv=inspect_inline_groups(old,1)
    for v in profile['original_vector_paths']:
     matches=[h for h in baseline_inv['vector_paths']if h['paint_operator']==v['paint_operator']and max(abs(a-b)for a,b in zip(h['rect'],v['rect']))<.001];assert len(matches)==1;vectors.append(matches[0])
   dx=infer(gs,actual);wanted={glyph_key(g)for g in gs};current=[]
   for g in gs:
    matches=[h for h in baseline if glyph_key(h)==glyph_key(g)and h['trace_gid']==g['trace_gid']];assert len(matches)==1;current.append(matches[0])
   forms={glyph_key(g)for v in inv['forms']for g in v['glyphs']if g['c'].strip()};erase=[g for g in baseline if g['c'].strip()and glyph_key(g)not in wanted|forms]
  # The full original Word row clip owns all its original fraction paths;
  # the unchanged guard rejects duplicate vector-path motion requests.
  raw,guard=reposition_inline(old,1,erased_glyphs=erase,shifts=[dict(glyphs=current,dx=dx,vector_paths=[]if n==8 else vectors)],allow_white_background_panels=True);ref=O/'exact-original-native-CIDs-clips-rules-paint-only.pdf';ref.write_bytes(raw)
  with f.open(ref)as doc:
   refrows=_traces(doc[0]);moved=[h for g in gs for h in refrows if h['c']==g['c']and h['font']==g['font']and h['trace_gid']==g['trace_gid']and abs(h['size']-g['size'])<.001 and abs(h['origin'][1]-g['origin'][1])<.001 and abs(h['origin'][0]-g['origin'][0]-dx)<.001];assert len(moved)==len(gs)
  measures=[]
  for scale in[4,8,12]:
   for renderer in['MuPDF','Poppler']:
    a=rgb(ref,scale,renderer,R,O/f'original-reference-{renderer}-{scale}');b=rgb(proof,scale,renderer,R,O/f'actual-proof-{renderer}-{scale}');assert a.shape==b.shape;ink=a.min(2)<255;dark=a.min(2)<32;r=dict(renderer=renderer,scale=scale,reference_original_program_nonwhite_pixels=int(ink.sum()),reference_original_program_deep_dark_pixels=int(dark.sum()),missing_original_native_program_pixels=int((dark&(b.min(2)>=220)).sum()),actual_reference_nonwhite_RGB_errors=int((ink&np.any(a!=b,2)).sum()));r['passed']=r['reference_original_program_deep_dark_pixels']>0 and r['missing_original_native_program_pixels']==r['actual_reference_nonwhite_RGB_errors']==0;measures.append(r);print('COMPLETE_ORIGINAL2018_WORD_PROGRAM',n,r,flush=True)
  for inp,out in[(ref,O/'original-reference-same-integer-crop.pdf'),(proof,O/'actual-proof-same-integer-crop.pdf')]:
   with pikepdf.open(inp)as doc:h=float(doc.pages[0].MediaBox[3]);doc.pages[0].CropBox=pikepdf.Array([R[0],h-R[3],R[2],h-R[1]]);doc.save(out,compress_streams=False)
  with f.open(O/'original-reference-same-integer-crop.pdf')as doc:cropped=[g for g in _traces(doc[0])if g['c'].strip()and 0<=g['origin'][0]<=R[2]-R[0]and 0<=g['origin'][1]<=R[3]-R[1]];assert len(cropped)==len(gs),(n,len(cropped),len(gs))
  svg={str(s):audit_moved_native_ink(O/'original-reference-same-integer-crop.pdf',1,O/'actual-proof-same-integer-crop.pdf',protected_glyphs=cropped,scale=s)for s in[4,8,12]}
  # Independently collect every literal encoded CID and original text state.
  inventories=[inspect_inline_groups(path,page,include_text_shows=True)for path,page in[(source,n),(ref,1),(proof,1)]];programs=[]
  for g,h in zip(gs,moved):
   target=next(a for a in actual if a['c']==g['c']and a['font']==g['font']and a['trace_gid']==g['trace_gid']and abs(a['size']-g['size'])<.001 and abs(a['origin'][1]-g['origin'][1])<.001 and abs(a['origin'][0]-g['origin'][0]-dx)<.001);a=entry(inventories[0],g);b=entry(inventories[1],h);c=entry(inventories[2],target);fields=['encoded_CID_hex','code','font_resource','Tf','Tm','Tc','Tw','Th','Ts','Tr'];assert all(a[k]==b[k]==c[k]for k in fields),(n,g,a,b,c);programs.append(dict(source_glyph=g,actual_target_glyph=target,independent_reference_glyph=h,requested_dx=dx,source_encoded_program=a,reference_encoded_program=b,actual_encoded_program=c,all_original_CID_font_Tf_fullTm_and_paint_preserved=True))
  q=dict(kind=f'source2018-page{n:02}-complete-original-native-word-program-v1',original_source_sha256=sha(source),source_page=n,original_input_page_sha256=sha(old),proof_sha256=pin,proof=str(proof),proof_unmodified=True,mathematics_retyped=False,source_font_programs_substituted=False,complete_original_expression_glyphs=gs,exact_original_CID_programs=programs,independently_inferred_whole_original_expression_dx=dx,source_native_reference_guard=guard,source_reference_sha256=sha(ref),source_reference_file=str(ref),source_math_expression_point_sizes=sorted({g['size']for g in gs}),same_integer_page_crop=R,native_original_program_reference_measurements=measures,svg_reference_scales=svg,passed=all(m['passed']for m in measures)and all(svg[str(s)]['passed']and svg[str(s)]['newly_missing_native_ink_pixels']==0 for s in[4,8,12]));assert sha(proof)==pin;(O/'witness.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('SOURCE2018_COMPLETE_WORD_PROGRAM_WITNESS',n,q['passed'],len(gs),sha(O/'witness.json'),flush=True)

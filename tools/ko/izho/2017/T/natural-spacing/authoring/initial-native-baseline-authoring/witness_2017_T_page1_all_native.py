"""Analysis-only exact original encoded paints for every native instruction glyph."""
from pathlib import Path
import sys,json,hashlib
import numpy as np,pikepdf,pymupdf as fitz
B=Path(__file__).resolve().parent;sys.path[:0]=[str(B/'engine'),str(Path.cwd()/'tools')]
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import reposition_inline,_traces,inspect_inline_groups
from pdf_native_glyph_promote import promote_native_glyphs
from pdf_original_text_ops import glyph_key
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
f=B/'natural/2017/T';old=f/'page01.old-source.pdf';target=Path(sys.argv[1])if len(sys.argv)>1 else f/'page01.pdf';out=f/('all-original-CID-witness-negative'if len(sys.argv)>1 else'all-original-CID-witness');out.mkdir(exist_ok=True)
q=json.loads((f/'page01.qa.json').read_text('utf8'));plan=json.loads((f/'plans/page01.json').read_text('utf8'))
with fitz.open(plan['original_english_source'])as original,fitz.open(old)as src,fitz.open(target)as final:
 original_glyphs=_traces(original[0]);source_glyphs=_traces(src[0]);final_glyphs=_traces(final[0]);assert not original[0].get_image_info()
 physical_keys={(glyph_key(g),g['trace_gid'],g['render_mode'])for g in original_glyphs if g['c'].strip()and g['trace_gid']>=0 and g['render_mode']!=3}
 physical=[g for g in source_glyphs if (glyph_key(g),g['trace_gid'],g['render_mode'])in physical_keys and g['c'].strip()]
 assert len(physical)==96
 moves={glyph_key(g):s['dx']for s in q['native_shifts']for g in s['glyphs']};targets=[];shifts=[]
 for g in physical:
  dx=moves.get(glyph_key(g),0.)
  hits=[r for r in final_glyphs if r['c']==g['c']and r['font']==g['font']and r['trace_gid']==g['trace_gid']and r['render_mode']==g['render_mode']and r['color']==g['color']and abs(r['size']-g['size'])<1e-6 and abs(r['origin'][1]-g['origin'][1])<.001 and abs(r['origin'][0]-g['origin'][0]-dx)<.001]
  if len(hits)!=1:raise ValueError('Original source glyph does not have one exact same-font/GID/size/paint/y destination')
  targets.append(hits[0]);shifts.append(dict(glyphs=[g],dx=dx))
with page_worker():
 # Replay the original grouped journal: splitting each word into individual
 # Tj translations would introduce different sub-millipoint rounding phases.
 moved,moveqa=reposition_inline(old,1,shifts=q['native_shifts'],erased_glyphs=q['erased_hangul_glyphs'],**q.get('native_move_options',{}))
 promoted,promoteqa=promote_native_glyphs(moved,1,targets)
 keep={glyph_key(g)for g in targets}
 with fitz.open(stream=promoted,filetype='pdf')as doc:unwanted=[g for g in _traces(doc[0])if g['c'].strip()and glyph_key(g)not in keep]
 ref,eraseqa=reposition_inline(promoted,1,erased_glyphs=unwanted);reference=out/'original-encoded-native-CID-reference.pdf';reference.write_bytes(ref)
 inv=inspect_inline_groups(plan['original_english_source'],1,include_text_shows=True);codes={}
 for show in inv['top_level_text_shows']:
  for part in show['parts']:
   for g in part['glyphs']:codes[glyph_key(g)]=(part['raw_hex'],g['trace_gid'],show['state']['tf'])
 checks=[]
 for source,actual,paint in zip(physical,targets,promoteqa['promoted_native_paints']):
  expected=codes[glyph_key(source)];assert expected==(paint['source_encoded_cid_hex'],paint['gid'],paint['source_Tf'])
  checks.append(dict(source=source,actual_destination=actual,original_encoded_cid_hex=expected[0],original_GID=expected[1],original_Tf=expected[2],original_source_CID_gid_Tf_exact=True,requested_dx=moves.get(glyph_key(source),0.)))
 # Integer-point horizontal strips preserve raster phase while keeping the
 # 12x actual-font comparison under a few MB, rather than a full-page bitmap.
 strips=[]
 for g in sorted(targets,key=lambda g:g['bbox'][1]):
  lo=max(0,int(np.floor(g['bbox'][1]))-2);hi=int(np.ceil(g['bbox'][3]))+2
  if strips and lo<=strips[-1][1]:strips[-1][1]=max(hi,strips[-1][1])
  else:strips.append([lo,hi])
 scales={}
 with fitz.open(reference)as native,fitz.open(target)as final:
  for scale in [4,8,12]:
   checked=[]
   for lo,hi in strips:
    rect=fitz.Rect(0,lo,native[0].rect.width,hi)
    a=native[0].get_pixmap(matrix=fitz.Matrix(scale,scale),clip=rect,colorspace=fitz.csRGB,alpha=False);z=final[0].get_pixmap(matrix=fitz.Matrix(scale,scale),clip=rect,colorspace=fitz.csRGB,alpha=False)
    aa=np.frombuffer(a.samples,np.uint8).reshape(a.height,a.width,3).min(axis=2);zz=np.frombuffer(z.samples,np.uint8).reshape(z.height,z.width,3).min(axis=2)
    dark=aa<32;missing=int((dark&(zz>=220)).sum());assert missing==0
    checked.append(dict(rect_pt=list(rect),native_reference_dark_pixels=int(dark.sum()),missing_original_encoded_CID_pixels=missing))
   scales[str(scale)]=dict(strips=checked,native_reference_dark_pixels=sum(r['native_reference_dark_pixels']for r in checked),missing_original_encoded_CID_pixels=sum(r['missing_original_encoded_CID_pixels']for r in checked),passed=True)
 report=dict(kind='all-original-instruction-native-CIDs-v1',proof_sha256=sha(target),proof_unmodified=True,original_language_source_sha256=plan['original_english_source_sha256'],input_native_baseline_page_sha256=sha(old),source_native_glyphs=96,original_CID_checks=checks,source_CID_promotion=promoteqa,source_move_qa=moveqa,reference_other_text_suppression=eraseqa,reference=str(reference),reference_sha256=sha(reference),native_reference_scales=scales,delivered_pdf_modified=False,mathematics_retyped=False,passed=moveqa['passed']and promoteqa['passed']and eraseqa['passed']and all(r['passed']for r in scales.values()))
 (out/'witness.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');print('ALL_ORIGINAL_CID_WITNESS',report['passed'],len(checks),{k:v['missing_original_encoded_CID_pixels']for k,v in scales.items()},flush=True)

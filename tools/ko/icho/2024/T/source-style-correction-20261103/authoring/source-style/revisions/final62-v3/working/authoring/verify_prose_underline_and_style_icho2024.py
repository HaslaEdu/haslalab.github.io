"""Independently read actual glyph curves, source-only underlines and PDF shear."""
from pathlib import Path
from io import BytesIO
import hashlib,json,math,re
import pymupdf as f
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
import natural_plan_compose_icho2024_style as c
import actual_prose_ink_icho2024_style as actual_ink
import prose_outline_geometry_icho2024_style as outline_geometry
import numpy as np
import icho2024_style_experiment_guard as g
B=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
face=lambda s:re.sub('[^a-z0-9]','',s.lower())

def run(n):
 path=g.PROOFS/f'page{n:02}.pdf';g.assert_output(path,n);q=json.loads(path.with_suffix('.layout.json').read_text('utf8'));assert q['page']==n and Path(q['source']).resolve()==g.SOURCE and q['source_sha256']==g.SOURCE_SHA and sha(path)==q['output_sha256']
 raw=path.read_bytes();doc=f.open(path);actual=c._glyphs(doc[0]);metrics=c.FontMetrics({role:Path(p)for role,p in q['new_font_paths'].items()});full={};subset={};fontpins={}
 for entry in doc[0].get_fonts():
  if entry[4].startswith('KO_Natural_')and not entry[4].startswith('KO_Natural_Raster_'):subset[entry[4].removeprefix('KO_Natural_').replace('_','-')]=TTFont(BytesIO(doc.extract_font(entry[0])[3]))
 def font(role):
  if role not in full:
   p=Path(q['new_font_paths'][role]);full[role]=TTFont(p,fontNumber=0 if p.suffix.lower()=='.ttc'else -1);fontpins[role]=dict(path=str(p),sha256=sha(p),postscript_face=full[role]['name'].getDebugName(6))
  return full[role]
 positions={};styles=[];want_origins={};full_shapes=set()
 for p in q['placements']:
  metric=metrics[p['font_role']];x,y=p['point'];positions[p['id']]=positions.get(p['id'],[])+[(p,[])];chars=positions[p['id']][-1][1];newword=True
  for index,char in enumerate(p['text']):
   if char.isspace():x+=c.word_space(metric,p['size']);newword=True;continue
   matches=[v for v in actual if v['c']==char and face(v['font'])==face(metric.name)and abs(v['size']-p['size'])<.001 and max(abs(v['origin'][0]-x),abs(v['origin'][1]-y))<.001];assert len(matches)==1,(n,p['id'],char,x,y,matches)
   v=matches[0];chars.append((index,v));want_origins[c.ops.glyph_key(v)]=(x,y)
   styles.append((p,v));newword=False
   x+=metric.text_length(char,fontsize=p['size'])
 requested={c.ops.glyph_key(v):v for _,v in styles};specs=[]
 for spec in q.get('prose_vector_decorations',[]):
  spec['target_ink_records']=[dict(slot_id=spec['slot_id'],target_text=spec['target_text'],full_font_sha256=spec['target_full_font_sha256'])]
  chosen=[]
  for frag in spec['target_ink_records']:
   matches=[(p,chars)for p,chars in positions.get(frag['slot_id'],[])if frag['target_text']in p['text']];assert len(matches)==1,(n,spec['id'],frag,matches);p,chars=matches[0];start=p['text'].index(frag['target_text']);end=start+len(frag['target_text']);values=[v for i,v in chars if start<=i<end];assert values
   assert sha(q['new_font_paths'][p['font_role']])==frag['full_font_sha256']
   ff=font(p['font_role']);ss=subset[p['font_role']];fs=ff.getGlyphSet();sg=ss.getGlyphSet();fc=ff.getBestCmap();sc=ss.getBestCmap()
   for v in values:
    gn=fc[ord(v['c'])];assert v['gid']==ff.getGlyphID(gn);sgn=ss.getGlyphOrder()[v['gid']];assert sc[ord(v['c'])]==sgn and ss['hmtx'].metrics[sgn]==ff['hmtx'].metrics[gn]
    a=DecomposingRecordingPen(fs);fs[gn].draw(a);b=DecomposingRecordingPen(sg);sg[sgn].draw(b);assert a.value==b.value
    requested[c.ops.glyph_key(v)]=v;chosen.append(v)
  for v in spec.get('native_source_glyphs',[]):
   dx=[s['dx']for s in q['native_shifts']if any(c.ops.glyph_key(a)==c.ops.glyph_key(v)for a in s['glyphs'])];mx=next(iter(dx),0.);origin=[v['origin'][0]+mx,v['origin'][1]];matches=[a for a in actual if a['c']==v['c']and a['gid']==v['gid']and a['font']==v['font']and abs(a['size']-v['size'])<.001 and max(abs(x-y)for x,y in zip(a['origin'],origin))<.001];assert len(matches)==1
   chosen+=matches;requested[c.ops.glyph_key(matches[0])]=matches[0]
  specs.append((spec,chosen))
 bounds,matrices=actual_ink.measure(raw,list(requested.values()),with_matrices=True)if requested else({},{});style_rows=[]
 for p,v in styles:
  record=matrices[c.ops.glyph_key(v)];assert v['size']==p['size'];assert record['glyph']['render_mode']==0 and record['glyph']['opacity']==1.;expected=math.tan(math.radians(p['angle']));observed=record['actual_shear_tangent'];assert observed is not None and abs(observed-expected)<=1e-9,(n,p['id'],expected,record)
  ff=font(p['font_role']);assert v['gid']==ff.getGlyphID(ff.getBestCmap()[ord(v['c'])])
  ss=subset[p['font_role']];cp=ord(v['c']);pair=(p['font_role'],cp);gn=ff.getBestCmap()[cp];sgn=ss.getGlyphOrder()[v['gid']]
  assert ss.getBestCmap()[cp]==sgn and ss['hmtx'].metrics[sgn]==ff['hmtx'].metrics[gn]
  if pair not in full_shapes:
   fs=ff.getGlyphSet();sg=ss.getGlyphSet();aa=DecomposingRecordingPen(fs);fs[gn].draw(aa);bb=DecomposingRecordingPen(sg);sg[sgn].draw(bb);assert aa.value==bb.value;full_shapes.add(pair)
  xx,yy=want_origins[c.ops.glyph_key(v)];bb=outline_geometry.glyph_bounds(q['new_font_paths'][p['font_role']],cp,p['angle']);expected_box=[xx+bb[0]*p['size'],yy-bb[3]*p['size'],xx+bb[2]*p['size'],yy-bb[1]*p['size']];observed_box=bounds[c.ops.glyph_key(v)];bbox_error=max(abs(a-b)for a,b in zip(expected_box,observed_box));assert bbox_error<=.001,(n,p['id'],v,expected_box,observed_box,bbox_error)
  if 'source_font_descriptor_italic_angle'in p:assert abs(p['angle']+p['source_font_descriptor_italic_angle'])<=1e-12
  style_rows.append(dict(slot_id=p['id'],actual_glyph=v,original_source_font=p.get('semantic_source_style_font',p['source_font']),actual_curve_bbox=observed_box,expected_full_font_curve_bbox=expected_box,actual_curve_bbox_error_pt=bbox_error,original_source_descriptor_ItalicAngle=p.get('source_font_descriptor_italic_angle'),authored_pdf_shear_angle=p['angle'],actual_pdf_shear_tangent=observed,expected_pdf_shear_tangent=expected,actual_font_linear_matrix_page_coordinates=record['actual_font_linear_matrix_page_coordinates']))
 inv=c.motion.inspect_inline_groups(raw,1);drawings=doc[0].get_drawings();rows=[]
 for spec,chosen in specs:
  rr=[bounds[c.ops.glyph_key(v)]for v in chosen];r=[min(v[0]for v in rr),min(v[1]for v in rr),max(v[2]for v in rr),max(v[3]for v in rr)];path2=inv['vector_paths'][spec['source_path_index']];u=path2['rect'];error=max(abs(u[0]-r[0]),abs(u[2]-r[2]));assert error<=.001,(n,spec['id'],r,u,error)
  assert path2['paint_operator']==spec['paint_operator']and abs(u[1]-spec['source_rect'][1])<=1e-7 and abs(u[3]-spec['source_rect'][3])<=1e-7
  ds=[d for d in drawings if max(abs(a-b)for a,b in zip(d['rect'],u))<.001];assert len(ds)==1 and ds[0]['color']==(0.,0.,0.)and ds[0]['fill']is None and ds[0]['type']=='s'and tuple(ds[0]['lineCap'])==(0,0,0)
  # A horizontal butt-cap affine leaves the physical vertical stroke unchanged.
  # MuPDF's scalar width is sqrt(det(CTM)); actual32x vertical columns verify appearance instead.
  samples=[];matched=False
  with f.open(g.SOURCE)as sd:
   for fraction in [.1,.25,.5,.75,.9]:
    vectors=[]
    for pg,rect in [(sd[n-1],spec['source_rect']),(doc[0],u)]:
     x=rect[0]+fraction*(rect[2]-rect[0]);y=rect[1];pix=pg.get_pixmap(matrix=f.Matrix(32,32),clip=f.Rect(x-.125,y-.35,x+.125,y+.35),colorspace=f.csGRAY,alpha=False);arr=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width);vectors.append((pix.y,arr[:,arr.shape[1]//2].tolist()))
    same=vectors[0]==vectors[1]and any(x<220 for x in vectors[0][1]);samples.append(dict(fraction=fraction,source=vectors[0],candidate=vectors[1],byte_identical=same));matched|=same
  assert matched,(n,spec['id'],'actual source/candidate vertical stroke differs')
  spec['actual32x_vertical_stroke_samples']=samples
  rows.append(dict(id=spec['id'],actual_emphasized_glyph_curve_union_bbox=r,actual_underline_bbox=u,actual_horizontal_ink_coverage_error_pt=error,original_y_thickness_black_stroke_and_paint_preserved=True,actual32x_vertical_stroke_sample_byte_equal=matched,actual32x_samples=samples,source_rect=spec['source_rect'],actual_native_path_index=spec['source_path_index'],source_English_glyph_path_guards_verified=True,all_Korean_used_glyph_GIDs_outlines_and_hmtx_match_pinned_full_font=True))
 assert q['new_korean_intrusion_on_native_ink_pixels']==0
 assert q['raster_labels']==[]
 actual_new=[v for v in actual if v['c'].strip()and v['font'].startswith(('NotoSerifCJK','NotoSansCJK'))];assert len(actual_new)==len(styles)==sum(len(p['text'].replace(' ',''))for p in q['placements'])
 report=dict(page=n,passed=True,proof_sha256=sha(path),source_sha256=g.SOURCE_SHA,measurement_code_sha256=sha(__file__),actual_curve_reader_sha256=sha(actual_ink.__file__),full_Korean_font_pins=fontpins,underline_rows=rows,underline_coverage_tolerance_pt=.001,source_native_vector_tolerance_pt=1e-7,protected_native_ink_contact_pixels=q['new_korean_intrusion_on_native_ink_pixels'],all_authored_glyphs_verified=len(styles),unique_full_font_outlines_hmtx_and_GIDs_verified=len(full_shapes),all_actual_curve_bboxes_match_requested_full_font_and_matrix=True,authored_word_style_samples=style_rows,actual_shear_tangent_tolerance=1e-9,scope='Every actual emitted Korean prose glyph verifies the real PDF shear/font GID and original physical point/baseline. Every emphasized glyph curve is independently read from actual output font programs under actual PDF matrices; source-English prose underline x extents must cover exactly the emitted phrase ink. Native source/math programs and coordinate checks are unchanged.')
 q['actual_prose_underline_coverage_and_style_audit']=report;path.with_suffix('.layout.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');path.with_suffix('.underline-style-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');doc.close();return report

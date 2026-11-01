"""Independent old-body/native geometry, source font and final ink QA."""
from pathlib import Path
from io import BytesIO
from collections import Counter
import sys,json,hashlib,subprocess,gc,os,math
import pymupdf as fitz,pikepdf,numpy as np
from PIL import Image
from fontTools.ttLib import TTFont
from fontTools.cffLib import CFFFontSet
from fontTools.pens.recordingPen import DecomposingRecordingPen
sys.path.insert(0,'D:/CodexBuilds/Hasla-publish-20261031/tools')
from pdf_native_inline_reposition import _traces,inspect_inline_groups
from pdf_original_text_ops import glyph_key
from pdf_moved_native_ink import audit_moved_native_ink,source_outline_reference
from pdf_memory_gate import page_worker
from pdf_text_motion_ink import ink_envelope
from izho_new_prose_outline_qa import trace_font_resources
from build_figure_labels import B,sha
def semantic(value,ancestors=()):
 if isinstance(value,pikepdf.Stream):
  assert value.objgen not in ancestors
  return dict(dictionary={str(k):semantic(v,ancestors+(value.objgen,))for k,v in value.items()},raw_sha256=hashlib.sha256(value.read_raw_bytes()).hexdigest())
 if isinstance(value,pikepdf.Dictionary):return {str(k):semantic(v,ancestors)for k,v in value.items()}
 if isinstance(value,pikepdf.Array):return [semantic(v,ancestors)for v in value]
 if isinstance(value,pikepdf.String):return dict(pdf_string_hex=bytes(value).hex())
 return str(value)
def font_data(raw):
 if raw[:4]in[b'\x00\x01\x00\x00',b'OTTO',b'true',b'ttcf']:
  ft=TTFont(BytesIO(raw),lazy=True);return dict(font=ft,glyphs=ft.getGlyphSet(),order=ft.getGlyphOrder(),upm=ft['head'].unitsPerEm,name=ft['name'].getDebugName(6),cmap=ft.getBestCmap())
 cff=CFFFontSet();cff.decompile(BytesIO(raw),None);top=cff[cff.fontNames[0]]
 return dict(cff=cff,glyphs=top.CharStrings,order=top.charset,upm=round(1/top.FontMatrix[0]),name=cff.fontNames[0])
def outline(data,name):
 pen=DecomposingRecordingPen(data['glyphs']);data['glyphs'][name].draw(pen)
 return [(op,[None if point is None else tuple(round(v/data['upm'],7)for v in point)for point in points])for op,points in pen.value]
def fresh(path,png):
 code="import sys,pymupdf as f;d=f.open(sys.argv[1]);d[0].get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csRGB,alpha=False).save(sys.argv[2])"
 subprocess.run([sys.executable,'-X','utf8','-c',code,str(path),str(png)],check=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt'else 0)
 with Image.open(png)as im:return np.asarray(im.convert('RGB')).copy()
def actual_label_linear_checks(pdf,placements):
 stack=[];linear=[1.,0.,0.,1.];tm=None;active=None;point=None;rows=[]
 for op in pikepdf.parse_content_stream(pdf.pages[0]):
  name=str(op.operator);v=op.operands
  if name=='q':stack.append(list(linear))
  elif name=='Q':linear=stack.pop()
  elif name=='cm':
   a,b,c,d=map(float,v[:4]);A,B,C,D=linear;linear=[a*A+b*C,a*B+b*D,c*A+d*C,c*B+d*D]
  elif name=='Tm':tm=list(map(float,v[:4]))
  elif name=='Tf':active=str(v[0]);point=float(v[1])
  elif name in['Tj','TJ']:
   row=placements[len(rows)];wanted=[1.,0.,math.tan(math.radians(row['source_italic_angle_degrees'])),1.]
   assert tm==[1.,0.,0.,1.]and max(abs(a-b)for a,b in zip(linear,wanted))<.00001
   assert active=='/'+row['font_resource']and abs(point-row['point_size'])<1e-6
   rows.append(dict(label=row['id'],actual_point_size=point,actual_font_basis=linear,source_role_inferred_italic_angle_degrees=row['source_italic_angle_degrees'],no_font_scale_or_added_tracking=True,passed=True))
 assert not stack and len(rows)==len(placements)
 return rows
def audit(year,number,*,analysis_target=None,analysis_report=None):
 folder=B/f'{year}/TS';canonical=folder/f'page{number:02}.pdf';q=json.loads(canonical.with_suffix('.labels.json').read_text('utf8'));body=Path(q['body']);assert sha(body)==q['body_sha256']and sha(canonical)==q['proof_sha256']
 target=Path(analysis_target)if analysis_target else canonical;out=folder/'qa'/f'page{number:02}';out.mkdir(parents=True,exist_ok=True)
 if not q['placements']:
  assert body.read_bytes()==target.read_bytes();r=dict(year=year,page=number,body_sha256=sha(body),proof_sha256=sha(target),qa_mode='publication',passed=True,byte_identical_no_label_page=True,labels=0)
 else:
  erase={glyph_key(g)for g in q['erased_native_word_glyphs']};offsets={glyph_key(g):s['dx']for s in q['original_caption_digit_shifts']for g in s['glyphs']};used=set();glyph_checks=[]
  with fitz.open(body)as old,fitz.open(target)as final,pikepdf.open(body)as oldpdf,pikepdf.open(target)as newpdf:
   original=[g for g in _traces(old[0])if g['c'].strip()];actual=[g for g in _traces(final[0])if g['c'].strip()];protected=[g for g in original if glyph_key(g)not in erase]
   for g in protected:
    x=g['origin'][0]+offsets.get(glyph_key(g),0);y=g['origin'][1]
    candidates=[]
    for i,h in enumerate(actual):
     if i in used:continue
     if any(g[k]!=h[k]for k in ['c','font','trace_gid','render_mode','color','opacity','linewidth','direction','stroke_color','stroke_opacity']):continue
     if abs(g['size']-h['size'])<1e-6 and abs(h['origin'][0]-x)<=.001 and abs(h['origin'][1]-y)<=.001:candidates.append(i)
    assert len(candidates)==1,('Original physical body glyph changed',year,number,g,len(candidates));used.add(candidates[0])
   new_actual=[g for i,g in enumerate(actual)if i not in used];expected=Counter(c for p in q['placements']for c in p['text']if c.strip());assert Counter(g['c']for g in new_actual)==expected
   mapped,programs=trace_font_resources(newpdf,final[0]);added=[g for g in mapped if g['font_alias'].startswith('/TranslatedFigure')and g['c'].strip()and g['gid']>=0]
   assert len(added)==len(new_actual);assert Counter(g['c']for g in added)==expected
   data={digest:font_data(programs[digest]['raw'])for digest in{g['font_program_sha256']for g in added}};donors={};cache={};cursor=0
   for p in q['placements']:
    font=Path(p['font_source']);assert sha(font)==p['font_source_sha256']
    if font not in donors:donors[font]=font_data(font.read_bytes())
    donor=donors[font];metric=fitz.Font(fontfile=p['embedded_font']);x,y=p['origin'];size=p['point_size'];advance=0.
    assert not p['target_point_size_fitted']
    for c in p['text']:
     g=added[cursor];cursor+=1;assert g['c']==c and g['font_alias']=='/'+p['font_resource']
     assert abs(g['size']-size)<1e-6 and max(abs(a-b)for a,b in zip(g['origin'],[x+advance,y]))<=.003 and g['render_type']==0 and g['color']==[0.,0.,0.]
     actual_font=data[g['font_program_sha256']];name=actual_font['order'][g['gid']];wanted=donor['cmap'][ord(c)];key=g['font_program_sha256'],g['gid'],str(font),c
     if key not in cache:
      a=outline(actual_font,name);b=outline(donor,wanted);assert a and a==b;cache[key]=True
     glyph_checks.append(dict(c=c,actual_gid=g['gid'],actual_font=actual_font['name'],source_point_size=size,actual_point_size=g['size'],source_baseline=y,actual_baseline=g['origin'][1],actual_outline_matches_complete_role_donor=True,source_point_is_estimate=p['source_point_size_is_estimate'],source_italic_angle_degrees=p['source_italic_angle_degrees']))
     advance+=metric.text_length(c,fontsize=size)
   assert cursor==len(added)
   for d in list(data.values())+list(donors.values()):
    if d.get('font'):d['font'].close()
   old_fonts={(r[3],hashlib.sha256(old.extract_font(r[0])[3]).hexdigest())for r in old[0].get_fonts(full=True)};new_fonts={(r[3],hashlib.sha256(final.extract_font(r[0])[3]).hexdigest())for r in final[0].get_fonts(full=True)};assert old_fonts<=new_fonts
   def images(page):return {str(k):semantic(v)for k,v in page.Resources.get('/XObject',{}).items()if str(v.get('/Subtype'))=='/Image'}
   assert images(oldpdf.pages[0])==images(newpdf.pages[0]);assert semantic(oldpdf.pages[0].get('/Group'))==semantic(newpdf.pages[0].get('/Group'));assert semantic(oldpdf.pages[0].Resources.get('/ColorSpace'))==semantic(newpdf.pages[0].Resources.get('/ColorSpace'))
   # Actual outline locations include the original inferred italic shear.
   shape,shape_match=source_outline_reference(final[0],new_actual,scale=4);assert shape_match['passed']
   erased_native=[g for g in original if glyph_key(g)in erase]
   native_word_mask,_=ink_envelope(old[0],[g['origin']for g in erased_native],4)
   moving_original=[g for g in protected if glyph_key(g)in offsets]
   old_digit_mask,_=ink_envelope(old[0],[g['origin']for g in moving_original],4)
   new_digit_mask,_=ink_envelope(final[0],[[g['origin'][0]+offsets[glyph_key(g)],g['origin'][1]]for g in moving_original],4)
  old_inv=inspect_inline_groups(body,1);new_inv=inspect_inline_groups(target,1);assert len(old_inv['images'])==len(new_inv['images'])
  for a,b in zip(old_inv['images'],new_inv['images']):assert a['original_raw_sha256']==b['original_raw_sha256']and max(abs(x-y)for x,y in zip(a['entry_ctm'],b['entry_ctm']))<=.002
  # Text-only overlay may contain no additional drawing/image, and its actual
  # font programs/GIDs/points/origins must match the final inserted glyphs.
  with fitz.open(q['text_overlay'])as overlay,pikepdf.open(q['text_overlay'])as overlay_pdf:
   assert sha(q['text_overlay'])==q['text_overlay_sha256'];assert not overlay[0].get_images(full=True)and not overlay[0].get_drawings()
   actual_linear=actual_label_linear_checks(overlay_pdf,q['placements'])
   ref,ref_programs=trace_font_resources(overlay_pdf,overlay[0]);ref=[g for g in ref if g['c'].strip()and g['gid']>=0];assert len(ref)==len(added)
   for a,b in zip(ref,added):
    for key in ['c','gid','font_program_sha256','render_type']:assert a[key]==b[key]
    assert abs(a['size']-b['size'])<1e-6 and max(abs(x-y)for x,y in zip(a['origin'],b['origin']))<=.001
  before=fresh(body,out/'before.png');native=fresh(q['native_control'],out/'native-control.png');erased=fresh(q['erased_only'],out/'erased-only.png');actual=fresh(target,out/'final.png');reference=fresh(q['text_overlay'],out/'actual-font-reference.png')
  source_words=np.zeros(shape.shape,bool)
  for p in q['placements']:
   if p['source_kind']!='bitmap-source-measured':continue
   x0,y0,x1,y1=[int(np.floor(v*4))for v in p['source_word_rect_pt']];source_words[max(0,y0-1):y1+2,max(0,x0-1):x1+2]=True
  native_changed=np.any(before!=native,axis=2);word_changed=np.any(native!=erased,axis=2);added_changed=np.any(erased!=actual,axis=2);changed=np.any(before!=actual,axis=2);ref_mask=np.any(reference<255,axis=2)
  pixel=dict(native_control_changed_outside_erased_source_native_words_and_original_caption_digits=int((native_changed&~(native_word_mask|old_digit_mask|new_digit_mask)).sum()),bitmap_word_erasure_outside_reviewed_source_words=int((word_changed&~source_words).sum()),added_ink_outside_independent_actual_font_reference=int((added_changed&~ref_mask).sum()),final_changed_outside_reviewed_words_caption_digits_and_reference=int((changed&~(source_words|native_word_mask|old_digit_mask|new_digit_mask|ref_mask)).sum()),new_label_over_preserved_original_ink=int((shape&(erased.min(axis=2)<120)).sum()),actual_new_label_ink_missing=int(((reference.min(axis=2)<160)&(actual.min(axis=2)>=220)).sum()),independent_reference_contains_only_verified_actual_label_glyphs=True,reference_sha256=sha(q['text_overlay']))
  if pixel['new_label_over_preserved_original_ink']:
   yy,xx=np.nonzero(shape&(erased.min(axis=2)<120));pixel['collision_bbox']=[float(xx.min()/4),float(yy.min()/4),float((xx.max()+1)/4),float((yy.max()+1)/4)]
  physical=audit_moved_native_ink(body,1,target,shifts=q['original_caption_digit_shifts'],erased_glyphs=q['erased_native_word_glyphs'],protected_glyphs=protected)
  passed=all(pixel[k]==0 for k in pixel if isinstance(pixel[k],int)and not isinstance(pixel[k],bool))and physical['passed']
  r=dict(year=year,page=number,body_sha256=sha(body),proof_sha256=sha(target),unmodified_canonical_proof_sha256=sha(canonical),qa_mode='analysis-only-negative-clone'if analysis_target else'publication',labels=len(q['placements']),original_physical_body_glyphs_checked=len(protected),erased_native_language_only_glyphs=len(erase),original_body_glyph_font_GID_point_paint_and_y_preserved=True,only_reviewed_caption_digits_moved_horizontally=True,all_original_font_programs_retained=True,all_original_image_palette_ICC_mask_graphs_and_CTMs_retained=True,original_page_group_and_colorspace_retained=True,actual_label_glyphs_checked=len(added),actual_label_glyph_style_checks=glyph_checks,actual_label_font_basis_checks=actual_linear,actual_label_outline_source_match=shape_match,original_native_ink=physical,pixel_audit=pixel,point_sizes_fitted=False,source_bitmap_font_and_point_sizes_are_estimates=any(p['source_point_size_is_estimate']for p in q['placements']),passed=passed)
  del before,native,erased,actual,reference,shape;fitz.TOOLS.store_shrink(100);gc.collect()
 report=Path(analysis_report)if analysis_report else folder/'qa'/f'page{number:02}.audit.json';report.parent.mkdir(exist_ok=True);report.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n','utf8');print('FIGURE_WORD_QA',year,number,r['passed'],r.get('pixel_audit'),flush=True)
 if not r['passed']:raise ValueError(('Strict figure language proof failed',year,number))
 return r
if __name__=='__main__':
 with page_worker():audit(int(sys.argv[1]),int(sys.argv[2]))

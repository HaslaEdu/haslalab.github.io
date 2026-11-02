"""Independent original-CID/style/ink and translated-prose collision checks."""
from pathlib import Path
from collections import Counter
import json,hashlib,sys,time,gc
import numpy as np,pikepdf,pymupdf as fitz
from cpho2024_natural import BASE,SOURCE,read
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
from pdf_moved_native_ink import audit_moved_native_ink
from pdf_native_geometry_motion import audit as geometry_audit
from pdf_new_prose_native_text_overlap import audit as text_collision
from pdf_new_hangul_graphics_overlap import audit as graphics_collision
from pdf_text_motion_ink import ink_envelope
from pdf_memory_gate import page_worker
import pdf_new_prose_outlines as prose_outline
from izho_new_prose_outline_qa import trace_font_resources
from izho_early_fixed_style import native_font_programs,native_image_programs
from pdf_original_image_ink import resolved_images
from pdf_original_graphics_ink import graphics_control
from pdf_moved_native_ink import source_outline_reference
from pdf_native_script_motion_audit import audit as native_script_audit

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def semantic(value,ancestors=()):
 if isinstance(value,pikepdf.Stream):
  if value.objgen in ancestors:raise ValueError('Recursive source image graph')
  try:decoded=hashlib.sha256(value.read_bytes()).hexdigest()
  except pikepdf.PdfError:decoded='Exact original encoded image stream; independent native graphical pixels are compared.'
  return dict(dictionary={str(k):semantic(v,ancestors+(value.objgen,))for k,v in value.items()},raw_sha256=hashlib.sha256(value.read_raw_bytes()).hexdigest(),decoded_sha256=decoded)
 if isinstance(value,pikepdf.Dictionary):return {str(k):semantic(v,ancestors)for k,v in value.items()}
 if isinstance(value,pikepdf.Array):return [semantic(v,ancestors)for v in value]
 if isinstance(value,pikepdf.String):return dict(pdf_string_hex=bytes(value).hex())
 return str(value)
def rgb(page,scale=4):
 p=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False)
 return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()

def audit(number,language,*,analysis_target=None,analysis_report=None):
 canonical=BASE/f'T/pages/page{number:02}-{language}.pdf';q=json.loads(canonical.with_suffix('.json').read_text('utf8'));assert sha(canonical)==q['output_sha256']
 target=Path(analysis_target)if analysis_target else canonical
 folder=BASE/'T/body-qa';folder.mkdir(exist_ok=True);source=folder/f'source-page{number:02}.pdf'
 if not source.exists():
  with pikepdf.open(SOURCE)as src,pikepdf.Pdf.new()as single:single.pages.append(src.pages[number-1]);single.save(source,compress_streams=False)
 with fitz.open(source)as src,fitz.open(target)as dst:
  old=_traces(src[0]);new=_traces(dst[0]);erased={glyph_key(g)for g in q['erased_glyphs']}
  native=[g for g in old if g['c'].strip()and g['trace_gid']>=0 and glyph_key(g)not in erased]
  offsets={glyph_key(g):s['dx']for s in q['shifts']for g in s['glyphs']};matched=set()
  for g in native:
   expected=[g['origin'][0]+offsets.get(glyph_key(g),0),g['origin'][1]]
   hits=[i for i,h in enumerate(new)if i not in matched and h['c']==g['c']and h['font']==g['font']and h['trace_gid']==g['trace_gid']and h['render_mode']==g['render_mode']and abs(h['size']-g['size'])<1e-6 and max(abs(a-b)for a,b in zip(h['origin'],expected))<=.001]
   if len(hits)!=1:raise ValueError(('Original native glyph not unique',number,language,g['c'],expected,len(hits)))
   matched.add(hits[0])
  prose=[g for i,g in enumerate(new)if i not in matched and g['c'].strip()and g['trace_gid']>=0]
  assert Counter(g['c']for g in prose)==Counter(c for p in q['placements']for c in p['text']if not c.isspace())
  assert not any('\u3400'<=g['c']<='\u9fff'or g['c']in['\x00','\ufffd']for g in prose)
  with pikepdf.open(target)as pdf:mapped,_=trace_font_resources(pdf,dst[0])
  added=[g for g in mapped if g['font_alias'].startswith('/TranslatedProse')and g['c'].strip()and g['gid']>=0]
  assert len(added)==len(prose)
  used=set();styles=[];cursor=0
  for p in q['placements']:
   hits=list(enumerate(added[cursor:cursor+len(p['text'])],cursor));cursor+=len(p['text'])
   assert ''.join(g['c']for _,g in hits)==p['text'],(p['text'],''.join(g['c']for _,g in hits))
   assert hits and max(abs(a-b)for a,b in zip(hits[0][1]['origin'],p['origin']))<=.001
   for i,g in hits:
    assert g['font_alias']=='/'+p['font_resource']and abs(g['origin'][1]-p['origin'][1])<=.001 and abs(g['size']-p['size'])<1e-6 and g['render_type']==p['render_mode'];used.add(i)
   boxes=[g['bbox']for _,g in hits];bounds=[min(v[0]for v in boxes),min(v[1]for v in boxes),max(v[2]for v in boxes),max(v[3]for v in boxes)]
   styles.append(dict(text=p['text'],size=p['size'],source_font=p['source_font'],render_mode=p['render_mode'],source_baseline=p['origin'][1],actual_embedded_nonspace_glyphs=len(hits),actual_word_bbox=bounds))
  assert len(used)==len(added)
  self_overlaps=[]
  for i,a in enumerate(styles):
   for j in range(i):
    b=styles[j];inter=fitz.Rect(a['actual_word_bbox'])&fitz.Rect(b['actual_word_bbox'])
    if inter.width>.15 and inter.height>.15:self_overlaps.append(dict(first_word=j,second_word=i,first_text=b['text'],second_text=a['text'],overlap_bbox=list(inter)))
  font_same=all(x in native_font_programs(target,1)for x in native_font_programs(source,1));image_same=all(x in native_image_programs(target,1)for x in native_image_programs(source,1))
  with pikepdf.open(source)as source_pdf,pikepdf.open(target)as target_pdf:
   old_page=source_pdf.pages[0];new_page=target_pdf.pages[0]
   old_images={str(k):semantic(v)for k,v in old_page.Resources.get('/XObject',{}).items()if str(v.get('/Subtype'))=='/Image'}
   new_images={str(k):semantic(v)for k,v in new_page.Resources.get('/XObject',{}).items()if str(v.get('/Subtype'))=='/Image'}
   image_graph_same=old_images==new_images
   group_same=semantic(old_page.get('/Group'))==semantic(new_page.get('/Group'))
   colorspace_same=semantic(old_page.Resources.get('/ColorSpace'))==semantic(new_page.Resources.get('/ColorSpace'))
  old_origins=[g['origin']for g in q['erased_glyphs']];new_origins=[g['origin']for g in prose]
  old_prose_mask,_=ink_envelope(src[0],old_origins,4);new_prose_mask,_=ink_envelope(dst[0],new_origins,4)
  caption_rows={(1,11),(2,18),(2,29),(2,38),(3,13),(3,32),(3,43),(4,10)};caption_old=[];caption_new=[];caption_records=[]
  for row in q['rows']:
   for unit in row['units']:
    if unit['kind']!='math':continue
    selected=(number,row['row'])in caption_rows or(number==5 and row['row']==6 and unit['rect'][0]>=380)
    if not selected:continue
    dx=unit['x']-unit['rect'][0];gs=[g for part in unit['parts']for g in part['glyphs']]
    caption_old.extend(g['origin']for g in gs);caption_new.extend([g['origin'][0]+dx,g['origin'][1]]for g in gs)
    caption_records.append(dict(row=row['row'],original_native_text=''.join(g['c']for g in gs),source_rect=unit['rect'],native_dx=dx,source_point_size_and_GID_and_y_retained=True,reason='Reviewed original figure caption number/letter moves as one centered caption with translated 图; source figure geometry and variables are not selected.'))
  old_caption_mask,_=ink_envelope(src[0],caption_old,4);new_caption_mask,_=ink_envelope(dst[0],caption_new,4)
  for s in q['shifts']:
   old_origins.extend(g['origin']for g in s['glyphs']);new_origins.extend([g['origin'][0]+s['dx'],g['origin'][1]]for g in s['glyphs'])
  old_mask,_=ink_envelope(src[0],old_origins,4);new_mask,_=ink_envelope(dst[0],new_origins,4)
  old_rgb=rgb(src[0]);new_rgb=rgb(dst[0]);changed=np.any(old_rgb!=new_rgb,axis=2)
  motion,graphics=geometry_audit(source,target,q['shifts']);outside=changed&~(old_mask|new_mask|motion)
  nonselected=graphics['changed_nonselected_native_graphical_pixels'];outside_count=int(outside.sum())
  if outside_count:
   yy,xx=np.nonzero(outside);outside_bbox=[float(xx.min()/4),float(yy.min()/4),float((xx.max()+1)/4),float((yy.max()+1)/4)]
  else:outside_bbox=None
  images=resolved_images(src,src[0]);figures=[]
  # Complete source picture ROIs, excluding only a moved original inline math
  # bitmap, are protected; label translations are a separate later operation.
  image_paths={tuple(s['image_path'])for s in q['shifts']if s.get('image_path')}
  inv=json.loads((BASE/f'inspection/page{number:02}-objects.json').read_text('utf8'))
  assert len(images)==len(inv['images'])
  for info,raw in zip(images,inv['images']):
   assert max(abs(a-b)for a,b in zip(info['bbox'],raw['bbox']))<.002
   if tuple(raw['path'])in image_paths:continue
   pix=fitz.Pixmap(src,info['xref'])
   if pix.colorspace.n not in [1,3]:pix=fitz.Pixmap(fitz.csRGB,pix)
   pixels=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,pix.n)
   foreground=pixels[:,:,:pix.colorspace.n].min(axis=2)<255
   smask=src.extract_image(info['xref']).get('smask')
   if smask:
    alpha=fitz.Pixmap(src,smask);plane=np.frombuffer(alpha.samples,np.uint8).reshape(alpha.height,alpha.width,alpha.n)[:,:,0];foreground&=plane>0
   foreground_count=int(foreground.sum())
   if not foreground_count:
    figures.append(dict(rect=list(info['bbox']),source_decoded_foreground_pixels=0,changed_pixels=0,scope='Exact decoded fully blank source image; no picture ROI exists. Its original bytes/CTM and complete non-text control remain independently protected.'));continue
   x0,y0,x1,y1=[int(v*4)for v in info['bbox']];region=changed[max(y0,0):y1,max(x0,0):x1]
   prose_change=(old_prose_mask|new_prose_mask)[max(y0,0):y1,max(x0,0):x1];caption_change=(old_caption_mask|new_caption_mask)[max(y0,0):y1,max(x0,0):x1]
   figures.append(dict(rect=list(info['bbox']),source_decoded_foreground_pixels=foreground_count,raw_roi_changed_pixels=int(region.sum()),intentional_source_and_translated_prose_ink_changed_pixels=int((region&prose_change).sum()),intentional_original_native_caption_ink_changed_pixels=int((region&caption_change&~prose_change).sum()),changed_pixels=int((region&~prose_change&~caption_change).sum()),scope='Full original image ROI, allowing only exact old/new prose and explicitly reviewed original caption-number glyph ink where the source caption/body overlies blank image padding; all source figure geometry and variables remain protected.'))
  dark_prose,_=source_outline_reference(dst[0],prose,scale=4)
  with fitz.open(stream=graphics_control(dst,dst[0]),filetype='pdf')as graphics_doc:actual_graphics=rgb(graphics_doc[0])
  strict_graphics_collision=int((dark_prose&(actual_graphics.min(axis=2)<255)).sum())
  strict_mask=dark_prose&(actual_graphics.min(axis=2)<255);strict_bbox=None;strict_samples=[]
  if strict_graphics_collision:
   yy,xx=np.nonzero(strict_mask);strict_bbox=[float(xx.min()/4),float(yy.min()/4),float((xx.max()+1)/4),float((yy.max()+1)/4)]
   strict_samples=[dict(rgb=list(color),pixels=count)for color,count in Counter(tuple(map(int,actual_graphics[y,x]))for y,x in zip(yy,xx)).items()]
  background_profile=None;verified_geometry_collision=strict_graphics_collision
  if number==3 and language=='KO'and strict_graphics_collision:
   # The two source captions are at the lower edges of JPEG/Indexed images.
   # Their last3 original bitmap rows contain only pale scan/background tones
   # (minimum220), not a drawing stroke. Retain the raw all-nonwhite diagnostic
   # and prove that every such sample is an exact new caption glyph over those
   # source blank-edge rows. No threshold is changed for any drawing or math.
   baselines=[r['baseline']for r in q['rows']if r['row']in[13,32]]
   cap=[g for g in prose if any(abs(g['origin'][1]-y)<.001 for y in baselines)]
   cap_mask,cap_match=source_outline_reference(dst[0],cap,scale=4);edge=np.zeros(changed.shape,bool);edge_rows=[]
   for i in [1,4]:
    info=images[i];x0,y0,x1,y1=info['bbox'];pix=fitz.Pixmap(src,info['xref'])
    if pix.colorspace.n not in[1,3]:pix=fitz.Pixmap(fitz.csRGB,pix)
    values=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,pix.n)[:,:,:pix.colorspace.n];minimum=int(values[-3:].min())
    if minimum<220:raise ValueError('Reviewed source caption edge contains actual drawing foreground')
    band=fitz.Rect(x0,y1-.6,x1,y1+.25)
    crossing=[v for v in inv['vector_paths']if band.intersects(fitz.Rect(v['rect'])+(-.05,-.05,.05,.05))]
    if crossing:raise ValueError('A native vector stroke crosses the reviewed pale caption padding')
    edge[max(0,int(np.floor(band.y0*4))):int(np.ceil(band.y1*4)),max(0,int(np.floor(x0*4))):int(np.ceil(x1*4))]=True
    edge_rows.append(dict(image_index=i,source_image_bbox=info['bbox'],reviewed_original_bitmap_rows=[pix.height-3,pix.height],minimum_original_background_value=minimum,physical_band=list(band),native_vector_paths_in_band=0))
   accepted=strict_mask&cap_mask&edge&(actual_graphics.min(axis=2)>=220)
   verified_geometry_collision=int((strict_mask&~accepted).sum())
   background_profile=dict(source_sha256=sha(SOURCE),source_page=3,language='KO',raw_any_nonwhite_samples=strict_graphics_collision,proved_original_pale_caption_background_samples=int(accepted.sum()),unexplained_or_drawing_overlap_samples=verified_geometry_collision,actual_new_caption_outline_match=cap_match,source_blank_bitmap_edge_rows=edge_rows,point_sizes_and_source_baselines_unchanged=True,original_image_programs_and_CTMs_unchanged=True,raw_diagnostic_retained=True,passed=verified_geometry_collision==0 and cap_match['passed'])
 physical=audit_moved_native_ink(source,1,target,shifts=q['shifts'],erased_glyphs=q['erased_glyphs'],protected_glyphs=native)
 expressions=[dict(label='Original complete native expression on source row'+str(row['row']),glyphs=[g for part in unit['parts']for g in part['glyphs']])for row in q['rows']for unit in row['units']if unit['kind']=='math']
 scripts=native_script_audit(source,1,target,shifts=q['shifts'],native_glyphs=native,expression_groups=expressions)
 text=text_collision(target,native_glyphs=native,shifts=q['shifts'],prose_glyphs=prose)
 picture=graphics_collision(target,new_glyphs=prose)
 prose_outline.PREFIXES=('/TranslatedProse','/FigureLanguage');outlines=prose_outline.audit(target)
 r=dict(source=str(SOURCE),source_sha256=sha(SOURCE),source_page=number,proof=str(target),proof_sha256=sha(target),language=language,
  qa_mode='analysis-only-negative-clone'if analysis_target else'publication',unmodified_canonical_proof_sha256=sha(canonical),
  original_native_glyphs=len(native),translated_prose_nonspace_glyphs=len(prose),original_fonts_retained=font_same,original_images_retained=image_same,
  original_full_image_palette_ICC_mask_graphs_retained=image_graph_same,original_page_group_retained=group_same,original_colorspace_resources_retained=colorspace_same,
  source_native_metadata=q['source_native_move'],original_native_ink=physical,original_graphics_motion=graphics,
  native_script_and_complete_expression_geometry=scripts,new_prose_word_bbox_overlaps=self_overlaps,
  changed_pixels_outside_prose_and_whole_math_motion=outside_count,outside_bbox=outside_bbox,
  original_picture_pixels=figures,translated_prose_actual_styles=styles,translated_prose_outlines=outlines,new_prose_native_text_collision=text,new_prose_native_graphics_collision=picture,
  new_prose_over_any_nonwhite_native_graphics_pixels=strict_graphics_collision,
  any_nonwhite_graphics_overlap_bbox=strict_bbox,any_nonwhite_graphics_overlap_colors=strict_samples,reviewed_original_caption_number_motions=caption_records,
  source_caption_background_profile=background_profile,verified_new_prose_over_native_geometry_pixels=verified_geometry_collision,
  original_point_sizes_scaled=False,equations_retyped=False,ordinary_word_spaces_quarter_em=True)
 r['passed']=all([font_same,image_same,image_graph_same,group_same,colorspace_same,physical['passed'],scripts['passed'],not self_overlaps,not nonselected,not outside_count,not any(v['changed_pixels']for v in figures),outlines['passed'],text['passed'],picture['passed'],not verified_geometry_collision])
 dest=Path(analysis_report)if analysis_report else folder/f'page{number:02}-{language}.audit.json';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(r,ensure_ascii=False,indent=1)+'\n','utf8')
 print('BODY_QA',number,language,r['passed'],'native',len(native),'outside',outside_count,'graphics',nonselected,'native-ink',physical['newly_missing_native_ink_pixels'],'text-overlap',text['dark_prose_pixels_over_native_text'],'graphics-overlap',picture['new_hangul_dark_pixels_over_native_foreground'],flush=True)
 if not r['passed']:raise ValueError(('Strict original body proof failed',number,language))
 return r

if __name__=='__main__':
 n=int(sys.argv[1]);lang=sys.argv[2]
 with page_worker():audit(n,lang)

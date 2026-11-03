"""Source-only white-padding layout profile; the full picture stays protected."""
from pathlib import Path
import hashlib,pymupdf as f,numpy as np
def apply_reviewed_layout(plan):
 if plan['source_page']not in[3,9,10]:return
 assert plan['original_english_source_sha256']=='ecc4a34a50fade6a08fd5f629480bebfa20ec418cdc19fa87915f6c0465ee008'
 source=Path(plan['original_english_source']);assert hashlib.sha256(source.read_bytes()).hexdigest()==plan['original_english_source_sha256']
 with f.open(source)as d:
  page_number=plan['source_page'];p=d[page_number-1];info=p.get_image_info()[0];xref=p.get_images(full=True)[0][0];pix=f.Pixmap(f.csRGB,f.Pixmap(d,xref));a=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,pix.n)[:,:,:3]
  if page_number in[9,10]:
   from izho_initial_fixed_style import runs_of
   import math
   at=(65,0,0)if page_number==9 else(18,0,0);counter='1'if page_number==9 else'2';run=runs_of(p)[at];assert run['text'].strip()=='Fig.'+counter
   box=list(info['bbox']);r=f.Rect(run['bbox']);hole=[max(box[0],r.x0-10),max(box[1],run['origin'][1]-12),min(box[2],r.x1+10),box[3]]
   px=[max(0,math.floor((hole[0]-box[0])*pix.width/(box[2]-box[0]))),max(0,math.floor((hole[1]-box[1])*pix.height/(box[3]-box[1]))),min(pix.width,math.ceil((hole[2]-box[0])*pix.width/(box[2]-box[0]))),pix.height]
   x0,y0,x1,y1=px;foreground=int(np.any(a[y0:y1,x0:x1]!=255,axis=2).sum());assert foreground==0,('Caption layout-only aperture must contain no source bitmap foreground',page_number,hole,px,foreground)
   pieces=[[box[0],box[1],box[2],hole[1]],[box[0],hole[1],hole[0],box[3]],[hole[2],hole[1],box[2],box[3]]];pieces=[r for r in pieces if f.Rect(r).width>0 and f.Rect(r).height>0]
   assert box in plan['excluded_figure_rects'];plan['reviewed_layout_figure_rects']=[part for old in plan['excluded_figure_rects']for part in(pieces if old==box else[old[:]])]
   scopes=[s for s in plan['source_line_scopes']if s['source_at']==list(at[:2])];assert len(scopes)==1
   old_rect=scopes[0]['rect'][:];new_rect=[hole[0],old_rect[1],hole[2],old_rect[3]]
   plan['allowed_line_rects']=[new_rect[:]if r==old_rect else r for r in plan['allowed_line_rects']]
   for item in plan['source_line_scopes']+plan['centered_lines']+plan['right_aligned_lines']:
    if item.get('rect')==old_rect:item['rect']=new_rect[:]
   plan['reviewed_native_figure_language_labels']=[dict(reviewed=True,source_sha256=plan['original_english_source_sha256'],at=list(at),text='그림',original_native_counter=counter,source_kind='Original native caption text printed over white bitmap padding; original counter stays native.')]
   plan['reviewed_original_picture_white_padding']=dict(source_sha256=plan['original_english_source_sha256'],source_image_raw_stream_sha256=hashlib.sha256(d.xref_stream_raw(xref)).hexdigest(),source_image_dimensions_px=[pix.width,pix.height],source_image_bbox=box,caption_source_at=list(at),layout_only_white_aperture=hole,source_raw_RGB_aperture_pixels=px,source_bitmap_nonwhite_aperture_pixels=foreground,actual_picture_program_or_pixels_changed=False,full_original_picture_rectangle_still_used_for_zero_difference_QA=True,reason='The original Fig.n caption is independent PDF text printed over pure-white bitmap padding. Only this source-verified empty aperture is open for caption layout. Full figure QA excludes only actual old/new caption glyph ink, verifies the exact original counter font/GID/point/paint/y and x-only motion, and protects every nonlanguage bitmap pixel at zero difference.')
   return
  rows=np.flatnonzero(np.any(a!=255,axis=(1,2)));assert int(rows[0])==13 and np.all(a[:13]==255)
  box=list(info['bbox']);assert max(abs(a-b)for a,b in zip(box,[71.99998474121094,87.949951171875,488.14990234375,531.9497680664062]))<.001
  padding=13*(box[3]-box[1])/pix.height;layout=box[:];layout[1]+=padding/2
  assert box in plan['excluded_figure_rects'];plan['reviewed_layout_figure_rects']=[layout[:]if r==box else r[:]for r in plan['excluded_figure_rects']]
  plan['reviewed_original_picture_white_padding']=dict(source_sha256=plan['original_english_source_sha256'],source_image_raw_stream_sha256=hashlib.sha256(d.xref_stream_raw(xref)).hexdigest(),source_image_dimensions_px=[pix.width,pix.height],source_image_bbox=box,all_RGB_white_top_rows=13,measured_top_white_padding_pt=padding,layout_only_rectangle=layout,actual_picture_program_or_pixels_changed=False,full_original_picture_rectangle_still_used_for_zero_difference_QA=True,reason='The original14.04pt heading font metric boxes touch only the picture bitmap white top padding. Retain all heading numerals and punctuation in the same natural centered line. Exclude half of the independently measured white padding for layout only; every image pixel, its CTM, actual drawing ink and the other half of the white padding remain protected.')

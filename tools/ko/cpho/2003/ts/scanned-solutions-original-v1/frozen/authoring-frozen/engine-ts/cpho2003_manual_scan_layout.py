"""Manually selected source language/math regions; source-only physical measurements.

Nothing here recognizes prose or infers an erasure from translated text. Every
erase/atom/cell rectangle is explicitly supplied by the human-reviewed driver.
"""
from pathlib import Path
import json,math,hashlib
import numpy as np
from PIL import Image
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from pdf_native_inline_reposition import inspect_inline_groups
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');T=B/'TS'
SOURCE=B/'inputs/CPhO_2003_Chinese_original.pdf';SHA='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63'
class ManualPage:
 def __init__(self,number):
  assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
  self.number=number;self.rows=[];self.images={};self.fonts={}
  inv=inspect_inline_groups(SOURCE,number)
  reads=[r for r in json.loads((T/'source-image-reading/image-reading-index.json').read_text('utf8'))if r['page']==number]
  for index,(paint,reading)in enumerate(zip(inv['images'],reads),1):
   assert len(inv['images'])==len(reads)
   self.images[index]=dict(bbox=paint['bbox'],path=paint['path'],width=reading['width'],height=reading['height'],file=Path(reading['path']),array=np.array(Image.open(reading['path']).convert('L')))
 def rect(self,image,box):
  im=self.images[image];b=im['bbox'];x,y,r,z=box
  return[b[0]+x*(b[2]-b[0])/im['width'],b[1]+y*(b[3]-b[1])/im['height'],b[0]+r*(b[2]-b[0])/im['width'],b[1]+z*(b[3]-b[1])/im['height']]
 def measure(self,image,char,cell,size,face):
  if face not in self.fonts:
   path=Path('D:/CodexBuilds/Hasla-original-style-20261031/english-face-repair/font-faces/SimSun-5.24.ttf')if face=='SimSun'else Path('D:/CodexBuilds/Hasla-original-style-20261031/official-hans-fonts/faces/simhei.ttf')
   self.fonts[face]=(TTFont(path),path)
  font,path=self.fonts[face];gs=font.getGlyphSet();p=BoundsPen(gs);gs[font.getBestCmap()[ord(char)]].draw(p);x0,y0,x1,y1=p.bounds;em=font['head'].unitsPerEm
  im=self.images[image];x,y,r,z=cell;yy,xx=np.where(im['array'][y:z,x:r]<100);assert len(xx)
  lo,top,hi,bottom=int(xx.min()+x),int(yy.min()+y),int(xx.max()+x+1),int(yy.max()+y+1)
  ink=self.rect(image,[lo,top,hi,bottom]);left=(ink[0]-x0/em*size+ink[2]-x1/em*size)/2;baseline=(ink[1]+y1/em*size+ink[3]+y0/em*size)/2
  return dict(source_char=char,manual_source_cell_raw_pixels=cell,actual_original_ink_box_raw_pixels=[lo,top,hi,bottom],original_source_image_sha256=hashlib.sha256(im['file'].read_bytes()).hexdigest(),fixed_original_point=size,source_full_face_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source_original_advance_origin_x=left,independent_source_baseline_estimate=baseline,source_top_bottom_baseline_estimate_spread_pt=abs(ink[1]+y1/em*size-ink[3]-y0/em*size),method='Only manually identified original Chinese glyph ink and original-size source-family contour bounds; no translated width/shape/fitting.')
 def atom(self,image,id,box,pieces=None):
  v=self.rect(image,box);b=self.images[image]['bbox']
  def aligned(v):return[max(b[0],math.floor(v[0]*4)/4),max(b[1],math.floor(v[1]*4)/4),min(b[2],math.ceil(v[2]*4)/4),min(b[3],math.ceil(v[3]*4)/4)]
  a=dict(id=id,rect=aligned(v),image_path=self.images[image]['path'],manually_reviewed_source_pixels=box,reason='Complete manually read original symbol/expression/number, including scripts; original encoded image/clip/CTM/scale/y retained. Only whole-expression page-horizontal translation is allowed.')
  if pieces:a['paint_pieces']=[aligned(self.rect(image,p))for p in pieces]
  return a
 def row(self,id,image,box,char,cell,source,ko,en,atoms=(),size=10.5,face='SimSun',left=None,right=None,first_known_char_is_first_token=True):
  m=self.measure(image,char,cell,size,face);v=self.rect(image,box)
  r=dict(id=id,reviewed=True,source=source,ko=ko,en=en,size=size,source_prose_face=face,render_mode=0,baseline=m['independent_source_baseline_estimate'],left=m['source_original_advance_origin_x']if left is None and first_known_char_is_first_token else v[0]if left is None else left,right=self.images[image]['bbox'][2]if right is None else right,erase_rects=[v],source_atom_ids=[a['id']for a in atoms],atoms=list(atoms),independent_original_baseline_measurement=m)
  import re
  assert sorted(re.findall(r'\[\[([^\]]+)\]\]',ko))==sorted(r['source_atom_ids']),id
  assert sorted(re.findall(r'\[\[([^\]]+)\]\]',en))==sorted(r['source_atom_ids']),id
  r['whole_original_image_expression_pixel_grid']=True
  r['exact_manual_prose_region_before_antialias_support_margin']=v
  r['erase_rects']=[[math.floor(v[0]*2)/2,math.floor(v[1]*2)/2,math.ceil(v[2]*2)/2,math.ceil(v[3]*2)/2]]
  r['manual_prose_erase_edge_review']='Outward0.5pt grid covers the actual original prose antialias support at scan boundaries, with no math/figure/font/point/scale change.'
  self.rows.append(r);return r
 def footer(self):
  p=T/f'authoring/page{self.number:02}.json';assert not p.exists()
  p.write_text(json.dumps(dict(source_page=self.number,source_sha256=SHA,native_headers=[dict(source_slot=f'{self.number}-full-footer',source_prose_face='SimSun',translations=dict(ko=f'{self.number-3} / 7쪽',en=f'Page {self.number-3} of 7'))],original_source_folio_digits_font_points_and_y_retained=True),ensure_ascii=False,indent=2)+'\n','utf8')
 def save(self,protected):
  q=dict(source_page=self.number,source_sha256=SHA,manual_rois_reviewed=True,publication_ready=False,rows=self.rows,protected_source_display_and_figure_rects=protected,reviewed_blank_background_rects=[],all_original_math_and_figures_native_image_programs_preserved=True,original_prose_points_independently_measured=True)
  p=T/f'authoring/page{self.number:02}-layout.json';assert not p.exists();p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');self.footer();return q

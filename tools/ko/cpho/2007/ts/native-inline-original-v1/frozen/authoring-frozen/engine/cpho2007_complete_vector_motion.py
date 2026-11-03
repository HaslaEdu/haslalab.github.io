"""Exact-object stroke controls for CPhO2007 page6's 16 native radical paths.

Line-center bounding boxes omit the original stroke's cap/miter ink. This
read-only audit uses only actual painted ink of the identified original path
objects; it never admits a widened prose rectangle or changes any threshold.
"""
from io import BytesIO
import hashlib,re
import numpy as np
import cv2
import pymupdf as f
import pikepdf
from pdf_native_inline_reposition import inspect_inline_groups
from pdf_original_graphics_ink import graphics_control

def _close(a,b,tol=.001):return len(a)==len(b)and all(abs(x-y)<=tol for x,y in zip(a,b))
def _rgb(raw,scale):
 with f.open(stream=raw,filetype='pdf')as d:
  p=d[0].get_pixmap(matrix=f.Matrix(scale,scale),colorspace=f.csRGB,alpha=False)
  return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()

def _only_selected_path_ink(raw,selected):
 with pikepdf.open(BytesIO(raw))as d:
  page=d.pages[0];parsed=pikepdf.parse_content_stream(page)
  assert all(str(parsed[i].operator)=='S'for i in selected)
  class Tokens(pikepdf.TokenFilter):
   def __init__(self):super().__init__();self.items=[]
   def handle_token(self,t):self.items.append((t.type_,t.raw_value));return t
  collector=Tokens();content=page.get_filtered_contents(collector);regions=[];offset=start=0
  for kind,value in collector.items:
   offset+=len(value)
   if kind==pikepdf.TokenType.inline_image:raise ValueError('Unexpected inline image in exact radical control')
   if kind==pikepdf.TokenType.word:regions.append((start,offset,value.decode('ascii')));start=offset
  assert len(parsed)==len(regions)and all(str(i.operator)==r[2]for i,r in zip(parsed,regions))
  parts=[];position=0;paint={'S','s','f','F','f*','B','B*','b','b*'}
  for i,(a,z,op)in enumerate(regions):
   if op not in paint or i in selected:continue
   prefix=re.match(rb'\s*',content[a:z])[0];parts.extend([content[position:a],prefix,b'n']);position=z
  parts.append(content[position:]);page.Contents=d.make_stream(b''.join(parts));buffer=BytesIO();d.save(buffer,compress_streams=False);return buffer.getvalue()

def audit(source,target,shifts,scale=4):
 old_inv=inspect_inline_groups(source,1);new_inv=inspect_inline_groups(target,1)
 if old_inv['forms']or old_inv['images']or new_inv['forms']or new_inv['images']:
  raise ValueError('CPhO2007 page6 exact radical profile must remain native top-level paths only')
 selected=[(path,shift['dx'])for shift in shifts for path in shift.get('vector_paths',[])]
 assert len(selected)==16,('The complete four original radicals require exactly16 source path strokes',len(selected))
 old_paints=set();new_paints=set();records=[]
 with pikepdf.open(source)as a,pikepdf.open(target)as b,f.open(source)as ad,f.open(target)as bd:
  aops=pikepdf.parse_content_stream(a.pages[0]);bops=pikepdf.parse_content_stream(b.pages[0]);adraw=ad[0].get_drawings();bdraw=bd[0].get_drawings()
  for path,dx in selected:
   before=[p for p in old_inv['vector_paths']if p['operator_indices']==path['operator_indices']and _close(p['rect'],path['rect'])]
   assert len(before)==1 and before[0]['paint_operator']=='S'
   expected=[v+(dx if i in[0,2]else 0)for i,v in enumerate(path['rect'])]
   after=[p for p in new_inv['vector_paths']if _close(p['rect'],expected)]
   assert len(after)==1 and after[0]['paint_operator']=='S',('Original radical segment absent or not at declared dx',path,expected)
   after=after[0]
   av=pikepdf.unparse_content_stream([aops[i]for i in path['operator_indices']]);bv=pikepdf.unparse_content_stream([bops[i]for i in after['operator_indices']]);assert av==bv,'Original radical path operands or paint operator changed'
   old_style=[v for v in adraw if _close(list(v['rect']),path['rect'])];new_style=[v for v in bdraw if _close(list(v['rect']),expected)];assert len(old_style)==len(new_style)==1
   stylekeys=['type','width','color','fill','dashes','lineCap','lineJoin','closePath','stroke_opacity','fill_opacity','even_odd']
   sa={k:old_style[0].get(k)for k in stylekeys};sb={k:new_style[0].get(k)for k in stylekeys};assert sa==sb,('Original radical stroke style changed',sa,sb)
   oi=path['operator_indices'][-1];ni=after['operator_indices'][-1];assert oi not in old_paints and ni not in new_paints;old_paints.add(oi);new_paints.add(ni)
   records.append(dict(kind='exact original radical stroke object',rect=path['rect'],dx=dx,operator_indices=path['operator_indices'],target_operator_indices=after['operator_indices'],path_program_sha256=hashlib.sha256(av).hexdigest(),path_operands_and_paint_unchanged=True,stroke_style=sa,stroke_style_unchanged=True))
  old_control=graphics_control(ad,ad[0]);new_control=graphics_control(bd,bd[0])
 old=_rgb(old_control,scale);new=_rgb(new_control,scale)
 old_selected=_rgb(_only_selected_path_ink(old_control,old_paints),scale);new_selected=_rgb(_only_selected_path_ink(new_control,new_paints),scale)
 old_ink=old_selected.min(axis=2)<255;new_ink=new_selected.min(axis=2)<255
 motion=cv2.dilate((old_ink|new_ink).astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool);changed=np.any(old!=new,axis=2)
 outside=int((changed&~motion).sum())
 report=dict(method='Exact original radical path objects: identical native path operands/paint/stroke style, declared horizontal dx, and actual selected-only stroke controls; all other non-text pixels must remain identical.',selected_native_math_groups=records,changed_actual_inline_math_graphical_pixels=int((changed&motion).sum()),changed_nonselected_native_graphical_pixels=outside,original_native_math_actual_graphics_pixels=int(old_ink.sum()),new_native_math_actual_graphics_pixels=int(new_ink.sum()),actual_selected_path_paint_objects_only=True,no_metric_bbox_cropping=True,no_rectangle_or_threshold_exception=True)
 return motion,report

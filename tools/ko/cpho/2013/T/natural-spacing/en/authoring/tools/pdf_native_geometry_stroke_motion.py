"""Use real source stroke footprints in the existing native-motion audit.

The old path-geometry rectangle is a centerline, not its stroke bounds. Only
an exactly identified reviewed source path receives symmetric half-width and
one raster-pixel AA support. All nonselected controls remain pixel-exact.
"""
from copy import deepcopy
import math
import pymupdf as fitz
import pdf_native_geometry_motion as legacy
from pdf_native_inline_reposition import inspect_inline_groups

def audit(source,target,shifts,scale=4):
 if not isinstance(scale,(int,float))or not math.isfinite(scale)or scale<=0:raise ValueError('Positive finite raster scale required')
 inv=inspect_inline_groups(source,1)
 with fitz.open(source)as doc:drawings=doc[0].get_drawings()
 revised=deepcopy(shifts);witnesses=[]
 for shift in revised:
  for path in shift.get('vector_paths',[]):
   exact=[p for p in inv['vector_paths']if p['operator_indices']==path['operator_indices']and all(abs(a-b)<.001 for a,b in zip(p['rect'],path['rect']))]
   if len(exact)!=1:raise ValueError('Selected native stroke is not the exact original operator path')
   if exact[0]['paint_operator']not in('S','s'):raise ValueError('A filled native path needs its own exact-ink profile')
   matches=[d for d in drawings if 's'in d['type']and all(abs(a-b)<.001 for a,b in zip(d['rect'],path['rect']))]
   if len(matches)!=1:raise ValueError('Selected native path has no unique original drawing-state witness')
   d=matches[0];width=d.get('width')
   if width is None or not math.isfinite(width)or width<0:raise ValueError('Native path actual page-space stroke width is unknown')
   # PDF hairline width0 is device-pixel sized; no font/path is rewritten.
   half=width/2 if width else .5/scale;pad=half+1/scale
   center=list(path['rect']);foot=list(fitz.Rect(center)+(-pad,-pad,pad,pad));path['rect']=foot
   witnesses.append(dict(operator_indices=path['operator_indices'],original_centerline_rect=center,
    actual_source_stroke_width_pt=width,source_linecap=d.get('lineCap'),source_linejoin=d.get('lineJoin'),
    source_stroke_opacity=d.get('stroke_opacity'),source_stroke_color=d.get('color'),
    original_source_paint_operator=exact[0]['paint_operator'],dx=shift['dx'],native_stroke_footprint=foot,
    AA_support_pixels=1,original_program_bytes_and_CTM_unchanged=True))
 motion,report=legacy.audit(source,target,revised,scale)
 report['selected_original_path_stroke_witnesses']=witnesses
 report['stroke_footprint_policy']='Unique original operator path + original page-space drawing width/2 + one raster pixel, symmetric; actual control ink only. All nonselected graphics retain the unchanged strict pixel test.'
 return motion,report

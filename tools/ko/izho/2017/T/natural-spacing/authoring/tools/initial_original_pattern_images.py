"""Resolve actual Image Do paints inside original stationary tiling patterns.

The common resolver owns ordinary image/Form paints. This private profile also
traces a selected colored tiling pattern at its actual fill operation. It
verifies each full image CTM/dimension against the renderer, without editing or
promoting any pattern, image or mathematical object in the delivered PDF.
"""
from pathlib import Path
from io import BytesIO
import math
import pikepdf
from pdf_original_image_ink import resolved_images as ordinary_images

IDENTITY=(1.,0.,0.,1.,0.,0.)
def mul(a,b):
 x,y,z,w,e,f=a;A,B,C,D,E,F=b
 return(x*A+y*C,x*B+y*D,z*A+w*C,z*B+w*D,e*A+f*C+E,e*B+f*D+F)
def box(m):
 a,b,c,d,e,f=m;points=[(a*x+c*y+e,b*x+d*y+f)for x,y in[(0,0),(1,0),(0,1),(1,1)]]
 return[min(p[0]for p in points),min(p[1]for p in points),max(p[0]for p in points),max(p[1]for p in points)]
def resolved_images(doc,page):
 try:return ordinary_images(doc,page)
 except ValueError as error:
  if str(error)!='Image paint order cannot be proved':raise
 result=[dict(item)for item in page.get_image_info(xrefs=True)];painted=[];patterns=[];pm=tuple(page.transformation_matrix)
 source=doc.name if doc.name and Path(doc.name).is_file()else BytesIO(doc.tobytes(garbage=0))
 with pikepdf.open(source)as pdf:
  def walk(node,res,ctm=IDENTITY,path=(),ancestors=(),is_pattern=False):
   if len(ancestors)>20:raise ValueError('Excessive original image nesting')
   stack=[];space=None;pattern=None
   for i,o in enumerate(pikepdf.parse_content_stream(node)):
    op=str(o.operator);v=o.operands
    if op=='q':stack.append((ctm,space,pattern))
    elif op=='Q':
     if not stack:raise ValueError('Unbalanced original graphics state')
     ctm,space,pattern=stack.pop()
    elif op=='cm':ctm=mul(tuple(map(float,v)),ctm)
    elif op=='cs':space=str(v[0]);pattern=None
    elif op=='scn':
     if space=='/Pattern':pattern=str(v[-1])
    elif op=='Do':
     child=res.get('/XObject',{}).get(v[0])
     if child is None:raise ValueError('Missing actual Image/Form')
     subtype=str(child.get('/Subtype'));current=path+(i,)
     if subtype=='/Image':painted.append(dict(xref=child.objgen[0],path=list(current),bbox=box(mul(ctm,pm)),width=int(child.Width),height=int(child.Height),pattern=bool(is_pattern),pattern_lattice=is_pattern or None))
     elif subtype=='/Form':
      if child.objgen in ancestors:raise ValueError('Recursive original Form')
      walk(child,child.get('/Resources',res),mul(tuple(map(float,child.get('/Matrix',IDENTITY))),ctm),current,ancestors+(child.objgen,),is_pattern)
    elif op in ('f','f*','B','B*','b','b*')and pattern:
     child=res.get('/Pattern',{}).get(pattern)
     if child is None or int(child.get('/PatternType',0))!=1 or int(child.get('/PaintType',0))!=1:raise ValueError('Unsupported original pattern paint')
     if is_pattern:raise ValueError('Nested image patterns require independent review')
     bounds=list(map(float,child.BBox))
     if bounds[:2]!=[0.,0.]or abs(float(child.XStep)-bounds[2])>.001 or abs(float(child.YStep)-bounds[3])>.001:raise ValueError('Only one complete original pattern tile is reviewed')
     matrix=tuple(map(float,child.Matrix))
     if matrix[1]!=0 or matrix[2]!=0 or matrix[0]<=0 or matrix[3]<=0:raise ValueError('Rotated/skewed source pattern needs a separate review')
     lattice=dict(x_step_pt=float(child.XStep)*matrix[0],y_step_pt=float(child.YStep)*matrix[3],matrix=list(matrix))
     patterns.append((pattern,i));walk(child,child.Resources,matrix,path+(i,-1),ancestors+(child.objgen,),lattice)
  p=pdf.pages[page.number];walk(p,p.Resources)
 if not patterns or len(painted)!=len(result):raise ValueError('Complete original Image/Pattern paint count cannot be proved')
 for item,raw in zip(result,painted):
  if raw['pattern']:
   # MuPDF reports a periodic tile occurrence, which can differ by an exact
   # integer pattern step from its base Image Do. Derive and verify that tile
   # offset explicitly; the original pattern program/Matrix and actual source
   # and final figure pixels are independently compared by the caller.
   lattice=raw['pattern_lattice'];dx=item['bbox'][0]-raw['bbox'][0];dy=item['bbox'][1]-raw['bbox'][1]
   ix=round(dx/lattice['x_step_pt']);iy=round(dy/lattice['y_step_pt'])
   if abs(dx-ix*lattice['x_step_pt'])>.002 or abs(dy-iy*lattice['y_step_pt'])>.002:raise ValueError('Rendered pattern occurrence is not on its original exact tile lattice')
   raw['bbox']=[raw['bbox'][0]+dx,raw['bbox'][1]+dy,raw['bbox'][2]+dx,raw['bbox'][3]+dy]
   item['original_pattern_tile_offset']=[ix,iy];item['original_pattern_matrix']=lattice['matrix']
  if(item['width'],item['height'])!=(raw['width'],raw['height'])or max(abs(a-b)for a,b in zip(item['bbox'],raw['bbox']))>.002:raise ValueError(('Original pattern Image Do CTM/dimensions disagree with renderer',item['bbox'],raw))
  item['mupdf_cached_xref']=item['xref'];item['xref']=raw['xref'];item['original_paint_path']=raw['path'];item['xref_resolved_from_original_Do']=True;item['original_stationary_pattern_image']=raw['pattern']
 return result

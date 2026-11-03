"""Read actual embedded glyph curves under the actual PDF text/shear matrix.

The native motion reader still performs every original code/GID/charset/font
guard. Only this read-only inspector computes curve extrema after the matrix,
instead of transforming an axis-aligned glyph box. Native composition bounds
and source/math motion algorithms are unchanged.
"""
import hashlib
from io import BytesIO
from functools import lru_cache
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
import pikepdf
import natural_plan_compose_icho2024_style as c
from native_ink_bounds import SourceOutlineReader,_program,_mul

@lru_cache(maxsize=8)
def otf_program(raw):
 font=TTFont(BytesIO(raw));assert 'CFF 'in font
 top=font['CFF '].cff.topDictIndex[0];assert 'ROS'in top.rawDict
 return font,top,font.getGlyphSet(),tuple(font.getGlyphOrder()),tuple(map(float,top.FontMatrix))

class ActualCurveReader(SourceOutlineReader):
 def __init__(self,source):super().__init__();self.records={}
 def measure(self,font,code,cluster,state,text_matrix,page_matrix):
  actual=cluster[0];gid=actual['trace_gid'];face=font.get('/DescendantFonts',[font])[0];desc=face.get('/FontDescriptor',{})
  is_otf='/FontFile3'in desc and str(desc.FontFile3.get('/Subtype'))=='/OpenType'
  if is_otf:
   if str(font.get('/Subtype'))!='/Type0'or str(face.get('/Subtype'))!='/CIDFontType0'or str(font.get('/Encoding'))!='/Identity-H':raise ValueError('Unsupported actual embedded OpenType prose font profile')
   raw=desc.FontFile3.read_bytes();kind='OpenTypeCFFCID';otf,top,glyphs,order,matrix=otf_program(raw)
   if gid!=code or not 0<=gid<len(order):raise ValueError('Actual embedded OpenType encoded CID/trace GID mismatch')
   name='.notdef'if code==0 else f'cid{code:05d}'
   if order[gid]!=name or top.CharStrings.charStrings.get(name)!=gid:raise ValueError('Actual embedded OpenType CID/charset/CharString index mismatch')
   if len(cluster)!=1 or otf.getGlyphID(otf.getBestCmap()[ord(actual['c'])])!=gid:raise ValueError('Actual embedded OpenType Unicode/encoded CID/actual GID mapping differs')
   fd=top.FDArray[top.FDSelect[gid]]
   if 'FontMatrix'in fd.rawDict:raise ValueError('Actual embedded OpenType explicit FD matrix needs its own exact profile')
  else:super().measure(font,code,cluster,state,text_matrix,page_matrix)
  if is_otf:pass
  elif str(font.get('/Subtype'))=='/Type1'and '/FontFile'in desc:kind='Type1';raw=desc.FontFile.read_bytes()
  elif '/FontFile2'in desc:kind='TrueType';raw=desc.FontFile2.read_bytes()
  elif '/FontFile3'in desc and str(desc.FontFile3.get('/Subtype'))=='/CIDFontType0C':kind='CFFCID';raw=desc.FontFile3.read_bytes()
  elif '/FontFile3'in desc and str(desc.FontFile3.get('/Subtype'))=='/Type1C':kind='CFFType1';raw=desc.FontFile3.read_bytes()
  else:raw,kind=self.source_renderer.resolve(font)
  if not is_otf:
   program,glyphs,order,matrix=_program(raw,kind);name=('.notdef'if code==0 else f'cid{code:05d}')if kind=='CFFCID'else order[gid]
  tf=float(state['tf']);th=float(state['th'])
  for mat in[(tf*th,0,0,tf,0,0),text_matrix,state['ctm'],page_matrix]:
   a,b,z,d,_,_=map(float,mat);matrix=_mul(matrix,(a,b,z,d,0,0))
  a,b,z,d,_,_=matrix;x,y=actual['origin'];pen=BoundsPen(glyphs);transform=TransformPen(pen,(a,b,z,d,x,y));glyphs[name].draw(transform)
  self.records[c.ops.glyph_key(actual)]=dict(glyph=actual,actual_font_linear_matrix_page_coordinates=[a,b,z,d],actual_shear_tangent=z/-d if abs(d)>1e-15 and abs(b)<1e-15 else None,actual_font_program_sha256=hashlib.sha256(raw).hexdigest(),actual_font_program_kind=kind)
  if pen.bounds is None:
   if not all(v['c'].isspace()for v in cluster):raise ValueError('Actual painted prose glyph has no curve outline')
   return[x,y,x,y]
  return list(pen.bounds)

def measure(raw,glyphs,with_matrices=False):
 reader=ActualCurveReader(raw)
 inv=c.motion.reposition_inline(raw,1,_inspect_only=True,_inspect_ink_glyphs=glyphs,_outline_reader=reader)
 result={}
 for item in inv['native_ink_bounds']:
  for glyph in item['glyphs']:
   key=c.ops.glyph_key(glyph);r=item['bbox']
   if key not in result:result[key]=r
   else:
    old=result[key];result[key]=[min(old[0],r[0]),min(old[1],r[1]),max(old[2],r[2]),max(old[3],r[3])]
 return(result,reader.records)if with_matrices else result

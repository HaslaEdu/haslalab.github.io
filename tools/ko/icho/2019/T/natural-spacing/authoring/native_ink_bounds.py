"""Read embedded or directly source-resolved outlines; never alter PDF text.

measure_native_ink_bounds(source, page_number, glyphs, inventory=None) returns
{glyph_key: [x0,y0,x1,y1]} in displayed page points. Source records must come
from get_texttrace (including exact ligature continuation records). Bounds are
for the original encoded glyph, not its Unicode substitute. No guessed font,
bitmap inference, synthesized glyph, or guessed physical font size is used.
"""
from io import BytesIO
from pathlib import Path
from functools import lru_cache
import hashlib,math
import pikepdf
from fontTools.t1Lib import T1Font
from fontTools.ttLib import TTFont
from fontTools.cffLib import CFFFontSet
from fontTools.pens.boundsPen import BoundsPen
from fontTools.agl import UV2AGL
from pdf_latex_text_ops import glyph_key,cmap

def _mul(a,b):
 x,y,z,w,e,f=a;A,B,C,D,E,F=b
 return(x*A+y*C,x*B+y*D,z*A+w*C,z*B+w*D,e*A+f*C+E,e*B+f*D+F)

@lru_cache(maxsize=32)
def _program(raw,kind):
 if kind in {'CFFCID','CFFType1'}:
  cff=CFFFontSet();cff.decompile(BytesIO(raw),None)
  if len(cff.fontNames)!=1:raise ValueError('Original CFF must contain exactly one font')
  top=cff[cff.fontNames[0]];order=tuple(top.charset)
  if not order or order[0]!='.notdef'or len(set(order))!=len(order):raise ValueError('Invalid original CFF charset/GID order')
  if (kind=='CFFCID')!=('ROS'in top.rawDict):raise ValueError('Original CFF CID/name profile mismatch')
  if int(getattr(top,'CharstringType',2))!=2:raise ValueError('Unsupported original CFF CharstringType')
  matrix=tuple(map(float,top.FontMatrix))
  return top,top.CharStrings,order,matrix
 if kind=='Type1':
  font=T1Font.__new__(T1Font);font.data=raw;font.encoding='ascii';font.parse()
  glyphs=font['CharStrings'];order=list(glyphs)
  if not order or order.count('.notdef')!=1:raise ValueError('Outline bounds require one explicit Type1 .notdef/GID order')
  # FreeType's Type1 face swaps .notdef into slot zero; it does not
  # prepend .notdef and renumber every glyph. Verify this original named
  # glyph order against the encoded name and MuPDF GID for every request.
  missing=order.index('.notdef');order[0],order[missing]=order[missing],order[0];order=tuple(order)
  matrix=tuple(map(float,font['FontMatrix']))
  return font,glyphs,order,matrix
 font=TTFont(BytesIO(raw),recalcBBoxes=False,recalcTimestamp=False,lazy=False)
 upem=int(font['head'].unitsPerEm)
 if upem<=0:raise ValueError('Invalid original TTF em')
 return font,font.getGlyphSet(),tuple(font.getGlyphOrder()),(1/upem,0.,0.,1/upem,0.,0.)

def _simple_names(font,builtin):
 enc=font.get('/Encoding')
 if enc is None:return dict(enumerate(builtin))
 if str(enc)=='/WinAnsiEncoding':
  out={}
  for n in range(256):
   try:out[n]=UV2AGL.get(ord(bytes([n]).decode('cp1252')))
   except UnicodeDecodeError:pass
  out.update({127:'bullet',129:'bullet',141:'bullet',143:'bullet',144:'bullet',157:'bullet',160:'space',173:'hyphen'})
  return out
 if str(enc)=='/MacRomanEncoding':
  from fontTools.encodings.MacRoman import MacRoman
  return dict(enumerate(MacRoman))
 if not isinstance(enc,pikepdf.Dictionary):raise ValueError('Unsupported simple outline Encoding')
 base=enc.get('/BaseEncoding')
 if base is None:out=dict(enumerate(builtin))
 elif str(base)=='/StandardEncoding':
  from fontTools.encodings.StandardEncoding import StandardEncoding
  out=dict(enumerate(StandardEncoding))
 elif str(base)=='/WinAnsiEncoding':
  proxy=pikepdf.Dictionary(Encoding=pikepdf.Name('/WinAnsiEncoding'));out=_simple_names(proxy,builtin)
 else:raise ValueError('Unsupported outline BaseEncoding')
 pos=None
 for value in enc.get('/Differences',[]):
  if isinstance(value,int):pos=value;continue
  if pos is None or not 0<=pos<=255:raise ValueError('Invalid outline Encoding Differences')
  out[pos]=str(value).lstrip('/');pos+=1
 return out

class SourceOutlineReader:
 def __init__(self,source=None):self.bounds={};self.source=source;self.source_renderer=None
 def measure(self,font,code,cluster,state,text_matrix,page_matrix):
  actual=cluster[0];gid=actual['trace_gid']
  if gid<0 or any(c['trace_gid']!=-1 for c in cluster[1:]):raise ValueError('Outline cluster lacks one exact original painted GID')
  if any(c['origin']!=actual['origin']for c in cluster[1:]):raise ValueError('Outline cluster has noncoincident continuations')
  face=font.get('/DescendantFonts',[font])[0];desc=face.get('/FontDescriptor',{})
  if str(font.get('/Subtype'))=='/Type1'and '/FontFile'in desc:kind='Type1';raw=desc.FontFile.read_bytes()
  elif '/FontFile2'in desc:kind='TrueType';raw=desc.FontFile2.read_bytes()
  elif '/FontFile3'in desc and str(desc.FontFile3.get('/Subtype'))=='/CIDFontType0C'and str(font.get('/Subtype'))=='/Type0'and str(face.get('/Subtype'))=='/CIDFontType0':kind='CFFCID';raw=desc.FontFile3.read_bytes()
  elif '/FontFile3'in desc and str(desc.FontFile3.get('/Subtype'))=='/Type1C'and str(font.get('/Subtype'))=='/Type1':kind='CFFType1';raw=desc.FontFile3.read_bytes()
  else:
   if self.source is None:raise ValueError('Unembedded outline requires the exact original source packet')
   if self.source_renderer is None:
    from source_renderer_font import SourceRendererFontReader
    self.source_renderer=SourceRendererFontReader(self.source)
   raw,kind=self.source_renderer.resolve(font)
  program,glyphs,order,font_matrix=_program(raw,kind)
  if len(font_matrix)!=6 or any(not math.isfinite(x)for x in font_matrix)or abs(font_matrix[0]*font_matrix[3]-font_matrix[1]*font_matrix[2])<1e-20 or any(abs(x)>1e-15 for x in font_matrix[4:]):
   raise ValueError('Unsupported nonfinite/singular/translated original FontMatrix')
  if kind=='CFFCID':
   # MuPDF exposes CID-keyed CFF trace glyph IDs as CIDs, not as the
   # subset CharStrings INDEX. Resolve the original CFF charset explicitly.
   if gid!=code:raise ValueError('Original CFF Identity-H source code and MuPDF trace CID differ')
   name='.notdef'if code==0 else f'cid{code:05d}'
   actual_gid=program.CharStrings.charStrings.get(name)
   if not isinstance(actual_gid,int)or not 0<=actual_gid<len(order)or order[actual_gid]!=name:raise ValueError('Original CFF CID has no exact charset/CharString INDEX mapping')
  else:
   if not 0<=gid<len(order):raise ValueError(f'Source trace GID outside embedded program: font={font.get("/BaseFont")}, code={code}, trace_gid={gid}, CFF/TTF_glyph_count={len(order)}, kind={kind}')
   actual_gid=gid;name=order[gid]
  if kind=='CFFCID':
   if str(font.get('/Encoding'))!='/Identity-H':raise ValueError('Original CFF CID outline currently requires explicit Identity-H')
   encoded='.notdef'if code==0 else f'cid{code:05d}'
   if encoded!=name or program.CharStrings.charStrings.get(encoded)!=actual_gid:raise ValueError(f'Original CFF CID/charset/CharString/trace mapping mismatch: CID{code} {encoded} != CharString{actual_gid} {name}')
   fd=program.FDArray[program.FDSelect[actual_gid]]
   # Every LatinModernMath source subset uses inherited TopDICT FontMatrix.
   # Explicit FD matrices are rejected rather than silently mis-scaled.
   if 'FontMatrix'in fd.rawDict:raise ValueError('Explicit original CFF FD FontMatrix requires separate reviewed composition')
  elif kind=='CFFType1':
   builtin=program.Encoding
   if isinstance(builtin,str):
    if builtin!='StandardEncoding':raise ValueError('Unsupported original name-keyed CFF Encoding')
    from fontTools.encodings.StandardEncoding import StandardEncoding
    builtin=StandardEncoding
   encoded=_simple_names(font,builtin).get(code)
   if encoded!=name or program.CharStrings.charStrings.get(encoded)!=gid:raise ValueError(f'Original name-keyed CFF code/CharString/trace GID mismatch: code{code} {encoded} != GID{gid} {name}')
  elif kind=='Type1':
   encoded=_simple_names(font,program['Encoding']).get(code)
   if encoded!=name:raise ValueError(f'Original Type1 code/GID/name mismatch: code{code} {encoded!r} != GID{gid} {name!r}')
  elif str(font.get('/Subtype'))=='/Type0':
   mapping=face.get('/CIDToGIDMap')
   if mapping is None or str(mapping)=='/Identity':expected=code
   elif isinstance(mapping,pikepdf.Stream):
    data=mapping.read_bytes();a=2*code
    if a+2>len(data):raise ValueError('CID lies outside explicit original CIDToGIDMap')
    expected=int.from_bytes(data[a:a+2],'big')
   else:raise ValueError('Unsupported original CIDToGIDMap')
   if expected!=gid:raise ValueError('Original TTF CID/GID mapping differs from trace')
  else:
   declared=cmap(font).get(code);valid=set()
   for table in program['cmap'].tables:
    if table.isUnicode()and declared and len(declared)==1:
     value=table.cmap.get(ord(declared))
     if value is not None:valid.add(value)
    if table.platformID==1 and table.platEncID==0 and str(font.get('/Encoding'))=='/MacRomanEncoding':
     value=table.cmap.get(code)
     if value is not None:valid.add(value)
    if table.platformID==3 and table.platEncID==0:
     for n in[code,0xf000+code]:
      value=table.cmap.get(n)
      if value is not None:valid.add(value)
   explicit=_simple_names(font,[]).get(code)
   if explicit in glyphs:valid.add(explicit)
   if name not in valid:raise ValueError('Original simple TTF encoded glyph cannot be verified against its actual trace GID')
  identity=(hashlib.sha256(raw).hexdigest(),name)
  if identity not in self.bounds:
   pen=BoundsPen(glyphs);glyph=glyphs[name]
   if kind=='Type1':glyph.draw(pen)
   else:glyph.draw(pen)
   self.bounds[identity]=pen.bounds
  bounds=self.bounds[identity]
  x,y=actual['origin']
  if bounds is None:
   if not all(c['c'].isspace()for c in cluster):raise ValueError('Painted source glyph has no measurable vector outline')
   return [x,y,x,y]
  tf=float(state['tf']);th=float(state['th'])
  if not math.isfinite(tf)or not math.isfinite(th)or tf<=0 or th==0:raise ValueError('Unsupported original text scaling for outline bounds')
  transform=font_matrix
  for matrix in[(tf*th,0.,0.,tf,0.,0.),text_matrix,state['ctm'],page_matrix]:
   # Only the linear part acts on an outline relative to the exact source
   # trace origin, which already includes text rise and all translations.
   a,b,c,d,_,_=tuple(map(float,matrix));transform=_mul(transform,(a,b,c,d,0.,0.))
  a,b,c,d,_,_=transform
  if abs(a*d-b*c)<1e-20:raise ValueError('Singular source text outline transformation')
  x0,y0,x1,y1=bounds
  points=[(x+a*u+c*v,y+b*u+d*v)for u,v in[(x0,y0),(x0,y1),(x1,y0),(x1,y1)]]
  return[min(p[0]for p in points),min(p[1]for p in points),max(p[0]for p in points),max(p[1]for p in points)]

def measure_native_ink_bounds(source,page_number,glyphs,inventory=None,audit_out=None):
 from latex_native_motion import reposition_inline
 raw=bytes(source)if isinstance(source,(bytes,bytearray))else Path(source).read_bytes()
 wanted={glyph_key(c)for c in glyphs}
 if not wanted:return{}
 sha=hashlib.sha256(raw).hexdigest()
 if inventory is None or inventory.get('source_sha256')!=sha or inventory.get('page_number')!=page_number or not wanted<=set(tuple(v)for v in inventory.get('ink_requested_keys',[])):
  inventory=reposition_inline(raw,page_number,_inspect_only=True,_inspect_ink_glyphs=glyphs)
 if audit_out is not None:audit_out.extend(inventory.get('source_renderer_font_resolution',[]))
 result={};actual_gids={}
 for item in inventory.get('native_ink_bounds',[]):
  rect=item['bbox']
  for c in item['glyphs']:
   key=glyph_key(c)
   if key not in wanted:continue
   actual_gids.setdefault(key,set()).add(c['trace_gid'])
   if key not in result:result[key]=list(rect)
   else:
    a=result[key];result[key]=[min(a[0],rect[0]),min(a[1],rect[1]),max(a[2],rect[2]),max(a[3],rect[3])]
 if wanted!=result.keys():raise ValueError('Not every requested original glyph received verified outline bounds')
 for c in glyphs:
  supplied=c.get('trace_gid',c.get('gid'))
  if supplied is not None and supplied not in actual_gids[glyph_key(c)]:raise ValueError('Requested glyph GID differs from the exact source trace')
 return result

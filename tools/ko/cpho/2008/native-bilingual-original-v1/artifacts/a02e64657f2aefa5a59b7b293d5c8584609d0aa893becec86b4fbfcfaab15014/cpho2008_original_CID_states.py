"""Actual original encoded CID/Tf/full-Tm binding; never retypes mathematics."""
from collections import defaultdict
import json,hashlib
import pikepdf
from pdf_original_text_ops import widths,source_code_bytes,glyph_key
from pdf_native_inline_reposition import _multiply,IDENTITY

def original_clip_programs(page):
 ctm=IDENTITY;stack=[];pending=[];clips={}
 for i,op in enumerate(pikepdf.parse_content_stream(page)):
  name=str(op.operator)
  if name=='q':stack.append(ctm)
  elif name=='Q':ctm=stack.pop()
  elif name=='cm':ctm=_multiply(tuple(map(float,op.operands)),ctm)
  if name in('m','l','c','v','y','h','re'):pending.append(op)
  elif name in('W','W*'):
   raw=pikepdf.unparse_content_stream(pending+[op]);clips[i]=dict(original_literal_clip_path_program_sha256=hashlib.sha256(raw).hexdigest(),original_clip_rule=name,CTM=list(ctm))
  elif name in('S','s','f','F','f*','B','B*','b','b*','n'):pending=[]
 return clips

def records(page,inv):
 shows={s['operator_index']:s for s in inv['top_level_text_shows']};tm=[1.,0.,0.,1.,0.,0.];tlm=tm[:];leading=0.;stack=[];rows=[];clips=original_clip_programs(page)
 def advance(x):tm[4]+=tm[0]*x;tm[5]+=tm[1]*x
 for oi,op in enumerate(pikepdf.parse_content_stream(page)):
  name=str(op.operator);v=list(op.operands)
  if name=='q':stack.append(leading)
  elif name=='Q':leading=stack.pop()
  elif name=='BT':tm=[1.,0.,0.,1.,0.,0.];tlm=tm[:]
  elif name=='Tm':tm=list(map(float,v));tlm=tm[:]
  elif name=='TL':leading=float(v[0])
  elif name in('Td','TD'):
   x,y=map(float,v)
   if name=='TD':leading=-y
   tlm[4]+=tlm[0]*x+tlm[2]*y;tlm[5]+=tlm[1]*x+tlm[3]*y;tm=tlm[:]
  elif name=='T*':tlm[4]-=tlm[2]*leading;tlm[5]-=tlm[3]*leading;tm=tlm[:]
  if oi not in shows:continue
  assert name in('Tj','TJ'),'Source2008 uses explicit original Tj/TJ only'
  show=shows[oi];st=show['state'];font=page.Resources.Font[pikepdf.Name(st['active'])];ws,default=widths(font);cb=source_code_bytes(font);parts=iter(show['parts'])
  for value in(list(v[0])if name=='TJ'else[v[0]]):
   if not isinstance(value,pikepdf.String):advance(-float(value)*st['tf']*st['th']/1000);continue
   raw=bytes(value)
   for offset in range(0,len(raw),cb):
    encoded=raw[offset:offset+cb];code=int.from_bytes(encoded,'big');part=next(parts);assert part['raw_hex']==encoded.hex()
    rows.append(dict(original_source_operator=oi,font_resource=st['active'],encoded_CID_hex=encoded.hex(),encoded_CID=code,Tf=st['tf'],literal_Tm=show['text_matrix'],full_per_CID_Tm=tm[:],CTM=st['ctm'],Tc=st['tc'],Tw=st['tw'],Tz=st['th'],Ts=st['ts'],Tr=st['tr'],ancestor_clips=[dict(c,**clips[c['operator_index']])for c in st['clips']],glyphs=part['glyphs']))
    advance((ws.get(code,default)/1000*st['tf']+st['tc']+(st['tw']if cb==1 and code==32 else 0))*st['th'])
  assert next(parts,None)is None
 assert not stack
 return rows

def binding_key(r):return(r['font_resource'],r['encoded_CID_hex'],r['Tf'],tuple(round(v,5)for v in r['full_per_CID_Tm']))

def audit(source,source_page,proof,source_inv,actual_inv,erased_glyphs):
 erased={glyph_key(g)for g in erased_glyphs};errors=[];bound=[]
 with pikepdf.open(source)as src,pikepdf.open(proof)as dst:
  a=records(src.pages[source_page-1],source_inv);b=records(dst.pages[0],actual_inv)
 buckets=defaultdict(list)
 for r in b:buckets[binding_key(r)].append(r)
 for old in a:
  keys={glyph_key(g)for g in old['glyphs']}
  if keys&erased:
   assert keys<=erased,'A language edit may never split an original multi-Unicode CID';continue
  hits=buckets[binding_key(old)]
  if not hits:errors.append(dict(original=old,error='Original encoded CID/font resource/Tf/full original Tm absent'));continue
  new=hits.pop(0)
  try:
   for key in('font_resource','encoded_CID_hex','encoded_CID','Tf','literal_Tm','Tc','Tw','Tz','Ts','Tr'):assert json.dumps(old[key])==json.dumps(new[key]),key
   assert max(abs(x-y)for x,y in zip(old['full_per_CID_Tm'],new['full_per_CID_Tm']))<1e-5
   assert list(old['CTM'][:4])==list(new['CTM'][:4])
   assert len(old['ancestor_clips'])==len(new['ancestor_clips'])
   native_dx=new['CTM'][4]-old['CTM'][4]
   for x,y in zip(old['ancestor_clips'],new['ancestor_clips']):
    assert x['original_literal_clip_path_program_sha256']==y['original_literal_clip_path_program_sha256']
    assert x['original_clip_rule']==y['original_clip_rule']and x['CTM'][:4]==y['CTM'][:4]
    assert abs(x['CTM'][5]-y['CTM'][5])<.001
    clip_dx=y['CTM'][4]-x['CTM'][4];assert min(abs(clip_dx),abs(clip_dx-native_dx))<.001
   assert len(old['glyphs'])==len(new['glyphs'])
   for x,y in zip(old['glyphs'],new['glyphs']):
    for key in('c','font','trace_gid','size','render_mode','color','opacity','linewidth','direction','stroke_color','stroke_opacity','wmode','colorspace'):assert json.dumps(x.get(key))==json.dumps(y.get(key)),key
    assert abs(x['origin'][1]-y['origin'][1])<.001
   bound.append(dict(font_resource=old['font_resource'],original_encoded_CID_hex=old['encoded_CID_hex'],original_Tf=old['Tf'],original_literal_Tm=old['literal_Tm'],original_full_per_CID_Tm=old['full_per_CID_Tm'],actual_full_per_CID_Tm=new['full_per_CID_Tm'],original_CTM=old['CTM'],actual_CTM=new['CTM'],original_literal_ancestor_clip_programs=old['ancestor_clips'],actual_literal_ancestor_clip_programs=new['ancestor_clips'],source_glyphs=[{k:g[k]for k in('c','font','trace_gid','size','origin')}for g in old['glyphs']],original_CID_Tf_Tm_font_GID_fractional_point_and_paint_exact=True))
  except AssertionError as e:errors.append(dict(original=old,actual=new,error=str(e)))
 return dict(original_source_sha256=hashlib.sha256(open(source,'rb').read()).hexdigest(),proof_sha256=hashlib.sha256(open(proof,'rb').read()).hexdigest(),source_page=source_page,actual_original_encoded_CIDs_checked=len(bound),original_CID_Tf_full_Tm_point_font_GID_paint_bindings=bound,all_original_encoded_CIDs_Tf_Tm_points_preserved=not errors,errors=errors,position_measurement_tolerance_pt=.001,computed_text_advance_arithmetic_tolerance_in_original_text_units=1e-5,mathematics_or_font_programmes_modified=False,passed=not errors)

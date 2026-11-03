"""Preserve exact clipped source CIDs independently of stationary gray fields.

Source2012 only. A complete authored reference is copied as original encoded
CID paints, font resources, physical matrices and paint-state history. Its
original row clips travel with it. Original gray-field paths stay untouched.
No Unicode insertion, substitute font, raster, scaling or guard change.
"""
from pathlib import Path
from io import BytesIO
import hashlib,pikepdf,pymupdf as f
from pdf_native_inline_reposition import inspect_inline_groups,reposition_inline,_traces,_raw_regions,_multiply,_number,_font_programs,_verify_glyphs
from pdf_native_glyph_promote import PAINT_STATE,_inverse,_point_inverse
from pdf_original_text_ops import glyph_key,widths,source_code_bytes
SOURCE='41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db'
def promote(source,page_number,groups,prose_stream_count):
 raw=Path(source).read_bytes();native=f.open(stream=raw,filetype='pdf');page=native[page_number-1];inv=inspect_inline_groups(raw,page_number,include_text_shows=True)
 keys={glyph_key(g)for group in groups for g in group['glyphs']};recipes={};found=set();painted={glyph_key(g):g for g in _traces(page)if g['c'].strip()}
 for show in inv['top_level_text_shows']:
  for part in show['parts']:
   partkeys={glyph_key(g)for g in part['glyphs']}
   if not keys&partkeys:continue
   if not partkeys<=keys or len(part['glyphs'])!=1:raise ValueError('A reviewed reference requires its exact complete one-glyph source CID cluster')
   g=part['glyphs'][0]
   if g['render_mode']!=0 or abs(g['opacity']-1)>1e-8 or g['font']!='CambriaMath':raise ValueError('Reviewed clipped-reference source paint differs')
   if any(clip['rect']is None for clip in show['state']['clips']):raise ValueError('Unknown source reference clipping shape')
   key=glyph_key(g)
   if key in recipes:raise ValueError('Source reference native paint is not unique')
   recipes[key]=(show,part,g);found.add(key)
 if found!=keys:raise ValueError('Reviewed source reference CID paint missing')
 erased,erase_qa=reposition_inline(raw,page_number,erased_glyphs=[painted[k]for k in keys])
 with pikepdf.open(BytesIO(raw))as original,pikepdf.open(BytesIO(erased))as pdf:
  src=original.pages[page_number-1];target=pdf.pages[0];content,regions=_raw_regions(src);instructions=pikepdf.parse_content_stream(src)
  exact_matrices={};whole_shows={};show_suppression={}
  for group in groups:
   groupkeys={glyph_key(g)for g in group['glyphs']};shows={recipes[k][0]['operator_index']for k in groupkeys}
   if len(shows)!=1:continue
   show=recipes[next(iter(groupkeys))][0];visible={glyph_key(g)for part in show['parts']for g in part['glyphs']if g['c'].strip()}
   if visible!=groupkeys:continue
   whole_shows[show['operator_index']]=groupkeys
   st=show['state'];font=src.Resources.Font[pikepdf.Name(st['active'])];ws,default=widths(font);cb=source_code_bytes(font);inst=instructions[show['operator_index']];values=list(inst.operands[0])if show['operator']=='TJ'else[inst.operands[0]];empty=[]
   for value in values:
    if not isinstance(value,pikepdf.String):empty.append(value);continue
    raw_codes=bytes(value)
    for off in range(0,len(raw_codes),cb):
     code=int.from_bytes(raw_codes[off:off+cb],'big');empty.append(-(ws.get(code,default)+(st['tc']+(st['tw']if cb==1 and code==32 else 0))*1000/st['tf']))
   show_suppression[show['operator_index']]=pikepdf.unparse_content_stream([pikepdf.ContentStreamInstruction([pikepdf.Array(empty)],pikepdf.Operator('TJ'))])
  for show in inv['top_level_text_shows']:
   if not any(glyph_key(g)in keys for part in show['parts']for g in part['glyphs']):continue
   st=show['state'];font=src.Resources.Font[pikepdf.Name(st['active'])];ws,default=widths(font);cb=source_code_bytes(font);inst=instructions[show['operator_index']]
   values=list(inst.operands[0])if show['operator']=='TJ'else[inst.operands[0]];advance=0.;index=0
   for value in values:
    if isinstance(value,pikepdf.String):
     encoded=bytes(value)
     for offset in range(0,len(encoded),cb):
      code_bytes=encoded[offset:offset+cb];code=int.from_bytes(code_bytes,'big');part=show['parts'][index];index+=1
      if part['raw_hex']!=code_bytes.hex():raise ValueError('Original native CID text-matrix association differs')
      tm=list(show['text_matrix']);tm[4]+=tm[0]*advance;tm[5]+=tm[1]*advance
      for g in part['glyphs']:
       if glyph_key(g)in keys:exact_matrices[show['operator_index'],glyph_key(g)]=tm[:]
      advance+=(ws.get(code,default)*st['tf']/1000+st['tc']+(st['tw']if cb==1 and code==32 else 0))*st['th']
    else:advance-=float(value)*st['tf']*st['th']/1000
   if index!=len(show['parts']):raise ValueError('Original native text-show CID stream was not fully consumed')
  source_streams=list(src.Contents)if isinstance(src.Contents,pikepdf.Array)else[src.Contents]
  if not 0<prose_stream_count<len(source_streams):raise ValueError('Original prose stream suffix not resolved')
  cut=sum(len(pikepdf.parse_content_stream(stream))for stream in source_streams[:-prose_stream_count])
  first_prose=next(show for show in inv['top_level_text_shows']if show['operator_index']>=cut)
  if max(abs(a-b)for a,b in zip(first_prose['state']['ctm'],inv['final_ctm']))>.000001:raise ValueError('Prose suffix needs an explicit original CTM profile')
  resources=target.Resources;new=pikepdf.Dictionary(resources);new.XObject=pikepdf.Dictionary(resources.get('/XObject',{}));new.ExtGState=pikepdf.Dictionary(resources.get('/ExtGState',{}))
  def alias(prefix,table):
   i=0
   while pikepdf.Name('/'+prefix+str(i))in table:i+=1
   return pikepdf.Name('/'+prefix+str(i))
  reset=alias('SourceReferencePaintReset',new.ExtGState);new.ExtGState[reset]=pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.ExtGState,ca=1,CA=1,BM=pikepdf.Name.Normal,SMask=pikepdf.Name('/None'),OP=False,op=False,OPM=0,AIS=False))
  append=[('q '+' '.join(_number(v)for v in _inverse(inv['final_ctm']))+' cm '+str(reset)+' gs 0 g 0 G 1 w 0 J 0 j 10 M [] 0 d\n').encode('ascii')];reports=[];matrix=tuple(page.transformation_matrix)
  for group in groups:
   body=[];box=f.Rect();records=[];painted_shows=set()
   for glyph in group['glyphs']:
    show,part,g=recipes[glyph_key(glyph)];st=show['state'];box|=f.Rect(g['bbox']);records.append(dict(c=g['c'],gid=g['trace_gid'],font=g['font'],point=g['size'],origin=g['origin'],original_encoded_CID_hex=part['raw_hex'],original_font_resource=st['active'],original_clips=st['clips']))
    whole=show['operator_index']in whole_shows
    if whole and show['operator_index']in painted_shows:continue
    painted_shows.add(show['operator_index']);history=[];stack=[]
    for index,instruction in enumerate(instructions[:show['operator_index']]):
     op=str(instruction.operator)
     if op=='q':stack.append(history[:])
     elif op=='Q':history=stack.pop()
     elif op in PAINT_STATE:
      if op=='gs':
       state=src.Resources.get('/ExtGState',{}).get(instruction.operands[0],{})
       if '/Font'in state or str(state.get('/SMask','/None'))!='/None':raise ValueError('Unsupported original reference paint state')
      a,z,_=regions[index];history.append(content[a:z])
    combined=_multiply(st['ctm'],matrix);tm=show['text_matrix']if whole else exact_matrices[show['operator_index'],glyph_key(g)]
    body.append(('q '+' '.join(_number(v)for v in st['ctm'])+' cm\n').encode('ascii'));body.extend(history)
    for clip in st['clips']:
     ci=clip['operator_index'];rect_op=instructions[ci-1]
     if tuple(st['ctm'])!=(1.,0.,0.,1.,0.,0.)or str(rect_op.operator)!='re'or str(instructions[ci].operator)not in['W','W*']or str(instructions[ci+1].operator)!='n':raise ValueError('Exact original source reference clip needs the reviewed identity-CTM re/W/n profile')
     left,bottom,width,height=map(float,rect_op.operands);expected=[left,float(page.rect.height)-bottom-height,left+width,float(page.rect.height)-bottom]
     if max(abs(a-b)for a,b in zip(expected,clip['rect']))>1e-7:raise ValueError('Original reference raw clip path does not match its reviewed physical clip')
     body.append(b'\n'+content[regions[ci-1][0]:regions[ci+1][1]]+b'\n')
    body.append(('\nBT '+st['active']+' '+_number(st['tf'])+' Tf '+_number(st['tc'])+' Tc '+_number(st['tw'])+' Tw '+_number(st['th']*100)+' Tz '+str(st['tr'])+' Tr '+_number(st['ts'])+' Ts '+' '.join(_number(v)for v in tm)+' Tm\n').encode('ascii'))
    if whole:
     at=show['operator_index'];body.append(content[regions[at][0]:regions[at][1]])
    else:body.append(('<'+part['raw_hex']+'> Tj').encode('ascii'))
    body.append(b'\nET Q\n')
   box+=(-2,-2,2,2)
   form=pdf.make_stream(b'\n'.join(body));form.Type=pikepdf.Name.XObject;form.Subtype=pikepdf.Name.Form
   points=[_point_inverse(matrix,x,y)for x,y in[(box.x0,box.y0),(box.x1,box.y1)]];form.BBox=pikepdf.Array([min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points)]);form.Resources=resources
   name=alias('OriginalSourceReference',new.XObject);new.XObject[name]=form;append.append((str(name)+' Do\n').encode('ascii'))
   reports.append(dict(source_at=group['source_at'],source_text=group['source_text'],glyphs=records,form_sha256=hashlib.sha256(form.read_bytes()).hexdigest(),original_clip_geometry_copied=True))
  append.append(b'Q');target.Resources=new;erased_content,erased_regions=_raw_regions(target)
  if len(erased_regions)!=len(regions):raise ValueError('Source CID suppression changed instruction count before prose suffix')
  pos=erased_regions[cut][0];edits=[(erased_regions[i][0],erased_regions[i][1],value)for i,value in show_suppression.items()];edits.append((pos,pos,b'\n'+b''.join(append)+b'\n'));pieces=[];cursor=0
  for start,end,value in sorted(edits):
   if start<cursor:raise ValueError('Original source complete-show isolation edits overlap')
   pieces.extend([erased_content[cursor:start],value]);cursor=end
  pieces.append(erased_content[cursor:]);target.Contents=pdf.make_stream(b''.join(pieces));buffer=BytesIO();pdf.save(buffer,compress_streams=False);result=buffer.getvalue()
  with pikepdf.open(BytesIO(result))as final:fonts_unchanged=_font_programs(src)==_font_programs(final.pages[0])
 qa=_verify_glyphs(page,result,set(),{},tolerance=.001);qa.update(source_page=page_number,source_sha256=hashlib.sha256(raw).hexdigest(),output_sha256=hashlib.sha256(result).hexdigest(),reference_groups=reports,complete_original_Tj_TJ_show_programs_copied=len(whole_shows),original_nonpainting_space_CIDs_relocated_once_not_duplicated=True,original_font_programs_unchanged=fonts_unchanged,original_gray_paths_untouched=True,original_encoded_CIDs_and_clips_preserved=True,original_raw_re_W_n_clipping_operator_bytes_copied=True,original_text_matrices_computed_from_exact_PDF_CID_widths_and_TJ_numbers=True,passed=fonts_unchanged and not qa['native_glyph_mismatches']and not qa['unexpected_glyphs'])
 native.close()
 if not qa['passed']:raise ValueError('Original source clipped-reference roundtrip metadata differs')
 return result,qa

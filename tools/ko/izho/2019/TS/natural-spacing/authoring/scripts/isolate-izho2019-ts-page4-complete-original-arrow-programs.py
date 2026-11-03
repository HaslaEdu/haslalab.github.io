from pathlib import Path
from io import BytesIO
from collections import Counter
import sys,json,hashlib,pikepdf,pymupdf as f,numpy as np,subprocess,os,shutil
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions');E=B/'engine';sys.path[:0]=[str(E),'D:/CodexBuilds/Hasla-publish-20261031/tools'];SOURCE='5e83000f5d2abe161186a6f81e5b9cd306a0758d2969744edbfb68fcad413da8';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups,_traces,_raw_regions,_number,_font_programs,_verify_glyphs
from pdf_original_text_ops import glyph_key,widths,source_code_bytes
from pdf_native_glyph_promote import PAINT_STATE
P=B/'natural/2019/TS/plans/page04.json';p=json.loads(P.read_text('utf8'));assert p['original_english_source_sha256']==sha(p['original_english_source'])==SOURCE;base=Path(p['source_base']);assert sha(base)==p['source_base_sha256'];out=B/'2019/original-complete-arrow-program-isolation'/p['source_base_sha256'][:16];out.mkdir(parents=True,exist_ok=True)
with page_worker():
 inv=inspect_inline_groups(str(base),4,include_text_shows=True);officialinv=inspect_inline_groups(p['original_english_source'],4,include_text_shows=True)
 with f.open(base)as doc:source_rows=_traces(doc[3]);pageheight=doc[3].rect.height
 groups=[]
 for a in p['explicit_native_math_atoms']:
  heads=[g for g in source_rows if g['c']==' 'and g['font']=='CambriaMath'and g['trace_gid']==1318 and f.Rect(a['rect']).contains(f.Point(g['origin']))]
  if not heads:continue
  assert len(heads)==1 and a['baseline']in[388.61,430.25,535.99];gs=a['source_native_glyphs']+heads;groups.append(dict(atom=a,gs=gs,head=heads[0]))
 assert len(groups)==4
 with pikepdf.open(base)as srcpdf,pikepdf.open(p['original_english_source'])as original,pikepdf.Pdf.new()as target:
  src=srcpdf.pages[3];official=original.pages[3];target.pages.append(src);page=target.pages[0];content,regions=_raw_regions(src);instructions=list(pikepdf.parse_content_stream(src));ocontent,oregions=_raw_regions(official);oinstructions=list(pikepdf.parse_content_stream(official));resources=page.Resources;new=pikepdf.Dictionary(resources);new.XObject=pikepdf.Dictionary(resources.get('/XObject',{}));edits=[];reports=[]
  def program(container_content,container_regions,ops,inventory,keys):
   shows=[s for s in inventory['top_level_text_shows']if any(glyph_key(g)in keys for part in s['parts']for g in part['glyphs'])];found={glyph_key(g)for s in shows for part in s['parts']for g in part['glyphs']};assert found==keys
   first=min(s['operator_index']for s in shows);last=max(s['operator_index']for s in shows);clips=[]
   for s in shows:
    assert len(s['state']['clips'])==1 and tuple(s['state']['ctm'])==(1.,0.,0.,1.,0.,0.)and s['state']['tr']==0
    rect=s['state']['clips'][0]['rect'];assert rect is not None
    matches=[v for v in inventory['clip_groups']if v['known_rectangular_clips']and v['clip_rects']==[rect]and v['operator_indices'][0]<s['operator_index']<v['operator_indices'][-1]];assert matches;clips.append(min(matches,key=lambda v:v['operator_indices'][-1]-v['operator_indices'][0]))
   start=min(v['operator_indices'][0]for v in clips);end=max(v['operator_indices'][-1]for v in clips);assert str(ops[start].operator)=='q'and str(ops[end].operator)=='Q';inside=[s for s in inventory['top_level_text_shows']if start<=s['operator_index']<=end];assert {s['operator_index']for s in inside}=={s['operator_index']for s in shows}
   assert all(g['opacity']==1 and g['render_mode']==0 for s in shows for part in s['parts']for g in part['glyphs'])
   assert any(str(ops[i].operator)=='Tm'for i in range(start,first));assert not any(str(ops[i].operator)in['Do','f','f*','S','B','cm']for i in range(start,end+1));raw=container_content[container_regions[start][0]:container_regions[end][1]]
   return raw,shows,start,end
  for index,group in enumerate(groups):
   keys={glyph_key(g)for g in group['gs']};program_bytes,shows,start,end=program(content,regions,instructions,inv,keys);official_bytes,officialshows,ostart,oend=program(ocontent,oregions,oinstructions,officialinv,keys);assert program_bytes==official_bytes,'Every copied native arrow program must be byte-exact to the official source'
   initial=shows[0]['state'];history=[];stack=[]
   for i,inst in enumerate(instructions[:start]):
    op=str(inst.operator)
    if op=='q':stack.append(history[:])
    elif op=='Q':history=stack.pop()
    elif op in PAINT_STATE:
     assert op!='gs' or str(src.Resources.get('/ExtGState',{}).get(inst.operands[0],{}).get('/SMask','/None'))=='/None';history.append(content[regions[i][0]:regions[i][1]])
   prefix=('q\nBT '+initial['active']+' '+_number(initial['tf'])+' Tf '+_number(initial['tc'])+' Tc '+_number(initial['tw'])+' Tw '+_number(initial['th']*100)+' Tz '+str(initial['tr'])+' Tr '+_number(initial['ts'])+' Ts ET\n').encode('ascii');body=b'\n'.join([prefix,*history,program_bytes,b'\nQ\n']);form=target.make_stream(body);form.Type=pikepdf.Name.XObject;form.Subtype=pikepdf.Name.Form;box=f.Rect()
   for g in group['gs']:box|=f.Rect(g['bbox'])
   box=f.Rect(box.x0,box.y0-3,box.x1,box.y1+3);form.BBox=pikepdf.Array([box.x0,pageheight-box.y1,box.x1,pageheight-box.y0]);form.Resources=resources;name=pikepdf.Name('/OriginalSourceCompleteArrow'+str(index));assert name not in new.XObject;new.XObject[name]=form
   head_records=[];cid_records=[]
   for show in shows:
    state=show['state'];font=src.Resources.Font[pikepdf.Name(state['active'])];ws,default=widths(font);cb=source_code_bytes(font);inst=instructions[show['operator_index']];values=list(inst.operands[0])if show['operator']=='TJ'else[inst.operands[0]];empty=[];parts=iter(show['parts'])
    for value in values:
     if not isinstance(value,pikepdf.String):empty.append(value);continue
     encoded=bytes(value)
     for offset in range(0,len(encoded),cb):
      codebytes=encoded[offset:offset+cb];code=int.from_bytes(codebytes,'big');part=next(parts);assert part['raw_hex']==codebytes.hex()and len(part['glyphs'])==1;g=part['glyphs'][0];assert glyph_key(g)in keys;empty.append(-(ws.get(code,default)+(state['tc']+(state['tw']if cb==1 and code==32 else 0))*1000/state['tf']));record=dict(original_encoded_CID_hex=part['raw_hex'],original_font_resource=state['active'],original_Tf=state['tf'],original_text_matrix=show['text_matrix'],original_clips=state['clips'],source_operator_index=show['operator_index'],glyph=g);cid_records.append(record)
      if g['c']==' ':assert g['trace_gid']==1318 and g['font']=='CambriaMath';head_records.append(record)
    assert next(parts,None)is None;replacement=pikepdf.unparse_content_stream([pikepdf.ContentStreamInstruction([pikepdf.Array(empty)],pikepdf.Operator('TJ'))]);edits.append((regions[show['operator_index']][0],regions[show['operator_index']][1],replacement))
   assert len(head_records)==1;edits.append((regions[end][1],regions[end][1],('\nq '+str(name)+' Do Q\n').encode('ascii')));programfile=out/f'arrow{index}-official-original-program.bin';programfile.write_bytes(official_bytes)
   reports.append(dict(index=index,source_sha256=SOURCE,source_page=4,source_baseline=group['atom']['baseline'],source_atom_reason=group['atom']['reason'],original_official_operator_range=[ostart,oend],baseline_operator_range=[start,end],original_program_path=str(programfile),original_program_sha256=sha(programfile),original_program_verbatim_in_Form=True,Form_name=str(name),Form_raw_sha256=hashlib.sha256(body).hexdigest(),Form_bbox_page=list(box),native_CID_records=cid_records,painted_U0020_head_records=head_records,all_original_fonts_GIDs_points_Tf_Tm_paint_Y_and_encoded_CIDs_preserved=True))
  pieces=[];cursor=0
  for start,end,value in sorted(edits):assert start>=cursor;pieces.extend([content[cursor:start],value]);cursor=end
  pieces.append(content[cursor:]);page.Contents=target.make_stream(b''.join(pieces));page.Resources=new;buffer=BytesIO();target.save(buffer,compress_streams=False);raw=buffer.getvalue();single=out/'page04.pdf';single.write_bytes(raw)
  with f.open(base)as native:qa=_verify_glyphs(native[3],raw,set(),{},tolerance=.001)
  with pikepdf.open(single)as proof:assert _font_programs(src)==_font_programs(proof.pages[0])
  assert not qa['native_glyph_mismatches']and not qa['unexpected_glyphs'];checks=[]
 for scale in[4,8]:
  with f.open(base)as before,f.open(single)as after:
   aa=before[3].get_pixmap(matrix=f.Matrix(scale,scale),colorspace=f.csRGB,alpha=False);bb=after[0].get_pixmap(matrix=f.Matrix(scale,scale),colorspace=f.csRGB,alpha=False);a=np.frombuffer(aa.samples,np.uint8).reshape(aa.height,aa.width,3);b=np.frombuffer(bb.samples,np.uint8).reshape(bb.height,bb.width,3);changed=int(np.any(a!=b,axis=2).sum());checks.append(dict(renderer='MuPDF RGB',scale=scale,changed_pixels=changed));assert changed==0,checks[-1]
 POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
 for pdf,number,label in[(base,4,'before'),(single,1,'after')]:subprocess.run([POP,'-f',str(number),'-l',str(number),'-singlefile','-r','144','-png',str(pdf),str(out/label)],check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
 from PIL import Image
 a=np.asarray(Image.open(out/'before.png').convert('RGB'));b=np.asarray(Image.open(out/'after.png').convert('RGB'));changed=int(np.any(a!=b,axis=2).sum());checks.append(dict(renderer='independent external Poppler RGB',dpi=144,changed_pixels=changed));assert changed==0,checks[-1]
 joined=out/f'IZhO_2019_TS_native-base-complete-original-arrow-CID-programs-12p-{sha(single)[:16]}.pdf'
 with pikepdf.Pdf.new()as doc,pikepdf.open(base)as before,pikepdf.open(single)as after:
  for i,pg in enumerate(before.pages):doc.pages.append(after.pages[0]if i==3 else pg)
  doc.save(joined,compress_streams=False)
 newinv=inspect_inline_groups(str(joined),4);history=P.parent/'history'/sha(P);history.mkdir(parents=True,exist_ok=True);(history/P.name).write_bytes(P.read_bytes());p['source_base']=str(joined);p['source_base_sha256']=sha(joined);bindings=[]
 for group,report in zip(groups,reports):
  a=group['atom'];wanted={glyph_key(g)for g in a['source_native_glyphs']};forms=[v for v in newinv['forms']if{glyph_key(g)for g in v['glyphs']if g['c'].strip()}==wanted and v['original_raw_sha256']==report['Form_raw_sha256']];assert len(forms)==1;v=forms[0];a.update(source_form_path=v['path'],source_form_bbox=v['native_page_bbox']);bindings.append(dict(rect=a['rect'],path=v['path'],original_form_bbox=v['native_page_bbox'],original_form_program_sha256=v['original_raw_sha256'],complete_native_glyph_set=True,complete_original_encoded_arrow_program_including_literal_U0020_GID1318=True));report['source_form_path']=v['path']
 p['reviewed_complete_original_mathematical_form_bindings']=bindings;p['reviewed_complete_original_painted_space_arrow_programs']=dict(source_sha256=SOURCE,pre_isolation_base_sha256=sha(base),new_immutable_base_sha256=sha(joined),isolated_page_sha256=sha(single),groups=reports,roundtrip_checks=checks,literal_original_space_CIDs_replaced_by_advance_and_replayed_once=True,shared_guard_unchanged=True);P.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf8');(out/'source-program-and-zeroRGB-contract.json').write_text(json.dumps(dict(p['reviewed_complete_original_painted_space_arrow_programs'],native_CID_roundtrip_qa=qa),ensure_ascii=False,indent=2)+'\n','utf8')
assert sha(E/'pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f';print('SOURCE2019_P4_COMPLETE_ORIGINAL_ARROW_PROGRAMS_WITH_LITERAL_PAINTED_SPACE_CIDS_ZERO_RGB_ROUNDTRIPS',checks,flush=True)

"""Source2017-only original page programs masked to complete math expressions.
Every original CID, font/Tf/Tm/paint and all ancestor clips remain native.
No outline/bitmap replacement; exact full-page RGB roundtrips are required.
"""
from pathlib import Path
from io import BytesIO
import json,hashlib,sys,pikepdf,pymupdf as f,numpy as np,subprocess,os
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2017-complete-solutions');C=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2017-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups,_traces,reposition_inline,_raw_regions,_font_programs,_verify_glyphs
from pdf_native_glyph_promote import _inverse,_number
from pdf_original_text_ops import glyph_key,widths,source_code_bytes
SOURCE='fb90239d8da3dea3dcfe104551243f444802632a74a47a139374013aa16080f1';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
n=int(sys.argv[1]);P=B/f'natural/2017/TS/plans/page{n:02}.json';p=json.loads(P.read_text('utf8'));base=Path(p['source_base']);assert sha(base)==p['source_base_sha256'];assert p['original_english_source_sha256']==sha(p['original_english_source'])==SOURCE
out=C/f'native-expression-program-isolation/page{n:02}-{sha(P)[:16]}-page07-v1';out.mkdir(parents=True,exist_ok=False)
with page_worker():
 inv=inspect_inline_groups(base,n,include_text_shows=True)
 first_prose=min(s['operator_index']for s in inv['top_level_text_shows']if any('\uac00'<=g['c']<='\ud7a3'for part in s['parts']for g in part['glyphs']))
 with pikepdf.open(base)as initial:
  firstops=list(pikepdf.parse_content_stream(initial.pages[n-1]));stack=[]
  for oi,op in enumerate(firstops[:first_prose]):
   if str(op.operator)=='q':stack.append(oi)
   elif str(op.operator)=='Q':stack.pop()
  insert_at=stack[-1]
 groups=[a for a in p['explicit_native_math_atoms']if n==7 and a.get('reviewed_source2017_page07_program_group')]
 assert len(groups)==6 and [len(a['source_native_glyphs'])for a in groups]==[4,24,4,14,4,14], 'Closed source2017 page7 references/math around three selected conjunctions only'
 with f.open(base)as doc:rows=_traces(doc[n-1]);height=doc[n-1].rect.height
 all_top={glyph_key(g):g for s in inv['top_level_text_shows']for part in s['parts']for g in part['glyphs']}
 programs=[];all_remove=[];remove_Do=set();remove_paints=set()
 for index,a in enumerate(groups):
  keys={glyph_key(g)for g in a['source_native_glyphs']};topwanted=set(all_top)&keys
  forms=[v for v in inv['forms']if len(v['path'])==1 and {glyph_key(g)for g in v['glyphs']if g['c'].strip()}<=keys and any(g['c'].strip()for g in v['glyphs'])]
  assert topwanted|{glyph_key(g)for v in forms for g in v['glyphs']if g['c'].strip()}==keys
  paths=[v for v in inv['vector_paths']if f.Rect(a['rect']).contains(f.Rect(v['rect']))]
  keep_Do={v['path'][0]for v in forms};keep_paints={v['operator_indices'][-1]for v in paths}
  with pikepdf.open(base)as src,pikepdf.Pdf.new()as doc:
   doc.pages.append(src.pages[n-1]);page=doc.pages[0];content,regions=_raw_regions(page);ops=list(pikepdf.parse_content_stream(page));selected=[];shows={s['operator_index']:s for s in inv['top_level_text_shows']}
   for oi,op in enumerate(ops):
    name=str(op.operator)
    if name=='Do'and oi not in keep_Do:continue
    if oi in shows:
     show=shows[oi];showkeys={glyph_key(g)for part in show['parts']for g in part['glyphs']}
     if showkeys and showkeys<=keys and all(part['glyphs']for part in show['parts']):selected.append(op);continue
     state=show['state'];assert name in ['Tj','TJ'];font=page.Resources.Font[pikepdf.Name(state['active'])];ws,default=widths(font);cb=source_code_bytes(font);values=list(op.operands[0])if name=='TJ'else[op.operands[0]];parts=iter(show['parts']);masked=[]
     for value in values:
      if not isinstance(value,pikepdf.String):masked.append(value);continue
      encoded=bytes(value)
      for offset in range(0,len(encoded),cb):
       codebytes=encoded[offset:offset+cb];code=int.from_bytes(codebytes,'big');part=next(parts);assert part['raw_hex']==codebytes.hex();partkeys={glyph_key(g)for g in part['glyphs']};assert not(partkeys&keys)or partkeys<=keys
       if partkeys and partkeys<=keys:masked.append(pikepdf.String(codebytes))
       else:masked.append(-(ws.get(code,default)+(state['tc']+(state['tw']if cb==1 and code==32 else 0))*1000/state['tf']))
     assert next(parts,None)is None;selected.append(pikepdf.ContentStreamInstruction([pikepdf.Array(masked)],pikepdf.Operator('TJ')))
    elif name in ['S','s','f','F','f*','B','B*','b','b*']and oi not in keep_paints:selected.append(pikepdf.ContentStreamInstruction([],pikepdf.Operator('n')))
    else:selected.append(op)
   page.Contents=doc.make_stream(pikepdf.unparse_content_stream(selected));ref=out/f'expression{index}-original-CIDs-clips-paths-only.pdf';doc.save(ref,compress_streams=False)
  with f.open(ref)as doc:actual=[g for g in _traces(doc[0])if g['c'].strip()]
  assert {glyph_key(g)for g in actual}==keys,(index,'Reference must retain all and only requested original math')
  programs.append(dict(index=index,atom=a,reference=str(ref),reference_sha256=sha(ref),original_glyphs=a['source_native_glyphs'],original_source_vector_paths=paths,original_source_Form_paths=[v['path']for v in forms],all_ancestor_clips_and_original_text_matrices_retained=True))
  all_remove.extend(all_top[k]for k in topwanted);remove_Do|=keep_Do;remove_paints|=keep_paints
 erased,eraseqa=reposition_inline(base,n,erased_glyphs=all_remove)
 with pikepdf.open(BytesIO(erased))as doc:
  page=doc.pages[0];ops=list(pikepdf.parse_content_stream(page));selected=[];before_insert=None
  for oi,op in enumerate(ops):
   if oi==insert_at:before_insert=len(selected)
   name=str(op.operator)
   if name=='Do'and oi in remove_Do:continue
   if oi in remove_paints:assert name in ['S','s','f','F','f*','B','B*','b','b*'];selected.append(pikepdf.ContentStreamInstruction([],pikepdf.Operator('n')))
   else:selected.append(op)
  page.Contents=doc.make_stream(pikepdf.unparse_content_stream(selected));resources=pikepdf.Dictionary(page.Resources);resources.XObject=pikepdf.Dictionary(page.Resources.get('/XObject',{}));append=['q '+' '.join(_number(v)for v in _inverse(inv['final_ctm']))+' cm\n']
  for r in programs:
   with pikepdf.open(r['reference'])as ref:form=doc.copy_foreign(ref.pages[0].as_form_xobject())
   # The original PAGE transparency group already remains on the target page.
   # as_form_xobject copies it into a newly added nesting level; that changes
   # edge compositing. The new wrapper is an ordinary Form, so each original
   # paint retains precisely its original single page-group ancestry.
   if '/Group'in form:del form['/Group']
   box=f.Rect()
   for g in r['original_glyphs']:box|=f.Rect(g['bbox']);box.include_point(f.Point(g['origin']))
   for v in r['original_source_vector_paths']:box|=f.Rect(v['rect'])
   box=f.Rect(box.x0,box.y0-2,box.x1+(0 if r['atom'].get('reviewed_source2017_page07_reference_only')else 2),box.y1+2);form.BBox=pikepdf.Array([box.x0,height-box.y1,box.x1,height-box.y0]);name=pikepdf.Name('/Source2017CompleteExpression'+str(r['index']));assert name not in resources.XObject;resources.XObject[name]=form;append.append(str(name)+' Do\n');r.update(Form_name=str(name),Form_raw_sha256=hashlib.sha256(form.read_bytes()).hexdigest(),Form_bbox_page=list(box))
  append.append('Q\n');assert before_insert is not None;page.Resources=resources;page.Contents=doc.make_stream(pikepdf.unparse_content_stream(selected[:before_insert])+b'\n'+''.join(append).encode()+b'\n'+pikepdf.unparse_content_stream(selected[before_insert:]));single=out/f'page{n:02}.pdf';doc.save(single,compress_streams=False)
 with f.open(base)as before:roundtrip=_verify_glyphs(before[n-1],single.read_bytes(),set(),{},tolerance=.001)
 assert not roundtrip['native_glyph_mismatches']and not roundtrip['unexpected_glyphs']
 checks=[]
 for scale in [4,8]:
  with f.open(base)as before,f.open(single)as after:
   a=before[n-1].get_pixmap(matrix=f.Matrix(scale,scale),colorspace=f.csRGB,alpha=False);b=after[0].get_pixmap(matrix=f.Matrix(scale,scale),colorspace=f.csRGB,alpha=False);assert a.width==b.width and a.height==b.height;aa=np.frombuffer(a.samples,np.uint8).reshape(a.height,a.width,3);bb=np.frombuffer(b.samples,np.uint8).reshape(b.height,b.width,3);changed=int(np.any(aa!=bb,2).sum());checks.append(dict(renderer='MuPDF',scale=scale,changed_pixels=changed));assert changed==0,checks[-1]
 POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
 from PIL import Image
 for path,number,label in [(base,n,'before'),(single,1,'after')]:subprocess.run([POP,'-f',str(number),'-l',str(number),'-singlefile','-r','144','-png',str(path),str(out/label)],check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
 aa=np.asarray(Image.open(out/'before.png').convert('RGB'));bb=np.asarray(Image.open(out/'after.png').convert('RGB'));changed=int(np.any(aa!=bb,2).sum());checks.append(dict(renderer='independent external Poppler',dpi=144,changed_pixels=changed));assert changed==0,checks[-1]
 joined=out/f'IZhO_2017_TS_exact-native-expressions-{sha(single)[:16]}.pdf'
 with pikepdf.Pdf.new()as doc,pikepdf.open(base)as before,pikepdf.open(single)as after:
  for i,pg in enumerate(before.pages):doc.pages.append(after.pages[0]if i==n-1 else pg)
  doc.save(joined,compress_streams=False)
 newinv=inspect_inline_groups(joined,n);oldplan=out/'pre-isolation-plan.json';oldplan.write_bytes(P.read_bytes());p['source_base']=str(joined);p['source_base_sha256']=sha(joined)
 for a,r in zip(groups,programs):
  wanted={glyph_key(g)for g in a['source_native_glyphs']};forms=[v for v in newinv['forms']if v['original_raw_sha256']==r['Form_raw_sha256']and{glyph_key(g)for g in v['glyphs']if g['c'].strip()}==wanted];assert len(forms)==1;v=forms[0];a.update(source_form_path=v['path'],source_form_bbox=v['native_page_bbox']);r['source_form_path']=v['path']
 report=dict(source_sha256=SOURCE,source_page=n,pre_isolation_base_sha256=sha(base),new_immutable_base_sha256=sha(joined),isolated_page_sha256=sha(single),programs=programs,roundtrip_checks=checks,original_CID_roundtrip_qa=roundtrip,shared_guard_unchanged=True,passed=True);p['reviewed_source2017_complete_original_expression_program_isolation']=report;(out/'source-program-and-zeroRGB-contract.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');P.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf8')
print('SOURCE2017_COMPLETE_ORIGINAL_EXPRESSION_PROGRAM_ISOLATION_ZERO_RGB',n,checks,flush=True)

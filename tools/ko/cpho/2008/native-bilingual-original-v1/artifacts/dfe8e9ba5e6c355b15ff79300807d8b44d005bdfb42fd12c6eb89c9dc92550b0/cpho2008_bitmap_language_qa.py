"""Independent actual glyph/program and nonlanguage-pixel checks for source4."""
from pathlib import Path
from io import BytesIO
import json,hashlib,math
import pikepdf,pymupdf as f,numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from cpho2008_bitmap_language import policy,ALIAS
from cpho2008_prose_outline_primitives import trace_font_resources
from pdf_original_graphics_ink import graphics_control
B=Path(__file__).resolve().parents[1];S=B/'source/CPhO_2008_original_combined_ZH.pdf';SHA='4e076fb9234683d028792190bcec56f12de72890da6c0e44ddf0e9146013459d';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rgb(path):
 with f.open(path)as d:p=d[0].get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csRGB,alpha=False);return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()
def streams(page):return list(page.Contents)if isinstance(page.Contents,pikepdf.Array)else[page.Contents]
def audit(n,lang,target,c,coarse_graphics):
 assert n==4;target=Path(target);plan=json.loads(Path(c['actual_immutable_producing_plan']).read_text('utf8'));q=policy(plan);overlay=c['source_bitmap_language_overlay'];body=Path(overlay['actual_before_bitmap_language_body_path']);assert sha(body)==overlay['actual_before_bitmap_language_body_sha256'];folder=B/'evidence/bitmap-language';folder.mkdir(exist_ok=True);errors=[]
 # Source-only measurements are closed to these actual original CJK words.
 for index,row in enumerate(q['labels']):
  assert row['source_only_measured_size_pt']==[9.28459560660653,9.574087273837046][index]
  assert row['source_only_measured_baseline_pt']==[406.61330400609626,431.78499789759326][index]
 raw=Path(overlay['font']['subset_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==overlay['font']['subset_sha256']
 with TTFont(BytesIO(raw))as tt:
  cmap=tt.getBestCmap();gs=tt.getGlyphSet();em=tt['head'].unitsPerEm;expected=[]
  for row in q['labels']:
   point=row['source_only_measured_size_pt'];advance=0.;glyphs=[];bounds=[]
   for ch in row[lang]:
    name=cmap[ord(ch)];pen=BoundsPen(gs);gs[name].draw(pen);assert pen.bounds;l,b,r,t=pen.bounds;bounds.append([advance+l*point/em,advance+r*point/em]);glyphs.append((ch,tt.getGlyphID(name),advance));advance+=tt['hmtx'][name][0]*point/em
   center=row['source_word_ink_center_x'];x=center-(min(a[0]for a in bounds)+max(a[1]for a in bounds))/2
   expected.extend(dict(c=ch,gid=gid,font_alias='/'+ALIAS,size=point,origin=[x+offset,row['source_only_measured_baseline_pt']],color=[0.,0.,0.],render_type=0)for ch,gid,offset in glyphs)
 with pikepdf.open(target)as pdf,f.open(target)as native,pikepdf.open(body)as prior:
  page=pdf.pages[0];records,_=trace_font_resources(pdf,native[0]);actual=[g for g in records if g['font_alias']=='/'+ALIAS]
  label_font=page.Resources.Font[pikepdf.Name('/'+ALIAS)];fd=label_font.get('/DescendantFonts',[label_font])[0].FontDescriptor;field=next(k for k in ['/FontFile2','/FontFile3']if k in fd);font_exact=fd[field].read_bytes()==raw
  if not font_exact:errors.append('Actual bitmap-label font program differs from reviewed serif-bold donor subset')
  if len(expected)!=len(actual):errors.append(dict(expected_glyphs=len(expected),actual_glyphs=len(actual)))
  for wanted,got in zip(expected,actual):
   good=all(wanted[k]==got[k]for k in ['c','gid','font_alias','color','render_type'])and abs(wanted['size']-got['size'])<.001 and max(abs(a-b)for a,b in zip(wanted['origin'],got['origin']))<.001
   if not good:errors.append(dict(error='Actual label GID/font/point/source-baseline/source-word-center differs',expected=wanted,actual=got))
  previous=streams(prior.pages[0]);content=streams(page);before=[hashlib.sha256(s.read_bytes()).hexdigest()for s in previous];prefix=[hashlib.sha256(s.read_bytes()).hexdigest()for s in content[:len(previous)]]
  if before!=prefix:errors.append('Initial reviewed native/body content-program prefix changed during bitmap language overlay')
  suffix=content[len(previous):];at=0;label_programs=[]
  for row in q['labels']:
   white=suffix[at];ops=list(pikepdf.parse_content_stream(white));at+=1;names=[str(v.operator)for v in ops];assert set(names)<={'q','Q','re','h','rg','g','f'},names
   rectangles=[list(map(float,v.operands))for v in ops if str(v.operator)=='re'];assert len(rectangles)==1 and names.count('f')==1
   x0,y0,x1,y1=row['erase_rect_pt'];rect=[x0,841.6799926757812-y1,x1-x0,y1-y0]
   if max(abs(a-b)for a,b in zip(rectangles[0],rect))>.001:errors.append(dict(error='Language cover rectangle differs from isolated original word',actual=rectangles[0],expected=rect))
   colors=[list(map(float,v.operands))for v in ops if str(v.operator)in ['g','rg']];assert colors and all(all(a==1 for a in color)for color in colors)
   for char in row[lang]:
    stream=suffix[at];at+=1;assert('/'+ALIAS).encode()in stream.read_bytes();glyph_ops=list(pikepdf.parse_content_stream(stream));assert all(str(v.operator)in{'q','Q','BT','ET','Tm','Tf','Tr','Tj','TJ','rg','RG','g','G','w'}for v in glyph_ops);label_programs.append(hashlib.sha256(stream.read_bytes()).hexdigest())
  if at!=len(suffix):errors.append('Unreviewed content programs appended around bitmap labels')
  reference=folder/f'page04-{lang}-{sha(target)[:16]}-actual-label-glyphs-only.pdf'
  with pikepdf.Pdf.new()as out:
   out.pages.append(page);pg=out.pages[0];pg.Contents=pikepdf.Array([s for s in streams(pg)if('/'+ALIAS).encode()in s.read_bytes()]);out.save(reference,compress_streams=False)
 source_graphics=folder/'page04-actual-original-source-graphics.pdf'
 if not source_graphics.exists():
  with f.open(S)as doc:source_graphics.write_bytes(graphics_control(doc,doc[3]))
 final_graphics=folder/f'page04-{lang}-{sha(target)[:16]}-actual-final-graphics.pdf'
 with f.open(target)as doc:final_graphics.write_bytes(graphics_control(doc,doc[0]))
 original=rgb(source_graphics);after=rgb(final_graphics);old_mask=np.zeros(original.shape[:2],bool)
 for row in q['labels']:
  x0,y0,x1,y1=row['erase_rect_pt'];x0,y0,x1,y1=math.floor(x0*4),math.floor(y0*4),math.ceil(x1*4),math.ceil(y1*4);old_mask[y0:y1,x0:x1]|=np.any(original[y0:y1,x0:x1]!=255,2)
 changed=np.any(original!=after,2);outside=int((changed&~old_mask).sum());uncleared=int((old_mask&np.any(after!=255,2)).sum());pure=rgb(reference);proof=rgb(target);new_mask=np.any(pure!=255,2);overlap=int((new_mask&np.any(original!=255,2)&~old_mask).sum());new_rgb=int((np.any(pure!=proof,2)&new_mask).sum());missing=int(((pure.min(2)<32)&(proof.min(2)>=220)).sum())
 result=dict(original_source_sha256=SHA,source_page=4,language=lang,proof_sha256=sha(target),source_policy_sha256=plan['source_bitmap_language_policy_sha256'],source_measurement_sha256=q['source_measurement_sha256'],errors=errors,actual_label_glyphs_checked=len(actual),actual_label_font_program_exact=font_exact,original_body_program_prefix_exact=before==prefix,actual_original_language_ink_pixels=int(old_mask.sum()),actual_old_language_ink_not_cleared_pixels=uncleared,actual_new_label_glyph_program_sha256s=label_programs,actual_new_label_native_reference_path=str(reference),actual_new_label_native_reference_sha256=sha(reference),actual_original_graphics_control_path=str(source_graphics),actual_original_graphics_control_sha256=sha(source_graphics),actual_final_graphics_control_path=str(final_graphics),actual_final_graphics_control_sha256=sha(final_graphics),changed_original_nonlanguage_graphics_RGB_pixels=outside,new_label_over_original_nonlanguage_ink_pixels=overlap,new_label_native_RGB_differences=new_rgb,missing_new_label_native_ink_pixels=missing,actual_original_images_reencoded_or_replaced=False,actual_source_font_point_metadata_claimed_for_bitmap=False,passed=not errors and outside==uncleared==overlap==new_rgb==missing==0)
 out=target.with_suffix('.bitmap-language-native-source-audit.json');out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');print('C08_ACTUAL_BITMAP_LABEL_NATIVE_AND_NONLANGUAGE_RGB',lang,result['passed'],'outside',outside,'uncleared',uncleared,'overlap',overlap,'RGB',new_rgb,'missing',missing,'errors',len(errors),flush=True)
 adjusted=dict(coarse_graphics,raw_coarse_changed_nonselected_native_graphical_pixels=coarse_graphics['changed_nonselected_native_graphical_pixels'],explicit_original_bitmap_language_ink_pixels=int(old_mask.sum()),changed_nonselected_native_graphical_pixels=outside,source_specific_bitmap_language_qa=result)
 return result,adjusted

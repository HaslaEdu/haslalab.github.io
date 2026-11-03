"""Source-native program, fixed font, collision and actual math visibility QA."""
from pathlib import Path
from io import BytesIO
from collections import Counter,defaultdict
import argparse,json,re,sys,hashlib,math
import pymupdf as fitz,numpy as np,pikepdf
from cpho_2005_ts_compose import BASE,SOURCE,SOURCE_SHA,sha,row_layout,write_row_token,width,isolate_native_raster_instances
from pdf_scanned_translation_ink_qa import audit_scan_page
from pdf_original_raster_math import source_recipe,roundtrip,geometry_copy,add_form,reset_state,command

def single_math_reference(number,atom):
 recipe=source_recipe(SOURCE,number,atom['image_path'])
 roundtrip(SOURCE,number,recipe,atom['source_rect'])
 with pikepdf.open(SOURCE)as source,pikepdf.Pdf.new()as doc:
  sp=source.pages[number-1];page=doc.add_blank_page(page_size=(float(sp.MediaBox[2]),float(sp.MediaBox[3])));geometry_copy(sp,page,doc,source)
  page.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(OriginalSingleMath=add_form(doc,source,sp,recipe)),ExtGState=pikepdf.Dictionary(OriginalRasterReset=reset_state()))
  # Match the explicitly introduced opacity-isolation pipeline, while retaining
  # one independent original source invocation and no other replayed atom.
  page.Resources.XObject.OriginalSingleMath.Group=pikepdf.Dictionary(S=pikepdf.Name.Transparency,I=True,K=False,CS=pikepdf.Name.DeviceRGB)
  page.Contents=doc.make_stream(command(recipe,atom['source_rect'],atom['dx'],'OriginalSingleMath'))
  result=BytesIO();doc.save(result,compress_streams=False)
 return result.getvalue()

def body_style(target,layout,lang,composition,metrics):
 from izho_new_prose_outline_qa import trace_font_resources
 errors=[];counts=defaultdict(Counter);checked=0
 with pikepdf.open(target)as pdf,fitz.open(target)as doc:
  mapped,_=trace_font_resources(pdf,doc[0]);traces=doc[0].get_texttrace();tokens=[]
  for row in layout['rows']:
   for token in row_layout(row,lang,metrics[row['source_prose_face']])[0]:
    if token['kind']=='prose'and token['text'].strip():tokens.append((row,token))
  for glyph in mapped:
   if not glyph['font_alias'].startswith('/TSScanBody')or glyph['c'].isspace():continue
   checked+=1
   matches=[(r,t)for r,t in tokens if abs(r['size']-glyph['size'])<.001 and abs(r['baseline']-glyph['origin'][1])<.001 and t['x']-.001<=glyph['origin'][0]<t['x']+t['width']+.001]
   if len(matches)!=1:errors.append(dict(reason='No unique fixed-size/baseline prose slot',glyph=glyph));continue
   row,token=matches[0];face=row['source_prose_face']
   expected_font=composition['body_fonts'][face]['subset_sha256']
   if glyph['font_program_sha256']!=expected_font:errors.append(dict(reason='Actual new font program differs',glyph=glyph))
   if glyph['render_type']==2:counts[row['id']].update([0,1])
   else:counts[row['id']][glyph['render_type']]+=1
   if glyph['render_type']!=2:errors.append(dict(reason='Source-estimated glyph paint mode differs',glyph=glyph))
   expected=row['printed_stroke_by_language'][lang]['regular']
   matching=[t for t in traces if t['type']==1 and abs(t['size']-glyph['size'])<.001 and any(cp==ord(glyph['c'])and gid==glyph['gid']and abs(point[0]-glyph['origin'][0])<.001 and abs(point[1]-glyph['origin'][1])<.001 for cp,gid,point,bbox in t['chars'])]
   if not matching or any(abs(t['linewidth']-expected)>1e-5 for t in matching):errors.append(dict(reason='Actual source-calibrated stroke differs',glyph=glyph,expected=expected,actual=[t['linewidth']for t in matching]))
  for row in layout['rows']:
   expected=sum(not c.isspace()for c in re.sub(r'\[\[[^\]]+\]\]','',row[lang]))
   if counts[row['id']]!=Counter({0:expected,1:expected}):errors.append(dict(reason='Actual glyph paint counts differ',row=row['id'],expected=expected,actual=dict(counts[row['id']])))
 return dict(glyph_paints_checked=checked,errors=errors,passed=not errors)

def audit(number,lang):
 target=BASE/f'proofs/{lang}/page{number:02}.pdf';composition=json.loads(target.with_suffix('.composition.json').read_text('utf8'));layout=json.loads((BASE/f'authoring/page{number:02}-layout.json').read_text('utf8'))
 if sha(SOURCE)!=SOURCE_SHA or sha(target)!=composition['output_sha256']:raise ValueError('Pinned source or final proof changed')
 metrics={};fonts={}
 for face,record in composition['body_fonts'].items():
  raw=Path(record['subset']).read_bytes()
  if hashlib.sha256(raw).hexdigest()!=record['subset_sha256']:raise ValueError('Pinned actual font changed')
  fonts[face]=raw;metrics[face]=fitz.Font(fontbuffer=raw)
 with fitz.open(SOURCE)as source:bounds=source[number-1].rect
 prose=target.with_suffix('.prose-only.pdf')
 with fitz.open()as d:
  p=d.new_page(width=bounds.width,height=bounds.height)
  for face,raw in fonts.items():p.insert_font(fontname='TSScanBody'+face,fontbuffer=raw)
  for row in layout['rows']:
   face=row['source_prose_face']
   for token in row_layout(row,lang,metrics[face])[0]:
    if token['kind']=='prose':write_row_token(p,row,token,metrics[face],'TSScanBody'+face,lang)
  d.save(prose,garbage=0,deflate=False)
 control=target.with_suffix('.math-control.pdf');control.write_bytes(target.with_suffix('.pre-prose.pdf').read_bytes())
 math=composition['inline_math_replay']['atoms'];isolate_native_raster_instances(control,len(math))
 slots=json.loads((BASE/'inputs/native-slots.json').read_text('utf8'))['pages'][number-1]['slots']
 headers=[c['bbox']for slot in slots for c in slot['source_characters']]
 headers +=[[r['left']-1,r['baseline']-r['size']*1.4,r['right']+1,r['baseline']+r['size']*.4]for r in composition['header']['placements']]
 report=audit_scan_page(SOURCE,number,target,control,prose,
  language_erase_rects=[rect for r in layout['rows']for rect in r['erase_rects']],
  new_prose_rects=[[r['left']-1,r['baseline']-r['size']*1.3,r['right']+1,r['baseline']+r['size']*.4]for r in composition['body_placements']],
  original_inline_math_rects=[a['rect']for r in layout['rows']for a in r['atoms']],moved_inline_math_rects=[a['destination_rect']for a in math],protected_source_rects=layout.get('protected_source_display_and_figure_rects',[]),native_header_change_rects=headers,replayed_math_records=math,reviewed_blank_records=layout.get('reviewed_blank_background_rects',[]))
 target.with_suffix('.generic-scan-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
 # An actual final-page pixel check against a separate, single-atom original
 # source control catches missing/cached math that program/CTM audits cannot.
 blank=target.with_suffix('.blank-control.pdf')
 with fitz.open()as d:d.new_page(width=bounds.width,height=bounds.height);d.save(blank)
 with fitz.open(target)as d:
  p=d[0].get_pixmap(matrix=fitz.Matrix(4,4),alpha=False,colorspace=fitz.csRGB)
  final=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()
 records=[]
 for atom in math:
  raw=single_math_reference(number,atom)
  with fitz.open(stream=raw,filetype='pdf')as d:
   ref=d[0].get_pixmap(matrix=fitz.Matrix(4,4),clip=fitz.Rect(atom['destination_rect']),alpha=False,colorspace=fitz.csRGB)
   expected=np.frombuffer(ref.samples,np.uint8).reshape(ref.height,ref.width,3)
   actual=final[ref.y:ref.y+ref.height,ref.x:ref.x+ref.width]
   if actual.shape!=expected.shape:raise ValueError('Native math reference geometry differs')
   changed=np.any(actual!=expected,axis=2)
   deep=int(np.any(expected<150,axis=2).sum())
   if not deep:raise ValueError(('Independent native mathematical reference has no actual dark glyph ink',atom['id']))
   records.append(dict(id=atom['id'],source_rect=atom['source_rect'],destination_rect=atom['destination_rect'],changed_RGB_pixels=int(changed.sum()),expected_nonwhite_pixels=int(np.any(expected<248,axis=2).sum()),expected_actual_dark_glyph_pixels=deep))
   if changed.any():
    from PIL import Image
    im=Image.new('RGB',(ref.width*2+8,ref.height),'white');im.paste(Image.fromarray(expected),(0,0));im.paste(Image.fromarray(actual),(ref.width+8,0));im.save(target.parent/f'page{number:02}.math-diff-{atom["id"]}.png')
 style=body_style(target,layout,lang,composition,metrics)
 import pdf_new_prose_outlines as outlines
 old=outlines.PREFIXES
 try:outlines.PREFIXES=('/TSHeader','/TSScanBody');outline=outlines.audit(target)
 finally:outlines.PREFIXES=old
 report.update(actual_final_math_single_native_source_controls=dict(atoms=len(records),RGB_errors=sum(r['changed_RGB_pixels']for r in records),records=records),actual_prose_font_point_baseline_and_paint=style,new_prose_outlines=outline,publication_ready=False,full_edition_complete=False)
 report['passed']=report['passed']and style['passed']and outline['passed']and not any(r['changed_RGB_pixels']for r in records)
 target.with_suffix('.source-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
 print(lang,number,'PASS',report['passed'],'metrics',{k:v['pixels']for k,v in report.items()if isinstance(v,dict)and'pixels'in v},'math_RGB_errors',sum(r['changed_RGB_pixels']for r in records),'style_errors',len(style['errors']),flush=True)
 return report

if __name__=='__main__':
 from pdf_memory_gate import page_worker
 p=argparse.ArgumentParser();p.add_argument('page',type=int);p.add_argument('language',choices=['ko','en']);a=p.parse_args()
 with page_worker():audit(a.page,a.language)

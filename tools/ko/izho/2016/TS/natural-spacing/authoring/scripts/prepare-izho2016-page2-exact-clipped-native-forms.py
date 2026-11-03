from pathlib import Path
import json,hashlib,sys,pikepdf,pymupdf as f,numpy as np,subprocess,os
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');E=B/'engine';sys.path[:0]=[str(E),'D:/CodexBuilds/Hasla-publish-20261031/tools'];SOURCE='19f23f790b5dd43bf2303f4b597da862c5d17a0267320fee3cca7f5f015a1df8';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups,_traces
from pdf_original_text_ops import glyph_key
helper=E/'pdf_source_prose_reference_forms.py';text=helper.read_text('utf8');history=E/'history'/sha(helper);history.mkdir(parents=True,exist_ok=True);(history/helper.name).write_bytes(helper.read_bytes());text=text.replace("g['font']!='CambriaMath'","g['font']not in['CambriaMath','Cambria Math']").replace("SOURCE='41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db'","SOURCE="+repr(SOURCE)).replace("/'2012/native-reference-isolation/failures'","/'2016/native-reference-isolation/failures'");helper.write_text(text,'utf8')
engine=E/'izho_natural_spacing_rebuild.py';text=engine.read_text('utf8');needle="any(g['font']!='CambriaMath'for g in glyphs)";replacement="any(not(g['font']=='CambriaMath'or(d['original_english_source_sha256']=="+repr(SOURCE)+"and g['font']=='Cambria Math'))for g in glyphs)"
if needle in text:
 history=E/'history'/sha(engine);history.mkdir(parents=True,exist_ok=True);(history/engine.name).write_bytes(engine.read_bytes());engine.write_text(text.replace(needle,replacement),'utf8')
from pdf_source_prose_reference_forms import promote
P=B/'natural/2016/TS/plans/page02.json';p=json.loads(P.read_text('utf8'));assert p['original_english_source_sha256']==sha(p['original_english_source'])==SOURCE;base=Path(p['source_base']);assert sha(base)==p['source_base_sha256'];groups=[]
with page_worker():
 with f.open(base)as doc:actual={glyph_key(g):g for g in _traces(doc[1])if g['c'].strip()}
 for index,label in[(0,'Complete original CV-R'),(1,'Complete original R/2')]:
  a=p['explicit_native_math_atoms'][index];assert a['baseline']==84.62
  if index==1:
   a['source_native_glyphs']=[g for g in a['source_native_glyphs']if g['font']=='Cambria Math'];a['rect']=[277,74,297.5,96]
  gs=[actual[glyph_key(g)]for g in a['source_native_glyphs']];assert all(g['font']=='Cambria Math'for g in gs);groups.append(dict(source_at=[1,1,index],source_text=label,glyphs=gs))
 raw,qa=promote(base,2,groups,sum(len(v['parts'])for v in p['prose_placements']))
 out=B/'2016/native-reference-isolation'/p['source_base_sha256'][:16];out.mkdir(parents=True,exist_ok=True);single=out/'page02.pdf';single.write_bytes(raw);qa.update(original_english_source_sha256=SOURCE,private_engine_sha256=sha(helper));single.with_suffix('.native-cid-qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n','utf8');assert qa['passed']
 checks=[]
 for scale in[4,8]:
  with f.open(base)as old,f.open(single)as new:
   a=old[1].get_pixmap(matrix=f.Matrix(scale,scale),colorspace=f.csRGB,alpha=False);b=new[0].get_pixmap(matrix=f.Matrix(scale,scale),colorspace=f.csRGB,alpha=False);aa=np.frombuffer(a.samples,np.uint8).reshape(a.height,a.width,3);bb=np.frombuffer(b.samples,np.uint8).reshape(b.height,b.width,3);changed=int(np.any(aa!=bb,axis=2).sum());checks.append(dict(renderer='MuPDF RGB',scale=scale,changed_pixels=changed));assert changed==0,checks[-1]
 POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
 for pdf,page,name in[(base,2,'page02-before'),(single,1,'page02-after')]:subprocess.run([POP,'-f',str(page),'-l',str(page),'-singlefile','-r','144','-png',str(pdf),str(out/name)],check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
 from PIL import Image
 aa=np.asarray(Image.open(out/'page02-before.png').convert('RGB'));bb=np.asarray(Image.open(out/'page02-after.png').convert('RGB'));changed=int(np.any(aa!=bb,axis=2).sum());checks.append(dict(renderer='independent external Poppler RGB',dpi=144,changed_pixels=changed));assert changed==0,checks[-1]
 version=hashlib.sha256((sha(base)+sha(single)).encode()).hexdigest()[:16];joined=out/f'IZhO_2016_TS_native-base-original-CIDs-clips-8p-{version}.pdf'
 with pikepdf.Pdf.new()as doc,pikepdf.open(base)as original,pikepdf.open(single)as promoted:
  for index,page in enumerate(original.pages):doc.pages.append(promoted.pages[0]if index==1 else page)
  doc.save(joined,compress_streams=False)
 inv=inspect_inline_groups(str(joined),2)
 history=P.parent/'history'/sha(P);history.mkdir(parents=True,exist_ok=True);(history/P.name).write_bytes(P.read_bytes());p['source_base']=str(joined);p['source_base_sha256']=sha(joined);bindings=[]
 for index,a in enumerate(p['explicit_native_math_atoms']):
  keys={glyph_key(g)for g in a['source_native_glyphs']};forms=[v for v in inv['forms']if{glyph_key(g)for g in v['glyphs']if g['c'].strip()}==keys]
  if len(forms)!=1:
   assert index not in[0,1]and'source_form_path'not in a,(index,len(forms));continue
  v=forms[0];a.update(source_form_path=v['path'],source_form_bbox=v['native_page_bbox'])
  if index in[0,1]:a.update(source_reference_preserve_original_glyph_advance=True,source_form_program_sha256=v['original_raw_sha256'])
  bindings.append(dict(rect=a['rect'],path=v['path'],original_form_bbox=v['native_page_bbox'],original_form_program_sha256=v['original_raw_sha256'],complete_native_glyph_set=True,reason='Original encoded CID/font/Tf/Tm/paint and exact inherited original raw re/W/n clip programs copied into independent native source-reference Form. Full-page MuPDF4x/8x and external Poppler144 RGB roundtrips are byte-pixel identical before movement. Original advance retained; no Unicode/math retyping, synthetic clip or threshold changes.'))
p['reviewed_complete_original_mathematical_form_bindings']=bindings;p['reviewed_original_clipped_native_expression_isolation']=dict(source_sha256=SOURCE,pre_isolation_base_sha256=sha(base),isolated_page_sha256=sha(single),new_immutable_base_sha256=sha(joined),roundtrip_checks=checks,report=str(single.with_suffix('.roundtrip.json')))
P.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf8');single.with_suffix('.roundtrip.json').write_text(json.dumps(p['reviewed_original_clipped_native_expression_isolation'],ensure_ascii=False,indent=2)+'\n','utf8')
assert sha(E/'pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f';print('IZHO2016_PAGE2_EXACT_CLIPPED_NATIVE_FORMS_ZERO_PIXEL_ROUNDTRIPS',checks,flush=True)

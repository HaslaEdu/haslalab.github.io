from pathlib import Path
from io import BytesIO
import sys,json,hashlib,os,pikepdf,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2014-complete-solutions');F=B/'natural/2014/TS';OUT=B/'natural/2014-page02-independent-native-parenthesis-witness';sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import _traces
from pdf_native_glyph_raster_witness import audit as cid_audit,replay
from pdf_moved_native_ink import audit_moved_native_ink
from pdf_original_text_ops import glyph_key
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();SOURCE_SHA='1e526966f308280accc9fe747d08259279f35324e7e7f2e0290271adcaf6536c';PROOF_SHA='bfeda4e1facf5b4555781d2c517dae2d1140a7e14aee428fe05ecfee297da3c2';source=B/'2014/source/IZhO_2014_TS.pdf';target=F/'page02.pdf'
def main():
 assert sha(source)==SOURCE_SHA and sha(target)==PROOF_SHA
 assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
 OUT.mkdir(exist_ok=True)
 with f.open(source)as doc:old=[g for g in _traces(doc[1])if g['c']=='('and abs(g['origin'][0]-257.8475036621094)<.001 and abs(g['origin'][1]-760.8822631835938)<.001]
 assert len(old)==1,old;glyph=old[0]
 with f.open(target)as doc:new=[g for g in _traces(doc[0])if g['c']==glyph['c']and g['font']==glyph['font']and g['trace_gid']==glyph['trace_gid']and abs(g['size']-glyph['size'])<.0001 and abs(g['origin'][1]-glyph['origin'][1])<.001]
 assert len(new)==1,new;actual=new[0];dx=actual['origin'][0]-glyph['origin'][0]
 composition=json.loads((F/'page02.qa.json').read_text('utf8'));moves=[s['dx']for s in composition['native_shifts']for g in s['glyphs']if glyph_key(g)==glyph_key(glyph)];assert moves and max(abs(v-dx)for v in moves)<.001
 print('EXACT_ORIGINAL_LEFT_PARENTHESIS_NATIVE_TRACE_IDENTITY',json.dumps(dict(font=glyph['font'],point=glyph['size'],gid=glyph['trace_gid'],source_origin=glyph['origin'],actual_origin=actual['origin'],dx=dx),ensure_ascii=False),flush=True)
 assert glyph['font']=='TimesNewRomanPSMT'and glyph['size']==12 and abs(actual['origin'][0]-194.39557647705078)<.001
 report=dict(original_English_source=str(source),original_language_source_sha256=SOURCE_SHA,source_page=2,proof=str(target),proof_sha256=PROOF_SHA,source_glyph=glyph,actual_target_glyph=actual,requested_dx=dx,original_journal_dx=moves,proof_unmodified=True,delivered_pdf_modified=False,mathematics_retyped=False,source_font_programs_substituted=False)
 try:
  raw,cid_replay=replay(source,2,glyph,dx);reference=OUT/'original-encoded-left-parenthesis-at-actual-destination.pdf';reference.write_bytes(raw);report['exact_original_native_CID_replay']=cid_replay;report['original_encoded_reference_pdf_sha256']=sha(reference)
  report['native_CID_reference']=cid_audit(source,2,target,glyph,dx,4)
  cropped_source=OUT/'original-source-same-integer-crop.pdf';cropped_final=OUT/'current-proof-same-integer-crop.pdf';clip=[180,740,315,777]
  for original,page_index,destination in[(source,1,cropped_source),(target,0,cropped_final)]:
   with pikepdf.open(original)as pdf:
    with pikepdf.Pdf.new()as out:
     out.pages.append(pdf.pages[page_index]);page=out.pages[0];height=float(page.MediaBox[3]);page.CropBox=pikepdf.Array([clip[0],height-clip[3],clip[2],height-clip[1]]);out.save(destination,compress_streams=False)
  with f.open(cropped_source)as doc:candidates=[g for g in _traces(doc[0])if g['c']==glyph['c']and g['font']==glyph['font']and g['trace_gid']==glyph['trace_gid']and abs(g['origin'][0]-(glyph['origin'][0]-clip[0]))<.001 and abs(g['origin'][1]-(glyph['origin'][1]-clip[1]))<.001]
  assert len(candidates)==1,candidates;cropped=candidates[0]
  svg={};native={}
  for scale in[4,8,12]:
   svg[str(scale)]=audit_moved_native_ink(cropped_source,1,cropped_final,shifts=[dict(glyphs=[cropped],dx=dx)],protected_glyphs=[cropped],scale=scale)
   native[str(scale)]=cid_audit(cropped_source,1,cropped_final,cropped,dx,scale)
  report.update(svg_reference_scales=svg,cropped_native_CID_reference_scales=native,crop_reference_source_sha256=sha(cropped_source),crop_reference_final_sha256=sha(cropped_final),same_integer_page_crop=clip)
  report['passed']=report['native_CID_reference']['passed']and all(svg[s]['passed']and svg[s]['newly_missing_native_ink_pixels']==0 for s in['8','12'])and all(q['passed']for q in native.values())
 except Exception as error:
  report.update(passed=False,independent_reference_failure=f'{type(error).__name__}: {error}')
 assert sha(source)==SOURCE_SHA and sha(target)==PROOF_SHA
 (OUT/'witness.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
 print('SOURCE2014_PAGE2_INDEPENDENT_LEFT_PARENTHESIS_REFERENCE',json.dumps(dict(passed=report['passed'],source_point=glyph['size'],source_font=glyph['font'],source_gid=glyph['trace_gid'],actual_origin=actual['origin'],cid_missing=report.get('native_CID_reference',{}).get('missing_native_CID_reference_pixels'),svg_missing={s:q.get('newly_missing_native_ink_pixels')for s,q in report.get('svg_reference_scales',{}).items()},native_missing={s:q.get('missing_native_CID_reference_pixels')for s,q in report.get('cropped_native_CID_reference_scales',{}).items()},failure=report.get('independent_reference_failure'),report=str(OUT/'witness.json')),ensure_ascii=False),flush=True)
with page_worker():main()

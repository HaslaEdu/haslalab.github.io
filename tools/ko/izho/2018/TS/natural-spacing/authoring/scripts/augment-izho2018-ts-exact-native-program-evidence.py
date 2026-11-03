from pathlib import Path
import sys,json,hashlib,os,pikepdf,pymupdf as f,numpy as np
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from izho2018_ts_literal_form_program import read_form
from pdf_native_inline_reposition import _traces
from pdf_text_motion_ink import ink_envelope
from izho_2018_independent_original_math_geometry import same
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();source=B/'2018/source/IZhO_2018_TS.pdf'
def find(path,page,digest):
 with pikepdf.open(path)as pdf:
  p=pdf.pages[page-1];hits=[]
  for i,op in enumerate(pikepdf.parse_content_stream(p)):
   if str(op.operator)=='Do':
    obj=p.Resources.XObject[str(op.operands[0])]
    if str(obj.get('/Subtype'))=='/Form'and hashlib.sha256(obj.read_raw_bytes()).hexdigest()==digest:hits.append([i])
  assert len(hits)==1,(path,hits);return hits[0]
for n in[2,5,8]:
 O=B/(f'natural/2018-page{n:02}-original-'+('formula6-program'if n==2 else'native-word-program'));path=O/'witness.json';w=json.loads(path.read_text('utf8'));assert w['passed'];proof=Path(w['proof']);dx=w['independently_inferred_whole_original_expression_dx'];gs=w['complete_original_expression_glyphs']
 with page_worker():
  with f.open(source)as original,f.open(proof)as final:
   actual=_traces(final[0]);source_actual=_traces(original[n-1]);records=[]
   for g in gs:
    assert any(same(g,h)and max(abs(a-b)for a,b in zip(g['origin'],h['origin']))<.001 for h in source_actual)
    found=[h for h in actual if same(g,h)and abs(h['origin'][0]-g['origin'][0]-dx)<.001];assert len(found)==1;records.append(dict(source_glyph=g,actual_target_glyph=found[0],requested_dx=dx,all_original_native_font_GID_fractional_points_paint_and_Y_preserved=True))
   envelope,uses=ink_envelope(original[n-1],[g['origin']for g in gs],12);yy,xx=np.nonzero(envelope);bounds=[float(xx.min()/12+dx),float(yy.min()/12),float((xx.max()+1)/12+dx),float((yy.max()+1)/12)];R=w['same_integer_page_crop'];assert R[0]<=bounds[0]and R[1]<=bounds[1]and bounds[2]<=R[2]and bounds[3]<=R[3],(n,R,bounds)
  w['independent_exact_original_visible_glyph_records']=records;w['native_reference_crop_contains_complete_original_expression_actual_outline_envelope']=dict(scale=12,source_outline_uses=uses,source_native_expression_ink_envelope_after_common_dx=bounds,crop=R,contains_all_selected_original_mathematical_ink=True)
  if n==2:
   digest=w['original_form']['original_raw_sha256'];programs=[read_form(inp,page,find(inp,page,digest))for inp,page in[(source,2),(w['source_reference_file'],1),(proof,1)]];assert programs[0]==programs[1]==programs[2];q=programs[0];w['exact_original_Form_CID_Tf_fullTm_programs']=dict(original=q,reference=programs[1],actual=programs[2],all_raw_programs_and_font_resources_identical=True);w['complete_original_encoded_Form_CIDs_checked']=len(q['all_encoded_CID_Tf_fullTm_programs']);w['complete_original_visible_native_glyphs_checked']=21;print('LITERAL_ORIGINAL2018_FORM_CID_PROGRAM_COUNTS',len(q['all_encoded_CID_Tf_fullTm_programs']),sum(bool(r['unicode'].strip())for r in q['all_encoded_CID_Tf_fullTm_programs']),flush=True)
  else:
   assert len(w['exact_original_CID_programs'])==len(gs)
   for r in w['exact_original_CID_programs']:
    assert r['reference_encoded_program']['CTM']==r['actual_encoded_program']['CTM']
   w['complete_original_visible_native_glyphs_checked']=len(gs)
  w['unaugmented_reference_witness_sha256']=sha(path);out=O/'witness-with-exact-source-programs.json';out.write_text(json.dumps(w,ensure_ascii=False,indent=2)+'\n','utf8');print('SOURCE2018_EXACT_NATIVE_PROGRAM_FINAL_WITNESS',n,sha(out),flush=True)

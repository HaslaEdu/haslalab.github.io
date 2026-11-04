"""Five deliberately bad actual PDFs, checked against independent audits."""
from pathlib import Path
from io import BytesIO
from collections import Counter
import sys,json,hashlib,importlib.util
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');sys.path.insert(0,str(B/'engine'));N=B/'evidence/negative-controls';N.mkdir(exist_ok=True)
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import _traces,reposition_inline
from pdf_original_text_ops import glyph_key
from cpho2003_initial_native_baseline import selected_glyphs
from pdf_moved_native_ink import audit_moved_native_ink
from pdf_new_prose_native_text_overlap import audit as collision
from pdf_native_script_motion_audit import audit as geometry
from cpho_natural_full_qa import native_font_programs
import pymupdf as f,pikepdf
from fontTools.ttLib import TTFont
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,q):
 if p.exists():
  old=json.loads(p.read_text('utf8'));q=json.loads(json.dumps(q));assert old['passed']==q['passed']==False,p
  for k in ['source_sha256','output_sha256','sha256','dark_prose_pixels_over_native_text','newly_missing_native_ink_pixels','missing_final_native_glyphs','glyph_signature_or_position_errors','relative_geometry_failures']:
   if k in old or k in q:assert old.get(k)==q.get(k),(p,k)
 else:p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
source=B/'inputs/CPhO_2003_Chinese_original.pdf';positive=B/'natural/2003/en/page02.pdf';positive3=B/'natural/2003/en/page03.pdf';data=json.loads((B/'inputs/original-all10-source-slots.json').read_text('utf8'));q=json.loads(positive.with_suffix('.qa.json').read_text('utf8'))
with page_worker(),f.open(source)as src,f.open(positive)as good:
 erased={glyph_key(g)for g in selected_glyphs(data['pages'][1])};native=[g for g in _traces(src[1])if g['c'].strip()and glyph_key(g)not in erased]
 delta=next(g for g in _traces(good[0])if g['c']=='Δ'and abs(g['origin'][1]-444.1899719238281)<.001)
 records=[]
 # Actual original mathematical CID deletion.
 raw,metadata=reposition_inline(positive,1,erased_glyphs=[delta]);bad=N/'rejected-erased-original-Delta.pdf';
 if not bad.exists():bad.write_bytes(raw)
 report=audit_moved_native_ink(source,2,bad,protected_glyphs=native,shifts=q['native_shifts']);assert report['passed']is False and any(g['c']=='Δ'for g in report['missing_final_native_glyphs']);save(bad.with_suffix('.rejection.json'),report)
 records.append(dict(type='original-native-CID-erased',fixture=bad.name,sha256=sha(bad),rejected=True,report=bad.with_suffix('.rejection.json').name))
 # New real embedded source-family prose painted through retained native ink.
 bad=N/'rejected-new-prose-over-original-Delta.pdf'
 if not bad.exists():
  with f.open(positive)as doc:
   doc[0].insert_text(delta['origin'],'MMMM',fontname='TranslationserifRegular',fontsize=delta['size'],color=(0,0,0));doc.save(bad,garbage=0,deflate=False)
 report=collision(bad,native_glyphs=native,shifts=q['native_shifts']);assert report['passed']is False and report['dark_prose_pixels_over_native_text']>0;save(bad.with_suffix('.rejection.json'),report)
 records.append(dict(type='actual-new-prose-over-native-math',fixture=bad.name,sha256=sha(bad),rejected=True,collision_pixels=report['dark_prose_pixels_over_native_text'],report=bad.with_suffix('.rejection.json').name))
 # Move only the original zero script inside the original m2=4m0 expression.
 evidence=json.loads((B/'authoring/native/complete-inline-expressions-evidence.json').read_text('utf8'));expr=next(e for e in evidence if e['page']==3 and e['text']=='m2＝4m0');cq=json.loads(positive3.with_suffix('.qa.json').read_text('utf8'));offset={glyph_key(g):s['dx']for s in cq['native_shifts']for g in s['glyphs']}
 with f.open(positive3)as doc:
  actual=_traces(doc[0]);group=[]
  for g in expr['physical_glyphs']:
   expected=(g['origin'][0]+offset.get(glyph_key(g),0),g['origin'][1]);matches=[h for h in actual if h['c']==g['c']and h['font']==g['font']and h['trace_gid']==g['trace_gid']and abs(h['size']-g['size'])<1e-6 and max(abs(a-b)for a,b in zip(h['origin'],expected))<.001];assert len(matches)==1;group.append(matches[0])
 zero=next(g for g in group if g['c']=='0');shifts=[dict(glyphs=[zero],dx=2.)];raw,metadata=reposition_inline(positive3,1,shifts=shifts);bad=N/'rejected-original-zero-script-shifted-alone.pdf';
 if not bad.exists():bad.write_bytes(raw)
 report=geometry(positive3,1,bad,native_glyphs=group,shifts=shifts,expression_groups=[dict(label='Original m2=4m0 complete expression',glyphs=group)]);assert report['passed']is False and any(g['passed']is False for g in report['reviewed_expression_groups']);save(bad.with_suffix('.rejection.json'),report)
 records.append(dict(type='original-script-relative-geometry',fixture=bad.name,sha256=sha(bad),rejected=True,report=bad.with_suffix('.rejection.json').name))
 # Wrong point size in an actual newly authored prose text-show stream.
 bad=N/'rejected-new-prose-wrong-9_5pt-size.pdf';assert not bad.exists()
 with pikepdf.open(positive)as pdf:
  changed=False
  contents=pdf.pages[0].Contents
  for stream in (list(contents)if isinstance(contents,pikepdf.Array)else [contents]):
   ops=list(pikepdf.parse_content_stream(stream))
   for i,op in enumerate(ops):
    if str(op.operator)=='Tf'and str(op.operands[0])=='/TranslationserifRegular':
     operands=list(op.operands);operands[1]=9.5;ops[i]=pikepdf.ContentStreamInstruction(operands,op.operator);stream.write(pikepdf.unparse_content_stream(ops));changed=True;break
   if changed:break
  assert changed;pdf.save(bad,compress_streams=False)
 wrong_size=bad
 # Wrong actual embedded body glyph outline, retaining its name/GID/advance.
 bad=N/'rejected-new-prose-mutated-p-outline.pdf';assert not bad.exists();pg=next(g for g in _traces(good[0])if g['c']=='p'and g['font']=='CPhO2003TranslationSimSun')
 with pikepdf.open(positive)as pdf:
  descriptor=pdf.pages[0].Resources.Font['/TranslationserifRegular'].DescendantFonts[0].FontDescriptor;font=TTFont(BytesIO(descriptor.FontFile2.read_bytes()),recalcTimestamp=False);glyph=font['glyf'][font.getGlyphOrder()[pg['trace_gid']]];assert not glyph.isComposite()and glyph.numberOfContours>0
  for i,(x,y)in enumerate(glyph.coordinates):glyph.coordinates[i]=(round(x*.75),y)
  out=BytesIO();font.save(out);font.close();descriptor.FontFile2.write(out.getvalue());pdf.save(bad,compress_streams=False)
 wrong_outline=bad
 spec=importlib.util.spec_from_file_location('cpho2003_actual_prose_style_auditor',Path('D:/CodexBuilds/audit-cpho2003-actual-prose-style.py'));style=importlib.util.module_from_spec(spec);spec.loader.exec_module(style)
 for fixture,kind,expected in [(wrong_size,'new-prose-point-size','No original source role/size/baseline'),(wrong_outline,'new-prose-actual-donor-outline','Actual embedded glyph outline differs from donor')]:
  style.OUT=N/('unexpected-accepted-'+kind)
  try:style.audit_page('en',2,proof_override=fixture)
  except AssertionError as error:
   reason=str(error);assert expected in reason,reason
  else:raise AssertionError('Actual bad new prose was accepted: '+kind)
  report=dict(passed=False,source_sha256=sha(source),positive_sha256=sha(positive),fixture_sha256=sha(fixture),rejected=True,actual_auditor_reason=reason,expected_original_source_failure=expected);save(fixture.with_suffix('.rejection.json'),report);records.append(dict(type=kind,fixture=fixture.name,sha256=sha(fixture),rejected=True,report=fixture.with_suffix('.rejection.json').name))
 for row in records:
  n=3 if row['type']=='original-script-relative-geometry'else 2
  original=Counter(native_font_programs(source,n));final=Counter(native_font_programs(N/row['fixture'],1));assert all(final[k]>=v for k,v in original.items());row['all_original_font_programs_names_and_ToUnicode_preserved']=True
 result=dict(passed=True,source_sha256=sha(source),positive_page02_sha256=sha(positive),positive_page03_sha256=sha(positive3),all5_actual_bad_PDFs_rejected=True,controls=records,diagnostic_false_alarm_not_counted=True)
 save(N/'native-negative-control-manifest.json',result);print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

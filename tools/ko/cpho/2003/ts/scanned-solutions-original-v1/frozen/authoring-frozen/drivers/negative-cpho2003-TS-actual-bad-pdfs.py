"""Five real deliberately bad PDFs, independently rejected against source ink/face."""
from pathlib import Path
from io import BytesIO
from collections import Counter
import sys,json,hashlib,traceback
import pikepdf,pymupdf as f
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');T=B/'TS'
sys.path[:0]=[str(T/'engine'),str(B/'engine'),'D:/CodexBuilds']
from pdf_memory_gate import page_worker
from cpho_2003_ts_compose import add_erase_rects,restore_actual_source_group,write_words
from pdf_scanned_translation_ink_qa import audit_scan_page
from cpho2003_ts_actual_donor_style import audit as actual_style
from cpho2003_ts_native_ink import audit as actual_native
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import suppress_prose
SOURCE=B/'inputs/CPhO_2003_Chinese_original.pdf';OUT=T/'negative-controls-v1';OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,q):
 assert not p.exists();p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
def pixel(candidate,extra_prose=None,extra_rects=()):
 n=6;good=T/'proofs/ko/page06.pdf';c=json.loads(good.with_suffix('.composition.json').read_text('utf8'));q=json.loads((T/'authoring/page06-layout.json').read_text('utf8'))
 slots=json.loads((T/'inputs/native-slots.json').read_text('utf8'))['pages'][5]['slots']
 headers=[g['bbox']for s in slots for g in s['source_characters']]+[[r['left']-1,r['baseline']-r['size']*1.4,r['right']+1,r['baseline']+r['size']*.4]for r in c['header']['placements']]
 return audit_scan_page(SOURCE,n,candidate,good.with_suffix('.math-control.pdf'),extra_prose or good.with_suffix('.prose-only.pdf'),language_erase_rects=[v for r in q['rows']for v in r['erase_rects']],new_prose_rects=[[r['left']-1,r['baseline']-r['size']*1.3,r['right']+1,r['baseline']+r['size']*.4]for r in c['body_placements']]+list(extra_rects),original_inline_math_rects=[a['rect']for r in q['rows']for a in r['atoms']],moved_inline_math_rects=[a['destination_rect']for a in c['inline_math_replay']['atoms']],protected_source_rects=q['protected_source_display_and_figure_rects'],native_header_change_rects=headers,replayed_math_records=c['inline_math_replay']['atoms'],reviewed_blank_records=q['reviewed_blank_background_rects'])
def point_mutant(good,bad):
 with pikepdf.open(good)as d:
  changed=False
  for stream in d.pages[0].Contents:
   ops=list(pikepdf.parse_content_stream(stream));mut=[]
   for ins in ops:
    if not changed and str(ins.operator)=='Tf'and str(ins.operands[0]).startswith('/TSScanBody'):
     assert abs(float(ins.operands[1])-10.5)<.001
     ins=pikepdf.ContentStreamInstruction([ins.operands[0],11.5],ins.operator);changed=True
    mut.append(ins)
   if changed:
    stream.write(pikepdf.unparse_content_stream(mut));break
  assert changed;d.save(bad,compress_streams=False)
def outline_mutant(good,bad):
 with pikepdf.open(good)as d:
  font=d.pages[0].Resources.Font['/TSScanBody'];face=font.DescendantFonts[0];program=face.FontDescriptor.FontFile2
  ft=TTFont(BytesIO(program.read_bytes()),recalcTimestamp=False);name=ft.getBestCmap()[ord('이')];gs=ft.getGlyphSet();pen=TTGlyphPen(gs);gs[name].draw(TransformPen(pen,(1,0,0,1,0,90)));ft['glyf'][name]=pen.glyph();b=BytesIO();ft.save(b);ft.close();program.write(b.getvalue());program.Length1=len(b.getvalue());d.save(bad,compress_streams=False)
def inject(good,bad):
 c=json.loads((T/'proofs/ko/page06.composition.json').read_text('utf8'));raw=Path(c['body_fonts']['SimSun']['subset']).read_bytes();metric=f.Font(fontbuffer=raw)
 with f.open(good)as d:
  p=d[0];p.insert_font(fontname='TSScanBody',fontbuffer=raw);write_words(p,140,152,'회전',metric,10.5,'TSScanBody');d.save(bad,garbage=0,deflate=False)
 restore_actual_source_group(bad,6)
def script_loss(good,bad):
 c=json.loads(good.with_suffix('.composition.json').read_text('utf8'));groups=[r for r in c['header']['native_shifts']if Counter(g['c']for g in r['glyphs'])==Counter('m2=4m0')];assert len(groups)==1
 group=groups[0];g=next(g for g in group['glyphs']if g['c']=='0');assert g['c']=='0'and abs(g['size']-7.009312629699707)<.001
 with f.open(good)as d:
  found=[a for a in _traces(d[0])if a['c']=='0'and a['font']==g['font']and abs(a['size']-g['size'])<.001 and abs(a['origin'][0]-g['origin'][0]-group['dx'])<.001 and abs(a['origin'][1]-g['origin'][1])<.001]
 assert len(found)==1
 # Deliberately malformed fixture only: direct source Form edit. The production
 # suppressor correctly forbids selecting preserved Form glyphs and is unchanged.
 with pikepdf.open(good)as d:
  form=d.pages[0].Resources.XObject['/Meta80'];ops=list(pikepdf.parse_content_stream(form));assert len(ops)==27
  matches=[i for i,v in enumerate(ops)if str(v.operator)=='TJ'and len(v.operands[0])==1 and bytes(v.operands[0][0])==b'20'];assert len(matches)==1
  i=matches[0];before=hashlib.sha256(form.read_bytes()).hexdigest();ops[i]=pikepdf.ContentStreamInstruction([pikepdf.Array([pikepdf.String(b'2')])],ops[i].operator);form.write(pikepdf.unparse_content_stream(ops));after=hashlib.sha256(form.read_bytes()).hexdigest();d.save(bad,compress_streams=False)
 with f.open(good)as aa,f.open(bad)as bb:
  from pdf_original_text_ops import glyph_key
  old=Counter(glyph_key(v)for v in _traces(aa[0])if v['c'].strip());new=Counter(glyph_key(v)for v in _traces(bb[0])if v['c'].strip());assert old-new==Counter({glyph_key(found[0]):1})and not(new-old)
 return dict(original_source_script=g,actual_removed_script=found[0],removed_actual_source_glyphs=1,actual_original_Form_before_sha256=before,deliberately_bad_Form_after_sha256=after,production_native_form_guard_unchanged=True)
cases=[('missing-stationary-original-equation',6),('new-prose-over-original-math',6),('wrong-new-prose-point',6),('wrong-new-prose-outline',6),('missing-original-native-subscript',10)]
records=[]
for name,n in cases:
 with page_worker():
  good=T/f'proofs/ko/page{n:02}.pdf';bad=OUT/(name+'.pdf');receipt=OUT/(name+'.json');detail={}
  if receipt.exists():
   q=json.loads(receipt.read_text('utf8'));assert q['rejected_as_expected']and q['candidate_sha256']==sha(bad)and q['positive_sha256']==sha(good);records.append(q);continue
  if not bad.exists():
   if name=='missing-stationary-original-equation':add_erase_rects(good,bad,[[129,136.5,337.5,163]])
   elif name=='new-prose-over-original-math':inject(good,bad)
   elif name=='wrong-new-prose-point':point_mutant(good,bad)
   elif name=='wrong-new-prose-outline':outline_mutant(good,bad)
   else:detail=script_loss(good,bad)
  assert sha(bad)!=sha(good)
  if name=='missing-stationary-original-equation':
   raw=pixel(bad);assert not raw['passed']and raw['independent_protected_source_ink_lost']['pixels']>0
   assert raw['original_encoded_image_programs_masks_palettes_icc_and_declared_ctms_retained']and not raw['original_native_font_program_changes']and raw['original_pagegroup_unchanged'];dump(OUT/(name+'.raw-source-qa.json'),raw);detail['protected_original_pixels_lost']=raw['independent_protected_source_ink_lost']['pixels']
  elif name=='new-prose-over-original-math':
   prose=OUT/(name+'.actual-prose-only.pdf')
   if not prose.exists():inject((T/'proofs/ko/page06.prose-only.pdf'),prose)
   raw=pixel(bad,prose,[[139,138,162,155]]);assert not raw['passed']and raw['new_prose_overlap_original_or_replayed_nonlanguage_ink']['pixels']>0;dump(OUT/(name+'.raw-source-qa.json'),raw);detail['actual_collision_pixels']=raw['new_prose_overlap_original_or_replayed_nonlanguage_ink']['pixels']
  else:
   error=None
   try:
    if name=='missing-original-native-subscript':actual_native(10,'ko',proof_override=bad,output_override=OUT/(name+'.raw-native-ink.json'))
    else:actual_style(6,'ko',proof_override=bad,output_override=OUT/(name+'.raw-actual-style.json'))
   except (AssertionError,ValueError)as exc:error=str(exc)
   assert error,('Actual bad PDF unexpectedly passed',name)
   expected='No unique measured original scan role/point/baseline'if name=='wrong-new-prose-point'else'Actual PDF glyph differs from full donor'if name=='wrong-new-prose-outline'else'native'
   assert expected.lower()in error.lower(),('Unexpected failure rather than intended actual negative',name,error)
   detail['actual_checker_error']=error
   if name=='missing-original-native-subscript':
    raw=json.loads((OUT/(name+'.raw-native-ink.json')).read_text('utf8'));assert not raw['passed']and len(raw['missing_final_native_glyphs'])==1 and raw['missing_final_native_glyphs'][0]['c']=='0'and raw['source_outline_audit']['passed']
    detail['actual_missing_final_native_glyphs']=raw['missing_final_native_glyphs'];detail['original_source_protected_glyphs']=raw['protected_native_glyphs'];detail['production_native_form_guard_sha256']=sha(B/'engine/pdf_native_inline_reposition.py');assert detail['production_native_form_guard_sha256']=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'

  q=dict(schema='cpho2003-ts-actual-bad-pdf-negative-v1',case=name,source_original_sha256=sha(SOURCE),source_page=n,language='ko',positive_sha256=sha(good),candidate_sha256=sha(bad),candidate_bytes=bad.stat().st_size,actual_pdf_mutation=True,not_a_metadata_only_mutation=True,rejected_as_expected=True,checker_sha256=sha(T/'engine/cpho2003_ts_native_ink.py')if n==10 else sha(T/'engine/cpho2003_ts_actual_donor_style.py')if 'wrong-new'in name else sha(T/'engine/pdf_scanned_translation_ink_qa.py'),detail=detail)
  dump(receipt,q);records.append(q);print('ACTUAL_BAD_PDF_REJECTED',name,detail,flush=True)
summary=OUT/'negative-control-results.json'
if not summary.exists():dump(summary,dict(schema='cpho2003-ts-five-actual-bad-pdf-controls-v1',all_five_actual_bad_pdfs_rejected=len(records)==5,source_original_sha256=sha(SOURCE),cases=records))

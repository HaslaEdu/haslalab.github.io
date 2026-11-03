from pathlib import Path
import sys,json,hashlib,contextlib,shutil,pikepdf,pymupdf as f
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2017-complete-solutions');F=B/'natural/2017/TS';O=B/'natural/2017-native-design-negatives';O.mkdir(exist_ok=True);sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'))
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import reposition_inline
from izho_2017_equation_counters import source_counters,audit as counter_audit
from izho_2017_original_formula_conjunction_order import audit as order_audit
import izho_natural_spacing_qa as qa
def save(p,q):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
rows=[]
with page_worker():
 plan=F/'plans/page06.json';positive=order_audit(plan);assert positive['passed'];old=next((F/'history').glob('rejected-06-058b5da800db0c75/page06.pdf'));out=O/'actual-previous-conjunction-after-both-expressions';out.mkdir();bad=out/'page06.pdf';shutil.copy2(old,bad);negative=order_audit(plan,final_override=bad,report_override=out/'actual-wrong-reading-order-rejected.json');assert not negative['passed'];rows.append(dict(id='actual-previous-conjunction-after-both-independent-expressions',page=6,proof_sha256=sha(F/'page06.pdf'),mutant_sha256=sha(bad),negative_rejected=True,delivered_proof_unmodified=True,all15_original_math_glyphs_and_source_fonts_points_still_present=True))
with page_worker():
 proof=F/'page04.pdf';pin=sha(proof);plan=load(F/'plans/page04.json');counter=source_counters(plan)[0];out=O/'actual-native-counter12pt-drift';out.mkdir();bad=out/proof.name;raw,motion=reposition_inline(proof,1,shifts=[dict(glyphs=counter['glyphs'],dx=-12.)]);bad.write_bytes(raw);q=counter_audit(F/'plans/page04.json',final_override=bad,report_override=out/'actual-counter-drift-rejected.json');assert not q['passed']and sha(proof)==pin;save(out/'actual-mutation-program.json',motion);rows.append(dict(id='actual-original-display-counter12pt-drift',page=4,proof_sha256=pin,mutant_sha256=sha(bad),negative_rejected=True,delivered_proof_unmodified=True))
for n,ident,rect in [(4,'actual-native-counter-covered-metadata-unchanged',None),(11,'actual-original-lambda-covered-metadata-unchanged',[111.8,736.,119.8,749.5]),(11,'actual-original-native-root-stroke-covered',[150.,735.,163.5,748.5])]:
 with page_worker():
  proof=F/f'page{n:02}.pdf';pin=sha(proof);out=O/ident/'2017/TS';(out/'plans').mkdir(parents=True);bad=out/proof.name;plan=load(F/f'plans/page{n:02}.json');composition=load(proof.with_suffix('.qa.json'))
  if rect is None:
   gs=source_counters(plan)[0]['glyphs'];rect=[min(g['bbox'][0]for g in gs)-.2,min(g['bbox'][1]for g in gs)-.2,max(g['bbox'][2]for g in gs)+.2,max(g['bbox'][3]for g in gs)+.2]
  with f.open(proof)as d:w,h=d[0].rect.width,d[0].rect.height
  overlay=out/'actual-white-ink-occlusion.pdf'
  with f.open()as d:p=d.new_page(width=w,height=h);p.draw_rect(f.Rect(rect),fill=(1,1,1),color=None,width=0);d.save(overlay)
  with pikepdf.open(proof)as d,pikepdf.open(overlay)as over:d.pages[0].add_overlay(over.pages[0]);d.save(bad,compress_streams=False)
  composition['output_sha256']=sha(bad);save(bad.with_suffix('.qa.json'),composition);save(out/f'plans/page{n:02}.json',plan);qa.BUILD=O/ident
  if n==4:assert counter_audit(F/'plans/page04.json',final_override=bad,report_override=out/'unchanged-original-counter-metadata.json')['passed']
  with (out/'actual-negative-audit.log').open('w',encoding='utf8')as log,contextlib.redirect_stdout(log):
   try:qa.audit(2017,'TS',n)
   except ValueError as exc:reason=str(exc)
   else:raise AssertionError('Actual original native math/counter ink damage was accepted')
  q=load(bad.with_suffix('.audit.json'));assert not q['passed']and sha(proof)==pin;missing=q['actual_native_math_visible_ink_audit']['missing_actual_native_pixels'];outline=q['original_input_outline_native_ink_audit']['newly_missing_native_ink_pixels'];assert missing>0 or outline>1
  row=dict(id=ident,page=n,proof_sha256=pin,mutant_sha256=sha(bad),actual_overlay_rect=rect,negative_rejected=True,delivered_proof_unmodified=True,missing_actual_native_pixels=missing,missing_original_outline_pixels=outline,rejection=reason);rows.append(row);save(out/'negative-control.json',row)
save(O/'negative-controls.json',dict(original_source_sha256=load(F/'plans/page11.json')['original_english_source_sha256'],rows=rows,all_actual_bad_PDFs_rejected=True,passed=len(rows)==5 and all(r['negative_rejected']and r['delivered_proof_unmodified']for r in rows)));print('SOURCE2017_ACTUAL_NATIVE_MATH_COUNTER_AND_READING_ORDER_NEGATIVES_REJECTED',len(rows),flush=True)

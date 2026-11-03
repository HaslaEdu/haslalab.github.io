from pathlib import Path
import sys,json,hashlib,contextlib,math
import pikepdf,pymupdf as f
from PIL import Image
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2013-complete-solutions');F=B/'natural/2013/TS';O=B/'natural/2013-native-design-negatives';O.mkdir(exist_ok=True);sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'))
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import reposition_inline
from izho_2013_equation_counters import source_counters,audit as counter_audit
import izho_natural_spacing_qa as qa
def save(p,q):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
rows=[]
with page_worker():
 proof=F/'page04.pdf';pin=sha(proof);plan=load(F/'plans/page04.json');counter=source_counters(plan)[0];folder=O/'actual-counter-drift';folder.mkdir(exist_ok=True);bad=folder/proof.name;assert not bad.exists()
 raw,motion=reposition_inline(proof,1,shifts=[dict(glyphs=counter['glyphs'],dx=-12.)]);bad.write_bytes(raw);q=counter_audit(F/'plans/page04.json',final_override=bad,report_override=folder/'actual-counter12pt-drift-rejected.json');assert not q['passed']and sha(proof)==pin;save(folder/'actual-native-counter-mutation.json',motion)
 rows.append(dict(id='actual-original-counter12pt-drift',page=4,proof_sha256=pin,mutant_sha256=sha(bad),negative_rejected=True,delivered_proof_unmodified=True,original_native_font_GID_point_and_Y_retained=True))
for n,ident in[(4,'actual-original-counter-covered-metadata-unchanged'),(2,'actual-original-math-bitmap-covered-beyond-English-descender-reference')]:
 with page_worker():
  proof=F/f'page{n:02}.pdf';pin=sha(proof);folder=O/ident/'2013/TS';(folder/'plans').mkdir(parents=True,exist_ok=True);bad=folder/proof.name;assert not bad.exists();plan=load(F/f'plans/page{n:02}.json');composition=load(proof.with_suffix('.qa.json'))
  if n==4:
   glyphs=source_counters(plan)[0]['glyphs'];rect=[min(g['bbox'][0]for g in glyphs)-.2,min(g['bbox'][1]for g in glyphs)-.2,max(g['bbox'][2]for g in glyphs)+.2,max(g['bbox'][3]for g in glyphs)+.2]
  else:
   figure=plan['reviewed_original_prose_bitmap_overlap_references'][0]['rect'];rect=None
   with Image.open(F/'qa-renders/02-new.png')as image:
    image=image.convert('RGB')
    for y in range(math.ceil((figure[1]+4)*4),math.floor((figure[3]-3)*4)):
     for x in range(math.ceil((figure[0]+2)*4),math.floor((figure[2]-2)*4)):
      if min(image.getpixel((x,y)))<80:rect=[x/4-.1,y/4-.1,x/4+.9,y/4+.9];break
     if rect:break
   assert rect
  with f.open(proof)as doc:w,h=doc[0].rect.width,doc[0].rect.height
  overlay=folder/'actual-negative-white-overlay.pdf'
  with f.open()as doc:p=doc.new_page(width=w,height=h);p.draw_rect(f.Rect(rect),fill=(1,1,1),color=None,width=0);doc.save(overlay)
  with pikepdf.open(proof)as doc,pikepdf.open(overlay)as over:doc.pages[0].add_overlay(over.pages[0]);doc.save(bad,compress_streams=False)
  composition['output_sha256']=sha(bad);save(bad.with_suffix('.qa.json'),composition);save(folder/f'plans/page{n:02}.json',plan);qa.BUILD=O/ident
  if n==4:assert counter_audit(F/'plans/page04.json',final_override=bad,report_override=folder/'native-counter-font-metadata-still-exact.json')['passed']
  with(folder/'actual-negative-audit.log').open('w',encoding='utf8')as log,contextlib.redirect_stdout(log):
   try:qa.audit(2013,'TS',n)
   except ValueError as exc:reason=str(exc)
   else:raise AssertionError('Actual original native counter/bitmap damage was accepted')
  q=load(bad.with_suffix('.audit.json'));assert not q['passed']and sha(proof)==pin;figures=sum(r['changed_pixels']for r in q['figure_pixel_audits']);missing=q['actual_native_math_visible_ink_audit']['missing_actual_native_pixels'];outline=q['original_input_outline_native_ink_audit']['newly_missing_native_ink_pixels']
  if n==2:assert figures>0
  else:assert missing>0 or outline>0
  row=dict(id=ident,page=n,proof_sha256=pin,mutant_sha256=sha(bad),actual_overlay_rect=rect,negative_rejected=True,delivered_proof_unmodified=True,changed_original_figure_pixels=figures,missing_actual_native_pixels=missing,missing_original_outline_pixels=outline,rejection=reason);rows.append(row);save(folder/'negative-control.json',row)
save(O/'negative-controls.json',dict(original_source_sha256='2804ded48ad009bf58884b871f0f4817c64762b8a0f586e42056908fc4be10f1',rows=rows,all_actual_bad_PDFs_rejected=True,passed=all(r['negative_rejected']and r['delivered_proof_unmodified']for r in rows)))
print('ACTUAL_IZHO2013_COUNTER_DRIFT_OCCLUSION_AND_BITMAP_DAMAGE_ALL_REJECTED',len(rows),flush=True)

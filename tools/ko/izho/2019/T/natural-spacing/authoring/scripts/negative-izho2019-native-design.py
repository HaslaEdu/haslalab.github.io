from pathlib import Path
import sys,json,hashlib,shutil
import pymupdf as f,pikepdf
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2019-theory-original');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
import izho_natural_spacing_qa as qa
from pdf_memory_gate import page_worker
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
root=B/'natural/2019-native-design-negatives';base=B/'natural/2019/T';reports=[]
with page_worker():
 for n,ident,rect in[(2,'unrelated-chart-ink',[120.,330.,121.,331.]),(8,'missing-original-derivative-fraction-rule',[231.,153.05,249.,153.8])]:
  folder=root/ident/'2019/T';(folder/'plans').mkdir(parents=True,exist_ok=True);proof=base/f'page{n:02}.pdf';digest=sha(proof);target=folder/proof.name
  for suffix in['.qa.json']:
   shutil.copy2(proof.with_suffix(suffix),target.with_suffix(suffix))
  shutil.copy2(base/f'plans/page{n:02}.json',folder/f'plans/page{n:02}.json')
  with f.open(proof)as doc:w,h=doc[0].rect.width,doc[0].rect.height
  overlay=folder/'actual-negative-overlay.pdf'
  with f.open()as doc:
   p=doc.new_page(width=w,height=h);p.draw_rect(f.Rect(rect),fill=(0,0,0)if n==2 else(1,1,1),color=None,width=0);doc.save(overlay)
  with pikepdf.open(proof)as doc,pikepdf.open(overlay)as over:doc.pages[0].add_overlay(over.pages[0]);doc.save(target,compress_streams=False)
  # A mutant's identity is declared honestly so independent content checks,
  # rather than the separate immutable-proof SHA guard, must reject it.
  composition=json.loads(target.with_suffix('.qa.json').read_text('utf8'));composition['output_sha256']=sha(target)
  target.with_suffix('.qa.json').write_text(json.dumps(composition,ensure_ascii=False,indent=2)+'\n','utf8')
  if proof.with_suffix('.language-overlay.json').exists():shutil.copy2(proof.with_suffix('.language-overlay.json'),target.with_suffix('.language-overlay.json'))
  qa.BUILD=root/ident
  try:qa.audit(2019,'T',n)
  except ValueError as e:reason=str(e)
  else:raise AssertionError('Actual native-design damage was accepted')
  q=json.loads(target.with_suffix('.audit.json').read_text('utf8'));assert not q['passed'];assert sha(proof)==digest
  graphic=q['native_graphics_motion_audit'];r=dict(id=ident,page=n,proof_sha256=digest,mutant_sha256=sha(target),actual_overlay_rect=rect,delivered_proof_unmodified=True,negative_rejected=True,rejection=reason,changed_nonselected_native_graphical_pixels=graphic['changed_nonselected_native_graphical_pixels'],changed_actual_inline_math_graphical_pixels=graphic['changed_actual_inline_math_graphical_pixels'],changed_pixels_outside_old_and_new_text_ink=q['changed_pixels_outside_old_and_new_text_ink'],figure_changed_pixels=sum(v['changed_pixels']for v in q['figure_pixel_audits']),passed=True)
  (folder/'negative-control.json').write_text(json.dumps(r,indent=2)+'\n','utf8');reports.append(r);print('ACTUAL_SOURCE_DESIGN_DAMAGE_REJECTED',ident,r['changed_nonselected_native_graphical_pixels'],r['changed_actual_inline_math_graphical_pixels'],flush=True)
 (root/'negative-controls.json').write_text(json.dumps(dict(source_sha256='29daec0cb9f759bed9b755cbae2937e1c4ab068fa804c62d512ea291e42619d1',rows=reports,passed=True),indent=2)+'\n','utf8')

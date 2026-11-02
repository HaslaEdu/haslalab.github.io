from pathlib import Path
import sys,json,hashlib,shutil
import pymupdf as f,pikepdf
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
import izho_natural_spacing_qa as qa
from pdf_memory_gate import page_worker
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();base=B/'natural/2011/TS';root=B/'natural/2011-native-design-negatives';reports=[]
with page_worker():
 for n,ident in[(9,'unrelated-original-plot-ink'),(10,'covered-original-native-caption-counter')]:
  folder=root/ident/'2011/TS';(folder/'plans').mkdir(parents=True,exist_ok=True);proof=base/f'page{n:02}.pdf';digest=sha(proof);target=folder/proof.name;source_audit=json.loads(proof.with_suffix('.audit.json').read_text('utf8'));assert source_audit['passed']and source_audit['output_sha256']==digest
  if n==9:rect=[380.,200.,381.,201.]
  else:
   row=source_audit['reviewed_native_figure_language_labels']['labels'][0]['original_native_caption_counter'];assert row['source_font_gid_point_y_and_paint_preserved'];rect=row['original']['bbox'][:];rect=[rect[0]+row['dx'],rect[1],rect[2]+row['dx'],rect[3]]
  shutil.copy2(proof.with_suffix('.qa.json'),target.with_suffix('.qa.json'));shutil.copy2(base/f'plans/page{n:02}.json',folder/f'plans/page{n:02}.json')
  with f.open(proof)as doc:w,h=doc[0].rect.width,doc[0].rect.height
  overlay=folder/'actual-negative-overlay.pdf'
  with f.open()as doc:p=doc.new_page(width=w,height=h);p.draw_rect(f.Rect(rect),fill=(0,0,0)if n==9 else(1,1,1),color=None,width=0);doc.save(overlay)
  with pikepdf.open(proof)as doc,pikepdf.open(overlay)as over:doc.pages[0].add_overlay(over.pages[0]);doc.save(target,compress_streams=False)
  composition=json.loads(target.with_suffix('.qa.json').read_text('utf8'));composition['output_sha256']=sha(target);target.with_suffix('.qa.json').write_text(json.dumps(composition,ensure_ascii=False,indent=2)+'\n','utf8');qa.BUILD=root/ident
  try:qa.audit(2011,'TS',n)
  except ValueError as e:reason=str(e)
  else:raise AssertionError('Actual original plot/counter damage accepted')
  q=json.loads(target.with_suffix('.audit.json').read_text('utf8'));assert not q['passed']and sha(proof)==digest
  r=dict(id=ident,page=n,proof_sha256=digest,mutant_sha256=sha(target),actual_overlay_rect=rect,delivered_proof_unmodified=True,negative_rejected=True,rejection=reason,changed_nonselected_native_graphical_pixels=q['native_graphics_motion_audit']['changed_nonselected_native_graphical_pixels'],missing_source_native_outline_pixels=q['original_input_outline_native_ink_audit']['newly_missing_native_ink_pixels'],missing_native_control_ink_pixels=q['actual_native_math_visible_ink_audit']['missing_actual_native_pixels'],figure_changed_pixels=sum(v['changed_pixels']for v in q['figure_pixel_audits']),source_native_caption_counter_metadata_still_exact=True,passed=True)
  if n==9:assert r['figure_changed_pixels']>0
  else:assert r['missing_source_native_outline_pixels']>0 or r['missing_native_control_ink_pixels']>0
  (folder/'negative-control.json').write_text(json.dumps(r,indent=2)+'\n','utf8');reports.append(r);print('ACTUAL_ORIGINAL_PLOT_OR_NATIVE_COUNTER_DAMAGE_REJECTED',ident,r['figure_changed_pixels'],r['missing_source_native_outline_pixels'],r['missing_native_control_ink_pixels'],flush=True)
 (root/'negative-controls.json').write_text(json.dumps(dict(source_sha256='ecc4a34a50fade6a08fd5f629480bebfa20ec418cdc19fa87915f6c0465ee008',rows=reports,passed=True),indent=2)+'\n','utf8')

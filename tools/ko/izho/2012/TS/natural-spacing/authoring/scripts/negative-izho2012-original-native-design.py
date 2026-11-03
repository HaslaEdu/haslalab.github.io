from pathlib import Path
import sys,json,hashlib,shutil,contextlib
import pikepdf,pymupdf as f
from PIL import Image
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions');F=B/'natural/2012/TS';O=B/'natural/2012-native-design-negatives';O.mkdir(exist_ok=True);sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'))
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import reposition_inline,_raw_regions
from izho_2012_equation_counters import source_counters,audit as counter_audit
from izho_2012_complete_inline_fractions import audit as fraction_audit
import izho_natural_spacing_qa as qa
rows=[]
def save(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
with page_worker():
 proof=F/'page06.pdf';pin=sha(proof);d=load(F/'plans/page06.json');tag=source_counters(d)[0];folder=O/'actual-counter-drift';folder.mkdir(exist_ok=True);bad=folder/proof.name
 raw,motion=reposition_inline(proof,1,shifts=[dict(glyphs=tag['glyphs'],dx=-12.)]);bad.write_bytes(raw);result=counter_audit(F/'plans/page06.json',final_override=bad,report_override=folder/'actual-counter-drift-rejected.json');assert not result['passed']and sha(proof)==pin
 save(folder/'native-counter-mutation.json',motion);rows.append(dict(id='actual-original-counter12pt-drift',page=6,proof_sha256=pin,mutant_sha256=sha(bad),negative_rejected=True,delivered_proof_unmodified=True,native_font_GIDs_point_sizes_and_paint_retained=True,rejection='Independent actual source x/y equation-label audit rejected moved equation1.'))
 proof=F/'page01.pdf';pin=sha(proof);folder=O/'actual-fraction-rule-only-motion';folder.mkdir(exist_ok=True);bad=folder/proof.name;positive=load(proof.with_suffix('.inline-fractions.json'));path=positive['groups'][0]['original_fraction_rules'][0]['actual_matching_painted_paths'][0]
 with pikepdf.open(proof)as pdf:
  content,regions=_raw_regions(pdf.pages[0]);a=regions[min(path['operator_indices'])][0];z=regions[max(path['operator_indices'])][1];pdf.pages[0].Contents=pdf.make_stream(content[:a]+b'\nq 1 0 0 1 20 0 cm\n'+content[a:z]+b'\nQ\n'+content[z:]);pdf.save(bad,compress_streams=False)
 composition=load(proof.with_suffix('.qa.json'));composition['output_sha256']=sha(bad);result=fraction_audit(F/'plans/page01.json',final_override=bad,composition_override=composition,report_override=folder/'actual-fraction-rule-only-motion-rejected.json');assert not result['passed']and all(r['source_native_font_gid_point_y_and_actual_dx_matched']for r in result['groups'])and sha(proof)==pin
 rows.append(dict(id='actual-fraction-rule-motion-with-all7-native-glyphs-unchanged',page=1,proof_sha256=pin,mutant_sha256=sha(bad),negative_rejected=True,delivered_proof_unmodified=True,all_original_native_fraction_glyphs_still_exact=True,rejection='Actual final painted fraction-rule endpoints no longer share the unchanged native expression dx.'))
for n,ident in[(3,'actual-nonlanguage-plot-damage'),(6,'actual-original-counter-covered-with-font-metadata-unchanged')]:
 with page_worker():
  proof=F/f'page{n:02}.pdf';pin=sha(proof);folder=O/ident/'2012/TS';(folder/'plans').mkdir(parents=True,exist_ok=True);bad=folder/proof.name;plan=load(F/f'plans/page{n:02}.json');composition=load(proof.with_suffix('.qa.json'))
  if n==3:
   figure=plan['excluded_figure_rects'][0];rect=None
   with Image.open(F/f'qa-renders/{n:02}-new.png')as image:
    image=image.convert('RGB')
    for y in range(int(figure[1])+5,int(figure[3])-5,3):
     for x in range(int(figure[0])+5,int(figure[2])-5,3):
      if image.crop((x*4,y*4,(x+1)*4,(y+1)*4)).getextrema()==((255,255),(255,255),(255,255)):rect=[x,y,x+1,y+1];break
     if rect:break
   assert rect
  else:
   glyphs=source_counters(plan)[0]['glyphs'];rect=[min(g['bbox'][0]for g in glyphs)-.2,min(g['bbox'][1]for g in glyphs)-.2,max(g['bbox'][2]for g in glyphs)+.2,max(g['bbox'][3]for g in glyphs)+.2]
  with f.open(proof)as doc:w,h=doc[0].rect.width,doc[0].rect.height
  overlay=folder/'actual-negative-overlay.pdf'
  with f.open()as doc:p=doc.new_page(width=w,height=h);p.draw_rect(f.Rect(rect),fill=(0,0,0)if n==3 else(1,1,1),color=None,width=0);doc.save(overlay)
  with pikepdf.open(proof)as doc,pikepdf.open(overlay)as over:doc.pages[0].add_overlay(over.pages[0]);doc.save(bad,compress_streams=False)
  composition['output_sha256']=sha(bad);save(bad.with_suffix('.qa.json'),composition);save(folder/f'plans/page{n:02}.json',plan);qa.BUILD=O/ident
  if n==6:assert counter_audit(F/'plans/page06.json',final_override=bad,report_override=folder/'native-counter-metadata-still-exact.json')['passed']
  with(folder/'actual-negative-audit.log').open('w',encoding='utf8')as log,contextlib.redirect_stdout(log):
   try:qa.audit(2012,'TS',n)
   except ValueError as exc:reason=str(exc)
   else:raise AssertionError('Actual nonlanguage plot/native-counter damage was accepted')
  result=load(bad.with_suffix('.audit.json'));assert not result['passed']and sha(proof)==pin
  figures=sum(r['changed_pixels']for r in result['figure_pixel_audits']);missing=result['actual_native_math_visible_ink_audit']['missing_actual_native_pixels']
  if n==3:assert figures>0
  else:assert missing>0 or result['original_input_outline_native_ink_audit']['newly_missing_native_ink_pixels']>0
  row=dict(id=ident,page=n,proof_sha256=pin,mutant_sha256=sha(bad),actual_overlay_rect=rect,negative_rejected=True,delivered_proof_unmodified=True,changed_figure_pixels=figures,missing_actual_native_ink_pixels=missing,rejection=reason);rows.append(row);save(folder/'negative-control.json',row)
save(O/'negative-controls.json',dict(original_source_sha256='41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db',rows=rows,all_actual_bad_PDFs_rejected=True,passed=all(r['negative_rejected']and r['delivered_proof_unmodified']for r in rows)))
print('ACTUAL_IZHO2012_FRACTION_COUNTER_PLOT_AND_OCCLUSION_BAD_PDFS_ALL_REJECTED',len(rows),flush=True)

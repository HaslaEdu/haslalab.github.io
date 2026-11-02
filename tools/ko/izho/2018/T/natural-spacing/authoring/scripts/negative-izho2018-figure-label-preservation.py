from pathlib import Path
import sys,json,hashlib
import pymupdf as f,pikepdf,numpy as np
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from initial_bitmap_language_labels import masks
from izho_natural_spacing_qa import fresh_render
from pdf_memory_gate import page_worker
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
with page_worker():
 folder=B/'natural/2018/T';out=folder/'negative-figure-labels';out.mkdir(exist_ok=True);target=folder/'page06.pdf';original_sha=sha(target);plan=json.loads((folder/'plans/page06.json').read_text('utf8'))
 source=fresh_render(plan['original_english_source'],6,out/'source.png');final=fresh_render(target,1,out/'final.png');old,new,q=masks(plan,target,source,4)
 region=np.zeros(source.shape[:2],bool);region[620:1110,1500:2211]=True
 delta=lambda rgb:int((np.any(source!=rgb,axis=2)&region&~(old|new)).sum())
 assert delta(final)==0
 over=f.open();p=over.new_page(width=595.32,height=841.92);p.draw_rect(f.Rect(379,160,380,161),fill=(0,0,0),color=None,width=0);op=out/'extra-rectangle-overlay.pdf';over.save(op);over.close()
 bad=out/'negative-original-picture-altered.pdf'
 with pikepdf.open(target)as d,pikepdf.open(op)as o:d.pages[0].add_overlay(o.pages[0]);d.save(bad,compress_streams=False)
 changed=delta(fresh_render(bad,1,out/'negative.png'));assert changed>0
 assert sha(target)==original_sha
 report=dict(source_sha256=plan['original_english_source_sha256'],proof_sha256=original_sha,positive_nonlanguage_figure_changed_pixels=0,negative_nonlanguage_figure_changed_pixels=changed,negative_rejected=True,mutant_sha256=sha(bad),actual_source_language_and_actual_new_glyph_ink_only=True,delivered_proof_unmodified=True,passed=True)
 (out/'negative-control.json').write_text(json.dumps(report,indent=2)+'\n','utf8');print('ACTUAL_UNRELATED_FIGURE_RECTANGLE_NEGATIVE_REJECTED',changed,flush=True)

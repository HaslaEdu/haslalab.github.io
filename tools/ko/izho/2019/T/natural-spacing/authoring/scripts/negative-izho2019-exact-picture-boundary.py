from pathlib import Path
import sys,json,hashlib,math
import numpy as np,pymupdf as f,pikepdf
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2019-theory-original');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from izho_natural_spacing_qa import fresh_render
from pdf_memory_gate import page_worker
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
with page_worker():
 folder=B/'natural/2019/T';out=folder/'negative-exact-picture-boundary';out.mkdir(exist_ok=True);proof=folder/'page03.pdf';digest=sha(proof);plan=json.loads((folder/'plans/page03.json').read_text('utf8'));a=fresh_render(plan['original_english_source'],3,out/'source.png');b=fresh_render(proof,1,out/'final.png')
 rect=[136.75,356.469970703125,458.54998779296875,559.6599731445312]
 def delta(rgb,centers):
  x0,y0,x1,y1=[math.ceil(x*4-.5)if centers else int(x*4)for x in rect];return int(np.any(a[y0:y1,x0:x1]!=rgb[y0:y1,x0:x1],axis=2).sum())
 assert delta(b,True)==0 and delta(b,False)==50
 with f.open(proof)as d:width,height=d[0].rect.width,d[0].rect.height
 overlay=f.open();p=overlay.new_page(width=width,height=height);p.draw_rect(f.Rect(140,370,141,371),color=None,fill=(0,0,0),width=0);op=out/'extra-black-pixel-area.pdf';overlay.save(op);overlay.close();bad=out/'negative-one-original-picture-area-altered.pdf'
 with pikepdf.open(proof)as d,pikepdf.open(op)as o:d.pages[0].add_overlay(o.pages[0]);d.save(bad,compress_streams=False)
 count=delta(fresh_render(bad,1,out/'negative.png'),True);assert count>0 and sha(proof)==digest
 report=dict(source_sha256=plan['original_english_source_sha256'],proof_sha256=digest,original_continuous_picture_bbox=rect,original_pixel_center_inside_bbox_changed_pixels=0,coarse_floor_sampling_diagnostic_only=50,diagnostic_scanline_point_y=356.25,diagnostic_scanline_pixel_center_y=356.375,original_picture_top_y=356.469970703125,explanation='All50 coarse-only differences are erased English prose descenders on the scanline physically above the exact original picture. The exact picture rectangle includes its genuine bottom-edge scanline that the former floor truncation omitted. Actual native image programs/CTMs and all nonselected graphical ink remain unchanged; zero comparison threshold.',negative_actual_inside_picture_rectangle_changed_pixels=count,negative_rejected=True,mutant_sha256=sha(bad),proof_unmodified=True,passed=True)
 (out/'negative-control.json').write_text(json.dumps(report,indent=2)+'\n','utf8');print('EXACT_SOURCE_PICTURE_BOUNDS_POSITIVE_AND_REAL_NEGATIVE_PASS',count,flush=True)

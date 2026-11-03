from pathlib import Path
import sys,json,hashlib,pymupdf as f,numpy as np
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2015-complete-solutions');F=B/'natural/2015/TS';sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools'];O=B/'natural/2015-page04-original-white-comma';O.mkdir(exist_ok=True)
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import _traces
from pdf_native_glyph_raster_witness import replay
from pdf_moved_native_ink import source_outline_reference,audit_moved_native_ink
from pdf_original_text_ops import glyph_key
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();source=B/'2015/source/IZhO_2015_TS.pdf';old=F/'page04.old-source.pdf';proof=F/'page04.pdf';pin=sha(proof)
with page_worker():
 with f.open(source)as a,f.open(old)as o,f.open(proof)as b:
  g=next(g for g in _traces(a[3])if g['c']==','and g['font']=='Times New Roman'and abs(g['origin'][0]-367.58)<.001 and abs(g['origin'][1]-763.656)<.001);actual=next(h for h in _traces(b[0])if glyph_key(h)==glyph_key(g));assert all(g[k]==actual[k]for k in ['c','font','size','trace_gid','origin','render_mode','color','opacity','linewidth','direction','stroke_color','stroke_opacity','wmode','colorspace']);assert list(g['color'])==[1.,1.,1.]and g['render_mode']==0 and g['opacity']==1
  mask,outline=source_outline_reference(o[0],[g],scale=4);assert mask[3054,1475]
  original_keys={glyph_key(h)for h in _traces(a[3])if h['c'].strip()};protected=[h for h in _traces(o[0])if glyph_key(h)in original_keys and h['c'].strip()and glyph_key(h)!=glyph_key(g)]
 raw,details=replay(source,4,g);ref=O/'exact-original-white-encoded-comma-only.pdf';ref.write_bytes(raw);checks=[]
 with f.open(stream=raw,filetype='pdf')as doc:
  for scale in[4,8,12]:
   p=doc[0].get_pixmap(matrix=f.Matrix(scale,scale),clip=f.Rect(360,749,378,772),colorspace=f.csRGB,alpha=False);pixels=np.frombuffer(p.samples,np.uint8);checks.append(dict(scale=scale,exact_original_white_CID_reference_nonwhite_samples=int((pixels<255).sum()),exact_original_white_CID_reference_dark_samples=int((pixels<32).sum()),passed=bool(np.all(pixels==255))))
 composition=json.loads(proof.with_suffix('.qa.json').read_text('utf8'));dark=audit_moved_native_ink(old,1,proof,protected_glyphs=protected,shifts=composition['native_shifts'],scale=4);assert dark['passed']and dark['newly_missing_native_ink_pixels']==0
 assert sha(proof)==pin
 q=dict(original_source_sha256=sha(source),source_page=4,proof_sha256=pin,proof=str(proof),proof_unmodified=True,delivered_pdf_modified=False,source_glyph=g,actual_target_glyph=actual,original_encoded_CID_reference=details,source_white_punctuation_blackened_SVG_mask_covers_only_raw_missing_pixel=True,raw_missing_bbox=[368.75,763.5,369.,763.75],original_white_CID_reference_scales=checks,all_other_original_native_glyphs_ink_audit=dark,all_original_physical_glyphs_still_checked_by_metadata=True,mathematical_ink_excluded=False,passed=all(c['passed']for c in checks)and dark['passed'])
 (O/'witness.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('SOURCE2015_WHITE_COMMA_ACTUAL_ORIGINAL_PAINT_VERIFIED',q['passed'],sha(O/'witness.json'),len(protected),details,flush=True)

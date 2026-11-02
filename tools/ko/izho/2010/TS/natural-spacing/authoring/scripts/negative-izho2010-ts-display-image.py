from pathlib import Path
import sys,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from reviewed_native_math_images import audit
from pdf_native_inline_reposition import inspect_inline_groups,reposition_inline
plan=B/'natural/2010/TS/plans/page09.json';source=plan.parents[1]/'page09.pdf';folder=B/'2010/native-image-negative';folder.mkdir(exist_ok=True);target=folder/'page09-display-shift.pdf';report=folder/'page09-display-shift.audit.json'
image=inspect_inline_groups(source,1)['images'][1];raw,q=reposition_inline(source,1,erased_glyphs=[],shifts=[dict(glyphs=[],image_path=image['path'],dx=.5)]);assert q['passed'];target.write_bytes(raw)
r=audit(plan,target,report);assert not r['passed'];failed=[i for i in r['images']if not i['passed']];assert len(failed)==1 and failed[0]['source_image_index']==1 and failed[0]['source_raw_sha256']==failed[0]['final_raw_sha256'];assert failed[0]['errors']==['Display formula moved from original complete CTM']
summary=dict(passed=True,actual_final_pdf_clone_with_native_fonts_and_original_raw_images_retained=True,changed_display_source_image_index=1,unapproved_horizontal_motion_pt=.5,independent_display_geometry_rejected=True,report=str(report),native_move_qa=q)
(folder/'regression.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n','utf8');print('REAL_DISPLAY_IMAGE_MOTION_NEGATIVE_REJECTED',failed[0]['errors'])

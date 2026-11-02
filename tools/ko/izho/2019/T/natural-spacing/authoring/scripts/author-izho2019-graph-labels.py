from pathlib import Path
import json,hashlib,numpy as np
from PIL import Image
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2019-theory-original');P=B/'natural/2019/T/plans/page02.json';d=json.loads(P.read_text('utf8'));labels=[];a=np.asarray(Image.open(B/'2019/inspection/page02-raw-graph.png').convert('RGB'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for ident in['title','time','temperature']:
 path=B/f'2019/inspection/page02-label-{ident}-measurement.json';m=json.loads(path.read_text('utf8'))
 # The long title and independent vertical axis identify SegoeUI Bold clearly.
 # Keep that common chart family for the short horizontal axis, where several
 # faces give near-tied source-only raster fits. Never fit the Korean target.
 best=m['best_by_face']['SegoeUI-Bold'];assert best['iou']>.82 and m['source_only']and not m['target_translation_used_for_fitting']
 x0,y0,x1,y1=m['rect'];yy,xx=np.nonzero(np.any(a[y0:y1,x0:x1]!=255,axis=2));ink=[x0+int(xx.min()),y0+int(yy.min()),x0+int(xx.max())+1,y0+int(yy.max())+1]
 labels.append(dict(reviewed=True,source_sha256=d['original_english_source_sha256'],source_label=m['source_label'],text=m['text'],image_index=0,source_word_ink_rect_px=ink,source_background_sample_px=[20,20],source_background_rgb=[255,255,255],rotation=m['rotation'],measured_source_font_role='sans-bold',measured_source_font_face=best['face'],measured_source_size_pt=best['size'],measured_source_baseline_pt=best['baseline_coordinate_pt'],source_baseline_coordinate_axis=best['baseline_coordinate_axis'],source_measurement=dict(path=str(path),sha256=sha(path)),source_only_measurement=True,target_text_used_for_fitting=False,source_face_selection_reason='Independent long chart title and vertical axis select SegoeUI Bold; retain that shared source chart family for the near-tied short time label.'))
d['reviewed_bitmap_language_labels']=labels;P.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');print([(r['source_label'],r['measured_source_size_pt'],r['measured_source_baseline_pt'],r['rotation'])for r in labels])

from pathlib import Path
import json,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original');P=B/'natural/2018/T/plans/page06.json';d=json.loads(P.read_text('utf8'));labels=[]
for word in ['bottom','detector']:
 path=B/f'2018/inspection/page06-label-{word}-measurement.json';m=json.loads(path.read_text('utf8'));best=m['top20'][0]
 assert best['face']=='SegoeUI-Bold'and best['iou']>.84 and m['source_only']and not m['target_translation_used_for_fitting']
 labels.append(dict(reviewed=True,source_sha256=d['original_english_source_sha256'],source_label=m['source_label'],text=m['text'],image_index=1,source_word_ink_rect_px=m['rect'],source_background_sample_px=[10,350],source_background_rgb=[255,255,255],measured_source_font_role='sans-bold',measured_source_font_face=best['face'],measured_source_size_pt=best['size'],measured_source_baseline_pt=best['baseline'],source_measurement=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()),source_only_measurement=True,target_text_used_for_fitting=False))
labels[0]['source_word_ink_rect_px']=[53,322,157,349]
labels[0]['reviewed_source_JPEG_language_halo']='Include the original Bottom word compression halo at original image rows322-323 (RGB253/254). Its preceding horizontal physical boundary is above this isolated language rectangle and remains protected; font measurement stays based on the unchanged324-349 source glyph crop.'
d['reviewed_bitmap_language_labels']=labels;P.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');print('SOURCE_MEASURED_SANS_BOLD_FIGURE_LABELS',[(r['source_label'],r['measured_source_size_pt'],r['measured_source_baseline_pt'])for r in labels])

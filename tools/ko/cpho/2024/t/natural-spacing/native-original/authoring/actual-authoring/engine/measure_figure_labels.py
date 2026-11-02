"""Source-only font/point/baseline measurement for the31 isolated words."""
from pathlib import Path
import json,time,gc,sys
import pymupdf as fitz
import cpho2024_bitmap_fonts as measure
from cpho2024_figure_label_plan import LABELS
from cpho2024_natural import BASE
from pdf_memory_gate import page_worker

all_faces=list(measure.FONTS)
for label in LABELS:
 if len(sys.argv)>1 and label['id']not in sys.argv[1:]:continue
 group=json.loads((BASE/f"inspection/font-{label['source_font_measurement_group']}.json").read_text('utf8'));prior=group['top20'][0];rect=label['source_word_roi_px'];text=label['source_text'];rotation=label['rotation']
 if rotation=='stack':rect=[34,44,49,63];text=text[0];rotation=0
 if label.get('source_named_glyph_measurement'):rect=label['source_named_glyph_measurement']['rect'];text=label['source_named_glyph_measurement']['char']
 field=dict(id=label['id'],page=label['page'],image=label['image_index'],text=text,rect=rect,point_range=[round(prior['size']-.8,2),round(prior['size']+.8,2)],rotation=rotation)
 with page_worker():
  measure.FONTS=all_faces;report=measure.calibrate(field);best=report['top20'][0];same=report['best_by_face'][prior['face']]
  # Keep the source reference's family for marginal low-resolution ties.
  # A clear source-only outline match can identify a different original face.
  selected=best if best['iou']>=.6 and best['iou']-same['iou']>.05 else same
  report['selected_source_font']=selected;report['source_reference_prior']=prior;report['source_reference_family_tie_policy']='Use original image reference family unless another original-source font has IoU>=.60 and improves it by>.05; target translation strings are not consulted.'
  if label['rotation']=='stack':
   measure.FONTS=[(selected['face'],Path(selected['font_file']))];chars=[]
   for c,r in zip(label['source_text'],[[34,44,49,63],[34,63,49,80],[34,80,49,97],[34,98,49,113]]):
    char=measure.calibrate(dict(id=label['id']+'-'+c,page=label['page'],image=label['image_index'],text=c,rect=r,point_range=[selected['size'],selected['size']]))
    chars.append(dict(source_char=c,rect=r,source_font_measurement=char['top20'][0]))
   report['stacked_original_characters']=chars
  report['source_label_id']=label['id'];report['source_word_only_measurement']=True;report['original_font_metadata_available']=False;report['point_size_is_source_measurement_estimate']=True;report['target_strings_used_for_sizing']=False
  dest=BASE/f"authoring/T/figure-label-measurements/{label['id']}.json";dest.parent.mkdir(exist_ok=True);dest.write_text(json.dumps(report,ensure_ascii=False,indent=1)+'\n','utf8')
 print('SOURCE_WORD_FONT',label['id'],selected['face'],selected['size'],round(selected['iou'],3),flush=True);fitz.TOOLS.store_shrink(100);gc.collect();time.sleep(.6)

"""Closed source4 Chinese island-word overlays, with original images untouched."""
from pathlib import Path
from io import BytesIO
import json,hashlib
import pymupdf as f
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
B=Path(__file__).resolve().parents[1];S=B/'source/CPhO_2008_original_combined_ZH.pdf';SHA='4e076fb9234683d028792190bcec56f12de72890da6c0e44ddf0e9146013459d';ALIAS='C08BitmapLabelSerifBold'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def policy(plan):
 p=Path(plan['source_bitmap_language_policy_path']);assert sha(p)==plan['source_bitmap_language_policy_sha256'];q=json.loads(p.read_text('utf8'));m=Path(q['source_measurement_path']);assert sha(m)==q['source_measurement_sha256'];assert q['source_sha256']==SHA and q['source_page']==4 and sha(S)==SHA
 assert [r['source_word_ink_rect_px']for r in q['labels']]==[[284,80,434,117],[232,224,387,262]]
 assert [r['image_index']for r in q['labels']]==[0,1]
 assert all(r['source_label']=='单电子岛'and r['ko']=='단전자섬'and r['en']=='Island'and r['reviewed_isolated_original_language_only']and r['source_background_rgb']==[255]*3 for r in q['labels'])
 assert q['point_fitted_to_translation_or_box']is False
 assert [r['erase_rect_pt']for r in q['labels']]==[[193.,398.25,229.75,408.],[378.,423.25,415.75,433.]]
 return q
def text_outline(raw,text,point):
 with TTFont(BytesIO(raw))as tt:
  cmap=tt.getBestCmap();gs=tt.getGlyphSet();em=tt['head'].unitsPerEm;offset=0.;boxes=[];chars=[]
  for ch in text:
   name=cmap[ord(ch)];pen=BoundsPen(gs);gs[name].draw(pen);assert pen.bounds
   l,b,r,t=pen.bounds;boxes.append([offset+l*point/em,-t*point/em,offset+r*point/em,-b*point/em]);chars.append(dict(c=ch,gid=tt.getGlyphID(name),advance_pt=tt['hmtx'][name][0]*point/em,offset_x=offset));offset+=chars[-1]['advance_pt']
 return[min(v[0]for v in boxes),min(v[1]for v in boxes),max(v[2]for v in boxes),max(v[3]for v in boxes)],chars
def apply(plan,lang,body,target,font_builder,glyph_writer):
 q=policy(plan);donor=q['font_donors'][lang];assert sha(donor['path'])==donor['sha256'];text=q['labels'][0][lang];raw,metric,font_record=font_builder(Path(donor['path']),text);placements=[]
 with f.open(body)as doc:
  page=doc[0];page.insert_font(fontname=ALIAS,fontbuffer=raw)
  for row in q['labels']:
   point=row['source_only_measured_size_pt'];bounds,characters=text_outline(raw,row[lang],point);x=row['source_word_ink_center_x']-(bounds[0]+bounds[2])/2;y=row['source_only_measured_baseline_pt'];actual=[x+bounds[0],y+bounds[1],x+bounds[2],y+bounds[3]]
   # The point comes exclusively from source Chinese glyphs. No shrinking,
   # tracking, synthetic slant or horizontal text scaling is permitted.
   page.draw_rect(f.Rect(row['erase_rect_pt']),color=None,fill=(1,1,1),width=0)
   glyph_writer(page,x,y,row[lang],metric,point,ALIAS,(0,0,0))
   placements.append(dict(id=row['id'],text=row[lang],font_alias='/'+ALIAS,origin=[x,y],point=point,ink_rect=actual,source_word_ink_center_x=row['source_word_ink_center_x'],source_only_measured_baseline_pt=y,source_only_measured_size_pt=point,source_erase_rect=row['erase_rect_pt'],actual_expected_glyphs=characters,source_image_index=row['image_index'],point_fitted_to_translation_or_box=False))
  doc.save(target,garbage=0,deflate=False)
 return dict(source_sha256=SHA,source_page=4,source_policy_path=plan['source_bitmap_language_policy_path'],source_policy_sha256=plan['source_bitmap_language_policy_sha256'],actual_before_bitmap_language_body_path=str(body),actual_before_bitmap_language_body_sha256=sha(body),actual_final_sha256=sha(target),font=font_record,placements=placements,source_images_reencoded_or_replaced=False,source_math_or_nonlanguage_picture_redrawn=False,source_raster_font_metadata_claimed_exact=False)

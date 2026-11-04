"""Original native mathematical expressions in the hybrid final C03 TS page.

Every expression uses its original CID/font/point/paint/clip and one common dx.
Only the reviewed original prose is erased; the original math is never retyped.
"""
from pathlib import Path
import json,re
import pymupdf as fitz
from pdf_native_inline_reposition import reposition_inline
from pdf_original_text_ops import glyph_key

def control(number,lang,out):
 from cpho_2003_ts_compose import BASE,SOURCE,new_font,font_path,width,write_words,restore_actual_source_group
 assert number==10
 inventory=json.loads((BASE/'inputs/native-slots.json').read_text('utf8'))
 plan=json.loads((BASE/'authoring/page10.json').read_text('utf8'))
 slots={r['id']:r for r in inventory['pages'][9]['slots']}
 fonts={};erased=[];shifts=[];placements=[];text_items=[]
 for face in {r['source_prose_face']for r in plan['native_headers']}:
  text=''.join(re.sub(r'\[\[[^\]]+\]\]','',h['translations'][lang])for h in plan['native_headers']if h['source_prose_face']==face)
  fonts[face]=new_font(font_path(lang,face),text)
 for h in plan['native_headers']:
  slot=slots[h['source_slot']];text=h['translations'][lang];face=h['source_prose_face'];raw,metric,font_qa=fonts[face]
  groups={r['id']:r for r in slot['native_expression_groups']}
  used=re.findall(r'\[\[([^\]]+)\]\]',text)
  if sorted(used)!=sorted(groups):raise ValueError(('Original native expression count differs',slot['id'],used,list(groups)))
  kept={glyph_key(g)for r in groups.values()for g in r['glyphs']}
  erased.extend(g for g in slot['source_characters']if glyph_key(g)not in kept)
  parts=[]
  for token in re.split(r'(\[\[[^\]]+\]\])',text):
   if not token:continue
   if token.startswith('[['):
    group=groups[token[2:-2]];left=min(g['origin'][0]for g in group['glyphs']);right=max(g['bbox'][2]for g in group['glyphs'])
    before=h.get('native_expression_before_gaps_by_language',{}).get(lang,{}).get(group['id'],0)
    if not isinstance(before,(int,float))or not 0<=before<=slot['size']/4:raise ValueError('Invalid complete-native-expression leading gap')
    parts.append(dict(kind='native',group=group,left=left,width=right-left,before_gap=before))
   else:parts.append(dict(kind='prose',text=token,width=width(metric,token,slot['size'])))
  total=sum(r['width']+r.get('before_gap',0)for r in parts)
  x=slot['original_horizontal_center']-total/2 if slot.get('align')=='center'else slot['origin'][0]
  if x<slot['allowed_rect'][0]-.001 or x+total>slot['allowed_rect'][2]+.001:raise ValueError(('Unchanged-point native prose overflow',slot['id'],lang,x,total))
  start=x;motions=[]
  for part in parts:
   if part['kind']=='native':
    x+=part.get('before_gap',0)
    dx=x-part['left'];shifts.append(dict(glyphs=part['group']['glyphs'],dx=dx))
    motions.append(dict(id=part['group']['id'],source_glyphs=part['group']['glyphs'],dx=dx,whole_expression_single_dx=True,all_original_y_size_fonts_and_scripts_retained=True))
   else:text_items.append(dict(x=x,y=slot['origin'][1],text=part['text'],face=face,size=slot['size'],render_mode=slot['render_mode'],line_width=slot.get('line_width')))
   x+=part['width']
  placements.append(dict(source_slot=slot['id'],text=text,left=start,right=x,baseline=slot['origin'][1],size=slot['size'],source_font=face,font=font_qa,alignment=slot.get('align','left'),native_expressions=motions))
 raw,qa=reposition_inline(SOURCE,number,erased_glyphs=erased,shifts=shifts,allow_white_background_panels=True)
 doc=fitz.open(stream=raw,filetype='pdf');page=doc[0]
 for face,(raw_font,metric,_)in fonts.items():page.insert_font(fontname='TSHeader'+face,fontbuffer=raw_font)
 for r in text_items:write_words(page,r['x'],r['y'],r['text'],fonts[r['face']][1],r['size'],'TSHeader'+r['face'],r['render_mode'],r.get('line_width'))
 doc.save(out,garbage=0,deflate=False);doc.close();restore_actual_source_group(out,number)
 return dict(native_digit_motion=qa,placements=placements,erased_original_prose=erased,native_shifts=shifts,complete_native_expressions_including_scripts_retained=True)

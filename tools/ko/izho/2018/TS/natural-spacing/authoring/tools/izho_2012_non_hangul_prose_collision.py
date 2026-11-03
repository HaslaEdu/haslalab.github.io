"""Actual final original-CID punctuation/Latin prose versus native text/graphics."""
from pathlib import Path
import hashlib,json,pymupdf as f
from initial_prose_reading_order import journal
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
from pdf_new_prose_native_text_overlap import audit as text_overlap
from pdf_new_hangul_graphics_overlap import audit as graphics_overlap
def underlined_header_source_intent(original_path,source_page,final_path,target):
 def underline(page):
  rows=[r for r in page.get_drawings()if r['rect'].y1<60 and r['rect'].width>400]
  if len(rows)!=1:raise ValueError('Original2012 long header decoration not unique')
  r=rows[0]
  if r['type']!='f'or r['fill']!=(0.,0.,0.)or r['fill_opacity']!=1 or r['color']is not None or not .9<r['rect'].height<1.2 or len(r['items'])!=1 or r['items'][0][0]!='re':raise ValueError('Original2012 underline geometry/paint differs')
  return dict(rect=list(r['rect']),items=repr(r['items']),fill=list(r['fill']),opacity=r['fill_opacity'],even_odd=r['even_odd'])
 def style(g):return(g['c'],g['font'],g['trace_gid'],round(g['size'],5),round(g['origin'][1],5),g['render_mode'],g['color'],g['opacity'],g['linewidth'],g['direction'],g['stroke_color'],g['stroke_opacity'])
 with f.open(original_path)as original,f.open(final_path)as final:
  if hashlib.sha256(Path(original_path).read_bytes()).hexdigest()!='41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db':raise ValueError('Original source underline intent requires pinned unmodified2012 source')
  a=original[source_page-1];b=final[0];source=[g for g in _traces(a)if g['c']==','and g['origin'][1]<60];header=[g for g in target if g['origin'][1]<60]
  if len(source)!=3 or len(header)!=3 or any(style(g)!=style(source[0])for g in source+header):raise ValueError('Only the three exact original-style underlined source header commas have reviewed decoration intent')
  decoration=underline(a)
  if decoration!=underline(b):raise ValueError('Original2012 header underline changed')
 original_ink=graphics_overlap(original_path,page_number=source_page,new_glyphs=source)
 if not original_ink['source_outline_match']['passed']or original_ink['new_hangul_dark_pixels_over_native_foreground']<=0:raise ValueError('Original source header commas do not show the reviewed actual underline intersection')
 return header,dict(source_sha256=hashlib.sha256(Path(original_path).read_bytes()).hexdigest(),source_page=source_page,source_header_commas=len(source),final_header_commas=len(header),original_font_GID_point_paint_baseline_identical=True,original_underline_exact_geometry_and_paint=decoration,actual_source_comma_underline_intersection=original_ink,scope='Only the original source-designed three underlined-header comma glyphs are excluded from graphic-collision rejection. All body punctuation and all new text/native-text collisions remain strict zero.',passed=True)

def audit(plan_path):
 plan_path=Path(plan_path);p=json.loads(plan_path.read_text('utf8'));pdf=plan_path.parents[1]/f"page{p['page']:02}.pdf";q=json.loads(pdf.with_suffix('.qa.json').read_text('utf8'))
 assert p['original_english_source_sha256']=='41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db'
 with f.open(p['source_base'])as old,f.open(pdf)as final:
  rows=journal(old[p['page']-1],p['prose_placements']);prose_keys={glyph_key(g)for row in rows for g in row['glyphs']if g['c'].strip()};source=_traces(old[p['page']-1]);actual=_traces(final[0]);native=[g for g in source if g['c'].strip()and glyph_key(g)not in prose_keys]
  selected=[g for g in source if glyph_key(g)in prose_keys and g['c'].strip()and not(0xac00<=ord(g['c'])<=0xd7a3)]
  shifts={glyph_key(g):s['dx']for s in q['native_shifts']for g in s['glyphs']};target=[]
  for g in selected:
   dx=shifts.get(glyph_key(g),0.);hits=[v for v in actual if v['c']==g['c']and v['font']==g['font']and v['trace_gid']==g['trace_gid']and v['render_mode']==g['render_mode']and abs(v['size']-g['size'])<.001 and abs(v['origin'][1]-g['origin'][1])<.001 and abs(v['origin'][0]-g['origin'][0]-dx)<.001]
   if len(hits)!=1:raise ValueError(('Final translated punctuation/Latin original CID does not resolve uniquely',g,dx,len(hits)))
   target.append(hits[0])
 text=text_overlap(pdf,native_glyphs=native,shifts=q['native_shifts'],prose_glyphs=target)
 source=plan_path.parents[4]/'2012/source/IZhO_2012_TS.pdf';header,intent=underlined_header_source_intent(source,p['source_page'],pdf,target);header_keys={glyph_key(g)for g in header};body=[g for g in target if glyph_key(g)not in header_keys]
 graphics=graphics_overlap(pdf,new_glyphs=body)
 result=dict(source_sha256=p['original_english_source_sha256'],source_base_sha256=p['source_base_sha256'],proof_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),new_non_Hangul_prose_glyphs=len(target),body_non_Hangul_prose_glyphs=len(body),method='Exact authored prose suffix identifies every new non-Hangul CID, including punctuation and dashes; actual final CIDs/font/GID/point/paint/baseline and motion are resolved independently, then actual outline ink is tested against retained native text and clip-aware non-text graphics. No glyph metric-box or family-name collision shortcut. Exactly source-designed underlined-header commas are verified independently against actual original-source ink and decoration.',reviewed_source_underlined_header_comma_intent=intent,native_text_overlap=text,native_graphics_overlap=graphics,passed=text['passed']and graphics['passed']and intent['passed'])
 dest=pdf.with_suffix('.non-hangul-prose-collision.json');raw=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf8')
 if dest.exists()and dest.read_bytes()!=raw:
  history=dest.parent/'audit-history'/hashlib.sha256(dest.read_bytes()).hexdigest()[:16];history.mkdir(parents=True,exist_ok=True);(history/dest.name).write_bytes(dest.read_bytes())
 dest.write_bytes(raw);return result

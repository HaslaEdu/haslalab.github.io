"""Check every final Hangul font outline, source point and baseline independently."""
from pathlib import Path
from io import BytesIO
from collections import Counter
import json,hashlib,re
import pikepdf,pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools.cffLib import CFFFontSet
from fontTools.pens.recordingPen import DecomposingRecordingPen
from izho_initial_outline_qa import trace_font_resources
from pdf_original_style_fonts import FONTS
from pdf_original_text_ops import family_name
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def data(raw):
 if raw[:4]in[b'\x00\x01\x00\x00',b'OTTO',b'true']:
  f=TTFont(BytesIO(raw),lazy=True);return dict(font=f,glyphs=f.getGlyphSet(),order=f.getGlyphOrder(),upm=f['head'].unitsPerEm,cmap=f.getBestCmap(),name=f['name'].getDebugName(6))
 c=CFFFontSet();c.decompile(BytesIO(raw),None);t=c[c.fontNames[0]];return dict(cff=c,glyphs=t.CharStrings,order=t.charset,upm=round(1/t.FontMatrix[0]),name=c.fontNames[0])
def outline(d,name):
 p=DecomposingRecordingPen(d['glyphs']);d['glyphs'][name].draw(p)
 return [(op,[None if pt is None else tuple(round(x/d['upm'],7)for x in pt)for pt in pts])for op,pts in p.value]
def audit(plan_path,cache=None):
 cache={}if cache is None else cache;plan_path=Path(plan_path);p=json.loads(plan_path.read_text('utf8'));target=plan_path.parents[1]/f"page{p['page']:02}.pdf";expected=Counter()
 paths={'Batang':Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2024-original-natural/fonts/Batang-Regular.ttf'),'NotoSerifCJKkr-Regular':FONTS['serif'],'NotoSerifCJKkr-Bold':FONTS['serif-bold'],'NotoSansCJKkr-Regular':FONTS['sans'],'NotoSansCJKkr-Bold':FONTS['sans-bold']}
 source_colors={};source_paints={};source_runs={}
 with fitz.open(p['original_english_source'])as source:
  assert sha(p['original_english_source'])==p['original_english_source_sha256']
  if p['original_english_source_sha256'] in ['41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db','1e526966f308280accc9fe747d08259279f35324e7e7f2e0290271adcaf6536c']:
   from izho_initial_fixed_style import runs_of
   from source_prose_paint import attach_source_paints
   source_page=source[p['source_page']-1];source_runs=runs_of(source_page)
   selected={tuple(placement['at'])for placement in p['prose_placements']};attach_source_paints(source_runs,source_page,selected)
   source_paints={at:source_runs[at]['source_paint']for at in selected}
  for bi,block in enumerate(source[p['source_page']-1].get_text('rawdict')['blocks']):
   if block['type']:continue
   for li,line in enumerate(block['lines']):
    si=0
    for span in line['spans']:
     if not ''.join(c['c']for c in span['chars']).strip():continue
     value=span['color'];source_colors[bi,li,si]=tuple(round((value>>shift&255)/255,6)for shift in [16,8,0]);si+=1
 for placement in p['prose_placements']:
  source_color=source_colors[tuple(placement['at'])]
  source_paint=source_paints.get(tuple(placement['at']))
  if source_paint:
   source_color=tuple(round(v,6)for v in source_paint['fill_color'])
   original=source_runs[tuple(placement['at'])]
   actual_source_baselines={round(c['origin'][1],4)for c in original['chars']if c['c'].strip()}
   if len(actual_source_baselines)!=1:raise ValueError('Original source prose span has mixed physical nonspace baselines; explicit source selection required')
   assert placement['source_font']==original['font']and abs(placement['source_baseline']-next(iter(actual_source_baselines)))<.001
  paint_signature=(source_paint['render_mode'],round(source_paint['line_width'],4),tuple(round(v,6)for v in source_paint['stroke_color']),source_paint['fill_opacity'],source_paint['stroke_opacity'])if source_paint else(0,0.,source_color,1.,1.)
  for part in placement['parts']:
   if not part['font'].startswith('KO_'):continue
   role=part['font'][3:];family={'serif':'NotoSerifCJKkr-Regular','serif_bold':'NotoSerifCJKkr-Bold','sans':'NotoSansCJKkr-Regular','sans_bold':'NotoSansCJKkr-Bold'}[role]
   if role=='serif'and not part.get('oblique_angle')and not re.search('Ital|Oblique',part['source_font']):family='Batang'
   for c in part['text']:
    if 0xac00<=ord(c)<=0xd7a3:
     if source_paint:assert abs(part['size']-original['size'])<.001 and part['source_font']==original['font']
     expected[c,family,round(part['size'],5),round(placement['source_baseline'],2),source_color,(1.,0.),paint_signature]+=1
 for label in p.get('reviewed_bitmap_language_labels',[]):
  family='NotoSansCJKkr-Bold'if label.get('measured_source_font_role','serif-bold')=='sans-bold'else'NotoSerifCJKkr-Bold'
  for c in label['text']:
   if 0xac00<=ord(c)<=0xd7a3:expected[c,family,round(label['measured_source_size_pt'],5),round(label['measured_source_baseline_pt'],2),(0.,0.,0.),(0.,-1.)if label.get('rotation',0)==90 else(1.,0.),(0,0.,(0.,0.,0.),1.,1.)]+=1
 with fitz.open(target)as doc,pikepdf.open(target)as pdf:
  mapped,programs=trace_font_resources(pdf,doc[0]);actual=[g for g in mapped if len(g['c'])==1 and 0xac00<=ord(g['c'])<=0xd7a3 and g['gid']>=0]
  directions={tuple(round(v,4)for v in point):tuple(round(v,4)for v in t['dir'])for t in doc[0].get_texttrace()for cp,gid,point,box in t['chars']if 0xac00<=cp<=0xd7a3}
  def direction(g):return directions[tuple(round(v,4)for v in g['origin'])]
  from izho_natural_spacing import records
  paint_records={}
  def paint_key(g):return(g['c'],family_name(g['font']),round(g['size'],5),tuple(round(v,4)for v in g['origin']))
  for row in records(doc[0]):
   if len(row['c'])==1 and 0xac00<=ord(row['c'])<=0xd7a3:
    k=paint_key(row)
    if k in paint_records:raise ValueError('Final Hangul occurrence has overlapping actual paint records')
    paint_records[k]=row
  def actual_paint(g):
   r=paint_records[paint_key(g)];assert r['paint']==g['render_type']
   return(r['paint'],round(r.get('linewidth')or 0.,4)if r['paint']==2 else 0.,tuple(round(v,6)for v in(r.get('stroke_color')or r['color'])),r.get('opacity',1),r.get('stroke_opacity',1)or 1)
  got=Counter((g['c'],family_name(g['font']),round(g['size'],5),round(g['origin'][0 if direction(g)==(0.,-1.)else 1],2),tuple(round(v,6)for v in g['color']),direction(g),actual_paint(g))for g in actual)
  assert got==expected,('Original font-role, point or baseline mismatch',list((got-expected).items())[:5],list((expected-got).items())[:5])
  programs_data={digest:data(programs[digest]['raw'])for digest in {g['font_program_sha256']for g in actual}};donors={};rows=[]
  for g in actual:
   family=family_name(g['font']);path=paths[family]
   if family not in donors:donors[family]=data(path.read_bytes())
   a=programs_data[g['font_program_sha256']];d=donors[family];key=(g['font_program_sha256'],g['gid'],str(path),g['c'])
   if key not in cache:
    wanted=d['cmap'][ord(g['c'])];o=outline(a,a['order'][g['gid']]);assert o and o==outline(d,wanted),('Actual embedded outline differs from role donor',g);cache[key]=True
   rows.append(dict(c=g['c'],font_family=family,actual_gid=g['gid'],point_size=g['size'],baseline=g['origin'][1],color=g['color'],actual_source_paint_matched=actual_paint(g),source_role_point_baseline_and_color_matched=True,actual_outline_matches_complete_role_donor=True))
  for d in list(programs_data.values())+list(donors.values()):
   if d.get('font'):d['font'].close()
 q=dict(page=p['page'],proof_sha256=sha(target),plan_sha256=sha(plan_path),method='Every final Hangul occurrence must match the authored original source role, exact point size and original prose baseline. Every actual embedded font/GID outline must match the complete role-donor Unicode glyph; no family name or nonempty-outline shortcut.',source_role_point_baseline_counter_matched=True,hangul_glyphs_checked=len(rows),donors={name:dict(path=str(paths[name]),sha256=sha(paths[name]))for name in donors},actual_glyph_checks=rows,passed=True)
 target.with_suffix('.font-source-style.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');return q

from pathlib import Path
import json,hashlib,sys,pikepdf
import pymupdf as f
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2019-theory-original');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from izho_natural_spacing_rebuild import prepare
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
if len(sys.argv)<2:raise SystemExit('Explicit page numbers required; preserve already reviewed plans.')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();folder=B/'2019/native-baseline';pages=sorted(folder.glob('page??.pdf'));assert pages
version=hashlib.sha256(''.join(sha(p)for p in pages).encode()).hexdigest()[:12];output=folder/f'IZhO_2019_T_native-baseline-{len(pages)}p-{version}.pdf'
if not output.exists():
 with pikepdf.Pdf.new()as doc:
  for page in pages:
   with pikepdf.open(page)as single:doc.pages.append(single.pages[0])
  doc.save(output,compress_streams=False)
(folder/'edition-input.json').write_text(json.dumps(dict(year=2019,kind='T',pdf=str(output),sha256=sha(output)),indent=2)+'\n','utf8')
for path in prepare(2019,'T',selected_pages=set(map(int,sys.argv[1:]))):
 d=json.loads(path.read_text('utf8'));d.update(source_language='English',reviewed_initial_prose_reading_order=True,baseline_tolerance_pt=.75,include_image_only_native_math=True)
 d.setdefault('native_move_options',{})['allow_white_background_panels']=True
 # Original2019 pages use a36pt left body margin and a562.8pt right edge.
 # Keep translated prose inside those source columns at unchanged points.
 for r in d['allowed_line_rects']:
  old=r[:]
  if r[1]>60:r[0]=max(35.75,r[0]);r[2]=min(562.8,r[2])
  if r!=old:
   for other in d['source_line_scopes']+d['centered_lines']+d['right_aligned_lines']:
    if other.get('rect')==old:other['rect']=r[:]
 if d['page']in [5,6,7]:
  with f.open(d['original_english_source'])as doc:images=[list(v['bbox'])for v in doc[d['source_page']-1].get_image_info()if v['bbox'][0]>300 and v['bbox'][2]-v['bbox'][0]>30 and v['bbox'][3]-v['bbox'][1]>25]
  columns=[]
  for r in d['allowed_line_rects']:
   if r[1]<60 or any(c['rect']==r for c in d['centered_lines']):continue
   size=(r[3]-r[1])/1.33;y=r[1]+.85*size
   intersecting=[box for box in images if y+.3*size>=box[1]and y-.85*size<=box[3]and r[0]<box[0]]
   if not intersecting:continue
   old=r[:];r[2]=min(r[2],min(box[0]for box in intersecting)-1.5)
   for other in d['source_line_scopes']:
    if other.get('rect')==old:other['rect']=r[:]
   columns.append(dict(baseline=y,rect=r[:],original_images=intersecting,reason='Reviewed original right-side energy-level, molecular-process or resonator picture. Keep the original left prose column and all source picture programs/geometry; only horizontal natural spacing at original source points.'))
  d['reviewed_original_figure_prose_columns']=columns
 if d['page']==2:
  reviewed=[]
  for scope in d['source_line_scopes']:
   y=scope['baseline'];right=373.0 if 99<y<179 else 410.5 if 565<y<656 else None
   if right is None:continue
   old=scope['rect'][:];new=[36.,old[1],right,old[3]];scope['rect']=new
   d['allowed_line_rects']=[new[:]if r==old else r for r in d['allowed_line_rects']]
   for a in d['centered_lines']+d['right_aligned_lines']:
    if a.get('rect')==old:a['rect']=new[:]
   reviewed.append(dict(source_at=scope['source_at'],rect=new,reason='Original source body column ends before the stationary winding-cylinder or circuit picture; source physical points and baselines retained.'))
  d['reviewed_original_figure_prose_columns']=reviewed
  with f.open(d['original_english_source'])as source,f.open(d['source_base'])as initial:
   survivors={glyph_key(g)for g in _traces(initial[1])if g['c'].strip()};gs=[g for g in _traces(source[1])if g['c'].strip()and glyph_key(g)in survivors]
  groups=[]
  for label,rect,wanted in [('free thread length',[79,134.4,87.4,135.7],'l0'),('angular frequency',[90,584.7,165.5,589.5],'ω=1.00∙103s-1'),('voltage amplitude',[87,603.1,142,603.3],'U=15.0V'),('resistance',[301,603.1,370,603.3],'r=2019Ohm'),('capacitance',[197,616.9,253.5,617.1],'C=100μF')]:
   selected=[g for g in gs if f.Rect(rect).contains(f.Point(g['origin']))];assert ''.join(g['c']for g in selected)==wanted,(label,''.join(g['c']for g in selected))
   groups.append(dict(label='Complete original mixed-font '+label+'; all variables, numerals, units and scripts retain original source font/GID/point/y and one common horizontal dx. No equation retyping or unit substitution.',glyphs=selected))
  d['reviewed_native_expression_groups']=groups
 if d['page']==8:
  # The second line of3.10 is a ragged final line of the same full-width
  # paragraph. Its short English text is not a separate narrow source column.
  for r in d['allowed_line_rects']:
   if abs(r[1]-(156.14-10.2))<.04:r[2]=562.8
  for scope in d['source_line_scopes']:
   if abs(scope['baseline']-156.14)<.04:scope['rect'][2]=562.8;scope['reviewed_original_paragraph_width']='Same full-width3.10 paragraph as preceding original line; no adjacent image or right-hand column.'
  d['explicit_native_math_atoms']=[dict(reviewed=True,original_source_only=True,rect=rect,font_regex='.*',baseline=y,reason='One complete original source derivative fraction: keep its original numerator, denominator, subscript, native bar/Form and all fractional font points as a single horizontal object. No piecewise fraction movement or mathematical retyping.')for rect,y in [([427.8,115.5,443.4,135.5],124.34),([149.5,147.,171.8,168.2],156.14)]]
  from pdf_native_inline_reposition import inspect_inline_groups
  inv=inspect_inline_groups(d['source_base'],8)
  with f.open(d['source_base'])as native:rows=_traces(native[7])
  with f.open(d['original_english_source'])as original:source_keys={glyph_key(g)for g in _traces(original[7])if g['c'].strip()}
  for rule in d['explicit_native_math_atoms']:
   keys={glyph_key(g)for g in rows if g['c'].strip()and f.Rect(rule['rect']).contains(f.Point(g['origin']))and glyph_key(g)in source_keys}
   matches=[v for v in inv['forms']if {glyph_key(g)for g in v['glyphs']if g['c'].strip()}==keys]
   assert len(matches)==1
   rule.update(source_form_path=matches[0]['path'],source_form_bbox=matches[0]['native_page_bbox'])
  for y,bottom in [(124.34,135.5),(156.14,168.2)]:
   for r in d['allowed_line_rects']:
    if abs(r[1]-(y-10.2))<.04:r[3]=max(r[3],bottom)
   for scope in d['source_line_scopes']:
    if abs(scope['baseline']-y)<.04:scope['rect'][3]=max(scope['rect'][3],bottom)
  fixed=[187.,423.,260.,449.5]
  d.setdefault('frozen_display_math_rects',[]).append(fixed);d.setdefault('excluded_figure_rects',[]).append(fixed)
  with f.open(d['original_english_source'])as doc:
   gs=[g for g in _traces(doc[7])if g['c'].strip()and g['font']=='CambriaMath'and f.Rect(fixed).contains(f.Point(g['origin']))]
  assert gs
  d['reviewed_stationary_expression_groups']=[dict(label='Complete original second displayed integral, including power numerator/denominator scripts and its original fraction bar. Only the adjoining italic English narrative is translated; every mathematical glyph stays at zero dx.',glyphs=gs)]
 if d['page']==7:
  with f.open(d['original_english_source'])as source:
   gs=[g for g in _traces(source[6])if g['c'].strip()and f.Rect(306.,219.,401.,230.).contains(f.Point(g['origin']))]
  assert len(gs)==16,[(g['c'],g['origin'])for g in gs]
  d['reviewed_native_expression_groups']=[dict(label='Complete original absorption cross-section sigma_A=3,90*10^-16cm^2. The exponent16 belongs to the original10 base inside this same native Form, not to the unrelated dye identifier6G on the preceding prose baseline. All original16 glyphs and scripts must share one horizontal dx.',glyphs=gs)]
 path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
print('PREPARED_SELECTED_2019_T_NATIVE_NATURAL_PAGES',sys.argv[1:],flush=True)

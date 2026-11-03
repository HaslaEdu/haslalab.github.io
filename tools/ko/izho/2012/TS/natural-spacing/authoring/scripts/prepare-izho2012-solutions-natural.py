from pathlib import Path
import json,hashlib,sys,pikepdf,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from izho_natural_spacing_rebuild import prepare
if len(sys.argv)<2:raise SystemExit('Explicit source pages required; preserve reviewed plans.')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();folder=B/'2012/native-baseline';pages=sorted(folder.glob('page??.pdf'));assert pages
version=hashlib.sha256(''.join(sha(p)for p in pages).encode()).hexdigest()[:12];output=folder/f'IZhO_2012_TS_native-baseline-{len(pages)}p-{version}.pdf'
if not output.exists():
 with pikepdf.Pdf.new()as doc:
  for page in pages:
   with pikepdf.open(page)as single:doc.pages.append(single.pages[0])
  doc.save(output,compress_streams=False)
(folder/'edition-input.json').write_text(json.dumps(dict(year=2012,kind='TS',pdf=str(output),sha256=sha(output)),indent=2)+'\n','utf8')
for path in prepare(2012,'TS',selected_pages=set(map(int,sys.argv[1:]))):
 d=json.loads(path.read_text('utf8'));d.update(source_language='English',reviewed_initial_prose_reading_order=True,baseline_tolerance_pt=.75,include_image_only_native_math=True)
 d.setdefault('native_move_options',{})['allow_white_background_panels']=True
 with f.open(d['original_english_source'])as source:
  f.TOOLS.set_small_glyph_heights(True);raw=source[d['source_page']-1].get_text('rawdict')
 columns=[]
 for r in d['allowed_line_rects']:
  old=r[:];scopes=[s for s in d['source_line_scopes']if s['rect']==old or(abs((s['rect'][1]+s['rect'][3])/2-(old[1]+old[3])/2)<.12 and min(s['rect'][2],old[2])>max(s['rect'][0],old[0]))]
  if d['page']==5 and any(s['source_at']==[9,34]for s in scopes):
   if len(scopes)!=1:raise ValueError('Source page5 row10 must be one explicitly split content scope')
   r[0]=144.23;r[2]=468.49
   scopes[0]['original_grid_cell_bounds']=[139.67,468.49]
   scopes[0]['source_enumerator10_stays_in_separate_left_cell']=True
  if r[1]>60 and not any(s.get('original_grid_cell_rect')for s in scopes)and not any(v['rect']==old for v in d['centered_lines']):
   ats=[s['source_at']for s in scopes]
   left=min(raw['blocks'][bi]['lines'][li]['bbox'][0]for bi,li in ats)-.25
   right=555.73
   if d['page']==1 and all(bi==2 and 2<=li<=11 for bi,li in ats):right=280.57
   if d['page']==2 and all((bi==11 or bi==12 and li<=8 or bi==9 and li in[11,12])for bi,li in ats):right=319.21
   r[0]=left;r[2]=right
   columns.append(dict(rect=r[:],source_line_ats=ats,reason='Human-read source2012 original85.08..555.48pt body; upper page1 prose ends280.32pt beside the complete original lever diagram. Exact source line indents and baselines retained; no point fitting.'))
  if r!=old:
   for other in d['source_line_scopes']+d['centered_lines']+d['right_aligned_lines']:
    if other.get('rect')==old:other['rect']=r[:]
 d['reviewed_original_body_columns']=columns
 from izho_native_atomic_tokens import _inventory
 base=Path(d['source_base']);stat=base.stat();inv=_inventory(str(base.resolve()),d['page'],stat.st_mtime_ns,stat.st_size)
 gray=[]
 with f.open(base)as doc:
  for drawing in doc[d['page']-1].get_drawings():
   color=drawing.get('fill')
   if drawing['type']!='f'or color is None or len(color)!=3 or drawing.get('color')is not None:continue
   if max(abs(a-b)for a,b in zip(color,[.9621423482894897,.9622796773910522,.9620965719223022]))>.000001:continue
   if drawing.get('fill_opacity')!=1 or not drawing['items']or any(item[0]!='re'for item in drawing['items']):raise ValueError('Source gray field needs exact unstroked rectangle profile')
   matches=[v for v in inv['vector_paths']if max(abs(a-b)for a,b in zip(v['rect'],drawing['rect']))<.001]
   if len(matches)!=1:raise ValueError('Exact gray field vector program not uniquely resolved')
   gray.append(dict(**matches[0],actual_fill_color=list(color),source_only=True,reason='Exact original source2012 OLE gray field stays stationary behind translated language and complete native mathematics; no path, point, paint or background geometry is modified.'))
 d['reviewed_stationary_gray_field_panels']=gray
 d['native_move_options']['reviewed_stationary_vector_paths']=gray
 from izho_2012_complete_inline_fractions import apply_reviewed_fractions
 apply_reviewed_fractions(d)
 from izho_2012_equation_counters import apply_reviewed_counters
 apply_reviewed_counters(d)
 from izho_2012_inline_clips import apply as apply_inline_clips
 apply_inline_clips(d)
 joins={1:[([2,9,0],'2','법칙을')],2:[([12,7,0],'2','배,'),([12,7,0],'3','배를')],3:[([8,9,0],'3','개 점;'),([8,11,0],'6','개 점.')],11:[([8,4,0],'X','축 기호 표기'),([8,7,0],'Y','축 기호 표기'),([8,17,0],'k','값')]}
 d['reviewed_native_hangul_word_joins']=[]
 for at,literal,following in joins.get(d['page'],[]):
  matches=[v for v in d['reviewed_source_prose_native_reference_glyphs']if v['source_at']==at and v['source_text']==literal]
  if len(matches)!=1:raise ValueError('Reviewed native/Hangul compound join must identify one original literal')
  d['reviewed_native_hangul_word_joins'].append(dict(native_source_glyphs=matches[0]['source_glyphs'],following_source_at=at,following_text=following,reviewed=True,reason='Explicit authored Korean compound or counter attaches directly to this unchanged original native numeral/variable; no added quarter-em inside 제2법칙,3개,X축 or k값.'))
 path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
print('PREPARED_SELECTED_2012_TS_NATIVE_NATURAL_PAGES',sys.argv[1:],flush=True)

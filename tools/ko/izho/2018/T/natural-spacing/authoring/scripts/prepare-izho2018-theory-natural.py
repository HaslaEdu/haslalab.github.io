from pathlib import Path
import json,hashlib,sys,pikepdf
import pymupdf as fitz
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original')
sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from izho_natural_spacing_rebuild import prepare
from pdf_native_inline_reposition import _traces
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
folder=B/'2018/native-baseline';pages=sorted(folder.glob('page??.pdf'));assert pages
version=hashlib.sha256(''.join(sha(p)for p in pages).encode()).hexdigest()[:12]
output=folder/f'IZhO_2018_T_native-baseline-{len(pages)}p-{version}.pdf'
if not output.exists():
 with pikepdf.Pdf.new()as doc:
  for page in pages:
   with pikepdf.open(page)as single:doc.pages.append(single.pages[0])
  doc.save(output,compress_streams=False)
(folder/'edition-input.json').write_text(json.dumps(dict(year=2018,kind='T',pdf=str(output),sha256=sha(output)),indent=2)+'\n','utf8')
selected=set(map(int,sys.argv[1:]))if len(sys.argv)>1 else None
for pp in prepare(2018,'T',selected_pages=selected):
 d=json.loads(pp.read_text('utf8'));d.update(source_language='English',reviewed_initial_prose_reading_order=True,baseline_tolerance_pt=.75,include_image_only_native_math=True)
 # The original Word PDF has white text-frame backing rectangles. They stay
 # stationary and byte-identical. The shared guard independently verifies its
 # existing safe-white-panel predicate; no drawing/mathematical path moves.
 d.setdefault('native_move_options',{})['allow_white_background_panels']=True
 d['reviewed_original_stationary_white_word_text_frames']=True
 if d['page']==2:
  reviewed=[]
  for scope in d['source_line_scopes']:
   y=scope['baseline'];limits=None
   if 105<y<177:limits=(84.73,512.25,'Full first-part body column ends before original test-tube image x515.95.')
   elif 180<y<402:limits=(235.77,554.27,'Right prose column stays to the right of original wide-vessel figure x226.95.')
   elif 439<y<571:limits=(243.69,554.27,'Right circuit prose column stays beyond original circuit image x234.95.')
   elif 607<y<784:limits=(84.73,370.75,'Left optical prose column ends before original17-gon figure x372.8; original English and target Korean source baselines/font points unchanged.')
   if limits is None:continue
   old=scope['rect'][:];new=[limits[0],old[1],limits[1],old[3]]
   d['allowed_line_rects']=[new[:]if r==old else r for r in d['allowed_line_rects']]
   for other in d['source_line_scopes']+d['centered_lines']+d['right_aligned_lines']:
    if other.get('rect')==old:other['rect']=new[:]
   reviewed.append(dict(source_at=scope['source_at'],baseline=y,rect=new,reason=limits[2]))
  d['reviewed_original_figure_prose_columns']=reviewed
 if d['page']==3:
  reviewed=[]
  for scope in d['source_line_scopes']:
   if not 94<scope['baseline']<243:continue
   old=scope['rect'][:];new=[84.73,old[1],328.5,old[3]]
   d['allowed_line_rects']=[new[:]if r==old else r for r in d['allowed_line_rects']]
   for other in d['source_line_scopes']+d['centered_lines']+d['right_aligned_lines']:
    if other.get('rect')==old:other['rect']=new[:]
   reviewed.append(dict(source_at=scope['source_at'],baseline=scope['baseline'],rect=new,reason='Original mountain photograph begins atx330.0; introductory prose stays in its original left column with unchanged source font points and baselines.'))
  d['reviewed_original_figure_prose_columns']=reviewed
 if d['page']==4:
  d.setdefault('frozen_display_math_rects',[]).append([265.5,385.5,375.,407.])
  d.setdefault('excluded_figure_rects',[]).append([265.5,385.5,375.,407.])
  d['explicit_native_math_atoms']=[dict(reviewed=True,original_source_only=True,rect=[332.5,519.,439.5,539.],font_regex='Cambria.?Math',baseline=529.5800170898438,reason='Complete original inline integral dx/(a*x+b)=1/a*ln|a*x+b|: retain original integral, all numerator/denominator scripts, fraction bars, glyph fonts/points/baselines and internal geometry as one source-native mathematical widget. Only one common horizontal translation beside Korean hint. No mathematical retyping.')]
 if d['page']==5:
  reviewed=[]
  for scope in d['source_line_scopes']:
   if not 110<scope['baseline']<227:continue
   old=scope['rect'][:];new=[84.73,old[1],388.,old[3]]
   d['allowed_line_rects']=[new[:]if r==old else r for r in d['allowed_line_rects']]
   for other in d['source_line_scopes']+d['centered_lines']+d['right_aligned_lines']:
    if other.get('rect')==old:other['rect']=new[:]
   reviewed.append(dict(source_at=scope['source_at'],rect=new,reason='Original inertial-frame diagram begins atx389.55; keep original left prose column, source physical points/baselines and unchanged diagram.'))
  d['reviewed_original_figure_prose_columns']=reviewed
  display=[154.,231.5,491.,254.5]
  d.setdefault('excluded_figure_rects',[]).append(display);d.setdefault('frozen_display_math_rects',[]).append(display)
  with fitz.open(d['original_english_source'])as original:
   gs=_traces(original[4]);box=fitz.Rect(261.69,439.54,346.45,443.9)
   invariant=[g for g in gs if g['c'].strip()and g['font']=='Cambria Math'and box.contains(fitz.Point(g['origin']))]
  assert invariant
  d['reviewed_native_expression_groups']=[dict(label='Complete original energy-momentum invariant. Its superscript2 belongs to this source expression, not the momentum variable on the previous prose line; every source glyph must retain one common dx and original y/point.',glyphs=invariant)]
  for scope in d['source_line_scopes']:
   if scope['source_at']!=[17,3]:continue
   old=scope['rect'][:];new=[84.73,min(old[1],688.),554.27,max(old[3],710.)]
   d['allowed_line_rects']=[new[:]if r==old else r for r in d['allowed_line_rects']]
   for other in d['source_line_scopes']+d['centered_lines']+d['right_aligned_lines']:
    if other.get('rect')==old:other['rect']=new[:]
  d['explicit_native_math_atoms']=[dict(reviewed=True,original_source_only=True,rect=[96.,688.,147.16,710.],font_regex='Cambria.?Math',baseline=700.75,reason='Complete original recession-speed expression including the1/100 fraction, its original numerator/denominator and bar, original velocity subscript and final c. All glyphs and paths retain their internal geometry and one common horizontal dx beside Korean prose; no equation retyping.')]
 if d['page']==6:
  reviewed=[]
  for scope in d['source_line_scopes']:
   y=scope['baseline'];limits=None
   if 154<y<278:limits=(84.73,373.7,'Original water-refraction diagram starts atx375.2; translated prose stays left of it at unchanged source points/baselines.')
   elif scope['source_at'][0]==10 and 404<y<593:limits=(286.67,554.27,'Original Fizeau apparatus ends atx277.35; preserve original right prose column atx286.92 and unchanged source diagram.')
   if limits is None:continue
   old=scope['rect'][:];new=[limits[0],old[1],limits[1],old[3]]
   d['allowed_line_rects']=[new[:]if r==old else r for r in d['allowed_line_rects']]
   for other in d['source_line_scopes']+d['centered_lines']+d['right_aligned_lines']:
    if other.get('rect')==old:other['rect']=new[:]
   reviewed.append(dict(source_at=scope['source_at'],rect=new,reason=limits[2]))
  d['reviewed_original_figure_prose_columns']=reviewed
 pp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
print('PREPARED_ORIGINAL_NATIVE_2018_T_PREFIX',len(pages),'private only; full6page edition not complete',flush=True)

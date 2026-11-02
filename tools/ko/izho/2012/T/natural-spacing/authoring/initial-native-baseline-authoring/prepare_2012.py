from pathlib import Path
import sys,json,hashlib,pikepdf,re
import pymupdf as fitz
B=Path(__file__).resolve().parent;sys.path[:0]=[str(B/'engine'),str(Path.cwd()/'tools'),str(B.parent/'izho-natural-spacing')]
from izho_natural_spacing_rebuild import prepare,split_scopes_around_math
from pdf_memory_gate import page_worker
from coalesce_initial_scopes import coalesce
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
folder=B/'2012/native-baseline';merged=folder/'IZhO_2012_T_KO_native-baseline.pdf'
with pikepdf.Pdf.new()as joined:
 for n in range(1,7):
  with pikepdf.open(folder/f'page{n:02}.pdf')as d:joined.pages.append(d.pages[0])
 joined.save(merged,compress_streams=False)
(folder/'edition-input.json').write_text(json.dumps(dict(year=2012,kind='T',pdf=str(merged),sha256=sha(merged)),indent=2),encoding='utf8')
plans=prepare(2012,'T')
for n,pp in enumerate(plans,1):
 d=json.loads(pp.read_text('utf8'));old=json.loads((B/f'2012/original_style/page{n}.json').read_text('utf8'))
 d['reviewed_initial_prose_reading_order']=True;d['baseline_tolerance_pt']=.75
 # Source columns are reviewed against complete original figures, not merely
 # occupied pixels: new prose must not enter the white diagram background.
 columns=old.get('reviewed_source_columns',[])
 if n==3:columns=[dict(source_at_block=2,line_range=[1,41],left=235.8,right=558)]
 if n==5:columns=[dict(source_at_block=b,line_range=[0,100],left=189,right=558)for b in[9,10]]
 def scope_rect(s):
  r=list(s['rect']);bi,li=s['source_at']
  if s['baseline']>=60:r[0]=max(71.75,r[0]);r[2]=min(558,r[2])
  for c in columns:
   if bi==c.get('source_at_block')and c['line_range'][0]<=li<=c['line_range'][1]:r[0]=max(c['left']-.25,r[0]);r[2]=c['right']
  return r
 # Rebuild logical row rectangles after source-specific column clamps.
 rects=[]
 for s in d['source_line_scopes']:
  before=list(s['rect']);s['rect']=scope_rect(s);r=s['rect']
  for align in d['centered_lines']+d['right_aligned_lines']:
   if align.get('rect')==before:align['rect']=r
  if not any(all(abs(a-b)<.01 for a,b in zip(r,v))for v in rects):rects.append(r)
 # The original Russian footer is a separate right-aligned page label.
 for s in d['source_line_scopes']:
  if s['source_at']==[0,1]:
   old_rect=list(s['rect']);s['rect']=[522,old_rect[1],550,old_rect[3]]
   rects=[s['rect']if r==old_rect else r for r in rects]
   d['right_aligned_lines'].append(dict(baseline=s['baseline'],right=548.94,rect=s['rect']))
 displays=old.get('reviewed_original_display_rects',[])
 if n==2:displays=[[173,584,339,600]]
 if n==4:displays=[[182,90,558,119],[181,169,558,187],[146,491,558,513],[146,581,558,612]]
 if n==5:displays=[[147,128.5,558,148],[184,549,558,577],[183,607,558,634],[145,650,558,695]]
 if n==6:displays=[[329,74,479,105],[283,150,425,227],[255,263,323,291],[369,263,406,291],[217,302,362,332],[409,302,446,332]]
 d['frozen_display_math_rects']=displays
 # Exact original display glyphs stay outside narrative token collection.
 d['excluded_figure_rects']=[r for r in d['excluded_figure_rects']if r not in d.get('stationary_table_math',[])]
 d['excluded_figure_rects']+=displays
 d['allowed_line_rects']=split_scopes_around_math(rects,[dict(rect=r,baseline=s['baseline'])for r in displays for s in d['source_line_scopes']if r[1]<=s['baseline']<=r[3]])
 coalesce(d)
 if n==4:d['hangul_word_revisions']=[dict(source_at=[7,14,0],old='의존하는',new='따른',reason='Equivalent Korean dependence clause at source point size; no parameter or information omitted.'),dict(source_at=[7,14,0],old='상수이다',new='상수다',reason='Equivalent compact Korean copula; original variable list retained unchanged.')]
 if n==3:
  measurements=json.loads((B/'2012/source-figure-review/piston-label-source-font-measurements.json').read_text('utf8'))
  d['reviewed_bitmap_language_labels']=[dict(reviewed=True,source_sha256=d['original_english_source_sha256'],image_index=0,source_word_ink_rect_px=rect,text=text,source_label=row['label'],measured_source_size_pt=row['inferred_size_pt_unrounded'],measured_source_baseline_pt=row['inferred_baseline_pt'],measurement=row,source_face_weight_estimate='Times New Roman Bold (serif/bold visual review; bitmap metadata unavailable)',measurement_is_estimate=True)for row,text,rect in zip(measurements['measurements'],['대기','피스톤','공기'],[[75,14,202,38],[211,83,307,99],[93,262,164,278]])]
 # The source uses regular Times question numbers, rather than bold ones.
 with fitz.open(old['source'])as source:
  raw=source[n-1].get_text('rawdict');prefix=[]
  for block in raw['blocks']:
   if block['type']:continue
   for line in block['lines']:
    for span in line['spans']:
     text=''.join(c['c']for c in span['chars'])
     if re.fullmatch(r'[23]\.\d+\s*',text):
      prefix.extend(dict(c=c['c'],font=span['font'],size=span['size'],origin=list(c['origin']))for c in span['chars']if c['c'].strip())
  d['section_number_prefixes']+=prefix
  whites=[list(p['rect'])for p in source[n-1].get_drawings()if p.get('fill')==(1,1,1)and p.get('color')is None]
  if whites:d['native_move_options']=dict(reviewed_white_panel_rects=whites)
  review=B/'2012/source-page-review';review.mkdir(exist_ok=True)
  if not(review/f'page{n:02}.png').exists():
   with page_worker():source[n-1].get_pixmap(matrix=fitz.Matrix(1.3,1.3),alpha=False).save(review/f'page{n:02}.png')
 d['reviewed_source_columns']=columns
 pp.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
 print('PREPARED_INITIAL',n,flush=True)

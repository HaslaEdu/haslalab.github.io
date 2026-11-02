from pathlib import Path
import json,hashlib,sys,pikepdf,pymupdf as f
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from izho_natural_spacing_rebuild import prepare
if len(sys.argv)<2:raise SystemExit('Explicit page numbers required; preserve reviewed plans.')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();folder=B/'2011/native-baseline';pages=sorted(folder.glob('page??.pdf'));assert pages
version=hashlib.sha256(''.join(sha(p)for p in pages).encode()).hexdigest()[:12];output=folder/f'IZhO_2011_TS_native-baseline-{len(pages)}p-{version}.pdf'
if not output.exists():
 with pikepdf.Pdf.new()as doc:
  for page in pages:
   with pikepdf.open(page)as single:doc.pages.append(single.pages[0])
  doc.save(output,compress_streams=False)
(folder/'edition-input.json').write_text(json.dumps(dict(year=2011,kind='TS',pdf=str(output),sha256=sha(output)),indent=2)+'\n','utf8')
for path in prepare(2011,'TS',selected_pages=set(map(int,sys.argv[1:]))):
 d=json.loads(path.read_text('utf8'));d.update(source_language='English',reviewed_initial_prose_reading_order=True,baseline_tolerance_pt=.75,include_image_only_native_math=True);d.setdefault('native_move_options',{})['allow_white_background_panels']=True
 with f.open(d['original_english_source'])as source:pictures=[list(v['bbox'])for v in source[d['source_page']-1].get_image_info()if v['bbox'][0]>300 and v['bbox'][2]-v['bbox'][0]>30 and v['bbox'][3]-v['bbox'][1]>25]
 columns=[]
 for r in d['allowed_line_rects']:
  old=r[:]
  if r[1]>60:
   r[0]=max(71.75,r[0]);r[2]=min(558.25,r[2])
   scopes=[s for s in d['source_line_scopes']if s['rect']==old]
   if not any(s.get('original_grid_cell_rect')for s in scopes)and not any(v['rect']==old for v in d['centered_lines']):
    # Ordinary source prose uses the72..558pt body column. A short, ragged
    # English line is not an independently narrow paragraph container.
    r[2]=558.25
    adjacent=[box for box in pictures if r[0]<box[0]and r[1]<box[3]and r[3]>box[1]]
    if adjacent:r[2]=min(r[2],min(box[0]for box in adjacent)-1.5)
    columns.append(dict(rect=r[:],source_line_ats=[s['source_at']for s in scopes],original_adjacent_pictures=adjacent,reason='Reviewed original72..558pt prose column, retaining source indentation, exact baselines and source figure/table boundaries; ragged short text is not a narrow container. No font-point fitting.'))
  if r!=old:
   for other in d['source_line_scopes']+d['centered_lines']+d['right_aligned_lines']:
    if other.get('rect')==old:other['rect']=r[:]
 d['reviewed_original_body_columns']=columns
 # Source Word may split a single physical prose/formula line into several
 # blocks. Rejoin overlapping scopes after restoring the source column width.
 # Actual disjoint table columns retain their original grid-cell boundaries.
 rects=[r[:]for r in d['allowed_line_rects']];changed=True
 while changed:
  changed=False
  for i,a in enumerate(rects):
   match=next((j for j in range(i+1,len(rects))if abs((a[1]+a[3])/2-(rects[j][1]+rects[j][3])/2)<.12 and min(a[2],rects[j][2])>max(a[0],rects[j][0])),None)
   if match is None:continue
   b=rects.pop(match);old=[a[:],b[:]];a[:]=[min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])]
   for other in d['source_line_scopes']+d['centered_lines']+d['right_aligned_lines']:
    if other.get('rect')in old:other['rect']=a[:]
   changed=True;break
 d['allowed_line_rects']=rects
 if d['page']in[3,9,10]:
  from izho_2011_picture_layout import apply_reviewed_layout
  apply_reviewed_layout(d)
 if d['page']in[4,8]:
  from izho_2011_complete_inline_fractions import apply_reviewed_fractions
  apply_reviewed_fractions(d)
 from izho_2011_equation_counters import apply_reviewed_counters
 apply_reviewed_counters(d)
 path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
print('PREPARED_SELECTED_2011_TS_NATIVE_NATURAL_PAGES',sys.argv[1:],flush=True)

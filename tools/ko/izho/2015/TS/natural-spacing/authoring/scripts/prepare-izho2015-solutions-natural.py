"""Private source2015 layout review; never regenerates shared/frozen engines."""
from pathlib import Path
import json,hashlib,sys,os,pikepdf,pymupdf as f
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2015-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from izho_natural_spacing_rebuild import prepare,stationary_table_math
from izho_initial_fixed_style import runs_of,slot_source
from izho_2015_equation_counters import apply_reviewed_counters
from pdf_native_inline_reposition import inspect_inline_groups,_traces
from pdf_original_text_ops import glyph_key
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
SOURCE='c1bc32cc38c3f3b65121439f41feee3a8bcb48dcce1a41e14b16ba177eccbcde'
FRAMES={1:[[665,787]],2:[[72,119.4]],3:[[88,232],[603,785]],4:[[72,119.4]],5:[[157,579]],6:[],7:[],8:[],9:[],10:[[284,784]],11:[[73,690]]}
PROFILES={
1:[([368,164,392.6,182],175.73),([531.8,164,552,182],175.73),([113.6,181,127,200],192.77),([186,181,199.6,200],192.77),([283,181,308.4,200],192.77),([401.5,181,417.1,200],192.77),([479,181,494.4,200],192.77),([116,213,140.3,232],224.47),([265,213,280.3,232],224.47),([117,230,132.6,249],241.51),([259,230,286.5,249],241.51),([115,248,142.2,267],259.51),([202,248,216,267],259.51)],
2:[([101,233,193.6,269],251.59)],3:[([165,257,186.2,275],268.15)],
4:[([120,342,155.4,366],355.78),([169,342,206.8,366],355.78),([218.5,342,256.5,366],355.78),([267,342,296.8,366],355.78),([119,538,149.2,558],550.97)],
6:[([88,114,123.3,133],125.81),([72.8,248,87.4,269],260.95001220703125),([269.5,249,282.8,270],260.95001220703125),([285.5,700,292.5,720],710.83),([367,700,383,721],710.83)],
8:[([484,450,552,486],469.82),([507,487,552,521],503.42),([501,521,552,554],537.5),([391,557,473,591],573.53),([510,561,552,589],573.53)],
9:[([366,535,400,561],550.25),([354,633,369,653],646.03),([213.5,610,313,640],626.57),([350,610,448,640],626.57)],
10:[([210,309,239,328],319.78),([202,351,213.5,371],362.5),([235.5,351,249,371],362.5),([250,368,316,403],385.08),([118,413,185,449],430.44),([118,465,179,501],482.3),([268,490,304,524],506.06),([210,513,307,549],530.3),([147,547,283,583],565.61)],
11:[([210,74,239,94],84.5),([338,119,391,160],137.57),([297,191,353,230],210.55)]}
def right_bound(n,ats):
 if n==5 and all(bi==76 and 1<=li<=5 for bi,li in ats):return 354.
 if n==6:
  if all((bi in[30,31])or(bi==33 and 1<=li<=4)or(bi==34 and li in[0,1])for bi,li in ats):return 322.7
  if all((bi==34 and li in[2,3])or(bi==37 and li in[0,1])for bi,li in ats):return 411.6
  if all(bi==42 and 0<=li<=9 for bi,li in ats):return 405.8
 if n==8 and all(bi==1 and li in[2,3]for bi,li in ats):return 366.2
 return 555.94
def native_match(g,rows):
 hits=[h for h in rows if h['c']==g['c']and h['font']==g['font']and h['trace_gid']==g['trace_gid']and abs(h['size']-g['size'])<.0001 and max(abs(a-b)for a,b in zip(h['origin'],g['origin']))<.0001 and all(h.get(k)==g.get(k)for k in ['render_mode','color','opacity','linewidth','direction','stroke_color','stroke_opacity','wmode','colorspace'])]
 if len(hits)!=1:raise ValueError(('Original physical glyph must match uniquely',g,len(hits)))
 return hits[0]
def atoms(d,authored,raw,runs):
 n=d['page'];orig=Path(d['original_english_source']);cache=B/f'2015/inspection/page{n:02}-original-native-inline-inventory.json'
 original_inv=json.loads(cache.read_text('utf8'))if cache.exists()else inspect_inline_groups(orig,n)
 if not cache.exists():cache.write_text(json.dumps(original_inv,ensure_ascii=False)+'\n','utf8')
 initial=inspect_inline_groups(d['source_base'],n)
 with f.open(orig)as source:original_rows=_traces(source[n-1])
 with f.open(d['source_base'])as base:initial_rows=_traces(base[n-1])
 erased={glyph_key(g)for s in authored['slots']for g in slot_source(s,runs)[1]}
 original_rows=[g for g in original_rows if g['c'].strip()and glyph_key(g)not in erased]
 profiles=list(PROFILES.get(n,[]));table_profiles=[]
 if n==5:
  labels=[(12,6,0),(14,0,0),(14,2,0),(14,4,0),(16,0,0),(21,0,0),(26,0,0),(26,3,0),(26,7,0),(26,10,0),(31,1,0),(33,3,0),(33,6,0),(38,0,0),(56,0,0),(57,0,0),(75,0,0)]
  grid=sorted({round((v['rect'][1]+v['rect'][3])/2,4)for v in original_inv['vector_paths']if v['rect'][2]-v['rect'][0]>=350 and abs(v['rect'][3]-v['rect'][1])<=1.5 and v['rect'][0]<=112 and v['rect'][2]>=482 and 157<=v['rect'][1]<=579})
  for i,at in enumerate(labels,1):
   y=runs[at]['origin'][1];top=max(v for v in grid if v<y);bottom=min(v for v in grid if v>y)
   rect=[155.,top+.001,483.,bottom-.001];profiles.append((rect,y));table_profiles.append(dict(source_at=list(at[:2]),formula=i,rect=rect,baseline=y))
  d['reviewed_inline_grading_math_rows']=table_profiles
 out=[];evidence=[];claimed=set()
 for profile_index,(box,baseline) in enumerate(profiles):
  rect=f.Rect(box);gs=[g for g in original_rows if rect.contains(f.Point(g['origin']))]
  union_glyphs=None
  force_path={8:{0:[1706],1:[1841],2:[1940]},10:{8:[4985]}}.get(n,{}).get(profile_index)
  if force_path:
   complete=[v for v in original_inv['forms']if v['path']==force_path];assert len(complete)==1
   if n==10:union_glyphs=gs
   form_keys={glyph_key(g)for g in complete[0]['glyphs']if g['c'].strip()};gs=[g for g in original_rows if glyph_key(g)in form_keys];assert len(gs)==len(form_keys)
  if not gs:raise ValueError(('Empty reviewed original math region',n,box,baseline))
  wanted={glyph_key(g)for g in gs};assert not(wanted&claimed),(n,box)
  # Prefer the complete original Form invocation. Its literal source stream
  # carries every root/fraction rule, clip, intrinsic background and script.
  forms=[v for v in original_inv['forms']if {glyph_key(g)for g in v['glyphs']if g['c'].strip()}==wanted]
  rule=dict(reviewed=True,original_source_only=True,rect=box,font_regex='.*',baseline=baseline,source_native_glyphs=[native_match(g,initial_rows)for g in gs],include_zero_height_vector_bounds=True,reason='Full original2015 source page visually read. One complete original inline mathematical expression shares one horizontal displacement, retaining exact native glyphs/fonts/GIDs/fractional points/paint/Y and every original fraction/root rule. Original source scoring grids and display labels stay stationary; translation and natural quarter-em prose gaps alone change.')
  entry=dict(reviewed_rect=box,logical_prose_baseline=baseline,original_glyphs=gs)
  if n==9 and profile_index in[0,1]:rule['include_original_zero_advance_glyph_origins_in_bounds']=True
  if n==5:
   initial_wanted={glyph_key(g)for g in rule['source_native_glyphs']}
   clips=[v for v in initial['clip_groups']if v.get('known_rectangular_clips')and len(v['clip_rects'])==1 and{glyph_key(g)for g in v['glyphs']if g['c'].strip()}==initial_wanted]
   if not clips:raise ValueError(('Complete original source2015 table-row clip not found',profile_index+1,''.join(g['c']for g in gs)))
   clip=min(clips,key=lambda v:v['operator_indices'][0]);rule.update(rect=clip['clip_rects'][0],use_complete_original_clip=True,source_complete_clip_operator_indices=clip['operator_indices'])
   # The complete original source row clip includes the native reference
   # (n), every formula line/root/fraction, and no score or grid column.
   # Its English label was already legitimately suppressed in the baseline;
   # Korean 식 is outside that native clip. Moving the complete row avoids
   # falsely clipping a source script at a repeated Word ancestor boundary.
   entry.update(original_vector_paths=[v for v in original_inv['vector_paths']if f.Rect(clip['clip_rects'][0]).contains(f.Rect(v['rect']))],native_program='complete original table-row native clip: reference plus every original formula glyph and fraction/root vector; only original English prose suppressed',initial_complete_clip=clip)
   out.append(rule);evidence.append(entry);claimed|=wanted;continue
  if forms:
   form=min(forms,key=lambda v:len(v['path']));matches=[v for v in initial['forms']if v['original_raw_sha256']==form['original_raw_sha256']and max(abs(a-b)for a,b in zip(v['native_page_bbox'],form['native_page_bbox']))<.001 and {glyph_key(g)for g in v['glyphs']if g['c'].strip()}=={glyph_key(g)for g in rule['source_native_glyphs']}]
   if len(matches)!=1:raise ValueError(('Complete original Form absent/ambiguous in initial',n,box,len(matches)))
   actual=matches[0];r=f.Rect(actual['native_page_bbox'])
   for g in actual['glyphs']:
    if g['c'].strip():r|=f.Rect(g['bbox']);r.include_point(f.Point(g['origin']))
   rule.update(rect=list(r+(-.001,-.001,.001,.001)),source_form_path=actual['path'],source_form_bbox=actual['native_page_bbox'])
   entry.update(original_form=form,initial_form_path=actual['path'],native_program='complete original Form')
   if n in[3,8,10,11]:
    keys={glyph_key(g)for g in rule['source_native_glyphs']};clips=[v for v in initial['clip_groups']if v.get('known_rectangular_clips')and len(v['clip_rects'])==1 and f.Rect(v['clip_rects'][0]).height<80 and{glyph_key(g)for g in v['glyphs']if g['c'].strip()}==keys]
    if clips:
     complete=min(clips,key=lambda v:v['operator_indices'][0]);rule.update(rect=complete['clip_rects'][0],use_complete_original_clip=True,source_complete_clip_operator_indices=complete['operator_indices']);entry['initial_complete_original_invocation_clip']=complete
   if union_glyphs:
    entry.update(original_glyphs=union_glyphs,native_program='complete original Form plus adjacent original native suffix: common physical dx independently checked across both programs',original_vector_paths=[])
    entry.pop('original_form');entry['literal_source_form_program_sha256']=form['original_raw_sha256']
  else:
   paths=[v for v in original_inv['vector_paths']if rect.contains(f.Rect(v['rect']))]
   entry.update(original_vector_paths=paths,native_program='original glyphs and every wholly enclosed original native vector path')
  out.append(rule);evidence.append(entry);claimed|=wanted
 # Word can clip several circled-reference numerals in a vertical list as
 # one container. They are separate prose references on separate source
 # baselines, not a fraction or one moving multi-line mathematical object.
 # Explicit individual original references override that false collector.
 import re
 reference_review=[]
 for item in d.get('reviewed_source_prose_native_reference_glyphs',[]):
  if not re.fullmatch(r'[0-9()]+',item['source_text'].strip()):continue
  gs=[g for g in original_rows if any(glyph_key(g)==glyph_key(h)for h in item['source_glyphs'])]
  if not gs or any(glyph_key(g)in claimed for g in gs):continue
  baseline=gs[0]['origin'][1]
  if not any(a<=baseline<=b for a,b in FRAMES[n]):continue
  if max(g['origin'][1]for g in gs)-min(g['origin'][1]for g in gs)>.001:raise ValueError('A protected native prose reference spans source baselines')
  r=f.Rect()
  for g in gs:r|=f.Rect(g['bbox']);r.include_point(f.Point(g['origin']))
  rule=dict(reviewed=True,original_source_only=True,rect=list(r+(-.001,-.001,.001,.001)),font_regex='.*',baseline=baseline,source_native_glyphs=[native_match(g,initial_rows)for g in gs],include_zero_height_vector_bounds=True,reason='Exact original source table prose reference numeral; one original physical text row only. Source vertical list container is not a mathematical fraction. This original encoded numeral packs naturally with its translated prose while retaining original font/GID/point/paint/Y.')
  out.append(rule);claimed.update(glyph_key(g)for g in gs);reference_review.append(dict(source_at=item['source_at'],native_reference=item['source_text'],original_baseline=baseline))
 d['reviewed_individual_native_grading_prose_references']=reference_review
 if n==9:
  d['reviewed_original_accent_to_prose_word_spaces']=[dict(reviewed=True,native_source_glyphs=out[i]['source_native_glyphs'],following_source_at=at,reason='The literal original Times combining dot has zero advance and an outline overhang after the original Cambria p-dot cluster. Retain that complete original compound accent geometry and use one ordinary quarter-em word space before the following Korean clause. This prevents actual native ink collision without fitting or an English-width hole.')for i,at in[(0,[49,2,4]),(1,[56,0,2])]]
 moving={glyph_key(g)for rule in out for g in rule['source_native_glyphs']}
 removed=[];regions=[]
 for region in d['stationary_table_math']:
  overlap=[g for g in region['native_glyphs']if glyph_key(g)in moving]
  if overlap:
   removed.append(dict(source_at=region['source_at'],moving_run_in_native_glyphs=overlap,reason='Original run-in prose mathematical phrase, not a separate aligned formula column. Complete original expression is bound to a common dx; actual grading grids/score columns remain stationary.'))
   region['native_glyphs']=[g for g in region['native_glyphs']if glyph_key(g)not in moving]
  if region['native_glyphs']:regions.append(region)
 d['stationary_table_math']=regions;d['reviewed_run_in_expression_stationary_detector_corrections']=removed
 d['explicit_native_math_atoms']=out;d['reviewed_independent_original_expression_geometry_profiles']=evidence
 d['reviewed_original_math_profile_source_sha256']=SOURCE
 return original_inv
def clean(d,authored,raw,runs):
 n=d['page'];frames=FRAMES[n];d.update(source_language='English',reviewed_initial_prose_reading_order=True,baseline_tolerance_pt=.75,include_image_only_native_math=True)
 d.setdefault('native_move_options',{})['allow_white_background_panels']=True
 recovered=[]
 for s in d['source_line_scopes']:
  if s.get('original_grid_cell_rect')or not any(a<=s['baseline']<=b for a,b in frames):continue
  bi,li=s['source_at'];x=raw['blocks'][bi]['lines'][li]['bbox'][0];y=s['baseline'];cells=[]
  for neighbor in d['source_line_scopes']:
   r=neighbor.get('original_grid_cell_rect')
   if r and r[0]<=x<=r[2]and r[1]<=y<=r[3]and r not in cells:cells.append(r)
  if len(cells)==1:
   r=cells[0];s['original_grid_cell_rect']=r[:];s['original_grid_cell_bounds']=[r[0],r[2]];recovered.append(dict(source_at=s['source_at'],actual_original_cell=r,reason='Actual enclosing source grid already independently resolved on a neighboring line within this exact same cell. The generic65pt rule search missed its distant top edge; this is still the same original content cell, never the adjacent score column.'))
 d['reviewed_recovered_same_original_grading_cells']=recovered
 false=[]
 for s in d['source_line_scopes']:
  if s.get('original_grid_cell_rect')and not any(a<=s['baseline']<=b for a,b in frames):false.append(dict(source_at=s['source_at'],original_false_grid_rect=s['original_grid_cell_rect']));s.pop('original_grid_cell_rect',None);s.pop('original_grid_cell_bounds',None)
 d['reviewed_actual_source_grading_table_y_spans']=frames;d['reviewed_non_table_source_narrative_rows']=false
 # Reconstruct each complete source physical narrative row. Generic detection
 # splits around false math/grid boundaries; those stale fragments cannot
 # define a translated source row. Actual table cells stay separate.
 centered={tuple(s['at'][:2])for s in authored['slots']if s.get('align')=='center'}|{tuple(at[:2])for at in authored.get('centered',[])}
 groups=[]
 for s in d['source_line_scopes']:
  if s['baseline']<60:continue
  if n==6 and s['source_at']==[33,0]:continue # empty translated source trailing fragment; same actual physical row is265.99
  if n==6 and s['source_at']==[31,1]:s['baseline']=260.95001220703125
  cell=s.get('original_grid_cell_rect');key=('cell',tuple(cell))if cell else('center',tuple(s['source_at']))if tuple(s['source_at'])in centered else('narrative',round(s['baseline'],1))
  group=next((v for v in groups if v['key']==key and abs(v['baseline']-s['baseline'])<.1),None)
  if group is None:group=dict(key=key,baseline=s['baseline'],scopes=[]);groups.append(group)
  group['scopes'].append(s)
 rects=[];unions=[]
 for group in groups:
  scopes=group['scopes'];ats=[s['source_at']for s in scopes];old=[s['rect'][:]for s in scopes];cell=scopes[0].get('original_grid_cell_rect')
  if cell:
   left,right=cell[0],cell[2]
  elif any(tuple(at)in centered for at in ats):left=min(r[0]for r in old);right=max(r[2]for r in old)
  else:left=min(raw['blocks'][bi]['lines'][li]['bbox'][0]for bi,li in ats)-.25;right=right_bound(n,ats)
  rect=[left,min(r[1]for r in old),right,max(r[3]for r in old)]
  if rect not in rects:rects.append(rect)
  for s in scopes:s['rect']=rect[:]
  for center in d['centered_lines']+d['right_aligned_lines']:
   if center['rect']in old:center['rect']=rect[:]
  unions.append(dict(source_line_ats=ats,source_physical_baseline=group['baseline'],complete_original_row_rect=rect))
 d['allowed_line_rects']=rects;d['reviewed_original_same_physical_row_scope_unions']=unions;d['original_fixed_header_columns_retained']=True
 # Recompute only real grading-grid locks, excluding actual run-in labels.
 with f.open(d['original_english_source'])as source:
  page=source[n-1];prefix=[g for k in ['reviewed_rubric_prose_prefixes','reviewed_math_font_narrative_literals','reviewed_source_prose_native_reference_glyphs']for row in d.get(k,[])for g in row['source_glyphs']]
  d['stationary_table_math']=stationary_table_math(page,d['source_line_scopes'],page.get_drawings(),prefix)
 if n==5:d['stationary_table_math']=[]
 if n==5:d['reviewed_actual_source_grading_score_column']=dict(original_source_sha256=SOURCE,source_page=5,left=482.35,top=157.,bottom=575.,reason='Full original table visually read. Actual source vertical rule at482.35 separates the entire mathematical Content cell from its two score columns. Native4 and periods at463/474 are formula14/16 content, not grading entries; every such math glyph remains in strict original native ink/script/complete expression geometry checks.')
 apply_reviewed_counters(d)
 atoms(d,authored,raw,runs)
 if n==4:
  with f.open(d['original_english_source'])as source:gs=[g for g in _traces(source[n-1])if g['c'].strip()and 140<g['origin'][0]<350 and 270<g['origin'][1]<290]
  assert len(gs)==28;d['reviewed_stationary_expression_groups']=[dict(label='Full original stationary displayed equation4. Its native superscript2 belongs to its own x0 base, not the prose reference(1) above. All28 native glyphs remain independently checked.',glyphs=gs)]

if __name__=='__main__':
 assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
 numbers=list(map(int,sys.argv[1:]))or list(range(1,12));folder=B/'2015/native-baseline';pages=[folder/f'page{n:02}.pdf'for n in range(1,12)]
 assert all(p.exists()and p.with_suffix('.qa.json').exists()for p in pages),'All11 independently checked baselines are required'
 version=hashlib.sha256(''.join(sha(p)for p in pages).encode()).hexdigest()[:12];output=folder/f'IZhO_2015_TS_native-baseline-11p-{version}.pdf'
 if not output.exists():
  with pikepdf.Pdf.new()as doc:
   for page in pages:
    with pikepdf.open(page)as one:doc.pages.append(one.pages[0])
   doc.save(output,compress_streams=False)
 (folder/'edition-input.json').write_text(json.dumps(dict(year=2015,kind='TS',pdf=str(output),sha256=sha(output)),indent=2)+'\n','utf8')
 for n in numbers:
  with page_worker():
   path=prepare(2015,'TS',selected_pages={n})[0];d=json.loads(path.read_text('utf8'));assert d['original_english_source_sha256']==SOURCE
   authored=json.loads((B/f'2015/original_style/page{n}.json').read_text('utf8'))
   with f.open(d['original_english_source'])as source:raw=source[n-1].get_text('rawdict');runs=runs_of(source[n-1])
   clean(d,authored,raw,runs);path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
  print('PREPARED_ORIGINAL2015_COMPLETE_NATIVE_EXPRESSION_SCOPES',n,len(d['explicit_native_math_atoms']),flush=True)

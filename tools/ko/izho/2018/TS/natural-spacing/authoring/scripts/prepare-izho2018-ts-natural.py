from pathlib import Path
import json,hashlib,sys,os,re,pikepdf,pymupdf as f
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from izho_natural_spacing_rebuild import prepare,stationary_table_math
from izho_initial_fixed_style import runs_of,slot_source
from izho_2018_equation_counters import apply_reviewed_counters
from pdf_native_inline_reposition import inspect_inline_groups,_traces
from pdf_original_text_ops import glyph_key
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
SOURCE='f338dd0093628b658df3f02ca40a34b97e6ecd8fa431cf8517f08aa4eb14ff49'
FRAMES={1:[],2:[[270,780]],3:[[71,127],[540,724]],4:[],5:[[71,337]],6:[],7:[[500,790]],8:[[70,670]],9:[],10:[],11:[],12:[],13:[[216,780]],14:[[71,785]],15:[[71,720]]}
# Source original Forms named from all15 visually read pages; display-only multirow math stays stationary.
INLINE_FORMS={1:{650:163.4599609375,920:223.219970703125,994:223.219970703125,1674:370.8499755859375,1918:415.72998046875,2836:703.4199829101562},4:{291:94.5799560546875,792:326.0899658203125,1206:370.489990234375},10:{1453:426.52996826171875}}
def right_bound(n,ats):
 if n==1:
  if all(bi==4 or (bi==5 and li==17)or(bi==5 and li==18)or(bi==6 and li==12)for bi,li in ats):return 475.
  if all(bi==12 or(bi==13 and li in[13,14,15])or bi==18 for bi,li in ats):return 448.
  if all(bi==41 or bi==45 for bi,li in ats):return 448.
 if n==3 and all(bi in[3,4]or(bi==5 and li in[5,6])for bi,li in ats):return 555.94
 if n==4 and all((bi==3 and li in[1,2])or(bi==4 and li in[15,16,37])or bi==11 for bi,li in ats):return 480.
 return 555.94
def native_match(g,rows):
 hits=[h for h in rows if h['c']==g['c']and h['font']==g['font']and h['trace_gid']==g['trace_gid']and abs(h['size']-g['size'])<.0001 and max(abs(a-b)for a,b in zip(h['origin'],g['origin']))<.0001 and all(h.get(k)==g.get(k)for k in ['render_mode','color','opacity','linewidth','direction','stroke_color','stroke_opacity','wmode','colorspace'])]
 if len(hits)!=1:raise ValueError(('Original physical glyph must match uniquely',g,len(hits)))
 return hits[0]
def atoms(d,authored,raw,runs):
 n=d['page'];orig=Path(d['original_english_source']);original_inv=json.loads((B/f'2018/inspection/page{n:02}-original-native-inline-inventory.json').read_text('utf8'));initial=inspect_inline_groups(d['source_base'],n)
 with f.open(orig)as source:original_rows=_traces(source[n-1])
 with f.open(d['source_base'])as base:initial_rows=_traces(base[n-1])
 erased={glyph_key(g)for s in authored['slots']for g in slot_source(s,runs)[1]}
 original_rows=[g for g in original_rows if g['c'].strip()and glyph_key(g)not in erased]
 out=[];evidence=[];claimed=set();frozen=[]
 labels=[(r['origin'][1],at)for at,r in runs.items()if re.match(r'Formula \(\d+\)',r['text'])or r['text'].strip()=='Numerical value']
 for form in original_inv['forms']:
  path=form['path'];box=f.Rect(form['native_page_bbox']);baseline=INLINE_FORMS.get(n,{}).get(path[0])if len(path)==1 else None
  if baseline is None and any(a<=box.y0<=b for a,b in FRAMES[n]):
   choices=[(y,at)for y,at in labels if box.y0<=y<=box.y1 and runs[at]['origin'][0]<box.x0]
   if len(choices)==1:baseline=choices[0][0]
  if baseline is None:
   frozen.append(list(box+(-.05,-.05,.05,.05)));continue
  form_keys={glyph_key(g)for g in form['glyphs']if g['c'].strip()};gs=[g for g in original_rows if glyph_key(g)in form_keys];wanted={glyph_key(g)for g in gs};assert len(wanted)==len(form_keys),(n,path,len(wanted),len(form_keys));assert not(wanted&claimed)
  hits=[v for v in initial['forms']if v['original_raw_sha256']==form['original_raw_sha256']and max(abs(a-b)for a,b in zip(v['native_page_bbox'],form['native_page_bbox']))<.001 and{glyph_key(g)for g in v['glyphs']if g['c'].strip()}=={glyph_key(native_match(g,initial_rows))for g in gs}]
  assert len(hits)==1,(n,path,len(hits));actual=hits[0];r=f.Rect(actual['native_page_bbox'])
  for g in actual['glyphs']:
   if g['c'].strip():r|=f.Rect(g['bbox']);r.include_point(f.Point(g['origin']))
  rule=dict(reviewed=True,original_source_only=True,rect=list(r+(-.001,-.001,.001,.001)),font_regex='.*',baseline=baseline,source_native_glyphs=[native_match(g,initial_rows)for g in gs],include_zero_height_vector_bounds=True,source_form_path=actual['path'],source_form_bbox=actual['native_page_bbox'],reason='All original2018 source pages visually read. This exact entire original MathType Form is one run-in phrase in the same original physical prose/table-content row. Preserve literal native glyphs/fonts/GIDs/fractional points/paint/Y and full fraction/root rules/clip/background; one common horizontal dx packs it with Korean prose. Separate display rows/counters/score cells/grid retain original positions.')
  entry=dict(reviewed_rect=list(box),logical_prose_baseline=baseline,original_glyphs=gs,original_form=form,initial_form_path=actual['path'],native_program='complete original source2018 MathType Form')
  # A surrounding repeated Word clip, when uniquely containing exactly the full expression, also travels intact.
  keys={glyph_key(g)for g in rule['source_native_glyphs']};clips=[v for v in initial['clip_groups']if v.get('known_rectangular_clips')and len(v['clip_rects'])==1 and f.Rect(v['clip_rects'][0]).height<90 and{glyph_key(g)for g in v['glyphs']if g['c'].strip()}==keys]
  if clips:
   complete=min(clips,key=lambda v:v['operator_indices'][0]);rule.update(rect=complete['clip_rects'][0],use_complete_original_clip=True,source_complete_clip_operator_indices=complete['operator_indices']);entry['initial_complete_original_invocation_clip']=complete
  out.append(rule);evidence.append(entry);claimed|=wanted
 # Native Word/Cambria grading rows have one actual original content cell,
 # unlike the independently invoked MathType Forms above. Use the complete
 # original row clip only where its remaining native reference+formula form
 # one physical phrase. Every enclosed original fraction rule travels with it.
 if n in [3,5,7,8]:
  candidate_rows=[]
  for scope in d['source_line_scopes']:
   cell=scope.get('original_grid_cell_rect');baseline=scope['baseline']
   if not cell or cell[0]>150 or cell[2]<450 or not any(a<=baseline<=b for a,b in FRAMES[n]):continue
   if n==3 and baseline<540:continue
   if n==5 and not any(abs(baseline-y)<.01 for y in [213.01995849609375,295.969970703125]):continue
   if n==7 and abs(baseline-712.5399780273438)<.01:continue
   if any(abs(baseline-y)<.01 for y in candidate_rows):continue
   candidate_rows.append(baseline)
   candidates=[]
   for clip in initial['clip_groups']:
    if not clip.get('known_rectangular_clips')or len(clip['clip_rects'])!=1:continue
    cr=f.Rect(clip['clip_rects'][0]);gs0=[g for g in clip['glyphs']if g['c'].strip()]
    if not gs0 or cr.height>45 or cr.width<200 or not(cr.y0<baseline<cr.y1)or abs(cr.x0-cell[0])>1 or abs(cr.x1-cell[2])>1:continue
    if any('Noto'in g['font']for g in gs0):continue
    keys={glyph_key(g)for g in gs0}
    if keys&claimed:continue
    original_match=[]
    for g in gs0:
     hits=[h for h in original_rows if h['c']==g['c']and h['font']==g['font']and h['trace_gid']==g['trace_gid']and abs(h['size']-g['size'])<.0001 and max(abs(a-b)for a,b in zip(h['origin'],g['origin']))<.0001]
     if len(hits)!=1:break
     original_match.append(hits[0])
    if len(original_match)!=len(gs0):continue
    candidates.append((len(keys),clip,gs0,original_match))
   if not candidates:continue
   _,clip,gs0,gs=max(candidates,key=lambda v:(v[0],-v[1]['operator_indices'][0]));cr=clip['clip_rects'][0]
   # Header/total labels contain no actual equation. A table scoring number
   # cannot enter a content-cell profile because its native clip is separate.
   if not any('Math'in g['font']or '='in g['c']or g['size']<10 for g in gs):continue
   paths=[v for v in original_inv['vector_paths']if f.Rect(cr).contains(f.Rect(v['rect']))]
   rule=dict(reviewed=True,original_source_only=True,rect=cr,font_regex='.*',baseline=baseline,source_native_glyphs=gs0,include_zero_height_vector_bounds=True,use_complete_original_clip=True,source_complete_clip_operator_indices=clip['operator_indices'],reason='Full original2018 grading content row visually read: exact complete original Word clip contains the original equation-reference glyphs and the entire following mathematical expression, including every fraction/root bar and script. Their source intrinsic gap is retained as one phrase; natural Korean label packs before it. Separate score cells, grids and display equations stay stationary.')
   out.append(rule);evidence.append(dict(reviewed_rect=cr,logical_prose_baseline=baseline,original_glyphs=gs,original_vector_paths=paths,native_program='complete original source2018 native grading-content row clip',initial_complete_clip=clip));claimed.update(glyph_key(g)for g in gs0)
 if n==7:
  # The original row contains TWO mathematical phrases separated by actual
  # English prose. Moving the entire row would strand an English-width hole
  # and put Korean 'or equivalent' after both formulas. Bind each complete
  # original expression separately, retaining every script and its true Y.
  separate=[]
  for box in [[178.,700.,220.,721.],[288.,700.,347.,721.]]:
   gs=[g for g in original_rows if f.Rect(box).contains(f.Point(g['origin']))and 'Math'in g['font']];assert gs
   initial_gs=[native_match(g,initial_rows)for g in gs];paths=[v for v in original_inv['vector_paths']if f.Rect(box).contains(f.Rect(v['rect']))];assert not paths
   rule=dict(reviewed=True,original_source_only=True,rect=box,font_regex='Math',baseline=712.5399780273438,source_native_glyphs=initial_gs,include_zero_height_vector_bounds=True,reason='The original formula9 grading row has gamma=7/5, then English or equivalent, then the separate complete CP=7/2R expression. Each original native expression and all scripts keep exact font/GID/fractional point/paint/Y and one internal common dx; the Korean connective remains BETWEEN these two source phrases. Original mathematical slash codes are literal, not retypeset fractions.')
   out.append(rule);evidence.append(dict(reviewed_rect=box,logical_prose_baseline=712.5399780273438,original_glyphs=gs,original_vector_paths=[],native_program='one complete original native Word inline expression separated from the next expression by source prose'));claimed.update(glyph_key(g)for g in initial_gs)
   separate.append(dict(original_glyphs=gs,source_native_glyphs=initial_gs))
  d['reviewed_source2018_multiple_expression_grading_cell']=dict(source_sha256=SOURCE,source_page=7,source_at=[59,5],actual_original_prose_between='or equivalent ',partitions=separate,all_original_math_glyphs_checked=True)
 if n==6:
  refs=[r for r in d['reviewed_source_prose_native_reference_glyphs']if r['source_at']==[12,10,0]and r['source_text']in['(4)','(12)','(13)']];assert len(refs)==3
  for ref in refs:
   keys={glyph_key(g)for g in ref['source_glyphs']};gs=[g for g in original_rows if glyph_key(g)in keys];assert len(gs)==len(keys);box=f.Rect()
   for g in gs:box|=f.Rect(g['bbox'])
   box=list(box+(-.001,-.001,.001,.001));initial_gs=[native_match(g,initial_rows)for g in gs]
   out.append(dict(reviewed=True,original_source_only=True,rect=box,font_regex='.*',baseline=253.82000732421875,source_native_glyphs=initial_gs,include_zero_height_vector_bounds=True,reason='One literal original native equation reference in a prose list. Original English comma/and separates all three references; each complete encoded(n) phrase packs independently with its corresponding translated Korean conjunction. Never combine two references across intervening authored prose. Original native font/GID/point/paint/Y retained.'))
   evidence.append(dict(reviewed_rect=box,logical_prose_baseline=253.82000732421875,original_glyphs=gs,original_vector_paths=[],native_program='one complete original equation-reference phrase in source prose list'));claimed.update(glyph_key(g)for g in initial_gs)
 moving={glyph_key(g)for rule in out for g in rule['source_native_glyphs']};regions=[]
 for region in d['stationary_table_math']:
  region['native_glyphs']=[g for g in region['native_glyphs']if glyph_key(g)not in moving]
  if region['native_glyphs']:regions.append(region)
 d['stationary_table_math']=regions;d['explicit_native_math_atoms']=out;d['reviewed_independent_original_expression_geometry_profiles']=evidence;d['reviewed_original_math_profile_source_sha256']=SOURCE
 d['reviewed_source_display_only_original_forms']=frozen;d['excluded_figure_rects']+=frozen;d['frozen_display_math_rects']+=frozen
 for r in authored.get('frozen_display_math_rects',[]):
  if n==12 and r==[177.5,72,443,140.5]:
   d['reviewed_superseded_broad_display_rectangle']=dict(rect=r,reason='Exact full original MathType Form rectangles already protect both complete equation38 alternatives. This older broad rectangle extended into the ascender ink of the following translated prose line; remove only that redundant prose-crossing rectangle, never mathematical glyphs or checks. Every original display Form remains exact in separate native-program and independent geometry audits.');continue
  if r not in d['excluded_figure_rects']:d['excluded_figure_rects'].append(r);d['frozen_display_math_rects'].append(r)
 if n==15:
  proof=B/'2018/inspection/page15-original-adjacent-Form-layout-padding.json';padding=json.loads(proof.read_text('utf8'));assert padding['source_sha256']==SOURCE and all(r['nonwhite_pixels']==0 for r in padding['measures'])
  layout=[r[:]for r in d['excluded_figure_rects']];assert len(layout)==1 and 106.2<layout[0][1]<106.3;layout[0][1]=107.
  d['reviewed_layout_figure_rects']=layout;d['reviewed_original_white_Form_boundary_layout_padding']=dict(evidence=str(proof),evidence_sha256=sha(proof),reason='Actual original source boundary strip106.2–107pt is entirely white at4x/8x/12x. Adjacent exact MathType BBoxes and native font metrics overlap by a fraction of a point there; this redundant white padding prevented selection of the COMPLETE first run-in Form and led the generic collector to partial selection, correctly rejected by the guard. Only this layout boundary moves to107; every original complete second display Form glyph, bitmap, raw program, clip and all actual ink stay independently protected at original coordinates by full source rectangles and geometry audits.')
 return original_inv
def clean(d,authored,raw,runs):
 n=d['page'];frames=FRAMES[n];d.update(source_language='English',reviewed_initial_prose_reading_order=True,baseline_tolerance_pt=.75,include_image_only_native_math=True)
 if n==2:
  refs=[r for r in d['reviewed_source_prose_native_reference_glyphs']if r['source_at']==[6,0,0]and r['source_text']=='А2.3'];assert len(refs)==1
  d['section_number_prefixes'].extend(refs[0]['source_glyphs']);d['reviewed_original_subsection_enumerator_spacing']=dict(native_source_identifier='А2.3',source_at=[6,0,0],reason='The following Korean 이 means this system, not a particle attached to the original subsection label. Retain one ordinary quarter-em word space after the entire exact original native identifier; no tracking or math/font change.')
 if n==10:
  policy=B/'2018/inspection/page10-stellar-label-source-measurements.json'
  if policy.exists():d.update(reviewed_bitmap_language_labels=json.loads(policy.read_text('utf8'))['reviewed_bitmap_language_labels'],reviewed_bitmap_source_measurements=str(policy),reviewed_bitmap_source_measurements_sha256=sha(policy))
  clearance=B/'2018/inspection/page10-stellar-label-translation-clearance.json'
  if clearance.exists():d.update(reviewed_bitmap_label_translation_clearance=str(clearance),reviewed_bitmap_label_translation_clearance_sha256=sha(clearance))
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
 apply_reviewed_counters(d)
 atoms(d,authored,raw,runs)
if __name__=='__main__':
 assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
 numbers=list(map(int,sys.argv[1:]))or list(range(1,16));folder=B/'2018/native-baseline';pages=[folder/f'page{n:02}.pdf'for n in range(1,16)]
 assert all(p.exists()and p.with_suffix('.qa.json').exists()for p in pages)
 version=hashlib.sha256(''.join(sha(p)for p in pages).encode()).hexdigest()[:12];output=folder/f'IZhO_2018_TS_native-baseline-15p-{version}.pdf'
 if not output.exists():
  with pikepdf.Pdf.new()as doc:
   for page in pages:
    with pikepdf.open(page)as one:doc.pages.append(one.pages[0])
   doc.save(output,compress_streams=False)
 (folder/'edition-input.json').write_text(json.dumps(dict(year=2018,kind='TS',pdf=str(output),sha256=sha(output)),indent=2)+'\n','utf8')
 for n in numbers:
  with page_worker():
   path=prepare(2018,'TS',selected_pages={n})[0];d=json.loads(path.read_text('utf8'));assert d['original_english_source_sha256']==SOURCE
   authored=json.loads((B/f'2018/original_style/page{n}.json').read_text('utf8'))
   with f.open(d['original_english_source'])as source:raw=source[n-1].get_text('rawdict');runs=runs_of(source[n-1])
   clean(d,authored,raw,runs);path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
  print('PREPARED_ORIGINAL2018_COMPLETE_NATIVE_EXPRESSION_SCOPES',n,len(d['explicit_native_math_atoms']),flush=True)

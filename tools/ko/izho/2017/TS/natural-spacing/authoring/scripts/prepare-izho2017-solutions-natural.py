"""Private source2017 layout review; never regenerates shared/frozen engines."""
from pathlib import Path
import json,hashlib,sys,os,pikepdf,pymupdf as f
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2017-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from izho_natural_spacing_rebuild import prepare,stationary_table_math
from izho_initial_fixed_style import runs_of,slot_source
from izho_2017_equation_counters import apply_reviewed_counters
from pdf_native_inline_reposition import inspect_inline_groups,_traces
from pdf_original_text_ops import glyph_key
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
SOURCE='fb90239d8da3dea3dcfe104551243f444802632a74a47a139374013aa16080f1'
FRAMES={1:[[384,533]],2:[[195,369]],3:[[72,190]],4:[],5:[],6:[[625,785]],7:[[72,774]],8:[[72,219]],9:[],10:[],11:[],12:[[483,766]],13:[[72,774]],14:[[72,703]]}
# Every complete original page was read at144dpi. These are the two native
# Cambria expressions around the explicitly translated conjunction in eq1.
PROFILES={3:[([183,258,247.5,288],274.15),([270.5,258,330,288],274.15),([341.5,547,399.7,572],560.09)],4:[([357,371,364,394],385.32),([103.8,763,169.6,786],777.096)],6:[([407,168,452.2,184.5],179.09),([471.5,168,501.3,184.5],179.09),([261,252,295.8,269],263.11)]}
def right_bound(n,ats):
 if n==3 and all(bi==15 and li in[4,5,7,8]for bi,li in ats):return 355.
 return 555.94
def native_match(g,rows):
 hits=[h for h in rows if h['c']==g['c']and h['font']==g['font']and h['trace_gid']==g['trace_gid']and abs(h['size']-g['size'])<.0001 and max(abs(a-b)for a,b in zip(h['origin'],g['origin']))<.0001 and all(h.get(k)==g.get(k)for k in ['render_mode','color','opacity','linewidth','direction','stroke_color','stroke_opacity','wmode','colorspace'])]
 if len(hits)!=1:raise ValueError(('Original physical glyph must match uniquely',g,len(hits)))
 return hits[0]
def atoms(d,authored,raw,runs):
 n=d['page'];orig=Path(d['original_english_source']);cache=B/f'2017/inspection/page{n:02}-original-native-inline-inventory.json'
 original_inv=json.loads(cache.read_text('utf8'))if cache.exists()else inspect_inline_groups(orig,n)
 if not cache.exists():cache.write_text(json.dumps(original_inv,ensure_ascii=False)+'\n','utf8')
 initial=inspect_inline_groups(d['source_base'],n)
 with f.open(orig)as source:original_rows=_traces(source[n-1])
 with f.open(d['source_base'])as base:initial_rows=_traces(base[n-1])
 erased={glyph_key(g)for s in authored['slots']for g in slot_source(s,runs)[1]}
 original_rows=[g for g in original_rows if g['c'].strip()and glyph_key(g)not in erased]
 profiles=list(PROFILES.get(n,[]));forced_forms={};table_profiles={};forced_table_members={};counter_ys=[g['origin'][1]for row in d['reviewed_stationary_native_equation_counters']for g in row['glyphs']];prose_rows=sorted({round(scope['baseline'],5)for scope in d['source_line_scopes']if scope['baseline']>60})
 # Same-cell run-in grade formulas are complete original mathematical
 # objects, including every native reference, script and line of a system.
 # Their actual grid cell, not an English slot width, defines ownership.
 if n>=6:
  import re
  seen=set()
  for at,run in runs.items():
   if not re.search(r'^(?:Formula|Formulas|Solution|Numerical value|Correct initial)',run['text']):continue
   scopes=[scope for scope in d['source_line_scopes']if scope['source_at']==list(at[:2])];assert len(scopes)<=1,(n,at)
   if not scopes:continue
   scope=scopes[0];cell=scope.get('original_grid_cell_rect')
   if cell is None:
    if not(n==7 and at==(51,4,0)):raise ValueError(('Reviewed grade formula has no physical cell',n,at))
    boundaries=sorted({round((v['rect'][1]+v['rect'][3])/2,4)for v in original_inv['vector_paths']if v['rect'][2]-v['rect'][0]>340 and abs(v['rect'][3]-v['rect'][1])<1.5})
    y=scope['baseline'];cell=[111.76,max(v for v in boundaries if v<y)+.6,457.98,min(v for v in boundaries if v>y)-.6]
    scope['original_grid_cell_rect']=cell[:];scope['original_grid_cell_bounds']=cell[:]
   key=tuple(cell)
   if key in seen:continue
   seen.add(key);box=list(f.Rect(cell)+(.25,-1.5,-.25,1.5))
   if n==7 and at==(51,4,0):
    # The two long formulas are on independent rows below their caption,
    # already at the content-cell left margin. Retain their original
    # display coordinates, while translating the caption/conjunction.
    native=[native_match(g,initial_rows)for g in original_rows if f.Rect(box).contains(f.Point(g['origin']))and g['font']=='Cambria Math']
    assert native;d['stationary_table_math'].append(dict(source_at=list(at[:2]),cell=cell,rect=box,glyphs=len(native),native_glyphs=native,baseline=scope['baseline'],policy='Actual separate multiline mathematical display rows below the translated caption; exact original x/y/fonts/points/rules retained.'))
    d['reviewed_stationary_multiline_grading_display']=dict(source_at=list(at[:2]),rect=box,native_glyphs=len(native),original_coordinates_retained=True)
    d.setdefault('reviewed_stationary_expression_groups',[]).append(dict(label='Complete original standalone mathematical display equations26/27 below the translated grading caption; every native fraction/script remains at original x/y.',glyphs=native))
    continue
   # MathType already provides a complete original Form. Retain that
   # native container instead of translating a larger Word table-row clip.
   original_keys={glyph_key(g)for g in original_rows}
   cell_clips=[c for c in initial['clip_groups']if c.get('known_rectangular_clips')and len(c['clip_rects'])==1 and max(abs(a-b)for a,b in zip(c['clip_rects'][0],cell))<1.]
   # A Word script origin may lie outside the cell while its ascender is
   # intentionally visible through that exact original row clip. Use the
   # original clip program's CID membership, not a glyph-metric cutoff.
   cell_keys={glyph_key(g)for c in cell_clips for g in c['glyphs']if g['c'].strip()and glyph_key(g)in original_keys}
   if not cell_keys:cell_keys={glyph_key(g)for g in original_rows if f.Rect(box).contains(f.Point(g['origin']))}

   references={glyph_key(g)for item in d.get('reviewed_source_prose_native_reference_glyphs',[])for g in item['source_glyphs']}
   body_keys=cell_keys-references
   if any({glyph_key(g)for g in form['glyphs']if g['c'].strip()}==body_keys for form in original_inv['forms']):continue
   if n==6 and at==(65,4,0):
    # The source cell contains two independent complete expressions with
    # an explicitly selected English 'or' BETWEEN them. A cell-wide atom
    # wrongly appends that translated conjunction after both expressions.
    word=runs[(66,1,1)];assert word['text']=='  or  '
    left=word['origin'][0]
    buckets=[{glyph_key(g)for g in original_rows if glyph_key(g)in cell_keys and g['origin'][0]<left}, {glyph_key(g)for g in original_rows if glyph_key(g)in cell_keys and g['origin'][0]>=left}]
    assert all(buckets)and not(buckets[0]&buckets[1])and set.union(*buckets)==cell_keys
    divider=min(g['origin'][0]for g in original_rows if glyph_key(g)in buckets[1])-.001
    for members,subbox in zip(buckets,[[box[0],box[1],divider,box[3]],[divider,box[1],box[2],box[3]]]):
     forced_table_members[len(profiles)]=members;profiles.append((subbox,scope['baseline']))
    d['reviewed_source_formula6_conjunction_reading_order']=dict(source_word_at=[66,1,1],source_word='  or  ',Korean=' 또는 ',two_complete_original_native_expressions=True,original_glyphs_and_fraction_rules_retained=True,common_cell_wide_atom_rejected_by_visual_review=True)
    continue
   forced_table_members[len(profiles)]=cell_keys;table_profiles[len(profiles)]=dict(source_at=list(at[:2]),rect=box,baseline=scope['baseline']);profiles.append((box,scope['baseline']))
 d['reviewed_inline_grading_math_rows']=list(table_profiles.values())
 if n==6 and d.get('reviewed_source_formula6_conjunction_reading_order'):
  d['reviewed_inline_grading_math_rows'].append(dict(source_at=[65,4],complete_original_expression_groups=2,original_native_glyphs=15,reason='Source formula6 contains two complete independent expressions separated by an explicitly translated or. Each complete group has its own strict original glyph/program/rule geometry audit; one common translation for the entire cell is incorrect.'))
 reserved=set()
 for i,(box,_)in enumerate(profiles):reserved|=forced_table_members.get(i,{glyph_key(g)for g in original_rows if f.Rect(box).contains(f.Point(g['origin']))})
 # Bind a complete original native Form, never a redrawn fraction or a
 # glyph-only approximation. Exact original glyph identity links the full
 # source PDF to the independently checked initial page.
 source_forms=sorted(original_inv['forms'],key=lambda form:(len(form['path']),form['native_page_bbox'][1],form['native_page_bbox'][0]))
 for form in source_forms:
  gs=[g for g in form['glyphs']if g['c'].strip()];keys={glyph_key(g)for g in gs};box=form['native_page_bbox']
  if not keys or keys&erased or keys&reserved or box[3]-box[1]>150:continue
  if any(box[1]-.75<=y<=box[3]+.75 for y in counter_ys):continue
  candidates=[y for y in prose_rows if box[1]-.75<=y<=box[3]+.75]
  if not candidates:continue
  baseline=min(candidates,key=lambda y:abs(y-(box[1]+box[3])/2))
  if not keys.issubset({glyph_key(g)for g in original_rows}):continue
  forced_forms[len(profiles)]=form;profiles.append((box,baseline));reserved|=keys
 out=[];evidence=[];claimed=set()
 for profile_index,(box,baseline) in enumerate(profiles):
  rect=f.Rect(box);gs=[g for g in original_rows if rect.contains(f.Point(g['origin']))]
  union_glyphs=None
  if profile_index in forced_table_members:gs=[g for g in original_rows if glyph_key(g)in forced_table_members[profile_index]]
  if profile_index in forced_forms:
   chosen={glyph_key(g)for g in forced_forms[profile_index]['glyphs']if g['c'].strip()};gs=[g for g in original_rows if glyph_key(g)in chosen];assert len(gs)==len(chosen)
  if not gs:raise ValueError(('Empty reviewed original math region',n,box,baseline))
  wanted={glyph_key(g)for g in gs};assert not(wanted&claimed),(n,box)
  # Prefer the complete original Form invocation. Its literal source stream
  # carries every root/fraction rule, clip, intrinsic background and script.
  forms=[v for v in original_inv['forms']if {glyph_key(g)for g in v['glyphs']if g['c'].strip()}==wanted]
  rule=dict(reviewed=True,original_source_only=True,rect=box,font_regex='.*',baseline=baseline,source_native_glyphs=[native_match(g,initial_rows)for g in gs],include_zero_height_vector_bounds=True,reason='Full original2017 source page visually read. One complete original inline mathematical expression shares one horizontal displacement, retaining exact native glyphs/fonts/GIDs/fractional points/paint/Y and every original fraction/root rule. Original source scoring grids and display labels stay stationary; translation and natural quarter-em prose gaps alone change.')
  entry=dict(reviewed_rect=box,logical_prose_baseline=baseline,original_glyphs=gs)
  if n==9 and profile_index in[0,1]:rule['include_original_zero_advance_glyph_origins_in_bounds']=True
  if profile_index in table_profiles:
   initial_wanted={glyph_key(g)for g in rule['source_native_glyphs']}
   clips=[v for v in initial['clip_groups']if v.get('known_rectangular_clips')and len(v['clip_rects'])==1 and{glyph_key(g)for g in v['glyphs']if g['c'].strip()}==initial_wanted]
   if clips:
    clip=min(clips,key=lambda v:v['operator_indices'][0]);rule.update(rect=clip['clip_rects'][0],use_complete_original_clip=True,source_complete_clip_operator_indices=clip['operator_indices'],source_grid_table_math=True)
    entry.update(original_vector_paths=[v for v in original_inv['vector_paths']if f.Rect(clip['clip_rects'][0]).contains(f.Rect(v['rect']))and f.Rect(v['rect']).height<2 and f.Rect(v['rect']).width<f.Rect(clip['clip_rects'][0]).width*.8],native_program='complete original Word content-cell clip, with original native reference and every formula line, script and rule',initial_complete_clip=clip)
   else:
    rule['source_grid_table_math']=True
    entry.update(original_vector_paths=[v for v in original_inv['vector_paths']if rect.contains(f.Rect(v['rect']))and f.Rect(v['rect']).height<2 and f.Rect(v['rect']).width<rect.width*.8],native_program='complete original content-cell mathematical glyphs plus every native fraction/root/vector rule')
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
 canonical=sorted({round(slot_source(slot,runs)[0]['origin'][1],5)for slot in authored['slots']if slot['text'].strip()});adjustments=[]
 for atom in out:
  candidates=[y for y in canonical if abs(y-atom['baseline'])<=.75]
  if candidates:
   actual=min(candidates,key=lambda y:abs(y-atom['baseline']))
   if abs(actual-atom['baseline'])>.001:adjustments.append(dict(previous_generic_scope_baseline=atom['baseline'],actual_original_selected_prose_baseline=actual,original_native_glyph_Y_unmodified=True));atom['baseline']=actual
 d['reviewed_actual_original_prose_row_baselines']=adjustments
 d['explicit_native_math_atoms']=out;d['reviewed_independent_original_expression_geometry_profiles']=evidence
 d['reviewed_original_math_profile_source_sha256']=SOURCE
 return original_inv
def clean(d,authored,raw,runs):
 n=d['page'];frames=FRAMES[n];d.update(source_language='English',reviewed_initial_prose_reading_order=True,baseline_tolerance_pt=.75,include_image_only_native_math=True)
 d.setdefault('native_move_options',{})['allow_white_background_panels']=True
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
 if n==5:d['reviewed_actual_source_grading_score_column']=dict(original_source_sha256=SOURCE,source_page=5,left=482.35,top=157.,bottom=575.,reason='Full original table visually read. Actual source vertical rule at482.35 separates the entire mathematical Content cell from its two score columns. Native4 and periods at463/474 are formula14/16 content, not grading entries; every such math glyph remains in strict original native ink/script/complete expression geometry checks.')
 apply_reviewed_counters(d)
 atoms(d,authored,raw,runs)

if __name__=='__main__':
 assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
 numbers=list(map(int,sys.argv[1:]))or list(range(1,15));folder=B/'2017/native-baseline';pages=[folder/f'page{n:02}.pdf'for n in range(1,15)]
 assert all(p.exists()and p.with_suffix('.qa.json').exists()for p in pages),'All14 independently checked baselines are required'
 version=hashlib.sha256(''.join(sha(p)for p in pages).encode()).hexdigest()[:12];output=folder/f'IZhO_2017_TS_native-baseline-14p-{version}.pdf'
 if not output.exists():
  with pikepdf.Pdf.new()as doc:
   for page in pages:
    with pikepdf.open(page)as one:doc.pages.append(one.pages[0])
   doc.save(output,compress_streams=False)
 (folder/'edition-input.json').write_text(json.dumps(dict(year=2017,kind='TS',pdf=str(output),sha256=sha(output)),indent=2)+'\n','utf8')
 for n in numbers:
  with page_worker():
   path=prepare(2017,'TS',selected_pages={n})[0];d=json.loads(path.read_text('utf8'));assert d['original_english_source_sha256']==SOURCE
   authored=json.loads((B/f'2017/original_style/page{n}.json').read_text('utf8'))
   with f.open(d['original_english_source'])as source:raw=source[n-1].get_text('rawdict');runs=runs_of(source[n-1])
   clean(d,authored,raw,runs)
   if n==4:
    with f.open(d['original_english_source'])as original:gs=[g for g in _traces(original[n-1])if g['c'].strip()and f.Rect(183,488,252,514).contains(f.Point(g['origin']))]
    assert gs;d['reviewed_stationary_expression_groups']=[dict(label='Complete original stationary displayed equation15; numerator rho3 is not a script of the preceding inline prose reference(14)',glyphs=gs)]
   if n==3:
    # Keep both standalone equation expressions exactly at their source
    # coordinates and center the Korean conjunction in its original slot.
    scopes=[v for v in d['source_line_scopes']if v['source_at']==[7,1]];assert len(scopes)==1;scope=scopes[0];old=scope['rect'][:]
    original=runs[(7,1,1)];left=original['origin'][0];right=original['bbox'][2];rect=[left,old[1],right,old[3]];chars=[c for c in original['chars']if c['c'].strip()];word_center=(min(c['bbox'][0]for c in chars)+max(c['bbox'][2]for c in chars))/2
    d['allowed_line_rects']=[rect[:]if v==old else v for v in d['allowed_line_rects']];scope['rect']=rect[:]
    d['centered_lines'].append(dict(baseline=original['origin'][1],center=word_center,rect=rect[:],reviewed_original_source_prose_span=dict(at=[7,1,1],source_text=' and ')))
    native=[g for row in d['reviewed_independent_original_expression_geometry_profiles']if row['reviewed_rect']in[PROFILES[3][0][0],PROFILES[3][1][0]]for g in row['original_glyphs']];assert len(native)==27
    d['stationary_table_math'].append(dict(source_at=[7,1],rect=[183,258,330,288],native_glyphs=native,baseline=274.15,policy='Original displayed equation: mathematical positions, original rules and ancestor clips remain stationary; only the English conjunction is translated in its original physical slot.'))
    d['reviewed_original_display_conjunction_stationary_layout']=dict(source_at=[7,1,1],source_text=' and ',Korean=' 및 ',original_native_mathematics_positions_unchanged=True,original_source_word_slot_center=word_center,full_regular_Hangul_natural_coverage_required=True)
   if n==6:
    original=runs[(57,1,1)];assert original['text']==' and '
    conjunction=[v for v in d['source_line_scopes']if v['source_at']==[57,1]];prefix=[v for v in d['source_line_scopes']if v['source_at']==[53,1]];assert len(conjunction)==len(prefix)==1;old=conjunction[0]['rect'][:];assert prefix[0]['rect']==old
    fixed=[g for region in d['stationary_table_math']for g in region['native_glyphs']if g['c']=='𝐹'and abs(g['origin'][1]-original['origin'][1])<.75];assert fixed
    narrow=[old[0],old[1],min(g['origin'][0]for g in fixed)-.5,old[3]];word=[original['origin'][0],old[1],original['bbox'][2],old[3]]
    d['allowed_line_rects']=[v for v in d['allowed_line_rects']if v!=old]+[narrow,word];prefix[0]['rect']=narrow;conjunction[0]['rect']=word
    chars=[c for c in original['chars']if c['c'].strip()];center=(min(c['bbox'][0]for c in chars)+max(c['bbox'][2]for c in chars))/2
    d['centered_lines'].append(dict(baseline=original['origin'][1],center=center,rect=word,reviewed_original_source_prose_span=dict(at=[57,1,1],source_text=' and ')))
    d['reviewed_original_independent_grade_display_conjunction']=dict(source_at=[57,1,1],original_math_and_grid_positions_retained=True,selected_English_word_center=center,prefix_and_conjunction_remain_separate_source_slots=True)
   path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
  print('PREPARED_ORIGINAL2017_COMPLETE_NATIVE_EXPRESSION_SCOPES',n,len(d['explicit_native_math_atoms']),flush=True)

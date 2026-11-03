from pathlib import Path
from collections import Counter
import sys,json,hashlib,pikepdf,pymupdf as f,re
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions');E=B/'engine';SOURCE='5e83000f5d2abe161186a6f81e5b9cd306a0758d2969744edbfb68fcad413da8';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
sys.path[:0]=[str(E),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from izho_natural_spacing_rebuild import prepare,table_cell_bounds
from izho_2019_ts_equation_counters import apply_reviewed_counters
from pdf_native_inline_reposition import _traces,inspect_inline_groups
from pdf_original_text_ops import glyph_key
from izho_initial_fixed_style import runs_of,slot_source,characters
numbers=set(map(int,sys.argv[1:]));assert numbers
folder=B/'2019/native-baseline';pages=sorted(folder.glob('page??.pdf'));assert len(pages)==12
version=hashlib.sha256(''.join(sha(p)for p in pages).encode()).hexdigest()[:12];output=folder/f'IZhO_2019_TS_native-baseline-12p-{version}.pdf'
with page_worker():
 if not output.exists():
  with pikepdf.Pdf.new()as doc:
   for item in pages:
    with pikepdf.open(item)as one:doc.pages.append(one.pages[0])
   doc.save(output,compress_streams=False)
(folder/'edition-input.json').write_text(json.dumps(dict(year=2019,kind='TS',pdf=str(output),sha256=sha(output)),indent=2)+'\n','utf8')
frames={1:[[480,614]],2:[[365,480],[750,785]],3:[[60,191]],4:[],5:[],6:[[140,785]],7:[[60,441]],8:[],9:[],10:[],11:[[110,775]],12:[[60,573]]}
def cap(n,y):
 if n==2 and 637<=y<=708:return 490.5
 if n==7 and 491<=y<=572:return 462.4
 if n==8 and 108<=y<=213:return 473.3
 if n==8 and 396<=y<=452:return 482.65
 return 558.0
def cache_inv(n,source,number,label):
 p=B/f'2019/inspection/page{n:02}-{label}-native-groups.json'
 if p.exists():
  v=json.loads(p.read_text('utf8'))
  assert v.pop('_input_sha256',sha(source))==sha(source)
  return v
 with page_worker():v=inspect_inline_groups(str(source),number)
 p.write_text(json.dumps(dict(v,_input_sha256=sha(source)),ensure_ascii=False,indent=2),'utf8');return v
for n in numbers:
 prior=B/f'natural/2019/TS/plans/page{n:02}.json'
 if prior.exists():
  h=prior.parent/'history'/sha(prior);h.mkdir(parents=True,exist_ok=True);target=h/prior.name
  if target.exists():assert target.read_bytes()==prior.read_bytes()
  else:target.write_bytes(prior.read_bytes())
with page_worker():paths=prepare(2019,'TS',selected_pages=numbers)
for path in paths:
 d=json.loads(path.read_text('utf8'));n=d['page'];d.update(source_language='English',reviewed_initial_prose_reading_order=True,baseline_tolerance_pt=.75,include_image_only_native_math=True)
 d.setdefault('native_move_options',{})['allow_white_background_panels']=True
 with f.open(d['original_english_source'])as doc:
  page=doc[n-1];raw=page.get_text('rawdict');runs=runs_of(page);rows=_traces(page);drawings=page.get_drawings()
 authored=json.loads((B/f'2019/original_style/page{n}.json').read_text('utf8'));selected_keys={glyph_key(g)for s in authored['slots']for g in slot_source(s,runs)[1]if g['c'].strip()};original_keys={glyph_key(g)for g in rows if g['c'].strip()}
 centered_ats={tuple(at[:2])for at in authored['centered']}|{tuple(s['at'][:2])for s in authored['slots']if s.get('align')=='center'}
 d['original_fixed_header_columns_retained']=True;physical=[]
 for scope in d['source_line_scopes']:
  y=scope['baseline'];table=any(a<=y<=b for a,b in frames[n]);scope['reviewed_original_true_grading_table']=table
  if not table:scope.pop('original_grid_cell_rect',None);scope.pop('original_grid_cell_bounds',None)
  if y<60 or tuple(scope['source_at'])in centered_ats:continue
  group=next((g for g in physical if abs(g['y']-y)<.12 and g['table']==table),None)
  if group is None:group=dict(y=y,table=table,scopes=[]);physical.append(group)
  group['scopes'].append(scope)
 for group in physical:
  scopes=group['scopes'];y=group['y'];left=min(raw['blocks'][s['source_at'][0]]['lines'][s['source_at'][1]]['bbox'][0]for s in scopes)-.25;right=cap(n,y)
  if n==9 and abs(y-293.33)<.02:left=71.774
  if group['table']:
   cell=table_cell_bounds(drawings,117.86 if n in[6,7,11,12]else 80,y);assert cell,(n,y);right=cell[1]
  merged=[left,min(s['rect'][1]for s in scopes),right,max(s['rect'][3]for s in scopes)]
  for s in scopes:s['rect']=merged[:]
 d['allowed_line_rects']=[]
 for s in d['source_line_scopes']:
  if s['baseline']>60 and s['rect']not in d['allowed_line_rects']:d['allowed_line_rects'].append(s['rect'][:])
 if n in[7,12]:
  at=(41,6,0)if n==7 else(41,0,0);gs=[g for g in characters(runs[at])if g['c'].strip()];y=runs[at]['origin'][1];scope=next(s for s in d['source_line_scopes']if s['source_at']==list(at[:2]));d['centered_lines'].append(dict(baseline=y,center=(min(g['bbox'][0]for g in gs)+max(g['bbox'][2]for g in gs))/2,rect=scope['rect'][:],reason='Full source visual: Total is centered in the narrow original Part cell, unlike left-aligned Total in the earlier full-width content cells. Preserve original nonspace center.'))
 d['reviewed_actual_source_grading_table_y_spans']=frames[n]
 # These are actual separate source score columns, not mathematical objects
 # in the run-in content cell. Authored English headings are explicitly absent.
 scoreleft=458.2 if n in[6,7,11,12]else 462.0
 scores=[g for g in rows if g['c'].strip()and glyph_key(g)not in selected_keys and g['origin'][0]>=scoreleft and any(a<=g['origin'][1]<=b for a,b in frames[n])]
 parts=[g for g in rows if g['c'].strip()and glyph_key(g)not in selected_keys and 66<g['origin'][0]<112.6 and any(a<=g['origin'][1]<=b for a,b in frames[n])]if n in[6,7,11,12]else[]
 d['stationary_table_math']=[dict(rect=[scoreleft,60,560,790],native_glyphs=scores+parts,reviewed=True,reason='Full original2019 source table read: genuine distinct score/subtotal and Part columns retain exact source native font/GID/point/paint/x/y. English selected headings are not stationary native glyphs.')]
 apply_reviewed_counters(d)
 original_inv=cache_inv(n,Path(d['original_english_source']),n,'original');inv=cache_inv(n,Path(d['source_base']),n,'combined-baseline')
 original_forms=original_inv['forms'];atoms=[];claimed=set();bindings=[];clipbindings=[];inline_rows=[]
 for group in physical:
  if not group['table']:continue
  y=group['y'];left=112 if n in[6,7,11,12]else 66;right=458.38 if n in[6,7,11,12]else 462.22
  cc=[c for c in inv['clip_groups']if c.get('known_rectangular_clips')and len(c['clip_rects'])==1 and abs(c['clip_rects'][0][0]-left)<2 and abs(c['clip_rects'][0][2]-right)<2 and c['clip_rects'][0][1]<y<c['clip_rects'][0][3]and f.Rect(c['clip_rects'][0]).height<100 and any(g['c'].strip()for g in c['glyphs'])and all(glyph_key(g)in original_keys for g in c['glyphs']if g['c'].strip())]
  if not cc:continue
  c=min(cc,key=lambda v:(-sum(bool(g['c'].strip())for g in v['glyphs']),v['operator_indices'][0]));gs=[g for g in c['glyphs']if g['c'].strip()];keys={glyph_key(g)for g in gs}
  if keys&claimed:continue
  claimed.update(keys);atom=dict(rect=c['clip_rects'][0],baseline=y,font_regex='.*',source_native_glyphs=gs,original_source_only=True,include_zero_height_vector_bounds=True,source_grid_table_math=True,use_complete_original_clip=True,source_complete_clip_operator_indices=c['operator_indices'],reviewed=True,reason='Full original2019 source rubric visually read. Complete original OUTER Word content-row clip binds native reference/numerals and every complete formula CID/script/fraction/root/overbar path to one common horizontal dx after the Korean label. Exact source raw clip and original operator indices pinned; original clipping/paint/fonts/GIDs/physicalpoints/Y/relative math geometry preserved. Genuine score and Part columns remain fixed, no fitting or math retyping.');atoms.append(atom)
  clipbindings.append(dict(baseline=y,source_clip=c['clip_rects'][0],outer_original_operator_indices=c['operator_indices'],complete_original_native_glyphs=len(gs)))
  inline_rows.extend(dict(source_at=s['source_at'],reason='Full original source review: same physical row inside same content cell, complete native formula and original reference pack with Korean prose while score/Part columns remain fixed.')for s in group['scopes'])
 # Exact original MathType Form invocations in actual translated prose rows.
 # Their native programs carry all fraction rules and internal white panels.
 for form in sorted(inv['forms'],key=lambda v:(-len(v['glyphs']),len(v['path']))):
  gs=[g for g in form['glyphs']if g['c'].strip()];keys={glyph_key(g)for g in gs}
  if not keys or keys&claimed or not keys<=original_keys:continue
  matches=[v for v in original_forms if v['original_raw_sha256']==form['original_raw_sha256']and max(abs(a-b)for a,b in zip(v['native_page_bbox'],form['native_page_bbox']))<.001]
  if not matches:continue
  choices=[g for g in physical if any(z['size']>=9 and abs(z['origin'][1]-g['y'])<4.5 for z in gs)and f.Rect(form['native_page_bbox']).x0>=min(s['rect'][0]for s in g['scopes'])-1 and f.Rect(form['native_page_bbox']).x1<=max(s['rect'][2]for s in g['scopes'])+1]
  if n==8 and abs(form['native_page_bbox'][1]-642.6599146605563)<.001 and any(abs(form['native_page_bbox'][0]-x)<.001 for x in[113.11,376.60997285559586]):
   # The actual numerator/denominator baselines are654.158/671.211,
   # while the surrounding prose is662.14. This reviewed complete original
   # fraction cannot be inferred from a single glyph baseline.
   choices=[g for g in physical if abs(g['y']-662.14)<.02];assert len(choices)==1
  if not choices:continue
  group=min(choices,key=lambda g:min(abs(z['origin'][1]-g['y'])for z in gs if z['size']>=9));y=group['y'];bb=form['native_page_bbox'];rect=[min(bb[0],min(g['origin'][0]for g in gs))-.01,min(bb[1],min(g['origin'][1]for g in gs))-.01,max(bb[2],max(g['origin'][0]for g in gs))+.01,max(bb[3],max(g['origin'][1]for g in gs))+.01]
  atom=dict(rect=rect,baseline=y,font_regex='.*',source_native_glyphs=gs,original_source_only=True,include_zero_height_vector_bounds=True,source_grid_table_math=group['table'],source_form_path=form['path'],source_form_bbox=bb,reviewed=True,reason='Full original2019 source prose physically read. Complete original MathType Form invocation in this exact physical prose row, with all native fonts/GIDs/fractional Tf/Tm/paint/point/Y and internal fraction/root/overbar/rule/white-panel programs, moves by one common dx. Exact original Form raw program and source bbox independently match; no math retyping or synthetic clip.');atoms.append(atom);claimed.update(keys)
  bindings.append(dict(rect=rect,path=form['path'],original_form_bbox=bb,original_form_program_sha256=form['original_raw_sha256'],complete_native_glyph_set=True,original_official_source_program_and_bbox_match=True))
 # Explicit source runs for every direct-Cambria narrative expression on
 # pages1–5. These are human-read source spans, not a font/math classifier.
 bare={
  1:[(['5,11,1'],219.14,'unwound thread length l')],
  2:[(['18,52,1'],515.59,'active resistance R'),(['18,52,3'],515.59,'reactance X'),(['29,0,0','30,0,0','30,0,1'],662.02,'complete 1/(omega C)=omega L fraction'),(['30,0,3','31,0,0','32,0,0','32,0,1','32,0,2','32,0,3','32,0,4','32,0,5'],662.02,'complete L=1/(omega2 C)=1.00e-2 Hn fraction'),(['32,2,1','32,2,2','32,2,3'],693.46,'inductance numerical value and native Hn')],
  3:[(['9,1,2'],242.78,'point charge q'),(['12,0,1'],278.81,'fictitious charge Q'),(['21,10,1'],380.81,'eliminated y'),(['32,5,1'],511.99,'complete interval x in (-R,R)'),(['32,6,1'],526.03,'linear x term'),(['53,2,1','53,2,2'],778.18,'complete Wq with native q script'),(['53,2,4'],778.18,'point charge q'),(['53,2,6','53,2,7'],778.18,'complete WQ with native Q script')],
  4:[(['1,0,1','1,0,2'],80.88,'complete interaction energy WQq'),(['1,0,4'],80.88,'point charge q'),(['10,2,1'],242.78,'complete interior-radius r<R condition'),(['22,1,0'],388.61,'native vector r as printed'),(['22,4,1','22,4,2','22,4,3'],430.25,'complete r-plus vector and all native arrow continuations'),(['22,4,5','22,4,6','22,4,7'],430.25,'complete r-minus vector and all native arrow continuations'),(['34,0,1'],535.99,'center-displacement vector a as printed'),(['35,10,1'],633.1,'thin-layer delta'),(['35,11,1'],647.26,'angle theta'),(['35,11,3'],647.26,'small center displacement a'),(['36,9,1'],675.34,'surface angle theta')],
  5:[(['5,10,2'],144.74,'ring electric field E'),(['10,9,1'],278.21,'ring electric field E'),(['10,10,1'],292.25,'axial distance z'),(['10,11,1','10,11,2'],306.29,'complete element charge Delta q_i with native i script'),(['43,0,1'],661.3,'small equilibrium displacement x')],
  9:[(['12,26,1'],279.53,'complete excited-state molecule count n gamma V')],
 }
 barebindings=[]
 for ats,y,label in bare.get(n,[]):
  selected=[g for at in ats for g in characters(runs[tuple(map(int,at.split(',')))])if g['c'].strip()];sourcebox=f.Rect()
  for g in selected:sourcebox|=f.Rect(g['bbox'])
  # MuPDF rawdict attaches combining-arrow offsets to logical characters;
  # physical texttrace reports the actual original repeated arrow CIDs.
  # Select the original physical CIDs in the exact reviewed source envelope
  # and require identical character/font/point multiplicities, never offset
  # a rawdict arrow or manufacture a combining mark.
  expected=Counter((g['c'],g['font'],round(g['size'],5))for g in selected);gs=[g for g in rows if g['c'].strip()and(sourcebox+(-.001,-.001,.001,.001)).contains(f.Point(g['origin']))and(g['c'],g['font'],round(g['size'],5))in expected];assert Counter((g['c'],g['font'],round(g['size'],5))for g in gs)==expected,(n,label,expected,gs)
  keys={glyph_key(g)for g in gs};assert not keys&claimed,(n,label)
  box=f.Rect()
  for g in gs:box|=f.Rect(g['bbox'])
  rect=list(box+(-1,-1,1,1))
  if n==2 and y==662.02:rect=[164,647,209,671]if len(ats)==3 else[263,647,394,671]
  atoms.append(dict(rect=rect,baseline=y,font_regex='.*',source_native_glyphs=gs,original_source_only=True,include_zero_height_vector_bounds=True,source_grid_table_math=False,reviewed=True,reason='Full original2019 source prose visually read. Exact manually selected source runs: '+label+'. Every original native CID/GID/font/fractional point/paint/Y, script/combining-arrow continuation and contained original fraction rule moves by one common dx. All adjacent English prose explicitly excluded by exact run selection; genuine separate expressions remain separate. No math retyping, fitting or clipping/threshold changes.'));claimed.update(keys);barebindings.append(dict(source_ats=ats,baseline=y,label=label,rect=rect,native_glyphs=len(gs)))
 d['reviewed_exact_direct_Cambria_inline_source_runs']=barebindings
 d['reviewed_complete_original_mathematical_form_bindings']=bindings;d['reviewed_complete_original_grading_row_clips']=clipbindings;d['explicit_native_math_atoms']=atoms;d['reviewed_inline_grading_math_rows']=inline_rows
 # Complete original displays are stationary expression ownership groups.
 # This prevents source scripts being falsely paired with a prose reference.
 proseys=sorted({s['baseline']for s in d['source_line_scopes']if s['baseline']>60});groups=[]
 for counter in d['reviewed_stationary_native_equation_counters']:
  y=counter['glyphs'][0]['origin'][1];above=max([z for z in proseys if z<y-1],default=60)+3;below=min([z for z in proseys if z>y+1],default=790)-8
  native=[g for g in rows if g['c'].strip()and above<=g['origin'][1]<=below and 66<=g['origin'][0]<525 and glyph_key(g)not in selected_keys and glyph_key(g)not in claimed]
  if native:groups.append(dict(label=f'Original2019 stationary complete display{counter["number"]} at sourceY{y}. Full original source reviewed, original math scripts/rules and fonts/GIDs/points/paint/x/y remain native.',glyphs=native))
 d['reviewed_stationary_expression_groups']=groups
 # The pure formula rows in the first grading table retain their original
 # centered displays; no translated prose shares those physical formula rows.
 if n==1:
  gs=[g for g in rows if g['c'].strip()and 506<g['origin'][1]<604 and g['origin'][0]<462 and glyph_key(g)not in selected_keys]
  d['stationary_table_math'].append(dict(rect=[66,506,462,604],native_glyphs=gs,reviewed=True,reason='Full original source p1 table: pure formula rows retain original stationary centered geometry.'))
 path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');print('PRIVATE_2019_NATURAL_PLAN',n,'whole_clips',len(clipbindings),'whole_forms',len(bindings),'fixed_scores_parts',len(scores+parts),'stationary_displays',len(groups),flush=True)
assert sha(E/'pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'

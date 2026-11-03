from pathlib import Path
import json,hashlib,sys,pikepdf,pymupdf as f,re
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');OLD=B.with_name('izho2012-complete-solutions');E=B/'engine';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();SOURCE='19f23f790b5dd43bf2303f4b597da862c5d17a0267320fee3cca7f5f015a1df8';numbers=set(map(int,sys.argv[1:]));assert numbers
target=E/'izho_natural_spacing_rebuild.py';text=target.read_text('utf8')
needle="        if year==2012 and kind=='TS'and d['source_sha256']=='41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db':\n            prose_ats="
if needle in text:
 text=text.replace(needle,"        if kind=='TS'and(year,d['source_sha256'])in[(2012,'41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db'),(2016,'"+SOURCE+"')]:\n            prose_ats=");target.write_text(text,'utf8')
ats={1:['20,7,0','25,10,0','30,9,0','34,11,0','40,5,0'],2:['6,8,0','8,9,0','11,10,0','15,22,0','16,24,0','17,17,0','18,24,0','19,14,0'],3:['3,25,0','6,17,0','9,10,0','11,20,0','12,26,0','15,20,0','23,4,0','26,14,0'],4:['13,11,0','19,13,0','21,18,0'],5:['22,15,0','22,28,0','22,40,0','22,55,0','24,9,0','26,10,0','30,7,0'],6:['1,12,0','3,8,0','6,9,0','10,8,0','13,5,0','17,10,0','20,9,0','20,23,0','26,8,0','33,10,0','33,24,0'],7:['1,12,0','10,5,0','12,6,0','14,10,0','20,9,0','24,4,0','25,8,0','25,22,0','27,8,0'],8:[]}
policy=dict(source_sha256=SOURCE,reviewed_display_counter_ats={str(n):[list(map(int,a.split(',')))for a in v]for n,v in ats.items()},excluded_inline_reference=dict(page=4,at=[23,51,0],text='(6)',reason='Rubric prose reference to equation6, on physical source row568.87, not a display counter.'),left_column_display_counter_policy='p2eq4/5 and p3eq8/9 atx390.67 are true source display counters and remain exact.',full_source_visual_review=True)
policy_path=B/'2016/reviewed-equation-counter-policy.json';policy_path.write_text(json.dumps(policy,ensure_ascii=False,indent=2)+'\n','utf8');ph=sha(policy_path)
text=(OLD/'engine/izho_2012_equation_counters.py').read_text('utf8').replace('41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db',SOURCE).replace("g['font']=='CambriaMath'","g['font']=='Times New Roman'")
a=text.index('RANGES=');b=text.index('\nsha=',a);text=text[:a]+"RANGES={1:list(range(1,6)),2:[1,2,3,1,2,3,4,5],3:list(range(6,14)),4:[14,15,16],5:list(range(1,8)),6:list(range(8,19)),7:list(range(19,28)),8:[]}\nPOLICY=Path(__file__).resolve().parents[1]/'2016/reviewed-equation-counter-policy.json'\nPOLICY_SHA="+repr(ph)+text[b:]
text=text.replace(" with f.open(plan['original_english_source'])as doc:"," assert sha(POLICY)==POLICY_SHA\n policy=json.loads(POLICY.read_text('utf8'));assert policy['source_sha256']==plan['original_english_source_sha256']\n reviewed=policy['reviewed_display_counter_ats'][str(plan['source_page'])]\n with f.open(plan['original_english_source'])as doc:",1).replace('   if not m:continue','   if not m or list(at)not in reviewed:continue',1)
(E/'izho_2016_equation_counters.py').write_text(text,'utf8')
sys.path[:0]=[str(E),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from izho_natural_spacing_rebuild import prepare
from izho_2016_equation_counters import apply_reviewed_counters
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
from izho_initial_fixed_style import runs_of,slot_source
folder=B/'2016/native-baseline';pages=sorted(folder.glob('page??.pdf'));assert len(pages)==8
version=hashlib.sha256(''.join(sha(p)for p in pages).encode()).hexdigest()[:12];output=folder/f'IZhO_2016_TS_native-baseline-8p-{version}.pdf'
with page_worker():
 if not output.exists():
  with pikepdf.Pdf.new()as doc:
   for page in pages:
    with pikepdf.open(page)as one:doc.pages.append(one.pages[0])
   doc.save(output,compress_streams=False)
(folder/'edition-input.json').write_text(json.dumps(dict(year=2016,kind='TS',pdf=str(output),sha256=sha(output)),indent=2)+'\n','utf8')
frames={1:[[318,507],[730,785]],2:[[60,105],[289,405]],3:[],4:[[474,756]],5:[[60,351]],6:[],7:[[628,771]],8:[[60,551]]}
def cap(n,y):
 if n==1 and 160<=y<=225:return 414
 if n==2 and y>=575:return 422
 if n==3 and 220<=y<=380:return 422
 if n==3 and 615<=y<=770:return 370
 return 555.94
# Every entry below was read in the full original144dpi page. Bounds enclose a
# complete source expression and its rule primitives; translated prose is
# explicitly excluded by the authored slot glyph set, never a math classifier.
profiles={
1:[([233,185,264,201],195.74,'inline a=R'),([294,282,410,307],295.13,'flight-range expression and pi/2 rule'),([227,401,258,419],411.05,'rubric a=R'),([196,456,203.3,477],468.67,'rubric angle phi'),([265,455,322,480],468.67,'rubric phi=pi/2-alpha including closing parenthesis and rule'),([336,569,377,587],579.91,'inline P0,V0,T0 tuple'),([275,676,333.4,695],687.82,'inline P0V0=RT0')],
2:[([225,74,261,96],84.62,'rubric CV-R'),([277,74,300,96],84.62,'rubric R/2'),([328,302,375,324],313.49,'rubric center potential phi~rho R2'),([110,583,135.3,605],594.19,'inline DeltaUS'),([73,600,89.3,622],611.83,'inline Delta h'),([106,632,168.9,656],643.9,'inline Delta S=2pi R Delta h'),([399,661,425,684],672.7,'inline DeltaUG'),([191,692,208,715],704.02,'inline Delta h'),([354,726,425,750],738.7,'inline Delta m=pi R2 Delta h rho')],
3:[([169,73,196.9,97],85.22,'inline absolute DeltaUS'),([245,73,270.3,98],85.22,'inline DeltaUG'),([128,228,152.2,251],239.9,'inline DeltaUS'),([100,246,115.6,269],257.54,'inline Delta h'),([99,290,164.9,313],302.33,'inline r=R-h tg alpha'),([73,321,98.6,346],333.05,'inline DeltaUG'),([242,339,258.6,362],350.57,'inline Delta h'),([186,480,198.4,503],491.47,'inline h0'),([179,631,205.5,655],643.42,'inline h=0'),([231,622,272.9,663],643.42,'inline h=R/tg alpha complete fraction'),([231,657,285.9,697],676.3,'inline R/(4tg alpha)cos alpha complete fraction'),([301,657,350,697],676.3,'inline h=R/(2tg alpha) complete fraction'),([73,704,152.7,744],723.1,'inline h0>R/(4tg alpha)cos alpha complete fraction'),([233,736,329,777],755.98,'inline R/(4tg alpha)cos alpha=25mm complete fraction')],
4:[([301,501,427,527],513.67,'rubric segment-balance expression'),([179,520,385,545],532.15,'rubric formula4'),([179,539,270,563],551.35,'rubric formula5'),([178,605,258,645],624.94,'rubric formula7 complete fraction'),([179,677,402,707],691.3,'rubric formula8 complete fraction'),([179,704,271,730],716.5,'rubric formula9'),([222,724,350,760],741.7,'rubric formula10 complete fraction')],
5:[([188,73,433,123],93.74,'rubric equation12 nested fractions'),([248,168,316,207],186.98,'rubric root-absence inequality complete fraction'),([260,201,350,226],213.74,'rubric angle numerical inequality'),([200,250,310,283],268.25,'rubric inequality15 complete fraction'),([104,651,216.5,684],666.7,'inline f(q)=R/(U0-q/C(q)) complete nested fraction')],
6:[([423,600,552,631],619.66,'inline I~cos omega t=sin(omega t-pi/2) complete fraction'),([82,638,130,664],652.78,'inline phi=-pi/2 complete fraction')],
7:[([180,641,209,663],653.02,'rubric I=0'),([180,655,255,679],667.66,'rubric C=0.10muF'),([180,670,288,695],682.18,'rubric q=CU0=0.5muCl'),([192,685,231,703],696.82,'rubric t=infinity'),([179,699,254,724],713.14,'rubric U0=q/C+IR complete fraction'),([179,720,217,746],734.26,'rubric I=dq/dt complete fraction'),([185,739,313,771],754.9,'rubric dt=R/(U0-q/C(q))dq=f(q)dq complete nested fraction'),([416,743,455,768],754.9,'rubric final f(q)= continuation')],
8:[([255,96,348,120],108.02,'rubric f(q)=a+bq'),([182,110,254,138],124.46,'rubric a=0.10 ms/muCl complete fraction'),([185,132,261,160],145.7,'rubric b=0.20 ms/(muCl)2 complete fraction'),([185,156,269,182],168.26,'rubric t=aq+bq2/2 complete fraction'),([278,174,340,197],186.02,'rubric t=2.0ms'),([185,194,334,224],209.9,'rubric time interval complete fraction'),([185,237,269,264],250.58,'rubric q=(root(a2+2bt)-a)/b complete root and fraction'),([185,286,234,310],298.61,'rubric phi=-pi/2 complete fraction'),([185,304,270,329],316.49,'rubric UC=5.000V'),([185,321,387,347],334.49,'rubric complete effective-capacitance current expression and all fraction rules'),([305,340,387,365],352.37,'rubric Ceff=0.200muF'),([185,357,239,385],370.01,'rubric XC=1/(omega Ceff) complete fraction'),([185,394,257,433],407.69,'rubric I=deltaU/root(R2+1/(omega2 Ceff2)) complete roots and rules'),([305,434,382,458],445.99,'rubric I=44.7muA'),([185,451,279,478],464.47,'rubric alpha=arctg(1/(omega Ceff R)) complete fraction'),([305,473,433,496],484.15,'rubric alpha=1.11rad=63.4degree'),([185,487,395,509],498.67,'rubric I(t) native function'),([185,501,294,525],513.31,'rubric UC=deltaU sin alpha'),([185,516,455,542],527.83,'rubric UC(t) native function')]
}
for n in numbers:
 prior=B/f'natural/2016/TS/plans/page{n:02}.json'
 if prior.exists():
  archive=prior.parent/'history'/sha(prior);archive.mkdir(parents=True,exist_ok=True);target=archive/prior.name
  if target.exists():assert target.read_bytes()==prior.read_bytes()
  else:target.write_bytes(prior.read_bytes())
with page_worker():paths=prepare(2016,'TS',selected_pages=numbers)
for path in paths:
 d=json.loads(path.read_text('utf8'));n=d['page'];d.update(source_language='English',reviewed_initial_prose_reading_order=True,baseline_tolerance_pt=.75,include_image_only_native_math=True)
 d.setdefault('native_move_options',{})['allow_white_background_panels']=True
 with f.open(d['original_english_source'])as doc:
  page=doc[n-1];raw=page.get_text('rawdict');runs=runs_of(page);rows=_traces(page);drawings=page.get_drawings()
 authored=json.loads((B/f'2016/original_style/page{n}.json').read_text('utf8'));selected_keys={glyph_key(g)for s in authored['slots']for g in slot_source(s,runs)[1]if g['c'].strip()}
 centered_ats={tuple(at[:2])for at in authored['centered']}|{tuple(s['at'][:2])for s in authored['slots']if s.get('align')=='center'}
 d['allowed_line_rects']=[r for r in d['allowed_line_rects']if r[1]>60];d['original_fixed_header_columns_retained']=True
 physical=[];inline_rows=[]
 for scope in d['source_line_scopes']:
  y=scope['baseline'];is_table=any(a<=y<=b for a,b in frames[n]);scope['reviewed_original_true_grading_table']=is_table
  if not is_table:scope.pop('original_grid_cell_rect',None);scope.pop('original_grid_cell_bounds',None)
  if y<60 or tuple(scope['source_at'])in centered_ats:continue
  group=next((g for g in physical if abs(g['y']-y)<.12 and g['table']==is_table),None)
  if group is None:group=dict(y=y,table=is_table,scopes=[]);physical.append(group)
  group['scopes'].append(scope)
 for group in physical:
  scopes=group['scopes'];y=group['y'];oldrects=[s['rect'][:]for s in scopes];left=min(raw['blocks'][s['source_at'][0]]['lines'][s['source_at'][1]]['bbox'][0]for s in scopes)-.25;right=cap(n,y)
  if group['table']:
   # All human-read source rubrics have one content column; its right grid is
   # before the fixed score column. Retain source prose left indent.
   right=491.3 if n==2 and y>290 else 457.85 if n in[4,5,7,8]else 470.3
  merged=[left,min(r[1]for r in oldrects),right,max(r[3]for r in oldrects)]
  d['allowed_line_rects']=[r for r in d['allowed_line_rects']if not any(max(abs(a-b)for a,b in zip(r,old))<.001 for old in oldrects)]+[merged]
  for s in scopes:s['rect']=merged[:]
 d['reviewed_actual_source_grading_table_y_spans']=frames[n]
 # No blanket math freeze inside a run-in content row. Independent explicit
 # atoms below preserve full formulas; every genuine score stays fixed.
 scores=[g for g in rows if g['c'].strip()and glyph_key(g)not in selected_keys and g['origin'][0]>=(491.5 if n==2 and 290<=g['origin'][1]<=405 else 458.1 if n in[4,5,7,8]else 470.5)and any(a<=g['origin'][1]<=b for a,b in frames[n])]
 d['stationary_table_math']=[dict(rect=[458,60,560,800],native_glyphs=scores,reviewed=True,reason='Human-read actual original score and subtotal columns. Every original score glyph retains exact x/y/font/GID/point/paint; separate from the translated content cell.')]
 atoms=[]
 for rect,y,label in profiles[n]:
  rect=rect[:] 
  if n==8 and abs(y-316.49)<.01:rect=[185,310,270,323]
  if n==5 and abs(y-268.25)<.01:rect=[195,247,310,283]
  if n==2 and abs(y-704.02)<.01:rect=[191,692,208,707]
  box=f.Rect(rect);gs=[g for g in rows if g['c'].strip()and box.contains(f.Point(g['origin']))and glyph_key(g)not in selected_keys];assert gs,(n,label)
  table=any(a<=y<=b for a,b in frames[n])
  atoms.append(dict(rect=rect,baseline=y,font_regex='.*',source_native_glyphs=gs,original_source_only=True,include_zero_height_vector_bounds=True,source_grid_table_math=table,reviewed=True,reason='Full original2016 source page visually read: '+label+'. Complete original encoded native expression, including all scripts and every original contained vector fraction/root rule, moves by one common dx. Source font/GID/fractional Tf/Tm/paint/Y and relative geometry preserved; selected authored English prose excluded explicitly. No scaling or math retyping.'))
  if table:
   for s in d['source_line_scopes']:
    if abs(s['baseline']-y)<.15:inline_rows.append(dict(source_at=s['source_at'],reason='Human-reviewed same-cell same-row label+complete native formula; mathematical relative geometry is enforced by explicit native atom and independent actual-output geometry audit.'))
 from pdf_native_inline_reposition import inspect_inline_groups
 with page_worker():inv=inspect_inline_groups(d['source_base'],n)
 form_bindings=[]
 for atom in atoms:
  wanted={glyph_key(g)for g in atom['source_native_glyphs']}
  matches=[v for v in inv['forms']if {glyph_key(g)for g in v['glyphs']if g['c'].strip()}==wanted]
  if len(matches)==1:
   value=matches[0];atom['source_form_path']=value['path'];atom['source_form_bbox']=value['native_page_bbox'];form_bindings.append(dict(rect=atom['rect'],path=value['path'],original_form_bbox=value['native_page_bbox'],original_form_program_sha256=value['original_raw_sha256'],complete_native_glyph_set=True,reason='Complete original mathematical Form invocation carries all internal fraction rules, roots and absolute-value bars as well as its original CIDs; one shared dx.'))
 d['reviewed_complete_original_mathematical_form_bindings']=form_bindings
 d['explicit_native_math_atoms']=atoms;d['reviewed_inline_grading_math_rows']=inline_rows
 # Reconstruct from actual final physical scopes. Generic transitive unions
 # can leave a stale rectangle in allowed_line_rects after a Word source row
 # was split around an equation object; it must not claim that row twice.
 d['allowed_line_rects']=[]
 for s in d['source_line_scopes']:
  if s['baseline']>60 and s['rect']not in d['allowed_line_rects']:d['allowed_line_rects'].append(s['rect'][:])
 # Keep source displays and original figure graphics stationary even where
 # wide original math rows contain no translated prose at all.
 d['stationary_table_math'].extend(dict(rect=rect,native_glyphs=[g for g in rows if g['c'].strip()and f.Rect(rect).contains(f.Point(g['origin']))],reviewed=True,reason='Full source table visual: separate physical display row, not a same-row prose run-in. Exact original equation geometry retained.')for rect in({4:[[116,575,375,612]],5:[[116,299,220,334]],8:[[116,74,193,100]]}.get(n,[])))
 apply_reviewed_counters(d)
 path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
 print('PRIVATE_2016_NATURAL_PLAN_PREPARED',n,'atoms',len(atoms),'fixed_scores',len(scores),flush=True)
assert sha(E/'pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'

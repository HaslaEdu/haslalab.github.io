from pathlib import Path
import json,hashlib,sys,pikepdf,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2013-complete-solutions');OLD=B.with_name('izho2012-complete-solutions');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();source_sha='2804ded48ad009bf58884b871f0f4817c64762b8a0f586e42056908fc4be10f1';numbers=set(map(int,sys.argv[1:]));assert numbers
for name in['izho_natural_spacing_rebuild.py','izho_natural_spacing_qa.py']:
 source=OLD/'engine'/name;target=B/'engine'/name;text=source.read_text('utf8').replace(OLD.as_posix(),B.as_posix()).replace(repr(str(OLD))[1:-1],repr(str(B))[1:-1])
 if name=='izho_natural_spacing_rebuild.py':
  needle="        if year==2012 and kind=='TS'and d['source_sha256']=='41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db':\n            prose_ats="
  replacement="        if kind=='TS'and(year,d['source_sha256'])in[(2012,'41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db'),(2013,'2804ded48ad009bf58884b871f0f4817c64762b8a0f586e42056908fc4be10f1')]:\n            prose_ats="
  assert needle in text;text=text.replace(needle,replacement)
 if target.exists():
  archive=B/'engine/history'/sha(target)[:16];archive.mkdir(parents=True,exist_ok=True);(archive/target.name).write_bytes(target.read_bytes())
 target.write_text(text,'utf8')
text=(OLD/'engine/izho_2012_equation_counters.py').read_text('utf8').replace('41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db',source_sha).replace("g['font']=='CambriaMath'","g['font']=='TimesNewRomanPSMT'")
old="RANGES={1:range(1,5),2:range(1,4),3:[],4:range(1,9),5:[],6:range(1,13),7:range(13,25),8:[25],9:range(1,12),10:range(12,21),11:[21]}";new="RANGES={1:[],2:[],3:[1],4:range(1,12),5:range(12,18),6:range(18,30),7:[],8:range(1,10),9:range(10,20),10:[]}";assert old in text;text=text.replace(old,new);(B/'engine/izho_2013_equation_counters.py').write_text(text,'utf8')
counter=B/'engine/izho_2013_equation_counters.py';text=counter.read_text('utf8');needle='   if not m:continue';assert needle in text;text=text.replace(needle,"   if not m or run['origin'][0]<490:continue");counter.write_text(text,'utf8')
text=(OLD/'engine/izho_2012_inline_clips.py').read_text('utf8').replace('41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db',source_sha).replace('source2012','source2013');(B/'engine/izho_2013_inline_clips.py').write_text(text,'utf8')
sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from izho_natural_spacing_rebuild import prepare
from izho_2013_equation_counters import apply_reviewed_counters
from izho_2013_inline_clips import apply as inline_clips
folder=B/'2013/native-baseline';pages=sorted(folder.glob('page??.pdf'));assert len(pages)==10
version=hashlib.sha256(''.join(sha(p)for p in pages).encode()).hexdigest()[:12];output=folder/f'IZhO_2013_TS_native-baseline-10p-{version}.pdf'
if not output.exists():
 with pikepdf.Pdf.new()as doc:
  for page in pages:
   with pikepdf.open(page)as one:doc.pages.append(one.pages[0])
  doc.save(output,compress_streams=False)
(folder/'edition-input.json').write_text(json.dumps(dict(year=2013,kind='TS',pdf=str(output),sha256=sha(output)),indent=2)+'\n','utf8')
for path in prepare(2013,'TS',selected_pages=numbers):
 d=json.loads(path.read_text('utf8'));d.update(source_language='English',reviewed_initial_prose_reading_order=True,baseline_tolerance_pt=.75,include_image_only_native_math=True)
 d.setdefault('native_move_options',{})['allow_white_background_panels']=True
 with f.open(d['original_english_source'])as source:raw=source[d['source_page']-1].get_text('rawdict')
 from izho_initial_fixed_style import runs_of
 with f.open(d['original_english_source'])as source:runs=runs_of(source[d['source_page']-1])
 headers=[(at,r['origin'][1])for at,r in runs.items()if r['text'].strip()=='Description'];totals=[(at,r['origin'][1])for at,r in runs.items()if r['text'].strip()=='Total'];frames=[]
 for at,y in headers:
  following=[yy for _,yy in totals if yy>y];frames.append([y-12,min(following)+8 if following else 800])
 if totals and not headers:frames.append([60,max(y for _,y in totals)+8])
 false_cells=[]
 for scope in d['source_line_scopes']:
  if scope.get('original_grid_cell_rect')and not any(a<=scope['baseline']<=b for a,b in frames):
   false_cells.append(dict(source_at=scope['source_at'],baseline=scope['baseline'],original_detector_rect=scope['original_grid_cell_rect'],reason='Human-read source2013 physical row is narrative outside every actual grading-table header/Total span. Nearby native math delimiters and fraction rules are not a prose scoring-grid cell.'))
   scope.pop('original_grid_cell_rect',None);scope.pop('original_grid_cell_bounds',None)
 d['reviewed_actual_source_grading_table_y_spans']=frames;d['reviewed_non_table_source_narrative_rows']=false_cells
 # Original9.96pt Arial bold header is already naturally translated in two
 # separate fixed source slots; retain its original left title/right Page
 # column and native page-number position rather than merging those columns.
 d['allowed_line_rects']=[r for r in d['allowed_line_rects']if r[1]>60];d['original_fixed_header_columns_retained']=True
 for rect in d['allowed_line_rects']:
  old=rect[:];scopes=[s for s in d['source_line_scopes']if s['rect']==old];centered=any(c['rect']==old for c in d['centered_lines'])
  if not scopes or centered or any(s.get('original_grid_cell_rect')for s in scopes):continue
  ats=[s['source_at']for s in scopes];rect[0]=min(raw['blocks'][bi]['lines'][li]['bbox'][0]for bi,li in ats)-.25;rect[2]=555.94
  if d['page']==3 and all(bi==4 for bi,li in ats):rect[2]=402.89
  if rect!=old:
   for scope in d['source_line_scopes']+d['centered_lines']+d['right_aligned_lines']:
    if scope.get('rect')==old:scope['rect']=rect[:]
 authored=json.loads((B/f"2013/original_style/page{d['page']}.json").read_text('utf8'));centered_source_ats={tuple(at[:2])for at in authored.get('centered',[])}|{tuple(s['at'][:2])for s in authored['slots']if s.get('align')=='center'}
 physical=[]
 for scope in d['source_line_scopes']:
  if scope['baseline']<60 or scope.get('original_grid_cell_rect')or tuple(scope['source_at'])in centered_source_ats:continue
  group=next((g for g in physical if abs(g['baseline']-scope['baseline'])<.1),None)
  if group is None:group=dict(baseline=scope['baseline'],scopes=[]);physical.append(group)
  group['scopes'].append(scope)
 unions=[]
 for group in physical:
  rects=[]
  for scope in group['scopes']:
   if scope['rect']not in rects:rects.append(scope['rect'][:])
  ats=[s['source_at']for s in group['scopes']];left=min(raw['blocks'][bi]['lines'][li]['bbox'][0]for bi,li in ats)-.25;right=402.89 if d['page']==3 and all(bi==4 for bi,li in ats)else 555.94
  merged=[left,min(r[1]for r in rects),right,max(r[3]for r in rects)]
  midpoint=sum((r[1]+r[3])/2 for r in rects)/len(rects)
  d['allowed_line_rects']=[r for r in d['allowed_line_rects']if abs((r[1]+r[3])/2-midpoint)>=.12]+[merged]
  for scope in group['scopes']:scope['rect']=merged[:]
  unions.append(dict(original_physical_baseline=group['baseline'],source_line_ats=[s['source_at']for s in group['scopes']],original_rectangles=rects,one_original_physical_row_rectangle=merged,reason='Every selected original narrative slot on this physical source row is reachable, including the initial source fragment after the generic transitive-rectangle union. Source Word can split one row around native objects into distinct raw blocks. A single reviewed row scope prevents omission or duplicate glyph claims; original physical baselines and separate scoring-table cells remain unchanged.'))
 d['reviewed_original_same_physical_row_scope_unions']=unions
 apply_reviewed_counters(d);inline_clips(d)
 path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
print('PREPARED_SELECTED_IZHO2013_NATURAL_SOURCE_STYLE_PLANS',sorted(numbers),flush=True)

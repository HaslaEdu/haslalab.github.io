from pathlib import Path
import sys,json,hashlib,pikepdf,re
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from izho_natural_spacing_rebuild import prepare
from pdf_native_inline_reposition import inspect_inline_groups
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
folder=B/'2010/native-baseline';pages=sorted(folder.glob('page??.pdf'));assert pages
selected=set(map(int,sys.argv[1:]))if len(sys.argv)>1 else None
retain={p:p.read_bytes()for p in (B/'natural/2010/TS/plans').glob('page??.json')if selected and int(p.stem[4:])not in selected}
version=hashlib.sha256(''.join(sha(p)for p in pages).encode('ascii')).hexdigest()[:12]
output=folder/f'IZhO_2010_TS_RU_native-baseline-{len(pages)}p-{version}.pdf'
if not output.exists():
 with pikepdf.Pdf.new()as doc:
  for page in pages:
   with pikepdf.open(page)as single:doc.pages.append(single.pages[0])
  doc.save(output,compress_streams=False)
with pikepdf.open(output)as joined:
 assert len(joined.pages)==len(pages)
 for index,page in enumerate(pages):
  with pikepdf.open(page)as single:
   def content(p):
    values=p.Contents;values=list(values)if isinstance(values,pikepdf.Array)else[values]
    return [v.read_bytes()for v in values]
   assert content(joined.pages[index])==content(single.pages[0])
record=output.with_suffix('.component-shas.json');components=dict(pages=[dict(pdf=str(p),sha256=sha(p))for p in pages],joined_sha256=sha(output),all_original_page_content_programs_identical=True)
if record.exists():assert json.loads(record.read_text('utf8'))==components
else:record.write_text(json.dumps(components,ensure_ascii=False,indent=2)+'\n','utf8')
(folder/'edition-input.json').write_text(json.dumps(dict(year=2010,kind='TS',pdf=str(output),sha256=sha(output)),indent=2),'utf8')
for n,pp in enumerate(prepare(2010,'TS'),1):
 d=json.loads(pp.read_text('utf8'));d.update(source_language='Russian',reviewed_initial_prose_reading_order=True,baseline_tolerance_pt=.75,include_image_only_native_math=True)
 for r in d['allowed_line_rects']:
  if r[1]>60:r[0]=max(63.59,r[0]);r[2]=min(558.,r[2])
 if n==1:
  inv=inspect_inline_groups(output,n)
  atoms=[dict(reviewed=True,rect=rect,font_regex='TimesNewRoman',baseline=y,reason='Complete original source formula retains its original glyph offsets, font/point/paint and the unchanged normal-font trigonometric function.')for rect,y in[([282.5,143.,347.5,153.],148.43994140625),([378.5,246.,408.1,256.],251.63995361328125),([433.8,246.,502.7,256.],251.63995361328125)]]
  bindings=[]
  for index,rect,y in [(0,[168.4,155.,212.9,167.],162.5999755859375),(1,[244.9,155.,267.2,167.],162.5999755859375),(3,[331.,275.,336.,284.],279.5999755859375)]:
   image=inv['images'][index]
   atoms.append(dict(reviewed=True,rect=rect,font_regex='TimesNewRoman',baseline=y,source_image_path=image['path'],source_image_sha256=image['original_raw_sha256'],reason='The original encoded equation and adjoining bitmap fraction or squared term move together as one complete mathematical atom; no text/image overlap can move the following prose cursor backwards.'))
   bindings.append(dict(reviewed=True,image_path=image['path'],original_color_stream_sha256=image['original_raw_sha256'],original_image_bbox=image['bbox'],native_glyph_rect=rect,native_font_regex='TimesNewRoman',reason='Independent original bitmap Do CTM and adjoining original equation glyphs must share one horizontal translation.'))
  for atom in atoms:atom['original_source_only']=True
  d.update(explicit_native_math_atoms=atoms,reviewed_sibling_math_image_bindings=bindings)
 if n==2:
  d['explicit_native_math_atoms']=[dict(reviewed=True,original_source_only=True,rect=rect,font_regex='BookmanOldStyle|SymbolMT',baseline=y,reason=reason)for rect,y,reason in[
   ([218.7,332.,269.8,351.],342.8399658203125,'Complete original V(h)<V0 condition, including both enlarged parentheses and the original subscript.'),
   ([226.7,496.,288.1,513.],506.51995849609375,'Complete original density definition rho_0,1=M/V_0,1, including both original small subscripts and native diagonal slash path.'),
   ([281.5,513.,315.1,531.],523.67999267578125,'Complete original rho/rho_max ratio, including the original diagonal division path and all three letters of max.'),
   ([337.1,513.,362.4,531.],523.67999267578125,'Complete original h/H ratio; the original slash is a vector path and moves with its original glyphs.'),
   ([349.5,558.,430.9,596.],578.1599731445312,'Complete original height condition h=H(1-sqrt(V1/V0)), including all stacked bracket glyphs, original root strokes/fill and the original fraction rule.')]]
  # The condition is one source sentence interrupted by a tall MathType
  # object. Its two Word text blocks share one original prose baseline.
  fragments=[r for r in d['allowed_line_rects']if abs(r[1]-567.9599731445312)<.01]
  assert len(fragments)==2,fragments
  d['allowed_line_rects']=[r for r in d['allowed_line_rects']if r not in fragments]+[[63.59,567.9599731445312,558.,583.9199731445312]]
  for scope in d['source_line_scopes']:
   if scope['source_at']in [[52,1],[54,1]]:
    old=scope['rect'][:];new=[old[0],old[1],425.,old[3]]
    scope['rect']=new[:]
    index=next(i for i,r in enumerate(d['allowed_line_rects'])if abs(r[1]-old[1])<.001 and abs(r[3]-old[3])<.001)
    d['allowed_line_rects'][index]=new[:]
 if n==3:
  for scope in d['source_line_scopes']:
   if scope['source_at']==[16,8]:
    old=scope['rect'][:];new=[128.62050018310546,old[1],458.4200042724609,old[3]]
    scope['rect']=new[:]
    index=next(i for i,x in enumerate(d['allowed_line_rects'])if abs(x[1]-old[1])<.001 and abs(x[3]-old[3])<.001)
    d['allowed_line_rects'][index]=new[:]
   if scope['source_text'].startswith('Рис.'):
    old=scope['rect'][:]
    centered=next(x for x in d['centered_lines']if x['rect']==old and abs(x['baseline']-scope['baseline'])<.01)
    new=[centered['center']-32,old[1],centered['center']+32,old[3]]
    scope['rect']=new[:];centered['rect']=new[:]
    index=next(i for i,x in enumerate(d['allowed_line_rects'])if abs(x[1]-old[1])<.001 and abs(x[3]-old[3])<.001)
    d['allowed_line_rects'][index]=new[:]
  d['explicit_native_math_atoms']=[dict(reviewed=True,original_source_only=True,rect=[435.8,503.,446.2,519.6],font_regex='BookmanOldStyle|SymbolMT',baseline=514.199951171875,reason='Complete original rho_1 inline variable retains its original Greek letter, subscript and relative offsets.')]
 if n==4:
  # These are original single prose rows wrapping around the stationary
  # diagram, split into multiple Word runs by inline MathType bitmaps.
  # The complete formula has to fit the same reviewed body column, so that
  # it is packed with the sentence rather than stranded at its old x.
  for y in [194.76,209.04,243.6,277.68,291.48,319.56,356.04,373.8,387.96,401.88,415.68,444.12]:
   scopes=[s for s in d['source_line_scopes']if abs(s['baseline']-y)<.02]
   if not scopes:continue
   old=[r for r in d['allowed_line_rects']if abs(r[1]-(scopes[0]['baseline']-10.2))<.02]
   assert old,(y,scopes)
   new=[63.59,min(r[1]for r in old),299.,max(r[3]for r in old)]
   d['allowed_line_rects']=[r for r in d['allowed_line_rects']if r not in old]+[new]
   for scope in scopes:scope['rect']=new[:]
 rows={
  5:[83.04,235.92,264.48,649.8],
  6:[469.2,565.32,581.88],
  7:[478.68,547.08,579.96,596.76,637.2,667.68,684.,698.16,728.64,759.24],
  8:[83.04,103.08,119.76,154.32,168.48,217.2,235.44,253.56,271.8,290.04,337.8,447.36,463.2,570.96,677.64,725.88,753.96,769.68],
  9:[143.52,241.56,290.16,432.6,462.6,494.76,550.8,564.6,592.56,674.4,703.56,741.72],
  10:[136.56,150.36,240.12,255.84,271.56,287.4,302.76,316.56,330.72,347.4,397.2,411.36,484.8,525.24,605.16,637.2,666.36,680.16,741.84,757.56],
  11:[83.04,112.2,126.,140.16,158.4,176.64,222.,236.16],
 }
 for y in rows.get(n,[]):
  scopes=[s for s in d['source_line_scopes']if abs(s['baseline']-y)<.02]
  if not scopes:continue
  old=[r for r in d['allowed_line_rects']if abs(r[1]-(scopes[0]['baseline']-10.2))<.02]
  assert old,(n,y,scopes)
  new=[63.59,min(r[1]for r in old),558.,max(r[3]for r in old)]
  d['allowed_line_rects']=[r for r in d['allowed_line_rects']if r not in old]+[new]
  for scope in scopes:scope['rect']=new[:]
  d.setdefault('reviewed_complete_prose_rows',[]).append(dict(baseline=scopes[0]['baseline'],source_at=[s['source_at']for s in scopes],rect=new[:],reason='One reviewed original source prose row interrupted by original inline math; same physical baseline and original fixed font sizes, ordinary quarter-em spaces, no source diagram/table columns merged.'))
 if n==9:
  assert not d['frozen_display_math_rects']
  d['reviewed_mathematical_image_invocations']=dict(source_page=9,images=22,inline_indices=[2,6,10,11,14,16,18,20],stationary_display_indices=[0,1,3,4,5,7,8,9,12,13,15,17,19,21],reason='All22 original p9 bitmaps are mathematical expressions, not illustrations. Original adjoining MathType bitmap boxes overlap by0.10-0.15pt. Exact raw image/palette/ICC/mask programs and CTM linear bases/y are checked independently; all14 display objects must keep their complete original CTM, and only8 reviewed complete inline objects may translate horizontally with original prose baselines. No image is resized, retyped or rasterized.')
  d['excluded_figure_rects']=[]
 pp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
for p,raw in retain.items():p.write_bytes(raw)
print('PREPARED_COMPLETE_RUSSIAN_TS',len(pages),'native baseline pages',flush=True)

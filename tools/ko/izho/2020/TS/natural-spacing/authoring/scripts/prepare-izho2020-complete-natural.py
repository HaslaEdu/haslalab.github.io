from pathlib import Path
import sys,json,hashlib,pikepdf
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2020-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from izho_natural_spacing_rebuild import prepare
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
import pymupdf as fitz
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
folder=B/'2020/native-baseline';pages=sorted(folder.glob('page??.pdf'));assert pages
selected=set(map(int,sys.argv[1:]))if len(sys.argv)>1 else None
version=hashlib.sha256(''.join(sha(p)for p in pages).encode()).hexdigest()[:12];output=folder/f'IZhO_2020_TS_native-baseline-{len(pages)}p-{version}.pdf'
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
    values=p.Contents;values=list(values)if isinstance(values,pikepdf.Array)else[values];return[v.read_bytes()for v in values]
   assert content(joined.pages[index])==content(single.pages[0])
(folder/'edition-input.json').write_text(json.dumps(dict(year=2020,kind='TS',pdf=str(output),sha256=sha(output)),indent=2)+'\n','utf8')
for pp in prepare(2020,'TS',selected_pages=selected):
 n=int(pp.stem[4:])
 d=json.loads(pp.read_text('utf8'));d.update(source_language='English',reviewed_initial_prose_reading_order=True,baseline_tolerance_pt=.75,include_image_only_native_math=True)
 for r in d['allowed_line_rects']:
  old_rect=r[:]
  if r[1]>60:r[0]=max(63.59,r[0]);r[2]=min(558.,r[2])
  if r!=old_rect:
   for a in d['centered_lines']+d['right_aligned_lines']+d['source_line_scopes']:
    if a.get('rect')==old_rect:a['rect']=r[:]
 with fitz.open(d['original_english_source'])as original:
  source_native=_traces(original[n-1])
 if n==4:
  for y,label in [(220.92,'1.3.1'),(622.68,'1.3.2')]:
   gs=sorted([g for g in source_native if g['c'].strip()and g['trace_gid']>=0 and abs(g['origin'][1]-y)<.02],key=lambda g:g['origin'][0])[:len(label)]
   assert ''.join(g['c']for g in gs)==label
   d['section_number_prefixes'].extend({k:g[k]for k in ['c','font','size','origin']}for g in gs)
 if n==9:
  logarithm=[g for g in source_native if g['c']in ['l','n']and g['font']=='TimesNewRomanPSMT'and abs(g['origin'][1]-284.88)<.02 and 175<g['origin'][0]<200]
  logarithm.sort(key=lambda g:g['origin'][0]);assert ''.join(g['c']for g in logarithm)=='ln'
  logarithm_region=next(r for r in d['stationary_table_math']if r['source_at']==[25,2]);logarithm_region['native_glyphs'].extend({k:g[k]for k in ['c','font','size','origin']}for g in logarithm);logarithm_region['rect'][0]=min(g['bbox'][0]for g in logarithm)
  for r in d['allowed_line_rects']:
   if abs(r[1]-(284.88-10.2))<.02 and r[0]<170:r[2]=min(r[2],logarithm_region['rect'][0]-.1)
  d['reviewed_mixed_font_mathematical_functions']=[dict(source_at=[25,2],text='ln',glyphs=logarithm,reason='The source natural logarithm is encoded in TNR beside an otherwise CambriaMath expression, within the same run as the prose label. Both original ln glyphs are stationary parts of the complete original mathematical expression, not movable prose-reference text.')]
  region=next(r for r in d['stationary_table_math']if r['source_at']==[3,2]);scope=next(s for s in d['source_line_scopes']if s['source_at']==[3,2]);y=scope['baseline']
  d['stationary_table_math'].remove(region)
  d['allowed_line_rects']=[r for r in d['allowed_line_rects']if not(abs(r[1]-(y-10.2))<.02 and r[0]<460)]+[scope['rect'][:]]
  d['reviewed_inline_grading_math_rows']=[dict(source_at=[3,2],source_text=scope['source_text'],cell=scope['original_grid_cell_rect'],reason='One original prose row contains two separate numerical expressions interrupted by the English word or. Both complete original encoded expressions pack horizontally with the Korean translation at original point sizes/baselines. The table cell, scores, actual expression glyphs and internal geometry are retained; this row is checked by two explicit complete-expression atoms, not treated as one rigid formula across the intervening prose word.')]
  for rect in [[272.6,94.,347.5,113.],[363.4,94.,431.,113.]]:
   d.setdefault('explicit_native_math_atoms',[]).append(dict(reviewed=True,original_source_only=True,rect=rect,font_regex='CambriaMath',baseline=y,reason='One complete original numerical pressure expression, including all encoded variables, equality, digits and atm unit. The two expressions are separated by narrative or and preserve all internal glyph geometry while packing beside its Korean translation.'))
 d['reviewed_stationary_expression_groups']=[]
 prose_prefix_keys={glyph_key(g)for p in d.get('reviewed_rubric_prose_prefixes',[])for g in p['source_glyphs']}
 for index,region in enumerate(d['stationary_table_math'],1):
  keys={glyph_key(g)for g in region['native_glyphs']}
  cell=fitz.Rect(region['cell']);extended=cell+(0,-2.4,0,2.4)
  gs=[g for g in source_native if g['c'].strip()and g['trace_gid']>=0 and glyph_key(g)not in prose_prefix_keys and (glyph_key(g)in keys or(g['font']=='CambriaMath'and extended.contains(fitz.Point(g['origin']))))]
  assert gs
  d['reviewed_stationary_expression_groups'].append(dict(label=f'Original stationary mathematical expression in grading cell{index}, including original fraction-script baselines extending at most2.4pt beyond its grid row; literal prose-label/reference prefix excluded explicitly where present.',glyphs=gs))
 for prefix in d.get('reviewed_rubric_prose_prefixes',[]):
  keys={glyph_key(g)for g in prefix['source_glyphs']if g['c'].strip()and not g['c'].isalpha()}
  gs=[g for g in source_native if glyph_key(g)in keys and g['trace_gid']>=0]
  assert gs and {glyph_key(g)for g in gs}==keys
  rect=[min(g['bbox'][0]for g in gs)-.01,min(g['bbox'][1]for g in gs)-.01,max(g['bbox'][2]for g in gs)+.01,max(g['bbox'][3]for g in gs)+.01]
  row_baseline=next(s['baseline']for s in d['source_line_scopes']if s['source_at']==prefix['source_at'])
  d.setdefault('explicit_native_math_atoms',[]).append(dict(reviewed=True,original_source_only=True,rect=rect,font_regex='CambriaMath|TimesNewRoman',baseline=row_baseline,reason='Complete original grading-label reference number and punctuation following the literal English word Formula/Equation. This prose reference moves as one original encoded glyph group beside the translated word, retaining each original glyph baseline offset; the actual mathematical expression remains stationary.'))
 if n==9:
  region=next(r for r in d['stationary_table_math']if r['source_at']==[9,0]);scope=next(s for s in d['source_line_scopes']if s['source_at']==[9,0]);y=scope['baseline']
  first_line=[g for g in region['native_glyphs']if abs(g['origin'][1]-y)<.02 and g['size']>=11.9];assert first_line
  start=min(g['origin'][0]for g in first_line)
  for r in d['allowed_line_rects']:
   if abs(r[1]-(y-10.2))<.02 and r[0]<112:
    old=r[:];r[2]=start-.15;scope['rect']=r[:];d['reviewed_wrapped_formula_prose_rect']=dict(source_at=[9,0],baseline=y,previous_rect=old,rect=r[:],reason='Formula22 wraps onto a second source line whose left edge is not the first-line math boundary. All original formula glyphs/rules on both lines remain fixed; the translated first-line label only uses the blank space before the actual first-line mathematical expression.')
 rows={1:[211.32,309.96,511.56,525.6,539.64,652.8,774.],2:[562.44,576.6,762.84],3:[208.56,272.16,335.88,372.],5:[751.8]}
 for y in rows.get(n,[]):
  scopes=[s for s in d['source_line_scopes']if abs(s['baseline']-y)<.02];assert scopes,(n,y)
  old=[r for r in d['allowed_line_rects']if abs(r[1]-(scopes[0]['baseline']-10.2))<.02];assert old,(n,y)
  new=[63.59,min(r[1]for r in old),558.,max(r[3]for r in old)];d['allowed_line_rects']=[r for r in d['allowed_line_rects']if r not in old]+[new]
  for scope in scopes:scope['rect']=new[:]
  d.setdefault('reviewed_complete_prose_rows',[]).append(dict(baseline=scopes[0]['baseline'],source_at=[s['source_at']for s in scopes],rect=new[:],reason='One reviewed original prose row in the same full body column; original point sizes and baseline retained, complete native expressions packed unchanged with ordinary quarter-em spaces.'))
 if n==1:
  atoms=[]
  for rect,y,font,reason in [
   ([95.8,296.,124.9,316.],309.9599914550781,'CambriaMath','Original pair g_1,g_2 with its original smaller scripts and original mathematical comma.'),
   ([158.8,498.,181.6,518.],511.55999755859375,'CambriaMath','Complete original m*g_0 definition and original subscript.'),
   ([429.3,498.,440.9,518.],511.55999755859375,'CambriaMath','Complete original F_1 variable and original subscript.'),
   ([322.9,512.,334.7,532.],525.5999755859375,'CambriaMath','Complete original F_2 variable and original subscript.'),
   ([88.3,526.,100.1,546.],539.6399536132812,'CambriaMath','Complete original F_3 variable and original subscript.'),
   ([285.,759.,394.5,782.],774.,'TimesNewRoman|SymbolMT','Complete original MathType polynomial (1+x)^-2 approximately1-2x+3x^2, including both differently sized original parentheses and all original superscripts.')]:
   atoms.append(dict(reviewed=True,original_source_only=True,rect=rect,font_regex=font,baseline=y,reason=reason))
  d['explicit_native_math_atoms']=atoms
 if n==2:d.update(native_ink_witness='parenthesis-native-reference/witness.json',native_ink_witness_profile='2020-TS2-native-parenthesis')
 if n==3:d.update(native_ink_witness='page03-parentheses-native-reference/witness.json',native_ink_witness_profile='2020-TS3-native-parentheses')
 pp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
print('PREPARED_OFFICIAL_2020_TS_NATIVE_BASELINE',len(pages),'pages',flush=True)

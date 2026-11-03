from pathlib import Path
import json,hashlib,os,sys,contextlib
import pikepdf,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS');E=B/'engine';D=B.parents[1];PD=Path('D:/CodexBuilds/Hasla-publish-20261031');SOURCE=B/'inputs/CPhO_2007_Chinese_original.pdf';SOURCE_SHA='2e30b56ab9274363686cbf5bc1ef7532dcf579e0703de2c01098b003ab70cdd9'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def baseline_path(n,lang):return B/f'native-baseline/{lang}/page{n:02}-source-indexed.pdf'
def source_page(n):
 data=json.loads((B/'inputs/original-all20-source-slots.json').read_text('utf8'));assert data['source_sha256']==SOURCE_SHA
 return next(p for p in data['pages']if p['source_page']==n)
def build_initial(n,lang):
 assert 5<=n<=19 and lang in['ko','en']and sha(SOURCE)==SOURCE_SHA
 import cpho2007_ts_initial_native_baseline as m
 from cpho_original_latin_fonts import verify_real_glyphs
 m.ROOT=PD;m.SOURCE=SOURCE;m.SOURCE_SHA=SOURCE_SHA;m.AUTHOR=B/'authoring';m.FONTS=PD/'tools/ko/fonts';m.BASE=B/f'initial-fixed-slot-staging/{lang}/page{n:02}';m.BASE.mkdir(parents=True,exist_ok=True);m.EN_REPAIR_ROOT=B/'private-font-subsets'
 data=dict(source=str(SOURCE),source_sha256=SOURCE_SHA,pages=[source_page(n)],staging_only=True)
 (m.BASE/'slots.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
 fullfaces={'serif':D/'english-face-repair/font-faces/SimSun-5.24.ttf','sans':D/'official-hans-fonts/faces/simhei.ttf'}
 assert sha(fullfaces['serif'])=='79ba39fde98703ec0cd804ba1119b915f5e8f4e6663b2d729105b0f4c761ded6';assert sha(fullfaces['sans'])=='aa4560dd8fe5645745fed3ffa301c3ca4d6c03cbd738145b613303961ba733b8'
 m.original_latin_face=lambda year,family,bold=False:fullfaces[family]
 metrics={k:f.Font(fontfile=str(v))for k,v in fullfaces.items()}
 m.latin_word_gap=lambda slot,language,year=None:(slot['size']*.25-metrics[slot['family']].text_length(' ',fontsize=slot['size']))if language=='en'else 0
 # Staging can overlap long new translations before natural packing. Distinct
 # source slots can then put the same new English character at exactly one x.
 # Give only later new prose slots on that row a tiny, journaled staging x
 # offset so the native move helper never has two indistinguishable glyphs.
 # Original source glyphs, all points/Y and the first source anchor are intact.
 fitting=m.fitting
 def staged_fitting(*args,**kwargs):
  rows=fitting(*args,**kwargs);seen={}
  for row in rows:
   if not row['text'].strip():continue
   y=round(row['origin'][1],3);index=seen.get(y,0);seen[y]=index+1
   if index:
    row['source_prose_x_before_staging_disambiguation']=row['origin'][0]
    row['private_staging_prose_dx']=index*.0017
    row['origin'][0]+=index*.0017
  return rows
 m.fitting=staged_fitting
 folder=m.BASE/'editions';folder.mkdir(exist_ok=True);os.environ['CPHO_EN_REPAIR_DIR']=str(folder);os.environ['CPHO_KO_REPAIR_DIR']=str(folder)
 single=m.compose(lang,[n],allow_draft=True);journal=json.loads(single.with_suffix('.build.json').read_text('utf8'))
 target=baseline_path(n,lang);target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists():raise ValueError('Existing native staging baseline must be preserved before rebuild')
 with pikepdf.open(SOURCE)as original,pikepdf.open(single)as translated,pikepdf.Pdf.new()as output:
  for i,page in enumerate(original.pages):output.pages.append(translated.pages[0]if i==n-1 else page)
  output.save(target,compress_streams=False)
 journal.update(output_sha256=sha(target),source_page_index_preserved=True,staging_only=True,not_a_deliverable=True,only_page_with_new_translated_prose=n,source_point_sizes_and_baselines_unchanged=True,new_english_fonts_are_actual_original_SimSun_and_official_SimHei=True,new_english_word_spaces_quarter_em=True,original_source_sha256=SOURCE_SHA)
 target.with_suffix('.build.json').write_text(json.dumps(journal,ensure_ascii=False,indent=2)+'\n','utf8');print('CPHO2007_PRIVATE_INITIAL_NATIVE_BASELINE',n,lang,sha(target),flush=True)
 return target
def configure(n,lang):
 import cpho_natural_spacing as m
 m.ROOT=B;m.OUT=B/'natural';m.baseline=lambda year,language:baseline_path(n,language);m.original=lambda year:SOURCE;m.source_plan=lambda year,number:source_page(number)
 if n==6:
  # The original radicals are four separately painted strokes each. Their
  # actual stroke ink, including native cap/miter pixels, is the complete
  # selected object; line-center metric boxes are not an ink boundary.
  import pdf_native_geometry_motion as geometry
  from cpho2007_complete_vector_motion import audit as exact_radical_motion
  geometry.audit=exact_radical_motion
 # Own new bilingual prose has no legacy wording repairs. Its full source
 # SimSun/SimHei English faces and quarter-em spaces are already set in the
 # initial native baseline; avoid a redundant reordered suffix rewrite.
 import cpho_natural_prose_edits as edits
 edits.prepare_korean_prose=lambda year,source,number,placements,folder,**kwargs:(Path(source),number,placements,None)
 import cpho_natural_english_fonts as faces
 def already_original_faces(year,source,number,placements,folder):
  return Path(source),number,placements,dict(native_number_shifts=[],initial_native_baseline_already_uses_original_SimSun_and_official_SimHei=True,original_font_family_and_point_size_retained=True,new_prose_spaces_quarter_em=True)
 faces.prepare_english_faces=already_original_faces
 # Source CJK punctuation is native, but unlike native mathematics it is a
 # prose boundary. Keeping a deleted Chinese phrase's old native-native gap
 # would strand its comma at the old x. Preserve the CID/advance/paint/Y and
 # apply punctuation spacing only to our explicitly reviewed punctuation atoms.
 import cpho_natural_atoms as atom_module
 saved_atoms=atom_module.explicit_atoms
 def punctuation_atoms(spec):
  atoms=saved_atoms(spec)
  for atom in atoms:
   if atom.get('source_rule',{}).get('label','').startswith('Original complete inline expression '):
    atom['text']=''.join(g['c']for g in sorted(atom['glyphs'],key=lambda g:(g['origin'][0],g['origin'][1])))
   if atom.get('source_rule',{}).get('label','').startswith('Original retained prose punctuation '):
    atom['text']=''.join(g['c']for g in atom['glyphs'])
    atom['retained_original_prose_punctuation']=True
  return atoms
 atom_module.explicit_atoms=punctuation_atoms
 import pdf_korean_natural_composer as composer
 saved_gap=composer.boundary_gap
 def punctuation_gap(left,right,*args,**kwargs):
  if left.get('retained_original_prose_punctuation')or right.get('retained_original_prose_punctuation'):
   if right['text'].strip()[:1]in ',.;:!?，。；：)]）'or left['text'].rstrip()[-1:]in '([（':return 0
   return max(left['size'],right['size'])/4
  return saved_gap(left,right,*args,**kwargs)
 composer.boundary_gap=punctuation_gap
 prepare=m.prepare
 def own_prepare(year,language,number,*args,**kwargs):
  spec=prepare(year,language,number,*args,**kwargs);slots={s['id']:s for s in source_page(number)['slots']}
  for center in spec['centered_lines']:
   aligned=[s for s in slots.values()if s.get('align')=='center'and abs(s['origin'][1]-center['baseline'])<.02]
   if len(aligned)==1:center['center']=(aligned[0]['source_rect'][0]+aligned[0]['source_rect'][2])/2
  if number==5:
   ys=[r['baseline']for r in source_page(number)['rows']if 3<=r['row']<=9]
   for region in spec['regions']:
    if any(abs(region['baseline']-y)<.02 for y in ys):region['rect'][2]=296.4
  if number==7:
   ys=[r['baseline']for r in source_page(number)['rows']if 3<=r['row']<=10]
   for region in spec['regions']:
    if any(abs(region['baseline']-y)<.02 for y in ys):region['rect'][2]=303.12
  if number==12:
   ys=[r['baseline']for r in source_page(number)['rows']if 6<=r['row']<=11]
   for region in spec['regions']:
    if any(abs(region['baseline']-y)<.02 for y in ys):region['rect'][2]=355.68
  if number==14:
   # The source has one Chinese conjunction inside display equation(14).
   # Its actual blank gap fits both translations at the exact source size.
   # Translate that prose in place; keep both full fractions, radicals and the
   # original equation counter stationary at their exact source x/y.
   y=next(r['baseline']for r in source_page(number)['rows']if r['row']==14)
   slot=slots['14-14-0'];box=slot['source_rect'];center=(box[0]+box[2])/2
   for region in spec['regions']:
    if abs(region['baseline']-y)<.02:region['rect'][0]=177.0;region['rect'][2]=207.0
   spec['centered_lines'].append(dict(baseline=y,center=center))
  # A figure caption can share an original y with the adjacent narrative.
  # Its translated word and original native numeral form a separate source
  # region, so line packing never drags the caption into the paragraph.
  captions=[p for p in spec['prose_placements']if slots[p['id']]['source'].strip()in['图','表','图甲','图乙']and slots[p['id']].get('align')in['right','center']]
  for p in captions:
   for key in['regions','picture_label_regions','caption_regions']:
    kept=[]
    for region in spec[key]:
     if p['id']in region['placements']:
      region=dict(region,placements=[v for v in region['placements']if v!=p['id']])
      if not region['placements']:continue
     kept.append(region)
    spec[key]=kept
   slot=slots[p['id']];size=p['size'];y=p['point'][1];box=slot['source_rect'];cx=(box[0]+box[2])/2
   spec['caption_regions'].append(dict(rect=[cx-65,y-.85*size,cx+65,y+.32*size],baseline=y,placements=[p['id']],caption=True,alignment=slot['align'],center=cx))
  spec['private_full_source_slot_authoring']=True;spec['source_page_bilingual_prose_sha256']=sha(B/f'authoring/page{number:02}-bilingual-prose.json');return spec
 m.prepare=own_prepare
 return m
def build_natural(n,lang):
 m=configure(n,lang);target=m.OUT/f'2007/{lang}/page{n:02}.pdf'
 if target.exists():raise ValueError('Preserve and review any prior proof before rebuilding')
 import pdf_korean_natural_composer as composer
 from initial_prose_reading_order import journal,rewrite
 original=composer.baseline_lines;initial=None;reports=[];input_path=baseline_path(n,lang).resolve()
 def source_slot_order(page,**options):
  nonlocal initial
  lines=original(page,**options)
  if Path(page.parent.name).resolve()!=input_path:return lines
  if initial is None:initial=journal(page,options['prose_placements'])
  lines,report=rewrite(lines,page,options['allowed_line_rects'][0],options['prose_placements'],initial,options.get('baseline_tolerance_pt',.12));reports.append(report);return lines
 composer.baseline_lines=source_slot_order
 try:path=m.build(2007,lang,n)
 finally:composer.baseline_lines=original
 q=json.loads(path.with_suffix('.qa.json').read_text('utf8'));q['initial_fixed_slot_source_prose_order']=reports;q['initial_source_slot_suffix_verified']=bool(reports);q['private_authoring_not_yet_visual_release']=True;path.with_suffix('.qa.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');return path
def audit_natural(n,lang):
 configure(n,lang)
 from cpho_natural_full_qa import audit
 q=audit(2007,lang,n)
 if q['passed']:
  from cpho_natural_spacing_qa import original_native_glyphs
  from pdf_new_prose_native_text_overlap import audit as prose_collision
  target=B/f'natural/2007/{lang}/page{n:02}.pdf';composition=json.loads(target.with_suffix('.qa.json').read_text('utf8'))
  collision=prose_collision(target,native_glyphs=original_native_glyphs(2007,lang,n),shifts=composition['native_shifts'])
  target.with_suffix('.prose-native-text-overlap.json').write_text(json.dumps(collision,ensure_ascii=False,indent=2)+'\n','utf8')
  q['independent_actual_new_prose_native_text_ink']=collision;q['passed']=q['passed']and collision['passed']
  target.with_suffix('.audit.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
  print('CPHO2007_TS_INDEPENDENT_PROSE_NATIVE_TEXT_INK',n,lang,collision['passed'],collision['dark_prose_pixels_over_native_text'],flush=True)
 assert q['passed'];return q

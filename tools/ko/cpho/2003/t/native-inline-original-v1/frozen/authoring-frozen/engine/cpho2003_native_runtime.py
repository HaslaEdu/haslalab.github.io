"""Private CPhO2003 digital prose; original native mathematics is not retyped."""
from pathlib import Path
import sys,json,hashlib,os
import pikepdf,pymupdf as f
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native')
D=Path('D:/CodexBuilds/Hasla-original-style-20261031');PD=Path('D:/CodexBuilds/Hasla-publish-20261031')
SOURCE=B/'inputs/CPhO_2003_Chinese_original.pdf';SOURCE_SHA='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def isolated_new_english_subset(path,family):
 """Distinct new font identity; source programs and donor glyphs are untouched."""
 from fontTools.ttLib import TTFont
 path=Path(path);prefix='CPhO2003Translation'+('SimSun'if family=='serif'else'SimHei');cache=B/'new-font-identity';cache.mkdir(exist_ok=True);out=cache/f'{prefix}-{sha(path)[:16]}.ttf'
 if not out.exists():
  font=TTFont(path,recalcTimestamp=False)
  for record in font['name'].names:
   if record.nameID in [3,4,6]:
    value=prefix+('-'+sha(path)[:16]if record.nameID==3 else'');record.string=value.encode(record.getEncoding())
  font.save(out);font.close()
 with TTFont(path,recalcTimestamp=False)as before,TTFont(out,recalcTimestamp=False)as after:
  for tag in before.keys():
   if tag in ['GlyphOrder','name','head']:continue
   assert before.getTableData(tag)==after.getTableData(tag),(family,'New font isolation changed non-name table',tag)
  assert before['name'].getDebugName(1)==after['name'].getDebugName(1)
 return out
def source_page(n):
 q=json.loads((B/'inputs/original-all10-source-slots.json').read_text('utf8'));assert q['source_sha256']==SOURCE_SHA
 return q['pages'][n-1]
def baseline_path(n,lang):return B/f'native-baseline/{lang}/page{n:02}-source-indexed.pdf'
def build_initial(n,lang):
 import cpho2003_initial_native_baseline as m
 assert n in [1,2,3,10]and lang in ['ko','en']and sha(SOURCE)==SOURCE_SHA
 m.ROOT=PD;m.SOURCE=SOURCE;m.SOURCE_SHA=SOURCE_SHA;m.AUTHOR=B/'authoring/native';m.FONTS=PD/'tools/ko/fonts';m.BASE=B/f'initial-fixed-slot-staging/{lang}/page{n:02}';m.BASE.mkdir(parents=True,exist_ok=True);m.EN_REPAIR_ROOT=B/'private-font-subsets'
 (m.BASE/'slots.json').write_text(json.dumps(dict(source=str(SOURCE),source_sha256=SOURCE_SHA,pages=[source_page(n)],staging_only=True),ensure_ascii=False,indent=2)+'\n','utf8')
 faces={'serif':D/'english-face-repair/font-faces/SimSun-5.24.ttf','sans':D/'official-hans-fonts/faces/simhei.ttf'}
 assert sha(faces['serif'])=='79ba39fde98703ec0cd804ba1119b915f5e8f4e6663b2d729105b0f4c761ded6';assert sha(faces['sans'])=='aa4560dd8fe5645745fed3ffa301c3ca4d6c03cbd738145b613303961ba733b8'
 m.original_latin_face=lambda year,family,bold=False:faces[family]
 original_prepare_fonts=m.prepare_fonts
 def prepare_distinct_fonts(*args,**kwargs):
  paths=original_prepare_fonts(*args,**kwargs)
  return {key:isolated_new_english_subset(path,key[0])for key,path in paths.items()}if lang=='en'else paths
 m.prepare_fonts=prepare_distinct_fonts
 metrics={k:f.Font(fontfile=str(v))for k,v in faces.items()}
 m.latin_word_gap=lambda slot,language,year=None:(slot['size']*.25-metrics[slot['family']].text_length(' ',fontsize=slot['size']))if language=='en'else 0
 saved=m.fitting
 def distinct_staging(*a,**kw):
  rows=saved(*a,**kw);seen={}
  for r in rows:
   if not r['text'].strip():continue
   key=round(r['origin'][1],3);i=seen.get(key,0);seen[key]=i+1
   if i:r['source_prose_x_before_staging_disambiguation']=r['origin'][0];r['private_staging_prose_dx']=i*.0017;r['origin'][0]+=i*.0017
  return rows
 m.fitting=distinct_staging
 folder=m.BASE/'editions';folder.mkdir(exist_ok=True);os.environ['CPHO_EN_REPAIR_DIR']=str(folder);os.environ['CPHO_KO_REPAIR_DIR']=str(folder)
 single=m.compose(lang,[n],allow_draft=True);journal=json.loads(single.with_suffix('.build.json').read_text('utf8'))
 out=baseline_path(n,lang);out.parent.mkdir(parents=True,exist_ok=True);assert not out.exists()
 with pikepdf.open(SOURCE)as original,pikepdf.open(single)as translated,pikepdf.Pdf.new()as result:
  if lang=='en':
   for alias,family in [('TranslationserifRegular','SimSun'),('TranslationsansRegular','SimHei')]:
    font=translated.pages[0].Resources.Font.get('/'+alias)
    if font is None:continue
    name=pikepdf.Name('/CPhO2003Translation'+family);font.BaseFont=name
    for face in font.get('/DescendantFonts',[font]):
     face.BaseFont=name
     if '/FontDescriptor'in face:face.FontDescriptor.FontName=name
  for i,p in enumerate(original.pages):
   result.pages.append(translated.pages[0]if i==n-1 else p)
   if i==n-1:
    # PyMuPDF's initial insert_pdf does not copy the original transparency
    # page group. Restore the actual original object graph before composing.
    if '/Group'in p:result.pages[-1].Group=result.copy_foreign(original.make_indirect(p.Group))
    elif '/Group'in result.pages[-1]:del result.pages[-1]['/Group']
  result.save(out,compress_streams=False)
 journal.update(output_sha256=sha(out),source_page_index_preserved=True,staging_only=True,not_a_deliverable=True,only_page_with_new_translated_prose=n,source_point_sizes_and_baselines_unchanged=True,new_english_fonts_are_actual_original_SimSun_and_official_SimHei=True,new_english_word_spaces_quarter_em=True,original_source_sha256=SOURCE_SHA,new_english_postscript_names_isolated_from_original_source=(lang=='en'),new_english_glyph_and_advance_and_nonname_tables_unchanged=(lang=='en'),actual_original_source_page_group_retained=True)
 out.with_suffix('.build.json').write_text(json.dumps(journal,ensure_ascii=False,indent=2)+'\n','utf8');return out
def configure(n,lang):
 import cpho_natural_spacing as m
 m.ROOT=B;m.OUT=B/'natural';m.baseline=lambda year,language:baseline_path(n,language);m.original=lambda year:SOURCE;m.source_plan=lambda year,number:source_page(number)
 import cpho_natural_prose_edits as edits
 edits.prepare_korean_prose=lambda year,source,number,placements,folder,**kw:(Path(source),number,placements,None)
 import cpho_natural_english_fonts as faces
 faces.prepare_english_faces=lambda year,source,number,placements,folder:(Path(source),number,placements,dict(native_number_shifts=[],initial_native_baseline_already_uses_original_SimSun_and_official_SimHei=True,original_font_family_and_point_size_retained=True,new_prose_spaces_quarter_em=True))
 def prepare(year,language,number,input_path=None,input_page=None,prose_placements=None):
  from collections import defaultdict
  from pdf_native_inline_reposition import _traces
  input_path=Path(input_path or baseline_path(number,language));placements=prose_placements or m.placements(year,language,number);by_y=defaultdict(list)
  for p in placements:
   y=round(p['point'][1],3);near=[v for v in by_y if abs(v-y)<.12];by_y[near[0]if near else y].append(p)
  regions=[];centers=[]
  with f.open(SOURCE)as doc:
   pg=doc[number-1];images=[list(f.Rect(i['bbox'])+(-4,0,4,0))for i in pg.get_image_info()if i['width']>8 and i['height']>8];physical=_traces(pg)
   slots_by_id={s['id']:s for s in source_page(number)['slots']}
   from pdf_original_text_ops import glyph_key
   for p in placements:
    slot=slots_by_id[p['id']]
    if slot.get('render_mode')!=2:continue
    selected={glyph_key(g)for g in slot['source_characters']};actual=[g for g in physical if glyph_key(g)in selected and g['c'].strip()]
    assert actual and all(g['render_mode']==2 and abs(g['size']-slot['size'])<1e-6 and abs(g['linewidth']-slot['line_width'])<.0001 for g in actual)
    assert len({tuple(g['color'])for g in actual})==1 and len({tuple(g['stroke_color'])for g in actual})==1
    p['parts']=[dict(text=p['text'],size=slot['size'],source_paint=dict(source_only=True,actual_glyph_evidence=actual,render_mode=2,line_width=slot['line_width'],fill_color=list(actual[0]['color']),stroke_color=list(actual[0]['stroke_color'])))]
   for y,items in sorted(by_y.items()):
    size=max(p['size']for p in items);left=24.;right=524.3
    for image in images:
     if image[1]<y+size*.2 and image[3]>y-size*.85:
      if all(p['point'][0]+min(p['width'],20)<=image[0]+.1 for p in items):right=min(right,image[0]-2)
      elif all(p['point'][0]>=image[2]-.1 for p in items):left=max(left,image[2]+2)
    if size>=14:
     slots=[s for s in source_page(number)['slots']if s.get('align')=='center'and abs(s['origin'][1]-y)<.02];assert len(slots)==1
     box=slots[0]['source_rect'];centers.append(dict(baseline=y,center=(box[0]+box[2])/2));left=24.;right=pg.rect.width-24
    elif size==9 and y>pg.rect.height-60:
     glyphs=[g for g in physical if g['c'].strip()and abs(g['origin'][1]-y)<.02];box=f.Rect(glyphs[0]['bbox'])
     for g in glyphs[1:]:box|=f.Rect(g['bbox'])
     centers.append(dict(baseline=y,center=(box.x0+box.x1)/2));left=210.;right=390.
    regions.append(dict(rect=[left,y-.85*size,right,y+.32*size],baseline=y,placements=[p['id']for p in items],caption=False))
  return dict(year=year,language=language,page=number,input=str(input_path),input_page=input_page or number,input_sha256=sha(input_path),original=str(SOURCE),original_sha256=SOURCE_SHA,regions=regions,caption_regions=[],picture_label_regions=[],centered_lines=centers,excluded_figure_rects=images,prose_placements=placements,private_full_source_slot_authoring=True,source_page_bilingual_prose_sha256=sha(B/f'authoring/native/page{number:02}-bilingual-prose.json'))
 m.prepare=prepare
 import cpho_natural_atoms as atoms
 saved=atoms.explicit_atoms
 def source_expressions(spec):
  result=saved(spec)
  for a in result:a['text']=''.join(g['c']for g in sorted(a['glyphs'],key=lambda g:(g['origin'][0],g['origin'][1])))
  return result
 atoms.explicit_atoms=source_expressions
 return m
def build_natural(n,lang):
 m=configure(n,lang);out=m.OUT/f'2003/{lang}/page{n:02}.pdf';assert not out.exists()
 import pdf_korean_natural_composer as composer
 from initial_prose_reading_order import journal,rewrite
 saved=composer.baseline_lines;initial=None;reports=[];input_path=baseline_path(n,lang).resolve()
 def ordered(page,**options):
  nonlocal initial
  lines=saved(page,**options)
  if Path(page.parent.name).resolve()!=input_path:return lines
  if initial is None:initial=journal(page,options['prose_placements'])
  lines,report=rewrite(lines,page,options['allowed_line_rects'][0],options['prose_placements'],initial,options.get('baseline_tolerance_pt',.12));reports.append(report);return lines
 composer.baseline_lines=ordered
 try:out=m.build(2003,lang,n)
 finally:composer.baseline_lines=saved
 q=json.loads(out.with_suffix('.qa.json').read_text('utf8'));q['initial_fixed_slot_source_prose_order']=reports;q['initial_source_slot_suffix_verified']=bool(reports);q['private_authoring_not_yet_visual_release']=True;out.with_suffix('.qa.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');return out
def audit_natural(n,lang):
 configure(n,lang)
 from cpho_natural_full_qa import audit
 from cpho_natural_spacing_qa import original_native_glyphs
 from pdf_new_prose_native_text_overlap import audit as prose_ink
 q=audit(2003,lang,n);out=B/f'natural/2003/{lang}/page{n:02}.pdf';composition=json.loads(out.with_suffix('.qa.json').read_text('utf8'))
 collision=prose_ink(out,native_glyphs=original_native_glyphs(2003,lang,n),shifts=composition['native_shifts']);out.with_suffix('.prose-native-text-overlap.json').write_text(json.dumps(collision,ensure_ascii=False,indent=2)+'\n','utf8');q['independent_actual_new_prose_native_text_ink']=collision;q['passed']=q['passed']and collision['passed'];out.with_suffix('.audit.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');assert q['passed'];return q

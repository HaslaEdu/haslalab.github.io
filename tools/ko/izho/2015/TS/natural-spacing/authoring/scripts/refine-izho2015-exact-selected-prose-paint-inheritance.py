from pathlib import Path
import hashlib,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2015-complete-solutions');E=B/'engine';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def preserve(p):
 history=E/'history'/sha(p)[:16];history.mkdir(parents=True,exist_ok=True);shutil.copy2(p,history/p.name)
p=E/'source_prose_paint.py';preserve(p);text=p.read_text('utf8');a='def attach_source_paints(runs,page,selected):';b='def attach_source_paints(runs,page,selected,selected_glyphs=None):';assert text.count(a)==1;text=text.replace(a,b)
a="  for char in span['chars']:\n   if char['c'].isspace():continue\n   traces=lookup.get(key(span['font'],span['size'],char['c'],char['origin']),[])"
b="""  wanted=None if selected_glyphs is None else {key(g['font'],g['size'],g['c'],g['origin'])for g in selected_glyphs.get(at,[])if not g['c'].isspace()}
  chosen=[char for char in span['chars']if not char['c'].isspace()and(wanted is None or key(span['font'],span['size'],char['c'],char['origin'])in wanted)]
  whitespace_style_donor=False
  if not chosen and wanted is not None:
   donors=[char for char in span['chars']if not char['c'].isspace()and lookup.get(key(span['font'],span['size'],char['c'],char['origin']))]
   if not donors:raise ValueError(('Whitespace-only prose source has no actual style donor glyph',at))
   chosen=donors[:1];whitespace_style_donor=True
  for char in chosen:
   traces=lookup.get(key(span['font'],span['size'],char['c'],char['origin']),[])"""
assert text.count(a)==1;text=text.replace(a,b);a="source_only=True,glyphs_checked=len(patterns),actual_glyph_evidence=examples)";b="source_only=True,glyphs_checked=len(patterns),actual_glyph_evidence=examples,exact_selected_source_prose_characters_only=selected_glyphs is not None,whitespace_only_source_uses_actual_adjacent_style_donor=whitespace_style_donor)";assert text.count(a)==1;text=text.replace(a,b);p.write_text(text,'utf8')
p=E/'izho_initial_fixed_style.py';preserve(p);text=p.read_text('utf8');a='        attach_source_paints(runs,page,paint_scope)';b="""        exact_source_prose=defaultdict(list)
        for slot in data['slots']:exact_source_prose[tuple(slot['at'])].extend(slot_source(slot,runs)[1])
        attach_source_paints(runs,page,paint_scope,selected_glyphs=exact_source_prose)""";assert text.count(a)==1;text=text.replace(a,b);p.write_text(text,'utf8')
p=E/'final_translation_font_audit.py';preserve(p);text=p.read_text('utf8');a="   selected={tuple(placement['at'])for placement in p['prose_placements']};attach_source_paints(source_runs,source_page,selected)"
b="""   selected={tuple(placement['at'])for placement in p['prose_placements']}
   from izho_initial_fixed_style import slot_source
   original_plan=Path(__file__).resolve().parents[1]/str(p['year'])/'original_style'/f"page{p['source_page']}.json";authored=json.loads(original_plan.read_text('utf8'));assert authored['source_sha256']==p['original_english_source_sha256']
   exact_source_prose={}
   for slot in authored['slots']:exact_source_prose.setdefault(tuple(slot['at']),[]).extend(slot_source(slot,source_runs)[1])
   attach_source_paints(source_runs,source_page,selected,selected_glyphs=exact_source_prose)"""
assert text.count(a)==1;text=text.replace(a,b);p.write_text(text,'utf8');assert sha(E/'pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f';print('SOURCE2015_PROSE_PAINT_SAMPLES_EXACT_TRANSLATED_CHARACTERS_WITH_ALL_NATIVE_MATH_UNCHANGED',flush=True)

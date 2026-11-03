from pathlib import Path
import json,hashlib,ast
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');E=B/'engine';F=B/'natural/2016/TS';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();engine=E/'izho_natural_spacing_rebuild.py';text=engine.read_text('utf8')
needle="            if left['kind']!='native'or right['kind']!='korean'or 'placement'not in right:continue"
replacement="            if right['kind']!='korean'or 'placement'not in right:continue\n            if left['kind']!='native':\n                exact_bold_initial=(join.get('reviewed_authored_bold_initial')is True and d['original_english_source_sha256']=='19f23f790b5dd43bf2303f4b597da862c5d17a0267320fee3cca7f5f015a1df8'and d['source_page']==2 and left['kind']=='korean'and left['text'].strip()=='액'and all('Bold'in g['font']for g in left['glyphs']if g['c'].strip()))\n                if not exact_bold_initial:continue"
if needle in text:
 history=E/'history'/sha(engine);history.mkdir(parents=True,exist_ok=True);(history/engine.name).write_bytes(engine.read_bytes());text=text.replace(needle,replacement);ast.parse(text);engine.write_text(text,'utf8')
for n in[2,7]:
 P=F/f'plans/page{n:02}.json';p=json.loads(P.read_text('utf8'));history=P.parent/'history'/sha(P);history.mkdir(parents=True,exist_ok=True);(history/P.name).write_bytes(P.read_bytes())
 if n==2:
  joins=p['reviewed_native_hangul_word_joins'];assert len(joins)==1;joins[0]['reviewed_authored_bold_initial']=True
 else:
  a=next(a for a in p['explicit_native_math_atoms']if abs(a['baseline']-754.9)<.02 and a['rect'][0]<200);a['rect']=[185,744,313,771];a['source_native_glyphs']=[g for g in a['source_native_glyphs']if g['origin'][1]>744];assert len(a['source_native_glyphs'])>15
  p['reviewed_last_formula_physical_row_boundary']=dict(rect=a['rect'],reason='Full original7 rubric: preceding I=dq/dt denominator d,t has source baseline740.26 and belongs to the earlier row. The next dt=R/(U0-q/C(q))dq=f(q)dq begins with source numerator R at747.82. Native row ownership excludes the prior denominator, with every original formula7 glyph/rule retained unchanged.')
 P.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf8')
 if n==2:
  files=sorted(v for v in F.glob('page02*')if v.is_file());version=hashlib.sha256(''.join(v.name+sha(v)for v in files).encode()).hexdigest();archive=F/'history'/('page02-QA-positive-before-confirmed-single-word-join-'+version);archive.mkdir(parents=True,exist_ok=True)
  for v in files:
   dest=archive/v.name;assert v.resolve().is_relative_to(B.resolve())and dest.resolve().is_relative_to(B.resolve());assert not dest.exists();digest=sha(v);v.rename(dest);assert sha(dest)==digest
print('IZHO2016_EXACT_SOURCE_BOLD_INITIAL_AND_FINAL_MATH_ROW_OWNERSHIP_FIXED',flush=True)

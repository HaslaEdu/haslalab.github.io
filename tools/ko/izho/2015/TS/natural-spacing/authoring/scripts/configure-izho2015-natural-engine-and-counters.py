from pathlib import Path
import hashlib,json,shutil
R=Path('D:/CodexBuilds');B=R/'Hasla-original-style-20261031/izho2015-complete-solutions';E=B/'engine';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();source_sha=sha(B/'2015/source/IZhO_2015_TS.pdf');policy=B/'2015/reviewed-math-font-prose-policy.json';policy_sha=sha(policy)
p=E/'izho_natural_spacing_rebuild.py';text=p.read_text('utf8');history=E/'history'/sha(p)[:16];history.mkdir(parents=True,exist_ok=True);shutil.copy2(p,history/p.name)
a="        if year==2012 and kind=='TS'and d['source_sha256']=='41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db':\n            prose_ats="
b=f"        if kind=='TS'and(year,d['source_sha256'])in[(2012,'41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db'),(2015,'{source_sha}')]:\n            prose_ats=";assert text.count(a)==1;text=text.replace(a,b)
a="        for label in d.get('reviewed_math_font_prose_words',[]):\n            bi,li,_=label['at'];line=raw['blocks'][bi]['lines'][li]\n";assert text.count(a)==1
b=a+f"""            if year==2015 and kind=='TS'and d['source_sha256']=={source_sha!r}:
                policy_path=Path(__file__).resolve().parents[1]/'2015/reviewed-math-font-prose-policy.json'
                if sha(policy_path)!={policy_sha!r}:raise ValueError('Exact source2015 conjunction-prose policy changed')
                policy=json.loads(policy_path.read_text('utf8'));selection={{key:label.get(key)for key in ['at','substring','source_substring','range']}}
                if d['page']!=8 or label.get('reviewed')is not True or selection not in policy['reviewed_source_pages'].get(str(d['page']),[]):raise ValueError('Source2015 mathematical-font prose selection is not the reviewed conjunction')
                indexed=[s for s in line['spans']if ''.join(c['c']for c in s['chars']).strip()];span=indexed[label['at'][2]];chosen=span['chars'][label['range'][0]:label['range'][1]]
                if span['font']!='Cambria Math'or ''.join(c['c']for c in chosen)!=label['substring']or label['substring'].strip()!='and':raise ValueError('Exact original source2015 conjunction range changed')
                glyphs=[dict(c=c['c'],font=span['font'],size=span['size'],origin=list(c['origin']),bbox=list(c['bbox']))for c in chosen]
                math_narrative_literals.append(dict(source_at=label['at'],source_text=label['substring'],source_glyphs=glyphs,reason=label['reason']));continue
"""
text=text.replace(a,b);p.write_text(text,'utf8')
template=(E/'izho_2012_equation_counters.py').read_text('utf8');tail=template.split('def apply_reviewed_counters',1)[1]
head=f'''"""Every source2015 display label, including the original leading-period(16), stays native at source x/y."""
from pathlib import Path
import json,hashlib,re,pymupdf as f
from izho_initial_fixed_style import runs_of,characters
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
SOURCE={source_sha!r}
RANGES={{1:[],2:range(1,5),3:[],4:range(1,16),5:[16,17,1,2],6:range(3,11),7:range(11,19),8:range(19,25),9:range(25,29),10:[],11:[]}}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source_counters(plan):
 assert sha(plan['original_english_source'])==plan['original_english_source_sha256']==SOURCE
 with f.open(plan['original_english_source'])as doc:
  page=doc[plan['source_page']-1];runs=runs_of(page);physical={{glyph_key(g):g for g in _traces(page)if g['c'].strip()}};rows=[]
  for at,run in runs.items():
   m=re.fullmatch(r'\\s*\\.?\\s*(\\((\\d+)\\))\\s*',run['text'])
   if not m or run['font']!='Times New Roman'or run['size']!=12:continue
   chars=characters(run);assert ''.join(c['c']for c in chars)==run['text'];gs=[physical[glyph_key(g)]for g in chars[m.start(1):m.end(1)]if g['c'].strip()]
   rows.append(dict(source_at=list(at),number=int(m[2]),glyphs=gs,reason='Full original2015 source visually read: exact displayed-equation label, retaining its original Times New Roman12pt encoded glyphs and physical source x/y. Source leading prose/formula period before(16) is separate and remains unchanged. Inline references and grades are not display labels.'))
  assert[n['number']for n in rows]==list(RANGES[plan['source_page']]),(plan['source_page'],[n['number']for n in rows])
  assert all(g['size']==12 and g['font']=='Times New Roman'for row in rows for g in row['glyphs'])
  return rows
def apply_reviewed_counters'''
(E/'izho_2015_equation_counters.py').write_text(head+tail,'utf8')
assert sha(E/'pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
(B/'2015-natural-source-engine-config.json').write_text(json.dumps(dict(source_sha256=source_sha,natural_rebuild_sha256=sha(p),counter_module_sha256=sha(E/'izho_2015_equation_counters.py'),expected_display_labels=49,expected_original_counter_glyphs=174,prose_policy_sha256=policy_sha,shared_native_guard_unchanged=True),indent=2)+'\n','utf8')
print('SOURCE2015_NATURAL_ENGINE_AND49_NATIVE_COUNTER_POLICY_CONFIGURED',flush=True)

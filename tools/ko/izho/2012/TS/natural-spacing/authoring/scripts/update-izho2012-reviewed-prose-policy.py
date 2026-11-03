"""Add explicit human-authored page selections; retain every historical policy."""
from pathlib import Path
import sys,json,hashlib,re
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions');p=B/'2012/reviewed-math-font-prose-policy.json';raw=p.read_bytes();oldsha=hashlib.sha256(raw).hexdigest();q=json.loads(raw)
history=p.parent/'policy-history';history.mkdir(exist_ok=True);old=history/(oldsha+'.json')
if old.exists():assert old.read_bytes()==raw
else:old.write_bytes(raw)
for n in map(int,sys.argv[1:]):
 plan=json.loads((B/f'2012/original_style/page{n}.json').read_text('utf8'));assert plan['source_sha256']==q['source_sha256']
 q['reviewed_source_pages'][str(n-1)]=[{k:label.get(k)for k in['at','substring','source_substring','range']}for label in plan['reviewed_math_font_prose_words']]
updated=(json.dumps(q,ensure_ascii=False,indent=2)+'\n').encode('utf8');newsha=hashlib.sha256(updated).hexdigest()
for name in ['izho_initial_fixed_style.py','izho_natural_spacing_rebuild.py']:
 target=B/'engine'/name;source=target.read_text('utf8');assert oldsha in source,(name,oldsha)
 destination=history/(name+'.'+hashlib.sha256(target.read_bytes()).hexdigest()+'.py')
 if not destination.exists():destination.write_bytes(target.read_bytes())
 target.write_text(source.replace(oldsha,newsha),encoding='utf8')
p.write_bytes(updated);print('REVIEWED_2012_SOURCE_POLICY_PAGES',sorted(q['reviewed_source_pages']),newsha,flush=True)

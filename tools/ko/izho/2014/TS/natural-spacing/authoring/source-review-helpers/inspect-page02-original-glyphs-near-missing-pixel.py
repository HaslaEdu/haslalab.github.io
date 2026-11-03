from pathlib import Path
import json
F=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2014-complete-solutions/natural/2014/TS');d=json.loads((F/'page02.qa.json').read_text('utf8'));rows=[]
for shift in d['native_shifts']:
 for g in shift['glyphs']:
  dx=shift['dx'];x,y=g['origin'];new_x=x+dx
  if 184<=new_x<=207 and 745<=y<=767:
   rows.append(dict(c=g['c'],font=g['font'],point=g['size'],gid=g.get('trace_gid',g.get('gid')),source_origin=g['origin'],actual_expected_origin=[new_x,y],dx=dx))
print(json.dumps(rows,ensure_ascii=False,indent=2))

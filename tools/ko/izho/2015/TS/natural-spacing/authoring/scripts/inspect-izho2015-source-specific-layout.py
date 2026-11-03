from pathlib import Path
import json,re
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2015-complete-solutions')
for n in range(1,12):
 runs=json.loads((B/f'2015/inspection/page{n:02}-runs.json').read_text('utf8'));rows=[]
 for at,r in runs.items():
  if re.search(r'\(\d+\)',r['text'])and r['origin'][0]>490:rows.append(dict(at=at,text=r['text'],font=r['font'],point=r['size'],origin=r['origin']))
 print(n,json.dumps(rows,ensure_ascii=False))

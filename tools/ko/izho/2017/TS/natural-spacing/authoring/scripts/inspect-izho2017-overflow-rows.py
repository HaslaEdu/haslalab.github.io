from pathlib import Path
import json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-initial-theory')
targets={2:468.62,4:114.5,5:372.34,6:692.11,7:167.09}
for n,y in targets.items():
 q=json.loads((B/f'natural/2017/T/plans/page{n:02}.json').read_text('utf8'))
 print('\nPAGE',n,'baseline',y)
 for row in q['prose_placements']:
  if abs(row['source_baseline']-y)<15:
   print(json.dumps({k:row[k]for k in ['at','source_text','text','size','source_baseline']},ensure_ascii=False))

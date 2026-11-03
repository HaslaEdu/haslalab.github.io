from pathlib import Path
import json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2015-complete-solutions');d=json.loads((B/'2015/inspection/page09-original-native-inline-inventory.json').read_text('utf8'))
for k in['forms','vector_paths','clip_groups']:
 print(k,'count',len(d[k]),'keys',list(d[k][0])if d[k]else[])
 if k=='vector_paths':print(json.dumps(d[k][1],ensure_ascii=False)[:2300])
 if k=='forms':print({kk:vv for kk,vv in d[k][0].items()if kk not in['glyphs','vector_paths','images']})

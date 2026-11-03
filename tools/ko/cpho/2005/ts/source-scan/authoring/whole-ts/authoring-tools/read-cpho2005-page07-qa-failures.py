from pathlib import Path
import json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
for lang in ['ko','en']:
 p=B/f'proofs/{lang}/page07.source-qa.json'
 if not p.exists():continue
 j=json.loads(p.read_text('utf8'));r=j['actual_final_math_single_native_source_controls']['records']
 print(lang,'RECORD_KEYS',list(r[0]))
 for a in r:
  if a.get('changed_RGB_pixels',0):print(a)

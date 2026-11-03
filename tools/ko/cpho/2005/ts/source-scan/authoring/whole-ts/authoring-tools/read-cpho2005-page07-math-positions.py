from pathlib import Path
import json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
for r in json.loads((B/'row-hints/page07-ctc-location-proposals.json').read_text('utf8'))['rows']:
 if r['hint']in[9,14,24,37,39,41,42,46,23,25,29,56]:
  print(r['hint'],[(q['c'],round(q['x'],1))for q in r['ctc_peaks']],flush=True)

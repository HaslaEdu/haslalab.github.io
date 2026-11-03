from pathlib import Path
import json,sys,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path.insert(0,'D:/CodexBuilds/Hasla-publish-20261031/tools')
from pdf_native_inline_reposition import inspect_inline_groups
source=B/'inputs/CPhO_2005_Chinese_original.pdf'
inv=inspect_inline_groups(source,6)
print('IMAGES',json.dumps(inv['images'],ensure_ascii=False)[:6000])
hints=json.loads((B/'row-hints/page06-ctc-location-proposals.json').read_text('utf8'))['rows']
for h in hints:
 if h['hint'] in [1,6,7,9,14,17,23,31,33,37,39,40,43,45,46,47,48,49,52,57,58,59,62,63]:
  print('HINT',h['hint'],h['rect'],h['ctc_text'],[(a['c'],round(a['x'],1))for a in h['ctc_peaks']])

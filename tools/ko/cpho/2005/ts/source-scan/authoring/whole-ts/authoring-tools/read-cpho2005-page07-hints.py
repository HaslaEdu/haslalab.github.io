from pathlib import Path
import json,sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path.insert(0,'D:/CodexBuilds/Hasla-publish-20261031/tools')
from pdf_native_inline_reposition import inspect_inline_groups
print('IMAGES',json.dumps(inspect_inline_groups(B/'inputs/CPhO_2005_Chinese_original.pdf',7)['images'],ensure_ascii=False))
for r in json.loads((B/'row-hints/page07-ctc-location-proposals.json').read_text('utf8'))['rows']:
 print(r['hint'],r['rect'],r['ctc_text'],flush=True)

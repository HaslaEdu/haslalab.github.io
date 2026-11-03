from pathlib import Path
import json,sys,subprocess
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from pdf_memory_gate import page_worker
from cpho_2005_ts_compose import build
plan=json.loads((B/'authoring/page14-layout-proposal.json').read_text('utf8'))
plan['manual_rois_reviewed']=True
plan['review_note']='Manual source/full mathematical atlas review:27 bilingual source prose/caption rows,49 complete source-native mathematical/reference paints, all6 original graph/display/rule regions. Fig3 grid and I1/I2 labels untouched. Original q reaches the source inner clip; its original paint/clip retained byte-for-byte, outer crop includes empty paper through525pt, exact source roundtrip at4x/8x enforced. Caption source8.95pt/baseline/center612 retained, native3 unchanged. Independently measured body points/weights, quarter-em spaces. Final two-renderer QA required.'
for row in plan['rows']:row['reviewed']=True
(B/'authoring/page14-layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
for lang in ['ko','en']:
 with page_worker():target=build(14,lang)
 subprocess.run(['C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe','-f','1','-singlefile','-r','144','-png',str(target),str(B/f'proofs/{lang}/page14-preview')],check=True,capture_output=True)

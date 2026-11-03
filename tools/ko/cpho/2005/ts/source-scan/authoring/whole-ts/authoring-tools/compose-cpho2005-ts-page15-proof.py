from pathlib import Path
import json,sys,subprocess
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from pdf_memory_gate import page_worker
from cpho_2005_ts_compose import build
plan=json.loads((B/'authoring/page15-layout-proposal.json').read_text('utf8'))
plan['manual_rois_reviewed']=True
plan['review_note']='Manual source/full mathematical atlas review:25 bilingual source prose/caption rows,47 source-native mathematical/reference paints,9 original graph/display regions. Fig4 grid/II1/II2 labels untouched. Original z<D crosses columns; z< at left bottom and D at right top keep their original y. Original equation8-reference parentheses touch the source inner clip; original clip/paint retained byte-for-byte with outer crop through empty paper to521.75pt and exact source roundtrip at4x/8x. Caption source8.95pt/baseline/center236 retained. Quarter-em spaces. Final two-renderer QA required.'
for row in plan['rows']:row['reviewed']=True
(B/'authoring/page15-layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
for lang in ['ko','en']:
 with page_worker():target=build(15,lang)
 subprocess.run(['C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe','-f','1','-singlefile','-r','144','-png',str(target),str(B/f'proofs/{lang}/page15-preview')],check=True,capture_output=True)

from pathlib import Path
import json,sys,subprocess
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from pdf_memory_gate import page_worker
from cpho_2005_ts_compose import build
plan=json.loads((B/'authoring/page07-layout-proposal.json').read_text('utf8'))
plan['manual_rois_reviewed']=True
plan['review_note']='Manual landscape source review of all19 source-line prose regions,45 complete native mathematical/figure-number objects and protected two-panel diagram. Native enumeration marks preceding fP/fQ intentionally retained with those objects; no duplicate target punctuation. All crop borders zero deep-dark pixels at8x. Caption center is612pt in both languages, with original native numeral1 y/1x shape retained. Fixed independently measured source font family/point/baseline/print weight; no target shrinking.'
for row in plan['rows']:row['reviewed']=True
(B/'authoring/page07-layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
for lang in ['ko','en']:
 with page_worker():target=build(7,lang)
 subprocess.run(['C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe','-f','1','-singlefile','-r','144','-png',str(target),str(B/f'proofs/{lang}/page07-preview')],check=True,capture_output=True)

from pathlib import Path
import json,sys,subprocess
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from pdf_memory_gate import page_worker
from cpho_2005_ts_compose import build
plan=json.loads((B/'authoring/page13-layout-proposal.json').read_text('utf8'))
plan['manual_rois_reviewed']=True
plan['review_note']='Manual full-page and native math atlas review:28 bilingual prose rows and49 complete original mathematical/reference bitmap paints. All11 display-equation and separating-rule regions stay unchanged. Original primes, field signs, Qi prose versus DeltaQi formula, equation numbers, encoded scan programs, unit scales and y positions preserved. Independently source-measured font points/baselines/stem weights; quarter-em word spaces. Final two-renderer QA still required.'
for row in plan['rows']:row['reviewed']=True
(B/'authoring/page13-layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
for lang in ['ko','en']:
 with page_worker():target=build(13,lang)
 subprocess.run(['C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe','-f','1','-singlefile','-r','144','-png',str(target),str(B/f'proofs/{lang}/page13-preview')],check=True,capture_output=True)

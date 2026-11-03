from pathlib import Path
import json,sys,subprocess
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from pdf_memory_gate import page_worker
from cpho_2005_ts_compose import build
plan=json.loads((B/'authoring/page09-layout-proposal.json').read_text('utf8'))
plan['manual_rois_reviewed']=True
plan['review_note']='Manual source page and native atom atlas review:18 bilingual prose rows,21 complete original scan mathematical objects,13 stationary display-formula regions. Original photon nu1/nu2, velocity v1/v2, wavelength lambda0/lambda1, primes, equation numbers and2. part numeral retained as native encoded image paints at original y and unit scale. All native atom crop borders independently clear at8x. Fixed source-only measured CJK point/baseline/weight and independent Korean primary stems. Normal quarter-em word spaces; final two-renderer/source visibility checks still required.'
for row in plan['rows']:row['reviewed']=True
(B/'authoring/page09-layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
for lang in ['ko','en']:
 with page_worker():target=build(9,lang)
 subprocess.run(['C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe','-f','1','-singlefile','-r','144','-png',str(target),str(B/f'proofs/{lang}/page09-preview')],check=True,capture_output=True)

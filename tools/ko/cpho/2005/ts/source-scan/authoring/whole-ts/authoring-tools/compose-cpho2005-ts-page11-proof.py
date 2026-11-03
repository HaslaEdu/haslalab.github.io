from pathlib import Path
import json,sys,subprocess
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from pdf_memory_gate import page_worker
from cpho_2005_ts_compose import build
plan=json.loads((B/'authoring/page11-layout-proposal.json').read_text('utf8'))
plan['manual_rois_reviewed']=True
plan['review_note']='Manual full-page/source atlas review:25 bilingual source-line rows,31 original native bitmap mathematical objects and15 stationary display-formula regions. Original roman(ii)/(iii)/(iv), part2., radii list with original indices and punctuation, delta-r equality, original radially varying resistivity formula, complete omega0/2 fraction and all native equation numbers kept. No conventional constant-resistivity logarithmic replacement, no mathematical retyping. Narrative punctuation excluded from math crops. Every crop edge independently clear at8x. Source CJK-only point/baseline/weight measurements and independent Korean primary stems; every weight record must match its source point and measurement window. Quarter-em word spaces, no shrinking. Full fresh visual and two-renderer audits remain required.'
for row in plan['rows']:row['reviewed']=True
(B/'authoring/page11-layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
for lang in ['ko','en']:
 with page_worker():target=build(11,lang)
 subprocess.run(['C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe','-f','1','-singlefile','-r','144','-png',str(target),str(B/f'proofs/{lang}/page11-preview')],check=True,capture_output=True)

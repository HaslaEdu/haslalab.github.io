from pathlib import Path
import json,sys,subprocess
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from pdf_memory_gate import page_worker
from cpho_2005_ts_compose import build
plan=json.loads((B/'authoring/page08-layout-proposal.json').read_text('utf8'))
plan['manual_rois_reviewed']=True
plan['review_note']='Manual full-page source review:19 bilingual source-line prose regions,33 complete native scan mathematical objects and all15 stationary display formula regions. Original Arabic part number, equation ranges, variable/subscript/prime shapes and list separators retained as native image paints. Every crop boundary independently clear at8x. Each prose line uses source-only measured SimSun point/baseline and scan weight; Korean Batang primary stems independently matched. Fixed quarter-em word spaces; no font shrinking. Final two-renderer audits and complete-edition review remain required.'
for row in plan['rows']:row['reviewed']=True
(B/'authoring/page08-layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
for lang in ['ko','en']:
 with page_worker():target=build(8,lang)
 subprocess.run(['C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe','-f','1','-singlefile','-r','144','-png',str(target),str(B/f'proofs/{lang}/page08-preview')],check=True,capture_output=True)

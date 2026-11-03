from pathlib import Path
import json,sys,subprocess
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from pdf_memory_gate import page_worker
from cpho_2005_ts_compose import build
plan=json.loads((B/'authoring/page10-layout-proposal.json').read_text('utf8'))
plan['manual_rois_reviewed']=True
plan['review_note']='Manual full-page source and22-object native math atlas review.34 bilingual source-line prose rows, five narrow source rows beside the original circuit drawing,10 protected source display/circuit regions. Original circuit/current arrows and glyph labels completely preserved. All native variables, equation/part numbers, omega/t/theta/wavelength subscripts and heading(i) retain original encoded image programs and original y/unit scale. Source math atoms explicitly exclude narrative punctuation and adjacent Chinese. Every crop edge independently clear at8x, including the complete lower tail of the lambda2 subscript. Font points/baselines/scan weights measured from source CJK-only samples, Korean primary stems matched independently. Fixed quarter-em word spaces; source-size overflow resolved by faithful prose reflow across the existing source rows. Final visual and two-renderer audits still required.'
for row in plan['rows']:row['reviewed']=True
(B/'authoring/page10-layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
for lang in ['ko','en']:
 with page_worker():target=build(10,lang)
 subprocess.run(['C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe','-f','1','-singlefile','-r','144','-png',str(target),str(B/f'proofs/{lang}/page10-preview')],check=True,capture_output=True)

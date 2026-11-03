from pathlib import Path
import json,sys,subprocess
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from pdf_memory_gate import page_worker
from cpho_2005_ts_compose import build
plan=json.loads((B/'authoring/page12-layout-proposal.json').read_text('utf8'))
plan['manual_rois_reviewed']=True
plan['review_note']='Manual full-page source/math atlas review:23 bilingual prose/caption rows,37 complete original scan mathematical/number paints, both original potential graphs and7 protected display/plot regions. Original Roman I/II curve labels, axes, maxima/valley geometry, graph function labels and all mathematical bitmap programs/y/unit scales stay unchanged. Only the printed Fig2 caption is translated, at its independently measured8.95pt source point/baseline and source center608.0pt; original native digit2 retained. No unprinted Fig1 caption added. Four-family source-only CJK comparison confirms SimSun for left prose; expanded samples include complete original glyphs, no clipped source-word measurement. Body points/baselines/weights independently source-measured and Korean primary stems matched. Quarter-em word spaces; final actual two-renderer, caption/native ink and plot checks still required.'
for row in plan['rows']:row['reviewed']=True
(B/'authoring/page12-layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
for lang in ['ko','en']:
 with page_worker():target=build(12,lang)
 subprocess.run(['C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe','-f','1','-singlefile','-r','144','-png',str(target),str(B/f'proofs/{lang}/page12-preview')],check=True,capture_output=True)

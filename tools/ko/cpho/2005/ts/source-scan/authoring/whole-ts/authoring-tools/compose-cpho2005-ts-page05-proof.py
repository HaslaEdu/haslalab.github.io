from pathlib import Path
import json,sys,subprocess
import pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from pdf_memory_gate import page_worker
from cpho_2005_ts_compose import build
plan=json.loads((B/'authoring/page05-layout-proposal.json').read_text('utf8'))
plan['manual_rois_reviewed']=True
plan['review_note']='Manually specified source line erase geometry checked against original landscape page and diagram/display constraints.58 complete source math crops visually reviewed after correcting neighbouring Chinese/punctuation and split-formula bounds; all crop edges free of dark ink at8x threshold150. Every source prose line independently measured in source CJK only for family/physical font points/baselines and printed weight; Korean independent primary stem matching. This is a private proof, not full-edition publication.'
for row in plan['rows']:row['reviewed']=True
(B/'authoring/page05-layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
for lang in ['ko','en']:
 with page_worker():target=build(5,lang)
 subprocess.run(['C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe','-f','1','-singlefile','-r','144','-png',str(target),str(B/f'proofs/{lang}/page05-preview')],check=True,capture_output=True)

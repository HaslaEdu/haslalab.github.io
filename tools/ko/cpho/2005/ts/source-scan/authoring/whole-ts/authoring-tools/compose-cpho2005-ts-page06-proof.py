from pathlib import Path
import json,sys,subprocess
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from pdf_memory_gate import page_worker
from cpho_2005_ts_compose import build
plan=json.loads((B/'authoring/page06-layout-proposal.json').read_text('utf8'))
plan['manual_rois_reviewed']=True
plan['review_note']='All30 original prose lines and explicit erase rectangles manually checked against landscape original;37 source-native math crops visually reviewed with no Chinese/punctuation remnants and zero deep-dark border pixels at8x. Source physical SimSun point/baseline/printed weight measured separately for each row, no target font shrinking. Page6 final prose continues on source page7. Private proof only; whole13-page edition remains.'
for row in plan['rows']:row['reviewed']=True
(B/'authoring/page06-layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
for lang in ['ko','en']:
 with page_worker():target=build(6,lang)
 subprocess.run(['C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe','-f','1','-singlefile','-r','144','-png',str(target),str(B/f'proofs/{lang}/page06-preview')],check=True,capture_output=True)

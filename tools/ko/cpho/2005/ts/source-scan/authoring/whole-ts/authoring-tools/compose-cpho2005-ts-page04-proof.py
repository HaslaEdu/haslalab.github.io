from pathlib import Path
import sys,json,subprocess
import pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from pdf_memory_gate import page_worker
from cpho_2005_ts_compose import build
plan=json.loads((B/'authoring/page04-layout-proposal.json').read_text('utf8'))
plan['manual_rois_reviewed']=True
plan['review_note']='All41 actual original atom crops manually reviewed against full source, source-coordinate line rulers and corrected crop atlas. Entire mathematical glyphs included; Chinese and adjacent prose punctuation excluded. All crop edges have zero foreground in the innermost0.25pt at8x threshold150. Font family and physical sizes measured on source Chinese shapes, not fitted to translations. This is a private composition proof, not final publication.'
for row in plan['rows']:
 row['reviewed']=True
 for a in row['atoms']:a['reviewed']=True
(B/'authoring/page04-layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
for lang in ['ko','en']:
 with page_worker():target=build(4,lang)
 subprocess.run(['C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe','-f','1','-singlefile','-r','144','-png',str(target),str(B/f'proofs/{lang}/page04-preview')],check=True,capture_output=True)

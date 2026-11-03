from pathlib import Path
import sys,pymupdf as f,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2015-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import _traces
with page_worker():
 with f.open(B/'natural/2015/TS/page04.pdf')as d:
  gs=[g for g in _traces(d[0])if g['c'].strip()and f.Rect(g['bbox']).intersects(f.Rect(368.75,763.5,369,763.75))];print(json.dumps(gs,ensure_ascii=False,indent=2))

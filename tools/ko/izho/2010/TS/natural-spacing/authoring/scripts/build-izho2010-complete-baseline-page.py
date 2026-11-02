from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from izho_initial_fixed_style import build
from pdf_memory_gate import page_worker
n=int(sys.argv[1])
with page_worker():build(B/f'2010/original_style/page{n}.json',B/f'2010/native-baseline/page{n:02}.pdf')

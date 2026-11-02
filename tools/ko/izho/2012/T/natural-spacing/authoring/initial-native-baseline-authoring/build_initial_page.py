from pathlib import Path
import sys
B=Path(__file__).resolve().parent;sys.path[:0]=[str(B/'engine'),str(Path.cwd()/'tools')]
from izho_initial_fixed_style import build
from pdf_memory_gate import page_worker
year=int(sys.argv[1]);page=int(sys.argv[2]);plan=B/str(year)/'original_style'/f'page{page}.json';output=B/str(year)/'native-baseline'/f'page{page:02}.pdf'
with page_worker():build(plan,output)

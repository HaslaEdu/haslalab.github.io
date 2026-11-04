from pathlib import Path
import sys,shutil
B=Path(__file__).resolve().parents[1];sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from cpho2008_native_compose import build
for value in sys.argv[1:]:
 n,lang=value.split(':');n=int(n)
 if shutil.disk_usage(B).free<128*1024*1024:raise SystemExit('C08 build paused before new page: less than 128 MiB free; existing source/proofs remain preserved')
 with page_worker():build(n,lang)

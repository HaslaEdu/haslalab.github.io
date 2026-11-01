from pathlib import Path
import sys
sys.path.insert(0,'C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab/tools')
import pymupdf as f
from pdf_memory_gate import page_worker
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025')
with page_worker(),f.open(B/'CPhO_2025_T_original-explicit-page-clip.pdf') as d:
 d[5].get_pixmap(matrix=f.Matrix(4,4),alpha=False).save(B/'p6-authoring/source-p6-4x.png')
 for name,rect in [('top',[58,84,540,230]),('middle',[58,229,540,389]),('bottom',[58,388,540,550]),('footer',[260,770,340,790])]:
  d[5].get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(rect),alpha=False).save(B/f'p6-authoring/source-{name}.png')

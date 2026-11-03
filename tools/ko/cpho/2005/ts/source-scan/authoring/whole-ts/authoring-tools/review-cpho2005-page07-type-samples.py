from pathlib import Path
import json
import pymupdf as f
from PIL import Image,ImageDraw
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
rows=json.loads((B/'page07-row-baseline-proposals.json').read_text('utf8'))['rows']
im=Image.new('RGB',(480,len(rows)*110),'white');draw=ImageDraw.Draw(im)
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as d:
 for i,r in enumerate(rows):
  pic=d[6].get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(r['source_measurement_window']),alpha=False)
  tile=Image.frombytes('RGB',(pic.width,pic.height),pic.samples)
  draw.text((3,i*110+2),r['id'],fill='black');im.paste(tile,(3,i*110+23))
im.save(B/'source-renders/page07-source-CJK-measurement-samples.png')

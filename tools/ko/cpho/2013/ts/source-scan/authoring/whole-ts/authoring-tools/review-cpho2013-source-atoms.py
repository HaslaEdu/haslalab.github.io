"""Read-only exact source ROI contact inventory for a scanned solutions page."""
from pathlib import Path
import sys,json,math
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS');sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
import pymupdf as fitz
from PIL import Image,ImageDraw,ImageFont
SOURCE=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab/tmp/original-style-sources/CPhO_2013_Chinese_original.pdf')
n=int(sys.argv[1]);out=B/'source-atom-final-review';out.mkdir(exist_ok=True)
p=json.loads((B/f'authoring/page{n:02d}-layout.json').read_text('utf8'));atoms=[(r['id'],a)for r in p['rows']for a in r['atoms']];font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
with page_worker():
 with fitz.open(SOURCE)as d:
  pix=d[n-1].get_pixmap(matrix=fitz.Matrix(4,4),alpha=False);full=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
 for k in range(0,len(atoms),18):
  sheet=Image.new('RGB',(1440,1080),'white');dr=ImageDraw.Draw(sheet)
  for j,(row,a)in enumerate(atoms[k:k+18]):
   x,y=j%3*480,j//3*180;r=a['rect'];dr.text((x+3,y+2),row+' / '+a['id'],font=font,fill='black');dr.text((x+3,y+18),str(r),font=font,fill='black');cr=full.crop([math.floor(r[0]*4),math.floor(r[1]*4),math.ceil(r[2]*4),math.ceil(r[3]*4)]);cr.thumbnail((470,138));sheet.paste(cr,(x+3,y+38))
  sheet.save(out/f'page{n:02d}-{k//18+1:02d}.png')
print(n,len(atoms),'whole original source mathematical ROI contacts')

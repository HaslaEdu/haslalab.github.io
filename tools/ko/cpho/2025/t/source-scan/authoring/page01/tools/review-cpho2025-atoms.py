from pathlib import Path
import json,sys,math
from PIL import Image,ImageDraw,ImageFont
import pymupdf as fitz
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025');d=json.loads((B/'authoring/page01-draft-layout.json').read_text('utf8'))
proposed='--proposed'in sys.argv
out=B/('atom-review-proposed'if proposed else'atom-review');out.mkdir(exist_ok=True)
if proposed:
    changes=json.loads((B/'authoring/page01-single-symbol-clip-proposals.json').read_text('utf8'))
    updates={(r['row'],r['atom']):r['proposed_rect']for r in changes}
    for row in d['rows']:
        for atom in row['atoms']:
            if(row['id'],atom['id'])in updates:atom['rect']=updates[(row['id'],atom['id'])]
with fitz.open(B/'CPhO_2025_T_original-explicit-page-clip.pdf')as pdf:
    pm=pdf[0].get_pixmap(matrix=fitz.Matrix(4,4),alpha=False);full=Image.frombytes('RGB',(pm.width,pm.height),pm.samples)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
atoms=[(r['id'],a)for r in d['rows']for a in r['atoms']]
for k in range(0,len(atoms),12):
    cells=[]
    for rid,a in atoms[k:k+12]:
        x0,y0,x1,y1=a['rect'];left=max(0,x0-8);right=min(595,x1+8);top=y0-4;bottom=y1+4
        rect=(math.floor(left*4),math.floor(top*4),math.ceil(right*4),math.ceil(bottom*4))
        crop=full.crop(rect);draw=ImageDraw.Draw(crop);draw.rectangle([(x0*4-rect[0],y0*4-rect[1]),(x1*4-rect[0],y1*4-rect[1])],outline='red',width=1)
        cell=Image.new('RGB',(480,150),'white');dc=ImageDraw.Draw(cell);dc.text((3,3),rid+' / '+a['id'],font=font,fill='black');dc.text((3,22),str(a['rect']),font=font,fill='black')
        if crop.width>470:crop.thumbnail((470,95))
        cell.paste(crop,(4,45));cells.append(cell)
    sheet=Image.new('RGB',(1440,600),(235,235,235))
    for i,c in enumerate(cells):sheet.paste(c,((i%3)*480,(i//3)*150))
    path=out/f'page01-atoms-{k//12+1:02}.png';sheet.save(path);print(path)

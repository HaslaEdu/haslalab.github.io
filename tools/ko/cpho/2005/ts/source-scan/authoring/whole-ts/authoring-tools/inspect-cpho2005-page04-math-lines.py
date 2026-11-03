from pathlib import Path
import pymupdf as f
from PIL import Image,ImageDraw
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
fields=[('equationrefs',[65,362,218,382]),('first-indices',[460,305,647,326]),('always',[435,357,785,383]),('second-indices',[460,400,647,423]),('last-first',[435,464.7,784.85,488]),('last-second',[435,488,784.85,506.69])]
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf') as doc:
 for name,rect in fields:
  p=doc[3].get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(rect),alpha=False)
  im=Image.frombytes('RGB',[p.width,p.height],p.samples)
  canvas=Image.new('RGB',(im.width,im.height+42),'#ddd');canvas.paste(im,(0,42));d=ImageDraw.Draw(canvas)
  for x in range(int(rect[0]/5)*5,int(rect[2])+1,5):
   xx=x*4-p.x;yy=0 if x%10==0 else 15;d.text((xx-8,yy),str(x),fill='black');d.line((xx,32,xx,41),fill='red')
  canvas.save(B/f'source-renders/page04-math-line-{name}.png')

from pathlib import Path
import pymupdf as f
from PIL import Image,ImageDraw
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf') as doc:
 for name,rect in [('left',[55,55,412,525]),('right',[429,59,788,516])]:
  p=doc[3].get_pixmap(matrix=f.Matrix(3,3),clip=f.Rect(rect),alpha=False)
  im=Image.frombytes('RGB',[p.width,p.height],p.samples)
  canvas=Image.new('RGB',(im.width+52,im.height+24),'#e6e6e6');canvas.paste(im,(45,24));d=ImageDraw.Draw(canvas)
  for y in range(int(rect[1]/5)*5,int(rect[3])+1,5):
   yy=24+y*3-p.y
   d.text((2,yy-5),str(y),fill='black');d.line((36,yy,44,yy),fill='red')
  for x in range(int(rect[0]/10)*10,int(rect[2])+1,10):
   xx=45+x*3-p.x;d.text((xx-9,2),str(x),fill='black');d.line((xx,17,xx,23),fill='red')
  canvas.save(B/f'source-renders/page04-{name}-ruler.png')

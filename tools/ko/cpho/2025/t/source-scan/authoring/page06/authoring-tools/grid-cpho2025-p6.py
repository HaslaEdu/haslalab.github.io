from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025/p6-authoring');font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',16)
for name,rect in [('top',[58,84,540,230]),('middle',[58,229,540,389]),('bottom',[58,388,540,550])]:
 im=Image.open(B/f'source-{name}.png').convert('RGB');d=ImageDraw.Draw(im)
 for x in range(60,541,10):
  xx=(x-rect[0])*4;d.line((xx,0,xx,im.height),fill='#a8c4ff',width=1)
  if x%20==0:d.text((xx+1,0),str(x),font=font,fill='blue')
 for y in range(((rect[1]+9)//10)*10,rect[3],10):
  yy=(y-rect[1])*4;d.line((0,yy,im.width,yy),fill='#a8c4ff',width=1);d.text((0,yy),str(y),font=font,fill='blue')
 im.save(B/f'source-{name}-grid.png')

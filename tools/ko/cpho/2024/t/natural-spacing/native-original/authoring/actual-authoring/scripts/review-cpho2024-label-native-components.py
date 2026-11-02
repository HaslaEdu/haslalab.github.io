from pathlib import Path
import sys,numpy as np,cv2
from PIL import Image,ImageOps,ImageDraw
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2024-original-natural');sys.path.insert(0,str(B/'engine'))
from cpho2024_figure_label_plan import LABELS
tiles=[];cache={}
for label in LABELS:
 key=(label['page'],label['image_index'])
 if key not in cache:
  a=np.asarray(Image.open(B/f'inspection/image-p{key[0]}-{key[1]}.png').convert('RGB')).copy();_,cc,stats,_=cv2.connectedComponentsWithStats((a.min(axis=2)<160).astype('uint8'),8);cache[key]=(a,cc,stats)
 a,cc,stats=cache[key];x0,y0,x1,y1=label['source_word_roi_px'];roi=a[y0:y1,x0:x1].copy();local=cc[y0:y1,x0:x1]
 for i in np.unique(local):
  if not i:continue
  x,y,w,h,n=stats[i]
  if n>1000:roi[local==i]=[255,0,0]
  elif not(x0<=x and y0<=y and x+w<=x1 and y+h<=y1):roi[local==i]=[0,100,255]
 im=Image.fromarray(roi);preview=ImageOps.contain(im.resize((im.width*5,im.height*5),Image.Resampling.NEAREST),(230,115));tile=Image.new('RGB',(250,150),'white');ImageDraw.Draw(tile).text((5,5),label['id'],fill='red');tile.paste(preview,((250-preview.width)//2,27));tiles.append(tile)
sheet=Image.new('RGB',(1250,150*((len(tiles)+4)//5)),'#cccccc')
for i,tile in enumerate(tiles):sheet.paste(tile,((i%5)*250,(i//5)*150))
sheet.save(B/'inspection/figure-language-roi-review/native-components.png')

from pathlib import Path
import sys
from PIL import Image,ImageDraw,ImageOps
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2024-original-natural');sys.path.insert(0,str(B/'engine'))
from cpho2024_figure_label_plan import LABELS
out=B/'inspection/figure-language-roi-review';out.mkdir(exist_ok=True);tiles=[]
for label in LABELS:
 with Image.open(B/f"inspection/image-p{label['page']}-{label['image_index']}.png")as src:crop=src.crop(label['source_word_roi_px']).convert('RGB')
 crop.save(out/(label['id']+'.png'));preview=ImageOps.contain(crop.resize((crop.width*3,crop.height*3),Image.Resampling.NEAREST),(230,115))
 tile=Image.new('RGB',(250,150),'white');ImageDraw.Draw(tile).text((5,5),label['id'],fill='red');tile.paste(preview,((250-preview.width)//2,27));tiles.append(tile)
sheet=Image.new('RGB',(250*5,150*((len(tiles)+4)//5)),'#cccccc')
for i,tile in enumerate(tiles):sheet.paste(tile,((i%5)*250,(i//5)*150))
sheet.save(out/'contact.png');print(len(tiles),'ROIs for actual manual isolation review')

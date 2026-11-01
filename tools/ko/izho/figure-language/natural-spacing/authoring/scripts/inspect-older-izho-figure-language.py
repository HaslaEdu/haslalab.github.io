from pathlib import Path
import pymupdf as f,json
from PIL import Image,ImageOps,ImageDraw
B=Path('D:/CodexBuilds/Hasla-original-style-20261031');out=B/'izho-older-figure-language';out.mkdir(exist_ok=True);tiles=[];records=[]
for year in [2010,2011]:
 ready=json.loads((B/f'izho-natural-spacing/editions/IZhO_{year}_T_KO.ready.json').read_text('utf8'));source=ready['input_archives'][1]['path']
 with f.open(source)as d:
  for n,p in enumerate(d,1):
   for i,info in enumerate(p.get_image_info()):
    if info['width']<60 or info['height']<24:continue
    name=f'{year}-p{n:02}-image{i:02}';box=f.Rect(info['bbox']);image=p.get_pixmap(matrix=f.Matrix(2,2),clip=box,alpha=False);path=out/f'{name}.png';image.save(path)
    native=[dict(font=t['font'],size=t['size'],chars=''.join(chr(c[0])for c in t['chars']),origin=list(t['chars'][0][2]))for t in p.get_texttrace()if t['chars']and box.intersects(f.Rect(t['bbox']))]
    records.append(dict(year=year,page=n,image_index=i,image=info,path=str(path),native=native))
    with Image.open(path)as im:
     tile=ImageOps.contain(im.convert('RGB'),(520,380));bg=Image.new('RGB',(540,410),'white');bg.paste(tile,((540-tile.width)//2,25));ImageDraw.Draw(bg).text((8,5),name,fill='red');tiles.append(bg)
sheet=Image.new('RGB',(540*3,410*((len(tiles)+2)//3)),'#dddddd')
for i,t in enumerate(tiles):sheet.paste(t,((i%3)*540,(i//3)*410))
sheet.save(out/'source-contact.png');(out/'source-inventory.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n','utf8');print(len(records),'source figures')

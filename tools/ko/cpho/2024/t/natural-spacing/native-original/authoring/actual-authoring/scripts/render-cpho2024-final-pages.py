from pathlib import Path
import json,hashlib,subprocess
from PIL import Image,ImageOps,ImageDraw
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2024-original-natural');out=B/'inspection/final-page-review';out.mkdir(exist_ok=True);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
for lang in ['KO','EN']:
 tiles=[]
 for n in range(1,6):
  pdf=B/f'T/figure-language/page{n:02}-{lang}.pdf';q=json.loads(pdf.with_suffix('.labels.json').read_text('utf8'));assert sha(pdf)==q['output_sha256'];prefix=out/f'page{n:02}-{lang}'
  subprocess.run(['pdftoppm','-r','144','-singlefile','-png',str(pdf),str(prefix)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  png=prefix.with_suffix('.png');rows.append(dict(page=n,language=lang,proof_sha256=sha(pdf),image=str(png),image_sha256=sha(png),renderer='Poppler144dpiRGB',reviewed=False))
  with Image.open(png)as im:tile=ImageOps.contain(im.convert('RGB'),(357,505));bg=Image.new('RGB',(375,530),'white');bg.paste(tile,((375-tile.width)//2,18));ImageDraw.Draw(bg).text((6,3),f'2024 T {lang} page{n}',fill='red');tiles.append(bg)
  print('FINAL_PAGE_PREVIEW',n,lang,sha(pdf),flush=True)
 sheet=Image.new('RGB',(375*5,530),'#cccccc')
 for i,tile in enumerate(tiles):sheet.paste(tile,(i*375,0))
 sheet.save(out/f'contact-{lang}.png')
(out/'preview-index.json').write_text(json.dumps(dict(pages=rows),indent=2)+'\n','utf8')

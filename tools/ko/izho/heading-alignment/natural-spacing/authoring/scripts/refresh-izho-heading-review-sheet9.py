from pathlib import Path
import json,hashlib,subprocess,math
from PIL import Image,ImageDraw
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/heading-alignment-v1');out=B/'visual-review';cache=out/'poppler-crops';cache.mkdir(exist_ok=True)
load=lambda p:json.loads(Path(p).read_text('utf8'));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
q=load(out/'contact-sheet-inventory.json');rows=q['source_rows'];s=1.5;w=round(545*s);tiles=[]
for index in range(160,180):
 r=rows[index];y=r['scopes'][0]['baseline'];proof=B/r['file'].removesuffix('.pdf')/f"page{r['published_page']:02}.pdf"
 tile=Image.new('RGB',(w,86),'white');draw=ImageDraw.Draw(tile);draw.text((4,1),f"{index+1}. {r['file']} p{r['published_page']} {r['source_at']} dx={-r['actual_center_error']:+.3f}pt",fill='black')
 for offset,file,n,label in [(19,r['source_path'],r['source_page'],'S'),(52,str(proof),1,'K')]:
  prefix=cache/f'{index+1}-{label}';subprocess.run(['pdftoppm','-f',str(n),'-l',str(n),'-r','108','-x',str(round(25*s)),'-y',str(round((y-15)*s)),'-W',str(w),'-H','30','-singlefile','-png',file,str(prefix)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  with Image.open(str(prefix)+'.png')as im:tile.paste(im.convert('RGB'),(0,offset))
  draw.text((1,offset),label,fill='#555');x=round((r['source_center']-25)*s);draw.line([(x,offset),(x,offset+2)],fill='#d00000')
 tiles.append(tile)
canvas=Image.new('RGB',(2*(w+6),920),'#ddd')
for j,tile in enumerate(tiles):canvas.paste(tile,((j%2)*(w+6),(j//2)*92))
file=out/'headings-09.png';canvas.save(file)
q['contact_sheets'][-1]['sha256']=sha(file);q['contact_sheets'][-1]['renderer']='Fresh Poppler process for each source and target crop'
q['first_preview_incomplete_tile_170_rechecked_in_fresh_mupdf_full_and_narrow_and_poppler']=True
(out/'contact-sheet-inventory.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('SHEET9_REFRESHED_WITH_POPPLER',flush=True)

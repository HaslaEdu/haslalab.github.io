from pathlib import Path
from collections import defaultdict
import json,hashlib,math
import pymupdf as fitz
from PIL import Image,ImageDraw
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/heading-alignment-v1')
load=lambda p:json.loads(Path(p).read_text('utf8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rows=[r for r in load(B.parent/'published-izho-heading-detail-20261102.json')['candidates_requiring_review']if abs(r['actual_center_error'])>.001]
out=B/'visual-review';out.mkdir(exist_ok=True);tiles=[];pages=defaultdict(list)
scale=1.5;clipx=(25,570);width=round((clipx[1]-clipx[0])*scale)
for index,r in enumerate(rows):
 folder=B/r['file'].removesuffix('.pdf');proof=folder/f"page{r['published_page']:02}.pdf";q=load(proof.with_suffix('.alignment.json'));assert q['passed']and sha(proof)==q['proof_sha256']
 y=r['scopes'][0]['baseline'];clip=fitz.Rect(clipx[0],y-15,clipx[1],y+5)
 tile=Image.new('RGB',(width,86),'white');draw=ImageDraw.Draw(tile);draw.text((4,1),f"{index+1}. {r['file']} p{r['published_page']} {r['source_at']}  dx={-r['actual_center_error']:+.3f}pt",fill='black')
 for offset,file,n,label in [(19,r['source_path'],r['source_page']-1,'S'),(52,str(proof),0,'K')]:
  with fitz.open(file)as doc:pix=doc[n].get_pixmap(matrix=fitz.Matrix(scale,scale),clip=clip,alpha=False);im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
  tile.paste(im,(0,offset));draw.text((1,offset),label,fill='#555')
  x=round((r['source_center']-clipx[0])*scale);draw.line([(x,offset),(x,offset+2)],fill='#d00000')
 tiles.append(tile);pages[(r['file'],r['published_page'])].append(index+1)
 fitz.TOOLS.store_shrink(100)
for start in range(0,len(tiles),20):
 group=tiles[start:start+20];canvas=Image.new('RGB',(2*(width+6),10*92),'#ddd')
 for j,tile in enumerate(group):canvas.paste(tile,((j%2)*(width+6),(j//2)*92))
 canvas.save(out/f'headings-{start//20+1:02}.png')
manifest=dict(source_rows=rows,heading_count=len(rows),contact_sheets=[dict(path=str(p),sha256=sha(p))for p in sorted(out.glob('headings-*.png'))],page_tiles=[dict(file=f,page=n,tiles=ids)for (f,n),ids in sorted(pages.items())],source_first_target_second=True,red_tick_is_original_nonspace_glyph_center=True,publication_pdfs_not_annotated=True)
(out/'contact-sheet-inventory.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8');print('RENDERED',len(rows),len(manifest['contact_sheets']),flush=True)

"""Read-only source image crops for complete manually selected expressions."""
from pathlib import Path
import json,sys,math
from PIL import Image,ImageDraw
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');T=B/'TS'
sys.path[:0]=[str(T/'engine'),str(B/'engine')]
from pdf_native_inline_reposition import inspect_inline_groups
n=int(sys.argv[1]);version=sys.argv[2]
q=json.loads((T/f'authoring/page{n:02}-layout.json').read_text('utf8'));reads=[r for r in json.loads((T/'source-image-reading/image-reading-index.json').read_text('utf8'))if r['page']==n];paint=inspect_inline_groups(B/'inputs/CPhO_2003_Chinese_original.pdf',n)['images'];index={tuple(p['path']):(p,r)for p,r in zip(paint,reads)}
count=sum(len(r['atoms'])for r in q['rows']);canvas=Image.new('RGB',(1100,math.ceil(count/4)*105),'white');draw=ImageDraw.Draw(canvas);i=0
for row in q['rows']:
 for atom in row['atoms']:
  p,r=index[tuple(atom['image_path'])];b=p['bbox'];v=atom['rect'];box=[round((v[0]-b[0])*r['width']/(b[2]-b[0])),round((v[1]-b[1])*r['height']/(b[3]-b[1])),round((v[2]-b[0])*r['width']/(b[2]-b[0])),round((v[3]-b[1])*r['height']/(b[3]-b[1]))];im=Image.open(r['path']).crop(tuple(box));im.thumbnail((255,75));x=(i%4)*275;y=(i//4)*105;draw.text((x,y),row['id']+'-'+atom['id'],fill='black');canvas.paste(im,(x,y+23));i+=1
p=T/f'source-image-reading/page{n:02}-manual-math-atlas-{version}.png';assert not p.exists();canvas.save(p);print(p)

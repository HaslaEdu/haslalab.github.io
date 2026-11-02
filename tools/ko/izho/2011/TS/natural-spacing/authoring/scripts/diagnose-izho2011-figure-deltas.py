from pathlib import Path
import sys,json,math,numpy as np,cv2,pymupdf as f
from PIL import Image
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');F=B/'natural/2011/TS'
for n in map(int,sys.argv[1:]):
 d=json.loads((F/f'page{n:02}.audit.json').read_text('utf8'));r=d['figure_pixel_audits'][0]['rect'];a=np.array(Image.open(F/f'qa-renders/{n:02}-original-figure-reference.png').convert('RGB'));z=np.array(Image.open(F/f'qa-renders/{n:02}-new.png').convert('RGB'));v=np.any(a!=z,axis=2).astype('uint8');x0,y0,x1,y1=[math.ceil(q*4-.5)for q in r];m=np.zeros(v.shape,'uint8');m[y0:y1,x0:x1]=v[y0:y1,x0:x1];_,_,stats,_=cv2.connectedComponentsWithStats(m,8)
 changes=[dict(pixels=int(px),bbox=[round(x/4,3),round(y/4,3),round((x+w)/4,3),round((y+h)/4,3)])for x,y,w,h,px in stats[1:]if px>1]
 print('EXACT_PICTURE_CHANGED_COMPONENTS',n,changes,flush=True)
 with f.open(B/'2011/source/IZhO_2011_TS.pdf')as doc:
  raw=doc[n-1].get_text('dict');texts=[dict(text=s['text'],bbox=s['bbox'])for b in raw['blocks']if not b['type']for line in b['lines']for s in line['spans']if any(f.Rect(c['bbox']).intersects(f.Rect(s['bbox']))for c in changes)]
  print('ORIGINAL_NEIGHBORING_TEXT',n,texts,flush=True)

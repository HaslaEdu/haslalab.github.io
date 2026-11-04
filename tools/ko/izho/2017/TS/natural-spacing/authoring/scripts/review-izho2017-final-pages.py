from pathlib import Path
import json,hashlib,sys
from PIL import Image,ImageOps,ImageDraw
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-initial-theory');sys.path.insert(0,str(Path.cwd()/'tools'))
from pdf_memory_gate import page_worker
f=B/'natural/2017/T';out=f/'final-page-review';out.mkdir(exist_ok=True);tiles=[]
for n in range(1,8):
 p=f/f'page{n:02}.pdf';a=json.loads(p.with_suffix('.audit.json').read_text('utf8'));c=json.loads(p.with_suffix('.prose-collision.json').read_text('utf8'));digest=hashlib.sha256(p.read_bytes()).hexdigest()
 assert a['passed']and c['passed']and a['output_sha256']==c['final_sha256']==digest,(n,a['passed'],c['passed'])
 with page_worker():
  with Image.open(f/f'qa-renders/{n:02}-new.png')as src:
   src.convert('RGB').resize((774,1095),Image.Resampling.LANCZOS).save(out/f'page{n:02}.png')
  with Image.open(out/f'page{n:02}.png')as src:
   t=ImageOps.pad(src,(387,568),color='white');ImageDraw.Draw(t).text((6,2),f'2017 T page{n}',fill='red');tiles.append(t)
 print('EXACT_PROOF_REVIEW',n,digest,flush=True)
sheet=Image.new('RGB',(387*4,568*2),'#cccccc')
for i,t in enumerate(tiles):sheet.paste(t,((i%4)*387,(i//4)*568))
sheet.save(out/'contact.png')

from pathlib import Path
import sys,json,math
sys.path[:0]=['D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools','C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab/tools']
import pymupdf as f
from PIL import Image,ImageDraw,ImageFont
from pdf_memory_gate import page_worker
from cpho_2013_ts_manual_page04 import source_baseline
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025');P=B/'p6-authoring'
plan=P/'plans/page06-draft-layout.json';q=json.loads(plan.read_text('utf8'))
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',15)
with page_worker(),f.open(B/'CPhO_2025_T_original-explicit-page-clip.pdf')as doc:
 p=doc[5];pix=p.get_pixmap(matrix=f.Matrix(4,4),alpha=False);im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
 items=[]
 for row in q['rows']:
  if row['baseline'] is None:
   text=row['source'];row['baseline'],row['baseline_evidence']=source_baseline(p,row['erase_rects'][0],text[:6],row['size'])
  for atom in row['atoms']:items.append((row,atom))
 for index in range(math.ceil(len(items)/20)):
  chunk=items[index*20:(index+1)*20];sheet=Image.new('RGB',(1800,math.ceil(len(chunk)/4)*160),'#dedede');draw=ImageDraw.Draw(sheet)
  for i,(row,atom)in enumerate(chunk):
   x=(i%4)*450;y=(i//4)*160;r=atom['rect'];crop=im.crop(tuple(round(v*4)for v in r))
   crop.thumbnail((440,105));sheet.paste(crop,(x+4,y+42));draw.text((x+4,y+3),row['id']+'/'+atom['id'],font=font,fill='black');draw.text((x+4,y+21),str(r),font=font,fill='black')
  sheet.save(P/f'atom-contact-{index+1}.png')
plan.write_text(json.dumps(q,ensure_ascii=False,indent=2),'utf8')
print(json.dumps([dict(id=r['id'],baseline=r['baseline'],iou=r.get('baseline_evidence',{}).get('iou'))for r in q['rows']],indent=2))

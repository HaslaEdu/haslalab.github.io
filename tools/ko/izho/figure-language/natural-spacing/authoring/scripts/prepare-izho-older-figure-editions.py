from pathlib import Path
import sys,json,hashlib,numpy as np,cv2
from PIL import Image,ImageDraw
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-older-figure-language');sys.path.insert(0,str(B/'engine'))
from build_figure_labels import build,OLD,PUB,sha
from audit_figure_labels import audit
from measure_source_labels import FIELDS
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
inv=json.loads((B/'source-inventory.json').read_text('utf8'));review=[];out=B/'source-label-roi-review';out.mkdir(exist_ok=True);sheet=Image.new('RGB',(600,520),'#ccc')
for i,field in enumerate(FIELDS):
 meta=next(r for r in inv if r['year']==2010 and r['page']==field['page']and r['image_index']==field['image']);path=Path(meta['path']);im=Image.open(path).convert('RGB');a=np.asarray(im.convert('L'));_,cc,stats,_=cv2.connectedComponentsWithStats((a<160).astype('uint8'),8);x0,y0,x1,y1=field['rect'];ids=set(map(int,np.unique(cc[y0:y1,x0:x1])))-{0};crossing=[]
 for ident in sorted(ids):
  x,y,w,h,n=map(int,stats[ident])
  if n>=2 and(x<x0 or y<y0 or x+w>x1 or y+h>y1):crossing.append(dict(id=ident,bbox=[x,y,x+w,y+h],pixels=n))
 assert not crossing,(field['id'],crossing)
 review.append(dict(id=field['id'],source_text=field['text'],source_crop_sha256=sha(path),rect=field['rect'],source_connected_components=len(ids),intersecting_nonword_components=crossing,source_only=True,passed=True))
 crop=im.crop(field['rect']);crop.save(out/(field['id']+'.png'));crop=crop.resize((crop.width*2,crop.height*2));crop.thumbnail((285,90));tile=Image.new('RGB',(300,130),'white');ImageDraw.Draw(tile).text((5,5),field['id'],fill='red');tile.paste(crop,(5,30));sheet.paste(tile,((i%2)*300,(i//2)*130))
sheet.save(out/'contact.png');save(out/'source-components.json',dict(labels=review,source_only=True,source_threshold=160,passed=True))
for year,count in [(2010,5),(2011,6)]:
 base=json.loads((PUB/f'tools/ko/izho/{year}/T/natural-spacing/publication.json').read_text('utf8'));pages=[];visual=[]
 for n in range(1,count+1):
  target=B/f'{year}/T/page{n:02}.pdf';changed=(year,n)in[(2010,2),(2010,3),(2011,3)]
  if not changed:build(year,n);audit(year,n)
  q=json.loads((B/f'{year}/T/qa/page{n:02}.audit.json').read_text('utf8'));assert q['passed']and q['proof_sha256']==sha(target)
  oldsha=next(p for p in base['page_proofs']if p['page']==n)['proof_sha256'];assert q['body_sha256']==oldsha
  if not changed:assert sha(target)==oldsha
  pages.append(dict(source_page=n,pdf=str(target),sha256=sha(target)))
  row=dict(page=n,source_page=n,proof_sha256=sha(target),body_sha256=oldsha,reviewed=True,original_math_and_body_unchanged=True,review_origin='Fresh complete774x1095 Poppler page visually inspected after figure-word translation'if changed else'Byte-identical previously reviewed full page; original frozen visual review and source audits are retained in the baseline publication')
  if changed:
   preview=B/f'inspection/final-label-previews/{year}-page{n:02}.png';row.update(image=str(preview),image_sha256=sha(preview),native_figure_lines_and_variables_reviewed=True,word_spacing_reviewed=True)
  visual.append(row)
 save(B/f'master-v1/{year}-assembly-spec.json',dict(output=str(B/f'master-v1/IZhO_{year}_T_KO.pdf'),proofs=pages))
 save(B/f'master-v1/{year}-visual-review.json',dict(year=year,pages=visual))
print('Eleven complete pages pinned; three changed pages actually visually inspected, eight prior reviewed pages byte-identical. Seven source-word regions are complete isolated components.')

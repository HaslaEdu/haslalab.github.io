from pathlib import Path
from PIL import Image,ImageDraw
import json,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
old=Image.open(B/'source-renders/page05.png').convert('RGB');new=Image.open(B/'proofs/ko/page05-preview.png').convert('RGB');assert old.size==new.size
rect=[110,270,822,682];a=old.crop(rect);b=new.crop(rect);out=Image.new('RGB',(a.width+b.width+18,a.height+25),'white');draw=ImageDraw.Draw(out);draw.text((3,5),'Original',fill='black');draw.text((a.width+21,5),'Korean',fill='black');out.paste(a,(0,25));out.paste(b,(a.width+18,25));target=B/'proofs/page05-source-vs-Korean-detail.png';out.save(target)
record=dict(source_sha256=hashlib.sha256((B/'inputs/CPhO_2005_Chinese_original.pdf').read_bytes()).hexdigest(),proof_sha256=hashlib.sha256((B/'proofs/ko/page05.pdf').read_bytes()).hexdigest(),preview_renderer='Poppler144dpi; cached MuPDF previews are not used.',source_rect_points=[55,135,411,341],comparison=str(target),comparison_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),publication_ready=False,whole_edition_complete=False)
target.with_suffix('.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n','utf8');print(target,flush=True)

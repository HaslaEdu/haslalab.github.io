from pathlib import Path
from collections import Counter
import hashlib,json,sys,shutil
import pymupdf as fitz
from PIL import Image,ImageDraw
import icho2019_write_guard as guard
BASE=Path(__file__).resolve().parent
if(BASE/'HOLD-OUTPUT').exists():print('2019 source output held for root publication disk space',flush=True);raise SystemExit(2)
sys.path.insert(0,str(BASE/'engine'));import latex_native_motion as motion
n=int(sys.argv[1]);assert 1<=n<=60
guard.assert_protected_2024()
if shutil.disk_usage(BASE).free<guard.MIN_FREE:raise SystemExit('256MiB metadata minimum reached')
doc=fitz.open(guard.SOURCE);page=doc[n-1];raw=page.get_text('rawdict');plain=page.get_text('text')
inventory=motion.inspect_inline_groups(guard.SOURCE,n)
fonts=page.get_fonts(full=True);styles=Counter((s['font'],round(s['size'],6),s['flags'],s['color'])for b in raw['blocks']for l in b.get('lines',[])for s in l['spans'])
tables=[]
for t in page.find_tables().tables:
    if t.row_count>=2 and t.col_count>=2:tables.append(dict(bbox=list(t.bbox),rows=t.row_count,columns=t.col_count,cells=[list(c)for c in t.cells if c],text=t.extract()))
data=dict(page=n,source=str(guard.SOURCE),source_sha256=guard.SOURCE_SHA,physical_page_rect=list(page.rect),pdf_metadata=doc.metadata,fonts=[list(f)for f in fonts],styles=[dict(font=k[0],point_size=k[1],flags=k[2],color=k[3],span_count=v)for k,v in styles.items()],images=[dict(xref=i['xref'],bbox=list(i['bbox']),width=i['width'],height=i['height'])for i in page.get_image_info(xrefs=True)],tables=tables,source_text=plain,source_text_sha256=hashlib.sha256(plain.encode()).hexdigest(),forms=[dict(path=f['path'],bbox=f['native_page_bbox'],glyph_count=len(f['glyphs']),raw_sha256=f['original_raw_sha256'],glyph_text=''.join(g['c']for g in f['glyphs']),own_vector_path_count=len(f['own_vector_paths']))for f in inventory.get('forms',[])],vector_path_count=len(inventory['vector_paths']))
out=BASE/'source-profile';out.mkdir(exist_ok=True);(out/f'page{n:02}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
if '--profile-only'in sys.argv or shutil.disk_usage(BASE.anchor).free<guard.MIN_FREE:
    print(json.dumps(dict(page=n,profile_saved=True,source_render_pending=True,font_types=sorted({f[2]for f in fonts}),forms=len(data['forms']),tables=len(tables),images=len(data['images'])),ensure_ascii=False),flush=True);raise SystemExit(0)
review=BASE/'source-review';review.mkdir(parents=True,exist_ok=True)
page.get_pixmap(matrix=fitz.Matrix(1.25,1.25),alpha=False).save(review/f'page{n:02}.png')
if n%2==0 and(review/f'page{n-1:02}.png').exists():
    images=[Image.open(review/f'page{k:02}.png').convert('RGB')for k in[n-1,n]];w=max(i.width for i in images)+12;h=max(i.height for i in images)+28;sheet=Image.new('RGB',(2*w,h),'#ddd');draw=ImageDraw.Draw(sheet)
    for i,im in enumerate(images):sheet.paste(im,(i*w+6,23));draw.text((i*w+6,6),f'IChO2019 ORIGINAL SOURCE page{n-1+i}',fill='black')
    sheet.save(review/f'panel{n//2:02}.png')
print(json.dumps(dict(page=n,font_types=sorted({f[2]for f in fonts}),forms=len(data['forms']),tables=len(tables),images=len(data['images'])),ensure_ascii=False),flush=True)

"""Audit actual inline-image extents against their PDF HTML clipping boxes."""
from pathlib import Path
import argparse,json
import pymupdf as fitz
from PIL import Image,ImageChops

def audit(manifest,pdf,lang,pages=None):
    data=json.loads(Path(manifest).read_text(encoding='utf8'));folder=Path(manifest).parent
    roots=[folder,*map(Path,data.get('asset_roots',[]))]
    doc=fitz.open(pdf);mapping={n-1:i for i,n in enumerate(pages)} if pages else {i:i for i in range(len(doc))}
    images={pi:page.get_image_info(hashes=True)for pi,page in enumerate(doc)}
    cache={};rows=[]
    for e in data['entries']:
        if e['page'] not in mapping:continue
        rect=fitz.Rect(e.get(lang+'_insert_rect',e.get('insert_rect',e['rect'])));rect.y0-=.7;rect.y1+=1
        for mi,m in enumerate(e['math']):
            if mi in e.get('preserved_math',[])or f'[[{mi}]]'not in e.get(lang,''):continue
            name=m['file']
            if name not in cache:
                path=next((root/name for root in roots if(root/name).is_file()),None)
                if path is None:raise FileNotFoundError(name)
                pix=fitz.Pixmap(path)
                im=Image.open(path).convert('RGBA');matte=Image.new('RGBA',im.size,'white');matte.alpha_composite(im)
                mask=matte.convert('RGB').convert('L').point(lambda z:255 if z<200 else 0)
                cache[name]=((fitz.Pixmap(pix,0)if pix.alpha else pix).digest,mask.getbbox(),im.size)
            digest,ink,size=cache[name]
            choices=[i for i in images[mapping[e['page']]]if i['digest']==digest]
            if not choices:rows.append({'id':e['id'],'math':mi,'missing_image':True});continue
            plausible=[i for i in choices if fitz.Rect(i['bbox']).intersects(rect)]
            if not plausible:
                rows.append({'id':e['id'],'math':mi,'ambiguous_digest_match':True});continue
            box=fitz.Rect(min(plausible,key=lambda i:abs((i['bbox'][1]+i['bbox'][3])/2-(rect.y0+rect.y1)/2))['bbox'])
            full=list(box)
            if ink:
                box=fitz.Rect(box.x0+ink[0]/size[0]*box.width,box.y0+ink[1]/size[1]*box.height,
                              box.x0+ink[2]/size[0]*box.width,box.y0+ink[3]/size[1]*box.height)
            over=[max(0,rect.x0-box.x0),max(0,rect.y0-box.y0),max(0,box.x1-rect.x1),max(0,box.y1-rect.y1)]
            if max(over)>.3:rows.append({'id':e['id'],'page':e['page']+1,'math':mi,'image':full,'ink':list(box),'clip_rect':list(rect),'overhang':over})
    return rows

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest',type=Path);p.add_argument('pdf',type=Path);p.add_argument('--lang',required=True);p.add_argument('--pages',nargs='*',type=int);p.add_argument('--output',type=Path)
    a=p.parse_args();rows=audit(a.manifest,a.pdf,a.lang,a.pages)
    value=json.dumps(rows,ensure_ascii=False,indent=2)
    if a.output:a.output.write_text(value,encoding='utf8')
    print(value)

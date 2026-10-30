"""Audit actual inline-image extents against their PDF HTML clipping boxes."""
from pathlib import Path
import argparse,json
import pymupdf as fitz

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
                pix=fitz.Pixmap(path);cache[name]=(fitz.Pixmap(pix,0)if pix.alpha else pix).digest
            choices=[i for i in images[mapping[e['page']]]if i['digest']==cache[name]]
            if not choices:rows.append({'id':e['id'],'math':mi,'missing_image':True});continue
            box=fitz.Rect(min(choices,key=lambda i:abs(fitz.Rect(i['bbox']).tl.y-rect.y0)+max(0,rect.x0-i['bbox'][0],i['bbox'][2]-rect.x1)*4)['bbox'])
            over=[max(0,rect.x0-box.x0),max(0,rect.y0-box.y0),max(0,box.x1-rect.x1),max(0,box.y1-rect.y1)]
            if max(over)>.75:rows.append({'id':e['id'],'page':e['page']+1,'math':mi,'image':list(box),'clip_rect':list(rect),'overhang':over})
    return rows

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest',type=Path);p.add_argument('pdf',type=Path);p.add_argument('--lang',required=True);p.add_argument('--pages',nargs='*',type=int);p.add_argument('--output',type=Path)
    a=p.parse_args();rows=audit(a.manifest,a.pdf,a.lang,a.pages)
    value=json.dumps(rows,ensure_ascii=False,indent=2)
    if a.output:a.output.write_text(value,encoding='utf8')
    print(value)

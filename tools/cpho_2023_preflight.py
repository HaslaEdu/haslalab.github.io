"""Fast prose fitting audit without repeatedly redacting the 36-page source."""
from pathlib import Path
import argparse,html,json,re
import pymupdf as fitz
import cpho_2023_build as builder
import pdf_layout_translate as layout

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepared',action='store_true');parser.add_argument('--pages',nargs='+',type=int);args=parser.parse_args()
    folder=builder.ROOT/'tmp/cpho-build/2023-reviewed' if args.prepared else builder.prepare()
    data=json.loads((folder/'translation.json').read_text(encoding='utf8'))
    archive=fitz.Archive(str(folder));archive.add(str(builder.BASE));archive.add(str(layout.FONT.parent));archive.add('C:/Windows/Fonts')
    rows=[]
    for lang in ['ko','en']:
        font='NotoSansKR-Regular.ttf' if lang=='ko' else 'times.ttf'
        css=f'@font-face{{font-family:Body;src:url({font});}}@font-face{{font-family:Korean;src:url(NotoSansKR-Regular.ttf);}}*{{font-family:Body,Korean;color:#000;}}body,p{{margin:0;padding:0;}}img{{vertical-align:middle;}}'
        doc=fitz.open()
        for e in data['entries']:
            if args.pages and e['page']+1 not in args.pages:continue
            p=doc.new_page(width=595.32,height=841.92);s=html.escape(e[lang]);height=0
            for mi,m in enumerate(e['math']):
                if mi in e.get('preserved_math',[]):continue
                f=min(1,e.get('math_cap',26)/m['height']);w,h=m['width']*f,m['height']*f;height=max(height,h)
                s=s.replace(f'[[{mi}]]',f'<img src="{m["file"]}" width="{w}" height="{h}">')
            leading=e.get('line_height',max(1.25,(height+2)/e['size']))
            r=fitz.Rect(e.get(lang+'_insert_rect',e.get('insert_rect',e['rect'])));r.y0-=.7;r.y1+=1
            spare,scale=p.insert_htmlbox(r,f'<p style="font-size:{e["size"]}pt;line-height:{leading};text-align:{e.get("align","left")}">{s}</p>',css=css,archive=archive,scale_low=.7)
            rows.append({'id':e['id'],'lang':lang,'scale':scale,'spare':spare,'size':scale*e['size']})
            if spare<0:print('FAIL',e['id'],lang,r,s,flush=True)
        doc.close()
    name='preflight'+(''.join('-'+str(n)for n in args.pages)if args.pages else'')+'.json'
    target=builder.ROOT/'tmp/cpho-build/2023-qa'/name;target.write_text(json.dumps(rows,indent=2),encoding='utf8')
    print('FAILURES',sum(x['spare']<0 for x in rows),'MIN',min(x['size']for x in rows if x['spare']>=0),flush=True)
if __name__=='__main__':main()

"""Independent Poppler rendering, outside-prose and visible native-ink checks."""
from pathlib import Path
import hashlib,json,math,subprocess
import cv2,numpy as np
from PIL import Image
import pymupdf as fitz
import cpho_2013_original_build as b
import cpho_2013_original_qa as q
import cpho_2013_original_raster_guard as witness
from pdf_white_raster_original_style import fill_rectangles,reviewed_backgrounds

OUT=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/poppler')

def render(path,number,target,dpi):
    proc=subprocess.run(['pdftoppm','-f',str(number),'-l',str(number),'-r',str(dpi),'-singlefile','-png',str(path),str(target)],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    return target.with_suffix('.png'),proc.stderr.decode('utf8',errors='replace')

def rgb(path):
    with Image.open(path)as im:return np.array(im.convert('RGB'))

def mask(shape,rects,scale):
    result=np.zeros(shape,bool)
    for x0,y0,x1,y1 in rects:
        result[max(0,math.floor(y0*scale)):min(shape[0],math.ceil(y1*scale)),max(0,math.floor(x0*scale)):min(shape[1],math.ceil(x1*scale))]=True
    return result

def audit(pages,kind,dpi=144):
    OUT.mkdir(parents=True,exist_ok=True);scale=dpi/72;report=dict(source_sha256=b.source.SOURCE_SHA,
        renderer='Poppler pdftoppm',dpi=dpi,prose_outline_antialias_allowance_px=1,pages=[],warnings=[],passed=True)
    for number in pages:
        source_png,warning=render(b.source.SOURCE,number,OUT/f'source-page{number:02}',dpi)
        if warning:report['warnings'].append(dict(file='source',page=number,warning=warning))
        original=rgb(source_png)
        native_pdf=b.BASE/'ko'/f'page{number:02}.control.pdf'
        raster=b.raster.plans(number,'ko')
        if raster:
            target=OUT/f'native-page{number:02}.pdf';witness.control(native_pdf,target,raster);native_pdf=target
        native_png,warning=render(native_pdf,1,OUT/f'native-page{number:02}',dpi);native=rgb(native_png)
        for language in ['ko','en']:
            path=b.BASE/language/f'page{number:02}.pdf';proof_png,warning=render(path,1,OUT/f'{language}-page{number:02}',dpi)
            if warning:report['warnings'].append(dict(file=path.name,language=language,page=number,warning=warning))
            translated=rgb(proof_png);page=b.data()['pages'][number-1];picked=q.selected(page)
            with fitz.open(b.source.SOURCE)as src,fitz.open(path)as doc:
                added=q.extra_glyphs(src[number-1],doc[0]);allowed=q.translation_ink_rects(doc,doc[0],added)
                allowed.extend([g['bbox'][0]-.25,g['bbox'][1]-.25,g['bbox'][2]+.25,g['bbox'][3]+.25]for g in picked)
                old=[];background=[];protected=[]
                if raster:
                    old,protected=fill_rectangles(raster,src[number-1].rect)
                    background=[r['rect']for r in reviewed_backgrounds(raster,src[number-1].rect,b.source.SOURCE_SHA)]
                    allowed.extend(list(r+(-.25,-.25,.25,.25))for r in old)
            prose=mask(original.shape[:2],allowed,scale);difference=(original!=translated).any(2)
            padded=cv2.dilate(prose.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
            unexpanded=difference&~prose;outside=difference&~padded
            language_mask=mask(prose.shape,[*old,*background],scale);explicit=mask(prose.shape,protected,scale)
            actual=(native.min(2)<250)&(~language_mask|explicit)
            changed_native=(native!=translated).any(2)&actual
            source_mixing=(original!=native).any(2)&actual
            row=dict(source_page=number,language=language,proof_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                outside_prose_pixels=int(outside.sum()),unexpanded_outline_fringe_pixels=int(unexpanded.sum()),
                changed_visible_native_ink_pixels=int(changed_native.sum()),original_prose_native_antialias_mix_pixels=int(source_mixing.sum()),
                preview=str(proof_png),native_control_preview=str(native_png))
            if outside.any():
                yy,xx=np.nonzero(outside);row['outside_bbox_pt']=[xx.min()/scale,yy.min()/scale,(xx.max()+1)/scale,(yy.max()+1)/scale]
            if changed_native.any():
                yy,xx=np.nonzero(changed_native);row['native_bbox_pt']=[xx.min()/scale,yy.min()/scale,(xx.max()+1)/scale,(yy.max()+1)/scale]
            row['passed']=not outside.any()and not changed_native.any();report['pages'].append(row);report['passed']&=row['passed']
            print(number,language,'outside',row['outside_prose_pixels'],'native',row['changed_visible_native_ink_pixels'],flush=True)
    (b.AUTHOR/f'qa-poppler-{kind}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=float),'utf8')
    return report

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=['T','TS'],default='T');a=p.parse_args()
    r=audit([1,2,3]if a.kind=='T'else list(range(4,15)),a.kind);raise SystemExit(not r['passed'])

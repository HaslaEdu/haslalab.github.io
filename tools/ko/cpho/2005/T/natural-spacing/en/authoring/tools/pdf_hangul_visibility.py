"""Independently render Hangul glyphs to find text hidden by PDF clips/overlays."""
from pathlib import Path
import argparse,json,hashlib,re,html
import numpy as np
import pymupdf as fitz
from PIL import Image,ImageFilter
from izho_native_math_audit import components
ROOT=Path(__file__).resolve().parents[1]

def audit(path,pages=None,scale=4):
    doc=fitz.open(path);rows=[]
    for pi,page in enumerate(doc):
        if pages and pi+1 not in pages:continue
        # Retain the PDF's actual glyph outlines and page coordinates while
        # removing all clipping groups and later white overlays. This handles
        # both Noto body text and the original SVG fallback fonts exactly.
        svg=page.get_svg_image(text_as_path=True);defs=re.search(r'<defs>[\s\S]*?</defs>',svg)
        uses=[];count=0
        for use in re.findall(r'<use\b[^>]*data-text=[^>]*?/?>',svg):
            match=re.search(r'data-text="([^"]*)"',use)
            if not match:continue
            value=html.unescape(match[1])
            if not re.search('[가-힣]',value):continue
            count+=sum(bool(re.search('[가-힣]',char)) for char in value)
            use=re.sub(r'\s(?:fill|stroke)="[^"]*"','',use)
            use=use.replace('/>',' fill="black" stroke="none"/>')
            uses.append(use)
        definition=re.sub(r'<image\b[^>]*?/?>','',defs[0]) if defs else '<defs/>'
        value=f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{page.rect.width}" height="{page.rect.height}" viewBox="0 0 {page.rect.width} {page.rect.height}">{definition}'+''.join(uses)+'</svg>'
        outline=fitz.open(stream=value.encode('utf8'),filetype='svg');expected_doc=fitz.open(stream=outline.convert_to_pdf(),filetype='pdf');expected_page=expected_doc[0]
        a=expected_page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY)
        b=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY)
        expected=np.frombuffer(a.samples,np.uint8).reshape(a.height,a.width)<80
        actual=np.frombuffer(b.samples,np.uint8).reshape(b.height,b.width)<170
        nearby=np.asarray(Image.fromarray(actual.astype(np.uint8)*255).filter(ImageFilter.MaxFilter(5)))>0
        missing=expected&~nearby;groups=components(missing)
        rows.append({'page':pi+1,'hangul_characters':count,'missing_pixels':int(missing.sum()),'clusters':groups})
        print(f'{path.name} p{pi+1}: {len(groups)} visible text loss candidates',flush=True);expected_doc.close();outline.close()
    return {'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'method':'independent original glyph outlines without clipping or overlays','scale':scale,
            'pixel_tolerance':2,'flagged_components':sum(len(row['clusters']) for row in rows),'pages':rows}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('pdf',type=Path)
    parser.add_argument('--pages',nargs='+',type=int)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();report=audit(args.pdf,args.pages)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print('Total candidates:',report['flagged_components']);raise SystemExit(bool(report['flagged_components']))

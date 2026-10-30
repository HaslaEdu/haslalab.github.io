"""Check native glyph and pixel preservation in an original-layout proof.

The JSON specification contains source_page/proof_page (1-based), allowed_rects
for the old/new prose ink only, and erased_glyph_origins from the text-operation
suppression journal. All other original glyphs must retain font, gid, size,
colour, and origin. Original figures and rules are checked by pixel comparison.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,math,re
import numpy as np
import pymupdf as fitz
import cv2

def glyphs(page):
    result=[]
    for span in page.get_texttrace():
        for char in span['chars']:
            code,gid,origin,box=char
            result.append(dict(c=chr(code)if 0<=code<=0x10ffff else str(code),gid=gid,
                font=re.sub(r'^[A-Z]{6}\+','',span['font']),size=span['size'],origin=list(origin),
                bbox=list(box),color=list(span['color']),render_type=span['type']))
    return result

def close_origin(a,b,tol=.03):return abs(a[0]-b[0])<=tol and abs(a[1]-b[1])<=tol

def key(g):
    return (g['c'],g['gid'],g['font'],round(g['size'],4),round(g['origin'][0],3),round(g['origin'][1],3),
            tuple(round(c,5)for c in g['color']),g['render_type'])


def whitespace_identity(g):
    """Exact actual-trace identity; never match synthetic/rawdict padding."""
    return (g['c'],re.sub(r'^[A-Z]{6}\+','',g['font']),float(g['size']),
            float(g['origin'][0]),float(g['origin'][1]))


def reviewed_prose_whitespace(old,spec):
    """Classify only explicitly selected, real prose whitespace as mutable.

    Physical/math/Form whitespace remains native. The caller's opt-in journal
    must exactly match the original trace and lie inside a prose frame.
    """
    journal=spec.get('mutable_prose_whitespace_glyphs',[])
    actual={whitespace_identity(g)for g in old if g['c'].isspace()}
    protected={whitespace_identity(g)for g in spec.get('protected_whitespace_glyphs',[])}
    result=set()
    for entry in journal:
        token=whitespace_identity(entry)
        if not entry['c'].isspace()or token not in actual:
            raise ValueError('Prose whitespace journal does not identify an actual source-trace whitespace glyph')
        if token in result:raise ValueError('Duplicate prose whitespace journal entry')
        if token in protected or re.search(r'Cambria.?Math|Symbol|MT.?Extra',entry['font'],re.I)or any(close_origin(entry['origin'],p)for p in spec.get('protected_glyph_origins',[])):
            raise ValueError('Prose whitespace journal touches protected native math/Form whitespace')
        if not any(fitz.Point(entry['origin'])in fitz.Rect(rect)for rect in spec['allowed_rects']):
            raise ValueError('Prose whitespace journal lies outside the explicit prose frames')
        result.add(token)
    return result

def native_ink_neighborhood(page,origins,scale):
    """Use actual outlines, avoiding the oversized source font metric boxes."""
    svg=page.get_svg_image(text_as_path=True)
    defs=re.search(r'<defs>[\s\S]*?</defs>',svg)
    definition=re.sub(r'<image\b[^>]*?/?>','',defs[0])if defs else '<defs/>'
    uses=[]
    for use in re.findall(r'<use\b[^>]*data-text=[^>]*?/?>',svg):
        match=re.search(r'transform="matrix\(([^)]+)\)"',use)
        if not match:continue
        values=[float(v)for v in match[1].replace(',',' ').split()]
        if not any(close_origin(values[-2:],p)for p in origins):continue
        use=re.sub(r'\s(?:fill|stroke)="[^"]*"','',use)
        uses.append(use.replace('/>',' fill="black" stroke="none"/>'))
    content=f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{page.rect.width}" height="{page.rect.height}">{definition}'+''.join(uses)+'</svg>'
    vector=fitz.open(stream=content.encode('utf8'),filetype='svg')
    native=fitz.open(stream=vector.convert_to_pdf(),filetype='pdf')
    pix=native[0].get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY)
    mask=(np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)<200).astype(np.uint8)
    count,labels,stats,centres=cv2.connectedComponentsWithStats(mask,connectivity=8)
    protected=np.zeros(mask.shape,bool)
    for x,y,w,h,pixels in stats[1:]:
        if pixels<2:continue
        protected[max(0,y-1):min(mask.shape[0],y+h+1),max(0,x-1):min(mask.shape[1],x+w+1)]=True
    native.close();vector.close()
    return protected,len(uses)

def audit(source_path,proof_path,spec,scale=4):
    source=fitz.open(source_path);proof=fitz.open(proof_path)
    a=source[spec['source_page']-1];b=proof[spec.get('proof_page',1)-1]
    assert a.rect==b.rect,(a.rect,b.rect)
    erased=spec.get('erased_glyph_origins',[])
    locked=spec.get('protected_glyph_origins',[])
    protected_erasure=[p for p in locked if any(close_origin(p,q)for q in erased)]
    old=glyphs(a);current=Counter(key(g)for g in glyphs(b));mutable_spaces=reviewed_prose_whitespace(old,spec)
    preserved=[g for g in old if whitespace_identity(g)not in mutable_spaces and(any(close_origin(g['origin'],p)for p in locked)or not any(close_origin(g['origin'],p)for p in erased))]
    missing=[]
    for g in preserved:
        token=key(g)
        if current[token]:current[token]-=1
        else:missing.append(g)
    aa=a.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False,colorspace=fitz.csRGB)
    bb=b.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False,colorspace=fitz.csRGB)
    before=np.frombuffer(aa.samples,np.uint8).reshape(aa.height,aa.width,3)
    after=np.frombuffer(bb.samples,np.uint8).reshape(bb.height,bb.width,3)
    difference=np.any(before!=after,axis=2);allowed=np.zeros(difference.shape,bool)
    for rect in spec['allowed_rects']:
        r=fitz.Rect(rect)
        x0=max(0,math.floor(r.x0*scale));x1=min(aa.width,math.ceil(r.x1*scale))
        y0=max(0,math.floor(r.y0*scale));y1=min(aa.height,math.ceil(r.y1*scale))
        allowed[y0:y1,x0:x1]=True
    outside=difference&~allowed
    protected,outline_count=native_ink_neighborhood(a,[g['origin']for g in preserved],scale)
    for rect in spec.get('protected_rects',[]):
        r=fitz.Rect(rect)
        x0=max(0,math.floor(r.x0*scale));x1=min(aa.width,math.ceil(r.x1*scale))
        y0=max(0,math.floor(r.y0*scale));y1=min(aa.height,math.ceil(r.y1*scale))
        protected[y0:y1,x0:x1]=True
    changed_native_ink=difference&protected
    report=dict(source=Path(source_path).name,proof=Path(proof_path).name,
        source_sha256=hashlib.sha256(Path(source_path).read_bytes()).hexdigest(),
        proof_sha256=hashlib.sha256(Path(proof_path).read_bytes()).hexdigest(),
        source_page=spec['source_page'],proof_page=spec.get('proof_page',1),scale=scale,
        native_glyphs_checked=len(preserved),native_glyphs_changed=missing,
        selected_prose_actual_whitespace_glyphs_checked=len(mutable_spaces),
        mutable_prose_whitespace_glyphs=spec.get('mutable_prose_whitespace_glyphs',[]),
        protected_glyph_origins_checked=len(locked),protected_glyphs_selected_for_erasure=protected_erasure,
        native_glyph_outlines_checked=outline_count,
        changed_pixels_in_native_glyph_neighborhood=int(changed_native_ink.sum()),
        changed_pixels_outside_prose=int(outside.sum()),allowed_page_area_fraction=float(allowed.mean()))
    if np.any(outside):
        ys,xs=np.nonzero(outside);report['outside_change_bbox']=[float(xs.min()/scale),float(ys.min()/scale),float((xs.max()+1)/scale),float((ys.max()+1)/scale)]
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('proof',type=Path);parser.add_argument('spec',type=Path)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--scale',type=int,default=4)
    args=parser.parse_args();report=audit(args.source,args.proof,json.loads(args.spec.read_text(encoding='utf8')),args.scale)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items()if k not in ['native_glyphs_changed']},ensure_ascii=False))
    print('changed native glyphs:',len(report['native_glyphs_changed']))
    raise SystemExit(bool(report['native_glyphs_changed']or report['protected_glyphs_selected_for_erasure']or report['changed_pixels_outside_prose']or report['changed_pixels_in_native_glyph_neighborhood']))

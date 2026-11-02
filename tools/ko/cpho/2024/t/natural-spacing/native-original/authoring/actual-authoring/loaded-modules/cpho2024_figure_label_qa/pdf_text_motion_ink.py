"""Actual resolved-glyph envelopes for auditing deliberate text movement.

This is an analysis mask only: it never modifies the source or proof. Include
every nonwhite SVG glyph sample, including faint antialiasing and one-pixel
components; source-font metric boxes are not used as ink substitutes.
"""
import re,math
from collections import defaultdict
import cv2
import numpy as np
import pymupdf as fitz

def _origin_selector(origins,tolerance=.001):
    """Select the same physical origin without decimal half-even aliases."""
    scale=1/tolerance;grid=defaultdict(list)
    for x,y in origins:grid[(math.floor(x*scale),math.floor(y*scale))].append((x,y))
    def selected(x,y):
        ix,iy=math.floor(x*scale),math.floor(y*scale)
        return any(abs(px-x)<=tolerance and abs(py-y)<=tolerance
            for dx in(-1,0,1)for dy in(-1,0,1)
            for px,py in grid.get((ix+dx,iy+dy),()))
    return selected

def ink_envelope(page,origins,scale=4):
    svg=page.get_svg_image(text_as_path=True)
    defs=re.search(r'<defs>[\s\S]*?</defs>',svg)
    definition=re.sub(r'<image\b[^>]*?/?>','',defs[0])if defs else'<defs/>'
    selected=_origin_selector(origins)
    uses=[]
    for use in re.findall(r'<use\b[^>]*data-text=[^>]*?/?>',svg):
        match=re.search(r'transform="matrix\(([^)]+)\)"',use)
        if not match:continue
        values=[float(v)for v in match[1].replace(',',' ').split()]
        if not selected(*values[-2:]):continue
        use=re.sub(r'\s(?:fill|stroke)="[^"]*"','',use)
        uses.append(use.replace('/>',' fill="black" stroke="none"/>'))
    text=f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{page.rect.width}" height="{page.rect.height}">{definition}'+''.join(uses)+'</svg>'
    vector=fitz.open(stream=text.encode('utf8'),filetype='svg')
    flat=fitz.open(stream=vector.convert_to_pdf(),filetype='pdf')
    pix=flat[0].get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY)
    ink=(np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)<255).astype(np.uint8)
    count,labels,stats,centres=cv2.connectedComponentsWithStats(ink,connectivity=8)
    envelope=np.zeros(ink.shape,bool)
    for x,y,w,h,pixels in stats[1:]:
        envelope[max(0,y-1):min(ink.shape[0],y+h+1),max(0,x-1):min(ink.shape[1],x+w+1)]=True
    flat.close();vector.close()
    return envelope,len(uses)

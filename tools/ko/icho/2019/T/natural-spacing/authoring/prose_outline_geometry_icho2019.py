"""True full-font glyph ink bounds in the same PDF shear convention as output."""
from pathlib import Path
import math
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
fonts={};bounds={}
def glyph_bounds(path,cp,angle):
    path=Path(path);key=(str(path),cp,angle)
    if key in bounds:return bounds[key]
    if str(path)not in fonts:fonts[str(path)]=TTFont(path,fontNumber=0 if path.suffix.lower()=='.ttc'else -1)
    font=fonts[str(path)];glyphset=font.getGlyphSet();name=font.getBestCmap()[cp];pen=BoundsPen(glyphset);transform=TransformPen(pen,(1,0,math.tan(math.radians(angle)),1,0,0));glyphset[name].draw(transform);r=pen.bounds
    if r is None:raise ValueError('Authored emphasized character has no full-font outline')
    bounds[key]=tuple(v/font['head'].unitsPerEm for v in r);return bounds[key]

def text_bounds(path,text,size,angle,metric,space):
    x=0;rects=[]
    for char in text:
        if not char.isspace():
            r=glyph_bounds(path,ord(char),angle);rects.append([x+r[0]*size,r[1]*size,x+r[2]*size,r[3]*size])
        x+=space if char==' 'else metric.text_length(char,fontsize=size)
    if not rects:raise ValueError('Emphasized phrase is empty')
    return[min(v[0]for v in rects),min(v[1]for v in rects),max(v[2]for v in rects),max(v[3]for v in rects)]

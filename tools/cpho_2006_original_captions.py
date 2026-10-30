"""Translate only the two raster Chinese caption characters in the source.

The stored original image streams, diagram lines, and number pixels are never
modified. Exact raster font metadata does not exist; point size and baseline
are inferred from the measured ink and the same-document native Song glyph.
"""
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
import numpy as np
import pymupdf as fitz

CAPTIONS=[
    {'number':1,'page':2,'source_ink':[389.875,686.625,396,693.375],
     'erase_rect':[388.5,685.5,397.5,694.5],'comparison_rect':[382,685,397.5,695.5],
     'baseline':692.64,'numeric_protected_rect':[398.5,686.5,403.5,693.5]},
    {'number':2,'page':2,'source_ink':[390,804.5,396,811.125],
     'erase_rect':[388.5,803.5,397.5,812.5],'comparison_rect':[382,803,397.5,813.5],
     'baseline':810.52,'numeric_protected_rect':[398.5,804.5,403.5,811.5]},
]
SIZE=7.44


def text_ink(path,text,size):
    font=TTFont(path);glyphs=font.getGlyphSet();mapping=font.getBestCmap();upem=font['head'].unitsPerEm
    pen=BoundsPen(glyphs);advance=0;rect=None
    for char in text:
        name=mapping[ord(char)];p=BoundsPen(glyphs);glyphs[name].draw(p)
        if p.bounds is not None:
            x0,y0,x1,y1=p.bounds;r=fitz.Rect((advance+x0)*size/upem,-y1*size/upem,
                                            (advance+x1)*size/upem,-y0*size/upem)
            rect=r if rect is None else rect|r
        advance+=font['hmtx'].metrics[name][0]
    font.close();return rect


def placement(font_path,lang,item):
    text='도'if lang=='ko'else'Fig.';ink=text_ink(font_path,text,SIZE)
    # Preserve the original right ink edge and the untouched gap to 1 or 2.
    origin=[item['source_ink'][2]-ink.x1,item['baseline']]
    return text,origin,list(fitz.Rect(ink.x0+origin[0],ink.y0+origin[1],ink.x1+origin[0],ink.y1+origin[1]))


def apply(doc,source,lang,font_path,pages=None):
    records=[]
    pages=pages or list(range(1,len(doc)+1))
    for item in CAPTIONS:
        if item['page']not in pages:continue
        original=source[item['page']-1];target=doc[pages.index(item['page'])]
        # The nominal background is white, with small JPEG ringing. Check its
        # actual range and preserve all pixels outside the language rectangle.
        pix=original.get_pixmap(matrix=fitz.Matrix(8,8),clip=fitz.Rect(item['erase_rect']),colorspace=fitz.csRGB)
        pixels=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)
        border=np.concatenate([pixels[0],pixels[-1],pixels[:,0],pixels[:,-1]])
        if np.min(border)<240 or np.max(np.ptp(border.astype(int),axis=1))>1:
            raise ValueError('Caption is not on the measured near-white neutral background')
        text,origin,ink=placement(font_path,lang,item)
        target.draw_rect(fitz.Rect(item['erase_rect']),color=None,fill=(1,1,1),overlay=True)
        target.insert_text(origin,text,fontsize=SIZE,fontname='CaptionTranslation',fontfile=str(font_path),color=(0,0,0))
        records.append({**item,'translation':text,'translation_origin':origin,'translation_ink':ink,
            'translation_font_size':SIZE,'background_border_min':border.min(axis=0).tolist(),
            'background_border_max':border.max(axis=0).tolist(),'background_border_median':np.median(border,axis=0).tolist(),
            'same_document_reference':'Native Song 图 at 12pt has actual outline ink height 10.828125pt.',
            'source_size_estimate_pt':fitz.Rect(item['source_ink']).height/10.828125*12,
            'font_metadata_limitation':'Raster captions have no font metadata. Song style, 7.44pt and the common baseline are inferred from ink measurements; the original number and all figure pixels outside this character region remain unchanged.'})
    return records

"""Reuse the older expert paper's exact embedded Korean outlines.

The full installed HCR font supplies missing explanation-only characters; every
character included in the official legacy subset is replaced with that source's
unchanged outline, scaled only between the fonts' units-per-em grids.
"""
from pathlib import Path
from functools import lru_cache
import io
import re
import pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from kphe_fonts import CACHE, font_path, _family

def unicode_cids(data):
    result = {}
    for block in re.findall(r'beginbfchar(.*?)endbfchar', data, re.S):
        for source, target in re.findall(r'<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>', block):
            result[int(target,16)] = int(source,16)
    for block in re.findall(r'beginbfrange(.*?)endbfrange', data, re.S):
        for start, end, target in re.findall(r'<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>',block):
            for offset, cid in enumerate(range(int(start,16),int(end,16)+1)):
                result[int(target,16)+offset] = cid
    return {code:cid for code,cid in result.items() if 32 <= code < 0xffff}

@lru_cache(None)
def legacy_body_font(source):
    target = CACHE/'HaansoftBatang-KPS-body-v1.ttf'
    if target.is_file(): return target
    pdf = fitz.open(source)
    xref = next(font[0] for font in pdf[0].get_fonts(full=True) if 'Haansoft' in font[3])
    src = TTFont(io.BytesIO(pdf.extract_font(xref)[3]))
    cmxref = int(pdf.xref_get_key(xref,'ToUnicode')[1].split()[0])
    cids = unicode_cids(pdf.xref_stream(cmxref).decode())
    descendant = int(pdf.xref_get_key(xref,'DescendantFonts')[1].split()[0][1:])
    mapping = pdf.xref_get_key(descendant,'CIDToGIDMap')[1]
    if mapping != '/Identity':
        raw = pdf.xref_stream(int(mapping.split()[0]))
        cids = {code:int.from_bytes(raw[cid*2:cid*2+2],'big') for code,cid in cids.items()}
    dst = TTFont(font_path('HCRBatang'))
    scale = dst['head'].unitsPerEm / src['head'].unitsPerEm
    glyphs, order, original_order = src.getGlyphSet(), list(dst.getGlyphOrder()), src.getGlyphOrder()
    for code, gid in cids.items():
        if gid >= len(original_order): continue
        name = f'KPS_{code:04X}'
        record = DecomposingRecordingPen(glyphs)
        glyphs[original_order[gid]].draw(record)
        pen = TTGlyphPen(None)
        record.replay(TransformPen(pen,(scale,0,0,scale,0,0)))
        dst['glyf'][name] = pen.glyph()
        advance, left = src['hmtx'][original_order[gid]]
        dst['hmtx'][name] = round(advance*scale),round(left*scale)
        order.append(name)
        for table in dst['cmap'].tables:
            if table.isUnicode(): table.cmap[code] = name
    dst.setGlyphOrder(order)
    dst['maxp'].numGlyphs = dst['hhea'].numberOfHMetrics = len(order)
    _family(dst,'Haansoft Batang KPS')
    dst.save(target)
    return target

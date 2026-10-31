"""Remove adjacent prose ink from a source crop without redacting mathematical fonts.

Some Word math fonts have enormous glyph boxes. Text redaction can therefore
delete an equation while targeting an adjacent English letter. An SVG outline
mask uses only the exact paths of the prose glyphs and leaves equation ink alone.
"""
import copy
import hashlib
import re
import xml.etree.ElementTree as ET
from PIL import Image, ImageFilter
import pymupdf as fitz
from izho_extract_word import candidate, mathword

_source_glyphs = {}


def math_pixmap(page, rect, protected_origins=()):
    key = (page.parent.name, page.number, hashlib.sha256(page.read_contents()).digest())
    if key not in _source_glyphs:
        positions = set()
        for block in page.get_text('rawdict')['blocks']:
            if block['type'] != 0:
                continue
            for line in block['lines']:
                for span in line['spans']:
                    text = ''.join(c['c'] for c in span['chars'])
                    words = re.findall('[A-Za-zА-Яа-яЁё]{2,}', text)
                    if not words or all(mathword(w) for w in words) or candidate({**span, 'text': text}):
                        continue
                    positions.update((round(c['origin'][0], 2), round(c['origin'][1], 2))
                                     for c in span['chars'] if c['c'].strip())
        svg = ET.fromstring(page.get_svg_image(text_as_path=True))
        ns = '{http://www.w3.org/2000/svg}'
        uses = []
        for use in svg.iter(ns+'use'):
            matrix = re.search(r'matrix\(([^)]+)\)', use.get('transform', ''))
            if not matrix:
                continue
            values = [float(v) for v in re.split(r'[,\s]+', matrix[1].strip())]
            if len(values) == 6:
                point = (round(values[4], 2), round(values[5], 2))
                uses.append((point, point in positions, copy.deepcopy(use)))
        _source_glyphs[key] = (svg.tag, svg.attrib, svg.findall(ns+'defs'), uses)
    pix = page.get_pixmap(matrix=fitz.Matrix(4, 4), clip=rect, alpha=False)
    bitmap = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    tag, attributes, definitions, uses = _source_glyphs[key]
    attributes = dict(attributes, width=str(pix.width/4), height=str(pix.height/4),
                      viewBox=f'{pix.x/4} {pix.y/4} {pix.width/4} {pix.height/4}')
    mask_svg = ET.Element(tag, attributes)
    for defs in definitions:
        mask_svg.append(copy.deepcopy(defs))
    protected = {(round(x, 2), round(y, 2)) for x, y in protected_origins}
    for point, prose, use in uses:
        if not (rect.x0-72 < point[0] < rect.x1+72 and rect.y0-72 < point[1] < rect.y1+72):
            continue
        # A neighbouring equation's descender may also intrude into this crop.
        # Its baseline is outside the reviewed formula rectangle.
        baseline_inside = (rect.x0-4 <= point[0] <= rect.x1+1 and
                           rect.y0-2 <= point[1] <= rect.y1+2)
        if (prose and point not in protected) or not baseline_inside:
            mask_svg.append(copy.deepcopy(use))
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
    mask_doc = fitz.open(stream=ET.tostring(mask_svg), filetype='svg')
    mask_pix = mask_doc[0].get_pixmap(matrix=fitz.Matrix(4, 4), colorspace=fitz.csGRAY, alpha=False)
    mask = Image.frombytes('L', (mask_pix.width, mask_pix.height), mask_pix.samples)
    mask = mask.point(lambda v: 255 if v < 248 else 0).filter(ImageFilter.MaxFilter(3))
    mask_doc.close()
    bitmap.paste('white', mask=mask)
    return bitmap, pix

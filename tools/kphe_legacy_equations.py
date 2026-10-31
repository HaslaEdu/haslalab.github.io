"""Retain HyhwpEQ outlines wherever the official typography profile uses them."""
from functools import lru_cache
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from kphe_fonts import CACHE, SYSTEM, equation_fonts, _family

@lru_cache(None)
def legacy_equation_fonts():
    source = TTFont(SYSTEM/'HYHWPEQ.TTF')
    source_map, glyphs = source.getBestCmap(), source.getGlyphSet()
    result = []
    for style, native in zip(('Roman','Italic'),equation_fonts()):
        path = CACHE/(native.stem.replace('HancomEQN','HyhwpEQ')+'-v1.ttf')
        result.append(path)
        if path.is_file(): continue
        font = TTFont(native)
        mapping = font.getBestCmap()
        assert source['head'].unitsPerEm == font['head'].unitsPerEm
        for code, name in mapping.items():
            if not 0xe000 <= code <= 0xe121 or code not in source_map: continue
            record = DecomposingRecordingPen(glyphs)
            glyphs[source_map[code]].draw(record)
            pen = TTGlyphPen(None)
            record.replay(pen)
            font['glyf'][name] = pen.glyph()
            font['hmtx'][name] = source['hmtx'][source_map[code]]
        _family(font,f'KPhE HyhwpEQ {style}')
        font.save(path)
    return tuple(result)

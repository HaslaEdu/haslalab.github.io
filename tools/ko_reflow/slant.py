# -*- coding: utf-8 -*-
"""Gently slanted Hangul faces for italic runs in the Korean editions.

The Korean system fonts have no italic, so Chrome would shear Hangul by about 14 degrees, which reads as a
distorted Latin italic. Where the original sets prose in italic (hints, quotations, notes) the Korean is set in a
copy of the upright face sheared by SLANT_DEG instead. Only Hangul, Korean punctuation and full-width forms are
kept; Latin and digits in the same run fall through to the Computer Modern italic.

The derived fonts are a local build cache (tools/ko_reflow/.cache, ignored by git): they are made from the
fonts installed with Windows and are never committed or published except as the subsets Chrome embeds in a PDF.
"""
import math, pathlib
from fontTools.ttLib import TTFont
from fontTools.subset import Subsetter, Options
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

SLANT_DEG = 8
CACHE = pathlib.Path(__file__).resolve().parent / '.cache'
RANGES = [(0x1100, 0x11FF), (0x3000, 0x303F), (0x3130, 0x318F), (0x3200, 0x32FF), (0xAC00, 0xD7A3), (0xFF00, 0xFFEF),
          (0x2018, 0x201F), (0x2026, 0x2026), (0x00B7, 0x00B7)]


def slanted(src):
    """Path of the slanted Hangul copy of the font file src, building it on first use."""
    src = pathlib.Path(src)
    out = CACHE / f'{src.stem}-slant{SLANT_DEG}.ttf'
    if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
        return out
    CACHE.mkdir(exist_ok=True)
    (CACHE / '.gitignore').write_text('*\n', encoding='utf-8')
    font = TTFont(src, lazy=False)
    opts = Options()
    opts.hinting = False
    opts.layout_features = ['*']
    opts.name_IDs = ['*']
    opts.notdef_outline = True
    sub = Subsetter(opts)
    sub.populate(unicodes=[u for a, b in RANGES for u in range(a, b + 1)])
    sub.subset(font)
    t = math.tan(math.radians(SLANT_DEG))
    gs = font.getGlyphSet()
    glyf = font['glyf']
    for name in font.getGlyphOrder():
        rec = DecomposingRecordingPen(gs)
        gs[name].draw(rec)
        pen = TTGlyphPen(None)
        rec.replay(TransformPen(pen, (1, 0, t, 1, 0, 0)))
        glyf[name] = pen.glyph()
    font['post'].italicAngle = -SLANT_DEG
    font['head'].macStyle |= 2
    font['OS/2'].fsSelection = (font['OS/2'].fsSelection | 1) & ~(1 << 6)
    tmp = out.with_suffix('.tmp')
    font.save(tmp)
    tmp.replace(out)
    return out


if __name__ == '__main__':
    import sys
    for f in sys.argv[1:]:
        print(slanted(f))

"""Use the original KPS font outlines, with a Unicode map for LaTeX math.

System font programs stay outside the repository. Only subset fonts embedded in
the resulting PDFs are distributed. HancomEQN's italic Latin/digit/Greek glyphs
are mapped from its original equation PUA slots to ordinary Unicode for MathText.
"""
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import os
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'tmp/kphe-native-fonts'
SYSTEM = Path(os.environ.get('KPHE_FONT_DIR', 'C:/Windows/Fonts'))
FILES = {'Gulim': ('gulim.ttc', 0), 'Batang': ('batang.ttc', 0),
         'BatangChe': ('batang.ttc', 1), 'Haansoft Batang': ('HANBatang.ttf', None),
         'HCRBatang': ('HANBatang.ttf', None), 'HCRDotum-Bold': ('HANDotumB.ttf', None),
         'HancomEQN': ('HancomEQN.ttf', None), 'TimesNewRomanPS-BoldMT': ('timesbd.ttf', None)}

@lru_cache(None)
def font_path(name):
    if name == 'KoPubDotumBold':
        path = CACHE / 'KoPubDotum-Bold.ttf'
        if not path.is_file():
            raise FileNotFoundError('Place the original KoPubDotum-Bold.ttf in tmp/kphe-native-fonts')
        return path
    filename, face = FILES[name]
    path = SYSTEM / filename
    if not path.is_file():
        raise FileNotFoundError(f'Original KPS font unavailable: {path}; set KPHE_FONT_DIR')
    if face is None:
        return path
    CACHE.mkdir(exist_ok=True)
    target = CACHE / f'{name}.ttf'
    if not target.is_file():
        TTFont(path, fontNumber=face).save(target)
    return target

def _family(font, family):
    for record in font['name'].names:
        if record.nameID in (1, 3, 4, 6, 16):
            value = family.replace(' ', '') if record.nameID == 6 else family
            record.string = value.encode(record.getEncoding(), errors='replace')

@lru_cache(None)
def equation_fonts():
    CACHE.mkdir(exist_ok=True)
    # Math labels need only the Korean characters used in these documents.
    chars = set()
    for path in sorted((ROOT / 'tools/kphe_solutions').glob('*.json')):
        chars.update(ch for ch in path.read_text(encoding='utf-8') if '가' <= ch <= '힣')
    signature = hashlib.sha256(''.join(sorted(chars)).encode()).hexdigest()[:10]
    roman, italic = (CACHE / f'HancomEQN-{signature}-{style}.ttf' for style in ('Roman', 'Italic'))
    if roman.is_file() and italic.is_file():
        return roman, italic
    original = TTFont(font_path('HancomEQN'))
    cmap = original.getBestCmap()
    # Add unchanged, scaled Gulim outlines solely for Korean subscript labels.
    korean = TTFont(font_path('Gulim'))
    kglyphs, kcmap = korean.getGlyphSet(), korean.getBestCmap()
    scale = original['head'].unitsPerEm / korean['head'].unitsPerEm
    order = list(original.getGlyphOrder())
    for ch in sorted(chars):
        code = ord(ch)
        if code in cmap or code not in kcmap:
            continue
        name = f'Gulim_{code:04X}'
        record = DecomposingRecordingPen(kglyphs)
        kglyphs[kcmap[code]].draw(record)
        pen = TTGlyphPen(None)
        record.replay(TransformPen(pen, (scale, 0, 0, scale, 0, 0)))
        original['glyf'][name] = pen.glyph()
        width, left = korean['hmtx'][kcmap[code]]
        original['hmtx'][name] = round(width * scale), round(left * scale)
        order.append(name)
        for table in original['cmap'].tables:
            if table.isUnicode(): table.cmap[code] = name
    original.setGlyphOrder(order)
    original['maxp'].numGlyphs = len(order)
    original['hhea'].numberOfHMetrics = len(order)
    # Hancom equation numbers have different slots from its text numbers.
    mapping = {ord(str(n)): 0xE033 + n if n else 0xE03D for n in range(10)}
    for table in original['cmap'].tables:
        if table.isUnicode():
            for code, private in mapping.items():
                if private in cmap: table.cmap[code] = cmap[private]
    _family(original, 'KPhE HancomEQN Roman')
    original.save(roman)
    # Exact italic letter outlines used in the official 2026 equation objects.
    mappings = {ord('A') + i: 0xE000 + i for i in range(26)}
    mappings.update({ord('a') + i: 0xE0E5 + i for i in range(26)})
    greek = 'αβγδεζηθικλμνξοπρστυφχψω'
    mappings.update({ord(ch): 0xE09D + i for i, ch in enumerate(greek)})
    for table in original['cmap'].tables:
        if table.isUnicode():
            for code, private in mappings.items():
                if private in cmap: table.cmap[code] = cmap[private]
    _family(original, 'KPhE HancomEQN Italic')
    original.save(italic)
    return roman, italic

def original_body(source):
    """Read measured original font profiles; canonical 2026 is Gulim."""
    if source and '2024_T2d' in str(source):
        return 'Haansoft Batang'
    return 'Gulim'

"""Strict original prose-family choices for repaired CPhO English editions.

Full fonts are read from licensed installed faces, never published as font
assets. Only verified glyph subsets are embedded as new translation resources.
Source PDF font programs and physical/mathematical glyphs remain untouched.
"""
from pathlib import Path
from functools import lru_cache
import hashlib, json, os
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = Path(os.environ.get('CPHO_EN_REPAIR_BASE', 'D:/CodexBuilds/Hasla-original-style-20261031/english-face-repair'))
CACHE = BUILD_ROOT / 'font-faces'
SIMSUN_TTC = Path('C:/Windows/Fonts/simsun.ttc')
SIMSUN_TTC_SHA = '1526ac24375f51f6eb73bc2d3f8072dbe4a80a3a65217677c9d9a84f67dab2ab'
SIMSUN_TTF_SHA = '79ba39fde98703ec0cd804ba1119b915f5e8f4e6663b2d729105b0f4c761ded6'


@lru_cache(maxsize=1)
def simsun():
    if hashlib.sha256(SIMSUN_TTC.read_bytes()).hexdigest() != SIMSUN_TTC_SHA:
        raise ValueError('Installed SimSun changed: review family, version and glyph outlines first')
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / 'SimSun-5.24.ttf'
    if not path.exists():
        font = TTFont(SIMSUN_TTC, fontNumber=0, recalcTimestamp=False)
        assert font['name'].getDebugName(1) == 'SimSun'
        assert font['name'].getDebugName(5) == 'Version 5.24'
        assert font['OS/2'].usWeightClass == 400
        assert not font['OS/2'].fsType & 0x0102
        font.save(path)
        font.close()
    if hashlib.sha256(path.read_bytes()).hexdigest() != SIMSUN_TTF_SHA:
        raise ValueError('Extracted installed SimSun cache does not match its verified original face')
    return path


def face(year, family, bold=False):
    if bold:
        raise ValueError('These original CPhO prose profiles have no real bold700 face')
    if family == 'serif':
        return simsun()
    if year == 2022:
        # Original title combines SimHei CJK with actual native Calibri Latin.
        # SimHei full face is absent; this is the same-run Latin counterpart.
        return Path('C:/Windows/Fonts/calibri.ttf')
    if year == 2007:
        # No installed/full embedded SimHei and no same-run Latin witness.
        # This explicit final fallback is recorded in the edition provenance.
        return Path('C:/Windows/Fonts/arial.ttf')
    raise ValueError('Unreviewed original prose family')


@lru_cache(maxsize=3)
def reviewed_spacing(year):
    path = ROOT / f'tools/ko/cpho/{year}/original/english-face-spacing.json'
    return json.loads(path.read_text(encoding='utf8')) if path.exists() else {}


def word_gap(slot, lang, year=None):
    """Explicit new English inter-word spacing; glyphs never change scale.

    SimSun's ASCII blank is half an em. New prose uses a quarter-em word
    space, matching the source document's Times Latin space. Reviewed local
    adjustments remain explicit in the original slot plans. Source operators
    and every unselected native whitespace glyph are kept exactly as-is.
    """
    adjustment = slot.get(lang + '_word_gap_adjustment', 0)
    if lang == 'en' and slot['family'] == 'serif':
        adjustment -= slot['size'] * .25
    if lang == 'en' and year is not None:
        adjustment += reviewed_spacing(year).get(slot['id'], 0)
    if lang == 'en' and slot['size'] * .5 + adjustment <= 0:
        raise ValueError('Non-positive English word space is forbidden')
    return adjustment


def verify_real_glyphs(path, text):
    """A nominal cmap/GID/advance alone cannot detect subset phantom glyphs."""
    with TTFont(path) as font:
        cmap = font.getBestCmap(); glyphs = font.getGlyphSet()
        failures = []
        for char in sorted(set(text)):
            if char in '\r\n\t':
                continue
            name = cmap.get(ord(char))
            if name is None or name == '.notdef':
                failures.append((char, 'missing actual cmap glyph'))
                continue
            if font['hmtx'].metrics[name][0] <= 0:
                failures.append((char, 'non-positive advance'))
            if char == ' ':
                continue
            pen = BoundsPen(glyphs); glyphs[name].draw(pen)
            if pen.bounds is None:
                failures.append((char, 'empty actual outline'))
        if failures:
            raise ValueError('Invalid new prose glyphs: ' + repr(failures))
        return dict(actual_nonspace_outlines_checked=len(set(text) - set(' \r\n\t')),
                    empty_actual_outlines=0, missing_glyphs=0, nonpositive_advances=0)

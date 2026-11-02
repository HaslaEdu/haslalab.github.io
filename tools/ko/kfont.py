"""Write new text with a font already embedded in a Korean overlay PDF (kserif/kserifb: HCR Batang subsets, Type0
Identity-H). The ToUnicode CMap of those fonts covers the whole font, but the embedded subset holds only the glyphs the
translation used, so a character is usable only when its glyph is really in the font file.

    f = KFont(doc, font_xref)            # the Type0 font object
    hexs, missing = f.encode('보정 자료')  # glyph ids as hex for a TJ string; missing = characters with no glyph
    f.width('보정 자료', 10)               # advance width in points
"""
import io
import re

import pymupdf
from fontTools.ttLib import TTFont


def _hex(s):
    return int(s, 16)


class KFont:
    def __init__(self, doc, xref):
        self.doc = doc
        o = doc.xref_object(xref)
        tu = int(re.search(r'/ToUnicode (\d+) 0 R', o).group(1))
        desc = int(re.search(r'/DescendantFonts \[ *(\d+) 0 R', o).group(1))
        self.u2c = {}
        cm = doc.xref_stream(tu).decode('latin1')
        for blk in re.findall(r'beginbfrange(.*?)endbfrange', cm, re.S):
            for a, b, c in re.findall(r'<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>', blk):
                for i in range(_hex(b) - _hex(a) + 1):
                    self.u2c.setdefault(chr(_hex(c) + i), _hex(a) + i)
        for blk in re.findall(r'beginbfchar(.*?)endbfchar', cm, re.S):
            for a, c in re.findall(r'<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>', blk):
                if len(c) <= 4:
                    self.u2c.setdefault(chr(_hex(c)), _hex(a))
        do = doc.xref_object(desc)
        self.dw = int(re.search(r'/DW (\d+)', do).group(1)) if '/DW' in do else 1000
        self.w = {}
        wm = re.search(r'/W (\d+) 0 R', do)
        wtxt = doc.xref_object(int(wm.group(1))) if wm else (re.search(r'/W \[(.*?)\]\s*/', do, re.S) or [None, ''])[1]
        toks = re.findall(r'\[|\]|[\d.]+', wtxt)
        i = 0
        while i < len(toks):
            if toks[i] in '[]':
                i += 1
                continue
            c0 = int(float(toks[i]))
            if toks[i + 1] == '[':
                j = i + 2
                k = 0
                while toks[j] != ']':
                    self.w[c0 + k] = float(toks[j])
                    k += 1
                    j += 1
                i = j + 1
            else:
                c1, wv = int(float(toks[i + 1])), float(toks[i + 2])
                for c in range(c0, c1 + 1):
                    self.w[c] = wv
                i += 3
        fd = int(re.search(r'/FontDescriptor (\d+) 0 R', do).group(1))
        ff = int(re.search(r'/FontFile2 (\d+) 0 R', doc.xref_object(fd)).group(1))
        tt = TTFont(io.BytesIO(doc.xref_stream(ff)))
        glyf = tt['glyf']
        order = tt.getGlyphOrder()
        self.has = set()
        for gid, name in enumerate(order):
            g = glyf[name]
            if getattr(g, 'numberOfContours', 0) != 0:
                self.has.add(gid)

    def cid(self, ch):
        return self.u2c.get(ch)

    def encode(self, text):
        out, missing = [], []
        for ch in text:
            c = self.cid(ch)
            if c is None or (c not in self.has and not ch.isspace()):
                missing.append(ch)
                continue
            out.append('%04x' % c)
        return ''.join(out).encode(), missing

    def width(self, text, size):
        return sum(self.w.get(self.cid(ch), self.dw) for ch in text if self.cid(ch) is not None) * size / 1000


def font_xref(doc, page, resname):
    """xref of the font named resname (e.g. 'kserif') in the page's overlay form resources"""
    seen = set()
    todo = [page.xref]
    while todo:
        x = todo.pop()
        if x in seen:
            continue
        seen.add(x)
        o = doc.xref_object(x)
        m = re.search(r'/%s (\d+) 0 R' % re.escape(resname), o)
        if m and '/Font' in doc.xref_object(int(m.group(1))) and '/Type0' in doc.xref_object(int(m.group(1))):
            return int(m.group(1))
        todo += [int(v) for v in re.findall(r'(\d+) 0 R', o)][:200]
    return None

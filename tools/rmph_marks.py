"""RMPh Korean papers (python3 tools/rmph_marks.py <in.pdf> <out.pdf>): the marks read like the original (pt, not 점) and sit where the original has them — in a mark
cell, centred in it (the original centres «1.5 p» in the cell), elsewhere in place."""
import pymupdf, re, sys
pymupdf.TOOLS.set_small_glyph_heights(True)   # glyph boxes as tall as the font size: nothing above or below is caught
PAT = re.compile(r"[\(\[]?\s*(\d+(?:[.,]\d+)?)\s*점\s*[\)\]]?")
def segs(page):
    """the page's ruling: horizontal and vertical segments (lines, and rectangles' edges)"""
    H, V = [], []
    for d in page.get_drawings():
        for it in d["items"]:
            if it[0] == "l":
                p, q = it[1], it[2]
                if abs(p.y - q.y) < 0.8: H.append((min(p.x, q.x), max(p.x, q.x), (p.y + q.y) / 2))
                elif abs(p.x - q.x) < 0.8: V.append((min(p.y, q.y), max(p.y, q.y), (p.x + q.x) / 2))
            elif it[0] == "re":
                r = pymupdf.Rect(it[1])
                if r.height < 1.5: H.append((r.x0, r.x1, (r.y0 + r.y1) / 2))
                elif r.width < 1.5: V.append((r.y0, r.y1, (r.x0 + r.x1) / 2))
                else:
                    H += [(r.x0, r.x1, r.y0), (r.x0, r.x1, r.y1)]; V += [(r.y0, r.y1, r.x0), (r.y0, r.y1, r.x1)]
    return H, V
def cell_of(box, H, V):
    """the cell a mark is drawn in: the nearest rules above, below, left and right of it, if all four exist"""
    cx, cy = (box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2
    up = [y for x0, x1, y in H if x0 - 1 <= cx <= x1 + 1 and y <= box.y0 + 1]
    dn = [y for x0, x1, y in H if x0 - 1 <= cx <= x1 + 1 and y >= box.y1 - 1]
    lf = [x for y0, y1, x in V if y0 - 1 <= cy <= y1 + 1 and x <= box.x0 + 1]
    rt = [x for y0, y1, x in V if y0 - 1 <= cy <= y1 + 1 and x >= box.x1 - 1]
    if not (up and dn and lf and rt): return None
    r = pymupdf.Rect(max(lf), max(up), min(rt), min(dn))
    return r if r.width < 140 and r.height < 400 else None
def fix(src, dst):
    doc = pymupdf.open(src); n = 0
    for page in doc:
        H, V = segs(page)
        # second pass with character boxes: locate each mark precisely
        raw = page.get_text("rawdict")
        marks = []
        for b in raw["blocks"]:
            for l in b.get("lines", []):
                # a glyph's box from its baseline and the font size (the CJK fonts report boxes three lines tall)
                cs = [(c["c"], pymupdf.Rect(c["bbox"][0], c["origin"][1] - 0.78 * s["size"], c["bbox"][2], c["origin"][1] + 0.18 * s["size"]),
                       s["size"], bool(s["flags"] & 16) or bool(re.search(r"Bold|Black|Heavy", s["font"])), c["origin"]) for s in l["spans"] for c in s["chars"]]
                text = "".join(c[0] for c in cs)
                for m in PAT.finditer(text):
                    box = pymupdf.Rect(cs[m.start()][1])
                    for c in cs[m.start():m.end()]: box |= c[1]
                    whole = m.group(0).strip()
                    opener = whole[0] if whole[0] in "([" else ""
                    closer = whole[-1] if whole[-1] in ")]" else ""
                    k = m.start() + (1 if opener else 0)          # the first digit: its baseline and weight
                    bold = cs[k][3]
                    marks.append((box, f"{opener}{m.group(1)} pt{closer}", cs[k][2], text.strip() == whole, cs[k][4][1], bold))
        # a mark set on two lines in a narrow cell: «0.60» above «점»
        lines = [(("".join(c[0] for c in cs)).strip(), cs) for cs in
                 ([(c["c"], pymupdf.Rect(c["bbox"][0], c["origin"][1] - 0.78 * s["size"], c["bbox"][2], c["origin"][1] + 0.18 * s["size"]),
                    s["size"], bool(s["flags"] & 16) or bool(re.search(r"Bold|Black|Heavy", s["font"])), c["origin"])
                   for s in l["spans"] for c in s["chars"]] for b in raw["blocks"] for l in b.get("lines", []))]
        for i, (t, cs) in enumerate(lines):
            if t != "점" or not cs: continue
            unit = [c for c in cs if c[0] == "점"][0]
            for t2, cs2 in lines:
                if re.fullmatch(r"\d+(?:[.,]\d+)?", t2) and cs2:
                    nb = pymupdf.Rect(cs2[0][1]);  [nb.include_rect(c[1]) for c in cs2]
                    if abs((nb.x0 + nb.x1) / 2 - (unit[1].x0 + unit[1].x1) / 2) < 25 and 0 < unit[1].y0 - nb.y0 < 2.2 * unit[2]:
                        box = nb | unit[1]
                        marks.append((box, f"{t2} pt", cs2[0][2], True, cs2[0][4][1], cs2[0][3]))
                        break
        if not marks: continue
        for box, new, size, alone, base, bold in marks:
            page.add_redact_annot(box + (-0.3, 0, 0.3, 0))
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
        for box, new, size, alone, base, bold in marks:
            font = "tibo" if bold else "tiro"
            w = pymupdf.get_text_length(new, fontname=font, fontsize=size)
            cell = None
            if alone:   # a mark by itself on its line: the cell it is drawn in
                cell = cell_of(box, H, V)
            if cell:
                x = cell.x0 + (cell.width - w) / 2; y = cell.y0 + cell.height / 2 + size * 0.35
            else:
                x = box.x0; y = base
            page.insert_text((x, y), new, fontname=font, fontsize=size, color=(0, 0, 0))
            n += 1
    doc.save(dst, garbage=3, deflate=True); return n
if __name__ == "__main__":
    print(fix(sys.argv[1], sys.argv[2]))

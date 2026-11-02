"""Finish the ISPhO answer and working sheets after tools/olydoc/docs/ispho-sheets.cjs is built.

    python3 -I tools/olydoc/ispho_sheets.py

1. 2023–2025: each problem's answer sheets joined into the whole paper's (ISPhO_<y>_TA.pdf, _T_A_KO.pdf), as the
   official 2026 TA.pdf is (A1-1 … A3-n); 2024–2026: the working sheets of the three problems joined into one
   (ISPhO_<y>_T_W.pdf, _T_W_KO.pdf, W1-1 … W3-3), the per-problem files removed.
2. 2026: the Korean theory answer sheets keep «Theory» in English at the top left, as the official translations do
   (the overlay had «이론»); the official English answer sheets get the scanner's corner squares too (site copies
   in pdfx/ispho); the experiment's answer sheet is translated into Korean in place (title, part headings, «(0.2점)»,
   the language) — every table and graph grid stays the official one.

Coordinates are those of the official 2026 sheets (see stamp.py «ispho»).
"""
import os, re, sys
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from stamp import markers, text, F  # noqa: E402

PX = os.path.join(ROOT, "pdfx/ispho")
SHEETS = os.path.join(ROOT, "sim/sheets")
KO_LABEL = "Korean (Korea (Republic of))"


def save(doc, path):
    doc.subset_fonts()
    tmp = path + ".tmp"
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    os.replace(tmp, path)


def join(parts, out, remove=False):
    if not all(os.path.exists(p) for p in parts):      # already joined (the per-problem working sheets are removed)
        return
    doc = pymupdf.open()
    for p in parts:
        doc.insert_pdf(pymupdf.open(p))
    save(doc, out)
    if remove:
        for p in parts:
            os.remove(p)
    print("joined", os.path.relpath(out, ROOT), len(parts))


def has_markers(page):
    W, H = page.rect.width, page.rect.height
    return any(abs(r["rect"].x0 + r["rect"].width / 2 - 0.045 * W) < 2 and abs(r["rect"].y0 + r["rect"].height / 2 - 0.035 * H) < 2
               for r in page.get_drawings() if r.get("fill") == (0.0, 0.0, 0.0))


def mark(src, dst):
    doc = pymupdf.open(src)
    for page in doc:
        if not has_markers(page):
            markers(page)
    save(doc, dst)


COVER = pymupdf.Rect(55.5, 88.5, 112, 110.2)


def theory_header(path):
    """the Korean 2026 sheets: «이론» → «Theory» (NotoSans Bold 14.17 pt at (56.7, 106.1), as the English sheets);
    a page that already has the white cover is left as it is"""
    doc = pymupdf.open(path)
    for page in doc:
        if any(d.get("fill") == (1.0, 1.0, 1.0) and abs(d["rect"].x0 - COVER.x0) < 0.1 and abs(d["rect"].y1 - COVER.y1) < 0.1 for d in page.get_drawings()):
            continue
        page.draw_rect(COVER, color=None, fill=(1, 1, 1))
        text(page, 56.7, 106.1, "Theory", "nsb", 14.17)
    save(doc, path)


KO_2026_E1 = {
    "Fiber Bragg grating": "광섬유 브래그 격자",
    "Part A. FBG fabrication technology (5.0 points)": "Part A. FBG 제작 기술 (5.0점)",
    "Part B. Coupled mode theory (2.9 points)": "Part B. 결합 모드 이론 (2.9점)",
    "Part C. Calibration of an FBG temperature sensor (2.9 points)": "Part C. FBG 온도 센서의 교정 (2.9점)",
    "Part D. Using the FBG temperature sensor (2.4 points)": "Part D. FBG 온도 센서의 사용 (2.4점)",
    "Part E. FBG dynamometer (3.9 points)": "Part E. FBG 동력계 (3.9점)",
    "Part F. Birefringence in FBG (2.9 points)": "Part F. FBG에서의 복굴절 (2.9점)",
}


def translate(src, dst, table):
    """each span to translate is covered with white and set again in Korean at its own baseline, size and colour"""
    doc = pymupdf.open(src)
    left = set(table)
    for page in doc:
        jobs = []
        for b in page.get_text("dict")["blocks"]:
            for line in b.get("lines", []):
                for s in line["spans"]:
                    t = s["text"]
                    bold = "Bold" in s["font"]
                    rgb = tuple(((s["color"] >> k) & 255) / 255 for k in (16, 8, 0))
                    if t.strip() in table:
                        jobs.append((s, table[t.strip()], "krb" if bold else "kr", rgb, "left")); left.discard(t.strip())
                    elif re.fullmatch(r"\s*\((\d+(?:\.\d+)?)pt\)", t):
                        jobs.append((s, " (%s점)" % re.search(r"[\d.]+", t).group(0), "kr", rgb, "left"))
                    elif t.strip() == "English (Official)":
                        jobs.append((s, KO_LABEL, "ns", rgb, "right"))
        for s, ko, key, rgb, align in jobs:
            r = pymupdf.Rect(s["bbox"])
            page.draw_rect(pymupdf.Rect(r.x0 - 0.3, r.y0 + 0.5, r.x1 + 0.5, r.y1 + 0.6), color=None, fill=(1, 1, 1))
        for s, ko, key, rgb, align in jobs:
            x, y = s["origin"]
            if align == "right":
                text(page, 536.0, y, ko, key, s["size"], "right", rgb)
            else:
                text(page, x, y, ko, key, s["size"], "left", rgb)
    assert not left, left
    save(doc, dst)


def main():
    # 1. the whole paper's answer sheets, and one working sheet per year
    for y in (2025, 2024, 2023):
        join([f"{PX}/ISPhO_{y}_T{q}A.pdf" for q in (1, 2, 3)], f"{PX}/ISPhO_{y}_TA.pdf")
        join([f"{PX}/ISPhO_{y}_T{q}_A_KO.pdf" for q in (1, 2, 3)], f"{PX}/ISPhO_{y}_T_A_KO.pdf")
    for y in (2026, 2025, 2024):
        join([f"{PX}/ISPhO_{y}_T{q}W.pdf" for q in (1, 2, 3)], f"{PX}/ISPhO_{y}_T_W.pdf", remove=True)
        join([f"{PX}/ISPhO_{y}_T{q}_W_KO.pdf" for q in (1, 2, 3)], f"{PX}/ISPhO_{y}_T_W_KO.pdf", remove=True)
    # 2. ISPhO 2026
    for name in ("ISPhO_2026_T_A_KO.pdf", "ISPhO_2026_T1_A_KO.pdf", "ISPhO_2026_T2_A_KO.pdf", "ISPhO_2026_T3_A_KO.pdf"):
        theory_header(f"{PX}/{name}")
        print("Theory header", name)
    for name in ("ISPhO_2026_TA.pdf", "ISPhO_2026_T_A_KO.pdf", "ISPhO_2026_T1_A_KO.pdf", "ISPhO_2026_T2_A_KO.pdf", "ISPhO_2026_T3_A_KO.pdf"):
        mark(f"{PX}/{name}", f"{PX}/{name}")
    # the per-problem official English sheets, marked: cut from the marked whole-paper sheet (A1-1 … A3-3)
    whole = pymupdf.open(f"{PX}/ISPhO_2026_TA.pdf")
    starts = [i for i, p in enumerate(whole) if re.search(r"A\d-1\b", p.get_text())]
    for q, (a, b) in enumerate(zip(starts, starts[1:] + [len(whole)]), 1):
        d = pymupdf.open()
        d.insert_pdf(whole, from_page=a, to_page=b - 1)
        save(d, f"{PX}/ISPhO_2026_T{q}A.pdf")
        print("cut", f"ISPhO_2026_T{q}A.pdf", b - a, "pages")
    translate(f"{SHEETS}/ISPhO_2026_E1_AS.pdf", f"{SHEETS}/ISPhO_2026_E1_AS_KO.pdf", KO_2026_E1)
    print("translated ISPhO_2026_E1_AS_KO.pdf")


if __name__ == "__main__":
    main()

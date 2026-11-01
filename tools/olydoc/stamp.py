"""Print the running head and foot of an olympiad's own documents onto a body typeset by tools/olydoc/build.cjs.

    python3 -I tools/olydoc/stamp.py JOBS.json

Each job: {pdf, style, kind, lang, code, langLabel, section?}.  Positions, sizes and fonts are those measured on the
edition's official PDFs (IPhO 2017 papers / answer sheets / solutions, APhO 2018 papers / answer sheets / solutions),
in PDF points from the top left of an A4 page.  Answer and working sheets also get the scanner's four corner squares
(7 mm, centred at labscan/scanner.js MARKER_INSET).
"""
import json, os, sys
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
IMG = os.path.join(HERE, "img")
F = {
    "dv": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "dvb": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "ns": os.path.join(ROOT, "tools/ko/fonts/NotoSans-Regular.ttf"),
    "nsb": os.path.join(ROOT, "tools/ko/fonts/NotoSans-Bold.ttf"),
    "krb": os.path.join(ROOT, "tools/ko/fonts/NotoSansKR-Bold.ttf"),
    "kr": os.path.join(ROOT, "tools/ko/fonts/NotoSansKR-Regular.ttf"),
}
INSET = (0.045, 0.035, 0.955, 0.965)
SIDE = 7 / 25.4 * 72


OBLIQUE = {"dvo": "dv", "dvbo": "dvb"}   # DejaVu's oblique faces are not installed: the upright ones, slanted 12°


def font(key):
    return pymupdf.Font(fontfile=F[OBLIQUE.get(key, key)])


def text(page, x, y, s, key, size, align="left", color=(0, 0, 0)):
    """s at baseline y; x is the left edge, the right edge (align=right) or the centre (align=center)"""
    f = font(key)
    w = f.text_length(s, fontsize=size)
    x0 = x - w if align == "right" else x - w / 2 if align == "center" else x
    base = OBLIQUE.get(key, key)
    morph = (pymupdf.Point(x0, y), pymupdf.Matrix(1, 0, -0.21, 1, 0, 0)) if key in OBLIQUE else None
    page.insert_text((x0, y), s, fontsize=size, fontname=base, fontfile=F[base], color=color, morph=morph)
    return w


def image(page, name, rect, behind=False):
    page.insert_image(pymupdf.Rect(*rect), filename=os.path.join(IMG, name), overlay=not behind, keep_proportion=True)


def markers(page):
    W, H = page.rect.width, page.rect.height
    for u, v in ((INSET[0], INSET[1]), (INSET[2], INSET[1]), (INSET[0], INSET[3]), (INSET[2], INSET[3])):
        cx, cy = u * W, v * H
        page.draw_rect(pymupdf.Rect(cx - SIDE / 2, cy - SIDE / 2, cx + SIDE / 2, cy + SIDE / 2), color=None, fill=(0, 0, 0))


def ipho2017(page, i, n, job):
    """(the watermark image is stored at the 20 % opacity the official pages print it with)
    paper / answer sheet: «Theory» 16 pt bold at (51, 55), the language 11 pt at (51, 73), «T4» 27 pt to x = 543
    at baseline 65; the IPhO 2017 watermark behind the middle; «page i of n» 8 pt oblique centred at 791"""
    image(page, "ipho2017-watermark.png", (145.5, 319.5, 449.2, 522.8), behind=True)
    text(page, 51, 55, job.get("section", "Theory"), "dvb", 16)
    text(page, 51, 73, job["langLabel"], "kr" if not job["langLabel"].isascii() else "dv", 11)
    text(page, 543, 65, job["code"], "dv", 27, "right")
    a = "page "
    parts = [(a, "dvo"), (str(i), "dvbo"), (" of ", "dvo"), (str(n), "dvbo")]
    total = sum(font(k).text_length(s, fontsize=8) for s, k in parts)
    x = 297.6 - total / 2
    for s, k in parts:
        x += text(page, x, 791, s, k, 8)


def ipho2017sol(page, i, n, job):
    """solutions: «Solutions/ Marking Scheme» (Korean «풀이 / 채점 기준») 15.6 pt bold in two lines centred on x = 131,
    the ministry and IPhO 2017 logos, «T4» 27 pt at x = 459, a 3.7 pt slate rule; «Page i of n» under a hairline"""
    image(page, "ipho2017-watermark.png", (145.5, 319.5, 449.2, 522.8), behind=True)
    ko = job["lang"] == "ko"
    l1, l2 = ("풀이 /", "채점 기준") if ko else ("Solutions/", "Marking Scheme")
    key = "krb" if ko else "dvb"
    text(page, 131, 100, l1, key, 15.6 if ko else 14, "center")
    text(page, 131, 119, l2, key, 15.6 if ko else 14, "center")
    image(page, "ipho2017-ministry.png", (249.8, 70.5, 299.2, 126.8))
    image(page, "ipho2017-logo.png", (299.2, 77.2, 369.8, 126.8))
    text(page, 459, 100, job["code"], "dv", 27.2)
    page.draw_rect(pymupdf.Rect(67.5, 135.8, 530.2, 139.5), color=None, fill=(0.2667, 0.3294, 0.4392))
    page.draw_line((68.2, 747.4), (526.5, 747.4), color=(0, 0, 0), width=0.8)
    text(page, 297.6, 759, f"Page {i} of {n}", "dvo", 9.5, "center")


def apho2018(page, i, n, job):
    """paper / answer sheet: «Theory» 14.2 pt bold at (56.7, 41.2), the APhO 2018 logo, «Q4-i» / «A4-i» 56.7 pt bold to
    x = 538.6 at baseline 108.4 (answer sheets: 45.4 pt at 87.8), the language 10 pt to x = 536 at baseline 127.6, a 2 pt rule at y = 132"""
    text(page, 56.7, 41.2, job.get("section", "Theory"), "nsb", 14.17)
    image(page, "apho2018-logo.png", (56.7, 52.4, 127.6, 127.4))
    paper = job["kind"] == "paper"
    text(page, 538.6, 108.4 if paper else 87.8, f"{job['code']}-{i}", "nsb", 56.7 if paper else 45.4, "right")
    text(page, 536, 127.6, job["langLabel"], "ns", 9.97, "right")
    page.draw_line((56.7, 132), (538.6, 132), color=(0, 0, 0), width=2)


def apho2018sol(page, i, n, job):
    """solutions: «Page i» 11 pt centred at baseline 818"""
    text(page, 297.6, 818, f"Page {i}", "ns", 11, "center")


STYLES = {"ipho2017": ipho2017, "ipho2017sol": ipho2017sol, "apho2018": apho2018, "apho2018sol": apho2018sol}


def stamp(job):
    doc = pymupdf.open(job["pdf"])
    n = len(doc)
    for k, page in enumerate(doc):
        STYLES[job["style"]](page, k + 1, n, job)
        if job["kind"] in ("answer", "working"):
            markers(page)
    tmp = job["pdf"] + ".tmp"
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    os.replace(tmp, job["pdf"])


if __name__ == "__main__":
    for job in json.load(open(sys.argv[1])):
        stamp(job)

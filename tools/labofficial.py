"""The officially published answer and working sheets of the experiments in exam mode, ready to print (sim/sheets/).

    python3 -I tools/labofficial.py OFFICIAL_DIR GROUPS.json sim/sheets

OFFICIAL_DIR holds the downloaded PDFs and manifest.json: [{comp, year, task, kind: answer|working, file, pages
("16-25" or null), source_url, language, note}].  GROUPS.json lists the experiments of exam mode (key, y, task).
For each sheet the pages that belong to it are cut out and, where the four corners of a page are blank and the page
is A4, the scanner's corner squares (7 mm, centred as labscan/scanner.js MARKER_INSET expects) are printed onto it,
so a photographed page is straightened from them; nothing else on the official sheet is touched.
Writes <dir>/<Comp>_<year>_<task>_<AS|WS>[n].pdf and <dir>/index.json:
{"ipho2024": {"E1": {"answer": [{"file", "pages", "marked", "src"}], "working": [...]}}}.
"""
import io, json, os, subprocess, sys, tempfile
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

INSET = {"left": 0.045, "top": 0.035, "right": 0.955, "bottom": 0.965}
SIDE = 7 * mm


def rng(spec, n):
    if not spec:
        return list(range(n))
    a, _, b = spec.partition("-")
    return list(range(int(a) - 1, int(b or a)))


def corners_blank(pdf, i, w, h):
    """render the page small and look at a 13 mm box round each marker centre: nothing printed there"""
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftoppm", "-f", str(i + 1), "-l", str(i + 1), "-r", "40", "-gray", "-singlefile", pdf, d + "/p"], check=True, capture_output=True)
        raw = open(d + "/p.pgm", "rb").read()
    parts = raw.split(b"\n", 3)
    W, H = map(int, parts[1].split()); px = parts[3]
    half = 6.5 / 25.4 * 40
    for u, v in ((INSET["left"], INSET["top"]), (INSET["right"], INSET["top"]), (INSET["left"], INSET["bottom"]), (INSET["right"], INSET["bottom"])):
        cx, cy = u * W, v * H
        for y in range(max(0, int(cy - half)), min(H, int(cy + half) + 1)):
            row = px[y * W: (y + 1) * W]
            if min(row[max(0, int(cx - half)): min(W, int(cx + half) + 1)] or b"\xff") < 200:
                return False
    return True


def marks(w, h):
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(w, h)); c.setFillGray(0)
    for u, v in ((INSET["left"], INSET["top"]), (INSET["right"], INSET["top"]), (INSET["left"], INSET["bottom"]), (INSET["right"], INSET["bottom"])):
        c.rect(u * w - SIDE / 2, h - v * h - SIDE / 2, SIDE, SIDE, stroke=0, fill=1)
    c.save(); buf.seek(0)
    return PdfReader(buf).pages[0]


def main():
    src, groups, out = sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3]
    want = {(g["key"], int(g["y"]), g["task"]) for g in groups}
    man = json.load(open(src + "/manifest.json"))
    index, seen = {}, {}
    for e in man:
        if not e.get("file"):
            continue
        key = (e["comp"].lower(), int(e["year"]), e["task"])
        if key not in want:
            continue
        path = os.path.join(src, e["file"])
        rd = PdfReader(path)
        wr, marked = PdfWriter(), 0
        for i in rng(e.get("pages"), len(rd.pages)):
            pg = rd.pages[i]
            w, h = float(pg.mediabox.width), float(pg.mediabox.height)
            if pg.get("/Rotate", 0) == 0 and 1.38 < h / w < 1.45 and corners_blank(path, i, w, h):
                pg.merge_page(marks(w, h)); marked += 1
            wr.add_page(pg)
        try:                                                   # smaller where the file allows it; as it is where not
            for p in wr.pages:
                p.compress_content_streams()
            wr.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
        except Exception:
            wr = PdfWriter()
            for i in rng(e.get("pages"), len(rd.pages)):
                wr.add_page(rd.pages[i])
        tag = "AS" if e["kind"] == "answer" else "WS"
        n = seen[(key, tag)] = seen.get((key, tag), 0) + 1
        name = f"{e['comp']}_{e['year']}_{e['task']}_{tag}{n if n > 1 else ''}.pdf"
        with open(os.path.join(out, name), "wb") as f:
            wr.write(f)
        index.setdefault(f"{key[0]}{key[1]}", {}).setdefault(key[2], {}).setdefault(e["kind"], []).append(
            {"file": name, "pages": len(wr.pages), "marked": marked, "src": e.get("source_url"), "lang": e.get("language")})
        print(f"{name:32} pages {len(wr.pages):2}  marked {marked:2}  {os.path.getsize(os.path.join(out, name)) // 1024} KB", file=sys.stderr)
    with open(os.path.join(out, "index.json"), "w") as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()

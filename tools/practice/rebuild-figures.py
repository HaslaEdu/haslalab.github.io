"""Rebuild the PhysLeague question figures from the official exam PDFs.

The figures were served by the retired PhysLeague Worker and are gone, but every figure kept its crop box
(sourcePdfCropMilliPoints, top-left origin) and the SHA-256 of the official PDF it came from. This script
downloads each official PDF once, refuses a file whose hash differs, finds the page from the printed question
number inside the recorded question region, and renders the crop at the recorded pixel size as WebP.

usage: python3 tools/practice/rebuild-figures.py EXPORT.json PDF_CACHE_DIR OUT_DIR
"""
import hashlib, io, json, os, re, sys, urllib.request
import pymupdf
from PIL import Image

export, cache, out = sys.argv[1:4]
os.makedirs(cache, exist_ok=True); os.makedirs(out, exist_ok=True)
rows = json.load(open(export, encoding="utf-8"))

def fetch(url, sha):
    path = os.path.join(cache, sha + ".pdf")
    if not os.path.exists(path):
        with urllib.request.urlopen(url, timeout=60) as r: data = r.read()
        if hashlib.sha256(data).hexdigest() != sha: raise ValueError("hash mismatch for " + url)
        open(path, "wb").write(data)
    return pymupdf.open(path)

labels = {}
def find_page(doc, sha, number, region):
    if sha not in labels:
        found = {}
        for i, page in enumerate(doc):
            for b in page.get_text("dict")["blocks"]:
                for l in b.get("lines", []):
                    t = "".join(s["text"] for s in l["spans"]).strip()
                    m = re.match(r"^(\d{1,2})\s?\.", t)
                    if m: found.setdefault(int(m.group(1)), []).append((i, l["bbox"]))
        labels[sha] = found
    x0, y0, x1, y1 = (region[k] / 1000 for k in ("left", "top", "right", "bottom"))
    hits = [i for i, bb in labels[sha].get(number, []) if x0 - 2 <= bb[0] <= x1 and y0 - 2 <= bb[1] <= y1]
    return hits[0] if len(set(hits)) == 1 else None

def render(doc, page, crop, width, height):
    r = pymupdf.Rect(*(crop[k] / 1000 for k in ("left", "top", "right", "bottom")))
    zoom = (width / r.width) if width else 4
    pix = doc[page].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=r, alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    if width and height and abs(img.width - width) <= 3: img = img.resize((width, height))
    buf = io.BytesIO(); img.save(buf, "WEBP", quality=82, method=6); return buf.getvalue(), img.size

# Scanned papers have no text layer. Their pages follow from the question order: two columns per page,
# left column top to bottom, then the right column; a question that starts above its predecessor in the same
# column, or back in the left column after the right one, starts a new page.
sequence_pages = {}
def sequence_page(sha, number):
    if sha not in sequence_pages:
        regions = {}
        for row in rows:
            for m in row["media"] + row["choices"]:
                c = m.get("crop") or {}
                if c.get("sourcePdfSha256") == sha and c.get("sourcePdfRegionMilliPoints"):
                    regions.setdefault(row["question_number"], c["sourcePdfRegionMilliPoints"])
        page, prev, pages = 0, None, {}
        for q in sorted(regions):
            reg = regions[q]; col = 0 if reg["left"] < 400000 else 1
            if prev is not None:
                pcol, ptop = prev
                if col < pcol or (col == pcol and reg["top"] < ptop): page += 1
            pages[q] = page; prev = (col, reg["top"])
        sequence_pages[sha] = pages
    return sequence_pages[sha].get(number)

def question_regions(sha):
    out = {}
    for row in rows:
        for m in row["media"]:
            c = m.get("crop") or {}
            if c.get("sourcePdfSha256") == sha and c.get("sourcePdfRegionMilliPoints"): out.setdefault(row["question_number"], c["sourcePdfRegionMilliPoints"])
    return out

def extend_to_choices(doc, sha, page, number, region):
    """The recorded region ends with the stem; the choices sit below it, down to the next question in the same column."""
    col = region["left"] < 400000
    below = []
    for q, reg in question_regions(sha).items():
        if q == number or (reg["left"] < 400000) != col or reg["top"] <= region["top"]: continue
        qpage = find_page(doc, sha, q, reg)
        if qpage is None and not any(p.get_text().strip() for p in doc): qpage = sequence_page(sha, q)
        if qpage == page: below.append(reg["top"])
    bottom = (min(below) - 6000) if below else round(doc[page].rect.height * 1000) - 80000
    return dict(region, bottom=max(region["bottom"], bottom))

manifest, missing = {}, []
for row in rows:
    pid, n = row["id"], row["question_number"]
    items = [("f%d" % (i + 1), m, m.get("w"), m.get("h")) for i, m in enumerate(row["media"])]
    # Where a choice has no text (graphs or diagrams as answers) the whole question region is rendered,
    # choices included: the recorded choice crops refer to an intermediate scan that no longer exists.
    if any(not (c.get("t") or "").strip() for c in row["choices"]):
        base = next((m["crop"] for m in row["media"] if (m.get("crop") or {}).get("sourcePdfRegionMilliPoints")), None)
        if base:
            reg = base["sourcePdfRegionMilliPoints"]
            items.append(("q", {"crop": {"sourcePdfSha256": base["sourcePdfSha256"], "sourcePdfRegionMilliPoints": reg, "sourcePdfCropMilliPoints": reg}}, round((reg["right"] - reg["left"]) / 1000 * 2.4), None))
        else: missing.append((pid, "q", "no question region"))
    for key, item, w, h in items:
        crop = item.get("crop") or {}
        box, region, sha = crop.get("sourcePdfCropMilliPoints"), crop.get("sourcePdfRegionMilliPoints"), crop.get("sourcePdfSha256")
        if not (box and region and sha): missing.append((pid, key, "no crop")); continue
        try:
            doc = fetch(row["official_problem_url"], sha)
            page = find_page(doc, sha, n, region)
            if page is None and not any(p.get_text().strip() for p in doc): page = sequence_page(sha, n)
            if page is None or page >= len(doc): missing.append((pid, key, "page not found")); continue
            if key == "q": box = extend_to_choices(doc, sha, page, n, region)
            data, size = render(doc, page, box, w, h)
        except Exception as e:
            missing.append((pid, key, str(e)[:80])); continue
        name = "%s-%s.webp" % (pid, key)
        open(os.path.join(out, name), "wb").write(data)
        manifest.setdefault(pid, {})[key] = {"file": name, "w": size[0], "h": size[1]}
json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=0)
print("figures", sum(len(v) for v in manifest.values()), "problems", len(manifest), "missing", len(missing))
for m in missing[:15]: print("  ", *m)

"""Prepare competition PDFs for per-problem transcription.

For each PDF: renders every page to PNG (for reading) and cuts out figure candidates: clusters of vector drawings
and embedded images, padded to keep their labels, rendered at 2x as WebP with ids p<page>-f<n>. Writes a
manifest the transcription step and tools/practice/build-contest-items.mjs read.

usage: python3 tools/practice/prepare-contest-pages.py PDF_DIR OUT_DIR [ID ...]
"""
import io, json, os, sys
import pymupdf
from PIL import Image

pdf_dir, out = sys.argv[1:3]
only = set(sys.argv[3:])
os.makedirs(out, exist_ok=True)

def merge(rects, gap):
    rects = [pymupdf.Rect(r) for r in rects]
    changed = True
    while changed:
        changed = False
        out_r = []
        while rects:
            r = rects.pop()
            for i, o in enumerate(out_r):
                if (r + (-gap, -gap, gap, gap)).intersects(o):
                    out_r[i] = o | r; changed = True; break
            else:
                out_r.append(r)
        rects = out_r
    return rects

def figures(page):
    W, H = page.rect.width, page.rect.height
    rects = []
    for d in page.get_drawings():
        r = d["rect"]
        if r.width > 0.85 * W and r.height < 4: continue          # rules across the page
        if r.width < 1 and r.height < 1: continue
        rects.append(r)
    for info in page.get_image_info():
        r = pymupdf.Rect(info["bbox"])
        if r.width > 8 and r.height > 8: rects.append(r)
    cl = [c for c in merge(rects, 10) if c.width >= 40 and c.height >= 30 and c.width * c.height < 0.92 * W * H]
    # keep labels around the drawing (axis names, letters, captions under it) but never part of a paragraph:
    # a text line joins only if it lies within the drawing's columns, so a line of body text that merely
    # touches the drawing is not cut in half at the crop edge
    # captions are transcribed as text, so only short labels (≤ 14 characters) join a figure
    lines = [pymupdf.Rect(l["bbox"]) for b in page.get_text("dict")["blocks"] for l in b.get("lines", [])
             if len("".join(s["text"] for s in l["spans"]).strip()) <= 14]
    long_lines = [pymupdf.Rect(l["bbox"]) for b in page.get_text("dict")["blocks"] for l in b.get("lines", [])
                  if len("".join(s["text"] for s in l["spans"]).strip()) > 14]
    out_r = []
    for c in cl:
        g = pymupdf.Rect(c)
        near = c + (-14, -14, 14, 14)
        for lr in lines:
            if not near.intersects(lr): continue
            inside = lr.x0 >= c.x0 - 30 and lr.x1 <= c.x1 + 30
            if inside: g |= lr
        # a paragraph line caught at the top or bottom edge is cut off by the crop: move that edge past it
        for lr in long_lines:
            if not g.intersects(lr): continue
            if lr.y1 <= g.y0 + 0.35 * g.height: g.y0 = max(g.y0, lr.y1 + 1)
            elif lr.y0 >= g.y1 - 0.35 * g.height: g.y1 = min(g.y1, lr.y0 - 1)
        if g.height >= 20: out_r.append((g + (-4, -4, 4, 4)) & page.rect)
    return sorted(merge(out_r, 2), key=lambda r: (r.y0, r.x0))

manifest = {}
for name in sorted(os.listdir(pdf_dir)):
    if not name.endswith(".pdf"): continue
    pid = name[:-4]
    if only and pid not in only: continue
    doc = pymupdf.open(os.path.join(pdf_dir, name))
    d = os.path.join(out, pid); os.makedirs(d, exist_ok=True)
    entry = {"pages": [], "figures": []}
    for i, page in enumerate(doc, 1):
        page.get_pixmap(matrix=pymupdf.Matrix(1.6, 1.6)).save(os.path.join(d, f"page{i}.png"))
        entry["pages"].append(f"page{i}.png")
        for k, r in enumerate([r for r in figures(page) if r.width >= 20 and r.height >= 20], 1):
            try: pix = page.get_pixmap(matrix=pymupdf.Matrix(2.2, 2.2), clip=r, alpha=False)
            except Exception: continue
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            fid = f"p{i}-f{k}"
            img.save(os.path.join(d, fid + ".webp"), "WEBP", quality=82, method=6)
            entry["figures"].append({"id": fid, "page": i, "bbox": [round(v, 1) for v in r], "w": img.width, "h": img.height})
        # a copy of the page with the candidates outlined and numbered, for whoever assigns figures to problems
        cands = [f for f in entry["figures"] if f["page"] == i]
        if cands:
            from PIL import ImageDraw
            im = Image.open(os.path.join(d, f"page{i}.png")).convert("RGB"); dr = ImageDraw.Draw(im)
            for f in cands:
                x0, y0, x1, y1 = (v * 1.6 for v in f["bbox"])
                dr.rectangle([x0, y0, x1, y1], outline=(220, 30, 30), width=3); dr.text((x0 + 4, y0 + 2), f["id"], fill=(220, 30, 30))
            im.save(os.path.join(d, f"page{i}-boxes.png"))
    manifest[pid] = entry
json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=0)
print("pdfs", len(manifest), "pages", sum(len(e["pages"]) for e in manifest.values()), "figures", sum(len(e["figures"]) for e in manifest.values()))

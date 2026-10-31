"""Translate prose inside the original PDF geometry; preserve mathematical glyphs.

extract writes a reviewable translation manifest and lossless inline-math crops.
build requires a translation for every extracted prose region and refuses omissions.
No network translation or automatic formula rewriting is performed.
"""
from __future__ import annotations
import argparse
from collections import Counter
import html
import hashlib
import json
import re
from pathlib import Path
import urllib.request
import pymupdf as fitz
from PIL import Image, ImageDraw
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "tools/ko/fonts/NotoSansKR-Regular.ttf"


def regenerate_math_crop(page, math, target):
    """Recreate a reviewed crop, including recorded source glyph repairs."""
    if math.get("clean_prose"):
        from izho_math_clean import math_pixmap
        bitmap, pix = math_pixmap(page, fitz.Rect(math["rect"]), math.get("keep_glyph_origins", ()))
    else:
        pix = page.get_pixmap(matrix=fitz.Matrix(4, 4), clip=fitz.Rect(math["rect"]), alpha=False)
        bitmap = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    if math.get("ink_rects"):
        mask = Image.new("L", bitmap.size)
        draw = ImageDraw.Draw(mask)
        for q in math["ink_rects"]:
            r = fitz.Rect(q)
            draw.rectangle((r.x0*4-pix.x, r.y0*4-pix.y,
                            r.x1*4-pix.x, r.y1*4-pix.y), fill=255)
        bitmap = Image.composite(bitmap, Image.new("RGB", bitmap.size, "white"), mask)
    for patch in math.get("glyph_patches", []):
        q = fitz.Rect(patch["rect"])
        ImageDraw.Draw(bitmap).rectangle((q.x0*4-pix.x, q.y0*4-pix.y,
                                         q.x1*4-pix.x, q.y1*4-pix.y), fill="white")
        glyph_doc = fitz.open()
        glyph_page = glyph_doc.new_page(width=pix.width/4, height=pix.height/4)
        font = patch.get("font", "noto")
        if font == "noto":
            glyph_page.insert_font(fontname=font, fontfile=str(FONT))
        point = fitz.Point(patch["point"]) - fitz.Point(pix.x/4, pix.y/4)
        glyph_page.insert_text(point, patch["text"], fontname=font,
                               fontsize=patch.get("size", 9))
        glyph = glyph_page.get_pixmap(matrix=fitz.Matrix(4, 4), alpha=False)
        ink = Image.frombytes("RGB", (glyph.width, glyph.height), glyph.samples)
        from PIL import ImageChops
        bitmap = ImageChops.darker(bitmap, ink)
        glyph_doc.close()
    bitmap.save(target)


def resolve_source(data):
    """Resolve a portable original, fetching the already-published archive asset if needed."""
    name = data.get("provenance", {}).get("source_name") or Path(data["source"]).name
    source = ROOT / "tmp" / "source-audit" / name
    if not source.exists():
        configured = Path(data["source"])
        if not configured.is_absolute():
            configured = ROOT / configured
        if configured.exists():
            source = configured
        else:
            source.parent.mkdir(parents=True, exist_ok=True)
            url = f"https://github.com/HaslaEdu/haslalab.github.io/releases/download/pdf-izho/{name}"
            request = urllib.request.Request(url, headers={"User-Agent": "HaslaLab IZhO rebuild"})
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = response.read()
            if not raw.startswith(b"%PDF-"):
                raise ValueError("The source archive did not return a PDF: " + name)
            source.write_bytes(raw)
    expected = data.get("source_sha256")
    if expected and hashlib.sha256(source.read_bytes()).hexdigest() != expected:
        raise ValueError("Original PDF changed; review the translation before rebuilding: " + name)
    return source


def extract(source: Path, folder: Path, pages=None):
    folder.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(source)
    if pages is not None:
        doc.select(pages)
    small_glyphs = any(s["bbox"][3]-s["bbox"][1] > s["size"]*2.5
                       for page in doc for b in page.get_text("dict")["blocks"] if b["type"] == 0
                       for line in b["lines"] for s in line["spans"])
    fitz.TOOLS.set_small_glyph_heights(small_glyphs)
    entries = []
    for pi, page in enumerate(doc):
        for bi, block in enumerate(page.get_text("dict")["blocks"]):
            if block["type"] != 0:
                continue
            words = " ".join(s["text"] for ln in block["lines"] for s in ln["spans"])
            prose = re.findall(r"[A-Za-z]{3,}", words)
            if not prose or (len(prose) == 1 and prose[0].lower() in {"sin", "cos", "max", "min", "exp", "amu", "mev", "ghz", "kev", "log", "out"}):
                continue
            key = f"{pi+1}-{bi}"
            sizes = [s["size"] for ln in block["lines"] for s in ln["spans"]]
            base = max(sizes)
            chunks, maths = [], []
            for ln in block["lines"]:
                pending = None
                pending_text = []
                def flush():
                    nonlocal pending, pending_text
                    if pending is None:
                        return
                    rect = pending + (-.3, -.3, .3, .3)
                    name = f"{key}-m{len(maths)}.png"
                    page.get_pixmap(matrix=fitz.Matrix(4, 4), clip=rect, alpha=False).save(folder / name)
                    maths.append({"file": name, "width": rect.width, "height": rect.height,
                                  "rect": list(rect), "text": "".join(pending_text)})
                    chunks.append(f"[[{len(maths)-1}]]")
                    pending = None
                    pending_text = []
                for span in ln["spans"]:
                    text = span["text"]
                    math = (span["font"].replace(" ", "").startswith(("CM", "LMMath", "CambriaMath", "Symbol")) or
                            ("Italic" in span["font"] and not re.search(r"[A-Za-z]{2,}", text)))
                    if math:
                        pending_text.append(text)
                        rect = fitz.Rect(span["bbox"])
                        # Some official 2024 Cambria Math fonts report ascenders about five
                        # times their size. Use the baseline to avoid cropping adjacent lines.
                        if rect.height > span["size"] * 2.5:
                            rect.y0 = span["origin"][1] - span["size"] * 1.05
                            rect.y1 = span["origin"][1] + span["size"] * .30
                        if pending is None:
                            pending = rect
                        else:
                            pending |= rect
                    else:
                        flush()
                        chunks.append(text)
                flush()
                chunks.append(" ")
            text = re.sub(r"\s+", " ", "".join(chunks)).strip()
            entries.append({"id": key, "page": pi, "rect": block["bbox"],
                            "size": base, "source": text, "math": maths,
                            "ko": ""})
    out = {"source": str(source.resolve()), "entries": entries}
    if small_glyphs:
        out["small_glyph_heights"] = True
    if pages is not None:
        out["source_pages"] = pages
    (folder / "translation.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf8")
    print(f"Extracted {len(entries)} prose regions into {folder}")


def build(folder: Path, target: Path):
    data = json.loads((folder / "translation.json").read_text(encoding="utf8"))
    fitz.TOOLS.set_small_glyph_heights(bool(data.get("small_glyph_heights")))
    missing = [e["id"] for e in data["entries"] if not e["ko"].strip()]
    if missing:
        raise ValueError("Untranslated regions: " + ", ".join(missing))
    source = resolve_source(data)
    doc = fitz.open(source)
    original = fitz.open(source)
    if data.get("source_pages") is not None:
        doc.select(data["source_pages"])
        original.select(data["source_pages"])
    original_blocks = [page.get_text("dict")["blocks"] for page in original]
    def prose_span_rect(span, pi):
        for override in data.get("prose_mask_overrides", []):
            if override["page"] == pi and max(abs(a-b) for a, b in zip(override["source_rect"], span["bbox"])) < .05:
                return fitz.Rect(override["rect"])
        return fitz.Rect(span["bbox"])

    def restore_math(page, pi, rect):
        if not data.get("transparent_math_restore"):
            page.show_pdf_page(rect, original, pi, clip=rect)
            return
        # Transparent ink avoids an original page's white background masking adjacent Korean.
        pix = original[pi].get_pixmap(matrix=fitz.Matrix(4, 4), clip=rect,
                                     colorspace=fitz.csRGB, alpha=False)
        rgb = pix.samples
        if data.get("mask_original_prose_in_math"):
            # A formula's font box can extend into the following prose row.
            # Exclude original prose spans before restoring equation ink.
            bitmap = Image.frombytes("RGB", (pix.width, pix.height), rgb)
            draw = ImageDraw.Draw(bitmap)
            for suppression in data.get("math_erase_rects", []):
                if suppression["page"] != pi:
                    continue
                box = fitz.Rect(suppression["rect"]) & rect
                if not box.is_empty:
                    draw.rectangle((box.x0*4-pix.x, box.y0*4-pix.y,
                                    box.x1*4-pix.x, box.y1*4-pix.y), fill="white")
            for entry in data["entries"]:
                if entry["page"] != pi or entry.get("passthrough"): continue
                for mi, math in enumerate(entry.get("math", [])):
                    if mi in entry.get("preserved_math", []): continue
                    box = fitz.Rect(math["rect"]) & rect
                    if not box.is_empty:
                        draw.rectangle((box.x0*4-pix.x, box.y0*4-pix.y,
                                        box.x1*4-pix.x, box.y1*4-pix.y), fill="white")
            for block in original_blocks[pi]:
                if block["type"] != 0: continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        override = next((item for item in data.get("prose_mask_overrides", [])
                                         if item["page"] == pi and max(abs(a-b) for a, b in
                                         zip(item["source_rect"], span["bbox"])) < .05), None)
                        if override is not None:
                            # Reviewed prose can share a CambriaMath span with an equation.
                            # Its explicit prefix mask takes priority over font heuristics.
                            box = fitz.Rect(override["rect"]) & rect
                            if not box.is_empty:
                                draw.rectangle((box.x0*4-pix.x, box.y0*4-pix.y,
                                                box.x1*4-pix.x, box.y1*4-pix.y), fill="white")
                            continue
                        words = re.findall(r"[A-Za-z]{2,}", span["text"])
                        if data.get("word_math_preserve"):
                            from izho_extract_word import mathword
                            if words and all(mathword(w) for w in words):
                                continue
                            cyrillic_words = re.findall(r"[А-Яа-яЁё]{2,}", span["text"])
                            if cyrillic_words and all(mathword(w) for w in cyrillic_words):
                                continue
                            if cyrillic_words:
                                box = prose_span_rect(span, pi) & rect
                                if not box.is_empty:
                                    draw.rectangle((box.x0*4-pix.x, box.y0*4-pix.y,
                                                    box.x1*4-pix.x, box.y1*4-pix.y), fill="white")
                                continue
                        if not words or span["font"].replace(" ", "").startswith(("CambriaMath", "CM", "Symbol")): continue
                        if all(w.lower() in {"sin","cos","tan","exp","ln","log","const","max","min","mol","mole","dpt","pa","kg","cm","mm","km","rad","years","ma","wb","hz","hn","year","arcsin","arccos","arctan","asin","acos","atan","sinh","cosh","tanh","coth","abs","sign","floor","ceil"} or re.fullmatch(r"[A-Za-z]*d[A-Z][A-Za-z]*", w) or w.lower() in {"dx","dy","dz","dt","dr","du","da","dq","dv"} for w in words): continue
                        box = prose_span_rect(span, pi) & rect
                        if box.is_empty: continue
                        draw.rectangle((box.x0*4-pix.x, box.y0*4-pix.y,
                                        box.x1*4-pix.x, box.y1*4-pix.y), fill="white")
            rgb = bitmap.tobytes()
        colors = np.frombuffer(rgb, dtype=np.uint8).reshape(-1, 3).astype(np.float64)
        alpha = 255-colors.min(axis=1)
        rgba = np.zeros((len(colors), 4), dtype=np.uint8)
        live = alpha > 0
        rgba[live, :3] = np.rint((colors[live]-255+alpha[live, None])*255/alpha[live, None]).astype(np.uint8)
        rgba[:, 3] = alpha
        ink = fitz.Pixmap(fitz.csRGB, pix.width, pix.height, rgba.tobytes(), True)
        pixel_rect = fitz.Rect(pix.x/4, pix.y/4, (pix.x+pix.width)/4, (pix.y+pix.height)/4)
        page.insert_image(pixel_rect, stream=ink.tobytes("png"), overlay=True, keep_proportion=False)
    # Stored crop rectangles allow a clean checkout to recreate absent inline-math PNGs.
    for e in data["entries"]:
        for math in e.get("math", []):
            target_crop = folder / math["file"]
            if not target_crop.exists():
                if "rect" not in math:
                    raise ValueError("Missing math crop without a source rectangle: " + str(target_crop))
                regenerate_math_crop(original[e["page"]], math, target_crop)
    archive = fitz.Archive(str(folder.resolve()))
    archive.add(str(FONT.parent))
    css = """@font-face { font-family: Korean; src: url(NotoSansKR-Regular.ttf); }
      * {font-family: Korean; color: #000;} body {margin:0;padding:0;}
      p {margin:0; padding:0; line-height:1.18;} img {vertical-align:middle;}"""
    if data.get("math_bottom_align"):
        css += " img {vertical-align:bottom;}"
    failures, report = [], []
    for pi, page in enumerate(doc):
        entries = [e for e in data["entries"] if e["page"] == pi and not e.get("passthrough")]
        pictures = [fitz.Rect(b["bbox"]) for b in original_blocks[pi] if b["type"] == 1]
        math_rects = []
        if data.get("transparent_math_restore"):
            math_rects = [fitz.Rect(r["rect"]) for r in data.get("preserve_rects", [])
                          if r["page"] == pi and not any(fitz.Rect(r["rect"]) == q for q in pictures)]
            if data.get("preserve_all_math"):
                for block in original_blocks[pi]:
                    if block["type"] != 0:
                        continue
                    spans = [s for line in block["lines"] for s in line["spans"] if s["text"].strip()]
                    words = re.findall(r"[A-Za-z]{2,}", " ".join(s["text"] for s in spans))
                    if spans and any(s["font"].replace(" ", "").startswith(("CambriaMath", "CM", "Symbol")) for s in spans) and all(
                        w.lower() in {"sin", "cos", "tan", "exp", "ln", "log", "const", "max", "min", "mol", "mole", "dpt", "pa", "kg", "cm", "mm", "km"} for w in words
                    ):
                        # The complete block includes radical hooks and fraction rules
                        # drawn outside individual text-glyph bounds by Word's equation engine.
                        math_rects.append(fitz.Rect(block["bbox"]))
            merged = []
            for rect in math_rects:
                while data.get("preserve_all_math") or data.get("merge_math_rects"):
                    overlap = next((j for j,r in enumerate(merged) if (rect & r).get_area() > 0
                        or (min(rect.y1, r.y1) > max(rect.y0, r.y0)
                            and max(rect.x0, r.x0)-min(rect.x1, r.x1) < 4)), None)
                    if overlap is None: break
                    rect |= merged.pop(overlap)
                merged.append(rect)
            math_rects = merged
            # Mask each original equation once before Korean is inserted. A white overlay
            # preserves score glyphs that straddle the crop boundary; text redaction
            # would delete their complete glyph and restore only a clipped fragment.
            for rect in math_rects:
                page.draw_rect(rect, color=None, fill=(1, 1, 1), overlay=True)
        for erase in data.get("erase_rects", []):
            if erase["page"] == pi:
                page.add_redact_annot(fitz.Rect(erase["rect"]), fill=(1, 1, 1))
        for e in entries:
            page.add_redact_annot(fitz.Rect(e.get("redact_rect", e["rect"])), fill=(1, 1, 1))
        page.apply_redactions(images=0, graphics=0, text=1 if data.get("mask_prose_instead_of_redact") else 0)
        for e in entries:
            expected = Counter(re.findall(r"\[\[(\d+)\]\]", e["source"]))
            for mi in e.get("preserved_math", []):
                del expected[str(mi)]
            actual = Counter(re.findall(r"\[\[(\d+)\]\]", e["ko"]))
            if actual != expected:
                raise ValueError(f"Formula placeholders differ at {e['id']}: {expected} != {actual}")
            content = html.escape(e["ko"])
            if data.get("honor_line_breaks"):
                content = content.replace("\n", "<br>")
            for mi, math in enumerate(e["math"]):
                baseline_style = ''
                if "baseline_from_bottom" in math:
                    baseline_style = f' style="vertical-align:{-math["baseline_from_bottom"]}pt"'
                image = f'<img src="{math["file"]}" width="{math["width"]}" height="{math["height"]}"{baseline_style}>'
                content = content.replace(f"[[{mi}]]", image)
            rect = fitz.Rect(e["rect"])
            rect.y0 -= 1
            rect.y1 += 2
            if rect.width < 180 and e["size"] > 12:
                rect.x0, rect.x1 = 68, page.rect.width - 68
            style = f'font-size:{e["size"]}pt;'
            if e.get("align"):
                style += f'text-align:{e["align"]};'
            if e.get("line_height"):
                style += f'line-height:{e["line_height"]}pt;'
            elif data.get("math_line_height"):
                heights = [m["height"] for mi, m in enumerate(e.get("math", [])) if str(mi) in actual]
                height = max([e["size"]*1.18] + [h+1 for h in heights])
                style += f'line-height:{height}pt;'
            spare, scale = page.insert_htmlbox(rect, f'<p style="{style}">{content}</p>',
                css=css, archive=archive, scale_low=.72)
            report.append({"id": e["id"], "scale": scale, "spare": spare})
            if spare < 0:
                failures.append(e["id"])
        for keep in data.get("preserve_rects", []):
            if keep["page"] != pi:
                continue
            rect = fitz.Rect(keep["rect"])
            if rect.is_empty or rect.is_infinite:
                continue
            if any(rect == picture for picture in pictures):
                page.show_pdf_page(rect, original, pi, clip=rect)
            elif not data.get("transparent_math_restore"):
                restore_math(page, pi, rect)
        if data.get("preserve_all_math") and not data.get("transparent_math_restore"):
            for block in original_blocks[pi]:
                if block["type"] != 0:
                    continue
                spans = [s for line in block["lines"] for s in line["spans"]]
                words = re.findall(r"[A-Za-z]{2,}", " ".join(s["text"] for s in spans))
                if any(s["font"].replace(" ", "").startswith(("CambriaMath", "CM", "Symbol")) for s in spans) and all(
                    w.lower() in {"sin", "cos", "tan", "exp", "ln", "log", "const", "max", "min", "mol", "mole", "dpt", "pa", "kg", "cm", "mm", "km"} for w in words
                ):
                    rect = fitz.Rect(block["bbox"])
                    restore_math(page, pi, rect)
        for rect in math_rects:
            restore_math(page, pi, rect)
        if data.get("restore_table_rules"):
            table_rects = [fitz.Rect(t["rect"]) for t in data.get("tables", []) if t["page"] == pi]
            for path in original[pi].get_drawings():
                # Word draws grid lines as thin filled rectangles rather than strokes.
                for item in path["items"]:
                    if item[0] == "re" and path.get("fill") is not None:
                        r = item[1]
                        if min(r.width, r.height) < 2 and any((t+(-2,-2,2,2)).contains(r) for t in table_rects):
                            page.draw_rect(r, color=None, fill=path["fill"], overlay=True)
                if path.get("color") is None:
                    continue
                for item in path["items"]:
                    if item[0] == "l" and any(r.contains(item[1]) and r.contains(item[2]) for r in table_rects):
                        page.draw_line(item[1], item[2], color=path["color"], width=path.get("width", .5), overlay=True)
        # Preserve the rule beneath the original competition header.
        if data.get("header_rule"):
            page.draw_line((36, 49.5), (562.4, 49.5), color=(0, 0, 0), width=.5)
        # Optional translations inside retained raster/vector figures, after figure restoration.
        # Each patch uses absolute PDF coordinates and a Korean font over a white background.
        for oi, patch in enumerate(data.get("post_overlays", [])):
            if patch["page"] != pi:
                continue
            patch_rect = fitz.Rect(patch["rect"])
            page.draw_rect(patch_rect, color=None, fill=(1, 1, 1), overlay=True)
            label = html.escape(patch["text"])
            align = patch.get("align", "center")
            label_html = f'<p style="font-size:{patch.get("size", 10)}pt;text-align:{align};">{label}</p>'
            spare, scale = page.insert_htmlbox(patch_rect, label_html, css=css,
                archive=archive, rotate=patch.get("rotate", 0), scale_low=patch.get("scale_low", .72))
            key = f"post-{pi+1}-{oi}"
            report.append({"id": key, "scale": scale, "spare": spare})
            if spare < 0:
                failures.append(key)
        # Restore explicitly reviewed source glyphs that were blank transparent images.
        for repair in data.get("native_text_overlays", []):
            if repair["page"] == pi:
                page.insert_text(tuple(repair["point"]), repair["text"],
                    fontsize=repair.get("size", 12), fontname=repair.get("font", "tiro"), overlay=True)
        page.wrap_contents()
    if failures:
        raise ValueError("Text does not fit: " + ", ".join(failures))
    target.parent.mkdir(parents=True, exist_ok=True)
    doc.save(target, garbage=4, deflate=True)
    target.with_suffix(".qa.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    print(f"Wrote {target}; {len(report)} translated regions, minimum scale {min(r['scale'] for r in report):.3f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    ex = sub.add_parser("extract"); ex.add_argument("source", type=Path); ex.add_argument("folder", type=Path)
    ex.add_argument("--pages", help="Inclusive one-based page range, e.g. 1-6 for an English section")
    bu = sub.add_parser("build"); bu.add_argument("folder", type=Path); bu.add_argument("target", type=Path)
    a = p.parse_args()
    if a.command == "extract":
        pages = None
        if a.pages:
            first, last = map(int, a.pages.split("-"))
            pages = list(range(first-1, last))
        extract(a.source, a.folder, pages)
    else: build(a.folder, a.target)

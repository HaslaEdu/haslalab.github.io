"""Translate prose inside the original PDF geometry; preserve mathematical glyphs.

extract writes a reviewable translation manifest and lossless inline-math crops.
build requires a translation for every extracted prose region and refuses omissions.
No network translation or automatic formula rewriting is performed.
"""
from __future__ import annotations
import argparse
from collections import Counter
import html
import json
import re
from pathlib import Path
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "tools/ko/fonts/NotoSansKR-Regular.ttf"


def extract(source: Path, folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(source)
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
                def flush():
                    nonlocal pending
                    if pending is None:
                        return
                    rect = pending + (-.3, -.3, .3, .3)
                    name = f"{key}-m{len(maths)}.png"
                    page.get_pixmap(matrix=fitz.Matrix(4, 4), clip=rect, alpha=False).save(folder / name)
                    maths.append({"file": name, "width": rect.width, "height": rect.height})
                    chunks.append(f"[[{len(maths)-1}]]")
                    pending = None
                for span in ln["spans"]:
                    text = span["text"]
                    math = (span["font"].startswith(("CM", "LMMath")) or
                            (span["size"] < base * .85 and re.search(r"[A-Za-z0-9]", text)))
                    if math:
                        rect = fitz.Rect(span["bbox"])
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
    (folder / "translation.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf8")
    print(f"Extracted {len(entries)} prose regions into {folder}")


def build(folder: Path, target: Path):
    data = json.loads((folder / "translation.json").read_text(encoding="utf8"))
    missing = [e["id"] for e in data["entries"] if not e["ko"].strip()]
    if missing:
        raise ValueError("Untranslated regions: " + ", ".join(missing))
    doc = fitz.open(data["source"])
    original = fitz.open(data["source"])
    archive = fitz.Archive(str(folder.resolve()))
    archive.add(str(FONT.parent))
    css = """@font-face { font-family: Korean; src: url(NotoSansKR-Regular.ttf); }
      * {font-family: Korean; color: #000;} body {margin:0;padding:0;}
      p {margin:0; padding:0; line-height:1.18;} img {vertical-align:middle;}"""
    failures, report = [], []
    for pi, page in enumerate(doc):
        entries = [e for e in data["entries"] if e["page"] == pi]
        for e in entries:
            page.add_redact_annot(fitz.Rect(e["rect"]), fill=e.get("redact_fill", (1, 1, 1)))
        page.apply_redactions(images=0, graphics=0)
        for e in entries:
            expected = Counter(re.findall(r"\[\[(\d+)\]\]", e["source"]))
            for mi in e.get("preserved_math", []):
                del expected[str(mi)]
            actual = Counter(re.findall(r"\[\[(\d+)\]\]", e["ko"]))
            if actual != expected:
                raise ValueError(f"Formula placeholders differ at {e['id']}: {expected} != {actual}")
            content = html.escape(e["ko"])
            for mi, math in enumerate(e["math"]):
                image = f'<img src="{math["file"]}" width="{math["width"]}" height="{math["height"]}">'
                content = content.replace(f"[[{mi}]]", image)
            rect = fitz.Rect(e.get("insert_rect", e["rect"]))
            rect.y0 -= 1
            rect.y1 += 2
            if rect.width < 180 and e["size"] > 12:
                rect.x0, rect.x1 = 68, page.rect.width - 68
            spare, scale = page.insert_htmlbox(rect, f'<p style="font-size:{e["size"]}pt;line-height:{e.get("line_height",1.18)}">{content}</p>',
                css=css, archive=archive, scale_low=.72)
            report.append({"id": e["id"], "scale": scale, "spare": spare})
            if spare < 0:
                failures.append(e["id"])
        for keep in data.get("preserve_rects", []):
            if keep["page"] != pi:
                continue
            rect = fitz.Rect(keep["rect"])
            page.draw_rect(rect, color=None, fill=(1, 1, 1))
            page.show_pdf_page(rect, original, pi, clip=rect)
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
    bu = sub.add_parser("build"); bu.add_argument("folder", type=Path); bu.add_argument("target", type=Path)
    a = p.parse_args()
    if a.command == "extract": extract(a.source, a.folder)
    else: build(a.folder, a.target)

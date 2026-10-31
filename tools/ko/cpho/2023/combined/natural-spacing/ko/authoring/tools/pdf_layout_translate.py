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
import unicodedata
from pathlib import Path
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "tools/ko/fonts/NotoSansKR-Regular.ttf"


def script_markup(value):
    """Typeset Unicode superscripts/subscripts with supported normal glyphs.

    The bundled Hangul font lacks most superscript digits and every subscript
    digit. HTML script positioning preserves these mathematical values instead
    of embedding a missing-glyph box in small annotations.
    """
    result=[];kind=None;pending=[]
    def flush():
        nonlocal pending
        if pending:result.append(f'<{kind}>'+html.escape(''.join(pending))+f'</{kind}>');pending=[]
    for char in value:
        decomposition=unicodedata.decomposition(char)
        tag='sup' if decomposition.startswith('<super>') else 'sub' if decomposition.startswith('<sub>') else None
        if tag!=kind:flush();kind=tag
        if tag:pending.append(unicodedata.normalize('NFKD',char))
        else:result.append(html.escape(char))
    flush()
    return ''.join(result)


def outlined_copy(original):
    """Keep original glyph shapes as vectors, without oversized text metrics."""
    output = fitz.open()
    for page in original:
        svg = page.get_svg_image(text_as_path=True)
        picture = fitz.open(stream=svg.encode("utf8"), filetype="svg")
        vector = fitz.open(stream=picture.convert_to_pdf(), filetype="pdf")
        vector[0].set_mediabox(fitz.Rect(0, 0, page.rect.width, page.rect.height))
        output.insert_pdf(vector)
        vector.close()
        picture.close()
    output.set_metadata(original.metadata)
    return output


def background_color(page, bounds):
    """Find the original paper/panel color under a prose region."""
    from PIL import Image
    clip = fitz.Rect(bounds) & page.rect
    pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), clip=clip, colorspace=fitz.csRGB)
    picture = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    colors = picture.getcolors(maxcolors=pix.width * pix.height)
    rgb = max(colors, key=lambda item: item[0])[1]
    return tuple(value / 255 for value in rgb)


def extract(source: Path, folder: Path, roman_prose: bool = False):
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
                    maths.append({"file": name, "width": rect.width, "height": rect.height,
                                  "source_rect":list(rect)})
                    chunks.append(f"[[{len(maths)-1}]]")
                    pending = None
                for span in ln["spans"]:
                    text = span["text"]
                    math_prefixes = ("CMMI", "CMSY", "CMEX", "LMMath") if roman_prose else ("CM", "LMMath")
                    math = (span["font"].startswith(math_prefixes) or
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
    font=fitz.Font(fontfile=str(FONT))
    for entry in data['entries']:
        unsupported=sorted({char for char in entry['ko'] if not char.isspace() and
            not font.has_glyph(ord(char)) and
            not unicodedata.decomposition(char).startswith(('<super>','<sub>'))})
        if unsupported:raise ValueError(f'Unsupported text glyphs at {entry["id"]}: {unsupported}')
    original = fitz.open(data["source"])
    doc = outlined_copy(original) if data.get("outline_source") else fitz.open(data["source"])
    archive = fitz.Archive(str(folder.resolve()))
    archive.add(str(FONT.parent))
    css = """@font-face { font-family: Korean; src: url(NotoSansKR-Regular.ttf); }
      * {font-family: Korean; color: #000;} body {margin:0;padding:0;}
      p {margin:0; padding:0; line-height:1.18;} img {vertical-align:middle;}"""
    failures, report = [], []
    for pi, page in enumerate(doc):
        entries = [e for e in data["entries"] if e["page"] == pi]
        if data.get("outline_source"):
            for e in entries:
                bounds = e.get("redact_rect", e["rect"])
                fill = e.get("redact_fill")
                if fill is None:
                    fill = background_color(original[pi], bounds)
                page.draw_rect(fitz.Rect(bounds), color=None, fill=fill, overlay=True)
                for extra in e.get("erase_rects", []):
                    page.draw_rect(fitz.Rect(extra), color=None,
                                   fill=background_color(original[pi], extra), overlay=True)
        else:
            for e in entries:
                page.add_redact_annot(fitz.Rect(e.get("redact_rect", e["rect"])), fill=e.get("redact_fill", (1, 1, 1)))
            page.apply_redactions(images=0, graphics=0)
        for e in entries:
            expected = Counter(re.findall(r"\[\[(\d+)\]\]", e["source"]))
            for mi in e.get("preserved_math", []):
                del expected[str(mi)]
            actual = Counter(re.findall(r"\[\[(\d+)\]\]", e["ko"]))
            if actual != expected:
                raise ValueError(f"Formula placeholders differ at {e['id']}: {expected} != {actual}")
            content = script_markup(e["ko"])
            for mi, math in enumerate(e["math"]):
                image = f'<img src="{math["file"]}" width="{math["width"]}" height="{math["height"]}">'
                content = content.replace(f"[[{mi}]]", image)
            rect = fitz.Rect(e.get("insert_rect", e["rect"]))
            rect.y0 -= 1
            rect.y1 += 2
            if rect.width < 180 and e["size"] > 12:
                rect.x0, rect.x1 = 68, page.rect.width - 68
            spare, scale = page.insert_htmlbox(rect, f'<p style="font-size:{e["size"]}pt;line-height:{e.get("line_height",1.18)};text-align:{e.get("align","left")}">{content}</p>',
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
    for pi,page in enumerate(doc):
        for block in page.get_text('dict')['blocks']:
            if block['type']!=0:continue
            for line in block['lines']:
                for span in line['spans']:
                    if 'NotoSansKR' in span['font'] and '\x00' in span['text']:
                        raise ValueError(f'Missing rendered text glyph on page {pi+1}')
    target.parent.mkdir(parents=True, exist_ok=True)
    doc.save(target, garbage=4, deflate=True)
    target.with_suffix(".qa.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    print(f"Wrote {target}; {len(report)} translated regions, minimum scale {min(r['scale'] for r in report):.3f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    ex = sub.add_parser("extract"); ex.add_argument("source", type=Path); ex.add_argument("folder", type=Path)
    ex.add_argument("--roman-prose", action="store_true", help="CMR fonts contain ordinary prose, as in the CPhO 2005 source")
    bu = sub.add_parser("build"); bu.add_argument("folder", type=Path); bu.add_argument("target", type=Path)
    a = p.parse_args()
    if a.command == "extract": extract(a.source, a.folder, roman_prose=a.roman_prose)
    else: build(a.folder, a.target)

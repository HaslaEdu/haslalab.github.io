"""Audit rendered Korean text against original figure boxes and translation coverage.

    python tools/izho_validate.py 2026
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import pymupdf as fitz
from izho_translate import ROOT, resolve_source

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("years", type=int, nargs="+")
p.add_argument("--kind", choices=("T", "TS"), help="Audit one edition while the other is still being translated.")
a = p.parse_args()
failures = []
report = []
for year in a.years:
    for kind in ("T", "TS"):
        if a.kind and kind != a.kind:
            continue
        path = ROOT / "tools" / "ko" / "izho" / str(year) / kind / "translation.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf8"))
        fitz.TOOLS.set_small_glyph_heights(bool(data.get("small_glyph_heights")))
        source = fitz.open(resolve_source(data))
        if data.get("source_pages") is not None:
            source.select(data["source_pages"])
        target = ROOT / "pdfx" / "izho" / f"IZhO_{year}_{kind}_KO.pdf"
        output = fitz.open(target)
        if len(source) != len(output):
            failures.append(f"{year}/{kind}: page count differs")
        hits = []
        math_hits = []
        korean = 0
        for pi, page in enumerate(output):
            ignored = [fitz.Rect(r["rect"]) for r in data.get("ignored_picture_rects", []) if r["page"] == pi]
            pictures = [fitz.Rect(b["bbox"]) for b in source[pi].get_text("dict")["blocks"] if b["type"] == 1
                        and not any(fitz.Rect(b["bbox"]) == r for r in ignored)]
            restored_math = [fitz.Rect(r["rect"]) for r in data.get("preserve_rects", [])
                             if r["page"] == pi and not any(fitz.Rect(r["rect"]) == q for q in pictures)]
            for block in page.get_text("dict")["blocks"]:
                if block["type"] != 0:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        if not re.search("[가-힣]", span["text"]):
                            continue
                        korean += 1
                        for picture in pictures:
                            overlap = fitz.Rect(span["bbox"]) & picture
                            if overlap.width > .5 and overlap.height > .5:
                                hits.append({"page": pi+1, "text": span["text"], "overlap": list(overlap)})
                        for equation in restored_math:
                            overlap = fitz.Rect(span["bbox"]) & equation
                            if overlap.width > .5 and overlap.height > .5:
                                math_hits.append({"page": pi+1, "text": span["text"], "overlap": list(overlap)})
        missing = [e["id"] for e in data["entries"] if not e["ko"].strip()]
        # Original formula glyph boxes include large empty ascender/descender margins.
        # Small bounding-box intersections are candidates for visual review, not proof of ink collision.
        critical_math = [hit for hit in math_hits
                         if hit["overlap"][3]-hit["overlap"][1] > 8
                         and hit["overlap"][2]-hit["overlap"][0] > 12]
        sha = hashlib.sha256(target.read_bytes()).hexdigest()
        ink_path = ROOT / "tmp" / "izho-qa" / f"{year}_{kind}_ink.json"
        ink = json.loads(ink_path.read_text(encoding="utf8")) if ink_path.exists() else {}
        ink_reviewed = isinstance(ink, dict) and ink.get("sha256") == sha and ink.get("flagged_components") == 0
        if ((hits or critical_math) and not ink_reviewed) or missing:
            failures.append(f"{year}/{kind}: {len(hits)} figure overlaps; {len(critical_math)} large equation intersections; {len(missing)} untranslated regions")
        item = {"file": target.name, "pages": len(output), "translated_regions": sum(not e.get("passthrough", False) for e in data["entries"]),
                "Korean_spans": korean, "image_overlaps": hits, "equation_bbox_candidates": math_hits,
                "large_equation_intersections": critical_math, "equation_ink_review_passed": ink_reviewed,
                "figure_ink_review_passed": ink_reviewed, "untranslated": missing,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
        report.append(item)
        print(json.dumps({"file": item["file"], "pages": item["pages"],
                          "translated_regions": item["translated_regions"],
                          "figure_overlaps": len(hits), "equation_bbox_candidates": len(math_hits),
                          "large_equation_intersections": len(critical_math), "equation_ink_review_passed": ink_reviewed,
                          "untranslated": len(missing), "sha256": item["sha256"]}, ensure_ascii=False))
audit = ROOT / "tmp" / "izho-qa" / "overlap-audit.json"
audit.parent.mkdir(parents=True, exist_ok=True)
audit.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf8")
if failures:
    raise SystemExit("\n".join(failures))

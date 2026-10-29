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
a = p.parse_args()
failures = []
report = []
for year in a.years:
    for kind in ("T", "TS"):
        path = ROOT / "tools" / "ko" / "izho" / str(year) / kind / "translation.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf8"))
        source = fitz.open(resolve_source(data))
        if data.get("source_pages") is not None:
            source.select(data["source_pages"])
        target = ROOT / "pdfx" / "izho" / f"IZhO_{year}_{kind}_KO.pdf"
        output = fitz.open(target)
        if len(source) != len(output):
            failures.append(f"{year}/{kind}: page count differs")
        hits = []
        korean = 0
        for pi, page in enumerate(output):
            pictures = [fitz.Rect(b["bbox"]) for b in source[pi].get_text("dict")["blocks"] if b["type"] == 1]
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
        missing = [e["id"] for e in data["entries"] if not e["ko"].strip()]
        if hits or missing:
            failures.append(f"{year}/{kind}: {len(hits)} Korean spans intersect figures; {len(missing)} untranslated regions")
        item = {"file": target.name, "pages": len(output), "translated_regions": len(data["entries"]),
                "Korean_spans": korean, "image_overlaps": hits, "untranslated": missing,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
        report.append(item)
        print(json.dumps(item, ensure_ascii=False))
audit = ROOT / "tmp" / "izho-qa" / "overlap-audit.json"
audit.parent.mkdir(parents=True, exist_ok=True)
audit.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf8")
if failures:
    raise SystemExit("\n".join(failures))

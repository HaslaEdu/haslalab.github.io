#!/usr/bin/env python3
"""Validate the restored USAPhO editions against their original pages and IDs."""
import hashlib
import json
from pathlib import Path

import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sources = json.loads((ROOT / "tools/usapho_restore_sources.json").read_text(encoding="utf-8"))
    translations = json.loads((ROOT / "tools/usapho_ko_additions.json").read_text(encoding="utf-8"))["usapho"]
    layout = json.loads((ROOT / "tmp/source-audit/usapho-design/restore-report.json").read_text(encoding="utf-8"))
    assert set(sources) == set(translations) == {str(year) for year in range(1997, 2027)}
    report = []
    pages = 0
    for year, source in sorted(sources.items()):
        path = ROOT / translations[year]["T"]["paper"]
        official = ROOT / source["en"]
        original, output = fitz.open(official), fitz.open(path)
        assert len(original) == len(output), f"{year}: page count"
        assert all(a.rect == b.rect for a, b in zip(original, output)), f"{year}: page geometry"
        item = layout[year]
        expected = {"A1", "A2", "A3", "A4", "B1", "B2"} if int(year) < 2018 else {"A1", "A2", "A3", "B1", "B2", "B3"}
        if year == "2008":
            expected.add("C1")
        assert set(item["original_questions"]) == set(item["translated_questions"]) == expected, f"{year}: printed question IDs"
        question_pages = {piece[0] for parts in item["original_regions"].values() for piece in parts}
        for index, page in enumerate(output):
            pixels = page.get_pixmap(matrix=fitz.Matrix(.25, .25), colorspace=fitz.csGRAY)
            assert sum(value < 180 for value in pixels.samples) > 30, f"{year}/{index + 1}: blank page"
            if index in question_pages:
                height = 120 if year == "2006" else 40
                first_body = min(piece[1] for parts in item["original_regions"].values() for piece in parts if piece[0] == index)
                height = max(1, min(height, first_body - 2))
                region = fitz.Rect(0, 0, page.rect.width, height)
                a = original[index].get_pixmap(matrix=fitz.Matrix(1, 1), colorspace=fitz.csGRAY, clip=region)
                b = page.get_pixmap(matrix=fitz.Matrix(1, 1), colorspace=fitz.csGRAY, clip=region)
                assert a.samples == b.samples, f"{year}/{index + 1}: source header changed"
        pages += len(output)
        report.append({"year": int(year), "file": path.name, "pages": len(output), "questions": sorted(expected),
                       "source_url": source["source_url"], "source_sha256": digest(official),
                       "translation_input_sha256": digest(ROOT / source["ko"]), "output_sha256": digest(path),
                       "minimum_body_scale": min(q["scale"] for q in item["questions"].values()),
                       "layout_notes": [q["layout_note"] for q in item["questions"].values() if q.get("layout_note")]})
    data = {"files": len(report), "pages": pages, "question_sets": len(report),
            "questions": sum(len(item["questions"]) for item in report),
            "checks": ["exact original page counts", "exact original page dimensions", "printed question IDs", "nonblank rendered pages", "original question headers", "source/input/output SHA-256"],
            "editions": report}
    (ROOT / "tools/usapho_restore_report.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in data.items() if key != "editions"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

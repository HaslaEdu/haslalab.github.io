"""Extract private source regions from the reviewed 202-page PNS Optics scan.

No OCR service, translation provider, or network request is used. Embedded OCR
is retained as unverified source text. The profile is intentionally fail-closed:
an unfamiliar edition or a missing number/solution boundary requires review.
Book content and crops must be written outside this public Git checkout.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import tempfile
from difflib import SequenceMatcher
from pathlib import Path

import pymupdf
from PIL import Image
from private_paths import private_directory


PARTS = (
    (1, 13, 60, 41, r"^[1lI][0oO][0-9sSlI]{2}$", "geometrical-optics"),
    (2, 63, 160, 89, r"^[23][0oO][0-9sSlI]{2}$", "wave-optics"),
    (3, 163, 202, 30, r"^[358sS][0oO][0-9sSlI]{2}$", "quantum-optics"),
)


def write_bytes(path: Path, data: bytes):
    """Leave the existing artifact intact if storage fills during a write."""
    if path.exists() and path.read_bytes() == data:
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".extract-",
                                         suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def layout(document):
    pages = []
    flags = pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES
    for index, page in enumerate(document):
        lines = []
        for block in page.get_text("dict", flags=flags)["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block["lines"]:
                lines.append({
                    "text": "".join(span["text"] for span in line["spans"]).strip(),
                    "bbox": list(line["bbox"]),
                    "fonts": [span["font"] for span in line["spans"]],
                })
        pages.append({"page": index + 1, "width": page.rect.width,
                      "height": page.rect.height, "lines": lines})
    return pages


def is_solution(line):
    clean = re.sub(r"[^a-z]", "", line["text"].lower())
    return (len(line["text"]) < 30 and clean.startswith(("sol", "soh"))
            and SequenceMatcher(None, clean, "solution").ratio() > .65)


def headers(pages):
    found = []
    for part, first_page, last_page, count, pattern, chapter in PARTS:
        section = []
        for page in pages[first_page - 1:last_page]:
            for line in page["lines"]:
                box = line["bbox"]
                label = re.sub(r"\s+", "", line["text"])
                if (re.fullmatch(pattern, label)
                    and any("Bold" in font for font in line["fonts"])
                    and box[0] > page["width"] * .37
                    and box[2] < page["width"] * .65
                    and 48 < box[1] < page["height"] - 45):
                    section.append({"page": page["page"], "bbox": box,
                                    "raw_label": line["text"], "origin": "embedded_ocr"})
        if part == 1:
            # This whole statement is absent from the embedded OCR. Its number,
            # statement and separate problem figure were read on source page 14.
            section.append({"page": 14, "bbox": [205, 222, 235, 237],
                            "raw_label": None, "origin": "visual_source_review"})
        section.sort(key=lambda item: (item["page"], item["bbox"][1]))
        if len(section) != count:
            raise ValueError(f"Part {part}: found {len(section)} number regions; expected {count}. Review required.")
        for index, item in enumerate(section, 1):
            item.update(number=str(part * 1000 + index), chapter=chapter, part=part)
        found.extend(section)
    return found


def point(item):
    return item["page"], item["bbox"][1]


def normalize_box(box, page):
    width, height = page["width"], page["height"]
    return [round(box[0] / width, 7), round(box[1] / height, 7),
            round(box[2] / width, 7), round(box[3] / height, 7)]


def extract(pdf: Path, output: Path, drive_id: str, revision: str, dpi: int,
            transcriptions=None, region_overrides=None):
    output = private_directory(output)
    recovered = {}
    if transcriptions:
        supplied = json.loads(transcriptions.read_text(encoding="utf-8-sig"))
        if supplied.get("source_sha256") != hashlib.sha256(pdf.read_bytes()).hexdigest():
            raise ValueError("Private transcription source hash mismatch")
        recovered = supplied.get("transcriptions", {})
    reviewed_regions = {}
    if region_overrides:
        supplied = json.loads(region_overrides.read_text(encoding="utf-8-sig"))
        if supplied.get("source_sha256") != hashlib.sha256(pdf.read_bytes()).hexdigest():
            raise ValueError("Private region-review source hash mismatch")
        reviewed_regions = supplied.get("questions", {})
    repo = Path(__file__).resolve().parents[2]
    if output.resolve().is_relative_to(repo):
        raise ValueError("Book content must be written outside the public Git checkout.")
    if not 72 <= dpi <= 180:
        raise ValueError("Crop dpi must be between 72 and 180.")
    document = pymupdf.open(pdf)
    if len(document) != 202:
        raise ValueError("This reviewed profile supports the 202-page PNS Optics scan only.")
    pages = layout(document)
    starts = headers(pages)
    solutions = [dict(line, page=page["page"]) for page in pages[12:]
                 for line in page["lines"] if is_solution(line)]
    solutions.append({"page": 14, "bbox": [56, 408, 110, 424],
                      "text": "Solution:", "origin": "visual_source_review"})
    solutions.sort(key=point)
    if len(solutions) != 160:
        raise ValueError(f"Found {len(solutions)} solution boundaries; expected 160. Review required.")
    output.mkdir(parents=True, exist_ok=True)
    (output / "crops").mkdir(exist_ok=True)
    questions = []
    failures = []
    for index, start in enumerate(starts):
        end_limit = point(starts[index + 1]) if index + 1 < len(starts) else (203, 0)
        boundaries = [line for line in solutions if point(start) < point(line) < end_limit]
        if len(boundaries) != 1:
            failures.append({"number": start["number"], "reason": "ambiguous_solution_boundary",
                             "candidate_count": len(boundaries)})
            continue
        stop = boundaries[0]
        regions = []
        for page_number in range(start["page"], stop["page"] + 1):
            page = pages[page_number - 1]
            top = start["bbox"][1] - 5 if page_number == start["page"] else 50
            bottom = stop["bbox"][1] - 3 if page_number == stop["page"] else page["height"] - 48
            if bottom > top + 3:
                regions.append({"page": page_number, "bbox_points": [25, top, page["width"] - 18, bottom]})
        if start["number"] == "1003":
            # Fig. 1.4 is a solution diagram printed alongside Fig. 1.3, above
            # the Solution heading. Keep only the referenced problem diagram.
            regions = [{"page": 14, "bbox_points": [45, 218, 389, 301]},
                       {"page": 14, "bbox_points": [58, 300, 204, 405]}]
        region_review = reviewed_regions.get(start["number"])
        if region_review:
            # A referenced problem figure can be printed after the Solution
            # heading, and a solution diagram can precede that heading. The
            # private, source-hash-bound visual review records exact rectangles.
            regions = []
            for reviewed in region_review["regions"]:
                page_number = reviewed["page"]
                if not 1 <= page_number <= len(pages):
                    raise ValueError("Reviewed source page is outside the PDF")
                x0, y0, x1, y1 = reviewed["bbox"]
                if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
                    raise ValueError("Reviewed rectangles must be normalized and nonempty")
                page = pages[page_number - 1]
                regions.append({"page": page_number, "bbox_points": [
                    x0 * page["width"], y0 * page["height"],
                    x1 * page["width"], y1 * page["height"]]})
            if not regions:
                raise ValueError("A reviewed statement cannot have no source regions")
        extracted_lines = []
        assets = []
        spans = []
        for region_index, region in enumerate(regions, 1):
            page = pages[region["page"] - 1]
            box = region["bbox_points"]
            span = {"page": region["page"], "bbox": normalize_box(box, page)}
            spans.append(span)
            for line in page["lines"]:
                x0, y0, x1, y1 = line["bbox"]
                if box[0] <= (x0 + x1) / 2 <= box[2] and box[1] <= (y0 + y1) / 2 < box[3]:
                    if line["text"] and not is_solution(line):
                        extracted_lines.append(line["text"])
            pixmap = document[region["page"] - 1].get_pixmap(
                matrix=pymupdf.Matrix(dpi / 72, dpi / 72),
                clip=pymupdf.Rect(box), alpha=False)
            image_path = output / "crops" / f"{start['number']}-{region_index:02d}.webp"
            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
            encoded = io.BytesIO()
            image.save(encoded, "WEBP", quality=92, method=4)
            write_bytes(image_path, encoded.getvalue())
            assets.append({"role": "question_crop", "local_path": str(image_path.resolve()),
                           "mime_type": "image/webp", "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                           "spans": [span], "review_status": "pending"})
        text = "\n".join(extracted_lines)
        if start["number"] == "1003":
            # Recovered book text belongs in private input data, never public source code.
            text = recovered.get("1003", "")
        # Crop images remain the source of truth. OCR may have missing words,
        # corrupted equations or unreferenced diagrams even within these bounds.
        flags = ["embedded_ocr_not_proofread", "math_not_verified", "figure_assignment_not_verified"]
        if re.sub(r"\s+", "", start["raw_label"] or "") != start["number"]:
            flags.append("number_corrected_by_section_sequence_needs_visual_review")
        if start["number"] == "1003":
            flags.extend(["statement_visually_transcribed" if text else "statement_transcription_required",
                          "solution_figure_1.4_excluded"])
        if region_review:
            flags.append("source_regions_visually_reviewed")
            flags.extend(region_review.get("quality_flags", []))
        questions.append({
            "source": {"drive_id": drive_id, "revision": revision},
            "locator": f"part-{start['part']}/problem-{start['number']}",
            "original_number": start["number"], "chapter": start["chapter"],
            "kind": "problem", "subjects": ["optics"] + (["quantum_mechanics"] if start["part"] == 3 else []),
            "level": "mixed", "review_status": "pending", "spans": spans,
            "versions": ([{"language": "en", "role": "original", "text": text,
                          "review_status": "pending", "extraction_method": "embedded_ocr_with_visual_recovery"}] if text.strip() else []),
            "assets": assets,
            "figure_references_raw": sorted(set(re.findall(r"Fig\.?\s*([0-9S]\.[0-9]+)", text))),
            "number_region": {"page": start["page"], "bbox": normalize_box(start["bbox"], pages[start["page"] - 1]),
                              "raw_ocr": start["raw_label"], "origin": start["origin"]},
            "solution_start": {"page": stop["page"], "bbox": normalize_box(stop["bbox"], pages[stop["page"] - 1])},
            "quality_flags": flags,
            **({"source_region_review_notes": region_review.get("notes", [])}
               if region_review else {}),
        })
    expected = [str(part * 1000 + i) for part, _, _, count, _, _ in PARTS for i in range(1, count + 1)]
    numbers = [question["original_number"] for question in questions]
    missing = sorted(set(expected) - set(numbers))
    duplicate = sorted({number for number in numbers if numbers.count(number) > 1})
    audit = {"source_page_count": len(document), "expected_question_count": 160,
             "extracted_question_count": len(questions), "missing_numbers": missing,
             "duplicate_numbers": duplicate, "boundary_errors": failures,
             "all_versions_review_status": "pending", "korean_translation_count": 0,
             "paid_api_calls": 0, "source_crops_authoritative": True,
             "not_ready_for_publication": True,
             "visually_reviewed_region_override_count": len(reviewed_regions),
             "known_limitations": ["Embedded OCR is incomplete and contains wrong symbols and numbers.",
                                   "Crop boundaries default to the printed Solution heading; source-hash-bound visual overrides isolate reviewed figures.",
                                   "Problem 1003 has a visual transcription and separate crop for its referenced Fig. 1.3."]}
    data = {"version": 1, "profile": "pns-optics-202-page-scan",
            "source_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(), "questions": questions}
    write_bytes(output / "questions.raw.json", json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
    write_bytes(output / "coverage-audit.json", json.dumps(audit, ensure_ascii=False, indent=2).encode("utf-8"))
    print(json.dumps(audit, ensure_ascii=False))
    if missing or duplicate or failures:
        raise ValueError("Incomplete coverage. Inspect coverage-audit.json before importing.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--drive-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--dpi", type=int, default=120)
    parser.add_argument("--transcriptions", type=Path)
    parser.add_argument("--region-overrides", type=Path,
                        help="Private source-hash-bound normalized source rectangles from visual review")
    args = parser.parse_args()
    extract(args.pdf, args.out, args.drive_id, args.revision, args.dpi,
            args.transcriptions, args.region_overrides)


if __name__ == "__main__":
    main()

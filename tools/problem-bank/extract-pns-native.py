"""Extract private question regions from a profiled native-OCR PNS scan.

Profiles and all manually recovered source text live outside the public checkout.
The extractor requires a fixed PDF hash, a table-of-contents number sequence and
explicit, reviewed overrides for OCR label errors or absent solution markers.
No OCR service, translation provider, API, network, or publication is used.
"""

from __future__ import annotations

import argparse
from collections import Counter
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import sys

import pymupdf
from PIL import Image

from private_paths import private_directory


PUBLIC_ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def private_input(path):
    path = Path(path).resolve()
    if path.is_relative_to(PUBLIC_ROOT):
        raise ValueError("Source profiles/overrides must remain outside the public checkout")
    return path


def point(line):
    return line["page"], line["bbox"][1]


def layout(document, profile):
    pages = []
    settings = profile["layout"]
    flags = pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES
    for page_number, page in enumerate(document, 1):
        lines = []
        for block in page.get_text("dict", flags=flags)["blocks"]:
            for line in block.get("lines", []):
                text = "".join(span["text"] for span in line["spans"]).strip()
                if text:
                    lines.append({"page": page_number, "bbox": list(line["bbox"]),
                                  "text": text, "max_size": max(s["size"] for s in line["spans"]),
                                  "fonts": sorted({s["font"] for s in line["spans"]})})
        top = settings["body_top"]
        for line in lines:
            if line["bbox"][1] >= 100:
                continue
            clean = re.sub(r"[^a-z]", "", line["text"].lower())
            for title in settings.get("running_header_strings", []):
                target = re.sub(r"[^a-z]", "", title.lower())
                if (clean and len(clean) <= len(target) * 1.5
                        and SequenceMatcher(None, clean, target).ratio() > .72):
                    top = max(top, line["bbox"][3] + 5)
        bottom = min(settings["body_bottom"], page.rect.height - 5)
        if page_number in settings.get("footer_pages", []):
            # Part-opening pages put the folio at the foot, while ordinary pages
            # put it in the running header. Never infer a footer from OCR order.
            footer = [line for line in lines if line["text"].isdigit()
                      and line["bbox"][1] > 530 and line["bbox"][2] - line["bbox"][0] < 24
                      and page.rect.width * .45 < (line["bbox"][0] + line["bbox"][2]) / 2 < page.rect.width * .55]
            if footer:
                bottom = min(bottom, min(line["bbox"][1] for line in footer) - 3)
        pages.append({"page": page_number, "width": page.rect.width, "height": page.rect.height,
                      "body_top": top, "body_bottom": bottom, "lines": lines})
    return pages


def expected_numbers(profile):
    result = []
    for part in profile["parts"]:
        numbers = list(range(part["first_number"], part["last_number"] + 1))
        if len(numbers) != part["expected_count"]:
            raise ValueError("Profile part count disagrees with printed number range")
        result.extend(str(number) for number in numbers)
    if len(result) != len(set(result)):
        raise ValueError("Profile number ranges overlap")
    return result


def number_headers(pages, profile, overrides):
    expected = expected_numbers(profile)
    expected_set = set(expected)
    corrections = {(item["page"], item["raw_label"]): item for item in overrides.get("number_labels", [])}
    candidates = []
    first = min(part["first_page"] for part in profile["parts"])
    last = max(part["last_page"] for part in profile["parts"])
    for page in pages[first - 1:last]:
        for line in page["lines"]:
            label = re.sub(r"\s+", "", line["text"])
            box = line["bbox"]
            # Confusable glyphs permit candidacy, never an unreviewed correction.
            normalized = label.translate(str.maketrans({"I": "1", "l": "1", "O": "0", "S": "5", "s": "3"}))
            if (re.fullmatch(r"[1-9][0-9IlOSs]{3}", label) and normalized in expected_set
                    and box[0] > page["width"] * .42 and box[2] < page["width"] * .60
                    and 50 < box[1] < page["height"] - 35):
                candidates.append(dict(line, raw_label=line["text"]))
    candidates.sort(key=point)
    if len(candidates) != len(expected):
        raise ValueError(f"Expected {len(expected)} number labels; found {len(candidates)}. Source review required")
    for candidate, number in zip(candidates, expected):
        raw = re.sub(r"\s+", "", candidate["raw_label"])
        if raw != number:
            correction = corrections.get((candidate["page"], candidate["raw_label"]))
            if (not correction or correction["number"] != number
                    or correction.get("source_image_checked") is not True
                    or any(abs(a - b) > .5 for a, b in zip(correction["bbox"], candidate["bbox"]))):
                raise ValueError(f"Unreviewed number discrepancy p{candidate['page']}: OCR {raw}, expected {number}")
            candidate["number_origin"] = "private_visually_verified_source_label"
        else:
            candidate["number_origin"] = "native_ocr_label_matches_toc_sequence"
        candidate["number"] = number
        part = next(part for part in profile["parts"]
                    if part["first_number"] <= int(number) <= part["last_number"])
        if not part["first_page"] <= candidate["page"] <= part["last_page"]:
            raise ValueError(f"Question {number} falls outside its profiled part pages")
        candidate["part"] = part["part"]
    return candidates


def solution_headers(pages, overrides):
    found = []
    for page in pages:
        for line in page["lines"]:
            text = line["text"]
            clean = re.sub(r"[^a-z]", "", text.lower())
            if (len(text) < 30 and clean.startswith("so") and line["bbox"][0] < 120
                    and line["bbox"][1] > 55 and SequenceMatcher(None, clean, "solution").ratio() > .65):
                found.append(dict(line, origin="native_ocr_solution_heading"))
    for marker in overrides.get("solution_markers", []):
        if marker.get("source_image_checked") is not True:
            raise ValueError("A missing OCR solution marker requires visual source review")
        found.append({"page": marker["page"], "bbox": marker["bbox"], "text": "Solution:",
                      "number": marker["number"], "origin": "private_visually_verified_solution_heading"})
    return sorted(found, key=point)


def normalize(region, pages):
    page = pages[region["page"] - 1]
    x0, y0, x1, y1 = region["bbox_points"]
    if not (0 <= x0 < x1 <= page["width"] and 0 <= y0 < y1 <= page["height"]):
        raise ValueError(f"Invalid source region {region}")
    return {"page": region["page"], "bbox": [round(x0 / page["width"], 7), round(y0 / page["height"], 7),
            round(x1 / page["width"], 7), round(y1 / page["height"], 7)]}


def question_regions(start, stop, pages, profile):
    regions = []
    for page_number in range(start["page"], stop["page"] + 1):
        page = pages[page_number - 1]
        top = start["bbox"][1] - 4 if page_number == start["page"] else page["body_top"]
        bottom = stop["y"] if page_number == stop["page"] else page["body_bottom"]
        if bottom > top + 2:
            regions.append({"page": page_number, "bbox_points": [profile["layout"]["left"], top,
                            page["width"] - profile["layout"]["right_margin"], bottom]})
    return regions


def render(document, region, target, dpi):
    pix = document[region["page"] - 1].get_pixmap(matrix=pymupdf.Matrix(dpi / 72, dpi / 72),
            clip=pymupdf.Rect(region["bbox_points"]), alpha=False, colorspace=pymupdf.csRGB)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    image.save(target, "WEBP", lossless=True, method=4)
    return {"width": image.width, "height": image.height, "byte_length": target.stat().st_size}


def white_region(document, region):
    # Text absence cannot establish that a diagram is absent. Inspect source
    # pixels instead, so image-only equations/figures always remain eligible.
    pix = document[region["page"] - 1].get_pixmap(matrix=pymupdf.Matrix(1, 1),
            clip=pymupdf.Rect(region["bbox_points"]), alpha=False, colorspace=pymupdf.csGRAY)
    return bool(pix.samples) and min(pix.samples) >= 250


def extract(args):
    output = private_directory(args.out)
    profile = read_json(private_input(args.profile))
    overrides = read_json(private_input(args.overrides)) if args.overrides else {}
    source_hash = sha(args.pdf)
    if source_hash != profile["source_sha256"] or overrides.get("source_sha256", source_hash) != source_hash:
        raise ValueError("Unrecognised PDF hash: profile/override review required")
    if not 96 <= args.dpi <= 180:
        raise ValueError("Source crop DPI must be between 96 and 180")
    source = next(item for item in read_json(args.manifest)["sources"] if item["drive_id"] == profile["drive_id"])
    if source["sha256"] != source_hash:
        raise ValueError("Manifest does not match the supplied PDF revision")
    document = pymupdf.open(args.pdf)
    if len(document) != profile["page_count"]:
        raise ValueError("Page count disagrees with reviewed profile")
    pages = layout(document, profile)
    headers = number_headers(pages, profile, overrides)
    solutions = solution_headers(pages, overrides)
    images = output / "crops"
    images.mkdir(exist_ok=True)
    cache = {}
    if args.reuse_matching_crops and (output / "crop-audit.json").is_file():
        old = read_json(output / "crop-audit.json")
        if old.get("source_sha256") == source_hash and old.get("crop_dpi") == args.dpi:
            for question in old["questions"]:
                for index, asset in enumerate(question["assets"]):
                    cache[(question["locator"], index)] = asset
    questions, audits, no_solution = [], [], []
    for index, start in enumerate(headers):
        number = start["number"]
        limit = point(headers[index + 1]) if index + 1 < len(headers) else (len(document) + 1, 0)
        candidates = [item for item in solutions if point(start) < point(item) < limit]
        explicit = overrides.get("question_ends", {}).get(number)
        if explicit:
            if explicit.get("source_image_checked") is not True:
                raise ValueError(f"Question {number} end override lacks visual review")
            stop = explicit
            boundary = {"origin": "private_visually_verified_question_end", **explicit}
            if explicit.get("no_solution_printed"):
                if candidates:
                    raise ValueError(f"Question {number}: a solution contradicts no-solution override")
                no_solution.append(number)
        else:
            if len(candidates) != 1:
                raise ValueError(f"Question {number}: expected one Solution boundary, found {len(candidates)}")
            marker = candidates[0]
            if marker.get("number", number) != number:
                raise ValueError(f"Private solution marker assigned to the wrong question: {number}")
            stop = {"page": marker["page"], "y": marker["bbox"][1] - 2.7}
            boundary = marker
        regions = question_regions(start, stop, pages, profile)
        if number in overrides.get("question_regions", {}):
            replacement = overrides["question_regions"][number]
            if replacement.get("source_image_checked") is not True:
                raise ValueError(f"Question {number} crop override lacks source review")
            regions = replacement["regions"]
        if not regions:
            raise ValueError(f"Question {number} has no source regions")
        blank_regions = [region for region in regions if white_region(document, region)]
        regions = [region for region in regions if region not in blank_regions]
        if not regions:
            raise ValueError(f"Question {number} source regions are all white: source review required")
        spans = [normalize(region, pages) for region in regions]
        texts = [document[region["page"] - 1].get_text("text", clip=pymupdf.Rect(region["bbox_points"]),
                 sort=True).strip() for region in regions]
        text = "\n\n".join(texts).strip()
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "\ufffd", text)
        manual_text = overrides.get("text_overrides", {}).get(number)
        if manual_text:
            if manual_text.get("source_image_checked") is not True:
                raise ValueError("A private source transcription requires image review")
            text = manual_text["text"]
        if not text:
            # An image-only question still gets its locator and canonical image,
            # not fabricated prose or an invented translation.
            text = f"[Question {number}: source text layer absent; see original source crop.]"
        locator = f"part-{start['part']}/problem-{number}"
        assets, image_audits = [], []
        for asset_index, region in enumerate(regions):
            target = images / f"problem-{number}-{asset_index + 1:02d}.webp"
            previous = cache.get((locator, asset_index))
            if (previous and previous["region"] == region and target.is_file()
                    and previous["sha256"] == sha(target)):
                dimensions = previous["dimensions"]
            else:
                dimensions = render(document, region, target, args.dpi)
            digest = sha(target)
            assets.append({"asset_id": f"crop-{asset_index + 1}", "role": "question_crop",
                           "local_path": str(target.resolve()), "sha256": digest, "mime_type": "image/webp",
                           "spans": [normalize(region, pages)], "review_status": "pending"})
            image_audits.append({"region": region, "dimensions": dimensions, "sha256": digest})
        section = next(section for section in profile["sections"]
                       if section["first_number"] <= int(number) <= section["last_number"])
        flags = ["embedded_ocr_math_unverified", "canonical_source_crops_pending_review"]
        if start["number_origin"].startswith("private"):
            flags.append("number_ocr_corrected_from_verified_printed_label")
        if manual_text:
            flags.append("private_source_transcription_supplied")
        context = {"source_author": profile["source_author"], "profile": profile["profile"],
                   "canonical_representation": "lossless_source_question_crops", "quality_flags": flags,
                   "number_origin": start["number_origin"], "number_raw_ocr": start["raw_label"],
                   "solution_boundary_origin": boundary["origin"], "unresolved_source": False,
                   "provenance_notes": "User-supplied PNS volume; original embedded OCR is unverified, with university credits retained in source crops."}
        if number in no_solution:
            context["no_solution_printed"] = True
        if number in overrides.get("question_regions", {}):
            context["source_region_override_review_note"] = overrides["question_regions"][number].get("review_note", "")
        if blank_regions:
            context["white_continuation_regions_omitted"] = blank_regions
        questions.append({"source": {"drive_id": source["drive_id"], "revision": source["revision"]},
                          "source_language": "en", "locator": locator, "original_number": number,
                          "chapter": section["chapter"], "kind": "problem", "subjects": section["subjects"],
                          "level": profile["level"], "review_status": "pending", "spans": spans,
                          "versions": [{"language": "en", "role": "original", "text": text,
                                        "review_status": "pending", "extraction_method": "native_ocr_with_canonical_source_crops"}],
                          "assets": assets, "context": context})
        audits.append({"locator": locator, "number": number, "number_region": start,
                       "solution_boundary": boundary, "assets": image_audits, "review_status": "pending"})
        if (index + 1) % 50 == 0:
            print(f"Extracted {index + 1}/{len(headers)} source questions", flush=True)
    counts = Counter(question["subjects"][0] for question in questions)
    audit = {"version": 1, "profile": profile["profile"], "source_sha256": source_hash,
             "page_count": len(document), "expected_question_count": len(expected_numbers(profile)),
             "found_question_count": len(questions), "found_numbers": [question["original_number"] for question in questions],
             "gaps": [], "duplicates": [], "number_coverage_complete": True,
             "toc_evidence": profile["toc_evidence"], "preface_evidence": profile["preface_evidence"],
             "subject_counts": dict(counts), "solution_boundary_count": len(solutions),
             "no_solution_printed": no_solution, "private_number_corrections": len(overrides.get("number_labels", [])),
             "private_solution_markers": len(overrides.get("solution_markers", [])),
             "asset_count": sum(len(question["assets"]) for question in questions), "crop_dpi": args.dpi,
             "paid_api_calls": 0, "statement_boundary_review_complete": False, "publication_ready": False,
             "review_limitations": ["Coverage applies to the fixed profiled PDF revision, not to other editions.",
                                    "Native OCR mathematical text is noisy; original images remain canonical.",
                                    "All problem crops and text versions remain pending mathematical/layout review.",
                                    "No new conditions, solutions or translations were invented during extraction."]}
    write_json(output / "questions.raw.json", {"version": 1, "source_sha256": source_hash,
               "profile": profile["profile"], "paid_api_calls": 0, "questions": questions})
    write_json(output / "crop-audit.json", {"version": 1, "source_sha256": source_hash,
               "crop_dpi": args.dpi, "questions": audits})
    write_json(output / "coverage-audit.json", audit)
    print(json.dumps({key: audit[key] for key in ("found_question_count", "subject_counts", "asset_count",
               "solution_boundary_count", "no_solution_printed", "publication_ready")}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dpi", type=int, default=160)
    parser.add_argument("--reuse-matching-crops", action="store_true")
    extract(parser.parse_args())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

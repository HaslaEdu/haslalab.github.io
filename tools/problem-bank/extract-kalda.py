"""Private, offline extraction profile for the supplied 229-page compilation.

The compilation is not one continuously numbered Kalda book. It contains seven
numbered handouts (including a Kiisk translation and an Estonian Kree handout),
plus an eight-page solutions-only booklet. Printed locators are preserved even
when two handouts may contain the same physical problem. Source crops, rather
than unverified embedded PDF math text, are the authoritative representation.
No OCR/translation service, API call, publication, or network request is used.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys

import pymupdf
from PIL import Image

from private_paths import private_directory


SOURCE_SHA256 = "cdc374d8ac1992d6a5a5e244906f83fb0751e6477237267570318f93caa0264d"


@dataclass(frozen=True)
class Component:
    key: str
    first: int
    last: int
    count: int
    title: str
    author: str
    language: str
    subject: str
    color: int | None = None
    provenance: str = ""


COMPONENTS = (
    Component("mechanics", 1, 37, 86, "Problems on Mechanics", "Jaan Kalda", "en",
              "classical_mechanics", 0x004D4D,
              "Version 1.2 beta 1, 13 November 2019; translation partly by S. Ainsaar, T. Pungas and S. Zavjalov."),
    Component("kinematics", 38, 63, 66, "Problems on Kinematics", "Jaan Kalda", "en",
              "classical_mechanics", 0x004D4D,
              "Version 29 November 2017; translation partly by Taavi Pungas."),
    Component("electricity-magnetism-translation", 64, 111, 175,
              "Translation of Problems in Elektri Ja Magnetismi Ulesandeid", "Valter Kiisk", "en",
              "electromagnetism", None,
              "Original Valter Kiisk handout, version 2.0; translation edition 2.0.0, 9 April 2020, by Daniel Yang and Kushal Thaman; edited by Ashmit Dutta and QiLin Xue. Compilation attribution is not sole authorship."),
    Component("thermodynamics", 112, 151, 88, "Thermodynamics", "Jaan Kalda", "en",
              "thermodynamics", 0x00334D, "Version 15 June 2019."),
    Component("electrical-circuits", 152, 197, 111, "Electrical Circuits", "Jaan Kalda", "en",
              "electromagnetism", 0x00334D, "Version 3 December 2017."),
    Component("kepler-kree-et", 206, 215, 10, "Kepleri seadused ja muu taevamehaanika",
              "Mihkel Kree", "et", "classical_mechanics", None,
              "Estonian original, Mihkel Kree, 2006. This component is not authored by Kalda. No English or Korean translation has been fabricated."),
    Component("wave-optics", 216, 229, 19, "Wave Optics", "Jaan Kalda", "en", "optics",
              0x00334D, "Version 24 May 2016. Problem 19 includes black-text Part A and Part B after its coloured figure caption."),
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def layout(document):
    pages = []
    flags = pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES
    for page_number, page in enumerate(document, 1):
        lines = []
        for block in page.get_text("dict", flags=flags)["blocks"]:
            for line in block.get("lines", []):
                spans = line["spans"]
                text = "".join(span["text"] for span in spans).strip()
                if not text:
                    continue
                box = list(line["bbox"])
                lines.append({
                    "page": page_number, "bbox": box, "text": text,
                    "colors": sorted({span["color"] for span in spans}),
                    "max_size": max(span["size"] for span in spans),
                    "column": int((box[0] + box[2]) / 2 > page.rect.width / 2),
                    "fonts": sorted({span["font"] for span in spans}),
                })
        # Footnotes are black 8 pt prose at the foot of a column; long spanning
        # notes are excluded too. Do not lower a column below coloured 10 pt text.
        footnote_tops = [line["bbox"][1] for line in lines
                         if line["bbox"][1] > 730 and line["max_size"] < 8.5
                         and re.match(r"^\d+[A-Za-z]", line["text"])
                         and len(re.findall(r"[A-Za-z]{2,}", line["text"])) >= 3]
        pages.append({"page": page_number, "width": page.rect.width,
                      "height": page.rect.height, "lines": lines,
                      "body_bottom": min([816.0] + [v - 3.8 for v in footnote_tops])})
    return pages


def flow_key(line):
    return line["page"], line["column"], line["bbox"][1], line["bbox"][0]


def body_lines(component, pages):
    lines = []
    for page in pages[component.first - 1:component.last]:
        for line in page["lines"]:
            x0, y0, x1, y1 = line["bbox"]
            if (y0 < 44 or y0 >= page["body_bottom"] or y1 > 817
                    or x1 - x0 > 340):
                continue
            lines.append(line)
    return sorted(lines, key=flow_key)


def is_anchor(line, component):
    if component.key == "kepler-kree-et":
        return re.match(r"^Ülesanne\s+(\d+)\.", line["text"])
    match = re.match(r"^pr\s*(\d+)\.", line["text"])
    return match if match and (component.color is None or component.color in line["colors"]) else None


def find_anchors(component, pages):
    if component.key == "kepler-kree-et":
        # Single-column handout; labels 1-4 are embedded in theory, 5-10 form a
        # separate exercise section. Solutions and bibliography start on p212.
        candidates = [line for page in pages[205:211] for line in page["lines"]]
    elif component.key == "electricity-magnetism-translation":
        candidates = [line for page in pages[63:111] for line in page["lines"]]
    else:
        candidates = body_lines(component, pages)
    anchors = []
    for line in candidates:
        match = is_anchor(line, component)
        if match:
            anchors.append(dict(line, number=int(match.group(1))))
    if component.color is None:
        return sorted(anchors, key=lambda line: (line["page"], line["bbox"][1]))
    return sorted(anchors, key=flow_key)


def is_narrative(line):
    text = line["text"]
    words = re.findall(r"[A-Za-z]{2,}", text)
    # Short black diagram labels and mathematical lines are not solution prose.
    return (line["max_size"] >= 8.5 and len(words) >= 4
            and sum(map(len, words)) >= 15)


def stop_heading(line):
    return re.match(r"^(?:idea\s+\d+|fact\s+\d+|def\.?\s*\d+|method\s+\d+|appendix\s+\d+|Hints\b|Answers\b)",
                    line["text"], re.I)


def standard_regions(component, anchor, next_anchor, pages, lines):
    start_key = flow_key(anchor)
    limit_key = flow_key(next_anchor) if next_anchor else (component.last + 1, 0, 0, 0)
    chunk = [line for line in lines if start_key <= flow_key(line) < limit_key]
    coloured = [i for i, line in enumerate(chunk) if component.color in line["colors"]]
    if not coloured:
        raise ValueError(f"No coloured source statement: {component.key}/{anchor['number']}")
    last = coloured[-1]
    statement_last = chunk[last]
    boundary = None
    reason = None
    if component.key == "wave-optics" and anchor["number"] == 19:
        # Verified against p227: black Part A/B belong to the problem; appendix
        # 1 starts at y593.9. The problem's figure was also retained in colour.
        for line in chunk[last + 1:]:
            if re.match(r"^appendix\s+1:", line["text"], re.I):
                boundary, reason = line, "reviewed_black_subquestions_before_appendix"
                break
    else:
        for line in chunk[last + 1:]:
            if stop_heading(line) or is_narrative(line):
                boundary = line
                reason = "heading_after_statement" if stop_heading(line) else "uncoloured_commentary_after_statement"
                break
    if boundary is None and next_anchor:
        boundary, reason = next_anchor, "next_printed_problem"
    if boundary is None:
        raise ValueError(f"No end boundary: {component.key}/{anchor['number']}")
    first_slot = anchor["page"] * 2 + anchor["column"]
    last_slot = boundary["page"] * 2 + boundary["column"]
    regions = []
    footnotes = []
    for slot in range(first_slot, last_slot + 1):
        page_number, column = divmod(slot, 2)
        page = pages[page_number - 1]
        top = anchor["bbox"][1] - 3.0 if slot == first_slot else 43.0
        bottom = min(page["body_bottom"], boundary["bbox"][1] - 2.7) if slot == last_slot else page["body_bottom"]
        if bottom <= top + 2:
            continue
        # A source figure can be a raster image with no embedded text at all
        # (e.g. Circuits pr1 on p154). Never infer a blank region from text alone.
        left, right = (16.1, 294.8) if column == 0 else (296.4, 575.0)
        regions.append({"page": page_number, "bbox_points": [left, max(42.8, top), right, bottom]})
        if page["body_bottom"] < 816:
            footnotes.append(page_number)
    if component.key == "thermodynamics" and anchor["number"] == 45:
        # The N-T graph between pr45 and pr46 belongs to pr46, whose statement
        # explicitly references it. Pr45 ends with the cV definition at y590.3.
        regions[-1]["bbox_points"][3] = 593.3
        reason = "reviewed_following_problem_figure_excluded"
    # A statement may span a column break but must not run through intervening
    # tutorial prose. Only 8 pt footnotes occur between its coloured text lines
    # in the reviewed source profile (they are removed from the page clips).
    internal_prose = [line for line in chunk[:last] if component.color not in line["colors"]
                      and is_narrative(line)]
    flags = []
    if internal_prose:
        flags.append("uncoloured_prose_inside_statement_requires_review")
    return regions, {
        "method": "reviewed_source_colour_and_two_column_flow",
        "start": {"page": anchor["page"], "bbox_points": anchor["bbox"]},
        "last_coloured_line": {"page": statement_last["page"], "bbox_points": statement_last["bbox"],
                                "text": statement_last["text"]},
        "stop": {"page": boundary["page"], "bbox_points": boundary["bbox"], "text": boundary["text"]},
        "stop_reason": reason, "footnote_pages_excluded": sorted(set(footnotes)),
        "internal_prose": [{"page": line["page"], "text": line["text"]} for line in internal_prose],
    }, flags


def gray_cards(document, component, anchors):
    regions = {}
    for page_number in range(component.first, component.last + 1):
        page = document[page_number - 1]
        cards = []
        for drawing in page.get_drawings():
            fill, rect = drawing.get("fill"), drawing["rect"]
            if (fill and len(fill) == 3 and all(.85 <= v <= .99 for v in fill)
                    and max(fill) - min(fill) < .015 and rect.width > page.rect.width * .7):
                cards.append(rect)
        for rect in cards:
            matched = [anchor for anchor in anchors if anchor["page"] == page_number
                       and rect.contains(pymupdf.Point(anchor["bbox"][0],
                                                      (anchor["bbox"][1] + anchor["bbox"][3]) / 2))]
            if len(matched) != 1:
                raise ValueError(f"p{page_number}: grey source card has {len(matched)} problem labels")
            number = matched[0]["number"]
            if number in regions:
                raise ValueError(f"Duplicate grey source card {number}")
            regions[number] = [{"page": page_number,
                                "bbox_points": [rect.x0 - 1, rect.y0 - 1, rect.x1 + 1, rect.y1 + 1]}]
    if len(regions) != component.count:
        raise ValueError(f"Expected {component.count} complete grey source cards, found {len(regions)}")
    return regions


# The Kree original interleaves black-text exercises and black-text theory, so
# colour alone cannot segment it. These source rectangles were checked against
# the printed paragraph and equation blocks. The p211 diagram belongs to pr10.
KREE_REGIONS = {
    1: [(207, [72.0, 651.8, 532.0, 673.3])],
    2: [(207, [72.0, 717.8, 532.0, 802.2])],
    3: [(207, [89.4, 717.8, 389.0, 737.0]), (208, [72.0, 101.0, 532.0, 135.0])],
    4: [(210, [72.0, 660.5, 532.0, 720.0])],
    5: [(211, [72.0, 129.7, 532.0, 180.5])],
    6: [(211, [72.0, 183.0, 532.0, 233.7])],
    7: [(211, [72.0, 236.2, 532.0, 285.2])],
    8: [(211, [72.0, 289.4, 532.0, 353.0])],
    9: [(211, [72.0, 357.2, 532.0, 420.7])],
    10: [(211, [72.0, 425.0, 532.0, 745.0])],
}

# Referenced source figures may precede their numbered problem. They are not
# tutorial solution figures: Thermodynamics pr23 explicitly requests data from
# this saturation-pressure graph printed immediately above its label on p127.
PRECEDING_FIGURES = {
    ("thermodynamics", 23): [{"page": 127, "bbox_points": [17.0, 308.3, 212.0, 468.0]}],
    ("thermodynamics", 46): [{"page": 136, "bbox_points": [298.0, 594.5, 495.5, 768.5]}],
}

SOURCE_FOOTNOTES = {
    ("kinematics", 62): [{"page": 55, "bbox_points": [24.0, 799.7, 261.0, 813.0]}],
    ("thermodynamics", 57): [{"page": 139, "bbox_points": [17.0, 788.8, 574.0, 813.0]}],
    ("thermodynamics", 67): [{"page": 141, "bbox_points": [27.0, 799.7, 571.0, 813.0]}],
    ("thermodynamics", 73): [{"page": 142, "bbox_points": [24.0, 799.7, 518.0, 813.0]}],
    ("thermodynamics", 76): [{"page": 144, "bbox_points": [24.0, 799.7, 248.0, 813.0]}],
    ("thermodynamics", 84): [{"page": 147, "bbox_points": [17.0, 747.8, 574.0, 790.9]}],
    ("thermodynamics", 85): [{"page": 147, "bbox_points": [17.0, 790.9, 574.0, 813.0]}],
    ("thermodynamics", 87): [{"page": 148, "bbox_points": [24.0, 799.7, 157.0, 813.0]}],
}


def normalized(region, pages):
    page = pages[region["page"] - 1]
    x0, y0, x1, y1 = region["bbox_points"]
    return {"page": region["page"], "bbox": [round(x0 / page["width"], 7),
            round(y0 / page["height"], 7), round(x1 / page["width"], 7), round(y1 / page["height"], 7)]}


def source_text(regions, document):
    # sort=True is only a reading aid. Complex equations are not reconstructed or
    # translated; original pixels retain their exact printed geometry.
    raw = "\n\n".join(document[region["page"] - 1].get_text(
        "text", clip=pymupdf.Rect(region["bbox_points"]), sort=True).strip() for region in regions).strip()
    # Some legacy TeX fonts map mathematical delimiters to C0 control codes.
    # Mark those missing text glyphs visibly; never invent their interpretation.
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "\ufffd", raw)


def render_crop(document, region, path: Path, dpi):
    page = document[region["page"] - 1]
    pix = page.get_pixmap(matrix=pymupdf.Matrix(dpi / 72, dpi / 72),
                          clip=pymupdf.Rect(region["bbox_points"]), alpha=False,
                          colorspace=pymupdf.csRGB)
    im = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    im.save(path, "WEBP", lossless=True, method=4)
    return {"width": im.width, "height": im.height, "byte_length": path.stat().st_size}


def extract(pdf: Path, output: Path, manifest: Path, dpi: int, reuse_matching: bool = False, drive_id=None):
    output = private_directory(output)
    if not 96 <= dpi <= 180:
        raise ValueError("Source crop DPI must be between 96 and 180")
    source_hash = digest(pdf)
    if source_hash != SOURCE_SHA256:
        raise ValueError("Unrecognised compilation revision: source SHA256 review required")
    source_manifest = json.loads(manifest.read_text(encoding="utf-8-sig"))
    candidates = [item for item in source_manifest["sources"] if item["sha256"] == SOURCE_SHA256
                  and (drive_id is None or item["drive_id"] == drive_id)]
    if len(candidates) != 1:
        raise ValueError("The private manifest must identify one source; use --drive-id for duplicate copies")
    source = candidates[0]
    drive_id = source["drive_id"]
    if source["sha256"] != source_hash:
        raise ValueError("Manifest SHA256 does not match source")
    document = pymupdf.open(pdf)
    if len(document) != 229:
        raise ValueError("This extraction profile supports the reviewed 229-page compilation only")
    pages = layout(document)
    crops_dir = output / "crops"
    crops_dir.mkdir(exist_ok=True)
    cache = {}
    if reuse_matching:
        # Reuse only byte-verified local crops whose exact source rectangle,
        # source hash and DPI match a previous completed run. Metadata/text and
        # boundaries are always recalculated from the PDF, never taken on trust.
        prior_paths = [output / name for name in ("questions.raw.json", "crop-audit.json", "coverage-audit.json")]
        if all(path.is_file() for path in prior_paths):
            old_raw, old_crops, old_coverage = [json.loads(path.read_text(encoding="utf-8")) for path in prior_paths]
            if (all(old.get("source_sha256") == source_hash for old in (old_raw, old_crops, old_coverage))
                    and old_coverage.get("crop_dpi") == dpi):
                old_questions = {q["locator"]: q for q in old_raw["questions"]}
                for old_crop in old_crops["questions"]:
                    old_question = old_questions.get(old_crop["locator"])
                    if old_question:
                        for i, region in enumerate(old_crop["regions"]):
                            if i < len(old_question["assets"]) and i < len(old_crop["assets"]):
                                cache[(old_crop["locator"], i)] = {
                                    "region": region, "asset": old_question["assets"][i],
                                    "dimensions": old_crop["assets"][i]}
    reused = 0
    questions, component_audits, crop_audits, aliases = [], [], [], []
    for component in COMPONENTS:
        anchors = find_anchors(component, pages)
        found = [anchor["number"] for anchor in anchors]
        expected = list(range(1, component.count + 1))
        duplicates = sorted(n for n, count in Counter(found).items() if count > 1)
        gaps = sorted(set(expected) - set(found))
        unexpected = sorted(set(found) - set(expected))
        if duplicates or gaps or unexpected or found != expected:
            raise ValueError(f"{component.key}: numbered coverage/order needs review: found={found}, gaps={gaps}, duplicate={duplicates}")
        lines = body_lines(component, pages) if component.color is not None else None
        cards = gray_cards(document, component, anchors) if component.key == "electricity-magnetism-translation" else None
        for index, anchor in enumerate(anchors):
            number = anchor["number"]
            flags = ["embedded_pdf_math_text_unverified", "statement_crops_pending_manual_review"]
            context = {"component": component.key, "component_title": component.title,
                       "source_author": component.author, "provenance_notes": component.provenance,
                       "source_language": component.language,
                       "unresolved_source": False,
                       "canonical_representation": "lossless_source_question_crops",
                       "numbering_scope": "component_not_entire_compilation"}
            if cards is not None:
                regions = cards[number]
                boundary = {"method": "one_number_per_printed_grey_card", "card_verified": True}
            elif component.key == "kepler-kree-et":
                regions = [{"page": page, "bbox_points": box} for page, box in KREE_REGIONS[number]]
                boundary = {"method": "visually_reviewed_black_text_source_regions"}
                flags.append("estonian_original_not_translated")
                if number in (2, 3):
                    context["shared_source_instruction"] = "Constant-density assumption printed on source p207, retained as a separate context crop for pr3."
                if number in (2, 7, 10):
                    flags.append("printed_inline_hint_retained_as_part_of_original_statement")
            else:
                regions, boundary, extra_flags = standard_regions(
                    component, anchor, anchors[index + 1] if index + 1 < len(anchors) else None, pages, lines)
                flags.extend(extra_flags)
                if extra_flags:
                    context["unresolved_source"] = True
            if (component.key, number) in PRECEDING_FIGURES:
                regions.extend(PRECEDING_FIGURES[(component.key, number)])
                context["preceding_referenced_figure_recovered"] = True
                boundary["preceding_referenced_figure_regions"] = PRECEDING_FIGURES[(component.key, number)]
            if (component.key, number) in SOURCE_FOOTNOTES:
                regions.extend(SOURCE_FOOTNOTES[(component.key, number)])
                context["referenced_source_footnote_recovered"] = True
                boundary["referenced_source_footnote_regions"] = SOURCE_FOOTNOTES[(component.key, number)]
            text = source_text(regions, document)
            if not text:
                raise ValueError(f"Empty source text: {component.key}/pr-{number}")
            if "\ufffd" in text:
                flags.append("legacy_tex_text_glyph_mapping_requires_review")
                context["text_glyph_warning"] = "Unusable embedded glyph/control mappings are visibly replaced by U+FFFD; original source crop is canonical."
            spans = [normalized(region, pages) for region in regions]
            assets, dimensions = [], []
            for asset_index, region in enumerate(regions, 1):
                target = crops_dir / f"{component.key}-pr-{number:03d}-{asset_index:02d}.webp"
                previous = cache.get((f"{component.key}/pr-{number}", asset_index - 1))
                if (previous and previous["region"] == region and target.is_file()
                        and digest(target) == previous["asset"]["sha256"]):
                    dimensions.append(previous["dimensions"])
                    reused += 1
                else:
                    dimensions.append(render_crop(document, region, target, dpi))
                assets.append({"asset_id": f"crop-{asset_index}", "role": "question_crop",
                               "local_path": str(target.resolve()), "mime_type": "image/webp",
                               "sha256": digest(target), "spans": [normalized(region, pages)],
                               "review_status": "pending"})
            crossrefs = re.findall(r"Kalda\s+(Circuits|Mechanics|Kinematics|Thermodynamics|Optics)\s+P\s*(\d+)", text, re.I)
            for target_component, target_number in crossrefs:
                target_key = {"circuits": "electrical-circuits", "mechanics": "mechanics",
                              "kinematics": "kinematics", "thermodynamics": "thermodynamics",
                              "optics": "wave-optics"}[target_component.lower()]
                aliases.append({"from": f"{component.key}/pr-{number}",
                                "to": f"{target_key}/pr-{int(target_number)}",
                                "kind": "explicit_source_cross_reference_potential_duplicate",
                                "action": "preserved_both_printed_locators_not_automatically_deduplicated"})
            context["quality_flags"] = flags
            context["boundary_method"] = boundary["method"]
            questions.append({"source": {"drive_id": drive_id, "revision": source["revision"]},
                              "source_language": component.language,
                              "locator": f"{component.key}/pr-{number}", "original_number": str(number),
                              "chapter": f"{component.title} — {component.author}", "kind": "problem",
                              "subjects": [component.subject], "level": "olympiad", "review_status": "pending",
                              "spans": spans,
                              "versions": [{"language": component.language, "role": "original", "text": text,
                                            "review_status": "pending", "extraction_method": "embedded_pdf_text_with_canonical_source_crops"}],
                              "assets": assets, "context": context})
            crop_audits.append({"locator": f"{component.key}/pr-{number}", "regions": regions,
                                "boundary": boundary, "assets": dimensions,
                                "flags": flags, "review_status": "pending"})
        component_audits.append({"component": component.key, "title": component.title,
                                "author": component.author, "source_language": component.language,
                                "pdf_pages": [component.first, component.last],
                                "expected_numbers": expected, "found_numbers": found,
                                "gaps": gaps, "duplicate_numbers": duplicates, "unexpected_numbers": unexpected,
                                "number_coverage_complete": True, "statement_boundary_review_complete": False,
                                "provenance_notes": component.provenance})
        print(f"{component.key}: {len(anchors)} printed locators extracted", flush=True)
    raw = {"version": 1, "profile": "reviewed-kalda-compilation-229pages-v1",
           "source_sha256": source_hash, "paid_api_calls": 0, "questions": questions}
    write_json(output / "questions.raw.json", raw)
    unresolved = [{"locator": q["locator"], "flags": q["context"]["quality_flags"]}
                  for q in questions if q["context"]["unresolved_source"]]
    audit = {"version": 1, "source_sha256": source_hash, "page_count": len(document),
             "source_drive_id": drive_id, "source_revision": source["revision"], "paid_api_calls": 0,
             "printed_locator_count": len(questions), "expected_printed_locator_count": 555,
             "original_language_counts": dict(Counter(q["source_language"] for q in questions)),
             "asset_count": sum(len(q["assets"]) for q in questions), "crop_dpi": dpi,
             "byte_verified_matching_crops_reused": reused,
             "number_coverage_complete": len(questions) == 555,
             "statement_boundary_review_complete": False, "publication_ready": False,
             "unique_physical_problem_count": None,
             "deduplication": "No automatic deletion; all component-scoped printed locators preserved.",
             "components": component_audits,
             "excluded_components": [{"pdf_pages": [198, 205], "page_count": 8,
                                      "title": "Solutions to Jaan Kalda's Problems in Waves and Optics",
                                      "reason": "solutions_only_no_new_problem_statements"}],
             "other_exclusions": ["Introductory theory, interleaved ideas/facts/commentary, hints and answer sections.",
                                  "Kree unnumbered theory prompts and the external-reference list on p212 are not counted as numbered exercises."],
             "unresolved_boundaries": unresolved,
             "review_limitations": ["Number coverage is complete for this fixed source profile, not a certification of all statement or crop boundaries.",
                                    "All embedded mathematical text and all original-language versions remain pending review.",
                                    "A printed inline hint within a problem is retained and flagged, not rewritten.",
                                    "The source compilation includes multiple authors and duplicate candidates; 555 is a printed-locator count, not a unique-physics-problem claim.",
                                    "English and Korean translations were not fabricated."],
             "potential_duplicate_cross_references": aliases}
    write_json(output / "coverage-audit.json", audit)
    write_json(output / "crop-audit.json", {"version": 1, "source_sha256": source_hash, "questions": crop_audits})
    print(json.dumps({key: audit[key] for key in ["printed_locator_count", "original_language_counts", "asset_count", "number_coverage_complete", "publication_ready"]}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--dpi", type=int, default=160)
    parser.add_argument("--drive-id", help="Optional private source identity when identical copies exist")
    parser.add_argument("--reuse-matching-crops", action="store_true")
    args = parser.parse_args()
    extract(args.pdf.resolve(), args.out.resolve(), args.manifest.resolve(), args.dpi, args.reuse_matching_crops, args.drive_id)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

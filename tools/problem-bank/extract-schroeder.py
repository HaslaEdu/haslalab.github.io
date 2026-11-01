"""Extract source-only problem regions from a private Schroeder textbook PDF.

Only standalone bold problem labels are identities; prose references, worked
examples and lecture text are excluded. Native math text and automatic figure
assignment remain pending visual review. No network or model API is used.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf
from PIL import Image

from private_paths import private_directory


LABEL = re.compile(r"^(Problem|Exercise)\s+([1-8AB])\.(\d+)\.")
REFERENCE = re.compile(r"^(Problem|Exercise)\s+([1-8AB])\.(\d+)")
FIGURE = re.compile(r"^Figure\s+([1-8AB]\.\d+)\.")
RENDER_CACHE = {}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == data:
        return
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".extract-", delete=False) as f:
            temp = Path(f.name)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if temp:
            temp.unlink(missing_ok=True)


def json_write(path, value):
    write(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def norm(rect, page):
    return [round(rect[0] / page.rect.width, 7), round(rect[1] / page.rect.height, 7),
            round(rect[2] / page.rect.width, 7), round(rect[3] / page.rect.height, 7)]


def position(item):
    return item["page"], item["bbox"][1]


def text_lines(page):
    result = []
    for block in page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            text = "".join(s["text"] for s in line["spans"]).strip()
            if text:
                result.append({"text": text, "bbox": list(line["bbox"]),
                               "baseline": line["spans"][0]["origin"][1],
                               "spans": [{"font": s["font"], "size": s["size"], "text": s["text"]}
                                         for s in line["spans"]], "block_bbox": list(block["bbox"])})
    # Superscripts can make a sentence fragment's bbox start above its problem
    # label despite sharing a baseline. Preserve the actual reading row.
    return sorted(result, key=lambda r: (round(r["baseline"], 1), r["bbox"][0]))


def bold_label(line):
    return LABEL.match(line["text"]) and line["spans"][0]["font"] == "CMBX9"


def lecture_boundary(line):
    if line["bbox"][1] < 48:
        return False
    large_heading = any(s["size"] >= 9.5 and "CMBX" in s["font"] for s in line["spans"])
    body = sum(len(s["text"]) for s in line["spans"]
               if re.match(r"CM(?:R|SL|TI|TT|SS)10", s["font"]) and s["size"] >= 9.5) >= 35
    return large_heading or body


def render(document, output, page_number, rect, dpi, role):
    page = document[page_number - 1]
    rect = pymupdf.Rect(rect) & page.rect
    span = {"page": page_number, "bbox": norm(rect, page)}
    cached = RENDER_CACHE.get(str(output.resolve()))
    if (cached and cached["spans"] == [span] and cached.get("render_dpi", 120) == dpi
            and output.exists() and hashlib.sha256(output.read_bytes()).hexdigest() == cached["sha256"]):
        return dict(cached, role=role)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(dpi / 72, dpi / 72), clip=rect, alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    buffer = io.BytesIO()
    image.save(buffer, "WEBP", quality=92, method=4)
    write(output, buffer.getvalue())
    return {"role": role, "local_path": str(output.resolve()), "mime_type": "image/webp",
            "sha256": hashlib.sha256(buffer.getvalue()).hexdigest(), "spans": [span],
            "render_dpi": dpi, "review_status": "pending"}


def graphic_groups(page):
    rectangles = [pymupdf.Rect(i["bbox"]) for i in page.get_image_info()]
    rectangles.extend(pymupdf.Rect(d["rect"]) for d in page.get_drawings()
                      if d["rect"].width >= 4 and d["rect"].height >= 4)
    groups = []
    for rect in rectangles:
        if rect.y0 < 46:
            continue
        joined = rect
        changed = True
        while changed:
            changed = False
            for old in groups[:]:
                if (joined + (-6, -6, 6, 6)).intersects(old):
                    joined |= old
                    groups.remove(old)
                    changed = True
        groups.append(joined)
    return [g for g in groups if g.width >= 12 and g.height >= 10]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--drive-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--dpi", type=int, default=120)
    parser.add_argument("--context-regions", type=Path,
                        help="Private source-hash-bound manual rectangles for shared figures and givens")
    args = parser.parse_args()
    output = private_directory(args.out)
    repo = Path(__file__).resolve().parents[2]
    if output.is_relative_to(repo):
        raise ValueError("Book content must stay outside the public repository")
    if not 72 <= args.dpi <= 180:
        raise ValueError("Use a source crop resolution between 72 and 180 dpi")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    source = next(s for s in manifest["sources"] if s["drive_id"] == args.drive_id)
    pdf = args.pdf or Path(source["local_path"])
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if digest != source["sha256"]:
        raise ValueError("Manifest source SHA does not match the PDF")
    existing_raw = output / "questions.raw.json"
    if existing_raw.exists():
        previous = json.loads(existing_raw.read_text(encoding="utf-8-sig"))
        if previous.get("source_sha256") == digest:
            for question in previous["questions"]:
                for asset in question["assets"]:
                    RENDER_CACHE[str(Path(asset["local_path"]).resolve())] = asset
            previous_figures = output / "figure-index.json"
            if previous_figures.exists():
                for asset in json.loads(previous_figures.read_text(encoding="utf-8-sig"))["figures"].values():
                    RENDER_CACHE[str(Path(asset["local_path"]).resolve())] = asset
    profile_path = args.context_regions or output / "source-context-regions.json"
    manual_context = {}
    if profile_path.exists():
        manual_context = json.loads(profile_path.read_text(encoding="utf-8-sig"))
        if manual_context.get("source_sha256") != digest:
            raise ValueError("Manual context source SHA mismatch")
    document = pymupdf.open(pdf)
    pages = [text_lines(page) for page in document]
    footnote_rules = {}
    for index, page in enumerate(document, 1):
        rules = [d["rect"].y0 for d in page.get_drawings()
                 if abs(d["rect"].width - 144) < .1 and d["rect"].height < .6
                 and 60 < d["rect"].x0 < 122 and d["rect"].y0 > 400]
        if rules:
            footnote_rules[index] = min(rules)
    starts, prose_references, stops, captions = [], [], [], {}
    for index, lines in enumerate(pages, 1):
        for line in lines:
            item = dict(line, page=index)
            if bold_label(line):
                match = LABEL.match(line["text"])
                item["bbox"] = list(item["bbox"])
                item["header_bbox"] = list(item["bbox"])
                item["bbox"][1] = min(l["bbox"][1] for l in lines
                                      if abs(l["baseline"] - line["baseline"]) < .1)
                starts.append(dict(item, kind=match[1].lower(), chapter_id=match[2],
                                   number=f"{match[2]}.{match[3]}"))
            elif REFERENCE.match(line["text"]):
                prose_references.append({"page": index, "text": line["text"]})
            if lecture_boundary(line):
                stops.append(item)
            m = FIGURE.match(line["text"])
            if m and line["spans"][0]["font"] == "CMBX9":
                if m[1] in captions:
                    raise ValueError(f"Duplicate figure caption: {m[1]}")
                captions[m[1]] = item
    starts.sort(key=position)
    chapter_ids = [str(i) for i in range(1, 9)] + ["A", "B"]
    coverage = {}
    errors = []
    for chapter in chapter_ids:
        labels = [int(s["number"].split(".")[1]) for s in starts if s["chapter_id"] == chapter]
        if not labels:
            errors.append({"chapter": chapter, "reason": "no_standalone_labels"})
            continue
        maximum = max(labels)
        missing = sorted(set(range(1, maximum + 1)) - set(labels))
        duplicates = sorted(n for n, count in Counter(labels).items() if count > 1)
        coverage[chapter] = {"observed_first": min(labels), "observed_last": maximum,
                             "observed_count": len(labels), "range_count_inferred_from_printed_labels": maximum,
                             "missing_numbers": missing, "duplicate_numbers": duplicates}
        if missing or duplicates or min(labels) != 1:
            errors.append({"chapter": chapter, "reason": "nonconsecutive_printed_labels"})
    if errors:
        json_write(output / "coverage-audit.json", {"errors": errors, "chapters": coverage})
        raise ValueError("Problem-number coverage requires review")
    chapter_titles = {}
    topics = []
    for level, title, number in document.get_toc():
        m = re.match(r"^([1-8AB])\s+(.+)", title.replace("\r", " "))
        if level == 1 and m:
            chapter_titles[m[1]] = m[2]
        if level == 2 and re.match(r"^[1-8AB]\.\d+\s", title):
            section = title.split()[0]
            matches = [l for l in pages[number - 1] if l["text"].startswith(section + " ")
                       and any(s["size"] >= 11 for s in l["spans"])]
            topics.append({"page": number, "bbox": [0, matches[0]["bbox"][1] if matches else 48, 0, 0], "title": title})
    figure_assets = {}
    figure_errors = []
    groups_cache = {}
    for label, caption in captions.items():
        page_number = caption["page"]
        page = document[page_number - 1]
        if page_number not in groups_cache:
            groups_cache[page_number] = graphic_groups(page)
        cap = pymupdf.Rect(caption["block_bbox"])
        if label in manual_context.get("figures", {}):
            reviewed = manual_context["figures"][label]
            box = reviewed["bbox"]
            box = [box[0] * page.rect.width, box[1] * page.rect.height,
                   box[2] * page.rect.width, box[3] * page.rect.height]
            asset = render(document, output / "figures" / f"figure-{label}.webp", page_number, box,
                           args.dpi, "source_figure")
            asset.update(figure_label=label, quality_flags=["source_rectangle_visually_reviewed"])
            figure_assets[label] = asset
            continue
        candidates = []
        for rect in groups_cache[page_number]:
            vertical = max(0, cap.y0 - rect.y1, rect.y0 - cap.y1)
            horizontal = max(0, cap.x0 - rect.x1, rect.x0 - cap.x1)
            if vertical <= 150 and horizontal <= 150 and rect.y0 <= cap.y1 + 15:
                candidates.append((vertical + horizontal * .5, rect))
        if not candidates:
            figure_errors.append({"figure": label, "page": page_number, "reason": "graphic_rectangle_not_isolated"})
            continue
        best = min(score for score, _ in candidates)
        selected = [rect for score, rect in candidates if score <= best + 15]
        box = cap
        for rect in selected:
            box |= rect
        box += (-12, -8, 12, 3)
        asset = render(document, output / "figures" / f"figure-{label}.webp", page_number, box,
                       args.dpi, "source_figure")
        asset["figure_label"] = label
        asset["quality_flags"] = ["automatic_figure_rectangle_needs_visual_review"]
        figure_assets[label] = asset
    footnote_assets = {}
    footnote_text = {}
    for number, top in footnote_rules.items():
        page = document[number - 1]
        bottom = page.rect.height - 50
        left = 68 if number % 2 == 0 else 102
        footnote_assets[number] = render(document, output / "footnotes" / f"page-{number}.webp", number,
                                         [left, top + 1, page.rect.width - 68, bottom], args.dpi, "source_footnote")
        footnote_text[number] = "\n".join(l["text"] for l in pages[number - 1] if l["bbox"][1] > top)
    questions = []
    for index, start in enumerate(starts):
        next_point = position(starts[index + 1]) if index + 1 < len(starts) else (len(document) + 1, 0)
        possible = [s for s in stops if position(start) < position(s) < next_point]
        stop = min(possible, key=position) if possible else None
        limit = position(stop) if stop else ((starts[index + 1]["page"], starts[index + 1]["header_bbox"][1])
                                            if index + 1 < len(starts) else next_point)
        regions = []
        statement = []
        for number in range(start["page"], min(limit[0], len(document)) + 1):
            if number == limit[0] and limit[1] < 49:
                continue
            page = document[number - 1]
            top = start["bbox"][1] - 2 if number == start["page"] else 48
            bottom = min(limit[1] - 2 if number == limit[0] else page.rect.height - 50,
                         footnote_rules.get(number, page.rect.height) - 2)
            if bottom <= top:
                continue
            left = 68 if number % 2 == 0 else 102
            right = page.rect.width - 68
            box = pymupdf.Rect(left, top, right, bottom)
            relevant = [l for l in pages[number - 1] if top <= (l["bbox"][1] + l["bbox"][3]) / 2 < bottom
                        and l["bbox"][1] >= 48]
            if not relevant:
                continue
            statement.extend(l["text"] for l in relevant)
            regions.append((number, box))
        text = "\n".join(statement)
        label_prefix = f"{start['kind'].title()} {start['number']}."
        label_lines = [line for line in statement if line.startswith(label_prefix)]
        if not label_lines:
            raise ValueError(f"Missing statement at {start['number']}")
        if not text.startswith(label_prefix):
            statement.remove(label_lines[0])
            text = "\n".join([label_lines[0]] + statement)
        assets = [render(document, output / "crops" / f"problem-{start['number']}-{i:02d}.webp", n, box,
                         args.dpi, "question_crop") for i, (n, box) in enumerate(regions, 1)]
        refs = sorted(set(re.findall(r"(?:Figure|Fig\.)\s*([1-8AB]\.\d+)", text)))
        missing_figures = [r for r in refs if r not in figure_assets]
        for ref in refs:
            if ref in figure_assets:
                assets.append(figure_assets[ref])
        linked_footnotes = []
        excluded_footnote_pages = manual_context.get("footnote_exclusions", {}).get(start["number"], [])
        if re.search(r"[⇤*†‡]", text):
            for number, _ in regions:
                if number in footnote_assets and number not in excluded_footnote_pages:
                    assets.append(footnote_assets[number])
                    linked_footnotes.append({"page": number, "text": footnote_text[number], "review_status": "pending"})
        shared_regions = manual_context.get("questions", {}).get(start["number"], [])
        for i, region in enumerate(shared_regions, 1):
            page = document[region["page"] - 1]
            box = region["bbox"]
            box = [box[0] * page.rect.width, box[1] * page.rect.height,
                   box[2] * page.rect.width, box[3] * page.rect.height]
            assets.append(render(document, output / "context" / f"problem-{start['number']}-{i:02d}.webp",
                                 region["page"], box, args.dpi, "question_crop"))
        topic = next((t["title"] for t in reversed(topics) if position(t) <= position(start)
                      and t["title"].startswith(start["chapter_id"] + ".")), chapter_titles[start["chapter_id"]])
        chapter = start["chapter_id"]
        subjects = ["thermodynamics"] if chapter not in ["A", "B"] else (["quantum_mechanics"] if chapter == "A" else ["mathematics"])
        if chapter == "7":
            subjects.append("quantum_mechanics")
        printed_answer = bool(re.search(r"\bAnswer\s*:", text))
        questions.append({"source": {"drive_id": args.drive_id, "revision": source["revision"]},
                          "source_language": "en", "locator": f"chapter-{chapter}/problem-{start['number']}",
                          "original_number": start["number"], "chapter": chapter_titles[chapter],
                          "kind": start["kind"], "subjects": subjects, "level": "undergraduate", "review_status": "pending",
                          "spans": [a["spans"][0] for a in assets if a["role"] == "question_crop"],
                          "versions": [{"language": "en", "role": "original", "text": text, "review_status": "pending",
                                        "extraction_method": "native_pdf_text_with_font_boundaries"}],
                          "assets": assets, "figure_references_raw": refs,
                          "context": {"source_author": "Daniel V. Schroeder", "chapter_id": chapter, "topic": topic,
                                      "unresolved_source": bool(missing_figures) or start["header_bbox"][1] - start["bbox"][1] > 4,
                                      "missing_figure_references": missing_figures,
                                      "source_footnotes": linked_footnotes,
                                      "excluded_source_footnote_pages": excluded_footnote_pages,
                                      "source_inline_answer_present": printed_answer,
                                      "shared_source_regions": shared_regions,
                                      "inline_math_boundary_overlap": start["header_bbox"][1] - start["bbox"][1] > 4,
                                      "quality_flags": ["native_pdf_math_symbols_unverified", "source_regions_pending_visual_review"]
                                      + (["source_crop_contains_printed_answer"] if printed_answer else []),
                                      "boundary_method": "bold_problem_label_until_next_label_or_lecture_font"}})
    audit = {"source_page_count": len(document), "standalone_problem_count": len(questions),
             "expected_count_basis": "Consecutive standalone printed labels from 1 to the observed final label in each TOC chapter; not a publisher-declared total.",
             "range_count_inferred_from_printed_labels": sum(x["range_count_inferred_from_printed_labels"] for x in coverage.values()),
             "chapters": coverage, "excluded_prose_reference_count": len(prose_references),
             "excluded_prose_references": prose_references, "figure_caption_count": len(captions),
             "isolated_figure_count": len(figure_assets), "figure_isolation_errors": figure_errors,
             "footnote_region_count": len(footnote_assets),
             "question_count_with_missing_figure_context": sum(bool(q["context"]["missing_figure_references"]) for q in questions),
             "question_count_with_unresolved_source": sum(q["context"]["unresolved_source"] for q in questions),
             "paid_api_calls": 0, "all_versions_review_status": "pending", "not_ready_for_publication": True}
    json_write(output / "questions.raw.json", {"version": 1, "profile": "schroeder-native-font-problems",
                                               "source_sha256": digest, "questions": questions})
    json_write(output / "coverage-audit.json", audit)
    json_write(output / "figure-index.json", {"figures": figure_assets, "errors": figure_errors})
    print(json.dumps({k: audit[k] for k in ["standalone_problem_count", "range_count_inferred_from_printed_labels",
                                          "excluded_prose_reference_count", "isolated_figure_count",
                                          "question_count_with_missing_figure_context"]}))


if __name__ == "__main__":
    main()

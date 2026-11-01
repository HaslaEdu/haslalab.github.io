"""Extract private boxed problems from a reflowed native-text textbook PDF.

Problem identities come from standalone semibold labels; source geometry keeps
worked examples and lecture prose outside question crops. Image-based equations
remain in source crops and require direct transcription. No model/network API.
Source identity, damaged-source overrides and book excerpts stay in private data.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile

import pymupdf
from PIL import Image

from private_paths import private_directory


LABEL = re.compile(r"^Problem\s+((\d+|[A-Z])\.(\d+))\b")
FIGURE = re.compile(r"^Figure\s+((?:\d+|[A-Z])\.\d+)(?:\s*:|\s+)")
CACHE = {}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == data:
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".extract-", delete=False) as f:
        temp = Path(f.name)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def jsave(path, value):
    write(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def normalized(rect, page):
    return [round(rect[0] / page.rect.width, 7), round(rect[1] / page.rect.height, 7),
            round(rect[2] / page.rect.width, 7), round(rect[3] / page.rect.height, 7)]


def absolute(box, page):
    return pymupdf.Rect(box[0] * page.rect.width, box[1] * page.rect.height,
                        box[2] * page.rect.width, box[3] * page.rect.height)


def lines(page):
    rows = []
    for block in page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            text = "".join(s["text"] for s in line["spans"]).strip()
            if text:
                rows.append({"text": text, "bbox": list(line["bbox"]),
                             "baseline": line["spans"][0]["origin"][1],
                             "spans": [{k: s[k] for k in ["text", "font", "size", "bbox", "color"]}
                                       for s in line["spans"]]})
    return sorted(rows, key=lambda r: (round(r["baseline"], 1), r["bbox"][0]))


def visible_body(page):
    # This reflow export uses a scaled rectangular clipping path for body text.
    stream = page.read_contents().decode("latin1")
    scale = re.search(r"q\s+([\d.]+)\s+0\s+0\s+([\d.]+)\s+0\s+0\s+cm", stream)
    clips = re.findall(r"([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+re\s+W\*?\s+n", stream)
    if scale and clips:
        sx, sy = map(float, scale.groups())
        for values in clips:
            x, y, w, h = map(float, values)
            if h * sy > page.rect.height / 2 and w * sx > page.rect.width / 2:
                return pymupdf.Rect(x * sx, page.rect.height - (y + h) * sy,
                                    (x + w) * sx, page.rect.height - y * sy)
    return pymupdf.Rect(0, 0, page.rect.width, page.rect.height * .94)


def question_boxes(page):
    # The narrow light-gray fill distinguishes exercises from wide worked examples.
    boxes = []
    for drawing in page.get_drawings():
        fill, r = drawing.get("fill"), drawing["rect"]
        if fill and len(fill) >= 3 and min(fill[:3]) > .97 and .52 < r.width / page.rect.width < .66:
            boxes.append(r)
    return boxes


def render(doc, out, page_number, rect, dpi, role="question_crop"):
    page = doc[page_number - 1]
    rect = pymupdf.Rect(rect) & page.rect
    span = {"page": page_number, "bbox": normalized(rect, page)}
    old = CACHE.get(str(out.resolve()))
    if old and old["spans"] == [span] and old.get("render_dpi", 120) == dpi and out.exists():
        if hashlib.sha256(out.read_bytes()).hexdigest() == old["sha256"]:
            return dict(old, role=role)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(dpi / 72, dpi / 72), clip=rect, alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    buffer = io.BytesIO()
    image.save(buffer, "WEBP", quality=93, method=4)
    data = buffer.getvalue()
    write(out, data)
    return {"role": role, "local_path": str(out.resolve()), "mime_type": "image/webp",
            "sha256": hashlib.sha256(data).hexdigest(), "spans": [span],
            "render_dpi": dpi, "review_status": "pending"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--drive-id", required=True)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dpi", type=int, default=120)
    args = parser.parse_args()
    out = private_directory(args.out)
    if not 72 <= args.dpi <= 180:
        raise ValueError("Source crops must use 72–180 dpi")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    source = next(s for s in manifest["sources"] if s["drive_id"] == args.drive_id)
    pdf = args.pdf or Path(source["local_path"])
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if digest != source["sha256"]:
        raise ValueError("Source SHA mismatch")
    profile_path = out / "source-context-regions.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8-sig")) if profile_path.exists() else {}
    if profile and profile.get("source_sha256") != digest:
        raise ValueError("Private context source SHA mismatch")
    oldpath = out / "questions.raw.json"
    if oldpath.exists():
        old = json.loads(oldpath.read_text(encoding="utf-8-sig"))
        if old.get("source_sha256") == digest:
            for q in old["questions"]:
                for a in q["assets"]:
                    CACHE[str(Path(a["local_path"]).resolve())] = a
    oldfig = out / "figure-index.json"
    if oldfig.exists():
        for a in json.loads(oldfig.read_text(encoding="utf-8-sig"))["figures"].values():
            CACHE[str(Path(a["local_path"]).resolve())] = a
    doc = pymupdf.open(pdf)
    rows = [lines(p) for p in doc]
    bodies = [visible_body(p) for p in doc]
    boxes = [question_boxes(p) for p in doc]
    candidates, excluded = defaultdict(list), []
    for pn, page_rows in enumerate(rows, 1):
        for row in page_rows:
            match = LABEL.match(row["text"])
            if not match:
                continue
            if "Semibold" not in row["spans"][0]["font"]:
                excluded.append({"page": pn, "text": row["text"]})
                continue
            point = pymupdf.Point(row["bbox"][0] + 2, row["baseline"] - 2)
            containing = [b for b in boxes[pn - 1] if b.contains(point)]
            if not containing:
                raise ValueError(f"No question enclosure at page {pn}: {row['text']}")
            enclosure = min(containing, key=lambda b: b.get_area())
            candidates[match[1]].append(dict(row, number=match[1], chapter_id=match[2],
                                            page=pn, enclosure=list(enclosure), orphan=False))
    starts, duplicates = [], []
    for number, occurrences in candidates.items():
        override = profile.get("canonical_occurrences", {}).get(number)
        if override:
            canonical = next(o for o in occurrences if o["page"] == override["page"])
        else:
            # Prefer a complete enclosure over an opening clipped at a page break.
            canonical = max(occurrences, key=lambda o: min(pymupdf.Rect(o["enclosure"]).y1,
                            bodies[o["page"] - 1].y1) - o["bbox"][1])
        starts.append(canonical)
        if len(occurrences) > 1:
            duplicates.append({"original_number": number, "canonical_page": canonical["page"],
                               "pages": [o["page"] for o in occurrences], "override": override})
    for orphan in profile.get("orphan_questions", []):
        if orphan["original_number"] in candidates:
            raise ValueError("Orphan override overlaps an actual label")
        page = doc[orphan["page"] - 1]
        rect = absolute(orphan["bbox"], page)
        starts.append(dict(number=orphan["original_number"], chapter_id=orphan["chapter_id"],
                           page=orphan["page"], bbox=list(rect), enclosure=list(rect), orphan=True,
                           reason=orphan["reason"]))
    starts.sort(key=lambda s: (s["page"], s["bbox"][1]))
    chapter_titles, chapter_points = {}, []
    topics = []
    for level, title, page in doc.get_toc():
        match = re.match(r"^(\d+)\s+(.+)", title)
        if match and level == 2:
            chapter_titles[match[1]] = match[2]
            chapter_points.append((page, match[1]))
        elif level == 1 and title.startswith("Appendix"):
            chapter_titles["A"] = title
            chapter_points.append((page, "A"))
        if re.match(r"^(?:\d+|[A-Z])\.\d+\s", title):
            topics.append({"page": page, "title": title})
    figure_assets, figure_errors = {}, []
    for pn, page_rows in enumerate(rows, 1):
        page = doc[pn - 1]
        images = [pymupdf.Rect(i["bbox"]) for i in page.get_image_info()]
        for ix, row in enumerate(page_rows):
            match = FIGURE.match(row["text"])
            if not match:
                continue
            if "Semibold" not in row["spans"][0]["font"]:
                continue
            label = match[1]
            caption = pymupdf.Rect(row["bbox"])
            baseline = row["baseline"]
            for nxt in page_rows[ix + 1:]:
                if nxt["baseline"] - baseline > 19 or LABEL.match(nxt["text"]) or FIGURE.match(nxt["text"]):
                    break
                if nxt["bbox"][1] < caption.y0:
                    continue
                caption |= pymupdf.Rect(nxt["bbox"])
                baseline = nxt["baseline"]
            manual = profile.get("figures", {}).get(label)
            if manual:
                pn_source = manual["page"]
                rect = absolute(manual["bbox"], doc[pn_source - 1])
            else:
                near = [r for r in images if r.width > 35 and r.height > 18 and
                        0 <= caption.y0 - r.y1 < 65 and r.get_area() > 1100]
                if not near:
                    figure_errors.append({"figure": label, "page": pn, "error": "No nearby source image"})
                    continue
                image = max(near, key=lambda r: r.y1)
                rect = image | caption
                for panel in images:
                    if abs(panel.y1 - image.y1) < 12 and panel.y0 >= image.y0 - 12 and panel.width > 35:
                        rect |= panel
                rect += (-3, -3, 3, 3)
                pn_source = pn
            asset = render(doc, out / "figures" / f"figure-{label}.webp", pn_source, rect,
                           args.dpi, "source_figure")
            asset.update(figure_label=label, quality_flags=["source_figure_rectangle_pending_visual_review"])
            asset["source_caption_span"] = {"page": pn, "bbox": normalized(caption, page)}
            figure_assets[label] = asset
    # Endnotes use small colored numbered labels in the left margin. Ordinary
    # body superscripts are larger, and isotope numbers are black, not links.
    note_starts = defaultdict(list)
    for pn, page_rows in enumerate(rows, 1):
        chapter = next((c for p, c in reversed(chapter_points) if p <= pn), None)
        if chapter is None:
            continue
        for row in page_rows:
            for s in row["spans"]:
                if (s["text"].strip().isdigit() and s["size"] <= 6.3 and s["color"] != 0
                        and s["bbox"][0] <= bodies[pn-1].x0 + 8):
                    note_starts[chapter].append({"number": s["text"].strip(), "page": pn,
                                                  "top": max(bodies[pn-1].y0, s["bbox"][1]-2)})
    notes = {}
    for chapter, entries in note_starts.items():
        entries.sort(key=lambda n: (n["page"], n["top"]))
        next_chapter = next((p for p, c in chapter_points if p > entries[-1]["page"]), len(doc)+1)
        for ix, entry in enumerate(entries):
            limit = entries[ix+1] if ix+1 < len(entries) else {"page": next_chapter, "top": 0}
            spans, text = [], []
            for pn in range(entry["page"], min(limit["page"], len(doc))+1):
                top = entry["top"] if pn == entry["page"] else bodies[pn-1].y0
                bottom = limit["top"]-1 if pn == limit["page"] else bodies[pn-1].y1
                if bottom <= top:
                    continue
                picked = [r for r in rows[pn-1] if top <= r["baseline"]-2 < bottom]
                if not picked:
                    continue
                small = sum(len(s["text"]) for r in picked for s in r["spans"] if s["size"] < 8.2)
                chars = sum(len(r["text"]) for r in picked)
                if small < chars * .6:
                    break
                # Keep image equations between note text lines, while trimming
                # blank page tails after the final note.
                images_here = [pymupdf.Rect(i["bbox"]) for i in doc[pn-1].get_image_info()
                               if top <= (i["bbox"][1]+i["bbox"][3])/2 < bottom]
                end = max([r["bbox"][3]+2 for r in picked] + [i.y1+1 for i in images_here])
                # Link-marker ascenders overlap the preceding line's image
                # equations by a few points in this reflow. Preserve the equation.
                rect = pymupdf.Rect(bodies[pn-1].x0, top, bodies[pn-1].x1, min(bottom+4.5, end))
                spans.append({"page": pn, "bbox": normalized(rect, doc[pn-1])})
                text.extend(r["text"] for r in picked)
            notes[(chapter, entry["number"])] = {"number": entry["number"], "text": "\n".join(text),
                                                    "spans": spans, "review_status": "pending"}
    questions, boundary_errors = [], []
    for ix, start in enumerate(starts):
        following = starts[ix + 1] if ix + 1 < len(starts) else None
        regions, statement, inline_images, note_refs = [], [], [], set()
        pn = start["page"]
        enclosure = pymupdf.Rect(start["enclosure"])
        while pn <= len(doc):
            page, body = doc[pn - 1], bodies[pn - 1]
            top = max(body.y0, start["bbox"][1] - 2) if pn == start["page"] else body.y0
            bottom = min(enclosure.y1 + 2, body.y1)
            if following and pn == following["page"]:
                bottom = min(bottom, following["bbox"][1] - 3)
            rect = pymupdf.Rect(max(body.x0, enclosure.x0 - 22), top, body.x1, bottom)
            selected = [r for r in rows[pn - 1] if top <= r["baseline"] - 3 < bottom
                        and rect.x0 <= r["bbox"][0] < rect.x1]
            if bottom > top and selected:
                regions.append((pn, rect))
                statement.extend(r["text"] for r in selected)
                note_refs.update(s["text"].strip() for r in selected for s in r["spans"]
                                 if s["size"] < 8.2 and s["color"] != 0 and s["text"].strip().isdigit())
                inline_images.extend({"page": pn, "bbox": normalized(pymupdf.Rect(i["bbox"]), page)}
                                     for i in page.get_image_info()
                                     if rect.contains(pymupdf.Point((i["bbox"][0]+i["bbox"][2])/2,
                                                                  (i["bbox"][1]+i["bbox"][3])/2)))
            if ((following and pn == following["page"])
                    or pn == profile.get("question_end_pages", {}).get(start["number"])):
                break
            if enclosure.y1 <= body.y1 + 1:
                # Reflow can close one box early, leave a largely blank page,
                # then restart the same exercise in a fresh rounded box. Detect
                # its unlabeled leading text rather than treating the border as
                # the end of the problem.
                fresh = None
                if pn < len(doc) and (not following or pn+1 <= following["page"]):
                    for candidate in boxes[pn]:
                        if (abs(candidate.x0-enclosure.x0) < 4
                                and candidate.y0 <= bodies[pn].y0+20 and candidate.y1 > bodies[pn].y0+4):
                            leading = [r for r in rows[pn] if candidate.contains(
                                pymupdf.Point(r["bbox"][0]+1, r["baseline"]-2))
                                and r["baseline"] > bodies[pn].y0]
                            if leading and not LABEL.match(leading[0]["text"]):
                                fresh = candidate
                                break
                if fresh is None:
                    break
                pn += 1
                enclosure = fresh
                continue
            pn += 1
            if pn > len(doc) or (following and pn > following["page"]):
                break
            continuations = [b for b in boxes[pn - 1] if b.y0 <= bodies[pn - 1].y0 + 2 < b.y1
                             and abs(b.x0 - enclosure.x0) < 4]
            if not continuations:
                boundary_errors.append({"original_number": start["number"], "page": pn,
                                        "error": "Enclosure extends past viewport but no continuation box"})
                break
            enclosure = min(continuations, key=lambda b: b.get_area())
        if not regions:
            raise ValueError(f"No source statement regions for {start['number']}")
        text = "\n".join(statement)
        note_refs.update(re.findall(r"\bfootnote\s+(\d+)", text, re.I))
        assets = [render(doc, out / "crops" / f"problem-{start['number']}-{j:02d}.webp", n,
                         rect, args.dpi) for j, (n, rect) in enumerate(regions, 1)]
        refs = sorted(set(re.findall(r"(?:Figure|Fig\.)\s*((?:\d+|[A-Z])\.\d+)", text)))
        missing = [ref for ref in refs if ref not in figure_assets]
        assets.extend(figure_assets[ref] for ref in refs if ref in figure_assets)
        linked_notes, missing_notes = [], []
        for ref in sorted(note_refs, key=int):
            note = notes.get((start["chapter_id"], ref))
            if not note:
                missing_notes.append(ref)
                continue
            linked_notes.append(note)
            for j, span in enumerate(note["spans"], 1):
                assets.append(render(doc, out / "footnotes" / f"chapter-{start['chapter_id']}-note-{ref}-{j:02d}.webp",
                                     span["page"], absolute(span["bbox"], doc[span["page"]-1]), args.dpi,
                                     "source_footnote"))
        shared = profile.get("questions", {}).get(start["number"], [])
        for j, region in enumerate(shared, 1):
            assets.append(render(doc, out / "context" / f"problem-{start['number']}-{j:02d}.webp",
                                 region["page"], absolute(region["bbox"], doc[region["page"] - 1]), args.dpi))
        chapter = start["chapter_id"]
        topic = next((t["title"] for t in reversed(topics) if t["page"] <= start["page"]
                      and t["title"].startswith(chapter + ".")), chapter_titles.get(chapter, chapter))
        answer = bool(re.search(r"\bAnswer\s*:", text, re.I))
        errors_here = [e for e in boundary_errors if e["original_number"] == start["number"]]
        source_review = profile.get("question_review_flags", {}).get(start["number"], {})
        flags = ["native_text_omits_image_based_math", "source_regions_pending_visual_review"]
        if answer:
            flags.append("source_crop_contains_printed_answer")
        if start["orphan"]:
            flags.append("source_opening_missing")
        if source_review.get("unresolved_source"):
            flags.append("source_review_override_pending")
        questions.append({"source": {"drive_id": args.drive_id, "revision": source["revision"]},
                          "source_language": "en", "locator": f"chapter-{chapter}/problem-{start['number']}",
                          "original_number": start["number"], "chapter": chapter_titles.get(chapter, chapter),
                          "kind": "problem", "subjects": ["mathematics" if chapter.isalpha() else "quantum_mechanics"],
                          "level": "undergraduate", "review_status": "pending", "assets": assets,
                          "spans": [a["spans"][0] for a in assets if a["role"] == "question_crop"],
                          "versions": [{"language": "en", "role": "original", "text": text,
                                        "review_status": "pending", "extraction_method": "native_pdf_boxed_problem_text"}],
                          "figure_references_raw": refs,
                          "context": {"source_author": profile.get("source_author", ""), "chapter_id": chapter,
                                      "topic": topic, "source_math_image_regions": inline_images,
                                      "source_primary_regions": [{"page": n, "bbox": normalized(rect, doc[n-1])}
                                                                 for n, rect in regions],
                                      "unresolved_source": bool(start["orphan"] or missing or errors_here or missing_notes
                                                                or source_review.get("unresolved_source")),
                                      "source_review_notes": source_review.get("review_notes", []),
                                      "source_opening_missing": start["orphan"], "source_opening_note": start.get("reason"),
                                      "duplicate_header_occurrences": [d for d in duplicates if d["original_number"] == start["number"]],
                                      "missing_figure_references": missing, "boundary_errors": errors_here,
                                      "source_footnotes": linked_notes, "missing_footnote_references": missing_notes,
                                      "source_inline_answer_present": answer, "shared_source_regions": shared,
                                      "quality_flags": flags, "boundary_method": "semibold_label_within_visible_question_enclosure"}})
    assigned = defaultdict(list)
    for q in questions:
        for region in q["context"]["source_primary_regions"]:
            assigned[region["page"]].append(absolute(region["bbox"], doc[region["page"]-1]))
    uncovered_boxes = []
    for pn, page in enumerate(doc, 1):
        for box in boxes[pn-1]:
            visible = box & bodies[pn-1]
            if visible.is_empty:
                continue
            missed_text, missed_images = [], []
            for row in rows[pn-1]:
                point = pymupdf.Point(row["bbox"][0]+1, row["baseline"]-2)
                if visible.contains(point) and not any(r.contains(point) for r in assigned[pn]):
                    missed_text.append(row["text"])
            for image in page.get_image_info():
                r = image["bbox"]
                point = pymupdf.Point((r[0]+r[2])/2, (r[1]+r[3])/2)
                if visible.contains(point) and not any(a.contains(point) for a in assigned[pn]):
                    missed_images.append(normalized(r, page))
            if missed_text or missed_images:
                first_label = next((LABEL.match(t) for t in missed_text if LABEL.match(t)), None)
                duplicate = next((x for x in duplicates if first_label and
                                  x["original_number"] == first_label[1] and pn in x["pages"]
                                  and pn != x["canonical_page"]), None)
                uncovered_boxes.append({"page": pn, "bbox": normalized(visible, page),
                                        "unassigned_native_lines": missed_text,
                                        "unassigned_image_regions": missed_images,
                                        "excluded_partial_duplicate": bool(duplicate),
                                        "canonical_duplicate_provenance": duplicate})
    coverage = {}
    for chapter in sorted(set(q["context"]["chapter_id"] for q in questions), key=lambda c: (c.isalpha(), int(c) if c.isdigit() else c)):
        ns = [int(q["original_number"].split(".")[1]) for q in questions if q["context"]["chapter_id"] == chapter]
        coverage[chapter] = {"observed_count": len(ns), "observed_first": min(ns), "observed_last": max(ns),
                             "range_count_inferred_from_printed_labels": max(ns),
                             "missing_numbers": sorted(set(range(1, max(ns)+1)) - set(ns)),
                             "duplicates": [n for n, ct in Counter(ns).items() if ct > 1]}
    audit = {"source_page_count": len(doc), "standalone_problem_count": len(questions),
             "range_count_inferred_from_printed_labels": sum(c["observed_last"] for c in coverage.values()),
             "expected_count_basis": "Observed chapter number sequences plus explicitly flagged private orphan-source overrides; not a publisher-declared total.",
             "chapters": coverage, "excluded_prose_references": excluded, "duplicate_headers": duplicates,
             "figure_isolation_errors": figure_errors, "isolated_figure_count": len(figure_assets),
             "boundary_errors": boundary_errors,
             "unassigned_question_box_regions": uncovered_boxes,
             "unassigned_question_box_region_count": sum(not x["excluded_partial_duplicate"] for x in uncovered_boxes),
             "source_endnote_count": len(notes),
             "question_count_with_unresolved_source": sum(q["context"]["unresolved_source"] for q in questions),
             "paid_api_calls": 0, "all_versions_review_status": "pending", "not_ready_for_publication": True}
    jsave(out / "questions.raw.json", {"version": 1, "profile": "native-boxed-quantum-problems",
                                       "source_sha256": digest, "questions": questions})
    jsave(out / "figure-index.json", {"figures": figure_assets, "errors": figure_errors})
    jsave(out / "footnote-index.json", {"notes": [{"chapter": c, **n} for (c, _), n in notes.items()]})
    jsave(out / "coverage-audit.json", audit)
    print(json.dumps({k: audit[k] for k in ["standalone_problem_count", "range_count_inferred_from_printed_labels",
                                          "isolated_figure_count", "question_count_with_unresolved_source",
                                          "unassigned_question_box_region_count"]}))


if __name__ == "__main__":
    main()

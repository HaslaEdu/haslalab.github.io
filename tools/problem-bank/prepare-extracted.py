"""Prepare private, provenance-preserving import files from reviewed extractor adapters.

This performs no OCR, translation, network requests, or automatic verification.
Run with a private root; store.mjs performs the final schema/integrity validation.
"""
import argparse
import base64
import copy
import hashlib
import json
import re
from pathlib import Path
from private_paths import private_directory


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def payload(path, expected):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected:
        raise ValueError(f"Source crop hash mismatch: {path.name}")
    return {"sha256": digest, "byte_length": len(data),
            "inline_base64": base64.b64encode(data).decode("ascii")}


def normalized_subjects(values):
    aliases = {"quantum_atomic_particle_physics": ["quantum_mechanics"],
               "mathematics": ["mathematical_methods"],
               "special_relativity": ["relativity"],
               "thermodynamics_statistical_physics": ["thermodynamics", "statistical_mechanics"]}
    return sorted({subject for value in values for subject in aliases.get(value, [value])})


def translations(folder):
    result = {}
    candidates = sorted(path for path in (folder / "translations").glob("*.json")
                        if re.fullmatch(r"\d+(?:-\d+)?\.json", path.name))
    if (folder / "ko-first10.json").exists():
        candidates.insert(0, folder / "ko-first10.json")
    for path in candidates:
        data = read_json(path)
        for item in data.get("questions", data.get("items", [])):
            number = str(item.get("locator", item["original_number"]))
            en, ko = item.get("text_en", item.get("en")), item.get("text_ko", item.get("ko"))
            if en and ko:
                result[number] = {"en": en, "ko": ko,
                    "unresolved_source": bool(item.get("unresolved_source", False)),
                    "source_image_checked": bool(item.get("source_image_checked", False)),
                    "review_notes": (item.get("review_notes", []) +
                                     item.get("scientific_review_notes", []) +
                                     item.get("transcription_corrections", []))}
    return result


def with_translation(question, translated):
    # Directly generated or image-checked content is still awaiting independent review.
    if translated:
        question.setdefault("context", {}).update({
            "unresolved_source": bool(question.get("context", {}).get("unresolved_source", False)
                                      or translated["unresolved_source"]),
            "source_image_checked": translated["source_image_checked"],
            "review_notes": translated["review_notes"]})
        original_language = question.get("source_language", "en")
        question["versions"] = [version for version in question.get("versions", [])
                                if version["language"] not in ("en", "ko")]
        question["versions"] += [{"language": language,
            "role": "original" if language == original_language else "translation",
            "text": translated[language], "review_status": "pending"} for language in ("en", "ko")]
    return question


REVIEWED_COUNTS = {"pns-optics": 160, "puzzling-200": 200, "guide-part1": 139,
                   "guide-part2": 182, "kalda": 555, "pns-thermo": 367,
                   "schroeder": 486, "puzzling-more": 200, "blundell": 238, "morin-mechanics": 496,
                   "pns-electro": 440, "astronomy-korean": 439, "griffiths-qm": 491,
                   "griffiths-electrodynamics": 587, "pns-quantum": 380, "pns-mechanics": 410}


def refresh_reviewed_source_counts(root, sources):
    # Every import includes the source inventory. Its progress must not depend on
    # which question payloads were selected for this particular update.
    for pattern in ("*/questions.raw.json", "*/questions-raw.json"):
        for path in sorted(root.glob(pattern)):
            expected = REVIEWED_COUNTS.get(path.parent.name)
            if expected is None:
                continue
            raw = read_json(path)
            if path.name == "questions.raw.json":
                ids = {question["source"]["drive_id"] for question in raw["questions"]}
                if len(ids) != 1:
                    raise ValueError("A reviewed extractor must identify exactly one registered source")
                source = sources[next(iter(ids))]
            else:
                matches = [source for source in sources.values() if source["sha256"] == raw["source_sha256"]]
                if len(matches) != 1:
                    raise ValueError("Reviewed source SHA must identify exactly one registered source")
                source = matches[0]
            source.update(expected_question_count=expected,
                          extraction_complete=len(raw["questions"]) == expected)


def prepare(root, text_only=False, profiles=None):
    root = private_directory(root)
    if profiles:
        available = {path.parent.name for pattern in ("*/questions.raw.json", "*/questions-raw.json")
                     for path in root.glob(pattern)}
        missing = sorted(set(profiles) - available)
        if missing:
            raise ValueError("Selected extractor folders have no question inventory: " + ", ".join(missing))
    manifest = read_json(root / "manifest.json")
    sources = {item["drive_id"]: item for item in manifest["sources"]}
    refresh_reviewed_source_counts(root, sources)
    questions = []
    for raw_file in sorted(root.glob("*/questions.raw.json")):
        if profiles and raw_file.parent.name not in profiles:
            continue
        raw, folder = read_json(raw_file), raw_file.parent
        translated = translations(folder)
        unique_numbers = len({str(q["original_number"]) for q in raw["questions"]}) == len(raw["questions"])
        for original in raw["questions"]:
            question = copy.deepcopy(original)
            question["subjects"] = normalized_subjects(question["subjects"])
            question["assets_complete"] = not text_only
            question.setdefault("context", {}).setdefault("quality_flags", original.get("quality_flags", []))
            for index, asset in enumerate(question.get("assets", [])):
                asset["asset_id"] = f"crop-{index + 1}"
                if asset["role"] in ("source_figure", "source_footnote", "source_context"):
                    question["context"].setdefault("source_asset_details", []).append({
                        "asset_id": asset["asset_id"], "source_role": asset["role"],
                        "figure_label": asset.get("figure_label"),
                        "quality_flags": asset.get("quality_flags", [])})
                    asset["role"] = "figure" if asset["role"] == "source_figure" else "question_crop"
                if not text_only:
                    path = Path(asset["local_path"])
                    if not path.is_absolute():
                        path = folder / path
                    asset.update(payload(path, asset["sha256"]))
            if text_only:
                question["assets"] = []
            translated_item = translated.get(question["locator"])
            if translated_item is None and unique_numbers:
                translated_item = translated.get(str(question["original_number"]))
            questions.append(with_translation(question, translated_item))
    for raw_file in sorted(root.glob("*/questions-raw.json")):
        if profiles and raw_file.parent.name not in profiles:
            continue
        raw, folder = read_json(raw_file), raw_file.parent
        matches = [source for source in sources.values() if source["sha256"] == raw["source_sha256"]]
        if len(matches) != 1:
            raise ValueError("Extracted source SHA must identify one registered private source")
        source = matches[0]
        translated = translations(folder)
        import pymupdf
        document = pymupdf.open(source["local_path"])
        for original in raw["questions"]:
            spans, assets = [], []
            for index, segment in enumerate(original["statement_segments"]):
                box = segment["bbox_pt"]
                size = segment.get("page_size_pt") or list(document[segment["pdf_page"] - 1].rect)[2:]
                span = {"page": segment["pdf_page"], "bbox": [
                    round(box[0] / size[0], 8), round(box[1] / size[1], 8),
                    round(box[2] / size[0], 8), round(box[3] / size[1], 8)]}
                spans.append(span)
                if not text_only:
                    assets.append({"asset_id": f"crop-{index + 1}", "role": "question_crop",
                    "mime_type": "image/webp", "spans": [span],
                    **payload(folder / segment["image"], segment["image_sha256"])})
            question = {"source": {"drive_id": source["drive_id"], "revision": source["revision"]},
                "locator": "problem-" + original["original_number"],
                "original_number": original["original_number"],
                "kind": "problem", "subjects": normalized_subjects(original["subjects"]),
                "level": source["level"], "assets_complete": not text_only,
                "chapter": str(original.get("chapter_title_en", original.get("chapter", ""))) or None,
                "spans": spans, "review_status": "pending", "assets": assets,
                "context": {"quality_flags": original.get("flags", []),
                            "topics_source": original.get("topics_source", []),
                            "difficulty_source_asterisks": original.get("difficulty_source_asterisks", 0),
                            "classification_provenance": original.get("classification_provenance", {}),
                            "title_en": original.get("title_en"),
                            "institutions_source": original.get("institutions_source", []),
                            "institution_provenance_text": original.get("institution_provenance_text")},
                "versions": [{"language": "en", "role": "original",
                    "text": original["text_en_ocr_raw"], "review_status": "pending"}]}
            questions.append(with_translation(question, translated.get(question["original_number"])))
        document.close()
    if profiles and not questions:
        raise ValueError("Selected extractor folders contain no questions; import snapshot was not replaced")
    out_manifest, out_questions = root / "import-manifest.json", root / "import-questions.json"
    out_manifest.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    out_questions.write_text(json.dumps({"version": 1, "questions": questions}, ensure_ascii=False), encoding="utf-8")
    return {"sources": len(sources), "questions": len(questions),
            "ko_versions": sum(any(v["language"] == "ko" for v in q["versions"]) for q in questions),
            "crop_images": sum(len(q["assets"]) for q in questions),
            "review_status": "pending", "paid_api_calls": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--text-only", action="store_true", help="Update already imported questions without resending their crop payloads")
    parser.add_argument("--profiles", nargs="+", help="Only import these complete private extractor folders")
    args = parser.parse_args()
    print(json.dumps(prepare(args.private_root.resolve(), args.text_only, args.profiles), ensure_ascii=True))

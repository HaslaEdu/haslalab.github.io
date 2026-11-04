"""Prepare private, page-level book text for later review; never train or upload.

Uses existing PDF/text caches and registered source hashes. All output remains
pending review. A user's local-processing instruction is recorded separately
from copyright, licensing, extraction quality, and scientific review.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_source_index(index_path: Path):
    """Accept either the active index pointer or a normalized source index."""
    data = load_json(index_path)
    selected = index_path
    if "normalized_sources" not in data:
        selected = Path(data["source_index"]["path"])
        if not selected.is_absolute():
            selected = index_path.parent / selected
        expected = data["source_index"].get("sha256")
        if expected and sha_file(selected) != expected:
            raise ValueError("Source index does not match the active pointer hash")
        data = load_json(selected)
    sources = data.get("normalized_sources")
    if not isinstance(sources, list) or not all(isinstance(s, dict) for s in sources):
        raise ValueError("Expected normalized_sources in the selected source index")
    return sources, selected


def extract_page(value, ordinal: int):
    if isinstance(value, str):
        return value, ordinal
    if isinstance(value, dict) and isinstance(value.get("text"), str):
        return value["text"], value.get("page", ordinal)
    raise ValueError(f"Unsupported cached text page format at ordinal {ordinal}")


def quality(text: str, min_chars: int = 80):
    issues = []
    visible = len(text.strip())
    replacement = text.count("\ufffd")
    controls = sum(ord(c) < 32 and c not in "\n\r\t\f" for c in text)
    if not visible:
        issues.append("empty_native_text")
    elif visible < min_chars:
        issues.append("short_native_text")
    if replacement / max(1, len(text)) > 0.02:
        issues.append("decoding_replacement_ratio")
    if controls / max(1, len(text)) > 0.01:
        issues.append("unexpected_control_ratio")
    return {
        "status": "pending_extraction" if issues else "ready_for_review",
        "issues": issues,
        "characters": len(text),
        "replacement_characters": replacement,
        "unexpected_control_characters": controls,
        "scientific_accuracy_verified": False,
    }


def select_source(pdf: Path, digest: str, by_hash):
    candidates = by_hash.get(digest, [])
    exact = [s for s in candidates if s.get("drive_id") == pdf.stem]
    if len(exact) == 1:
        return exact[0], "matched_pdf_hash_and_drive_id"
    if len(candidates) == 1:
        return candidates[0], "matched_pdf_hash"
    return None, "unmatched_pdf_hash" if not candidates else "ambiguous_pdf_hash"


def prepare(source_dir: Path, index_path: Path, output_dir: Path,
            authorization_note: str, min_chars: int = 80):
    if not authorization_note.strip():
        raise ValueError("A local-processing authorization note is required")
    source_dir, index_path = source_dir.resolve(), index_path.resolve()
    output_dir = output_dir.resolve()
    if output_dir == source_dir or source_dir in output_dir.parents:
        raise ValueError("Output must be separate from the original source directory")
    if output_dir.exists():
        raise FileExistsError("Output directory already exists; choose a new run directory")
    sources, selected_index = read_source_index(index_path)
    by_hash = defaultdict(list)
    for source in sources:
        if source.get("sha256"):
            by_hash[source["sha256"]].append(source)
    pdfs = sorted(source_dir.glob("*.pdf"))
    if not pdfs:
        raise ValueError("No original PDFs found in the selected source directory")

    # Validate and inventory before creating any output. No PDF/OCR/model API is used.
    books, skipped = [], []
    for pdf in pdfs:
        digest = sha_file(pdf)
        source, match = select_source(pdf, digest, by_hash)
        cached = pdf.with_suffix(".text.json")
        if not source or not cached.is_file():
            skipped.append({"pdf_name": pdf.name, "pdf_sha256": digest,
                            "reason": match if not source else "missing_text_cache"})
            continue
        pages = load_json(cached).get("pages")
        if not isinstance(pages, list):
            raise ValueError(f"Missing cached pages array: {cached.name}")
        parsed = [extract_page(page, i) for i, page in enumerate(pages, 1)]
        issues = []
        if source.get("page_count") != len(parsed):
            issues.append("registered_page_count_mismatch")
        books.append((pdf, cached, source, digest, parsed, issues, match))

    output_dir.mkdir(parents=True, exist_ok=False)
    authorization = {
        "basis": "user_requested_private_local_processing",
        "instruction_reference": authorization_note.strip(),
        "scope": "private_local_corpus_preparation",
        "copyright_ownership_asserted": False,
        "model_training_license_asserted": False,
        "external_upload_authorized_by_this_record": False,
    }
    inventory_books, source_records = [], []
    page_counts, issue_counts = Counter(), Counter()
    payload_path = output_dir / "pages.jsonl"
    with payload_path.open("x", encoding="utf-8", newline="\n") as out:
        for pdf, cached, source, digest, pages, book_issues, match in books:
            document_id = "private-book:" + digest
            origin = source.get("origin")
            license_identifier = origin.get("license_identifier") if isinstance(origin, dict) else None
            source_record = {
                "id": source["id"], "source_id": source["id"],
                "document_id": document_id, "type": "book",
                "title": source.get("title"), "revision": source.get("revision"),
                "sha256": digest, "source_language": source.get("source_language"),
                "subjects": source.get("subjects", []), "level": source.get("level"),
                "origin": origin, "license_identifier": license_identifier,
                "review_status": "pending", "rights_review": "pending",
                "processing_authorization": authorization,
                "metadata": {
                    "private": True, "pdf_path": str(pdf), "cached_text_path": str(cached),
                    "cached_text_sha256": sha_file(cached), "source_match": match,
                    "registered_page_count": source.get("page_count"),
                    "cached_page_count": len(pages), "extraction_issues": book_issues,
                    "canonical_source_metadata": source,
                },
            }
            source_records.append(source_record)
            counts = Counter()
            for ordinal, (text, cached_page_label) in enumerate(pages, 1):
                gate = quality(text, min_chars)
                if book_issues:
                    gate["issues"].extend(book_issues)
                    gate["status"] = "pending_extraction"
                counts[gate["status"]] += 1
                page_counts[gate["status"]] += 1
                issue_counts.update(gate["issues"])
                record = {
                    "id": document_id + f":page:{ordinal}",
                    "source_id": source["id"], "document_id": document_id,
                    "text": text, "review_status": "pending",
                    "metadata": {
                        "private": True, "kind": "book_page", "page_number": ordinal,
                        "cached_page_label": cached_page_label,
                        "text_sha256": text_sha(text), "original_pdf_sha256": digest,
                        "source_language": source.get("source_language"),
                        "rights_review": "pending", "license_identifier": license_identifier,
                        "scientific_review": "pending", "quality_gate": gate,
                        "processing_authorization": authorization, "training_eligible": False,
                    },
                }
                out.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            inventory_books.append({"source_id": source["id"], "document_id": document_id,
                                    "pdf_name": pdf.name, "pages": len(pages),
                                    "quality_counts": dict(counts), "extraction_issues": book_issues})
    (output_dir / "sources.json").write_text(
        json.dumps(source_records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(), "private": True,
        "processing_authorization": authorization,
        "source_index_path": str(selected_index), "source_index_sha256": sha_file(selected_index),
        "input_pdf_count": len(pdfs), "matched_book_count": len(books),
        "skipped_pdf_count": len(skipped), "skipped": skipped,
        "page_count": sum(page_counts.values()), "quality_counts": dict(page_counts),
        "quality_issue_counts": dict(issue_counts), "books": inventory_books,
        "payload": {"path": str(payload_path), "bytes": payload_path.stat().st_size,
                    "sha256": sha_file(payload_path)},
        "training_examples_created": 0, "external_uploads": 0,
        "all_records_pending_rights_and_scientific_review": True,
        "notes": ["Native text may omit equations, figures, tables, and scanned pages.",
                  "Extraction quality does not establish scientific correctness or a training license.",
                  "Page-level records are not solved question/answer pairs."],
    }
    (output_dir / "inventory.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--source-index", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--authorization-note", required=True)
    parser.add_argument("--min-page-chars", type=int, default=80)
    args = parser.parse_args(argv)
    if args.min_page_chars < 1:
        parser.error("--min-page-chars must be positive")
    try:
        report = prepare(args.source_dir, args.source_index, args.output_dir,
                         args.authorization_note, args.min_page_chars)
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=True), file=sys.stderr)
        return 1
    print(json.dumps({"output_dir": str(args.output_dir.resolve()),
                      "books": report["matched_book_count"], "pages": report["page_count"],
                      "skipped_pdfs": report["skipped_pdf_count"],
                      "quality_counts": report["quality_counts"],
                      "training_examples_created": 0, "external_uploads": 0}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

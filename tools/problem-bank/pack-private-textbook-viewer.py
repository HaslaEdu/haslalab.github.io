"""Build the private viewer's immutable R2 objects from the archived intake."""

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

import pymupdf
from PIL import Image

PREFIX = Path("textbook-intake/2026-11-21/viewer-v1")
REPO = Path(__file__).resolve().parents[2]
BATCH_SIZE = 24
IMAGE_LIMIT = 2 * 1024 * 1024
JSON_LIMIT = 6 * 1024 * 1024
HEX = re.compile(r"[0-9a-f]{64}")
BOOK = re.compile(r"[a-z][a-z0-9-]{0,31}")
REVIEW = {
    "source_compared": 5,
    "model_source_reviewed": 4,
    "upstream_corrected_edition": 3,
    "source_translation_pending_review": 2,
    "machine_draft": 0,
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def json_data(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_json(path, value):
    data = json_data(value)
    if len(data) > JSON_LIMIT:
        raise ValueError(f"Viewer JSON exceeds its read limit: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return digest(data)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path):
    with path.open(encoding="utf-8-sig") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def require_relative(path, parent):
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(parent.resolve()):
        raise ValueError("Input path escapes the private intake")
    return resolved


def loaded_sources(intake):
    sources = {}
    for row in read_json(intake / "verified-sources.json")["sources"]:
        sid, sha, key = row["id"], row["sha256"], row["key"]
        if not BOOK.fullmatch(sid) or not HEX.fullmatch(sha) or key != f"sources/{sha}.pdf":
            raise ValueError("Invalid source identity")
        path = require_relative(intake / "sources" / f"{sid}.pdf", intake)
        if file_sha256(path) != sha or path.stat().st_size != row["byte_length"]:
            raise ValueError(f"Source file differs from its archive receipt: {sid}")
        sources[key] = (sid, pymupdf.open(path))
    return sources


def raster(page):
    scale = min(1600 / max(page.rect.width, page.rect.height), 3.5)
    rendered = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
    image = Image.frombytes("RGB", (rendered.width, rendered.height), rendered.samples)
    buffer = BytesIO()
    image.save(buffer, "WEBP", quality=88, method=0)
    return buffer.getvalue()


class MediaPack:
    def __init__(self, root, filename):
        self.path = root / filename
        self.stream = self.path.open("wb")
        self.by_digest = {}
        self.by_item = {}

    def add(self, key, read):
        if key not in self.by_item:
            data = read()
            sha = digest(data)
            if (not 12 <= len(data) <= IMAGE_LIMIT or data[:4] != b"RIFF" or
                    data[8:12] != b"WEBP"):
                raise ValueError("Unexpected size or format in a private viewer image")
            if sha not in self.by_digest:
                self.by_digest[sha] = {"offset": self.stream.tell(), "length": len(data), "sha256": sha}
                self.stream.write(data)
            self.by_item[key] = self.by_digest[sha]
        return self.by_item[key]

    def close(self, destination):
        self.stream.close()
        sha, size = file_sha256(self.path), self.path.stat().st_size
        if not 12 <= size <= 1024 * 1024 * 1024:
            raise ValueError("Unexpected textbook media pack size")
        for attrs in self.by_digest.values():
            attrs.update(pack_sha256=sha, pack_size=size)
        destination.mkdir(parents=True, exist_ok=True)
        self.path.replace(destination / f"{sha}.bin")


def text_versions(row, overlay):
    result = {}
    for lang in ("en", "ko"):
        candidates = [
            version for version in row["versions"] if version.get("language") == lang
            and version.get("role") in {"original", "translation", "statement"}
            and isinstance(version.get("text"), str) and version["text"].strip()
        ]
        if overlay and overlay.get(f"text_{lang}"):
            candidates.append({"text": overlay[f"text_{lang}"], "review_status": overlay["review_status"],
                               "review_basis": overlay.get("review_basis")})
        if candidates:
            best = max(candidates, key=lambda version: REVIEW.get(version.get("review_status"), 1))
            if len(best["text"]) > 120000:
                raise ValueError(f"Statement too large for viewer: {row['id']}")
            result[lang] = {"text": best["text"], "review_status": best.get("review_status") or "pending"}
            if best.get("review_basis") == "structured_english_russian":
                result[lang]["review_basis"] = best["review_basis"]
        else:
            result[lang] = None
    if not result.get("en"):
        raise ValueError(f"Missing English statement: {row['id']}")
    return result


def read_overlays(paths):
    output = {}
    for path in paths:
        for overlay in read_jsonl(path):
            ident = overlay.get("id")
            state = overlay.get("review_status")
            if not isinstance(ident, str) or not HEX.fullmatch(overlay.get("source_sha256", "")) or state not in {
                "machine_draft", "model_source_reviewed", "source_compared"
            } or not isinstance(overlay.get("text_ko"), str) or not overlay["text_ko"].strip():
                raise ValueError("Invalid viewer translation overlay")
            structured = (ident.startswith("savchenko:") and
                          overlay.get("review_basis") == "structured_english_russian" and
                          HEX.fullmatch(overlay.get("statement_sha256", "")))
            if state != "machine_draft" and not structured and overlay.get("source_image_checked") is not True:
                raise ValueError(f"Source comparison missing in overlay: {ident}")
            if "text_en" in overlay and not isinstance(overlay["text_en"], str):
                raise ValueError(f"Invalid English text in overlay: {ident}")
            previous = output.get(ident)
            if previous:
                if previous["source_sha256"] != overlay["source_sha256"]:
                    raise ValueError(f"Conflicting source revisions for overlay: {ident}")
                precedence = REVIEW[state] - REVIEW[previous["review_status"]]
                if precedence == 0 and previous != overlay:
                    raise ValueError(f"Conflicting overlays with the same review status: {ident}")
                if precedence <= 0:
                    continue
            output[ident] = overlay
    return output


def svg_raster(data):
    # The viewer serves raster bytes exclusively, including site diagrams.
    with pymupdf.open(stream=data, filetype="svg") as doc:
        return raster(doc[0])


def add_media(row, intake, sources, pack, figures, overlay):
    media = []
    def item(attrs, kind, *, page=None, label=""):
        media.append({"id": len(media) + 1, "kind": kind, "page": page,
                      "label": label, "slice": attrs})
    source_key = row["source_object"]
    source_id, document = sources[source_key]
    if source_key != f"sources/{row['source_sha256']}.pdf":
        raise ValueError(f"Mismatched source for {row['id']}")
    for entry in row.get("question_crops", []):
        path = require_relative(intake / source_id / entry["file"], intake)
        sha = entry["sha256"]
        def crop():
            data = path.read_bytes()
            if digest(data) != sha:
                raise ValueError(f"Source crop hash changed: {path.name}")
            return data
        item(pack.add(("crop", sha), crop), "question_crop", page=entry["span"]["page"])
    if figures:
        for entry in row.get("figures", []):
            path = entry["path"]
            if not re.fullmatch(r"assets/img/[0-9.]+/[a-zA-Z0-9_.-]+\.svg", path):
                continue
            if path in figures.NameToInfo:
                if not 1 <= figures.getinfo(path).file_size <= IMAGE_LIMIT:
                    raise ValueError("Archived figure exceeds the raster input limit")
                item(pack.add(("figure", path), lambda: svg_raster(figures.read(path))), "figure")
    primary_pages = list(dict.fromkeys(span["page"] for span in row.get("spans", [])))
    if not primary_pages and row.get("source_pdf_page"):
        primary_pages = [row["source_pdf_page"]]
    if not primary_pages:
        raise ValueError(f"Missing original page for {row['id']}")
    if overlay and overlay["review_status"] != "machine_draft":
        extra_pages = {figure.get("source_page") for figure in overlay.get("figures", [])
                       if isinstance(figure.get("source_page"), int)}
        extra_pages.update(span["page"] for span in overlay.get("figure_spans", [])
                           if isinstance(span.get("page"), int))
        primary_pages += sorted(p for p in extra_pages if p not in primary_pages)
    for pg in primary_pages:
        if not isinstance(pg, int) or not 1 <= pg <= len(document):
            raise ValueError(f"Invalid PDF page on {row['id']}")
        item(pack.add(("page", source_key, pg), lambda: raster(document[pg - 1])), "source_page", page=pg)
    reference = row.get("english_reference")
    if reference:
        alt_key = reference["source_object"]
        _, alternate = sources[alt_key]
        for pg in dict.fromkeys(span["page"] for span in reference["spans"]):
            if not isinstance(pg, int) or not 1 <= pg <= len(alternate):
                raise ValueError(f"Invalid alternate PDF page on {row['id']}")
            item(pack.add(("page", alt_key, pg), lambda: raster(alternate[pg - 1])), "english_page", page=pg)
    if len(media) > 100:
        raise ValueError(f"Too many media records for {row['id']}")
    return media


def flatten_media(media):
    for asset in media:
        yield {**{k: v for k, v in asset.items() if k != "slice"}, **asset["slice"]}


def build(intake, temporary, overlays):
    catalogue = read_json(intake / "records" / "catalog.json")
    sources = loaded_sources(intake)
    seen = set()
    stage = temporary / "texts"
    manifest = {"schema": "haslalab-private-textbook-viewer/v1", "books": []}
    zip_path = intake / "savchenko/figures.zip"
    figures = zipfile.ZipFile(require_relative(zip_path, intake)) if zip_path.exists() else None
    try:
        for material in catalogue["materials"]:
            key = material["id"]
            if not BOOK.fullmatch(key):
                raise ValueError("Invalid archive book identifier")
            rows, directory = [], []
            pack = MediaPack(temporary, key + ".bin")
            try:
                entries = require_relative(intake / material["records"], intake)
                for ordinal, row in enumerate(read_jsonl(entries), 1):
                    ident = row["id"]
                    if ident in seen:
                        raise ValueError(f"Repeated archive identity: {ident}")
                    seen.add(ident)
                    overlay = overlays.get(ident)
                    if overlay and overlay["source_sha256"] != row["source_sha256"]:
                        raise ValueError(f"Overlay source revision differs: {ident}")
                    if overlay and overlay.get("review_basis") == "structured_english_russian":
                        if key != "savchenko" or digest(row["statement_en"].encode()) != overlay["statement_sha256"]:
                            raise ValueError(f"Savchenko English statement revision differs: {ident}")
                    versions = text_versions(row, overlay)
                    chapter = row.get("chapter_title_en") or row.get("chapter") or row.get("section") or ""
                    summary = {"ordinal": ordinal, "number": row["original_number"],
                               "label": row.get("title") or row.get("section_title_en") or "",
                               "chapter": str(chapter), "kind": row.get("kind") or "",
                               "has_korean": bool(versions["ko"])}
                    directory.append(summary)
                    details = {**summary, **versions, "media": add_media(
                        row, intake, sources, pack, figures if key == "savchenko" else None, overlay
                    )}
                    if key == "savchenko":
                        number = row["original_number"]
                        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){2}", number):
                            raise ValueError(f"Unexpected Savchenko problem label: {ident}")
                        details["credit"] = {
                            "source_url": f"https://savchenkosolutions.com/en/{number}",
                            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                        }
                    rows.append(details)
                if len(rows) != material["problem_count"]:
                    raise ValueError(f"Book row count changed: {key}")
                pack.close(temporary / PREFIX / "media")
            finally:
                pack.stream.close()
            for row in rows:
                row["media"] = list(flatten_media(row["media"]))
            book_path = stage / key
            index_hash = write_json(book_path / "index.json", directory)
            batches = [
                write_json(book_path / "batches" / f"{i // BATCH_SIZE}.json", rows[i:i + BATCH_SIZE])
                for i in range(0, len(rows), BATCH_SIZE)
            ]
            manifest["books"].append({
                "id": key, "title": material["title"], "limitation": material.get("limitation", ""),
                "count": len(rows), "korean_count": sum(item["has_korean"] for item in directory),
                "index_sha256": index_hash, "batches": batches,
            })
            print(key, len(rows), manifest["books"][-1]["korean_count"], flush=True)
        if overlays.keys() - seen:
            raise ValueError("An overlay does not match any archived question")
    finally:
        for _, document in sources.values():
            document.close()
        if figures:
            figures.close()
    release = write_json(stage / "manifest.json", manifest)
    target = temporary / PREFIX / "releases" / release
    target.parent.mkdir(parents=True, exist_ok=True)
    stage.replace(target)
    return release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, action="append", default=[])
    args = parser.parse_args()
    intake, output = args.intake.resolve(), args.output.resolve()
    if intake.is_relative_to(REPO) or output.is_relative_to(REPO):
        parser.error("Keep private source bytes and viewer packs outside the public worktree")
    if output.exists():
        parser.error("Choose a new private output directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix="viewer-build-") as work:
        stage = Path(work)
        release = build(intake, stage, read_overlays(args.overlay))
        objects = [{"key": path.relative_to(stage).as_posix(), "sha256": file_sha256(path),
                    "byte_length": path.stat().st_size}
                   for path in sorted((stage / PREFIX).rglob("*")) if path.is_file()]
        write_json(stage / "viewer-object-manifest.json", {"release": release, "objects": objects})
        output.mkdir()
        shutil.move(stage / "textbook-intake", output / "textbook-intake")
        shutil.move(stage / "viewer-object-manifest.json", output / "viewer-object-manifest.json")
    print(json.dumps({"release": release, "objects": len(objects)}), flush=True)


if __name__ == "__main__":
    main()

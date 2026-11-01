"""Local Tesseract OCR checkpoints for scanned books. No paid provider calls.

Text/math remain unverified; original PDF coordinates and source images govern.
Requires tesserocr, Pillow, PyMuPDF and locally installed English trained data.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from private_paths import private_directory


def process(args):
    os.environ.setdefault("OMP_THREAD_LIMIT", "1")
    import pymupdf
    import tesserocr
    from PIL import Image
    output, source = private_directory(args.output_dir), args.pdf.resolve()
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    training = args.tessdata_dir / (args.language + ".traineddata")
    training_hash = hashlib.sha256(training.read_bytes()).hexdigest()
    document = pymupdf.open(source)
    last = args.last_page or len(document)
    if not 1 <= args.first_page <= last <= len(document):
        raise ValueError("Invalid source page range")
    if args.max_render_side and not 1000 <= args.max_render_side <= 10000:
        raise ValueError("Maximum rendered side must be 1000–10000 pixels, or zero")
    with tesserocr.PyTessBaseAPI(path=str(args.tessdata_dir.resolve()), lang=args.language) as engine:
        for number in range(args.first_page, last + 1):
            target = output / f"page-{number:05d}.json"
            if target.exists():
                previous = json.loads(target.read_text(encoding="utf-8"))
                if (previous["source_sha256"], previous["page"], previous["dpi"], previous["training_sha256"]) != (source_hash, number, args.dpi, training_hash):
                    raise ValueError("OCR checkpoint source/scale/training mismatch")
                if previous.get("max_render_side", 0) != args.max_render_side:
                    raise ValueError("OCR checkpoint rendering-cap mismatch")
                continue
            started, page = time.monotonic(), document[number - 1]
            scale = args.dpi / 72
            if args.max_render_side:
                scale = min(scale, args.max_render_side / max(page.rect.width, page.rect.height))
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale),
                                     colorspace=pymupdf.csGRAY, alpha=False)
            image = Image.frombytes("L", [pixmap.width, pixmap.height], pixmap.samples)
            engine.SetImage(image)
            text, confidence, tsv = engine.GetUTF8Text(), engine.MeanTextConf(), engine.GetTSVText(number - 1)
            record = {"page": number, "source_pages": len(document), "source_sha256": source_hash,
                "page_size_pt": list(page.rect)[2:], "render_size_px": [pixmap.width, pixmap.height],
                "dpi": args.dpi, "max_render_side": args.max_render_side,
                "render_scale": scale, "engine": "tesseract-local", "language": args.language,
                "training_sha256": training_hash, "confidence": confidence, "text": text,
                "tsv": tsv, "review_status": "pending", "paid_api_calls": 0}
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            temporary.replace(target)
            print(json.dumps({"page": number, "of": last, "confidence": confidence,
                              "seconds": round(time.monotonic() - started, 2)}), flush=True)
            image.close()
            engine.Clear()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--tessdata-dir", required=True, type=Path)
    parser.add_argument("--first-page", type=int, default=1)
    parser.add_argument("--last-page", type=int, default=0)
    parser.add_argument("--dpi", type=int, default=180)
    parser.add_argument("--max-render-side", type=int, default=0,
                        help="Optional pixel cap for scans with oversized PDF page boxes; zero preserves the requested DPI")
    parser.add_argument("--language", default="eng")
    process(parser.parse_args())

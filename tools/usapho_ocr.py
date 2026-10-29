#!/usr/bin/env python3
"""Extract scan-only source positions for layout matching (never exam content).

Requires RapidOCR's ONNX runtime. Scans are rendered at 2 pixels per PDF point;
the saved line positions are converted back to PDF points. Korean body text and
equations continue to come from the user's original vector translation PDFs.
"""
import json
from pathlib import Path

from rapidocr_onnxruntime import RapidOCR
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "tmp/source-audit/usapho-design/scans"


def main():
    engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=2)
    images = sorted(FOLDER.glob("*.png"))
    for number, path in enumerate(images, 1):
        output = path.with_suffix(".json")
        if output.exists():
            continue
        if path.name.startswith("1997-"):
            continue  # The 1997 original already has an extractable text layer.
        image = Image.open(path).convert("RGB")
        if not path.stem.endswith("-1"):
            # Question IDs live in the left margin. Reading prose/formulae is
            # unnecessary for geometry and slower than reading the ID strip.
            image = image.crop((0, 0, 300, image.height))
        found, _ = engine(np.array(image))
        result = []
        for polygon, text, confidence in found or []:
            xs, ys = zip(*polygon)
            result.append({"text": text, "rect": [min(xs) / 2, min(ys) / 2, max(xs) / 2, max(ys) / 2],
                           "confidence": confidence})
        output.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        if number % 5 == 0:
            print(f"OCR positions: {number}/{len(images)}", flush=True)


if __name__ == "__main__":
    main()

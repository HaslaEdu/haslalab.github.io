"""Rebuild reviewed Korean IZhO editions; fetch originals from their archive release as needed.

    python tools/izho_rebuild.py 2026
    python tools/izho_rebuild.py 2025 2026 --output pdfx/izho

Only complete reviewed translation.json files are built. This never re-extracts or overwrites Korean text.
"""
import argparse
from pathlib import Path
from izho_translate import ROOT, build

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("years", nargs="+", type=int)
p.add_argument("--output", type=Path, default=ROOT / "pdfx" / "izho")
a = p.parse_args()
for year in a.years:
    folders = [ROOT / "tools" / "ko" / "izho" / str(year) / kind for kind in ("T", "TS")]
    for folder in folders:
        if not (folder / "translation.json").exists():
            continue
        build(folder, a.output / f"IZhO_{year}_{folder.name}_KO.pdf")

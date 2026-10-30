"""Apply reviewed Korean prose maps to extracted IZhO translation manifests."""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    import sys
    for year in map(int, sys.argv[1:] or range(2010, 2018)):
        for kind in ("T", "TS", "T3S"):
            folder = ROOT / "tools/ko/izho" / str(year) / kind
            manual = folder / "ko.json"
            if not manual.exists():
                continue
            words = json.loads(manual.read_text(encoding="utf-8"))
            manifest = folder / "translation.raw.json"
            if not manifest.exists():
                manifest = folder / "translation.json"
            data = json.loads(manifest.read_text(encoding="utf-8"))
            known = {entry["id"] for entry in data["entries"]}
            if set(words) - known:
                raise ValueError(f"Unknown source IDs: {year}/{kind}: {set(words) - known}")
            for entry in data["entries"]:
                if entry["id"] in words:
                    entry["ko"] = words[entry["id"]]
                if entry["ko"] and Counter(re.findall(r"\[\[\d+\]\]", entry["ko"])) != Counter(re.findall(r"\[\[\d+\]\]", entry["source"])):
                    raise ValueError(f"Inline math differs: {year}/{kind}/{entry['id']}")
            manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(year, kind, sum(bool(entry["ko"]) for entry in data["entries"]), "/", len(data["entries"]))


if __name__ == "__main__":
    main()

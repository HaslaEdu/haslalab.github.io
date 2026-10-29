#!/usr/bin/env python3
"""Verify source classifications and PDF downloads for the W/X/Y catalogue.

python tools/rupho_selection_validate.py [--download]
Downloads are cached under tmp/source-audit/rupho-selection, never rewritten.
"""
import argparse
import concurrent.futures
import io
import json
import re
import urllib.request
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    snapshot = json.loads((ROOT / "tools/rupho_selection_sources.json").read_text(encoding="utf-8"))
    assert {x["id"] for x in snapshot["phoxiv_groups"]} == {"rupho-w", "rupho-x", "rupho-y"}
    tasks = []
    seen_files = set()
    for letter in "WXY":
        manifest = json.loads((ROOT / f"tools/theory/rupho{letter.lower()}.json").read_text(encoding="utf-8"))
        assert manifest["classification"] == letter
        for year in manifest["years"]:
            paper_parts = set()
            for file in year["files"]:
                assert file["file"] not in seen_files, file["file"]
                seen_files.add(file["file"])
                assert re.fullmatch(r"T\d+[a-z]?", file["part"]), file
                assert f"/rupho-{letter.lower()}/{year['y']}/" in file["url"], file
                if file["kind"] == "paper":
                    paper_parts.add(file["part"])
                tasks.append((file["file"], file["url"]))
            assert paper_parts == {x["id"] for x in year["problems"]}
        for year in snapshot["groups"][letter]:
            for problem in year["problems"]:
                if problem["number"].startswith("T"):
                    continue
                for index, file in enumerate(problem["files"]):
                    if file["url"].endswith(".pdf"):
                        tasks.append((f"RuPhO{letter}_{year['year']}_{problem['number']}_{index}.pdf", file["url"]))
    print(f"Catalogue checked: {len(seen_files)} unique theory PDFs, {len(tasks)} total source PDFs", flush=True)
    if not args.download:
        return
    output = ROOT / "tmp/source-audit/rupho-selection"
    output.mkdir(parents=True, exist_ok=True)

    def check(task):
        name, url = task
        path = output / name
        try:
            if not path.exists():
                request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                data = urllib.request.urlopen(request, timeout=45).read()
                if not data.startswith(b"%PDF"):
                    raise ValueError("Response is not a PDF")
                path.write_bytes(data)
            data = path.read_bytes()
            pdf = PdfReader(io.BytesIO(data))
            return {"name": name, "url": url, "bytes": len(data), "pages": len(pdf.pages)}
        except Exception as exc:
            return {"name": name, "url": url, "error": str(exc)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(check, tasks))
    failed = [x for x in results if "error" in x]
    report = {"checked": len(results), "passed": len(results) - len(failed), "failures": failed, "files": results}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "files"}, ensure_ascii=False, indent=2), flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build the W/X/Y Russian team-selection archive, separately from RuPhO finals.

    python tools/rupho_selection_build.py --refresh
    python tools/rupho_selection_build.py

The checked-in source snapshot retains phoXiv's file labels and pho.rs's problem
titles/identifiers. Only actual PDF links from phoXiv enter the theory manifests.
E/PE stay in the experiment collection; a numbered T stays a theory problem.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "tools/rupho_selection_sources.json"
UA = "Mozilla/5.0 (HaslaLab source catalogue)"
GROUPS = {
    "W": {
        "ko": "러시아 대표 선발 예비 과정 (W)",
        "en": "Russian Team Selection Test (W)",
        "description": {
            "ko": "전러시아 물리 올림피아드 결선에서 진행하는 대표 선발 예비 과정입니다. 10학년의 X·Y 선발 준비 과정으로, 결선의 학년별 시험과 구분합니다.",
            "en": "Preliminary selection at the All-Russian finals, preparing grade 10 students for the X and Y selection stages. Separate from the grade-specific national final papers.",
        },
    },
    "X": {
        "ko": "러시아 대표 선발 1차 (X)",
        "en": "Russian Team Selection Test (X)",
        "description": {
            "ko": "러시아 IPhO 대표 선발의 첫 번째 단계입니다. W 예비 과정, Y 2차 선발 및 전러시아 결선과 구분합니다.",
            "en": "First stage of the Russian IPhO team selection. Separate from W preparation, Y second-stage selection and the national finals.",
        },
    },
    "Y": {
        "ko": "러시아 대표 선발 2차 (Y)",
        "en": "Russian Team Selection Test (Y)",
        "description": {
            "ko": "러시아 IPhO 대표 선발의 두 번째 단계입니다. W 예비 과정, X 1차 선발 및 전러시아 결선과 구분합니다.",
            "en": "Second stage of the Russian IPhO team selection. Separate from W preparation, X first-stage selection and the national finals.",
        },
    },
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8-sig")


def pho_titles(page: str) -> dict:
    """Parse only the visible source's numbered problem links, not scripts."""
    result = {}
    sections = re.split(r'<a name="y([WXY]\d{2})">', page)
    for i in range(1, len(sections), 2):
        code, body = sections[i], sections[i + 1]
        entries = re.findall(
            r'<span class="label[^\"]*">([^<]+)</span>.*?'
            r'<a href="//pho\.rs/p/(\d+)"[^>]*>(.*?)</a>', body, re.S
        )
        result[code] = {
            html.unescape(number).strip(): {
                "title": html.unescape(re.sub(r"<[^>]*>", "", title)).strip(),
                "url": "https://pho.rs/p/" + source_id,
            }
            for number, source_id, title in entries
        }
    return result


def refresh() -> dict:
    catalogue = json.loads(fetch("https://phoxiv.org/api/olympiads"))
    russian = [x for x in catalogue if x["id"].startswith("rupho-")]
    titles = pho_titles(fetch("https://xy.pho.rs/"))
    data = {
        "sources": ["https://phoxiv.org/api/olympiads", "https://xy.pho.rs/"],
        "classification": {
            "final": "National finals by grade (separate tools/theory/rupho.json)",
            "W": "Preliminary selection / grade-10 preparation",
            "X": "First team-selection stage",
            "Y": "Second team-selection stage",
            "Z": "Not listed in either source. Do not infer an extra stage or map IZhO to it.",
        },
        "phoxiv_groups": russian,
        "groups": {},
        "pho_rs_only": {},
    }
    for letter in GROUPS:
        years = json.loads(fetch(f"https://phoxiv.org/api/olympiads/rupho-{letter.lower()}"))
        for year in years:
            source_key = letter + str(year["year"])[-2:]
            matched = titles.get(source_key, {})
            for problem in year["problems"]:
                problem.update(matched.get(problem["number"], {}))
        data["groups"][letter] = years
        known = {letter + str(y["year"])[-2:] for y in years}
        for key, problems in titles.items():
            if key.startswith(letter) and key not in known:
                data["pho_rs_only"][key] = {
                    "url": "https://xy.pho.rs/" + key,
                    "problems": problems,
                }
    SNAPSHOT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Refresh both source catalogues")
    args = parser.parse_args()
    data = refresh() if args.refresh else json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    experiments, counts = {}, {}
    for letter, settings in GROUPS.items():
        comp, prefix = "rupho" + letter.lower(), "RuPhO" + letter
        manifest = {
            "comp": comp, "prefix": prefix, "abbr": f"RuPhO ({letter})",
            "full": {"ko": settings["ko"], "en": settings["en"]},
            "since": min(y["year"] for y in data["groups"][letter]),
            "scope": {"ko": "러시아 · 대표 선발", "en": "Russia · team selection"},
            "about": settings["description"]["en"],
            "classification": letter,
            "sources": [f"https://phoxiv.org/olympiads/rupho-{letter.lower()}", "https://xy.pho.rs/"],
            "years": [],
        }
        experiment = {
            "abbr": manifest["abbr"], "full": manifest["full"], "since": manifest["since"],
            "scope": manifest["scope"], "soon": settings["description"],
            "note": settings["description"], "plain": True, "years": [],
        }
        n_theory = n_experiment = n_files = 0
        for source in data["groups"][letter]:
            year = source["year"]
            theory = {
                "y": year, "host": {"ko": "러시아 · " + letter + " 선발", "en": "Russia · " + letter + " selection"},
                "cc": "ru", "source_page": "https://xy.pho.rs/" + letter + str(year)[-2:],
                "problems": [], "files": [],
            }
            practical = {"y": year, "host": theory["host"], "cc": "ru", "problems": []}
            for problem in source["problems"]:
                code = problem["number"]
                if not re.fullmatch(r"(?:T\d+|E\d+|PE\d*)\+?", code):
                    raise ValueError(f"Unclassified problem code {letter} {year} {code}")
                title = problem.get("title", code)
                if code.startswith("T"):
                    n_theory += 1
                    for item in problem["files"]:
                        label = item["label"]
                        part_match = re.fullmatch(r"Part (\d+)", label)
                        part = code + chr(96 + int(part_match[1])) if part_match else code
                        if not re.fullmatch(r"T\d+[a-z]?", part):
                            raise ValueError(f"Unsupported theory part {part}")
                        kind = {"Problem": "paper", "Solution": "solution", "Answer Sheet": "answer"}.get(label)
                        if part_match:
                            kind = "paper"
                        if kind is None:
                            raise ValueError(f"Unknown file role {letter} {year} {code} {label}")
                        if not item["url"].endswith(".pdf"):
                            raise ValueError("Non-PDF theory source: " + item["url"])
                        suffix = "_RU" if kind == "paper" else {"solution": "S", "answer": "A"}[kind]
                        file = {
                            "file": f"{prefix}_{year}_{part}{suffix}.pdf", "part": part,
                            "kind": kind, "url": item["url"],
                            "source_problem": code, "source_label": label,
                        }
                        if kind == "paper":
                            file["lang"] = "RU"
                        theory["files"].append(file)
                        n_files += 1
                        if kind == "paper":
                            entry = {"id": part, "title": title + (" (" + label + ")" if part_match else "")}
                            if problem.get("url"):
                                entry["source_page"] = problem["url"]
                            theory["problems"].append(entry)
                else:
                    n_experiment += 1
                    files = {item["label"]: item["url"] for item in problem["files"]}
                    if "Problem" not in files:
                        raise ValueError(f"No experimental paper: {letter} {year} {code}")
                    links = {"pdf": {"ru": files["Problem"]}}
                    if files.get("Solution"):
                        links["sol"] = {"ru": files["Solution"]}
                    if problem.get("url"):
                        links["src"] = problem["url"]
                    practical["problems"].append({
                        "id": code,
                        "title": {"ko": title, "en": title},
                        "desc": settings["description"],
                        "tags": ["지필 실험" if code.startswith("PE") else "실험", letter + " 선발"],
                        "tagsEn": ["Paper experiment" if code.startswith("PE") else "Experiment", letter + " selection"],
                        "files": links,
                    })
            if theory["files"]:
                manifest["years"].append(theory)
            if practical["problems"]:
                experiment["years"].append(practical)
        (ROOT / "tools/theory" / (comp + ".json")).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        experiments[comp] = experiment
        counts[letter] = {"years": len(manifest["years"]), "theory_problems": n_theory,
                          "theory_files": n_files, "experimental_problems": n_experiment}
        shutil.copyfile(ROOT / "logo/rupho.png", ROOT / "logo" / (comp + ".png"))
    js = "/* Russian selection W/X/Y: generated by tools/rupho_selection_build.py. */\n"
    js += "window.RUPHO_SELECTION=" + json.dumps(experiments, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (ROOT / "rupho-selection.js").write_text(js, encoding="utf-8")
    print(json.dumps({"counts": counts, "pho_rs_only": list(data.get("pho_rs_only", {}))}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

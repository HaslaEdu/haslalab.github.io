"""Collect public score distributions without contestant names.

Run from the repository root.  Raw downloads are cached under tmp/physics-benchmarks;
only anonymized distributions and source receipts are written to tools/results.
IPhO's public database is MIT licensed; unawarded contestants' absent scores remain
absent.  Never normalize a partial paper to a complete contest score.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "tmp/physics-benchmarks"
OUT = ROOT / "tools/results"
CHECKED = "2026-10-30"
IPHO_COMMIT = "51f424f879719707719d32b0f94d5d0b0504c836"
IPHO_RAW = f"https://raw.githubusercontent.com/abeakkas/ipho-unofficial.org/{IPHO_COMMIT}/src/database/"
STATUTES = "https://www.ipho-new.org/statutes-syllabus/"
RECEIPTS: list[dict] = []
EXPERIMENT_SETS = {
    "ipho": {y: [["E1", "E2"]] for y in [2012, 2015, 2016, 2018, 2021, 2022, 2023, 2024, 2025]},
    "eupho": {2017: [["E1"]], 2018: [["E1"]], 2019: [["E1"]], 2020: [["E1", "E2"]],
               2021: [["E1", "E2"]], 2022: [["E1"]], 2023: [["E1", "E2"]],
               2024: [["E1"]], 2025: [["E1", "E2"]], 2026: [["E1"]]},
    "apho": {2017: [["E1"]], 2019: [["E1", "E2"]], 2025: [["E1"]], 2026: [["E1", "E2"]]},
}


def source(url, title, official=True):
    return {"url": url, "title": title, "official": official}


def fetch(url, filename):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / filename
    if not f.exists():
        r = requests.get(url, timeout=35)
        r.raise_for_status()
        f.write_bytes(r.content)
    data = f.read_bytes()
    RECEIPTS.append({"url": url, "file": filename, "bytes": len(data),
                     "sha256": hashlib.sha256(data).hexdigest()})
    return data


def paper_sets(comp, year):
    manifest = json.loads((ROOT / f"tools/theory/{comp}.json").read_text(encoding="utf-8"))
    item = next((x for x in manifest["years"] if x["y"] == year), None)
    if not item:
        return []
    parts = {x["part"] for x in item["files"] if x["kind"] == "paper"}
    out = []
    if "T" in parts:
        out.append(["T"])
    if {"T1", "T2", "T3"} <= parts:
        # This alternative is appropriate only for the three-problem theory exams.
        if comp in {"ipho", "apho", "eupho"}:
            out.append(["T1", "T2", "T3"])
    return out


def record(comp, year, scope, maximum, scores, n, complete, sources, *, sets=None, note=None):
    labels = {"theory": ("이론 전체", "Complete theory exam"),
              "experiment": ("실험 전체", "Complete experimental exam"),
              "total": ("이론·실험 합계", "Theory and experiment total"),
              "round": ("혼합 문제지 전체", "Complete mixed paper")}
    ko, en = labels[scope]
    result = {"id": f"{comp}-{year}-{scope}", "year": year, "scope": scope,
              "label": {"ko": ko, "en": en}, "max": maximum,
              "scores": sorted(scores), "complete": bool(complete), "participants": n,
              "population": "individual", "awardScope": scope in {"total", "round"},
              "sources": sources}
    if sets:
        result["taskSets"] = sets
    if note:
        result["note"] = note
    assert all(isinstance(x, (float, int)) and 0 <= x <= maximum for x in scores), result["id"]
    assert not complete or len(scores) == n, result["id"]
    return result


def components(comp, year, theory=30, experiment=20):
    return [{"id": "theory", "label": {"ko": "이론 전체", "en": "Complete theory"},
             "max": theory, "taskSets": paper_sets(comp, year)},
            {"id": "experiment", "label": {"ko": "실험 전체", "en": "Complete experiment"},
             "max": experiment, **({"taskSets": EXPERIMENT_SETS[comp][year]}
                                     if year in EXPERIMENT_SETS.get(comp, {}) else {})}]


def xlsx_rows(data, sheet="xl/worksheets/sheet1.xml"):
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    z = zipfile.ZipFile(io.BytesIO(data))
    strings = ["".join(x.itertext()) for x in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("s:si", ns)]
    for row in ET.fromstring(z.read(sheet)).findall(".//s:row", ns):
        result = {}
        for cell in row.findall("s:c", ns):
            value = cell.find("s:v", ns)
            value = value.text if value is not None else ""
            if cell.get("t") == "s" and value:
                value = strings[int(value)]
            result[re.sub(r"\d", "", cell.get("r"))] = value
        yield result


def close(a, b, tol=0.111):
    return abs(a - b) <= tol


def pdf_rows(data, columns, xmin=0, extra=0):
    """Read numeric table columns at shared baselines, preserving duplicate scores.

    Coordinates are used for old tables whose ranking/name columns contain numbers.
    Column counts and arithmetic are validated by each contest-specific parser.
    """
    document = pymupdf.open(stream=data, filetype="pdf")
    for page in document:
        spans = [s for b in page.get_text("dict")["blocks"] if "lines" in b
                 for line in b["lines"] for s in line["spans"] if s["text"].strip()]
        groups = []
        for span in sorted(spans, key=lambda s: s["origin"][1]):
            if not groups or span["origin"][1] - groups[-1][0] > 3:
                groups.append([span["origin"][1], [span]])
            else:
                groups[-1][1].append(span)
        for _, spans in groups:
            spans.sort(key=lambda s: s["bbox"][0])
            raw = " ".join(s["text"] for s in spans)
            # Do not reject a contestant named Max/Maxim: only reject actual headings.
            if re.match(r"^\s*(?:MAX\s|Max Perfect|Max pts obtained|Name\s+Surname|Average\b|Median\b|solving rate|more than|Thresholds:|29\.6;|% from MAX|Best score|8% best|25% best|50% best|67% best|Difficulty rating)", raw):
                continue
            values = []
            for s in spans:
                if s["bbox"][0] >= xmin and re.fullmatch(r"[\d\s.,]+", s["text"]):
                    values.extend(float(v.replace(",", ".")) for v in s["text"].split())
                elif columns == 6 and (m := re.search(r"[A-Za-z]\s*(\d+\.\d{2})$", s["text"])):
                    # EuPhO 2026 row 83: a long surname touches the first score,
                    # forming a single text span ending in "Santiago6.10".
                    values.append(float(m[1]))
            if columns <= len(values) <= columns + extra:
                yield values[-columns:], raw


def observed_cutoffs(rows):
    # Rows are (theory, experiment, total, award).  HM is only imported from an
    # explicit published numeric threshold, never inferred from award membership.
    cuts = {}
    levels = {"G": 3, "S": 2, "B": 1, "H": 0, None: 0, "": 0}
    for award, key in [("G", "gold"), ("S", "silver"), ("B", "bronze")]:
        scores = [r[2] for r in rows if r[3] == award]
        if scores:
            floor = min(scores)
            # Guests, special awards, or parser uncertainty can make a medal
            # non-scalar. Do not promise that every score above this minimum
            # receives the same or a higher award when the published table
            # contains a lower/unclassified award at that score.
            if not any(levels.get(r[3], 0) < levels[award] and r[2] >= floor - 1e-9 for r in rows):
                cuts[key] = floor
    return cuts


def award_counts(rows):
    """Actual published overall G/S/B awards, not fixed medal percentages."""
    counts = Counter(r[3] for r in rows)
    return {name: counts[code] for code, name in [("G", "gold"), ("S", "silver"), ("B", "bronze")]}


def round_reference(item, counts, sources):
    """Project an edition's actual medal counts onto one complete-round score.

    This is explicitly a reference medal band, never an official separate-round
    award. Incomplete score distributions stay published-population references.
    Boundary ties share a band; no score is rescaled to a different examination.
    """
    assert item["scope"] in {"theory", "experiment"} and not item["awardScope"]
    keys = ["gold", "silver", "bronze"]
    assert set(counts) == set(keys) and all(type(counts[k]) is int and counts[k] >= 0 for k in keys)
    if not sources or not 0 < sum(counts.values()) <= len(item["scores"]):
        return False
    ordered = sorted(item["scores"], reverse=True)
    cuts, rank = {}, 0
    for key in keys:
        rank += counts[key]
        if counts[key]:
            cuts[key] = ordered[rank - 1]
    item["medalReference"] = {
        "basis": "round_rank", "counts": dict(counts), "cuts": cuts,
        "population": "complete" if item["complete"] else "published",
        "sources": list(sources),
    }
    return True


def eupho2020_award_counts(data, rows):
    """The 2020 PDF uses explicit award-section headings, not per-row labels.

    Match every extracted score vector back to the established numeric table.
    The HM heading also precedes anonymous non-award rows, so HM is not counted.
    """
    headings = {"gold medals": "G", "silver medals": "S", "bronze medals": "B", "honourable mentions": "H"}
    state, seen, found = None, [], []
    for page in pymupdf.open(stream=data, filetype="pdf"):
        for line in page.get_text(sort=True).splitlines():
            key = line.strip().lower()
            if key in headings:
                state = headings[key]
                seen.append(state)
            if line.strip().startswith(("MAX possible", "% from MAX")):
                continue
            numbers = re.findall(r"(?<![A-Za-z])\b\d+(?:[.,]\d+)?\b(?![A-Za-z])", line)
            if len(numbers) != 21:
                continue
            values = [float(x.replace(",", ".")) for x in numbers]
            theory, experiment, total = values[-1], values[-2], values[-3]
            if close(theory + experiment, total):
                found.append((theory, experiment, total, state))
    assert seen == ["G", "S", "B", "H"]
    assert sorted(r[:3] for r in found) == sorted(r[:3] for r in rows)
    result = award_counts(found)
    assert result == {"gold": 27, "silver": 49, "bronze": 60}
    return result


def ipho():
    raw = fetch(IPHO_RAW + "participants.csv", "ipho-participants.csv").decode("utf-8")
    timeline = csv.reader(io.StringIO(fetch(IPHO_RAW + "timeline.csv", "ipho-timeline.csv").decode("utf-8")))
    totals = {int(r[1]): int(r[7]) if r[7] else None for r in timeline}
    people = defaultdict(list)
    for r in csv.reader(io.StringIO(raw)):
        assert len(r) == 9
        people[int(r[0])].append(r)
    cutoffs = {}
    minutes = {}
    for year in range(1998, 2015):
        # Identical original minutes are mirrored by the named unofficial archive;
        # numeric thresholds were independently checked on the primary URL.
        primary = f"https://www.ipho-new.org/download/{377 + (year - 1998) * 3}/"
        data = fetch(f"https://ipho-unofficial.org/minutes/{year}.pdf", f"ipho-minutes-{year}.pdf")
        text = "\n".join(p.get_text() for p in pymupdf.open(stream=data, filetype="pdf"))
        vals = []
        for label in ["Gold Medal", "Silver Medal", "Bronze Medal", "Honou?rable Mention"]:
            m = re.search(label + r"\s*([0-9]+(?:[.,][0-9]+)?)\s*points", text, re.I)
            assert m, (year, label)
            vals.append(float(m[1].replace(",", ".")))
        cutoffs[year] = dict(zip(["gold", "silver", "bronze", "hm"], vals))
        minutes[year] = primary
    explicit = {
        2015: (429, [42.2, 33.0, 24.0, 18.0]),
        2016: (431, [39.8, 30.7, 22.7, 17.5]),
        2017: (434, [28.01, 21.30, 14.70, 11.12]),
        2021: (2063, [33.32, 23.45, 14.50, 9.15]),
        2022: (2069, [23.70, 16.05, 11.65, 7.15]),
        2023: (2072, [35.6, 25.2, 17.4, 13.4]),
        2024: (None, [33.92, 19.35, 12.49, 9.03]),
        2025: (None, [31.1, 22.9, 15.3, 11.3]),
    }
    for year, (download_id, vals) in explicit.items():
        cutoffs[year] = dict(zip(["gold", "silver", "bronze", "hm"], vals))
        minutes[year] = (f"https://www.ipho-new.org/download/{download_id}/" if download_id else
                         f"https://www.ipho-new.org/physics/wp-content/uploads/{year}/{'12' if year == 2024 else '08'}/Minutes-IPhO-{year}-{'Iran' if year == 2024 else 'France'}.pdf?x30394=")
    scored = {}
    full_sources = {}
    for year, rs in people.items():
        rows = [(float(r[5]), float(r[6]), float(r[7]), r[4]) for r in rs if all(r[i] for i in [5, 6, 7])]
        if rows:
            bad = [r for r in rows if not close(r[0] + r[1], r[2])]
            # One source transcription is inconsistent. Preserve its independently
            # published total, but omit both component values rather than repairing
            # either number without a primary original.
            assert not bad or (year == 2015 and bad == [(19.1, 13.5, 32.8, "B")]), (year, bad)
            scored[year] = rows
    for year, tcol, ecol, totalcol, awardcol, expected in [(2012, "AG", "AY", "AZ", "BA", 378), (2022, "BC", "BB", "BD", "BE", 368)]:
        url = f"https://olimpicos.net/files/ipho/IPhO_{year}_Results.xlsx"
        data = fetch(url, f"IPhO_{year}_Results.xlsx")
        rows = []
        for row in xlsx_rows(data):
            try:
                t, e, total = [round(float(row[c]), 4) for c in [tcol, ecol, totalcol]]
            except (ValueError, KeyError):
                continue
            assert close(t + e, total, .001), (year, t, e, total)
            award = {"Gold": "G", "Silver": "S", "Bronze": "B", "HM": "H"}.get(row[awardcol], row[awardcol])
            rows.append((t, e, total, award))
        assert len(rows) == expected == totals[year]
        assert sorted(r[:3] for r in rows if r[3] in "GSBH" and r[3]) == sorted(r[:3] for r in scored[year])
        scored[year] = rows
        full_sources[year] = source(url, f"IPhO {year} original results workbook, public anonymous non-award rows (archive mirror)", False)
    records = []
    for year in sorted(set(cutoffs) | set(scored)):
        rows = scored.get(year, [])
        score_sources = [source(f"https://ipho-unofficial.org/timeline/{year}/individual", f"IPhO {year} public results (unofficial)", False),
                         source(IPHO_RAW + "participants.csv", "IPhO unofficial source database (MIT; pinned revision)", False)] if rows else []
        if year in full_sources:
            score_sources = [full_sources[year]] + score_sources
        src = score_sources + [source(STATUTES, "IPhO statutes §5–6: exact paper scope, 30+20 points, non-award score privacy")]
        n = totals.get(year)
        note = {"ko": "비수상자의 점수는 공개되지 않아 공개 수상자 점수만 수록했습니다. 이론·실험 순위를 전체 참가자 백분위로 해석할 수 없습니다.",
                "en": "Non-award scores are private; this distribution contains published awardees only. Theory/experiment ranks are not full-field percentiles."}
        complete = year in full_sources
        if complete:
            note = {"ko": "공개 결과 통합문서의 익명 비수상자 행까지 포함한 전체 점수입니다. 원본 형식의 보존본을 사용하고 수상자 수와 총점을 교차 검증했습니다.",
                    "en": "The public results workbook includes anonymous non-award rows and the complete field. The preserved original-format mirror was cross-checked against award counts and component totals."}
        if rows:
            for scope, i, maximum in [("theory", 0, 30), ("experiment", 1, 20)]:
                component_rows = [r for r in rows if close(r[0] + r[1], r[2])]
                component_note = dict(note)
                if len(component_rows) != len(rows):
                    component_note = {"ko": note["ko"] + " 원문에서 합계와 0.2점 어긋나는 1명의 이론·실험 점수는 제외했습니다.",
                                      "en": note["en"] + " One inconsistent theory/experiment pair (0.2-point total discrepancy) is excluded."}
                item = record("ipho", year, scope, maximum, [r[i] for r in component_rows], n, complete,
                              src, sets=paper_sets("ipho", year) if scope == "theory" else EXPERIMENT_SETS["ipho"].get(year), note=component_note)
                count_url = minutes.get(year, "https://www.ipho-new.org/download/437/")
                # Every gold/silver/bronze winner is included in the public
                # database, even where non-award scores remain unpublished.
                counts = {name: sum(p[4] == code for p in people[year])
                          for code, name in [("G", "gold"), ("S", "silver"), ("B", "bronze")]}
                round_reference(item, counts, [
                    source(count_url, f"IPhO {year} official minutes: actual overall medal counts"),
                    source(IPHO_RAW + "participants.csv", "Complete public IPhO award listing (MIT; pinned revision)", False),
                ])
                records.append(item)
        total = record("ipho", year, "total", 50, [r[2] for r in rows], n, complete, src, note=note if rows else {
            "ko": "공식 회의록의 총점 수상 기준만 확인되었으며 점수 분포는 확보하지 못했습니다.",
            "en": "Published overall award thresholds only; no numeric score distribution has been recovered."})
        total["components"] = components("ipho", year)
        if year in cutoffs:
            total.update(medalCutoffs=cutoffs[year], cutoffKind="published", medalCutoffRule="gte")
            total["sources"].append(source(minutes[year], f"IPhO {year} official International Board minutes"))
            # The official cutoff makes every unpublished certificate-only total
            # strictly lower.  Require all named awardees to have all three scores.
            award_rows = [r for r in people.get(year, []) if r[4] in "GSBH"]
            if rows and len(rows) == len(award_rows) and all(all(r[i] for i in [5, 6, 7]) for r in award_rows):
                total["rankFloor"] = cutoffs[year]["hm"]
        elif rows:
            total.update(medalCutoffs=observed_cutoffs(rows), cutoffKind="observed", medalCutoffRule="gte")
        records.append(total)
    for item in records:
        if item["year"] == 2025:
            item["participantCountUncertain"] = True
            item["note"]["ko"] += " 참가 인원은 공식 회의록 415명과 주최 측 폐막 발표 406명으로 달라 전체 참가자 백분위를 표시하지 않습니다."
            item["note"]["en"] += " The official minutes report 415 entrants, whereas the organiser's closing announcement reports 406; no full-field percentile is inferred."
            item["sources"].append(source("https://fr.linkedin.com/posts/soci%C3%A9t%C3%A9-fran%C3%A7aise-de-physique_la-c%C3%A9r%C3%A9monie-de-cl%C3%B4ture-des-olympiades-activity-7354442364045651969-Ys2e", "Organiser's closing announcement: 406 contestants"))
    return {"records": records, "coverage": {
        "checked": CHECKED, "scoreYears": sorted(scored), "publishedCutoffYears": sorted(cutoffs),
        "sourceRevision": IPHO_COMMIT, "completeScoreYears": sorted(full_sources),
        "limitations": {"ko": "1967–2026 공개 데이터베이스 전체를 점검했습니다. 비공식 데이터베이스의 9개 점수 연도 중 2012·2022년은 익명 비수상자 행이 포함된 공개 통합문서로 보완했습니다. 나머지는 수상자만 있습니다. 2020은 별도 IDPhO이므로 IPhO로 합치지 않았습니다.",
                        "en": "The entire 1967–2026 database was inspected. Of its nine scored editions, 2012 and 2022 were supplemented by public workbooks including anonymous non-award scores. Other editions remain awardees-only. 2020 IDPhO is separate and not merged into IPhO."},
        "medalReferenceYears": sorted(scored),
        "medalReferenceMethod": "Actual overall G/S/B award counts projected onto each same-round score ranking; boundary ties included. Component references are not official medals.",
        "sources": [source("https://ipho-unofficial.org/", "IPhO unofficial archive requested by the user", False),
                    source("https://www.ipho-new.org/documentations/", "Official IPhO minutes archive")]}}


EUPHO = {
    2017: ("https://eupho.ee/wp-content/uploads/2020/07/1stEuPhO_results.pdf", 8, 275, 0, 91),
    2018: ("https://eupho.ee/wp-content/uploads/2020/07/eupho18-results.pdf", 8, 225, 0, 115),
    2020: ("https://eupho.ee/wp-content/uploads/2020/07/EuPhO-2020-results.pdf", 21, 225, 0, 260),
    2021: ("https://eupho.ee/wp-content/uploads/2021/06/EuPhO2021-results.pdf", 8, 0, 1, 219),
    2022: ("https://eupho.ee/wp-content/uploads/2022/05/EuPhO2022-awards.pdf", 5, 400, 0, 182),
    2023: ("https://eupho.ee/wp-content/uploads/2023/06/EuPhO23-results.pdf", 24, 0, 0, 176),
    2024: ("https://eupho.ee/wp-content/uploads/2024/07/EuPhO-2024-results-resultsforweb.pdf", 19, 0, 0, 256),
    2025: ("https://eupho.ee/wp-content/uploads/2025/06/EuPhO_2025_results-3.pdf", 25, 0, 0, 189),
    2026: ("https://eupho.ee/wp-content/uploads/2026/06/EuPhO_2026_Results-1.pdf", 6, 0, 0, 199),
}


def eupho():
    records = []
    for year, (url, columns, xmin, extra, n) in EUPHO.items():
        data = fetch(url, url.rsplit("/", 1)[1])
        rows = []
        for v, raw in pdf_rows(data, columns, xmin, extra):
            if year in [2017, 2018]:
                t, e, total = v[3], v[6], v[7]
                assert close(sum(v[:3]), t), (year, v)
            elif year == 2020:
                t, e, total = v[-1], v[-2], v[-3]
                assert close(sum([v[2], v[5], v[6]]), t), (year, v)
            elif year == 2021:
                t, e, total = v[-3:]
                assert close(sum(v[:3]), t), (year, v)
            elif year == 2022:
                t, e, total = round(sum(v[:3]), 2), v[3], v[4]
            elif year == 2023:
                t, e, total = round(sum([v[15], v[18], v[22]]), 2), round(v[4] + v[11], 2), v[-1]
            elif year == 2024:
                t, e, total = v[-2], v[8], v[-1]
            elif year == 2025:
                t, e, total = v[-3:]
                if raw.startswith("Name") or raw.startswith("Max pts"):
                    continue
                assert close(sum([v[2], v[5], v[9]]), t), (year, v)
            else:
                e, t, total = v[1], round(sum(v[2:5]), 2), v[5]
            assert close(t + e, total), (year, v, t, e, total)
            assert 0 <= t <= 30 and 0 <= e <= 20 and 0 <= total <= 50, (year, v)
            m = re.search(r"(?:^|\s)(Gold|Silver|Bronze|G|S|B)(?:\s|,|$)", raw)
            award = {"Gold": "G", "Silver": "S", "Bronze": "B"}.get(m[1], m[1]) if m else None
            rows.append((t, e, total, award))
        assert len(rows) == n, (year, len(rows), n)
        counts = None
        if year in {2017, 2018, 2023, 2024, 2026}:
            counts = award_counts(rows)
        elif year == 2020:
            counts = eupho2020_award_counts(data, rows)
        src = [source(url, f"EuPhO {year} official final score table"),
               source("https://eupho.ee/rules/", "EuPhO rules: theory 30, experiment 20; guest awards")]
        note = {"ko": "공개 결과표의 전체 참가자(초청 참가자 포함)를 비교합니다. 유럽 외 국가 참가자는 메달 기준 산정에서 제외되지만 기준 이상의 점수에는 메달을 받습니다.",
                "en": "Comparison includes all entrants in the published table, including guests. Non-European guest scores do not set medal thresholds, but scores above the thresholds receive medals."}
        if year in [2017, 2018, 2020]:
            note["ko"] += " 원문의 별도 비공식·초청 참가자도 이 분포에 포함되므로 공식 참가자만의 순위와 다릅니다."
            note["en"] += " The source's additional unofficial/guest entrants are retained, so this is not an official-entrants-only ranking."
        if year == 2024:
            note["ko"] += " 원문은 공식 참가자 185명, 전체 참가자 256명을 구분합니다."
            note["en"] += " The source distinguishes 185 official entrants and 256 total entrants."
        if year == 2020:
            note["ko"] += " 결과표에는 수치 행 260개(끝의 0점 행 5개)가 있으나 공식 소개는 257명을 기록합니다. 빈 행 여부를 구분할 수 없어 전체 참가자 백분위를 계산하지 않습니다."
            note["en"] += " The PDF has 260 numeric rows, including five trailing zero rows, while the official overview reports 257 entrants. Possible blank rows cannot be distinguished; no full-field percentile is inferred."
        if year == 2025:
            note["ko"] += " 특별상 표기가 일반 메달 표기를 대신한 행이 있어 단일 점수로 검증할 수 없는 수상 기준은 표시하지 않습니다."
            note["en"] += " Some special-prize labels replace ordinary medal labels; award tiers that cannot be verified as a single score threshold are withheld."
        for scope, maximum, idx in [("theory", 30, 0), ("experiment", 20, 1), ("total", 50, 2)]:
            item = record("eupho", year, scope, maximum, [r[idx] for r in rows], n if year != 2020 else None, year != 2020,
                          src, sets=paper_sets("eupho", year) if scope == "theory" else EXPERIMENT_SETS["eupho"].get(year) if scope == "experiment" else None, note=dict(note))
            if scope in {"theory", "experiment"} and counts:
                round_reference(item, counts, [source(url, f"EuPhO {year} official final table: actual G/S/B award counts")])
            if scope == "total":
                item["components"] = components("eupho", year)
                if year in [2024, 2026]:
                    vals = [29.6, 22.1, 16.7, 12.3] if year == 2024 else [25.2, 16.5, 11.4, 7.5]
                    item.update(medalCutoffs=dict(zip(["gold", "silver", "bronze", "hm"], vals)), cutoffKind="published", medalCutoffRule="gte")
                elif year not in {2020, 2021, 2022}:
                    cuts = observed_cutoffs(rows)
                    if cuts:
                        item.update(medalCutoffs=cuts, cutoffKind="observed", medalCutoffRule="gte")
            records.append(item)
    # The 2019 archive publishes awardees' totals but no component breakdown or
    # anonymous non-award score rows. Its population must remain incomplete.
    url = "https://eupho.ee/wp-content/uploads/2020/07/EuPhO2019_results.pdf"
    data = fetch(url, "EuPhO2019_results.pdf")
    rows = []
    for page in pymupdf.open(stream=data, filetype="pdf"):
        for line in page.get_text(sort=True).splitlines():
            m = re.search(r"(\d+(?:\.\d+)?)\s+(Gold Medal|Silver Medal|Bronze Medal|Honorable Mention)\b", line)
            if m:
                rows.append((None, None, float(m[1]), {"Gold Medal": "G", "Silver Medal": "S", "Bronze Medal": "B"}.get(m[2])))
    assert len(rows) > 80
    item = record("eupho", 2019, "total", 50, [r[2] for r in rows], None, False,
                  [source(url, "EuPhO 2019 official awardees' total scores"), source("https://eupho.ee/rules/", "EuPhO rules: 50-point total")],
                  note={"ko": "2019년 자료는 공개 수상자의 총점만 있습니다. 이론·실험 분리 순위나 전체 참가자 백분위를 계산할 수 없습니다.",
                        "en": "The 2019 source lists awardees' totals only; no theory/experiment rank or full-field percentile can be calculated."})
    item.update(components=components("eupho", 2019), medalCutoffs=observed_cutoffs(rows), cutoffKind="observed", medalCutoffRule="gte")
    records.append(item)
    return {"records": records, "coverage": {"checked": CHECKED, "scoreYears": list(range(2017, 2027)),
            "completeScoreYears": sorted(y for y in EUPHO if y != 2020), "limitations": {"ko": "2019년은 수상자 총점만 공개되었습니다. 2020년 수치 행과 참가 인원에 불일치가 있습니다. 2020–2022년 결과표의 색상만으로 메달 기준을 추정하지 않았습니다.",
            "en": "2019 provides awardee totals only. 2020 has a row-count/participant-count discrepancy. Medal thresholds were not inferred from colored rows in 2020–2022."},
            "medalReferenceYears": [2017, 2018, 2020, 2023, 2024, 2026],
            "medalReferenceOmitted": {"2019": "No separate theory/experiment scores.", "2021": "Ordinary medal categories are color-only; special-prize labels cannot supply G/S/B counts.", "2022": "Ordinary medal categories are color-only; exact published G/S/B counts were not independently verified.", "2025": "Best/BExp/BThe replace ordinary medal labels on three rows; complete G/S/B counts remain ambiguous."},
            "medalReferenceMethod": "Actual G/S/B award counts in the official table projected onto same-round score rankings, including source guest populations. These are reference bands, not official component awards.",
            "sources": [source("https://eupho.ee/archive/", "Official EuPhO archive covering every edition")]}}


NBPHO = {
    2020: ("https://nbpho.ee/wp-content/uploads/2020/05/NB_final_results_publish.pdf", 36.5),
    2021: ("https://nbpho.ee/wp-content/uploads/2021_problems/nbpho2021results_v2.pdf", 36),
    2022: ("https://nbpho.ee/wp-content/uploads/2022/NBPhO2022_final_results-1.pdf", 72),
    2023: ("https://nbpho.ee/wp-content/uploads/2023/04/NBPhO-2023-Final-Results-1.pdf", 72),
    2024: ("https://nbpho.ee/wp-content/uploads/2024/04/NBPhO-2024-final-results.pdf", 72),
    2025: ("https://nbpho.ee/wp-content/uploads/2026/03/NBPhO-2025-grading-Final-for-web.pdf", 72),
    2026: ("https://nbpho.ee/wp-content/uploads/2026/04/NBPhO-2026-results.pdf", 72),
}


def nbpho():
    records = []
    row_counts = {}
    for year, (url, maximum) in NBPHO.items():
        data = fetch(url, url.rsplit("/", 1)[1])
        rows = []
        for v, raw in pdf_rows(data, 3 if year == 2026 else 1, 0, 80):
            if len(re.findall(r"\b\d+(?:\.\d+)?\b", raw)) < 5:
                continue
            if re.match(r"^\s*(?:Max\s+(?:\d|points)|MAX\b|AVERAGE\b|Average\b|solvability\b|Name\b|Medal\b|%:)", raw):
                continue
            if re.search(r"\bTotal(?:\s+Aw\b|\s*$)", raw):
                continue
            if year == 2025 and v == [72] and not re.search(r"[A-Za-z]", raw):
                continue
            if year == 2026:
                if v == [72, 54, 18] or "Ukraine" in raw:
                    continue
                total, t, e = v
                assert close(t + e, total), (year, v)
            else:
                total, t, e = v[0], None, None
            if total > maximum:
                continue  # A repeated task-number heading, never a student score.
            m = re.search(r"(?:^|\s)(G|S|B)(?:\s|$)", raw)
            rows.append((t, e, total, m[1] if m else None))
        row_counts[year] = len(rows)
        if year in {2022, 2023, 2024, 2025}:
            assert len(rows) == {2022: 84, 2023: 88, 2024: 104, 2025: 105}[year], (year, len(rows))
        full = year in {2022, 2023, 2024, 2025}
        src = [source(url, f"NBPhO {year} official final results and printed score maxima")]
        note = {"ko": "이론·실험이 섞인 원문 문제지 전체의 총점입니다. 일부 이론 문제만 채점한 점수를 이 총점으로 환산하지 않습니다.",
                "en": "This is the complete mixed theory/experiment paper total. Scores on a theory subset must not be rescaled to this total."}
        if year in {2020, 2021}:
            note["ko"] += " 명단만 공개된 다른 참가자가 있어 전체 참가자 백분위는 제공하지 않습니다."
            note["en"] += " Other contestants are listed without scores; no full-field percentile is available."
        if year == 2020:
            note["ko"] += " 최종 성적표의 배점은 36.5점이며 원래 문제지의 36점과 다릅니다."
            note["en"] += " The final score table uses 36.5 points, differing from the original 36-point problem sheet."
        if year == 2021:
            src.append(source("https://nbpho.ee/wp-content/uploads/2021_problems/NBPhO_2021_with_solutions_and_grading_v4.pdf", "NBPhO 2021 official marking guide: 5+10+13+8 points"))
            note["ko"] += " 별도 순위의 초청 참가자 점수도 보존하여 공개 점수 위치는 공식 수상 자격 참가자의 순위와 다릅니다. 단일 총점으로 구분되지 않는 메달 기준은 표시하지 않습니다."
            note["en"] += " Out-of-ranking guest scores are retained; the published score position is not the official eligible-field rank. Non-scalar medal tiers are withheld."
        if year == 2024:
            src.append(source("https://www.spa.gov.sa/en/N2092443", "Participating Saudi delegation report: 104 entrants"))
        if year == 2026:
            note["ko"] += " 별도 장소·채점으로 실린 우크라이나 팀은 제외했습니다. 끝의 익명 0점 행이 실제 참가자인지 빈 행인지 확인되지 않아 전체 백분위를 제공하지 않습니다."
            note["en"] += " The separately administered/graded Ukrainian team is excluded. Trailing anonymous zero rows may include blank rows, so a full-field percentile is withheld."
        item = record("nbpho", year, "round", maximum, [r[2] for r in rows], len(rows) if full else None, full, src,
                      sets=[["E1", "E2", "T"]] if year >= 2022 else None, note=note)
        cuts = observed_cutoffs(rows)
        if cuts:
            item.update(medalCutoffs=cuts, cutoffKind="observed", medalCutoffRule="gte")
        if year == 2026:
            item["participantCountUncertain"] = True
            item["components"] = components("nbpho", year, 54, 18)
            # The T booklet contains experimental tasks and its runtime skip list
            # changes its grading scope, so theory-only automatic matching is unsafe.
            item["components"][0].pop("taskSets", None)
            item["components"][1]["taskSets"] = [["E1", "E2"]]
            for scope, idx, max_pts in [("theory", 0, 54), ("experiment", 1, 18)]:
                records.append(record("nbpho", year, scope, max_pts, [r[idx] for r in rows], None, False,
                                      src, sets=[["E1", "E2"]] if scope == "experiment" else None, note=dict(note)))
        records.append(item)
    return {"records": records, "coverage": {"checked": CHECKED, "scoreYears": sorted(NBPHO),
            "completeScoreYears": [2022, 2023, 2024, 2025], "publishedRows": row_counts,
            "limitations": {"ko": "2003–2019 공식 아카이브의 legacy ioc.ee 성적 링크는 HTTP·HTTPS 모두 시간 초과로 수집하지 못했습니다. 2020·2021 점수 없는 참가자, 2026 빈 행 가능성은 보완하지 않았습니다.",
                           "en": "The official 2003–2019 legacy ioc.ee score links timed out over HTTP and HTTPS. Missing 2020/2021 scores and possible 2026 blank rows were not imputed."},
            "sources": [source("https://nbpho.ee/archive/", "Official NBPhO results archive, 2003 onward")]}}


def rotated_apho_rows(data):
    for page in pymupdf.open(stream=data, filetype="pdf"):
        spans = [s for b in page.get_text("dict")["blocks"] if "lines" in b
                 for line in b["lines"] for s in line["spans"] if s["text"].strip()]
        groups = []
        for span in sorted(spans, key=lambda s: s["origin"][0]):
            if not groups or span["origin"][0] - groups[-1][0] > 2:
                groups.append([span["origin"][0], [span]])
            else:
                groups[-1][1].append(span)
        for _, spans in groups:
            spans.sort(key=lambda s: -s["bbox"][1])
            raw = " ".join(s["text"] for s in spans)
            numbers = [float(s["text"]) for s in spans if re.fullmatch(r"\d+(?:\.\d+)?", s["text"])]
            if len(numbers) == 4 and close(numbers[1] + numbers[2], numbers[3], .011):
                yield numbers[2], numbers[1], numbers[3], raw


def apho():
    records = []
    rules = "https://apho2019.asi.edu.au/about/about-apho/"
    groups = {}
    url = "https://apho2017.mipt.ru/results/"
    soup = BeautifulSoup(fetch(url, "apho2017.html"), "html.parser")
    rows = []
    for tr in soup.select("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.select("td")]
        if len(cells) != 10 or not cells[0].isdigit():
            continue
        t = round(sum(float(v) for v in cells[4:7]), 4)
        e, total = float(cells[7]), float(cells[8])
        assert close(t + e, total, .011), cells[0]
        rows.append((t, e, total, {"Gold": "G", "Silver": "S", "Bronze": "B"}.get(cells[9])))
    assert len(rows) == 167
    groups[2017] = (url, rows, 167, True)
    url = "https://www.apho2025.sa/media/4mkc32ln/apho_2025_نشر-النتائج-1.pdf"
    data = fetch(url, "apho-2025.pdf")
    rows = []
    for t, e, total, raw in rotated_apho_rows(data):
        # The official 2025 table consistently spells the category "Bronz".
        m = re.search(r"\b(Gold|Silver|Bronze|Bronz)\s*$", raw)
        rows.append((t, e, total, {"Gold": "G", "Silver": "S", "Bronze": "B", "Bronz": "B"}.get(m[1]) if m else None))
    assert len(rows) == 169
    groups[2025] = (url, rows, None, False)
    url = "https://apho2026.kr/en/APhO_2026_ranking.pdf"
    data = fetch(url, "APhO_2026_ranking.pdf")
    rows = []
    for v, raw in pdf_rows(data, 3, 0, 3):
        e, t, total = v
        if close(t + e, total, .011) and 0 <= e <= 20 and 0 <= t <= 30:
            m = re.search(r"\b(Gold|Silver|Bronze)\s*$", raw)
            rows.append((t, e, total, {"Gold": "G", "Silver": "S", "Bronze": "B"}.get(m[1]) if m else None))
    assert len(rows) == 161
    groups[2026] = (url, rows, 201, False)
    for year, (url, rows, n, complete) in groups.items():
        assert award_counts(rows) == {
            2017: {"gold": 19, "silver": 13, "bronze": 25},
            2025: {"gold": 28, "silver": 37, "bronze": 59},
            2026: {"gold": 29, "silver": 31, "bronze": 48},
        }[year]
        src = [source(url, f"APhO {year} official final score table"), source(rules, "APhO statutes §9: theory 30 + experiment 20")]
        note = {"ko": "이론 30점·실험 20점을 구분하여 비교합니다. 메달 수치는 실제 수상자의 최소 총점이며 공식 공표 커트라인과 구분합니다.",
                "en": "Theory (30) and experiment (20) are compared separately. Medal values are observed minimum awarded totals, not separately published official boundaries."}
        if not complete:
            note["ko"] += " 이 결과표는 수상자만 포함하여 전체 참가자 백분위를 제공하지 않습니다."
            note["en"] += " This table contains awardees only; no full-field percentile is available."
        if year == 2025:
            note["ko"] += " 발표 기관마다 전체 참가 인원이 달라 분모를 확정하지 않았습니다."
            note["en"] += " Published participant totals differ across delegations; the denominator is left unresolved."
        if year == 2026:
            src.append(source("https://www.jpho.jp/international/sanka/", "Japan's participating committee: 201 APhO 2026 entrants"))
        for scope, idx, maximum in [("theory", 0, 30), ("experiment", 1, 20), ("total", 2, 50)]:
            item = record("apho", year, scope, maximum, [r[idx] for r in rows], n, complete, src,
                          sets=paper_sets("apho", year) if scope == "theory" else EXPERIMENT_SETS["apho"].get(year) if scope == "experiment" else None,
                          note=dict(note))
            if year == 2025:
                item["participantCountUncertain"] = True
            if scope in {"theory", "experiment"}:
                round_reference(item, award_counts(rows), [source(url, f"APhO {year} official final table: actual G/S/B award counts")])
            if scope == "total":
                item.update(components=components("apho", year), medalCutoffs=observed_cutoffs(rows), cutoffKind="observed", medalCutoffRule="gte")
            records.append(item)
    return {"records": records, "coverage": {"checked": CHECKED, "scoreYears": sorted(groups), "completeScoreYears": [2017],
            "medalReferenceYears": sorted(groups),
            "medalReferenceMethod": "Actual G/S/B award counts from each official final table projected onto same-round score rankings; only the published score population is used for incomplete editions. Not official component awards.",
            "limitations": {"ko": "2017년은 익명 비수상자까지 포함합니다. 2025·2026년은 수상자 점수만 있습니다. 2019년 공식 PDF는 글자·열이 겹쳐 자동 추출 검증을 통과하지 못해 포함하지 않았습니다. 다른 연도의 수상자 수를 점수 분포로 환산하지 않았습니다.",
                           "en": "2017 includes anonymous non-award scores. 2025/2026 provide awardees only. The overlapping 2019 PDF failed extraction validation and is not imported. Award counts from other editions are not converted into score distributions."},
            "sources": [source("https://apho2019.asi.edu.au/2019-awards-list-2/", "Official 2019 result candidate excluded pending reliable extraction"),
                        source("https://www.apho2025.sa/results-and-questions/results/", "Official 2025 results"), source("https://apho2026.kr/en/sub2_4.html", "Official 2026 results")]}}


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"schema": 1, "checked": CHECKED, "competitions": {"ipho": ipho(), "eupho": eupho(), "nbpho": nbpho(), "apho": apho()}}
    (OUT / "physics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    references = [{"record": r["id"], "method": "same-round descending score at cumulative actual G/S/B award counts",
                   "scoreCount": len(r["scores"]), "counts": r["medalReference"]["counts"],
                   "cuts": r["medalReference"]["cuts"], "population": r["medalReference"]["population"],
                   "tieRule": "all scores equal to the boundary remain in the same reference band"}
                  for c in result["competitions"].values() for r in c["records"] if "medalReference" in r]
    (OUT / "physics-receipts.json").write_text(json.dumps({"checked": CHECKED, "sources": RECEIPTS, "medalReferences": references}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print({key: len(value["records"]) for key, value in result["competitions"].items()})

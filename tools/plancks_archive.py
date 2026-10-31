"""Collect unchanged published international PLANCKS finals and record their provenance."""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import pathlib
import sys

import pymupdf
import requests
import numpy as np
from pypdf import PdfReader, PdfWriter

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "pdfx" / "plancks"
REPORT = ROOT / "tools" / "plancks_archive_report.json"
UK = "https://plancks.uk/wp-content/uploads/2023/11/"
UK_INDEX = "https://plancks.uk/about/past-papers/"
RO_INDEX = "https://fizicieni.ro/?page=plancks"
NL_INDEX = "https://plancks2026.verenigingspin.nl/exams/"

SOURCES = []
for year in range(2014, 2020):
    name = "plancks-2019-problem-set.pdf" if year == 2019 else f"plancks{year}_problems.pdf"
    SOURCES.append(dict(year=year, kind="paper", url=UK + name, source_page=UK_INDEX))
    if year <= 2016:
        SOURCES.append(dict(year=year, kind="solution", url=UK + f"plancks{year}_solutions.pdf", source_page=UK_INDEX))
SOURCES.extend([
    dict(year=2020, kind="paper", url=UK + "plancks2020_questions.pdf", source_page=UK_INDEX),
    dict(year=2020, kind="solution", url=UK + "plancks2020_answerbooklet.pdf", source_page=UK_INDEX),
    dict(year=2021, kind="combined", url=UK + "plancks2021_problems_solutions.pdf", source_page=UK_INDEX),
    dict(year=2022, kind="paper", url="https://fizicieni.ro/pages/plancks/subiecte_plancks/PLANCKS2022_Problems.pdf", source_page=RO_INDEX),
    dict(year=2022, kind="combined", url="https://fizicieni.ro/pages/plancks/subiecte_plancks/PLANCKS2022_Problems_Solutions.pdf", source_page=RO_INDEX),
    dict(year=2023, kind="combined", url=UK + "solutions.pdf", source_page=UK_INDEX),
    dict(year=2024, kind="combined", url="https://plancks.uk/wp-content/uploads/2025/01/plancks_dublin_2024_exam_solutions.pdf", source_page=UK_INDEX),
    dict(year=2025, kind="combined", url="https://estudiantes.rsef.es/PLANCKS25/PLANCKS25_Soluciones.pdf", source_page="https://estudiantes.rsef.es/PLANCKS25/"),
    dict(year=2026, kind="paper", url="https://plancks2026.verenigingspin.nl/wp-content/uploads/2026/10/PLANCKS-2026-Eindhoven-Questions.pdf", source_page=NL_INDEX),
    dict(year=2026, kind="solution", url="https://plancks2026.verenigingspin.nl/wp-content/uploads/2026/10/PLANCKS-2026-Eindhoven-Answers.pdf", source_page=NL_INDEX),
])

# One-based source pages; all mathematics, figures and original page furniture are preserved.
PROBLEM_PAGES = {
    2021: [(1, 4), (9, 13), (20, 22), (25, 27), (32, 34), (38, 40), (43, 45), (52, 54), (58, 59), (62, 67), (77, 78), (81, 84)],
    2023: [(1, 3), (8, 8), (11, 12), (17, 17), (23, 23), (27, 28), (34, 35), (40, 41), (45, 45), (50, 50)],
    2024: [(1, 3), (6, 7), (11, 11), (14, 14), (17, 17), (20, 22), (25, 25), (27, 27), (31, 31), (35, 35), (38, 38)],
    2025: [(1, 3), (7, 7), (10, 10), (14, 15), (17, 18), (21, 21), (24, 25), (28, 29), (34, 35)],
}


def extract_clean_papers(report):
    """Run only after the PDF operation marker; never alter the original source/solution PDFs."""
    records = []
    for year, ranges in PROBLEM_PAGES.items():
        source_path = OUT / f"PLANCKS_{year}_TS.pdf"
        source = pymupdf.open(source_path)
        pages = [page for first, last in ranges for page in range(first, last + 1)]
        output = OUT / f"PLANCKS_{year}_T_EN.pdf"
        # A fresh document prevents removed solution pages from surviving through the original
        # structure tree, outline destinations or annotations. Original visible page streams stay.
        writer = PdfWriter()
        reader = PdfReader(source_path)
        for number in pages:
            writer.add_page(reader.pages[number - 1], excluded_keys=("/Annots", "/B", "/StructParents"))
        writer.add_metadata({"/Title": f"PLANCKS {year} — original problem pages", "/Subject": "Original problem pages excerpted from the published combined booklet; source pages recorded in tools/plancks_archive_report.json."})
        writer.write(output)
        clean = pymupdf.open(output)
        redactions = []
        if year == 2025:
            page = clean[pages.index(25)]
            matches = page.search_for("Solution")
            if len(matches) != 1 or not 300 < matches[0].y0 < 340:
                raise ValueError("Unexpected source layout on the mixed question/solution page")
            rect = pymupdf.Rect(0, matches[0].y0 - 4, page.rect.width, page.rect.height)
            page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions(images=2, graphics=2, text=0)
            redactions.append(dict(source_page=25, rect=list(rect), reason="The original page has the end of question 7 above the beginning of its worked solution; only the solution area is removed."))
        if redactions:
            temporary = output.with_suffix(".tmp.pdf")
            clean.save(temporary, garbage=0, deflate=True)
            clean.close()
            temporary.replace(output)
        # A re-opened PDF must retain all original text and exact rendered pixels on unchanged pages.
        check = pymupdf.open(output)
        text_differences, render_differences = [], []
        for index, number in enumerate(pages):
            if year == 2025 and number == 25:
                assert not check[index].search_for("Solution")
                assert "diameter of the star" in check[index].get_text()
                continue
            if check[index].get_text() != source[number - 1].get_text():
                text_differences.append(number)
            a = np.frombuffer(check[index].get_pixmap(matrix=pymupdf.Matrix(0.6, 0.6)).samples, dtype=np.uint8).astype(np.int16)
            b = np.frombuffer(source[number - 1].get_pixmap(matrix=pymupdf.Matrix(0.6, 0.6)).samples, dtype=np.uint8).astype(np.int16)
            delta = np.abs(a - b)
            # PDF serializer numeric precision can change isolated antialias values by one RGB unit.
            assert delta.max() <= 3 and delta.mean() < 0.01, (year, number, int(delta.max()), float(delta.mean()))
            if delta.max():
                render_differences.append(dict(source_page=number, max_channel_difference=int(delta.max()), mean_channel_difference=float(delta.mean())))
        content = output.read_bytes()
        records.append(dict(year=year, file=output.name, source_file=source_path.name,
                            source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(), source_pages=pages,
                            redactions=redactions, pages=len(check), bytes=len(content), sha256=hashlib.sha256(content).hexdigest(),
                            accessibility_text_differs_on_source_pages=text_differences,
                            rendering_roundoff=render_differences,
                            validation="Reopened every PDF; rendered pages equal to source within <=3 RGB units and mean difference <0.01/255 for unchanged pages (serializer antialias roundoff). Original scanned pages remain original images. The document-wide tagged accessibility tree is omitted so deleted solutions are not retained invisibly; source-page text differences are recorded separately. The sole mixed page retains the complete question and removes its solution area."))
    report["extractions"] = records
    return report


def collect(source):
    source = dict(source)
    filename = f"PLANCKS_{source['year']}_{'T_EN' if source['kind'] == 'paper' else 'TS'}.pdf"
    path = OUT / filename
    if not path.exists():
        response = requests.get(source["url"], timeout=70)
        response.raise_for_status()
        if not response.content.startswith(b"%PDF-"):
            raise ValueError(f"Not a PDF: {source['url']}")
        path.write_bytes(response.content)
        source["final_url"] = response.url
    data = path.read_bytes()
    doc = pymupdf.open(stream=data, filetype="pdf")
    if not doc.page_count or doc.needs_pass:
        raise ValueError(f"Unreadable document: {filename}")
    source.update(file=filename, bytes=len(data), pages=doc.page_count,
                  sha256=hashlib.sha256(data).hexdigest(), title=doc.metadata.get("title"),
                  first_page_text=doc[0].get_text()[:2500])
    for page in doc:
        if page.rect.width < 100 or page.rect.height < 100:
            raise ValueError(f"Implausible page geometry: {filename}")
    return source


def write_manifest(report):
    if len(report.get("extractions", [])) != 4:
        raise ValueError("The four clean problem-paper extractions must be validated first")
    locations = {
        2014: ("Utrecht, Netherlands", "네덜란드 · 위트레흐트", "nl"),
        2015: ("Leiden, Netherlands", "네덜란드 · 레이던", "nl"),
        2016: ("Bucharest, Romania", "루마니아 · 부쿠레슈티", "ro"),
        2017: ("Graz, Austria", "오스트리아 · 그라츠", "at"),
        2018: ("Zagreb, Croatia", "크로아티아 · 자그레브", "hr"),
        2019: ("Odense, Denmark", "덴마크 · 오덴세", "dk"),
        2020: ("London, United Kingdom (online)", "영국 · 런던 (온라인)", "gb"),
        2021: ("Porto, Portugal (online)", "포르투갈 · 포르투 (온라인)", "pt"),
        2022: ("Munich, Germany (hybrid)", "독일 · 뮌헨 (대면·온라인)", "de"),
        2023: ("Milan, Italy", "이탈리아 · 밀라노", "it"),
        2024: ("Dublin, Ireland", "아일랜드 · 더블린", "ie"),
        2025: ("Barcelona, Spain", "스페인 · 바르셀로나", "es"),
        2026: ("Eindhoven, Netherlands", "네덜란드 · 에인트호번", "nl"),
    }
    counts = {year: 10 for year in locations}
    counts.update({2020: 9, 2021: 12, 2025: 9, 2026: 9})
    rules = "https://iaps.info/wp-content/uploads/2021/01/PLANCKS-General-Rules-EGM-2020.pdf"
    manifest = dict(comp="plancks", prefix="PLANCKS", abbr="PLANCKS",
                    full={"ko": "국제 대학생 이론물리 경시대회", "en": "Physics League Across Numerous Countries for Kick-ass Students"},
                    since=2014, scope={"ko": "국제 · 학부·석사", "en": "International · bachelor and master students"}, plain=True, rounds=False,
                    officialWebsite="https://iaps.info/events/plancks/", source_page=NL_INDEX,
                    checked="2026-10-30", archive_scope="international_finals",
                    about="Published international PLANCKS finals, 2014–2026 inclusive. National preliminaries are excluded. Original English PDFs are kept locally; four combined booklets have clean problem-page extracts with page-level provenance. Official solutions were found for ten finals; 2017–2019 solutions were not found. The 2021 Porto online final used sixteen hours and twelve problems, unlike the usual four-hour format.",
                    resourceNote={"ko": "2014~2026년 국제 결선 13개년의 영어 원문 문제지와 확보한 공식 해설을 모았습니다. 국가별 예선은 포함하지 않습니다. 2017~2019년 공식 해설은 확인되지 않았습니다. 보통 4시간이며, 2021년 포르투 온라인 결선은 원문 규정에 따라 12문항·16시간입니다.",
                                  "en": "All thirteen international finals from 2014–2026, with original English papers and available official solutions. National preliminaries are excluded. No official solutions were found for 2017–2019. The usual duration is four hours; the 2021 Porto online final had twelve problems and sixteen hours."},
                    resources=[
                        dict(label={"ko": "IAPS 공식 일반 규정", "en": "IAPS official general rules"}, url=rules, kind="pdf"),
                    ], sources=[UK_INDEX, RO_INDEX, NL_INDEX, "https://estudiantes.rsef.es/PLANCKS25/Exams", rules], years=[])
    for year in sorted(locations, reverse=True):
        records = [r for r in report["sources"] if r["year"] == year]
        extraction = next((r for r in report["extractions"] if r["year"] == year), None)
        paper = next((r for r in records if r["kind"] == "paper"), None) or next(r for r in records if r["kind"] == "combined")
        solution = next((r for r in records if r["kind"] in ("solution", "combined")), None)
        host_en, host_ko, cc = locations[year]
        note_ko = f"국제 결선 · {counts[year]}문항. "
        note_en = f"International final · {counts[year]} problems. "
        if extraction:
            note_ko += "문제·해설 합본에서 원문 문제 페이지만 발췌했습니다. 원본 합본은 공식 해설에서 볼 수 있습니다. "
            note_en += "Original problem pages extracted from the published combined booklet; the original combined document is retained under solutions. "
        if year == 2021:
            note_ko += "온라인 특별 규정: 16시간, 자료 참조 허용. 일반적인 4시간 대면 결선과 구분합니다."
            note_en += "Online exception: sixteen hours, with books and sources permitted. This is separate from the usual four-hour in-person format."
        elif year in (2017, 2018, 2019):
            note_ko += "공식 해설 파일은 확보하지 못했습니다."
            note_en += "No published official solution PDF was found."
        elif year == 2020:
            note_ko += "공식 풀이 시간은 4시간이며, 당시 온라인 행사에는 선택적 30분 점심 휴식과 별도 답안 업로드 시간이 있었습니다."
            note_en += "Four hours of official working time; the online event also offered an optional thirty-minute lunch break and a separate answer-upload period."
        files = []
        filename = f"PLANCKS_{year}_T_EN.pdf"
        data = (OUT / filename).read_bytes()
        files.append(dict(file=filename, local=f"pdfx/plancks/{filename}", part="T", kind="paper", lang="EN", url=paper["url"],
                          source_page=paper["source_page"], pages=len(pymupdf.open(stream=data, filetype="pdf")), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                          contains_solutions=False, **({"derived_from": extraction["source_file"], "source_pages": extraction["source_pages"], "redactions": extraction["redactions"]} if extraction else {})))
        if solution:
            files.append({k: solution[k] for k in ("file", "url", "source_page", "pages", "bytes", "sha256")})
            files[-1].update(local=f"pdfx/plancks/{solution['file']}", part="T", kind="solution", lang="EN", contains_solutions=solution["kind"] == "combined")
        timing = dict(minutes=960 if year == 2021 else 240, source=paper["url"] if year in (2017, 2021, 2022, 2024) else rules,
                      basis="published paper" if year in (2017, 2021, 2022, 2024) else "IAPS general rule 4.1.2 (four hours)")
        if year == 2021:
            timing.update(source_page=2, quote="You have 16 hours to submit this problem.", archive_context="The UK official archive separately labels this Porto international final and the Kent national preliminary; this is the twelve-problem Porto file, not the Kent preliminary.")
        if year == 2020:
            timing.update(source="https://plancksprelims.wixsite.com/ediplancks/format", basis="Organiser's London2020 international online final format page: four hours plus optional lunch break")
        if year == 2026:
            timing.update(source="https://plancks2026.verenigingspin.nl/schedule/", basis="Saturday23May official competition schedule10:00–14:00")
        manifest["years"].append(dict(y=year, host={"ko": host_ko, "en": host_en}, cc=cc, source_page=paper["source_page"],
                                      minutes=timing["minutes"], problem_count=counts[year], online=year in (2020, 2021),
                                      timing_evidence=timing, note={"ko": note_ko.strip(), "en": note_en.strip()},
                                      problems=[dict(id="T", title=f"International final — full paper ({counts[year]} problems)")], files=files))
    path = ROOT / "tools" / "theory" / "plancks.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["logo"] = dict(file="logo/plancks.svg", source="https://plancks2026.verenigingspin.nl/wp-content/uploads/2026/02/PLANCKS-logo-light-background.svg", source_page="https://plancks2026.verenigingspin.nl/branding/", note="Unchanged official vector asset; site may choose light/dark variants.")
    return manifest


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        records = sorted(pool.map(collect, SOURCES), key=lambda r: (r["year"], r["kind"]))
    report = dict(checked="2026-10-30", scope="International finals only; no national preliminaries.",
                  sources=records, missing_solutions=[2017, 2018, 2019],
                  archive_pages=[UK_INDEX, RO_INDEX, NL_INDEX],
                  known_source_errors=["The Eindhoven archive labels one 2024 row with the 2025 PDF; the 2024 source here is the correctly identified Dublin PDF from the UK archive."])
    if "--extract" in sys.argv:
        report = extract_clean_papers(report)
    elif REPORT.exists():
        prior = json.loads(REPORT.read_text(encoding="utf-8"))
        if "extractions" in prior:
            report["extractions"] = prior["extractions"]
    if report.get("extractions"):
        write_manifest(report)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for r in records:
        print(f"{r['file']}: {r['pages']} pages, {r['bytes']} bytes, {r['sha256'][:12]}")


if __name__ == "__main__":
    main()

"""Import public, official non-physics historical score distributions.

Run from any directory: python tools/results/import_other.py [--refresh]
Dependencies: requests, beautifulsoup4, pymupdf. Network originals are cached
under tmp/results-other; only anonymous numeric scores enter the public data.
"""
from __future__ import annotations

import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CACHE = ROOT / 'tmp' / 'results-other'
CACHE.mkdir(parents=True, exist_ok=True)
REFRESH = '--refresh' in sys.argv
RECEIPTS: dict[str, dict] = {}
LOCK = threading.Lock()


def fetch(url: str) -> bytes:
    target = CACHE / (hashlib.sha256(url.encode()).hexdigest()[:24] + '.bin')
    if not target.exists() or REFRESH:
        for attempt in range(3):
            try:
                response = requests.get(url, timeout=45, headers={'Accept-Encoding': 'identity', 'User-Agent': 'Mozilla/5.0'})
                response.raise_for_status()
                target.write_bytes(response.content)
                break
            except requests.RequestException:
                if attempt == 2:
                    # Windows' native certificate store can verify some host
                    # chains missing from Python's bundled CA set. Curl keeps
                    # normal HTTPS verification; no insecure flags are used.
                    curl = shutil.which('curl.exe') or shutil.which('curl')
                    if not curl:
                        raise
                    result = subprocess.run([curl, '-fsSL', '--max-time', '45', '-A', 'Mozilla/5.0', url],
                                            check=True, capture_output=True)
                    target.write_bytes(result.stdout)
    content = target.read_bytes()
    with LOCK:
        RECEIPTS[url] = {'url': url, 'bytes': len(content),
                         'sha256': hashlib.sha256(content).hexdigest()}
    return content


def soup(url: str) -> BeautifulSoup:
    return BeautifulSoup(fetch(url), 'html.parser')


def pdf(url: str):
    document = pymupdf.open(stream=fetch(url), filetype='pdf')
    RECEIPTS[url]['pages'] = len(document)
    return document


def manifest(comp: str) -> dict:
    return json.loads((ROOT / 'tools' / 'theory' / (comp + '.json')).read_text(encoding='utf-8'))


def whole_paper_sets(comp: str, year: int) -> list[list[str]]:
    """A T file denotes the complete theoretical paper in these manifests."""
    annual = next((item for item in manifest(comp)['years'] if item['y'] == year), None)
    if annual and any(item.get('part') == 'T' and item.get('kind') == 'paper' for item in annual['files']):
        return [['T']]
    return []


def source(url: str, title: str) -> dict:
    return {'url': url, 'title': title, 'official': True}


def number(text: str):
    text = text.strip().replace('\xa0', '')
    return float(text) if re.fullmatch(r'-?\d+(?:\.\d+)?', text) else None


def compact(value: float):
    return int(value) if value == int(value) else value


def imo():
    overview_url = 'https://www.imo-official.org/results/'
    overview = soup(overview_url)
    editions = []
    for row in overview.select('table tbody tr'):
        cells = row.find_all('td', recursive=False)
        if not cells or not re.fullmatch(r'\d{4}', cells[0].get_text(strip=True)):
            continue
        year = int(cells[0].get_text(strip=True))
        maximum = number(cells[9].get_text(strip=True))
        if maximum is None:
            continue
        editions.append({'year': year, 'participants': int(cells[3].get_text(strip=True)),
                         'max': compact(maximum), 'cuts': {
                             key: compact(value) for key, cell in zip(['gold', 'silver', 'bronze'], cells[11:14])
                             if (value := number(cell.get_text(strip=True))) is not None},
                         'url': urljoin(overview_url, cells[0].find('a')['href']),
                         'quality': [cell.get_text(strip=True) for cell in cells[14:]]})

    def one(edition):
        page = soup(edition['url'])
        totals, rows, invalid = [], [], 0
        for row in page.select('table tbody tr'):
            cells = row.find_all('td', recursive=False)
            if len(cells) < 5:
                continue
            # Some editions insert a special-prize column before Points.
            # Select the semantic total cell rather than a positional index.
            total_cell = row.select_one('.data-table__total-cell')
            total, rank = number(total_cell.get_text(strip=True)) if total_cell else None, number(cells[2].get_text(strip=True))
            if total is None:
                invalid += 1
                continue
            assert 0 <= total <= edition['max'], (edition['year'], total)
            totals.append(compact(total)); rows.append((total, rank))
        assert totals, edition['year']
        inconsistencies = sum(rank is not None and 1 + sum(score > total for score in totals) != rank for total, rank in rows)
        complete = len(totals) == edition['participants'] and invalid == 0
        note_en = 'Hypothetical score position among the published totals; this is not an official participation result. Only the entire two-day paper is comparable. Honourable mentions cannot be determined from the total alone.'
        note_ko = '공개 총점 분포에 넣어 계산한 가상 위치이며 실제 참가 성적이 아닙니다. 이틀간의 전체 문제를 모두 푼 총점만 비교합니다. 총점만으로 장려상을 판정하지 않습니다.'
        if inconsistencies:
            note_en += ' The source has historical rank/score inconsistencies; positions are computed from published numeric totals, not copied ranks.'
            note_ko += ' 원문 순위와 점수 사이에 불일치가 있어, 표기 순위 대신 공개 숫자 점수로 위치를 계산합니다.'
        if not complete:
            note_en += ' The published numeric score distribution is incomplete.'
            note_ko += ' 공개 숫자 점수 분포가 완전하지 않습니다.'
        record = {'id': f'imo-{edition["year"]}-total', 'year': edition['year'], 'scope': 'total',
                  'label': {'ko': '전체 대회 · 두 날 합계', 'en': 'Complete competition · both days'},
                  'max': edition['max'], 'scores': sorted(totals, reverse=True),
                  'complete': complete, 'participants': edition['participants'], 'population': 'individual',
                  'medalCutoffs': edition['cuts'], 'cutoffKind': 'published', 'awardScope': True,
                  'sources': [source(overview_url, 'IMO official edition statistics and medal cutoffs'),
                              source(edition['url'], f'IMO {edition["year"]} official individual results')],
                  'note': {'ko': note_ko, 'en': note_en}}
        sets = whole_paper_sets('imo', edition['year'])
        if sets:
            record['taskSets'] = sets
        RECEIPTS[edition['url']].update({'year': edition['year'], 'scoreRows': len(totals),
                                         'participants': edition['participants'], 'missingScores': invalid,
                                         'publishedRankInconsistencies': inconsistencies,
                                         'overviewQualityFlags': edition['quality']})
        print('IMO', edition['year'], len(totals), 'complete' if complete else 'incomplete', flush=True)
        return record

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        records = list(executor.map(one, editions))
    return {'records': sorted(records, key=lambda record: record['year'], reverse=True)}


def observed_cutoffs(rows: list[tuple[float, str]]) -> dict:
    rank = {'Gold': 4, 'Silver': 3, 'Bronze': 2, 'HM': 1}
    cuts = {}
    for award, name in [('gold', 'Gold'), ('silver', 'Silver'), ('bronze', 'Bronze'), ('hm', 'HM')]:
        awarded = [score for score, label in rows if label == name]
        if not awarded:
            continue
        threshold = min(awarded)
        # An observed minimum is not a universal score boundary when other
        # contestants above it receive a lower award (e.g. problem-based HMs).
        if any(score >= threshold and rank.get(label, 0) < rank[name] for score, label in rows):
            continue
        cuts[award] = compact(threshold)
    return cuts


def ioaa_2025():
    url = 'https://ioaa2025.in/wp-content/uploads/2025/12/IOAA2025-Final-Marklist.pdf'
    document = pdf(url)
    theory, overall = {}, {}
    for page in document:
        text = page.get_text(sort=True)
        is_theory, is_overall = 'Theoretical Component' in text, 'Overall Results' in text
        for line in text.splitlines():
            fields = line.split()
            if not fields or not re.fullmatch(r'[A-Z]{3}-S\d+', fields[0]):
                continue
            if is_theory:
                values = [float(value) for value in fields[1:]]
                assert len(values) == 13, fields
                assert abs(sum(values[:-1]) - values[-1]) < .001, fields
                assert fields[0] not in theory, fields[0]
                theory[fields[0]] = values
            elif is_overall:
                values = [float(value) for value in fields[1:6]]
                assert len(values) == 5, fields
                assert abs(values[1] + values[2] - values[3]) < .001, fields
                assert abs(values[0] + values[3] - values[4]) < .001, fields
                assert fields[0] not in overall, fields[0]
                overall[fields[0]] = (values, fields[6] if len(fields) == 7 else '')
    assert set(theory) == set(overall) and len(theory) > 200
    for code, values in theory.items():
        assert values[-1] == overall[code][0][0], code
    participants = len(overall)
    sources = [source(url, 'IOAA 2025 official final component marklist'),
               source('https://ioaa2025.in/ioaa-2025-final-marklist/', 'IOAA 2025 organiser: final marklist')]
    common = {'year': 2025, 'complete': True, 'participants': participants,
              'population': 'individual', 'sources': sources}
    theory_record = {**common, 'id': 'ioaa-2025-theory', 'scope': 'theory',
                     'label': {'ko': '이론 전체', 'en': 'Complete theory round'}, 'max': 300,
                     'taskSets': whole_paper_sets('ioaa', 2025),
                     'scores': sorted((compact(value[-1]) for value in theory.values()), reverse=True),
                     'awardScope': False,
                     'note': {'ko': '이론 12문제 전체의 원점수 분포입니다. 이론만의 메달 기준은 아니며 총점 메달과 비교하지 않습니다.',
                              'en': 'Raw scores for all twelve theory problems. These give theory-only score positions, not medal estimates from combined totals.'}}
    practical = {**common, 'id': 'ioaa-2025-practical', 'scope': 'experiment',
                 'label': {'ko': '실기 전체 · 자료 분석 + 관측', 'en': 'Complete practical · data analysis + observation'},
                 'max': 300, 'scores': sorted((compact(value[0][3]) for value in overall.values()), reverse=True),
                 'awardScope': False,
                 'note': {'ko': '자료 분석 150점과 관측 150점을 합한 실기 전체입니다. 일부 관측 문제만의 점수와 비교하지 않습니다.',
                          'en': 'All data analysis (150) and observation (150) combined; a single observation task is not comparable.'}}
    total = {**common, 'id': 'ioaa-2025-total', 'scope': 'total',
             'label': {'ko': '전체 대회 · 이론 + 실기', 'en': 'Complete competition · theory + practical'},
             'max': 600, 'scores': sorted((compact(value[0][4]) for value in overall.values()), reverse=True),
             'medalCutoffs': observed_cutoffs([(value[0][4], value[1]) for value in overall.values()]),
             'cutoffKind': 'observed', 'awardScope': True,
             'components': [{'id': 'theory', 'label': theory_record['label'], 'max': 300, 'taskSets': theory_record['taskSets']},
                            {'id': 'practical', 'label': practical['label'], 'max': 300}],
             'note': {'ko': '이론 300점과 실기 300점을 모두 합한 총점만 메달 분포와 비교합니다. 기준은 공식 표에 기재된 금·은·동 수상 등급의 최저 관측 점수입니다. 장려상은 총점만으로 결정되지 않아 기준을 제시하지 않습니다.',
                      'en': 'Only theory (300) plus every practical component (300) is comparable to this total. Medal cutoffs are observed gold/silver/bronze minima in the official marklist. Honourable mentions are not determined by total alone and have no scalar cutoff here.'}}
    RECEIPTS[url].update({'year': 2025, 'theoryRows': len(theory), 'overallRows': participants,
                         'crossChecks': ['unique and identical contestant-code populations', 'all twelve theory question sums',
                                         'theory totals agree in both tables', 'data analysis + observation = practical',
                                         'theory + practical = total', 'gold/silver/bronze observed minima are monotone in the complete table'],
                         'hmCutoffOmitted': 'Twenty non-HM contestants score at or above the lowest HM total; HMs are not a total-score threshold.'})
    return [theory_record, practical, total]


def icho_2023():
    url = 'https://science.olympiad.ch/fileadmin/user_upload/Archiv/Public/Reports_Intl_Olympiads_in_Switzerland/Final_Report_IChO_2023/IChO_2023_Final_Report_Appendix.pdf'
    document = pdf(url)
    rows = []
    for page in list(document)[311:322]:
        for line in page.get_text(sort=True).splitlines():
            match = re.match(r'^\s*([A-Z]{3}-\d)\s+(\d+,\d+)\s+(\d+)\s+(Gold|Silver|Bronze|Honorable Mention|Participant)\b', line)
            if match:
                rows.append((float(match[2].replace(',', '.')), int(match[3]), 'HM' if match[4] == 'Honorable Mention' else match[4]))
    assert len(rows) > 300
    assert sorted(rank for _, rank, _ in rows) == list(range(1, len(rows) + 1))
    assert all(0 <= score <= 100 for score, _, _ in rows)
    sources = [source(url, 'IChO 2023 official final report appendix: final marking / ranking, PDF pages 312–322'),
               source('https://science.olympiad.ch/icho2023', 'IChO 2023 organiser: exams and official final report')]
    record = {'id': 'icho-2023-total', 'year': 2023, 'scope': 'total',
              'label': {'ko': '전체 대회 · 공식 가중 총점', 'en': 'Complete competition · official weighted total'},
              'max': 100, 'scores': sorted((score for score, _, _ in rows), reverse=True),
              'participants': len(rows), 'complete': True, 'population': 'individual',
              'medalCutoffs': observed_cutoffs([(score, award) for score, _, award in rows]),
              'cutoffKind': 'observed', 'awardScope': True, 'sources': sources,
              'components': [{'id': 'theory', 'label': {'ko': '이론 가중 점수', 'en': 'Weighted theory score'}, 'max': 60,
                              'taskSets': whole_paper_sets('icho', 2023)},
                             {'id': 'practical', 'label': {'ko': '실험 가중 점수', 'en': 'Weighted practical score'}, 'max': 40}],
              'note': {'ko': '공식 이론 60점과 실험 40점을 합한 가중 총점입니다. 이론만의 풀이를 이 총점이나 메달 기준으로 환산하지 않습니다. 메달 기준은 공식 수상자 표의 최저 관측 점수입니다.',
                       'en': 'Official weighted total: theory 60 plus practical 40. A theory-only attempt must not be rescaled to this total or its awards. Award cutoffs are observed minima in the official award table.'}}
    RECEIPTS[url].update({'year': 2023, 'scoreRows': len(rows), 'sourcePages': list(range(312, 323)),
                         'crossChecks': ['all published ranks form the consecutive complete participant list', 'all weighted totals are between 0 and 100']})
    return [record]


def ibo_2024():
    url = 'https://www.ibo-info.org/files/downloads/results-reports/results/IBO2024%20results%20-%20amended%20version%20January%202025.pdf'
    document = pdf(url)
    rows = []
    for page in document:
        for line in page.get_text(sort=True).splitlines():
            rank = re.match(r'^\s*(\d+)\s+', line)
            if not rank:
                continue
            values = re.findall(r'(?<!\S)-?\d+(?:\.\d+)?(?=\s|$)', line)
            if len(values) < 16:
                continue
            # Fifteen numeric columns follow the name. A delegation label can
            # contain a digit, so take the numeric tail rather than all tokens.
            columns = list(map(float, values[-15:]))
            a, b, total = columns[10:13]
            assert 0 <= a <= 50 and 0 <= b <= 50 and abs(a + b - total) < .001, line
            rows.append((int(rank[1]), a, b, total))
    assert [rank for rank, *_ in rows] == list(range(1, 287))
    annual = next(year for year in manifest('ibo')['years'] if year['y'] == 2024)
    assert {'T1', 'T2'} <= {item.get('part') for item in annual['files'] if item['kind'] == 'paper'}
    report = 'https://www.ibo-info.org/files/downloads/results-reports/final-reports/IBO-2024%20Report.pdf'
    sources = [source(url, 'IBO 2024 official amended ranking, approved 26 January 2025'),
               source(report, 'IBO 2024 official report, printed page 114: two 50-question theory papers and scoring scale')]
    common = {'year': 2024, 'complete': True, 'participants': len(rows), 'population': 'individual',
              'awardScope': False, 'sources': sources,
              'note': {'ko': '공식 원점수입니다. 각 문항은 1/0.6/0.2/0점이며 A·B 각 50문항입니다. 이론 점수 위치만 비교하며, 실험과 표준화 T점수를 합산해 정한 실제 메달 기준은 적용하지 않습니다. 공식 2025년 1월 수정 순위를 사용합니다.',
                       'en': 'Official raw scores: each of the fifty questions in A and B earns 1/0.6/0.2/0 points. Compare theory score positions only; actual medals use standardized theory and practical T-scores. Uses the official January 2025 amended ranking.'}}
    definitions = [('theory', 'theory', 100, 3, [['T1', 'T2']], {'ko': '이론 전체 · A + B', 'en': 'Complete theory · A + B'}),
                   ('theory-a', 'round', 50, 1, [['T1']], {'ko': '이론 A', 'en': 'Theory A'}),
                   ('theory-b', 'round', 50, 2, [['T2']], {'ko': '이론 B', 'en': 'Theory B'})]
    records = [{**common, 'id': 'ibo-2024-' + identifier, 'scope': scope, 'label': label,
                'max': maximum, 'taskSets': sets, 'scores': sorted((compact(row[column]) for row in rows), reverse=True)}
               for identifier, scope, maximum, column, sets, label in definitions]
    RECEIPTS[url].update({'year': 2024, 'scoreRows': len(rows), 'amended': '2025-01-26',
                         'crossChecks': ['all 286 published ranks consecutive', 'all theory A and B scores between 0 and 50',
                                         'all theory totals equal A + B', 'published official report defines max and regressive scoring']})
    return records


def ieso_2026():
    url = 'https://www.ieso2026-to.com/sites/default/files/download/IESO_TOTAL_RANKING.pdf'
    document = pdf(url)
    entries = []
    for page in document:
        for line in page.get_text(sort=True).splitlines():
            match = re.search(r'(\S+-S\d+)\s+(\d+,\d+)\s*(GOLD|SILVER|BRONZE)?\s*$', line)
            if match:
                entries.append((match[1], float(match[2].replace(',', '.'))))
    assert len(entries) == len({code for code, _ in entries}) == 151
    record = {'id': 'ieso-2026-total', 'year': 2026, 'scope': 'total', 'manualOnly': True,
              'label': {'ko': '전체 대회 · 공개 총점 단위 직접 입력', 'en': 'Complete competition · enter the published score units'},
              'max': None, 'taskSets': [], 'scores': sorted((value for _, value in entries), reverse=True),
              'complete': True, 'participants': 151, 'population': 'individual', 'awardScope': False,
              'sources': [source(url, 'IESO 2026 official total ranking'),
                          source('https://www.ieso2026-to.com/node/8', 'IESO 2026 organiser: results and standings announcement')],
              'note': {'ko': '공식 표에 기재된 전체 총점을 같은 단위로 직접 입력할 때만 비교합니다. 만점과 이론·실험 가중치는 확인되지 않아 AI 채점 점수를 환산하지 않습니다. 일부 낮은 점수에도 추가 동메달이 있어, 보편적인 메달 컷을 제시하지 않습니다. 위치는 공개 숫자 점수로 다시 계산한 가상 위치입니다.',
                       'en': 'Manual comparison only: enter a complete total in the same units as the official table. The maximum and theory/practical weighting are unverified, so AI grades are never rescaled. Additional bronze awards occur below the main award band; no universal medal cutoff is asserted. Position is recomputed hypothetically from the published numeric totals.'}}
    RECEIPTS[url].update({'year': 2026, 'scoreRows': len(entries), 'maximum': None,
                         'manualOnly': True, 'medalCutoffsOmitted': 'Bronze awards occur below the main medal band; a universal score threshold would be misleading.',
                         'crossChecks': ['151 distinct contestant codes', 'all eight ranking pages parsed']})
    return [record]


def main():
    if '--reuse-imo' in sys.argv:
        existing = json.loads((OUT / 'other.json').read_text(encoding='utf-8'))
        imo_data = existing['competitions']['imo']
        previous = json.loads((OUT / 'other-receipts.json').read_text(encoding='utf-8'))
        RECEIPTS.update({row['url']: row for row in previous['files']})
    else:
        imo_data = imo()
    data = {'schema': 1, 'competitions': {'imo': imo_data, 'ioaa': {'records': ioaa_2025()},
                                       'icho': {'records': icho_2023()}, 'ibo': {'records': ibo_2024()},
                                       'ieso': {'records': ieso_2026()}}}
    checked = datetime.date.today().isoformat()
    for comp, value in data['competitions'].items():
        records = value['records']
        value['coverage'] = {'checked': checked, 'scoreYears': sorted({record['year'] for record in records}),
                             'completeScoreYears': sorted({record['year'] for record in records if record['complete']}),
                             'publishedCutoffYears': sorted({record['year'] for record in records if record.get('cutoffKind') == 'published'})}
    data['competitions']['imo']['coverage'].update({
        'limitations': {'ko': '1959–2026년 실제 개최된 67개 대회의 공식 총점, 만점, 메달 기준을 수집했습니다. 1980년은 개최되지 않았습니다. 일부 과거 표는 점수와 표기 순위가 달라 숫자 점수로 가상 위치를 계산합니다. 장려상은 총점만으로 추정하지 않습니다.',
                        'en': 'Official totals, maxima and medal boundaries for all 67 held editions, 1959–2026. No competition was held in 1980. Some historical printed ranks disagree with totals, so hypothetical positions use numeric scores. Honourable mentions are not inferred from totals.'},
        'sources': [source('https://www.imo-official.org/results/', 'IMO official results and edition statistics')]})
    data['competitions']['ioaa']['coverage'].update({
        'limitations': {'ko': '2025년 공식 최종 성적표의 288명에 대해 이론·실기·총점 전체를 검증했습니다. 이론 단독 점수에는 총점 메달 기준을 적용하지 않습니다. 다른 연도는 점수 단위와 전체 수록 범위가 검증된 뒤 추가합니다.',
                        'en': 'All 288 theory, practical and total score rows in the 2025 official final marklist were checked. Combined medal thresholds do not apply to theory alone. Other editions require verified score units and population coverage before importing.'},
        'sources': [source('https://ioaa2025.in/ioaa-2025-final-marklist/', 'IOAA 2025 organiser: final marklist')]})
    data['competitions']['icho']['coverage'].update({
        'limitations': {'ko': '2023년 주최 측 공식 최종 보고서 부록의 348명 가중 총점입니다. 중앙 2024·2025년 결과표에는 순위·수상만 있고 숫자 점수가 없습니다. 이론 점수를 전체 총점으로 환산하지 않습니다.',
                        'en': '348 weighted totals from the 2023 organiser\'s official final report appendix. The checked central 2024 and 2025 tables publish ranks and awards without numeric scores. Theory-only grades are never rescaled to combined totals.'},
        'sources': [source('https://science.olympiad.ch/icho2023', 'IChO 2023 organiser archive'),
                    source('https://www.icho-official.org/results/', 'IChO Steering Committee results database')]})
    data['competitions']['ibo']['coverage'].update({
        'limitations': {'ko': '2024년 수정된 공식 순위표의 286명 이론 A·B 및 합계 원점수입니다. 실제 메달을 결정한 표준화 이론·실험 T점수와 구분합니다. 다른 연도는 문제별 만점과 점수 체계를 검증한 뒤 추가합니다.',
                        'en': 'Raw theory A, B and combined scores for all 286 students in the amended 2024 official ranking. These are separate from the standardized theory/practical T-scores used for medals. Other years require verified maxima and scoring rules.'},
        'sources': [source('https://www.ibo-info.org/en/info/results-reports.html', 'IBO official results and reports, 1990–2026')]})
    data['competitions']['ieso']['coverage'].update({
        'limitations': {'ko': '2026년 공식 전체 순위표의 151명 총점을 수집했습니다. 만점·가중치가 검증되지 않아 공식 단위의 전체 총점을 직접 입력할 때만 비교합니다. 추가 동메달 때문에 보편적인 메달 컷은 제시하지 않습니다. 과거 IGEO 수상자 목록은 숫자 점수·만점 검증 없이 순위 분포로 만들지 않았습니다.',
                        'en': '151 totals from the 2026 official complete ranking. Its maximum/weighting is unverified; only an explicitly entered complete total in the source units is comparable. Additional bronze awards prevent a universal medal cutoff. Older IGEO medal lists were not turned into score distributions without verified numeric marks and scales.'},
        'sources': [source('https://www.ieso2026-to.com/sites/default/files/download/IESO_TOTAL_RANKING.pdf', 'IESO 2026 official total ranking'),
                    source('https://www.igeoscied.org/activities/ieso-2/list-of-medal-and-team-award-winners/', 'IGEO official medal archive')]})
    data['competitions']['ioaajr'] = {'records': [], 'coverage': {
        'checked': checked, 'scoreYears': [], 'completeScoreYears': [], 'publishedCutoffYears': [],
        'limitations': {'ko': '2022–2025년 IOAA 공식 연도별 자료와 2025년 주최 측 결과 페이지를 확인했습니다. 2025년 결과는 수상자 이름·국가 슬라이드이며 숫자 성적표나 메달 컷이 아닙니다. 검증한 숫자 분포가 없어 가상 순위·메달을 표시하지 않습니다. 2026년 대회는 이 자료 확인일 이후에 열립니다.',
                        'en': 'Checked the 2022–2025 official IOAA edition pages and the 2025 organiser\'s results. The latter presents medalist name/country slides, not numeric marklists or cutoffs. No verified score distribution is available for a hypothetical rank or medal comparison. The 2026 edition takes place after this check date.'},
        'sources': [source('https://ioaastrophysics.org/junior-ioaa/past-olympiads', 'IOAA official Junior edition archive'),
                    source('https://www.ioaajr2025.ro/results', 'IOAA Junior 2025 organiser: medal announcement slides'),
                    source('https://www.ioaajr2025.ro/ioaajr-regulations', 'IOAA Junior official working principles: 60% theory, 40% sky observation')]}}
    output = OUT / 'other.json'
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    receipts = {'schema': 1, 'checked': checked,
                'files': sorted(RECEIPTS.values(), key=lambda row: row['url'])}
    (OUT / 'other-receipts.json').write_text(json.dumps(receipts, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('Wrote', output.relative_to(ROOT), flush=True)


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main()

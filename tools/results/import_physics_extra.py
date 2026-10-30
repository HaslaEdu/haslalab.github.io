"""Import anonymous official OPhO/Physics Cup results and the verified IZhO 2025 transcript.

    python tools/results/import_physics_extra.py [--refresh]

Dependencies: requests, beautifulsoup4, pymupdf. Originals are cached in tmp;
the shipped datasets contain numeric scores and provenance, never participant names.
"""
from __future__ import annotations
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
import sys
import threading
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CACHE = ROOT / 'tmp/results-physics-extra'
CACHE.mkdir(parents=True, exist_ok=True)
REFRESH = '--refresh' in sys.argv
RECEIPTS = {}
LOCK = threading.Lock()


def fetch(url):
    target = CACHE / (hashlib.sha256(url.encode()).hexdigest()[:24] + '.bin')
    if REFRESH or not target.exists():
        response = requests.get(url, timeout=45)
        response.raise_for_status()
        target.write_bytes(response.content)
    content = target.read_bytes()
    with LOCK:
        RECEIPTS[url] = {'url': url, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
    return content


def source(url, title, official=True):
    return {'url': url, 'title': title, 'official': official}


def pdf_text(url):
    content = fetch(url)
    assert content.startswith(b'%PDF'), url
    with pymupdf.open(stream=content, filetype='pdf') as document:
        RECEIPTS[url]['pages'] = len(document)
        return '\n'.join(page.get_text() for page in document)


def table(url):
    soup = BeautifulSoup(fetch(url), 'html.parser')
    tables = soup.select('table')
    assert len(tables) == 1, (url, len(tables))
    rows = [[cell.get_text(' ', strip=True) for cell in row.find_all(['td', 'th'], recursive=False)]
            for row in tables[0].select('tr')]
    return soup.get_text(' ', strip=True), rows[0], rows[1:]


def number(text):
    assert re.fullmatch(r'\d+(?:[.,]\d+)?', text), text
    value = float(text.replace(',', '.'))
    return int(value) if value.is_integer() else value


def record(comp, year, identity, scope, label, maximum, scores, sources, *, complete=True, participants=None, population='team', tasks=None, **extra):
    return dict(id=f'{comp}-{year}-{identity}', year=year, scope=scope, label=label, max=maximum,
                taskSets=tasks or [], scores=sorted(scores, reverse=True), complete=complete,
                participants=len(scores) if complete else participants, population=population,
                awardScope=False, sources=sources, **extra)


def component(identity, maximum, tasks=None):
    labels = {'theory': {'ko': '이론', 'en': 'Theory'}, 'experiment': {'ko': '실험', 'en': 'Experiment'}}
    return {'id': identity, 'label': labels[identity], 'max': maximum, 'taskSets': tasks or []}


def observed_cuts(scores, awards):
    """Only expose inclusive thresholds when the actual award table is monotone.

    Quota/category exceptions must not become a universal medal-score prediction.
    """
    levels = {'gold': 3, 'silver': 2, 'bronze': 1}
    grouped = {tier: [score for score, award in zip(scores, awards) if award == tier] for tier in levels}
    if not all(grouped.values()):
        return None
    cuts = {tier: min(values) for tier, values in grouped.items()}
    if any(score >= cut and levels.get(award, 0) < levels[tier]
           for tier, cut in cuts.items() for score, award in zip(scores, awards)):
        return None
    return cuts


def opho():
    base = 'https://opho.physoly.org/'
    paths = ['2026'] + [f'{year}-invitational' for year in (2021, 2022, 2023, 2025)]
    paths += [f'{year}-open' if year != 2021 else '2021' for year in range(2020, 2026)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        results = dict(zip(paths, pool.map(lambda path: table(base + 'results/' + path), paths)))
    records = []
    for year, theory_max, experiment_max in [(2021, 100, 50), (2022, 110, 40), (2023, 160, None)]:
        url = base + f'results/{year}-invitational'
        intro, headers, rows = results[f'{year}-invitational']
        expected = {2021: 37, 2022: 29, 2023: 47}[year]
        assert len(rows) == expected
        index = {key: headers.index(key) for key in ('Exp', 'Total')}
        qcols = [i for i, key in enumerate(headers) if re.fullmatch(r'T\d+', key)]
        theories = [round(sum(number(row[i]) for i in qcols), 6) for row in rows]
        experiments = [number(row[index['Exp']]) for row in rows]
        totals = [number(row[index['Total']]) for row in rows]
        assert all(abs(t + e - total) < 1e-6 for t, e, total in zip(theories, experiments, totals))
        if 'Th' in headers:
            assert all(abs(t - number(row[headers.index('Th')])) < 1e-6 for t, row in zip(theories, rows))
        theory_url = base + f'archives/{year}-invitational-theory.pdf'
        theory_text = pdf_text(theory_url)
        assert re.search(rf'{theory_max}\s+points', theory_text)
        refs = [source(url, f'OPhO {year} Invitational — complete official standings'),
                source(theory_url, f'OPhO {year} — original theoretical paper and scoring maximum')]
        records.append(record('opho', year, 'invitational-theory', 'theory',
            {'ko': '초청 라운드 · 이론 전체', 'en': 'Invitational · complete theory'}, theory_max, theories, refs, tasks=[['Ti']]))
        RECEIPTS[url].update(year=year, scoreRows=expected, checks=['complete table row count', 'every theory question summed', 'theory + experiment = total'])
        if experiment_max is None:
            # The cover says 25, yet the organiser's results have Exp=30. Do not infer a revised maximum.
            continue
        experiment_url = base + f'archives/{year}-invitational-experimental.pdf'
        experiment_text = pdf_text(experiment_url)
        assert re.search(r'50\s+points', experiment_text) if year == 2021 else ('(15 pts)' in experiment_text and '(25 pts)' in experiment_text)
        refs = refs + [source(experiment_url, f'OPhO {year} — original experimental paper and printed marks')]
        records.append(record('opho', year, 'invitational-experiment', 'experiment',
            {'ko': '초청 라운드 · 실험 전체', 'en': 'Invitational · complete experiment'}, experiment_max, experiments, refs, tasks=[['E']]))
        total = record('opho', year, 'invitational-total', 'total',
            {'ko': '초청 라운드 · 이론·실험 합계', 'en': 'Invitational · theory + experiment'}, theory_max + experiment_max,
            totals, refs, tasks=[['Ti', 'E']], components=[component('theory', theory_max, [['Ti']]), component('experiment', experiment_max, [['E']])])
        awards = [next((key for key in ('gold', 'silver', 'bronze') if key in row[-1].lower()), '') for row in rows]
        cuts = observed_cuts(totals, awards)
        if cuts:
            total.update(awardScope=True, medalCutoffs=cuts, cutoffKind='observed')
        RECEIPTS[url]['monotoneMedalThresholds'] = bool(cuts)
        records.append(total)
    year = 2025
    url = base + 'results/2025-invitational'
    intro, headers, rows = results['2025-invitational']
    assert len(rows) == 46 and '46 teams' in intro
    part1 = base + 'archives/2025-invitational-part-1.pdf'
    part2 = base + 'archives/2025-invitational-part-2.pdf'
    assert len(re.findall(r'Theory Question [123] \[10 marks\]', pdf_text(part1))) == 3
    part2_text = pdf_text(part2)
    assert 'Experimental Question [15 marks]' in part2_text and 'Theory Question 4 [5 marks]' in part2_text
    records.append(record('opho', year, 'invitational-total', 'total',
        {'ko': '초청 라운드 · 두 부분 전체 합계', 'en': 'Invitational · both complete parts'}, 50,
        [number(row[headers.index('Total')]) for row in rows],
        [source(url, 'OPhO 2025 Invitational — official full standings'), source(part1, 'Original Part I: three 10-mark questions'), source(part2, 'Original Part II: experiment 15 + theory 5')],
        tasks=[['T1i', 'T2i']], components=[component('theory', 35), component('experiment', 15, [['E']])],
        note={'ko': '팀 점수입니다. 학부생 팀은 시상에서 따로 분류되므로 전체 표본에 메달 경계점수를 적용하지 않습니다.',
              'en': 'Team scores. Undergraduate teams have separate prize eligibility, so no overall medal threshold is inferred.'}))
    RECEIPTS[url].update(year=year, scoreRows=46, checks=['all 46 published team totals', 'Part I 30 + Part II 20 = 50'])
    intro, headers, rows = results['2026']
    assert len(rows) == 443 and '519 competed and 443 scored' in intro
    records.append(record('opho', 2026, 'combined-total', 'total',
        {'ko': '통합 라운드 · 공식 가중 합계', 'en': 'Combined round · official weighted total'}, 100,
        [number(row[-1]) for row in rows], [source(base + 'results/2026', 'OPhO 2026 — official standings and 55/35/10 scoring weights')],
        complete=False, participants=519, manualOnly=True,
        note={'ko': '519개 참가 팀 중 점수를 얻은 443개 팀만 공개되어 전체 분포가 아닙니다. 단답 55·장답 35·실험 10의 공식 가중 점수이며 HaslaLab 원점수와 자동 비교하지 않습니다.',
              'en': 'Only 443 scoring teams out of 519 competing teams are published. These official 55/35/10 weighted totals are not automatically matched to a HaslaLab raw grade.'}))
    for year in range(2020, 2026):
        path = str(year) if year == 2021 else f'{year}-open'
        intro, headers, rows = results[path]
        index = headers.index('Score')
        scores = [number(row[index]) for row in rows]
        full_count = {2020: 340, 2021: 625, 2022: 453, 2023: 918, 2024: 975, 2025: 1231}[year]
        complete = year not in (2021, 2024)
        assert len(rows) == ({2021: 45, 2024: 54}.get(year, full_count))
        records.append(record('opho', year, 'open-total', 'total',
            {'ko': '오픈 라운드 · 공식 원점수', 'en': 'Open round · official published score'}, None, scores,
            [source(base + 'results/' + path, f'OPhO {year} Open — official results and coverage statement')],
            complete=complete, participants=full_count, manualOnly=True,
            note={'ko': '공식 결과표의 점수를 그대로 보존했습니다. 연도별 가중치·풀이 수·시도 횟수에 따른 점수 체계이므로 HaslaLab 채점 점수에서 환산하지 않습니다.' + (' 진출 팀 점수만 공개된 부분 표본입니다.' if not complete else ''),
                  'en': 'Published scores are preserved without rescaling. Annual solve-count, weighting and attempt rules differ; HaslaLab grades are never converted to this scale.' + (' Only advancing teams are published: this is an incomplete field.' if not complete else '')}))
        RECEIPTS[base + 'results/' + path].update(year=year, scoreRows=len(scores), complete=complete)
    return {'records': records, 'coverage': {'ko': '2020~2026년 공식 결과 중 검증한 원점수·초청 라운드 배점을 제공합니다. 2023년 실험은 표지 25점과 결과표 30점이 달라 실험·전체 만점 비교를 보류했습니다. 2024년 초청 라운드의 전체 만점은 검증하지 않았습니다.',
        'en': 'Verified published scores and Invitational scales from 2020–2026. The 2023 experimental cover says 25 while results contain 30, so its experimental/overall maximum is withheld. The 2024 Invitational overall maximum is unverified.'}}


def izho():
    path = OUT / 'physics-extra-izho2025-source.json'
    original = path.read_bytes()
    data = json.loads(original)
    rows = data['rows']
    assert [row[0] for row in rows] == list(range(1, 181))
    theories = [round(sum(row[1:4]), 6) for row in rows]
    experiments, totals = [row[4] for row in rows], [row[5] for row in rows]
    assert all(abs(t + e - total) < 1e-6 for t, e, total in zip(theories, experiments, totals))
    theory_url = 'https://olimpicos.net/files/izho/IZhO_2025_Q1.pdf'
    theory_text = pdf_text(theory_url)
    assert len(re.findall(r'\(10\.0 points\)', theory_text)) == 3
    experiment_url = 'https://github.com/HaslaEdu/haslalab.github.io/releases/download/pdf-izho/IZhO_2025_S.pdf'
    assert re.search(r'TOTAL\s+20,0', pdf_text(experiment_url))
    refs = [source(data['url'], data['title']), source(theory_url, 'Unchanged original 2025 theory paper: 3 × 10 marks (mirror)', False),
            source(experiment_url, 'Archived original 2025 experimental marking scheme: TOTAL 20.0 (mirror)', False)]
    records = [record('izho', 2025, 'theory', 'theory', {'ko': '이론 전체', 'en': 'Complete theory'}, 30, theories, refs, population='individual', tasks=[['T']]),
               record('izho', 2025, 'experiment', 'experiment', {'ko': '실험 전체', 'en': 'Complete experiment'}, 20, experiments, refs, population='individual', tasks=[['E1']])]
    total = record('izho', 2025, 'total', 'total', {'ko': '물리 전체 · 이론·실험 합계', 'en': 'Complete physics · theory + experiment'}, 50, totals, refs,
        population='individual', tasks=[['T', 'E1']], components=[component('theory', 30, [['T']]), component('experiment', 20, [['E1']])],
        note={'ko': '공식 페이지 제목은 2025년이며 URL에만 2020이 남아 있습니다. 물리 결과 180명만 집계했습니다.',
              'en': 'The official page title identifies 2025; only its URL retains 2020. All 180 Physics rows are included; other subjects are excluded.'})
    cuts = observed_cuts(totals, [row[6] for row in rows])
    if cuts:
        total.update(awardScope=True, medalCutoffs=cuts, cutoffKind='observed')
    records.append(total)
    RECEIPTS[data['url']] = {'url': data['url'], 'method': data['method'], 'transcript': path.relative_to(ROOT).as_posix(),
        'transcriptSha256': hashlib.sha256(original).hexdigest(), 'year': 2025, 'scoreRows': 180, 'monotoneMedalThresholds': bool(cuts),
        'checks': ['contiguous official ranks 1–180', 'all three theory marks summed', 'every theory + experiment = published total', '30 + 20 maxima verified in original papers']}
    return {'records': records}


def physicscup():
    urls = {2024: 'https://physicscup.ee/final-results-of-physics-cup-2024/',
            2025: 'https://physicscup.ee/physics-cup-2025-final-results/',
            2026: 'https://physicscup.ee/physics-cup-2026-final-results/'}
    records = []
    for year, url in urls.items():
        soup = BeautifulSoup(fetch(url), 'html.parser')
        tables = soup.select('table')
        assert len(tables) == 2
        for category, table_node in zip(('preuniversity', 'university'), tables):
            rows = [[cell.get_text(' ', strip=True) for cell in row.find_all(['th', 'td'], recursive=False)] for row in table_node.select('tr')]
            header = rows[0]
            score_col = next(i for i, name in enumerate(header) if name.lower() in ('points', 'sum'))
            scores = [number(row[score_col]) for row in rows[1:] if any(row)]
            records.append(record('physcup', year, category + '-total', 'total',
                {'ko': ('대학 진학 전' if category == 'preuniversity' else '대학생') + ' · 공개 가중 점수',
                 'en': ('Pre-university' if category == 'preuniversity' else 'University') + ' · published weighted scores'},
                None, scores, [source(url, f'Physics Cup {year} — official final results by age group'),
                               source('https://physicscup.ee/participate/', 'Official scoring: speed, hints, attempts and solution bonuses')],
                complete=False, population='individual', manualOnly=True,
                note={'ko': '전체 등록자 분포가 아닌 공개된 결과 항목입니다. 공동 제출은 원문처럼 한 항목으로 보존했습니다. 속도·힌트·시도 횟수·풀이 보너스가 포함된 가중 점수여서 HaslaLab 원점수와 환산 비교하지 않습니다. 메달도 단순 총점만으로 추정하지 않습니다.',
                      'en': 'Published result entries, not the complete registered field; any joint submission remains one published entry. Scores include speed, hints, attempts and solution bonuses and are never converted from HaslaLab raw grades. No medal threshold is inferred.'}))
        RECEIPTS[url].update(year=year, tables=2, scoreRows=sum(len(r['scores']) for r in records if r['year'] == year), complete=False)
    return {'records': records}


def unavailable(ko, en):
    return {'records': [], 'coverage': {'ko': ko, 'en': en}}


def plancks():
    url = 'https://plancks23.ai-sf.it/files/list.pdf'
    text = pdf_text(url)
    assert all(word in text for word in ('POSITION', 'TEAM NAME', 'PARTICIPANTS'))
    assert not re.search(r'\b(?:SCORE|MARKS|POINTS)\b', text)
    RECEIPTS[url].update(year=2023, rankOnly=True, numericScores=False,
        checks=['official Milan international-final list', 'all five pages contain ranks and names, no numeric mark column', 'rank positions are not converted to scores'])
    return unavailable('2023년 밀라노 국제 결선의 공식 순위표는 확인했지만 숫자 점수가 없습니다. 검증한 점수 분포는 아직 없으며 국가별 예선 결과를 국제 결선에 섞지 않습니다.',
        'The official Milan 2023 international-final rank list is verified but contains no numeric marks. No numeric finals distribution is available; national preliminaries are not mixed into international finals.')


def main():
    competitions = {'opho': opho(), 'izho': izho(), 'physcup': physicscup(),
        'plancks': plancks(),
        'ispho': unavailable('현재 공식 결과는 수상자·부문 목록이며 숫자 점수표가 아니므로 분포나 메달 경계점수를 만들지 않았습니다.',
            'The current official results list awards and nominations without numeric marks; no score distribution or medal threshold is inferred.'),
        'gpho': unavailable('공식 숫자 점수표를 검증하지 못했습니다.', 'No official numeric standings have been verified.'),
        'ortvay': unavailable('공식 결과는 학년별 시상과 참가자별로 다른 제출 문항을 포함합니다. 2026년 표는 평균 40점 초과 참가자만 싣고 있어 전체 분포로 사용하지 않았습니다.',
            'Official results use study-year prize groups and different submitted task sets; the 2026 table includes only entrants averaging over 40. It is not treated as a complete comparable field.')}
    (OUT / 'physics-extra.json').write_text(json.dumps({'schema': 1, 'competitions': competitions}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    (OUT / 'physics-extra-receipts.json').write_text(json.dumps({'schema': 1, 'checked': '2026-10-30', 'files': list(RECEIPTS.values())}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('Imported', sum(len(data['records']) for data in competitions.values()), 'extra physics scoring records.')


if __name__ == '__main__':
    main()

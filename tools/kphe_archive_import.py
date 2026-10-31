"""Refresh the public KPS Physics League archive, preserving provenance.

Read-only against kphe.kps.or.kr. Downloads are cached in tmp/kphe_archive/originals.
The official '답지/정답' files are answer keys, not worked solutions.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'tmp/kphe_archive/originals'
BOARDS = {'2026-2': 43, '2026-1': 12, '2025-2': 11, '2025-1': 10, '2024-2': 9, '2024-1': 8}
LEVELS = {'초급': 'a', '중급': 'b', '고급': 'c', '전문가': 'd'}
UA = 'Mozilla/5.0 HaslaLab-archive'


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60).read()


def board_files(item):
    year, board = item
    url = f'https://kphe.kps.or.kr/board/board_detail/{board}'
    page = fetch(url).decode('utf-8')
    found = re.findall(r"download_file\('([^']+)',\s*'([^']+)'\)", page)
    if len(found) != 8:
        raise ValueError(f'{year}: expected eight official attachments; got {len(found)}')
    result = []
    for source, title in found:
        level = next((v for k, v in LEVELS.items() if k + '과정' in title), None)
        if not level:
            raise ValueError(title)
        part = f'T{year[-1]}{level}'
        kind = 'key' if ('정답' in title or '답지' in title) else 'paper'
        name = f'KPhE_{year[:4]}_{part}' + ('K.pdf' if kind == 'key' else '_KO.pdf')
        result.append({'file': name, 'part': part, 'kind': kind, 'lang': 'KO', 'url': source,
                       'source_page': url, 'source_title': title})
    return year, result


def download(record):
    year, entry = record
    path = CACHE / entry['file']
    if not path.exists():
        data = fetch(entry['url'])
        if not data.startswith(b'%PDF'):
            raise ValueError(f'not a PDF: {entry["url"]}')
        path.write_bytes(data)
    data = path.read_bytes()
    entry.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    return year, entry


def read_key(text):
    """Keep question numbers (PDF columns need not extract in reading order)."""
    parsed = {}
    for number, choices in re.findall(r'(\d+)\.\s*정답\s*:\s*([①②③④⑤](?:\s*[→⇒]\s*[①②③④⑤])?)', text):
        parsed[int(number)] = '①②③④⑤'.index(choices.strip()[-1]) + 1
    if not parsed or sorted(parsed) != list(range(1, max(parsed) + 1)):
        raise ValueError(f'Non-contiguous answer key: {sorted(parsed)}')
    return [parsed[i] for i in range(1, max(parsed) + 1)]


def main():
    import pymupdf as fitz
    CACHE.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        boards = dict(pool.map(board_files, BOARDS.items()))
        downloads = list(pool.map(download, [(year, f) for year, fs in boards.items() for f in fs]))
    manifest = json.loads((ROOT / 'tools/theory/kphe.json').read_text(encoding='utf-8'))
    manifest['about'] = ('Korean Physical Society Physics League. Public official archive: 2024-1 to 2026-2, '
                         'all four levels. Original answer PDFs contain answer keys, not worked solutions. '
                         'Earlier Korean Middle-School Physics Competition papers are in kphc.json.')
    for year in manifest['years']:
        y = year['y']
        year['problems'] = [{'id': f'T{y[-1]}{code}', 'title': level + '과정'} for level, code in LEVELS.items()]
        year['files'] = boards[y]
        year['keys'] = {}
        for entry in year['files']:
            if entry['kind'] != 'key':
                continue
            with fitz.open(CACHE / entry['file']) as pdf:
                text = '\n'.join(p.get_text(sort=True) for p in pdf)
            (CACHE / (entry['file'] + '.txt')).write_text(text, encoding='utf-8')
            year['keys'][entry['part']] = read_key(text)
        year['source_page'] = f'https://kphe.kps.or.kr/board/board_detail/{BOARDS[y]}'
        year['note'] = ('한국물리학회 공식 공개 기출문제 및 정답표. 초급·중급·고급·전문가 전 과정. '
                        '정답표는 풀이 해설이 아닙니다. 정정된 정답은 최종 공지를 기준으로 합니다.')
    manifest['missing'] = [{'y': 2023, 'why': 'Official public 자료실 currently lists 2024-1 onwards only; no original public PDF found.'}]
    (ROOT / 'tools/kphe_archive_downloads.json').write_text(json.dumps(boards, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (ROOT / 'tmp/kphe_archive/manifest.pending.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'Downloaded and SHA-256 checked {len(downloads)} PDFs in {CACHE}')


if __name__ == '__main__':
    main()

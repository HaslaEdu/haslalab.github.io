"""Download and validate the Eotvos manifest's published PDFs without retypesetting.

The manifest records each document's original URL and optional publication context.
This helper retains those sources while adding stable local copies and an audit.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import hashlib
import json
import re
import time

import pymupdf as fitz
import requests

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'tools/theory/eotvos.json'
REPORT = ROOT / 'tools/eotvos_archive_report.json'


def download(job):
    year, entry = job
    target = ROOT / entry.get('local', 'pdfx/eotvos/' + entry['file'])
    cached = target.read_bytes() if target.exists() else None
    content = cached if cached and hashlib.sha256(cached).hexdigest() == entry.get('sha256') else None
    error = None
    for attempt in range(3):
        if content is not None:
            break
        try:
            response = requests.get(entry['url'], timeout=(10, 35))
            response.raise_for_status()
            content = response.content
            if len(content) > 35_000_000 or b'%PDF-' not in content[:1024]:
                raise ValueError('Response is not a bounded PDF')
            break
        except Exception as exc:
            error = str(exc)
            content = None
            if attempt < 2:
                time.sleep(attempt + 1)
    if content is None:
        return {'year': year, 'file': entry['file'], 'url': entry['url'], 'error': error}
    try:
        document = fitz.open(stream=content, filetype='pdf')
        texts = [page.get_text() for page in document]
        digest = hashlib.sha256(content).hexdigest()
        year_pages = [index + 1 for index, text in enumerate(texts) if re.search(r'(?<!\d)' + str(year) + r'(?!\d)', text)]
        visual = entry.get('verification', {}).get('method') in ('visual', 'source_index') and entry.get('verification', {}).get('year') == year
        if not document.page_count or not (year_pages or visual):
            raise ValueError('The source year is not identifiable in the PDF text')
        mapped = entry.get('source_pages') or []
        historical_header = str(year) + r'.{0,100}feladatai|E[öo]tv[öo]s.{0,25}verseny\s*,\s*' + str(year) + r'.{0,70}1\.\s*feladat'
        header_verified = bool(mapped) and any(re.search(historical_header, texts[page - 1], re.I | re.S) for page in mapped if 1 <= page <= len(texts))
        if entry.get('source_document_year') and not header_verified:
            raise ValueError('Declared historical problem-set header was not found on its mapped source pages')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return {'year': year, 'file': entry['file'], 'url': entry['url'], 'local': target.relative_to(ROOT).as_posix(),
                'kind': entry['kind'], 'language': entry.get('lang'), 'bytes': len(content),
                'pages': document.page_count, 'sha256': digest, 'year_pages': year_pages,
                **({'source_document_year': entry['source_document_year'], 'source_pages': mapped, 'section_header_verified': header_verified,
                    'complete_problem_set': entry.get('complete_problem_set', False)} if entry.get('source_document_year') else {}),
                'previous_sha256': entry.get('sha256'), 'first_page_text': texts[0][:900]}
    except Exception as exc:
        return {'year': year, 'file': entry['file'], 'url': entry['url'], 'error': str(exc)}


def main():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    jobs = list({(year['y'], entry['url'], entry.get('local', 'pdfx/eotvos/' + entry['file'])): (year['y'], entry)
                 for year in manifest['years'] for entry in reversed(year.get('files', [])) if entry['file'].endswith('.pdf')}.values())
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(download, job): job for job in jobs}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(json.dumps({key: value for key, value in result.items() if key not in ('first_page_text', 'previous_sha256')}, ensure_ascii=False), flush=True)
    lookup = {(result['year'], result['url'], result['local']): result for result in results if 'local' in result}
    for year in manifest['years']:
        for entry in year.get('files', []):
            result = lookup.get((year['y'], entry['url'], entry.get('local', 'pdfx/eotvos/' + entry['file'])))
            if result:
                entry.update({key: result[key] for key in ('local', 'bytes', 'pages', 'sha256')})
                entry.pop('direct', None)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    available = sorted(year['y'] for year in manifest['years'])
    REPORT.write_text(json.dumps({'competition': 'eotvos', 'physics_since': 1916, 'checked': manifest.get('checked'),
                                 'search_sources': manifest.get('search_sources', []),
                                 'coverage': {'available_years': available,
                                              'continuous_recent_coverage': [1994, 2026],
                                              'historical_complete_years': [year for year in available if year < 1994],
                                              'english_translation_years': sorted(year['y'] for year in manifest['years'] if any(entry.get('lang') == 'EN' and entry['kind'] == 'paper' for entry in year['files'])),
                                              'unique_local_pdfs': len({result['local'] for result in results if 'local' in result}),
                                              'unobtained_years_since_1916': [year for year in range(1916, 2027) if year not in available],
                                              'unobtained_note': 'No verified paper obtained in this search. This does not imply that a competition was held in every missing year.'},
                                 'historical_reprints': [result for result in results if result.get('source_document_year')],
                                 'files': sorted(results, key=lambda item: (-int(item['year']), item['file']))}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if len(lookup) != len(jobs):
        raise SystemExit(f'Validated {len(lookup)} of {len(jobs)} PDFs; inspect {REPORT.name}')


if __name__ == '__main__':
    main()

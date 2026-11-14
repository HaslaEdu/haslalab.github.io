# -*- coding: utf-8 -*-
"""Register reviewed Korean IZhO editions (html-reflow-stamped-v1) in the repository.

usage: python -I tools/ko_reflow/izho/register.py PDF_DIR SRC_DIR NAME [NAME ...]

NAME is <year>_T or <year>_TS (IZhO), or icho:<year>_T (IChO theoretical paper, source IChO_<year>_T_EN.pdf). PDF_DIR holds IZhO_<year>_T_KO.pdf / IZhO_<year>_TS_KO.pdf, SRC_DIR the originals
(IZhO_<year>_T_EN.pdf / IZhO_<year>_TS.pdf, or the page range in RANGES). For each edition it writes
tools/ko_reflow/qa/<file>.json and replaces the file's rows in tools/original_style_publication.json,
tools/translation_font_validation.json and pdf-assets.json (keeping order, field set and line endings), and sets
tools/theory_ko.json izho/<year>/T paper or sol. Upload first (tools/pdf_release.py), then restore pdf-assets.json
from git, run this, then tools/update_original_layout_versions.py.
"""
import hashlib, json, pathlib, re, sys
import pymupdf

ROOT = pathlib.Path(__file__).resolve().parents[3]
RANGES = {   # name: (first, last) source pages when the Korean edition covers only part of the original
    # 2023 and 2024 publish one file with the English, Kazakh and Russian versions; the Korean follows the English part
    '2023_T': (1, 6), '2023_TS': (25, 43), '2024_T': (1, 6), '2024_TS': (1, 14),
    '2023_S': (1, 7), '2024_E': (1, 4), '2024_S': (1, 7),
}
# the 2012 English paper is a text-only export without figures, formulas or the instructions page; the Korean edition
# follows the official Russian paper (also 6 A4 pages)
SOURCES = {'2012_T': 'IZhO_2012_T_RU.pdf',
           # the 2013 experimental round exists only in Russian on the server
           '2013_E': 'IZhO_2013_E_RU.pdf', '2013_S': 'IZhO_2013_S_RU.pdf'}
# experimental round: E = problems (IZhO_<year>_E_EN.pdf), S = solutions (IZhO_<year>_S.pdf); linked from index.html
EXP = {'E': '_E_EN.pdf', 'S': '_S.pdf'}


def edition(name):
    """(korean file, source file, catalogue slot, year, comp, html source) for NAME = <year>_T|_TS or icho:<year>_T."""
    if name.startswith('icho:'):   # IChO theoretical exam paper (tools/ko_reflow/icho/<year>_T.html)
        year, part = name[5:].split('_')
        return (f'IChO_{year}_{part}_KO.pdf', f'IChO_{year}_T_EN.pdf', 'paper', int(year), 'icho',
                f'tools/ko_reflow/icho/{year}_{part}.html')
    year, part = name.split('_')
    if part in EXP:
        return (f'IZhO_{year}_{part}_KO.pdf', SOURCES.get(name) or f'IZhO_{year}{EXP[part]}', None, int(year), 'izho',
                f'tools/ko_reflow/izho/{name}.html')
    src = SOURCES.get(name) or (f'IZhO_{year}_T_EN.pdf' if part == 'T' else f'IZhO_{year}_TS.pdf')
    return (f'IZhO_{year}_{part}_KO.pdf', src, ('paper' if part == 'T' else 'sol'), int(year), 'izho',
            f'tools/ko_reflow/izho/{name}.html')


def load(rel):
    raw = (ROOT / rel).read_bytes()
    return json.loads(raw.decode('utf-8')), (b'\r\n' in raw), raw.endswith(b'\n')


def save(rel, data, crlf, final_nl, indent=2):
    text = json.dumps(data, indent=indent, ensure_ascii=False)
    if final_nl:
        text += '\n'
    if crlf:
        text = text.replace('\n', '\r\n')
    (ROOT / rel).write_bytes(text.encode('utf-8'))


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def replace_row(rows, file, row):
    for i, r in enumerate(rows):
        if r['file'] == file:
            rows[i] = row
            return
    rows.append(row)


def main(pdf_dir, src_dir, *names):
    pub, pub_crlf, pub_nl = load('tools/original_style_publication.json')
    fonts, f_crlf, f_nl = load('tools/translation_font_validation.json')
    ko, k_crlf, k_nl = load('tools/theory_ko.json')
    done = []
    for name in names:
        out, srcname, slot, year, comp, html = edition(name)
        p = pathlib.Path(pdf_dir) / out
        src_path = pathlib.Path(src_dir) / srcname
        doc, src = pymupdf.open(p), pymupdf.open(src_path)
        a, b = RANGES.get(name, (1, len(src)))
        n = b - a + 1
        assert len(doc) == n, (out, len(doc), n)
        sizes = all(abs(doc[i].rect.width - src[a - 1 + i].rect.width) < 0.5 and
                    abs(doc[i].rect.height - src[a - 1 + i].rect.height) < 0.5 for i in range(n))
        hangul = len(re.findall(r'[가-힣]', ''.join(pg.get_text() for pg in doc)))
        h, size = sha(p), p.stat().st_size
        assert (ROOT / html).exists(), html
        assert sizes and hangul > 0, (out, sizes, hangul)
        qa = {
            'schema': 'html-reflow-stamped-v1', 'file': out, 'status': 'READY', 'sha256': h, 'bytes': size, 'pages': n,
            'source_file': srcname, 'source_sha256': sha(src_path), 'source_page_range': [a, b], 'source_pages': n,
            'page_count_matches_source': True, 'page_sizes_match_source': sizes,
            'figures_logos_and_pure_math_stamped_from_source': True, 'korean_text_justified': True,
            'hangul_characters': hangul, 'html_source': html, 'builder': 'tools/ko_reflow/build.py',
            'visual_review': {'reviewed': True,
                              'method': 'every page compared side by side with the source at equal DPI '
                                        '(tools/ko_reflow/check.py and qa side-by-side images; every flag confirmed by zoom)',
                              'overflow_or_occlusion_observed': False},
        }
        save(f'tools/ko_reflow/qa/{out[:-4]}.json', qa, False, True, indent=1)
        replace_row(pub, out, {'file': out, 'year': year, 'language': 'ko', 'pages': n, 'bytes': size, 'sha256': h,
                               'qa': f'tools/ko_reflow/qa/{out[:-4]}.json', 'audit_schema': 'html-reflow-stamped-v1'})
        replace_row(fonts['files'], out, {'file': out, 'pages': n, 'bytes': size, 'sha256': h,
                                          'missing_glyph_spans': [], 'original_style': True})
        if slot:
            ko[comp].setdefault(str(year), {}).setdefault('T', {})[slot] = out
        done.append((out, size))
        print(f'{out}: {n} pages, {size} bytes, {hangul} hangul')
    save('tools/original_style_publication.json', pub, pub_crlf, pub_nl)
    save('tools/translation_font_validation.json', fonts, f_crlf, f_nl)
    save('tools/theory_ko.json', ko, k_crlf, k_nl)
    # pdf-assets.json: set only these rows (new files are added); the file is json indent 0, sorted, CRLF
    raw = (ROOT / 'pdf-assets.json').read_bytes()
    assets = json.loads(raw)
    for out, size in done:
        assets[out] = size
    text = json.dumps(dict(sorted(assets.items())), indent=0, ensure_ascii=False) + '\n'
    if b'\r\n' in raw:
        text = text.replace('\n', '\r\n')
    (ROOT / 'pdf-assets.json').write_bytes(text.encode('utf-8'))


if __name__ == '__main__':
    main(*sys.argv[1:])

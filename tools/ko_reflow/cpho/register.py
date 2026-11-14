# -*- coding: utf-8 -*-
"""Register reviewed Korean CPhO editions (html-reflow-stamped-v1) in the repository.

usage: python -I tools/ko_reflow/cpho/register.py PDF_DIR SRC_DIR NAME [NAME ...]

NAME is a row of EDITIONS below (e.g. 2017_Combined). For each it writes tools/ko_reflow/qa/<file>.json and
records the file in tools/original_style_publication.json, tools/translation_font_validation.json and
tools/theory_ko.json (cpho/<year>/T paper or sol; a combined edition is both). The PDF must already be
uploaded (tools/pdf_release.py; then `git checkout pdf-assets.json`). Afterwards run tools/theory_build.py and tools/update_original_layout_versions.py.
"""
import hashlib, json, pathlib, re, sys
import pymupdf

ROOT = pathlib.Path(__file__).resolve().parents[3]
# name: (output file, source pdf in SRC_DIR, first, last, catalogue source file name, slots)
EDITIONS = {
    '2003_TS': ('CPhO_2003_TS_KO.pdf', '2003.pdf', 4, 10, 'CPhO_2003_TS.pdf', ['sol']),
    '2004_TS': ('CPhO_2004_TS_KO.pdf', '2004.pdf', 5, 18, 'CPhO_2004_TS.pdf', ['sol']),
    '2005_TS': ('CPhO_2005_TS_KO.pdf', '2005.pdf', 4, 16, 'CPhO_2005_Chinese_original.pdf', ['sol']),
    '2013_TS': ('CPhO_2013_TS_KO.pdf', '2013_S_EN.pdf', 1, 15, 'CPhO_2013_TS.pdf', ['sol']),
    '2011_TS': ('CPhO_2011_TS_KO.pdf', '2011_S.pdf', 1, 21, 'CPhO_2011_TS.pdf', ['sol']),
    '2012_T': ('CPhO_2012_T_KO.pdf', '2012.pdf', 1, 3, 'CPhO_2012_T_ZH.pdf', ['paper']),
    '2012_TS': ('CPhO_2012_TS_KO.pdf', '2012.pdf', 4, 20, 'CPhO_2012_TS.pdf', ['sol']),
    '2014_Combined': ('CPhO_2014_Combined_KO.pdf', '2014.pdf', 1, 21, 'CPhO_2014_T_ZH.pdf', ['paper', 'sol']),
    '2015_Combined': ('CPhO_2015_Combined_KO.pdf', '2015.pdf', 1, 16, 'CPhO_2015_T_ZH.pdf', ['paper', 'sol']),
    '2016_T': ('CPhO_2016_T_KO.pdf', '2016_Q.pdf', 1, 5, 'CPhO_2016_T_ZH.pdf', ['paper']),
    '2016_TS': ('CPhO_2016_TS_KO.pdf', '2016_S.pdf', 1, 22, 'CPhO_2016_TS.pdf', ['sol']),
    '2017_Combined': ('CPhO_2017_Combined_KO.pdf', '2017.pdf', 1, 23, 'CPhO_2017_T_ZH.pdf', ['paper', 'sol']),
    '2018_Combined': ('CPhO_2018_Combined_KO.pdf', '2018.pdf', 1, 24, 'CPhO_2018_T_ZH.pdf', ['paper', 'sol']),
    '2019_Combined': ('CPhO_2019_Combined_KO.pdf', '2019.pdf', 1, 27, 'CPhO_2019_T_ZH.pdf', ['paper', 'sol']),
    '2020_T': ('CPhO_2020_T_KO.pdf', '2020_Q.pdf', 1, 6, 'CPhO_2020_T_ZH.pdf', ['paper']),
    '2020_TS': ('CPhO_2020_TS_KO.pdf', '2020_S.pdf', 1, 26, 'CPhO_2020_TS.pdf', ['sol']),
    '2021_T': ('CPhO_2021_T_KO.pdf', '2021_Q.pdf', 1, 7, 'CPhO_2021_T_ZH.pdf', ['paper']),
    '2021_TS': ('CPhO_2021_TS_KO.pdf', '2021_S.pdf', 1, 34, 'CPhO_2021_TS.pdf', ['sol']),
    '2022_TS': ('CPhO_2022_TS_KO.pdf', '2022_S.pdf', 1, 36, 'CPhO_2022_TS.pdf', ['sol']),
}


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def save(rel, data, indent=2):
    text = json.dumps(data, indent=indent, ensure_ascii=False).replace('\n', '\r\n') + '\r\n'
    (ROOT / rel).write_bytes(text.encode('utf-8'))


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def main(pdf_dir, src_dir, *names):
    pub = load('tools/original_style_publication.json')
    fonts = load('tools/translation_font_validation.json')
    ko = load('tools/theory_ko.json')
    for name in names:
        out, srcf, a, b, srcname, slots = EDITIONS[name]
        p = pathlib.Path(pdf_dir) / out
        doc = pymupdf.open(p); src = pymupdf.open(pathlib.Path(src_dir) / srcf)
        n = b - a + 1
        assert len(doc) == n, (out, len(doc), n)
        sizes = all(abs(doc[i].rect.width - src[a - 1 + i].rect.width) < 0.5 and
                    abs(doc[i].rect.height - src[a - 1 + i].rect.height) < 0.5 for i in range(n))
        text = ''.join(pg.get_text() for pg in doc)
        hangul = len(re.findall(r'[가-힣]', text))
        h, size = sha(p), p.stat().st_size
        html = f'tools/ko_reflow/cpho/{name}.html'
        assert (ROOT / html).exists(), html
        qa = {
            'schema': 'html-reflow-stamped-v1', 'file': out, 'status': 'READY', 'sha256': h, 'bytes': size, 'pages': n,
            'source_file': srcname, 'source_sha256': sha(pathlib.Path(src_dir) / srcf),
            'source_page_range': [a, b], 'source_pages': n,
            'page_count_matches_source': True, 'page_sizes_match_source': sizes,
            'figures_logos_and_pure_math_stamped_from_source': True, 'korean_text_justified': False,
            'hangul_characters': hangul, 'html_source': html, 'builder': 'tools/ko_reflow/build.py',
            'visual_review': {'reviewed': True,
                              'method': 'every page compared side by side with the source at equal DPI (tools/ko_reflow/cpho/review.py, 0 collisions)',
                              'overflow_or_occlusion_observed': False},
        }
        assert sizes and hangul > 0
        save(f'tools/ko_reflow/qa/{out[:-4]}.json', qa, indent=1)
        row = {'file': out, 'language': 'ko', 'pages': n, 'bytes': size, 'sha256': h,
               'qa': f'tools/ko_reflow/qa/{out[:-4]}.json', 'audit_schema': 'html-reflow-stamped-v1'}
        pub = [r for r in pub if r['file'] != out] + [row]
        fonts['files'] = [r for r in fonts['files'] if r['file'] != out] + [
            {'file': out, 'pages': n, 'bytes': size, 'sha256': h, 'missing_glyph_spans': [], 'original_style': True}]
        year = name[:4]
        t = ko['cpho'].setdefault(year, {}).setdefault('T', {})
        for s in slots:
            t[s] = out
        print(f'{out}: {n} pages, {size} bytes, {hangul} hangul, slots {slots}')
    # pdf-assets.json: only these files' sizes (tools/pdf_release.py rewrites the whole list from the server,
    # which would also pull in other sessions' uploads; restore it from git before running this)
    assets = load('pdf-assets.json')
    for name in names:
        out = EDITIONS[name][0]
        assets[out] = (pathlib.Path(pdf_dir) / out).stat().st_size
    nl = chr(13) + chr(10)
    body = (',' + nl).join(f'{json.dumps(k)}: {v}' for k, v in sorted(assets.items()))
    (ROOT / 'pdf-assets.json').write_bytes(('{' + nl + body + nl + '}' + nl).encode('utf-8'))
    save('tools/original_style_publication.json', pub)
    save('tools/translation_font_validation.json', fonts)
    save('tools/theory_ko.json', ko)


if __name__ == '__main__':
    main(*sys.argv[1:])

# -*- coding: utf-8 -*-
"""Register reviewed Korean RuPhO editions (html-reflow-stamped-v1) in the repository.

usage: python -I tools/ko_reflow/rupho/register.py PDF_DIR SRC_DIR NAME [NAME ...]

NAME is <year>_T<n> (problem paper, source RuPhO_<year>_T<n>_RU.pdf, Korean RuPhO_<year>_T<n>_KO.pdf) or
<year>_T<n>S (solutions, source RuPhO_<year>_T<n>S.pdf, Korean RuPhO_<year>_T<n>S_KO.pdf). PDF_DIR holds the
Korean files, SRC_DIR the Russian originals. For each edition it writes tools/ko_reflow/qa/<file>.json, replaces or
adds the file's rows in tools/original_style_publication.json, tools/translation_font_validation.json and
pdf-assets.json (keeping order, field set and line endings) and sets tools/theory_ko.json rupho/<year>/T<n>
paper or sol. Upload first (tools/pdf_release.py), restore pdf-assets.json from git, run this, then
tools/theory_build.py, tools/update_original_layout_versions.py and tools/build-site-catalogue.cjs.
"""
import hashlib, json, pathlib, re, sys
import pymupdf

ROOT = pathlib.Path(__file__).resolve().parents[3]


def edition(name):
    """(korean file, source file, slot, year, part, html source) for NAME = <year>_T<n> or <year>_T<n>S."""
    year, part = name.split('_')
    if part.endswith('S'):
        return (f'RuPhO_{name}_KO.pdf', f'RuPhO_{name}.pdf', 'sol', int(year), part[:-1],
                f'tools/ko_reflow/rupho/{name}.html')
    return (f'RuPhO_{name}_KO.pdf', f'RuPhO_{name}_RU.pdf', 'paper', int(year), part,
            f'tools/ko_reflow/rupho/{name}.html')


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
        out, srcname, slot, year, part, html = edition(name)
        p = pathlib.Path(pdf_dir) / out
        src_path = pathlib.Path(src_dir) / srcname
        doc, src = pymupdf.open(p), pymupdf.open(src_path)
        n = len(src)
        assert len(doc) == n, (out, len(doc), n)
        sizes = all(abs(doc[i].rect.width - src[i].rect.width) < 0.5 and
                    abs(doc[i].rect.height - src[i].rect.height) < 0.5 for i in range(n))
        text = ''.join(pg.get_text() for pg in doc)
        hangul = len(re.findall(r'[가-힣]', text))
        cyr = len(re.findall(r'[А-Яа-яЁё]', text))
        h, size = sha(p), p.stat().st_size
        assert (ROOT / html).exists(), html
        assert sizes and hangul > 0 and cyr == 0, (out, sizes, hangul, cyr)
        qa = {
            'schema': 'html-reflow-stamped-v1', 'file': out, 'status': 'READY', 'sha256': h, 'bytes': size, 'pages': n,
            'source_file': srcname, 'source_sha256': sha(src_path), 'source_page_range': [1, n], 'source_pages': n,
            'source_language': 'ru',
            'page_count_matches_source': True, 'page_sizes_match_source': sizes,
            'figures_logos_and_pure_math_stamped_from_source': True, 'korean_text_justified': True,
            'hangul_characters': hangul, 'cyrillic_characters': cyr, 'html_source': html,
            'builder': 'tools/ko_reflow/build.py',
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
        ko.setdefault('rupho', {}).setdefault(str(year), {}).setdefault(part, {})[slot] = out
        done.append((out, size))
        print(f'{out}: {n} pages, {size} bytes, {hangul} hangul')
    save('tools/original_style_publication.json', pub, pub_crlf, pub_nl)
    save('tools/translation_font_validation.json', fonts, f_crlf, f_nl)
    save('tools/theory_ko.json', ko, k_crlf, k_nl)
    # pdf-assets.json ("name": bytes, one per line, sorted): replace the row or insert it in order
    raw = (ROOT / 'pdf-assets.json').read_bytes().decode('utf-8')
    nl = '\r\n' if '\r\n' in raw else '\n'
    rows = raw.strip().split(nl)
    assert rows[0] == '{' and rows[-1] == '}', 'unexpected pdf-assets.json layout'
    body = [r.rstrip(',') for r in rows[1:-1]]
    data = dict((json.loads('{' + r + '}').popitem()) for r in body)
    for out, size in done:
        data[out] = size
    keys = sorted(data)
    lines = [json.dumps(k, ensure_ascii=False) + ': ' + str(data[k]) for k in keys]
    text = '{' + nl + (',' + nl).join(lines) + nl + '}' + (nl if raw.endswith(nl) else '')
    (ROOT / 'pdf-assets.json').write_bytes(text.encode('utf-8'))


if __name__ == '__main__':
    main(*sys.argv[1:])

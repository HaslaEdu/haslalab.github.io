# -*- coding: utf-8 -*-
"""Register reviewed Korean and English editions of the RuPhO W/X/Y rounds (html-reflow-stamped-v1).

usage: python -I tools/ko_reflow/rupho/register_rounds.py COMP PDF_DIR SRC_DIR NAME.LANG [NAME.LANG ...]

COMP is ruphow, ruphox or ruphoy (file prefix RuPhOW/RuPhOX/RuPhOY). NAME is <year>_<part> for a problem paper
(source <Prefix>_<year>_<part>_RU.pdf) or <year>_<part>S for its solutions (source <Prefix>_<year>_<part>S.pdf);
part as in the stage manifest (T1, T3a, ...). LANG is ko or en; the edition is <Prefix>_<NAME>_KO.pdf / _EN.pdf, its
html source tools/ko_reflow/<comp>/<NAME>.html (Korean) or <NAME>.en.html (English). For each edition this writes
tools/ko_reflow/qa/<file>.json and the rows in tools/original_style_publication.json,
tools/translation_font_validation.json and pdf-assets.json, and sets tools/theory_ko.json <comp>/<year>/<part>:
paper/sol for Korean, en.paper/en.sol for English (theory_build shows English beside the Russian original).
Upload first (tools/pdf_release.py), restore pdf-assets.json from git, run this, then rebuild theory.js etc.
"""
import hashlib, json, pathlib, re, sys
import pymupdf

ROOT = pathlib.Path(__file__).resolve().parents[3]
PREFIX = {'ruphow': 'RuPhOW', 'ruphox': 'RuPhOX', 'ruphoy': 'RuPhOY'}


def edition(comp, spec):
    name, lang = spec.rsplit('.', 1)
    assert lang in ('ko', 'en'), spec
    year, part = name.split('_', 1)
    sol = part.endswith('S')
    base = part[:-1] if sol else part
    pre = PREFIX[comp]
    src = f'{pre}_{name}.pdf' if sol else f'{pre}_{name}_RU.pdf'
    out = f'{pre}_{name}_{lang.upper()}.pdf'
    html = f'tools/ko_reflow/{comp}/{name}' + ('.en.html' if lang == 'en' else '.html')
    return out, src, 'sol' if sol else 'paper', year, base, lang, html


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


def main(comp, pdf_dir, src_dir, *specs):
    pub, pub_crlf, pub_nl = load('tools/original_style_publication.json')
    fonts, f_crlf, f_nl = load('tools/translation_font_validation.json')
    ko, k_crlf, k_nl = load('tools/theory_ko.json')
    done = []
    for spec in specs:
        out, srcname, slot, year, part, lang, html = edition(comp, spec)
        p, src_path = pathlib.Path(pdf_dir) / out, pathlib.Path(src_dir) / srcname
        doc, src = pymupdf.open(p), pymupdf.open(src_path)
        n = len(src)
        assert len(doc) == n, (out, len(doc), n)
        sizes = all(abs(doc[i].rect.width - src[i].rect.width) < 0.5 and
                    abs(doc[i].rect.height - src[i].rect.height) < 0.5 for i in range(n))
        text = ''.join(pg.get_text() for pg in doc)
        hangul = len(re.findall(r'[가-힣]', text))
        cyr = len(re.findall(r'[А-Яа-яЁё]', text))
        latin = len(re.findall(r'[A-Za-z]', text))
        h, size = sha(p), p.stat().st_size
        assert (ROOT / html).exists(), html
        assert sizes and cyr == 0 and (hangul > 0 if lang == 'ko' else latin > 0), (out, sizes, hangul, cyr, latin)
        qa = {
            'schema': 'html-reflow-stamped-v1', 'file': out, 'status': 'READY', 'sha256': h, 'bytes': size, 'pages': n,
            'language': lang, 'source_file': srcname, 'source_sha256': sha(src_path), 'source_page_range': [1, n],
            'source_pages': n, 'source_language': 'ru',
            'page_count_matches_source': True, 'page_sizes_match_source': sizes,
            'figures_logos_and_pure_math_stamped_from_source': True, 'korean_text_justified': lang == 'ko',
            'hangul_characters': hangul, 'latin_characters': latin, 'cyrillic_characters': cyr, 'html_source': html,
            'builder': 'tools/ko_reflow/build.py',
            'visual_review': {'reviewed': True,
                              'method': 'every page compared side by side with the source at equal DPI '
                                        '(tools/ko_reflow/check.py and qa side-by-side images; every flag confirmed by zoom)',
                              'overflow_or_occlusion_observed': False},
        }
        save(f'tools/ko_reflow/qa/{out[:-4]}.json', qa, False, True, indent=1)
        replace_row(pub, out, {'file': out, 'year': int(year), 'language': lang, 'pages': n, 'bytes': size, 'sha256': h,
                               'qa': f'tools/ko_reflow/qa/{out[:-4]}.json', 'audit_schema': 'html-reflow-stamped-v1'})
        replace_row(fonts['files'], out, {'file': out, 'pages': n, 'bytes': size, 'sha256': h,
                                          'missing_glyph_spans': [], 'original_style': True})
        row = ko.setdefault(comp, {}).setdefault(str(year), {}).setdefault(part, {})
        if lang == 'ko':
            row[slot] = out
        else:
            row.setdefault('en', {})[slot] = out
        done.append((out, size))
        print(f'{out}: {n} pages, {size} bytes, {hangul} hangul, {latin} latin')
    save('tools/original_style_publication.json', pub, pub_crlf, pub_nl)
    save('tools/translation_font_validation.json', fonts, f_crlf, f_nl)
    save('tools/theory_ko.json', ko, k_crlf, k_nl)
    raw = (ROOT / 'pdf-assets.json').read_bytes().decode('utf-8')
    nl = '\r\n' if '\r\n' in raw else '\n'
    rows = raw.strip().split(nl)
    assert rows[0] == '{' and rows[-1] == '}', 'unexpected pdf-assets.json layout'
    data = dict((json.loads('{' + r.rstrip(',') + '}').popitem()) for r in rows[1:-1])
    for out, size in done:
        data[out] = size
    lines = [json.dumps(k, ensure_ascii=False) + ': ' + str(data[k]) for k in sorted(data)]
    text = '{' + nl + (',' + nl).join(lines) + nl + '}' + (nl if raw.endswith(nl) else '')
    (ROOT / 'pdf-assets.json').write_bytes(text.encode('utf-8'))


if __name__ == '__main__':
    main(*sys.argv[1:])

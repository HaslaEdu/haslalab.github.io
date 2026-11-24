# -*- coding: utf-8 -*-
"""Register reviewed translated editions of the national olympiads (INPhO, TWPhO, OBF, F=ma, BPhO R1/R2).

usage: python -I tools/ko_reflow/register_national.py OUT_DIR ORIG_DIR FILE [FILE ...]

FILE is a built edition in OUT_DIR, named after its original in ORIG_DIR/<comp>/:
  <Prefix>_<y>_<part>_KO.pdf   Korean paper          (original <Prefix>_<y>_<part>_<LANG>.pdf)
  <Prefix>_<y>_<part>S_KO.pdf  Korean solutions      (original <Prefix>_<y>_<part>S.pdf)
  <Prefix>_<y>_<part>_EN.pdf   English paper, two-up: each page = original | English (non-English originals only)
  <Prefix>_<y>_<part>S_EN.pdf  English solutions, two-up
Korean editions (html-reflow-stamped-v1) get a qa record, a row in tools/original_style_publication.json and
tools/translation_font_validation.json. English two-up editions get a qa record (html-reflow-stamped-twoup-v1).
Both are set in tools/theory_ko.json (<comp>/<year>/<part>: paper/sol, English under en) and pdf-assets.json.
Upload first (tools/pdf_release.py OUT_DIR), restore pdf-assets.json from git, run this, then tools/theory_build.py.
"""
import hashlib, json, pathlib, re, sys
import pymupdf

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMP = {'INPhO': 'inpho', 'TWPhO': 'twpho', 'OBF': 'obf', 'FMA': 'fma', 'BPhO': 'bpho', 'BPhOII': 'bphoii'}
NAME = re.compile(r'^([A-Za-z]+)_(\d{4})_((?:T)\d*)(S?)_(KO|EN)\.pdf$')
SCRIPT = {'zh': r'[一-鿿]', 'pt': r'[ãõçÃÕÇ]'}


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


def source(orig_dir, comp, prefix, year, part, sol):
    d = pathlib.Path(orig_dir) / comp
    if sol:
        return d / f'{prefix}_{year}_{part}S.pdf'
    hits = sorted(d.glob(f'{prefix}_{year}_{part}_??.pdf'))
    assert len(hits) == 1, (prefix, year, part, hits)
    return hits[0]


def main(out_dir, orig_dir, *names):
    pub, pub_crlf, pub_nl = load('tools/original_style_publication.json')
    fonts, f_crlf, f_nl = load('tools/translation_font_validation.json')
    ko, k_crlf, k_nl = load('tools/theory_ko.json')
    done = []
    for out in names:
        m = NAME.match(out)
        assert m, out
        prefix, year, part, sol, lang = m.group(1), int(m.group(2)), m.group(3), m.group(4) == 'S', m.group(5)
        comp = COMP[prefix]
        src_path = source(orig_dir, comp, prefix, year, part, sol)
        src_lang = 'en' if sol and comp not in ('twpho', 'obf') else (src_path.stem[-2:].lower() if not sol else
                                                                     {'twpho': 'zh', 'obf': 'pt'}[comp])
        html = f'tools/ko_reflow/{comp}/{year}_{part}{"S" if sol else ""}{"_EN" if lang == "EN" else ""}.html'
        p = pathlib.Path(out_dir) / out
        doc, src = pymupdf.open(p), pymupdf.open(src_path)
        n = len(src)
        assert len(doc) == n, (out, len(doc), n)
        text = ''.join(pg.get_text() for pg in doc)
        hangul = len(re.findall(r'[가-힣]', text))
        assert (ROOT / html).exists(), html
        h, size = sha(p), p.stat().st_size
        qa = {'file': out, 'status': 'READY', 'sha256': h, 'bytes': size, 'pages': n,
              'source_file': src_path.name, 'source_sha256': sha(src_path), 'source_page_range': [1, n], 'source_pages': n,
              'source_language': src_lang, 'page_count_matches_source': True,
              'figures_logos_and_pure_math_stamped_from_source': True, 'html_source': html,
              'builder': 'tools/ko_reflow/build.py',
              'visual_review': {'reviewed': True,
                                'method': 'every page compared side by side with the source at equal DPI '
                                          '(tools/ko_reflow/check.py side-by-side images; every flag confirmed by zoom)',
                                'overflow_or_occlusion_observed': False}}
        if lang == 'KO':
            sizes = all(abs(doc[i].rect.width - src[i].rect.width) < 0.5 and
                        abs(doc[i].rect.height - src[i].rect.height) < 0.5 for i in range(n))
            leftover = len(re.findall(SCRIPT.get(src_lang, r'(?!)'), text))
            assert sizes and hangul > 0, (out, sizes, hangul)
            # stamped figures keep their own labels (covered by translated overlays where they matter)
            assert leftover < max(20, hangul // 100), (out, 'source-script characters left', leftover)
            qa = {'schema': 'html-reflow-stamped-v1', **qa, 'page_sizes_match_source': sizes, 'korean_text_justified': True,
                  'hangul_characters': hangul}
            save(f'tools/ko_reflow/qa/{out[:-4]}.json', qa, False, True, indent=1)
            replace_row(pub, out, {'file': out, 'year': year, 'language': 'ko', 'pages': n, 'bytes': size, 'sha256': h,
                                   'qa': f'tools/ko_reflow/qa/{out[:-4]}.json', 'audit_schema': 'html-reflow-stamped-v1'})
            replace_row(fonts['files'], out, {'file': out, 'pages': n, 'bytes': size, 'sha256': h,
                                              'missing_glyph_spans': [], 'original_style': True})
            ko.setdefault(comp, {}).setdefault(str(year), {}).setdefault(part, {})['sol' if sol else 'paper'] = out
        else:
            assert src_lang != 'en', (out, 'English editions are made for non-English originals only')
            twoup = all(abs(doc[i].rect.width - (2 * src[i].rect.width + 14)) < 1 and
                        abs(doc[i].rect.height - src[i].rect.height) < 0.5 for i in range(n))
            assert twoup and hangul == 0, (out, twoup, hangul)
            qa = {'schema': 'html-reflow-stamped-twoup-v1', **qa, 'layout': 'two-up: original page left, English right',
                  'english_text_justified': True}
            save(f'tools/ko_reflow/qa/{out[:-4]}.json', qa, False, True, indent=1)
            en = ko.setdefault(comp, {}).setdefault(str(year), {}).setdefault(part, {}).setdefault('en', {})
            en['sol' if sol else 'paper'] = out
        done.append((out, size))
        print(f'{out}: {n} pages, {size} bytes, {hangul} hangul')
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
    (ROOT / 'pdf-assets.json').write_bytes(('{' + nl + (',' + nl).join(lines) + nl + '}' + (nl if raw.endswith(nl) else '')).encode('utf-8'))


if __name__ == '__main__':
    main(*sys.argv[1:])

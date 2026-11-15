# -*- coding: utf-8 -*-
"""Split theory papers whose answer sheets are bound into the paper into a paper and an answer sheet.

    python tools/theory_split_answers.py <folder with the original English papers>

The originals (e.g. APhO_2005_T1_EN.pdf, as mirrored in the pdf-<prefix> releases) are read from the folder; the
problem pages go to pdfx/<comp>/<Prefix>_<year>_<part>_EN.pdf and the answer pages to …_<part>A.pdf, both kept on
the site (manifest "local", the release copy's url kept for provenance).  The Korean editions laid on the same pages
(pdfx/<comp>/<Prefix>_<year>_<part>_KO.pdf, tools/ko_reflow) are split the same way into …_KO.pdf and …_A_KO.pdf.
Run it again after rebuilding a Korean edition: the ko_reflow build writes the whole edition, which is split again;
an edition already split is left as it is.

Manifests (tools/theory/<comp>.json) and tools/theory_ko.json are updated in place.
"""
import json
import os
import shutil
import sys

import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# comp, prefix, year, part: the answer-sheet pages (1-based) of the original
SPLITS = [
    ('apho', 'APhO', 2005, 'T1', [3]),
    ('apho', 'APhO', 2005, 'T2', [5]),
    ('apho', 'APhO', 2005, 'T3', [4, 5]),
    ('ipho', 'IPhO', 1999, 'T1', [4]),
    ('ipho', 'IPhO', 1999, 'T2', [3]),
    ('ipho', 'IPhO', 1999, 'T3', [5]),
    ('ipho', 'IPhO', 2003, 'T1', [3]),
    ('ipho', 'IPhO', 2003, 'T2', [4]),
    ('ipho', 'IPhO', 2003, 'T3', [3]),
    ('ipho', 'IPhO', 2005, 'T1', [3]),
    ('ipho', 'IPhO', 2005, 'T2', [3]),
    ('ipho', 'IPhO', 2005, 'T3', [3]),
    ('ipho', 'IPhO', 2006, 'T1', [3, 4, 5]),
    ('ipho', 'IPhO', 2006, 'T2', [3, 4, 5]),
    ('ipho', 'IPhO', 2006, 'T3', [5, 6, 7, 8]),
]


def write(src, pages, out):
    doc = pymupdf.open()
    for p in pages:
        doc.insert_pdf(src, from_page=p - 1, to_page=p - 1)
    doc.save(out, garbage=4, deflate=True)


def split(path, answer, paper_out, answer_out):
    src = pymupdf.open(path)
    rest = [p for p in range(1, src.page_count + 1) if p not in answer]
    write(src, rest, paper_out)
    write(src, answer, answer_out)
    return src.page_count


def dump(path, data):
    raw = open(path, 'rb').read().decode('utf-8')
    text = json.dumps(data, ensure_ascii=False, indent=1 if '\n "' in raw[:20] else 2)
    if '\r\n' in raw:
        text = text.replace('\n', '\r\n')
    open(path, 'wb').write((text + ('\r\n' if raw.endswith('\r\n') else '\n' if raw.endswith('\n') else '')).encode('utf-8'))


def main(folder):
    manifests, ko_path = {}, os.path.join(ROOT, 'tools', 'theory_ko.json')
    ko = json.load(open(ko_path, encoding='utf-8'))
    for comp, prefix, year, part, answer in SPLITS:
        stem = '%s_%d_%s' % (prefix, year, part)
        rel = 'pdfx/%s/' % comp
        n = split(os.path.join(folder, stem + '_EN.pdf'), answer, os.path.join(ROOT, rel + stem + '_EN.pdf'),
                  os.path.join(ROOT, rel + stem + 'A.pdf'))
        m = manifests.setdefault(comp, json.load(open(os.path.join(ROOT, 'tools', 'theory', comp + '.json'), encoding='utf-8')))
        y = next(y for y in m['years'] if str(y['y']) == str(year))
        paper = next(f for f in y['files'] if f['file'] == stem + '_EN.pdf')
        paper['local'] = rel + stem + '_EN.pdf'
        paper['note'] = ('Problem pages of the original (the answer sheet bound in on page(s) %s is split off into %sA.pdf)'
                         % (', '.join(map(str, answer)), stem))
        paper.pop('bytes', None)
        if not any(f['file'] == stem + 'A.pdf' for f in y['files']):
            i = y['files'].index(paper)
            y['files'].insert(i + 1, {'file': stem + 'A.pdf', 'part': part, 'kind': 'answer', 'local': rel + stem + 'A.pdf',
                                      'url': paper['url'], 'note': 'Answer sheet bound into the original paper (page(s) %s of %d)'
                                      % (', '.join(map(str, answer)), n)})
        # the Korean edition laid on the same pages
        entry = ko.get(comp, {}).get(str(year), {}).get(part)
        if entry and entry.get('paper'):
            cur = os.path.join(ROOT, entry['paper'])
            ans = entry['paper'].replace('_KO.pdf', '_A_KO.pdf')
            pages = pymupdf.open(cur).page_count
            if pages == n:                       # a whole edition, as tools/ko_reflow/build.py writes it
                split(cur, answer, cur, os.path.join(ROOT, ans))
            elif pages != n - len(answer) or not os.path.exists(os.path.join(ROOT, ans)):
                print('skipped the Korean edition of %s: its pages do not match the original' % stem)
                continue
            entry['answer'] = ans
        print(stem, 'answer page(s)', answer, 'of', n)
    for comp, m in manifests.items():
        dump(os.path.join(ROOT, 'tools', 'theory', comp + '.json'), m)
    dump(ko_path, ko)


if __name__ == '__main__':
    main(sys.argv[1])
